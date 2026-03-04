# duckdb_dwh

Minimal extractor scaffold to test end-to-end extraction into DuckDB.

## Quick start

```bash
uv sync
uv run dwh-extract servicenow-csv --input sample_data/servicenow_ci.csv --db data/warehouse.duckdb
```

## Flexera API wireframe

Set token in env:

```bash
export FLEXERA_API_TOKEN="your-token-here"
```

Run extract:

```bash
uv run dwh-extract flexera-api \
  --base-url https://your-flexera-host \
  --endpoint /api/path/to/resource \
  --db data/warehouse.duckdb \
  --page-size 200 \
  --max-pages 10
```

This lands records in `raw_flexera_api` with one JSON payload per row.

## What this does

- Reads a ServiceNow-style CSV export
- Adds run metadata (`run_id`, `extract_ts_utc`, `source_system`, `extract_name`)
- Loads data into a DuckDB table: `raw_servicenow_ci`
- Writes audit rows to `etl_audit_log`
- Includes a Flexera API extractor template that lands raw JSON rows in `raw_flexera_api`
