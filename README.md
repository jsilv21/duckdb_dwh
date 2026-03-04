# duckdb_dwh

Minimal extractor scaffold to test end-to-end extraction into DuckDB.

## Quick start

```bash
uv sync
uv run dwh-extract servicenow-csv --input sample_data/servicenow_ci.csv --db data/warehouse.duckdb
```

## Flexera REST report export wireframe

Set token in env:

```bash
export FLEXERA_API_TOKEN="your-token-here"
```

Run extract:

```bash
uv run dwh-extract flexera-rest-report-export \
  --base-url https://your-flexera-host \
  --org-id your-org-id \
  --report-id 12345 \
  --out-dir data/raw \
  --poll-interval-seconds 10 \
  --max-polls 60
```

This workflow does:

1. Trigger report export by `report_id`
2. Poll report export status endpoint until completion
3. Download exported file using the status response download path/url
4. Save raw API responses + file in run folder

Raw output example:

- `data/raw/flexera_rest_report_export/report_<report_id>/<run_id>/trigger_response.json`
- `data/raw/flexera_rest_report_export/report_<report_id>/<run_id>/status_poll_0001.json`
- `data/raw/flexera_rest_report_export/report_<report_id>/<run_id>/<downloaded_report_file>`
- `data/raw/flexera_rest_report_export/report_<report_id>/<run_id>/manifest.json`

## What this does

- Reads a ServiceNow-style CSV export
- Adds run metadata (`run_id`, `extract_ts_utc`, `source_system`, `extract_name`)
- Loads data into a DuckDB table: `raw_servicenow_ci`
- Writes audit rows to `etl_audit_log`
- Includes a Flexera REST report export extractor template (trigger, status, download)
