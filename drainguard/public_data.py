"""Public infrastructure import helpers for DrainGuard AI.

The importer stores public mapped infrastructure separately from user-entered
inspection records. Public infrastructure existence is not treated as evidence
of blockage, inspection, maintenance, or priority.
"""

from __future__ import annotations

import json
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from drainguard.db import add_infrastructure_record, upsert_data_source

MCGM_MAPSERVER_URL = (
    "https://prsrvgisapp.mcgm.gov.in/server/rest/services/mcgm/"
    "MCGMGIS_Departments_Master_All_Layers/MapServer"
)
MCGM_SOURCE_NAME = "Brihanmumbai Municipal Corporation GIS: Storm Water Drainage"
MCGM_SOURCE_DESCRIPTION = (
    "Public ArcGIS REST MapServer published for MCGM/BMC department GIS layers. "
    "The stormwater group is Mumbai coverage and must not be treated as Belagavi data."
)
MCGM_STORM_GROUP_ID = 229
MCGM_STORM_MANHOLES_LAYER_ID = 6
MCGM_STORM_DRAINS_LAYER_ID = 7
MCGM_LAYER_IDS = (MCGM_STORM_DRAINS_LAYER_ID, MCGM_STORM_MANHOLES_LAYER_ID)

RECORD_TYPE_STORM_DRAIN = "public_stormwater_drain"
RECORD_TYPE_STORM_MANHOLE = "public_stormwater_manhole"

TACO_ZENODO_URL = "https://zenodo.org/records/3587843"
TACO_API_URL = "https://zenodo.org/api/records/3587843"
TACO_ANNOTATIONS_URL = (
    "https://raw.githubusercontent.com/pedropro/TACO/master/data/annotations.json"
)
TACO_SOURCE_NAME = "TACO: Trash Annotations in Context Dataset"
TACO_VERIFIED = {
    "retrieved_at": "2026-10-09",
    "license": "Creative Commons Attribution 4.0 International (CC BY 4.0)",
    "zenodo_doi": "10.5281/zenodo.3587843",
    "download": "TACO.zip, approximately 2.7 GB from Zenodo",
    "annotations": "COCO-style JSON: 1,500 images, 4,784 annotations, 60 trash categories",
    "compatibility": (
        "Useful as a real litter dataset for training or evaluation work, but not "
        "directly compatible with the current COCO-pretrained detector without a "
        "separate training/fine-tuning pipeline and category mapping."
    ),
}

DATA_GOV_SOURCE_NAME = "Open Government Data Platform India"
DATA_GOV_URL = "https://www.data.gov.in/"
DATA_GOV_INVESTIGATION = {
    "retrieved_at": "2026-10-09",
    "status": (
        "Catalog page was reachable, but a clean drainage geometry dataset suitable "
        "for import was not identified during this implementation. API probes to "
        "api.data.gov.in for drainage search were refused by the remote host."
    ),
    "imported": "No data.gov.in records imported.",
}


class PublicDataUnavailable(RuntimeError):
    """Raised when a public source cannot be reached or returns unusable data."""


@dataclass(frozen=True)
class ImportSummary:
    source_name: str
    retrieved_at: str
    layers: list[dict[str, Any]]
    inserted: int
    duplicates: int
    requested: int


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _url(path: str = "", **params) -> str:
    query = {"f": "pjson", **{k: v for k, v in params.items() if v is not None}}
    return f"{MCGM_MAPSERVER_URL}{path}?{urllib.parse.urlencode(query)}"


def fetch_json(url: str, timeout: int = 30) -> dict:
    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": "DrainGuardAI/1.0 (+public-source-verification)",
            "Accept": "application/json,text/plain,*/*",
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            payload = response.read().decode("utf-8", "replace")
    except (OSError, urllib.error.URLError) as err:
        raise PublicDataUnavailable(str(err)) from err
    try:
        data = json.loads(payload)
    except json.JSONDecodeError as err:
        raise PublicDataUnavailable("Source returned non-JSON data.") from err
    if "error" in data:
        raise PublicDataUnavailable(str(data["error"]))
    return data


def get_mcgmgis_service_metadata() -> dict:
    return fetch_json(_url())


def get_mcgmgis_layer_metadata(layer_id: int) -> dict:
    return fetch_json(_url(f"/{layer_id}"))


def get_mcgmgis_count(layer_id: int) -> int:
    data = fetch_json(_url(f"/{layer_id}/query", where="1=1", returnCountOnly="true"))
    return int(data.get("count", 0))


def _layer_record_type(layer_id: int) -> str:
    if layer_id == MCGM_STORM_DRAINS_LAYER_ID:
        return RECORD_TYPE_STORM_DRAIN
    if layer_id == MCGM_STORM_MANHOLES_LAYER_ID:
        return RECORD_TYPE_STORM_MANHOLE
    raise ValueError(f"Unsupported MCGM stormwater layer id: {layer_id}")


def _feature_point(geometry: dict | None) -> tuple[float | None, float | None]:
    """Return (latitude, longitude) only from actual point/path coordinates."""
    if not geometry:
        return None, None
    if "x" in geometry and "y" in geometry:
        return float(geometry["y"]), float(geometry["x"])
    paths = geometry.get("paths")
    if paths:
        for path in paths:
            for coord in path:
                if len(coord) >= 2:
                    return float(coord[1]), float(coord[0])
    return None, None


def _feature_label(layer_id: int, attrs: dict) -> tuple[str | None, str | None]:
    if layer_id == MCGM_STORM_DRAINS_LAYER_ID:
        upstream = attrs.get("US_NODE_ID") or "unknown upstream"
        downstream = attrs.get("DS_NODE_ID") or "unknown downstream"
        external_id = f"{upstream} -> {downstream}"
        label = f"Storm water drain {external_id}"
        return external_id, label
    if layer_id == MCGM_STORM_MANHOLES_LAYER_ID:
        node_id = attrs.get("NODE_ID")
        label = f"Storm water manhole {node_id or attrs.get('OBJECTID')}"
        return str(node_id) if node_id is not None else None, label
    return None, None


def query_mcgmgis_features(
    layer_id: int,
    *,
    limit: int,
    page_size: int = 1000,
) -> list[dict]:
    if limit <= 0:
        return []
    features: list[dict] = []
    offset = 0
    while len(features) < limit:
        batch_size = min(page_size, limit - len(features))
        data = fetch_json(
            _url(
                f"/{layer_id}/query",
                where="1=1",
                outFields="*",
                returnGeometry="true",
                outSR=4326,
                resultRecordCount=batch_size,
                resultOffset=offset,
                orderByFields="OBJECTID",
            )
        )
        batch = data.get("features") or []
        if not batch:
            break
        features.extend(batch)
        offset += len(batch)
        if len(batch) < batch_size:
            break
    return features


def import_mcgmgis_stormwater(
    conn,
    *,
    layer_ids: tuple[int, ...] = MCGM_LAYER_IDS,
    limit_per_layer: int = 500,
) -> ImportSummary:
    """Import real Mumbai stormwater features from the public MCGM ArcGIS service."""
    retrieved_at = utc_now()
    service = get_mcgmgis_service_metadata()
    layers: list[dict[str, Any]] = []
    inserted = duplicates = requested = 0

    upsert_data_source(
        conn,
        source_name=MCGM_SOURCE_NAME,
        source_url=MCGM_MAPSERVER_URL,
        source_description=MCGM_SOURCE_DESCRIPTION,
        retrieved_at=retrieved_at,
        status="available",
        metadata={
            "serviceDescription": service.get("serviceDescription"),
            "copyrightText": service.get("copyrightText"),
            "stormwater_group_layer_id": MCGM_STORM_GROUP_ID,
            "layer_ids": list(layer_ids),
        },
    )

    for layer_id in layer_ids:
        metadata = get_mcgmgis_layer_metadata(layer_id)
        count = get_mcgmgis_count(layer_id)
        features = query_mcgmgis_features(layer_id, limit=limit_per_layer)
        requested += len(features)
        layer_info = {
            "id": layer_id,
            "name": metadata.get("name"),
            "geometryType": metadata.get("geometryType"),
            "count": count,
            "imported_batch": len(features),
            "fields": [
                {"name": field.get("name"), "type": field.get("type"), "alias": field.get("alias")}
                for field in metadata.get("fields", [])
            ],
            "extent": metadata.get("extent"),
        }
        layers.append(layer_info)

        for feature in features:
            attrs = feature.get("attributes") or {}
            geometry = feature.get("geometry")
            object_id = attrs.get("OBJECTID")
            if object_id is None:
                continue
            latitude, longitude = _feature_point(geometry)
            external_id, label = _feature_label(layer_id, attrs)
            was_inserted = add_infrastructure_record(
                conn,
                source_name=MCGM_SOURCE_NAME,
                source_url=f"{MCGM_MAPSERVER_URL}/{layer_id}",
                source_layer_id=layer_id,
                source_layer_name=metadata.get("name"),
                source_object_id=str(object_id),
                record_type=_layer_record_type(layer_id),
                external_id=external_id,
                label=label,
                attributes=attrs,
                geometry=geometry,
                geometry_type=metadata.get("geometryType"),
                latitude=latitude,
                longitude=longitude,
                import_date=retrieved_at,
                source_retrieved_at=retrieved_at,
            )
            if was_inserted:
                inserted += 1
            else:
                duplicates += 1

    return ImportSummary(
        source_name=MCGM_SOURCE_NAME,
        retrieved_at=retrieved_at,
        layers=layers,
        inserted=inserted,
        duplicates=duplicates,
        requested=requested,
    )
