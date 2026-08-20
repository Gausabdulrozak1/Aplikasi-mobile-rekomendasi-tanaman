from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import math
import os
import statistics
import zipfile
from collections import defaultdict
from pathlib import Path, PurePosixPath
from typing import Any

from PIL import Image, ImageDraw, ImageOps

from ml_pipeline.src.training.validate_kaggle_export import (
    MODEL_FILENAME,
    validate_kaggle_export,
)

EVIDENCE_ENTRIES = (
    "complete_pipeline_state.json",
    "dataset_package_sha256.txt",
    "evaluation/automated_proxy_metrics.csv",
    "evaluation/evaluation_manifest.csv",
    "evaluation/evaluation_manifest.json",
    "evaluation/human_evaluation_template.csv",
    "export_manifest.json",
    "final_integrity.json",
    "final_training_report.json",
    "final_training_report.md",
    "main_loss_history.csv",
    "main_validation.json",
    "multisource_multicrop_lora.sha256",
    "sanity/sanity_manifest.json",
    "smoke_loss_history.csv",
    "smoke_validation.json",
    "training_config.json",
)
PROXY_FIELDS = ("brightness_proxy", "contrast_proxy", "entropy_proxy")


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _atomic_write(path: Path, value: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.tmp")
    temporary.write_bytes(value)
    os.replace(temporary, path)


def _read_csv(archive: zipfile.ZipFile, name: str) -> list[dict[str, str]]:
    return list(csv.DictReader(io.StringIO(archive.read(name).decode("utf-8-sig"))))


def _loss_summary(rows: list[dict[str, str]]) -> dict[str, float | int]:
    values = [float(row["loss"]) for row in rows]
    if not values or not all(math.isfinite(value) for value in values):
        raise RuntimeError("Loss history is empty or contains a non-finite value")
    window = min(100, len(values))
    return {
        "observations": len(values),
        "first": values[0],
        "last": values[-1],
        "mean": statistics.mean(values),
        "median": statistics.median(values),
        "minimum": min(values),
        "maximum": max(values),
        "first_window_mean": statistics.mean(values[:window]),
        "last_window_mean": statistics.mean(values[-window:]),
        "window_size": window,
    }


def _proxy_summary(rows: list[dict[str, str]]) -> list[dict[str, Any]]:
    groups: dict[tuple[str, str], list[dict[str, str]]] = defaultdict(list)
    for row in rows:
        groups[(row["variant"], row["class_id"])].append(row)
        groups[(row["variant"], "all")].append(row)
    summary: list[dict[str, Any]] = []
    for (variant, class_id), group in sorted(groups.items()):
        summary.append(
            {
                "variant": variant,
                "class_id": class_id,
                "images": len(group),
                **{
                    f"{field}_mean": round(
                        statistics.mean(float(row[field]) for row in group), 6
                    )
                    for field in PROXY_FIELDS
                },
            }
        )
    return summary


def _write_proxy_summary(path: Path, rows: list[dict[str, Any]]) -> None:
    if not rows:
        raise RuntimeError("Proxy metric summary is empty")
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def _duration(seconds: float) -> str:
    minutes, remaining = divmod(seconds, 60)
    return f"{int(minutes)} min {remaining:.2f} sec"


def _write_results_markdown(path: Path, summary: dict[str, Any]) -> None:
    evidence = summary["validation"]["evidence"]
    smoke = evidence["smoke"]
    main = evidence["main"]
    model = evidence["safetensors"]
    overall_proxy = {
        row["variant"]: row
        for row in summary["proxy_metrics"]
        if row["class_id"] == "all"
    }
    lines = [
        f"# Kaggle LoRA Evidence - Run {evidence['run_id']}",
        "",
        "## Validated Result",
        "",
        f"- Pipeline status: `{evidence['pipeline_status']}`",
        f"- Artifact ZIP SHA-256: `{summary['source_artifact_sha256']}`",
        f"- Dataset SHA-256: `{evidence['dataset_package_sha256']}`",
        f"- GPU: `{evidence['gpu']['count']} x {evidence['gpu']['name']}`",
        f"- Smoke: `{smoke['status']}`, {smoke['steps']} steps, {_duration(smoke['elapsed_seconds'])}",
        f"- Main: `{main['status']}`, {main['steps']} steps, {_duration(main['elapsed_seconds'])}",
        f"- LoRA: `{MODEL_FILENAME}`, {model['size_bytes']} bytes, {model['tensor_count']} tensors",
        f"- LoRA SHA-256: `{summary['model_sha256']}`",
        f"- Sanity images: {evidence['sanity_images_valid']}/4 valid",
        f"- Evaluation: {evidence['evaluation_conditions']} conditions, {evidence['evaluation_images_valid']} images valid",
        "- Human evaluation: pending; all 72 assessment rows remain blank",
        "",
        "## Loss Evidence",
        "",
        "| Run | Observations | First | Last | Mean | Median | First 100 mean | Last 100 mean |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for label, key in (("Smoke", "smoke_loss"), ("Main", "main_loss")):
        row = summary[key]
        lines.append(
            f"| {label} | {row['observations']} | {row['first']:.6f} | "
            f"{row['last']:.6f} | {row['mean']:.6f} | {row['median']:.6f} | "
            f"{row['first_window_mean']:.6f} | {row['last_window_mean']:.6f} |"
        )
    lines.extend(
        [
            "",
            "The loss series is noisy training evidence and is not a perceptual-quality score.",
            "",
            "## Automated Proxy Metrics",
            "",
            "| Variant | Images | Brightness mean | Contrast mean | Entropy mean |",
            "| --- | ---: | ---: | ---: | ---: |",
        ]
    )
    for variant in ("base", "lora"):
        row = overall_proxy[variant]
        lines.append(
            f"| {variant} | {row['images']} | {row['brightness_proxy_mean']:.6f} | "
            f"{row['contrast_proxy_mean']:.6f} | {row['entropy_proxy_mean']:.6f} |"
        )
    lines.extend(
        [
            "",
            "Brightness, contrast, and entropy are descriptive proxies only. They do not prove crop",
            "identity, realism, agronomic correctness, or superiority over the base model.",
            "",
            "## Human Review Files",
            "",
            "- `contact_sheets/`: four paired base-versus-LoRA sheets.",
            "- `human_evaluation_template_local.csv`: 72 blank rows with local image paths.",
            "- `generated/evaluation/`: 36 base and 36 LoRA PNG files.",
            "- `proxy_metrics_summary.csv`: grouped descriptive proxy statistics.",
            "",
            "Do not fill blank human fields automatically. A real reviewer must inspect each pair.",
        ]
    )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _extract_image(
    archive: zipfile.ZipFile,
    archive_name: str,
    output_root: Path,
) -> Path:
    target = output_root / archive_name
    _atomic_write(target, archive.read(archive_name))
    return target


def _make_contact_sheet(
    class_id: str,
    records: list[dict[str, Any]],
    generated_root: Path,
    output_path: Path,
) -> None:
    by_condition = defaultdict(dict)
    for record in records:
        if record["class_id"] == class_id:
            by_condition[record["condition_id"]][record["variant"]] = record
    ordered = sorted(
        by_condition.values(),
        key=lambda pair: (int(pair["base"]["prompt_index"]), int(pair["base"]["seed"])),
    )
    if not ordered or any(set(pair) != {"base", "lora"} for pair in ordered):
        raise RuntimeError(f"Incomplete base/LoRA pairs for contact sheet: {class_id}")

    thumb_width = 256
    thumb_height = 256
    label_height = 44
    title_height = 58
    sheet = Image.new(
        "RGB",
        (thumb_width * 2, title_height + len(ordered) * (thumb_height + label_height)),
        "white",
    )
    draw = ImageDraw.Draw(sheet)
    draw.text((12, 10), f"{class_id} | base (left) vs LoRA (right)", fill=(0, 0, 0))
    draw.text((12, 31), "Same prompt, seed, steps, guidance, and resolution", fill=(50, 50, 50))

    for row_index, pair in enumerate(ordered):
        y = title_height + row_index * (thumb_height + label_height)
        for column, variant in enumerate(("base", "lora")):
            record = pair[variant]
            image_name = PurePosixPath(record["image_path"]).name
            image_path = generated_root / "evaluation" / variant / image_name
            with Image.open(image_path) as source:
                thumb = ImageOps.fit(source.convert("RGB"), (thumb_width, thumb_height))
            sheet.paste(thumb, (column * thumb_width, y))
            draw.text(
                (column * thumb_width + 6, y + thumb_height + 5),
                f"{variant} | p{record['prompt_index']} | seed {record['seed']}",
                fill=(0, 0, 0),
            )
        draw.line(
            (0, y + thumb_height + label_height - 1, thumb_width * 2, y + thumb_height + label_height - 1),
            fill=(210, 210, 210),
        )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(output_path, format="JPEG", quality=88, optimize=True)


def _write_local_human_template(
    source_rows: list[dict[str, str]],
    path: Path,
) -> str:
    if not source_rows:
        raise RuntimeError("Human evaluation template is empty")
    if path.exists():
        return "preserved_existing"
    rows: list[dict[str, str]] = []
    for source in source_rows:
        row = dict(source)
        variant = row["variant"]
        image_name = PurePosixPath(row["expected_image_path"]).name
        row["expected_image_path"] = f"generated/evaluation/{variant}/{image_name}"
        rows.append(row)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    return "created"


def materialize_evidence(artifact_zip: Path, output_dir: Path, model_dir: Path) -> dict[str, Any]:
    validation = validate_kaggle_export(artifact_zip)
    if not validation.valid:
        raise RuntimeError("Kaggle export validation failed: " + "; ".join(validation.errors))

    output_dir.mkdir(parents=True, exist_ok=True)
    generated_root = output_dir / "generated"
    with zipfile.ZipFile(artifact_zip) as archive:
        for name in EVIDENCE_ENTRIES:
            _atomic_write(output_dir / name, archive.read(name))

        model_bytes = archive.read(MODEL_FILENAME)
        model_path = model_dir / MODEL_FILENAME
        _atomic_write(model_path, model_bytes)
        model_sha = hashlib.sha256(model_bytes).hexdigest()
        if model_sha != validation.evidence["model_sha256"] or _sha256_file(model_path) != model_sha:
            raise RuntimeError("Materialized LoRA SHA-256 mismatch")
        _atomic_write(
            model_dir / "multisource_multicrop_lora.sha256",
            f"{model_sha}  {MODEL_FILENAME}\n".encode(),
        )

        evaluation_manifest = json.loads(
            archive.read("evaluation/evaluation_manifest.json").decode("utf-8")
        )
        evaluation_records = evaluation_manifest["records"]
        for record in evaluation_records:
            variant = record["variant"]
            image_name = PurePosixPath(record["image_path"]).name
            _extract_image(
                archive,
                f"evaluation/{variant}/{image_name}",
                generated_root,
            )
        sanity_manifest = json.loads(
            archive.read("sanity/sanity_manifest.json").decode("utf-8")
        )
        for record in sanity_manifest:
            image_name = PurePosixPath(record["path"]).name
            _extract_image(archive, f"sanity/{image_name}", generated_root)

        human_rows = _read_csv(archive, "evaluation/human_evaluation_template.csv")
        human_template_action = _write_local_human_template(
            human_rows, output_dir / "human_evaluation_template_local.csv"
        )
        metric_rows = _read_csv(archive, "evaluation/automated_proxy_metrics.csv")
        smoke_losses = _read_csv(archive, "smoke_loss_history.csv")
        main_losses = _read_csv(archive, "main_loss_history.csv")

    for class_id in ("padi", "jagung", "cabai", "kacang_tanah"):
        _make_contact_sheet(
            class_id,
            evaluation_records,
            generated_root,
            output_dir / "contact_sheets" / f"{class_id}_base_vs_lora.jpg",
        )

    proxy_summary = _proxy_summary(metric_rows)
    summary = {
        "schema_version": 1,
        "source_artifact_zip": str(artifact_zip.resolve()),
        "source_artifact_sha256": validation.artifact_sha256,
        "validation": validation.to_dict(),
        "model_path": str(model_path.resolve()),
        "model_sha256": model_sha,
        "smoke_loss": _loss_summary(smoke_losses),
        "main_loss": _loss_summary(main_losses),
        "proxy_metrics": proxy_summary,
        "human_evaluation_status": "pending_real_human_review",
        "human_template_action": human_template_action,
    }
    (output_dir / "local_evidence_summary.json").write_text(
        json.dumps(summary, indent=2) + "\n", encoding="utf-8"
    )
    _write_proxy_summary(output_dir / "proxy_metrics_summary.csv", proxy_summary)
    _write_results_markdown(output_dir / "RESULTS.md", summary)
    return summary


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Materialize validated Kaggle LoRA evidence without running Stable Diffusion."
    )
    parser.add_argument("--artifact-zip", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--model-dir", type=Path, required=True)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    summary = materialize_evidence(args.artifact_zip, args.output_dir, args.model_dir)
    print(
        json.dumps(
            {
                "status": "success",
                "run_id": summary["validation"]["evidence"]["run_id"],
                "model_path": summary["model_path"],
                "model_sha256": summary["model_sha256"],
                "output_dir": str(args.output_dir.resolve()),
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
