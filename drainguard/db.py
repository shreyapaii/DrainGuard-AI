"""SQLite persistence for inspections, public infrastructure, and model output."""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any

from drainguard.scoring import assess_priority

STATUSES = ("Pending", "In progress", "Completed")
USER_SOURCE_NAME = "User entry"
USER_RECORD_TYPE = "user_inspection"
SAMPLE_RECORD_TYPE = "sample_inspection"

SCHEMA = """
CREATE TABLE IF NOT EXISTS inspections (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    drain_id TEXT NOT NULL,
    area_description TEXT,
    latitude REAL,
    longitude REAL,
    obstruction TEXT,
    water_level TEXT,
    rainfall TEXT,
    inspection_date TEXT NOT NULL,
    notes TEXT,
    ai_summary TEXT,
    priority_score INTEGER NOT NULL,
    priority TEXT NOT NULL,
    evidence TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'Pending',
    is_demo INTEGER NOT NULL DEFAULT 0,
    record_type TEXT NOT NULL DEFAULT 'user_inspection',
    source_name TEXT NOT NULL DEFAULT 'User entry',
    source_url TEXT,
    source_record_id TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS data_sources (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    source_name TEXT NOT NULL UNIQUE,
    source_url TEXT NOT NULL,
    source_description TEXT,
    retrieved_at TEXT,
    status TEXT NOT NULL DEFAULT 'unknown',
    metadata_json TEXT,
    updated_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS infrastructure_records (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    source_name TEXT NOT NULL,
    source_url TEXT NOT NULL,
    source_layer_id INTEGER,
    source_layer_name TEXT,
    source_object_id TEXT NOT NULL,
    record_type TEXT NOT NULL,
    external_id TEXT,
    label TEXT,
    attributes_json TEXT NOT NULL,
    geometry_json TEXT,
    geometry_type TEXT,
    latitude REAL,
    longitude REAL,
    import_date TEXT NOT NULL DEFAULT (datetime('now')),
    source_retrieved_at TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    UNIQUE(source_name, source_layer_id, source_object_id, record_type)
);

CREATE INDEX IF NOT EXISTS idx_infrastructure_type
    ON infrastructure_records(record_type);
CREATE INDEX IF NOT EXISTS idx_infrastructure_source
    ON infrastructure_records(source_name, source_layer_id);

CREATE TABLE IF NOT EXISTS model_inferences (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    inspection_id INTEGER NOT NULL,
    model_name TEXT NOT NULL,
    model_version TEXT,
    dataset_name TEXT,
    source_name TEXT NOT NULL,
    source_url TEXT,
    inference_date TEXT NOT NULL,
    threshold REAL,
    detections_json TEXT NOT NULL,
    summary TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY (inspection_id) REFERENCES inspections(id) ON DELETE CASCADE
);
"""

INSPECTION_MIGRATIONS = {
    "ai_summary": "ALTER TABLE inspections ADD COLUMN ai_summary TEXT",
    "latitude": "ALTER TABLE inspections ADD COLUMN latitude REAL",
    "longitude": "ALTER TABLE inspections ADD COLUMN longitude REAL",
    "is_demo": "ALTER TABLE inspections ADD COLUMN is_demo INTEGER NOT NULL DEFAULT 0",
    "record_type": (
        "ALTER TABLE inspections ADD COLUMN record_type TEXT NOT NULL "
        f"DEFAULT '{USER_RECORD_TYPE}'"
    ),
    "source_name": (
        "ALTER TABLE inspections ADD COLUMN source_name TEXT NOT NULL "
        f"DEFAULT '{USER_SOURCE_NAME}'"
    ),
    "source_url": "ALTER TABLE inspections ADD COLUMN source_url TEXT",
    "source_record_id": "ALTER TABLE inspections ADD COLUMN source_record_id TEXT",
}


def _json(data: Any) -> str:
    return json.dumps(data, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _migrate(conn: sqlite3.Connection) -> None:
    """Add columns introduced after earlier schema versions (safe to rerun)."""
    columns = {row["name"] for row in conn.execute("PRAGMA table_info(inspections)")}
    for column, statement in INSPECTION_MIGRATIONS.items():
        if column not in columns:
            conn.execute(statement)
    conn.commit()


def connect(db_path: str = "data/drainguard.db") -> sqlite3.Connection:
    """Open (and create if needed) the SQLite database."""
    path = Path(db_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    # check_same_thread=False lets Streamlit reuse the connection across reruns.
    conn = sqlite3.connect(path, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.executescript(SCHEMA)
    _migrate(conn)
    return conn


def _validate_coordinates(latitude, longitude) -> None:
    if (latitude is None) != (longitude is None):
        raise ValueError("Enter both latitude and longitude, or neither.")
    if latitude is not None:
        if not -90 <= latitude <= 90 or not -180 <= longitude <= 180:
            raise ValueError("Coordinates are out of range.")


def add_inspection(
    conn: sqlite3.Connection,
    *,
    drain_id: str,
    inspection_date: str,
    area_description: str | None = None,
    latitude: float | None = None,
    longitude: float | None = None,
    obstruction: str | None = None,
    water_level: str | None = None,
    rainfall: str | None = None,
    notes: str | None = None,
    ai_summary: str | None = None,
    status: str = "Pending",
    is_demo: bool = False,
    record_type: str = USER_RECORD_TYPE,
    source_name: str = USER_SOURCE_NAME,
    source_url: str | None = None,
    source_record_id: str | None = None,
) -> int:
    drain_id = (drain_id or "").strip()
    if not drain_id:
        raise ValueError("Drain identifier is required.")
    if status not in STATUSES:
        raise ValueError(f"Unknown status: {status!r}")
    _validate_coordinates(latitude, longitude)

    if is_demo:
        record_type = SAMPLE_RECORD_TYPE
        source_name = "Optional sample data"

    result = assess_priority(obstruction, water_level, rainfall)
    cur = conn.execute(
        """
        INSERT INTO inspections
            (drain_id, area_description, latitude, longitude, obstruction, water_level,
             rainfall, inspection_date, notes, ai_summary, priority_score, priority,
             evidence, status, is_demo, record_type, source_name, source_url,
             source_record_id)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            drain_id,
            area_description or None,
            latitude,
            longitude,
            obstruction,
            water_level,
            rainfall,
            inspection_date,
            notes or None,
            ai_summary or None,
            result.score,
            result.priority,
            result.evidence,
            status,
            1 if is_demo else 0,
            record_type,
            source_name,
            source_url,
            source_record_id,
        ),
    )
    conn.commit()
    return cur.lastrowid


def list_inspections(
    conn: sqlite3.Connection,
    priorities: list[str] | None = None,
    statuses: list[str] | None = None,
    search: str | None = None,
    include_samples: bool = False,
) -> list[dict]:
    clauses, params = [], []
    if not include_samples:
        clauses.append("COALESCE(is_demo, 0) = 0")
        clauses.append("record_type = ?")
        params.append(USER_RECORD_TYPE)
    if priorities:
        clauses.append(f"priority IN ({','.join('?' * len(priorities))})")
        params.extend(priorities)
    if statuses:
        clauses.append(f"status IN ({','.join('?' * len(statuses))})")
        params.extend(statuses)
    if search:
        clauses.append("(drain_id LIKE ? OR area_description LIKE ?)")
        params.extend([f"%{search}%", f"%{search}%"])

    where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
    rows = conn.execute(
        f"SELECT * FROM inspections {where} ORDER BY priority_score DESC, id DESC",
        params,
    ).fetchall()
    return [dict(row) for row in rows]


def update_status(conn: sqlite3.Connection, inspection_id: int, status: str) -> None:
    if status not in STATUSES:
        raise ValueError(f"Unknown status: {status!r}")
    conn.execute(
        "UPDATE inspections SET status = ? WHERE id = ? AND record_type = ?",
        (status, inspection_id, USER_RECORD_TYPE),
    )
    conn.commit()


def count_demo_records(conn: sqlite3.Connection) -> int:
    row = conn.execute(
        "SELECT COUNT(*) FROM inspections WHERE COALESCE(is_demo, 0) = 1"
    ).fetchone()
    return int(row[0])


def delete_demo_records(conn: sqlite3.Connection) -> int:
    """Delete only rows that were explicitly marked as fictional demo/sample data."""
    before = count_demo_records(conn)
    conn.execute("DELETE FROM inspections WHERE COALESCE(is_demo, 0) = 1")
    conn.commit()
    return before


def upsert_data_source(
    conn: sqlite3.Connection,
    *,
    source_name: str,
    source_url: str,
    source_description: str | None = None,
    retrieved_at: str | None = None,
    status: str = "available",
    metadata: dict | None = None,
) -> None:
    conn.execute(
        """
        INSERT INTO data_sources
            (source_name, source_url, source_description, retrieved_at, status,
             metadata_json, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, datetime('now'))
        ON CONFLICT(source_name) DO UPDATE SET
            source_url = excluded.source_url,
            source_description = excluded.source_description,
            retrieved_at = excluded.retrieved_at,
            status = excluded.status,
            metadata_json = excluded.metadata_json,
            updated_at = datetime('now')
        """,
        (
            source_name,
            source_url,
            source_description,
            retrieved_at,
            status,
            _json(metadata or {}),
        ),
    )
    conn.commit()


def list_data_sources(conn: sqlite3.Connection) -> list[dict]:
    rows = conn.execute(
        "SELECT * FROM data_sources ORDER BY updated_at DESC, source_name"
    ).fetchall()
    return [dict(row) for row in rows]


def add_infrastructure_record(
    conn: sqlite3.Connection,
    *,
    source_name: str,
    source_url: str,
    source_layer_id: int | None,
    source_layer_name: str | None,
    source_object_id: str,
    record_type: str,
    attributes: dict,
    geometry: dict | None,
    geometry_type: str | None,
    import_date: str,
    source_retrieved_at: str | None,
    external_id: str | None = None,
    label: str | None = None,
    latitude: float | None = None,
    longitude: float | None = None,
) -> bool:
    _validate_coordinates(latitude, longitude)
    cur = conn.execute(
        """
        INSERT OR IGNORE INTO infrastructure_records
            (source_name, source_url, source_layer_id, source_layer_name,
             source_object_id, record_type, external_id, label, attributes_json,
             geometry_json, geometry_type, latitude, longitude, import_date,
             source_retrieved_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            source_name,
            source_url,
            source_layer_id,
            source_layer_name,
            source_object_id,
            record_type,
            external_id,
            label,
            _json(attributes),
            _json(geometry) if geometry else None,
            geometry_type,
            latitude,
            longitude,
            import_date,
            source_retrieved_at,
        ),
    )
    conn.commit()
    return cur.rowcount == 1


def list_infrastructure_records(
    conn: sqlite3.Connection,
    record_types: list[str] | None = None,
    search: str | None = None,
    limit: int = 2000,
) -> list[dict]:
    clauses, params = [], []
    if record_types:
        clauses.append(f"record_type IN ({','.join('?' * len(record_types))})")
        params.extend(record_types)
    if search:
        clauses.append(
            "(source_object_id LIKE ? OR external_id LIKE ? OR label LIKE ? "
            "OR source_layer_name LIKE ?)"
        )
        like = f"%{search}%"
        params.extend([like, like, like, like])
    where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
    params.append(limit)
    rows = conn.execute(
        f"""
        SELECT * FROM infrastructure_records
        {where}
        ORDER BY import_date DESC, source_layer_id, CAST(source_object_id AS INTEGER)
        LIMIT ?
        """,
        params,
    ).fetchall()
    return [dict(row) for row in rows]


def infrastructure_counts(conn: sqlite3.Connection) -> dict[str, int]:
    rows = conn.execute(
        "SELECT record_type, COUNT(*) AS n FROM infrastructure_records GROUP BY record_type"
    ).fetchall()
    return {row["record_type"]: row["n"] for row in rows}


def add_model_inference(
    conn: sqlite3.Connection,
    *,
    inspection_id: int,
    model_name: str,
    model_version: str | None,
    dataset_name: str | None,
    source_name: str,
    source_url: str | None,
    inference_date: str,
    threshold: float | None,
    detections: list[dict],
    summary: str,
) -> int:
    cur = conn.execute(
        """
        INSERT INTO model_inferences
            (inspection_id, model_name, model_version, dataset_name, source_name,
             source_url, inference_date, threshold, detections_json, summary)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            inspection_id,
            model_name,
            model_version,
            dataset_name,
            source_name,
            source_url,
            inference_date,
            threshold,
            _json(detections),
            summary,
        ),
    )
    conn.commit()
    return cur.lastrowid


def list_model_inferences(
    conn: sqlite3.Connection,
    inspection_id: int | None = None,
    limit: int = 100,
) -> list[dict]:
    params: list[Any] = []
    where = ""
    if inspection_id is not None:
        where = "WHERE inspection_id = ?"
        params.append(inspection_id)
    params.append(limit)
    rows = conn.execute(
        f"""
        SELECT * FROM model_inferences
        {where}
        ORDER BY inference_date DESC, id DESC
        LIMIT ?
        """,
        params,
    ).fetchall()
    return [dict(row) for row in rows]
