from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from PIL import Image, UnidentifiedImageError

from ml_pipeline.src.common.config import (
    class_definitions,
    class_lookup,
    dataset_reports_dir,
    resolve_path,
    source_definitions,
)
from ml_pipeline.src.dataset.io_utils import sha256_file, write_csv, write_json
from ml_pipeline.src.dataset.models import ImageRecord
from ml_pipeline.src.dataset.provenance import apply_manifest_provenance, manifest_index


class DatasetNotAvailableError(RuntimeError):
    pass


INVENTORY_FIELDS = [
    "original_path",
    "class_id",
    "display_name",
    "trigger_token",
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
    "file_name",
    "original_file_name",
    "extension",
    "format",
    "file_format",
    "width",
    "height",
    "color_mode",
    "file_size",
    "sha256",
    "perceptual_hash",
    "status",
    "technical_status",
    "rejection_reason",
    "duplicate_group",
    "duplicate_warning",
    "exif_orientation",
    "exif_orientation_status",
]


def _configured_sources(config: dict[str, Any]) -> list[dict[str, object]]:
    configured: list[dict[str, object]] = []
    for item in source_definitions(config):
        configured.append(
            {
                **item,
                "path": resolve_path(str(item["directory"])).resolve(),
                "required": bool(item.get("required", True)),
            }
        )
    if not configured:
        raise ValueError("No raw dataset source directories are configured")
    return configured


def _scan_root(sources: list[dict[str, object]]) -> Path | None:
    paths = [Path(item["path"]) for item in sources]
    common = Path(os.path.commonpath([str(path) for path in paths])).resolve()
    relative_first_parts = {path.relative_to(common).parts[0] for path in paths if path != common}
    configured_classes = {str(item["class_id"]) for item in sources}
    if relative_first_parts and relative_first_parts <= configured_classes:
        return common
    return None


def _infer_source(
    path: Path,
    sources: list[dict[str, object]],
) -> tuple[str, str]:
    matches = [item for item in sources if path.is_relative_to(Path(item["path"]))]
    if not matches:
        return "unknown", ""
    selected = max(matches, key=lambda item: len(Path(item["path"]).parts))
    return str(selected["class_id"]), str(selected["type"])


def build_inventory(config: dict[str, Any], source_dir: Path | None = None) -> list[ImageRecord]:
    dataset = config["dataset"]
    definitions = class_definitions(config)
    definitions_by_id = class_lookup(config)
    allowed_extensions = {ext.lower() for ext in dataset.get("allowed_extensions", [])}
    allowed_formats = {
        str(value).upper()
        for value in dataset.get("allowed_image_formats", ["JPEG", "PNG", "WEBP"])
    }
    active_ids = {item["id"] for item in definitions}

    if source_dir is not None:
        sources = [
            {
                "class_id": item["id"],
                "type": "public",
                "path": (source_dir / item["id"]).resolve(),
                "required": True,
            }
            for item in definitions
        ]
        if len(definitions) == 1 and not Path(sources[0]["path"]).exists():
            sources[0]["path"] = source_dir.resolve()
        roots = [source_dir]
    else:
        sources = _configured_sources(config)
        common_root = _scan_root(sources)
        scan_unknown = len(active_ids) == len(class_lookup(config))
        roots = (
            [common_root]
            if common_root and scan_unknown
            else [Path(item["path"]) for item in sources]
        )

    required_missing = [
        Path(item["path"])
        for item in sources
        if item.get("required", True) and not Path(item["path"]).exists()
    ]
    if required_missing:
        expected = ", ".join(str(path) for path in required_missing)
        raise DatasetNotAvailableError(
            f"Dataset raw is not available. Expected required source directories: {expected}"
        )
    existing_roots = [root for root in roots if root.exists()]
    if not existing_roots:
        expected = ", ".join(str(item["path"]) for item in sources)
        raise DatasetNotAvailableError(
            f"Dataset raw is not available. Expected source directories: {expected}"
        )

    files = sorted(
        {
            path.resolve()
            for root in existing_roots
            for path in root.rglob("*")
            if (
                path.is_file()
                and path.name != ".gitkeep"
                and path.suffix.lower() in allowed_extensions
            )
        }
    )
    if not files:
        expected = ", ".join(str(item["path"]) for item in sources)
        raise DatasetNotAvailableError(f"No dataset images were found. Add images to: {expected}")

    records: list[ImageRecord] = []
    provenance_by_path = manifest_index(config)

    for path in files:
        extension = path.suffix.lower()
        class_id, source_type = _infer_source(path, sources)
        class_info = definitions_by_id.get(class_id, {})
        size_bytes = path.stat().st_size
        status = "pending"
        reason = ""
        image_format = ""
        width = 0
        height = 0
        mode = ""
        digest = ""
        exif_orientation = ""
        exif_orientation_status = "missing"

        if size_bytes <= 0:
            status = "invalid"
            reason = "empty_file"

        try:
            digest = sha256_file(path)
            if size_bytes > 0:
                with Image.open(path) as image:
                    image_format = image.format or ""
                    width, height = image.size
                    mode = image.mode
                    image.verify()
                with Image.open(path) as image:
                    orientation_value = image.getexif().get(274)
                    if orientation_value is None:
                        exif_orientation_status = "missing"
                    elif orientation_value == 1:
                        exif_orientation = "1"
                        exif_orientation_status = "normal"
                    elif orientation_value in {2, 3, 4, 5, 6, 7, 8}:
                        exif_orientation = str(orientation_value)
                        exif_orientation_status = "requires_transpose"
                    else:
                        exif_orientation = str(orientation_value)
                        exif_orientation_status = "invalid_value"
                    image.load()
        except (OSError, UnidentifiedImageError) as exc:
            status = "invalid"
            reason = f"unreadable_image: {exc.__class__.__name__}"

        if extension not in allowed_extensions:
            status = "invalid"
            reason = "extension_not_allowed"
        elif image_format and image_format.upper() not in allowed_formats:
            status = "invalid"
            reason = "format_not_allowed"

        record = ImageRecord(
            original_path=str(path),
            class_id=class_id,
            display_name=str(class_info.get("display_name", "")),
            trigger_token=str(class_info.get("trigger_token", "")),
            file_name=path.name,
            extension=extension,
            format=image_format,
            width=width,
            height=height,
            color_mode=mode,
            file_size=size_bytes,
            sha256=digest,
            original_file_name=path.name,
            source_type=source_type,
            is_local_aikmel=source_type == "local_aikmel",
            exif_orientation=exif_orientation,
            exif_orientation_status=exif_orientation_status,
            status=status,
            rejection_reason=reason,
        )
        records.append(apply_manifest_provenance(record, provenance_by_path))

    return records


def write_inventory(
    config: dict[str, Any],
    records: list[ImageRecord],
) -> dict[str, object]:
    output_dir = dataset_reports_dir(config)
    rows = [record.to_dict() for record in records]
    paths: dict[str, object] = {}
    paths["json"] = str(write_json(output_dir / "inventory_all_classes.json", rows))
    paths["all_classes"] = str(
        write_csv(
            output_dir / "inventory_all_classes.csv",
            rows,
            INVENTORY_FIELDS,
        )
    )

    per_class: dict[str, str] = {}
    for item in class_definitions(config):
        class_rows = [record.to_dict() for record in records if record.class_id == item["id"]]
        class_path = write_csv(
            output_dir / f"inventory_{item['id']}.csv",
            class_rows,
            INVENTORY_FIELDS,
        )
        per_class[item["id"]] = str(class_path)
    paths["per_class"] = per_class

    invalid_rows = [record.to_dict() for record in records if record.status == "invalid"]
    paths["invalid"] = str(
        write_csv(
            output_dir / "invalid_images.csv",
            invalid_rows,
            INVENTORY_FIELDS,
        )
    )
    return paths
