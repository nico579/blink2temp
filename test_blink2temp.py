"""Tests unitaires pour l'application blink2temp."""

import csv
import datetime as dt
from pathlib import Path
import tempfile
import unittest
from unittest.mock import AsyncMock, MagicMock

import collector
import scheduler
from storage import Storage
import updater
import web


class TestTemperatureConversion(unittest.TestCase):
    def test_conversions_fahrenheit_en_celsius(self):
        self.assertEqual(collector.convertir_fahrenheit_en_celsius(32), 0.0)
        self.assertEqual(collector.convertir_fahrenheit_en_celsius(55), 12.8)
        self.assertEqual(collector.convertir_fahrenheit_en_celsius(73), 22.8)
        self.assertEqual(collector.convertir_fahrenheit_en_celsius(68), 20.0)

    def test_valeurs_nulles_ou_invalides(self):
        self.assertIsNone(collector.convertir_fahrenheit_en_celsius(None))
        self.assertIsNone(collector.convertir_fahrenheit_en_celsius("invalide"))


class TestOutdoorCameraDetection(unittest.TestCase):
    def test_types_materiel_outdoor(self):
        self.assertTrue(collector.est_camera_outdoor({"type": "catalina", "name": "Jardin"}))
        self.assertTrue(collector.est_camera_outdoor({"type": "sedona", "name": "Entrée"}))
        self.assertTrue(collector.est_camera_outdoor({"type": "xt2", "name": "Garage"}))
        self.assertTrue(collector.est_camera_outdoor({"type": "canary", "name": "Allée"}))

    def test_cameras_interieures_non_outdoor(self):
        self.assertFalse(collector.est_camera_outdoor({"type": "owl", "name": "Salon"}))
        self.assertFalse(collector.est_camera_outdoor({"type": "mini", "name": "Cuisine"}))

    def test_nom_avec_outdoor_meme_si_type_inconnu(self):
        self.assertTrue(collector.est_camera_outdoor({"type": "custom", "name": "Caméra Outdoor Sud"}))

    def test_nom_modele_commercial(self):
        self.assertEqual(collector.nom_modele("catalina"), "Blink Outdoor")
        self.assertEqual(collector.nom_modele("sedona"), "Blink Outdoor 4")
        self.assertEqual(collector.nom_modele("owl"), "Blink Mini")
        self.assertEqual(collector.nom_modele("lotus"), "Blink Video Doorbell")


class TestStorage(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.temp_dir.name) / "test_temp.db"
        self.storage = Storage(self.db_path)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_insertion_et_derniers_releves(self):
        maintenant = dt.datetime.now(dt.timezone.utc).isoformat()
        releves = [
            {
                "recorded_at": maintenant,
                "local_time": "2026-11-03 10:00:00",
                "camera_name": "Jardin",
                "camera_id": "111",
                "camera_type": "catalina",
                "model": "Blink Outdoor",
                "is_outdoor": 1,
                "temp_c": 12.5,
                "temp_f": 54.5,
                "battery": "ok",
                "battery_level": 3,
                "wifi_strength": 4,
                "lfr_signal": 1,
                "status": "done",
                "blink_updated_at": maintenant,
            },
            {
                "recorded_at": maintenant,
                "local_time": "2026-11-03 10:00:00",
                "camera_name": "Portail",
                "camera_id": "222",
                "camera_type": "catalina",
                "model": "Blink Outdoor",
                "is_outdoor": 1,
                "temp_c": 15.0,
                "temp_f": 59.0,
                "battery": "low",
                "battery_level": 2,
                "wifi_strength": 3,
                "lfr_signal": 1,
                "status": "done",
                "blink_updated_at": maintenant,
            },
        ]
        nb = self.storage.enregistrer_releves(releves)
        self.assertEqual(nb, 2)

        derniers = self.storage.obtenir_dernieres_temperatures(outdoor_only=True)
        self.assertEqual(len(derniers), 2)
        noms = [d["camera_name"] for d in derniers]
        self.assertIn("Jardin", noms)
        self.assertIn("Portail", noms)

    def test_statistiques(self):
        base_time = dt.datetime.now(dt.timezone.utc)
        releves = [
            {
                "recorded_at": (base_time - dt.timedelta(minutes=10)).isoformat(),
                "local_time": "2026-11-03 10:00:00",
                "camera_name": "Jardin",
                "camera_id": "111",
                "camera_type": "catalina",
                "model": "Blink Outdoor",
                "is_outdoor": 1,
                "temp_c": 10.0,
                "temp_f": 50.0,
                "battery": "ok",
                "battery_level": 3,
                "wifi_strength": 4,
                "lfr_signal": 1,
                "status": "done",
                "blink_updated_at": base_time.isoformat(),
            },
            {
                "recorded_at": base_time.isoformat(),
                "local_time": "2026-11-03 10:10:00",
                "camera_name": "Jardin",
                "camera_id": "111",
                "camera_type": "catalina",
                "model": "Blink Outdoor",
                "is_outdoor": 1,
                "temp_c": 20.0,
                "temp_f": 68.0,
                "battery": "ok",
                "battery_level": 3,
                "wifi_strength": 4,
                "lfr_signal": 1,
                "status": "done",
                "blink_updated_at": base_time.isoformat(),
            },
        ]
        self.storage.enregistrer_releves(releves)
        stats = self.storage.obtenir_statistiques(heures=24)
        self.assertEqual(len(stats), 1)
        jardin_stat = stats[0]
        self.assertEqual(jardin_stat["camera_name"], "Jardin")
        self.assertEqual(jardin_stat["min_temp_c"], 10.0)
        self.assertEqual(jardin_stat["max_temp_c"], 20.0)
        self.assertEqual(jardin_stat["avg_temp_c"], 15.0)
        self.assertEqual(jardin_stat["count"], 2)

    def test_historique_avec_bornes_dates(self):
        t1 = "2026-11-01T10:00:00+00:00"
        t2 = "2026-11-02T10:00:00+00:00"
        t3 = "2026-11-03T10:00:00+00:00"
        self.storage.enregistrer_releves([
            {"recorded_at": t1, "local_time": "2026-11-01 10:00:00", "camera_name": "Jardin", "is_outdoor": 1, "temp_c": 11.0},
            {"recorded_at": t2, "local_time": "2026-11-02 10:00:00", "camera_name": "Jardin", "is_outdoor": 1, "temp_c": 12.0},
            {"recorded_at": t3, "local_time": "2026-11-03 10:00:00", "camera_name": "Jardin", "is_outdoor": 1, "temp_c": 13.0},
        ])
        # Filtre sur le 2 novembre seulement
        res = self.storage.obtenir_historique(debut="2026-11-02T00:00:00", fin="2026-11-02T23:59:59")
        self.assertEqual(len(res), 1)
        self.assertEqual(res[0]["temp_c"], 12.0)

    def test_export_csv(self):
        now_str = dt.datetime.now(dt.timezone.utc).isoformat()
        self.storage.enregistrer_releves([{
            "recorded_at": now_str,
            "local_time": "2026-11-03 10:00:00",
            "camera_name": "Terrasse",
            "camera_id": "333",
            "camera_type": "catalina",
            "model": "Blink Outdoor",
            "is_outdoor": 1,
            "temp_c": 18.2,
            "temp_f": 64.7,
            "battery": "ok",
            "battery_level": 3,
            "wifi_strength": 5,
            "lfr_signal": 1,
            "status": "done",
            "blink_updated_at": now_str,
        }])
        csv_file = Path(self.temp_dir.name) / "export.csv"
        total = self.storage.exporter_csv(csv_file)
        self.assertEqual(total, 1)
        self.assertTrue(csv_file.exists())

        with open(csv_file, "r", encoding="utf-8-sig") as f:
            reader = csv.reader(f, delimiter=";")
            rows = list(reader)
            self.assertEqual(len(rows), 2)  # Entête + 1 ligne
            self.assertIn("camera_name", rows[0])
            self.assertEqual(rows[1][rows[0].index("camera_name")], "Terrasse")


class TestCollector(unittest.IsolatedAsyncioTestCase):
    async def test_releve_avec_cameras_homescreen_mock(self):
        mock_blink = MagicMock()
        mock_blink.get_homescreen = AsyncMock()
        mock_blink.homescreen = {
            "cameras": [
                {
                    "name": "Jardin",
                    "id": 101,
                    "type": "catalina",
                    "status": "done",
                    "battery": "ok",
                    "signals": {"temp": 50, "battery": 3, "wifi": 4, "lfr": 1},
                    "updated_at": "2026-11-03T09:00:00+00:00",
                },
                {
                    "name": "Cour",
                    "id": 102,
                    "type": "owl",  # Mini d'intérieur -> ignoré par défaut
                    "status": "done",
                    "battery": "ok",
                    "signals": {"temp": None},
                },
            ],
            "owls": [],
            "doorbells": [],
        }

        with tempfile.TemporaryDirectory() as tmp:
            store = Storage(Path(tmp) / "mock.db")
            releves = await collector.relever_temperatures(mock_blink, storage=store, outdoor_only=True)
            self.assertEqual(len(releves), 1)
            self.assertEqual(releves[0]["camera_name"], "Jardin")
            self.assertEqual(releves[0]["temp_c"], 10.0)  # 50°F = 10°C
            self.assertEqual(releves[0]["model"], "Blink Outdoor")

    async def test_releve_avec_filtre_camera_cible(self):
        mock_blink = MagicMock()
        mock_blink.get_homescreen = AsyncMock()
        mock_blink.homescreen = {
            "cameras": [
                {"name": "Jardin", "id": 101, "type": "catalina", "signals": {"temp": 50}},
                {"name": "Portail", "id": 102, "type": "catalina", "signals": {"temp": 60}},
            ]
        }
        with tempfile.TemporaryDirectory() as tmp:
            store = Storage(Path(tmp) / "mock.db")
            releves = await collector.relever_temperatures(mock_blink, storage=store, camera_cible="jardin")
            self.assertEqual(len(releves), 1)
            self.assertEqual(releves[0]["camera_name"], "Jardin")

    async def test_releve_avec_liste_cameras_ciblees(self):
        mock_blink = MagicMock()
        mock_blink.get_homescreen = AsyncMock()
        mock_blink.homescreen = {
            "cameras": [
                {"name": "Jardin", "id": 101, "type": "catalina", "signals": {"temp": 50}},
                {"name": "Portail", "id": 102, "type": "catalina", "signals": {"temp": 60}},
                {"name": "Terrasse", "id": 103, "type": "catalina", "signals": {"temp": 70}},
            ]
        }
        with tempfile.TemporaryDirectory() as tmp:
            store = Storage(Path(tmp) / "mock.db")
            # Casse ignorée, un sous-ensemble seulement
            releves = await collector.relever_temperatures(
                mock_blink, storage=store, cameras_ciblees=["PORTAIL", "jardin"]
            )
            noms = {r["camera_name"] for r in releves}
            self.assertEqual(noms, {"Jardin", "Portail"})

            # Liste vide explicite -> aucun relevé
            releves_vides = await collector.relever_temperatures(
                mock_blink, storage=store, cameras_ciblees=[]
            )
            self.assertEqual(releves_vides, [])

            # Liste absente -> toutes les caméras outdoor (comportement historique)
            releves_tous = await collector.relever_temperatures(mock_blink, storage=store)
            self.assertEqual(len(releves_tous), 3)


class TestReveilCameras(unittest.IsolatedAsyncioTestCase):
    def test_temperature_inchangee(self):
        self.assertTrue(collector.temperature_inchangee(12.3, 12.3))
        self.assertTrue(collector.temperature_inchangee(12.3, 12.32))
        self.assertFalse(collector.temperature_inchangee(12.3, 12.9))
        # Première mesure : on établit une référence.
        self.assertTrue(collector.temperature_inchangee(12.3, None))
        # Une caméra sans température n'est jamais réveillée.
        self.assertFalse(collector.temperature_inchangee(None, 12.3))
        self.assertFalse(collector.temperature_inchangee(None, None))

    def test_delai_entre_reveils(self):
        maintenant = 10_000_000.0
        heure = 60 * 60
        self.assertTrue(collector.reveil_autorise(None, maintenant))
        self.assertTrue(collector.reveil_autorise(0, maintenant))
        self.assertFalse(collector.reveil_autorise(maintenant - 30 * 60, maintenant))
        self.assertTrue(collector.reveil_autorise(maintenant - heure, maintenant))

    async def test_reveil_seulement_des_temperatures_inchangees(self):
        class FausseCamera:
            def __init__(self):
                self.reveillee = False

            async def snap_picture(self):
                self.reveillee = True
                return {"id": 1, "network_id": 9001}

        class FauxBlink:
            def __init__(self, ecrans, cameras):
                self._ecrans = ecrans
                self.homescreen = ecrans[0]
                self.cameras = cameras
                self.appels = 0

            async def get_homescreen(self):
                self.homescreen = self._ecrans[min(self.appels, len(self._ecrans) - 1)]
                self.appels += 1

        jardin = FausseCamera()
        portail = FausseCamera()
        avant = {
            "cameras": [
                {"name": "Jardin", "id": 101, "type": "catalina", "signals": {"temp": 50}},
                {"name": "Portail", "id": 102, "type": "catalina", "signals": {"temp": 60}},
            ]
        }
        apres = {
            "cameras": [
                {"name": "Jardin", "id": 101, "type": "catalina", "signals": {"temp": 53.6}},
                {"name": "Portail", "id": 102, "type": "catalina", "signals": {"temp": 60}},
            ]
        }
        blink = FauxBlink([avant, apres], {"Jardin": jardin, "Portail": portail})

        with tempfile.TemporaryDirectory() as tmp:
            store = Storage(Path(tmp) / "reveil.db")
            ancien = dt.datetime.now(dt.timezone.utc) - dt.timedelta(hours=1)
            store.enregistrer_releves([
                {
                    "recorded_at": ancien.isoformat(), "local_time": "2026-11-03 09:00:00",
                    "camera_name": "Jardin", "is_outdoor": 1, "temp_c": 10.0,
                },
                {
                    "recorded_at": ancien.isoformat(), "local_time": "2026-11-03 09:00:00",
                    "camera_name": "Portail", "is_outdoor": 1, "temp_c": 12.0,
                },
            ])

            reveils: list[str] = []
            releves = await collector.relever_temperatures(
                blink, storage=store, reveiller=True, reveils_effectues=reveils
            )

            # Jardin est resté à 10 °C : il est réveillé. Portail a bougé : non.
            self.assertTrue(jardin.reveillee)
            self.assertFalse(portail.reveillee)
            self.assertEqual(reveils, ["Jardin"])
            # L'écran d'accueil a été relu après le réveil.
            self.assertEqual(blink.appels, 2)
            self.assertEqual(
                {r["camera_name"]: r["temp_c"] for r in releves},
                {"Jardin": 12.0, "Portail": 15.6},
            )


class TestSchedulerCalcul(unittest.TestCase):
    def test_calcul_attente_prochaine_heure(self):
        attente = scheduler.calculer_attente_prochaine_heure(aligner_heure=True, intervalle_minutes=60)
        self.assertGreater(attente, 0)
        self.assertLessEqual(attente, 3600)

        attente_fixe = scheduler.calculer_attente_prochaine_heure(aligner_heure=False, intervalle_minutes=30)
        self.assertEqual(attente_fixe, 1800.0)


class TestWebDashboard(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.temp_dir.name) / "test_web.db"
        self.storage = Storage(self.db_path)
        self.port = 18775
        self.serveur = web.demarrer_serveur_web(self.storage, port=self.port, daemon=True)

    def tearDown(self):
        self.serveur.shutdown()
        self.serveur.server_close()
        self.temp_dir.cleanup()

    def test_endpoints_web(self):
        import json
        import urllib.request

        # 1. Page d'accueil HTML
        with urllib.request.urlopen(f"http://127.0.0.1:{self.port}/") as resp:
            self.assertEqual(resp.status, 200)
            html = resp.read().decode("utf-8")
            self.assertIn("Blink2Temp", html)

        # 2. API latest (vide)
        with urllib.request.urlopen(f"http://127.0.0.1:{self.port}/api/latest") as resp:
            self.assertEqual(resp.status, 200)
            data = json.loads(resp.read().decode("utf-8"))
            self.assertEqual(data, [])

        # 3. API stats
        with urllib.request.urlopen(f"http://127.0.0.1:{self.port}/api/stats?hours=24") as resp:
            self.assertEqual(resp.status, 200)
            data = json.loads(resp.read().decode("utf-8"))
            self.assertEqual(data, [])

        # 4. API history avec plage de dates
        with urllib.request.urlopen(f"http://127.0.0.1:{self.port}/api/history?start=2026-11-01T00:00:00&end=2026-11-03T23:59:59") as resp:
            self.assertEqual(resp.status, 200)
            data = json.loads(resp.read().decode("utf-8"))
            self.assertEqual(data, [])


class TestUniteDesEnTetes(unittest.TestCase):
    def test_les_en_tetes_de_la_synthese_n_affichent_pas_un_gabarit_brut(self):
        # Le tableau de synthèse affichait « Min (${UNITE_TEMP}) » : un gabarit
        # JavaScript dans du HTML statique, jamais interprété.
        self.assertNotIn("(${UNITE_TEMP})", web.HTML_PAGE)
        self.assertEqual(web.HTML_PAGE.count('<span class="unite-temp">'), 3)
        self.assertIn('querySelectorAll(".unite-temp")', web.HTML_PAGE)


class TestMiseAJour(unittest.TestCase):
    def test_comparaison_versions(self):
        self.assertGreater(updater.numeros("1.6.10"), updater.numeros("1.6.9"))
        self.assertEqual(updater.numeros("v0.1.5"), (0, 1, 5))
        self.assertEqual(updater.numeros("invalide"), (0,))

    def test_version_locale_lue_depuis_version(self):
        attendue = (Path(__file__).parent / "VERSION").read_text(encoding="utf-8").strip()
        self.assertEqual(updater.version_locale(), attendue)

    def test_choix_archive_windows(self):
        version = "9.8.7"
        nom = f"blink2temp-{version}-windows-x64.zip"
        url = f"https://github.com/nico579/blink2temp/releases/download/v{version}/{nom}"
        assets = [{
            "name": nom,
            "browser_download_url": url,
            "size": 1234,
            "digest": "sha256:" + "a" * 64,
        }]
        choix = updater.choisir_archive(assets, version, "windows-x64")
        self.assertEqual(choix["nom"], nom)
        self.assertEqual(choix["url"], url)
        self.assertEqual(choix["sha256"], "a" * 64)

    def test_archive_d_un_autre_depot_refusee(self):
        version = "9.8.7"
        nom = f"blink2temp-{version}-linux-x64.tar.gz"
        assets = [{
            "name": nom,
            "browser_download_url": f"https://github.com/autre/depot/releases/download/v{version}/{nom}",
            "size": 1234,
            "digest": "sha256:" + "b" * 64,
        }]
        self.assertEqual(updater.choisir_archive(assets, version, "linux-x64"), {})

    def test_chemin_archive_dangereux_refuse(self):
        with tempfile.TemporaryDirectory() as dossier:
            racine = Path(dossier)
            with self.assertRaises(updater.UpdaterError):
                updater._destination_sure(racine, "../evasion.txt")
            with self.assertRaises(updater.UpdaterError):
                updater._destination_sure(racine, "/etc/passwd")

    def test_extraction_zip_refuse_traversee(self):
        import zipfile

        with tempfile.TemporaryDirectory() as dossier:
            racine = Path(dossier)
            archive = racine / "piege.zip"
            with zipfile.ZipFile(archive, "w") as paquet:
                paquet.writestr("../evasion.txt", "x")
            with self.assertRaises(updater.UpdaterError):
                updater._extraire(archive, racine / "sortie")
            self.assertFalse((racine.parent / "evasion.txt").exists())

    def test_instantane_sans_reseau(self):
        etat = updater.etat()
        self.assertIn("version_locale", etat)
        self.assertIn("disponible", etat)
        self.assertIn("etape", etat)


if __name__ == "__main__":
    unittest.main()
