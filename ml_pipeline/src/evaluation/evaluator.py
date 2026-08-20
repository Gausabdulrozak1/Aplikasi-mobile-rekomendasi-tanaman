from __future__ import annotations

import csv
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from PIL import Image, ImageDraw


def build_manifest(
    config: dict[str, Any],
    output_paths: list[Path],
    variant: str,
    lora_path: str = "",
) -> list[dict[str, object]]:
    validation = config["validation"]
    records: list[dict[str, object]] = []
    for output_path in output_paths:
        records.append(
            {
                "experiment_id": config["experiment_name"],
                "variant": variant,
                "model": config["base_model"],
                "lora_path": lora_path,
                "prompt": "",
                "negative_prompt": validation["negative_prompt"],
                "seed": "",
                "steps": validation["inference_steps"],
                "guidance_scale": validation["guidance_scale"],
                "width": validation["width"],
                "height": validation["height"],
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "output_path": str(output_path),
                "runtime_seconds": "",
            }
        )
    return records


def write_manifest(path: Path, records: list[dict[str, object]]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(records, indent=2), encoding="utf-8")
    return path


def write_human_evaluation_template(path: Path, records: list[dict[str, object]]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    extra_fields = [
        "visual_quality_1_5",
        "crop_identity_1_5",
        "agricultural_relevance_1_5",
        "notes",
    ]
    fieldnames = list(records[0].keys()) + extra_fields if records else extra_fields
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for record in records:
            writer.writerow({**record, **{field: "" for field in extra_fields}})
    return path


def write_confusion_review_template(
    path: Path,
    records: list[dict[str, object]],
) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = [
        "expected_class",
        "predicted_visual_class",
        "prompt",
        "seed",
        "reviewer_score",
        "class_correct",
        "mixed_crop_detected",
        "notes",
    ]
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for record in records:
            writer.writerow(
                {
                    "expected_class": record.get("expected_class", ""),
                    "predicted_visual_class": "",
                    "prompt": record.get("prompt", ""),
                    "seed": record.get("seed", ""),
                    "reviewer_score": "",
                    "class_correct": "",
                    "mixed_crop_detected": "",
                    "notes": "",
                }
            )
    return path


def make_contact_sheet(image_paths: list[Path], target_path: Path, label: str) -> Path:
    target_path.parent.mkdir(parents=True, exist_ok=True)
    if not image_paths:
        Image.new("RGB", (512, 128), "white").save(target_path)
        return target_path

    thumbs = []
    for image_path in image_paths:
        image = Image.open(image_path).convert("RGB").resize((256, 256))
        thumbs.append((image_path.name, image))

    width = 512
    height = ((len(thumbs) + 1) // 2) * 300
    sheet = Image.new("RGB", (width, height), "white")
    draw = ImageDraw.Draw(sheet)
    for index, (name, image) in enumerate(thumbs):
        x = (index % 2) * 256
        y = (index // 2) * 300
        sheet.paste(image, (x, y))
        draw.text((x + 4, y + 260), f"{label}: {name}", fill=(0, 0, 0))
    sheet.save(target_path)
    return target_path


def write_markdown_report(path: Path, records: list[dict[str, object]]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "# LoRA Evaluation Report",
        "",
        "This report template records generated evidence only. It does not invent scores.",
        "",
        f"- Generated images recorded: {len(records)}",
        f"- Created at: {datetime.now(timezone.utc).isoformat()}",
        "",
        "## Human Rubric",
        "",
        "- Visual quality: 1-5",
        "- Crop identity: 1-5",
        "- Agricultural relevance: 1-5",
        "",
        "## Notes",
        "",
        "- Public dataset output is pilot evidence only.",
        "- Compare base and LoRA images generated with identical prompts and seeds.",
    ]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path
