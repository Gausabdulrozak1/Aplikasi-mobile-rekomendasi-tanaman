# %% [markdown]
# # TaniAdaptif - Train Multisource Multicrop LoRA SD 1.5
#
# Training satu LoRA gabungan untuk padi, jagung, cabai, dan kacang tanah.
# Jalankan hanya pada Google Colab GPU. Konfigurasi 1600 langkah adalah
# baseline eksperimen, bukan klaim konfigurasi terbaik.

# %%
import csv
import hashlib
import json
import math
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

if "COLAB_RELEASE_TAG" not in os.environ:
    raise SystemExit("Training diblokir: notebook ini hanya untuk Google Colab.")

print("Python:", sys.version)
subprocess.run(["nvidia-smi"], check=False)

# %%
import torch

if not torch.cuda.is_available():
    raise SystemExit(
        "CUDA tidak tersedia. Di VS Code: jalankan Colab: Remove Server, "
        "tutup dan buka kembali notebook, lalu pilih Select Kernel > Colab > "
        "New Colab Server > GPU > T4. Jangan pilih Auto Connect atau kernel lokal."
    )

gpu_name = torch.cuda.get_device_name(0)
vram_gb = torch.cuda.get_device_properties(0).total_memory / (1024**3)
print("GPU:", gpu_name)
print("VRAM GB:", round(vram_gb, 2))
if vram_gb < 14:
    print("WARNING: konfigurasi awal ditujukan untuk T4 16GB atau setara.")

# %%
from google.colab import drive

drive.mount("/content/drive")

# %%
DRIVE_ROOT = Path("/content/drive/MyDrive/skripsi_lora")
CONFIG_DIR = DRIVE_ROOT / "logs/dataset_preparation/configs"
CONFIG_PATH = CONFIG_DIR / "training_public_multicrop.yaml"
RUNTIME_DATASET_DIR = Path("/content/taniadaptif_dataset/multicrop_v1")
RUNTIME_DATASET_MANIFEST = RUNTIME_DATASET_DIR / "runtime_dataset_manifest.json"
RUNTIME_DATASETS_CACHE_DIR = Path("/content/taniadaptif_hf_datasets_cache")
EXPECTED_DATASET_SHA256 = "f6aa060658cf95e48996f10f0ffde200938d340dd15e6b60adace5bb5cecfb33"
EXPECTED_CLASS_COUNTS = {
    "padi": 95,
    "jagung": 100,
    "cabai": 97,
    "kacang_tanah": 97,
}
if not CONFIG_PATH.is_file():
    raise SystemExit(
        "Konfigurasi training belum tersedia di Drive. "
        "Jalankan notebook preparation sampai selesai terlebih dahulu."
    )
if not RUNTIME_DATASET_MANIFEST.is_file():
    raise SystemExit(
        "STOP: dataset hasil preparation tidak ditemukan di runtime Colab. "
        "Pastikan /content/dataset_multicrop_v1.zip sudah di-upload, lalu "
        "jalankan notebook preparation pada runtime yang sama."
    )
runtime_dataset_manifest = json.loads(RUNTIME_DATASET_MANIFEST.read_text(encoding="utf-8"))
if (
    runtime_dataset_manifest.get("status") != "valid"
    or runtime_dataset_manifest.get("dataset_sha256") != EXPECTED_DATASET_SHA256
    or runtime_dataset_manifest.get("train_rows") != 312
    or runtime_dataset_manifest.get("validation_rows") != 77
    or runtime_dataset_manifest.get("class_counts") != EXPECTED_CLASS_COUNTS
):
    raise SystemExit(
        "STOP: manifest dataset runtime tidak sesuai paket final. "
        "Jalankan ulang notebook preparation dari ZIP yang checksum-nya valid."
    )


def validate_runtime_split(split_root, expected_rows):
    split_root = Path(split_root)
    metadata_path = split_root / "metadata.jsonl"
    if not metadata_path.is_file():
        raise SystemExit(f"STOP: metadata runtime tidak ditemukan: {metadata_path}")

    errors = []
    rows = []
    seen_file_names = set()
    metadata_lines = [
        line for line in metadata_path.read_text(encoding="utf-8").splitlines() if line.strip()
    ]
    for line_number, line in enumerate(metadata_lines, start=1):
        try:
            row = json.loads(line)
        except json.JSONDecodeError as exc:
            errors.append(f"line {line_number}: JSON tidak valid ({exc})")
            continue
        if not isinstance(row, dict):
            errors.append(f"line {line_number}: metadata harus berupa object JSON")
            continue
        rows.append(row)

        raw_file_name = str(row.get("file_name", "")).strip()
        normalized_file_name = raw_file_name.replace("\\", "/")
        relative_path = Path(normalized_file_name)
        if not normalized_file_name:
            errors.append(f"line {line_number}: file_name kosong")
            continue
        if (
            relative_path.is_absolute()
            or ".." in relative_path.parts
            or relative_path.as_posix() != normalized_file_name
        ):
            errors.append(f"line {line_number}: file_name tidak aman: {raw_file_name}")
            continue
        if normalized_file_name in seen_file_names:
            errors.append(f"line {line_number}: file_name duplikat: {normalized_file_name}")
        seen_file_names.add(normalized_file_name)

        class_id = str(row.get("class_id", "")).strip()
        if not relative_path.parts or relative_path.parts[0] != class_id:
            errors.append(
                f"line {line_number}: prefix class tidak cocok: {normalized_file_name} / {class_id}"
            )
        image_path = split_root / relative_path
        if not image_path.is_file():
            errors.append(f"line {line_number}: gambar tidak ditemukan: {image_path}")
        elif image_path.stat().st_size <= 0:
            errors.append(f"line {line_number}: gambar kosong: {image_path}")

    allowed_extensions = {".jpg", ".jpeg", ".png", ".webp"}
    actual_images = {
        path.relative_to(split_root).as_posix()
        for path in split_root.rglob("*")
        if path.is_file() and path.suffix.casefold() in allowed_extensions
    }
    metadata_images = {str(row.get("file_name", "")).strip().replace("\\", "/") for row in rows}
    missing_images = sorted(metadata_images - actual_images)
    unlisted_images = sorted(actual_images - metadata_images)
    if len(rows) != expected_rows:
        errors.append(f"jumlah metadata {len(rows)} != expected {expected_rows}")
    if missing_images:
        errors.append("metadata menunjuk gambar yang tidak ada: " + ", ".join(missing_images[:10]))
    if unlisted_images:
        errors.append("gambar tidak tercantum di metadata: " + ", ".join(unlisted_images[:10]))
    if errors:
        detail = "\n- ".join(errors[:20])
        raise SystemExit(f"STOP: dataset runtime {split_root.name} tidak konsisten:\n- {detail}")

    return rows, {
        "split": split_root.name,
        "metadata_path": str(metadata_path),
        "metadata_sha256": hashlib.sha256(metadata_path.read_bytes()).hexdigest(),
        "metadata_rows": len(rows),
        "image_files": len(actual_images),
        "status": "valid",
    }


runtime_split_rows = {}
runtime_split_reports = {}
for split_name, expected_rows in (("train", 312), ("validation", 77)):
    split_rows, split_report = validate_runtime_split(
        RUNTIME_DATASET_DIR / split_name,
        expected_rows,
    )
    runtime_split_rows[split_name] = split_rows
    runtime_split_reports[split_name] = split_report
    print("Dataset preflight:", json.dumps(split_report, sort_keys=True))

observed_class_counts = {}
for split_rows in runtime_split_rows.values():
    for row in split_rows:
        class_id = str(row.get("class_id", "")).strip()
        observed_class_counts[class_id] = observed_class_counts.get(class_id, 0) + 1
if observed_class_counts != EXPECTED_CLASS_COUNTS:
    raise SystemExit(
        f"STOP: distribusi kelas metadata runtime tidak sesuai paket final: {observed_class_counts}"
    )

# %%
DIFFUSERS_DIR = Path("/content/diffusers")
DIFFUSERS_REF = "v0.35.1"
if not DIFFUSERS_DIR.exists():
    subprocess.run(
        [
            "git",
            "clone",
            "--branch",
            DIFFUSERS_REF,
            "--depth",
            "1",
            "https://github.com/huggingface/diffusers.git",
            str(DIFFUSERS_DIR),
        ],
        check=True,
    )
else:
    subprocess.run(
        [
            "git",
            "-C",
            str(DIFFUSERS_DIR),
            "fetch",
            "--depth",
            "1",
            "origin",
            "tag",
            DIFFUSERS_REF,
        ],
        check=True,
    )
    subprocess.run(
        ["git", "-C", str(DIFFUSERS_DIR), "checkout", "--detach", DIFFUSERS_REF],
        check=True,
    )

# requirements.txt pada example Diffusers v0.35.1 mem-pin peft==0.7.0,
# sedangkan runtime tag yang sama mensyaratkan peft>=0.17.0. Instal constraints
# yang koheren secara eksplisit agar pip tidak menurunkan PEFT setelah setup.
COLAB_TRAINING_REQUIREMENTS = (
    "accelerate>=0.31.0,<2",
    "transformers>=4.41.2,<5",
    "peft>=0.17.0,<1",
    "huggingface-hub>=0.34.0,<1",
    "datasets>=2.19.1,<5",
    "safetensors>=0.3.1,<1",
    "bitsandbytes>=0.43.3,<1",
    "ftfy>=6,<7",
    "tensorboard>=2.16,<3",
    "Jinja2>=3.1,<4",
)
UNUSED_CONFLICTING_PACKAGES = ("torchao", "wandb")
subprocess.run(
    [
        sys.executable,
        "-m",
        "pip",
        "install",
        "--upgrade",
        *COLAB_TRAINING_REQUIREMENTS,
    ],
    check=True,
)
# TorchAO dan W&B bawaan Colab tidak dipakai oleh training ini. Keduanya tetap
# dideteksi sebagai integrasi opsional dan versi runtime yang tidak kompatibel
# dapat menggagalkan import sebelum langkah training pertama.
subprocess.run(
    [
        sys.executable,
        "-m",
        "pip",
        "uninstall",
        "--yes",
        *UNUSED_CONFLICTING_PACKAGES,
    ],
    check=True,
)
subprocess.run(
    [sys.executable, "-m", "pip", "install", "-e", str(DIFFUSERS_DIR)],
    check=True,
)
diffusers_commit = subprocess.check_output(
    ["git", "-C", str(DIFFUSERS_DIR), "rev-parse", "HEAD"],
    text=True,
).strip()
print("Diffusers commit:", diffusers_commit)

dependency_probe_source = r"""
import importlib.util
import json
from importlib.metadata import version
from packaging.specifiers import SpecifierSet

requirements = {
    "accelerate": ">=0.31.0,<2",
    "transformers": ">=4.41.2,<5",
    "peft": ">=0.17.0,<1",
    "huggingface-hub": ">=0.34.0,<1",
    "datasets": ">=2.19.1,<5",
    "safetensors": ">=0.3.1,<1",
    "bitsandbytes": ">=0.43.3,<1",
}
resolved = {name: version(name) for name in requirements}
invalid = {
    name: {"version": resolved[name], "required": specifier}
    for name, specifier in requirements.items()
    if resolved[name] not in SpecifierSet(specifier)
}
if invalid:
    raise RuntimeError(f"Incompatible Colab dependencies: {invalid}")
for unused_package in ("torchao", "wandb"):
    if importlib.util.find_spec(unused_package) is not None:
        raise RuntimeError(
            f"{unused_package} must be absent because this training does not use it"
        )

import diffusers
import peft
import torch
from diffusers import StableDiffusionPipeline
from peft import LoraConfig, inject_adapter_in_model

adapter_probe = torch.nn.Sequential(torch.nn.Linear(4, 4))
inject_adapter_in_model(
    LoraConfig(r=2, lora_alpha=2, target_modules={"0"}),
    adapter_probe,
)
if not any("lora_" in name for name, _ in adapter_probe.named_parameters()):
    raise RuntimeError("PEFT adapter injection probe did not create LoRA parameters")

resolved["diffusers"] = diffusers.__version__
resolved["peft_import"] = peft.__version__
resolved["peft_adapter_probe"] = "passed"
resolved["torchao"] = "not installed"
resolved["wandb"] = "not installed"
print(json.dumps(resolved, sort_keys=True))
"""
dependency_probe = subprocess.run(
    [sys.executable, "-c", dependency_probe_source],
    text=True,
    capture_output=True,
)
if dependency_probe.returncode != 0:
    raise SystemExit(
        "Validasi dependency Colab gagal sebelum training.\n"
        + dependency_probe.stdout
        + dependency_probe.stderr
    )
resolved_dependency_versions = json.loads(dependency_probe.stdout.strip().splitlines()[-1])
print("Resolved training dependencies:", json.dumps(resolved_dependency_versions, indent=2))
from safetensors import safe_open

training_script = DIFFUSERS_DIR / "examples/text_to_image/train_text_to_image_lora.py"
if not training_script.is_file():
    raise SystemExit(f"Entrypoint training Diffusers tidak ditemukan: {training_script}")
training_entrypoint_probe = subprocess.run(
    [sys.executable, str(training_script), "--help"],
    text=True,
    capture_output=True,
)
if training_entrypoint_probe.returncode != 0:
    raise SystemExit(
        "Import probe entrypoint training gagal sebelum smoke test.\n"
        + training_entrypoint_probe.stdout
        + training_entrypoint_probe.stderr
    )
print("Training entrypoint import probe: passed")

# %%
DIFFUSERS_DEFAULT_LORA_FILENAME = "pytorch_lora_weights.safetensors"
MIN_LORA_FILE_BYTES = 1024
MIN_LORA_TENSOR_COUNT = 8
TRAINING_REPORT_TO = "tensorboard"
TRAINING_LOGGING_DIR = "tensorboard"
PLACEHOLDER_MARKERS = ("placeholder", "dummy artifact", "synthetic artifact")


def inspect_lora_safetensors(path):
    path = Path(path)
    errors = []
    tensor_count = 0
    nonempty_tensor_count = 0
    metadata = {}
    size_bytes = 0

    if path.exists() and path.is_dir():
        errors.append("path is a directory")
    elif not path.is_file():
        errors.append("file does not exist")
    else:
        size_bytes = path.stat().st_size
        if size_bytes <= 0:
            errors.append("file is empty")
        elif size_bytes < MIN_LORA_FILE_BYTES:
            errors.append(f"file is too small for a real LoRA adapter ({size_bytes} bytes)")

    if not errors:
        try:
            with safe_open(path, framework="pt", device="cpu") as handle:
                keys = list(handle.keys())
                metadata = handle.metadata() or {}
                tensor_count = len(keys)
                for key in keys:
                    if handle.get_tensor(key).numel() > 0:
                        nonempty_tensor_count += 1
                if not keys:
                    errors.append("SafeTensors contains no tensors")
                elif nonempty_tensor_count == 0:
                    errors.append("SafeTensors contains no tensor data")
                elif nonempty_tensor_count < MIN_LORA_TENSOR_COUNT:
                    errors.append(
                        "SafeTensors has too few nonempty tensors for the configured LoRA "
                        f"adapter ({nonempty_tensor_count})"
                    )
                metadata_text = json.dumps(metadata, sort_keys=True, default=str).casefold()
                if any(marker in metadata_text for marker in PLACEHOLDER_MARKERS):
                    errors.append("SafeTensors metadata identifies a placeholder artifact")
        except Exception as exc:
            errors.append(f"SafeTensors cannot be opened: {exc}")

    return {
        "valid": not errors,
        "path": str(path),
        "size_bytes": size_bytes,
        "tensor_count": tensor_count,
        "nonempty_tensor_count": nonempty_tensor_count,
        "metadata": metadata,
        "errors": errors,
    }


def sha256_file(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def normalize_diffusers_lora(output_directory, canonical_filename, require_source=True):
    output_directory = Path(output_directory)
    if (
        not isinstance(canonical_filename, str)
        or not canonical_filename.endswith(".safetensors")
        or Path(canonical_filename).name != canonical_filename
    ):
        raise RuntimeError("Canonical LoRA filename must be a SafeTensors basename.")

    canonical_path = output_directory / canonical_filename
    canonical_report = inspect_lora_safetensors(canonical_path)
    if canonical_report["valid"]:
        return canonical_path, canonical_report, "existing_canonical"

    default_path = output_directory / DIFFUSERS_DEFAULT_LORA_FILENAME
    default_report = inspect_lora_safetensors(default_path)
    if not default_report["valid"]:
        if require_source:
            raise RuntimeError(
                "No valid LoRA artifact is available. "
                f"canonical_errors={canonical_report['errors']}; "
                f"diffusers_default_errors={default_report['errors']}"
            )
        return canonical_path, canonical_report, "missing"

    if canonical_path.exists() and not canonical_path.is_file():
        raise RuntimeError(f"Canonical LoRA path is not a regular file: {canonical_path}")

    descriptor, temporary_name = tempfile.mkstemp(
        dir=output_directory,
        prefix=f".{canonical_filename}.",
        suffix=".copying",
    )
    os.close(descriptor)
    temporary_path = Path(temporary_name)
    try:
        shutil.copy2(default_path, temporary_path)
        if sha256_file(temporary_path) != sha256_file(default_path):
            raise RuntimeError("Temporary canonical copy hash does not match Diffusers output.")
        temporary_report = inspect_lora_safetensors(temporary_path)
        if not temporary_report["valid"]:
            raise RuntimeError(f"Temporary canonical copy is invalid: {temporary_report['errors']}")
        os.replace(temporary_path, canonical_path)
    finally:
        if temporary_path.exists() and temporary_path.is_file():
            temporary_path.unlink()

    canonical_report = inspect_lora_safetensors(canonical_path)
    default_after_copy = inspect_lora_safetensors(default_path)
    if not canonical_report["valid"]:
        raise RuntimeError(f"Canonical LoRA validation failed: {canonical_report['errors']}")
    if not default_after_copy["valid"]:
        raise RuntimeError("Diffusers default LoRA was not retained after canonical copy.")
    if sha256_file(canonical_path) != sha256_file(default_path):
        raise RuntimeError("Canonical LoRA hash does not match retained Diffusers output.")
    return canonical_path, canonical_report, "normalized_diffusers_default"


# %%
import yaml

config = yaml.safe_load(CONFIG_PATH.read_text(encoding="utf-8"))
train_config = config["training"]
SMOKE_TEST = True
RESUME_FROM_CHECKPOINT = None

run_mode_override = os.environ.get("TANIADAPTIF_RUN_MODE", "").strip().casefold()
if run_mode_override not in {"", "smoke", "main"}:
    raise SystemExit(f"TANIADAPTIF_RUN_MODE tidak valid: {run_mode_override!r}")
if run_mode_override:
    SMOKE_TEST = run_mode_override == "smoke"
resume_override = os.environ.get("TANIADAPTIF_RESUME_FROM_CHECKPOINT", "").strip()
if resume_override:
    RESUME_FROM_CHECKPOINT = resume_override

# Untuk training utama, ubah SMOKE_TEST menjadi False. Kedua mode otomatis
# memakai checkpoint valid terbaru apabila artefak final belum tersedia.
RUN_MODE = "smoke" if SMOKE_TEST else "main"
if RESUME_FROM_CHECKPOINT is None:
    RESUME_FROM_CHECKPOINT = "latest"

run_config = dict(train_config)
if RUN_MODE == "smoke":
    smoke_config = config["smoke_test"]
    for key in ("max_train_steps", "checkpointing_steps", "checkpoints_total_limit"):
        run_config[key] = smoke_config[key]
    output_dir = Path(smoke_config["google_drive_directory"])
    output_lora_filename = smoke_config["lora_filename"]
else:
    output_dir = Path(config["output"]["google_drive_directory"])
    output_lora_filename = config["output"]["lora_filename"]
train_data_dir = RUNTIME_DATASET_DIR / "train"
metadata_path = train_data_dir / "metadata.jsonl"
run_log_dir = DRIVE_ROOT / "logs" / ("smoke_test" if SMOKE_TEST else "multicrop_v1")
output_dir.mkdir(parents=True, exist_ok=True)
run_log_dir.mkdir(parents=True, exist_ok=True)

if (
    not isinstance(output_lora_filename, str)
    or not output_lora_filename.endswith(".safetensors")
    or Path(output_lora_filename).name != output_lora_filename
):
    raise SystemExit("Nama file LoRA canonical pada config tidak valid.")

final_lora, initial_lora_validation, lora_artifact_action = normalize_diffusers_lora(
    output_dir,
    output_lora_filename,
    require_source=False,
)
SKIP_TRAINING = initial_lora_validation["valid"]
if SKIP_TRAINING:
    print("Canonical LoRA valid; training subprocess tidak dijalankan ulang:", final_lora)

if not SMOKE_TEST:
    smoke_manifest_path = DRIVE_ROOT / "outputs/smoke_test/training_manifest.json"
    if not smoke_manifest_path.is_file():
        raise SystemExit("Training utama diblokir: manifest smoke test belum tersedia.")
    smoke_manifest = json.loads(smoke_manifest_path.read_text(encoding="utf-8"))
    smoke_lora = (
        Path(config["smoke_test"]["google_drive_directory"]) / config["smoke_test"]["lora_filename"]
    )
    smoke_lora_validation = inspect_lora_safetensors(smoke_lora)
    smoke_images = [Path(path) for path in smoke_manifest.get("validation_images", [])]
    if not (
        smoke_manifest.get("status") == "success"
        and smoke_manifest.get("target_steps") == 100
        and Path(str(smoke_manifest.get("lora_path", ""))) == smoke_lora
        and smoke_lora_validation["valid"]
        and len(smoke_images) == 4
        and all(path.is_file() for path in smoke_images)
    ):
        raise SystemExit("Training utama diblokir: bukti smoke test belum lengkap atau invalid.")

if run_config.get("use_8bit_adam"):
    try:
        import bitsandbytes  # noqa: F401
    except (ImportError, OSError) as exc:
        print(f"WARNING: 8-bit Adam tidak didukung; memakai AdamW biasa ({exc}).")
        run_config["use_8bit_adam"] = False
actual_config = {
    "run_mode": RUN_MODE,
    "base_model": config["base_model"],
    "train_data_dir": str(train_data_dir),
    "dataset_preflight": runtime_split_reports,
    "hf_datasets_cache": {
        "path": str(RUNTIME_DATASETS_CACHE_DIR),
        "reset_before_training": True,
        "model_hub_cache_unchanged": True,
    },
    "output_dir": str(output_dir),
    "lora_filename": output_lora_filename,
    "diffusers_default_lora_filename": DIFFUSERS_DEFAULT_LORA_FILENAME,
    "logging": {
        "report_to": TRAINING_REPORT_TO,
        "logging_dir": TRAINING_LOGGING_DIR,
    },
    "dependencies": resolved_dependency_versions,
    "diffusers_commit": diffusers_commit,
    "training": run_config,
}
(output_dir / "actual_training_config.json").write_text(
    json.dumps(actual_config, indent=2), encoding="utf-8"
)
if not metadata_path.exists():
    raise SystemExit(
        f"Training metadata belum tersedia: {metadata_path}. "
        "Jalankan notebook preparation terlebih dahulu."
    )

metadata_rows = runtime_split_rows["train"]
metadata_lines = [json.dumps(row, ensure_ascii=False) for row in metadata_rows]
required_triggers = {
    "taniadaptif_padi",
    "taniadaptif_jagung",
    "taniadaptif_cabai",
    "taniadaptif_kacang_tanah",
}
metadata_text = "\n".join(metadata_lines)
missing_triggers = sorted(trigger for trigger in required_triggers if trigger not in metadata_text)
if missing_triggers:
    raise SystemExit("Metadata belum mencakup trigger: " + ", ".join(missing_triggers))

for row in metadata_rows:
    class_id = row.get("class_id", "")
    source_type = row.get("source_type", "")
    if source_type == "local_aikmel" and class_id != "padi":
        raise SystemExit(f"Source policy tidak valid: {class_id}/{source_type}")
    if class_id in {"jagung", "cabai", "kacang_tanah"} and source_type != "public":
        raise SystemExit(f"Kelas public-only memiliki sumber tidak valid: {class_id}/{source_type}")
    if source_type == "public" and "aikmel" in row.get("text", "").casefold():
        raise SystemExit("Caption public tidak boleh memuat klaim lokal Aikmel.")
    if row.get("manual_review_status") != "yes":
        raise SystemExit(f"Gambar belum diterima review manual: {row.get('file_name')}")
print("Training rows:", len(metadata_lines))

# %%
accelerate_config = Path("/content/accelerate_t4.yaml")
accelerate_config.write_text(
    """compute_environment: LOCAL_MACHINE
distributed_type: 'NO'
downcast_bf16: 'no'
gpu_ids: all
machine_rank: 0
main_training_function: main
mixed_precision: fp16
num_machines: 1
num_processes: 1
rdzv_backend: static
same_network: true
tpu_env: []
tpu_use_cluster: false
tpu_use_sudo: false
use_cpu: false
""",
    encoding="utf-8",
)
print(accelerate_config.read_text(encoding="utf-8"))


# %%
def checkpoint_is_valid(path):
    if not path.is_dir() or not re.fullmatch(r"checkpoint-\d+", path.name):
        return False
    files = [item for item in path.rglob("*") if item.is_file() and item.stat().st_size > 0]
    names = {item.name for item in files}
    return bool(files) and all(
        any(name.startswith(prefix) for name in names)
        for prefix in ("optimizer", "scheduler", "random_states")
    )


def newest_checkpoint(directory):
    candidates = sorted(
        directory.glob("checkpoint-*"),
        key=lambda path: (
            int(path.name.rsplit("-", 1)[-1]) if path.name.rsplit("-", 1)[-1].isdigit() else -1
        ),
        reverse=True,
    )
    invalid = [path.name for path in candidates if not checkpoint_is_valid(path)]
    if invalid:
        print("WARNING: checkpoint invalid diabaikan:", ", ".join(invalid))
    return next((path for path in candidates if checkpoint_is_valid(path)), None)


if SKIP_TRAINING:
    RESUME_FROM_CHECKPOINT = None
elif RESUME_FROM_CHECKPOINT == "latest":
    RESUME_FROM_CHECKPOINT = newest_checkpoint(output_dir)
elif RESUME_FROM_CHECKPOINT:
    requested = Path(str(RESUME_FROM_CHECKPOINT))
    RESUME_FROM_CHECKPOINT = requested if requested.is_absolute() else output_dir / requested
    if not checkpoint_is_valid(RESUME_FROM_CHECKPOINT):
        raise SystemExit(f"Checkpoint resume tidak valid: {RESUME_FROM_CHECKPOINT}")
if not RESUME_FROM_CHECKPOINT and not SKIP_TRAINING:
    print(f"WARNING: checkpoint {RUN_MODE} belum ada; training akan mulai dari awal.")
print("Resume:", str(RESUME_FROM_CHECKPOINT) if RESUME_FROM_CHECKPOINT else "fresh run")

# %%
command = [
    "accelerate",
    "launch",
    "--config_file",
    str(accelerate_config),
    str(training_script),
    "--pretrained_model_name_or_path",
    config["base_model"],
    "--train_data_dir",
    str(train_data_dir),
    "--caption_column",
    "text",
    "--resolution",
    str(run_config["resolution"]),
    "--random_flip",
    "--train_batch_size",
    str(run_config["train_batch_size"]),
    "--gradient_accumulation_steps",
    str(run_config["gradient_accumulation_steps"]),
    "--max_train_steps",
    str(run_config["max_train_steps"]),
    "--checkpointing_steps",
    str(run_config["checkpointing_steps"]),
    "--checkpoints_total_limit",
    str(run_config["checkpoints_total_limit"]),
    "--learning_rate",
    str(run_config["learning_rate"]),
    "--lr_scheduler",
    "constant",
    "--lr_warmup_steps",
    "0",
    "--seed",
    str(run_config["seed"]),
    "--rank",
    str(run_config["rank"]),
    "--dataloader_num_workers",
    str(run_config["dataloader_num_workers"]),
    "--output_dir",
    str(output_dir),
    "--report_to",
    TRAINING_REPORT_TO,
    "--logging_dir",
    TRAINING_LOGGING_DIR,
]

if run_config.get("mixed_precision"):
    command.extend(["--mixed_precision", run_config["mixed_precision"]])
if run_config.get("gradient_checkpointing"):
    command.append("--gradient_checkpointing")
if run_config.get("use_8bit_adam"):
    command.append("--use_8bit_adam")
if RESUME_FROM_CHECKPOINT:
    command.extend(["--resume_from_checkpoint", str(RESUME_FROM_CHECKPOINT)])

print("Training command:")
print(" ".join(command))

# %%
training_log_path = output_dir / "training.log"


def training_log_tail(path, line_count=30):
    path = Path(path)
    if not path.is_file():
        return []
    return path.read_text(encoding="utf-8", errors="replace").splitlines()[-line_count:]


def training_error_excerpt(path, line_count=35):
    path = Path(path)
    if not path.is_file():
        return []
    lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    traceback_indexes = [
        index for index, line in enumerate(lines) if line.startswith("Traceback (")
    ]
    if traceback_indexes:
        start = traceback_indexes[0]
    else:
        failure_indexes = [
            index
            for index, line in enumerate(lines)
            if any(marker in line for marker in ("Error:", "Exception:", "CUDA out of memory"))
        ]
        start = failure_indexes[0] if failure_indexes else max(0, len(lines) - line_count)
    return lines[start : start + line_count]


def stop_with_training_failure(message, return_code=None, duration_seconds=0.0):
    log_tail = training_log_tail(training_log_path)
    error_excerpt = training_error_excerpt(training_log_path)
    failure_manifest = {
        "status": "failed",
        **actual_config,
        "return_code": return_code,
        "error": str(message),
        "training_log": str(training_log_path),
        "training_error_excerpt": error_excerpt,
        "training_log_tail": log_tail,
        "duration_seconds": duration_seconds,
    }
    (output_dir / "training_manifest.json").write_text(
        json.dumps(failure_manifest, indent=2),
        encoding="utf-8",
    )
    root_context = "\n".join(error_excerpt) if error_excerpt else "traceback utama tidak ditemukan"
    tail_context = "\n".join(log_tail[-10:]) if log_tail else "training.log tidak tersedia"
    raise SystemExit(
        f"{message}\nRoot training error:\n{root_context}\nTraining log tail:\n{tail_context}"
    )


training_was_run = not SKIP_TRAINING
return_code = 0
duration_seconds = 0.0
prior_training_log_text = ""
prior_training_log_path = None
if SKIP_TRAINING:
    print("Training subprocess dilewati karena canonical LoRA sudah valid.")
else:
    (output_dir / "training_manifest.json").write_text(
        json.dumps(
            {
                "status": "started",
                **actual_config,
                "resume_from_checkpoint": (
                    str(RESUME_FROM_CHECKPOINT) if RESUME_FROM_CHECKPOINT else None
                ),
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    if RESUME_FROM_CHECKPOINT and training_log_path.is_file():
        prior_training_log_text = training_log_path.read_text(encoding="utf-8", errors="replace")
        archive_stamp = time.strftime("%Y%m%dT%H%M%SZ", time.gmtime())
        prior_training_log_path = run_log_dir / f"training_before_resume_{archive_stamp}.log"
        shutil.copy2(training_log_path, prior_training_log_path)
    content_root = Path("/content").resolve()
    datasets_cache_resolved = RUNTIME_DATASETS_CACHE_DIR.resolve()
    if datasets_cache_resolved == content_root or not datasets_cache_resolved.is_relative_to(
        content_root
    ):
        stop_with_training_failure(f"Lokasi cache datasets tidak aman: {datasets_cache_resolved}")
    if RUNTIME_DATASETS_CACHE_DIR.exists():
        shutil.rmtree(RUNTIME_DATASETS_CACHE_DIR)
    RUNTIME_DATASETS_CACHE_DIR.mkdir(parents=True)
    training_environment = os.environ.copy()
    training_environment["HF_DATASETS_CACHE"] = str(RUNTIME_DATASETS_CACHE_DIR)
    print("Fresh HF Datasets cache:", RUNTIME_DATASETS_CACHE_DIR)

    imagefolder_probe_source = r"""
import json
import os
import sys
from pathlib import Path

from datasets import load_dataset

train_data_dir = Path(sys.argv[1])
cache_dir = Path(sys.argv[2])
data_files = {"train": os.path.join(str(train_data_dir), "**")}
dataset = load_dataset(
    "imagefolder",
    data_files=data_files,
    cache_dir=str(cache_dir),
)["train"]
decoded_images = 0
for row in dataset:
    image = row["image"]
    image.load()
    image.close()
    decoded_images += 1
print(
    json.dumps(
        {
            "status": "valid",
            "rows": len(dataset),
            "decoded_images": decoded_images,
            "columns": dataset.column_names,
            "cache_dir": str(cache_dir),
        },
        sort_keys=True,
    )
)
"""
    dataset_probe = subprocess.run(
        [
            sys.executable,
            "-c",
            imagefolder_probe_source,
            str(train_data_dir),
            str(RUNTIME_DATASETS_CACHE_DIR),
        ],
        env=training_environment,
        capture_output=True,
        text=True,
    )
    dataset_probe_output = "\n".join(
        part.strip() for part in (dataset_probe.stdout, dataset_probe.stderr) if part.strip()
    )
    dataset_probe_log_path = output_dir / "dataset_loader_probe.log"
    dataset_probe_log_path.write_text(dataset_probe_output + "\n", encoding="utf-8")
    if dataset_probe.returncode != 0:
        training_log_path.write_text(dataset_probe_output + "\n", encoding="utf-8")
        stop_with_training_failure(
            f"ImageFolder decoder probe gagal dengan return code {dataset_probe.returncode}.",
            return_code=dataset_probe.returncode,
        )
    try:
        dataset_probe_report = json.loads(dataset_probe.stdout.strip().splitlines()[-1])
    except (IndexError, json.JSONDecodeError) as exc:
        training_log_path.write_text(dataset_probe_output + "\n", encoding="utf-8")
        stop_with_training_failure(f"Output ImageFolder decoder probe tidak valid: {exc}")
    if (
        dataset_probe_report.get("status") != "valid"
        or dataset_probe_report.get("rows") != len(metadata_rows)
        or dataset_probe_report.get("decoded_images") != len(metadata_rows)
        or not {"image", "text"}.issubset(dataset_probe_report.get("columns", []))
    ):
        training_log_path.write_text(dataset_probe_output + "\n", encoding="utf-8")
        stop_with_training_failure(
            f"ImageFolder decoder probe tidak lengkap: {dataset_probe_report}"
        )
    actual_config["dataset_loader_probe"] = {
        **dataset_probe_report,
        "log_path": str(dataset_probe_log_path),
    }
    (output_dir / "actual_training_config.json").write_text(
        json.dumps(actual_config, indent=2), encoding="utf-8"
    )
    (output_dir / "training_manifest.json").write_text(
        json.dumps(
            {
                "status": "started",
                **actual_config,
                "resume_from_checkpoint": (
                    str(RESUME_FROM_CHECKPOINT) if RESUME_FROM_CHECKPOINT else None
                ),
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    print("ImageFolder decoder probe: passed", json.dumps(dataset_probe_report))
    started_at = time.time()
    with training_log_path.open("w", encoding="utf-8") as log_file:
        process = subprocess.Popen(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
            env=training_environment,
        )
        if process.stdout is None:
            stop_with_training_failure("Training gagal membuka stream log.")
        for line in process.stdout:
            print(line, end="")
            log_file.write(line)
        return_code = process.wait()
    duration_seconds = round(time.time() - started_at, 2)
    if return_code != 0:
        stop_with_training_failure(
            f"Training gagal dengan return code {return_code}.",
            return_code=return_code,
            duration_seconds=duration_seconds,
        )

# %%
try:
    final_lora, final_lora_validation, final_lora_action = normalize_diffusers_lora(
        output_dir,
        output_lora_filename,
        require_source=True,
    )
except RuntimeError as exc:
    stop_with_training_failure(
        f"Training selesai tanpa LoRA valid: {exc}",
        return_code=return_code,
        duration_seconds=duration_seconds,
    )
if lora_artifact_action == "missing":
    lora_artifact_action = final_lora_action

expected_checkpoint = output_dir / f"checkpoint-{run_config['max_train_steps']}"
if not checkpoint_is_valid(expected_checkpoint):
    suffix = " Canonical LoRA dipertahankan tanpa training ulang." if SKIP_TRAINING else ""
    stop_with_training_failure(
        f"Checkpoint langkah akhir tidak valid: {expected_checkpoint}.{suffix}",
        return_code=return_code,
        duration_seconds=duration_seconds,
    )

if not training_log_path.is_file() or training_log_path.stat().st_size <= 0:
    stop_with_training_failure(
        "training.log tidak tersedia atau kosong; run tidak dapat dinyatakan sukses.",
        return_code=return_code,
        duration_seconds=duration_seconds,
    )
training_log = training_log_path.read_text(encoding="utf-8", errors="replace")
loss_evidence_text = "\n".join(text for text in (prior_training_log_text, training_log) if text)
loss_values = [
    float(value)
    for value in re.findall(
        r"['\"]?(?:loss|train_loss)['\"]?\s*[=:]\s*(-?[0-9.eE+]+)",
        loss_evidence_text,
    )
]
if not loss_values or any(not math.isfinite(value) for value in loss_values):
    stop_with_training_failure(
        "Loss log tidak tersedia atau memuat nilai non-finite.",
        return_code=return_code,
        duration_seconds=duration_seconds,
    )
with (output_dir / "loss_log.csv").open("w", newline="", encoding="utf-8") as handle:
    writer = csv.writer(handle)
    writer.writerow(["observation", "loss"])
    writer.writerows(enumerate(loss_values, start=1))

from diffusers import StableDiffusionPipeline

validation_prompts = {
    "padi": "a realistic agricultural photograph of taniadaptif_padi, rice plants growing in an agricultural environment, natural lighting",
    "jagung": "a realistic agricultural photograph of taniadaptif_jagung, maize plants growing in an agricultural environment, natural lighting",
    "cabai": "a realistic agricultural photograph of taniadaptif_cabai, chili plants growing in an agricultural environment, natural lighting",
    "kacang_tanah": "a realistic agricultural photograph of taniadaptif_kacang_tanah, peanut plants growing in an agricultural environment, natural lighting",
}
negative_prompt = "blurry, low quality, distorted plants, mixed crops, watermark, text"
validation_dir = output_dir / "validation_images"
validation_dir.mkdir(parents=True, exist_ok=True)
pipeline = StableDiffusionPipeline.from_pretrained(config["base_model"], torch_dtype=torch.float16)
pipeline.load_lora_weights(str(output_dir), weight_name=final_lora.name)
pipeline.to("cuda")
for class_id, prompt in validation_prompts.items():
    generator = torch.Generator(device="cuda").manual_seed(run_config["seed"])
    image = pipeline(
        prompt=prompt,
        negative_prompt=negative_prompt,
        generator=generator,
        num_inference_steps=25,
        guidance_scale=7.5,
        width=512,
        height=512,
    ).images[0]
    image.save(validation_dir / f"{class_id}_seed_{run_config['seed']}.png")
del pipeline
torch.cuda.empty_cache()
validation_images = sorted(validation_dir.glob("*_seed_*.png"))
if len(validation_images) != len(validation_prompts):
    raise SystemExit("Empat gambar validasi belum tersedia.")

environment_report = {
    "python": sys.version,
    "gpu": gpu_name,
    "vram_gb": round(vram_gb, 2),
    "diffusers_ref": DIFFUSERS_REF,
    "diffusers_commit": diffusers_commit,
    "dependency_versions": resolved_dependency_versions,
    "duration_seconds": duration_seconds,
    "training_rows": len(metadata_lines),
    "run_mode": RUN_MODE,
    "target_steps": run_config["max_train_steps"],
    "config_path": str(CONFIG_PATH),
    "lora_path": str(final_lora),
    "lora_validation": final_lora_validation,
    "lora_artifact_action": lora_artifact_action,
    "training_performed": training_was_run,
    "prior_training_log": str(prior_training_log_path) if prior_training_log_path else None,
    "pip_freeze": subprocess.check_output(
        [sys.executable, "-m", "pip", "freeze"],
        text=True,
    ).splitlines(),
}
(output_dir / "training_environment_report.json").write_text(
    json.dumps(environment_report, indent=2),
    encoding="utf-8",
)
shutil.copy2(CONFIG_PATH, output_dir / CONFIG_PATH.name)
success_manifest = {
    "status": "success",
    **actual_config,
    "target_steps": run_config["max_train_steps"],
    "final_checkpoint": str(expected_checkpoint),
    "lora_path": str(final_lora),
    "diffusers_default_lora_path": str(output_dir / DIFFUSERS_DEFAULT_LORA_FILENAME),
    "lora_validation": final_lora_validation,
    "lora_artifact_action": lora_artifact_action,
    "training_performed": training_was_run,
    "prior_training_log": str(prior_training_log_path) if prior_training_log_path else None,
    "resume_from_checkpoint": (str(RESUME_FROM_CHECKPOINT) if RESUME_FROM_CHECKPOINT else None),
    "training_log": str(training_log_path),
    "loss_log": str(output_dir / "loss_log.csv"),
    "loss_observations": len(loss_values),
    "final_observed_loss": loss_values[-1],
    "validation_images": [str(path) for path in validation_images],
    "environment_report": str(output_dir / "training_environment_report.json"),
    "duration_seconds": duration_seconds,
}
(output_dir / "training_manifest.json").write_text(
    json.dumps(success_manifest, indent=2), encoding="utf-8"
)
for artifact in (
    training_log_path,
    output_dir / "loss_log.csv",
    output_dir / "actual_training_config.json",
    output_dir / "training_environment_report.json",
    output_dir / "training_manifest.json",
    output_dir / CONFIG_PATH.name,
):
    shutil.copy2(artifact, run_log_dir / artifact.name)
print("LoRA:", final_lora)
print("Environment report:", output_dir / "training_environment_report.json")
print("Training manifest:", output_dir / "training_manifest.json")
print("Persistent logs:", run_log_dir)
