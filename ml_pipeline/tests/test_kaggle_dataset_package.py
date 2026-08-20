from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from ml_pipeline.src.dataset.kaggle_package import (
    KaggleDatasetBuildError,
    PhysicalImage,
    copy_image_byte_exact,
    ensure_unique_target_name,
    make_imagefolder_metadata_row,
    read_jsonl,
    resolve_metadata_row,
    validate_image_decode,
    write_jsonl,
)
from ml_pipeline.src.training.kaggle_runtime import (
    checkpoint_step,
    inspect_safetensors_file,
    newest_valid_checkpoint,
    resume_compatibility,
)


def _record(path: str, sha: str = "a" * 64) -> PhysicalImage:
    return PhysicalImage(
        split="train",
        absolute_source_path=f"C:/repo/processed/train/{path}",
        relative_source_path=f"ml_pipeline/data/processed/train/{path}",
        split_relative_path=path,
        basename=Path(path).name,
        extension=Path(path).suffix.lower(),
        byte_size=123,
        sha256=sha,
        class_id="padi",
        source_type="public",
        provenance_identifier="image-test",
        source_identifier="source-test",
        original_file_name="original.jpg",
    )


@pytest.mark.parametrize(
    ("file_name", "method"),
    (("padi/padi_0001.jpg", "exact_relative_path"), (r"padi\padi_0001.jpg", "exact_relative_path")),
)
def test_metadata_resolution_exact_path_and_windows_slash(file_name: str, method: str) -> None:
    result = resolve_metadata_row(
        "train",
        0,
        {"file_name": file_name},
        [_record("padi/padi_0001.jpg")],
    )

    assert result.status == "resolved"
    assert result.method == method
    assert result.image is not None
    assert result.image.split_relative_path == "padi/padi_0001.jpg"


def test_metadata_resolution_uses_only_unique_basename() -> None:
    result = resolve_metadata_row(
        "train",
        0,
        {"file_name": "legacy/padi_0001.jpg"},
        [_record("padi/padi_0001.jpg"), _record("padi/padi_0002.jpg")],
    )

    assert result.status == "resolved"
    assert result.method == "unique_basename"


def test_metadata_resolution_reports_missing_image() -> None:
    result = resolve_metadata_row(
        "train",
        0,
        {"file_name": "missing.jpg"},
        [_record("padi/padi_0001.jpg")],
    )

    assert result.status == "unresolved"
    assert result.image is None


def test_metadata_resolution_reports_ambiguous_basename() -> None:
    result = resolve_metadata_row(
        "train",
        0,
        {"file_name": "legacy/shared.jpg"},
        [_record("padi/shared.jpg"), _record("jagung/shared.jpg")],
    )

    assert result.status == "ambiguous"
    assert result.image is None
    assert result.candidate_paths == ("jagung/shared.jpg", "padi/shared.jpg")


def test_corrupted_image_is_rejected(tmp_path: Path) -> None:
    corrupt = tmp_path / "corrupt.jpg"
    corrupt.write_bytes(b"not-a-real-image")

    with pytest.raises(Exception):
        validate_image_decode(corrupt)


def test_duplicate_target_filename_is_rejected() -> None:
    names = {"train_0000_aaaaaaaaaaaa.jpg"}

    with pytest.raises(KaggleDatasetBuildError, match="duplicate target filename"):
        ensure_unique_target_name("train_0000_aaaaaaaaaaaa.jpg", names)


def test_source_target_sha_mismatch_is_rejected(tmp_path: Path) -> None:
    source = tmp_path / "source.jpg"
    target = tmp_path / "target.jpg"
    source.write_bytes(b"source-bytes")
    expected = hashlib.sha256(source.read_bytes()).hexdigest()

    def corrupt_copy(_source: Path, destination: Path) -> None:
        destination.write_bytes(b"different-bytes")

    with pytest.raises(KaggleDatasetBuildError, match="source-target SHA mismatch"):
        copy_image_byte_exact(source, target, expected, corrupt_copy)


def test_imagefolder_staging_manifest_preserves_provenance_safely(tmp_path: Path) -> None:
    original = {
        "file_name": "padi/padi_0001.jpg",
        "original_file_name": "IMG_20240923_181506.jpg",
        "text": "a photo of taniadaptif_padi",
        "class_id": "padi",
        "trigger_token": "taniadaptif_padi",
        "source_type": "local_aikmel",
    }
    staged, renamed = make_imagefolder_metadata_row(original, "train_0000_aaaaaaaaaaaa.jpg")
    metadata = tmp_path / "metadata.jsonl"
    write_jsonl(metadata, [staged])

    assert read_jsonl(metadata) == [staged]
    assert staged["file_name"] == "train_0000_aaaaaaaaaaaa.jpg"
    assert staged["source_original_name"] == "IMG_20240923_181506.jpg"
    assert "original_file_name" not in staged
    assert renamed == {"original_file_name": "source_original_name"}
    assert not [key for key in staged if key != "file_name" and key.endswith("_file_name")]


def _valid_checkpoint(root: Path, step: int) -> Path:
    checkpoint = root / f"checkpoint-{step}"
    checkpoint.mkdir()
    for name in ("optimizer.bin", "scheduler.bin", "random_states_0.pkl"):
        (checkpoint / name).write_bytes(b"state")
    return checkpoint


def test_checkpoint_parser_uses_highest_numeric_valid_checkpoint(tmp_path: Path) -> None:
    checkpoint_200 = _valid_checkpoint(tmp_path, 200)
    checkpoint_1000 = _valid_checkpoint(tmp_path, 1000)
    invalid = tmp_path / "checkpoint-final"
    invalid.mkdir()

    assert checkpoint_step(checkpoint_200) == 200
    assert checkpoint_step(invalid) is None
    assert newest_valid_checkpoint([checkpoint_200, invalid, checkpoint_1000]) == checkpoint_1000


def test_resume_compatibility_requires_exact_main_manifest() -> None:
    expected = {
        "dataset_package_sha256": "dataset-sha",
        "base_model": "stable-diffusion-v1-5/stable-diffusion-v1-5",
        "resolution": 512,
        "rank": 8,
        "seed": 42,
        "learning_rate": 0.0001,
        "optimizer": "adamw_8bit",
        "train_count": 312,
    }
    manifest = {"run_mode": "main", **expected}

    assert resume_compatibility(manifest, expected) == (True, [])
    manifest["rank"] = 16
    compatible, errors = resume_compatibility(manifest, expected)
    assert compatible is False
    assert any(error.startswith("rank:") for error in errors)


def test_invalid_and_zero_byte_safetensors_are_rejected(tmp_path: Path) -> None:
    invalid = tmp_path / "invalid.safetensors"
    invalid.write_bytes(b"not-safetensors")
    zero = tmp_path / "zero.safetensors"
    zero.touch()

    assert inspect_safetensors_file(invalid)["valid"] is False
    zero_report = inspect_safetensors_file(zero)
    assert zero_report["valid"] is False
    assert "file is zero bytes" in zero_report["errors"]


def test_minimal_safetensors_header_is_accepted(tmp_path: Path) -> None:
    path = tmp_path / "valid.safetensors"
    header = json.dumps(
        {"lora.weight": {"dtype": "F32", "shape": [1], "data_offsets": [0, 4]}},
        separators=(",", ":"),
    ).encode("utf-8")
    path.write_bytes(len(header).to_bytes(8, "little") + header + b"\x00\x00\x00\x00")

    report = inspect_safetensors_file(path)
    assert report["valid"] is True
    assert report["tensor_keys"] == 1
