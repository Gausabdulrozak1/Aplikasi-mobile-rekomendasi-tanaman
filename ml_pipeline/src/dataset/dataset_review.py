from __future__ import annotations

import csv
import random
from collections import Counter
from pathlib import Path
from typing import Any

from PIL import Image, ImageDraw, ImageOps

from ml_pipeline.src.common.config import class_definitions, dataset_reports_dir, dataset_review_dir
from ml_pipeline.src.dataset.io_utils import write_csv
from ml_pipeline.src.dataset.models import ImageRecord

REVIEW_CONTEXT_FIELDS = [
    "curated_file_name",
    "review_batch",
    "original_file_name",
    "original_path",
    "class_id",
    "source_type",
    "is_local_aikmel",
    "width",
    "height",
    "sha256",
    "duplicate_group",
    "duplicate_warning",
]

HUMAN_REVIEW_FIELDS = [
    "crop_correct",
    "shows_plant",
    "shows_whole_plant_or_multiple_plants",
    "shows_field_or_growing_environment",
    "too_close_up",
    "harvested_product_only",
    "food_or_market_image",
    "watermark_present",
    "blurred",
    "severe_occlusion",
    "near_duplicate_excessive",
    "ai_generated_suspected",
    "accepted",
    "reviewer_notes",
]

REVIEW_FIELDS = REVIEW_CONTEXT_FIELDS + HUMAN_REVIEW_FIELDS
VALID_ACCEPTED_VALUES = {"yes", "no", "unsure"}


def create_dataset_review(
    config: dict[str, Any],
    curated: list[dict[str, object]],
) -> dict[str, object]:
    review_dir = dataset_review_dir(config)
    review_dir.mkdir(parents=True, exist_ok=True)
    template_path = review_dir / "manual_review_template.csv"
    existing = _read_existing_review(template_path)
    seed = int(config.get("seed", 42))
    page_size = max(20, int(config["dataset"].get("review_sample_per_class", 20)))

    template_rows = [_review_row(item, existing) for item in _ordered_items(curated)]
    write_csv(template_path, template_rows, REVIEW_FIELDS)
    _write_instructions(review_dir / "MANUAL_REVIEW_INSTRUCTIONS.md")

    for old_sheet in review_dir.glob("review_*.jpg"):
        old_sheet.unlink()

    sheets: dict[str, list[str]] = {}
    warnings: list[str] = []
    for class_info in class_definitions(config):
        class_id = str(class_info["id"])
        class_items = [item for item in curated if str(item["class_id"]) == class_id]
        selected = _source_aware_sample(class_items, len(class_items), seed, class_id)
        if len(selected) < 20:
            warnings.append(
                f"Class {class_id} has only {len(selected)} candidates for manual review"
            )
        class_sheets: list[str] = []
        for page_index, offset in enumerate(range(0, len(selected), page_size), start=1):
            page = selected[offset : offset + page_size]
            sheet_path = review_dir / f"review_{class_id}_{page_index:02d}.jpg"
            _write_contact_sheet(page, sheet_path, class_id, page_index)
            class_sheets.append(str(sheet_path))
        sheets[class_id] = class_sheets

    status = inspect_manual_review(config, curated)
    return {
        "contact_sheets": sheets,
        "template": str(template_path),
        "instructions": str(review_dir / "MANUAL_REVIEW_INSTRUCTIONS.md"),
        "candidate_count": len(template_rows),
        "manual_review": status,
        "warnings": warnings,
    }


def inspect_manual_review(
    config: dict[str, Any],
    curated: list[dict[str, object]],
) -> dict[str, object]:
    template_path = dataset_review_dir(config) / "manual_review_template.csv"
    rows = _read_csv(template_path)
    expected = {str(item["curated_file_name"]): item for item in curated}
    indexed: dict[str, dict[str, str]] = {}
    duplicate_names: list[str] = []
    unexpected_names: list[str] = []
    invalid_values: list[str] = []

    for row in rows:
        name = str(row.get("curated_file_name", "")).strip()
        if not name:
            continue
        if name in indexed:
            duplicate_names.append(name)
            continue
        indexed[name] = row
        if name not in expected:
            unexpected_names.append(name)

    missing_names = sorted(set(expected) - set(indexed))
    accepted_count = 0
    rejected_count = 0
    unsure_count = 0
    pending_count = 0
    rejected_without_notes: list[str] = []
    decisions: dict[str, str] = {}
    for name in sorted(expected):
        value = str(indexed.get(name, {}).get("accepted", "")).strip().casefold()
        decisions[name] = value
        if value == "yes":
            accepted_count += 1
        elif value == "no":
            rejected_count += 1
            if not str(indexed[name].get("reviewer_notes", "")).strip():
                rejected_without_notes.append(name)
        elif value == "unsure":
            unsure_count += 1
        elif value:
            invalid_values.append(name)
        else:
            pending_count += 1

    complete = bool(expected) and not (
        missing_names
        or duplicate_names
        or unexpected_names
        or invalid_values
        or pending_count
        or unsure_count
    )
    return {
        "complete": complete,
        "template": str(template_path),
        "expected_rows": len(expected),
        "present_rows": len(indexed),
        "accepted": accepted_count,
        "rejected": rejected_count,
        "unsure": unsure_count,
        "pending": pending_count,
        "missing_curated_files": missing_names,
        "duplicate_curated_files": sorted(set(duplicate_names)),
        "unexpected_curated_files": sorted(set(unexpected_names)),
        "invalid_accepted_values": sorted(set(invalid_values)),
        "rejected_without_notes": rejected_without_notes,
        "decisions": decisions,
    }


def apply_manual_review(
    config: dict[str, Any],
    curated: list[dict[str, object]],
) -> list[dict[str, object]]:
    rows = _read_csv(dataset_review_dir(config) / "manual_review_template.csv")
    by_name = {str(row.get("curated_file_name", "")).strip(): row for row in rows}
    reviewed: list[dict[str, object]] = []
    for item in curated:
        name = str(item["curated_file_name"])
        row = by_name.get(name, {})
        accepted = str(row.get("accepted", "")).strip().casefold()
        notes = str(row.get("reviewer_notes", "")).strip()
        updated = dict(item)
        updated["manual_review_status"] = accepted or "pending"
        updated["reviewer_notes"] = notes
        if accepted == "yes":
            updated["validation_status"] = "manual_approved"
            updated["final_status"] = "accepted_for_final"
            updated["rejection_reason"] = ""
        elif accepted == "no":
            updated["validation_status"] = "manual_rejected"
            updated["final_status"] = "rejected_manual"
            updated["rejection_reason"] = notes or "manual_review_rejected"
        elif accepted == "unsure":
            updated["validation_status"] = "manual_unsure"
            updated["final_status"] = "pending_manual_review"
            updated["rejection_reason"] = ""
        else:
            updated["validation_status"] = "technical_valid_pending_manual_review"
            updated["final_status"] = "pending_manual_review"
        reviewed.append(updated)
    return reviewed


def write_manual_review_reports(
    config: dict[str, Any],
    records: list[ImageRecord],
    curated: list[dict[str, object]],
) -> dict[str, object]:
    reports_dir = dataset_reports_dir(config)
    semantic_rows = _read_csv(reports_dir / "automated_semantic_review.csv")
    semantic_by_name = {
        str(row.get("curated_file_name", "")): str(row.get("screening_status", ""))
        for row in semantic_rows
    }
    rows: list[dict[str, object]] = []
    for class_info in class_definitions(config):
        class_id = str(class_info["id"])
        raw = [record for record in records if record.class_id == class_id]
        candidates = [item for item in curated if item["class_id"] == class_id]
        accepted = [item for item in candidates if item["manual_review_status"] == "yes"]
        final = [
            item
            for item in accepted
            if str(item.get("final_status", "accepted_for_final")) == "accepted_for_final"
        ]
        excluded_above_maximum = [
            item
            for item in accepted
            if str(item.get("final_status", "")) == "excluded_above_class_maximum"
        ]
        rejected = [item for item in candidates if item["manual_review_status"] == "no"]
        unsure = [item for item in candidates if item["manual_review_status"] == "unsure"]
        pending = [item for item in candidates if item["manual_review_status"] == "pending"]
        proxy_pass = sum(
            semantic_by_name.get(str(item["curated_file_name"])) == "proxy_pass"
            for item in candidates
        )
        proxy_review = sum(
            semantic_by_name.get(str(item["curated_file_name"])) == "proxy_review"
            for item in candidates
        )
        minimum = int(class_info.get("target_minimum_images", 80))
        rows.append(
            {
                "class_id": class_id,
                "raw": len(raw),
                "technical_valid": sum(record.status == "valid" for record in raw),
                "technical_rejected": sum(record.status != "valid" for record in raw),
                "proxy_pass": proxy_pass,
                "proxy_review": proxy_review,
                "accepted": len(accepted),
                "rejected": len(rejected),
                "unsure": len(unsure),
                "pending": len(pending),
                "manual_accepted": len(accepted),
                "manual_rejected": len(rejected),
                "excluded_above_maximum": len(excluded_above_maximum),
                "final_valid": len(final),
                "final_public": sum(item["source_type"] == "public" for item in final),
                "final_local_aikmel": sum(item["source_type"] == "local_aikmel" for item in final),
                "shortfall_to_minimum": max(0, minimum - len(final)),
            }
        )

    fields = [
        "class_id",
        "raw",
        "technical_valid",
        "technical_rejected",
        "proxy_pass",
        "proxy_review",
        "accepted",
        "rejected",
        "unsure",
        "pending",
        "manual_accepted",
        "manual_rejected",
        "excluded_above_maximum",
        "final_valid",
        "final_public",
        "final_local_aikmel",
        "shortfall_to_minimum",
    ]
    csv_path = write_csv(reports_dir / "manual_review_summary.csv", rows, fields)
    md_lines = [
        "# Final Curation Summary",
        "",
        "Manual review decisions are applied exactly as recorded in the review CSV.",
        "",
        "| Class | Raw | Technical valid | Proxy pass | Proxy review | Accepted | Rejected | Unsure | Pending | Capped | Final valid | Public | Local Aikmel | Shortfall |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for row in rows:
        md_lines.append(
            f"| {row['class_id']} | {row['raw']} | {row['technical_valid']} | "
            f"{row['proxy_pass']} | {row['proxy_review']} | {row['accepted']} | "
            f"{row['rejected']} | {row['unsure']} | {row['pending']} | "
            f"{row['excluded_above_maximum']} | "
            f"{row['final_valid']} | {row['final_public']} | "
            f"{row['final_local_aikmel']} | {row['shortfall_to_minimum']} |"
        )
    md_path = reports_dir / "final_curation_summary.md"
    md_path.write_text("\n".join(md_lines) + "\n", encoding="utf-8")
    return {"csv": str(csv_path), "markdown": str(md_path), "rows": rows}


def _read_existing_review(path: Path) -> dict[str, dict[str, str]]:
    existing: dict[str, dict[str, str]] = {}
    for row in _read_csv(path):
        name = str(row.get("curated_file_name", "")).strip()
        if not name:
            name = Path(str(row.get("file_name", ""))).name
        if name:
            existing[name] = row
    return existing


def _read_csv(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open(newline="", encoding="utf-8-sig") as handle:
        return [dict(row) for row in csv.DictReader(handle)]


def _review_row(
    item: dict[str, object],
    existing: dict[str, dict[str, str]],
) -> dict[str, object]:
    name = str(item["curated_file_name"])
    previous = existing.get(name, {})
    same_image = all(
        not previous.get(field)
        or str(previous.get(field, "")).strip() == str(item.get(field, "")).strip()
        for field in ("original_file_name", "class_id", "source_type", "sha256")
    )
    row: dict[str, object] = {
        "curated_file_name": name,
        "review_batch": item.get("review_batch", "original_350"),
        "original_file_name": item.get("original_file_name", ""),
        "original_path": item.get("original_path", ""),
        "class_id": item.get("class_id", ""),
        "source_type": item.get("source_type", ""),
        "is_local_aikmel": str(bool(item.get("is_local_aikmel", False))).lower(),
        "width": item.get("width", ""),
        "height": item.get("height", ""),
        "sha256": item.get("sha256", ""),
        "duplicate_group": item.get("duplicate_group", ""),
        "duplicate_warning": item.get("duplicate_warning", ""),
    }
    for field in HUMAN_REVIEW_FIELDS:
        row[field] = previous.get(field, "") if same_image else ""
    return row


def _ordered_items(curated: list[dict[str, object]]) -> list[dict[str, object]]:
    return sorted(
        curated,
        key=lambda item: (str(item["class_id"]), str(item["curated_file_name"])),
    )


def _source_aware_sample(
    items: list[dict[str, object]],
    sample_size: int,
    seed: int,
    class_id: str,
) -> list[dict[str, object]]:
    by_source: dict[str, list[dict[str, object]]] = {}
    for item in items:
        by_source.setdefault(str(item.get("source_type", "")), []).append(item)
    for source_type, source_items in by_source.items():
        source_items.sort(key=lambda row: str(row.get("sha256", row["curated_file_name"])))
        random.Random(f"{seed}:review:{class_id}:{source_type}").shuffle(source_items)

    selected: list[dict[str, object]] = []
    offsets = Counter({source_type: 0 for source_type in by_source})
    while len(selected) < min(sample_size, len(items)):
        added = False
        for source_type in sorted(by_source):
            offset = offsets[source_type]
            if offset >= len(by_source[source_type]):
                continue
            selected.append(by_source[source_type][offset])
            offsets[source_type] += 1
            added = True
            if len(selected) >= sample_size:
                break
        if not added:
            break
    return selected


def _write_contact_sheet(
    items: list[dict[str, object]],
    target: Path,
    class_id: str,
    page_index: int,
) -> Path:
    columns = 4
    tile_width = 320
    tile_height = 280
    header_height = 48
    rows = max(1, (len(items) + columns - 1) // columns)
    sheet = Image.new("RGB", (columns * tile_width, header_height + rows * tile_height), "white")
    draw = ImageDraw.Draw(sheet)
    draw.text((12, 15), f"Manual review: {class_id} | page {page_index:02d}", fill="black")

    for index, item in enumerate(items):
        x = (index % columns) * tile_width
        y = header_height + (index // columns) * tile_height
        with Image.open(Path(str(item["curated_path"]))) as image:
            thumb = ImageOps.contain(ImageOps.exif_transpose(image).convert("RGB"), (300, 205))
        image_x = x + (tile_width - thumb.width) // 2
        sheet.paste(thumb, (image_x, y + 4))
        duplicate = str(item.get("duplicate_warning", "")) or "none"
        draw.text((x + 8, y + 215), str(item["curated_file_name"]), fill="black")
        draw.text(
            (x + 8, y + 232),
            f"source: {item.get('source_type', '')} | {item.get('width')}x{item.get('height')}",
            fill="black",
        )
        draw.text((x + 8, y + 249), f"duplicate: {duplicate}", fill="black")

    target.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(target, quality=92)
    return target


def _write_instructions(path: Path) -> None:
    content = """# Instruksi Review Manual Dataset

1. Jalankan `npm run dataset-review` dari root repository.
2. Buka `http://127.0.0.1:4173` dan periksa setiap gambar.
3. Pilih Terima, Tolak, atau Ragu. Tambahkan alasan untuk penolakan bila sesuai.
4. Setelah seluruh keputusan adalah Terima atau Tolak, klik Finalisasi Review.

Nilai kosong atau Ragu, baris hilang, nama file ganda, dan identitas yang berubah
akan menahan pembuatan dataset final. Proxy otomatis tidak menggantikan keputusan manusia.
"""
    path.write_text(content, encoding="utf-8")
