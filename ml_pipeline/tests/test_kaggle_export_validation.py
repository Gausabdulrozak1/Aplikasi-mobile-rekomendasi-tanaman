from __future__ import annotations

import csv
import hashlib
import io
import json
import zipfile
from pathlib import Path

from PIL import Image

from ml_pipeline.src.training.validate_kaggle_export import (
    MODEL_FILENAME,
    validate_kaggle_export,
)


def _json_bytes(value: object) -> bytes:
    return (json.dumps(value) + "\n").encode()


def _csv_bytes(fieldnames: list[str], rows: list[dict[str, object]]) -> bytes:
    output = io.StringIO(newline="")
    writer = csv.DictWriter(output, fieldnames=fieldnames)
    writer.writeheader()
    writer.writerows(rows)
    return output.getvalue().encode()


def _fixture_safetensors() -> bytes:
    header = json.dumps(
        {
            "fixture.weight": {
                "dtype": "F32",
                "shape": [1],
                "data_offsets": [0, 4],
            }
        },
        separators=(",", ":"),
    ).encode()
    padded_header = header + b" " * ((8 - len(header) % 8) % 8)
    return len(padded_header).to_bytes(8, "little") + padded_header + b"\0" * 4


def _fixture_png(color: tuple[int, int, int]) -> bytes:
    output = io.BytesIO()
    Image.new("RGB", (2, 2), color=color).save(output, format="PNG")
    return output.getvalue()


def _write_fixture_export(path: Path, *, canonical_model: bool = True) -> None:
    model = _fixture_safetensors()
    model_sha = hashlib.sha256(model).hexdigest()
    dataset_sha = "d" * 64
    run_id = "fixture-run"
    base_image = _fixture_png((0, 100, 0))
    lora_image = _fixture_png((0, 200, 0))
    sanity_image = _fixture_png((0, 150, 0))
    evaluation_records = [
        {
            "condition_id": "padi_p1_s42",
            "class_id": "padi",
            "prompt_index": 1,
            "prompt": "fixture prompt",
            "seed": 42,
            "variant": "base",
            "image_path": "/kaggle/working/evaluation/base/padi_base.png",
            "image_sha256": hashlib.sha256(base_image).hexdigest(),
        },
        {
            "condition_id": "padi_p1_s42",
            "class_id": "padi",
            "prompt_index": 1,
            "prompt": "fixture prompt",
            "seed": 42,
            "variant": "lora",
            "image_path": "/kaggle/working/evaluation/lora/padi_lora.png",
            "image_sha256": hashlib.sha256(lora_image).hexdigest(),
        },
    ]
    evaluation_csv_rows = [
        {
            "condition_id": row["condition_id"],
            "variant": row["variant"],
            "class_id": row["class_id"],
            "prompt_index": row["prompt_index"],
            "prompt": row["prompt"],
            "seed": row["seed"],
            "image_path": row["image_path"],
            "image_sha256": row["image_sha256"],
        }
        for row in evaluation_records
    ]
    metric_rows = [
        {
            "condition_id": row["condition_id"],
            "variant": row["variant"],
            "class_id": row["class_id"],
            "seed": row["seed"],
            "brightness_proxy": 1,
            "contrast_proxy": 1,
            "entropy_proxy": 1,
            "human_quality_claim": "",
        }
        for row in evaluation_records
    ]
    human_rows = [
        {
            "condition_id": row["condition_id"],
            "variant": row["variant"],
            "class_id": row["class_id"],
            "prompt": row["prompt"],
            "seed": row["seed"],
            "expected_image_path": row["image_path"],
            "crop_correct": "",
            "field_context_quality": "",
            "visual_realism_score": "",
            "class_confusion": "",
            "reviewer_role": "",
            "reviewer_notes": "",
        }
        for row in evaluation_records
    ]

    files: dict[str, bytes] = {
        MODEL_FILENAME if canonical_model else "pytorch_lora_weights.safetensors": model,
        "multisource_multicrop_lora.sha256": f"{model_sha}  {MODEL_FILENAME}\n".encode(),
        "dataset_package_sha256.txt": f"{dataset_sha}\n".encode(),
        "training_config.json": _json_bytes({"fixture": True}),
        "smoke_loss_history.csv": b"observation,loss\n1,0.1\n",
        "main_loss_history.csv": b"observation,loss\n1,0.2\n",
        "smoke_validation.json": _json_bytes(
            {
                "status": "pass",
                "return_code": 0,
                "actual_step": 100,
                "checkpoint_100_valid": True,
                "lora_validation": {"valid": True},
                "dataset_package_sha256": dataset_sha,
                "loss_count": 1,
                "elapsed_seconds": 1.0,
            }
        ),
        "main_validation.json": _json_bytes(
            {
                "status": "success",
                "return_code": 0,
                "actual_step": 1600,
                "checkpoint_valid": True,
                "canonical_lora_validation": {"valid": True},
                "canonical_lora_sha256": model_sha,
                "dataset_package_sha256": dataset_sha,
                "loss_count": 1,
                "elapsed_seconds": 2.0,
            }
        ),
        "sanity/sanity_padi.png": sanity_image,
        "sanity/sanity_manifest.json": _json_bytes(
            [
                {
                    "class_id": "padi",
                    "path": "/kaggle/working/sanity/sanity_padi.png",
                    "sha256": hashlib.sha256(sanity_image).hexdigest(),
                }
            ]
        ),
        "evaluation/base/padi_base.png": base_image,
        "evaluation/lora/padi_lora.png": lora_image,
        "evaluation/evaluation_manifest.json": _json_bytes(
            {
                "status": "complete",
                "conditions": 1,
                "expected_images": 2,
                "generated_images": 2,
                "records": evaluation_records,
            }
        ),
        "evaluation/evaluation_manifest.csv": _csv_bytes(
            list(evaluation_csv_rows[0]), evaluation_csv_rows
        ),
        "evaluation/automated_proxy_metrics.csv": _csv_bytes(
            list(metric_rows[0]), metric_rows
        ),
        "evaluation/human_evaluation_template.csv": _csv_bytes(
            list(human_rows[0]), human_rows
        ),
        "final_training_report.md": b"# Synthetic fixture\n",
        "final_training_report.json": _json_bytes(
            {
                "run_id": run_id,
                "status": "training_and_sanity_success",
                "dataset_package_sha256": dataset_sha,
                "evaluation_status": "complete",
                "gpu": {"name": "fixture GPU"},
                "dataset_counts": {"total": 1},
            }
        ),
        "complete_pipeline_state.json": _json_bytes(
            {
                "run_id": run_id,
                "current_stage": "complete_kaggle_pipeline",
                "status": "success",
                "dataset_package_sha256": dataset_sha,
                "final_lora_sha256": model_sha,
                "evaluation_status": "complete",
                "automated_metrics_are_proxy": True,
                "human_evaluation_status": "pending_real_human_review",
                "rule_engine_remains_authoritative": True,
            }
        ),
        "final_integrity.json": _json_bytes(
            {
                "status": "pass",
                "missing_entries": [],
                "model_sha256_expected": model_sha,
                "model_sha256_in_zip": model_sha,
                "smoke_status": "pass",
                "main_status": "success",
                "sanity_status": "pass",
                "evaluation_status": "complete",
                "human_template_blank_rows": 2,
            }
        ),
        "export_manifest.json": _json_bytes([]),
    }
    with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for name, value in files.items():
            archive.writestr(name, value)


def test_kaggle_export_validator_accepts_complete_evidence(tmp_path: Path) -> None:
    artifact = tmp_path / "artifact.zip"
    _write_fixture_export(artifact)

    result = validate_kaggle_export(
        artifact,
        expected_evaluation_images=2,
        required_class_ids=("padi",),
    )

    assert result.valid is True
    assert result.errors == []
    assert result.evidence["safetensors"]["tensor_count"] == 1
    assert result.evidence["evaluation_images_valid"] == 2
    assert result.evidence["human_template_blank_rows"] == 2


def test_kaggle_export_validator_rejects_diffusers_default_filename(tmp_path: Path) -> None:
    artifact = tmp_path / "artifact.zip"
    _write_fixture_export(artifact, canonical_model=False)

    result = validate_kaggle_export(
        artifact,
        expected_evaluation_images=2,
        required_class_ids=("padi",),
    )

    assert result.valid is False
    assert f"required ZIP entry is missing: {MODEL_FILENAME}" in result.errors
    assert "LoRA SafeTensors artifact is empty or truncated" in result.errors
