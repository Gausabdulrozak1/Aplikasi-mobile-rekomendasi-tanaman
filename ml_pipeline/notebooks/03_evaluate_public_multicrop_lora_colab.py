# %% [markdown]
# # TaniAdaptif - Evaluate Multisource Multicrop LoRA
#
# Notebook membandingkan base Stable Diffusion 1.5 dan LoRA dengan prompt,
# seed, serta parameter identik. Penilaian kelas dan skor manusia sengaja
# dibiarkan kosong sampai reviewer melihat gambar.

# %%
import csv
import json
import os
import subprocess
import sys
import time
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

if "COLAB_RELEASE_TAG" not in os.environ:
    raise SystemExit("Evaluasi image generation hanya dijalankan di Google Colab.")

import torch

if not torch.cuda.is_available():
    raise SystemExit(
        "CUDA tidak tersedia. Di VS Code: jalankan Colab: Remove Server, "
        "tutup dan buka kembali notebook, lalu pilih Select Kernel > Colab > "
        "New Colab Server > GPU > T4. Jangan pilih Auto Connect atau kernel lokal."
    )
subprocess.run(["nvidia-smi"], check=False)

# %%
from google.colab import drive

drive.mount("/content/drive")

# %%
DRIVE_ROOT = Path("/content/drive/MyDrive/skripsi_lora")
CONFIG_DIR = DRIVE_ROOT / "logs/dataset_preparation/configs"
required_configs = (
    CONFIG_DIR / "evaluation_public_multicrop.yaml",
    CONFIG_DIR / "training_public_multicrop.yaml",
)
if missing := [str(path) for path in required_configs if not path.is_file()]:
    raise SystemExit(
        "Konfigurasi evaluasi belum tersedia di Drive. "
        "Jalankan notebook preparation terlebih dahulu. Missing: " + ", ".join(missing)
    )

subprocess.run(
    [
        sys.executable,
        "-m",
        "pip",
        "install",
        "-U",
        "diffusers==0.35.1",
        "transformers>=4.41.2,<5",
        "accelerate>=0.31.0,<2",
        "peft>=0.17.0,<1",
        "huggingface-hub>=0.34.0,<1",
        "safetensors>=0.3.1,<1",
    ],
    check=True,
)
subprocess.run(
    [sys.executable, "-m", "pip", "uninstall", "--yes", "torchao"],
    check=True,
)

# %%
import yaml
from diffusers import StableDiffusionPipeline
from PIL import Image, ImageDraw, ImageFilter, ImageStat
from safetensors import safe_open
from transformers import CLIPModel, CLIPProcessor

EVALUATION_CONFIG_PATH = CONFIG_DIR / "evaluation_public_multicrop.yaml"
evaluation_config = yaml.safe_load(EVALUATION_CONFIG_PATH.read_text(encoding="utf-8"))
training_config_path = CONFIG_DIR / Path(evaluation_config["training_config"]).name
training_config = yaml.safe_load(training_config_path.read_text(encoding="utf-8"))
generation = evaluation_config["generation"]

EXPECTED_TRIGGERS = {
    "padi": "taniadaptif_padi",
    "jagung": "taniadaptif_jagung",
    "cabai": "taniadaptif_cabai",
    "kacang_tanah": "taniadaptif_kacang_tanah",
}
configured_triggers = {item["id"]: item["trigger_token"] for item in evaluation_config["classes"]}
if configured_triggers != EXPECTED_TRIGGERS:
    raise SystemExit("Trigger evaluasi tidak sesuai konfigurasi final.")

output_root = Path(evaluation_config["output"]["google_drive_directory"])
output_root.mkdir(parents=True, exist_ok=True)
canonical_lora_filename = training_config["output"]["lora_filename"]
if (
    not isinstance(canonical_lora_filename, str)
    or not canonical_lora_filename.endswith(".safetensors")
    or Path(canonical_lora_filename).name != canonical_lora_filename
):
    raise SystemExit("Nama file LoRA canonical pada config training tidak valid.")
lora_path = (
    Path(training_config["output"]["google_drive_directory"])
    / canonical_lora_filename
)


def require_valid_lora(path):
    path = Path(path)
    if not path.is_file():
        raise SystemExit(
            f"LoRA canonical belum ditemukan sebagai file: {path}. "
            "Jalankan notebook training dahulu."
        )
    if path.stat().st_size < 1024:
        raise SystemExit(f"LoRA canonical kosong atau terlalu kecil: {path}")
    try:
        with safe_open(path, framework="pt", device="cpu") as handle:
            keys = list(handle.keys())
            nonempty = sum(handle.get_tensor(key).numel() > 0 for key in keys)
            metadata_text = json.dumps(
                handle.metadata() or {}, sort_keys=True, default=str
            ).casefold()
    except Exception as exc:
        raise SystemExit(f"LoRA canonical bukan SafeTensors valid: {exc}") from exc
    if len(keys) < 8 or nonempty < 8:
        raise SystemExit("LoRA canonical tidak memuat tensor adapter yang cukup.")
    if any(
        marker in metadata_text
        for marker in ("placeholder", "dummy artifact", "synthetic artifact")
    ):
        raise SystemExit("LoRA canonical terdeteksi sebagai placeholder.")
    return path


lora_path = require_valid_lora(lora_path)

prompt_count = sum(len(item["prompts"]) for item in evaluation_config["classes"])
if prompt_count < 12:
    raise SystemExit("Evaluation config harus memiliki minimal 12 prompt.")
print("Validation prompts:", prompt_count)

# %%
pipeline = StableDiffusionPipeline.from_pretrained(
    evaluation_config["base_model"],
    torch_dtype=torch.float16,
    safety_checker=None,
)
pipeline = pipeline.to("cuda")
pipeline.enable_attention_slicing()

# %%
records = []


def generate_variant(variant, adapter_loaded):
    variant_dir = output_root / variant
    variant_dir.mkdir(parents=True, exist_ok=True)
    for class_item in evaluation_config["classes"]:
        class_id = class_item["id"]
        class_dir = variant_dir / class_id
        class_dir.mkdir(parents=True, exist_ok=True)
        for prompt_index, prompt in enumerate(class_item["prompts"], start=1):
            for seed in generation["seeds"]:
                generator = torch.Generator(device="cuda").manual_seed(int(seed))
                started_at = time.time()
                image = pipeline(
                    prompt=prompt,
                    negative_prompt=generation["negative_prompt"],
                    num_inference_steps=int(generation["inference_steps"]),
                    guidance_scale=float(generation["guidance_scale"]),
                    width=int(generation["width"]),
                    height=int(generation["height"]),
                    generator=generator,
                ).images[0]
                runtime_seconds = round(time.time() - started_at, 3)
                image_name = f"{class_id}_{variant}_prompt{prompt_index:02d}_seed{seed}.png"
                image_path = class_dir / image_name
                image.save(image_path)
                records.append(
                    {
                        "expected_class": class_id,
                        "variant": variant,
                        "adapter_loaded": adapter_loaded,
                        "prompt": prompt,
                        "negative_prompt": generation["negative_prompt"],
                        "seed": int(seed),
                        "inference_steps": int(generation["inference_steps"]),
                        "guidance_scale": float(generation["guidance_scale"]),
                        "width": int(generation["width"]),
                        "height": int(generation["height"]),
                        "output_path": str(image_path),
                        "runtime_seconds": runtime_seconds,
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                    }
                )


generate_variant("base", False)
pipeline.load_lora_weights(
    str(lora_path.parent),
    weight_name=lora_path.name,
)
generate_variant("lora", True)

# %%
manifest_path = output_root / "evaluation_manifest.json"
manifest_path.write_text(json.dumps(records, indent=2), encoding="utf-8")
manifest_csv_path = output_root / "base_vs_lora_manifest.csv"
with manifest_csv_path.open("w", newline="", encoding="utf-8") as handle:
    writer = csv.DictWriter(handle, fieldnames=list(records[0]))
    writer.writeheader()
    writer.writerows(records)

CLASS_LABELS = {
    "padi": "a photograph of rice plants growing in a field",
    "jagung": "a photograph of maize or corn plants growing in a field",
    "cabai": "a photograph of chili pepper plants growing in a field",
    "kacang_tanah": "a photograph of peanut plants growing in a field",
}
clip_model_id = "openai/clip-vit-base-patch32"
clip_processor = CLIPProcessor.from_pretrained(clip_model_id)
clip_model = CLIPModel.from_pretrained(clip_model_id).to("cuda")
clip_model.eval()


def image_proxy_metrics(record, model, processor):
    with Image.open(record["output_path"]) as opened:
        image = opened.convert("RGB")
        gray = image.convert("L")
        gray_stats = ImageStat.Stat(gray)
        edge_stats = ImageStat.Stat(gray.filter(ImageFilter.FIND_EDGES))
        inputs = processor(
            text=list(CLASS_LABELS.values()),
            images=image,
            return_tensors="pt",
            padding=True,
        )
    inputs = {key: value.to("cuda") for key, value in inputs.items()}
    with torch.no_grad():
        probabilities = model(**inputs).logits_per_image.softmax(dim=1)[0].cpu().tolist()
    scores = dict(zip(CLASS_LABELS, probabilities, strict=True))
    ranked = sorted(scores.items(), key=lambda item: item[1], reverse=True)
    predicted_class, confidence = ranked[0]
    return {
        "expected_class": record["expected_class"],
        "variant": record["variant"],
        "prompt": record["prompt"],
        "seed": record["seed"],
        "output_path": record["output_path"],
        "clip_model": clip_model_id,
        "clip_predicted_class": predicted_class,
        "clip_expected_class_score": round(scores[record["expected_class"]], 6),
        "clip_top_confidence": round(confidence, 6),
        "clip_top_margin": round(confidence - ranked[1][1], 6),
        "class_correct_proxy": predicted_class == record["expected_class"],
        "brightness_mean": round(gray_stats.mean[0], 4),
        "contrast_stddev": round(gray_stats.stddev[0], 4),
        "edge_stddev_proxy": round(edge_stats.stddev[0], 4),
    }


automated_rows = [image_proxy_metrics(record, clip_model, clip_processor) for record in records]
automated_metrics_path = output_root / "automated_metrics.csv"
with automated_metrics_path.open("w", newline="", encoding="utf-8") as handle:
    writer = csv.DictWriter(handle, fieldnames=list(automated_rows[0]))
    writer.writeheader()
    writer.writerows(automated_rows)

confusion_counts = Counter(
    (row["variant"], row["expected_class"], row["clip_predicted_class"]) for row in automated_rows
)
expected_counts = Counter((row["variant"], row["expected_class"]) for row in automated_rows)
confusion_rows = [
    {
        "variant": variant,
        "expected_class": expected_class,
        "predicted_class_proxy": predicted_class,
        "count": count,
        "share_within_expected": round(count / expected_counts[(variant, expected_class)], 6),
        "metric": clip_model_id,
        "is_automated_proxy": True,
    }
    for (variant, expected_class, predicted_class), count in sorted(confusion_counts.items())
]
confusion_proxy_path = output_root / "class_confusion_proxy.csv"
with confusion_proxy_path.open("w", newline="", encoding="utf-8") as handle:
    writer = csv.DictWriter(handle, fieldnames=list(confusion_rows[0]))
    writer.writeheader()
    writer.writerows(confusion_rows)

summary_rows = []
for variant in ("base", "lora"):
    selected = [row for row in automated_rows if row["variant"] == variant]
    summary_rows.append(
        {
            "variant": variant,
            "images": len(selected),
            "class_accuracy_proxy": sum(row["class_correct_proxy"] for row in selected)
            / len(selected),
            "mean_expected_class_score": sum(row["clip_expected_class_score"] for row in selected)
            / len(selected),
            "mean_edge_stddev_proxy": sum(row["edge_stddev_proxy"] for row in selected)
            / len(selected),
        }
    )

evaluation_summary_path = output_root / "evaluation_summary.md"
summary_lines = [
    "# Evaluation Summary",
    "",
    "Hasil berikut adalah proxy otomatis CLIP/statistik gambar, bukan penilaian visual manusia.",
    "",
    "| Variant | Images | Class accuracy proxy | Mean expected-class score | Mean edge proxy |",
    "| --- | ---: | ---: | ---: | ---: |",
]
for row in summary_rows:
    summary_lines.append(
        f"| {row['variant']} | {row['images']} | {row['class_accuracy_proxy']:.4f} | "
        f"{row['mean_expected_class_score']:.4f} | {row['mean_edge_stddev_proxy']:.4f} |"
    )
summary_lines.extend(
    [
        "",
        "## Keputusan Model",
        "",
        "- Status: pending human visual evaluation.",
        "- Multicrop/fallback: belum diputuskan dari proxy otomatis saja.",
        "- Fallback per kelas belum dijalankan.",
        "",
    ]
)
evaluation_summary_path.write_text("\n".join(summary_lines), encoding="utf-8")
del clip_model
torch.cuda.empty_cache()

human_columns = list(records[0]) + [
    "visual_quality_1_5",
    "crop_identity_1_5",
    "prompt_adherence_1_5",
    "agricultural_relevance_1_5",
    "reviewer_notes",
]
human_path = output_root / "human_evaluation_template.csv"
with human_path.open("w", newline="", encoding="utf-8") as handle:
    writer = csv.DictWriter(handle, fieldnames=human_columns)
    writer.writeheader()
    for record in records:
        writer.writerow(record)

confusion_columns = evaluation_config["confusion_review"]["columns"]
confusion_path = output_root / "class_confusion_review.csv"
with confusion_path.open("w", newline="", encoding="utf-8") as handle:
    writer = csv.DictWriter(handle, fieldnames=confusion_columns)
    writer.writeheader()
    for record in records:
        if record["variant"] != "lora":
            continue
        writer.writerow(
            {
                "expected_class": record["expected_class"],
                "predicted_visual_class": "",
                "prompt": record["prompt"],
                "seed": record["seed"],
                "reviewer_score": "",
                "class_correct": "",
                "mixed_crop_detected": "",
                "notes": "",
            }
        )


# %%
def make_class_contact_sheet(class_id):
    variant_order = {"base": 0, "lora": 1}
    class_records = sorted(
        (record for record in records if record["expected_class"] == class_id),
        key=lambda record: (
            record["prompt"],
            record["seed"],
            variant_order[record["variant"]],
        ),
    )
    tile_width = 256
    tile_height = 296
    columns = 2
    rows = (len(class_records) + columns - 1) // columns
    sheet = Image.new(
        "RGB",
        (columns * tile_width, rows * tile_height),
        "white",
    )
    draw = ImageDraw.Draw(sheet)
    for index, record in enumerate(class_records):
        image = Image.open(record["output_path"]).convert("RGB")
        image.thumbnail((tile_width, 256))
        x = (index % columns) * tile_width
        y = (index // columns) * tile_height
        sheet.paste(image, (x, y))
        label = f"{record['variant']} | seed {record['seed']}"
        draw.text((x + 4, y + 262), label, fill=(0, 0, 0))
    target = output_root / f"contact_sheet_{class_id}.png"
    sheet.save(target)
    return target


for class_item in evaluation_config["classes"]:
    print("Contact sheet:", make_class_contact_sheet(class_item["id"]))

print("Manifest:", manifest_path)
print("Base-vs-LoRA CSV:", manifest_csv_path)
print("Automated metrics:", automated_metrics_path)
print("Class confusion proxy:", confusion_proxy_path)
print("Evaluation summary:", evaluation_summary_path)
print("Human rubric:", human_path)
print("Confusion review:", confusion_path)

# %% [markdown]
# ## Review Manual
#
# Isi skor 1-5 hanya setelah gambar dilihat. Pada `class_confusion_review.csv`,
# isi kelas visual yang benar-benar terlihat, apakah kelas sesuai prompt, dan
# apakah dua komoditas atau lebih tercampur. Jangan mengisi nilai otomatis.
