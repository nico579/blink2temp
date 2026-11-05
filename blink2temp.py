"""Point d'entrée principal de l'application Blink2Temp.

Relève les températures des caméras extérieures Blink toutes les heures,
conserve l'historique dans une base SQLite et propose un tableau de bord web.
"""

from __future__ import annotations

import argparse
import asyncio
import datetime as dt
from pathlib import Path
import sys

# Permet l'exécution directe depuis n'importe quel répertoire courant
DOSSIER_APP = Path(__file__).parent.resolve()
if str(DOSSIER_APP) not in sys.path:
    sys.path.insert(0, str(DOSSIER_APP))

# Configuration de l'encodage de la console sous Windows
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

import autostart  # noqa: E402
import collector  # noqa: E402
import config  # noqa: E402
import scheduler  # noqa: E402
from storage import Storage  # noqa: E402
import updater  # noqa: E402
import web  # noqa: E402


def afficher_banniere():
    print("""
================================================================
  Blink2Temp - Releve Horaire des Cameras Outdoor Blink
=================================================================""")


def afficher_tableau_releves(releves: list[dict]):
    if not releves:
        print("\n[i] Aucune camera exterieure trouvee ou relevee.")
        return

    print("\n{:<15} {:<20} {:<16} {:<12} {:<10}".format(
        "Camera", "Modele", "Temperature", "Statut", "Batterie"
    ))
    print("-" * 75)
    for r in sorted(releves, key=lambda x: x["camera_name"]):
        nom = r["camera_name"]
        mod = r["model"] or "Outdoor"
        if r["temp_c"] is not None:
            temp_str = f"{r['temp_c']:>4.1f} °C ({int(r['temp_f'])}°F)"
        else:
            temp_str = "    -- °C"
        statut = "En ligne" if r["status"] != "offline" else "Hors ligne"
        bat = r["battery"] or "ok"
        print("{:<15} {:<20} {:<16} {:<12} {:<10}".format(
            nom, mod, temp_str, statut, bat
        ))
    print("-" * 75)


def afficher_stats(storage: Storage, heures: int = 24):
    stats = storage.obtenir_statistiques(heures=heures, outdoor_only=True)
    if not stats:
        print(f"\n[i] Aucune statistique disponible pour les dernières {heures}h.")
        return

    print(f"\nStatistiques de temperature sur les dernieres {heures} heures :")
    print("{:<15} {:<20} {:<10} {:<10} {:<10} {:<8}".format(
        "Camera", "Modele", "Min (°C)", "Moy (°C)", "Max (°C)", "Mesures"
    ))
    print("-" * 75)
    for s in stats:
        min_t = f"{s['min_temp_c']}°C" if s['min_temp_c'] is not None else "--"
        avg_t = f"{s['avg_temp_c']}°C" if s['avg_temp_c'] is not None else "--"
        max_t = f"{s['max_temp_c']}°C" if s['max_temp_c'] is not None else "--"
        print("{:<15} {:<20} {:<10} {:<10} {:<10} {:<8}".format(
            s["camera_name"], s["model"] or "Outdoor", min_t, avg_t, max_t, s["count"]
        ))
    print("-" * 75)


def afficher_historique(storage: Storage, heures: int = 24):
    hist = storage.obtenir_historique(heures=heures, outdoor_only=True)
    if not hist:
        print(f"\n[i] Aucun historique disponible pour les dernieres {heures}h.")
        return

    print(f"\nHistorique des releves ({len(hist)} mesures sur les dernieres {heures}h) :")
    print("{:<20} {:<15} {:<15} {:<10}".format("Horodatage", "Camera", "Temperature", "Statut"))
    print("-" * 65)
    for h in hist[-30:]:  # Afficher les 30 derniers
        t_str = f"{h['temp_c']} °C" if h['temp_c'] is not None else "--"
        print("{:<20} {:<15} {:<15} {:<10}".format(
            h["local_time"], h["camera_name"], t_str, h["status"]
        ))
    print("-" * 65)


def executer_releve(
    storage: Storage,
    outdoor_only: bool = True,
    camera_cible: str | None = None,
    reveiller: bool = False,
    forcer_reveil: bool = False,
) -> list[dict]:
    """Exécute un relevé complet et le sauvegarde en base."""
    reveils: list[str] = []
    releves = asyncio.run(collector.relever_une_fois(
        storage=storage, outdoor_only=outdoor_only, camera_cible=camera_cible,
        interactive=False, reveiller=reveiller, forcer_reveil=forcer_reveil,
        reveils_effectues=reveils,
    ))
    if reveils:
        print(f"[i] Caméra(s) réveillée(s) car température inchangée : {', '.join(reveils)}")
    return releves


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="blink2temp",
        description="Surveillance et relève horaire des températures des caméras extérieures Blink.",
    )
    parser.add_argument(
        "--once", action="store_true",
        help="Effectue un seul relevé immédiatement puis quitte (idéal pour tâche planifiée).",
    )
    parser.add_argument(
        "--loop", type=int, nargs="?", const=60, default=None, metavar="MINUTES",
        help="Exécute la relève en boucle (défaut : fréquence configurée dans config.json).",
    )
    parser.add_argument(
        "--frequence", "-f", "--interval", type=int, default=None, metavar="MINUTES",
        help="Définit la fréquence de relève en minutes pour cette session (ex: -f 30).",
    )
    parser.add_argument(
        "--set-frequence", type=int, default=None, metavar="MINUTES",
        help="Enregistre la fréquence de relève par défaut dans config.json et quitte.",
    )
    parser.add_argument(
        "--reset-db", action="store_true",
        help="Réinitialise la base de données SQLite (efface tous les relevés enregistrés).",
    )
    parser.add_argument(
        "--web", "--serve", dest="serve_web", action="store_true",
        help="Lance le serveur web du tableau de bord (par défaut sur http://localhost:8770).",
    )
    parser.add_argument(
        "--port", type=int, default=8770,
        help="Port d'écoute du serveur web (défaut : 8770).",
    )
    parser.add_argument(
        "--no-align", action="store_true",
        help="Désactive l'alignement sur l'heure ronde (ex: 10:00, 11:00).",
    )
    parser.add_argument(
        "--all", dest="outdoor_only", action="store_false", default=True,
        help="Relever toutes les caméras, pas seulement les caméras extérieures (outdoor).",
    )
    parser.add_argument(
        "--camera", metavar="NOM", default=None,
        help="Cible uniquement une caméra spécifique (ex: --camera jardin).",
    )
    parser.add_argument(
        "--reveiller", action="store_true",
        help="Réveille les caméras dont la température n'a pas changé (consomme la pile).",
    )
    parser.add_argument(
        "--force-reveil", action="store_true",
        help="Avec --reveiller, ignore le délai d'une heure entre deux réveils (relevé manuel).",
    )
    parser.add_argument(
        "--stats", action="store_true",
        help="Affiche les statistiques (min/max/moyenne) des dernières 24h et quitte.",
    )
    parser.add_argument(
        "--history", type=int, nargs="?", const=24, default=None, metavar="HEURES",
        help="Affiche l'historique des relevés récents et quitte.",
    )
    parser.add_argument(
        "--export", metavar="FICHIER.csv",
        help="Exporte tous les relevés dans un fichier CSV.",
    )
    parser.add_argument(
        "--install-task", action="store_true",
        help="Installe la tâche planifiée Windows pour exécuter la relève chaque heure en arrière-plan.",
    )
    parser.add_argument(
        "--uninstall-task", action="store_true",
        help="Supprime la tâche planifiée Windows.",
    )
    parser.add_argument(
        "--task-status", action="store_true",
        help="Vérifie si la tâche planifiée Windows est installée.",
    )
    parser.add_argument(
        "--version", action="store_true",
        help="Affiche la version de Blink2Temp et quitte.",
    )
    parser.add_argument(
        "--finaliser-maj", nargs=3, metavar=("DOSSIER", "PID", "ARGUMENTS"),
        help=argparse.SUPPRESS,  # usage interne de la mise à jour
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()

    # Réponses immédiates, sans bannière ni accès à la base de données :
    # --version est utilisé pour vérifier un exécutable de mise à jour, et
    # --finaliser-maj est la seconde moitié de l'installation.
    if args.version:
        print(f"blink2temp {updater.version_locale()}")
        return 0
    if args.finaliser_maj:
        return updater.finaliser(*args.finaliser_maj)

    updater.nettoyer_restes()
    afficher_banniere()
    storage = Storage()
    cfg = config.charger_config()

    if args.reset_db:
        nb = storage.reinitialiser_base()
        print(f"[OK] Base de données réinitialisée ({nb} relevés supprimés).")
        return 0

    if args.set_frequence is not None:
        maj = config.modifier_config(frequence_minutes=args.set_frequence)
        print(f"[OK] Fréquence de relève enregistrée : tous les {maj['frequence_minutes']} minutes dans config.json.")
        return 0

    cadence = args.frequence or args.loop or cfg.get("frequence_minutes", 60)
    reveiller = args.reveiller or bool(cfg.get("reveiller_cameras", False))
    if reveiller:
        print("[i] Réveil activé : seules les caméras dont la température n'a pas changé seront sollicitées "
              "(pile, jusqu'à 1 minute par caméra, au plus une fois par heure).")

    if args.install_task:
        return 0 if autostart.installer_tache_planifiee(cadence) else 1

    if args.uninstall_task:
        return 0 if autostart.desinstaller_tache_planifiee() else 1

    if args.task_status:
        active = autostart.verifier_tache_planifiee()
        if active:
            print(f"[✓] La tâche planifiée '{autostart.NOM_TACHE}' est active.")
        else:
            print(f"[i] La tâche planifiée '{autostart.NOM_TACHE}' n'est pas installée.")
        return 0

    if args.export:
        total = storage.exporter_csv(args.export)
        print(f"[✓] {total} enregistrements exportés vers '{args.export}'.")
        return 0

    if args.stats:
        afficher_stats(storage, heures=24)
        return 0

    if args.history is not None:
        afficher_historique(storage, heures=args.history)
        return 0

    # Si le serveur web est demandé
    if args.serve_web:
        print(f"[*] Démarrage du tableau de bord web sur http://localhost:{args.port}")
        web.demarrer_serveur_web(storage, port=args.port, daemon=True)

    # Mode 1 : Un seul passage demandé (--once)
    if args.once:
        cible_desc = f" ({args.camera})" if args.camera else ""
        print(f"[{dt.datetime.now().strftime('%H:%M:%S')}] Relève des caméras extérieures{cible_desc} en cours...")
        try:
            releves = executer_releve(
                storage, outdoor_only=args.outdoor_only, camera_cible=args.camera,
                reveiller=reveiller, forcer_reveil=args.force_reveil,
            )
            afficher_tableau_releves(releves)
            print(f"[✓] Relevé terminé : {len(releves)} caméra(s) enregistrée(s).")
            return 0
        except Exception as err:
            print(f"[!] Échec du relevé : {err}", file=sys.stderr)
            return 1

    # Mode 2 : Boucle de relève périodique
    aligner = not args.no_align

    def action_tour():
        releves = executer_releve(
            storage, outdoor_only=args.outdoor_only, camera_cible=args.camera,
            reveiller=reveiller,
        )
        afficher_tableau_releves(releves)
        print(f"[{dt.datetime.now().strftime('%H:%M:%S')}] {len(releves)} caméra(s) enregistrée(s) en base.")

    return scheduler.boucle_horaire(
        action=action_tour,
        intervalle_minutes=cadence,
        aligner_heure=aligner,
        executer_au_demarrage=True,
    )


if __name__ == "__main__":
    sys.exit(main())
