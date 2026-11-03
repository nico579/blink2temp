"""Chemins de données persistantes, en source comme dans un bundle PyInstaller.

En exécution depuis les sources, les fichiers restent à côté du projet (comme
auparavant). Dans un exécutable autonome, ils vont dans le dossier de données
de l'utilisateur : le dossier temporaire d'extraction n'est jamais durable.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

APP_NAME = "Blink2Temp"


def est_gele() -> bool:
    """Vrai lorsque l'application tourne depuis un exécutable PyInstaller."""
    return bool(getattr(sys, "frozen", False))


def dossier_donnees() -> Path:
    """Dossier inscriptible qui contient config.json, la base et les journaux."""
    if not est_gele():
        return Path(__file__).parent.resolve()

    if sys.platform == "win32":
        base = Path(os.environ.get("APPDATA") or Path.home() / "AppData" / "Roaming")
    elif sys.platform == "darwin":
        base = Path.home() / "Library" / "Application Support"
    else:
        base = Path(os.environ.get("XDG_DATA_HOME") or Path.home() / ".local" / "share")

    dossier = base / APP_NAME
    dossier.mkdir(parents=True, exist_ok=True)
    return dossier


def dossier_ressources() -> Path:
    """Dossier des ressources embarquées (lecture seule dans un bundle)."""
    if est_gele():
        return Path(getattr(sys, "_MEIPASS", Path(__file__).parent))
    return Path(__file__).parent.resolve()
