from __future__ import annotations

import json
from collections import Counter
from pathlib import Path
from typing import Any

from ml_pipeline.src.common.config import (
    class_lookup,
    dataset_output_dir,
    dataset_reports_dir,
    source_definitions,
)
from ml_pipeline.src.dataset.io_utils import write_json


def _read_metadata_rows(path: Path) -> tuple[list[dict[str, object]], list[str]]:
    rows: list[dict[str, object]] = []
    errors: list[str] = []
    if not path.exists():
        return rows, [f"metadata file not found: {path}"]
    with path.open("r", encoding="utf-8") as handle:
        for index, line in enumerate(handle, start=1):
            try:
                row = json.loads(line)
            except json.JSONDecodeError as exc:
                errors.append(f"line {index}: invalid JSON ({exc.msg})")
                continue
            if not isinstance(row, dict):
                errors.append(f"line {index}: JSON value must be an object")
                continue
            rows.append(row)
    return rows, errors


def _as_bool(value: object) -> bool:
    if isinstance(value, bool):
        return value
    return str(value).strip().casefold() in {"1", "true", "yes", "ya"}


def validate_metadata_file(
    path: Path,
    config: dict[str, Any],
) -> dict[str, object]:
    rows, errors = _read_metadata_rows(path)
    if not path.exists():
        return {
            "path": str(path),
            "rows": 0,
            "valid": False,
            "errors": errors,
            "distribution": {},
            "source_distribution": {},
        }

    seen_file_names: set[str] = set()
    distribution: Counter[str] = Counter()
    source_distribution: Counter[str] = Counter()
    classes = class_lookup(config)
    all_triggers = {class_id: str(item["trigger_token"]) for class_id, item in classes.items()}
    allowed_sources: dict[str, set[str]] = {class_id: set() for class_id in classes}
    for source in source_definitions(config, active_only=False):
        allowed_sources.setdefault(str(source["class_id"]), set()).add(str(source["type"]))

    for index, row in enumerate(rows, start=1):
        file_name = str(row.get("file_name", "")).strip()
        text = str(row.get("text", "")).strip()
        declared_class = str(row.get("class_id", "")).strip()
        source_type = str(row.get("source_type", "")).strip()
        duplicate_group = str(row.get("duplicate_group", "")).strip()
        is_local = _as_bool(row.get("is_local_aikmel", False))
        location = str(row.get("location_general", "")).strip()
        manual_review_status = str(row.get("manual_review_status", "")).strip().casefold()

        if not file_name:
            errors.append(f"line {index}: missing file_name")
            continue
        if file_name in seen_file_names:
            errors.append(f"line {index}: duplicate file_name {file_name}")
        seen_file_names.add(file_name)

        image_path = path.parent / file_name
        if not image_path.exists():
            errors.append(f"line {index}: image not found {image_path}")
        if not text:
            errors.append(f"line {index}: missing caption")
        if not duplicate_group:
            errors.append(f"line {index}: missing duplicate_group")
        if manual_review_status != "yes":
            errors.append(f"line {index}: image is not manually accepted")

        path_class = Path(file_name).parts[0] if Path(file_name).parts else ""
        class_id = declared_class or path_class
        if class_id != path_class:
            errors.append(
                f"line {index}: class_id '{class_id}' does not match file path '{path_class}'"
            )
        if class_id not in classes:
            errors.append(f"line {index}: unknown class_id '{class_id}'")
            continue

        distribution[class_id] += 1
        expected_trigger = all_triggers[class_id]
        if expected_trigger not in text:
            errors.append(f"line {index}: expected trigger '{expected_trigger}' is missing")
        wrong_triggers = [
            trigger
            for other_class, trigger in all_triggers.items()
            if other_class != class_id and trigger in text
        ]
        if wrong_triggers:
            errors.append(f"line {index}: wrong trigger token(s): {', '.join(wrong_triggers)}")

        if not source_type:
            errors.append(f"line {index}: missing source_type")
        elif source_type not in allowed_sources.get(class_id, set()):
            errors.append(
                f"line {index}: source_type '{source_type}' is not allowed for '{class_id}'"
            )
        else:
            source_distribution[f"{class_id}:{source_type}"] += 1

        if source_type == "local_aikmel" and class_id != "padi":
            errors.append(f"line {index}: local_aikmel is only valid for padi")
        if is_local != (source_type == "local_aikmel"):
            errors.append(f"line {index}: inconsistent is_local_aikmel flag")
        if source_type == "public" and "aikmel" in text.casefold():
            errors.append(f"line {index}: public caption must not claim Aikmel locality")
        if (
            source_type == "local_aikmel"
            and "aikmel" in text.casefold()
            and "aikmel" not in location.casefold()
        ):
            errors.append(
                f"line {index}: Aikmel caption lacks supporting location_general provenance"
            )

    allowed = {extension.lower() for extension in config["dataset"].get("allowed_extensions", [])}
    split_root = path.parent
    image_files = {
        image_path.relative_to(split_root).as_posix()
        for image_path in split_root.rglob("*")
        if image_path.is_file() and image_path.suffix.lower() in allowed
    }
    metadata_files = {str(row.get("file_name", "")).replace("\\", "/") for row in rows}
    for missing in sorted(image_files - metadata_files):
        errors.append(f"image has no caption: {missing}")
    if len(image_files) != len(rows):
        errors.append(
            f"metadata/image count mismatch: metadata={len(rows)}, images={len(image_files)}"
        )

    return {
        "path": str(path),
        "rows": len(rows),
        "valid": not errors,
        "errors": errors,
        "distribution": dict(sorted(distribution.items())),
        "source_distribution": dict(sorted(source_distribution.items())),
    }


def validate_metadata_paths(
    paths: dict[str, str],
    config: dict[str, Any],
) -> dict[str, object]:
    results = {split: validate_metadata_file(Path(path), config) for split, path in paths.items()}
    cross_split_errors: list[str] = []
    groups: dict[str, set[str]] = {}
    files: dict[str, set[str]] = {}
    for split, path in paths.items():
        rows, _ = _read_metadata_rows(Path(path))
        for row in rows:
            group = str(row.get("duplicate_group", "")).strip()
            file_name = str(row.get("file_name", "")).replace("\\", "/").strip()
            if group:
                groups.setdefault(group, set()).add(split)
            if file_name:
                files.setdefault(file_name, set()).add(split)

    leaking_groups = sorted(group for group, splits in groups.items() if len(splits) > 1)
    if leaking_groups:
        cross_split_errors.append(
            "duplicate groups cross train/validation: " + ", ".join(leaking_groups)
        )
    repeated_files = sorted(file_name for file_name, splits in files.items() if len(splits) > 1)
    if repeated_files:
        cross_split_errors.append("file names cross train/validation: " + ", ".join(repeated_files))

    manifest_errors = _validate_split_manifest(config, paths, results)
    return {
        "valid": (
            all(result["valid"] for result in results.values())
            and not cross_split_errors
            and not manifest_errors
        ),
        "splits": results,
        "cross_split_errors": cross_split_errors,
        "manifest_errors": manifest_errors,
    }


def _validate_split_manifest(
    config: dict[str, Any],
    paths: dict[str, str],
    results: dict[str, dict[str, object]],
) -> list[str]:
    import csv

    manifest = dataset_reports_dir(config) / "split_manifest.csv"
    if not manifest.exists():
        return [f"split manifest not found: {manifest}"]
    with manifest.open(newline="", encoding="utf-8-sig") as handle:
        rows = list(csv.DictReader(handle))

    errors: list[str] = []
    manifest_by_split = Counter(str(row.get("split", "")) for row in rows)
    for split, result in results.items():
        if manifest_by_split[split] != int(result["rows"]):
            errors.append(
                f"{split}: split manifest rows={manifest_by_split[split]}, "
                f"metadata rows={result['rows']}"
            )
    manifest_names = {
        (str(row.get("split", "")), str(row.get("file_name", "")).replace("\\", "/"))
        for row in rows
    }
    metadata_names: set[tuple[str, str]] = set()
    for split, path in paths.items():
        metadata_rows, _ = _read_metadata_rows(Path(path))
        metadata_names.update(
            (split, str(row.get("file_name", "")).replace("\\", "/")) for row in metadata_rows
        )
    if manifest_names != metadata_names:
        errors.append("split manifest file names do not match metadata")
    if any(str(row.get("manual_review_status", "")).casefold() != "yes" for row in rows):
        errors.append("split manifest contains an image not manually accepted")
    return errors


def write_metadata_validation_reports(
    config: dict[str, Any],
    validation: dict[str, object],
) -> dict[str, str]:
    reports_dir = dataset_reports_dir(config)
    json_path = write_json(reports_dir / "metadata_validation_report.json", validation)
    lines = [
        "# Metadata Validation Report",
        "",
        f"- Valid: {validation.get('valid', False)}",
        f"- Cross-split errors: {len(validation.get('cross_split_errors', []))}",
        f"- Manifest errors: {len(validation.get('manifest_errors', []))}",
        "",
        "## Splits",
        "",
        "| Split | Rows | Valid | Errors |",
        "| --- | ---: | --- | ---: |",
    ]
    for split, result in dict(validation.get("splits", {})).items():
        lines.append(
            f"| {split} | {result.get('rows', 0)} | {result.get('valid', False)} | "
            f"{len(result.get('errors', []))} |"
        )
    all_errors = [
        *list(validation.get("cross_split_errors", [])),
        *list(validation.get("manifest_errors", [])),
    ]
    for split, result in dict(validation.get("splits", {})).items():
        all_errors.extend(f"{split}: {error}" for error in result.get("errors", []))
    if all_errors:
        lines.extend(["", "## Errors", ""])
        lines.extend(f"- {error}" for error in all_errors)
    md_path = reports_dir / "metadata_validation_report.md"
    md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return {"json": str(json_path), "markdown": str(md_path)}


def discover_metadata_paths(config: dict[str, Any]) -> dict[str, str]:
    root = dataset_output_dir(config)
    return {split: str(root / split / "metadata.jsonl") for split in ("train", "validation")}
