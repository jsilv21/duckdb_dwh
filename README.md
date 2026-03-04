# duckdb_dwh

Minimal extractor scaffold to test end-to-end extraction into DuckDB.

## Quick start

```bash
uv sync
uv run dwh-extract servicenow-csv --input sample_data/servicenow_ci.csv --db data/warehouse.duckdb
```

## What this does

- Reads a ServiceNow-style CSV export
- Adds run metadata (`run_id`, `extract_ts_utc`, `source_system`, `extract_name`)
- Loads data into a DuckDB table: `raw_servicenow_ci`
- Writes audit rows to `etl_audit_log`
