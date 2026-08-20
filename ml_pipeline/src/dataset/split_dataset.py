from __future__ import annotations

import random
import shutil
from pathlib import Path
from typing import Any

from ml_pipeline.src.common.config import class_definitions, dataset_output_dir


def split_dataset(
    config: dict[str, Any],
    curated: list[dict[str, object]],
) -> dict[str, list[dict[str, object]]]:
    unapproved = [
        str(item.get("curated_file_name", item.get("new_file_name", "")))
        for item in curated
        if str(item.get("manual_review_status", "")).strip().casefold() != "yes"
    ]
    if unapproved:
        raise ValueError(
            "Final split accepts only manual_review_status=yes; blocked files: "
            + ", ".join(unapproved[:5])
        )
    dataset = config["dataset"]
    seed = int(config.get("seed", config.get("training", {}).get("seed", 42)))
    train_ratio = float(dataset.get("train_ratio", 0.8))
    output_dir = dataset_output_dir(config)
    train_dir = output_dir / "train"
    validation_dir = output_dir / "validation"
    for directory in (train_dir, validation_dir):
        if directory.exists():
            shutil.rmtree(directory)
    train_dir.mkdir(parents=True, exist_ok=True)
    validation_dir.mkdir(parents=True, exist_ok=True)

    by_class: dict[str, list[dict[str, object]]] = {}
    for item in curated:
        by_class.setdefault(str(item["class_id"]), []).append(item)

    group_items: dict[str, list[dict[str, object]]] = {}
    for item in curated:
        group_items.setdefault(str(item["duplicate_group"]), []).append(item)

    constraints = _split_constraints(config, by_class)
    assignments: dict[str, str] = {}
    for label, group_ids in constraints:
        shuffled = sorted(group_ids)
        random.Random(f"{seed}:{label}").shuffle(shuffled)
        item_count = sum(len(group_items[group_id]) for group_id in group_ids)
        target_train = max(1, min(round(item_count * train_ratio), item_count - 1))
        current_train = sum(
            len(group_items[group_id])
            for group_id in group_ids
            if assignments.get(group_id) == "train"
        )
        for group_id in shuffled:
            if group_id in assignments:
                continue
            group_size = len(group_items[group_id])
            train_distance = abs((current_train + group_size) - target_train)
            validation_distance = abs(current_train - target_train)
            split = "train" if train_distance <= validation_distance else "validation"
            assignments[group_id] = split
            if split == "train":
                current_train += group_size

    for group_id in sorted(group_items):
        assignments.setdefault(
            group_id,
            "train" if random.Random(f"{seed}:{group_id}").random() < train_ratio else "validation",
        )

    _ensure_constraints_have_both_splits(assignments, constraints)

    result: dict[str, list[dict[str, object]]] = {"train": [], "validation": []}
    for class_id, items in sorted(by_class.items()):
        for item in sorted(items, key=lambda row: str(row["new_file_name"])):
            split = assignments[str(item["duplicate_group"])]
            target_dir = (train_dir if split == "train" else validation_dir) / class_id
            target_dir.mkdir(parents=True, exist_ok=True)
            source = Path(str(item["curated_path"]))
            target = target_dir / str(item["new_file_name"])
            shutil.copy2(source, target)
            result[split].append(
                {
                    **item,
                    "file": str(target),
                    "split": split,
                    "class_id": class_id,
                    "seed": seed,
                }
            )

    return result


def _split_constraints(
    config: dict[str, Any],
    by_class: dict[str, list[dict[str, object]]],
) -> list[tuple[str, set[str]]]:
    constraints: list[tuple[str, set[str]]] = []
    seen: set[frozenset[str]] = set()
    for class_info in class_definitions(config):
        class_id = str(class_info["id"])
        items = by_class.get(class_id, [])
        class_groups = {str(item["duplicate_group"]) for item in items}
        if len(items) < 2 or len(class_groups) < 2:
            raise ValueError(
                f"Class '{class_id}' needs at least two duplicate groups to create "
                "train and validation splits without leakage"
            )
        if class_id == "padi":
            source_types = sorted({str(item["source_type"]) for item in items})
            for source_type in source_types:
                source_items = [item for item in items if str(item["source_type"]) == source_type]
                source_groups = {str(item["duplicate_group"]) for item in source_items}
                if len(source_items) >= 2 and len(source_groups) >= 2:
                    _append_constraint(
                        constraints,
                        seen,
                        f"class:{class_id}:source:{source_type}",
                        source_groups,
                    )
        _append_constraint(constraints, seen, f"class:{class_id}", class_groups)
    return constraints


def _append_constraint(
    constraints: list[tuple[str, set[str]]],
    seen: set[frozenset[str]],
    label: str,
    group_ids: set[str],
) -> None:
    key = frozenset(group_ids)
    if key not in seen:
        constraints.append((label, group_ids))
        seen.add(key)


def _ensure_constraints_have_both_splits(
    assignments: dict[str, str],
    constraints: list[tuple[str, set[str]]],
) -> None:
    for label, group_ids in constraints:
        present = {assignments[group_id] for group_id in group_ids}
        if present == {"train", "validation"}:
            continue
        missing = ({"train", "validation"} - present).pop()
        candidates = sorted(group_ids, reverse=True)
        moved = False
        for group_id in candidates:
            original = assignments[group_id]
            assignments[group_id] = missing
            if all(
                {assignments[item] for item in constrained_groups} == {"train", "validation"}
                for _, constrained_groups in constraints
                if group_id in constrained_groups and len(constrained_groups) >= 2
            ):
                moved = True
                break
            assignments[group_id] = original
        if not moved:
            raise ValueError(f"Constraint '{label}' cannot be stratified without duplicate leakage")
