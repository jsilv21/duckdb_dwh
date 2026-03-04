from __future__ import annotations

import json
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib import parse, request
from uuid import uuid4


class FlexeraRestReportExporter:
    """Trigger and download Flexera FNMS report exports (REST)."""

    source_system = "flexera"
    extract_name = "flexera_rest_report_export"

    def __init__(
        self,
        base_url: str,
        org_id: str,
        report_id: str,
        token: str,
        output_dir: Path,
        trigger_path_template: str = "/fnms/v1/orgs/{org_id}/reports/{report_id}/exports",
        status_path_template: str = "/fnms/v1/orgs/{org_id}/reports/exports/{export_id}",
        trigger_body: dict[str, Any] | None = None,
        poll_interval_seconds: int = 10,
        max_polls: int = 60,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.org_id = org_id
        self.report_id = report_id
        self.token = token
        self.output_dir = output_dir
        self.trigger_path_template = trigger_path_template
        self.status_path_template = status_path_template
        self.trigger_body = trigger_body or {}
        self.poll_interval_seconds = poll_interval_seconds
        self.max_polls = max_polls

    def run(self) -> dict[str, Any]:
        run_id = str(uuid4())
        extract_ts_utc = datetime.now(timezone.utc).isoformat()
        run_dir = self._build_run_dir(run_id)
        run_dir.mkdir(parents=True, exist_ok=True)

        trigger_url = self._build_trigger_url()
        trigger_response, trigger_headers = self._post_json(
            trigger_url, self.trigger_body
        )
        self._write_json(run_dir / "trigger_response.json", trigger_response)

        export_id = self._extract_export_id(trigger_response)
        status_url = self._extract_status_url(
            trigger_response, trigger_headers, export_id
        )
        if not status_url:
            raise RuntimeError(
                "Could not determine export status URL from trigger response."
            )

        final_status_payload: dict[str, Any] | None = None
        final_download_url: str | None = None

        for poll_number in range(1, self.max_polls + 1):
            status_payload = self._get_json(status_url)
            self._write_json(
                run_dir / f"status_poll_{poll_number:04d}.json", status_payload
            )

            if self._is_terminal_success(status_payload):
                final_status_payload = status_payload
                final_download_url = self._extract_download_url(status_payload)
                break

            if self._is_terminal_failure(status_payload):
                raise RuntimeError(f"Export failed: {json.dumps(status_payload)}")

            time.sleep(self.poll_interval_seconds)

        if final_status_payload is None:
            raise TimeoutError("Timed out waiting for report export to complete.")

        if not final_download_url:
            raise RuntimeError(
                "Export completed but download URL/path was not found in status response."
            )

        download_url = parse.urljoin(f"{self.base_url}/", final_download_url)
        downloaded_file = self._download_file(download_url, run_dir)

        manifest = {
            "run_id": run_id,
            "extract_ts_utc": extract_ts_utc,
            "source_system": self.source_system,
            "extract_name": self.extract_name,
            "base_url": self.base_url,
            "org_id": self.org_id,
            "report_id": self.report_id,
            "trigger_url": trigger_url,
            "status_url": status_url,
            "download_url": download_url,
            "poll_interval_seconds": self.poll_interval_seconds,
            "max_polls": self.max_polls,
            "run_dir": str(run_dir),
            "downloaded_file": str(downloaded_file),
        }
        self._write_json(run_dir / "manifest.json", manifest)

        return manifest

    def _build_run_dir(self, run_id: str) -> Path:
        return self.output_dir / self.extract_name / f"report_{self.report_id}" / run_id

    def _build_trigger_url(self) -> str:
        path = self.trigger_path_template.format(
            org_id=self.org_id, report_id=self.report_id
        )
        return parse.urljoin(f"{self.base_url}/", path.lstrip("/"))

    def _build_status_url(self, export_id: str) -> str:
        path = self.status_path_template.format(
            org_id=self.org_id,
            report_id=self.report_id,
            export_id=export_id,
        )
        return parse.urljoin(f"{self.base_url}/", path.lstrip("/"))

    def _post_json(
        self, url: str, payload: dict[str, Any]
    ) -> tuple[dict[str, Any], dict[str, str]]:
        req = request.Request(
            url,
            headers={
                "Authorization": f"Bearer {self.token}",
                "Accept": "application/json",
                "Content-Type": "application/json",
            },
            data=json.dumps(payload).encode("utf-8"),
            method="POST",
        )
        with request.urlopen(req, timeout=60) as resp:  # noqa: S310
            body = resp.read().decode("utf-8")
            headers = {k.lower(): v for k, v in resp.headers.items()}
        return (json.loads(body) if body else {}, headers)

    def _get_json(self, url: str) -> dict[str, Any]:
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
        return json.loads(body) if body else {}

    def _extract_export_id(self, payload: dict[str, Any]) -> str | None:
        data = self._data_node(payload)
        for key in ("exportId", "reportExportId", "id", "jobId"):
            value = data.get(key)
            if isinstance(value, (str, int)):
                return str(value)
        return None

    def _extract_status_url(
        self,
        payload: dict[str, Any],
        headers: dict[str, str],
        export_id: str | None,
    ) -> str | None:
        data = self._data_node(payload)
        for key in ("statusUrl", "status_url", "reportExportStatusUrl"):
            value = data.get(key)
            if isinstance(value, str) and value:
                return parse.urljoin(f"{self.base_url}/", value)

        location = headers.get("location")
        if location:
            return parse.urljoin(f"{self.base_url}/", location)

        if export_id:
            return self._build_status_url(export_id)

        return None

    def _extract_download_url(self, payload: dict[str, Any]) -> str | None:
        data = self._data_node(payload)
        for key in (
            "downloadUrl",
            "download_url",
            "url",
            "fileUrl",
            "path",
            "filePath",
        ):
            value = data.get(key)
            if isinstance(value, str) and value:
                return value

        links = data.get("links")
        if isinstance(links, dict):
            for key in ("download", "file", "self"):
                value = links.get(key)
                if isinstance(value, str) and value:
                    return value

        result = data.get("result")
        if isinstance(result, dict):
            return self._extract_download_url(result)

        return None

    def _is_terminal_success(self, payload: dict[str, Any]) -> bool:
        data = self._data_node(payload)
        for key in ("status", "state"):
            value = data.get(key)
            if isinstance(value, str) and value.lower() in {
                "completed",
                "complete",
                "done",
                "succeeded",
                "success",
            }:
                return True
        return False

    def _is_terminal_failure(self, payload: dict[str, Any]) -> bool:
        data = self._data_node(payload)
        for key in ("status", "state"):
            value = data.get(key)
            if isinstance(value, str) and value.lower() in {
                "failed",
                "error",
                "errored",
                "no data found",
                "cancelled",
                "canceled",
            }:
                return True
        return False

    def _data_node(self, payload: dict[str, Any]) -> dict[str, Any]:
        data = payload.get("data")
        if isinstance(data, dict):
            return data
        return payload

    def _download_file(self, url: str, run_dir: Path) -> Path:
        req = request.Request(
            url,
            headers={"Authorization": f"Bearer {self.token}"},
            method="GET",
        )
        with request.urlopen(req, timeout=300) as resp:  # noqa: S310
            disposition = resp.headers.get("Content-Disposition", "")
            filename = (
                self._filename_from_disposition(disposition)
                or Path(parse.urlparse(url).path).name
                or "report_export.bin"
            )
            output_file = run_dir / filename
            output_file.write_bytes(resp.read())

        return output_file

    def _filename_from_disposition(self, header_value: str) -> str | None:
        marker = "filename="
        if marker not in header_value:
            return None
        filename = header_value.split(marker, 1)[1].strip().strip('"')
        return filename or None

    def _write_json(self, file_path: Path, payload: dict[str, Any]) -> None:
        file_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
