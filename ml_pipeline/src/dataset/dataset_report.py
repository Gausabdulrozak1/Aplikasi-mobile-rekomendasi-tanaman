from __future__ import annotations

from collections import Counter
from pathlib import Path
from typing import Any

from ml_pipeline.src.common.config import class_definitions, dataset_reports_dir
from ml_pipeline.src.dataset.caption_dataset import build_caption
from ml_pipeline.src.dataset.io_utils import write_csv, write_json
from ml_pipeline.src.dataset.models import ImageRecord


def summarize_records(records: list[ImageRecord]) -> dict[str, object]:
    by_status = Counter(record.status for record in records)
    by_class = Counter(record.class_id for record in records)
    valid_by_class = Counter(record.class_id for record in records if record.status == "valid")
    by_source = Counter(record.source_type or "unknown" for record in records)
    return {
        "total_files": len(records),
        "by_status": dict(sorted(by_status.items())),
        "by_class": dict(sorted(by_class.items())),
        "valid_by_class": dict(sorted(valid_by_class.items())),
        "by_source": dict(sorted(by_source.items())),
    }


def write_dataset_report(
    config: dict[str, Any],
    records: list[ImageRecord],
    duplicate_report: dict[str, object] | None = None,
    metadata_validation: dict[str, object] | None = None,
    class_balance: list[dict[str, object]] | None = None,
    split_summary: dict[str, object] | None = None,
) -> dict[str, str]:
    output_dir = dataset_reports_dir(config)
    summary = summarize_records(records)
    report = {
        "project_name": config.get("project_name"),
        "experiment_name": config.get("experiment_name"),
        "base_model": config.get("base_model"),
        "dataset": config.get("dataset"),
        "summary": summary,
        "duplicate_report": duplicate_report or {},
        "metadata_validation": metadata_validation or {},
        "class_balance": class_balance or [],
        "split_summary": split_summary or {},
    }
    json_path = write_json(output_dir / "dataset_report.json", report)
    csv_path = write_csv(
        output_dir / "dataset_records.csv", [record.to_dict() for record in records]
    )
    md_path = write_markdown_summary(output_dir / "dataset_report.md", report)
    return {"json": str(json_path), "csv": str(csv_path), "markdown": str(md_path)}


def write_audit_summary(
    config: dict[str, Any],
    records: list[ImageRecord],
    duplicate_report: dict[str, list[dict[str, object]]],
    provenance_warning_count: int,
) -> str:
    path = dataset_reports_dir(config) / "audit_summary.md"
    lines = [
        "# Automatic Dataset Audit Summary",
        "",
        "The audit is technical only and does not replace human semantic review.",
        "",
        "## Discovered Structure",
        "",
        "| Class | Source | Raw | Technical valid | Duplicate copy | Invalid |",
        "| --- | --- | ---: | ---: | ---: | ---: |",
    ]
    keys = sorted({(record.class_id, record.source_type or "unknown") for record in records})
    for class_id, source_type in keys:
        items = [
            record
            for record in records
            if record.class_id == class_id and (record.source_type or "unknown") == source_type
        ]
        lines.append(
            f"| {class_id} | {source_type} | {len(items)} | "
            f"{sum(item.status == 'valid' for item in items)} | "
            f"{sum(item.status == 'duplicate' for item in items)} | "
            f"{sum(item.status == 'invalid' for item in items)} |"
        )

    different_extension = sum(
        bool(row.get("same_content_different_extension"))
        for row in duplicate_report.get("exact", [])
    )
    orientation_issues = sum(
        record.exif_orientation_status in {"requires_transpose", "invalid_value"}
        for record in records
    )
    lines.extend(
        [
            "",
            "## Checks",
            "",
            f"- Files discovered: {len(records)}",
            f"- Technical valid: {sum(record.status == 'valid' for record in records)}",
            f"- Exact duplicate pairs: {len(duplicate_report.get('exact', []))}",
            f"- Near duplicate pairs: {len(duplicate_report.get('near', []))}",
            f"- Cross-source padi duplicate pairs: {len(duplicate_report.get('cross_source_padi', []))}",
            f"- Cross-class duplicate pairs: {len(duplicate_report.get('cross_class', []))}",
            f"- Same content with different extension: {different_extension}",
            f"- EXIF orientation requiring attention: {orientation_issues}",
            f"- Provenance/manual-review warnings: {provenance_warning_count}",
            "",
            "Raw files were not moved, overwritten, or deleted.",
        ]
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return str(path)


def write_markdown_summary(path: Path, report: dict[str, object]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    summary = report["summary"]
    lines = [
        "# Dataset Report",
        "",
        f"Project: `{report.get('project_name')}`",
        f"Experiment: `{report.get('experiment_name')}`",
        f"Base model: `{report.get('base_model')}`",
        "",
        "## Summary",
        "",
        f"- Total files: {summary['total_files']}",
        f"- By status: {summary['by_status']}",
        f"- By class: {summary['by_class']}",
        f"- Valid by class: {summary['valid_by_class']}",
        f"- By source type: {summary['by_source']}",
        "",
        "## Notes",
        "",
        "- Padi may combine public images with documented local_aikmel images.",
        "- Jagung, cabai, and kacang_tanah use public images only.",
        "- Empty provenance and manual-review fields remain explicit warnings.",
    ]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


def write_duplicate_reports(
    config: dict[str, Any],
    duplicate_report: dict[str, list[dict[str, object]]],
) -> dict[str, str]:
    output_dir = dataset_reports_dir(config)
    exact_fields = [
        "sha256",
        "canonical_path",
        "canonical_class_id",
        "canonical_source_type",
        "duplicate_path",
        "duplicate_class_id",
        "duplicate_source_type",
        "same_content_different_extension",
    ]
    near_fields = [
        "left_path",
        "left_class_id",
        "left_source_type",
        "right_path",
        "right_class_id",
        "right_source_type",
        "distance",
        "threshold",
    ]
    cross_fields = [
        "duplicate_type",
        "sha256",
        "canonical_path",
        "canonical_class_id",
        "canonical_source_type",
        "duplicate_path",
        "duplicate_class_id",
        "duplicate_source_type",
        "same_content_different_extension",
        "left_path",
        "left_class_id",
        "left_source_type",
        "right_path",
        "right_class_id",
        "right_source_type",
        "distance",
        "threshold",
    ]
    return {
        "exact": str(
            write_csv(
                output_dir / "exact_duplicates.csv",
                duplicate_report.get("exact", []),
                exact_fields,
            )
        ),
        "near": str(
            write_csv(
                output_dir / "near_duplicates.csv",
                duplicate_report.get("near", []),
                near_fields,
            )
        ),
        "cross_source_padi": str(
            write_csv(
                output_dir / "cross_source_duplicates_padi.csv",
                duplicate_report.get("cross_source_padi", []),
                cross_fields,
            )
        ),
        "cross_class": str(
            write_csv(
                output_dir / "cross_class_duplicates.csv",
                duplicate_report.get("cross_class", []),
                cross_fields,
            )
        ),
    }


def write_filename_collision_report(
    config: dict[str, Any],
    records: list[ImageRecord],
) -> str:
    by_name: dict[str, list[ImageRecord]] = {}
    for record in records:
        by_name.setdefault(record.file_name.casefold(), []).append(record)
    rows: list[dict[str, object]] = []
    for normalized_name, items in sorted(by_name.items()):
        if len(items) < 2:
            continue
        for item in items:
            rows.append(
                {
                    "normalized_file_name": normalized_name,
                    "original_path": item.original_path,
                    "class_id": item.class_id,
                    "source_type": item.source_type,
                    "sha256": item.sha256,
                }
            )
    return str(
        write_csv(
            dataset_reports_dir(config) / "file_name_collisions.csv",
            rows,
            [
                "normalized_file_name",
                "original_path",
                "class_id",
                "source_type",
                "sha256",
            ],
        )
    )


def build_class_balance(
    config: dict[str, Any],
    records: list[ImageRecord],
    splits: dict[str, list[dict[str, object]]] | None = None,
    review_rows: list[dict[str, object]] | None = None,
) -> list[dict[str, object]]:
    split_data = splits or {"train": [], "validation": []}
    review_by_class = {str(row.get("class_id", "")): row for row in (review_rows or [])}
    rows: list[dict[str, object]] = []
    for class_info in class_definitions(config):
        class_id = class_info["id"]
        class_records = [record for record in records if record.class_id == class_id]
        valid_count = sum(record.status == "valid" for record in class_records)
        split_curated_count = sum(
            item["class_id"] == class_id for items in split_data.values() for item in items
        )
        review = review_by_class.get(str(class_id), {})
        curated_count = int(review.get("final_valid", split_curated_count) or 0)
        target_count = (
            curated_count if splits is not None or review_rows is not None else valid_count
        )
        minimum = int(class_info.get("target_minimum_images", 0) or 0)
        maximum = int(class_info.get("target_maximum_images", 0) or 0)
        if minimum and target_count < minimum:
            target_status = "below_minimum"
        elif maximum and target_count > maximum:
            target_status = "above_maximum"
        else:
            target_status = "within_target"
        rows.append(
            {
                "class_id": class_id,
                "raw_count": len(class_records),
                "valid_count": valid_count,
                "rejected_count": sum(record.status == "invalid" for record in class_records),
                "duplicate_count": sum(record.status == "duplicate" for record in class_records),
                "public_valid_count": sum(
                    record.status == "valid" and record.source_type == "public"
                    for record in class_records
                ),
                "local_aikmel_valid_count": sum(
                    record.status == "valid" and record.source_type == "local_aikmel"
                    for record in class_records
                ),
                "curated_count": curated_count,
                "proxy_pass_count": review.get("proxy_pass", ""),
                "proxy_review_count": review.get("proxy_review", ""),
                "manual_accepted_count": review.get("accepted", ""),
                "manual_rejected_count": review.get("rejected", ""),
                "manual_unsure_count": review.get("unsure", ""),
                "manual_pending_count": review.get("pending", ""),
                "final_valid_count": review.get("final_valid", ""),
                "final_public_count": review.get("final_public", ""),
                "final_local_aikmel_count": review.get("final_local_aikmel", ""),
                "shortfall_to_minimum": review.get("shortfall_to_minimum", ""),
                "train_count": sum(
                    item["class_id"] == class_id for item in split_data.get("train", [])
                ),
                "validation_count": sum(
                    item["class_id"] == class_id for item in split_data.get("validation", [])
                ),
                "target_status": target_status,
            }
        )
    return rows


def write_class_balance_report(
    config: dict[str, Any],
    rows: list[dict[str, object]],
) -> str:
    fields = [
        "class_id",
        "raw_count",
        "valid_count",
        "rejected_count",
        "duplicate_count",
        "public_valid_count",
        "local_aikmel_valid_count",
        "curated_count",
        "proxy_pass_count",
        "proxy_review_count",
        "manual_accepted_count",
        "manual_rejected_count",
        "manual_unsure_count",
        "manual_pending_count",
        "final_valid_count",
        "final_public_count",
        "final_local_aikmel_count",
        "shortfall_to_minimum",
        "train_count",
        "validation_count",
        "target_status",
    ]
    return str(
        write_csv(
            dataset_reports_dir(config) / "class_balance_report.csv",
            rows,
            fields,
        )
    )


def build_source_distribution(
    config: dict[str, Any],
    records: list[ImageRecord],
    splits: dict[str, list[dict[str, object]]] | None = None,
) -> list[dict[str, object]]:
    split_data = splits or {"train": [], "validation": []}
    keys = sorted({(record.class_id, record.source_type or "unknown") for record in records})
    rows: list[dict[str, object]] = []
    for class_id, source_type in keys:
        source_records = [
            record
            for record in records
            if record.class_id == class_id and (record.source_type or "unknown") == source_type
        ]
        rows.append(
            {
                "class_id": class_id,
                "source_type": source_type,
                "raw_count": len(source_records),
                "valid_count": sum(record.status == "valid" for record in source_records),
                "duplicate_count": sum(record.status == "duplicate" for record in source_records),
                "invalid_count": sum(record.status == "invalid" for record in source_records),
                "train_count": sum(
                    item["class_id"] == class_id and item.get("source_type") == source_type
                    for item in split_data.get("train", [])
                ),
                "validation_count": sum(
                    item["class_id"] == class_id and item.get("source_type") == source_type
                    for item in split_data.get("validation", [])
                ),
            }
        )
    return rows


def write_source_distribution_report(
    config: dict[str, Any],
    rows: list[dict[str, object]],
) -> str:
    return str(
        write_csv(
            dataset_reports_dir(config) / "source_distribution.csv",
            rows,
            [
                "class_id",
                "source_type",
                "raw_count",
                "valid_count",
                "duplicate_count",
                "invalid_count",
                "train_count",
                "validation_count",
            ],
        )
    )


def write_split_reports(
    config: dict[str, Any],
    splits: dict[str, list[dict[str, object]]],
) -> dict[str, object]:
    output_dir = dataset_reports_dir(config)
    manifest_rows = []
    for split, items in splits.items():
        for item in items:
            manifest_rows.append(
                {
                    "original_path": item["original_path"],
                    "original_file_name": item.get("original_file_name", ""),
                    "file_name": f"{item['class_id']}/{Path(item['file']).name}",
                    "class_id": item["class_id"],
                    "source_type": item.get("source_type", ""),
                    "source_name": item.get("source_name", ""),
                    "source_identifier": item.get("source_identifier", ""),
                    "source_url": item.get("source_url", ""),
                    "license": item.get("license", ""),
                    "access_date": item.get("access_date", ""),
                    "review_batch": item.get("review_batch", "original_350"),
                    "is_local_aikmel": str(bool(item.get("is_local_aikmel", False))).lower(),
                    "location_general": item.get("location_general", ""),
                    "split": split,
                    "sha256": item["sha256"],
                    "duplicate_group": item["duplicate_group"],
                    "seed": item.get(
                        "seed",
                        int(config.get("seed", config.get("training", {}).get("seed", 42))),
                    ),
                    "caption": build_caption(config, str(item["class_id"]), item),
                    "manual_review_status": item.get("manual_review_status", ""),
                }
            )
    manifest_rows.sort(key=lambda row: (row["split"], row["class_id"], row["file_name"]))
    manifest_path = write_csv(
        output_dir / "split_manifest.csv",
        manifest_rows,
        [
            "file_name",
            "original_file_name",
            "class_id",
            "source_type",
            "source_name",
            "source_identifier",
            "source_url",
            "license",
            "access_date",
            "review_batch",
            "is_local_aikmel",
            "split",
            "duplicate_group",
            "seed",
            "caption",
            "manual_review_status",
            "original_path",
            "sha256",
            "location_general",
        ],
    )

    classes = [item["id"] for item in class_definitions(config)]
    summary = {
        "seed": int(config.get("seed", config.get("training", {}).get("seed", 42))),
        "train_ratio": float(config["dataset"].get("train_ratio", 0.8)),
        "validation_ratio": float(config["dataset"].get("validation_ratio", 0.2)),
        "total": len(manifest_rows),
        "train": len(splits.get("train", [])),
        "validation": len(splits.get("validation", [])),
        "per_class": {
            class_id: {
                "train": sum(item["class_id"] == class_id for item in splits.get("train", [])),
                "validation": sum(
                    item["class_id"] == class_id for item in splits.get("validation", [])
                ),
            }
            for class_id in classes
        },
        "per_source": {
            class_id: {
                source_type: {
                    "train": sum(
                        item["class_id"] == class_id and item.get("source_type") == source_type
                        for item in splits.get("train", [])
                    ),
                    "validation": sum(
                        item["class_id"] == class_id and item.get("source_type") == source_type
                        for item in splits.get("validation", [])
                    ),
                }
                for source_type in sorted(
                    {
                        str(item.get("source_type", ""))
                        for split_items in splits.values()
                        for item in split_items
                        if item["class_id"] == class_id
                    }
                )
            }
            for class_id in classes
        },
    }
    json_path = write_json(output_dir / "split_summary.json", summary)
    md_lines = [
        "# Split Summary",
        "",
        f"- Seed: {summary['seed']}",
        f"- Train: {summary['train']}",
        f"- Validation: {summary['validation']}",
        "",
        "## Per Class",
        "",
        "| Class | Train | Validation |",
        "| --- | ---: | ---: |",
    ]
    for class_id, counts in summary["per_class"].items():
        md_lines.append(f"| {class_id} | {counts['train']} | {counts['validation']} |")
    md_lines.extend(
        [
            "",
            "## Per Source",
            "",
            "| Class | Source | Train | Validation |",
            "| --- | --- | ---: | ---: |",
        ]
    )
    for class_id, sources in summary["per_source"].items():
        for source_type, counts in sources.items():
            md_lines.append(
                f"| {class_id} | {source_type} | {counts['train']} | {counts['validation']} |"
            )
    md_path = output_dir / "split_summary.md"
    md_path.parent.mkdir(parents=True, exist_ok=True)
    md_path.write_text("\n".join(md_lines) + "\n", encoding="utf-8")
    return {
        "manifest": str(manifest_path),
        "json": str(json_path),
        "markdown": str(md_path),
        "summary": summary,
    }
