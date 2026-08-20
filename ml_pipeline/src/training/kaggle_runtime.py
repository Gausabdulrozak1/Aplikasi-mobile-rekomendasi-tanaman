from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Iterable

CHECKPOINT_PATTERN = re.compile(r"^checkpoint-(\d+)$")
RESUME_COMPATIBILITY_FIELDS = (
    "dataset_package_sha256",
    "base_model",
    "resolution",
    "rank",
    "seed",
    "learning_rate",
    "optimizer",
    "train_count",
)


def checkpoint_step(path: Path | str) -> int | None:
    match = CHECKPOINT_PATTERN.fullmatch(Path(path).name)
    return int(match.group(1)) if match else None


def checkpoint_is_structurally_valid(path: Path | str) -> bool:
    path = Path(path)
    if checkpoint_step(path) is None or not path.is_dir():
        return False
    files = [item for item in path.rglob("*") if item.is_file() and item.stat().st_size > 0]
    names = {item.name for item in files}
    return bool(files) and all(
        any(name.startswith(prefix) for name in names)
        for prefix in ("optimizer", "scheduler", "random_states")
    )


def newest_valid_checkpoint(paths: Iterable[Path | str]) -> Path | None:
    candidates = [Path(path) for path in paths]
    valid = [path for path in candidates if checkpoint_is_structurally_valid(path)]
    return max(valid, key=lambda path: checkpoint_step(path) or -1, default=None)


def resume_compatibility(
    manifest: dict[str, object],
    expected: dict[str, object],
    fields: Iterable[str] = RESUME_COMPATIBILITY_FIELDS,
) -> tuple[bool, list[str]]:
    errors = []
    for field in fields:
        if manifest.get(field) != expected.get(field):
            errors.append(
                f"{field}: manifest={manifest.get(field)!r}, expected={expected.get(field)!r}"
            )
    if manifest.get("run_mode") != "main":
        errors.append(f"run_mode: manifest={manifest.get('run_mode')!r}, expected='main'")
    return not errors, errors


def inspect_safetensors_file(path: Path | str) -> dict[str, object]:
    path = Path(path)
    report: dict[str, object] = {
        "path": str(path),
        "exists": path.exists(),
        "is_file": path.is_file(),
        "size_bytes": path.stat().st_size if path.is_file() else 0,
        "tensor_keys": 0,
        "valid": False,
        "errors": [],
    }
    errors = report["errors"]
    assert isinstance(errors, list)
    if not path.is_file():
        errors.append("file does not exist or is a directory")
        return report
    size = path.stat().st_size
    if size == 0:
        errors.append("file is zero bytes")
        return report
    if size < 10:
        errors.append("file is too small for a safetensors header")
        return report
    try:
        with path.open("rb") as handle:
            header_length = int.from_bytes(handle.read(8), "little", signed=False)
            if header_length <= 1 or header_length > size - 8:
                raise ValueError(f"invalid header length {header_length}")
            header = json.loads(handle.read(header_length).decode("utf-8"))
        if not isinstance(header, dict):
            raise ValueError("header is not a JSON object")
        tensor_items = {key: value for key, value in header.items() if key != "__metadata__"}
        if not tensor_items:
            raise ValueError("no tensor keys")
        data_size = size - 8 - header_length
        for key, value in tensor_items.items():
            if not isinstance(value, dict):
                raise ValueError(f"tensor {key} descriptor is not an object")
            offsets = value.get("data_offsets")
            if (
                not isinstance(offsets, list)
                or len(offsets) != 2
                or not all(isinstance(item, int) for item in offsets)
                or offsets[0] < 0
                or offsets[1] <= offsets[0]
                or offsets[1] > data_size
            ):
                raise ValueError(f"tensor {key} has invalid data offsets")
        report["tensor_keys"] = len(tensor_items)
        report["valid"] = True
    except (OSError, UnicodeDecodeError, json.JSONDecodeError, ValueError) as exc:
        errors.append(str(exc))
    return report
