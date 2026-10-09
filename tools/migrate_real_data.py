"""Safely remove fictional sample/demo rows and optionally reset inspections.

Examples:
    python tools/migrate_real_data.py --apply
    python tools/migrate_real_data.py --apply --reset-inspections
"""

from __future__ import annotations

import argparse
import csv
import shutil
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from drainguard.db import USER_RECORD_TYPE, connect, delete_demo_records, list_inspections


def timestamp() -> str:
    return datetime.now().strftime("%Y%m%d_%H%M%S")


def backup_database(db_path: Path, backup_dir: Path, stamp: str) -> Path | None:
    backup_dir.mkdir(parents=True, exist_ok=True)
    if not db_path.exists():
        return None
    target = backup_dir / f"drainguard_backup_{stamp}.db"
    shutil.copy2(db_path, target)
    return target


def export_user_inspections(conn, backup_dir: Path, stamp: str) -> Path:
    backup_dir.mkdir(parents=True, exist_ok=True)
    target = backup_dir / f"user_inspections_backup_{stamp}.csv"
    rows = list_inspections(conn)
    fieldnames = [
        "id",
        "drain_id",
        "area_description",
        "latitude",
        "longitude",
        "obstruction",
        "water_level",
        "rainfall",
        "inspection_date",
        "notes",
        "ai_summary",
        "priority_score",
        "priority",
        "evidence",
        "status",
        "record_type",
        "source_name",
        "source_url",
        "source_record_id",
        "created_at",
    ]
    with target.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)
    return target


def reset_user_inspections(conn) -> int:
    row = conn.execute(
        "SELECT COUNT(*) FROM inspections WHERE record_type = ? AND COALESCE(is_demo, 0) = 0",
        (USER_RECORD_TYPE,),
    ).fetchone()
    count = int(row[0])
    conn.execute(
        "DELETE FROM inspections WHERE record_type = ? AND COALESCE(is_demo, 0) = 0",
        (USER_RECORD_TYPE,),
    )
    conn.commit()
    return count


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", default="data/drainguard.db", help="SQLite database path")
    parser.add_argument("--backup-dir", default="data/backups", help="Backup output folder")
    parser.add_argument("--apply", action="store_true", help="Perform changes after backing up")
    parser.add_argument(
        "--reset-inspections",
        action="store_true",
        help="After backup, delete all user-entered inspection records as an explicit reset",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    db_path = Path(args.db)
    backup_dir = Path(args.backup_dir)
    conn = connect(str(db_path))
    demo_count = conn.execute(
        "SELECT COUNT(*) FROM inspections WHERE COALESCE(is_demo, 0) = 1"
    ).fetchone()[0]
    user_count = len(list_inspections(conn))

    print(f"Database: {db_path}")
    print(f"Fictional demo/sample inspection rows: {demo_count}")
    print(f"User-entered inspection rows: {user_count}")

    if not args.apply:
        print("Dry run only. Re-run with --apply to back up and modify the database.")
        return 0

    stamp = timestamp()
    db_backup = backup_database(db_path, backup_dir, stamp)
    csv_backup = export_user_inspections(conn, backup_dir, stamp)
    print(f"Database backup: {db_backup}")
    print(f"User inspection CSV backup: {csv_backup}")

    removed_demo = delete_demo_records(conn)
    print(f"Removed fictional demo/sample rows: {removed_demo}")

    if args.reset_inspections:
        removed_user = reset_user_inspections(conn)
        print(f"Removed user-entered inspection rows: {removed_user}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
