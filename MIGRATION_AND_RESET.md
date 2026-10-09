# Migration and Reset Procedure

This project previously seeded five fictional demo inspection rows. The updated app no longer seeds
or displays fictional records by default.

## Database inspection before migration

Before deletion, the existing checked-in database contained:

- Tables: `inspections`, `sqlite_sequence`
- Total inspection rows: `5`
- Rows marked `is_demo = 1`: `5`
- User-entered rows: `0`

## Backups created before deletion

Backups were created before removing anything:

- `data/backups/drainguard_backup_20261009_095656.db`
- `data/backups/user_inspections_backup_20261009_095656.csv`
- `data/backups/drainguard_backup_20261009_100831.db`
- `data/backups/user_inspections_backup_20261009_100831.csv`

The CSV backup contains headers and zero user-entered inspection rows, matching the audit above.

## Safe migration script

Dry run:

```powershell
python tools\migrate_real_data.py
```

Apply cleanup:

```powershell
python tools\migrate_real_data.py --apply
```

What `--apply` does:

1. Opens the SQLite database.
2. Creates a full database copy in `data/backups/`.
3. Exports user-entered inspection rows to CSV in `data/backups/`.
4. Deletes only rows where `is_demo = 1`.

## Explicit reset procedure

To reset user-entered inspections too, use the explicit flag:

```powershell
python tools\migrate_real_data.py --apply --reset-inspections
```

This still creates a database backup and a user-inspection CSV backup before deletion.

## Current post-migration state

After migration and MCGM import:

- `inspections`: 0 rows
- Fictional demo/sample rows: 0
- `infrastructure_records`: 200 rows
- `model_inferences`: 0 rows
- Public MCGM records stay separate from inspections.

## Restore note

To restore an old database manually, stop Streamlit, copy the desired backup over
`data/drainguard.db`, then restart the app. Inspect the restored database before using it
operationally, because older backups may contain fictional demo rows.
