from __future__ import annotations

import csv
from pathlib import Path

from PIL import Image

from ml_pipeline.scripts.materialize_kaggle_evidence import _write_local_human_template
from ml_pipeline.src.evaluation.validate_human_review import validate_human_review

FIELDS = [
    "condition_id",
    "variant",
    "class_id",
    "prompt",
    "seed",
    "expected_image_path",
    "crop_correct",
    "field_context_quality",
    "visual_realism_score",
    "class_confusion",
    "reviewer_role",
    "reviewer_notes",
]


def _write_fixture(path: Path, *, complete: bool, invalid_score: bool = False) -> None:
    generated = path.parent / "generated"
    generated.mkdir()
    rows = []
    for variant in ("base", "lora"):
        image_name = f"{variant}.png"
        Image.new("RGB", (2, 2), (0, 128, 0)).save(generated / image_name)
        rows.append(
            {
                "condition_id": "padi_p1_s42",
                "variant": variant,
                "class_id": "padi",
                "prompt": "fixture prompt",
                "seed": "42",
                "expected_image_path": f"generated/{image_name}",
                "crop_correct": "true" if complete else "",
                "field_context_quality": "6" if invalid_score else ("4" if complete else ""),
                "visual_realism_score": "3" if complete else "",
                "class_confusion": "padi" if complete else "",
                "reviewer_role": "peneliti" if complete else "",
                "reviewer_notes": "",
            }
        )
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(rows)


def test_human_review_validator_accepts_complete_real_rows(tmp_path: Path) -> None:
    review = tmp_path / "review.csv"
    _write_fixture(review, complete=True)

    result = validate_human_review(review, expected_rows=2)

    assert result.valid is True
    assert result.complete is True
    assert result.completed_rows == 2
    assert result.summary[-1]["crop_correct_percent"] == 100.0
    assert all(row["confusion_count"] == 0 for row in result.summary)
    assert all(row["target_confirmation_count"] == 1 for row in result.summary)


def test_human_review_validator_preserves_blank_template_as_pending(tmp_path: Path) -> None:
    review = tmp_path / "review.csv"
    _write_fixture(review, complete=False)

    result = validate_human_review(review, expected_rows=2)

    assert result.valid is True
    assert result.complete is False
    assert result.completed_rows == 0
    assert result.errors == []


def test_human_review_validator_rejects_score_outside_rubric(tmp_path: Path) -> None:
    review = tmp_path / "review.csv"
    _write_fixture(review, complete=True, invalid_score=True)

    result = validate_human_review(review, expected_rows=2)

    assert result.valid is False
    assert result.complete is False
    assert "row 2: field_context_quality must be between 1 and 5" in result.errors


def test_human_review_validator_rejects_unpaired_conditions(tmp_path: Path) -> None:
    review = tmp_path / "review.csv"
    _write_fixture(review, complete=True)
    with review.open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    rows[1]["condition_id"] = "padi_p2_s42"
    with review.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(rows)

    result = validate_human_review(review, expected_rows=2)

    assert result.valid is False
    assert result.complete is False
    assert "review CSV has 2 conditions; expected 1 paired conditions" in result.errors
    assert "condition padi_p1_s42: missing variants lora" in result.errors
    assert "condition padi_p2_s42: missing variants base" in result.errors


def test_human_review_validator_rejects_pair_identity_mismatch(tmp_path: Path) -> None:
    review = tmp_path / "review.csv"
    _write_fixture(review, complete=True)
    with review.open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    rows[1]["prompt"] = "different prompt"
    with review.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(rows)

    result = validate_human_review(review, expected_rows=2)

    assert result.valid is False
    assert result.complete is False
    assert "condition padi_p1_s42: base/lora prompt values do not match" in result.errors


def test_materializer_never_overwrites_existing_human_review(tmp_path: Path) -> None:
    target = tmp_path / "human_review.csv"
    target.write_text("reviewed evidence must survive\n", encoding="utf-8")

    action = _write_local_human_template([{"variant": "base"}], target)

    assert action == "preserved_existing"
    assert target.read_text(encoding="utf-8") == "reviewed evidence must survive\n"
