from __future__ import annotations

import csv
import json
import zipfile
from collections import Counter
from datetime import date
from pathlib import Path
from typing import Any

from ml_pipeline.src.common.config import (
    class_definitions,
    dataset_output_dir,
    dataset_packages_dir,
    dataset_reports_dir,
    dataset_source_manifest_path,
    resolve_path,
)
from ml_pipeline.src.dataset.dataset_review import inspect_manual_review
from ml_pipeline.src.dataset.io_utils import sha256_file
from ml_pipeline.src.dataset.validate_metadata import (
    discover_metadata_paths,
    validate_metadata_paths,
    write_metadata_validation_reports,
)

PACKAGE_VERSION = "dataset_multicrop_v1"


class PackageBlockedError(ValueError):
    pass


def create_dataset_package(
    config: dict[str, Any],
    *,
    tests_passed: bool,
) -> dict[str, object]:
    package_dir = dataset_packages_dir(config)
    package_dir.mkdir(parents=True, exist_ok=True)
    zip_path = package_dir / f"{PACKAGE_VERSION}.zip"
    checksum_path = package_dir / f"{PACKAGE_VERSION}.sha256"
    _remove_stale_package(zip_path, checksum_path)

    if not tests_passed:
        raise PackageBlockedError("Dataset package requires a successful automated test run")

    mapping_path = dataset_reports_dir(config) / "curation_mapping.csv"
    mapping = _read_csv(mapping_path)
    if not mapping:
        raise PackageBlockedError("Curation mapping is missing or empty")
    review = inspect_manual_review(config, mapping)
    if not review["complete"]:
        raise PackageBlockedError("Manual review is incomplete")

    accepted = [row for row in mapping if row.get("manual_review_status", "").casefold() == "yes"]
    shortfalls = _minimum_shortfalls(config, accepted)
    if shortfalls:
        raise PackageBlockedError(f"Final class minimum is not met: {shortfalls}")

    metadata_validation = validate_metadata_paths(discover_metadata_paths(config), config)
    write_metadata_validation_reports(config, metadata_validation)
    if not metadata_validation["valid"]:
        raise PackageBlockedError("Metadata validation failed")

    required_reports = [
        "curation_mapping.csv",
        "split_manifest.csv",
        "split_summary.json",
        "split_summary.md",
        "class_balance_report.csv",
        "manual_review_summary.csv",
        "metadata_validation_report.json",
        "metadata_validation_report.md",
        "final_curation_summary.md",
    ]
    required_reports.extend(
        name
        for name in (
            "additional_source_candidates.csv",
            "additional_semantic_screening.csv",
            "additional_semantic_summary.md",
        )
        if (dataset_reports_dir(config) / name).is_file()
    )
    missing_reports = [
        name for name in required_reports if not (dataset_reports_dir(config) / name).is_file()
    ]
    if missing_reports:
        raise PackageBlockedError(
            "Required package reports are missing: " + ", ".join(missing_reports)
        )

    config_paths = _package_config_paths(config)
    missing_configs = [str(path) for path in config_paths if not path.is_file()]
    if missing_configs:
        raise PackageBlockedError(
            "Required package configs are missing: " + ", ".join(missing_configs)
        )

    dataset_card = resolve_path(config["dataset"].get("dataset_card", "docs/DATASET_CARD.md"))
    if not dataset_card.is_file():
        raise PackageBlockedError(f"Dataset card is missing: {dataset_card}")
    source_manifest = dataset_source_manifest_path(config)
    if source_manifest is None or not source_manifest.is_file():
        raise PackageBlockedError("Dataset source manifest is missing")
    additional_docs = [
        path
        for path in (
            resolve_path("docs/DATASET_ADDITIONAL_SOURCES.md"),
            resolve_path("docs/rejected_sources.md"),
        )
        if path.is_file()
    ]

    split_rows = _read_csv(dataset_reports_dir(config) / "split_manifest.csv")
    package_manifest = _build_package_manifest(
        config,
        split_rows,
        [*required_reports, "dataset_source_manifest.csv"],
    )
    prefix = f"{PACKAGE_VERSION}/"
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        processed = dataset_output_dir(config)
        for path in sorted(processed.rglob("*")):
            if path.is_file() and path.name != ".gitkeep":
                archive.write(path, prefix + "processed/" + path.relative_to(processed).as_posix())
        for path in config_paths:
            archive.write(path, prefix + "configs/" + path.name)
        for name in required_reports:
            archive.write(dataset_reports_dir(config) / name, prefix + "reports/" + name)
        archive.write(source_manifest, prefix + "reports/dataset_source_manifest.csv")
        archive.write(dataset_card, prefix + "docs/DATASET_CARD.md")
        for document in additional_docs:
            archive.write(document, prefix + "docs/" + document.name)
        archive.writestr(
            prefix + "PACKAGE_MANIFEST.json",
            json.dumps(package_manifest, indent=2, ensure_ascii=False),
        )

    try:
        zip_validation = validate_package_archive(zip_path, prefix)
    except (OSError, ValueError, zipfile.BadZipFile, json.JSONDecodeError) as exc:
        _remove_stale_package(zip_path, checksum_path)
        raise PackageBlockedError(f"Created dataset package failed validation: {exc}") from exc

    checksum = sha256_file(zip_path)
    checksum_path.write_text(f"{checksum}  {zip_path.name}\n", encoding="ascii")
    validate_package_checksum(zip_path, checksum_path)
    manifest_doc = resolve_path(
        config["dataset"].get(
            "package_manifest_document",
            "docs/DATASET_PACKAGE_MANIFEST.md",
        )
    )
    _write_package_document(manifest_doc, package_manifest, zip_path, checksum)
    return {
        "version": PACKAGE_VERSION,
        "zip": str(zip_path),
        "checksum_file": str(checksum_path),
        "sha256": checksum,
        "size_bytes": zip_path.stat().st_size,
        "manifest_document": str(manifest_doc),
        "zip_validation": zip_validation,
    }


def _remove_stale_package(zip_path: Path, checksum_path: Path) -> None:
    for path in (zip_path, checksum_path):
        if path.exists():
            path.unlink()


def validate_package_archive(zip_path: Path, prefix: str | None = None) -> dict[str, object]:
    prefix = prefix or f"{PACKAGE_VERSION}/"
    required_entries = {
        f"{prefix}processed/train/metadata.jsonl",
        f"{prefix}processed/validation/metadata.jsonl",
        f"{prefix}PACKAGE_MANIFEST.json",
        f"{prefix}docs/DATASET_CARD.md",
    }
    allowed_roots = {"processed", "configs", "reports", "docs", "PACKAGE_MANIFEST.json"}
    forbidden_names = {"kaggle.json", ".env", "credentials.json"}
    forbidden_extensions = {".safetensors", ".ckpt", ".pt", ".bin", ".apk"}

    with zipfile.ZipFile(zip_path, "r") as archive:
        corrupt_name = archive.testzip()
        if corrupt_name:
            raise ValueError(f"corrupt ZIP member: {corrupt_name}")
        names = archive.namelist()
        if len(names) != len(set(names)):
            raise ValueError("ZIP contains duplicate member names")
        for name in names:
            normalized = name.replace("\\", "/")
            if normalized.startswith("/") or ".." in normalized.split("/"):
                raise ValueError(f"unsafe ZIP member path: {name}")
            if not normalized.startswith(prefix):
                raise ValueError(f"ZIP member is outside package prefix: {name}")
            relative = normalized[len(prefix) :]
            parts = [part for part in relative.split("/") if part]
            if not parts or parts[0] not in allowed_roots:
                raise ValueError(f"unexpected ZIP member: {name}")
            lowered = [part.casefold() for part in parts]
            if any(part in {"raw", ".venv", "venv", "checkpoints"} for part in lowered):
                raise ValueError(f"prohibited directory in ZIP: {name}")
            if any(part.startswith("checkpoint-") for part in lowered):
                raise ValueError(f"checkpoint found in ZIP: {name}")
            if lowered[-1] in forbidden_names or Path(lowered[-1]).suffix in forbidden_extensions:
                raise ValueError(f"prohibited file in ZIP: {name}")

        missing = sorted(required_entries - set(names))
        if missing:
            raise ValueError("required ZIP members are missing: " + ", ".join(missing))
        manifest = json.loads(archive.read(f"{prefix}PACKAGE_MANIFEST.json"))
        if manifest.get("version") != PACKAGE_VERSION:
            raise ValueError("PACKAGE_MANIFEST.json version is invalid")

    return {
        "valid": True,
        "entry_count": len(names),
        "corrupt_member": None,
        "prohibited_content_found": False,
    }


def validate_package_checksum(zip_path: Path, checksum_path: Path) -> str:
    parts = checksum_path.read_text(encoding="ascii").strip().split()
    if len(parts) != 2 or parts[1] != zip_path.name:
        raise PackageBlockedError("Dataset package checksum file has an invalid format")
    if parts[0] != sha256_file(zip_path):
        raise PackageBlockedError("Dataset package checksum does not match the ZIP")
    return parts[0]


def _read_csv(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open(newline="", encoding="utf-8-sig") as handle:
        return list(csv.DictReader(handle))


def _minimum_shortfalls(
    config: dict[str, Any],
    accepted: list[dict[str, str]],
) -> dict[str, int]:
    counts = Counter(row.get("class_id", "") for row in accepted)
    shortfalls: dict[str, int] = {}
    for class_info in class_definitions(config, active_only=False):
        minimum = int(class_info.get("target_minimum_images", 80))
        class_id = str(class_info["id"])
        if counts[class_id] < minimum:
            shortfalls[class_id] = minimum - counts[class_id]
    return shortfalls


def _package_config_paths(config: dict[str, Any]) -> list[Path]:
    configured = config["dataset"].get(
        "package_configs",
        [
            config.get("_config_path", "ml_pipeline/configs/dataset_public_multicrop.yaml"),
            "ml_pipeline/configs/training_public_multicrop.yaml",
            "ml_pipeline/configs/evaluation_public_multicrop.yaml",
        ],
    )
    return [resolve_path(str(path)) for path in configured]


def _build_package_manifest(
    config: dict[str, Any],
    split_rows: list[dict[str, str]],
    reports: list[str],
) -> dict[str, object]:
    per_split_class: dict[str, dict[str, int]] = {}
    for split in ("train", "validation"):
        per_split_class[split] = {
            str(item["id"]): sum(
                row.get("split") == split and row.get("class_id") == item["id"]
                for row in split_rows
            )
            for item in class_definitions(config, active_only=False)
        }
    padi_sources = Counter(
        row.get("source_type", "") for row in split_rows if row.get("class_id") == "padi"
    )
    return {
        "version": PACKAGE_VERSION,
        "date": date.today().isoformat(),
        "seed": int(config.get("seed", 42)),
        "minimum_resolution": {
            "width": int(config["dataset"].get("minimum_width", 512)),
            "height": int(config["dataset"].get("minimum_height", 512)),
        },
        "triggers": {
            str(item["id"]): str(item["trigger_token"])
            for item in class_definitions(config, active_only=False)
        },
        "counts": per_split_class,
        "padi_sources": dict(sorted(padi_sources.items())),
        "public_only_classes": ["jagung", "cabai", "kacang_tanah"],
        "main_files": [
            "processed/train/metadata.jsonl",
            "processed/validation/metadata.jsonl",
            *[f"reports/{name}" for name in reports],
            "docs/DATASET_CARD.md",
        ],
    }


def _write_package_document(
    path: Path,
    manifest: dict[str, object],
    zip_path: Path,
    checksum: str,
) -> None:
    counts = manifest["counts"]
    padi_sources = manifest["padi_sources"]
    lines = [
        "# Dataset Package Manifest",
        "",
        f"- Version: `{manifest['version']}`",
        f"- Date: {manifest['date']}",
        f"- ZIP size: {zip_path.stat().st_size} bytes",
        f"- ZIP SHA-256: `{checksum}`",
        f"- Seed: {manifest['seed']}",
        f"- Minimum resolution: {manifest['minimum_resolution']['width']}x{manifest['minimum_resolution']['height']}",
        f"- Padi public: {padi_sources.get('public', 0)}",
        f"- Padi local_aikmel: {padi_sources.get('local_aikmel', 0)}",
        "- Jagung, cabai, and kacang_tanah are public-only by research design.",
        "",
        "## Split Counts",
        "",
        "| Class | Train | Validation |",
        "| --- | ---: | ---: |",
    ]
    for class_id in manifest["triggers"]:
        lines.append(
            f"| {class_id} | {counts['train'][class_id]} | {counts['validation'][class_id]} |"
        )
    lines.extend(["", "## Triggers", ""])
    lines.extend(
        f"- `{class_id}`: `{trigger}`" for class_id, trigger in manifest["triggers"].items()
    )
    lines.extend(["", "## Main Files", ""])
    lines.extend(f"- `{name}`" for name in manifest["main_files"])
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
