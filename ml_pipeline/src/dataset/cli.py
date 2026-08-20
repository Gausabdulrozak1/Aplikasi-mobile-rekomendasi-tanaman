from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from typing import Any, Sequence

from ml_pipeline.src.common.config import (
    apply_class_filter,
    class_definitions,
    dataset_output_dir,
    dataset_packages_dir,
    dataset_reports_dir,
    load_config,
    source_definitions,
)
from ml_pipeline.src.dataset.caption_dataset import write_metadata
from ml_pipeline.src.dataset.curate_dataset import (
    curate_dataset,
    reset_processed_directory,
    reset_review_candidates_directory,
    write_curation_mapping,
)
from ml_pipeline.src.dataset.dataset_inventory import (
    DatasetNotAvailableError,
    build_inventory,
    write_inventory,
)
from ml_pipeline.src.dataset.dataset_report import (
    build_class_balance,
    build_source_distribution,
    write_audit_summary,
    write_class_balance_report,
    write_dataset_report,
    write_duplicate_reports,
    write_filename_collision_report,
    write_source_distribution_report,
    write_split_reports,
)
from ml_pipeline.src.dataset.dataset_review import (
    apply_manual_review,
    create_dataset_review,
    inspect_manual_review,
    write_manual_review_reports,
)
from ml_pipeline.src.dataset.detect_duplicates import (
    add_perceptual_hashes,
    assign_duplicate_groups,
    duplicate_report,
)
from ml_pipeline.src.dataset.final_package_validation import validate_final_dataset_package
from ml_pipeline.src.dataset.finalize_reviewed import finalize_reviewed_dataset
from ml_pipeline.src.dataset.io_utils import read_json, write_json
from ml_pipeline.src.dataset.models import ImageRecord
from ml_pipeline.src.dataset.package_dataset import create_dataset_package
from ml_pipeline.src.dataset.provenance import (
    provenance_warnings,
    sync_source_manifest,
    write_provenance_warnings,
)
from ml_pipeline.src.dataset.semantic_screening import run_automated_semantic_screening
from ml_pipeline.src.dataset.source_adapters import resolve_dataset_source
from ml_pipeline.src.dataset.split_dataset import split_dataset
from ml_pipeline.src.dataset.validate_images import validate_records
from ml_pipeline.src.dataset.validate_metadata import (
    discover_metadata_paths,
    validate_metadata_paths,
    write_metadata_validation_reports,
)

MANUAL_REVIEW_MESSAGE = (
    "Audit otomatis selesai. Pemeriksaan manual belum selesai.\n"
    "Jalankan `npm run dataset-review`, buka http://127.0.0.1:4173,\n"
    "lakukan keputusan visual, lalu klik Finalisasi Review."
)


def _inventory_source(
    config: dict[str, Any],
) -> tuple[list[ImageRecord], str]:
    if config.get("classes"):
        records = build_inventory(config)
        source = ", ".join(str(item["directory"]) for item in source_definitions(config))
        return records, source

    source_dir = resolve_dataset_source(config)
    return build_inventory(config, source_dir), str(source_dir)


def _audit_records(
    config: dict[str, Any],
) -> tuple[list[ImageRecord], dict[str, list[dict[str, object]]], str]:
    records, source = _inventory_source(config)
    sync_source_manifest(config, records)
    records = validate_records(config, records)
    records = add_perceptual_hashes(records)
    duplicates = duplicate_report(config, records)
    records = assign_duplicate_groups(records, duplicates)
    return records, duplicates, source


def _write_audit_outputs(
    config: dict[str, Any],
    records: list[ImageRecord],
    duplicates: dict[str, list[dict[str, object]]],
    splits: dict[str, list[dict[str, object]]] | None = None,
) -> dict[str, object]:
    inventory_paths = write_inventory(config, records)
    duplicate_paths = write_duplicate_reports(config, duplicates)
    collision_path = write_filename_collision_report(config, records)
    provenance_path = write_provenance_warnings(config, records)
    provenance_warning_rows = provenance_warnings(records)
    audit_summary_path = write_audit_summary(
        config,
        records,
        duplicates,
        len(provenance_warning_rows),
    )
    class_balance = build_class_balance(config, records, splits)
    balance_path = write_class_balance_report(config, class_balance)
    source_distribution = build_source_distribution(config, records, splits)
    source_distribution_path = write_source_distribution_report(config, source_distribution)
    report_paths = write_dataset_report(
        config,
        records,
        duplicates,
        class_balance=class_balance,
    )
    return {
        "inventory": inventory_paths,
        "duplicates": duplicate_paths,
        "file_name_collisions": collision_path,
        "source_manifest": sync_source_manifest(config, records),
        "provenance_warnings": provenance_path,
        "audit_summary": audit_summary_path,
        "class_balance": balance_path,
        "source_distribution": source_distribution_path,
        "report": report_paths,
    }


def _summary(records: list[ImageRecord]) -> dict[str, object]:
    by_class = {
        class_id: {
            "total": sum(record.class_id == class_id for record in records),
            "valid": sum(
                record.class_id == class_id and record.status == "valid" for record in records
            ),
            "duplicate": sum(
                record.class_id == class_id and record.status == "duplicate" for record in records
            ),
            "invalid": sum(
                record.class_id == class_id and record.status == "invalid" for record in records
            ),
        }
        for class_id in sorted({record.class_id for record in records})
    }
    return {
        "total": len(records),
        "valid": sum(record.status == "valid" for record in records),
        "duplicate": sum(record.status == "duplicate" for record in records),
        "invalid": sum(record.status == "invalid" for record in records),
        "by_class": by_class,
        "by_source": {
            source_type: sum(record.source_type == source_type for record in records)
            for source_type in sorted({record.source_type for record in records})
        },
    }


def command_audit(config: dict[str, Any]) -> dict[str, object]:
    records, duplicates, source = _audit_records(config)
    paths = _write_audit_outputs(config, records, duplicates)
    return {
        "source": source,
        **paths,
        "summary": _summary(records),
    }


def command_prepare(config: dict[str, Any]) -> dict[str, object]:
    records, duplicates, source = _audit_records(config)
    active_classes = [item["id"] for item in class_definitions(config)]
    insufficient = [
        class_id
        for class_id in active_classes
        if sum(record.class_id == class_id and record.status == "valid" for record in records) < 2
    ]
    if insufficient:
        raise DatasetNotAvailableError(
            "Each selected class needs at least 2 valid unique images. "
            f"Insufficient classes: {', '.join(insufficient)}"
        )

    audit_paths = _write_audit_outputs(config, records, duplicates)
    reset_review_candidates_directory(config)
    curated = curate_dataset(config, records)
    review_outputs = create_dataset_review(config, curated)
    review_status = inspect_manual_review(config, curated)
    reviewed = apply_manual_review(config, curated)
    mapping_path = write_curation_mapping(config, reviewed)
    class_balance = build_class_balance(config, records)
    balance_path = write_class_balance_report(config, class_balance)
    source_distribution_path = write_source_distribution_report(
        config,
        build_source_distribution(config, records),
    )
    report_paths = write_dataset_report(
        config,
        records,
        duplicates,
        class_balance=class_balance,
    )
    warnings = _prepare_warnings(config, records, reviewed, review_outputs)

    if not review_status["complete"]:
        invalidated = _invalidate_final_outputs(config)
        return {
            "status": "manual_review_required",
            "message": MANUAL_REVIEW_MESSAGE,
            "source": source,
            "final_dataset_created": False,
            "processed_directory": str(dataset_output_dir(config)),
            "technical_candidate_count": len(curated),
            "curation_mapping": mapping_path,
            "manual_review": review_status,
            "dataset_review": review_outputs,
            "invalidated_final_outputs": invalidated,
            "class_balance": balance_path,
            "source_distribution": source_distribution_path,
            "warnings": warnings,
            "audit": audit_paths,
            "report": report_paths,
        }

    accepted = [item for item in reviewed if item["manual_review_status"] == "yes"]
    manual_reports = write_manual_review_reports(config, records, reviewed)
    shortfalls = _target_shortfalls(config, accepted)
    if shortfalls:
        class_balance = build_class_balance(
            config,
            records,
            review_rows=list(manual_reports["rows"]),
        )
        balance_path = write_class_balance_report(config, class_balance)
        invalidated = _invalidate_final_outputs(config, keep_review_reports=True)
        return {
            "status": "insufficient_final_images",
            "source": source,
            "final_dataset_created": False,
            "technical_candidate_count": len(curated),
            "manual_review": review_status,
            "manual_review_reports": manual_reports,
            "shortfalls": shortfalls,
            "curation_mapping": mapping_path,
            "invalidated_final_outputs": invalidated,
            "warnings": warnings,
            "audit": audit_paths,
            "report": report_paths,
        }

    reset_processed_directory(config)
    splits = split_dataset(config, accepted)
    split_paths = write_split_reports(config, splits)
    metadata_paths = write_metadata(config, splits)
    metadata_validation = validate_metadata_paths(metadata_paths, config)
    metadata_validation_paths = write_metadata_validation_reports(
        config,
        metadata_validation,
    )
    class_balance = build_class_balance(
        config,
        records,
        splits,
        review_rows=list(manual_reports["rows"]),
    )
    balance_path = write_class_balance_report(config, class_balance)
    source_distribution_path = write_source_distribution_report(
        config,
        build_source_distribution(config, records, splits),
    )
    report_paths = write_dataset_report(
        config,
        records,
        duplicates,
        metadata_validation,
        class_balance,
        split_paths["summary"],
    )

    return {
        "status": "final_dataset_prepared" if metadata_validation["valid"] else "metadata_invalid",
        "source": source,
        "final_dataset_created": True,
        "package_created": False,
        "processed_directory": str(dataset_output_dir(config)),
        "technical_candidate_count": len(curated),
        "accepted_count": len(accepted),
        "curation_mapping": mapping_path,
        "split_counts": {split: len(items) for split, items in splits.items()},
        "split_reports": {key: value for key, value in split_paths.items() if key != "summary"},
        "metadata": metadata_paths,
        "metadata_validation": metadata_validation,
        "metadata_validation_reports": metadata_validation_paths,
        "class_balance": balance_path,
        "source_distribution": source_distribution_path,
        "dataset_review": review_outputs,
        "manual_review": review_status,
        "manual_review_reports": manual_reports,
        "warnings": warnings,
        "audit": audit_paths,
        "report": report_paths,
    }


def _target_shortfalls(
    config: dict[str, Any],
    accepted: list[dict[str, object]],
) -> dict[str, dict[str, int]]:
    shortfalls: dict[str, dict[str, int]] = {}
    for class_info in class_definitions(config):
        class_id = str(class_info["id"])
        minimum = int(class_info.get("target_minimum_images", 80))
        count = sum(item["class_id"] == class_id for item in accepted)
        if count < minimum:
            shortfalls[class_id] = {
                "accepted": count,
                "minimum": minimum,
                "shortfall": minimum - count,
            }
    return shortfalls


def _prepare_warnings(
    config: dict[str, Any],
    records: list[ImageRecord],
    curated: list[dict[str, object]],
    review_outputs: dict[str, object],
) -> list[str]:
    warnings: list[str] = []
    candidate_counts = {
        str(item["id"]): sum(row["class_id"] == item["id"] for row in curated)
        for item in class_definitions(config)
    }
    if len(set(candidate_counts.values())) > 1:
        warnings.append(
            "Technical candidate counts are imbalanced: "
            + ", ".join(f"{key}={value}" for key, value in candidate_counts.items())
        )
    for class_info in class_definitions(config):
        class_id = str(class_info["id"])
        minimum = int(class_info.get("target_minimum_images", 80))
        if candidate_counts[class_id] < minimum:
            warnings.append(f"Class {class_id} is below target minimum")
    provenance_warning_rows = provenance_warnings(records)
    if provenance_warning_rows:
        warnings.append(
            "Provenance/manual-review warnings remain for "
            f"{len(provenance_warning_rows)} image checks"
        )
    warnings.extend(str(item) for item in review_outputs.get("warnings", []))
    return warnings


def _invalidate_final_outputs(
    config: dict[str, Any],
    *,
    keep_review_reports: bool = False,
) -> list[str]:
    removed: list[str] = []
    output_dir = reset_processed_directory(config)
    marker = output_dir / ".gitkeep"
    marker.write_text("\n", encoding="utf-8")

    report_names = [
        "split_manifest.csv",
        "split_summary.json",
        "split_summary.md",
        "metadata_validation_report.json",
        "metadata_validation_report.md",
    ]
    if not keep_review_reports:
        report_names.extend(["manual_review_summary.csv", "final_curation_summary.md"])
    for name in report_names:
        path = dataset_reports_dir(config) / name
        if path.exists():
            path.unlink()
            removed.append(str(path))

    package_dir = dataset_packages_dir(config)
    for name in ("dataset_multicrop_v1.zip", "dataset_multicrop_v1.sha256"):
        path = package_dir / name
        if path.exists():
            path.unlink()
            removed.append(str(path))
    return removed


def _prepared_split_items(
    config: dict[str, Any],
) -> dict[str, list[dict[str, object]]]:
    active_classes = {item["id"] for item in class_definitions(config)}
    result: dict[str, list[dict[str, object]]] = {"train": [], "validation": []}
    manifest = dataset_reports_dir(config) / "split_manifest.csv"
    if not manifest.exists():
        return result
    with manifest.open(newline="", encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            split = row.get("split", "")
            class_id = row.get("class_id", "")
            if split not in result or class_id not in active_classes:
                continue
            path = dataset_output_dir(config) / split / row["file_name"]
            if not path.exists():
                continue
            result[split].append(
                {
                    **row,
                    "file": str(path),
                    "is_local_aikmel": row.get("is_local_aikmel", "").casefold() == "true",
                }
            )
    return result


def command_caption(config: dict[str, Any]) -> dict[str, object]:
    splits = _prepared_split_items(config)
    if not all(splits.values()):
        raise DatasetNotAvailableError(
            "Prepared train/validation images are missing. Run `prepare` first."
        )
    metadata_paths = write_metadata(config, splits)
    metadata_validation = validate_metadata_paths(metadata_paths, config)
    validation_reports = write_metadata_validation_reports(config, metadata_validation)
    return {
        "metadata": metadata_paths,
        "metadata_validation": metadata_validation,
        "metadata_validation_reports": validation_reports,
    }


def command_validate(config: dict[str, Any]) -> dict[str, object]:
    validation = validate_metadata_paths(discover_metadata_paths(config), config)
    report_paths = write_metadata_validation_reports(config, validation)
    return {
        **validation,
        "processed_directory": str(dataset_output_dir(config)),
        "report_paths": report_paths,
    }


def command_report(config: dict[str, Any]) -> dict[str, object]:
    records, duplicates, source = _audit_records(config)
    prepared_splits = _prepared_split_items(config)
    has_prepared_splits = all(prepared_splits.values())
    paths = _write_audit_outputs(
        config,
        records,
        duplicates,
        prepared_splits if has_prepared_splits else None,
    )
    metadata_paths = discover_metadata_paths(config)
    if all(Path(path).exists() for path in metadata_paths.values()):
        metadata_validation = validate_metadata_paths(metadata_paths, config)
    else:
        metadata_validation = {
            "valid": False,
            "splits": {},
            "note": "Prepared metadata is not available; run `prepare` first.",
        }
    if has_prepared_splits:
        split_summary_path = dataset_reports_dir(config) / "split_summary.json"
        split_summary = read_json(split_summary_path) if split_summary_path.exists() else {}
        paths["report"] = write_dataset_report(
            config,
            records,
            duplicates,
            metadata_validation,
            build_class_balance(config, records, prepared_splits),
            split_summary,
        )
    return {
        "source": source,
        **paths,
        "metadata_validation": metadata_validation,
        "summary": _summary(records),
    }


def command_package(
    config: dict[str, Any],
    *,
    tests_passed: bool,
) -> dict[str, object]:
    return create_dataset_package(config, tests_passed=tests_passed)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="TaniAdaptif multi-class dataset pipeline CLI")
    subparsers = parser.add_subparsers(dest="command", required=True)

    for command in (
        "audit",
        "prepare",
        "finalize-reviewed",
        "screen",
        "validate",
        "validate-package",
        "report",
        "caption",
        "package",
    ):
        command_parser = subparsers.add_parser(command)
        command_parser.add_argument("--config", required=True, help="Path to YAML config")
        filters = command_parser.add_mutually_exclusive_group()
        filters.add_argument(
            "--class",
            dest="class_id",
            default=None,
            help="Process one configured class ID",
        )
        filters.add_argument(
            "--all-classes",
            action="store_true",
            help="Explicitly process all configured classes",
        )
        command_parser.add_argument(
            "--json-out",
            default="",
            help="Optional path to write command result JSON",
        )
        if command == "package":
            command_parser.add_argument(
                "--tests-passed",
                action="store_true",
                help="Confirm that the required pytest/Ruff/notebook checks just passed",
            )
    return parser


def main(argv: Sequence[str] | None = None) -> dict[str, object]:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        config = apply_class_filter(
            load_config(args.config),
            args.class_id,
            all_classes=args.all_classes,
        )
        handlers = {
            "audit": command_audit,
            "prepare": command_prepare,
            "finalize-reviewed": finalize_reviewed_dataset,
            "validate": command_validate,
            "validate-package": validate_final_dataset_package,
            "report": command_report,
            "caption": command_caption,
            "screen": run_automated_semantic_screening,
        }
        if args.command == "package":
            result = command_package(config, tests_passed=args.tests_passed)
        else:
            result = handlers[args.command](config)
    except (DatasetNotAvailableError, ValueError) as exc:
        parser.error(str(exc))

    if args.json_out:
        write_json(Path(args.json_out), result)
    else:
        print(json.dumps(result, indent=2, ensure_ascii=False))
        if result.get("status") == "manual_review_required":
            print(MANUAL_REVIEW_MESSAGE)
    return result


if __name__ == "__main__":
    main()
