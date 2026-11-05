"""Mise à jour depuis la dernière release GitHub.

Deux temps, séparés parce qu'ils n'ont pas le même risque.

Le premier ne fait que demander à GitHub quelle est la dernière version
publiée, la comparer à la nôtre et garder la réponse en cache (six heures).
C'est ce qui allume le bouton dans le tableau de bord.

Le second remplace l'installation. Un exécutable ne peut pas se remplacer
pendant qu'il tourne : on télécharge donc l'archive de la plateforme, on
vérifie son empreinte SHA-256, on extrait le nouvel exécutable et on vérifie
qu'il répond à ``--version``. C'est ensuite *lui*, lancé depuis le dossier de
préparation, qui attend l'arrêt de l'ancien processus, installe le binaire et
relance l'application avec les mêmes arguments.

Depuis les sources (dépôt git), le même déroulé remplace le téléchargement par
``git pull --ff-only`` : rien n'est touché tant que la nouvelle version n'est
pas sur disque.
"""

from __future__ import annotations

import hashlib
import json
import os
import platform
import re
import shutil
import stat
import subprocess
import sys
import tarfile
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
import zipfile
from pathlib import Path, PurePosixPath
from typing import Any, Optional

import paths

DEPOT = "nico579/blink2temp"
API_LATEST = f"https://api.github.com/repos/{DEPOT}/releases/latest"
PAGE_RELEASES = f"https://github.com/{DEPOT}/releases/latest"
CACHE_FICHIER = "maj.json"
JOURNAL_MAJ = "maj.log"

FRAICHEUR_S = 6 * 3600
MAX_JSON_BYTES = 1024 * 1024
MAX_ARCHIVE_BYTES = 200 * 1024 * 1024
MAX_EXTRACTED_BYTES = 300 * 1024 * 1024
MAX_ARCHIVE_MEMBERS = 10_000
MAX_EMPREINTE_BYTES = 64 * 1024

HOTES_AUTORISES = (
    "api.github.com",
    "github.com",
    "objects.githubusercontent.com",
    "release-assets.githubusercontent.com",
)
VERSION_TAG_RE = re.compile(r"^v?\d+\.\d+\.\d+$")
SHA256_RE = re.compile(r"^[0-9a-fA-F]{64}$")
NOM_ARCHIVE_RE = re.compile(r"^blink2temp-(\d+\.\d+\.\d+)-(windows-x64|linux-x64|macos-x64|macos-arm64)\.(zip|tar\.gz)$")


class UpdaterError(Exception):
    """Erreur de mise à jour destinée à être affichée telle quelle."""


# ------------------------------------------------------------------ versions

def numeros(version: str) -> tuple:
    """« v1.6.10 » devient (1, 6, 10), comparable à un autre tuple.

    Une comparaison de chaînes rangerait 1.6.10 avant 1.6.9.
    """
    return tuple(int(n) for n in re.findall(r"\d+", str(version))[:3]) or (0,)


def version_locale() -> str:
    """Version de l'application en cours d'exécution.

    Le fichier VERSION est lu à chaque appel : après un ``git pull``, c'est
    bien la nouvelle version sur disque qui est comparée. Dans un bundle
    PyInstaller, il est embarqué par ``tools/build_bundle.py``.
    """
    try:
        return (paths.dossier_ressources() / "VERSION").read_text(
            encoding="utf-8"
        ).strip().lstrip("vV")
    except OSError:
        return "0.0.0"


def artefact() -> str:
    """Nom de la plateforme tel qu'il figure dans les archives publiées."""
    if sys.platform == "win32":
        return "windows-x64"
    if sys.platform == "darwin":
        return "macos-arm64" if platform.machine().lower() in ("arm64", "aarch64") else "macos-x64"
    return "linux-x64"


# ------------------------------------------------------------------ cache local

def _chemin_cache() -> Path:
    return paths.dossier_donnees() / CACHE_FICHIER


def _lire_cache() -> dict:
    try:
        donnees = json.loads(_chemin_cache().read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    if not isinstance(donnees, dict):
        return {}
    if not VERSION_TAG_RE.fullmatch(str(donnees.get("version") or "")):
        return {}
    try:
        donnees["verifie"] = float(donnees.get("verifie") or 0)
    except (TypeError, ValueError):
        donnees["verifie"] = 0.0
    if not isinstance(donnees.get("assets"), list):
        donnees["assets"] = []
    return donnees


def _ecrire_cache(cache: dict) -> None:
    try:
        chemin = _chemin_cache()
        chemin.parent.mkdir(parents=True, exist_ok=True)
        temporaire = chemin.with_name(f"{chemin.name}.{os.getpid()}.tmp")
        temporaire.write_text(json.dumps(cache, ensure_ascii=False), encoding="utf-8")
        temporaire.replace(chemin)
    except OSError:
        pass


# ------------------------------------------------------------------ GitHub

def _ouvrir_json(url: str) -> dict:
    requete = urllib.request.Request(url, headers={
        "Accept": "application/vnd.github+json",
        "User-Agent": f"blink2temp/{version_locale()}",
    })
    with urllib.request.urlopen(requete, timeout=15) as reponse:
        corps = reponse.read(MAX_JSON_BYTES + 1)
    if len(corps) > MAX_JSON_BYTES:
        raise UpdaterError("Réponse de GitHub trop volumineuse.")
    donnees = json.loads(corps.decode("utf-8"))
    if not isinstance(donnees, dict):
        raise UpdaterError("Réponse de GitHub invalide.")
    return donnees


def _interroger_github() -> dict:
    """Dernière release publiée, réduite aux champs utiles."""
    release = _ouvrir_json(API_LATEST)
    if release.get("draft") or release.get("prerelease"):
        raise UpdaterError("La dernière release GitHub n'est pas publiée.")
    version = str(release.get("tag_name") or "").lstrip("vV")
    if not VERSION_TAG_RE.fullmatch(version):
        raise UpdaterError("La dernière release GitHub n'a pas de version valide.")
    assets = [
        {cle: brut.get(cle) for cle in ("name", "browser_download_url", "size", "digest")}
        for brut in (release.get("assets") or [])
        if isinstance(brut, dict)
    ]
    return {
        "verifie": time.time(),
        "version": version,
        "page": str(release.get("html_url") or PAGE_RELEASES),
        "notes": str(release.get("body") or "")[:4000],
        "assets": assets,
    }


def verifier_release(force: bool = False, reseau: bool = True) -> dict:
    """Cache de la dernière release, rafraîchi au plus toutes les six heures."""
    cache = _lire_cache()
    age = time.time() - float(cache.get("verifie") or 0)
    if reseau and (force or not cache or age < 0 or age >= FRAICHEUR_S):
        try:
            cache = _interroger_github()
            _ecrire_cache(cache)
        except (UpdaterError, urllib.error.URLError, OSError, ValueError, json.JSONDecodeError):
            # Hors ligne ou API limitée : on garde ce que l'on savait.
            pass
    return cache


# ------------------------------------------------------------------ archives

def _sha256_normalise(valeur: Any) -> str:
    texte = str(valeur or "").strip()
    if texte.lower().startswith("sha256:"):
        texte = texte.split(":", 1)[1].strip()
    return texte.lower() if SHA256_RE.fullmatch(texte) else ""


def _url_https_github(url: str) -> bool:
    try:
        analyse = urllib.parse.urlparse(str(url))
        port = analyse.port
    except ValueError:
        return False
    hote = (analyse.hostname or "").lower().rstrip(".")
    autorise = any(hote == suffixe or hote.endswith("." + suffixe) for suffixe in HOTES_AUTORISES)
    return (
        analyse.scheme == "https"
        and autorise
        and port in (None, 443)
        and analyse.username is None
        and analyse.password is None
    )


def _url_release_officielle(url: str, nom: str) -> bool:
    """Lie l'URL au dépôt, au format de tag et au fichier attendus."""
    if not NOM_ARCHIVE_RE.fullmatch(nom) and nom != "SHA256SUMS.txt":
        return False
    try:
        analyse = urllib.parse.urlparse(str(url))
    except ValueError:
        return False
    attendu = ["", *DEPOT.split("/"), "releases", "download"]
    morceaux = urllib.parse.unquote(analyse.path).split("/")
    return (
        analyse.scheme == "https"
        and analyse.hostname == "github.com"
        and analyse.username is None
        and analyse.password is None
        and analyse.port is None
        and not analyse.params
        and not analyse.query
        and not analyse.fragment
        and len(morceaux) == len(attendu) + 2
        and morceaux[:len(attendu)] == attendu
        and VERSION_TAG_RE.fullmatch(morceaux[-2]) is not None
        and morceaux[-1] == nom
    )


def choisir_archive(assets: list, version: str, plateforme: Optional[str] = None) -> dict:
    """L'archive publiée qui correspond à cette machine, s'il y en a une."""
    plateforme = plateforme or artefact()
    extension = ".zip" if plateforme.startswith("windows") else ".tar.gz"
    nom = f"blink2temp-{version}-{plateforme}{extension}"
    par_nom = {
        str(asset.get("name") or ""): asset
        for asset in assets
        if isinstance(asset, dict)
    }
    brut = par_nom.get(nom)
    if not brut:
        return {}
    url = str(brut.get("browser_download_url") or "")
    if not _url_release_officielle(url, nom):
        return {}
    try:
        taille = int(brut.get("size") or 0)
    except (TypeError, ValueError):
        return {}
    if not 1 <= taille <= MAX_ARCHIVE_BYTES:
        return {}
    empreinte = _sha256_normalise(brut.get("digest"))
    checksum_url = ""
    if not empreinte:
        sommes = par_nom.get("SHA256SUMS.txt") or {}
        candidate = str(sommes.get("browser_download_url") or "")
        if _url_release_officielle(candidate, "SHA256SUMS.txt"):
            checksum_url = candidate
    return {
        "nom": nom,
        "url": url,
        "taille": taille,
        "sha256": empreinte,
        "checksum_url": checksum_url,
    }


def _lire_empreinte(url: str, nom_archive: str) -> str:
    if not _url_release_officielle(url, "SHA256SUMS.txt"):
        raise UpdaterError("Empreinte de mise à jour étrangère à la release officielle.")
    requete = urllib.request.Request(url, headers={
        "User-Agent": f"blink2temp/{version_locale()}",
    })
    with urllib.request.urlopen(requete, timeout=15) as reponse:
        if not _url_https_github(reponse.geturl()):
            raise UpdaterError("La redirection de l'empreinte quitte GitHub.")
        corps = reponse.read(MAX_EMPREINTE_BYTES + 1)
    if len(corps) > MAX_EMPREINTE_BYTES:
        raise UpdaterError("Fichier d'empreinte anormalement volumineux.")
    valeurs = [
        morceaux.group(1).lower()
        for ligne in corps.decode("utf-8", "replace").splitlines()
        if (morceaux := re.fullmatch(r"([0-9a-fA-F]{64})\s+\*?(.+)", ligne.strip()))
        and morceaux.group(2) == nom_archive
    ]
    if len(valeurs) != 1:
        raise UpdaterError("Empreinte de mise à jour absente ou ambiguë.")
    return valeurs[0]


def _empreinte_attendue(archive: dict) -> str:
    empreinte = _sha256_normalise(archive.get("sha256"))
    if empreinte:
        return empreinte
    url = str(archive.get("checksum_url") or "")
    if url:
        return _lire_empreinte(url, str(archive.get("nom") or ""))
    raise UpdaterError(
        "Cette release ne fournit aucune empreinte SHA-256 : mise à jour "
        "automatique refusée. Téléchargez-la manuellement depuis GitHub."
    )


def _telecharger(url: str, destination: Path, taille: int, empreinte: str,
                 progression=None) -> None:
    nom = destination.name
    if not _url_release_officielle(url, nom):
        raise UpdaterError("URL d'archive étrangère à la release officielle.")
    if not 1 <= taille <= MAX_ARCHIVE_BYTES:
        raise UpdaterError("Taille d'archive invalide.")
    if not empreinte:
        raise UpdaterError("Empreinte SHA-256 d'archive invalide.")

    requete = urllib.request.Request(url, headers={
        "Accept": "application/octet-stream",
        "User-Agent": f"blink2temp/{version_locale()}",
    })
    hacheur = hashlib.sha256()
    recu = 0
    dernier = 0.0
    try:
        with urllib.request.urlopen(requete, timeout=60) as reponse:
            if not _url_https_github(reponse.geturl()):
                raise UpdaterError("La redirection de l'archive quitte GitHub ou HTTPS.")
            annoncee = reponse.headers.get("Content-Length")
            if annoncee:
                try:
                    if int(annoncee) != taille:
                        raise UpdaterError("Taille HTTP inattendue pour la mise à jour.")
                except ValueError as err:
                    raise UpdaterError("Taille HTTP invalide pour la mise à jour.") from err
            with destination.open("xb") as sortie:
                while True:
                    bloc = reponse.read(262144)
                    if not bloc:
                        break
                    recu += len(bloc)
                    if recu > taille:
                        raise UpdaterError("L'archive dépasse la taille publiée.")
                    sortie.write(bloc)
                    hacheur.update(bloc)
                    if progression and time.time() - dernier > 0.3:
                        dernier = time.time()
                        progression(recu / taille, "Téléchargement de la mise à jour")
    except Exception:
        destination.unlink(missing_ok=True)
        raise

    if recu != taille:
        destination.unlink(missing_ok=True)
        raise UpdaterError(f"Archive tronquée : {recu} octets reçus, {taille} attendus.")
    obtenue = hacheur.hexdigest()
    if obtenue != empreinte:
        destination.unlink(missing_ok=True)
        raise UpdaterError("Empreinte SHA-256 incorrecte : archive corrompue ou modifiée.")


# ------------------------------------------------------------------ extraction

def _destination_sure(racine: Path, nom: str) -> Path:
    brut = str(nom or "").replace("\\", "/").rstrip("/")
    posix = PurePosixPath(brut)
    morceaux = brut.split("/")
    if (not brut or posix.is_absolute()
            or any(morceau in ("", ".", "..") for morceau in morceaux)):
        raise UpdaterError(f"Chemin dangereux dans l'archive : {nom!r}")
    cible = (racine / Path(*morceaux)).resolve()
    racine = racine.resolve()
    if cible != racine and racine not in cible.parents:
        raise UpdaterError(f"Chemin hors du dossier d'extraction : {nom!r}")
    return cible


def _extraire_zip(archive: Path, racine: Path) -> None:
    with zipfile.ZipFile(archive) as paquet:
        membres = paquet.infolist()
        if len(membres) > MAX_ARCHIVE_MEMBERS:
            raise UpdaterError("Archive contenant trop de fichiers.")
        total = 0
        plan = []
        for membre in membres:
            genre_de_fichier = stat.S_IFMT((membre.external_attr >> 16) & 0xFFFF)
            if membre.is_dir():
                genre = "dir"
            elif genre_de_fichier in (0, stat.S_IFREG):
                genre = "fichier"
                total += membre.file_size
            else:
                raise UpdaterError(f"Lien ou type de fichier interdit : {membre.filename!r}")
            if total > MAX_EXTRACTED_BYTES:
                raise UpdaterError("Contenu de l'archive trop volumineux.")
            plan.append((membre, _destination_sure(racine, membre.filename), genre))
        for _, cible, genre in plan:
            if genre == "dir":
                cible.mkdir(parents=True, exist_ok=True)
        for membre, cible, genre in plan:
            if genre != "fichier":
                continue
            cible.parent.mkdir(parents=True, exist_ok=True)
            with paquet.open(membre) as source, cible.open("xb") as sortie:
                shutil.copyfileobj(source, sortie)


def _extraire_tar(archive: Path, racine: Path) -> None:
    with tarfile.open(archive) as paquet:
        membres = paquet.getmembers()
        if len(membres) > MAX_ARCHIVE_MEMBERS:
            raise UpdaterError("Archive contenant trop de fichiers.")
        total = 0
        plan = []
        for membre in membres:
            if membre.isdir():
                genre = "dir"
            elif membre.isfile() and not getattr(membre, "sparse", None):
                genre = "fichier"
                total += membre.size
            else:
                raise UpdaterError(f"Lien ou type de fichier interdit : {membre.name!r}")
            if total > MAX_EXTRACTED_BYTES:
                raise UpdaterError("Contenu de l'archive trop volumineux.")
            plan.append((membre, _destination_sure(racine, membre.name), genre))
        for _, cible, genre in plan:
            if genre == "dir":
                cible.mkdir(parents=True, exist_ok=True)
        for membre, cible, genre in plan:
            if genre != "fichier":
                continue
            cible.parent.mkdir(parents=True, exist_ok=True)
            source = paquet.extractfile(membre)
            if source is None:
                raise UpdaterError(f"Fichier illisible dans l'archive : {membre.name!r}")
            with source, cible.open("xb") as sortie:
                shutil.copyfileobj(source, sortie)
            cible.chmod(0o755 if membre.mode & 0o111 else 0o644)


def _extraire(archive: Path, vers: Path) -> None:
    vers.mkdir(parents=True, exist_ok=False)
    if archive.name.lower().endswith(".zip"):
        _extraire_zip(archive, vers)
    elif archive.name.lower().endswith(".tar.gz"):
        _extraire_tar(archive, vers)
    else:
        raise UpdaterError(f"Format d'archive inconnu : {archive.name}")


def _trouver_executable(dossier: Path) -> Path:
    nom = "blink2temp.exe" if os.name == "nt" else "blink2temp"
    candidats = [chemin for chemin in dossier.rglob(nom) if chemin.is_file()]
    if len(candidats) != 1:
        raise UpdaterError("L'archive ne contient pas l'exécutable attendu.")
    return candidats[0]


def _verifier_executable(executable: Path, version: str) -> None:
    """Le nouvel exécutable démarre-t-il et annonce-t-il la bonne version ?

    Tant qu'il n'a pas répondu, rien n'est remplacé : une archive tronquée ou
    destinée à un autre système échoue ici, sur une installation intacte.
    """
    try:
        resultat = subprocess.run(
            [str(executable), "--version"],
            capture_output=True, text=True, timeout=180, check=False,
        )
    except (OSError, subprocess.SubprocessError) as err:
        raise UpdaterError(f"Le nouvel exécutable ne démarre pas ({err}).") from err
    attendu = f"blink2temp {version}"
    if resultat.returncode != 0 or (resultat.stdout or "").strip() != attendu:
        raise UpdaterError(
            f"Le nouvel exécutable annonce « {(resultat.stdout or '').strip() or '?'} », "
            f"on attendait « {attendu} »."
        )


# ------------------------------------------------------------------ processus

def _vivant(pid: int) -> bool:
    if pid <= 0:
        return False
    if os.name == "nt":
        import ctypes
        PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
        STILL_ACTIVE = 259
        poignee = ctypes.windll.kernel32.OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, False, pid)
        if not poignee:
            return False
        try:
            code = ctypes.c_ulong()
            if not ctypes.windll.kernel32.GetExitCodeProcess(poignee, ctypes.byref(code)):
                return False
            return code.value == STILL_ACTIVE
        finally:
            ctypes.windll.kernel32.CloseHandle(poignee)
    try:
        os.kill(pid, 0)
    except (OSError, ProcessLookupError):
        return False
    return True


def _attendre_arret(pid: int, delai_s: float = 180) -> None:
    limite = time.monotonic() + delai_s
    while time.monotonic() < limite:
        if not _vivant(pid):
            return
        time.sleep(0.5)
    raise UpdaterError("L'ancienne version ne s'est pas arrêtée à temps.")


def _lancer_detache(commande: list[str], dossier: Path, journal: Path) -> None:
    journal.parent.mkdir(parents=True, exist_ok=True)
    options: dict[str, Any] = {}
    if os.name == "nt":
        options["creationflags"] = 0x00000008 | 0x00000200  # DETACHED_PROCESS | CREATE_NEW_PROCESS_GROUP
    else:
        options["start_new_session"] = True
    with journal.open("ab") as sortie:
        subprocess.Popen(
            commande, cwd=str(dossier),
            stdin=subprocess.DEVNULL, stdout=sortie, stderr=subprocess.STDOUT,
            close_fds=True, **options,
        )


def finaliser(dossier: str, pid: str, arguments_json: str) -> int:
    """Second temps : exécuté par la nouvelle version depuis son dossier.

    Attend la fin du processus précédent, met le nouvel exécutable en place
    (ou rien du tout depuis les sources, où ``git pull`` a déjà tout écrit)
    puis relance l'application avec ses arguments d'origine.
    """
    installation = Path(dossier).resolve()
    try:
        arguments = json.loads(arguments_json) if arguments_json else []
    except json.JSONDecodeError:
        arguments = []
    if not isinstance(arguments, list):
        arguments = []
    arguments = [str(argument) for argument in arguments]

    journal = paths.dossier_donnees() / JOURNAL_MAJ
    try:
        _attendre_arret(int(pid))
        # Laisser le système refermer le port d'écoute et les fichiers ouverts.
        time.sleep(1.5)

        if paths.est_gele():
            nouveau = Path(sys.executable).resolve()
            cible = installation / nouveau.name
            if nouveau != cible:
                # Copie vers un nom temporaire puis remplacement atomique : une
                # coupure ne laisse jamais l'installation sans exécutable.
                temporaire = installation / (nouveau.name + ".nouveau")
                for essai in range(15):
                    try:
                        shutil.copy2(nouveau, temporaire)
                        if os.name != "nt":
                            temporaire.chmod(0o755)
                        os.replace(temporaire, cible)
                        break
                    except OSError:
                        temporaire.unlink(missing_ok=True)
                        if essai == 14:
                            # L'ancien binaire est intact : on le relance pour
                            # ne pas laisser l'application arrêtée.
                            _lancer_detache([str(cible), *arguments], installation, journal)
                            raise
                        time.sleep(2)
                if sys.platform == "darwin":
                    subprocess.run(
                        ["xattr", "-dr", "com.apple.quarantine", str(cible)],
                        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                        check=False,
                    )
            commande = [str(cible), *arguments]
        else:
            commande = [sys.executable, "-u", str(installation / "blink2temp.py"), *arguments]

        _lancer_detache(commande, installation, journal)
        return 0
    except (OSError, UpdaterError) as err:
        try:
            journal.parent.mkdir(parents=True, exist_ok=True)
            with journal.open("a", encoding="utf-8") as sortie:
                sortie.write(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] "
                             f"Échec de la finalisation : {err}\n")
        except OSError:
            pass
        return 1


def nettoyer_restes() -> None:
    """Efface les préparations des mises à jour précédentes.

    Le ménage ne peut pas se faire à la fin : sous Windows, un exécutable ne
    peut pas supprimer le dossier depuis lequel il tourne. On le fait donc au
    démarrage suivant, sauf si le processus courant tourne encore dedans.
    """
    racine = (paths.dossier_donnees() / "maj").resolve()
    courant = Path(sys.executable).resolve() if paths.est_gele() else Path(__file__).resolve()
    if courant == racine or racine in courant.parents:
        return
    shutil.rmtree(racine, ignore_errors=True)


# ------------------------------------------------------------------ état / threads

class _Gestionnaire:
    """État partagé entre le serveur web et le fil d'installation."""

    def __init__(self) -> None:
        self._verrou = threading.Lock()
        self._cache = _lire_cache()
        self._fil_verification: Optional[threading.Thread] = None
        self._fil_installation: Optional[threading.Thread] = None
        self.etape = "inactif"
        self.message = ""
        self.progression = 0.0
        self.erreur = ""

    # -- lecture

    def _disponible(self) -> Optional[dict]:
        version = str(self._cache.get("version") or "")
        if not version or numeros(version) <= numeros(version_locale()):
            return None
        archive = choisir_archive(self._cache.get("assets") or [], version)
        return {
            "version": version,
            "page": str(self._cache.get("page") or PAGE_RELEASES),
            "notes": str(self._cache.get("notes") or ""),
            "archive_pret": bool(archive.get("url")),
            "archive": archive,
        }

    def instantane(self) -> dict:
        with self._verrou:
            etape = self.etape
            message = self.message
            progression = self.progression
            erreur = self.erreur
            disponible = self._disponible()
            verifie = float(self._cache.get("verifie") or 0)
        return {
            "version_locale": version_locale(),
            "mode": "bundle" if paths.est_gele() else "sources",
            "disponible": disponible,
            "verifie_a": verifie,
            "etape": etape,
            "message": message,
            "progression": round(progression, 3),
            "erreur": erreur,
        }

    # -- vérification

    def verifier_async(self, force: bool = False) -> None:
        with self._verrou:
            if self._fil_verification and self._fil_verification.is_alive():
                return
            age = time.time() - float(self._cache.get("verifie") or 0)
            if not force and self._cache and 0 <= age < FRAICHEUR_S:
                return
            self.etape = "verification"
            self.message = "Recherche d'une nouvelle version…"
            self.erreur = ""
            self._fil_verification = threading.Thread(
                target=self._verifier, kwargs={"force": force},
                name="maj-verification", daemon=True,
            )
            self._fil_verification.start()

    def _verifier(self, force: bool) -> None:
        try:
            cache = verifier_release(force=force)
            with self._verrou:
                if cache:
                    self._cache = cache
                self.etape = "inactif"
                self.message = ""
        except Exception as err:  # la vérification ne doit jamais tuer le serveur
            with self._verrou:
                self.etape = "erreur"
                self.erreur = f"Vérification impossible : {err}"

    # -- installation

    def installer_async(self) -> None:
        with self._verrou:
            if self._fil_installation and self._fil_installation.is_alive():
                return
            disponible = self._disponible()
            if not disponible:
                raise UpdaterError("Aucune mise à jour n'est disponible.")
            if not disponible["archive_pret"]:
                raise UpdaterError(
                    "Cette release ne contient pas d'archive pour ce système. "
                    f"Téléchargez-la depuis {disponible['page']}"
                )
            self.etape = "telechargement"
            self.message = "Téléchargement de la mise à jour…"
            self.progression = 0.0
            self.erreur = ""
            self._fil_installation = threading.Thread(
                target=self._installer, name="maj-installation", daemon=True,
            )
            self._fil_installation.start()

    def _progression(self, fraction: float, message: str) -> None:
        with self._verrou:
            self.progression = max(0.0, min(1.0, fraction))
            self.message = message

    def _installer(self) -> None:
        try:
            with self._verrou:
                disponible = self._disponible()
            if not disponible:
                raise UpdaterError("Aucune mise à jour n'est disponible.")
            archive = disponible.get("archive") or {}
            if paths.est_gele():
                self._installer_bundle(disponible, archive)
            else:
                self._installer_sources(disponible)

            with self._verrou:
                self.etape = "redemarrage"
                self.message = "Redémarrage de Blink2Temp…"
                self.progression = 1.0
            time.sleep(1.5)
            import scheduler
            scheduler.demander_arret()
        except Exception as err:
            with self._verrou:
                self.etape = "erreur"
                self.erreur = str(err)
                self.message = ""

    def _installer_bundle(self, disponible: dict, archive: dict) -> None:
        version = disponible["version"]
        travail = paths.dossier_donnees() / "maj" / version
        shutil.rmtree(travail, ignore_errors=True)
        travail.mkdir(parents=True, exist_ok=True)

        nom = str(archive.get("nom") or "")
        if not NOM_ARCHIVE_RE.fullmatch(nom):
            raise UpdaterError("Nom d'archive de mise à jour invalide.")
        empreinte = _empreinte_attendue(archive)
        fichier = travail / nom
        self._progression(0.0, "Téléchargement de la mise à jour…")
        _telecharger(str(archive.get("url") or ""), fichier,
                     int(archive.get("taille") or 0), empreinte,
                     progression=self._progression)

        with self._verrou:
            self.etape = "extraction"
            self.message = "Vérification de l'archive…"
        contenu = travail / "contenu"
        _extraire(fichier, contenu)
        candidat = _trouver_executable(contenu)
        if os.name != "nt":
            candidat.chmod(0o755)
        if sys.platform == "darwin":
            subprocess.run(
                ["xattr", "-dr", "com.apple.quarantine", str(candidat)],
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=False,
            )
        with self._verrou:
            self.message = "Vérification du nouvel exécutable…"
        _verifier_executable(candidat, version)
        fichier.unlink(missing_ok=True)

        with self._verrou:
            self.etape = "installation"
            self.message = "Installation de la mise à jour…"
        installation = Path(sys.executable).resolve().parent
        _lancer_detache(
            [
                str(candidat),
                "--finaliser-maj", str(installation), str(os.getpid()),
                json.dumps(sys.argv[1:], ensure_ascii=False),
            ],
            dossier=candidat.parent,
            journal=paths.dossier_donnees() / JOURNAL_MAJ,
        )

    def _installer_sources(self, disponible: dict) -> None:
        dossier = Path(__file__).resolve().parent
        if not (dossier / ".git").exists():
            raise UpdaterError(
                "Cette copie n'est pas un dépôt git : téléchargez la nouvelle "
                f"version depuis {disponible.get('page') or PAGE_RELEASES}"
            )
        with self._verrou:
            self.etape = "installation"
            self.message = "Mise à jour des sources (git pull)…"
        resultat = subprocess.run(
            ["git", "pull", "--ff-only"], cwd=str(dossier),
            capture_output=True, text=True, timeout=180, check=False,
        )
        if resultat.returncode != 0:
            detail = (resultat.stderr or resultat.stdout or "").strip().splitlines()
            raise UpdaterError(
                "« git pull » a échoué"
                + (f" : {detail[-1]}" if detail else "")
                + ". Rien n'a été modifié."
            )
        obtenue = version_locale()
        if numeros(obtenue) < numeros(disponible["version"]):
            raise UpdaterError(
                f"Le dépôt annonce la version {obtenue or '?'} après le tirage, "
                f"on attendait {disponible['version']}. Relance refusée."
            )

        with self._verrou:
            self.etape = "installation"
            self.message = "Redémarrage avec la nouvelle version…"
        _lancer_detache(
            [
                sys.executable, "-u", str(dossier / "blink2temp.py"),
                "--finaliser-maj", str(dossier), str(os.getpid()),
                json.dumps(sys.argv[1:], ensure_ascii=False),
            ],
            dossier=dossier,
            journal=paths.dossier_donnees() / JOURNAL_MAJ,
        )


_gestionnaire = _Gestionnaire()


def etat() -> dict:
    """Instantané pour l'interface web (ne touche jamais le réseau)."""
    return _gestionnaire.instantane()


def verifier_async(force: bool = False) -> None:
    _gestionnaire.verifier_async(force=force)


def installer_async() -> None:
    _gestionnaire.installer_async()
