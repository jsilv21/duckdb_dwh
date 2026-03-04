from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any
from urllib import parse, request

import duckdb

from duckdb_dwh.extractors.base import BaseExtractor, ExtractContext


class FlexeraApiExtractor(BaseExtractor):
    source_system = "flexera"
    extract_name = "flexera_api"

    def __init__(
        self,
        base_url: str,
        endpoint: str,
        token: str,
        target_table: str = "raw_flexera_api",
        page_size: int = 200,
        max_pages: int = 50,
        query: str | None = None,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.endpoint = endpoint.lstrip("/")
        self.token = token
        if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", target_table):
            raise ValueError(f"Invalid table name: {target_table}")
        self.target_table = target_table
        self.page_size = page_size
        self.max_pages = max_pages
        self.query = query

    def extract(self, context: ExtractContext) -> int:
        self._ensure_target_table(context.db_path)

        total_rows = 0
        next_url = self._build_initial_url()

        for page_number in range(1, self.max_pages + 1):
            payload = self._get_json(next_url)
            records = self._extract_records(payload)
            rows = self._build_rows(records, context, page_number)

            if rows:
                self._insert_rows(context.db_path, rows)
                total_rows += len(rows)

            discovered_next = self._next_url(payload)
            if discovered_next:
                next_url = parse.urljoin(f"{self.base_url}/", discovered_next)
                continue

            if len(records) < self.page_size:
                break

            next_url = self._offset_url(page_number * self.page_size)

        return total_rows

    def _build_initial_url(self) -> str:
        base = f"{self.base_url}/{self.endpoint}"
        if self.query:
            return f"{base}?{self.query}"
        return f"{base}?limit={self.page_size}&offset=0"

    def _offset_url(self, offset: int) -> str:
        base = f"{self.base_url}/{self.endpoint}"
        return f"{base}?limit={self.page_size}&offset={offset}"

    def _get_json(self, url: str) -> Any:
        req = request.Request(
            url,
            headers={
                "Authorization": f"Bearer {self.token}",
                "Accept": "application/json",
            },
            method="GET",
        )
        with request.urlopen(req, timeout=60) as resp:  # noqa: S310
            body = resp.read().decode("utf-8")
        return json.loads(body)

    def _extract_records(self, payload: Any) -> list[dict[str, Any]]:
        if isinstance(payload, list):
            return [r for r in payload if isinstance(r, dict)]

        if not isinstance(payload, dict):
            return []

        for key in ("items", "results", "data", "value"):
            value = payload.get(key)
            if isinstance(value, list):
                return [r for r in value if isinstance(r, dict)]

        return []

    def _next_url(self, payload: Any) -> str | None:
        if not isinstance(payload, dict):
            return None

        for key in ("next", "next_url", "nextPage", "next_page"):
            value = payload.get(key)
            if isinstance(value, str) and value:
                return value

        links = payload.get("links")
        if isinstance(links, dict):
            nxt = links.get("next")
            if isinstance(nxt, str) and nxt:
                return nxt

        return None

    def _build_rows(
        self,
        records: list[dict[str, Any]],
        context: ExtractContext,
        page_number: int,
    ) -> list[tuple[str, str, str, str, int, int, str]]:
        rows: list[tuple[str, str, str, str, int, int, str]] = []
        for index, record in enumerate(records, start=1):
            rows.append(
                (
                    context.run_id,
                    context.extract_ts_utc,
                    self.source_system,
                    self.endpoint,
                    page_number,
                    index,
                    json.dumps(record, separators=(",", ":"), sort_keys=True),
                )
            )
        return rows

    def _ensure_target_table(self, db_path: Path) -> None:
        with duckdb.connect(str(db_path)) as conn:
            conn.execute(
                f"""
                CREATE TABLE IF NOT EXISTS {self.target_table} (
                    run_id VARCHAR,
                    extract_ts_utc VARCHAR,
                    source_system VARCHAR,
                    endpoint VARCHAR,
                    page_number INTEGER,
                    record_number INTEGER,
                    payload_json VARCHAR
                )
                """
            )

    def _insert_rows(self, db_path: Path, rows: list[tuple[str, str, str, str, int, int, str]]) -> None:
        with duckdb.connect(str(db_path)) as conn:
            conn.executemany(
                f"""
                INSERT INTO {self.target_table}
                (run_id, extract_ts_utc, source_system, endpoint, page_number, record_number, payload_json)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                rows,
            )
