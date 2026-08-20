from __future__ import annotations

import argparse
import importlib.metadata
import json
import os
import platform
import sys
import tempfile
from datetime import UTC, datetime
from pathlib import Path

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
if str(REPOSITORY_ROOT) not in sys.path:
    sys.path.insert(0, str(REPOSITORY_ROOT))

from inference_api.app.core.config import Settings  # noqa: E402
from inference_api.app.providers.lora_validation import validate_lora_artifact  # noqa: E402

EXPECTED_BASE_MODEL = "stable-diffusion-v1-5/stable-diffusion-v1-5"
EXPECTED_LORA_SHA256 = "0bda8908d577513110c22cf5ec1b8a7e008d2b26dd90525732a5c4e4b1bdd43a"
EXPECTED_LORA_IDENTIFIER = "multisource_multicrop_lora_sd15_20260820T143551Z"
EXPECTED_PACKAGES = {
    "diffusers": "0.35.1",
    "transformers": "4.57.6",
    "accelerate": "1.14.0",
    "peft": "0.20.0",
    "safetensors": "0.8.0",
}


def _write_json(path: Path, payload: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(f"{path.suffix}.tmp")
    temporary.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    temporary.replace(path)


def _package_versions() -> dict[str, str]:
    return {name: importlib.metadata.version(name) for name in EXPECTED_PACKAGES}


def _writable_directory(path: Path) -> bool:
    path.mkdir(parents=True, exist_ok=True)
    try:
        with tempfile.NamedTemporaryFile(dir=path, prefix="preflight_", delete=True):
            pass
    except OSError:
        return False
    return True


def run_preflight(output_path: Path) -> int:
    checks: dict[str, bool] = {}
    details: dict[str, object] = {}
    error: str | None = None

    try:
        settings = Settings()
        checks["python_3_11_or_newer"] = sys.version_info >= (3, 11)
        checks["provider_is_diffusers"] = settings.provider.casefold() == "diffusers"
        checks["gpu_is_required"] = settings.require_gpu
        checks["private_token_is_required"] = settings.require_api_token
        checks["private_token_is_configured"] = len(
            settings.api_token
        ) >= 32 and not settings.api_token.strip().casefold().startswith("replace-with")
        checks["base_model_matches_final_config"] = settings.base_model == EXPECTED_BASE_MODEL
        checks["lora_identifier_matches_final_run"] = (
            settings.lora_identifier == EXPECTED_LORA_IDENTIFIER
        )
        checks["generation_timeout_below_runpod_proxy_limit"] = (
            1 <= settings.generation_timeout_seconds <= 85
        )
        checks["generated_directory_is_writable"] = _writable_directory(settings.generated_dir)

        artifact = validate_lora_artifact(settings.lora_path, settings.lora_sha256)
        checks["lora_sha256_matches_final_model"] = artifact.sha256 == EXPECTED_LORA_SHA256
        checks["lora_contains_tensor_data"] = artifact.tensor_count > 0 and artifact.data_bytes > 0

        import torch

        checks["cuda_available"] = torch.cuda.is_available()
        checks["cuda_device_present"] = torch.cuda.device_count() >= 1
        if torch.cuda.is_available():
            properties = torch.cuda.get_device_properties(0)
            total_vram_bytes = int(properties.total_memory)
            details["gpu"] = {
                "name": properties.name,
                "count": torch.cuda.device_count(),
                "total_vram_bytes": total_vram_bytes,
                "total_vram_gib": round(total_vram_bytes / (1024**3), 2),
                "cuda_runtime": torch.version.cuda,
                "torch_version": torch.__version__,
            }
            checks["gpu_has_at_least_12_gib_vram"] = total_vram_bytes >= 12 * 1024**3
        else:
            details["gpu"] = {"name": None, "count": torch.cuda.device_count()}
            checks["gpu_has_at_least_12_gib_vram"] = False

        versions = _package_versions()
        details["packages"] = versions
        checks["dependency_versions_match"] = all(
            versions[name] == expected for name, expected in EXPECTED_PACKAGES.items()
        )
        details["lora"] = artifact.to_dict()
        details["generated_dir"] = str(settings.generated_dir.resolve())
        details["hf_home"] = os.environ.get("HF_HOME")
    except Exception as exc:  # report the real deployment error without masking it
        error = f"{type(exc).__name__}: {exc}"

    success = error is None and bool(checks) and all(checks.values())
    report: dict[str, object] = {
        "schema_version": 1,
        "status": "success" if success else "failed",
        "scope": "gpu_environment_and_final_lora_preflight_without_model_generation",
        "generated_at_utc": datetime.now(UTC).isoformat(),
        "host": {
            "platform": platform.platform(),
            "python": platform.python_version(),
        },
        "expected": {
            "base_model": EXPECTED_BASE_MODEL,
            "lora_identifier": EXPECTED_LORA_IDENTIFIER,
            "lora_sha256": EXPECTED_LORA_SHA256,
        },
        "checks": checks,
        "details": details,
        "error": error,
        "training_performed": False,
        "stable_diffusion_loaded_by_this_check": False,
    }
    _write_json(output_path, report)
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if success else 1


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate the remote GPU runtime before startup.")
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("artifacts/deployment/gpu_preflight.json"),
    )
    args = parser.parse_args()
    return run_preflight(args.output)


if __name__ == "__main__":
    raise SystemExit(main())
