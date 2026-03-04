from __future__ import annotations

import argparse
import json
from pathlib import Path

from duckdb_dwh.extractors import ServiceNowCsvExtractor


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run extractor jobs into DuckDB")
    subparsers = parser.add_subparsers(dest="extractor", required=True)

    sn_parser = subparsers.add_parser("servicenow-csv", help="Load ServiceNow CMDB CSV export")
    sn_parser.add_argument("--input", required=True, type=Path, help="Path to input CSV")
    sn_parser.add_argument("--db", required=True, type=Path, help="Path to DuckDB database")

    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    if args.extractor == "servicenow-csv":
        extractor = ServiceNowCsvExtractor(input_csv=args.input)
        result = extractor.run(db_path=args.db)
        print(json.dumps(result, indent=2))
        return

    parser.error(f"Unknown extractor: {args.extractor}")


if __name__ == "__main__":
    main()
