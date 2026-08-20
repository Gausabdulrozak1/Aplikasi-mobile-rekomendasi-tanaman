from __future__ import annotations

import csv
import json
from pathlib import Path

from PIL import Image

from ml_pipeline.src.training.validate_run import REQUIRED_CLASS_IDS, validate_training_run


def _write_json(path: Path, value: object) -> None:
    path.write_text(json.dumps(value), encoding="utf-8")


def _write_fixture_safetensors(path: Path) -> None:
    header = json.dumps(
        {
            "fixture.weight": {
                "dtype": "F32",
                "shape": [1],
                "data_offsets": [0, 4],
            },
            "__metadata__": {"purpose": "synthetic automated test fixture"},
        },
        separators=(",", ":"),
    ).encode("utf-8")
    padding = b" " * ((8 - len(header) % 8) % 8)
    padded_header = header + padding
    path.write_bytes(len(padded_header).to_bytes(8, "little") + padded_header + b"\0" * 4)


def _make_valid_run(root: Path, *, steps: int = 100) -> None:
    root.mkdir()
    checkpoint = root / f"checkpoint-{steps}"
    checkpoint.mkdir()
    (checkpoint / "fixture_state.json").write_text(
        '{"purpose":"synthetic automated test fixture"}', encoding="utf-8"
    )
    _write_fixture_safetensors(root / "fixture_lora.safetensors")
    (root / "training.log").write_text("step=100 loss=0.125\n", encoding="utf-8")
    with (root / "loss_log.csv").open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(["observation", "loss"])
        writer.writerow([1, 0.25])
        writer.writerow([2, 0.125])
    _write_json(
        root / "actual_training_config.json",
        {"run_mode": "smoke", "training": {"max_train_steps": steps}},
    )
    _write_json(
        root / "training_manifest.json",
        {"status": "success", "target_steps": steps},
    )
    _write_json(root / "training_environment_report.json", {"gpu": "fixture GPU"})
    validation = root / "validation_images"
    validation.mkdir()
    for class_id in REQUIRED_CLASS_IDS:
        Image.new("RGB", (2, 2), color=(0, 128, 0)).save(validation / f"{class_id}_seed_42.png")


def test_training_run_validator_accepts_complete_fixture_evidence(tmp_path: Path) -> None:
    output = tmp_path / "run"
    _make_valid_run(output)

    result = validate_training_run(
        output,
        expected_steps=100,
        lora_filename="fixture_lora.safetensors",
    )

    assert result.valid is True
    assert result.errors == []
    assert result.evidence["checkpoint_file_count"] == 1
    assert result.evidence["safetensors"]["tensor_count"] == 1
    assert result.evidence["loss_observations"] == 2
    assert set(result.evidence["validation_images"]) == set(REQUIRED_CLASS_IDS)


def test_training_run_validator_rejects_nonfinite_loss_and_missing_evidence(
    tmp_path: Path,
) -> None:
    output = tmp_path / "run"
    _make_valid_run(output)
    (output / "checkpoint-100" / "fixture_state.json").unlink()
    (output / "checkpoint-100").rmdir()
    (output / "validation_images" / "cabai_seed_42.png").unlink()
    (output / "loss_log.csv").write_text("observation,loss\n1,nan\n", encoding="utf-8")
    (output / "fixture_lora.safetensors").write_bytes(b"not-a-safetensors-file")

    result = validate_training_run(
        output,
        expected_steps=100,
        lora_filename="fixture_lora.safetensors",
    )

    assert result.valid is False
    assert "missing final checkpoint: checkpoint-100" in result.errors
    assert "non-finite loss at CSV row 2" in result.errors
    assert "missing or invalid validation image for class: cabai" in result.errors
    assert "invalid SafeTensors header length: fixture_lora.safetensors" in result.errors
