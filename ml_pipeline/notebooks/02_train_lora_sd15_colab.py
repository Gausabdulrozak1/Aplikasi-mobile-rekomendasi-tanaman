# %% [markdown]
# # TaniAdaptif - 02 Train LoRA SD 1.5 Colab
#
# Notebook ini menjalankan pilot training LoRA untuk kelas padi.
#
# Jangan jalankan training di laptop lokal. Gunakan Google Colab GPU.
# Notebook akan berhenti jika CUDA tidak tersedia.

# %%
import json
import os
import subprocess
import sys
import time
from pathlib import Path

if "COLAB_RELEASE_TAG" not in os.environ:
    raise SystemExit("Training diblokir: notebook ini hanya untuk Google Colab.")

print("Python:", sys.version)
subprocess.run(["nvidia-smi"], check=False)
subprocess.run(["free", "-h"], check=False)
subprocess.run(["df", "-h"], check=False)

# %%
import torch

if not torch.cuda.is_available():
    raise SystemExit(
        "CUDA tidak tersedia. Pilih Runtime > Change runtime type > GPU sebelum training."
    )

device_name = torch.cuda.get_device_name(0)
total_vram_gb = torch.cuda.get_device_properties(0).total_memory / (1024**3)
compute_capability = torch.cuda.get_device_capability(0)
FP16_SUPPORTED = compute_capability[0] >= 7
MIXED_PRECISION = "fp16" if FP16_SUPPORTED else "no"
print("GPU:", device_name)
print("VRAM GB:", round(total_vram_gb, 2))
print("CUDA capability:", compute_capability)
print("Mixed precision:", MIXED_PRECISION)
if not FP16_SUPPORTED:
    print("Peringatan: fp16 tidak didukung; fallback ke full precision dan risiko OOM meningkat.")
if "T4" not in device_name and total_vram_gb < 14:
    print("Peringatan: setting notebook ini ditargetkan untuk T4 16GB atau GPU setara.")

# %%
from google.colab import drive

drive.mount("/content/drive")

# %%
PROJECT_DIR = Path("/content/TaniAdaptif")
DRIVE_ROOT = Path("/content/drive/MyDrive/TaniAdaptif")
REPO_URL = ""  # opsional, contoh: "https://github.com/username/TaniAdaptif.git"
if not PROJECT_DIR.exists():
    if REPO_URL:
        subprocess.run(["git", "clone", REPO_URL, str(PROJECT_DIR)], check=True)
    else:
        raise SystemExit(
            "Repo belum ada di /content/TaniAdaptif. Upload folder proyek ke Colab "
            "atau isi REPO_URL dengan URL Git repository, lalu jalankan ulang sel ini."
        )
os.chdir(PROJECT_DIR)
configured_path = Path(os.environ.get("TANIADAPTIF_CONFIG", "ml_pipeline/configs/pilot_padi.yaml"))
CONFIG_PATH = configured_path if configured_path.is_absolute() else PROJECT_DIR / configured_path

# %%
subprocess.run(
    [sys.executable, "-m", "pip", "install", "-r", "ml_pipeline/requirements/base.txt"], check=True
)
subprocess.run(
    [
        sys.executable,
        "-m",
        "pip",
        "install",
        "-U",
        "accelerate",
        "transformers",
        "peft",
        "safetensors",
        "bitsandbytes",
        "datasets",
    ],
    check=True,
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
            "https://github.com/huggingface/diffusers",
            str(DIFFUSERS_DIR),
        ],
        check=True,
    )
os.chdir(DIFFUSERS_DIR)
diffusers_commit = subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip()
print("Diffusers commit:", diffusers_commit)
subprocess.run([sys.executable, "-m", "pip", "install", "-e", "."], check=True)
subprocess.run(
    [sys.executable, "-m", "pip", "install", "-r", "examples/text_to_image/requirements.txt"],
    check=True,
)
os.chdir(PROJECT_DIR)

# %%
import yaml

config = yaml.safe_load(CONFIG_PATH.read_text())
train_cfg = config["training"]
validation_cfg = config["validation"]

train_data_dir = DRIVE_ROOT / "datasets" / config["experiment_name"] / "splits" / "train"
metadata_path = train_data_dir / "metadata.jsonl"
if not metadata_path.exists():
    raise SystemExit(
        f"metadata.jsonl belum ada di Drive: {metadata_path}. Jalankan notebook 01 dahulu."
    )

output_dir = Path(train_cfg["output_directory"])
output_dir.mkdir(parents=True, exist_ok=True)
print("Train data:", train_data_dir)
print("Output:", output_dir)

# %%
accelerate_config = Path("/content/accelerate_config.yaml")
accelerate_config.write_text(
    f"""compute_environment: LOCAL_MACHINE
debug: false
distributed_type: 'NO'
downcast_bf16: 'no'
gpu_ids: all
machine_rank: 0
main_training_function: main
mixed_precision: {MIXED_PRECISION}
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
print(accelerate_config.read_text())

# %%
RESUME_FROM_CHECKPOINT = ""  # isi "latest" atau path checkpoint tertentu untuk resume manual


def latest_checkpoint(directory: Path):
    checkpoints = sorted(
        directory.glob("checkpoint-*"), key=lambda path: int(path.name.split("-")[-1])
    )
    return str(checkpoints[-1]) if checkpoints else ""


if RESUME_FROM_CHECKPOINT == "latest":
    RESUME_FROM_CHECKPOINT = latest_checkpoint(output_dir)
print("Resume:", RESUME_FROM_CHECKPOINT or "fresh run")

# %%
cmd = [
    "accelerate",
    "launch",
    "--config_file",
    str(accelerate_config),
    str(DIFFUSERS_DIR / "examples" / "text_to_image" / "train_text_to_image_lora.py"),
    "--pretrained_model_name_or_path",
    config["base_model"],
    "--train_data_dir",
    str(train_data_dir),
    "--caption_column",
    "text",
    "--resolution",
    str(train_cfg["resolution"]),
    "--random_flip",
    "--train_batch_size",
    str(train_cfg["batch_size"]),
    "--gradient_accumulation_steps",
    str(train_cfg["gradient_accumulation_steps"]),
    "--max_train_steps",
    str(train_cfg["max_train_steps"]),
    "--checkpointing_steps",
    str(train_cfg["checkpointing_steps"]),
    "--checkpoints_total_limit",
    str(train_cfg["checkpoints_total_limit"]),
    "--learning_rate",
    str(train_cfg["learning_rate"]),
    "--lr_scheduler",
    "constant",
    "--lr_warmup_steps",
    "0",
    "--seed",
    str(train_cfg["seed"]),
    "--rank",
    str(train_cfg["rank"]),
    "--dataloader_num_workers",
    str(train_cfg.get("dataloader_num_workers", 0)),
    "--output_dir",
    str(output_dir),
    "--validation_prompt",
    validation_cfg["prompts"][0],
    "--num_validation_images",
    "2",
    "--report_to",
    "none",
]

if train_cfg.get("mixed_precision") == "fp16" and FP16_SUPPORTED:
    cmd += ["--mixed_precision", "fp16"]
if train_cfg.get("gradient_checkpointing"):
    cmd += ["--gradient_checkpointing"]
if train_cfg.get("use_8bit_adam"):
    cmd += ["--use_8bit_adam"]
if RESUME_FROM_CHECKPOINT:
    cmd += ["--resume_from_checkpoint", RESUME_FROM_CHECKPOINT]

print(" ".join(cmd))

# %%
start = time.time()
result = subprocess.run(cmd, check=False)
duration = time.time() - start
if result.returncode != 0:
    raise SystemExit(f"Training gagal dengan return code {result.returncode}. Cek log di atas.")
print("Durasi training detik:", round(duration, 2))

# %%
lora_output = output_dir / "pytorch_lora_weights.safetensors"
if not lora_output.exists():
    raise SystemExit(f"Training selesai tetapi file LoRA belum ditemukan: {lora_output}")

env_report = {
    "python": sys.version,
    "gpu": device_name,
    "vram_gb": round(total_vram_gb, 2),
    "diffusers_commit": diffusers_commit,
    "config": config,
    "duration_seconds": round(duration, 2),
    "output_dir": str(output_dir),
    "lora_output": str(lora_output),
}
(output_dir / "training_environment_report.json").write_text(
    json.dumps(env_report, indent=2), encoding="utf-8"
)
(output_dir / "training_config.json").write_text(json.dumps(config, indent=2), encoding="utf-8")
shutil_cmd = ["find", str(output_dir), "-maxdepth", "2", "-type", "f"]
subprocess.run(shutil_cmd, check=False)

# %% [markdown]
# Output utama Diffusers biasanya bernama `pytorch_lora_weights.safetensors` di `output_dir`.
# Jangan tulis klaim hasil training jika file tersebut belum ada.
