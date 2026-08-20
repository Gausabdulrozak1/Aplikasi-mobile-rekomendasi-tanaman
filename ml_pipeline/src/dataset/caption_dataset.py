from __future__ import annotations

from pathlib import Path
from typing import Any

from ml_pipeline.src.common.config import class_lookup, dataset_output_dir
from ml_pipeline.src.dataset.io_utils import write_jsonl
from ml_pipeline.src.dataset.models import MetadataRecord


def build_caption(
    config: dict[str, Any],
    class_id: str,
    provenance: dict[str, object] | None = None,
) -> str:
    caption = config["caption"]
    class_info = class_lookup(config).get(class_id)
    if not class_info:
        raise ValueError(f"Unknown class for caption: {class_id}")

    if "template" in caption and "classes" not in config:
        return str(caption["template"]).format(
            trigger_token=class_info["trigger_token"],
            crop_name=class_info["crop_name_en"],
            class_name=class_id,
        )

    details = provenance or {}
    phrases = [
        f"a realistic agricultural photograph of {class_info['trigger_token']}",
        f"{class_info['crop_name_en']} growing in an agricultural environment",
        str(caption.get("default_lighting", "natural lighting")),
    ]
    source_type = str(details.get("source_type", ""))
    location = str(details.get("location_general", "")).strip()
    if source_type == "local_aikmel" and "aikmel" in location.casefold():
        phrases.append("documented in Aikmel")
    return ", ".join(phrase.strip(" ,") for phrase in phrases if phrase.strip(" ,"))


def create_metadata_for_split(
    config: dict[str, Any],
    split_items: list[dict[str, object]],
) -> list[MetadataRecord]:
    records: list[MetadataRecord] = []
    classes = class_lookup(config)
    for item in split_items:
        path = Path(item["file"])
        class_id = item["class_id"]
        class_info = classes[class_id]
        records.append(
            MetadataRecord(
                file_name=f"{class_id}/{path.name}",
                text=build_caption(config, class_id, item),
                class_id=class_id,
                trigger_token=class_info["trigger_token"],
                source_type=str(item.get("source_type", "")),
                is_local_aikmel=bool(item.get("is_local_aikmel", False)),
                location_general=str(item.get("location_general", "")),
                duplicate_group=str(item.get("duplicate_group", "")),
                original_file_name=str(item.get("original_file_name", "")),
                manual_review_status=str(item.get("manual_review_status", "yes")),
            )
        )
    return records


def write_metadata(
    config: dict[str, Any],
    splits: dict[str, list[dict[str, object]]],
) -> dict[str, str]:
    paths: dict[str, str] = {}
    for split, items in splits.items():
        records = create_metadata_for_split(config, items)
        split_dir = dataset_output_dir(config) / split
        path = write_jsonl(
            split_dir / "metadata.jsonl",
            [record.to_training_dict() for record in records],
        )
        paths[split] = str(path)
    return paths
