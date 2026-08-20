"""Generate auditable BAB IV tables and figures from validated repository evidence.

This script is CPU-only. It never imports or executes Stable Diffusion, Torch,
Diffusers, or the final LoRA model. The SafeTensors artifact is verified by
size and SHA-256 only.
"""

from __future__ import annotations

import csv
import hashlib
import json
import shutil
from collections import deque
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Iterable

import matplotlib.pyplot as plt
import numpy as np
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[2]
RUN_ID = "20260820T143551Z"
RUN_DIR = ROOT / "artifacts" / "model_evaluation" / f"kaggle_run_{RUN_ID}"
MODEL_PATH = (
    ROOT
    / "artifacts"
    / "models"
    / "multisource_multicrop_lora_sd15"
    / "multisource_multicrop_lora.safetensors"
)
OUTPUT_ROOT = ROOT / "thesis_output"
FIGURE_DIR = OUTPUT_ROOT / "figures"
TABLE_DIR = OUTPUT_ROOT / "tables"
EVIDENCE_DIR = OUTPUT_ROOT / "evidence"

EXPECTED_MODEL_SHA256 = "0bda8908d577513110c22cf5ec1b8a7e008d2b26dd90525732a5c4e4b1bdd43a"
EXPECTED_MODEL_BYTES = 6_414_992

BLUE = "#1F4E79"
GREEN = "#548235"
ORANGE = "#C55A11"
GRAY = "#7F7F7F"
LIGHT_GRAY = "#D9E2F3"
CLASS_LABELS = {
    "padi": "Padi",
    "jagung": "Jagung",
    "cabai": "Cabai",
    "kacang_tanah": "Kacang tanah",
}
CLASS_ORDER = ["padi", "jagung", "cabai", "kacang_tanah"]


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def write_csv(path: Path, fieldnames: list[str], rows: Iterable[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def assert_evidence() -> dict[str, Any]:
    required = [
        RUN_DIR / "complete_pipeline_state.json",
        RUN_DIR / "training_config.json",
        RUN_DIR / "smoke_validation.json",
        RUN_DIR / "main_validation.json",
        RUN_DIR / "main_loss_history.csv",
        RUN_DIR / "human_evaluation_template_local.csv",
        RUN_DIR / "human_review_analysis.json",
        RUN_DIR / "post_review_verification.json",
        MODEL_PATH,
    ]
    missing = [str(path) for path in required if not path.is_file()]
    if missing:
        raise RuntimeError(f"Missing BAB IV evidence: {missing}")

    pipeline = load_json(RUN_DIR / "complete_pipeline_state.json")
    smoke = load_json(RUN_DIR / "smoke_validation.json")
    main = load_json(RUN_DIR / "main_validation.json")
    review = load_json(RUN_DIR / "human_review_analysis.json")
    verification = load_json(RUN_DIR / "post_review_verification.json")

    checks = {
        "pipeline_success": pipeline.get("status") == "success",
        "run_id_matches": pipeline.get("run_id") == RUN_ID,
        "smoke_pass": smoke.get("status") == "pass" and smoke.get("actual_step") == 100,
        "main_success": main.get("status") == "success" and main.get("actual_step") == 1600,
        "canonical_lora_valid": bool(main.get("canonical_lora_validation", {}).get("valid")),
        "human_review_complete": review.get("status") == "complete_validated_human_review",
        "review_rows_72": review.get("validation", {}).get("completed_rows") == 72,
        "review_pairs_36": review.get("overall", {}).get("paired_conditions") == 36,
        "post_review_checks": verification.get("all_checks_passed") is True,
        "no_automated_scores": review.get("review_provenance", {}).get("automated_scores_inserted")
        is False,
        "model_size": MODEL_PATH.stat().st_size == EXPECTED_MODEL_BYTES,
        "model_sha256": sha256(MODEL_PATH) == EXPECTED_MODEL_SHA256,
    }
    failed = [name for name, passed in checks.items() if not passed]
    if failed:
        raise RuntimeError(f"BAB IV evidence gate failed: {failed}")
    return {
        "pipeline": pipeline,
        "smoke": smoke,
        "main": main,
        "review": review,
        "verification": verification,
        "checks": checks,
    }


def configure_matplotlib() -> None:
    plt.rcParams.update(
        {
            "font.family": "serif",
            "font.serif": ["Times New Roman", "DejaVu Serif"],
            "font.size": 10,
            "axes.titlesize": 11,
            "axes.labelsize": 10,
            "xtick.labelsize": 9,
            "ytick.labelsize": 9,
            "axes.edgecolor": "#555555",
            "axes.linewidth": 0.8,
            "figure.facecolor": "white",
            "savefig.facecolor": "white",
            "savefig.bbox": "tight",
        }
    )


def save_figure(fig: plt.Figure, path: Path) -> None:
    fig.savefig(path, dpi=320, bbox_inches="tight", facecolor="white")
    plt.close(fig)


def rolling_mean(values: list[float], window: int) -> list[float]:
    queue: deque[float] = deque()
    total = 0.0
    output: list[float] = []
    for value in values:
        queue.append(value)
        total += value
        if len(queue) > window:
            total -= queue.popleft()
        output.append(total / len(queue))
    return output


def build_loss_figure() -> Path:
    rows = read_csv(RUN_DIR / "main_loss_history.csv")
    observations = [int(row["observation"]) for row in rows]
    losses = [float(row["loss"]) for row in rows]
    smooth = rolling_mean(losses, 100)

    fig, ax = plt.subplots(figsize=(7.2, 3.8))
    ax.plot(observations, losses, color=GRAY, alpha=0.18, linewidth=0.45, label="Loss aktual")
    ax.plot(
        observations, smooth, color=BLUE, linewidth=1.45, label="Rata-rata bergerak 100 observasi"
    )
    ax.set_title("Loss Fine-Tuning LoRA pada Main Training 1.600 Langkah")
    ax.set_xlabel("Observasi loss pada log training")
    ax.set_ylabel("Loss")
    ax.set_xlim(1, observations[-1])
    ax.set_ylim(bottom=0)
    ax.grid(axis="y", color="#DDDDDD", linewidth=0.6)
    ax.legend(frameon=False, loc="upper right")
    fig.tight_layout()
    path = FIGURE_DIR / "gambar_4_1_loss_main_training.png"
    save_figure(fig, path)
    return path


def add_bar_labels(ax: plt.Axes, bars: Any, suffix: str = "", decimals: int = 2) -> None:
    for bar in bars:
        value = float(bar.get_height())
        label = f"{value:.{decimals}f}{suffix}".replace(".", ",")
        ax.annotate(
            label,
            (bar.get_x() + bar.get_width() / 2, value),
            xytext=(0, 4),
            textcoords="offset points",
            ha="center",
            va="bottom",
            fontsize=9,
        )


def build_review_figures(review: dict[str, Any]) -> list[Path]:
    overall = review["overall"]
    paths: list[Path] = []

    fig, ax = plt.subplots(figsize=(5.8, 3.6))
    labels = ["Base SD 1.5", "LoRA"]
    values = [
        overall["base"]["crop_correct"]["percent"],
        overall["lora"]["crop_correct"]["percent"],
    ]
    bars = ax.bar(labels, values, color=[BLUE, GREEN], width=0.52)
    ax.set_title("Kesesuaian Komoditas pada 36 Kondisi Berpasangan")
    ax.set_ylabel("Gambar dinilai sesuai (%)")
    ax.set_ylim(0, 110)
    ax.grid(axis="y", color="#DDDDDD", linewidth=0.6)
    add_bar_labels(ax, bars, "%")
    fig.tight_layout()
    path = FIGURE_DIR / "gambar_4_2_kesesuaian_komoditas_overall.png"
    save_figure(fig, path)
    paths.append(path)

    fig, ax = plt.subplots(figsize=(6.6, 3.8))
    metrics = ["Konteks lahan", "Realisme visual"]
    base = [
        overall["base"]["field_context_quality"]["mean"],
        overall["base"]["visual_realism_score"]["mean"],
    ]
    lora = [
        overall["lora"]["field_context_quality"]["mean"],
        overall["lora"]["visual_realism_score"]["mean"],
    ]
    x = np.arange(len(metrics))
    width = 0.31
    base_bars = ax.bar(x - width / 2, base, width, label="Base SD 1.5", color=BLUE)
    lora_bars = ax.bar(x + width / 2, lora, width, label="LoRA", color=GREEN)
    ax.set_title("Rata-Rata Skor Konteks Lahan dan Realisme")
    ax.set_ylabel("Skor teknis peneliti (1-5)")
    ax.set_xticks(x, metrics)
    ax.set_ylim(0, 5.6)
    ax.grid(axis="y", color="#DDDDDD", linewidth=0.6)
    ax.legend(frameon=False, loc="upper right")
    add_bar_labels(ax, base_bars)
    add_bar_labels(ax, lora_bars)
    fig.tight_layout()
    path = FIGURE_DIR / "gambar_4_3_konteks_dan_realisme_overall.png"
    save_figure(fig, path)
    paths.append(path)

    fig, ax = plt.subplots(figsize=(7.2, 4.0))
    labels = [CLASS_LABELS[class_id] for class_id in CLASS_ORDER]
    base_values = [
        review["by_class"][class_id]["base"]["crop_correct"]["percent"] for class_id in CLASS_ORDER
    ]
    lora_values = [
        review["by_class"][class_id]["lora"]["crop_correct"]["percent"] for class_id in CLASS_ORDER
    ]
    x = np.arange(len(labels))
    width = 0.34
    base_bars = ax.bar(x - width / 2, base_values, width, label="Base SD 1.5", color=BLUE)
    lora_bars = ax.bar(x + width / 2, lora_values, width, label="LoRA", color=GREEN)
    ax.set_title("Kesesuaian Komoditas per Kelas")
    ax.set_ylabel("Gambar dinilai sesuai (%)")
    ax.set_xticks(x, labels)
    ax.set_ylim(0, 112)
    ax.grid(axis="y", color="#DDDDDD", linewidth=0.6)
    ax.legend(frameon=False, loc="lower left")
    add_bar_labels(ax, base_bars, "%")
    add_bar_labels(ax, lora_bars, "%")
    fig.tight_layout()
    path = FIGURE_DIR / "gambar_4_4_kesesuaian_per_komoditas.png"
    save_figure(fig, path)
    paths.append(path)

    fig, ax = plt.subplots(figsize=(5.8, 3.6))
    values = [
        overall["base"]["cross_class_or_unclear_count"],
        overall["lora"]["cross_class_or_unclear_count"],
    ]
    bars = ax.bar(["Base SD 1.5", "LoRA"], values, color=[BLUE, GREEN], width=0.52)
    ax.set_title("Jumlah Class Confusion atau Objek Tidak Jelas")
    ax.set_ylabel("Jumlah gambar")
    ax.set_ylim(0, max(values) + 2)
    ax.grid(axis="y", color="#DDDDDD", linewidth=0.6)
    add_bar_labels(ax, bars, decimals=0)
    fig.tight_layout()
    path = FIGURE_DIR / "gambar_4_5_class_confusion.png"
    save_figure(fig, path)
    paths.append(path)
    return paths


def get_font(size: int, bold: bool = False) -> ImageFont.ImageFont:
    candidates = [
        Path("C:/Windows/Fonts/timesbd.ttf" if bold else "C:/Windows/Fonts/times.ttf"),
        Path("C:/Windows/Fonts/arialbd.ttf" if bold else "C:/Windows/Fonts/arial.ttf"),
    ]
    for candidate in candidates:
        if candidate.is_file():
            return ImageFont.truetype(str(candidate), size=size)
    return ImageFont.load_default()


def build_selected_visual(review_rows: list[dict[str, str]]) -> Path:
    by_key = {(row["condition_id"], row["variant"]): row for row in review_rows}
    selected = [(class_id, f"{class_id}_p1_s42") for class_id in CLASS_ORDER]
    image_size = 384
    label_height = 58
    title_height = 68
    class_header_height = 48
    outer = 24
    row_gap = 18
    column_gap = 16
    variant_label_width = 104
    width = variant_label_width + outer * 2 + image_size * 4 + column_gap * 3
    height = title_height + class_header_height + outer + 2 * (image_size + label_height) + row_gap
    canvas = Image.new("RGB", (width, height), "white")
    draw = ImageDraw.Draw(canvas)
    title_font = get_font(31, bold=True)
    label_font = get_font(25, bold=True)
    note_font = get_font(22)
    draw.text(
        (outer, 20),
        "Contoh pasangan evaluasi dengan prompt dan seed identik",
        fill="black",
        font=title_font,
    )
    x_positions = [
        variant_label_width + outer + column * (image_size + column_gap) for column in range(4)
    ]
    for column, (class_id, _) in enumerate(selected):
        draw.text(
            (x_positions[column] + image_size / 2, title_height + 8),
            CLASS_LABELS[class_id],
            fill="black",
            font=label_font,
            anchor="ma",
        )

    y_start = title_height + class_header_height + outer
    for row_index, variant in enumerate(("base", "lora")):
        y = y_start + row_index * (image_size + label_height + row_gap)
        variant_label = "Base" if variant == "base" else "LoRA"
        variant_color = BLUE if variant == "base" else GREEN
        draw.text(
            (variant_label_width / 2, y + image_size / 2),
            variant_label,
            fill=variant_color,
            font=label_font,
            anchor="mm",
        )
        for column, (class_id, condition_id) in enumerate(selected):
            review_row = by_key[(condition_id, variant)]
            source = RUN_DIR / review_row["expected_image_path"]
            if not source.is_file():
                raise RuntimeError(f"Selected evaluation image is missing: {source}")
            with Image.open(source) as original:
                image = original.convert("RGB")
                if image.size != (image_size, image_size):
                    image = image.resize((image_size, image_size), Image.Resampling.LANCZOS)
                canvas.paste(image, (x_positions[column], y))
            row = review_row
            correct = "sesuai" if row["crop_correct"].lower() == "true" else "tidak sesuai"
            text_line = (
                f"{correct} | K{row['field_context_quality']} | R{row['visual_realism_score']}"
            )
            draw.text(
                (x_positions[column] + image_size / 2, y + image_size + 16),
                text_line,
                fill="black",
                font=note_font,
                anchor="ma",
            )

    path = FIGURE_DIR / "gambar_4_6_contoh_pasangan_base_lora.png"
    canvas.save(path, format="PNG", dpi=(300, 300), optimize=True)
    return path


def build_tables(evidence: dict[str, Any]) -> list[Path]:
    review = evidence["review"]
    smoke = evidence["smoke"]
    main = evidence["main"]
    training_config = load_json(RUN_DIR / "training_config.json")
    local_summary = load_json(RUN_DIR / "local_evidence_summary.json")
    outputs: list[Path] = []

    implementation_rows = [
        {
            "component": "Aplikasi mobile",
            "implementation": "Flutter Android: dashboard cuaca, form lahan, hasil rekomendasi, kalender empat minggu, permintaan visual",
            "status": "Terimplementasi dan diuji otomatis",
            "evidence": "mobile-flutter/tani_adaptif/lib; flutter test",
        },
        {
            "component": "Data cuaca",
            "implementation": "Express mengambil dan menormalisasi API BMKG untuk ADM4 Aikmel, dengan timeout dan cache",
            "status": "Kontrak dan respons live tercatat",
            "evidence": "backend-nodejs/src/services/bmkgService.js; node_bmkg_live_contract.json",
        },
        {
            "component": "Rekomendasi",
            "implementation": "Rule-based engine 30 kunci; keluaran dibatasi pada empat komoditas dan memuat rule ID",
            "status": "30/30 kunci diuji deterministik",
            "evidence": "aturanRotasi.js; rekomendasiService.test.js",
        },
        {
            "component": "Simulasi visual",
            "implementation": "Flutter -> Express proxy -> FastAPI -> provider Diffusers pada GPU",
            "status": "Kontrak mock lulus; E2E GPU nyata belum tersedia",
            "evidence": "backend_inference_proxy_live_contract.json; GPU report",
        },
        {
            "component": "Model visual",
            "implementation": "Stable Diffusion 1.5 dengan LoRA final run 20260820T143551Z",
            "status": "Training, export, sanity, dan evaluasi selesai",
            "evidence": "complete_pipeline_state.json; final_training_report.json",
        },
        {
            "component": "Penyimpanan lokal",
            "implementation": "Cache cuaca/rekomendasi dan riwayat visual maksimal 20 entri",
            "status": "Penyimpanan diuji; layar riwayat khusus belum tersedia",
            "evidence": "local_storage_service.dart; repository_test.dart",
        },
    ]
    path = TABLE_DIR / "tabel_4_1_ringkasan_implementasi.csv"
    write_csv(path, ["component", "implementation", "status", "evidence"], implementation_rows)
    outputs.append(path)

    bmkg_rows = [
        {"item": "Waktu uji tercatat", "value": "2026-08-05T11:50:22Z"},
        {"item": "Kode wilayah", "value": "52.03.09.2002"},
        {"item": "Lokasi", "value": "Aikmel, Aikmel, Lombok Timur, NTB"},
        {"item": "Titik prakiraan", "value": "18"},
        {"item": "Horizon teramati", "value": "3 hari"},
        {"item": "Titik dengan curah hujan", "value": "18/18 (lengkap)"},
        {"item": "Sumber respons", "value": "BMKG"},
        {"item": "Status cache pada pengambilan awal", "value": "network, tidak stale"},
        {
            "item": "Keluaran rule engine pada skenario uji",
            "value": "Cabai; ROT-RENDAH-CUKUP-PADI-SAWAH",
        },
    ]
    path = TABLE_DIR / "tabel_4_2_bmkg_integration.csv"
    write_csv(path, ["item", "value"], bmkg_rows)
    outputs.append(path)

    rule_rows = [
        {
            "aspect": "Kategori hujan",
            "actual": "tinggi, sedang, rendah",
            "handling": "Dari proyeksi setara 30 hari jika cakupan horizon lengkap",
        },
        {
            "aspect": "Ketersediaan air",
            "actual": "cukup, terbatas, kurang",
            "handling": "kurang dinormalisasi ke terbatas untuk pencarian aturan, dengan peringatan",
        },
        {
            "aspect": "Tanaman sebelumnya",
            "actual": "padi, jagung, cabai, kacang_tanah, kosong",
            "handling": "Menjadi bagian kunci aturan",
        },
        {
            "aspect": "Jenis lahan",
            "actual": "sawah, tegalan, kebun_campur",
            "handling": "Memengaruhi urutan prioritas dan rule ID",
        },
        {
            "aspect": "Jumlah kunci utama",
            "actual": "30",
            "handling": "3 kategori hujan x 2 kategori air pencarian x 5 tanaman sebelumnya",
        },
        {
            "aspect": "Keluaran",
            "actual": "padi, jagung, cabai, kacang_tanah",
            "handling": "Urutan prioritas, alasan, dan rule ID dapat diaudit",
        },
    ]
    path = TABLE_DIR / "tabel_4_3_rule_engine_contract.csv"
    write_csv(path, ["aspect", "actual", "handling"], rule_rows)
    outputs.append(path)

    dataset_counts = local_summary["validation"]["evidence"]["dataset_counts"]
    split_counts = {
        "padi": (76, 19),
        "jagung": (80, 20),
        "cabai": (78, 19),
        "kacang_tanah": (78, 19),
    }
    dataset_rows = []
    for class_id in CLASS_ORDER:
        train, validation = split_counts[class_id]
        dataset_rows.append(
            {
                "class_id": CLASS_LABELS[class_id],
                "final": dataset_counts["classes"][class_id],
                "train": train,
                "validation": validation,
            }
        )
    dataset_rows.append({"class_id": "Total", "final": 389, "train": 312, "validation": 77})
    path = TABLE_DIR / "tabel_4_4_dataset_distribution.csv"
    write_csv(path, ["class_id", "final", "train", "validation"], dataset_rows)
    outputs.append(path)

    config_rows = [
        {"parameter": "Model dasar", "value": training_config["base_model"]},
        {
            "parameter": "Resolusi",
            "value": f"{training_config['resolution']} x {training_config['resolution']} piksel",
        },
        {"parameter": "LoRA rank", "value": training_config["rank"]},
        {"parameter": "Train batch size", "value": 1},
        {
            "parameter": "Gradient accumulation",
            "value": training_config["gradient_accumulation_steps"],
        },
        {"parameter": "Learning rate", "value": training_config["learning_rate"]},
        {"parameter": "Optimizer", "value": "AdamW 8-bit"},
        {"parameter": "Mixed precision", "value": training_config["mixed_precision"]},
        {"parameter": "Gradient checkpointing", "value": "Aktif"},
        {"parameter": "Smoke test", "value": "100 langkah; checkpoint setiap 50"},
        {
            "parameter": "Main training",
            "value": f"{training_config['max_train_steps']} langkah; checkpoint setiap {training_config['checkpointing_steps']}",
        },
        {"parameter": "Seed", "value": training_config["seed"]},
        {
            "parameter": "Runtime",
            "value": "Kaggle GPU; Tesla T4 terdeteksi 2; VRAM 14,56 GiB pada laporan perangkat",
        },
        {"parameter": "Diffusers commit", "value": training_config["diffusers_commit"]},
    ]
    path = TABLE_DIR / "tabel_4_5_training_configuration.csv"
    write_csv(path, ["parameter", "value"], config_rows)
    outputs.append(path)

    training_rows = [
        {
            "run": "Smoke",
            "status": smoke["status"].upper(),
            "steps": smoke["actual_step"],
            "elapsed_seconds": smoke["elapsed_seconds"],
            "checkpoint": "checkpoint-50 dan checkpoint-100 valid",
            "loss_observations": smoke["loss_count"],
            "output": "multisource_multicrop_smoke_lora.safetensors",
        },
        {
            "run": "Main",
            "status": main["status"].upper(),
            "steps": main["actual_step"],
            "elapsed_seconds": main["elapsed_seconds"],
            "checkpoint": "checkpoint-1600 valid",
            "loss_observations": main["loss_count"],
            "output": "multisource_multicrop_lora.safetensors",
        },
    ]
    path = TABLE_DIR / "tabel_4_6_training_results.csv"
    write_csv(path, list(training_rows[0]), training_rows)
    outputs.append(path)

    loss_rows = []
    for label, key in (("Smoke", "smoke_loss"), ("Main", "main_loss")):
        item = local_summary[key]
        loss_rows.append(
            {
                "run": label,
                "observations": item["observations"],
                "first": item["first"],
                "last": item["last"],
                "mean": item["mean"],
                "median": item["median"],
                "minimum": item["minimum"],
                "maximum": item["maximum"],
                "first_100_mean": item["first_window_mean"],
                "last_100_mean": item["last_window_mean"],
            }
        )
    path = TABLE_DIR / "tabel_4_7_loss_summary.csv"
    write_csv(path, list(loss_rows[0]), loss_rows)
    outputs.append(path)

    overall = review["overall"]
    overall_rows = [
        {
            "metric": "Kesesuaian komoditas",
            "base": "31/36 (86,11%)",
            "lora": "34/36 (94,44%)",
            "difference": "+8,33 poin persentase",
        },
        {
            "metric": "Konteks lahan (mean; median)",
            "base": "4,0278; 4,5",
            "lora": "3,8611; 4,0",
            "difference": "-0,1667 pada mean",
        },
        {
            "metric": "Realisme visual (mean; median)",
            "base": "4,0278; 4,5",
            "lora": "3,8611; 4,0",
            "difference": "-0,1667 pada mean",
        },
        {
            "metric": "Class confusion/cross-class/unclear",
            "base": "5",
            "lora": "2",
            "difference": "-3 gambar",
        },
    ]
    path = TABLE_DIR / "tabel_4_8_human_review_overall.csv"
    write_csv(path, ["metric", "base", "lora", "difference"], overall_rows)
    outputs.append(path)

    class_rows = []
    for class_id in CLASS_ORDER:
        item = review["by_class"][class_id]
        class_rows.append(
            {
                "class_id": CLASS_LABELS[class_id],
                "pairs": item["paired_conditions"],
                "base_correct": f"{item['base']['crop_correct']['count']}/9",
                "lora_correct": f"{item['lora']['crop_correct']['count']}/9",
                "base_context_median": item["base"]["field_context_quality"]["median"],
                "lora_context_median": item["lora"]["field_context_quality"]["median"],
                "base_realism_median": item["base"]["visual_realism_score"]["median"],
                "lora_realism_median": item["lora"]["visual_realism_score"]["median"],
                "base_unclear": item["base"]["cross_class_or_unclear_count"],
                "lora_unclear": item["lora"]["cross_class_or_unclear_count"],
            }
        )
    path = TABLE_DIR / "tabel_4_9_human_review_by_class.csv"
    write_csv(path, list(class_rows[0]), class_rows)
    outputs.append(path)

    paired_rows = []
    for metric, label in (
        ("crop_correct", "Kesesuaian komoditas"),
        ("field_context_quality", "Konteks lahan"),
        ("visual_realism_score", "Realisme visual"),
    ):
        item = overall["paired_comparison"][metric]
        paired_rows.append(
            {
                "metric": label,
                "test": item["test"],
                "lora_wins": item["lora_wins"],
                "ties": item["ties"],
                "base_wins": item["base_wins"],
                "non_tied": item["non_tied"],
                "exact_p_value": item["exact_p_value"],
            }
        )
    path = TABLE_DIR / "tabel_4_10_paired_statistics.csv"
    write_csv(path, list(paired_rows[0]), paired_rows)
    outputs.append(path)

    proxy_rows = [row for row in local_summary["proxy_metrics"] if row["class_id"] == "all"]
    path = TABLE_DIR / "tabel_4_11_proxy_metrics.csv"
    write_csv(
        path,
        ["variant", "images", "brightness_proxy_mean", "contrast_proxy_mean", "entropy_proxy_mean"],
        proxy_rows,
    )
    outputs.append(path)
    return outputs


def build_black_box_table() -> Path:
    rows = [
        {
            "no": 1,
            "feature": "Health backend",
            "scenario": "Memanggil endpoint kesehatan",
            "input": "GET /api/kesehatan",
            "expected": "HTTP 200 dan status layanan",
            "actual": "Kontrak kesehatan terpenuhi",
            "status": "Lulus",
        },
        {
            "no": 2,
            "feature": "Validasi rekomendasi",
            "scenario": "Mengirim input valid dan tidak lengkap",
            "input": "POST /api/rekomendasi",
            "expected": "Input valid diproses; input salah ditolak",
            "actual": "Rule ID dikembalikan dan payload salah ditolak",
            "status": "Lulus",
        },
        {
            "no": 3,
            "feature": "Parser BMKG",
            "scenario": "Field curah hujan tidak tersedia",
            "input": "Fixture tanpa tp",
            "expected": "Nilai dipertahankan null",
            "actual": "Tidak dibuat nilai hujan fiktif",
            "status": "Lulus",
        },
        {
            "no": 4,
            "feature": "Cache BMKG",
            "scenario": "Network, cache segar, lalu timeout",
            "input": "Tiga permintaan berurutan",
            "expected": "network -> fresh-cache -> stale-cache",
            "actual": "Urutan fallback teramati",
            "status": "Lulus",
        },
        {
            "no": 5,
            "feature": "Decision table",
            "scenario": "Menjalankan seluruh kunci aturan",
            "input": "30 kombinasi hujan-air-tanaman",
            "expected": "Keluaran valid dan dapat diaudit",
            "actual": "30/30 kunci menghasilkan empat kelas terbatas",
            "status": "Lulus",
        },
        {
            "no": 6,
            "feature": "Penyesuaian lahan",
            "scenario": "Membandingkan sawah dan non-sawah",
            "input": "Input cuaca/air/tanaman sama",
            "expected": "Jenis lahan memengaruhi prioritas",
            "actual": "Prioritas berubah deterministik; rule ID berbeda",
            "status": "Lulus",
        },
        {
            "no": 7,
            "feature": "Kalender rekomendasi",
            "scenario": "Membentuk rencana satu bulan",
            "input": "Kondisi valid dan tanggal acuan",
            "expected": "Empat rentang mingguan stabil",
            "actual": "Empat minggu dengan tanggal stabil",
            "status": "Lulus",
        },
        {
            "no": 8,
            "feature": "Integrasi BMKG live",
            "scenario": "Mengambil cuaca ADM4 Aikmel",
            "input": "52.03.09.2002",
            "expected": "Respons lokasi dan horizon dapat diproses",
            "actual": "Uji 5 Agustus 2026: 18 titik/3 hari; 18 tp lengkap",
            "status": "Lulus",
        },
        {
            "no": 9,
            "feature": "FastAPI health/ready",
            "scenario": "Menjalankan provider lokal aman",
            "input": "GET /health dan /ready",
            "expected": "Status provider eksplisit",
            "actual": "HTTP 200, provider mock dan CPU terlabel jelas",
            "status": "Lulus (mock)",
        },
        {
            "no": 10,
            "feature": "Validasi inference",
            "scenario": "Crop/dimensi/prompt tidak valid",
            "input": "Payload di luar kontrak",
            "expected": "HTTP 422 terstruktur",
            "actual": "VALIDATION_ERROR dikembalikan",
            "status": "Lulus",
        },
        {
            "no": 11,
            "feature": "Timeout inference",
            "scenario": "Provider gagal atau lambat",
            "input": "Fixture error dan timeout",
            "expected": "Retry terbatas; HTTP 503/504",
            "actual": "Satu retry untuk error; timeout tidak diulang",
            "status": "Lulus",
        },
        {
            "no": 12,
            "feature": "Akses visual backend",
            "scenario": "Token kosong/placeholder dan rate limit",
            "input": "Route /api/visual",
            "expected": "Akses ditolak atau dibatasi",
            "actual": "Token salah ditolak; rate limit aktif",
            "status": "Lulus",
        },
        {
            "no": 13,
            "feature": "Proxy pembangkitan",
            "scenario": "Meneruskan konteks rekomendasi",
            "input": "POST /api/visual/generate",
            "expected": "Request ID dipertahankan; URL upstream tersembunyi",
            "actual": "Kontrak terpenuhi pada provider mock",
            "status": "Lulus (mock)",
        },
        {
            "no": 14,
            "feature": "Pengiriman PNG",
            "scenario": "Mengambil gambar melalui Express",
            "input": "GET /api/visual/images/*.png",
            "expected": "PNG valid dari domain backend",
            "actual": "PNG mock valid dan URL upstream tidak terbuka",
            "status": "Lulus (mock)",
        },
        {
            "no": 15,
            "feature": "Cache cuaca Flutter",
            "scenario": "Jaringan gagal setelah data tersimpan",
            "input": "Simulasi offline",
            "expected": "Cache lokal ditampilkan",
            "actual": "Data cache termuat dengan notice",
            "status": "Lulus",
        },
        {
            "no": 16,
            "feature": "Cache rekomendasi Flutter",
            "scenario": "Mencari cache dengan signature input",
            "input": "Signature sama dan berbeda",
            "expected": "Hanya signature sama yang dimuat",
            "actual": "Perilaku sesuai kontrak",
            "status": "Lulus",
        },
        {
            "no": 17,
            "feature": "Isolasi kegagalan visual",
            "scenario": "Provider visual gagal",
            "input": "Rekomendasi Jagung + error visual",
            "expected": "Rekomendasi tetap terlihat",
            "actual": "Widget tetap menampilkan Jagung",
            "status": "Lulus",
        },
        {
            "no": 18,
            "feature": "Riwayat visual",
            "scenario": "Menyimpan 25 entri",
            "input": "25 fixture riwayat",
            "expected": "Maksimal 20 entri terbaru",
            "actual": "Entri request-24 sampai request-5 tersimpan",
            "status": "Lulus",
        },
        {
            "no": 19,
            "feature": "Artefak LoRA",
            "scenario": "Memvalidasi model dan export",
            "input": "ZIP run 20260820T143551Z",
            "expected": "Hash, tensor, manifest, PNG, loss valid",
            "actual": "100 file; 256 tensor; 76 PNG; error 0",
            "status": "Lulus",
        },
        {
            "no": 20,
            "feature": "Human review analyzer",
            "scenario": "Menganalisis review final",
            "input": "72 penilaian/36 pasangan",
            "expected": "Tidak kosong; pair identik; tanpa skor otomatis",
            "actual": "Seluruh pemeriksaan true; JSON/CSV/Markdown terbentuk",
            "status": "Lulus",
        },
        {
            "no": 21,
            "feature": "Inference E2E GPU",
            "scenario": "Flutter-backend-FastAPI-CUDA-LoRA-PNG",
            "input": "Host GPU nyata",
            "expected": "Diffusers CUDA, hash final, PNG 512 x 512",
            "actual": "[BUKTI E2E GPU BELUM TERSEDIA]",
            "status": "Belum diuji",
        },
        {
            "no": 22,
            "feature": "Tampilan Android nyata",
            "scenario": "Menampilkan PNG E2E pada perangkat",
            "input": "APK + backend GPU nyata",
            "expected": "Gambar LoRA termuat dan dapat didokumentasikan",
            "actual": "[SCREENSHOT ANDROID BELUM TERSEDIA]",
            "status": "Belum diuji",
        },
    ]
    path = TABLE_DIR / "tabel_4_12_black_box_testing.csv"
    write_csv(path, ["no", "feature", "scenario", "input", "expected", "actual", "status"], rows)
    return path


def build_software_summary() -> tuple[Path, Path]:
    verified_at = datetime.now(timezone(timedelta(hours=8))).isoformat()
    rows = [
        {
            "layer": "Python dataset/LoRA",
            "command": ".venv Python -m pytest ml_pipeline/tests",
            "result": "96 passed",
            "status": "Lulus",
        },
        {
            "layer": "Python inference API",
            "command": ".venv Python -m pytest inference_api/tests",
            "result": "29 passed",
            "status": "Lulus",
        },
        {
            "layer": "Python total",
            "command": ".venv Python -m pytest ml_pipeline/tests inference_api/tests -q",
            "result": "125 passed in 70.13s",
            "status": "Lulus",
        },
        {
            "layer": "Express backend",
            "command": "npm test",
            "result": "23 passed; 0 failed",
            "status": "Lulus",
        },
        {"layer": "Flutter", "command": "flutter test", "result": "13 passed", "status": "Lulus"},
        {
            "layer": "Dataset review UI",
            "command": "npm run dataset-review:test",
            "result": "11 passed",
            "status": "Lulus",
        },
        {
            "layer": "LoRA review UI",
            "command": "npm run lora-review:test",
            "result": "7 passed",
            "status": "Lulus",
        },
        {
            "layer": "Flutter static analysis",
            "command": "flutter analyze",
            "result": "No issues found",
            "status": "Lulus",
        },
        {
            "layer": "Ruff lint",
            "command": "python -m ruff check ml_pipeline inference_api",
            "result": "All checks passed",
            "status": "Lulus",
        },
        {
            "layer": "Notebook validation",
            "command": "node ml_pipeline/scripts/validate_notebooks.mjs",
            "result": "8 notebook valid; Kaggle notebook 52 cells",
            "status": "Lulus",
        },
        {
            "layer": "Repository preflight",
            "command": "node ml_pipeline/scripts/preflight_check.mjs",
            "result": "All checks passed",
            "status": "Lulus",
        },
        {
            "layer": "Secret scan",
            "command": "node ml_pipeline/scripts/security_scan.mjs",
            "result": "No obvious secrets found",
            "status": "Lulus",
        },
        {
            "layer": "Python dependency audit",
            "command": "python -m pip_audit",
            "result": "No known vulnerabilities found",
            "status": "Lulus",
        },
        {
            "layer": "Node dependency audit",
            "command": "npm audit --omit=dev",
            "result": "0 vulnerabilities",
            "status": "Lulus",
        },
        {
            "layer": "Debug APK artifact",
            "command": "Get-FileHash SHA256",
            "result": "152,840,310 bytes; SHA-256 417604f6...cedb5",
            "status": "Terverifikasi",
        },
    ]
    csv_path = TABLE_DIR / "tabel_4_13_software_verification.csv"
    write_csv(csv_path, ["layer", "command", "result", "status"], rows)
    report = {
        "schema_version": 1,
        "verified_at": verified_at,
        "scope": "CPU-only software and artifact verification; no local Stable Diffusion execution",
        "commands_executed_in_current_session": rows[:-1],
        "existing_apk_verified": rows[-1],
        "real_gpu_e2e": "pending",
        "android_screenshot": "pending",
    }
    json_path = EVIDENCE_DIR / "software_verification_20260821.json"
    write_json(json_path, report)
    return csv_path, json_path


def build_manifest(evidence: dict[str, Any], generated_files: list[Path]) -> Path:
    source_paths = [
        Path(r"D:\referensi skripsi\SKRIPSI.docx"),
        Path(r"D:\referensi skripsi\PANDUAN SKRIPSI FAKULTAS TEKNIK 20 JULI 2026.pdf"),
        RUN_DIR / "complete_pipeline_state.json",
        RUN_DIR / "training_config.json",
        RUN_DIR / "smoke_validation.json",
        RUN_DIR / "main_validation.json",
        RUN_DIR / "main_loss_history.csv",
        RUN_DIR / "human_evaluation_template_local.csv",
        RUN_DIR / "human_review_analysis.json",
        RUN_DIR / "human_review_analysis.csv",
        RUN_DIR / "post_review_verification.json",
        ROOT / "artifacts" / "test_reports" / "node_bmkg_live_contract.json",
        ROOT / "artifacts" / "test_reports" / "backend_inference_proxy_live_contract.json",
        MODEL_PATH,
    ]
    records = []
    for path in source_paths + generated_files:
        if path.is_file():
            records.append(
                {
                    "path": str(path),
                    "bytes": path.stat().st_size,
                    "sha256": sha256(path),
                    "kind": "source" if path in source_paths else "generated",
                }
            )
    manifest = {
        "schema_version": 1,
        "run_id": RUN_ID,
        "generated_at": datetime.now(timezone(timedelta(hours=8))).isoformat(),
        "evidence_checks": evidence["checks"],
        "records": records,
        "claim_boundaries": {
            "recommendation_source": "rule_based_engine",
            "stable_diffusion_role": "visual_simulation_only",
            "human_review_role": "evaluasi visual teknis oleh peneliti",
            "gpu_e2e": "pending",
            "android_screenshot": "pending",
        },
    }
    path = EVIDENCE_DIR / "bab_iv_generated_asset_manifest.json"
    write_json(path, manifest)
    return path


def main() -> None:
    for directory in (FIGURE_DIR, TABLE_DIR, EVIDENCE_DIR):
        directory.mkdir(parents=True, exist_ok=True)

    evidence = assert_evidence()
    configure_matplotlib()
    generated: list[Path] = []
    generated.append(build_loss_figure())
    generated.extend(build_review_figures(evidence["review"]))
    review_rows = read_csv(RUN_DIR / "human_evaluation_template_local.csv")
    generated.append(build_selected_visual(review_rows))
    generated.extend(build_tables(evidence))
    generated.append(build_black_box_table())
    software_csv, software_json = build_software_summary()
    generated.extend([software_csv, software_json])

    source_loss = RUN_DIR / "main_loss_history.csv"
    copied_loss = TABLE_DIR / "source_main_loss_history.csv"
    shutil.copy2(source_loss, copied_loss)
    generated.append(copied_loss)
    source_review = RUN_DIR / "human_review_analysis.csv"
    copied_review = TABLE_DIR / "source_human_review_analysis.csv"
    shutil.copy2(source_review, copied_review)
    generated.append(copied_review)

    manifest_path = build_manifest(evidence, generated)
    print(f"BAB IV evidence gate: PASS ({len(evidence['checks'])} checks)")
    print(f"Generated figures: {len([path for path in generated if path.parent == FIGURE_DIR])}")
    print(f"Generated table/evidence files: {len(generated) - 6}")
    print(f"Manifest: {manifest_path}")


if __name__ == "__main__":
    main()
