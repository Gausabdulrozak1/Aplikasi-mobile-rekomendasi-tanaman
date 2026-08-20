from __future__ import annotations

import shutil
import subprocess
import sys
import zipfile
from pathlib import Path
from typing import Any

from ml_pipeline.src.common.config import resolve_path


class DatasetSourceError(RuntimeError):
    pass


def resolve_dataset_source(config: dict[str, Any]) -> Path:
    dataset = config["dataset"]
    source_type = dataset.get("source_type", "local_directory")

    if source_type == "local_directory":
        image_directory = resolve_path(dataset["image_directory"])
        if not image_directory.exists():
            raise DatasetSourceError(f"Image directory not found: {image_directory}")
        return image_directory

    if source_type == "local_zip":
        return _extract_local_zip(config)

    if source_type == "huggingface_dataset":
        return _download_huggingface_dataset(config)

    if source_type == "kaggle_dataset":
        return _download_kaggle_dataset(config)

    raise DatasetSourceError(f"Unsupported dataset source_type: {source_type}")


def _extract_local_zip(config: dict[str, Any]) -> Path:
    dataset = config["dataset"]
    archive_path = resolve_path(dataset["archive_path"])
    output_dir = resolve_path(dataset["output_directory"]) / "raw_extracted"
    if not archive_path.exists():
        raise DatasetSourceError(f"ZIP archive not found: {archive_path}")

    if output_dir.exists():
        shutil.rmtree(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(archive_path) as archive:
        archive.extractall(output_dir)
    return output_dir


def _download_huggingface_dataset(config: dict[str, Any]) -> Path:
    dataset = config["dataset"]
    dataset_id = dataset.get("dataset_id")
    if not dataset_id:
        raise DatasetSourceError("dataset.dataset_id is required for Hugging Face datasets")

    output_dir = _download_cache_dir(dataset_id, "huggingface")
    output_dir.mkdir(parents=True, exist_ok=True)
    if any(output_dir.iterdir()):
        return output_dir
    max_total = dataset.get("max_images_total") or dataset.get("max_images_per_class") or 0
    max_total = int(max_total)
    if max_total <= 0:
        raise DatasetSourceError(
            "Remote Hugging Face dataset downloads require dataset.max_images_total "
            "or dataset.max_images_per_class to protect local/Colab resources."
        )
    script = (
        "from datasets import load_dataset\n"
        "from pathlib import Path\n"
        f"ds = load_dataset({dataset_id!r}, streaming=True)\n"
        f"out = Path({str(output_dir)!r})\n"
        f"max_total = int({max_total!r})\n"
        "out.mkdir(parents=True, exist_ok=True)\n"
        "split = next(iter(ds.keys()))\n"
        "saved = 0\n"
        "for idx, item in enumerate(ds[split]):\n"
        "    image = item.get('image')\n"
        "    if image is None:\n"
        "        continue\n"
        "    image.save(out / f'hf_{saved:06d}.png')\n"
        "    saved += 1\n"
        "    if saved >= max_total:\n"
        "        break\n"
    )
    try:
        subprocess.run([sys.executable, "-c", script], check=True)
    except (OSError, subprocess.CalledProcessError) as exc:
        raise DatasetSourceError(
            "Failed to download Hugging Face dataset. Install `datasets` and authenticate if required."
        ) from exc
    return output_dir


def _download_kaggle_dataset(config: dict[str, Any]) -> Path:
    dataset = config["dataset"]
    dataset_id = dataset.get("dataset_id")
    if not dataset_id:
        raise DatasetSourceError("dataset.dataset_id is required for Kaggle datasets")

    output_dir = _download_cache_dir(dataset_id, "kaggle")
    output_dir.mkdir(parents=True, exist_ok=True)
    if any(output_dir.iterdir()):
        return output_dir
    try:
        subprocess.run(
            ["kaggle", "datasets", "download", "-d", dataset_id, "-p", str(output_dir), "--unzip"],
            check=True,
        )
    except (OSError, subprocess.CalledProcessError) as exc:
        raise DatasetSourceError(
            "Failed to download Kaggle dataset. Install Kaggle CLI and provide kaggle.json safely."
        ) from exc
    return output_dir


def _download_cache_dir(dataset_id: str, source: str) -> Path:
    safe_id = dataset_id.replace("/", "__").replace("\\", "__").replace(":", "_").replace(" ", "_")
    return resolve_path("ml_pipeline/data/downloads") / source / safe_id
