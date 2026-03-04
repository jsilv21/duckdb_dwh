from __future__ import annotations

from pathlib import Path

import duckdb

from duckdb_dwh.extractors.base import BaseExtractor, ExtractContext


class ServiceNowCsvExtractor(BaseExtractor):
    source_system = "servicenow"
    extract_name = "servicenow_cmdb_csv"
    target_table = "raw_servicenow_ci"

    def __init__(self, input_csv: Path) -> None:
        self.input_csv = input_csv

    def extract(self, context: ExtractContext) -> int:
        if not self.input_csv.exists():
            raise FileNotFoundError(f"Input CSV not found: {self.input_csv}")

        with duckdb.connect(str(context.db_path)) as conn:
            conn.execute(
                f"""
                CREATE TABLE IF NOT EXISTS {self.target_table} AS
                SELECT
                    *,
                    CAST(NULL AS VARCHAR) AS run_id,
                    CAST(NULL AS VARCHAR) AS extract_ts_utc,
                    CAST(NULL AS VARCHAR) AS source_system,
                    CAST(NULL AS VARCHAR) AS extract_name
                FROM read_csv_auto(?)
                WHERE 1 = 0
                """,
                [str(self.input_csv)],
            )

            conn.execute(
                f"""
                INSERT INTO {self.target_table}
                SELECT
                    csv_data.*,
                    ? AS run_id,
                    ? AS extract_ts_utc,
                    ? AS source_system,
                    ? AS extract_name
                FROM read_csv_auto(?) AS csv_data
                """,
                [
                    context.run_id,
                    context.extract_ts_utc,
                    self.source_system,
                    self.extract_name,
                    str(self.input_csv),
                ],
            )

            row_count = conn.execute("SELECT COUNT(*) FROM read_csv_auto(?)", [str(self.input_csv)]).fetchone()[0]

        return int(row_count)
