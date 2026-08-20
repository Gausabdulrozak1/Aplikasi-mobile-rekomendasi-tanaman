from __future__ import annotations

import csv
import json
from pathlib import Path

import pytest
from PIL import Image

from ml_pipeline.src.evaluation.analyze_human_review import (
    ANALYSIS_CSV,
    ANALYSIS_JSON,
    ANALYSIS_MARKDOWN,
    HumanReviewAnalysisError,
    analyze_human_review,
    exact_two_sided_binomial,
    write_analysis_artifacts,
)
from ml_pipeline.src.evaluation.validate_human_review import CLASS_IDS

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


def _write_analysis_fixture(path: Path, *, complete: bool = True) -> None:
    rows = []
    generated = path.parent / "generated"
    generated.mkdir()
    values = {
        "padi": {"base": (False, 2, 2, "unclear"), "lora": (True, 4, 4, "padi")},
        "jagung": {
            "base": (True, 3, 3, "jagung"),
            "lora": (True, 4, 5, "jagung"),
        },
        "cabai": {"base": (True, 4, 4, "cabai"), "lora": (False, 2, 2, "padi")},
        "kacang_tanah": {
            "base": (False, 3, 3, "unclear"),
            "lora": (False, 3, 4, "unclear"),
        },
    }
    for class_index, class_id in enumerate(CLASS_IDS, start=1):
        for variant in ("base", "lora"):
            image_name = f"{class_id}_{variant}.png"
            Image.new("RGB", (3, 3), (class_index * 30, 80, 40)).save(generated / image_name)
            crop, context, realism, confusion = values[class_id][variant]
            rows.append(
                {
                    "condition_id": f"{class_id}_p1_s42",
                    "variant": variant,
                    "class_id": class_id,
                    "prompt": f"fixture {class_id}",
                    "seed": "42",
                    "expected_image_path": f"generated/{image_name}",
                    "crop_correct": str(crop).lower() if complete else "",
                    "field_context_quality": str(context) if complete else "",
                    "visual_realism_score": str(realism) if complete else "",
                    "class_confusion": confusion if complete else "",
                    "reviewer_role": "peneliti" if complete else "",
                    "reviewer_notes": "",
                }
            )
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(rows)


def test_exact_two_sided_binomial_handles_ties_and_extreme_direction() -> None:
    assert exact_two_sided_binomial(0, 0) == 1.0
    assert exact_two_sided_binomial(4, 0) == 0.125
    assert exact_two_sided_binomial(1, 1) == 1.0


def test_complete_review_produces_paired_analysis_and_artifacts(tmp_path: Path) -> None:
    review = tmp_path / "review.csv"
    _write_analysis_fixture(review)

    report = analyze_human_review(
        review,
        expected_rows=8,
        generated_at="2026-08-21T00:00:00+00:00",
    )
    paths = write_analysis_artifacts(report, tmp_path / "analysis")

    assert report["status"] == "complete_validated_human_review"
    assert report["overall"]["paired_conditions"] == 4
    assert set(report["by_class"]) == set(CLASS_IDS)
    crop = report["overall"]["paired_comparison"]["crop_correct"]
    assert crop["base_correct_count"] == 2
    assert crop["lora_correct_count"] == 2
    assert crop["lora_wins"] == 1
    assert crop["base_wins"] == 1
    assert crop["exact_p_value"] == 1.0
    assert report["review_provenance"]["automated_scores_inserted"] is False
    assert report["overall"]["base"]["target_confirmation_count"] == 2
    assert report["overall"]["base"]["cross_class_or_unclear_count"] == 2
    assert set(path.name for path in paths.values()) == {
        ANALYSIS_JSON,
        ANALYSIS_CSV,
        ANALYSIS_MARKDOWN,
    }
    persisted = json.loads(paths["json"].read_text(encoding="utf-8"))
    assert persisted["review_csv_sha256"] == report["review_csv_sha256"]
    assert "exact_mcnemar_discordant_pairs" in paths["csv"].read_text(encoding="utf-8")
    markdown = paths["markdown"].read_text(encoding="utf-8")
    assert "Hasil Evaluasi Manusia Base vs LoRA" in markdown
    assert "Nilai p bersifat eksploratif" in markdown


def test_incomplete_review_cannot_generate_analysis(tmp_path: Path) -> None:
    review = tmp_path / "review.csv"
    _write_analysis_fixture(review, complete=False)

    with pytest.raises(HumanReviewAnalysisError, match="incomplete: 0/8"):
        analyze_human_review(review, expected_rows=8)

    assert not (tmp_path / ANALYSIS_JSON).exists()
