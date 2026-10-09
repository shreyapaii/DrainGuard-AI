# DrainGuard AI by PrimeOps

A civic-tech prototype for drain and street-litter inspections, built for the AI First
Product Builder Hackathon 2026 (College division, Track 04: Drain & Infrastructure Maintenance).

## What it does

- **Operations overview:** shows registered drains, inspection count, open maintenance tasks,
  and High-priority findings from genuine user-entered inspection records only.
- **Public infrastructure:** imports and maps real public stormwater infrastructure from the
  Mumbai MCGM/BMC ArcGIS REST service when coordinates or geometries are provided by the source.
- **New inspection:** records field observations and optional model-generated detections. Model
  output is saved separately and does not determine blockage or maintenance priority.
- **Maintenance queue:** filters, searches, updates status, and exports user-entered inspection
  records only.
- **Data sources:** lists provenance, retrieval dates, source URLs, source status, TACO dataset
  findings, data.gov.in investigation notes, and saved model inference metadata.

The default operational dashboard contains **zero fictional records**. Public infrastructure
records are reference assets and never become inspections, maintenance tasks, blocked drains, or
flood-risk predictions.

## Current bundled database state

`data/drainguard.db` has been migrated and cleaned:

- User-entered inspections: `0`
- Fictional demo/sample inspections: `0`
- Imported public infrastructure: `100` MCGM Storm Water Drains and `100` MCGM Storm Water
  Manholes, all stored in `infrastructure_records`
- Saved model inferences: `0`

Backups created before deleting the previous fictional demo rows are in `data/backups/`.

## Project structure

```text
DrainGuard AI/
├── app.py                         Streamlit web app
├── drainguard/
│   ├── analytics.py               Dashboard calculations
│   ├── db.py                      SQLite schema, migrations, provenance storage
│   ├── public_data.py             MCGM import and source metadata helpers
│   ├── scoring.py                 Transparent priority scoring
│   ├── ui.py                      Ivory/forest-green visual system
│   └── vision.py                  Optional COCO detector wrapper
├── tools/
│   ├── import_mcgmgis.py          Explicit public GIS import script
│   └── migrate_real_data.py       Safe backup, demo removal, optional reset
├── tests/                         Automated tests
├── data/
│   ├── drainguard.db              Local SQLite database
│   └── backups/                   Migration backups
├── DATA_SOURCES.md                Source investigation and provenance notes
├── MIGRATION_AND_RESET.md         Safe database migration/reset procedure
├── TEST_REPORT.md                 Honest verification report
├── AI_USAGE_DISCLOSURE.md
├── LICENSES_AND_ATTRIBUTIONS.md
├── requirements.txt
├── requirements-dev.txt
└── requirements-ai.txt
```

## Requirements

Use **Python 3.12** for the whole project. It is the safest version for the optional AI packages.

- Python 3.13 works for the core app and tests.
- Python 3.14 works for the core app and tests, but the optional AI stack may not have matching
  wheels.
- The optional AI packages are large and are not required for the core app.

Check installed Python versions:

```powershell
py -0
```

## Setup and run

```powershell
cd "D:\PROJECTS\DrainGuard AI"

# Only if activation is blocked, run once:
Set-ExecutionPolicy -Scope CurrentUser RemoteSigned

py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt

streamlit run app.py
```

Open http://localhost:8501.

## Import real MCGM public infrastructure

The app already includes a small imported batch. To refresh or import more:

```powershell
python tools\import_mcgmgis.py --limit-per-layer 100
```

By default this imports both verified stormwater sublayers:

- Layer `7`: `Storm Water Drains`, `esriGeometryPolyline`
- Layer `6`: `Storm Water Manholes`, `esriGeometryPoint`

Duplicate prevention is enforced by a uniqueness constraint on source name, layer ID, object ID,
and record type. Re-running the import skips previously imported public records.

## Safe migration or reset

Dry run:

```powershell
python tools\migrate_real_data.py
```

Apply demo/sample removal after creating a database backup and user-inspection CSV backup:

```powershell
python tools\migrate_real_data.py --apply
```

Explicit reset of user inspections, after backup:

```powershell
python tools\migrate_real_data.py --apply --reset-inspections
```

See `MIGRATION_AND_RESET.md` for details.

## Testing

```powershell
pip install -r requirements-dev.txt
python -m pytest -q
```

Latest local result: `44 passed`.

## Optional AI image detection

```powershell
pip install -r requirements-ai.txt
```

The runtime detector is a COCO-pretrained torchvision Faster R-CNN MobileNetV3 model. It performs
real inference when installed, but it is a general object detector. It is not trained on drain
blockage data and is not treated as proof that a drain is blocked.

TACO was investigated as a real litter dataset. It is CC BY 4.0 on Zenodo, but no TACO images or
annotations are bundled, and the current detector has not been trained or fine-tuned on TACO.

## Known limitations

- The MCGM/BMC public GIS source covers Mumbai stormwater infrastructure. It is not Belagavi data.
- Public infrastructure existence is not evidence of obstruction, flood risk, maintenance status,
  or inspection status.
- SQLite is suitable for a local prototype, not concurrent municipal operations.
- SQLite on Streamlit Community Cloud is not durable across restarts or redeploys.
- The priority score is a transparent rule-based score from recorded observations, not a calibrated
  flood prediction.
- data.gov.in was investigated, but no suitable official drainage geometry dataset was imported.

## Pinned versions

| Package | Version | Notes |
|---|---:|---|
| streamlit | 1.50.0 | Core UI |
| pandas | 2.3.3 | Tables and data frames |
| plotly | 6.3.0 | Charts |
| pillow | 11.3.0 | Image loading |
| pytest | 8.3.3 | Dev only |
| torch | 2.8.0 | Optional AI only |
| torchvision | 0.23.0 | Optional AI only |
