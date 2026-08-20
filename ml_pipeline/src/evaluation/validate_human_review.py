from __future__ import annotations

import argparse
import csv
import json
import statistics
from collections import Counter, defaultdict
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

from PIL import Image, UnidentifiedImageError

CLASS_IDS = ("padi", "jagung", "cabai", "kacang_tanah")
VARIANTS = ("base", "lora")
CONFUSION_VALUES = ("none", *CLASS_IDS, "mixed", "unclear")
IDENTITY_FIELDS = (
    "condition_id",
    "variant",
    "class_id",
    "prompt",
    "seed",
    "expected_image_path",
)
REQUIRED_ASSESSMENT_FIELDS = (
    "crop_correct",
    "field_context_quality",
    "visual_realism_score",
    "class_confusion",
    "reviewer_role",
)
OPTIONAL_ASSESSMENT_FIELDS = ("reviewer_notes",)


@dataclass(frozen=True)
class HumanReviewValidation:
    valid: bool
    complete: bool
    review_csv: str
    expected_rows: int
    total_rows: int
    completed_rows: int
    partial_rows: int
    errors: list[str] = field(default_factory=list)
    summary: list[dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _image_is_valid(path: Path) -> bool:
    try:
        with Image.open(path) as image:
            width, height = image.size
            image.verify()
        return width > 0 and height > 0
    except (OSError, UnidentifiedImageError):
        return False


def _parse_score(raw_value: str, field_name: str, row_number: int, errors: list[str]) -> int:
    try:
        value = int(raw_value)
    except ValueError:
        errors.append(f"row {row_number}: {field_name} must be an integer from 1 to 5")
        return 0
    if not 1 <= value <= 5:
        errors.append(f"row {row_number}: {field_name} must be between 1 and 5")
    return value


def _build_summary(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    groups: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        groups[(row["variant"], row["class_id"])].append(row)
        groups[(row["variant"], "all")].append(row)
    summary: list[dict[str, Any]] = []
    for (variant, class_id), group in sorted(groups.items()):
        summary.append(
            {
                "variant": variant,
                "class_id": class_id,
                "reviewed": len(group),
                "crop_correct_count": sum(row["crop_correct"] for row in group),
                "crop_correct_percent": round(
                    100 * sum(row["crop_correct"] for row in group) / len(group), 2
                ),
                "field_context_quality_median": statistics.median(
                    row["field_context_quality"] for row in group
                ),
                "visual_realism_score_median": statistics.median(
                    row["visual_realism_score"] for row in group
                ),
                "confusion_count": sum(
                    row["class_confusion"] not in {"none", row["class_id"]} for row in group
                ),
                "target_confirmation_count": sum(
                    row["class_confusion"] == row["class_id"] for row in group
                ),
            }
        )
    return summary


def validate_human_review(
    review_csv: Path,
    *,
    images_root: Path | None = None,
    expected_rows: int = 72,
) -> HumanReviewValidation:
    review_csv = review_csv.resolve()
    errors: list[str] = []
    if not review_csv.is_file():
        errors.append(f"review CSV not found: {review_csv}")
        return HumanReviewValidation(
            False, False, str(review_csv), expected_rows, 0, 0, 0, errors, []
        )
    images_root = (images_root or review_csv.parent).resolve()
    try:
        with review_csv.open(encoding="utf-8-sig", newline="") as handle:
            reader = csv.DictReader(handle)
            rows = list(reader)
            fields = list(reader.fieldnames or [])
    except (OSError, csv.Error) as exc:
        errors.append(f"cannot read review CSV: {exc}")
        return HumanReviewValidation(
            False, False, str(review_csv), expected_rows, 0, 0, 0, errors, []
        )

    required_fields = (*IDENTITY_FIELDS, *REQUIRED_ASSESSMENT_FIELDS, *OPTIONAL_ASSESSMENT_FIELDS)
    missing_fields = [field for field in required_fields if field not in fields]
    if missing_fields:
        errors.append("missing review columns: " + ", ".join(missing_fields))
    if len(rows) != expected_rows:
        errors.append(f"review CSV has {len(rows)} rows; expected {expected_rows}")

    keys: set[tuple[str, str]] = set()
    condition_pairs: dict[str, dict[str, dict[str, str]]] = defaultdict(dict)
    class_variant_counts: Counter[tuple[str, str]] = Counter()
    completed: list[dict[str, Any]] = []
    partial_rows = 0
    for row_number, row in enumerate(rows, start=2):
        condition_id = row.get("condition_id", "").strip()
        variant = row.get("variant", "").strip()
        class_id = row.get("class_id", "").strip()
        prompt = row.get("prompt", "").strip()
        seed = row.get("seed", "").strip()
        if not condition_id:
            errors.append(f"row {row_number}: condition_id is blank")
        if variant not in VARIANTS:
            errors.append(f"row {row_number}: invalid variant {variant!r}")
        if class_id not in CLASS_IDS:
            errors.append(f"row {row_number}: invalid class_id {class_id!r}")
        if not prompt:
            errors.append(f"row {row_number}: prompt is blank")
        try:
            int(seed)
        except ValueError:
            errors.append(f"row {row_number}: seed must be an integer")
        key = (condition_id, variant)
        if key in keys:
            errors.append(f"row {row_number}: duplicate condition/variant {key}")
        keys.add(key)
        if condition_id and variant in VARIANTS:
            condition_pairs[condition_id][variant] = {
                "class_id": class_id,
                "prompt": prompt,
                "seed": seed,
            }
        if class_id in CLASS_IDS and variant in VARIANTS:
            class_variant_counts[(class_id, variant)] += 1

        raw_image_path = row.get("expected_image_path", "").strip()
        relative_image_path = Path(raw_image_path)
        if (
            not raw_image_path
            or relative_image_path.is_absolute()
            or ".." in relative_image_path.parts
        ):
            errors.append(f"row {row_number}: expected_image_path must be a safe relative path")
        else:
            image_path = (images_root / relative_image_path).resolve()
            try:
                image_path.relative_to(images_root)
            except ValueError:
                errors.append(f"row {row_number}: image path escapes images_root")
            else:
                if not image_path.is_file() or not _image_is_valid(image_path):
                    errors.append(f"row {row_number}: review image missing or invalid")

        assessment_values = [
            row.get(field, "").strip()
            for field in (*REQUIRED_ASSESSMENT_FIELDS, *OPTIONAL_ASSESSMENT_FIELDS)
        ]
        required_values = [row.get(field, "").strip() for field in REQUIRED_ASSESSMENT_FIELDS]
        if not any(assessment_values):
            continue
        if not all(required_values):
            partial_rows += 1
            errors.append(f"row {row_number}: assessment is partially filled")
            continue

        crop_correct_raw = row["crop_correct"].strip().casefold()
        if crop_correct_raw not in {"true", "false"}:
            errors.append(f"row {row_number}: crop_correct must be true or false")
        context_score = _parse_score(
            row["field_context_quality"].strip(),
            "field_context_quality",
            row_number,
            errors,
        )
        realism_score = _parse_score(
            row["visual_realism_score"].strip(),
            "visual_realism_score",
            row_number,
            errors,
        )
        confusion = row["class_confusion"].strip().casefold()
        if confusion not in CONFUSION_VALUES:
            errors.append(f"row {row_number}: class_confusion must be one of {CONFUSION_VALUES}")
        reviewer_role = row["reviewer_role"].strip()
        if not 2 <= len(reviewer_role) <= 100:
            errors.append(f"row {row_number}: reviewer_role length must be 2-100")
        reviewer_notes = row.get("reviewer_notes", "")
        if len(reviewer_notes) > 2000:
            errors.append(f"row {row_number}: reviewer_notes exceeds 2000 characters")
        completed.append(
            {
                "condition_id": condition_id,
                "variant": variant,
                "class_id": class_id,
                "crop_correct": crop_correct_raw == "true",
                "field_context_quality": context_score,
                "visual_realism_score": realism_score,
                "class_confusion": confusion,
            }
        )

    if expected_rows % len(VARIANTS) != 0:
        errors.append("expected_rows must be divisible by the two review variants")
    else:
        expected_conditions = expected_rows // len(VARIANTS)
        if len(condition_pairs) != expected_conditions:
            errors.append(
                f"review CSV has {len(condition_pairs)} conditions; "
                f"expected {expected_conditions} paired conditions"
            )
    for condition_id, variants in sorted(condition_pairs.items()):
        missing_variants = [variant for variant in VARIANTS if variant not in variants]
        if missing_variants:
            errors.append(
                f"condition {condition_id}: missing variants {', '.join(missing_variants)}"
            )
            continue
        base_identity = variants["base"]
        lora_identity = variants["lora"]
        for field_name in ("class_id", "prompt", "seed"):
            if base_identity[field_name] != lora_identity[field_name]:
                errors.append(
                    f"condition {condition_id}: base/lora {field_name} values do not match"
                )

    if expected_rows == 72:
        expected_per_class_variant = expected_rows // (len(CLASS_IDS) * len(VARIANTS))
        for class_id in CLASS_IDS:
            for variant in VARIANTS:
                count = class_variant_counts[(class_id, variant)]
                if count != expected_per_class_variant:
                    errors.append(
                        f"class {class_id}/{variant}: {count} rows; "
                        f"expected {expected_per_class_variant}"
                    )

    complete = not errors and len(completed) == expected_rows and partial_rows == 0
    return HumanReviewValidation(
        valid=not errors,
        complete=complete,
        review_csv=str(review_csv),
        expected_rows=expected_rows,
        total_rows=len(rows),
        completed_rows=len(completed),
        partial_rows=partial_rows,
        errors=errors,
        summary=_build_summary(completed) if not errors and completed else [],
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Validate real human LoRA review entries.")
    parser.add_argument("--review-csv", type=Path, required=True)
    parser.add_argument("--images-root", type=Path)
    parser.add_argument("--expected-rows", type=int, default=72)
    parser.add_argument("--require-complete", action="store_true")
    parser.add_argument("--report-json", type=Path)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    result = validate_human_review(
        args.review_csv,
        images_root=args.images_root,
        expected_rows=args.expected_rows,
    )
    output = json.dumps(result.to_dict(), indent=2)
    print(output)
    if args.report_json:
        args.report_json.parent.mkdir(parents=True, exist_ok=True)
        args.report_json.write_text(output + "\n", encoding="utf-8")
    if not result.valid or (args.require_complete and not result.complete):
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
