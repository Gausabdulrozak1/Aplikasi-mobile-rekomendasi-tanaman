from __future__ import annotations

import random
import shutil
from pathlib import Path

import pytest
from PIL import Image

CLASS_SPECS = [
    ("padi", "Padi", "taniadaptif_padi", "rice plants"),
    ("jagung", "Jagung", "taniadaptif_jagung", "maize plants"),
    ("cabai", "Cabai", "taniadaptif_cabai", "chili plants"),
    (
        "kacang_tanah",
        "Kacang Tanah",
        "taniadaptif_kacang_tanah",
        "peanut plants",
    ),
]


def create_pattern_image(path: Path, seed: int, size: tuple[int, int] = (128, 128)) -> None:
    rng = random.Random(seed)
    image = Image.new("RGB", size)
    image.putdata(
        [
            (
                rng.randrange(256),
                rng.randrange(256),
                rng.randrange(256),
            )
            for _ in range(size[0] * size[1])
        ]
    )
    image.save(path)


@pytest.fixture
def multicrop_config(tmp_path: Path) -> dict:
    raw_root = tmp_path / "raw"
    classes = []
    for index, (class_id, display_name, trigger, crop_name) in enumerate(
        CLASS_SPECS,
        start=1,
    ):
        public_dir = raw_root / class_id / "public"
        public_dir.mkdir(parents=True)
        sources = [
            {
                "type": "public",
                "directory": str(public_dir),
                "required": True,
            }
        ]
        if class_id == "padi":
            local_dir = raw_root / class_id / "local_aikmel"
            local_dir.mkdir(parents=True)
            sources.append(
                {
                    "type": "local_aikmel",
                    "directory": str(local_dir),
                    "required": False,
                }
            )
            for image_index in range(1, 3):
                create_pattern_image(
                    local_dir / f"padi_local_{image_index}.png",
                    seed=500 + image_index,
                )

        classes.append(
            {
                "id": class_id,
                "display_name": display_name,
                "trigger_token": trigger,
                "crop_name_en": crop_name,
                "sources": sources,
                "target_minimum_images": 4,
                "target_maximum_images": 100,
            }
        )
        for image_index in range(1, 5):
            create_pattern_image(
                public_dir / f"{class_id}_{image_index}.png",
                seed=(index * 100) + image_index,
            )

    shutil.copy2(
        raw_root / "jagung" / "public" / "jagung_1.png",
        raw_root / "padi" / "public" / "exact_from_jagung.png",
    )
    shutil.copy2(
        raw_root / "padi" / "public" / "padi_1.png",
        raw_root / "padi" / "local_aikmel" / "exact_from_public.png",
    )

    near_source = Image.open(raw_root / "cabai" / "public" / "cabai_1.png").convert("RGB")
    near_source.putpixel((0, 0), (255, 255, 255))
    near_source.save(raw_root / "kacang_tanah" / "public" / "near_from_cabai.png")

    create_pattern_image(raw_root / "padi" / "public" / "too_small.png", 999, (16, 16))
    (raw_root / "jagung" / "public" / "broken.jpg").write_text(
        "not an image",
        encoding="utf-8",
    )
    unknown_dir = raw_root / "unknown"
    unknown_dir.mkdir()
    create_pattern_image(unknown_dir / "mystery.png", 2026)

    return {
        "project_name": "test_multicrop",
        "experiment_name": "test_multisource_multicrop",
        "seed": 42,
        "classes": classes,
        "dataset": {
            "source_manifest": str(tmp_path / "dataset_source_manifest.csv"),
            "processed_directory": str(tmp_path / "processed"),
            "reports_directory": str(tmp_path / "reports"),
            "review_directory": str(tmp_path / "dataset_review"),
            "review_candidates_directory": str(tmp_path / "dataset_review" / "candidates"),
            "packages_directory": str(tmp_path / "dataset_packages"),
            "package_manifest_document": str(tmp_path / "DATASET_PACKAGE_MANIFEST.md"),
            "review_sample_per_class": 2,
            "train_ratio": 0.75,
            "validation_ratio": 0.25,
            "minimum_width": 64,
            "minimum_height": 64,
            "duplicate_threshold": 5,
            "allowed_extensions": [".jpg", ".jpeg", ".png", ".webp"],
        },
        "caption": {
            "language": "en",
            "include_trigger_token": True,
            "default_style": "realistic agricultural photograph",
            "default_environment": "agricultural environment",
            "default_lighting": "natural lighting",
        },
    }
