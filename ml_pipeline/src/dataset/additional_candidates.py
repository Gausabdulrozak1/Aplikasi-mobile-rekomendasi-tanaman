from __future__ import annotations

import argparse
import binascii
import csv
import io
import json
import math
import os
import re
import shutil
import struct
import time
import zipfile
import zlib
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, replace
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Iterable, Sequence
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

import yaml
from PIL import Image, ImageOps, UnidentifiedImageError

from ml_pipeline.src.common.config import load_config, repo_root, resolve_path
from ml_pipeline.src.dataset.curate_dataset import CURATION_MAPPING_FIELDS
from ml_pipeline.src.dataset.dataset_review import HUMAN_REVIEW_FIELDS, REVIEW_FIELDS
from ml_pipeline.src.dataset.detect_duplicates import difference_hash, hamming_distance
from ml_pipeline.src.dataset.io_utils import sha256_file
from ml_pipeline.src.dataset.provenance import PROVENANCE_FIELDS
from ml_pipeline.src.dataset.semantic_screening import FIELDS as SEMANTIC_FIELDS
from ml_pipeline.src.dataset.semantic_screening import screen_image_proxy

ACCESS_USER_AGENT = "TaniAdaptif-Dataset-Pipeline/1.0"
SUPPORTED_ARCHIVE_COMPRESSION = {zipfile.ZIP_STORED, zipfile.ZIP_DEFLATED}
IMAGE_SUFFIXES = {".jpg", ".jpeg", ".png", ".webp"}
ADDITIONAL_CLASSES = ("jagung", "cabai", "kacang_tanah")
MAX_DOWNLOAD_ROUNDS = 3

SOURCE_REPORT_FIELDS = [
    "review_batch",
    "source_id",
    "status",
    "class_id",
    "dataset_name",
    "authors",
    "organization",
    "source_url",
    "doi",
    "license",
    "license_url",
    "access_date",
    "archive_name",
    "archive_size",
    "archive_sha256",
    "search_round",
    "planned_download_pool",
    "downloaded_files",
    "technical_valid",
    "technical_rejected",
    "exact_duplicates_removed",
    "near_duplicates_removed",
    "semantic_proxy_pass",
    "semantic_proxy_review",
    "staged_files",
    "rejection_reason",
    "notes",
]

ADDITIONAL_SCREENING_PREFIX_FIELDS = [
    "review_batch",
    "source_id",
    "source_name",
    "source_url",
    "doi",
    "license",
    "archive_member",
    "original_file_name",
    "download_round",
    "download_status",
    "technical_status",
    "filter_status",
    "filter_reason",
    "near_duplicate_match",
    "near_duplicate_distance",
]
ADDITIONAL_SCREENING_FIELDS = list(
    dict.fromkeys(ADDITIONAL_SCREENING_PREFIX_FIELDS + SEMANTIC_FIELDS)
)

REJECTED_SOURCES = [
    {
        "source_id": "mendeley_groundnut_leaf_22p2vcbxfk_v3",
        "status": "rejected",
        "class_id": "kacang_tanah",
        "dataset_name": "Dataset of groundnut plant leaf images for classification and detection",
        "authors": "Aishwarya Manvikar; Padmanabha Reddy",
        "organization": "Vijayanagara Sri Krishnadevaraya University Bellary",
        "source_url": "https://data.mendeley.com/datasets/22p2vcbxfk/3",
        "doi": "10.17632/22p2vcbxfk.3",
        "license": "CC BY 4.0",
        "license_url": "https://creativecommons.org/licenses/by/4.0/",
        "access_date": "2026-08-13",
        "archive_name": "Groundnut_Leaf_dataset.zip",
        "archive_size": 117033315,
        "search_round": 1,
        "rejection_reason": "low_context_leaf_crops_and_augmented_files",
        "notes": (
            "Visual samples are 256x256 leaf-focused crops; many filenames indicate augmented "
            "derivatives. This does not meet the growing-plant/context criteria."
        ),
    },
    {
        "source_id": "mendeley_pepper_tracking_z2fp5kbgbh_v1",
        "status": "rejected",
        "class_id": "cabai",
        "dataset_name": "Tracking Plant Growth Using Image Sequence Analysis - Datasets",
        "authors": "Yiftah Szoke; Guy Shani",
        "organization": "Ben-Gurion University of the Negev",
        "source_url": "https://data.mendeley.com/datasets/z2fp5kbgbh/1",
        "doi": "10.17632/z2fp5kbgbh.1",
        "license": "CC BY 4.0",
        "license_url": "https://creativecommons.org/licenses/by/4.0/",
        "access_date": "2026-08-13",
        "archive_name": "Pepper image sequence",
        "archive_size": "",
        "search_round": 1,
        "rejection_reason": "small_temporal_sequence_with_near_duplicate_risk",
        "notes": (
            "Only 24 hourly views of the same pepper setup were available; using them as a "
            "primary source would add excessive temporal near duplicates."
        ),
    },
]


@dataclass(frozen=True)
class SourceSpec:
    source_id: str
    class_id: str
    target_candidates: int
    minimum_candidates: int
    download_pool_size: int
    dataset_name: str
    authors: str
    organization: str
    source_url: str
    doi: str
    license: str
    license_url: str
    access_date: str
    archive_name: str
    archive_size: int
    archive_sha256: str
    review_rotation_degrees: int
    archive_download_url: str
    transport_url: str
    member_groups: tuple[tuple[str, str], ...]


@dataclass(frozen=True)
class SelectedMember:
    source_id: str
    class_id: str
    group: str
    info: zipfile.ZipInfo


class HttpRangeReader(io.RawIOBase):
    """Small seekable reader used to inspect a remote ZIP central directory."""

    def __init__(self, url: str, expected_size: int, block_size: int = 1024 * 1024):
        self.url = url
        self.size = _remote_size(url)
        if self.size != expected_size:
            raise ValueError(
                f"Remote archive size changed for {url}: {self.size} != {expected_size}"
            )
        self.block_size = block_size
        self.position = 0
        self.cache_start = 0
        self.cache = b""

    def readable(self) -> bool:
        return True

    def seekable(self) -> bool:
        return True

    def tell(self) -> int:
        return self.position

    def seek(self, offset: int, whence: int = io.SEEK_SET) -> int:
        if whence == io.SEEK_SET:
            position = offset
        elif whence == io.SEEK_CUR:
            position = self.position + offset
        elif whence == io.SEEK_END:
            position = self.size + offset
        else:
            raise ValueError(f"Unsupported seek mode: {whence}")
        self.position = max(0, min(position, self.size))
        return self.position

    def read(self, size: int = -1) -> bytes:
        if size is None or size < 0:
            size = self.size - self.position
        if size <= 0 or self.position >= self.size:
            return b""
        if not (
            self.cache_start <= self.position
            and self.position + size <= self.cache_start + len(self.cache)
        ):
            self.cache_start = self.position
            end = min(self.size - 1, self.position + max(size, self.block_size) - 1)
            self.cache = _fetch_range(self.url, self.cache_start, end)
        offset = self.position - self.cache_start
        result = self.cache[offset : offset + size]
        self.position += len(result)
        return result


def _http_open(request: Request, timeout: int = 90):
    last_error: Exception | None = None
    for attempt in range(3):
        try:
            return urlopen(request, timeout=timeout)
        except (HTTPError, URLError, TimeoutError) as exc:
            last_error = exc
            if attempt < 2:
                time.sleep(1.5 * (attempt + 1))
    assert last_error is not None
    raise last_error


def _remote_size(url: str) -> int:
    request = Request(url, method="HEAD", headers={"User-Agent": ACCESS_USER_AGENT})
    with _http_open(request, timeout=30) as response:
        value = response.headers.get("Content-Length")
    if not value:
        raise ValueError(f"Remote archive does not expose Content-Length: {url}")
    return int(value)


def _fetch_range(url: str, start: int, end: int) -> bytes:
    request = Request(
        url,
        headers={
            "Range": f"bytes={start}-{end}",
            "User-Agent": ACCESS_USER_AGENT,
        },
    )
    with _http_open(request) as response:
        data = response.read()
        status = getattr(response, "status", 0)
        content_range = response.headers.get("Content-Range", "")
    expected = end - start + 1
    if status != 206 or not content_range.startswith(f"bytes {start}-"):
        raise ValueError(f"Server ignored byte range {start}-{end} for {url}")
    if len(data) != expected:
        raise ValueError(
            f"Incomplete byte range {start}-{end} for {url}: {len(data)} != {expected}"
        )
    return data


def _load_sources(path: Path) -> tuple[dict[str, Any], list[SourceSpec]]:
    with path.open(encoding="utf-8") as handle:
        payload = yaml.safe_load(handle) or {}
    access_date = str(payload.get("access_date", "")).strip()
    sources: list[SourceSpec] = []
    for row in payload.get("sources", []):
        source = SourceSpec(
            source_id=str(row["id"]),
            class_id=str(row["class_id"]),
            target_candidates=int(row["target_candidates"]),
            minimum_candidates=int(row["minimum_candidates"]),
            download_pool_size=int(row["download_pool_size"]),
            dataset_name=str(row["dataset_name"]),
            authors=str(row["authors"]),
            organization=str(row["organization"]),
            source_url=str(row["source_url"]),
            doi=str(row["doi"]),
            license=str(row["license"]),
            license_url=str(row["license_url"]),
            access_date=access_date,
            archive_name=str(row["archive_name"]),
            archive_size=int(row["archive_size"]),
            archive_sha256=str(row["archive_sha256"]),
            review_rotation_degrees=int(row.get("review_rotation_degrees", 0)),
            archive_download_url=str(row["archive_download_url"]),
            transport_url=str(row["transport_url"]),
            member_groups=tuple(
                (str(group["name"]), str(group["pattern"]))
                for group in row.get("member_groups", [])
            ),
        )
        if source.class_id not in ADDITIONAL_CLASSES:
            raise ValueError(f"Additional source targets unsupported class: {source.class_id}")
        if source.license != "CC BY 4.0" or not source.doi:
            raise ValueError(f"Source license/DOI gate failed: {source.source_id}")
        sources.append(source)
    if {source.class_id for source in sources} != set(ADDITIONAL_CLASSES):
        raise ValueError("Additional source config must cover jagung, cabai, and kacang_tanah")
    return payload, sources


def _natural_key(value: str) -> tuple[object, ...]:
    return tuple(
        int(part) if part.isdigit() else part.casefold() for part in re.split(r"([0-9]+)", value)
    )


def _evenly_spaced(items: Sequence[zipfile.ZipInfo], count: int) -> list[zipfile.ZipInfo]:
    if count >= len(items):
        return list(items)
    indexes = [
        min(len(items) - 1, math.floor((index + 0.5) * len(items) / count))
        for index in range(count)
    ]
    return [items[index] for index in dict.fromkeys(indexes)]


def _source_members(source: SourceSpec) -> list[SelectedMember]:
    reader = HttpRangeReader(source.transport_url, source.archive_size)
    grouped: dict[str, list[zipfile.ZipInfo]] = {name: [] for name, _ in source.member_groups}
    compiled = [(name, re.compile(pattern)) for name, pattern in source.member_groups]
    with zipfile.ZipFile(reader) as archive:
        for info in archive.infolist():
            normalized = info.filename.replace("\\", "/")
            if info.is_dir() or Path(normalized).suffix.casefold() not in IMAGE_SUFFIXES:
                continue
            matches = [name for name, pattern in compiled if pattern.fullmatch(normalized)]
            if len(matches) > 1:
                raise ValueError(f"Archive member matches multiple groups: {normalized}")
            if matches:
                if info.flag_bits & 1:
                    raise ValueError(f"Encrypted ZIP member is not supported: {normalized}")
                if info.compress_type not in SUPPORTED_ARCHIVE_COMPRESSION:
                    raise ValueError(
                        f"Unsupported ZIP compression {info.compress_type}: {normalized}"
                    )
                grouped[matches[0]].append(info)

    requested = min(
        sum(len(items) for items in grouped.values()),
        source.download_pool_size * MAX_DOWNLOAD_ROUNDS,
    )
    group_names = [name for name, _ in source.member_groups]
    base, remainder = divmod(requested, len(group_names))
    selected_by_group: dict[str, list[zipfile.ZipInfo]] = {}
    for index, name in enumerate(group_names):
        items = sorted(grouped[name], key=lambda info: _natural_key(info.filename))
        quota = base + (1 if index < remainder else 0)
        selected_by_group[name] = _evenly_spaced(items, min(quota, len(items)))

    result: list[SelectedMember] = []
    # Interleave modulo slices so every download round spans the full archive,
    # rather than taking one contiguous time or plot interval first.
    for round_index in range(MAX_DOWNLOAD_ROUNDS):
        round_groups = {
            name: selected_by_group[name][round_index::MAX_DOWNLOAD_ROUNDS] for name in group_names
        }
        for offset in range(max((len(items) for items in round_groups.values()), default=0)):
            for name in group_names:
                if offset < len(round_groups[name]):
                    result.append(
                        SelectedMember(
                            source.source_id,
                            source.class_id,
                            name,
                            round_groups[name][offset],
                        )
                    )
    if len(result) < source.minimum_candidates:
        raise ValueError(f"Source {source.source_id} has only {len(result)} matching image members")
    return result


def _extract_member(source: SourceSpec, selected: SelectedMember, target: Path) -> Path:
    info = selected.info
    margin = 64 * 1024
    start = info.header_offset
    end = min(source.archive_size - 1, start + info.compress_size + margin)
    payload = _fetch_range(source.transport_url, start, end)
    if len(payload) < 30:
        raise ValueError(f"Truncated ZIP local header: {info.filename}")
    signature, _, flags, compression, _, _, _, _, _, name_length, extra_length = struct.unpack(
        "<IHHHHHIIIHH", payload[:30]
    )
    if signature != 0x04034B50:
        raise ValueError(f"Invalid ZIP local header: {info.filename}")
    if flags & 1:
        raise ValueError(f"Encrypted ZIP member is not supported: {info.filename}")
    data_offset = 30 + name_length + extra_length
    compressed = payload[data_offset : data_offset + info.compress_size]
    if len(compressed) != info.compress_size:
        raise ValueError(f"Truncated ZIP member data: {info.filename}")
    if compression == zipfile.ZIP_STORED:
        content = compressed
    elif compression == zipfile.ZIP_DEFLATED:
        content = zlib.decompress(compressed, -zlib.MAX_WBITS)
    else:
        raise ValueError(f"Unsupported ZIP compression {compression}: {info.filename}")
    if len(content) != info.file_size:
        raise ValueError(f"ZIP member size mismatch: {info.filename}")
    if (binascii.crc32(content) & 0xFFFFFFFF) != info.CRC:
        raise ValueError(f"ZIP member CRC mismatch: {info.filename}")
    target.parent.mkdir(parents=True, exist_ok=True)
    temporary = target.with_suffix(target.suffix + ".part")
    temporary.write_bytes(content)
    os.replace(temporary, target)
    return target


def _download_members(
    source: SourceSpec,
    members: Sequence[SelectedMember],
    work_root: Path,
    workers: int,
) -> dict[str, tuple[Path | None, str]]:
    results: dict[str, tuple[Path | None, str]] = {}

    def task(selected: SelectedMember) -> tuple[str, Path | None, str]:
        original_name = Path(selected.info.filename.replace("\\", "/")).name
        target = work_root / source.class_id / source.source_id / selected.group / original_name
        try:
            return selected.info.filename, _extract_member(source, selected, target), ""
        except (OSError, ValueError, zlib.error) as exc:
            return selected.info.filename, None, f"{exc.__class__.__name__}: {exc}"

    with ThreadPoolExecutor(max_workers=max(1, workers)) as executor:
        futures = {executor.submit(task, member): member for member in members}
        for future in as_completed(futures):
            member_name, path, error = future.result()
            results[member_name] = (path, error)
    return results


def _inspect_image(path: Path, minimum_width: int, minimum_height: int) -> dict[str, object]:
    try:
        with Image.open(path) as opened:
            image_format = (opened.format or "").upper()
            width, height = opened.size
            color_mode = opened.mode
            opened.verify()
        with Image.open(path) as opened:
            ImageOps.exif_transpose(opened).load()
    except (OSError, UnidentifiedImageError) as exc:
        return {
            "valid": False,
            "reason": f"unreadable_image:{exc.__class__.__name__}",
            "width": 0,
            "height": 0,
            "format": "",
            "color_mode": "",
        }
    reason = ""
    if image_format not in {"JPEG", "PNG", "WEBP"}:
        reason = "format_not_allowed"
    elif width < minimum_width or height < minimum_height:
        reason = "resolution_too_small"
    elif color_mode not in {"RGB", "RGBA", "L", "P"}:
        reason = "unsupported_color_mode"
    return {
        "valid": not reason,
        "reason": reason,
        "width": width,
        "height": height,
        "format": image_format,
        "color_mode": color_mode,
    }


def _read_csv(path: Path) -> tuple[list[str], list[dict[str, str]]]:
    if not path.exists():
        return [], []
    with path.open(newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle)
        return list(reader.fieldnames or []), [dict(row) for row in reader]


def _reference_hashes(root: Path) -> dict[str, object]:
    reports = root / "ml_pipeline" / "data" / "reports"
    mapping_path = reports / "curation_mapping.csv"
    inventory_path = reports / "inventory_all_classes.csv"
    _, inventory = _read_csv(inventory_path)
    _, mapping = _read_csv(mapping_path)
    exact: dict[str, str] = {}
    perceptual: list[tuple[str, str]] = []
    seen_pairs: set[tuple[str, str]] = set()

    def add(rows: Iterable[dict[str, str]], scope: str) -> None:
        for row in rows:
            sha = str(row.get("sha256", "")).strip()
            phash = str(row.get("perceptual_hash", "")).strip()
            label = f"{scope}:{row.get('original_file_name') or row.get('curated_file_name')}"
            if sha:
                exact.setdefault(sha, label)
            pair = (sha, phash)
            if phash and pair not in seen_pairs:
                seen_pairs.add(pair)
                perceptual.append((phash, label))

    add(inventory, "raw_inventory")
    add(mapping, "reviewed_candidates")

    processed_root = root / "ml_pipeline" / "data" / "processed"
    processed_count = 0
    for path in sorted(processed_root.rglob("*")) if processed_root.exists() else []:
        if not path.is_file() or path.suffix.casefold() not in IMAGE_SUFFIXES:
            continue
        processed_count += 1
        sha = sha256_file(path)
        phash = difference_hash(path)
        label = f"processed:{path.relative_to(processed_root).as_posix()}"
        exact.setdefault(sha, label)
        if (sha, phash) not in seen_pairs:
            seen_pairs.add((sha, phash))
            perceptual.append((phash, label))
    return {
        "exact": exact,
        "perceptual": perceptual,
        "scope_counts": {
            "raw_inventory": len(inventory),
            "reviewed_candidates": len(mapping),
            "processed": processed_count,
        },
    }


def _safe_reset(path: Path, expected: Path) -> None:
    resolved = path.resolve()
    if resolved != expected.resolve():
        raise ValueError(f"Refusing to reset unexpected path: {resolved}")
    if path.exists():
        shutil.rmtree(path)
    path.mkdir(parents=True, exist_ok=True)


def _candidate_image_hashes(
    candidates_root: Path, names: Iterable[tuple[str, str]]
) -> dict[str, str]:
    result: dict[str, str] = {}
    for class_id, name in names:
        path = candidates_root / class_id / name
        if not path.is_file():
            raise ValueError(f"Existing reviewed candidate image is missing: {path}")
        result[name] = sha256_file(path)
    return result


def _atomic_write_csv(path: Path, rows: list[dict[str, object]], fields: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    with temporary.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)
    os.replace(temporary, path)


def _atomic_write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    os.replace(temporary, path)


def _atomic_write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(content, encoding="utf-8")
    os.replace(temporary, path)


def _backup(path: Path, backup_root: Path, label: str, timestamp: str) -> str:
    if not path.exists():
        return ""
    backup_root.mkdir(parents=True, exist_ok=True)
    target = backup_root / f"{path.stem}_{timestamp}_{label}{path.suffix}"
    shutil.copy2(path, target)
    return str(target)


def _repair_existing_review_orientations(
    root: Path,
    sources: list[SourceSpec],
    batch: str,
    mapping_path: Path,
    review_path: Path,
) -> int:
    rotations = {
        source.doi: source.review_rotation_degrees
        for source in sources
        if source.review_rotation_degrees
    }
    if not rotations:
        return 0
    _, mapping = _read_csv(mapping_path)
    _, review = _read_csv(review_path)
    semantic_path = root / "ml_pipeline" / "data" / "reports" / "automated_semantic_review.csv"
    additional_path = (
        root / "ml_pipeline" / "data" / "reports" / "additional_semantic_screening.csv"
    )
    _, semantic = _read_csv(semantic_path)
    _, additional = _read_csv(additional_path)
    review_by_name = {str(row.get("curated_file_name", "")): row for row in review}
    semantic_by_name = {str(row.get("curated_file_name", "")): row for row in semantic}
    additional_by_name = {
        str(row.get("curated_file_name", "")): row
        for row in additional
        if row.get("filter_status") == "staged"
    }
    pending: list[tuple[Path, Path, dict[str, str], int, int]] = []
    marker_prefix = "review_rotation_degrees="
    for row in mapping:
        row_batch = str(row.get("review_batch", "") or "original_350")
        identifier = str(row.get("source_identifier", ""))
        notes = str(row.get("notes", ""))
        if row_batch != batch or identifier not in rotations or marker_prefix in notes:
            continue
        target = Path(str(row.get("curated_path", "")))
        if not target.is_file():
            raise ValueError(f"Cannot normalize missing review image: {target}")
        temporary = target.with_suffix(".orientation.tmp.jpg")
        with Image.open(target) as opened:
            normalized = (
                ImageOps.exif_transpose(opened)
                .convert("RGB")
                .rotate(rotations[identifier], expand=True)
            )
            width, height = normalized.size
            normalized.save(temporary, format="JPEG", quality=95)
        with Image.open(temporary) as check:
            check.verify()
        pending.append((target, temporary, row, width, height))

    if not pending:
        return 0
    timestamp = datetime.now(UTC).strftime("%Y%m%d_%H%M%SZ")
    backup_root = root / "artifacts" / "dataset_review" / "backups"
    for path in (mapping_path, review_path, semantic_path, additional_path):
        _backup(path, backup_root, f"before_{batch}_orientation", timestamp)

    for target, temporary, mapping_row, width, height in pending:
        os.replace(temporary, target)
        name = str(mapping_row["curated_file_name"])
        marker = f"{marker_prefix}{rotations[str(mapping_row['source_identifier'])]}"
        mapping_row["width"] = width
        mapping_row["height"] = height
        mapping_row["file_size"] = target.stat().st_size
        mapping_row["notes"] = "; ".join(
            value for value in (str(mapping_row.get("notes", "")).strip(), marker) if value
        )
        review_row = review_by_name[name]
        review_row["width"] = width
        review_row["height"] = height
        proxy = screen_image_proxy(target)
        semantic_by_name[name].update(proxy)
        if name in additional_by_name:
            additional_by_name[name].update(proxy)

    _atomic_write_csv(mapping_path, mapping, CURATION_MAPPING_FIELDS)
    _atomic_write_csv(review_path, review, REVIEW_FIELDS)
    _atomic_write_csv(semantic_path, semantic, SEMANTIC_FIELDS)
    _atomic_write_csv(additional_path, additional, ADDITIONAL_SCREENING_FIELDS)
    return len(pending)


def _progress_counts(rows: list[dict[str, object]]) -> dict[str, object]:
    def empty() -> dict[str, int]:
        return {
            "total": 0,
            "reviewed": 0,
            "accepted_yes": 0,
            "accepted_no": 0,
            "accepted_unsure": 0,
            "pending": 0,
        }

    totals = empty()
    per_class: dict[str, dict[str, int]] = {
        class_id: empty() for class_id in ("padi", *ADDITIONAL_CLASSES)
    }
    per_source: dict[str, dict[str, int]] = {"public": empty(), "local_aikmel": empty()}
    per_batch: dict[str, dict[str, int]] = {}

    def add(target: dict[str, int], value: str) -> None:
        target["total"] += 1
        if value in {"yes", "no", "unsure"}:
            target["reviewed"] += 1
            target[f"accepted_{value}"] += 1
        else:
            target["pending"] += 1

    for row in rows:
        value = str(row.get("accepted", "")).strip().casefold()
        class_id = str(row.get("class_id", ""))
        source_type = str(row.get("source_type", ""))
        batch = str(row.get("review_batch", "")).strip() or "original_350"
        per_class.setdefault(class_id, empty())
        per_source.setdefault(source_type, empty())
        per_batch.setdefault(batch, empty())
        for target in (totals, per_class[class_id], per_source[source_type], per_batch[batch]):
            add(target, value)
    return {
        "total_candidates": totals["total"],
        "reviewed": totals["reviewed"],
        "accepted_yes": totals["accepted_yes"],
        "accepted_no": totals["accepted_no"],
        "accepted_unsure": totals["accepted_unsure"],
        "pending": totals["pending"],
        "counts_per_class": per_class,
        "counts_per_source": per_source,
        "counts_per_batch": per_batch,
    }


def _next_curated_names(mapping: list[dict[str, str]], candidates: list[dict[str, object]]) -> None:
    maximum: dict[str, int] = Counter()
    for row in mapping:
        class_id = str(row.get("class_id", ""))
        match = re.fullmatch(
            rf"{re.escape(class_id)}_([0-9]{{4}})\.jpg", str(row.get("curated_file_name", ""))
        )
        if match:
            maximum[class_id] = max(maximum[class_id], int(match.group(1)))
    for candidate in candidates:
        class_id = str(candidate["class_id"])
        maximum[class_id] += 1
        candidate["curated_file_name"] = f"{class_id}_{maximum[class_id]:04d}.jpg"


def _mapping_row(
    candidate: dict[str, object], source: SourceSpec, review_path: Path, batch: str
) -> dict[str, object]:
    name = str(candidate["curated_file_name"])
    return {
        "curated_file_name": name,
        "new_file_name": name,
        "review_batch": batch,
        "curated_path": str(review_path),
        "original_file_name": candidate["original_file_name"],
        "original_path": str(candidate["staged_path"]),
        "class_id": source.class_id,
        "display_name": {"jagung": "Jagung", "cabai": "Cabai", "kacang_tanah": "Kacang Tanah"}[
            source.class_id
        ],
        "trigger_token": f"taniadaptif_{source.class_id}",
        "source_type": "public",
        "is_local_aikmel": False,
        "source_name": source.dataset_name,
        "source_identifier": source.doi,
        "source_url": source.source_url,
        "license": source.license,
        "access_date": source.access_date,
        "capture_date": "",
        "location_general": "Natural agricultural field conditions documented by source dataset",
        "photographer": source.authors,
        "permission_status": "public_dataset_cc_by_4_0",
        "review_status": "pending_manual_review",
        "width": candidate.get("review_width", candidate["width"]),
        "height": candidate.get("review_height", candidate["height"]),
        "file_size": candidate.get("review_file_size", candidate["file_size"]),
        "sha256": candidate["sha256"],
        "perceptual_hash": candidate["perceptual_hash"],
        "duplicate_group": f"image-{str(candidate['sha256'])[:16]}",
        "duplicate_warning": "",
        "technical_status": "valid",
        "manual_review_status": "pending",
        "validation_status": "technical_valid_pending_manual_review",
        "final_status": "pending_manual_review",
        "rejection_reason": "",
        "reviewer_notes": "",
        "notes": "; ".join(
            value
            for value in (
                f"Selective remote extraction from {source.archive_name}",
                f"archive member: {candidate['archive_member']}",
                (
                    f"review_rotation_degrees={source.review_rotation_degrees}"
                    if source.review_rotation_degrees
                    else ""
                ),
            )
            if value
        ),
    }


def _review_row(mapping: dict[str, object]) -> dict[str, object]:
    row: dict[str, object] = {
        field: mapping.get(field, "") for field in REVIEW_FIELDS if field not in HUMAN_REVIEW_FIELDS
    }
    for field in HUMAN_REVIEW_FIELDS:
        row[field] = ""
    return row


def _manifest_row(
    candidate: dict[str, object], source: SourceSpec, root: Path
) -> dict[str, object]:
    path = Path(str(candidate["staged_path"])).resolve()
    portable = path.relative_to(root.resolve()).as_posix()
    return {
        "original_file_name": candidate["original_file_name"],
        "original_path": portable,
        "class_id": source.class_id,
        "source_type": "public",
        "source_name": source.dataset_name,
        "source_identifier": source.doi,
        "source_url": source.source_url,
        "license": source.license,
        "access_date": source.access_date,
        "is_local_aikmel": "false",
        "capture_date": "",
        "location_general": "Natural agricultural field conditions documented by source dataset",
        "photographer": source.authors,
        "permission_status": "public_dataset_cc_by_4_0",
        "review_status": "pending_manual_review",
        "notes": f"Archive member: {candidate['archive_member']}",
    }


def _write_source_reports(
    root: Path,
    sources: list[SourceSpec],
    source_stats: dict[str, Counter[str]],
    screening_rows: list[dict[str, object]],
    batch: str,
) -> tuple[Path, Path, Path, Path]:
    reports = root / "ml_pipeline" / "data" / "reports"
    source_rows: list[dict[str, object]] = []
    for source in sources:
        stats = source_stats[source.source_id]
        source_rows.append(
            {
                "review_batch": batch,
                "source_id": source.source_id,
                "status": "selected",
                "class_id": source.class_id,
                "dataset_name": source.dataset_name,
                "authors": source.authors,
                "organization": source.organization,
                "source_url": source.source_url,
                "doi": source.doi,
                "license": source.license,
                "license_url": source.license_url,
                "access_date": source.access_date,
                "archive_name": source.archive_name,
                "archive_size": source.archive_size,
                "archive_sha256": source.archive_sha256,
                "search_round": stats.get("rounds", 0),
                "planned_download_pool": source.download_pool_size,
                "downloaded_files": stats.get("downloaded", 0),
                "technical_valid": stats.get("technical_valid", 0),
                "technical_rejected": stats.get("technical_rejected", 0),
                "exact_duplicates_removed": stats.get("exact_duplicate", 0),
                "near_duplicates_removed": stats.get("near_duplicate", 0),
                "semantic_proxy_pass": stats.get("proxy_pass", 0),
                "semantic_proxy_review": stats.get("proxy_review", 0),
                "staged_files": stats.get("staged", 0),
                "rejection_reason": "",
                "notes": "; ".join(
                    value
                    for value in (
                        "Original archive members only; no augmented archive used.",
                        (
                            f"Review JPEG normalized by {source.review_rotation_degrees} degree rotation; staged source bytes preserved."
                            if source.review_rotation_degrees
                            else ""
                        ),
                    )
                    if value
                ),
            }
        )
    source_csv = reports / "additional_source_candidates.csv"
    if batch != "additional_batch_v1":
        _, prior_source_rows = _read_csv(source_csv)
        source_rows = [
            *[
                row
                for row in prior_source_rows
                if str(row.get("review_batch", "") or "additional_batch_v1") != batch
            ],
            *source_rows,
        ]
    else:
        source_rows.extend({"review_batch": batch, **row} for row in REJECTED_SOURCES)
    _atomic_write_csv(source_csv, source_rows, SOURCE_REPORT_FIELDS)

    screening_csv = reports / "additional_semantic_screening.csv"
    all_screening_rows = screening_rows
    if batch != "additional_batch_v1":
        _, prior_screening_rows = _read_csv(screening_csv)
        all_screening_rows = [
            *[row for row in prior_screening_rows if str(row.get("review_batch", "")) != batch],
            *screening_rows,
        ]
    _atomic_write_csv(screening_csv, all_screening_rows, ADDITIONAL_SCREENING_FIELDS)

    by_class = Counter(
        str(row.get("class_id", ""))
        for row in all_screening_rows
        if row.get("filter_status") == "staged"
    )
    proxy_pass = Counter(
        str(row.get("class_id", ""))
        for row in all_screening_rows
        if row.get("filter_status") == "staged" and row.get("screening_status") == "proxy_pass"
    )
    proxy_review = Counter(
        str(row.get("class_id", ""))
        for row in all_screening_rows
        if row.get("filter_status") == "staged" and row.get("screening_status") == "proxy_review"
    )
    summary_lines = [
        "# Additional Semantic Screening Summary",
        "",
        f"Batch: `{batch}`",
        "",
        "The existing Pillow CPU proxy was run conservatively. Proxy output never becomes a human acceptance decision.",
        "",
        "| Class | Staged | Proxy pass | Proxy review |",
        "| --- | ---: | ---: | ---: |",
    ]
    for class_id in ADDITIONAL_CLASSES:
        summary_lines.append(
            f"| {class_id} | {by_class[class_id]} | {proxy_pass[class_id]} | {proxy_review[class_id]} |"
        )
    summary_lines.extend(
        [
            "",
            "Technical failures and duplicate removals are retained in the CSV audit trail, but are not appended to the review UI.",
        ]
    )
    semantic_summary = reports / "additional_semantic_summary.md"
    _atomic_write_text(semantic_summary, "\n".join(summary_lines) + "\n")

    docs_path = root / "docs" / "DATASET_ADDITIONAL_SOURCES.md"
    if batch != "additional_batch_v1" and docs_path.is_file():
        docs_lines = [
            docs_path.read_text(encoding="utf-8").rstrip(),
            "",
            f"## Follow-up {batch}",
            "",
        ]
    else:
        docs_lines = [
            "# Dataset Additional Sources",
            "",
            f"Access date: `{sources[0].access_date}`",
            f"Review batch: `{batch}`",
            "",
            "Only explicitly licensed public academic datasets were used. Original archive members were extracted selectively with HTTP byte ranges; full multi-gigabyte archives were not stored locally.",
            "",
        ]
    for source in sources:
        stats = source_stats[source.source_id]
        docs_lines.extend(
            [
                f"## {source.class_id}: {source.dataset_name}",
                "",
                f"- Authors/organization: {source.authors}; {source.organization}",
                f"- Source: {source.source_url}",
                f"- DOI: `{source.doi}`",
                f"- License: [{source.license}]({source.license_url})",
                f"- Archive: `{source.archive_name}` (`{source.archive_sha256}`)",
                f"- Downloaded selectively: {stats.get('downloaded', 0)} files",
                f"- Added to review: {stats.get('staged', 0)} files",
                (
                    f"- Review normalization: rotate {source.review_rotation_degrees} degrees; staged originals remain unchanged"
                    if source.review_rotation_degrees
                    else "- Review normalization: EXIF transpose only"
                ),
                "",
            ]
        )
    if batch == "additional_batch_v1":
        docs_lines.extend(
            [
                "## Excluded Sources",
                "",
                "Excluded alternatives and evidence-based reasons are recorded in [rejected_sources.md](rejected_sources.md).",
                "",
                "## Attribution",
                "",
                "Redistribution or derived dataset packages must retain dataset names, authors, DOI/source links, the CC BY 4.0 notice, and an indication that images were selected and normalized by TaniAdaptif.",
            ]
        )
    _atomic_write_text(docs_path, "\n".join(docs_lines) + "\n")

    rejected_path = root / "docs" / "rejected_sources.md"
    rejected_lines = [
        "# Rejected Additional Dataset Sources",
        "",
        "These sources were evaluated but not used in `additional_batch_v1`.",
        "",
        "| Dataset | Class | License | DOI | Reason |",
        "| --- | --- | --- | --- | --- |",
    ]
    for row in REJECTED_SOURCES:
        rejected_lines.append(
            f"| [{row['dataset_name']}]({row['source_url']}) | {row['class_id']} | {row['license']} | `{row['doi']}` | {row['notes']} |"
        )
    _atomic_write_text(rejected_path, "\n".join(rejected_lines) + "\n")
    return source_csv, screening_csv, semantic_summary, docs_path


def prepare_additional_candidates(
    dataset_config_path: Path,
    sources_config_path: Path,
    *,
    review_batch: str | None = None,
    class_targets: dict[str, int] | None = None,
) -> dict[str, object]:
    root = repo_root().resolve()
    dataset_config = load_config(dataset_config_path)
    source_config, sources = _load_sources(sources_config_path)
    batch = review_batch or str(source_config.get("review_batch", "additional_batch_v1"))
    if not re.fullmatch(r"additional_batch_v[1-9][0-9]*", batch):
        raise ValueError(f"Invalid additional review batch: {batch}")
    if class_targets:
        unknown = set(class_targets) - set(ADDITIONAL_CLASSES)
        if unknown:
            raise ValueError("Unsupported class target(s): " + ", ".join(sorted(unknown)))
        sources = [
            replace(
                source,
                target_candidates=int(class_targets[source.class_id]),
                minimum_candidates=int(class_targets[source.class_id]),
            )
            for source in sources
            if source.class_id in class_targets and int(class_targets[source.class_id]) > 0
        ]
        if not sources:
            raise ValueError("At least one positive class target is required")
    workers = int(source_config.get("max_download_workers", 8))
    duplicate_threshold = int(source_config.get("duplicate_threshold", 5))
    dataset = dataset_config["dataset"]
    minimum_width = int(dataset.get("minimum_width", 512))
    minimum_height = int(dataset.get("minimum_height", 512))

    reports = root / "ml_pipeline" / "data" / "reports"
    review_root = root / "artifacts" / "dataset_review"
    candidates_root = review_root / "candidates"
    staging_root = root / "ml_pipeline" / "data" / "additional_candidates"
    work_root = root / "ml_pipeline" / "data" / ".additional_candidates_work"
    mapping_path = reports / "curation_mapping.csv"
    review_path = review_root / "manual_review_template.csv"
    semantic_path = reports / "automated_semantic_review.csv"
    manifest_path = root / "ml_pipeline" / "data" / "dataset_source_manifest.csv"
    progress_path = review_root / "review_progress.json"

    _, existing_mapping = _read_csv(mapping_path)
    _, existing_review = _read_csv(review_path)
    if not existing_mapping or not existing_review:
        raise ValueError("Existing curation mapping and completed review CSV are required")
    if any((row.get("review_batch", "") or "original_350") == batch for row in existing_mapping):
        orientation_repairs = _repair_existing_review_orientations(
            root, sources, batch, mapping_path, review_path
        )
        counts = Counter(
            row.get("class_id", "")
            for row in existing_mapping
            if (row.get("review_batch", "") or "original_350") == batch
        )
        return {
            "status": "already_prepared",
            "review_batch": batch,
            "counts": dict(counts),
            "total": sum(counts.values()),
            "orientation_repairs": orientation_repairs,
            "review_url": "http://127.0.0.1:4173",
        }
    original_mapping = [
        row
        for row in existing_mapping
        if (row.get("review_batch", "") or "original_350") == "original_350"
    ]
    original_review = [
        row
        for row in existing_review
        if (row.get("review_batch", "") or "original_350") == "original_350"
    ]
    if len(original_mapping) != 350 or len(original_review) != 350:
        raise ValueError(
            "Original review baseline changed: "
            f"mapping={len(original_mapping)}, review={len(original_review)}"
        )
    if any(
        str(row.get("accepted", "")).strip().casefold() not in {"yes", "no"}
        for row in existing_review
    ):
        raise ValueError("The original 350 review decisions are not complete")

    original_identity_fields = [
        "curated_file_name",
        "original_file_name",
        "class_id",
        "source_type",
        "sha256",
        *HUMAN_REVIEW_FIELDS,
    ]
    original_snapshot = {
        str(row["curated_file_name"]): {
            field: row.get(field, "") for field in original_identity_fields
        }
        for row in original_review
    }
    old_candidate_hashes = _candidate_image_hashes(
        candidates_root,
        [(str(row["class_id"]), str(row["curated_file_name"])) for row in existing_mapping],
    )
    references = _reference_hashes(root)

    if batch == "additional_batch_v1":
        _safe_reset(staging_root, root / "ml_pipeline" / "data" / "additional_candidates")
    else:
        staging_root.mkdir(parents=True, exist_ok=True)
        for source in sources:
            batch_dir = staging_root / source.class_id / source.source_id / batch
            if batch_dir.exists():
                shutil.rmtree(batch_dir)
    _safe_reset(work_root, root / "ml_pipeline" / "data" / ".additional_candidates_work")

    source_by_id = {source.source_id: source for source in sources}
    source_stats: dict[str, Counter[str]] = {source.source_id: Counter() for source in sources}
    retained: list[dict[str, object]] = []
    screening_rows: list[dict[str, object]] = []
    new_hashes: dict[str, str] = {}
    new_perceptual: list[tuple[str, str]] = []

    for source in sources:
        all_members = _source_members(source)
        source_retained: list[dict[str, object]] = []
        for round_number in range(1, MAX_DOWNLOAD_ROUNDS + 1):
            start = (round_number - 1) * source.download_pool_size
            members = all_members[start : start + source.download_pool_size]
            if not members:
                break
            source_stats[source.source_id]["rounds"] = round_number
            downloaded = _download_members(source, members, work_root, workers)
            for selected in members:
                extracted_path, download_error = downloaded[selected.info.filename]
                row: dict[str, object] = {
                    "review_batch": batch,
                    "source_id": source.source_id,
                    "source_name": source.dataset_name,
                    "source_url": source.source_url,
                    "doi": source.doi,
                    "license": source.license,
                    "archive_member": selected.info.filename,
                    "original_file_name": Path(selected.info.filename.replace("\\", "/")).name,
                    "class_id": source.class_id,
                    "source_type": "public",
                    "download_round": round_number,
                    "download_status": "failed" if download_error else "downloaded",
                    "technical_status": "not_checked" if download_error else "pending",
                    "filter_status": "download_reject" if download_error else "pending",
                    "filter_reason": download_error,
                    "near_duplicate_match": "",
                    "near_duplicate_distance": "",
                }
                if download_error or extracted_path is None:
                    source_stats[source.source_id]["download_failed"] += 1
                    screening_rows.append(row)
                    continue

                source_stats[source.source_id]["downloaded"] += 1
                technical = _inspect_image(extracted_path, minimum_width, minimum_height)
                row.update(
                    {
                        "image_width": technical["width"],
                        "image_height": technical["height"],
                        "technical_status": "valid" if technical["valid"] else "invalid",
                    }
                )
                if not technical["valid"]:
                    row.update(filter_status="technical_reject", filter_reason=technical["reason"])
                    source_stats[source.source_id]["technical_rejected"] += 1
                    extracted_path.unlink(missing_ok=True)
                    screening_rows.append(row)
                    continue

                source_stats[source.source_id]["technical_valid"] += 1
                sha = sha256_file(extracted_path)
                phash = difference_hash(extracted_path)
                row["sha256"] = sha
                exact_match = references["exact"].get(sha) or new_hashes.get(sha)
                if exact_match:
                    row.update(
                        filter_status="duplicate_reject",
                        filter_reason="exact_duplicate",
                        near_duplicate_match=exact_match,
                    )
                    source_stats[source.source_id]["exact_duplicate"] += 1
                    extracted_path.unlink(missing_ok=True)
                    screening_rows.append(row)
                    continue

                nearest_label = ""
                nearest_distance = duplicate_threshold + 1
                for existing_hash, label in [*references["perceptual"], *new_perceptual]:
                    distance = hamming_distance(phash, existing_hash)
                    if distance < nearest_distance:
                        nearest_distance = distance
                        nearest_label = label
                        if distance == 0:
                            break
                if nearest_distance <= duplicate_threshold:
                    row.update(
                        filter_status="duplicate_reject",
                        filter_reason="near_duplicate",
                        near_duplicate_match=nearest_label,
                        near_duplicate_distance=nearest_distance,
                    )
                    source_stats[source.source_id]["near_duplicate"] += 1
                    extracted_path.unlink(missing_ok=True)
                    screening_rows.append(row)
                    continue

                proxy = screen_image_proxy(extracted_path)
                row.update(proxy)
                source_stats[source.source_id][str(proxy["screening_status"])] += 1
                if len(source_retained) >= source.target_candidates:
                    row.update(
                        filter_status="buffer_not_needed",
                        filter_reason="target_candidate_count_reached",
                    )
                    extracted_path.unlink(missing_ok=True)
                    screening_rows.append(row)
                    continue

                source_stage = staging_root / source.class_id / source.source_id
                if batch != "additional_batch_v1":
                    source_stage = source_stage / batch
                staged_path = source_stage / selected.group / extracted_path.name
                staged_path.parent.mkdir(parents=True, exist_ok=True)
                shutil.move(str(extracted_path), staged_path)
                candidate = {
                    "source_id": source.source_id,
                    "class_id": source.class_id,
                    "archive_member": selected.info.filename,
                    "original_file_name": extracted_path.name,
                    "staged_path": staged_path,
                    "width": technical["width"],
                    "height": technical["height"],
                    "file_size": staged_path.stat().st_size,
                    "sha256": sha,
                    "perceptual_hash": phash,
                    "proxy": proxy,
                    "screening_row": row,
                }
                source_retained.append(candidate)
                retained.append(candidate)
                new_hashes[sha] = f"additional:{selected.info.filename}"
                new_perceptual.append((phash, f"additional:{selected.info.filename}"))
                source_stats[source.source_id]["staged"] += 1
                row["filter_status"] = "staged"
                row["filter_reason"] = ""
                screening_rows.append(row)

            if len(source_retained) >= source.target_candidates:
                break
        if len(source_retained) < source.minimum_candidates:
            raise ValueError(
                f"Additional candidates below minimum for {source.class_id}: "
                f"{len(source_retained)} < {source.minimum_candidates}"
            )

    _next_curated_names(existing_mapping, retained)
    new_mapping: list[dict[str, object]] = []
    new_review: list[dict[str, object]] = []
    new_semantic: list[dict[str, object]] = []
    new_manifest: list[dict[str, object]] = []
    for candidate in retained:
        source = source_by_id[str(candidate["source_id"])]
        name = str(candidate["curated_file_name"])
        target = candidates_root / source.class_id / name
        if target.exists():
            raise ValueError(f"Refusing to overwrite existing review candidate: {target}")
        target.parent.mkdir(parents=True, exist_ok=True)
        with Image.open(Path(str(candidate["staged_path"]))) as opened:
            normalized = ImageOps.exif_transpose(opened).convert("RGB")
            if source.review_rotation_degrees:
                normalized = normalized.rotate(source.review_rotation_degrees, expand=True)
            candidate["review_width"], candidate["review_height"] = normalized.size
            normalized.save(target, format="JPEG", quality=95)
            candidate["review_file_size"] = target.stat().st_size
        candidate["review_proxy"] = screen_image_proxy(target)
        mapping_row = _mapping_row(candidate, source, target, batch)
        new_mapping.append(mapping_row)
        new_review.append(_review_row(mapping_row))
        semantic_row = {
            "curated_file_name": name,
            "curated_path": str(target),
            "original_path": str(candidate["staged_path"]),
            "class_id": source.class_id,
            "source_type": "public",
            "sha256": candidate["sha256"],
            **candidate["review_proxy"],
        }
        new_semantic.append(semantic_row)
        candidate["screening_row"]["curated_file_name"] = name
        candidate["screening_row"]["curated_path"] = str(target)
        candidate["screening_row"]["original_path"] = str(candidate["staged_path"])
        candidate["screening_row"].update(candidate["review_proxy"])
        new_manifest.append(_manifest_row(candidate, source, root))

    expected_counts = {
        source.class_id: source_stats[source.source_id]["staged"] for source in sources
    }
    actual_counts = Counter(str(item["class_id"]) for item in retained)
    if dict(actual_counts) != expected_counts:
        raise ValueError(
            f"Retained candidate count mismatch: {dict(actual_counts)} != {expected_counts}"
        )

    timestamp = datetime.now(UTC).strftime("%Y%m%d_%H%M%SZ")
    backups_root = review_root / "backups"
    backup_paths = [
        _backup(review_path, backups_root, f"before_{batch}", timestamp),
        _backup(mapping_path, backups_root, f"before_{batch}", timestamp),
        _backup(semantic_path, backups_root, f"before_{batch}", timestamp),
        _backup(manifest_path, backups_root, f"before_{batch}", timestamp),
        _backup(progress_path, backups_root, f"before_{batch}", timestamp),
    ]

    for row in existing_mapping:
        row["review_batch"] = row.get("review_batch", "") or "original_350"
        row.setdefault("file_size", "")
    for row in existing_review:
        row["review_batch"] = row.get("review_batch", "") or "original_350"
    _, existing_semantic = _read_csv(semantic_path)
    _, existing_manifest = _read_csv(manifest_path)
    manifest_index = {str(row.get("original_path", "")).casefold() for row in existing_manifest}
    combined_manifest = existing_manifest + [
        row for row in new_manifest if str(row["original_path"]).casefold() not in manifest_index
    ]

    combined_mapping: list[dict[str, object]] = [*existing_mapping, *new_mapping]
    combined_review: list[dict[str, object]] = [*existing_review, *new_review]
    combined_semantic: list[dict[str, object]] = [*existing_semantic, *new_semantic]
    _atomic_write_csv(mapping_path, combined_mapping, CURATION_MAPPING_FIELDS)
    _atomic_write_csv(review_path, combined_review, REVIEW_FIELDS)
    _atomic_write_csv(semantic_path, combined_semantic, SEMANTIC_FIELDS)
    _atomic_write_csv(manifest_path, combined_manifest, PROVENANCE_FIELDS)

    progress = _progress_counts(combined_review)
    if progress["counts_per_batch"]["original_350"]["reviewed"] != 350:
        raise ValueError("Original review progress was not preserved")
    previous_progress: dict[str, object] = {}
    for backup in backup_paths:
        if backup and Path(backup).name.startswith("review_progress_"):
            try:
                previous_progress = json.loads(Path(backup).read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                previous_progress = {}
    progress.update(
        {
            "last_reviewed_file": previous_progress.get("last_reviewed_file"),
            "updated_at": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
            "review_status": "in_progress",
        }
    )
    _atomic_write_json(progress_path, progress)

    _, written_review = _read_csv(review_path)
    written_by_name = {str(row["curated_file_name"]): row for row in written_review}
    for name, expected in original_snapshot.items():
        row = written_by_name[name]
        current = {field: row.get(field, "") for field in original_identity_fields}
        if current != expected:
            raise ValueError(f"Original review decision/identity changed: {name}")
    after_candidate_hashes = _candidate_image_hashes(
        candidates_root,
        [(str(row["class_id"]), str(row["curated_file_name"])) for row in existing_mapping],
    )
    if after_candidate_hashes != old_candidate_hashes:
        raise ValueError("An existing reviewed candidate image changed during append")

    source_csv, screening_csv, semantic_summary, docs_path = _write_source_reports(
        root, sources, source_stats, screening_rows, batch
    )
    _safe_reset(work_root, root / "ml_pipeline" / "data" / ".additional_candidates_work")
    work_root.rmdir()
    return {
        "status": "additional_review_batch_ready",
        "review_batch": batch,
        "counts": dict(actual_counts),
        "total": len(retained),
        "source_stats": {key: dict(value) for key, value in source_stats.items()},
        "reference_scope_counts": references["scope_counts"],
        "source_report": str(source_csv),
        "semantic_report": str(screening_csv),
        "semantic_summary": str(semantic_summary),
        "source_documentation": str(docs_path),
        "curation_mapping": str(mapping_path),
        "manual_review_csv": str(review_path),
        "review_progress": str(progress_path),
        "backups": [path for path in backup_paths if path],
        "review_url": "http://127.0.0.1:4173",
        "default_filter": batch,
        "human_action": "Buka Dataset Review UI dan review batch additional_batch_v1.",
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Prepare licensed public additional review candidates"
    )
    parser.add_argument(
        "--config",
        default="ml_pipeline/configs/dataset_public_multicrop.yaml",
        help="Existing multi-class dataset YAML",
    )
    parser.add_argument(
        "--sources-config",
        default="ml_pipeline/configs/additional_public_sources.yaml",
        help="Verified public source registry YAML",
    )
    parser.add_argument("--json-out", default="", help="Optional result JSON path")
    parser.add_argument(
        "--review-batch",
        default="",
        help="Override batch identifier, for example additional_batch_v2",
    )
    parser.add_argument(
        "--class-targets-json",
        default="",
        help='Optional candidate targets, for example {"jagung": 5}',
    )
    return parser


def main(argv: Sequence[str] | None = None) -> dict[str, object]:
    args = build_parser().parse_args(argv)
    class_targets = None
    if args.class_targets_json:
        parsed = json.loads(args.class_targets_json)
        if not isinstance(parsed, dict):
            raise ValueError("--class-targets-json must decode to an object")
        class_targets = {str(key): int(value) for key, value in parsed.items()}
    result = prepare_additional_candidates(
        resolve_path(args.config),
        resolve_path(args.sources_config),
        review_batch=args.review_batch or None,
        class_targets=class_targets,
    )
    if args.json_out:
        output = resolve_path(args.json_out)
        _atomic_write_json(output, result)
    else:
        print(json.dumps(result, indent=2, ensure_ascii=False))
    return result


if __name__ == "__main__":
    main()
