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


if __name__ == "__main__":
    unittest.main()
