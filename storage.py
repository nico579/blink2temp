"""Gestion de la base de données SQLite pour l'historique des températures.

Conserve chaque relevé horodaté par caméra, permet l'analyse statistique
(min/max/moyenne) et l'exportation CSV.
"""

from __future__ import annotations

from contextlib import contextmanager
import csv
import datetime as dt
from pathlib import Path
import sqlite3
from typing import Any, Generator

import paths

DB_FILENAME = "temperatures.db"


class Storage:
    def __init__(self, db_path: Path | str | None = None):
        if db_path is None:
            self.db_path = paths.dossier_donnees() / DB_FILENAME
        else:
            self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.init_db()

    @contextmanager
    def _connection(self) -> Generator[sqlite3.Connection, None, None]:
        """Ouvre une connexion SQLite, gère le commit et garantit la fermeture du handle."""
        conn = sqlite3.connect(str(self.db_path), timeout=15)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        finally:
            conn.close()

    def init_db(self) -> None:
        """Crée les tables et index nécessaires si absents."""
        with self._connection() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS readings (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    recorded_at TEXT NOT NULL,
                    local_time TEXT NOT NULL,
                    camera_name TEXT NOT NULL,
                    camera_id TEXT,
                    camera_type TEXT,
                    model TEXT,
                    is_outdoor INTEGER NOT NULL DEFAULT 1,
                    temp_c REAL,
                    temp_f REAL,
                    battery TEXT,
                    battery_level INTEGER,
                    wifi_strength INTEGER,
                    lfr_signal INTEGER,
                    status TEXT,
                    blink_updated_at TEXT
                )
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_readings_camera_time 
                ON readings (camera_name, recorded_at)
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_readings_recorded_at 
                ON readings (recorded_at)
            """)

    def enregistrer_releves(self, releves: list[dict[str, Any]]) -> int:
        """Enregistre un lot de relevés de caméras dans la base."""
        if not releves:
            return 0
        insert_query = """
            INSERT INTO readings (
                recorded_at, local_time, camera_name, camera_id, camera_type,
                model, is_outdoor, temp_c, temp_f, battery, battery_level,
                wifi_strength, lfr_signal, status, blink_updated_at
            ) VALUES (
                :recorded_at, :local_time, :camera_name, :camera_id, :camera_type,
                :model, :is_outdoor, :temp_c, :temp_f, :battery, :battery_level,
                :wifi_strength, :lfr_signal, :status, :blink_updated_at
            )
        """
        champs = [
            "recorded_at", "local_time", "camera_name", "camera_id", "camera_type",
            "model", "is_outdoor", "temp_c", "temp_f", "battery", "battery_level",
            "wifi_strength", "lfr_signal", "status", "blink_updated_at",
        ]
        normalises = [
            {c: r.get(c, 1 if c == "is_outdoor" else None) for c in champs}
            for r in releves
        ]
        with self._connection() as conn:
            conn.executemany(insert_query, normalises)
        return len(releves)

    def obtenir_dernieres_temperatures(self, outdoor_only: bool = True) -> list[dict[str, Any]]:
        """Renvoie le relevé le plus récent pour chaque caméra."""
        filtre = "WHERE is_outdoor = 1" if outdoor_only else ""
        query = f"""
            WITH Derniers AS (
                SELECT *, ROW_NUMBER() OVER (
                    PARTITION BY camera_name ORDER BY recorded_at DESC
                ) as rn
                FROM readings
                {filtre}
            )
            SELECT * FROM Derniers WHERE rn = 1 ORDER BY camera_name ASC
        """
        with self._connection() as conn:
            rows = conn.execute(query).fetchall()
            return [dict(r) for r in rows]

    def obtenir_historique(
        self,
        camera: str | None = None,
        heures: int | None = 24,
        debut: str | None = None,
        fin: str | None = None,
        outdoor_only: bool = True,
        limite: int = 20000,
    ) -> list[dict[str, Any]]:
        """Renvoie les relevés sur la période demandée."""
        conditions: list[str] = []
        params: list[Any] = []

        if debut:
            conditions.append("recorded_at >= ?")
            params.append(debut)
        elif heures is not None and heures > 0:
            since = (dt.datetime.now(dt.timezone.utc) - dt.timedelta(hours=heures)).isoformat()
            conditions.append("recorded_at >= ?")
            params.append(since)

        if fin:
            conditions.append("recorded_at <= ?")
            params.append(fin)

        if outdoor_only:
            conditions.append("is_outdoor = 1")
        if camera:
            conditions.append("camera_name = ?")
            params.append(camera)

        where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""
        query = f"""
            SELECT * FROM readings
            {where_clause}
            ORDER BY recorded_at ASC
            LIMIT ?
        """
        params.append(limite)
        with self._connection() as conn:
            rows = conn.execute(query, params).fetchall()
            return [dict(r) for r in rows]

    def obtenir_statistiques(
        self,
        heures: int = 24,
        outdoor_only: bool = True,
    ) -> list[dict[str, Any]]:
        """Calcule min, max, moyenne sur la période pour chaque caméra."""
        since = (dt.datetime.now(dt.timezone.utc) - dt.timedelta(hours=heures)).isoformat()
        filtre = "AND is_outdoor = 1" if outdoor_only else ""
        query = f"""
            SELECT 
                camera_name,
                model,
                MIN(temp_c) as min_temp_c,
                MAX(temp_c) as max_temp_c,
                ROUND(AVG(temp_c), 1) as avg_temp_c,
                COUNT(temp_c) as count,
                MAX(recorded_at) as last_seen
            FROM readings
            WHERE recorded_at >= ? AND temp_c IS NOT NULL {filtre}
            GROUP BY camera_name
            ORDER BY camera_name ASC
        """
        with self._connection() as conn:
            rows = conn.execute(query, (since,)).fetchall()
            return [dict(r) for r in rows]

    def exporter_csv(self, chemin: Path | str, heures: int | None = None) -> int:
        """Exporte l'historique des relevés dans un fichier CSV."""
        chemin = Path(chemin)
        chemin.parent.mkdir(parents=True, exist_ok=True)

        query = "SELECT * FROM readings"
        params: list[Any] = []
        if heures is not None:
            since = (dt.datetime.now(dt.timezone.utc) - dt.timedelta(hours=heures)).isoformat()
            query += " WHERE recorded_at >= ?"
            params.append(since)
        query += " ORDER BY recorded_at DESC"

        with self._connection() as conn:
            cursor = conn.execute(query, params)
            colonnes = [desc[0] for desc in cursor.description]
            lignes = cursor.fetchall()

        with open(chemin, "w", newline="", encoding="utf-8-sig") as f:
            writer = csv.writer(f, delimiter=";")
            writer.writerow(colonnes)
            for row in lignes:
                writer.writerow(list(row))

        return len(lignes)

    def reinitialiser_base(self) -> int:
        """Supprime tous les relevés de la base de données et optimise l'espace."""
        with self._connection() as conn:
            cur = conn.execute("DELETE FROM readings")
            conn.execute("VACUUM")
            return cur.rowcount
