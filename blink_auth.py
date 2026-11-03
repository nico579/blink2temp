"""Authentification Blink et gestion de session.

Réutilise la session Blink existante (notamment celle de blink2video si disponible)
ou permet une nouvelle connexion interactive avec support 2FA.
"""

from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager
import getpass
import json
import os
from pathlib import Path
import stat as stat_module
import time
import uuid

from aiohttp import ClientSession, TCPConnector
from blinkpy.auth import Auth, BlinkTwoFARequiredError
from blinkpy.blinkpy import Blink

import blink_tls
import paths

AUTH_FIELDS = (
    "username", "token", "expires_in", "expiration_date", "refresh_token",
    "host", "region_id", "client_id", "account_id", "user_id", "hardware_id",
)

DOSSIER_LOCAL = paths.dossier_donnees()
DOSSIER_APPDATA = Path(os.environ.get("LOCALAPPDATA", str(Path.home()))) / "blink2temp"
DOSSIER_BLINK2VIDEO = Path(os.environ.get("LOCALAPPDATA", str(Path.home()))) / "blink2video"
DOSSIER_BLINK_SRC = Path.home() / "Documents" / "blink"

CONFIG_CANDIDATES = [
    DOSSIER_LOCAL / "blink_auth.json",
    DOSSIER_APPDATA / "blink_auth.json",
    DOSSIER_BLINK2VIDEO / "blink_auth.json",
    DOSSIER_BLINK_SRC / "blink_auth.json",
]


def session_path() -> Path:
    """Retourne le chemin du fichier de session à utiliser."""
    for candidate in CONFIG_CANDIDATES:
        if candidate.exists():
            return candidate
    return DOSSIER_LOCAL / "blink_auth.json"


def contexte_tls():
    return blink_tls.contexte_tls()


def session_http() -> ClientSession:
    return ClientSession(connector=TCPConnector(ssl=contexte_tls()))


@asynccontextmanager
async def session_http_temporaire():
    session = session_http()
    try:
        yield session
    finally:
        await session.close()
        await asyncio.sleep(0.250)


def load_saved_session() -> tuple[dict | None, Path]:
    """Charge une session enregistrée depuis l'un des chemins connus."""
    chemin = session_path()
    if not chemin.exists():
        return None, chemin

    try:
        data = json.loads(chemin.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None, chemin

    if not isinstance(data, dict):
        return None, chemin

    if not isinstance(data.get("refresh_token"), str) or not data["refresh_token"]:
        return None, chemin

    data["username"] = data.get("username", "")
    data["password"] = ""
    return data, chemin


def ask_credentials() -> dict:
    """Demande les identifiants en ligne de commande."""
    print("\nConnexion au compte Blink")
    username = input("Adresse e-mail : ").strip()
    password = getpass.getpass("Mot de passe (non affiché) : ")
    return {"username": username, "password": password}


def make_blink(session: ClientSession, login_data: dict, dest_path: Path | None = None) -> Blink:
    blink = Blink(session=session)
    dest = dest_path or session_path()
    blink.auth = Auth(
        login_data,
        no_prompt=True,
        session=session,
        callback=lambda: save_session(blink, dest),
    )
    return blink


async def prompt_2fa_code(attempt: int) -> str:
    return input("Code de vérification Blink (reçu par email/SMS) : ").strip()


async def finish_login(blink: Blink, ask_code=None) -> bool:
    try:
        connected = await blink.start()
    except BlinkTwoFARequiredError:
        ask_code = ask_code or prompt_2fa_code
        print("\nUn code de vérification Blink vient d'être envoyé.")
        for attempt in range(3):
            code = (await ask_code(attempt) or "").strip()
            if code and await blink.send_2fa_code(code):
                return True
            restant = 2 - attempt
            if restant > 0:
                print(f"Code refusé. {restant} tentative(s) restante(s).")
        return False
    return bool(connected)


def save_session(blink: Blink, path: Path | None = None) -> None:
    """Sauvegarde les jetons rafraîchis en évitant d'écraser une session plus récente."""
    target = path or session_path()
    complet = blink.auth.login_attributes or {}
    data = {champ: complet[champ] for champ in AUTH_FIELDS if champ in complet}
    data["updated_at"] = time.time()

    target.parent.mkdir(parents=True, exist_ok=True)
    temp = target.with_name(f"{target.stem}.{os.getpid()}.{uuid.uuid4().hex[:8]}.tmp")
    try:
        temp.write_text(json.dumps(data, indent=2), encoding="utf-8")
        if os.name != "nt":
            os.chmod(temp, stat_module.S_IRUSR | stat_module.S_IWUSR)
        temp.replace(target)
    except OSError:
        pass
    finally:
        temp.unlink(missing_ok=True)


async def connect(session: ClientSession, interactive: bool = True) -> Blink | None:
    """Connexion au compte Blink.

    Tente d'abord de charger la session enregistrée, puis se rabat sur la saisie interactive
    si `interactive=True`.
    """
    saved, path = load_saved_session()
    if saved:
        print(f"Connexion via la session enregistrée ({path.name})...")
        blink = make_blink(session, saved, path)
        if await finish_login(blink, ask_code=prompt_2fa_code if interactive else None):
            save_session(blink, path)
            return blink
        print("La session enregistrée a expiré ou n'est plus valide.")

    if not interactive:
        return None

    creds = ask_credentials()
    target_path = DOSSIER_LOCAL / "blink_auth.json"
    blink = make_blink(session, creds, target_path)
    if not await finish_login(blink):
        print("Échec de l'authentification Blink.")
        return None

    save_session(blink, target_path)
    print("Connexion réussie et session sauvegardée.")
    return blink
