from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from inference_api.app.core.config import Settings
from inference_api.app.providers.diffusers_provider import DiffusersImageGenerator
from inference_api.app.providers.lora_validation import validate_lora_artifact


def _write_fixture_safetensors(path: Path) -> str:
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
    value = len(padded_header).to_bytes(8, "little") + padded_header + b"\0" * 4
    path.write_bytes(value)
    return hashlib.sha256(value).hexdigest()


def test_lora_artifact_validator_accepts_hash_and_tensor_data(tmp_path: Path) -> None:
    path = tmp_path / "fixture.safetensors"
    expected_sha256 = _write_fixture_safetensors(path)

    result = validate_lora_artifact(str(path), expected_sha256.upper())

    assert result.path == str(path.resolve())
    assert result.sha256 == expected_sha256
    assert result.tensor_count == 1
    assert result.data_bytes == 4


@pytest.mark.parametrize(
    ("path_value", "sha_value", "message"),
    [
        ("", "0" * 64, "LORA_PATH is required"),
        ("missing.safetensors", "0" * 64, "was not found as a regular file"),
        ("fixture.safetensors", "", "LORA_SHA256 is required"),
        ("fixture.safetensors", "invalid", "complete lowercase or uppercase SHA-256"),
        ("fixture.safetensors", "0" * 64, "does not match LORA_SHA256"),
    ],
)
def test_lora_artifact_validator_rejects_invalid_contract(
    tmp_path: Path,
    path_value: str,
    sha_value: str,
    message: str,
) -> None:
    fixture = tmp_path / "fixture.safetensors"
    _write_fixture_safetensors(fixture)
    raw_path = str(tmp_path / path_value) if path_value else ""

    with pytest.raises(RuntimeError, match=message):
        validate_lora_artifact(raw_path, sha_value)


def test_diffusers_provider_validates_lora_before_importing_ml_runtime(tmp_path: Path) -> None:
    settings = Settings(
        _env_file=None,
        provider="diffusers",
        generated_dir=tmp_path / "generated",
        lora_path=str(tmp_path / "missing.safetensors"),
        lora_sha256="0" * 64,
        require_gpu=True,
    )

    provider = DiffusersImageGenerator(settings)
    health = provider.health()

    assert health["model_loaded"] is False
    assert health["lora_validated"] is False
    assert "regular file" in str(health["reason"])
