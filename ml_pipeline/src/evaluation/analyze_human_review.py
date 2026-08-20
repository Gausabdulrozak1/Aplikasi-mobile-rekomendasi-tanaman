from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import math
import os
import statistics
from collections import Counter, defaultdict
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Callable

from ml_pipeline.src.evaluation.validate_human_review import (
    CLASS_IDS,
    CONFUSION_VALUES,
    VARIANTS,
    validate_human_review,
)

ANALYSIS_JSON = "human_review_analysis.json"
ANALYSIS_CSV = "human_review_analysis.csv"
ANALYSIS_MARKDOWN = "BAB_IV_HUMAN_REVIEW_RESULTS.md"


class HumanReviewAnalysisError(ValueError):
    """Raised when human-review evidence is not ready for analysis."""


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _round(value: float, digits: int = 6) -> float:
    return round(float(value), digits)


def _score_summary(values: list[int]) -> dict[str, int | float]:
    return {
        "count": len(values),
        "mean": _round(statistics.fmean(values)),
        "median": _round(statistics.median(values)),
        "standard_deviation": _round(statistics.stdev(values)) if len(values) > 1 else 0.0,
        "minimum": min(values),
        "maximum": max(values),
    }


def exact_two_sided_binomial(wins: int, losses: int) -> float:
    """Return the exact two-sided p-value for non-tied paired directions."""

    if wins < 0 or losses < 0:
        raise ValueError("wins and losses must be non-negative")
    trials = wins + losses
    if trials == 0:
        return 1.0
    lower = min(wins, losses)
    probability = 2 * sum(math.comb(trials, index) for index in range(lower + 1)) / (2**trials)
    return min(1.0, probability)


def _read_completed_rows(review_csv: Path) -> list[dict[str, Any]]:
    with review_csv.open(encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.DictReader(handle))
    return [
        {
            **row,
            "seed": int(row["seed"].strip()),
            "crop_correct": row["crop_correct"].strip().casefold() == "true",
            "field_context_quality": int(row["field_context_quality"].strip()),
            "visual_realism_score": int(row["visual_realism_score"].strip()),
            "class_confusion": row["class_confusion"].strip().casefold(),
            "reviewer_role": row["reviewer_role"].strip(),
        }
        for row in rows
    ]


def _variant_summary(rows: list[dict[str, Any]]) -> dict[str, Any]:
    correct = sum(row["crop_correct"] for row in rows)
    confusion_counts = Counter(row["class_confusion"] for row in rows)
    return {
        "reviewed": len(rows),
        "crop_correct": {
            "count": correct,
            "percent": _round(100 * correct / len(rows)),
        },
        "field_context_quality": _score_summary([row["field_context_quality"] for row in rows]),
        "visual_realism_score": _score_summary([row["visual_realism_score"] for row in rows]),
        "class_confusion_counts": {value: confusion_counts[value] for value in CONFUSION_VALUES},
        "target_confirmation_count": sum(row["class_confusion"] == row["class_id"] for row in rows),
        "cross_class_or_unclear_count": sum(
            row["class_confusion"] not in {"none", row["class_id"]} for row in rows
        ),
    }


def _direction_counts(differences: list[int]) -> dict[str, int]:
    lora_wins = sum(difference > 0 for difference in differences)
    base_wins = sum(difference < 0 for difference in differences)
    ties = sum(difference == 0 for difference in differences)
    return {
        "lora_wins": lora_wins,
        "ties": ties,
        "base_wins": base_wins,
        "non_tied": lora_wins + base_wins,
    }


def _binary_comparison(pairs: list[dict[str, dict[str, Any]]]) -> dict[str, Any]:
    base_values = [int(pair["base"]["crop_correct"]) for pair in pairs]
    lora_values = [int(pair["lora"]["crop_correct"]) for pair in pairs]
    directions = _direction_counts(
        [lora - base for base, lora in zip(base_values, lora_values, strict=True)]
    )
    base_percent = 100 * sum(base_values) / len(base_values)
    lora_percent = 100 * sum(lora_values) / len(lora_values)
    return {
        "base_correct_count": sum(base_values),
        "lora_correct_count": sum(lora_values),
        "base_percent": _round(base_percent),
        "lora_percent": _round(lora_percent),
        "lora_minus_base_percentage_points": _round(lora_percent - base_percent),
        **directions,
        "exact_p_value": _round(
            exact_two_sided_binomial(directions["lora_wins"], directions["base_wins"]),
            10,
        ),
        "test": "exact_mcnemar_discordant_pairs",
    }


def _ordinal_comparison(
    pairs: list[dict[str, dict[str, Any]]],
    field_name: str,
) -> dict[str, Any]:
    base_values = [int(pair["base"][field_name]) for pair in pairs]
    lora_values = [int(pair["lora"][field_name]) for pair in pairs]
    differences = [lora - base for base, lora in zip(base_values, lora_values, strict=True)]
    directions = _direction_counts(differences)
    return {
        "base_mean": _round(statistics.fmean(base_values)),
        "lora_mean": _round(statistics.fmean(lora_values)),
        "base_median": _round(statistics.median(base_values)),
        "lora_median": _round(statistics.median(lora_values)),
        "lora_minus_base_mean": _round(statistics.fmean(differences)),
        "lora_minus_base_median": _round(statistics.median(differences)),
        **directions,
        "exact_p_value": _round(
            exact_two_sided_binomial(directions["lora_wins"], directions["base_wins"]),
            10,
        ),
        "test": "exact_sign_test_ties_excluded",
    }


def _scope_report(pairs: list[dict[str, dict[str, Any]]]) -> dict[str, Any]:
    rows_by_variant = {variant: [pair[variant] for pair in pairs] for variant in VARIANTS}
    return {
        "paired_conditions": len(pairs),
        "base": _variant_summary(rows_by_variant["base"]),
        "lora": _variant_summary(rows_by_variant["lora"]),
        "paired_comparison": {
            "crop_correct": _binary_comparison(pairs),
            "field_context_quality": _ordinal_comparison(pairs, "field_context_quality"),
            "visual_realism_score": _ordinal_comparison(pairs, "visual_realism_score"),
        },
    }


def analyze_human_review(
    review_csv: Path,
    *,
    images_root: Path | None = None,
    expected_rows: int = 72,
    generated_at: str | None = None,
) -> dict[str, Any]:
    review_csv = review_csv.resolve()
    validation = validate_human_review(
        review_csv,
        images_root=images_root,
        expected_rows=expected_rows,
    )
    if not validation.valid:
        raise HumanReviewAnalysisError("human review is invalid: " + "; ".join(validation.errors))
    if not validation.complete:
        raise HumanReviewAnalysisError(
            f"human review is incomplete: {validation.completed_rows}/{expected_rows} rows"
        )

    rows = _read_completed_rows(review_csv)
    grouped: dict[str, dict[str, dict[str, Any]]] = defaultdict(dict)
    for row in rows:
        grouped[row["condition_id"]][row["variant"]] = row
    pairs = [grouped[condition_id] for condition_id in sorted(grouped)]
    roles = Counter(row["reviewer_role"] for row in rows)

    return {
        "schema_version": 1,
        "status": "complete_validated_human_review",
        "generated_at": generated_at or datetime.now(UTC).isoformat(),
        "review_csv": str(review_csv),
        "review_csv_sha256": _sha256(review_csv),
        "validation": validation.to_dict(),
        "review_provenance": {
            "source": "reviewer_entered_csv",
            "automated_scores_inserted": False,
            "reviewer_identity_independently_verified": False,
            "reported_role_counts": dict(sorted(roles.items())),
        },
        "methodology": {
            "design": "paired_base_vs_lora",
            "unit": "matched prompt and seed condition",
            "crop_correct_test": "exact McNemar test on discordant pairs",
            "ordinal_score_test": "exact two-sided sign test excluding ties",
            "ordinal_primary_summary": "median",
            "means_are_descriptive": True,
            "p_values_are_exploratory": True,
            "automated_proxy_metrics_are_separate": True,
        },
        "overall": _scope_report(pairs),
        "by_class": {
            class_id: _scope_report(
                [pair for pair in pairs if pair["base"]["class_id"] == class_id]
            )
            for class_id in CLASS_IDS
            if any(pair["base"]["class_id"] == class_id for pair in pairs)
        },
    }


def _analysis_rows(report: dict[str, Any]) -> list[dict[str, Any]]:
    output: list[dict[str, Any]] = []
    scopes = [
        ("overall", "all", report["overall"]),
        *[("class", class_id, scope) for class_id, scope in report["by_class"].items()],
    ]
    for scope_name, class_id, scope in scopes:
        comparisons = scope["paired_comparison"]
        for metric in ("crop_correct", "field_context_quality", "visual_realism_score"):
            comparison = comparisons[metric]
            if metric == "crop_correct":
                base_value = comparison["base_percent"]
                lora_value = comparison["lora_percent"]
                difference = comparison["lora_minus_base_percentage_points"]
                base_median = ""
                lora_median = ""
                unit = "percent"
            else:
                base_value = comparison["base_mean"]
                lora_value = comparison["lora_mean"]
                difference = comparison["lora_minus_base_mean"]
                base_median = comparison["base_median"]
                lora_median = comparison["lora_median"]
                unit = "score_1_to_5"
            output.append(
                {
                    "scope": scope_name,
                    "class_id": class_id,
                    "metric": metric,
                    "unit": unit,
                    "paired_conditions": scope["paired_conditions"],
                    "base_value": base_value,
                    "lora_value": lora_value,
                    "lora_minus_base": difference,
                    "base_median": base_median,
                    "lora_median": lora_median,
                    "lora_wins": comparison["lora_wins"],
                    "ties": comparison["ties"],
                    "base_wins": comparison["base_wins"],
                    "non_tied": comparison["non_tied"],
                    "exact_p_value": comparison["exact_p_value"],
                    "test": comparison["test"],
                }
            )
    return output


def _render_csv(report: dict[str, Any]) -> str:
    rows = _analysis_rows(report)
    buffer = io.StringIO(newline="")
    writer = csv.DictWriter(buffer, fieldnames=list(rows[0]))
    writer.writeheader()
    writer.writerows(rows)
    return buffer.getvalue()


def _id_number(value: int | float, digits: int = 3) -> str:
    if isinstance(value, int):
        return str(value)
    return f"{value:.{digits}f}".replace(".", ",")


def _render_markdown(report: dict[str, Any]) -> str:
    overall = report["overall"]
    comparisons = overall["paired_comparison"]
    roles = report["review_provenance"]["reported_role_counts"]
    lines = [
        "# Hasil Evaluasi Manusia Base vs LoRA",
        "",
        f"- Status: `{report['status']}`",
        f"- Kondisi berpasangan: {overall['paired_conditions']}",
        f"- Gambar dinilai: {report['validation']['completed_rows']}",
        f"- SHA-256 CSV: `{report['review_csv_sha256']}`",
        "- Peran reviewer yang dilaporkan: "
        + ", ".join(f"{role} ({count} baris)" for role, count in roles.items()),
        "",
        "## Ringkasan Keseluruhan",
        "",
        "| Metrik | Base | LoRA | Selisih LoRA-Base | LoRA menang / seri / Base menang | p exact |",
        "| --- | ---: | ---: | ---: | ---: | ---: |",
    ]
    crop = comparisons["crop_correct"]
    lines.append(
        "| Komoditas sesuai | "
        f"{_id_number(crop['base_percent'])}% | {_id_number(crop['lora_percent'])}% | "
        f"{_id_number(crop['lora_minus_base_percentage_points'])} poin persentase | "
        f"{crop['lora_wins']} / {crop['ties']} / {crop['base_wins']} | "
        f"{_id_number(crop['exact_p_value'], 6)} |"
    )
    for field_name, label in (
        ("field_context_quality", "Kualitas konteks lahan"),
        ("visual_realism_score", "Realisme visual"),
    ):
        value = comparisons[field_name]
        lines.append(
            f"| {label} (mean; median) | "
            f"{_id_number(value['base_mean'])}; {_id_number(value['base_median'])} | "
            f"{_id_number(value['lora_mean'])}; {_id_number(value['lora_median'])} | "
            f"{_id_number(value['lora_minus_base_mean'])} mean | "
            f"{value['lora_wins']} / {value['ties']} / {value['base_wins']} | "
            f"{_id_number(value['exact_p_value'], 6)} |"
        )

    lines.extend(
        [
            "",
            "## Ringkasan Per Kelas",
            "",
            "| Kelas | N pasangan | Benar Base | Benar LoRA | Median konteks Base/LoRA | Median realisme Base/LoRA | Confusion Base/LoRA |",
            "| --- | ---: | ---: | ---: | ---: | ---: | ---: |",
        ]
    )
    for class_id, scope in report["by_class"].items():
        base = scope["base"]
        lora = scope["lora"]
        base_confusion = base["cross_class_or_unclear_count"]
        lora_confusion = lora["cross_class_or_unclear_count"]
        lines.append(
            f"| {class_id} | {scope['paired_conditions']} | "
            f"{_id_number(base['crop_correct']['percent'])}% | "
            f"{_id_number(lora['crop_correct']['percent'])}% | "
            f"{_id_number(base['field_context_quality']['median'])} / "
            f"{_id_number(lora['field_context_quality']['median'])} | "
            f"{_id_number(base['visual_realism_score']['median'])} / "
            f"{_id_number(lora['visual_realism_score']['median'])} | "
            f"{base_confusion} / {lora_confusion} |"
        )

    lines.extend(
        [
            "",
            "## Batas Interpretasi",
            "",
            "- Skor 1-5 bersifat ordinal; median menjadi ringkasan utama dan mean hanya deskriptif.",
            "- Exact sign test menguji arah selisih pasangan setelah nilai seri dikeluarkan.",
            "- Exact McNemar menggunakan pasangan discordant untuk penilaian komoditas benar/salah.",
            "- Nilai p bersifat eksploratif dan tidak membuktikan ketepatan agronomi atau hubungan kausal.",
            "- Identitas reviewer tidak diverifikasi secara independen oleh perangkat lunak.",
            "- Brightness, contrast, dan entropy tetap proxy otomatis yang dilaporkan terpisah.",
            "",
        ]
    )
    return "\n".join(lines)


def _atomic_write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    try:
        temporary.write_text(content, encoding="utf-8", newline="")
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def write_analysis_artifacts(
    report: dict[str, Any],
    output_dir: Path,
) -> dict[str, Path]:
    output_dir = output_dir.resolve()
    paths = {
        "json": output_dir / ANALYSIS_JSON,
        "csv": output_dir / ANALYSIS_CSV,
        "markdown": output_dir / ANALYSIS_MARKDOWN,
    }
    renderers: dict[str, Callable[[dict[str, Any]], str]] = {
        "json": lambda value: json.dumps(value, indent=2, ensure_ascii=False) + "\n",
        "csv": _render_csv,
        "markdown": _render_markdown,
    }
    for key, path in paths.items():
        _atomic_write(path, renderers[key](report))
    return paths


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Analyze complete paired Base-vs-LoRA human review evidence."
    )
    parser.add_argument("--review-csv", type=Path, required=True)
    parser.add_argument("--images-root", type=Path)
    parser.add_argument("--expected-rows", type=int, default=72)
    parser.add_argument("--output-dir", type=Path)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    try:
        report = analyze_human_review(
            args.review_csv,
            images_root=args.images_root,
            expected_rows=args.expected_rows,
        )
        paths = write_analysis_artifacts(report, args.output_dir or args.review_csv.parent)
    except (OSError, csv.Error, HumanReviewAnalysisError, ValueError) as exc:
        print(f"STOP: {exc}")
        return 1
    print(json.dumps({key: str(path) for key, path in paths.items()}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
