# Test Report

Date: **2026-10-09**

## Automated tests

Command used:

```powershell
$env:PYTHONPATH = '.codex_test_deps;.'
C:\Users\Asus\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe -m pytest -q
```

Result:

```text
44 passed in 1.42s
```

Coverage added or verified:

- Empty operational dashboard renders with zero inspection metrics.
- Public infrastructure page renders without importing unless the user explicitly submits import.
- Maintenance queue empty state renders.
- Data sources page renders.
- SQLite migration adds provenance fields.
- Fictional sample rows are excluded by default and can be deleted safely.
- Public infrastructure records are stored separately from inspections.
- Duplicate public imports are skipped.
- Data-source metadata is upserted.
- Model inferences are saved separately from inspection priority.
- Coordinate validation prevents partial or out-of-range user coordinates.
- Vision summaries do not claim that no detection means a clear drain.

## Real source import test

Command used:

```powershell
python tools\import_mcgmgis.py --limit-per-layer 100
```

Result:

```text
Requested features: 200
Inserted: 200
Duplicates skipped: 0
Layer 7 Storm Water Drains: 100 fetched from 34711 available
Layer 6 Storm Water Manholes: 100 fetched from 34431 available
```

Duplicate verification command repeated:

```powershell
python tools\import_mcgmgis.py --limit-per-layer 100
```

Result:

```text
Requested features: 200
Inserted: 0
Duplicates skipped: 200
```

## Database persistence check

Post-migration database check:

```text
inspections 0
demo 0
public_stormwater_drain 100
public_stormwater_manhole 100
model_inferences 0
```

This confirms public infrastructure is persisted separately from user inspections.

## Runtime smoke test

The Streamlit app was started locally and returned HTTP 200 at:

```text
http://127.0.0.1:8501
```

## AI inference workflow

Unit tests verify model-output serialization, detector status handling, and limitation text.
Full end-to-end torch inference was not run in this environment because the optional AI packages
were not installed. The UI reports that honestly and the rest of the app works without them.

## Known unverified items

- No field inspection was performed.
- No municipal partnership or live sensor data exists.
- No flood-risk prediction model exists.
- No TACO-trained detector exists in this project.
- data.gov.in did not yield an imported drainage geometry dataset during this implementation.
