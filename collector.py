"""Collecteur de températures Blink.

Interroge l'API Blink pour obtenir l'écran d'accueil sans réveiller physiquement
les caméras (ce qui préserve leurs piles), extrait les mesures de température
des caméras extérieures et les enregistre en base.
"""

from __future__ import annotations

import datetime as dt
from typing import Any

from blinkpy.blinkpy import Blink

import blink_auth
from storage import Storage

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


async def relever_temperatures(
    blink: Blink,
    storage: Storage | None = None,
    outdoor_only: bool = True,
    camera_cible: str | None = None,
    cameras_ciblees: list[str] | None = None,
) -> list[dict[str, Any]]:
    """Récupère l'état courant et les températures depuis l'écran d'accueil Blink.

    L'écran d'accueil est une interrogation passive des serveurs Blink :
    il fournit les données de télémétrie récentes sans solliciter les batteries
    des caméras physiques.
    """
    await blink.get_homescreen()
    home = getattr(blink, "homescreen", None) or {}

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

            releve = {
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
            }
            releves.append(releve)

    if storage is not None and releves:
        storage.enregistrer_releves(releves)

    return releves


async def relever_une_fois(
    storage: Storage | None = None,
    outdoor_only: bool = True,
    camera_cible: str | None = None,
    cameras_ciblees: list[str] | None = None,
    interactive: bool = True,
) -> list[dict[str, Any]]:
    """Exécute un relevé complet ponctuel en ouvrant une session temporaire."""
    store = storage or Storage()
    async with blink_auth.session_http_temporaire() as session:
        blink = await blink_auth.connect(session, interactive=interactive)
        if not blink:
            raise ConnectionError("Impossible de se connecter au compte Blink.")
        return await relever_temperatures(
            blink, store, outdoor_only=outdoor_only, camera_cible=camera_cible,
            cameras_ciblees=cameras_ciblees
        )
