from __future__ import annotations

import csv
import random
from collections import Counter
from datetime import date
from pathlib import Path
from typing import Any

from PIL import Image

from ml_pipeline.src.common.config import (
    class_definitions,
    dataset_reports_dir,
    dataset_review_dir,
    resolve_path,
)
from ml_pipeline.src.dataset.caption_dataset import write_metadata
from ml_pipeline.src.dataset.curate_dataset import (
    reset_processed_directory,
    write_curation_mapping,
)
from ml_pipeline.src.dataset.dataset_inventory import build_inventory, write_inventory
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
    inspect_manual_review,
    write_manual_review_reports,
)
from ml_pipeline.src.dataset.detect_duplicates import (
    add_perceptual_hashes,
    assign_duplicate_groups,
    duplicate_report,
)
from ml_pipeline.src.dataset.models import ImageRecord
from ml_pipeline.src.dataset.provenance import (
    provenance_warnings,
    sync_source_manifest,
    write_provenance_warnings,
)
from ml_pipeline.src.dataset.split_dataset import split_dataset
from ml_pipeline.src.dataset.validate_images import validate_records
from ml_pipeline.src.dataset.validate_metadata import (
    validate_metadata_paths,
    write_metadata_validation_reports,
)

IDENTITY_FIELDS = (
    "curated_file_name",
    "original_file_name",
    "class_id",
    "source_type",
    "sha256",
    "review_batch",
)


def _read_csv(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open(newline="", encoding="utf-8-sig") as handle:
        return [dict(row) for row in csv.DictReader(handle)]


def _normalize_mapping_types(
    mapping: list[dict[str, str]],
) -> list[dict[str, object]]:
    normalized: list[dict[str, object]] = []
    for row in mapping:
        normalized.append(
            {
                **row,
                "is_local_aikmel": str(row.get("is_local_aikmel", "")).strip().casefold()
                in {"1", "true", "yes", "ya"},
            }
        )
    return normalized


def _validate_review_identity(
    mapping: list[dict[str, str]],
    review_rows: list[dict[str, str]],
) -> None:
    mapping_by_name = {str(row.get("curated_file_name", "")).strip(): row for row in mapping}
    if len(mapping_by_name) != len(mapping):
        raise ValueError("Curation mapping contains an empty or duplicate candidate name")
    review_by_name = {str(row.get("curated_file_name", "")).strip(): row for row in review_rows}
    if len(review_by_name) != len(review_rows):
        raise ValueError("Manual review CSV contains an empty or duplicate candidate name")
    if set(mapping_by_name) != set(review_by_name):
        raise ValueError("Manual review candidates do not match the curation mapping")

    candidates_root = dataset_review_candidates_dir_from_mapping(mapping)
    for name, expected in mapping_by_name.items():
        actual = review_by_name[name]
        for field in IDENTITY_FIELDS:
            expected_value = str(expected.get(field, "")).strip()
            actual_value = str(actual.get(field, "")).strip()
            if field == "review_batch":
                expected_value = expected_value or "original_350"
                actual_value = actual_value or "original_350"
            if expected_value != actual_value:
                raise ValueError(f"Review identity field '{field}' changed for {name}")
        class_id = str(expected.get("class_id", ""))
        source_type = str(expected.get("source_type", ""))
        if class_id != "padi" and source_type != "public":
            raise ValueError(f"Public-only source policy failed for {name}")
        if source_type == "local_aikmel" and class_id != "padi":
            raise ValueError(f"Invalid local source policy for {name}")
        if str(expected.get("technical_status", "")).casefold() != "valid":
            raise ValueError(f"Candidate is not technically valid: {name}")
        image_path = candidates_root / class_id / name
        if not image_path.is_file():
            raise ValueError(f"Reviewed candidate image is missing: {image_path}")
        with Image.open(image_path) as image:
            image.verify()


def dataset_review_candidates_dir_from_mapping(
    mapping: list[dict[str, str]],
) -> Path:
    for row in mapping:
        value = str(row.get("curated_path", "")).strip()
        if value:
            path = Path(value).resolve()
            if len(path.parents) >= 2:
                return path.parents[1]
    raise ValueError("Curation mapping has no candidate paths")


def _select_with_class_caps(
    config: dict[str, Any],
    reviewed: list[dict[str, object]],
) -> tuple[list[dict[str, object]], list[dict[str, object]]]:
    seed = int(config.get("seed", 42))
    selected_names: set[str] = set()
    for class_info in class_definitions(config):
        class_id = str(class_info["id"])
        accepted = [
            row
            for row in reviewed
            if row.get("class_id") == class_id and row.get("manual_review_status") == "yes"
        ]
        maximum = int(class_info.get("target_maximum_images", 100) or 100)
        ordered = sorted(
            accepted,
            key=lambda row: (
                str(row.get("sha256", "")),
                str(row.get("curated_file_name", "")),
            ),
        )
        random.Random(f"{seed}:final-cap:{class_id}").shuffle(ordered)
        selected_names.update(str(row["curated_file_name"]) for row in ordered[:maximum])

    updated: list[dict[str, object]] = []
    selected: list[dict[str, object]] = []
    for row in reviewed:
        item = dict(row)
        name = str(item.get("curated_file_name", ""))
        if item.get("manual_review_status") == "yes" and name not in selected_names:
            item["validation_status"] = "manual_approved_excluded_by_class_cap"
            item["final_status"] = "excluded_above_class_maximum"
            item["rejection_reason"] = ""
        elif item.get("manual_review_status") == "yes":
            item["validation_status"] = "manual_approved"
            item["final_status"] = "accepted_for_final"
            selected.append(item)
        updated.append(item)
    return updated, selected


def _target_shortfalls(
    config: dict[str, Any], accepted: list[dict[str, object]]
) -> dict[str, dict[str, int]]:
    counts = Counter(str(row.get("class_id", "")) for row in accepted)
    result: dict[str, dict[str, int]] = {}
    for class_info in class_definitions(config):
        class_id = str(class_info["id"])
        minimum = int(class_info.get("target_minimum_images", 80))
        if counts[class_id] < minimum:
            result[class_id] = {
                "accepted": counts[class_id],
                "minimum": minimum,
                "shortfall": minimum - counts[class_id],
            }
    return result


def _additional_record(row: dict[str, object]) -> ImageRecord:
    path = Path(str(row["original_path"]))
    if not path.is_file():
        raise ValueError(f"Additional source image is missing: {path}")
    suffix = path.suffix.casefold()
    with Image.open(path) as image:
        image_format = image.format or ""
        color_mode = image.mode
    return ImageRecord(
        original_path=str(path),
        class_id=str(row["class_id"]),
        display_name=str(row.get("display_name", "")),
        trigger_token=str(row.get("trigger_token", "")),
        file_name=str(row.get("original_file_name", path.name)),
        extension=suffix,
        format=image_format,
        width=int(row.get("width", 0) or 0),
        height=int(row.get("height", 0) or 0),
        color_mode=color_mode,
        file_size=path.stat().st_size,
        sha256=str(row.get("sha256", "")),
        original_file_name=str(row.get("original_file_name", path.name)),
        source_type=str(row.get("source_type", "public")),
        source_name=str(row.get("source_name", "")),
        source_identifier=str(row.get("source_identifier", "")),
        source_url=str(row.get("source_url", "")),
        license=str(row.get("license", "")),
        access_date=str(row.get("access_date", "")),
        is_local_aikmel=False,
        capture_date=str(row.get("capture_date", "")),
        location_general=str(row.get("location_general", "")),
        photographer=str(row.get("photographer", "")),
        permission_status=str(row.get("permission_status", "")),
        review_status=str(row.get("manual_review_status", "")),
        notes=str(row.get("notes", "")),
        perceptual_hash=str(row.get("perceptual_hash", "")),
        status="valid",
        duplicate_group=str(row.get("duplicate_group", "")),
        duplicate_warning=str(row.get("duplicate_warning", "")),
    )


def _audit_records_with_additions(
    config: dict[str, Any], reviewed: list[dict[str, object]]
) -> tuple[list[ImageRecord], dict[str, list[dict[str, object]]]]:
    raw = add_perceptual_hashes(validate_records(config, build_inventory(config)))
    additions = [
        _additional_record(row)
        for row in reviewed
        if str(row.get("review_batch", "") or "original_350") != "original_350"
    ]
    records = [*raw, *additions]
    records = validate_records(config, records)
    records = add_perceptual_hashes(records)
    duplicates = duplicate_report(config, records)
    return assign_duplicate_groups(records, duplicates), duplicates


def _write_audit_outputs(
    config: dict[str, Any],
    records: list[ImageRecord],
    duplicates: dict[str, list[dict[str, object]]],
    splits: dict[str, list[dict[str, object]]] | None = None,
    manual_rows: list[dict[str, object]] | None = None,
    metadata_validation: dict[str, object] | None = None,
    split_summary: dict[str, object] | None = None,
) -> dict[str, object]:
    inventory = write_inventory(config, records)
    duplicate_paths = write_duplicate_reports(config, duplicates)
    collision_path = write_filename_collision_report(config, records)
    provenance_path = write_provenance_warnings(config, records)
    warnings = provenance_warnings(records)
    audit_summary = write_audit_summary(config, records, duplicates, len(warnings))
    class_balance = build_class_balance(config, records, splits, review_rows=manual_rows)
    class_balance_path = write_class_balance_report(config, class_balance)
    source_distribution_path = write_source_distribution_report(
        config, build_source_distribution(config, records, splits)
    )
    report = write_dataset_report(
        config,
        records,
        duplicates,
        metadata_validation,
        class_balance,
        split_summary,
    )
    return {
        "inventory": inventory,
        "duplicates": duplicate_paths,
        "file_name_collisions": collision_path,
        "source_manifest": sync_source_manifest(config, records),
        "provenance_warnings": provenance_path,
        "provenance_warning_count": len(warnings),
        "audit_summary": audit_summary,
        "class_balance": class_balance_path,
        "source_distribution": source_distribution_path,
        "report": report,
    }


def _write_final_dataset_card(
    config: dict[str, Any],
    records: list[ImageRecord],
    reviewed: list[dict[str, object]],
    splits: dict[str, list[dict[str, object]]],
    metadata_validation: dict[str, object],
) -> str:
    configured_path = config["dataset"].get("dataset_card")
    path = (
        resolve_path(configured_path)
        if configured_path
        else dataset_reports_dir(config) / "DATASET_CARD.md"
    )
    accepted = Counter(
        str(row.get("class_id", "")) for row in reviewed if row.get("manual_review_status") == "yes"
    )
    rejected = Counter(
        str(row.get("class_id", "")) for row in reviewed if row.get("manual_review_status") == "no"
    )
    selected = Counter(
        str(row.get("class_id", ""))
        for row in reviewed
        if row.get("final_status") == "accepted_for_final"
    )
    unknown_public_provenance = sum(
        row.get("final_status") == "accepted_for_final"
        and row.get("source_type") == "public"
        and not all(
            str(row.get(field, "")).strip()
            for field in ("source_name", "source_identifier", "source_url", "license")
        )
        for row in reviewed
    )
    lines = [
        "# Dataset Card - TaniAdaptif Multicrop",
        "",
        f"Tanggal finalisasi: {date.today().isoformat()}  ",
        f"Status metadata: **{'valid' if metadata_validation.get('valid') else 'invalid'}**.",
        "",
        "Dataset ini disiapkan untuk fine-tuning LoRA Stable Diffusion 1.5 sebagai simulasi visual tanaman. Model visual tidak menentukan rekomendasi agronomi; rekomendasi tetap berasal dari rule-based engine dan data BMKG.",
        "",
        "## Komoditas, Sumber, dan Split",
        "",
        "| Kelas | Trigger | Kebijakan sumber | Audit files | Human accepted | Human rejected | Final | Train | Validation |",
        "| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for class_info in class_definitions(config):
        class_id = str(class_info["id"])
        policy = "public + local_aikmel" if class_id == "padi" else "public only"
        lines.append(
            f"| {class_id} | `{class_info['trigger_token']}` | {policy} | "
            f"{sum(record.class_id == class_id for record in records)} | {accepted[class_id]} | "
            f"{rejected[class_id]} | {selected[class_id]} | "
            f"{sum(row['class_id'] == class_id for row in splits['train'])} | "
            f"{sum(row['class_id'] == class_id for row in splits['validation'])} |"
        )
    lines.extend(
        [
            "",
            "## Kurasi",
            "",
            "Semua gambar final memiliki keputusan manusia `accepted=yes`. Kelas dibatasi maksimum 100 gambar secara deterministik dengan seed 42. Split 80:20 mempertahankan kelas, aturan sumber padi, dan isolasi duplicate group.",
            "",
            "Kandidat tambahan berasal dari dataset akademik CC BY 4.0 yang didokumentasikan dalam `docs/DATASET_ADDITIONAL_SOURCES.md`; provenance per gambar dipertahankan dalam source manifest, curation mapping, dan split manifest.",
            "",
            "## Lisensi dan Batasan",
            "",
            f"- Gambar final public dengan metadata provenance lama yang belum lengkap: {unknown_public_provenance}.",
            "- Ketiadaan metadata lisensi bukan bukti bahwa hak penggunaan tersedia. Verifikasi provenance tetap diperlukan sebelum redistribusi publik atau penggunaan komersial.",
            "- Dataset public membawa bias wilayah, kamera, varietas, fase tumbuh, dan komposisi.",
            "- Kelas selain padi tidak diklaim mewakili kondisi khusus Aikmel.",
            "- Trigger `taniadaptif_*` adalah identifier kelas model, bukan klaim lokasi.",
            "- Belum ada hasil training atau evaluasi LoRA yang diklaim oleh dataset card ini.",
            "",
            "## Caption",
            "",
            "Caption menyebut trigger kelas, tanaman yang tumbuh di lingkungan pertanian, dan pencahayaan alami. Caption tidak menebak cuaca, musim, tanah, atau fase pertumbuhan.",
        ]
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return str(path)


def finalize_reviewed_dataset(config: dict[str, Any]) -> dict[str, object]:
    reports_dir = dataset_reports_dir(config)
    mapping_path = reports_dir / "curation_mapping.csv"
    review_path = dataset_review_dir(config) / "manual_review_template.csv"
    mapping = _read_csv(mapping_path)
    review_rows = _read_csv(review_path)
    if not mapping or not review_rows:
        raise ValueError("Curation mapping or manual review CSV is missing")
    _validate_review_identity(mapping, review_rows)

    review_status = inspect_manual_review(config, mapping)
    if not review_status["complete"]:
        return {
            "status": "manual_review_required",
            "final_dataset_created": False,
            "manual_review": review_status,
        }

    reviewed = apply_manual_review(config, _normalize_mapping_types(mapping))
    human_accepted = [row for row in reviewed if row.get("manual_review_status") == "yes"]
    shortfalls = _target_shortfalls(config, human_accepted)
    records, duplicates = _audit_records_with_additions(config, reviewed)
    if shortfalls:
        write_curation_mapping(config, reviewed)
        manual_reports = write_manual_review_reports(config, records, reviewed)
        audit = _write_audit_outputs(
            config,
            records,
            duplicates,
            manual_rows=list(manual_reports["rows"]),
        )
        reset_processed_directory(config)
        return {
            "status": "insufficient_final_images",
            "final_dataset_created": False,
            "review_batch": "additional_batch_v1",
            "shortfalls": shortfalls,
            "next_batch": "additional_batch_v2",
            "next_batch_candidate_targets": {
                class_id: max(1, (item["shortfall"] * 13 + 9) // 10)
                for class_id, item in shortfalls.items()
            },
            "manual_review": review_status,
            "manual_review_reports": manual_reports,
            "audit": audit,
        }

    reviewed, selected = _select_with_class_caps(config, reviewed)
    write_curation_mapping(config, reviewed)
    manual_reports = write_manual_review_reports(config, records, reviewed)
    reset_processed_directory(config)
    splits = split_dataset(config, selected)
    split_paths = write_split_reports(config, splits)
    metadata_paths = write_metadata(config, splits)
    metadata_validation = validate_metadata_paths(metadata_paths, config)
    metadata_validation_paths = write_metadata_validation_reports(config, metadata_validation)
    audit = _write_audit_outputs(
        config,
        records,
        duplicates,
        splits=splits,
        manual_rows=list(manual_reports["rows"]),
        metadata_validation=metadata_validation,
        split_summary=dict(split_paths["summary"]),
    )
    dataset_card = _write_final_dataset_card(config, records, reviewed, splits, metadata_validation)
    return {
        "status": (
            "final_dataset_prepared" if metadata_validation["valid"] else "metadata_invalid"
        ),
        "final_dataset_created": True,
        "package_created": False,
        "review_batch_count": Counter(
            str(row.get("review_batch", "") or "original_350") for row in reviewed
        ),
        "human_accepted_count": len(human_accepted),
        "selected_count": len(selected),
        "selected_per_class": dict(Counter(str(row["class_id"]) for row in selected)),
        "excluded_above_class_maximum": len(human_accepted) - len(selected),
        "processed_directory": str(resolve_path(config["dataset"]["processed_directory"])),
        "curation_mapping": str(mapping_path),
        "split_counts": {split: len(rows) for split, rows in splits.items()},
        "split_reports": {key: value for key, value in split_paths.items() if key != "summary"},
        "metadata": metadata_paths,
        "metadata_validation": metadata_validation,
        "metadata_validation_reports": metadata_validation_paths,
        "manual_review": review_status,
        "manual_review_reports": manual_reports,
        "dataset_card": dataset_card,
        "audit": audit,
    }
