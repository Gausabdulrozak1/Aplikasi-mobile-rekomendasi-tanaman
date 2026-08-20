# %% [markdown]
# # TaniAdaptif - 03 Evaluate LoRA Colab
#
# Notebook ini membandingkan output base Stable Diffusion 1.5 dan LoRA.
# Jangan isi skor evaluasi palsu. Skor manusia diisi setelah melihat gambar.

# %%
import csv
import json
import os
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

if "COLAB_RELEASE_TAG" not in os.environ:
    raise SystemExit("Evaluasi image generation hanya dijalankan di Google Colab.")

import torch

if not torch.cuda.is_available():
    raise SystemExit("CUDA tidak tersedia. Evaluasi image generation membutuhkan GPU.")
subprocess.run(["nvidia-smi"], check=False)

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
        "diffusers==0.35.1",
        "transformers",
        "accelerate",
        "peft",
        "safetensors",
    ],
    check=True,
)

# %%
import yaml
from diffusers import StableDiffusionPipeline
from PIL import Image, ImageDraw

config = yaml.safe_load(CONFIG_PATH.read_text())
validation = config["validation"]
output_root = DRIVE_ROOT / "evaluation" / config["experiment_name"]
base_dir = output_root / "base"
lora_dir = output_root / "lora"
for directory in (base_dir, lora_dir):
    directory.mkdir(parents=True, exist_ok=True)

lora_path = Path(config["training"]["output_directory"]) / "pytorch_lora_weights.safetensors"
if not lora_path.exists():
    raise SystemExit(f"LoRA file belum ditemukan: {lora_path}. Jalankan notebook training dahulu.")

# %%
pipe = StableDiffusionPipeline.from_pretrained(
    config["base_model"],
    torch_dtype=torch.float16,
    safety_checker=None,
)
pipe = pipe.to("cuda")
pipe.enable_attention_slicing()

# %%
negative_prompt = validation["negative_prompt"]
records = []


def generate_set(label, pipeline, out_dir):
    for prompt_index, prompt in enumerate(validation["prompts"]):
        for seed in validation["seeds"]:
            generator = torch.Generator(device="cuda").manual_seed(int(seed))
            start = time.time()
            image = pipeline(
                prompt=prompt,
                negative_prompt=negative_prompt,
                num_inference_steps=int(validation["inference_steps"]),
                guidance_scale=float(validation["guidance_scale"]),
                width=int(validation["width"]),
                height=int(validation["height"]),
                generator=generator,
            ).images[0]
            runtime = time.time() - start
            image_id = f"{label}_p{prompt_index}_seed{seed}"
            image_path = out_dir / f"{image_id}.png"
            image.save(image_path)
            records.append(
                {
                    "experiment_id": config["experiment_name"],
                    "variant": label,
                    "model": config["base_model"],
                    "lora_path": str(lora_path) if label == "lora" else "",
                    "prompt": prompt,
                    "negative_prompt": negative_prompt,
                    "seed": int(seed),
                    "steps": int(validation["inference_steps"]),
                    "guidance_scale": float(validation["guidance_scale"]),
                    "width": int(validation["width"]),
                    "height": int(validation["height"]),
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "output_path": str(image_path),
                    "runtime_seconds": round(runtime, 3),
                }
            )


generate_set("base", pipe, base_dir)
pipe.load_lora_weights(str(lora_path))
generate_set("lora", pipe, lora_dir)

# %%
manifest_path = output_root / "evaluation_manifest.json"
manifest_path.write_text(json.dumps(records, indent=2), encoding="utf-8")

csv_path = output_root / "human_evaluation_template.csv"
with csv_path.open("w", newline="", encoding="utf-8") as handle:
    fieldnames = list(records[0].keys()) + [
        "visual_quality_1_5",
        "crop_identity_1_5",
        "agricultural_relevance_1_5",
        "notes",
    ]
    writer = csv.DictWriter(handle, fieldnames=fieldnames)
    writer.writeheader()
    for record in records:
        writer.writerow(
            {
                **record,
                "visual_quality_1_5": "",
                "crop_identity_1_5": "",
                "agricultural_relevance_1_5": "",
                "notes": "",
            }
        )

print("Manifest:", manifest_path)
print("Human evaluation template:", csv_path)


# %%
def make_contact_sheet(image_paths, target_path, label):
    thumbs = []
    for image_path in image_paths:
        image = Image.open(image_path).resize((256, 256))
        thumbs.append((image_path.name, image))
    width = 512
    height = ((len(thumbs) + 1) // 2) * 300
    sheet = Image.new("RGB", (width, height), "white")
    draw = ImageDraw.Draw(sheet)
    for index, (name, image) in enumerate(thumbs):
        x = (index % 2) * 256
        y = (index // 2) * 300
        sheet.paste(image, (x, y))
        draw.text((x + 4, y + 260), f"{label}: {name}", fill=(0, 0, 0))
    sheet.save(target_path)


make_contact_sheet(sorted(base_dir.glob("*.png")), output_root / "contact_sheet_base.png", "base")
make_contact_sheet(sorted(lora_dir.glob("*.png")), output_root / "contact_sheet_lora.png", "lora")
print("Contact sheets saved:", output_root)

# %% [markdown]
# ## Rubric Evaluasi Manusia
#
# Isi skala 1-5 pada CSV:
# - `visual_quality_1_5`: kualitas visual umum.
# - `crop_identity_1_5`: apakah terlihat seperti padi.
# - `agricultural_relevance_1_5`: apakah relevan sebagai simulasi pertanian.
#
# Jangan isi nilai sebelum gambar benar-benar dilihat.
