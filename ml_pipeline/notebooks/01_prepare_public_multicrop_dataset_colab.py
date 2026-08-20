# %% [markdown]
# # TaniAdaptif - Load Final Multicrop Dataset Package
#
# Notebook ini hanya membaca paket final `/content/dataset_multicrop_v1.zip`
# yang telah lolos audit, review manusia, split, metadata validation, dan
# automated test. Dataset kerja tetap di runtime Colab; Google Drive hanya
# menyimpan output persisten, laporan, dan konfigurasi run.

# %%
import hashlib
import json
import os
import shutil
import sys
import zipfile
from collections import Counter
from pathlib import Path

if "COLAB_RELEASE_TAG" not in os.environ:
    raise SystemExit("Preparation diblokir: notebook ini hanya untuk Google Colab.")

PACKAGE_PATH = Path("/content/dataset_multicrop_v1.zip")
UPLOAD_PARTS_DIR = Path("/content/dataset_multicrop_v1_upload_parts")
EXPECTED_SHA256 = "f6aa060658cf95e48996f10f0ffde200938d340dd15e6b60adace5bb5cecfb33"


def sha256_file(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def assemble_runtime_package(package_path, parts_dir, expected_sha256):
    package_path = Path(package_path)
    parts_dir = Path(parts_dir)
    if package_path.is_file() and sha256_file(package_path) == expected_sha256:
        return package_path, "existing_zip"
    if package_path.exists() and not package_path.is_file():
        raise SystemExit(f"STOP: path dataset bukan file regular: {package_path}")

    manifest_path = parts_dir / "upload_manifest.json"
    if not manifest_path.is_file():
        raise SystemExit(
            "STOP: ZIP final belum tersedia dan folder potongan upload tidak "
            f"ditemukan di {parts_dir}. Upload folder "
            "dataset_multicrop_v1_upload_parts melalui VS Code Explorer ke "
            "/content, lalu jalankan ulang notebook."
        )
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as exc:
        raise SystemExit(f"STOP: manifest potongan upload tidak valid: {exc}") from exc

    parts = manifest.get("parts")
    expected_size = manifest.get("source_size_bytes")
    if (
        manifest.get("schema_version") != 1
        or manifest.get("source_filename") != package_path.name
        or manifest.get("source_sha256") != expected_sha256
        or not isinstance(expected_size, int)
        or expected_size <= 0
        or not isinstance(parts, list)
        or not parts
        or manifest.get("part_count") != len(parts)
    ):
        raise SystemExit("STOP: kontrak manifest potongan upload tidak valid.")

    validated_parts = []
    observed_names = set()
    for item in parts:
        name = item.get("name") if isinstance(item, dict) else None
        size_bytes = item.get("size_bytes") if isinstance(item, dict) else None
        part_sha256 = item.get("sha256") if isinstance(item, dict) else None
        if (
            not isinstance(name, str)
            or Path(name).name != name
            or name in observed_names
            or not isinstance(size_bytes, int)
            or size_bytes <= 0
            or not isinstance(part_sha256, str)
        ):
            raise SystemExit("STOP: entry manifest potongan upload tidak valid.")
        part_path = parts_dir / name
        if not part_path.is_file() or part_path.stat().st_size != size_bytes:
            raise SystemExit(f"STOP: potongan upload hilang/tidak lengkap: {part_path}")
        actual_part_sha256 = sha256_file(part_path)
        if actual_part_sha256 != part_sha256:
            raise SystemExit(
                f"STOP: checksum potongan upload tidak cocok: {name}; "
                f"expected={part_sha256}, actual={actual_part_sha256}"
            )
        observed_names.add(name)
        validated_parts.append(part_path)

    temporary_path = package_path.with_name(f".{package_path.name}.assembling")
    if temporary_path.exists() and not temporary_path.is_file():
        raise SystemExit(f"STOP: path assembly sementara bukan file: {temporary_path}")
    try:
        temporary_path.unlink(missing_ok=True)
        with temporary_path.open("wb") as target:
            for part_path in validated_parts:
                with part_path.open("rb") as source:
                    shutil.copyfileobj(source, target, length=1024 * 1024)
        actual_size = temporary_path.stat().st_size
        actual_sha256 = sha256_file(temporary_path)
        if actual_size != expected_size or actual_sha256 != expected_sha256:
            raise SystemExit(
                "STOP: hasil penyusunan ZIP tidak valid. "
                f"size={actual_size}/{expected_size}, "
                f"sha256={actual_sha256}/{expected_sha256}"
            )
        os.replace(temporary_path, package_path)
    finally:
        temporary_path.unlink(missing_ok=True)

    if not package_path.is_file() or sha256_file(package_path) != expected_sha256:
        raise SystemExit("STOP: validasi ZIP setelah atomic replace gagal.")
    print(f"ZIP berhasil disusun dari {len(validated_parts)} potongan:", package_path)
    return package_path, "assembled_parts"


PACKAGE_PATH, PACKAGE_INPUT_MODE = assemble_runtime_package(
    PACKAGE_PATH, UPLOAD_PARTS_DIR, EXPECTED_SHA256
)
print("Package input mode:", PACKAGE_INPUT_MODE)
print("Python:", sys.version)

# %%
from google.colab import drive

drive.mount("/content/drive")

# %%
DRIVE_ROOT = Path("/content/drive/MyDrive/skripsi_lora")
EXTRACT_ROOT = Path("/content/taniadaptif_dataset_package")
PACKAGE_ROOT = EXTRACT_ROOT / "dataset_multicrop_v1"
RUNTIME_DATASET_DIR = Path("/content/taniadaptif_dataset/multicrop_v1")

for relative in (
    "outputs/smoke_test",
    "outputs/multicrop_v1",
    "evaluation",
    "logs",
):
    (DRIVE_ROOT / relative).mkdir(parents=True, exist_ok=True)

actual_checksum = sha256_file(PACKAGE_PATH)
if actual_checksum != EXPECTED_SHA256:
    raise SystemExit(
        "STOP: checksum ZIP tidak cocok. Dataset tidak diekstrak. "
        f"expected={EXPECTED_SHA256}, actual={actual_checksum}"
    )
print("ZIP SHA-256:", actual_checksum)

# %%
if EXTRACT_ROOT.exists():
    shutil.rmtree(EXTRACT_ROOT)
EXTRACT_ROOT.mkdir(parents=True)

with zipfile.ZipFile(PACKAGE_PATH) as archive:
    corrupt_member = archive.testzip()
    if corrupt_member:
        raise SystemExit(f"ZIP rusak pada member: {corrupt_member}")
    extract_root_resolved = EXTRACT_ROOT.resolve()
    for member in archive.infolist():
        target = (EXTRACT_ROOT / member.filename).resolve()
        if target != extract_root_resolved and not target.is_relative_to(extract_root_resolved):
            raise SystemExit(f"Path ZIP tidak aman: {member.filename}")
        if any(
            part.casefold() in {"raw", ".venv", "kaggle.json"}
            for part in Path(member.filename).parts
        ):
            raise SystemExit(f"Isi terlarang ditemukan dalam ZIP: {member.filename}")
    archive.extractall(EXTRACT_ROOT)

manifest_path = PACKAGE_ROOT / "PACKAGE_MANIFEST.json"
if not manifest_path.is_file():
    raise SystemExit("PACKAGE_MANIFEST.json tidak ditemukan.")
manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
if manifest.get("version") != "dataset_multicrop_v1":
    raise SystemExit("Versi paket tidak sesuai.")
print(json.dumps(manifest, indent=2, ensure_ascii=False))

# %%
EXPECTED_TRIGGERS = {
    "padi": "taniadaptif_padi",
    "jagung": "taniadaptif_jagung",
    "cabai": "taniadaptif_cabai",
    "kacang_tanah": "taniadaptif_kacang_tanah",
}
if manifest.get("triggers") != EXPECTED_TRIGGERS:
    raise SystemExit("Trigger package tidak sesuai konfigurasi final.")
if set(manifest.get("public_only_classes", [])) != {"jagung", "cabai", "kacang_tanah"}:
    raise SystemExit("Kebijakan kelas public-only tidak sesuai.")
padi_sources = manifest.get("padi_sources", {})
if padi_sources.get("public", 0) < 1 or padi_sources.get("local_aikmel", 0) < 1:
    raise SystemExit("Dataset final padi harus memuat public dan local_aikmel.")

processed_dir = PACKAGE_ROOT / "processed"
all_rows = {}
groups = {}
for split in ("train", "validation"):
    metadata_path = processed_dir / split / "metadata.jsonl"
    if not metadata_path.is_file():
        raise SystemExit(f"Metadata tidak ditemukan: {metadata_path}")
    rows = [
        json.loads(line)
        for line in metadata_path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    all_rows[split] = rows
    image_files = {
        path.relative_to(processed_dir / split).as_posix()
        for path in (processed_dir / split).rglob("*.jpg")
    }
    metadata_files = {row["file_name"] for row in rows}
    if image_files != metadata_files:
        raise SystemExit(f"Jumlah/nama gambar dan metadata tidak cocok pada {split}.")
    for row in rows:
        class_id = row.get("class_id", "")
        source_type = row.get("source_type", "")
        if EXPECTED_TRIGGERS.get(class_id) not in row.get("text", ""):
            raise SystemExit(f"Trigger caption tidak sesuai: {row.get('file_name')}")
        wrong_triggers = [
            trigger
            for other_class, trigger in EXPECTED_TRIGGERS.items()
            if other_class != class_id and trigger in row.get("text", "")
        ]
        if wrong_triggers:
            raise SystemExit(
                f"Trigger silang pada {row.get('file_name')}: {', '.join(wrong_triggers)}"
            )
        if row.get("manual_review_status") != "yes":
            raise SystemExit(f"Gambar belum diterima manual: {row.get('file_name')}")
        if class_id in {"jagung", "cabai", "kacang_tanah"} and source_type != "public":
            raise SystemExit(f"Source policy tidak valid: {class_id}/{source_type}")
        if source_type == "public" and "aikmel" in row.get("text", "").casefold():
            raise SystemExit("Caption public tidak boleh memuat klaim Aikmel.")
        groups.setdefault(row["duplicate_group"], set()).add(split)

if any(len(splits) > 1 for splits in groups.values()):
    raise SystemExit("Duplicate group bocor antara train dan validation.")

class_counts = Counter(row["class_id"] for rows in all_rows.values() for row in rows)
if any(class_counts[class_id] < 80 for class_id in EXPECTED_TRIGGERS):
    raise SystemExit(f"Jumlah final kurang dari 80 per kelas: {dict(class_counts)}")
for split, rows in all_rows.items():
    print(f"Class distribution ({split}):", dict(Counter(row["class_id"] for row in rows)))
print("Final class distribution:", dict(class_counts))
padi_source_counts = Counter(
    row["source_type"] for rows in all_rows.values() for row in rows if row["class_id"] == "padi"
)
print("Padi source distribution:", dict(padi_source_counts))
if dict(padi_source_counts) != manifest.get("padi_sources", {}):
    raise SystemExit("Distribusi sumber padi tidak cocok dengan PACKAGE_MANIFEST.json.")

# %%
DRIVE_REPORTS_DIR = DRIVE_ROOT / "logs/dataset_preparation"
for target in (RUNTIME_DATASET_DIR, DRIVE_REPORTS_DIR):
    if target.exists():
        shutil.rmtree(target)

shutil.copytree(processed_dir, RUNTIME_DATASET_DIR)
shutil.copy2(manifest_path, RUNTIME_DATASET_DIR / manifest_path.name)
shutil.copytree(PACKAGE_ROOT / "reports", DRIVE_REPORTS_DIR)
shutil.copytree(PACKAGE_ROOT / "configs", DRIVE_REPORTS_DIR / "configs")
shutil.copy2(manifest_path, DRIVE_REPORTS_DIR / manifest_path.name)
runtime_manifest = {
    "status": "valid",
    "dataset_sha256": actual_checksum,
    "package_version": manifest["version"],
    "runtime_dataset_directory": str(RUNTIME_DATASET_DIR),
    "train_rows": len(all_rows["train"]),
    "validation_rows": len(all_rows["validation"]),
    "class_counts": dict(class_counts),
}
(RUNTIME_DATASET_DIR / "runtime_dataset_manifest.json").write_text(
    json.dumps(runtime_manifest, indent=2), encoding="utf-8"
)
(DRIVE_REPORTS_DIR / "runtime_dataset_manifest.json").write_text(
    json.dumps(runtime_manifest, indent=2), encoding="utf-8"
)
print("Prepared runtime dataset:", RUNTIME_DATASET_DIR)
print("Reports:", DRIVE_REPORTS_DIR)

# %%
from IPython.display import display
from PIL import Image

for class_id in EXPECTED_TRIGGERS:
    sample = next((RUNTIME_DATASET_DIR / "train" / class_id).glob("*.jpg"), None)
    if sample:
        relative_name = sample.relative_to(RUNTIME_DATASET_DIR / "train").as_posix()
        sample_row = next(row for row in all_rows["train"] if row["file_name"] == relative_name)
        print(class_id, sample.name)
        print("Caption:", sample_row["text"])
        display(Image.open(sample).resize((256, 256)))

# %% [markdown]
# Paket final siap digunakan oleh notebook training pada runtime Colab yang
# sama. Jika runtime dihapus, upload folder potongan dan jalankan preparation
# kembali; checkpoint serta model di Google Drive tetap aman untuk resume.
