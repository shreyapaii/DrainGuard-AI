"""Import real MCGM/BMC stormwater infrastructure into the local database."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from drainguard import public_data
from drainguard.db import connect


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", default="data/drainguard.db", help="SQLite database path")
    parser.add_argument(
        "--limit-per-layer",
        type=int,
        default=100,
        help="Maximum features to fetch per selected layer",
    )
    parser.add_argument("--drains", action="store_true", help="Import Storm Water Drains layer 7")
    parser.add_argument("--manholes", action="store_true", help="Import Storm Water Manholes layer 6")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    layer_ids = []
    if args.drains:
        layer_ids.append(public_data.MCGM_STORM_DRAINS_LAYER_ID)
    if args.manholes:
        layer_ids.append(public_data.MCGM_STORM_MANHOLES_LAYER_ID)
    if not layer_ids:
        layer_ids = [public_data.MCGM_STORM_DRAINS_LAYER_ID, public_data.MCGM_STORM_MANHOLES_LAYER_ID]

    conn = connect(args.db)
    try:
        summary = public_data.import_mcgmgis_stormwater(
            conn,
            layer_ids=tuple(layer_ids),
            limit_per_layer=args.limit_per_layer,
        )
    except public_data.PublicDataUnavailable as err:
        print(f"MCGM source unavailable. No fallback data imported. Details: {err}")
        return 2

    print(f"Source: {summary.source_name}")
    print(f"Retrieved at: {summary.retrieved_at}")
    print(f"Requested features: {summary.requested}")
    print(f"Inserted: {summary.inserted}")
    print(f"Duplicates skipped: {summary.duplicates}")
    for layer in summary.layers:
        print(
            f"Layer {layer['id']} {layer['name']}: "
            f"{layer['imported_batch']} fetched from {layer['count']} available"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
