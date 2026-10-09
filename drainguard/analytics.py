"""
Dashboard calculations. Every figure is computed from stored records.
Pure functions over lists of dicts, so they can be unit tested without Streamlit.
"""

from collections import Counter

from drainguard.db import STATUSES

PRIORITY_ORDER = ["High", "Medium", "Low"]


def split_demo(records: list[dict]) -> tuple[list[dict], list[dict]]:
    """Return (real_records, demo_records)."""
    real = [r for r in records if not r["is_demo"]]
    demo = [r for r in records if r["is_demo"]]
    return real, demo


def overview_metrics(records: list[dict]) -> dict:
    open_tasks = [r for r in records if r["status"] != "Completed"]
    return {
        "registered_drains": len({r["drain_id"] for r in records}),
        "inspections_recorded": len(records),
        "open_tasks": len(open_tasks),
        "high_findings": sum(1 for r in records if r["priority"] == "High"),
        "completed_tasks": sum(1 for r in records if r["status"] == "Completed"),
    }


def status_breakdown(records: list[dict]) -> dict[str, int]:
    counts = Counter(r["status"] for r in records)
    return {status: counts.get(status, 0) for status in STATUSES}


def severity_counts(records: list[dict]) -> dict[str, int]:
    counts = Counter(r["priority"] for r in records)
    return {priority: counts.get(priority, 0) for priority in PRIORITY_ORDER}


def activity_by_date(records: list[dict]) -> dict[str, int]:
    counts = Counter(r["inspection_date"] for r in records)
    return dict(sorted(counts.items()))


def geo_points(records: list[dict]) -> list[dict]:
    """Only records with real, user-entered coordinates. Never invents locations."""
    return [
        {"lat": r["latitude"], "lon": r["longitude"], "drain_id": r["drain_id"],
         "priority": r["priority"]}
        for r in records
        if r["latitude"] is not None and r["longitude"] is not None
    ]


def recent_records(records: list[dict], limit: int = 8) -> list[dict]:
    return sorted(records, key=lambda r: r["id"], reverse=True)[:limit]
