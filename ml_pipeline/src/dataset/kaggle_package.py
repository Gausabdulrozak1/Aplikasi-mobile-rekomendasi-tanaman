from __future__ import annotations

import csv
import hashlib
import json
import os
import shutil
import zipfile
from collections import Counter, defaultdict
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path, PurePosixPath
from typing import Callable, Iterable

from PIL import Image

EXPECTED_OLD_PACKAGE_SHA256 = "f6aa060658cf95e48996f10f0ffde200938d340dd15e6b60adace5bb5cecfb33"
EXPECTED_REVIEW = {"rows": 475, "accepted": 390, "rejected": 85}
EXPECTED_SPLITS = {"train": 312, "validation": 77}
EXPECTED_CLASSES = {
    "padi": 95,
    "jagung": 100,
    "cabai": 97,
    "kacang_tanah": 97,
}
EXPECTED_TRIGGERS = {
    "padi": "taniadaptif_padi",
    "jagung": "taniadaptif_jagung",
    "cabai": "taniadaptif_cabai",
    "kacang_tanah": "taniadaptif_kacang_tanah",
}
ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}
RESERVED_METADATA_RENAMES = {"original_file_name": "source_original_name"}
PACKAGE_FILENAME = "dataset_multicrop_v1_kaggle_fixed.zip"
CHECKSUM_FILENAME = "dataset_multicrop_v1_kaggle_fixed.sha256"
REPORT_JSON_FILENAME = "KAGGLE_DATASET_PACKAGE_REPORT.json"
REPORT_MARKDOWN_FILENAME = "KAGGLE_DATASET_PACKAGE_REPORT.md"


class KaggleDatasetBuildError(RuntimeError):
    pass


@dataclass(frozen=True)
class PhysicalImage:
    split: str
    absolute_source_path: str
    relative_source_path: str
    split_relative_path: str
    basename: str
    extension: str
    byte_size: int
    sha256: str
    class_id: str
    source_type: str
    provenance_identifier: str
    source_identifier: str
    original_file_name: str

    def as_csv_row(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True)
class MetadataResolution:
    split: str
    row_index: int
    requested_file_name: str
    normalized_file_name: str
    status: str
    method: str
    candidate_paths: tuple[str, ...]
    image: PhysicalImage | None

    def as_report_row(self) -> dict[str, object]:
        return {
            "split": self.split,
            "row_index": self.row_index,
            "requested_file_name": self.requested_file_name,
            "normalized_file_name": self.normalized_file_name,
            "status": self.status,
            "method": self.method,
            "candidate_count": len(self.candidate_paths),
            "candidate_paths": "|".join(self.candidate_paths),
        }


def utc_now() -> str:
    return datetime.now(UTC).isoformat()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def read_jsonl(path: Path) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for line_number, line in enumerate(Path(path).read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        value = json.loads(line)
        if not isinstance(value, dict):
            raise KaggleDatasetBuildError(f"{path}:{line_number} is not a JSON object")
        rows.append(value)
    return rows


def write_jsonl(path: Path, rows: Iterable[dict[str, object]]) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    content = "".join(
        json.dumps(row, ensure_ascii=False, sort_keys=False, separators=(",", ":")) + "\n"
        for row in rows
    )
    path.write_text(content, encoding="utf-8", newline="\n")


def read_csv_rows(path: Path) -> list[dict[str, str]]:
    with Path(path).open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def write_csv_rows(path: Path, fieldnames: list[str], rows: Iterable[dict[str, object]]) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def normalize_relative_path(value: object) -> str:
    text = str(value or "").strip().replace("\\", "/")
    while text.startswith("./"):
        text = text[2:]
    path = PurePosixPath(text)
    if not text or path.is_absolute() or ".." in path.parts:
        return ""
    return path.as_posix()


def _repo_relative(path: Path, repository_root: Path) -> str:
    resolved = path.resolve()
    root = repository_root.resolve()
    try:
        return resolved.relative_to(root).as_posix()
    except ValueError:
        return resolved.as_posix()


def _split_manifest_lookup(repository_root: Path) -> dict[tuple[str, str], dict[str, str]]:
    manifest_path = repository_root / "ml_pipeline/data/reports/split_manifest.csv"
    rows = read_csv_rows(manifest_path)
    lookup: dict[tuple[str, str], dict[str, str]] = {}
    for row in rows:
        key = (str(row.get("split", "")), normalize_relative_path(row.get("file_name")))
        if key in lookup:
            raise KaggleDatasetBuildError(f"Duplicate split manifest key: {key}")
        lookup[key] = row
    return lookup


def build_physical_image_index(repository_root: Path) -> list[PhysicalImage]:
    repository_root = Path(repository_root).resolve()
    processed_root = repository_root / "ml_pipeline/data/processed"
    manifest = _split_manifest_lookup(repository_root)
    records: list[PhysicalImage] = []
    for split in EXPECTED_SPLITS:
        split_root = processed_root / split
        for image_path in sorted(split_root.rglob("*")):
            if not image_path.is_file() or image_path.suffix.casefold() not in ALLOWED_EXTENSIONS:
                continue
            relative = image_path.relative_to(split_root).as_posix()
            row = manifest.get((split, relative), {})
            records.append(
                PhysicalImage(
                    split=split,
                    absolute_source_path=str(image_path.resolve()),
                    relative_source_path=_repo_relative(image_path, repository_root),
                    split_relative_path=relative,
                    basename=image_path.name,
                    extension=image_path.suffix.casefold(),
                    byte_size=image_path.stat().st_size,
                    sha256=sha256_file(image_path),
                    class_id=str(row.get("class_id", "")),
                    source_type=str(row.get("source_type", "")),
                    provenance_identifier=str(
                        row.get("source_identifier") or row.get("duplicate_group") or ""
                    ),
                    source_identifier=str(row.get("source_identifier", "")),
                    original_file_name=str(row.get("original_file_name", "")),
                )
            )
    return records


def write_physical_image_index(repository_root: Path, records: list[PhysicalImage]) -> Path:
    path = Path(repository_root) / "ml_pipeline/data/reports/kaggle_physical_image_index.csv"
    fields = list(PhysicalImage.__dataclass_fields__)
    write_csv_rows(path, fields, (record.as_csv_row() for record in records))
    return path


def resolve_metadata_row(
    split: str,
    row_index: int,
    row: dict[str, object],
    records: list[PhysicalImage],
) -> MetadataResolution:
    requested = str(row.get("file_name", ""))
    normalized = normalize_relative_path(requested)
    exact_lookup = {record.split_relative_path: record for record in records}
    if normalized and normalized in exact_lookup:
        image = exact_lookup[normalized]
        return MetadataResolution(
            split,
            row_index,
            requested,
            normalized,
            "resolved",
            "exact_relative_path",
            (image.split_relative_path,),
            image,
        )

    path_fields = (
        "absolute_source_path",
        "relative_source_path",
        "processed_path",
        "curated_path",
        "source_path",
        "original_path",
    )
    absolute_lookup = {
        os.path.normcase(os.path.abspath(record.absolute_source_path)): record for record in records
    }
    relative_lookup = {
        normalize_relative_path(record.relative_source_path): record for record in records
    }
    provenance_matches: dict[str, PhysicalImage] = {}
    for field in path_fields:
        field_value = str(row.get(field, "")).strip()
        if not field_value:
            continue
        absolute_key = os.path.normcase(os.path.abspath(field_value))
        image = absolute_lookup.get(absolute_key)
        if image is None:
            image = relative_lookup.get(normalize_relative_path(field_value))
        if image is not None:
            provenance_matches[image.split_relative_path] = image
    if len(provenance_matches) == 1:
        image = next(iter(provenance_matches.values()))
        return MetadataResolution(
            split,
            row_index,
            requested,
            normalized,
            "resolved",
            "provenance_path",
            (image.split_relative_path,),
            image,
        )
    if len(provenance_matches) > 1:
        candidates = tuple(sorted(provenance_matches))
        return MetadataResolution(
            split,
            row_index,
            requested,
            normalized,
            "ambiguous",
            "provenance_path",
            candidates,
            None,
        )

    basename = PurePosixPath(normalized).name.casefold() if normalized else ""
    basename_matches = [record for record in records if record.basename.casefold() == basename]
    if len(basename_matches) == 1:
        image = basename_matches[0]
        return MetadataResolution(
            split,
            row_index,
            requested,
            normalized,
            "resolved",
            "unique_basename",
            (image.split_relative_path,),
            image,
        )
    if len(basename_matches) > 1:
        return MetadataResolution(
            split,
            row_index,
            requested,
            normalized,
            "ambiguous",
            "basename",
            tuple(sorted(record.split_relative_path for record in basename_matches)),
            None,
        )
    return MetadataResolution(
        split,
        row_index,
        requested,
        normalized,
        "unresolved",
        "none",
        (),
        None,
    )


def _review_audit(repository_root: Path) -> dict[str, object]:
    review_path = repository_root / "artifacts/dataset_review/manual_review_template.csv"
    rows = read_csv_rows(review_path)
    decisions = Counter(str(row.get("accepted", "")).strip().casefold() for row in rows)
    report = {
        "path": str(review_path),
        "rows": len(rows),
        "accepted": decisions.get("yes", 0),
        "rejected": decisions.get("no", 0),
        "other": len(rows) - decisions.get("yes", 0) - decisions.get("no", 0),
    }
    expected = {**EXPECTED_REVIEW, "other": 0}
    observed = {key: report[key] for key in expected}
    if observed != expected:
        raise KaggleDatasetBuildError(
            f"STOP: review counts changed: expected={expected}, observed={observed}"
        )
    return report


def audit_source_truth(repository_root: Path) -> dict[str, object]:
    repository_root = Path(repository_root).resolve()
    processed_root = repository_root / "ml_pipeline/data/processed"
    split_manifest_path = repository_root / "ml_pipeline/data/reports/split_manifest.csv"
    validation_path = repository_root / "artifacts/dataset_packages/final_package_validation.json"
    old_package = repository_root / "artifacts/dataset_packages/dataset_multicrop_v1.zip"
    old_checksum = repository_root / "artifacts/dataset_packages/dataset_multicrop_v1.sha256"

    validation = json.loads(validation_path.read_text(encoding="utf-8"))
    if validation.get("training_allowed") is not True:
        raise KaggleDatasetBuildError("STOP: source-of-truth says training_allowed is not true")
    old_sha = sha256_file(old_package)
    recorded_old_sha = old_checksum.read_text(encoding="utf-8").strip().split()[0].casefold()
    if old_sha != EXPECTED_OLD_PACKAGE_SHA256 or recorded_old_sha != old_sha:
        raise KaggleDatasetBuildError(
            f"STOP: old package audit SHA mismatch: actual={old_sha}, recorded={recorded_old_sha}"
        )

    review = _review_audit(repository_root)
    manifest_rows = read_csv_rows(split_manifest_path)
    metadata_rows: dict[str, list[dict[str, object]]] = {}
    metadata_names: dict[str, set[str]] = {}
    duplicate_splits: dict[str, set[str]] = defaultdict(set)
    class_counts: Counter[str] = Counter()
    split_counts: dict[str, int] = {}
    for split, expected_count in EXPECTED_SPLITS.items():
        metadata_path = processed_root / split / "metadata.jsonl"
        rows = read_jsonl(metadata_path)
        metadata_rows[split] = rows
        split_counts[split] = len(rows)
        if len(rows) != expected_count:
            raise KaggleDatasetBuildError(
                f"STOP: {split} metadata count {len(rows)} != {expected_count}"
            )
        names = [normalize_relative_path(row.get("file_name")) for row in rows]
        if "" in names or len(names) != len(set(names)):
            raise KaggleDatasetBuildError(f"STOP: invalid or duplicate metadata paths in {split}")
        metadata_names[split] = set(names)
        for row in rows:
            class_id = str(row.get("class_id", ""))
            class_counts[class_id] += 1
            duplicate_splits[str(row.get("duplicate_group", ""))].add(split)
            text = str(row.get("text", "")).strip()
            trigger = EXPECTED_TRIGGERS.get(class_id)
            if not text or not trigger or trigger not in text:
                raise KaggleDatasetBuildError(
                    f"STOP: caption/trigger invalid: {split}/{row.get('file_name')}"
                )
            wrong = [
                value
                for other_class, value in EXPECTED_TRIGGERS.items()
                if other_class != class_id and value in text
            ]
            if wrong:
                raise KaggleDatasetBuildError(
                    f"STOP: cross trigger in {split}/{row.get('file_name')}: {wrong}"
                )

    manifest_names: dict[str, set[str]] = {split: set() for split in EXPECTED_SPLITS}
    for row in manifest_rows:
        split = str(row.get("split", ""))
        if split in manifest_names:
            manifest_names[split].add(normalize_relative_path(row.get("file_name")))
    if manifest_names != metadata_names:
        raise KaggleDatasetBuildError("STOP: split manifest and metadata file sets differ")
    if split_counts != EXPECTED_SPLITS:
        raise KaggleDatasetBuildError(
            f"STOP: split counts changed: expected={EXPECTED_SPLITS}, observed={split_counts}"
        )
    if dict(class_counts) != EXPECTED_CLASSES:
        raise KaggleDatasetBuildError(
            f"STOP: class counts changed: expected={EXPECTED_CLASSES}, observed={dict(class_counts)}"
        )
    leaked = sorted(
        group for group, splits in duplicate_splits.items() if group and len(splits) > 1
    )
    if leaked:
        raise KaggleDatasetBuildError(f"STOP: duplicate leakage detected: {leaked[:10]}")

    physical_records = build_physical_image_index(repository_root)
    physical_counts = Counter(record.split for record in physical_records)
    if dict(physical_counts) != EXPECTED_SPLITS:
        raise KaggleDatasetBuildError(
            f"STOP: physical counts changed: expected={EXPECTED_SPLITS}, "
            f"observed={dict(physical_counts)}"
        )

    return {
        "audited_at": utc_now(),
        "training_allowed": True,
        "review": review,
        "split_counts": split_counts,
        "total": sum(split_counts.values()),
        "class_counts": dict(class_counts),
        "duplicate_leakage": len(leaked),
        "trigger_crossing": 0,
        "old_package_path": str(old_package),
        "old_package_sha256": old_sha,
        "metadata_paths": {
            split: str(processed_root / split / "metadata.jsonl") for split in EXPECTED_SPLITS
        },
        "split_manifest_path": str(split_manifest_path),
        "physical_image_count": len(physical_records),
    }


def make_imagefolder_metadata_row(
    row: dict[str, object], target_file_name: str
) -> tuple[dict[str, object], dict[str, str]]:
    output: dict[str, object] = {}
    renamed: dict[str, str] = {}
    for key, value in row.items():
        if key == "file_name":
            output[key] = target_file_name
            continue
        if key.endswith("_file_name"):
            safe_key = RESERVED_METADATA_RENAMES.get(key)
            if not safe_key:
                raise KaggleDatasetBuildError(
                    f"STOP: unsupported ImageFolder-reserved metadata column: {key}"
                )
            if safe_key in row or safe_key in output:
                raise KaggleDatasetBuildError(
                    f"STOP: metadata rename collision: {key} -> {safe_key}"
                )
            output[safe_key] = value
            renamed[key] = safe_key
            continue
        output[key] = value
    if not str(output.get("file_name", "")).strip() or not str(output.get("text", "")).strip():
        raise KaggleDatasetBuildError("STOP: staging metadata requires file_name and text")
    return output, renamed


def ensure_unique_target_name(target_name: str, used_names: set[str]) -> None:
    if target_name in used_names:
        raise KaggleDatasetBuildError(f"STOP: duplicate target filename: {target_name}")
    if Path(target_name).name != target_name or " " in target_name:
        raise KaggleDatasetBuildError(f"STOP: unsafe target filename: {target_name}")
    used_names.add(target_name)


def copy_image_byte_exact(
    source: Path,
    target: Path,
    expected_sha256: str,
    copy_file: Callable[[Path, Path], object] = shutil.copyfile,
) -> str:
    copy_file(Path(source), Path(target))
    target_sha = sha256_file(target)
    if target_sha != expected_sha256:
        raise KaggleDatasetBuildError(f"STOP: source-target SHA mismatch: {source} -> {target}")
    return target_sha


def validate_image_decode(path: Path) -> None:
    with Image.open(path) as image:
        image.verify()
    with Image.open(path) as image:
        image.load()


def _ensure_safe_staging_path(repository_root: Path, staging_root: Path) -> None:
    allowed_root = (repository_root / "artifacts/dataset_build").resolve()
    resolved = staging_root.resolve()
    if resolved == allowed_root or not resolved.is_relative_to(allowed_root):
        raise KaggleDatasetBuildError(f"STOP: unsafe staging path: {resolved}")


def build_kaggle_staging(
    repository_root: Path,
    staging_root: Path | None = None,
    *,
    copy_file: Callable[[Path, Path], object] = shutil.copyfile,
    target_name_factory: Callable[[str, int, PhysicalImage], str] | None = None,
) -> dict[str, object]:
    repository_root = Path(repository_root).resolve()
    staging_root = (
        Path(staging_root).resolve()
        if staging_root
        else repository_root / "artifacts/dataset_build/kaggle_fixed_v1"
    )
    _ensure_safe_staging_path(repository_root, staging_root)
    audit = audit_source_truth(repository_root)
    records = build_physical_image_index(repository_root)
    index_path = write_physical_image_index(repository_root, records)
    by_split = {
        split: [record for record in records if record.split == split] for split in EXPECTED_SPLITS
    }

    metadata_by_split = {
        split: read_jsonl(repository_root / f"ml_pipeline/data/processed/{split}/metadata.jsonl")
        for split in EXPECTED_SPLITS
    }
    resolutions: list[MetadataResolution] = []
    for split, rows in metadata_by_split.items():
        for row_index, row in enumerate(rows):
            resolutions.append(resolve_metadata_row(split, row_index, row, by_split[split]))
    unresolved = [result for result in resolutions if result.status == "unresolved"]
    ambiguous = [result for result in resolutions if result.status == "ambiguous"]
    resolution_report_path = (
        repository_root / "ml_pipeline/data/reports/kaggle_metadata_resolution.csv"
    )
    write_csv_rows(
        resolution_report_path,
        [
            "split",
            "row_index",
            "requested_file_name",
            "normalized_file_name",
            "status",
            "method",
            "candidate_count",
            "candidate_paths",
        ],
        (result.as_report_row() for result in resolutions),
    )
    if unresolved or ambiguous:
        raise KaggleDatasetBuildError(
            f"STOP: unresolved metadata-image mapping = {len(unresolved)}; "
            f"ambiguous = {len(ambiguous)}"
        )

    if staging_root.exists():
        shutil.rmtree(staging_root)
    (staging_root / "manifests").mkdir(parents=True)
    shutil.copy2(index_path, staging_root / "manifests/kaggle_physical_image_index.csv")
    shutil.copy2(
        resolution_report_path,
        staging_root / "manifests/kaggle_metadata_resolution.csv",
    )
    (staging_root / "manifests/source_truth_audit.json").write_text(
        json.dumps(audit, indent=2, ensure_ascii=False), encoding="utf-8"
    )

    mapping_rows: list[dict[str, object]] = []
    renamed_columns: Counter[str] = Counter()
    pil_results: dict[str, dict[str, object]] = {}
    target_names: set[str] = set()
    resolution_lookup = {(item.split, item.row_index): item for item in resolutions}
    for split, rows in metadata_by_split.items():
        split_root = staging_root / split
        split_root.mkdir(parents=True)
        output_metadata: list[dict[str, object]] = []
        write_jsonl(staging_root / f"manifests/original_metadata_{split}.jsonl", rows)
        decode_failures: list[dict[str, str]] = []
        for row_index, row in enumerate(rows):
            resolution = resolution_lookup[(split, row_index)]
            if resolution.image is None:
                raise KaggleDatasetBuildError("STOP: internal resolution invariant failed")
            source = Path(resolution.image.absolute_source_path)
            if target_name_factory:
                target_name = target_name_factory(split, row_index, resolution.image)
            else:
                target_name = (
                    f"{split}_{row_index:04d}_{resolution.image.sha256[:12]}"
                    f"{resolution.image.extension}"
                )
            ensure_unique_target_name(target_name, target_names)
            target = split_root / target_name
            target_sha = copy_image_byte_exact(source, target, resolution.image.sha256, copy_file)
            try:
                validate_image_decode(target)
            except Exception as exc:  # noqa: BLE001
                decode_failures.append({"file_name": target_name, "error": repr(exc)})

            safe_row, renamed = make_imagefolder_metadata_row(row, target_name)
            renamed_columns.update(
                f"{source_key}->{target_key}" for source_key, target_key in renamed.items()
            )
            output_metadata.append(safe_row)
            mapping_rows.append(
                {
                    "split": split,
                    "row_index": row_index,
                    "source_metadata_file_name": row.get("file_name", ""),
                    "source_original_file_name": row.get("original_file_name", ""),
                    "target_file_name": target_name,
                    "match_method": resolution.method,
                    "absolute_source_path": str(source),
                    "relative_source_path": resolution.image.relative_source_path,
                    "source_sha256": resolution.image.sha256,
                    "target_sha256": target_sha,
                    "byte_size": target.stat().st_size,
                    "class_id": row.get("class_id", ""),
                    "source_type": row.get("source_type", ""),
                    "trigger_token": row.get("trigger_token", ""),
                    "provenance_identifier": resolution.image.provenance_identifier,
                }
            )
        write_jsonl(split_root / "metadata.jsonl", output_metadata)
        actual_files = [
            path
            for path in split_root.iterdir()
            if path.is_file() and path.suffix.casefold() in ALLOWED_EXTENSIONS
        ]
        metadata_names = {str(row["file_name"]) for row in output_metadata}
        physical_names = {path.name for path in actual_files}
        if len(output_metadata) != EXPECTED_SPLITS[split] or metadata_names != physical_names:
            raise KaggleDatasetBuildError(f"STOP: staging physical/metadata mismatch in {split}")
        if decode_failures:
            raise KaggleDatasetBuildError(
                f"STOP: PIL {split} decode failures = {len(decode_failures)}"
            )
        pil_results[split] = {
            "status": "pass",
            "metadata_rows": len(output_metadata),
            "physical_images": len(actual_files),
            "missing": 0,
            "decode_failures": 0,
        }

    mapping_path = staging_root / "manifests/kaggle_file_mapping.csv"
    write_csv_rows(
        mapping_path,
        [
            "split",
            "row_index",
            "source_metadata_file_name",
            "source_original_file_name",
            "target_file_name",
            "match_method",
            "absolute_source_path",
            "relative_source_path",
            "source_sha256",
            "target_sha256",
            "byte_size",
            "class_id",
            "source_type",
            "trigger_token",
            "provenance_identifier",
        ],
        mapping_rows,
    )
    build_report = {
        "schema_version": 1,
        "built_at": utc_now(),
        "status": "staging_valid",
        "staging_root": str(staging_root),
        "source_truth": audit,
        "train": EXPECTED_SPLITS["train"],
        "validation": EXPECTED_SPLITS["validation"],
        "total": sum(EXPECTED_SPLITS.values()),
        "class_counts": EXPECTED_CLASSES,
        "unresolved": len(unresolved),
        "ambiguous": len(ambiguous),
        "match_methods": dict(Counter(item.method for item in resolutions)),
        "images_changed": 0,
        "human_decisions_changed": 0,
        "split_changed": 0,
        "caption_changed": 0,
        "metadata_file_name_changed": len(mapping_rows),
        "reserved_provenance_columns_renamed": dict(renamed_columns),
        "pil_validation": pil_results,
        "physical_index": str(index_path),
        "resolution_report": str(resolution_report_path),
        "mapping_manifest": str(mapping_path),
    }
    (staging_root / "manifests/staging_build_report.json").write_text(
        json.dumps(build_report, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    dataset_card = """# TaniAdaptif Multicrop LoRA Dataset - Kaggle Fixed v1

This package contains the final manually reviewed TaniAdaptif research dataset:
312 training images and 77 validation images across padi, jagung, cabai, and
kacang tanah. Image bytes, captions, class labels, triggers, split assignments,
human decisions, and provenance values are unchanged.

The training metadata renames `original_file_name` to `source_original_name`.
Hugging Face folder builders reserve both `file_name` and `*_file_name` columns
as physical media references. Keeping the old column name caused ImageFolder to
attempt to open provenance names such as `003_lahan_cabai.jpg`. The exact
original metadata is retained under `manifests/original_metadata_*.jsonl`.

Stable Diffusion is used only to generate recommendation visualizations. The
TaniAdaptif rule-based engine remains authoritative for crop recommendations.
"""
    (staging_root / "DATASET_CARD.md").write_text(dataset_card, encoding="utf-8")
    return build_report


def _deterministic_zip(source_root: Path, destination: Path) -> None:
    source_root = Path(source_root)
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = destination.with_suffix(destination.suffix + ".tmp")
    if temporary.exists():
        temporary.unlink()
    allowed_top_level = {"train", "validation", "manifests", "DATASET_CARD.md"}
    files = sorted(path for path in source_root.rglob("*") if path.is_file())
    for path in files:
        relative = path.relative_to(source_root).as_posix()
        if PurePosixPath(relative).parts[0] not in allowed_top_level:
            raise KaggleDatasetBuildError(f"STOP: unexpected staging content: {relative}")
    with zipfile.ZipFile(
        temporary, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9
    ) as archive:
        for path in files:
            relative = path.relative_to(source_root).as_posix()
            info = zipfile.ZipInfo(relative, date_time=(1980, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o100644 << 16
            archive.writestr(info, path.read_bytes(), compress_type=zipfile.ZIP_DEFLATED)
    with zipfile.ZipFile(temporary) as archive:
        corrupt = archive.testzip()
        names = set(archive.namelist())
        if corrupt:
            raise KaggleDatasetBuildError(f"STOP: Kaggle ZIP corrupt member: {corrupt}")
        for required in ("train/metadata.jsonl", "validation/metadata.jsonl", "DATASET_CARD.md"):
            if required not in names:
                raise KaggleDatasetBuildError(f"STOP: Kaggle ZIP missing {required}")
    os.replace(temporary, destination)


def finalize_kaggle_package(
    repository_root: Path,
    imagefolder_validation_report: Path,
    staging_root: Path | None = None,
) -> dict[str, object]:
    repository_root = Path(repository_root).resolve()
    staging_root = (
        Path(staging_root).resolve()
        if staging_root
        else repository_root / "artifacts/dataset_build/kaggle_fixed_v1"
    )
    _ensure_safe_staging_path(repository_root, staging_root)
    build_report_path = staging_root / "manifests/staging_build_report.json"
    if not build_report_path.is_file():
        raise KaggleDatasetBuildError("STOP: staging build report is missing")
    build_report = json.loads(build_report_path.read_text(encoding="utf-8"))
    loader_report = json.loads(Path(imagefolder_validation_report).read_text(encoding="utf-8"))
    required_loader_gates = {
        "imagefolder_train_full_decode": "pass",
        "imagefolder_validation_full_decode": "pass",
        "diffusers_loader_probe": "pass",
    }
    observed = {key: loader_report.get(key) for key in required_loader_gates}
    if observed != required_loader_gates:
        raise KaggleDatasetBuildError(
            f"STOP: ImageFolder validation gates failed: expected={required_loader_gates}, "
            f"observed={observed}"
        )
    if loader_report.get("train_decoded") != 312 or loader_report.get("validation_decoded") != 77:
        raise KaggleDatasetBuildError("STOP: ImageFolder decoded counts are incomplete")
    shutil.copy2(
        imagefolder_validation_report,
        staging_root / "manifests/imagefolder_validation_report.json",
    )

    package_dir = repository_root / "artifacts/dataset_packages"
    package_path = package_dir / PACKAGE_FILENAME
    checksum_path = package_dir / CHECKSUM_FILENAME
    report_json_path = package_dir / REPORT_JSON_FILENAME
    report_markdown_path = package_dir / REPORT_MARKDOWN_FILENAME
    old_package_path = package_dir / "dataset_multicrop_v1.zip"
    old_sha_before = sha256_file(old_package_path)
    _deterministic_zip(staging_root, package_path)
    new_sha = sha256_file(package_path)
    checksum_path.write_text(f"{new_sha}  {PACKAGE_FILENAME}\n", encoding="ascii")
    old_sha_after = sha256_file(old_package_path)
    if old_sha_before != EXPECTED_OLD_PACKAGE_SHA256 or old_sha_after != old_sha_before:
        raise KaggleDatasetBuildError("STOP: old audit package changed during Kaggle build")

    report = {
        "schema_version": 1,
        "created_at": utc_now(),
        "status": "valid",
        "old_package_path": str(old_package_path),
        "old_package_sha256": old_sha_after,
        "new_package_path": str(package_path),
        "new_package_sha256": new_sha,
        "new_package_size_bytes": package_path.stat().st_size,
        "checksum_path": str(checksum_path),
        "train": 312,
        "validation": 77,
        "total": 389,
        "class_counts": EXPECTED_CLASSES,
        "images_changed": 0,
        "human_decisions_changed": 0,
        "split_changed": 0,
        "caption_changed": 0,
        "metadata_file_name_changed": 389,
        "metadata_schema_adjustment": {
            "original_file_name": "source_original_name",
            "rows": 389,
            "reason": "Hugging Face ImageFolder reserves *_file_name as media paths",
        },
        "unresolved": build_report["unresolved"],
        "ambiguous": build_report["ambiguous"],
        "pil_validation": build_report["pil_validation"],
        "imagefolder_train_full_decode": loader_report["imagefolder_train_full_decode"],
        "imagefolder_validation_full_decode": loader_report["imagefolder_validation_full_decode"],
        "imagefolder_train_decoded": loader_report["train_decoded"],
        "imagefolder_validation_decoded": loader_report["validation_decoded"],
        "diffusers_loader_probe": loader_report["diffusers_loader_probe"],
        "loader_validation_report": str(imagefolder_validation_report),
        "staging_build_report": str(build_report_path),
    }
    report_json_path.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    report_markdown = f"""# Kaggle Dataset Package Report

## Package Relationship

- Original audit package: `{report["old_package_path"]}`
- Original SHA-256: `{report["old_package_sha256"]}`
- Corrected Kaggle package: `{report["new_package_path"]}`
- Corrected SHA-256: `{report["new_package_sha256"]}`

The original package was not overwritten. The corrected package preserves all
389 image bytes, human review decisions, captions, classes, triggers, splits,
and provenance values. It flattens images inside each split and changes the 389
training `file_name` values deterministically.

`original_file_name` is preserved as `source_original_name` in training
metadata and retained verbatim in `manifests/original_metadata_*.jsonl` because
Hugging Face reserves every `*_file_name` column as a physical media path.

## Gates

- Train / validation / total: 312 / 77 / 389
- Unresolved: {report["unresolved"]}
- Ambiguous: {report["ambiguous"]}
- PIL train: {report["pil_validation"]["train"]["status"]}
- PIL validation: {report["pil_validation"]["validation"]["status"]}
- ImageFolder train full decode: {report["imagefolder_train_full_decode"]} (312/312)
- ImageFolder validation full decode: {report["imagefolder_validation_full_decode"]} (77/77)
- Diffusers-equivalent loader probe: {report["diffusers_loader_probe"]}
- Images changed: 0
- Human decisions changed: 0
- Split changed: 0
- Caption changed: 0
- Metadata `file_name` changed: 389
"""
    report_markdown_path.write_text(report_markdown, encoding="utf-8")
    return report
