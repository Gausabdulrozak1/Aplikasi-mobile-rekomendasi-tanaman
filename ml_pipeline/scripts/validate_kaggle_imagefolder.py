from __future__ import annotations

import argparse
import json
import platform
import shutil
import sys
from importlib.metadata import version
from pathlib import Path

from datasets import load_dataset

EXPECTED_SPLITS = {"train": 312, "validation": 77}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Full-decode the Kaggle staging dataset with Hugging Face ImageFolder"
    )
    parser.add_argument("--staging-root", type=Path, required=True)
    parser.add_argument("--cache-root", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    return parser.parse_args()


def clean_cache(cache_root: Path, staging_root: Path) -> None:
    cache_root = cache_root.resolve()
    allowed_parent = staging_root.resolve().parent
    if cache_root == allowed_parent or not cache_root.is_relative_to(allowed_parent):
        raise RuntimeError(f"STOP: unsafe ImageFolder cache path: {cache_root}")
    if cache_root.exists():
        shutil.rmtree(cache_root)
    cache_root.mkdir(parents=True)


def load_split(staging_root: Path, cache_root: Path, split: str):
    data_files = {split: str(staging_root / split / "**")}
    return load_dataset(
        "imagefolder",
        data_files=data_files,
        cache_dir=str(cache_root),
    )[split]


def full_decode(dataset, expected_count: int, split: str) -> int:
    if len(dataset) != expected_count:
        raise RuntimeError(f"STOP: ImageFolder {split} examples {len(dataset)} != {expected_count}")
    decoded = 0
    for index in range(len(dataset)):
        image = dataset[index]["image"]
        image.load()
        image.close()
        decoded += 1
    if decoded != expected_count:
        raise RuntimeError(f"STOP: ImageFolder {split} full decode failed")
    return decoded


def diffusers_equivalent_probe(dataset, expected_count: int, batch_size: int = 4) -> dict:
    decoded = 0
    batches = 0
    for start in range(0, expected_count, batch_size):
        indexes = list(range(start, min(start + batch_size, expected_count)))
        batch = dataset[indexes]
        images = batch["image"]
        texts = batch["text"]
        if len(images) != len(indexes) or len(texts) != len(indexes):
            raise RuntimeError(f"STOP: Diffusers loader batch mismatch at {start}")
        for image, text in zip(images, texts, strict=True):
            if not str(text).strip():
                raise RuntimeError(f"STOP: empty caption in Diffusers loader batch {start}")
            image.load()
            image.close()
            decoded += 1
        batches += 1
    if decoded != expected_count:
        raise RuntimeError(f"STOP: Diffusers loader decoded {decoded} != {expected_count}")
    return {"status": "pass", "decoded": decoded, "batches": batches, "batch_size": batch_size}


def main() -> int:
    args = parse_args()
    staging_root = args.staging_root.resolve()
    cache_root = args.cache_root.resolve()
    report_path = args.report.resolve()
    report_path.parent.mkdir(parents=True, exist_ok=True)
    clean_cache(cache_root, staging_root)
    report: dict[str, object] = {
        "schema_version": 1,
        "status": "running",
        "python_executable": sys.executable,
        "python_version": platform.python_version(),
        "versions": {package: version(package) for package in ("datasets", "pillow", "pyarrow")},
        "staging_root": str(staging_root),
        "cache_root": str(cache_root),
    }
    try:
        train = load_split(staging_root, cache_root, "train")
        report["train_columns"] = list(train.column_names)
        report["train_decoded"] = full_decode(train, EXPECTED_SPLITS["train"], "train")
        report["imagefolder_train_full_decode"] = "pass"

        validation = load_split(staging_root, cache_root, "validation")
        report["validation_columns"] = list(validation.column_names)
        report["validation_decoded"] = full_decode(
            validation, EXPECTED_SPLITS["validation"], "validation"
        )
        report["imagefolder_validation_full_decode"] = "pass"

        probe = diffusers_equivalent_probe(train, EXPECTED_SPLITS["train"])
        report["diffusers_loader_probe"] = "pass"
        report["diffusers_loader_probe_details"] = probe
        report["status"] = "valid"
    except Exception as exc:
        report["status"] = "failed"
        report["error"] = repr(exc)
        report.setdefault("imagefolder_train_full_decode", "fail")
        report.setdefault("imagefolder_validation_full_decode", "fail")
        report.setdefault("diffusers_loader_probe", "fail")
        report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
        raise
    report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print("IMAGEFOLDER_TRAIN_FULL_DECODE = PASS")
    print("IMAGEFOLDER_VALIDATION_FULL_DECODE = PASS")
    print("DIFFUSERS_LOADER_PROBE = PASS")
    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
