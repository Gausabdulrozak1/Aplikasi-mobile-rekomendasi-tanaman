from __future__ import annotations

import shutil
from pathlib import Path
from typing import Any

from PIL import Image, ImageOps

from ml_pipeline.src.common.config import (
    class_definitions,
    dataset_output_dir,
    dataset_reports_dir,
    dataset_review_candidates_dir,
    repo_root,
    source_definitions,
)
from ml_pipeline.src.dataset.io_utils import write_csv
from ml_pipeline.src.dataset.models import ImageRecord

CURATION_MAPPING_FIELDS = [
    "curated_file_name",
    "new_file_name",
    "review_batch",
    "curated_path",
    "original_file_name",
    "original_path",
    "class_id",
    "display_name",
    "trigger_token",
    "source_type",
    "is_local_aikmel",
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
    "width",
    "height",
    "file_size",
    "sha256",
    "perceptual_hash",
    "duplicate_group",
    "duplicate_warning",
    "technical_status",
    "manual_review_status",
    "validation_status",
    "final_status",
    "rejection_reason",
    "reviewer_notes",
    "notes",
]


def curate_dataset(
    config: dict[str, Any],
    records: list[ImageRecord],
) -> list[dict[str, object]]:
    curated_dir = dataset_review_candidates_dir(config)
    curated_dir.mkdir(parents=True, exist_ok=True)
    curated: list[dict[str, object]] = []
    counters: dict[str, int] = {}
    dataset_config = config["dataset"]
    max_per_class = _optional_positive_int(dataset_config.get("max_images_per_class"))
    max_total = _optional_positive_int(dataset_config.get("max_images_total"))
    class_limits = {
        item["id"]: _optional_positive_int(item.get("target_maximum_images"))
        for item in class_definitions(config)
    }

    selected_records: list[ImageRecord] = []
    for class_info in class_definitions(config):
        class_id = str(class_info["id"])
        class_records = [
            record for record in records if record.class_id == class_id and record.status == "valid"
        ]
        source_order = [
            str(source["type"])
            for source in source_definitions(config)
            if source["class_id"] == class_id
        ]
        grouped = {
            source_type: sorted(
                [record for record in class_records if record.source_type == source_type],
                key=lambda item: item.original_path.casefold(),
            )
            for source_type in source_order
        }
        class_limit = class_limits.get(class_id)
        limits = [limit for limit in (max_per_class, class_limit) if limit is not None]
        effective_limit = min(limits) if limits else len(class_records)
        selected_records.extend(_round_robin_sources(grouped, effective_limit))

    for record in selected_records:
        if max_total is not None and len(curated) >= max_total:
            break
        current_count = counters.get(record.class_id, 0)
        counters[record.class_id] = current_count + 1
        source = Path(record.original_path)
        class_dir = curated_dir / record.class_id
        class_dir.mkdir(parents=True, exist_ok=True)
        target_name = f"{record.class_id}_{counters[record.class_id]:04d}.jpg"
        target = class_dir / target_name

        with Image.open(source) as image:
            ImageOps.exif_transpose(image).convert("RGB").save(target, quality=95)

        curated.append(
            {
                "original_path": str(source),
                "original_file_name": record.file_name,
                "curated_path": str(target),
                "new_file_name": target_name,
                "curated_file_name": target_name,
                "review_batch": "original_350",
                "class_id": record.class_id,
                "display_name": record.display_name,
                "trigger_token": record.trigger_token,
                "source_type": record.source_type,
                "source_name": record.source_name,
                "source_identifier": record.source_identifier,
                "source_url": record.source_url,
                "license": record.license,
                "access_date": record.access_date,
                "is_local_aikmel": record.is_local_aikmel,
                "capture_date": record.capture_date,
                "location_general": record.location_general,
                "photographer": record.photographer,
                "permission_status": record.permission_status,
                "review_status": record.review_status,
                "notes": record.notes,
                "validation_status": "technical_valid_pending_manual_review",
                "technical_status": record.status,
                "manual_review_status": "pending",
                "final_status": "pending_manual_review",
                "rejection_reason": record.rejection_reason,
                "width": record.width,
                "height": record.height,
                "file_size": record.file_size,
                "sha256": record.sha256,
                "perceptual_hash": record.perceptual_hash,
                "duplicate_group": record.duplicate_group,
                "duplicate_warning": record.duplicate_warning,
            }
        )

    return curated


def _round_robin_sources(
    grouped: dict[str, list[ImageRecord]],
    limit: int,
) -> list[ImageRecord]:
    selected: list[ImageRecord] = []
    offsets = {source_type: 0 for source_type in grouped}
    while len(selected) < limit:
        added = False
        for source_type, records in grouped.items():
            offset = offsets[source_type]
            if offset >= len(records):
                continue
            selected.append(records[offset])
            offsets[source_type] += 1
            added = True
            if len(selected) >= limit:
                break
        if not added:
            break
    return selected


def write_curation_mapping(
    config: dict[str, Any],
    curated: list[dict[str, object]],
) -> str:
    path = dataset_reports_dir(config) / "curation_mapping.csv"
    return str(write_csv(path, curated, CURATION_MAPPING_FIELDS))


def reset_processed_directory(config: dict[str, Any]) -> Path:
    output_dir = dataset_output_dir(config)
    _assert_safe_processed_output(output_dir)
    if output_dir.exists():
        shutil.rmtree(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    return output_dir


def reset_review_candidates_directory(config: dict[str, Any]) -> Path:
    output_dir = dataset_review_candidates_dir(config)
    _assert_safe_review_output(output_dir)
    if output_dir.exists():
        shutil.rmtree(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    return output_dir


def _assert_safe_processed_output(output_dir: Path) -> None:
    resolved = output_dir.resolve()
    root = repo_root().resolve()
    allowed_roots = [
        (root / "ml_pipeline" / "data" / "processed").resolve(),
        (root / "artifacts").resolve(),
    ]

    filesystem_root = Path(resolved.anchor).resolve()
    if resolved == root or resolved == filesystem_root:
        raise ValueError(f"Refusing to reset broad output path: {resolved}")

    if not any(
        resolved == allowed or resolved.is_relative_to(allowed) for allowed in allowed_roots
    ):
        # Temporary directories are allowed for automated tests.
        if "pytest-" not in str(resolved) and "tmp" not in str(resolved).lower():
            raise ValueError(
                "Refusing to reset output path outside known processed/artifact directories: "
                f"{resolved}"
            )


def _assert_safe_review_output(output_dir: Path) -> None:
    resolved = output_dir.resolve()
    root = repo_root().resolve()
    expected = (root / "artifacts" / "dataset_review" / "candidates").resolve()
    if resolved == expected or resolved.is_relative_to(expected):
        return
    if "pytest-" in str(resolved) or "tmp" in str(resolved).lower():
        return
    raise ValueError(f"Refusing to reset review candidates outside safe path: {resolved}")


def _optional_positive_int(value: object) -> int | None:
    if value in (None, "", 0):
        return None
    parsed = int(value)
    if parsed <= 0:
        return None
    return parsed


def remove_curated_staging(config: dict[str, Any]) -> None:
    staging = dataset_output_dir(config) / ".curated"
    if staging.exists():
        shutil.rmtree(staging)
