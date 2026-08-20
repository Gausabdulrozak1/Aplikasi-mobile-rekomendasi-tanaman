from __future__ import annotations

import csv
from dataclasses import replace
from pathlib import Path
from typing import Any

from ml_pipeline.src.common.config import (
    ALLOWED_SOURCE_TYPES,
    dataset_reports_dir,
    dataset_source_manifest_path,
    repo_root,
    resolve_path,
)
from ml_pipeline.src.dataset.io_utils import write_csv
from ml_pipeline.src.dataset.models import ImageRecord

PROVENANCE_FIELDS = [
    "original_file_name",
    "original_path",
    "class_id",
    "source_type",
    "source_name",
    "source_identifier",
    "source_url",
    "license",
    "access_date",
    "is_local_aikmel",
    "capture_date",
    "location_general",
    "photographer",
    "permission_status",
    "review_status",
    "notes",
]

DESCRIPTIVE_FIELDS = [
    "source_name",
    "source_identifier",
    "source_url",
    "license",
    "access_date",
    "capture_date",
    "location_general",
    "photographer",
    "permission_status",
    "review_status",
    "notes",
]

PROVENANCE_WARNING_FIELDS = [
    "original_path",
    "class_id",
    "source_type",
    "warning_code",
    "missing_fields",
    "message",
]


def _portable_path(path: str | Path) -> str:
    resolved = Path(path).resolve()
    root = repo_root().resolve()
    if resolved.is_relative_to(root):
        return resolved.relative_to(root).as_posix()
    return str(resolved)


def _path_key(value: str | Path) -> str:
    path = Path(value)
    if not path.is_absolute():
        path = resolve_path(path)
    return str(path.resolve()).casefold()


def _parse_bool(value: object) -> bool:
    return str(value).strip().casefold() in {"1", "true", "yes", "ya"}


def read_source_manifest(config: dict[str, Any]) -> list[dict[str, str]]:
    path = dataset_source_manifest_path(config)
    if path is None or not path.exists():
        return []
    with path.open(newline="", encoding="utf-8-sig") as handle:
        return [dict(row) for row in csv.DictReader(handle)]


def manifest_index(config: dict[str, Any]) -> dict[str, dict[str, str]]:
    result: dict[str, dict[str, str]] = {}
    for row in read_source_manifest(config):
        original_path = row.get("original_path", "").strip()
        if original_path:
            result[_path_key(original_path)] = row
    return result


def apply_manifest_provenance(
    record: ImageRecord,
    rows_by_path: dict[str, dict[str, str]],
) -> ImageRecord:
    row = rows_by_path.get(_path_key(record.original_path), {})
    values = {field: str(row.get(field, "")).strip() for field in DESCRIPTIVE_FIELDS}
    return replace(record, **values)


def sync_source_manifest(
    config: dict[str, Any],
    records: list[ImageRecord],
) -> str:
    path = dataset_source_manifest_path(config)
    if path is None:
        return ""

    existing_rows = read_source_manifest(config)
    existing = {
        _path_key(row["original_path"]): row
        for row in existing_rows
        if row.get("original_path", "").strip()
    }
    current_keys: set[str] = set()
    rows: list[dict[str, object]] = []

    for record in sorted(records, key=lambda item: item.original_path.casefold()):
        key = _path_key(record.original_path)
        current_keys.add(key)
        prior = existing.get(key, {})
        row: dict[str, object] = {
            "original_path": _portable_path(record.original_path),
            "original_file_name": record.original_file_name or record.file_name,
            "class_id": record.class_id,
            "source_type": record.source_type,
            "source_name": record.source_name or prior.get("source_name", ""),
            "source_identifier": record.source_identifier or prior.get("source_identifier", ""),
            "source_url": record.source_url or prior.get("source_url", ""),
            "license": record.license or prior.get("license", ""),
            "access_date": record.access_date or prior.get("access_date", ""),
            "is_local_aikmel": str(record.is_local_aikmel).lower(),
            "capture_date": record.capture_date or prior.get("capture_date", ""),
            "location_general": record.location_general or prior.get("location_general", ""),
            "photographer": record.photographer or prior.get("photographer", ""),
            "permission_status": record.permission_status or prior.get("permission_status", ""),
            "review_status": record.review_status or prior.get("review_status", ""),
            "notes": record.notes or prior.get("notes", ""),
        }
        rows.append(row)

    # Keep unmatched rows so a rerun never erases provenance entered by a human.
    for key, row in existing.items():
        if key not in current_keys:
            rows.append({field: row.get(field, "") for field in PROVENANCE_FIELDS})

    rows.sort(key=lambda row: str(row.get("original_path", "")).casefold())
    write_csv(path, rows, PROVENANCE_FIELDS)
    return str(path)


def provenance_warnings(records: list[ImageRecord]) -> list[dict[str, str]]:
    warnings: list[dict[str, str]] = []
    for record in records:
        if record.class_id == "unknown" or record.source_type not in ALLOWED_SOURCE_TYPES:
            warnings.append(
                {
                    "original_path": record.original_path,
                    "class_id": record.class_id,
                    "source_type": record.source_type,
                    "warning_code": "unknown_source_or_class",
                    "missing_fields": "class_id,source_type",
                    "message": "Image is outside the configured class/source directories.",
                }
            )
            continue

        if record.source_type == "local_aikmel" and record.class_id != "padi":
            warnings.append(
                {
                    "original_path": record.original_path,
                    "class_id": record.class_id,
                    "source_type": record.source_type,
                    "warning_code": "invalid_local_source_policy",
                    "missing_fields": "",
                    "message": "local_aikmel is only permitted for padi.",
                }
            )

        required = [
            "source_name",
            "source_identifier",
            "source_url",
            "license",
            "access_date",
        ]
        if record.source_type == "local_aikmel":
            required = [
                "source_name",
                "source_identifier",
                "license",
                "capture_date",
                "location_general",
                "photographer",
                "permission_status",
            ]
        missing = [field for field in required if not str(getattr(record, field)).strip()]
        if missing:
            warnings.append(
                {
                    "original_path": record.original_path,
                    "class_id": record.class_id,
                    "source_type": record.source_type,
                    "warning_code": "incomplete_provenance",
                    "missing_fields": ",".join(missing),
                    "message": "Provenance must be completed before final dataset approval.",
                }
            )

        if not record.review_status.strip():
            warnings.append(
                {
                    "original_path": record.original_path,
                    "class_id": record.class_id,
                    "source_type": record.source_type,
                    "warning_code": "manual_review_pending",
                    "missing_fields": "review_status",
                    "message": "Human suitability review has not been recorded.",
                }
            )
    return warnings


def write_provenance_warnings(
    config: dict[str, Any],
    records: list[ImageRecord],
) -> str:
    path = dataset_reports_dir(config) / "provenance_warnings.csv"
    return str(
        write_csv(
            path,
            provenance_warnings(records),
            PROVENANCE_WARNING_FIELDS,
        )
    )
