# Requirements

## Objective

Build a data integration framework that extracts from multiple enterprise sources and normalizes into a single warehouse (DuckDB).

Primary goal: close reporting and relationship gaps that do not natively exist in ServiceNow or Flexera.

## Scope (Phase 1)

1. Build repeatable extract jobs for each source.
2. Land raw snapshots in a consistent format.
3. Normalize key entities into curated warehouse tables.
4. Support cross-source mapping (Flexera + ServiceNow) for reporting use cases.

## Data Sources

- Flexera ITAM API: https://developer.flexera.com/docs/api/fnms/v1
- Flexera GraphQL (TI Platform): https://developer.flexera.com/docs/page/datasets-graphql
- ServiceNow CMDB:
  - Preferred: API extraction
  - Fallback: manual CSV report dumps

## Platform and Runtime

- Language: Python
- Warehouse: DuckDB
- Environment management: `uv`
- Development platform: macOS (MacBook Pro)
- Runtime target: Windows Server

### Cross-Platform Requirement (Important)

Implementation must be OS-agnostic:

- Use `pathlib` and avoid hardcoded path separators.
- Avoid shell-specific logic where possible.
- Store configuration in files/env vars, not absolute local paths.
- Validate jobs locally on macOS and in a Windows-compatible run mode.

## Extraction Framework Requirements

Each extractor should follow the same template:

1. `extract`: pull source data incrementally or as snapshot.
2. `validate`: schema/type and required-field checks.
3. `stage_raw`: write immutable raw snapshot with load metadata.
4. `normalize`: map to canonical model/table shapes.
5. `load`: upsert/append into DuckDB target tables.
6. `audit`: log run status, row counts, start/end time, and errors.

Minimum metadata for every load:

- `source_system`
- `extract_name`
- `extract_ts_utc`
- `run_id`
- `record_hash` (or equivalent dedupe key)

## Initial Data Model Targets

### Flexera

- License snapshots over time
- Device inventory snapshots

### ServiceNow

- CI inventory
- CI to App Service relationships

### Cross-Source Blends

- Flexera license cost mapped to ServiceNow App Service and/or CI
- Additional mappings to be added as canonical keys are defined

## Non-Functional Requirements

- Idempotent loads for reruns
- Basic data quality checks (null/key uniqueness/reference validity)
- Config-driven endpoints/queries
- Structured logging for troubleshooting
- Clear failure behavior (partial vs fail-fast per extract)

## Future Phases

- dbt for transformations, lineage, and testing
- Orchestration/scheduling
- Open-source dashboard layer for curated reporting

## Deliverables (Current Template Project)

1. Reusable extractor template (base class + config pattern)
2. Source-specific implementations (Flexera ITAM, Flexera GraphQL, ServiceNow)
3. Canonical staging/curated DuckDB table definitions
4. Example end-to-end run with sample output and run logs
