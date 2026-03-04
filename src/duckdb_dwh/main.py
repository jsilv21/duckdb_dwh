from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

from duckdb_dwh.extractors import FlexeraRestReportExporter, ServiceNowCsvExtractor


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run extraction jobs")
    subparsers = parser.add_subparsers(dest="extractor", required=True)

    sn_parser = subparsers.add_parser("servicenow-csv", help="Load ServiceNow CMDB CSV export")
    sn_parser.add_argument("--input", required=True, type=Path, help="Path to input CSV")
    sn_parser.add_argument("--db", required=True, type=Path, help="Path to DuckDB database")

    flex_parser = subparsers.add_parser(
        "flexera-rest-report-export",
        help="Trigger Flexera REST report export and download the output file",
    )
    flex_parser.add_argument("--base-url", required=True, help="Flexera API base URL")
    flex_parser.add_argument("--org-id", required=True, help="Flexera organization ID")
    flex_parser.add_argument("--report-id", required=True, help="Flexera report ID to export")
    flex_parser.add_argument("--out-dir", required=True, type=Path, help="Output root directory for raw files")
    flex_parser.add_argument(
        "--token-env",
        default="FLEXERA_API_TOKEN",
        help="Environment variable name that stores API bearer token",
    )
    flex_parser.add_argument(
        "--trigger-path-template",
        default="/fnms/v1/orgs/{org_id}/reports/{report_id}/export",
        help="Trigger endpoint template with {org_id} and {report_id}",
    )
    flex_parser.add_argument(
        "--status-path-template",
        default="/fnms/v1/orgs/{org_id}/reports/{report_id}/exports/{export_id}",
        help="Status endpoint template with {org_id}, {report_id}, and {export_id}",
    )
    flex_parser.add_argument("--poll-interval-seconds", type=int, default=10, help="Seconds between status polls")
    flex_parser.add_argument("--max-polls", type=int, default=60, help="Maximum status polls before timeout")
    flex_parser.add_argument(
        "--trigger-body-json",
        default=None,
        help='Optional JSON body for trigger request, e.g. \'{"format":"csv"}\'',
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

    if args.extractor == "flexera-rest-report-export":
        token = os.getenv(args.token_env)
        if not token:
            parser.error(f"Environment variable '{args.token_env}' is not set.")

        trigger_body = {}
        if args.trigger_body_json:
            try:
                parsed = json.loads(args.trigger_body_json)
            except json.JSONDecodeError as exc:
                parser.error(f"Invalid --trigger-body-json: {exc}")
            if not isinstance(parsed, dict):
                parser.error("--trigger-body-json must be a JSON object")
            trigger_body = parsed

        extractor = FlexeraRestReportExporter(
            base_url=args.base_url,
            org_id=args.org_id,
            report_id=args.report_id,
            token=token,
            output_dir=args.out_dir,
            trigger_path_template=args.trigger_path_template,
            status_path_template=args.status_path_template,
            trigger_body=trigger_body,
            poll_interval_seconds=args.poll_interval_seconds,
            max_polls=args.max_polls,
        )
        result = extractor.run()
        print(json.dumps(result, indent=2))
        return

    parser.error(f"Unknown extractor: {args.extractor}")


if __name__ == "__main__":
    main()
