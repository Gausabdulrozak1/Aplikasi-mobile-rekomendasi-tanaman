from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from pathlib import Path

MAX_SAFETENSORS_HEADER_BYTES = 16 * 1024 * 1024


@dataclass(frozen=True)
class LoraArtifactInfo:
    path: str
    size_bytes: int
    sha256: str
    tensor_count: int
    data_bytes: int

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _normalize_sha256(value: str) -> str:
    normalized = value.strip().lower()
    if len(normalized) != 64 or any(
        character not in "0123456789abcdef" for character in normalized
    ):
        raise RuntimeError("LORA_SHA256 must be a complete lowercase or uppercase SHA-256 value.")
    return normalized


def validate_lora_artifact(raw_path: str, expected_sha256: str) -> LoraArtifactInfo:
    if not raw_path.strip():
        raise RuntimeError("LORA_PATH is required for the Diffusers provider.")
    if not expected_sha256.strip():
        raise RuntimeError("LORA_SHA256 is required for the Diffusers provider.")
    expected_sha256 = _normalize_sha256(expected_sha256)
    path = Path(raw_path).expanduser().resolve()
    if not path.is_file():
        raise RuntimeError("Configured LoRA artifact was not found as a regular file.")
    if path.suffix.casefold() != ".safetensors":
        raise RuntimeError("Configured LoRA artifact must be a .safetensors file.")
    size_bytes = path.stat().st_size
    if size_bytes <= 8:
        raise RuntimeError("Configured LoRA SafeTensors artifact is empty or truncated.")

    actual_sha256 = _sha256_file(path)
    if actual_sha256 != expected_sha256:
        raise RuntimeError("Configured LoRA artifact SHA-256 does not match LORA_SHA256.")

    with path.open("rb") as handle:
        header_size = int.from_bytes(handle.read(8), byteorder="little", signed=False)
        if (
            header_size <= 0
            or header_size > MAX_SAFETENSORS_HEADER_BYTES
            or header_size > size_bytes - 8
        ):
            raise RuntimeError("Configured LoRA SafeTensors header length is invalid.")
        try:
            header = json.loads(handle.read(header_size).decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise RuntimeError("Configured LoRA SafeTensors header cannot be opened.") from exc
    if not isinstance(header, dict):
        raise RuntimeError("Configured LoRA SafeTensors header must be an object.")

    data_bytes = size_bytes - 8 - header_size
    tensors = {key: value for key, value in header.items() if key != "__metadata__"}
    if not tensors:
        raise RuntimeError("Configured LoRA SafeTensors artifact contains no tensors.")
    nonempty_tensors = 0
    for tensor_name, descriptor in tensors.items():
        if not isinstance(descriptor, dict):
            raise RuntimeError(f"Invalid LoRA tensor descriptor: {tensor_name}.")
        offsets = descriptor.get("data_offsets")
        shape = descriptor.get("shape")
        dtype = descriptor.get("dtype")
        valid_offsets = (
            isinstance(offsets, list)
            and len(offsets) == 2
            and all(isinstance(item, int) for item in offsets)
            and 0 <= offsets[0] <= offsets[1] <= data_bytes
        )
        valid_shape = isinstance(shape, list) and all(
            isinstance(item, int) and item >= 0 for item in shape
        )
        if not valid_offsets or not valid_shape or not isinstance(dtype, str) or not dtype:
            raise RuntimeError(f"Invalid LoRA tensor metadata: {tensor_name}.")
        if offsets[1] > offsets[0]:
            nonempty_tensors += 1
    if nonempty_tensors == 0:
        raise RuntimeError("Configured LoRA SafeTensors artifact contains no tensor data.")

    return LoraArtifactInfo(
        path=str(path),
        size_bytes=size_bytes,
        sha256=actual_sha256,
        tensor_count=len(tensors),
        data_bytes=data_bytes,
    )
