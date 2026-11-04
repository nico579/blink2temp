"""Collecteur de températures Blink.

Interroge l'API Blink pour obtenir l'écran d'accueil sans réveiller physiquement
les caméras (ce qui préserve leurs piles), extrait les mesures de température
des caméras extérieures et les enregistre en base.
"""

from __future__ import annotations

import datetime as dt
import logging
import time
from typing import Any

from blinkpy.blinkpy import Blink

import blink_auth
import config
from storage import Storage

_LOGGER = logging.getLogger(__name__)

# Deux températures distantes de moins de 0,05 °C sont considérées identiques :
# c'est le bruit d'arrondi de Blink, pas une évolution réelle.
TOLERANCE_REVEIL_C = 0.05

# Un réveil automatique consomme la pile : on l'espace d'au moins une heure.
DELAI_REVEIL_MINUTES = 60

CAMERA_MODELS: dict[str, str] = {
    "catalina": "Blink Outdoor",
    "catalina_clownfish": "Blink Outdoor Projecteur",
    "sedona": "Blink Outdoor 4",
    "canary": "Blink XT",
    "xt": "Blink XT",
    "xt2": "Blink XT2",
    "owl": "Blink Mini",
    "lotus": "Blink Video Doorbell",
    "sm": "Sync Module",
    "sm2": "Sync Module 2",
}

OUTDOOR_TYPES: set[str] = {
    "catalina",
    "catalina_clownfish",
    "sedona",
    "canary",
    "xt",
    "xt2",
}


def nom_modele(code_type: str | None) -> str:
    """Traduit le nom de code interne Amazon (ex: 'catalina') en nom de modèle commercial."""
    if not code_type:
        return "Blink Inconnu"
    return CAMERA_MODELS.get(code_type.lower(), f"Blink ({code_type})")


def est_camera_outdoor(item: dict[str, Any]) -> bool:
    """Détermine si un appareil Blink est une caméra extérieure.

    Vérifie le type matériel interne Amazon (ex: catalina, sedona, canary, xt2)
    ou la présence explicite du terme 'outdoor' dans le nom ou type.
    """
    code_type = str(item.get("type") or "").strip().lower()
    nom = str(item.get("name") or "").strip().lower()

    if code_type in OUTDOOR_TYPES:
        return True
    if "outdoor" in code_type or "outdoor" in nom:
        return True

    return False


def convertir_fahrenheit_en_celsius(temp_f: float | int | None) -> float | None:
    """Convertit les degrés Fahrenheit rapportés par Blink en degrés Celsius arrondis à 0.1°C."""
    if temp_f is None:
        return None
    try:
        return round((float(temp_f) - 32.0) * 5.0 / 9.0, 1)
    except (TypeError, ValueError):
        return None


def temperature_inchangee(
    actuelle: float | None,
    precedente: float | None,
    tolerance_c: float = TOLERANCE_REVEIL_C,
) -> bool:
    """Vrai si la température passive n'a pas évolué depuis la dernière mesure.

    C'est le seul cas où réveiller la caméra apporte une information nouvelle.
    Sans mesure précédente, on réveille pour établir une référence. Une caméra
    sans température n'est jamais réveillée.
    """
    if actuelle is None:
        return False
    if precedente is None:
        return True
    try:
        return abs(float(actuelle) - float(precedente)) <= tolerance_c
    except (TypeError, ValueError):
        return True


def _extraire_releves(
    home: dict[str, Any],
    outdoor_only: bool,
    camera_cible: str | None,
    cameras_ciblees: list[str] | None,
) -> list[dict[str, Any]]:
    """Transforme l'écran d'accueil Blink en lignes de relevé prêtes pour SQLite."""
    maintenant_utc = dt.datetime.now(dt.timezone.utc)
    maintenant_local = dt.datetime.now()
    recorded_at_str = maintenant_utc.isoformat()
    local_time_str = maintenant_local.strftime("%Y-%m-%d %H:%M:%S")

    groupes = ["cameras"]
    if not outdoor_only:
        groupes.extend(["owls", "doorbells"])

    releves: list[dict[str, Any]] = []

    # Filtre volontaire : liste exacte de noms de caméras (casse ignorée, vide = rien)
    noms_autorises = (
        {str(n).strip().lower() for n in cameras_ciblees if str(n).strip()}
        if cameras_ciblees is not None
        else None
    )

    for groupe in groupes:
        appareils = home.get(groupe) or []
        for app in appareils:
            nom = str(app.get("name") or "Caméra").strip()
            if camera_cible and camera_cible.strip().lower() not in nom.lower():
                continue
            if noms_autorises is not None and nom.lower() not in noms_autorises:
                continue

            is_outdoor = est_camera_outdoor(app)
            if outdoor_only and not is_outdoor:
                continue

            signals = app.get("signals") or {}
            raw_temp = signals.get("temp")
            temp_c = convertir_fahrenheit_en_celsius(raw_temp)
            temp_f = float(raw_temp) if raw_temp is not None else None

            cam_id = str(app.get("id") or app.get("device_id") or app.get("camera_id") or "")
            code_type = str(app.get("type") or "")
            modele = nom_modele(code_type)

            releves.append({
                "recorded_at": recorded_at_str,
                "local_time": local_time_str,
                "camera_name": nom,
                "camera_id": cam_id,
                "camera_type": code_type,
                "model": modele,
                "is_outdoor": 1 if is_outdoor else 0,
                "temp_c": temp_c,
                "temp_f": temp_f,
                "battery": str(app.get("battery") or ""),
                "battery_level": signals.get("battery"),
                "wifi_strength": signals.get("wifi"),
                "lfr_signal": signals.get("lfr"),
                "status": str(app.get("status") or ""),
                "blink_updated_at": app.get("updated_at"),
            })

    return releves


async def reveiller_cameras_immobiles(
    blink: Blink,
    releves: list[dict[str, Any]],
    precedentes: dict[str, float | None],
) -> list[str]:
    """Réveille uniquement les caméras dont la température passive n'a pas bougé.

    La commande « photo » force la caméra à renvoyer ses signaux à jour. Elle
    consomme de la pile et peut prendre jusqu'à une minute par caméra : elle
    n'est utilisée que si l'utilisateur l'a demandé.
    """
    cameras = getattr(blink, "cameras", None)
    if not hasattr(cameras, "get"):
        return []

    reveillees: list[str] = []
    for releve in releves:
        nom = releve["camera_name"]
        if not temperature_inchangee(releve.get("temp_c"), precedentes.get(nom)):
            continue
        camera = cameras.get(nom)
        if camera is None:
            _LOGGER.warning("Réveil ignoré : caméra %s introuvable côté blinkpy", nom)
            continue
        try:
            await camera.snap_picture()
        except Exception as err:  # noqa: BLE001 - une caméra ne doit pas bloquer les autres
            _LOGGER.warning("Réveil impossible pour %s : %s", nom, err)
            continue
        reveillees.append(nom)

    return reveillees


async def relever_temperatures(
    blink: Blink,
    storage: Storage | None = None,
    outdoor_only: bool = True,
    camera_cible: str | None = None,
    cameras_ciblees: list[str] | None = None,
    reveiller: bool = False,
    reveils_effectues: list[str] | None = None,
) -> list[dict[str, Any]]:
    """Récupère l'état courant et les températures depuis l'écran d'accueil Blink.

    L'écran d'accueil est une interrogation passive des serveurs Blink :
    il fournit les données de télémétrie récentes sans solliciter les batteries
    des caméras physiques.

    Si ``reveiller`` est vrai, les caméras dont la température n'a pas évolué
    depuis la dernière mesure en base reçoivent une commande photo, puis
    l'écran d'accueil est relu pour récupérer les températures fraîches.
    """
    await blink.get_homescreen()
    home = getattr(blink, "homescreen", None) or {}
    releves = _extraire_releves(home, outdoor_only, camera_cible, cameras_ciblees)

    if reveiller and storage is not None and releves:
        precedentes = {
            str(row["camera_name"]): row.get("temp_c")
            for row in storage.obtenir_dernieres_temperatures(outdoor_only=outdoor_only)
        }
        reveillees = await reveiller_cameras_immobiles(blink, releves, precedentes)
        if reveillees:
            await blink.get_homescreen()
            home = getattr(blink, "homescreen", None) or {}
            releves = _extraire_releves(home, outdoor_only, camera_cible, cameras_ciblees)
            if reveils_effectues is not None:
                reveils_effectues.extend(reveillees)

    if storage is not None and releves:
        storage.enregistrer_releves(releves)

    return releves


def reveil_autorise(dernier_reveil: float | int | None, maintenant: float | None = None) -> bool:
    """Respecte le délai minimal entre deux réveils automatiques."""
    if not dernier_reveil:
        return True
    instant = time.time() if maintenant is None else maintenant
    return instant - float(dernier_reveil) >= DELAI_REVEIL_MINUTES * 60


async def relever_une_fois(
    storage: Storage | None = None,
    outdoor_only: bool = True,
    camera_cible: str | None = None,
    cameras_ciblees: list[str] | None = None,
    interactive: bool = True,
    reveiller: bool = False,
    forcer_reveil: bool = False,
    reveils_effectues: list[str] | None = None,
) -> list[dict[str, Any]]:
    """Exécute un relevé complet ponctuel en ouvrant une session temporaire.

    ``forcer_reveil`` ignore le délai d'une heure : utilisé par le bouton
    manuel « Relever maintenant », pas par la relève planifiée.
    """
    store = storage or Storage()
    rever = reveiller
    if rever and not forcer_reveil:
        cfg = config.charger_config()
        rever = reveil_autorise(cfg.get("dernier_reveil"))

    reveils: list[str] = []
    async with blink_auth.session_http_temporaire() as session:
        blink = await blink_auth.connect(session, interactive=interactive)
        if not blink:
            raise ConnectionError("Impossible de se connecter au compte Blink.")
        releves = await relever_temperatures(
            blink, store, outdoor_only=outdoor_only, camera_cible=camera_cible,
            cameras_ciblees=cameras_ciblees, reveiller=rever,
            reveils_effectues=reveils,
        )
    if reveils_effectues is not None:
        reveils_effectues.extend(reveils)
    if reveils:
        config.modifier_config(dernier_reveil=time.time())
    return releves
