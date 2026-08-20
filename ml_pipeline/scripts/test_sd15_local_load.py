from __future__ import annotations

import argparse
import gc
import importlib.metadata
import json
import platform
import time
import traceback
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from check_directml import memory_snapshot

MODEL_ID = "stable-diffusion-v1-5/stable-diffusion-v1-5"
MIB = 1024**2
BASE_HEADROOM_BYTES = 512 * MIB
WEIGHT_LOAD_MULTIPLIER = 2.5


def package_version(name: str) -> str | None:
    try:
        return importlib.metadata.version(name)
    except importlib.metadata.PackageNotFoundError:
        return None


def component_weight_sizes(model_info: Any) -> dict[str, int | None]:
    prefixes = {
        "text_encoder": "text_encoder/",
        "vae": "vae/",
        "unet": "unet/",
    }
    sizes: dict[str, int | None] = {name: None for name in prefixes}
    preferred_suffixes = (".safetensors", ".bin")
    for component, prefix in prefixes.items():
        candidates = []
        for sibling in model_info.siblings:
            filename = sibling.rfilename
            size = getattr(sibling, "size", None)
            if filename.startswith(prefix) and filename.endswith(preferred_suffixes) and size:
                candidates.append((filename.endswith(".safetensors"), int(size), filename))
        if candidates:
            candidates.sort(reverse=True)
            sizes[component] = candidates[0][1]
    return sizes


def required_available_bytes(weight_bytes: int | None, fallback_gib: float) -> int:
    if weight_bytes:
        return int(weight_bytes * WEIGHT_LOAD_MULTIPLIER + BASE_HEADROOM_BYTES)
    return int(fallback_gib * 1024**3)


def stage_record(name: str, required_bytes: int) -> dict[str, Any]:
    return {
        "name": name,
        "status": "not_run",
        "required_available_bytes": required_bytes,
        "memory_before": None,
        "memory_after": None,
        "elapsed_seconds": None,
        "error": None,
        "traceback": None,
        "details": {},
    }


def memory_allows(stage: dict[str, Any]) -> bool:
    snapshot = memory_snapshot()
    stage["memory_before"] = snapshot
    available = snapshot.get("available_physical_bytes") or 0
    if available < stage["required_available_bytes"]:
        stage["status"] = "blocked_memory"
        stage["error"] = (
            f"Available RAM {available} bytes is below the safety threshold "
            f"{stage['required_available_bytes']} bytes"
        )
        stage["memory_after"] = snapshot
        return False
    return True


def finish_stage(stage: dict[str, Any], started: float) -> None:
    stage["elapsed_seconds"] = time.perf_counter() - started
    stage["memory_after"] = memory_snapshot()


def load_tokenizer(stage: dict[str, Any], cache_dir: Path) -> bool:
    if not memory_allows(stage):
        return False
    started = time.perf_counter()
    try:
        from transformers import CLIPTokenizer

        tokenizer = CLIPTokenizer.from_pretrained(
            MODEL_ID,
            subfolder="tokenizer",
            cache_dir=cache_dir,
        )
        tokens = tokenizer("a field of rice", return_tensors="pt")
        stage["details"] = {
            "class": type(tokenizer).__name__,
            "vocab_size": tokenizer.vocab_size,
            "token_shape": list(tokens.input_ids.shape),
        }
        stage["status"] = "passed"
        del tokens, tokenizer
        gc.collect()
    except Exception as exc:
        stage["status"] = "failed"
        stage["error"] = f"{type(exc).__name__}: {exc}"
        stage["traceback"] = traceback.format_exc()
    finally:
        finish_stage(stage, started)
    return stage["status"] == "passed"


def load_text_encoder(stage: dict[str, Any], cache_dir: Path) -> bool:
    if not memory_allows(stage):
        return False
    started = time.perf_counter()
    try:
        import torch
        from transformers import CLIPTextModel

        model = CLIPTextModel.from_pretrained(
            MODEL_ID,
            subfolder="text_encoder",
            cache_dir=cache_dir,
            torch_dtype=torch.float32,
            low_cpu_mem_usage=True,
        )
        stage["details"] = {
            "class": type(model).__name__,
            "dtype": str(model.dtype),
            "parameter_count": sum(parameter.numel() for parameter in model.parameters()),
        }
        stage["status"] = "passed"
        del model
        gc.collect()
    except Exception as exc:
        stage["status"] = "failed"
        stage["error"] = f"{type(exc).__name__}: {exc}"
        stage["traceback"] = traceback.format_exc()
    finally:
        finish_stage(stage, started)
    return stage["status"] == "passed"


def load_diffusers_component(
    stage: dict[str, Any], cache_dir: Path, class_name: str, subfolder: str
) -> bool:
    if not memory_allows(stage):
        return False
    started = time.perf_counter()
    try:
        import torch
        from diffusers import AutoencoderKL, UNet2DConditionModel

        component_class = {
            "AutoencoderKL": AutoencoderKL,
            "UNet2DConditionModel": UNet2DConditionModel,
        }[class_name]
        model = component_class.from_pretrained(
            MODEL_ID,
            subfolder=subfolder,
            cache_dir=cache_dir,
            torch_dtype=torch.float32,
            low_cpu_mem_usage=True,
        )
        stage["details"] = {
            "class": type(model).__name__,
            "dtype": str(model.dtype),
            "parameter_count": sum(parameter.numel() for parameter in model.parameters()),
        }
        stage["status"] = "passed"
        del model
        gc.collect()
    except Exception as exc:
        stage["status"] = "failed"
        stage["error"] = f"{type(exc).__name__}: {exc}"
        stage["traceback"] = traceback.format_exc()
    finally:
        finish_stage(stage, started)
    return stage["status"] == "passed"


def mark_following_blocked(stages: list[dict[str, Any]], blocker: str) -> None:
    blocked_seen = False
    for stage in stages:
        if stage["name"] == blocker:
            blocked_seen = True
            continue
        if blocked_seen and stage["status"] == "not_run":
            stage["status"] = "blocked_by_previous_stage"
            stage["error"] = f"Previous required stage did not pass: {blocker}"


def write_reports(report: dict[str, Any], output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "sd15_load_test.json").write_text(
        json.dumps(report, indent=2), encoding="utf-8"
    )
    lines = [
        "# SD 1.5 Local Load Test",
        "",
        f"- Status: `{report['status']}`",
        f"- Model: `{report['model_id']}`",
        f"- Timestamp UTC: `{report['timestamp_utc']}`",
        f"- Cache: `{report['cache_dir']}`",
        "- Safety formula: `2.5 * selected component weight bytes + 512 MiB`",
        "",
        "## Stages",
        "",
        "| Stage | Status | Required RAM bytes | Before | After | Seconds |",
        "| --- | --- | ---: | ---: | ---: | ---: |",
    ]
    for stage in report["stages"]:
        before = (stage.get("memory_before") or {}).get("available_physical_bytes")
        after = (stage.get("memory_after") or {}).get("available_physical_bytes")
        lines.append(
            f"| {stage['name']} | {stage['status']} | {stage['required_available_bytes']} | "
            f"{before} | {after} | {stage['elapsed_seconds']} |"
        )
    lines.extend(["", "## Errors and blockers", ""])
    for stage in report["stages"]:
        lines.append(f"- `{stage['name']}`: {stage.get('error') or 'none'}")
    lines.extend(
        [
            "",
            "No full pipeline or training was started by this test.",
            "",
        ]
    )
    (output_dir / "sd15_load_test.md").write_text("\n".join(lines), encoding="utf-8")


def run_test(cache_dir: Path) -> dict[str, Any]:
    report: dict[str, Any] = {
        "schema_version": 1,
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "status": "failed",
        "model_id": MODEL_ID,
        "cache_dir": str(cache_dir.resolve()),
        "python_version": platform.python_version(),
        "dependencies": {
            name: package_version(name)
            for name in (
                "torch",
                "torch-directml",
                "diffusers",
                "transformers",
                "accelerate",
                "safetensors",
                "peft",
                "huggingface_hub",
            )
        },
        "model_metadata_error": None,
        "component_weight_bytes": {},
        "stages": [],
        "memory_initial": memory_snapshot(),
        "memory_final": None,
    }

    cache_dir.mkdir(parents=True, exist_ok=True)
    try:
        from huggingface_hub import HfApi

        info = HfApi().model_info(MODEL_ID, files_metadata=True)
        sizes = component_weight_sizes(info)
    except Exception as exc:
        sizes = {"text_encoder": None, "vae": None, "unet": None}
        report["model_metadata_error"] = f"{type(exc).__name__}: {exc}"
    report["component_weight_bytes"] = sizes

    stages = [
        stage_record("tokenizer", 512 * MIB),
        stage_record("text_encoder", required_available_bytes(sizes["text_encoder"], 2.0)),
        stage_record("vae", required_available_bytes(sizes["vae"], 2.0)),
        stage_record("unet", required_available_bytes(sizes["unet"], 4.5)),
        stage_record("tiny_inference", 5 * 1024**3),
    ]
    report["stages"] = stages

    if not load_tokenizer(stages[0], cache_dir):
        mark_following_blocked(stages, "tokenizer")
    elif not load_text_encoder(stages[1], cache_dir):
        mark_following_blocked(stages, "text_encoder")
    elif not load_diffusers_component(stages[2], cache_dir, "AutoencoderKL", "vae"):
        mark_following_blocked(stages, "vae")
    elif not load_diffusers_component(stages[3], cache_dir, "UNet2DConditionModel", "unet"):
        mark_following_blocked(stages, "unet")
    else:
        stages[4]["status"] = "not_implemented_after_component_gate"
        stages[4]["error"] = "Full-pipeline inference requires a separate explicit implementation."

    if all(stage["status"] == "passed" for stage in stages[:4]):
        report["status"] = "components_passed"
    elif any(stage["status"] == "blocked_memory" for stage in stages):
        report["status"] = "blocked_memory"
    else:
        report["status"] = "failed"
    report["memory_final"] = memory_snapshot()
    return report


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Progressive, memory-gated SD 1.5 load test.")
    parser.add_argument("--output-dir", type=Path, default=Path("artifacts/local_ml"))
    parser.add_argument(
        "--cache-dir", type=Path, default=Path("artifacts/local_ml/hf_cache")
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    report = run_test(args.cache_dir)
    write_reports(report, args.output_dir)
    print(json.dumps(report, indent=2))
    return 0 if report["status"] == "components_passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
