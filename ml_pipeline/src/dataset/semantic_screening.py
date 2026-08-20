from __future__ import annotations

import csv
from collections import Counter
from pathlib import Path
from typing import Any

from PIL import Image, ImageDraw, ImageFilter, ImageOps, ImageStat
from PIL import __version__ as pillow_version

from ml_pipeline.src.common.config import (
    class_definitions,
    dataset_reports_dir,
    dataset_review_dir,
)
from ml_pipeline.src.dataset.io_utils import write_csv

METHOD = "Pillow CPU technical-semantic proxy v1"
THRESHOLDS = {
    "blur_edge_variance_min": 50.0,
    "entropy_min": 3.0,
    "brightness_min": 30.0,
    "brightness_max": 230.0,
    "green_ratio_min": 0.015,
    "close_up_green_ratio": 0.90,
    "watermark_border_edge_ratio": 3.0,
    "watermark_border_density_min": 0.18,
}

FIELDS = [
    "curated_file_name",
    "curated_path",
    "original_path",
    "class_id",
    "source_type",
    "sha256",
    "method",
    "method_version",
    "image_width",
    "image_height",
    "brightness_mean",
    "contrast_stddev",
    "entropy",
    "edge_variance",
    "green_pixel_ratio",
    "border_edge_density",
    "center_edge_density",
    "border_to_center_edge_ratio",
    "plant_visible_proxy",
    "growing_environment_proxy",
    "harvest_only_status",
    "food_status",
    "market_status",
    "too_close_up_proxy",
    "watermark_proxy",
    "blur_proxy",
    "synthetic_status",
    "semantic_class_status",
    "semantic_class_confidence",
    "class_ambiguous_status",
    "proxy_flags",
    "screening_status",
    "eligible_for_final_without_human_review",
]


def screen_image_proxy(path: Path) -> dict[str, object]:
    """Run the conservative CPU proxy for one technically valid image."""
    metrics = _measure_image(path)
    flags = _proxy_flags(metrics)
    return {
        "method": METHOD,
        "method_version": f"Pillow {pillow_version}",
        **metrics,
        "plant_visible_proxy": (
            "possible"
            if metrics["green_pixel_ratio"] >= THRESHOLDS["green_ratio_min"]
            else "not_detected"
        ),
        "growing_environment_proxy": _environment_proxy(metrics),
        "harvest_only_status": "not_assessed_no_semantic_model",
        "food_status": "not_assessed_no_semantic_model",
        "market_status": "not_assessed_no_semantic_model",
        "too_close_up_proxy": (
            "flag"
            if metrics["green_pixel_ratio"] >= THRESHOLDS["close_up_green_ratio"]
            else "clear"
        ),
        "watermark_proxy": "flag" if "watermark_proxy" in flags else "clear",
        "blur_proxy": "flag" if "blur_proxy" in flags else "clear",
        "synthetic_status": "not_assessed_no_detector",
        "semantic_class_status": "not_assessed_no_semantic_model",
        "semantic_class_confidence": "",
        "class_ambiguous_status": "requires_human_review",
        "proxy_flags": "|".join(flags),
        "screening_status": "proxy_review" if flags else "proxy_pass",
        "eligible_for_final_without_human_review": False,
    }


def run_automated_semantic_screening(config: dict[str, Any]) -> dict[str, object]:
    mapping_path = dataset_reports_dir(config) / "curation_mapping.csv"
    if not mapping_path.is_file():
        raise ValueError("Curation mapping is missing; run `prepare` before `screen`.")

    active_classes = {str(item["id"]) for item in class_definitions(config)}
    with mapping_path.open(newline="", encoding="utf-8-sig") as handle:
        mapping = [
            row for row in csv.DictReader(handle) if row.get("class_id", "") in active_classes
        ]

    rows: list[dict[str, object]] = []
    for item in mapping:
        path = _existing_image_path(item)
        rows.append(
            {
                "curated_file_name": item.get("curated_file_name", path.name),
                "curated_path": str(path),
                "original_path": item.get("original_path", ""),
                "class_id": item.get("class_id", ""),
                "source_type": item.get("source_type", ""),
                "sha256": item.get("sha256", ""),
                **screen_image_proxy(path),
            }
        )

    output_path = write_csv(
        dataset_reports_dir(config) / "automated_semantic_review.csv",
        rows,
        FIELDS,
    )
    contact_sheets = _write_overview_contact_sheets(config, rows)
    summary_path = _write_summary(config, rows, contact_sheets)
    return {
        "status": "proxy_complete_human_review_still_required",
        "method": METHOD,
        "method_version": f"Pillow {pillow_version}",
        "thresholds": THRESHOLDS,
        "images_screened": len(rows),
        "report": str(output_path),
        "summary": str(summary_path),
        "contact_sheets": [str(path) for path in contact_sheets],
        "human_review_required": True,
    }


def _existing_image_path(item: dict[str, str]) -> Path:
    for field in ("curated_path", "original_path"):
        value = item.get(field, "")
        if value and Path(value).is_file():
            return Path(value)
    raise ValueError(f"Candidate image is missing: {item.get('curated_file_name', 'unknown')}")


def _measure_image(path: Path) -> dict[str, float | int]:
    with Image.open(path) as opened:
        image = ImageOps.exif_transpose(opened).convert("RGB")
        original_width, original_height = image.size
        image.thumbnail((256, 256), Image.Resampling.LANCZOS)
        gray = image.convert("L")
        stats = ImageStat.Stat(gray)
        edges = gray.filter(ImageFilter.FIND_EDGES)
        if edges.width > 4 and edges.height > 4:
            edges = edges.crop((2, 2, edges.width - 2, edges.height - 2))

        edge_stats = ImageStat.Stat(edges)
        border_density, center_density = _edge_densities(edges)
        ratio = border_density / max(center_density, 0.001)
        pixels = list(image.get_flattened_data())
        green_count = sum(
            1
            for red, green, blue in pixels
            if green > 50 and green > red * 1.05 and green > blue * 1.05
        )

    return {
        "image_width": original_width,
        "image_height": original_height,
        "brightness_mean": round(stats.mean[0], 4),
        "contrast_stddev": round(stats.stddev[0], 4),
        "entropy": round(gray.entropy(), 4),
        "edge_variance": round(edge_stats.var[0], 4),
        "green_pixel_ratio": round(green_count / max(len(pixels), 1), 6),
        "border_edge_density": round(border_density, 6),
        "center_edge_density": round(center_density, 6),
        "border_to_center_edge_ratio": round(ratio, 4),
    }


def _edge_densities(edges: Image.Image) -> tuple[float, float]:
    border_height = max(1, int(edges.height * 0.15))
    top = edges.crop((0, 0, edges.width, border_height))
    bottom = edges.crop((0, edges.height - border_height, edges.width, edges.height))
    center_top = border_height
    center_bottom = max(center_top + 1, edges.height - border_height)
    center = edges.crop((0, center_top, edges.width, center_bottom))
    border_hits = _histogram_fraction(top, 40) + _histogram_fraction(bottom, 40)
    return border_hits / 2, _histogram_fraction(center, 40)


def _histogram_fraction(image: Image.Image, minimum: int) -> float:
    histogram = image.histogram()
    return sum(histogram[minimum + 1 :]) / max(image.width * image.height, 1)


def _proxy_flags(metrics: dict[str, float | int]) -> list[str]:
    flags: list[str] = []
    if metrics["edge_variance"] < THRESHOLDS["blur_edge_variance_min"]:
        flags.append("blur_proxy")
    if metrics["entropy"] < THRESHOLDS["entropy_min"]:
        flags.append("low_entropy")
    if (
        not THRESHOLDS["brightness_min"]
        <= metrics["brightness_mean"]
        <= THRESHOLDS["brightness_max"]
    ):
        flags.append("extreme_brightness")
    if metrics["green_pixel_ratio"] < THRESHOLDS["green_ratio_min"]:
        flags.append("vegetation_not_detected_proxy")
    if metrics["green_pixel_ratio"] >= THRESHOLDS["close_up_green_ratio"]:
        flags.append("too_close_up_proxy")
    if (
        metrics["border_to_center_edge_ratio"] >= THRESHOLDS["watermark_border_edge_ratio"]
        and metrics["border_edge_density"] >= THRESHOLDS["watermark_border_density_min"]
    ):
        flags.append("watermark_proxy")
    return flags


def _environment_proxy(metrics: dict[str, float | int]) -> str:
    green_ratio = metrics["green_pixel_ratio"]
    if green_ratio < THRESHOLDS["green_ratio_min"]:
        return "not_detected"
    if green_ratio >= THRESHOLDS["close_up_green_ratio"]:
        return "uncertain_close_up"
    return "possible"


def _write_overview_contact_sheets(
    config: dict[str, Any], rows: list[dict[str, object]]
) -> list[Path]:
    review_dir = dataset_review_dir(config)
    review_dir.mkdir(parents=True, exist_ok=True)
    outputs: list[Path] = []
    for class_info in class_definitions(config):
        class_id = str(class_info["id"])
        class_rows = [row for row in rows if row["class_id"] == class_id][:100]
        target = review_dir / f"review_{class_id}.jpg"
        _write_contact_sheet(class_rows, target, class_id)
        outputs.append(target)
    return outputs


def _write_contact_sheet(rows: list[dict[str, object]], target: Path, class_id: str) -> None:
    columns = 10
    cell_width, cell_height = 150, 125
    header_height = 45
    row_count = max(1, (len(rows) + columns - 1) // columns)
    sheet = Image.new(
        "RGB", (columns * cell_width, header_height + row_count * cell_height), "white"
    )
    draw = ImageDraw.Draw(sheet)
    draw.text(
        (12, 12),
        f"Automated proxy overview: {class_id} | {len(rows)} candidates | human review required",
        fill="black",
    )

    for index, row in enumerate(rows):
        x = (index % columns) * cell_width
        y = header_height + (index // columns) * cell_height
        with Image.open(Path(str(row["curated_path"]))) as opened:
            thumb = ImageOps.contain(
                ImageOps.exif_transpose(opened).convert("RGB"),
                (cell_width - 8, cell_height - 27),
                Image.Resampling.LANCZOS,
            )
        image_x = x + (cell_width - thumb.width) // 2
        sheet.paste(thumb, (image_x, y + 2))
        label = str(row["curated_file_name"])
        draw.text((x + 4, y + cell_height - 20), label[:22], fill="black")

    target.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(target, "JPEG", quality=88, optimize=True)


def _write_summary(
    config: dict[str, Any],
    rows: list[dict[str, object]],
    contact_sheets: list[Path],
) -> Path:
    class_lines = []
    for class_info in class_definitions(config):
        class_id = str(class_info["id"])
        class_rows = [row for row in rows if row["class_id"] == class_id]
        status_counts = Counter(str(row["screening_status"]) for row in class_rows)
        class_lines.append(
            f"| {class_id} | {len(class_rows)} | {status_counts['proxy_pass']} | "
            f"{status_counts['proxy_review']} |"
        )

    flag_counts = Counter(
        flag for row in rows for flag in str(row.get("proxy_flags", "")).split("|") if flag
    )
    threshold_lines = [f"- `{key}`: {value}" for key, value in THRESHOLDS.items()]
    flag_lines = [f"- `{key}`: {value}" for key, value in sorted(flag_counts.items())]
    if not flag_lines:
        flag_lines = ["- No technical proxy flags were emitted."]

    content = [
        "# Automated Semantic Screening Summary",
        "",
        f"Method: `{METHOD}` with Pillow {pillow_version} on CPU.",
        "",
        "This is a conservative technical-semantic proxy, not human review and not",
        "a trained semantic classifier. It does not accept images into the research-final",
        "dataset. Food, market, harvest-only, synthetic-image, and class-correctness fields",
        "remain explicitly unassessed because no authenticated semantic model was used.",
        "",
        "| Class | Screened | Proxy pass | Proxy review |",
        "| --- | ---: | ---: | ---: |",
        *class_lines,
        "",
        "## Thresholds",
        "",
        *threshold_lines,
        "",
        "## Emitted Flags",
        "",
        *flag_lines,
        "",
        "## Contact Sheets",
        "",
        *[f"- `{path}`" for path in contact_sheets],
        "",
        "All semantic confidence cells are intentionally blank. A person must inspect the",
        "contact sheets and record decisions in `manual_review_template.csv` before final",
        "split, metadata, packaging, training, or research claims are allowed.",
        "",
    ]
    target = dataset_reports_dir(config) / "automated_semantic_review_summary.md"
    target.write_text("\n".join(content), encoding="utf-8")
    return target
