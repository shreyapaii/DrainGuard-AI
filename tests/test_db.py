import sqlite3

import pytest

from drainguard.db import (
    add_inspection,
    add_infrastructure_record,
    add_model_inference,
    connect,
    delete_demo_records,
    infrastructure_counts,
    list_data_sources,
    list_infrastructure_records,
    list_inspections,
    list_model_inferences,
    upsert_data_source,
    update_status,
)


def make_conn(tmp_path):
    return connect(str(tmp_path / "test.db"))


def test_add_and_list_inspection_stores_priority(tmp_path):
    conn = make_conn(tmp_path)
    new_id = add_inspection(
        conn, drain_id="TEST-1", inspection_date="2026-10-01",
        obstruction="Heavy", water_level="High", rainfall="Heavy",
    )
    rows = list_inspections(conn)
    assert len(rows) == 1
    assert rows[0]["id"] == new_id
    assert rows[0]["priority"] == "High"
    assert rows[0]["priority_score"] == 10


def test_missing_drain_id_is_rejected(tmp_path):
    conn = make_conn(tmp_path)
    with pytest.raises(ValueError):
        add_inspection(conn, drain_id="  ", inspection_date="2026-10-01")


def test_update_status_and_filter(tmp_path):
    conn = make_conn(tmp_path)
    rid = add_inspection(conn, drain_id="TEST-2", inspection_date="2026-10-01", obstruction="Partial")
    update_status(conn, rid, "Completed")
    assert list_inspections(conn, statuses=["Completed"])[0]["id"] == rid
    assert list_inspections(conn, statuses=["Pending"]) == []


def test_search_filter(tmp_path):
    conn = make_conn(tmp_path)
    add_inspection(conn, drain_id="ALPHA-9", inspection_date="2026-10-01")
    add_inspection(conn, drain_id="BETA-3", inspection_date="2026-10-01")
    results = list_inspections(conn, search="ALPHA")
    assert [r["drain_id"] for r in results] == ["ALPHA-9"]


def test_ai_summary_is_saved(tmp_path):
    conn = make_conn(tmp_path)
    rid = add_inspection(conn, drain_id="AI-1", inspection_date="2026-10-01",
                         ai_summary="Detected (COCO classes): 1 x bottle.")
    row = list_inspections(conn, search="AI-1")[0]
    assert row["id"] == rid
    assert row["ai_summary"].startswith("Detected")


def test_sample_records_are_excluded_from_default_listing(tmp_path):
    conn = make_conn(tmp_path)
    add_inspection(
        conn,
        drain_id="SAMPLE-1",
        inspection_date="2026-10-01",
        notes="Optional sample only.",
        is_demo=True,
    )
    assert list_inspections(conn) == []
    sample = list_inspections(conn, include_samples=True)
    assert sample[0]["is_demo"] == 1
    assert sample[0]["record_type"] == "sample_inspection"


def test_delete_demo_records_only_removes_marked_rows(tmp_path):
    conn = make_conn(tmp_path)
    add_inspection(conn, drain_id="REAL-1", inspection_date="2026-10-01")
    add_inspection(conn, drain_id="SAMPLE-1", inspection_date="2026-10-01", is_demo=True)
    assert delete_demo_records(conn) == 1
    rows = list_inspections(conn, include_samples=True)
    assert [row["drain_id"] for row in rows] == ["REAL-1"]


def test_migration_adds_ai_column_to_old_database(tmp_path):
    path = tmp_path / "old.db"
    old = sqlite3.connect(path)
    old.executescript("""
        CREATE TABLE inspections (
            id INTEGER PRIMARY KEY AUTOINCREMENT, drain_id TEXT NOT NULL,
            area_description TEXT, obstruction TEXT, water_level TEXT, rainfall TEXT,
            inspection_date TEXT NOT NULL, notes TEXT, priority_score INTEGER NOT NULL,
            priority TEXT NOT NULL, evidence TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'Pending', is_demo INTEGER NOT NULL DEFAULT 0,
            created_at TEXT NOT NULL DEFAULT (datetime('now')));
    """)
    old.commit()
    old.close()
    conn = connect(str(path))
    cols = {r["name"] for r in conn.execute("PRAGMA table_info(inspections)")}
    assert "ai_summary" in cols


def test_coordinates_are_optional_and_stored(tmp_path):
    conn = make_conn(tmp_path)
    add_inspection(conn, drain_id="GEO-1", inspection_date="2026-10-01",
                   latitude=15.85, longitude=74.5)
    add_inspection(conn, drain_id="GEO-2", inspection_date="2026-10-01")
    rows = {r["drain_id"]: r for r in list_inspections(conn)}
    assert rows["GEO-1"]["latitude"] == 15.85
    assert rows["GEO-2"]["latitude"] is None


def test_half_coordinates_are_rejected(tmp_path):
    conn = make_conn(tmp_path)
    with pytest.raises(ValueError):
        add_inspection(conn, drain_id="GEO-3", inspection_date="2026-10-01", latitude=15.0)


def test_out_of_range_coordinates_are_rejected(tmp_path):
    conn = make_conn(tmp_path)
    with pytest.raises(ValueError):
        add_inspection(conn, drain_id="GEO-4", inspection_date="2026-10-01",
                       latitude=120.0, longitude=10.0)


def test_migration_adds_coordinate_columns(tmp_path):
    path = tmp_path / "v1.db"
    old = sqlite3.connect(path)
    old.executescript("""
        CREATE TABLE inspections (
            id INTEGER PRIMARY KEY AUTOINCREMENT, drain_id TEXT NOT NULL,
            area_description TEXT, obstruction TEXT, water_level TEXT, rainfall TEXT,
            inspection_date TEXT NOT NULL, notes TEXT, priority_score INTEGER NOT NULL,
            priority TEXT NOT NULL, evidence TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'Pending', is_demo INTEGER NOT NULL DEFAULT 0,
            created_at TEXT NOT NULL DEFAULT (datetime('now')));
    """)
    old.commit()
    old.close()
    conn = connect(str(path))
    cols = {r["name"] for r in conn.execute("PRAGMA table_info(inspections)")}
    assert {"latitude", "longitude", "ai_summary", "record_type", "source_name"} <= cols


def test_public_infrastructure_is_separate_and_deduplicated(tmp_path):
    conn = make_conn(tmp_path)
    payload = dict(
        source_name="Test public source",
        source_url="https://example.test/layer/7",
        source_layer_id=7,
        source_layer_name="Storm Water Drains",
        source_object_id="42",
        record_type="public_stormwater_drain",
        external_id="A -> B",
        label="Storm water drain A -> B",
        attributes={"OBJECTID": 42},
        geometry={"paths": [[[72.8, 19.0], [72.81, 19.01]]]},
        geometry_type="esriGeometryPolyline",
        latitude=19.0,
        longitude=72.8,
        import_date="2026-10-09T00:00:00+00:00",
        source_retrieved_at="2026-10-09T00:00:00+00:00",
    )
    assert add_infrastructure_record(conn, **payload) is True
    assert add_infrastructure_record(conn, **payload) is False
    assert list_inspections(conn) == []
    rows = list_infrastructure_records(conn)
    assert len(rows) == 1
    assert rows[0]["record_type"] == "public_stormwater_drain"
    assert infrastructure_counts(conn) == {"public_stormwater_drain": 1}


def test_data_source_metadata_is_upserted(tmp_path):
    conn = make_conn(tmp_path)
    upsert_data_source(
        conn,
        source_name="Source A",
        source_url="https://example.test",
        source_description="Original",
        retrieved_at="2026-10-09",
        status="available",
        metadata={"count": 1},
    )
    upsert_data_source(
        conn,
        source_name="Source A",
        source_url="https://example.test/new",
        source_description="Updated",
        retrieved_at="2026-10-10",
        status="unavailable",
        metadata={"error": "timeout"},
    )
    rows = list_data_sources(conn)
    assert len(rows) == 1
    assert rows[0]["source_url"].endswith("/new")
    assert rows[0]["status"] == "unavailable"


def test_model_inference_is_saved_separately_from_priority(tmp_path):
    conn = make_conn(tmp_path)
    rid = add_inspection(
        conn,
        drain_id="AI-2",
        inspection_date="2026-10-01",
        obstruction=None,
        water_level=None,
        rainfall=None,
    )
    iid = add_model_inference(
        conn,
        inspection_id=rid,
        model_name="Test detector",
        model_version="v1",
        dataset_name="COCO",
        source_name="Unit test",
        source_url="https://example.test/model",
        inference_date="2026-10-09T00:00:00+00:00",
        threshold=0.35,
        detections=[{"label": "bottle", "score": 0.9, "box": [1, 2, 3, 4]}],
        summary="Detected: bottle. Not a blockage claim.",
    )
    row = list_model_inferences(conn)[0]
    inspection = list_inspections(conn)[0]
    assert row["id"] == iid
    assert row["inspection_id"] == rid
    assert inspection["priority"] == "Low"
    assert inspection["priority_score"] == 0
