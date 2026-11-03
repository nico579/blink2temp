"""Planificateur et boucle périodique d'exécution pour blink2temp.

Exécute la relève des températures selon la fréquence configurée (défaut : 60 minutes),
aligne les relevés sur les fractions d'heure (ex: :00, :15, :30, :45), gère les arrêts
propres (Ctrl+C, signaux) et absorbe les coupures réseau transitoires.
"""

from __future__ import annotations

import datetime as dt
import logging
from pathlib import Path
import signal
import time
from typing import Any, Callable

import config
import paths

_ARRET_DEMANDE = False
LOG_PATH = paths.dossier_donnees() / "blink2temp.log"


def configurer_journal():
    """Initialise le fichier de journalisation blink2temp.log."""
    logging.basicConfig(
        filename=str(LOG_PATH),
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        encoding="utf-8",
    )


def journal(message: str, niveau: str = "info"):
    """Écrit une ligne horodatée dans blink2temp.log."""
    log_func = getattr(logging, niveau.lower(), logging.info)
    log_func(message)


def _intercepter_signaux():
    global _ARRET_DEMANDE

    def _gestionnaire(signum, frame):
        global _ARRET_DEMANDE
        _ARRET_DEMANDE = True
        print("\n[Arrêt] Signal de fermeture reçu, finalisation...")

    signal.signal(signal.SIGINT, _gestionnaire)
    signal.signal(signal.SIGTERM, _gestionnaire)


def arret_demande() -> bool:
    return _ARRET_DEMANDE


def calculer_attente_prochaine_heure(aligner_heure: bool = True, intervalle_minutes: int = 60) -> float:
    """Calcule le nombre de secondes jusqu'au prochain passage.

    Aligne intelligemment sur les fractions d'heure si aligner_heure=True :
    - 15 min : :00, :15, :30, :45
    - 30 min : :00, :30
    - 60 min : :00 (heure ronde)
    """
    intervalle_minutes = max(1, intervalle_minutes)
    if not aligner_heure:
        return float(intervalle_minutes * 60)

    maintenant = dt.datetime.now()
    if intervalle_minutes in (5, 10, 15, 20, 30):
        minute_suivante = ((maintenant.minute // intervalle_minutes) + 1) * intervalle_minutes
        if minute_suivante >= 60:
            prochaine = (maintenant + dt.timedelta(hours=1)).replace(minute=0, second=0, microsecond=0)
        else:
            prochaine = maintenant.replace(minute=minute_suivante, second=0, microsecond=0)
    elif intervalle_minutes >= 60 and intervalle_minutes % 60 == 0:
        nb_heures = intervalle_minutes // 60
        prochaine = (maintenant + dt.timedelta(hours=nb_heures)).replace(minute=0, second=0, microsecond=0)
    else:
        return float(intervalle_minutes * 60)

    secondes = (prochaine - maintenant).total_seconds()
    if secondes < 5:
        secondes += intervalle_minutes * 60
    return max(5.0, secondes)


def boucle_horaire(
    action: Callable[[], Any],
    intervalle_minutes: int = 60,
    aligner_heure: bool = True,
    executer_au_demarrage: bool = True,
) -> int:
    """Exécute `action` en boucle continue selon la fréquence définie."""
    configurer_journal()
    _intercepter_signaux()

    cfg = config.charger_config()
    cadence = intervalle_minutes or cfg.get("frequence_minutes", 60)

    journal(f"Démarrage de la boucle de relève (cadence: {cadence} min, aligné: {aligner_heure})")
    print(f"[*] Surveillance des températures démarrée (fréquence : tous les {cadence} min)")

    if executer_au_demarrage and not arret_demande():
        try:
            print(f"[{dt.datetime.now().strftime('%H:%M:%S')}] Exécution de la relève initiale...")
            action()
        except Exception as err:
            journal(f"Erreur lors de la relève initiale : {err}", "error")
            print(f"[!] Erreur lors de la relève initiale : {err}")

    while not arret_demande():
        # Relit la configuration à chaque cycle pour prise en compte à chaud
        cfg = config.charger_config()
        cadence_active = cfg.get("frequence_minutes", cadence)
        aligner_actif = cfg.get("aligner_heure", aligner_heure)

        secondes_attente = calculer_attente_prochaine_heure(aligner_actif, cadence_active)
        prochain_moment = dt.datetime.now() + dt.timedelta(seconds=secondes_attente)
        print(f"[*] Prochain relevé prévu à {prochain_moment.strftime('%H:%M:%S')} (dans {int(secondes_attente // 60)} min)")
        journal(f"Attente de {int(secondes_attente)}s jusqu'au prochain relevé à {prochain_moment.strftime('%H:%M:%S')}")

        echeance = time.monotonic() + secondes_attente
        while not arret_demande():
            reste = echeance - time.monotonic()
            if reste <= 0:
                break
            time.sleep(min(1.0, reste))

        if arret_demande():
            break

        try:
            print(f"\n[{dt.datetime.now().strftime('%H:%M:%S')}] Exécution de la relève...")
            journal("Début de la relève")
            action()
            journal("Relève terminée avec succès")
        except Exception as err:
            journal(f"Erreur durant le tour de relève : {err}", "error")
            print(f"[!] Erreur durant le tour de relève : {err} (on retente au prochain cycle)")

    journal("Arrêt propre de la boucle de relève")
    print("[*] Boucle de relève arrêtée proprement.")
    return 0
