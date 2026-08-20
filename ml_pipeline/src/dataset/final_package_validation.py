from __future__ import annotations

import csv
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from ml_pipeline.src.common.config import (
    FINAL_TRIGGER_TOKENS,
    class_definitions,
    dataset_packages_dir,
    dataset_reports_dir,
    dataset_review_dir,
)
from ml_pipeline.src.dataset.dataset_review import inspect_manual_review
from ml_pipeline.src.dataset.io_utils import write_json
from ml_pipeline.src.dataset.package_dataset import (
    PACKAGE_VERSION,
    PackageBlockedError,
    validate_package_archive,
    validate_package_checksum,
)
from ml_pipeline.src.dataset.validate_metadata import (
    discover_metadata_paths,
    validate_metadata_paths,
)


def validate_final_dataset_package(config: dict[str, Any]) -> dict[str, object]:
    package_dir = dataset_packages_dir(config)
    package_dir.mkdir(parents=True, exist_ok=True)
    reports_dir = dataset_reports_dir(config)
    mapping_path = reports_dir / "curation_mapping.csv"
    review_path = dataset_review_dir(config) / "manual_review_template.csv"
    mapping = _read_csv(mapping_path)
    review_rows = _read_csv(review_path)
    review = inspect_manual_review(config, mapping)

    classes = class_definitions(config, active_only=False)
    accepted_rows = [
        row for row in review_rows if str(row.get("accepted", "")).strip().casefold() == "yes"
    ]
    accepted_counts = Counter(str(row.get("class_id", "")) for row in accepted_rows)
    class_results: dict[str, dict[str, object]] = {}
    class_minimum_valid = True
    source_rules_valid = True
    for class_info in classes:
        class_id = str(class_info["id"])
        minimum = int(class_info.get("target_minimum_images", 80))
        class_accepted = [row for row in accepted_rows if row.get("class_id") == class_id]
        source_counts = Counter(str(row.get("source_type", "")) for row in class_accepted)
        source_valid = (
            all(row.get("source_type") == "public" for row in class_accepted)
            if class_id != "padi"
            else all(row.get("source_type") in {"public", "local_aikmel"} for row in class_accepted)
        )
        accepted = accepted_counts[class_id]
        minimum_met = accepted >= minimum
        class_minimum_valid &= minimum_met
        source_rules_valid &= source_valid
        class_results[class_id] = {
            "accepted": accepted,
            "minimum": minimum,
            "shortfall": max(0, minimum - accepted),
            "minimum_met": minimum_met,
            "sources": dict(sorted(source_counts.items())),
            "source_rule_valid": source_valid,
        }

    expected_triggers = {
        str(item["id"]): FINAL_TRIGGER_TOKENS.get(str(item["id"]), str(item["trigger_token"]))
        for item in classes
    }
    actual_triggers = {str(item["id"]): str(item["trigger_token"]) for item in classes}
    trigger_config_valid = actual_triggers == expected_triggers

    metadata_paths = discover_metadata_paths(config)
    metadata_available = all(Path(path).is_file() for path in metadata_paths.values())
    metadata = validate_metadata_paths(metadata_paths, config)
    duplicate_leakage_valid = metadata_available and not metadata["cross_split_errors"]
    metadata_triggers_valid = metadata_available and all(
        not any("trigger" in error.casefold() for error in result["errors"])
        for result in metadata["splits"].values()
    )

    zip_path = package_dir / f"{PACKAGE_VERSION}.zip"
    checksum_path = package_dir / f"{PACKAGE_VERSION}.sha256"
    package_result: dict[str, object] = {
        "zip": str(zip_path),
        "checksum_file": str(checksum_path),
        "zip_exists": zip_path.is_file(),
        "checksum_exists": checksum_path.is_file(),
        "archive_valid": False,
        "checksum_valid": False,
        "sha256": None,
        "size_bytes": zip_path.stat().st_size if zip_path.is_file() else None,
        "errors": [],
    }
    package_errors: list[str] = []
    if not zip_path.is_file():
        package_errors.append(f"ZIP dataset tidak ditemukan: {zip_path}")
    if not checksum_path.is_file():
        package_errors.append(f"Checksum dataset tidak ditemukan: {checksum_path}")
    if zip_path.is_file():
        try:
            package_result["archive"] = validate_package_archive(zip_path)
            package_result["archive_valid"] = True
        except (OSError, ValueError) as exc:
            package_errors.append(f"ZIP dataset tidak valid: {exc}")
    if zip_path.is_file() and checksum_path.is_file():
        try:
            package_result["sha256"] = validate_package_checksum(zip_path, checksum_path)
            package_result["checksum_valid"] = True
        except (OSError, PackageBlockedError) as exc:
            package_errors.append(f"Checksum dataset tidak valid: {exc}")
    package_result["errors"] = package_errors

    checks = [
        _check("review_complete", bool(review["complete"]), _review_detail(review)),
        _check(
            "class_minimum",
            class_minimum_valid,
            _class_minimum_detail(class_results),
        ),
        _check(
            "source_rules",
            source_rules_valid,
            "Padi boleh public/local_aikmel; kelas lain wajib public-only.",
        ),
        _check(
            "trigger_config",
            trigger_config_valid,
            f"Trigger aktual: {actual_triggers}",
        ),
        _check(
            "metadata_available",
            metadata_available,
            f"Train: {metadata_paths['train']}; validation: {metadata_paths['validation']}",
        ),
        _check(
            "metadata_valid",
            bool(metadata["valid"]),
            _metadata_detail(metadata),
        ),
        _check(
            "duplicate_leakage",
            duplicate_leakage_valid,
            _duplicate_detail(metadata, metadata_available),
        ),
        _check(
            "metadata_triggers",
            metadata_triggers_valid,
            "Trigger metadata belum dapat dinilai."
            if not metadata_available
            else "Tidak ada trigger silang atau trigger yang hilang.",
        ),
        _check(
            "package_archive",
            bool(package_result["archive_valid"]),
            next(
                (error for error in package_errors if error.startswith("ZIP")),
                "Struktur dan isi ZIP valid.",
            ),
        ),
        _check(
            "package_checksum",
            bool(package_result["checksum_valid"]),
            next(
                (error for error in package_errors if "Checksum" in error),
                "Checksum SHA-256 cocok dengan ZIP.",
            ),
        ),
    ]
    blockers = [str(check["detail"]) for check in checks if not check["passed"]]
    valid = not blockers
    result: dict[str, object] = {
        "schema_version": 1,
        "validated_at": datetime.now(timezone.utc).isoformat(),
        "status": "valid" if valid else "blocked",
        "valid": valid,
        "training_allowed": valid,
        "review": {key: value for key, value in review.items() if key != "decisions"},
        "classes": class_results,
        "triggers": {
            "expected": expected_triggers,
            "actual": actual_triggers,
            "config_valid": trigger_config_valid,
            "metadata_valid": metadata_triggers_valid,
        },
        "metadata": {
            "available": metadata_available,
            **metadata,
        },
        "duplicate_leakage": {
            "valid": duplicate_leakage_valid,
            "errors": metadata["cross_split_errors"],
        },
        "package": package_result,
        "checks": checks,
        "blockers": blockers,
    }
    json_path = package_dir / "final_package_validation.json"
    markdown_path = package_dir / "final_package_validation.md"
    result["reports"] = {"json": str(json_path), "markdown": str(markdown_path)}
    write_json(json_path, result)
    markdown_path.write_text(_render_markdown(result), encoding="utf-8")
    return result


def _check(check_id: str, passed: bool, detail: str) -> dict[str, object]:
    return {"id": check_id, "passed": passed, "detail": detail}


def _read_csv(path: Path) -> list[dict[str, str]]:
    if not path.is_file():
        return []
    with path.open(newline="", encoding="utf-8-sig") as handle:
        return list(csv.DictReader(handle))


def _review_detail(review: dict[str, object]) -> str:
    return (
        f"Review: expected={review['expected_rows']}, present={review['present_rows']}, "
        f"accepted={review['accepted']}, rejected={review['rejected']}, "
        f"unsure={review['unsure']}, pending={review['pending']}."
    )


def _class_minimum_detail(classes: dict[str, dict[str, object]]) -> str:
    shortfalls = [
        f"{class_id} kurang {result['shortfall']} (diterima {result['accepted']})"
        for class_id, result in classes.items()
        if not result["minimum_met"]
    ]
    return "Semua kelas memenuhi minimum." if not shortfalls else "; ".join(shortfalls) + "."


def _metadata_detail(metadata: dict[str, object]) -> str:
    errors = [
        *metadata["cross_split_errors"],
        *metadata["manifest_errors"],
        *[
            f"{split}: {error}"
            for split, result in metadata["splits"].items()
            for error in result["errors"]
        ],
    ]
    return "Metadata train/validation valid." if not errors else "; ".join(errors[:4])


def _duplicate_detail(metadata: dict[str, object], available: bool) -> str:
    if not available:
        return "Duplicate leakage belum dapat dinilai karena metadata final belum tersedia."
    errors = metadata["cross_split_errors"]
    return "Tidak ada duplicate leakage lintas split." if not errors else "; ".join(errors)


def _render_markdown(result: dict[str, object]) -> str:
    lines = [
        "# Final Package Validation",
        "",
        f"- Waktu validasi (UTC): `{result['validated_at']}`",
        f"- Status: **{str(result['status']).upper()}**",
        f"- Training diizinkan: **{result['training_allowed']}**",
        "",
        "## Jumlah Diterima (Belum Dipaketkan)",
        "",
        "| Kelas | Diterima | Minimum | Kekurangan | Public | Local Aikmel |",
        "| --- | ---: | ---: | ---: | ---: | ---: |",
    ]
    for class_id, item in result["classes"].items():
        sources = item["sources"]
        lines.append(
            f"| {class_id} | {item['accepted']} | {item['minimum']} | {item['shortfall']} | "
            f"{sources.get('public', 0)} | {sources.get('local_aikmel', 0)} |"
        )
    lines.extend(
        [
            "",
            "## Pemeriksaan",
            "",
            "| Pemeriksaan | Lulus | Detail |",
            "| --- | --- | --- |",
        ]
    )
    for check in result["checks"]:
        detail = str(check["detail"]).replace("|", "\\|").replace("\n", " ")
        lines.append(f"| `{check['id']}` | {check['passed']} | {detail} |")
    if result["blockers"]:
        lines.extend(["", "## Blocker", ""])
        lines.extend(f"- {blocker}" for blocker in result["blockers"])
    lines.extend(
        [
            "",
            "Training Stable Diffusion tidak boleh dimulai sebelum seluruh pemeriksaan lulus.",
            "",
        ]
    )
    return "\n".join(lines)
