from __future__ import annotations

from collections import defaultdict
from dataclasses import replace
from typing import Any

from ml_pipeline.src.common.config import ALLOWED_SOURCE_TYPES, class_definitions
from ml_pipeline.src.dataset.models import ImageRecord

RGB_COMPATIBLE_MODES = {"RGB", "RGBA", "L", "P"}


def validate_records(config: dict[str, Any], records: list[ImageRecord]) -> list[ImageRecord]:
    dataset = config["dataset"]
    min_width = int(dataset.get("minimum_width", 1))
    min_height = int(dataset.get("minimum_height", 1))
    selected_classes = {item["id"] for item in class_definitions(config)}
    hashes: dict[str, list[ImageRecord]] = defaultdict(list)

    for record in records:
        if record.sha256:
            hashes[record.sha256].append(record)

    duplicate_hashes = {
        digest
        for digest, duplicate_records in hashes.items()
        if digest and len(duplicate_records) > 1
    }

    validated: list[ImageRecord] = []
    seen_duplicate_hashes: set[str] = set()
    for record in records:
        status = record.status
        reason = record.rejection_reason

        if status != "invalid":
            if record.file_size <= 0:
                status, reason = "invalid", "empty_file"
            elif record.width < min_width or record.height < min_height:
                status, reason = "invalid", "resolution_too_small"
            elif record.color_mode not in RGB_COMPATIBLE_MODES:
                status, reason = "invalid", "unsupported_color_mode"
            elif selected_classes and record.class_id not in selected_classes:
                status, reason = "invalid", "unknown_class"
            elif record.source_type not in ALLOWED_SOURCE_TYPES:
                status, reason = "invalid", "unknown_source"
            elif record.source_type == "local_aikmel" and record.class_id != "padi":
                status, reason = "invalid", "local_source_not_allowed_for_class"
            elif record.is_local_aikmel != (record.source_type == "local_aikmel"):
                status, reason = "invalid", "inconsistent_local_source_flag"
            elif record.review_status.strip().casefold() in {
                "rejected",
                "ditolak",
                "not_suitable",
                "tidak_layak",
            }:
                status, reason = "invalid", "manual_review_rejected"
            elif record.sha256 in duplicate_hashes:
                if record.sha256 in seen_duplicate_hashes:
                    status, reason = "duplicate", "exact_duplicate"
                else:
                    seen_duplicate_hashes.add(record.sha256)
                    status, reason = "valid", ""
            else:
                status, reason = "valid", ""

        validated.append(
            replace(
                record,
                status=status,
                rejection_reason=reason,
            )
        )

    return validated
