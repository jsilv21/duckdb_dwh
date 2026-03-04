from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4

import duckdb


@dataclass
class ExtractContext:
    db_path: Path
    run_id: str
    extract_ts_utc: str


class BaseExtractor(ABC):
    source_system: str
    extract_name: str
    target_table: str

    def run(self, db_path: Path) -> dict[str, Any]:
        db_path.parent.mkdir(parents=True, exist_ok=True)
        context = ExtractContext(
            db_path=db_path,
            run_id=str(uuid4()),
            extract_ts_utc=datetime.now(timezone.utc).isoformat(),
        )

        self._ensure_audit_table(context.db_path)

        started = datetime.now(timezone.utc)
        try:
            row_count = self.extract(context)
            status = "success"
            error_message = None
        except Exception as exc:  # noqa: BLE001
            row_count = 0
            status = "failed"
            error_message = str(exc)
        ended = datetime.now(timezone.utc)

        self._write_audit_log(
            db_path=context.db_path,
            run_id=context.run_id,
            started_at=started.isoformat(),
            ended_at=ended.isoformat(),
            status=status,
            row_count=row_count,
            error_message=error_message,
        )

        if status == "failed":
            raise RuntimeError(f"{self.extract_name} failed: {error_message}")

        return {
            "run_id": context.run_id,
            "extract_ts_utc": context.extract_ts_utc,
            "status": status,
            "row_count": row_count,
            "target_table": self.target_table,
            "db_path": str(context.db_path),
        }

    @abstractmethod
    def extract(self, context: ExtractContext) -> int:
        """Execute extraction and return number of rows loaded."""

    def _ensure_audit_table(self, db_path: Path) -> None:
        with duckdb.connect(str(db_path)) as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS etl_audit_log (
                    run_id VARCHAR,
                    source_system VARCHAR,
                    extract_name VARCHAR,
                    started_at_utc VARCHAR,
                    ended_at_utc VARCHAR,
                    status VARCHAR,
                    row_count BIGINT,
                    error_message VARCHAR
                )
                """
            )

    def _write_audit_log(
        self,
        db_path: Path,
        run_id: str,
        started_at: str,
        ended_at: str,
        status: str,
        row_count: int,
        error_message: str | None,
    ) -> None:
        with duckdb.connect(str(db_path)) as conn:
            conn.execute(
                """
                INSERT INTO etl_audit_log
                (run_id, source_system, extract_name, started_at_utc, ended_at_utc, status, row_count, error_message)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                [
                    run_id,
                    self.source_system,
                    self.extract_name,
                    started_at,
                    ended_at,
                    status,
                    row_count,
                    error_message,
                ],
            )
