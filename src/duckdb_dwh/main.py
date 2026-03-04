from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

from duckdb_dwh.extractors import FlexeraApiExtractor, ServiceNowCsvExtractor


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run extractor jobs into DuckDB")
    subparsers = parser.add_subparsers(dest="extractor", required=True)

    sn_parser = subparsers.add_parser("servicenow-csv", help="Load ServiceNow CMDB CSV export")
    sn_parser.add_argument("--input", required=True, type=Path, help="Path to input CSV")
    sn_parser.add_argument("--db", required=True, type=Path, help="Path to DuckDB database")

    flex_parser = subparsers.add_parser("flexera-api", help="Load Flexera API endpoint into raw JSON table")
    flex_parser.add_argument("--base-url", required=True, help="Flexera API base URL")
    flex_parser.add_argument("--endpoint", required=True, help="Endpoint path, e.g. /api/inventory/devices")
    flex_parser.add_argument("--db", required=True, type=Path, help="Path to DuckDB database")
    flex_parser.add_argument(
        "--token-env",
        default="FLEXERA_API_TOKEN",
        help="Environment variable name that stores API bearer token",
    )
    flex_parser.add_argument("--target-table", default="raw_flexera_api", help="Destination raw table")
    flex_parser.add_argument("--page-size", type=int, default=200, help="Pagination page size")
    flex_parser.add_argument("--max-pages", type=int, default=50, help="Maximum pages per run")
    flex_parser.add_argument(
        "--query",
        default=None,
        help="Optional raw query string (overrides default limit/offset query), e.g. filter=x&limit=100",
    )

    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    if args.extractor == "servicenow-csv":
        extractor = ServiceNowCsvExtractor(input_csv=args.input)
        result = extractor.run(db_path=args.db)
        print(json.dumps(result, indent=2))
        return

    if args.extractor == "flexera-api":
        token = os.getenv(args.token_env)
        if not token:
            parser.error(f"Environment variable '{args.token_env}' is not set.")

        extractor = FlexeraApiExtractor(
            base_url=args.base_url,
            endpoint=args.endpoint,
            token=token,
            target_table=args.target_table,
            page_size=args.page_size,
            max_pages=args.max_pages,
            query=args.query,
        )
        result = extractor.run(db_path=args.db)
        print(json.dumps(result, indent=2))
        return

    parser.error(f"Unknown extractor: {args.extractor}")


if __name__ == "__main__":
    main()
