# %% [markdown]
# # TaniAdaptif - 01 Prepare Dataset Colab
#
# Notebook ini menyiapkan dataset publik pilot untuk training LoRA.
#
# Penting:
# - Notebook ini adalah jalur legacy untuk smoke test padi.
# - Gunakan notebook multicrop untuk keputusan sumber final.
# - Trigger pilot publik satu kelas adalah `gaus_padi_public`; trigger final multicrop tetap `taniadaptif_padi`.

# %%
import os
import shutil
import subprocess
import sys
from pathlib import Path

if "COLAB_RELEASE_TAG" not in os.environ:
    raise SystemExit("Preparation diblokir: notebook ini hanya untuk Google Colab.")

print("Python:", sys.version)
try:
    subprocess.run(["nvidia-smi"], check=False)
except FileNotFoundError:
    print("nvidia-smi tidak tersedia. Untuk prepare dataset masih bisa berjalan tanpa GPU.")
print("RAM:")
subprocess.run(["free", "-h"], check=False)
print("Disk:")
subprocess.run(["df", "-h"], check=False)

# %%
from google.colab import drive

drive.mount("/content/drive")

# %%
PROJECT_DIR = Path("/content/TaniAdaptif")
DRIVE_ROOT = Path("/content/drive/MyDrive/TaniAdaptif")
DRIVE_ROOT.mkdir(parents=True, exist_ok=True)
REPO_URL = ""  # opsional, contoh: "https://github.com/username/TaniAdaptif.git"

if not PROJECT_DIR.exists():
    if REPO_URL:
        subprocess.run(["git", "clone", REPO_URL, str(PROJECT_DIR)], check=True)
    else:
        raise SystemExit(
            "Repo belum ada di /content/TaniAdaptif. Upload folder proyek ke Colab "
            "atau isi REPO_URL dengan URL Git repository, lalu jalankan ulang sel ini."
        )
print("Repo siap:", PROJECT_DIR)

os.chdir(PROJECT_DIR)

# %%
subprocess.run(
    [sys.executable, "-m", "pip", "install", "-r", "ml_pipeline/requirements/base.txt"], check=True
)
subprocess.run([sys.executable, "-m", "pip", "install", "datasets", "kaggle"], check=False)

# %%
import yaml

CONFIG_PATH = Path(os.environ.get("TANIADAPTIF_CONFIG", "ml_pipeline/configs/pilot_padi.yaml"))
config = yaml.safe_load(CONFIG_PATH.read_text())
dataset_config = config["dataset"]
print(config["experiment_name"])
print(dataset_config["selected_classes"])
print("source_type:", dataset_config.get("source_type", "local_directory"))
print("max_images_per_class:", dataset_config.get("max_images_per_class"))
print("max_images_total:", dataset_config.get("max_images_total"))

# %% [markdown]
# ## Autentikasi Aman
#
# Untuk Kaggle:
# 1. Upload `kaggle.json` lewat file browser Colab atau simpan di Drive.
# 2. Jangan commit `kaggle.json` ke repository.
#
# Untuk Hugging Face:
# 1. Gunakan `huggingface-cli login`.
# 2. Jangan menulis token di notebook.

# %%
KAGGLE_JSON_IN_DRIVE = DRIVE_ROOT / "secrets" / "kaggle.json"
if KAGGLE_JSON_IN_DRIVE.exists():
    kaggle_dir = Path.home() / ".kaggle"
    kaggle_dir.mkdir(parents=True, exist_ok=True)
    shutil.copy2(KAGGLE_JSON_IN_DRIVE, kaggle_dir / "kaggle.json")
    os.chmod(kaggle_dir / "kaggle.json", 0o600)
    print("kaggle.json disalin dari Drive.")
else:
    print("kaggle.json belum tersedia. Local directory/ZIP tetap bisa dipakai.")

# Jalankan sel ini hanya jika dataset Hugging Face membutuhkan autentikasi.
# Token dimasukkan melalui prompt interaktif, bukan ditulis di notebook.
if config["dataset"].get("source_type") == "huggingface_dataset":
    subprocess.run(["huggingface-cli", "login"], check=False)

# %% [markdown]
# ## Siapkan Dataset
#
# Opsi A, default lokal:
# - letakkan 80-100 gambar padi di Drive;
# - salin ke `ml_pipeline/data/raw/padi/public`;
# - jalankan pipeline audit/prepare.
#
# Opsi B, Hugging Face/Kaggle:
# - ubah `TANIADAPTIF_CONFIG` atau `CONFIG_PATH` ke config sumber publik;
# - login secara aman;
# - biarkan CLI mengambil dataset sesuai config.

# %%
source_type = dataset_config.get("source_type", "local_directory")
if source_type == "local_directory":
    RAW_SOURCE_IN_DRIVE = DRIVE_ROOT / "dataset_lora" / "pilot_padi" / "raw" / "padi"
    configured_raw = Path(dataset_config["image_directory"])
    RAW_TARGET = configured_raw if configured_raw.is_absolute() else PROJECT_DIR / configured_raw
    RAW_TARGET.mkdir(parents=True, exist_ok=True)

    if RAW_SOURCE_IN_DRIVE.exists():
        for file_path in RAW_SOURCE_IN_DRIVE.iterdir():
            if file_path.is_file():
                shutil.copy2(file_path, RAW_TARGET / file_path.name)
        print("Dataset disalin dari Drive:", RAW_SOURCE_IN_DRIVE)
    else:
        print("Folder Drive belum ada:", RAW_SOURCE_IN_DRIVE)
else:
    print(f"source_type={source_type}; dataset akan diambil oleh CLI sesuai config.")


# %%
def run_cli(command):
    subprocess.run(
        [
            sys.executable,
            "-m",
            "ml_pipeline.src.dataset.cli",
            command,
            "--config",
            str(CONFIG_PATH),
        ],
        check=True,
    )


run_cli("audit")
run_cli("prepare")

# %%
import json

report_path = Path(config["dataset"]["output_directory"]) / "reports" / "dataset_report.json"
report = json.loads(report_path.read_text())
print(json.dumps(report["summary"], indent=2))

# %%
from IPython.display import display
from PIL import Image

train_dir = Path(config["dataset"]["output_directory"]) / "splits" / "train"
samples = list(train_dir.rglob("*.jpg"))[:8]
for sample in samples:
    display(Image.open(sample).resize((160, 160)))
    print(sample)

# %%
PROCESSED_LOCAL_DIR = Path(config["dataset"]["output_directory"])
PROCESSED_DRIVE_DIR = DRIVE_ROOT / "datasets" / config["experiment_name"]
PROCESSED_DRIVE_DIR.parent.mkdir(parents=True, exist_ok=True)
shutil.copytree(PROCESSED_LOCAL_DIR, PROCESSED_DRIVE_DIR, dirs_exist_ok=True)
print("Processed dataset disimpan ke:", PROCESSED_DRIVE_DIR)

REPORT_DRIVE_DIR = DRIVE_ROOT / "reports" / config["experiment_name"]
REPORT_DRIVE_DIR.mkdir(parents=True, exist_ok=True)
for report_file in (Path(config["dataset"]["output_directory"]) / "reports").glob("*"):
    shutil.copy2(report_file, REPORT_DRIVE_DIR / report_file.name)
print("Laporan disimpan ke:", REPORT_DRIVE_DIR)
