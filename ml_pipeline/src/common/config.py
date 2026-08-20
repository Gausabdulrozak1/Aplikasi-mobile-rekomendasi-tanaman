from __future__ import annotations

from copy import deepcopy
from pathlib import Path
from typing import Any

import yaml

ALLOWED_SOURCE_TYPES = {"public", "local_aikmel"}
FINAL_TRIGGER_TOKENS = {
    "padi": "taniadaptif_padi",
    "jagung": "taniadaptif_jagung",
    "cabai": "taniadaptif_cabai",
    "kacang_tanah": "taniadaptif_kacang_tanah",
}


def repo_root() -> Path:
    return Path(__file__).resolve().parents[3]


def resolve_path(value: str | Path, base_dir: Path | None = None) -> Path:
    path = Path(value)
    if path.is_absolute():
        return path
    return (base_dir or repo_root()) / path


def load_config(path: str | Path) -> dict[str, Any]:
    config_path = resolve_path(path)
    with config_path.open("r", encoding="utf-8") as handle:
        config = yaml.safe_load(handle) or {}
    config["_config_path"] = str(config_path)
    config["_repo_root"] = str(repo_root())
    validate_class_config(config)
    return config


def dataset_output_dir(config: dict[str, Any]) -> Path:
    dataset = config["dataset"]
    value = dataset.get("processed_directory") or dataset.get("output_directory")
    if not value:
        raise ValueError("dataset.processed_directory or dataset.output_directory is required")
    return resolve_path(value)


def dataset_reports_dir(config: dict[str, Any]) -> Path:
    dataset = config["dataset"]
    value = dataset.get("reports_directory")
    if value:
        return resolve_path(value)
    return dataset_output_dir(config) / "reports"


def class_definitions(
    config: dict[str, Any],
    *,
    active_only: bool = True,
) -> list[dict[str, Any]]:
    configured = config.get("classes")
    if configured:
        classes = [dict(item) for item in configured]
    else:
        dataset = config.get("dataset", {})
        caption = config.get("caption", {})
        classes = [
            {
                "id": class_id,
                "display_name": class_id.replace("_", " ").title(),
                "trigger_token": caption.get(
                    "trigger_token",
                    f"taniadaptif_{class_id}",
                ),
                "crop_name_en": caption.get(
                    "crop_name",
                    class_id.replace("_", " "),
                ),
                "raw_directory": dataset.get("image_directory", ""),
                "target_minimum_images": dataset.get("target_minimum_images", 1),
                "target_maximum_images": dataset.get(
                    "max_images_per_class",
                    dataset.get("target_maximum_images", 0),
                ),
            }
            for class_id in dataset.get("selected_classes", [])
        ]

    if active_only and config.get("_active_class_ids"):
        active = set(config["_active_class_ids"])
        classes = [item for item in classes if item["id"] in active]
    return classes


def class_lookup(config: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {item["id"]: item for item in class_definitions(config, active_only=False)}


def source_definitions(
    config: dict[str, Any],
    *,
    active_only: bool = True,
) -> list[dict[str, Any]]:
    sources: list[dict[str, Any]] = []
    for class_info in class_definitions(config, active_only=active_only):
        configured_sources = class_info.get("sources")
        if configured_sources:
            for source in configured_sources:
                sources.append(
                    {
                        **dict(source),
                        "class_id": class_info["id"],
                        "display_name": class_info["display_name"],
                        "trigger_token": class_info["trigger_token"],
                    }
                )
            continue

        raw_directory = class_info.get("raw_directory")
        if raw_directory:
            sources.append(
                {
                    "class_id": class_info["id"],
                    "display_name": class_info["display_name"],
                    "trigger_token": class_info["trigger_token"],
                    "type": "public",
                    "directory": raw_directory,
                    "required": True,
                }
            )
    return sources


def dataset_source_manifest_path(config: dict[str, Any]) -> Path | None:
    value = config.get("dataset", {}).get("source_manifest")
    return resolve_path(value) if value else None


def dataset_review_dir(config: dict[str, Any]) -> Path:
    value = config.get("dataset", {}).get("review_directory")
    return resolve_path(value or "artifacts/dataset_review")


def dataset_review_candidates_dir(config: dict[str, Any]) -> Path:
    value = config.get("dataset", {}).get("review_candidates_directory")
    if value:
        return resolve_path(value)
    return dataset_review_dir(config) / "candidates"


def dataset_packages_dir(config: dict[str, Any]) -> Path:
    value = config.get("dataset", {}).get("packages_directory")
    return resolve_path(value or "artifacts/dataset_packages")


def apply_class_filter(
    config: dict[str, Any],
    class_id: str | None = None,
    *,
    all_classes: bool = False,
) -> dict[str, Any]:
    selected = deepcopy(config)
    available = [item["id"] for item in class_definitions(config, active_only=False)]
    if class_id and all_classes:
        raise ValueError("--class and --all-classes cannot be used together")
    if class_id:
        if class_id not in available:
            choices = ", ".join(available)
            raise ValueError(f"Unknown class '{class_id}'. Available classes: {choices}")
        selected["_active_class_ids"] = [class_id]
    else:
        selected["_active_class_ids"] = available
    return selected


def validate_class_config(config: dict[str, Any]) -> None:
    classes = class_definitions(config, active_only=False)
    if not classes:
        raise ValueError("Configuration must define at least one dataset class")

    required = {"id", "display_name", "trigger_token", "crop_name_en"}
    for index, item in enumerate(classes):
        missing = sorted(required - item.keys())
        if missing:
            raise ValueError(f"classes[{index}] is missing required fields: {', '.join(missing)}")

    class_ids = [str(item["id"]) for item in classes]
    trigger_tokens = [str(item["trigger_token"]) for item in classes]
    if len(class_ids) != len(set(class_ids)):
        raise ValueError("All class IDs must be unique")
    if len(trigger_tokens) != len(set(trigger_tokens)):
        raise ValueError("All trigger tokens must be unique")

    for item in classes:
        class_id = str(item["id"])
        expected_trigger = FINAL_TRIGGER_TOKENS.get(class_id)
        if expected_trigger and str(item["trigger_token"]) != expected_trigger:
            raise ValueError(
                f"Class '{class_id}' must use final trigger token '{expected_trigger}'"
            )

        configured_sources = item.get("sources")
        if not configured_sources:
            continue
        seen_types: set[str] = set()
        for source_index, source in enumerate(configured_sources):
            source_type = str(source.get("type", ""))
            if source_type not in ALLOWED_SOURCE_TYPES:
                allowed = ", ".join(sorted(ALLOWED_SOURCE_TYPES))
                raise ValueError(
                    f"Class '{class_id}' source[{source_index}] has unsupported type "
                    f"'{source_type}'. Allowed: {allowed}"
                )
            if source_type in seen_types:
                raise ValueError(
                    f"Class '{class_id}' defines source type '{source_type}' more than once"
                )
            if not source.get("directory"):
                raise ValueError(f"Class '{class_id}' source[{source_index}] must define directory")
            if source_type == "local_aikmel" and class_id != "padi":
                raise ValueError("source_type 'local_aikmel' is only valid for class 'padi'")
            seen_types.add(source_type)

        if "public" not in seen_types:
            raise ValueError(f"Class '{class_id}' must define a public source")

    dataset = config.get("dataset", {})
    train_ratio = float(dataset.get("train_ratio", 0.8))
    validation_ratio = float(dataset.get("validation_ratio", 1 - train_ratio))
    if not 0 < train_ratio < 1 or not 0 < validation_ratio < 1:
        raise ValueError("Train and validation ratios must be between 0 and 1")
    if abs((train_ratio + validation_ratio) - 1.0) > 1e-6:
        raise ValueError("Train and validation ratios must add up to 1.0")


def ensure_directory(path: str | Path) -> Path:
    target = Path(path)
    target.mkdir(parents=True, exist_ok=True)
    return target
