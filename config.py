"""Gestion de la configuration persistante pour blink2temp.

Conserve les réglages utilisateur (fréquence de relève, port, alignement horaire)
dans un fichier config.json éditable et modifiable à chaud via le Web ou la CLI.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import paths

DOSSIER_APP = paths.dossier_donnees()
CONFIG_FILE = DOSSIER_APP / "config.json"

DEFAUTS: dict[str, Any] = {
    "frequence_minutes": 60,
    "aligner_heure": True,
    "port_web": 8770,
    "outdoor_only": True,
    "visibilite_cameras": {},
    "reveiller_cameras": False,
    "dernier_reveil": 0,
}


def charger_config() -> dict[str, Any]:
    """Charge la configuration depuis config.json ou initialise les valeurs par défaut."""
    if not CONFIG_FILE.exists():
        sauvegarder_config(DEFAUTS)
        return dict(DEFAUTS)

    try:
        data = json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            return dict(DEFAUTS)
        # Compléter avec les valeurs par défaut pour les clés manquantes
        config = dict(DEFAUTS)
        config.update(data)
        # Validation de la fréquence (au moins 1 minute)
        try:
            freq = int(config.get("frequence_minutes", 60))
            config["frequence_minutes"] = max(1, freq)
        except (ValueError, TypeError):
            config["frequence_minutes"] = 60
        return config
    except (OSError, json.JSONDecodeError):
        return dict(DEFAUTS)


def sauvegarder_config(donnees: dict[str, Any]) -> dict[str, Any]:
    """Écrit la configuration mise à jour dans config.json de façon atomique."""
    config = dict(DEFAUTS)
    config.update(donnees)
    try:
        config["frequence_minutes"] = max(1, int(config["frequence_minutes"]))
    except (ValueError, TypeError):
        config["frequence_minutes"] = 60

    temp_file = CONFIG_FILE.with_name(f"config.tmp.{Path(__file__).stem}")
    try:
        temp_file.write_text(json.dumps(config, indent=2, ensure_ascii=False), encoding="utf-8")
        temp_file.replace(CONFIG_FILE)
    except OSError:
        pass
    finally:
        temp_file.unlink(missing_ok=True)

    return config


def modifier_config(**kwargs) -> dict[str, Any]:
    """Met à jour des clés spécifiques dans la configuration."""
    actuel = charger_config()
    actuel.update(kwargs)
    return sauvegarder_config(actuel)
