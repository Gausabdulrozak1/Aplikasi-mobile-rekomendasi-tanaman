from __future__ import annotations

from dataclasses import replace
from itertools import combinations
from pathlib import Path
from typing import Any

from PIL import Image

from ml_pipeline.src.dataset.models import ImageRecord


def difference_hash(path: Path, hash_size: int = 8) -> str:
    """Return a two-axis difference hash without external numeric dependencies."""
    with Image.open(path) as image:
        grayscale = image.convert("L")
        horizontal = grayscale.resize(
            (hash_size + 1, hash_size),
            Image.Resampling.LANCZOS,
        )
        vertical = grayscale.resize(
            (hash_size, hash_size + 1),
            Image.Resampling.LANCZOS,
        )

    horizontal_pixels = list(horizontal.get_flattened_data())
    vertical_pixels = list(vertical.get_flattened_data())
    horizontal_bits = [
        horizontal_pixels[(row * (hash_size + 1)) + column]
        > horizontal_pixels[(row * (hash_size + 1)) + column + 1]
        for row in range(hash_size)
        for column in range(hash_size)
    ]
    vertical_bits = [
        vertical_pixels[(row * hash_size) + column]
        > vertical_pixels[((row + 1) * hash_size) + column]
        for row in range(hash_size)
        for column in range(hash_size)
    ]
    bits = "".join("1" if value else "0" for value in horizontal_bits + vertical_bits)
    return f"{int(bits, 2):0{len(bits) // 4}x}"


def hamming_distance(left: str, right: str) -> int:
    left_bits = bin(int(left, 16))[2:].zfill(len(left) * 4)
    right_bits = bin(int(right, 16))[2:].zfill(len(right) * 4)
    return sum(a != b for a, b in zip(left_bits, right_bits))


def add_perceptual_hashes(records: list[ImageRecord]) -> list[ImageRecord]:
    hashed: list[ImageRecord] = []
    for record in records:
        perceptual_hash = record.perceptual_hash
        if record.status in {"valid", "duplicate"} and not perceptual_hash:
            try:
                perceptual_hash = difference_hash(Path(record.original_path))
            except OSError:
                perceptual_hash = ""

        hashed.append(replace(record, perceptual_hash=perceptual_hash))
    return hashed


def duplicate_report(
    config: dict[str, Any], records: list[ImageRecord]
) -> dict[str, list[dict[str, object]]]:
    threshold = int(config["dataset"].get("duplicate_threshold", 4))
    exact: list[dict[str, object]] = []
    perceptual: list[dict[str, object]] = []

    by_hash: dict[str, list[ImageRecord]] = {}
    for record in records:
        if record.sha256:
            by_hash.setdefault(record.sha256, []).append(record)
    for digest, duplicates in by_hash.items():
        if len(duplicates) > 1:
            canonical = duplicates[0]
            for duplicate in duplicates[1:]:
                exact.append(
                    {
                        "sha256": digest,
                        "canonical_path": canonical.original_path,
                        "canonical_class_id": canonical.class_id,
                        "canonical_source_type": canonical.source_type,
                        "duplicate_path": duplicate.original_path,
                        "duplicate_class_id": duplicate.class_id,
                        "duplicate_source_type": duplicate.source_type,
                        "same_content_different_extension": (
                            canonical.extension.casefold() != duplicate.extension.casefold()
                        ),
                    }
                )

    valid_records = [
        record for record in records if record.status == "valid" and record.perceptual_hash
    ]
    for left, right in combinations(valid_records, 2):
        distance = hamming_distance(left.perceptual_hash, right.perceptual_hash)
        if distance <= threshold:
            perceptual.append(
                {
                    "left_path": left.original_path,
                    "left_class_id": left.class_id,
                    "left_source_type": left.source_type,
                    "right_path": right.original_path,
                    "right_class_id": right.class_id,
                    "right_source_type": right.source_type,
                    "distance": distance,
                    "threshold": threshold,
                }
            )

    cross_source_padi: list[dict[str, object]] = []
    cross_class: list[dict[str, object]] = []
    for row in exact:
        if (
            row["canonical_class_id"] == "padi"
            and row["duplicate_class_id"] == "padi"
            and row["canonical_source_type"] != row["duplicate_source_type"]
        ):
            cross_source_padi.append({"duplicate_type": "exact", **row})
        if row["canonical_class_id"] != row["duplicate_class_id"]:
            cross_class.append({"duplicate_type": "exact", **row})

    for row in perceptual:
        if (
            row["left_class_id"] == "padi"
            and row["right_class_id"] == "padi"
            and row["left_source_type"] != row["right_source_type"]
        ):
            cross_source_padi.append({"duplicate_type": "near", **row})
        if row["left_class_id"] != row["right_class_id"]:
            cross_class.append({"duplicate_type": "near", **row})

    return {
        "exact": exact,
        "near": perceptual,
        "cross_source_padi": cross_source_padi,
        "cross_class": cross_class,
    }


def assign_duplicate_groups(
    records: list[ImageRecord],
    report: dict[str, list[dict[str, object]]],
) -> list[ImageRecord]:
    parents = {record.original_path: record.original_path for record in records}
    exact_paths: set[str] = set()
    near_paths: set[str] = set()

    def find(value: str) -> str:
        while parents[value] != value:
            parents[value] = parents[parents[value]]
            value = parents[value]
        return value

    def union(left: str, right: str) -> None:
        left_root = find(left)
        right_root = find(right)
        if left_root != right_root:
            parents[max(left_root, right_root)] = min(left_root, right_root)

    for item in report.get("exact", []):
        canonical_path = str(item["canonical_path"])
        duplicate_path = str(item["duplicate_path"])
        exact_paths.update({canonical_path, duplicate_path})
        union(canonical_path, duplicate_path)
    for item in report.get("near", []):
        left_path = str(item["left_path"])
        right_path = str(item["right_path"])
        near_paths.update({left_path, right_path})
        union(left_path, right_path)

    components: dict[str, list[ImageRecord]] = {}
    for record in records:
        components.setdefault(find(record.original_path), []).append(record)

    grouped: list[ImageRecord] = []
    for record in records:
        component = components[find(record.original_path)]
        if len(component) > 1:
            group_key = min(item.sha256 for item in component if item.sha256)
            duplicate_group = f"duplicate-{group_key[:16]}"
        else:
            duplicate_group = f"image-{record.sha256[:16]}"
        warnings = []
        if record.original_path in exact_paths:
            warnings.append("exact_duplicate_group")
        if record.original_path in near_paths:
            warnings.append("near_duplicate_review")
        grouped.append(
            replace(
                record,
                duplicate_group=duplicate_group,
                duplicate_warning=";".join(warnings),
            )
        )
    return grouped
