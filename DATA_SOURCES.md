# Data Sources and Provenance

Retrieval and verification date: **2026-10-09**.

## MCGM/BMC Stormwater GIS

- Source name stored in app: `Brihanmumbai Municipal Corporation GIS: Storm Water Drainage`
- Source URL: `https://prsrvgisapp.mcgm.gov.in/server/rest/services/mcgm/MCGMGIS_Departments_Master_All_Layers/MapServer`
- Service description returned by endpoint: `All Department GIS Layers for SAP PS GIS usage, (202001091) Added DP Ward layer`
- Copyright text returned by endpoint: `MCGM, Esri India`
- Coverage: Mumbai-area municipal GIS layers. This must not be represented as Belagavi data.
- Source extent spatial reference: EPSG:32643. Import queries request WGS84 coordinates with `outSR=4326`.
- Import timestamp in bundled database: `2026-10-09T04:38:59+00:00`

Verified stormwater group:

| Layer ID | Name | Type | Geometry | Count observed |
|---:|---|---|---|---:|
| 229 | Storm Water Drainage | Group Layer | n/a | n/a |
| 7 | Storm Water Drains | Feature Layer | `esriGeometryPolyline` | 34,711 |
| 6 | Storm Water Manholes | Feature Layer | `esriGeometryPoint` | 34,431 |

### Layer 7: Storm Water Drains

Actual fields observed:

| Field | Type | Alias |
|---|---|---|
| OBJECTID | esriFieldTypeOID | FID |
| US_NODE_ID | esriFieldTypeString | Up Stream Node Id |
| DS_NODE_ID | esriFieldTypeString | Down Stream Node Id |
| CONDUIT_LE | esriFieldTypeDouble | Conduit Length (m) |
| SHAPE_1 | esriFieldTypeString | Conduit Shape |
| CONDUIT_WI | esriFieldTypeDouble | Conduit Width (mm) |
| CONDUIT_HE | esriFieldTypeDouble | Conduit Height (mm) |
| US_INVERT | esriFieldTypeDouble | Up Stream Invert Level (mTHD) |
| DS_INVERT | esriFieldTypeDouble | Down Stream Invert Lveel (mTHD) |
| USER_TEXT2 | esriFieldTypeString | Type |
| SHAPE | esriFieldTypeGeometry | SHAPE |
| SHAPE.LEN | esriFieldTypeDouble | SHAPE.LEN |

Example queried feature shape: a polyline path with WGS84 coordinates supplied by the source. The
import stores the full geometry JSON and uses source-provided path coordinates for map display.

### Layer 6: Storm Water Manholes

Actual fields observed:

| Field | Type | Alias |
|---|---|---|
| OBJECTID | esriFieldTypeOID | FID |
| NODE_ID | esriFieldTypeString | Node Id |
| GROUND_LEV | esriFieldTypeDouble | Ground Level |
| SHAPE | esriFieldTypeGeometry | SHAPE |

Example queried feature shape: a WGS84 point with `x` longitude and `y` latitude supplied by the
source.

### App handling rules

- Public infrastructure records are stored in `infrastructure_records`, not `inspections`.
- Record types are `public_stormwater_drain` and `public_stormwater_manhole`.
- Each record stores source name, source URL, layer ID, layer name, source object ID, import date,
  source retrieval date, attributes JSON, geometry JSON, and map coordinates when present.
- Duplicate imports are prevented by `UNIQUE(source_name, source_layer_id, source_object_id, record_type)`.
- Public infrastructure does not create inspection counts, maintenance tasks, obstruction status,
  priority scores, or flood-risk predictions.

## data.gov.in

- Source investigated: `https://www.data.gov.in/`
- Status: investigated, not imported.
- The catalog page was reachable on 2026-10-09.
- API probes to `api.data.gov.in` for drainage search were refused by the remote host from this
  environment.
- No official drainage geometry dataset suitable for this app was identified during this
  implementation.
- No data.gov.in records are imported or used as fallback data.

## TACO: Trash Annotations in Context

- Zenodo URL: `https://zenodo.org/records/3587843`
- Zenodo API URL checked: `https://zenodo.org/api/records/3587843`
- DOI: `10.5281/zenodo.3587843`
- License returned by Zenodo: `cc-by-4.0`
- Download listed by Zenodo: `TACO.zip`, approximately 2.7 GB
- Annotation JSON checked from the public TACO repository:
  `https://raw.githubusercontent.com/pedropro/TACO/master/data/annotations.json`
- Observed annotation summary: 1,500 images, 4,784 annotations, 60 trash categories.

TACO is a real litter dataset and may be useful for future training or evaluation. It is not bundled
with this project, and the current runtime detector has not been trained or fine-tuned on TACO.
Litter detection is not proof of drain blockage.
