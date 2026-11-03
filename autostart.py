"""Gestion du démarrage automatique et de la tâche planifiée Windows.

Permet de planifier la relève selon la fréquence voulue sans nécessiter de console ouverte,
via le Planificateur de tâches de Windows (schtasks).
"""

from __future__ import annotations

from pathlib import Path
import subprocess
import sys

import config

NOM_TACHE = "Blink2Temp_Releve_Horaire"
DOSSIER_COURANT = Path(__file__).parent.resolve()
SCRIPT_MAIN = DOSSIER_COURANT / "blink2temp.py"


def _trouver_pythonw() -> Path:
    """Trouve l'exécutable pythonw.exe pour une exécution silencieuse sans console noire."""
    interpreteur = Path(sys.executable)
    pythonw = interpreteur.with_name("pythonw.exe")
    if pythonw.exists():
        return pythonw
    return interpreteur


def installer_tache_planifiee(frequence_minutes: int | None = None) -> bool:
    """Installe une tâche planifiée Windows exécutant la relève selon la fréquence configurée."""
    cfg = config.charger_config()
    freq = frequence_minutes or cfg.get("frequence_minutes", 60)
    freq = max(1, int(freq))

    if getattr(sys, "frozen", False):
        commande = f'"{Path(sys.executable)}" --once'
    else:
        python_exe = _trouver_pythonw()
        commande = f'"{python_exe}" "{SCRIPT_MAIN}" --once'

    if freq < 60:
        schedule_type = "MINUTE"
        modifier = str(freq)
    else:
        schedule_type = "HOURLY"
        modifier = str(max(1, freq // 60))

    cmd = [
        "schtasks",
        "/Create",
        "/SC", schedule_type,
        "/MO", modifier,
        "/TN", NOM_TACHE,
        "/TR", commande,
        "/F",
    ]

    try:
        res = subprocess.run(cmd, capture_output=True, text=True, encoding="cp850")
        if res.returncode == 0:
            unite = f"{freq} minutes" if freq < 60 else f"{modifier} heure(s)"
            print(f"[OK] Tache planifiee Windows '{NOM_TACHE}' creee avec succes.")
            print(f"     La releve s'executera automatiquement toutes les {unite} en arriere-plan.")
            return True
        else:
            print(f"[!] Echec de creation de la tache planifiee : {res.stderr.strip()}")
            return False
    except Exception as err:
        print(f"[!] Erreur lors de l'appel a schtasks : {err}")
        return False


def desinstaller_tache_planifiee() -> bool:
    """Supprime la tâche planifiée Windows."""
    cmd = ["schtasks", "/Delete", "/TN", NOM_TACHE, "/F"]
    try:
        res = subprocess.run(cmd, capture_output=True, text=True, encoding="cp850")
        if res.returncode == 0:
            print(f"[OK] Tache planifiee Windows '{NOM_TACHE}' supprimee.")
            return True
        else:
            print(f"[i] La tache '{NOM_TACHE}' n'existe pas ou a deja ete supprimee.")
            return False
    except Exception as err:
        print(f"[!] Erreur : {err}")
        return False


def verifier_tache_planifiee() -> bool:
    """Vérifie si la tâche planifiée est actuellement active."""
    cmd = ["schtasks", "/Query", "/TN", NOM_TACHE]
    try:
        res = subprocess.run(cmd, capture_output=True, text=True, encoding="cp850")
        return res.returncode == 0
    except Exception:
        return False
