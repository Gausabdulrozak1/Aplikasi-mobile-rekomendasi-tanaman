from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import math
import zipfile
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath
from typing import Any, Sequence

from PIL import Image, UnidentifiedImageError

MODEL_FILENAME = "multisource_multicrop_lora.safetensors"
MODEL_SHA_FILENAME = "multisource_multicrop_lora.sha256"
REQUIRED_CLASS_IDS = ("padi", "jagung", "cabai", "kacang_tanah")
EXPECTED_EVALUATION_IMAGES = 72
MAX_SAFETENSORS_HEADER_BYTES = 16 * 1024 * 1024
HUMAN_ASSESSMENT_FIELDS = (
    "crop_correct",
    "field_context_quality",
    "visual_realism_score",
    "class_confusion",
    "reviewer_role",
    "reviewer_notes",
)
REQUIRED_ENTRIES = (
    MODEL_FILENAME,
    MODEL_SHA_FILENAME,
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
    "sanity/sanity_manifest.json",
    "smoke_loss_history.csv",
    "smoke_validation.json",
    "training_config.json",
)


@dataclass(frozen=True)
class KaggleExportValidation:
    valid: bool
    artifact_zip: str
    artifact_sha256: str
    validated_at: str
    errors: list[str] = field(default_factory=list)
    evidence: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _expected_sha(value: str, source: str, errors: list[str]) -> str | None:
    candidate = value.strip().split(maxsplit=1)[0].lower() if value.strip() else ""
    if len(candidate) != 64 or any(character not in "0123456789abcdef" for character in candidate):
        errors.append(f"invalid SHA-256 value in {source}")
        return None
    return candidate


def _read_json(
    archive: zipfile.ZipFile,
    name: str,
    errors: list[str],
    *,
    expected_type: type = dict,
) -> Any:
    try:
        value = json.loads(archive.read(name).decode("utf-8"))
    except KeyError:
        errors.append(f"missing JSON entry: {name}")
        return expected_type()
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        errors.append(f"invalid JSON entry {name}: {exc}")
        return expected_type()
    if not isinstance(value, expected_type):
        errors.append(f"JSON entry {name} must contain a {expected_type.__name__}")
        return expected_type()
    return value


def _read_csv(
    archive: zipfile.ZipFile,
    name: str,
    errors: list[str],
) -> tuple[list[dict[str, str]], list[str]]:
    try:
        raw = archive.read(name)
    except KeyError:
        errors.append(f"missing CSV entry: {name}")
        return [], []
    try:
        reader = csv.DictReader(io.StringIO(raw.decode("utf-8-sig")))
        rows = list(reader)
    except (UnicodeDecodeError, csv.Error) as exc:
        errors.append(f"invalid CSV entry {name}: {exc}")
        return [], []
    return rows, list(reader.fieldnames or [])


def _validate_safetensors_bytes(value: bytes, errors: list[str]) -> dict[str, int]:
    details = {"size_bytes": len(value), "tensor_count": 0, "header_bytes": 0, "data_bytes": 0}
    if len(value) <= 8:
        errors.append("LoRA SafeTensors artifact is empty or truncated")
        return details

    header_size = int.from_bytes(value[:8], byteorder="little", signed=False)
    if (
        header_size <= 0
        or header_size > MAX_SAFETENSORS_HEADER_BYTES
        or header_size > len(value) - 8
    ):
        errors.append("LoRA SafeTensors header length is invalid")
        return details

    try:
        header = json.loads(value[8 : 8 + header_size].decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        errors.append(f"LoRA SafeTensors header cannot be opened: {exc}")
        return details
    if not isinstance(header, dict):
        errors.append("LoRA SafeTensors header must be an object")
        return details

    tensor_entries = {key: item for key, item in header.items() if key != "__metadata__"}
    data_bytes = len(value) - 8 - header_size
    nonempty_tensors = 0
    for tensor_name, descriptor in tensor_entries.items():
        if not isinstance(descriptor, dict):
            errors.append(f"invalid SafeTensors descriptor: {tensor_name}")
            continue
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
            errors.append(f"invalid SafeTensors metadata: {tensor_name}")
            continue
        if offsets[1] > offsets[0]:
            nonempty_tensors += 1

    if not tensor_entries:
        errors.append("LoRA SafeTensors artifact contains no tensors")
    elif nonempty_tensors == 0:
        errors.append("LoRA SafeTensors artifact contains no tensor data")

    details.update(
        {
            "tensor_count": len(tensor_entries),
            "header_bytes": header_size,
            "data_bytes": data_bytes,
        }
    )
    return details


def _validate_image(value: bytes, name: str, errors: list[str]) -> dict[str, Any]:
    try:
        with Image.open(io.BytesIO(value)) as image:
            details = {"format": image.format, "width": image.width, "height": image.height}
            image.verify()
    except (OSError, UnidentifiedImageError) as exc:
        errors.append(f"invalid image {name}: {exc}")
        return {}
    if details["width"] <= 0 or details["height"] <= 0:
        errors.append(f"image has invalid dimensions: {name}")
    return details


def _validate_losses(
    archive: zipfile.ZipFile,
    name: str,
    errors: list[str],
) -> list[float]:
    rows, fields = _read_csv(archive, name, errors)
    if "loss" not in fields:
        errors.append(f"loss column is missing from {name}")
        return []
    values: list[float] = []
    for row_number, row in enumerate(rows, start=2):
        try:
            value = float(row.get("loss", ""))
        except (TypeError, ValueError):
            errors.append(f"invalid loss at {name} row {row_number}")
            continue
        if not math.isfinite(value):
            errors.append(f"non-finite loss at {name} row {row_number}")
            continue
        values.append(value)
    if not rows:
        errors.append(f"loss history has no observations: {name}")
    return values


def _validate_export_manifest(
    archive: zipfile.ZipFile,
    manifest: list[dict[str, Any]],
    archive_names: set[str],
    errors: list[str],
) -> None:
    seen: set[str] = set()
    for index, record in enumerate(manifest, start=1):
        if not isinstance(record, dict):
            errors.append(f"export manifest row {index} is not an object")
            continue
        name = record.get("path")
        if not isinstance(name, str) or not name:
            errors.append(f"export manifest row {index} has no path")
            continue
        if name in seen:
            errors.append(f"duplicate export manifest path: {name}")
            continue
        seen.add(name)
        if name not in archive_names:
            errors.append(f"export manifest entry is absent from ZIP: {name}")
            continue
        value = archive.read(name)
        if record.get("size_bytes") != len(value):
            errors.append(f"export manifest size mismatch: {name}")
        if record.get("sha256") != _sha256_bytes(value):
            errors.append(f"export manifest SHA-256 mismatch: {name}")


def _validate_sanity(
    archive: zipfile.ZipFile,
    records: list[dict[str, Any]],
    required_class_ids: Sequence[str],
    errors: list[str],
) -> int:
    if len(records) != len(required_class_ids):
        errors.append(
            f"sanity manifest has {len(records)} rows; expected {len(required_class_ids)}"
        )
    observed_classes: set[str] = set()
    valid_images = 0
    for record in records:
        if not isinstance(record, dict):
            errors.append("sanity manifest contains a non-object row")
            continue
        class_id = record.get("class_id")
        if isinstance(class_id, str):
            observed_classes.add(class_id)
        name = f"sanity/{PurePosixPath(str(record.get('path', ''))).name}"
        try:
            value = archive.read(name)
        except KeyError:
            errors.append(f"sanity image is absent from ZIP: {name}")
            continue
        if record.get("sha256") != _sha256_bytes(value):
            errors.append(f"sanity image SHA-256 mismatch: {name}")
        if _validate_image(value, name, errors):
            valid_images += 1
    if observed_classes != set(required_class_ids):
        errors.append("sanity manifest class set does not match the required classes")
    return valid_images


def _validate_evaluation(
    archive: zipfile.ZipFile,
    manifest: dict[str, Any],
    expected_images: int,
    errors: list[str],
) -> int:
    records = manifest.get("records")
    if not isinstance(records, list):
        errors.append("evaluation manifest records must be a list")
        return 0
    if manifest.get("status") != "complete":
        errors.append("evaluation manifest does not report status=complete")
    if manifest.get("expected_images") != expected_images:
        errors.append("evaluation manifest expected_images does not match the contract")
    if manifest.get("generated_images") != expected_images:
        errors.append("evaluation manifest generated_images does not match the contract")
    if len(records) != expected_images:
        errors.append(f"evaluation manifest has {len(records)} records; expected {expected_images}")

    valid_images = 0
    record_keys: set[tuple[str, str]] = set()
    for record in records:
        if not isinstance(record, dict):
            errors.append("evaluation manifest contains a non-object row")
            continue
        condition_id = record.get("condition_id")
        variant = record.get("variant")
        if not isinstance(condition_id, str) or variant not in {"base", "lora"}:
            errors.append("evaluation record has an invalid condition_id or variant")
            continue
        key = (condition_id, variant)
        if key in record_keys:
            errors.append(f"duplicate evaluation record: {condition_id}/{variant}")
        record_keys.add(key)
        name = f"evaluation/{variant}/{PurePosixPath(str(record.get('image_path', ''))).name}"
        try:
            value = archive.read(name)
        except KeyError:
            errors.append(f"evaluation image is absent from ZIP: {name}")
            continue
        if record.get("image_sha256") != _sha256_bytes(value):
            errors.append(f"evaluation image SHA-256 mismatch: {name}")
        if _validate_image(value, name, errors):
            valid_images += 1

    condition_ids = {condition_id for condition_id, _ in record_keys}
    expected_variants = {(condition_id, variant) for condition_id in condition_ids for variant in ("base", "lora")}
    if record_keys != expected_variants:
        errors.append("evaluation records do not contain one base/LoRA pair per condition")
    if manifest.get("conditions") != len(condition_ids):
        errors.append("evaluation manifest condition count is inconsistent")
    return valid_images


def validate_kaggle_export(
    artifact_zip: Path,
    *,
    sha256_file: Path | None = None,
    expected_sha256: str | None = None,
    expected_evaluation_images: int = EXPECTED_EVALUATION_IMAGES,
    required_class_ids: Sequence[str] = REQUIRED_CLASS_IDS,
) -> KaggleExportValidation:
    artifact_zip = artifact_zip.resolve()
    errors: list[str] = []
    evidence: dict[str, Any] = {}
    validated_at = datetime.now(timezone.utc).isoformat()
    if not artifact_zip.is_file() or artifact_zip.stat().st_size <= 0:
        errors.append(f"artifact ZIP is missing or empty: {artifact_zip}")
        return KaggleExportValidation(
            False, str(artifact_zip), "", validated_at, errors, evidence
        )

    artifact_sha256 = _sha256_file(artifact_zip)
    expected_values: list[tuple[str, str]] = []
    if expected_sha256 is not None:
        expected_values.append((expected_sha256, "--expected-sha256"))
    if sha256_file is not None:
        if not sha256_file.is_file():
            errors.append(f"SHA-256 sidecar is missing: {sha256_file}")
        else:
            expected_values.append((sha256_file.read_text(encoding="utf-8"), str(sha256_file)))
    for raw_value, source in expected_values:
        parsed = _expected_sha(raw_value, source, errors)
        if parsed is not None and parsed != artifact_sha256:
            errors.append(f"artifact ZIP SHA-256 does not match {source}")

    try:
        archive = zipfile.ZipFile(artifact_zip)
    except (OSError, zipfile.BadZipFile) as exc:
        errors.append(f"artifact cannot be opened as ZIP: {exc}")
        return KaggleExportValidation(
            False, str(artifact_zip), artifact_sha256, validated_at, errors, evidence
        )

    with archive:
        infos = archive.infolist()
        file_names = [info.filename for info in infos if not info.is_dir()]
        archive_names = set(file_names)
        if len(file_names) != len(archive_names):
            errors.append("artifact ZIP contains duplicate file names")
        for name in file_names:
            path = PurePosixPath(name)
            if path.is_absolute() or ".." in path.parts or "\\" in name:
                errors.append(f"unsafe ZIP member path: {name}")
        corrupt_member = archive.testzip()
        if corrupt_member is not None:
            errors.append(f"ZIP CRC check failed: {corrupt_member}")
        for required_entry in REQUIRED_ENTRIES:
            if required_entry not in archive_names:
                errors.append(f"required ZIP entry is missing: {required_entry}")

        if MODEL_FILENAME in archive_names:
            model_bytes = archive.read(MODEL_FILENAME)
            model_sha256 = _sha256_bytes(model_bytes)
            safetensors = _validate_safetensors_bytes(model_bytes, errors)
        else:
            model_bytes = b""
            model_sha256 = ""
            safetensors = _validate_safetensors_bytes(model_bytes, errors)

        if MODEL_SHA_FILENAME in archive_names:
            inside_sha = _expected_sha(
                archive.read(MODEL_SHA_FILENAME).decode("utf-8", errors="replace"),
                MODEL_SHA_FILENAME,
                errors,
            )
            if inside_sha is not None and inside_sha != model_sha256:
                errors.append("model SHA-256 sidecar does not match the model bytes")

        state = _read_json(archive, "complete_pipeline_state.json", errors)
        integrity = _read_json(archive, "final_integrity.json", errors)
        smoke = _read_json(archive, "smoke_validation.json", errors)
        main = _read_json(archive, "main_validation.json", errors)
        report = _read_json(archive, "final_training_report.json", errors)
        export_manifest = _read_json(
            archive, "export_manifest.json", errors, expected_type=list
        )
        sanity_manifest = _read_json(
            archive, "sanity/sanity_manifest.json", errors, expected_type=list
        )
        evaluation_manifest = _read_json(
            archive, "evaluation/evaluation_manifest.json", errors
        )

        if state.get("status") != "success":
            errors.append("complete_pipeline_state.json does not report status=success")
        if state.get("current_stage") != "complete_kaggle_pipeline":
            errors.append("complete pipeline state has an unexpected current_stage")
        if state.get("final_lora_sha256") != model_sha256:
            errors.append("complete pipeline state model SHA-256 mismatch")
        if state.get("evaluation_status") != "complete":
            errors.append("complete pipeline state does not report completed evaluation")
        if state.get("human_evaluation_status") != "pending_real_human_review":
            errors.append("complete pipeline state has an unexpected human evaluation status")
        if state.get("automated_metrics_are_proxy") is not True:
            errors.append("complete pipeline state must label automated metrics as proxy")
        if state.get("rule_engine_remains_authoritative") is not True:
            errors.append("complete pipeline state must preserve rule-engine authority")

        if integrity.get("status") != "pass" or integrity.get("missing_entries") != []:
            errors.append("final_integrity.json does not report a clean pass")
        if integrity.get("model_sha256_expected") != model_sha256:
            errors.append("final integrity expected model SHA-256 mismatch")
        if integrity.get("model_sha256_in_zip") != model_sha256:
            errors.append("final integrity ZIP model SHA-256 mismatch")
        if integrity.get("smoke_status") != "pass":
            errors.append("final integrity smoke status is not pass")
        if integrity.get("main_status") != "success":
            errors.append("final integrity main status is not success")
        if integrity.get("sanity_status") != "pass":
            errors.append("final integrity sanity status is not pass")
        if integrity.get("evaluation_status") != "complete":
            errors.append("final integrity evaluation status is not complete")

        smoke_lora = smoke.get("lora_validation", {})
        if not (
            smoke.get("status") == "pass"
            and smoke.get("return_code") == 0
            and smoke.get("actual_step") == 100
            and smoke.get("checkpoint_100_valid") is True
            and isinstance(smoke_lora, dict)
            and smoke_lora.get("valid") is True
        ):
            errors.append("smoke validation contract did not pass")
        canonical_lora = main.get("canonical_lora_validation", {})
        if not (
            main.get("status") == "success"
            and main.get("return_code") == 0
            and main.get("actual_step") == 1600
            and main.get("checkpoint_valid") is True
            and isinstance(canonical_lora, dict)
            and canonical_lora.get("valid") is True
        ):
            errors.append("main validation contract did not pass")
        if main.get("canonical_lora_sha256") != model_sha256:
            errors.append("main validation canonical LoRA SHA-256 mismatch")

        run_ids = {state.get("run_id"), report.get("run_id")}
        if None in run_ids or len(run_ids) != 1:
            errors.append("run_id is inconsistent across final evidence")
        dataset_hashes = {
            state.get("dataset_package_sha256"),
            smoke.get("dataset_package_sha256"),
            main.get("dataset_package_sha256"),
            report.get("dataset_package_sha256"),
        }
        if None in dataset_hashes or len(dataset_hashes) != 1:
            errors.append("dataset package SHA-256 is inconsistent across final evidence")
        if report.get("status") != "training_and_sanity_success":
            errors.append("final training report has an unexpected status")
        if report.get("evaluation_status") != "complete":
            errors.append("final training report does not report completed evaluation")

        _validate_export_manifest(archive, export_manifest, archive_names, errors)
        sanity_images = _validate_sanity(
            archive, sanity_manifest, required_class_ids, errors
        )
        evaluation_images = _validate_evaluation(
            archive, evaluation_manifest, expected_evaluation_images, errors
        )

        evaluation_rows, _ = _read_csv(
            archive, "evaluation/evaluation_manifest.csv", errors
        )
        metric_rows, metric_fields = _read_csv(
            archive, "evaluation/automated_proxy_metrics.csv", errors
        )
        human_rows, human_fields = _read_csv(
            archive, "evaluation/human_evaluation_template.csv", errors
        )
        for name, rows in (
            ("evaluation manifest CSV", evaluation_rows),
            ("automated proxy metrics", metric_rows),
            ("human evaluation template", human_rows),
        ):
            if len(rows) != expected_evaluation_images:
                errors.append(f"{name} has {len(rows)} rows; expected {expected_evaluation_images}")
        if "human_quality_claim" not in metric_fields:
            errors.append("automated proxy metrics are missing human_quality_claim")
        elif any(row.get("human_quality_claim", "").strip() for row in metric_rows):
            errors.append("automated proxy metrics contain a human-quality claim")
        missing_human_fields = [field for field in HUMAN_ASSESSMENT_FIELDS if field not in human_fields]
        if missing_human_fields:
            errors.append("human evaluation template is missing assessment fields")
        blank_human_rows = sum(
            all(not row.get(field, "").strip() for field in HUMAN_ASSESSMENT_FIELDS)
            for row in human_rows
        )
        if blank_human_rows != expected_evaluation_images:
            errors.append("human evaluation template contains pre-filled assessment values")
        if integrity.get("human_template_blank_rows") != blank_human_rows:
            errors.append("final integrity human-template count is inconsistent")

        smoke_losses = _validate_losses(archive, "smoke_loss_history.csv", errors)
        main_losses = _validate_losses(archive, "main_loss_history.csv", errors)
        if smoke.get("loss_count") != len(smoke_losses):
            errors.append("smoke validation loss count is inconsistent")
        if main.get("loss_count") != len(main_losses):
            errors.append("main validation loss count is inconsistent")

        evidence.update(
            {
                "run_id": state.get("run_id"),
                "pipeline_status": state.get("status"),
                "artifact_size_bytes": artifact_zip.stat().st_size,
                "zip_file_count": len(file_names),
                "model_filename": MODEL_FILENAME,
                "model_sha256": model_sha256,
                "safetensors": safetensors,
                "dataset_package_sha256": state.get("dataset_package_sha256"),
                "smoke": {
                    "status": smoke.get("status"),
                    "steps": smoke.get("actual_step"),
                    "elapsed_seconds": smoke.get("elapsed_seconds"),
                    "loss_observations": len(smoke_losses),
                },
                "main": {
                    "status": main.get("status"),
                    "steps": main.get("actual_step"),
                    "elapsed_seconds": main.get("elapsed_seconds"),
                    "loss_observations": len(main_losses),
                },
                "sanity_images_valid": sanity_images,
                "evaluation_images_valid": evaluation_images,
                "evaluation_conditions": evaluation_manifest.get("conditions"),
                "human_template_blank_rows": blank_human_rows,
                "automated_metrics_are_proxy": state.get("automated_metrics_are_proxy"),
                "human_evaluation_status": state.get("human_evaluation_status"),
                "gpu": report.get("gpu"),
                "dataset_counts": report.get("dataset_counts"),
                "export_manifest_records": len(export_manifest),
            }
        )

    return KaggleExportValidation(
        valid=not errors,
        artifact_zip=str(artifact_zip),
        artifact_sha256=artifact_sha256,
        validated_at=validated_at,
        errors=errors,
        evidence=evidence,
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Validate the final Kaggle LoRA export without loading Stable Diffusion."
    )
    parser.add_argument("--artifact-zip", type=Path, required=True)
    parser.add_argument("--sha256-file", type=Path)
    parser.add_argument("--expected-sha256")
    parser.add_argument("--report-json", type=Path)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    result = validate_kaggle_export(
        args.artifact_zip,
        sha256_file=args.sha256_file,
        expected_sha256=args.expected_sha256,
    )
    output = json.dumps(result.to_dict(), indent=2)
    print(output)
    if args.report_json:
        args.report_json.parent.mkdir(parents=True, exist_ok=True)
        args.report_json.write_text(output + "\n", encoding="utf-8")
    return 0 if result.valid else 1


if __name__ == "__main__":
    raise SystemExit(main())
