from __future__ import annotations

import argparse
import csv
import json
import math
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Sequence

from PIL import Image, UnidentifiedImageError

REQUIRED_CLASS_IDS = ("padi", "jagung", "cabai", "kacang_tanah")
MAX_SAFETENSORS_HEADER_BYTES = 16 * 1024 * 1024
FATAL_LOG_MARKERS = (
    "traceback (most recent call last)",
    "cuda out of memory",
    "runtimeerror:",
    "fatal error",
)


@dataclass(frozen=True)
class TrainingRunValidation:
    valid: bool
    output_directory: str
    expected_steps: int
    lora_filename: str
    errors: list[str] = field(default_factory=list)
    evidence: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _read_json(path: Path, errors: list[str]) -> dict[str, Any]:
    if not path.is_file():
        errors.append(f"missing JSON evidence: {path.name}")
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        errors.append(f"invalid JSON evidence {path.name}: {exc}")
        return {}
    if not isinstance(data, dict):
        errors.append(f"JSON evidence must be an object: {path.name}")
        return {}
    return data


def _read_losses(path: Path, errors: list[str]) -> list[float]:
    if not path.is_file():
        errors.append("missing loss evidence: loss_log.csv")
        return []
    try:
        with path.open(encoding="utf-8-sig", newline="") as handle:
            rows = list(csv.DictReader(handle))
    except OSError as exc:
        errors.append(f"cannot read loss_log.csv: {exc}")
        return []

    values: list[float] = []
    for row_number, row in enumerate(rows, start=2):
        raw_value = row.get("loss", "")
        try:
            value = float(raw_value)
        except (TypeError, ValueError):
            errors.append(f"invalid loss at CSV row {row_number}")
            continue
        if not math.isfinite(value):
            errors.append(f"non-finite loss at CSV row {row_number}")
            continue
        values.append(value)
    if not rows:
        errors.append("loss_log.csv has no observations")
    return values


def _validate_safetensors(path: Path, errors: list[str]) -> dict[str, int]:
    details = {"tensor_count": 0, "header_bytes": 0, "data_bytes": 0}
    if not path.is_file() or path.stat().st_size <= 8:
        errors.append(f"missing or invalid LoRA artifact: {path.name}")
        return details

    try:
        with path.open("rb") as handle:
            header_size_bytes = handle.read(8)
            header_size = int.from_bytes(header_size_bytes, byteorder="little", signed=False)
            file_size = path.stat().st_size
            if (
                header_size <= 0
                or header_size > MAX_SAFETENSORS_HEADER_BYTES
                or header_size > file_size - 8
            ):
                errors.append(f"invalid SafeTensors header length: {path.name}")
                return details
            header = json.loads(handle.read(header_size).decode("utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        errors.append(f"invalid SafeTensors header {path.name}: {exc}")
        return details

    if not isinstance(header, dict):
        errors.append(f"SafeTensors header must be an object: {path.name}")
        return details

    data_size = path.stat().st_size - 8 - header_size
    tensor_entries = {key: value for key, value in header.items() if key != "__metadata__"}
    if not tensor_entries:
        errors.append(f"SafeTensors file contains no tensors: {path.name}")

    nonempty_tensor_count = 0
    for tensor_name, descriptor in tensor_entries.items():
        if not isinstance(descriptor, dict):
            errors.append(f"invalid tensor descriptor in {path.name}: {tensor_name}")
            continue
        offsets = descriptor.get("data_offsets")
        shape = descriptor.get("shape")
        dtype = descriptor.get("dtype")
        valid_offsets = (
            isinstance(offsets, list)
            and len(offsets) == 2
            and all(isinstance(value, int) for value in offsets)
            and 0 <= offsets[0] <= offsets[1] <= data_size
        )
        valid_shape = isinstance(shape, list) and all(
            isinstance(value, int) and value >= 0 for value in shape
        )
        if not valid_offsets or not valid_shape or not isinstance(dtype, str) or not dtype:
            errors.append(f"invalid tensor metadata in {path.name}: {tensor_name}")
            continue
        if offsets[1] > offsets[0]:
            nonempty_tensor_count += 1

    if tensor_entries and nonempty_tensor_count == 0:
        errors.append(f"SafeTensors file contains no tensor data: {path.name}")

    details.update(
        {
            "tensor_count": len(tensor_entries),
            "header_bytes": header_size,
            "data_bytes": data_size,
        }
    )
    return details


def _valid_image(path: Path) -> bool:
    try:
        with Image.open(path) as image:
            image.verify()
            return image.width > 0 and image.height > 0
    except (OSError, UnidentifiedImageError):
        return False


def validate_training_run(
    output_directory: Path,
    *,
    expected_steps: int,
    lora_filename: str,
    required_class_ids: Sequence[str] = REQUIRED_CLASS_IDS,
) -> TrainingRunValidation:
    output_directory = output_directory.resolve()
    errors: list[str] = []
    evidence: dict[str, Any] = {}

    if expected_steps <= 0:
        errors.append("expected_steps must be positive")
    if not lora_filename.endswith(".safetensors") or Path(lora_filename).name != lora_filename:
        errors.append("lora_filename must be a basename ending in .safetensors")
    if not output_directory.is_dir():
        errors.append(f"output directory not found: {output_directory}")
        return TrainingRunValidation(
            valid=False,
            output_directory=str(output_directory),
            expected_steps=expected_steps,
            lora_filename=lora_filename,
            errors=errors,
            evidence=evidence,
        )

    actual_config = _read_json(output_directory / "actual_training_config.json", errors)
    manifest = _read_json(output_directory / "training_manifest.json", errors)
    environment = _read_json(output_directory / "training_environment_report.json", errors)

    if manifest and manifest.get("status") != "success":
        errors.append("training_manifest.json does not report status=success")
    if manifest and manifest.get("target_steps") != expected_steps:
        errors.append("training manifest target_steps does not match expected_steps")
    if actual_config:
        configured_steps = actual_config.get("training", {}).get("max_train_steps")
        if configured_steps != expected_steps:
            errors.append("actual training config max_train_steps does not match expected_steps")

    checkpoint = output_directory / f"checkpoint-{expected_steps}"
    if not checkpoint.is_dir():
        errors.append(f"missing final checkpoint: {checkpoint.name}")
        checkpoint_files: list[Path] = []
    else:
        checkpoint_files = [
            path for path in checkpoint.rglob("*") if path.is_file() and path.stat().st_size > 0
        ]
        if not checkpoint_files:
            errors.append(f"final checkpoint has no nonempty files: {checkpoint.name}")

    lora_path = output_directory / lora_filename
    safetensors_details = _validate_safetensors(lora_path, errors)

    training_log_path = output_directory / "training.log"
    if not training_log_path.is_file() or training_log_path.stat().st_size <= 0:
        errors.append("missing or empty training.log")
        training_log = ""
    else:
        training_log = training_log_path.read_text(encoding="utf-8", errors="replace")
        lowered_log = training_log.casefold()
        found_markers = [marker for marker in FATAL_LOG_MARKERS if marker in lowered_log]
        if found_markers:
            errors.append("fatal marker found in training.log: " + ", ".join(found_markers))

    losses = _read_losses(output_directory / "loss_log.csv", errors)
    if environment and not environment.get("gpu"):
        errors.append("environment report does not identify a GPU")

    validation_directory = output_directory / "validation_images"
    validation_images: dict[str, str] = {}
    for class_id in required_class_ids:
        candidates = sorted(validation_directory.glob(f"{class_id}_seed_*.png"))
        valid_candidates = [
            path
            for path in candidates
            if path.is_file() and path.stat().st_size > 0 and _valid_image(path)
        ]
        if not valid_candidates:
            errors.append(f"missing or invalid validation image for class: {class_id}")
        else:
            validation_images[class_id] = str(valid_candidates[0])

    evidence.update(
        {
            "manifest_status": manifest.get("status") if manifest else None,
            "checkpoint": str(checkpoint) if checkpoint.is_dir() else None,
            "checkpoint_file_count": len(checkpoint_files),
            "lora_path": str(lora_path) if lora_path.is_file() else None,
            "safetensors": safetensors_details,
            "loss_observations": len(losses),
            "final_observed_loss": losses[-1] if losses else None,
            "gpu": environment.get("gpu") if environment else None,
            "training_log_bytes": len(training_log.encode("utf-8")),
            "validation_images": validation_images,
        }
    )
    return TrainingRunValidation(
        valid=not errors,
        output_directory=str(output_directory),
        expected_steps=expected_steps,
        lora_filename=lora_filename,
        errors=errors,
        evidence=evidence,
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Validate real Colab training artifacts without loading an ML model."
    )
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--expected-steps", type=int, required=True)
    parser.add_argument("--lora-filename", required=True)
    parser.add_argument(
        "--required-class",
        action="append",
        dest="required_classes",
        help="Expected validation-image class; repeat for multiple classes.",
    )
    parser.add_argument("--report-json", type=Path)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    result = validate_training_run(
        args.output_dir,
        expected_steps=args.expected_steps,
        lora_filename=args.lora_filename,
        required_class_ids=args.required_classes or REQUIRED_CLASS_IDS,
    )
    output = json.dumps(result.to_dict(), indent=2)
    print(output)
    if args.report_json:
        args.report_json.parent.mkdir(parents=True, exist_ok=True)
        args.report_json.write_text(output + "\n", encoding="utf-8")
    return 0 if result.valid else 1


if __name__ == "__main__":
    raise SystemExit(main())
