from drainguard.analytics import (
    activity_by_date,
    geo_points,
    overview_metrics,
    recent_records,
    severity_counts,
    split_demo,
    status_breakdown,
)

RECORDS = [
    {"id": 1, "drain_id": "A", "priority": "High", "status": "Pending",
     "inspection_date": "2026-10-01", "latitude": 15.85, "longitude": 74.5, "is_demo": 0},
    {"id": 2, "drain_id": "A", "priority": "Low", "status": "Completed",
     "inspection_date": "2026-10-02", "latitude": None, "longitude": None, "is_demo": 0},
    {"id": 3, "drain_id": "B", "priority": "Medium", "status": "In progress",
     "inspection_date": "2026-10-02", "latitude": None, "longitude": None, "is_demo": 1},
]


def test_overview_metrics_from_records():
    m = overview_metrics(RECORDS)
    assert m["registered_drains"] == 2
    assert m["inspections_recorded"] == 3
    assert m["open_tasks"] == 2
    assert m["high_findings"] == 1
    assert m["completed_tasks"] == 1


def test_empty_records_give_zero_metrics():
    m = overview_metrics([])
    assert all(v == 0 for v in m.values())


def test_status_and_severity_include_zero_buckets():
    assert status_breakdown(RECORDS) == {"Pending": 1, "In progress": 1, "Completed": 1}
    assert severity_counts([]) == {"High": 0, "Medium": 0, "Low": 0}


def test_activity_is_sorted_by_date():
    assert activity_by_date(RECORDS) == {"2026-10-01": 1, "2026-10-02": 2}


def test_geo_points_only_include_real_coordinates():
    points = geo_points(RECORDS)
    assert len(points) == 1
    assert points[0]["drain_id"] == "A"


def test_split_demo_separates_records():
    real, demo = split_demo(RECORDS)
    assert [r["id"] for r in real] == [1, 2]
    assert [r["id"] for r in demo] == [3]


def test_recent_records_newest_first():
    assert [r["id"] for r in recent_records(RECORDS, limit=2)] == [3, 2]
