from __future__ import annotations

import argparse
import hashlib
import json
import os
import struct
import sys
import urllib.error
import urllib.request
from datetime import UTC, datetime
from pathlib import Path
from urllib.parse import urlsplit

EXPECTED_BASE_MODEL = "stable-diffusion-v1-5/stable-diffusion-v1-5"
EXPECTED_LORA_SHA256 = "0bda8908d577513110c22cf5ec1b8a7e008d2b26dd90525732a5c4e4b1bdd43a"
EXPECTED_LORA_IDENTIFIER = "multisource_multicrop_lora_sd15_20260820T143551Z"
PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"


class ProbeError(RuntimeError):
    pass


def normalize_backend_api_url(raw_url: str, allow_http: bool = False) -> str:
    parsed = urlsplit(raw_url.strip())
    if not parsed.scheme or not parsed.netloc or parsed.username or parsed.password:
        raise ProbeError("BACKEND_API_BASE_URL must be an absolute URL without credentials.")
    if parsed.query or parsed.fragment:
        raise ProbeError("BACKEND_API_BASE_URL must not contain query parameters or fragments.")
    if parsed.scheme != "https" and not allow_http:
        raise ProbeError("Real end-to-end evidence requires an HTTPS backend URL.")
    if parsed.scheme not in {"http", "https"}:
        raise ProbeError("BACKEND_API_BASE_URL must use HTTP or HTTPS.")
    path = parsed.path.rstrip("/")
    if not path.endswith("/api"):
        path = f"{path}/api"
    return parsed._replace(path=path, query="", fragment="").geturl()


def inspect_png(payload: bytes) -> dict[str, int]:
    if len(payload) < 24 or payload[:8] != PNG_SIGNATURE or payload[12:16] != b"IHDR":
        raise ProbeError("Generated artifact is not a structurally recognizable PNG.")
    width, height = struct.unpack(">II", payload[16:24])
    if width <= 0 or height <= 0:
        raise ProbeError("Generated PNG has invalid dimensions.")
    return {"width": width, "height": height, "size_bytes": len(payload)}


def _read_json(response: object) -> dict[str, object]:
    payload = json.loads(response.read().decode("utf-8"))
    if not isinstance(payload, dict):
        raise ProbeError("API response is not a JSON object.")
    return payload


def _request_json(
    method: str,
    url: str,
    token: str,
    *,
    body: dict[str, object] | None = None,
    timeout: float,
) -> dict[str, object]:
    headers = {
        "Accept": "application/json",
        "User-Agent": "TaniAdaptif-E2E-Probe/1.0",
        "X-Client-Token": token,
    }
    encoded = None
    if body is not None:
        encoded = json.dumps(body).encode("utf-8")
        headers["Content-Type"] = "application/json"
    request = urllib.request.Request(url, data=encoded, headers=headers, method=method)
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return _read_json(response)
    except urllib.error.HTTPError as exc:
        response_body = exc.read().decode("utf-8", errors="replace")[:2000]
        raise ProbeError(f"HTTP {exc.code} from {url}: {response_body}") from exc
    except (urllib.error.URLError, TimeoutError) as exc:
        raise ProbeError(f"Cannot reach {url}: {exc}") from exc


def _request_image(url: str, token: str, timeout: float) -> tuple[bytes, str]:
    request = urllib.request.Request(
        url,
        headers={
            "Accept": "image/png",
            "User-Agent": "TaniAdaptif-E2E-Probe/1.0",
            "X-Client-Token": token,
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return response.read(), response.headers.get_content_type()
    except urllib.error.HTTPError as exc:
        raise ProbeError(f"HTTP {exc.code} while downloading the generated image.") from exc
    except (urllib.error.URLError, TimeoutError) as exc:
        raise ProbeError(f"Cannot download the generated image: {exc}") from exc


def _write_json(path: Path, payload: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(f"{path.suffix}.tmp")
    temporary.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    temporary.replace(path)


def run_probe(
    backend_api_url: str,
    client_token: str,
    output_dir: Path,
    *,
    timeout: float,
    allow_http: bool,
) -> int:
    generated_at = datetime.now(UTC)
    run_id = generated_at.strftime("%Y%m%dT%H%M%SZ")
    report_path = output_dir / "real_inference_e2e_report.json"
    image_path = output_dir / f"real_inference_{run_id}.png"
    checks: dict[str, bool] = {}
    evidence: dict[str, object] = {}
    error: str | None = None

    try:
        api_url = normalize_backend_api_url(backend_api_url, allow_http=allow_http)
        if len(client_token) < 32:
            raise ProbeError("BACKEND_VISUAL_API_TOKEN must contain at least 32 characters.")

        health = _request_json("GET", f"{api_url}/kesehatan", client_token, timeout=timeout)
        checks["backend_health_is_good"] = health.get("status") == "baik"

        ready = _request_json("GET", f"{api_url}/visual/ready", client_token, timeout=timeout)
        checks["inference_ready"] = ready.get("status") == "ready"
        checks["provider_is_diffusers"] = ready.get("provider") == "diffusers"
        checks["device_is_cuda"] = ready.get("device") == "cuda"
        checks["model_is_loaded"] = ready.get("model_loaded") is True

        model_info = _request_json(
            "GET", f"{api_url}/visual/model-info", client_token, timeout=timeout
        )
        checks["base_model_matches"] = model_info.get("base_model") == EXPECTED_BASE_MODEL
        checks["lora_identifier_matches"] = (
            model_info.get("lora_identifier") == EXPECTED_LORA_IDENTIFIER
        )
        checks["model_info_provider_is_diffusers"] = model_info.get("provider") == "diffusers"

        recommendation = _request_json(
            "POST",
            f"{api_url}/rekomendasi",
            client_token,
            body={
                "curahHujan": "sedang",
                "ketersediaanAir": "cukup",
                "tanamanSebelumnya": "jagung",
                "jenisLahan": "sawah",
            },
            timeout=timeout,
        )
        recommended_crop = str(recommendation.get("recommendedCrop") or "")
        checks["rule_engine_succeeded"] = recommendation.get("status") == "berhasil"
        checks["rule_engine_returned_supported_crop"] = recommended_crop in {
            "padi",
            "jagung",
            "cabai",
            "kacang_tanah",
        }

        request_id = f"real-e2e-{run_id}"
        generation = _request_json(
            "POST",
            f"{api_url}/visual/generate",
            client_token,
            body={
                "crop": recommended_crop,
                "land_type": "sawah",
                "water_availability": "cukup",
                "previous_crop": "jagung",
                "weather_summary": "Cerah berawan; suhu 28 C; kelembaban 78 persen",
                "seed": 42,
                "request_id": request_id,
                "steps": 25,
                "guidance_scale": 7.5,
                "width": 512,
                "height": 512,
            },
            timeout=timeout,
        )
        metadata = generation.get("metadata")
        if not isinstance(metadata, dict):
            raise ProbeError("Generation response metadata is missing.")
        checks["generation_succeeded"] = generation.get("success") is True
        checks["request_id_preserved"] = generation.get("request_id") == request_id
        checks["generation_uses_rule_engine_crop"] = generation.get("crop") == recommended_crop
        checks["generation_model_matches"] = generation.get("model") == EXPECTED_BASE_MODEL
        checks["generated_by_diffusers"] = metadata.get("provider") == "diffusers"
        checks["generated_on_cuda"] = metadata.get("device") == "cuda"
        checks["output_is_not_mock"] = metadata.get("is_mock") is False
        checks["final_lora_sha256_matches"] = metadata.get("lora_sha256") == EXPECTED_LORA_SHA256
        checks["delivery_uses_backend_proxy"] = metadata.get("delivery_path") == "backend_proxy"
        checks["upstream_url_is_hidden"] = metadata.get("upstream_image_url_exposed") is False

        image_url = str(generation.get("image_url") or "")
        expected_origin = urlsplit(api_url)
        actual_image_url = urlsplit(image_url)
        checks["image_url_uses_backend_origin"] = (
            actual_image_url.scheme == expected_origin.scheme
            and actual_image_url.netloc == expected_origin.netloc
        )
        checks["image_url_uses_backend_route"] = actual_image_url.path.startswith(
            f"{expected_origin.path}/visual/images/"
        )
        image, content_type = _request_image(image_url, client_token, timeout)
        image_info = inspect_png(image)
        checks["image_content_type_is_png"] = content_type == "image/png"
        checks["image_dimensions_are_512"] = (
            image_info["width"] == 512 and image_info["height"] == 512
        )
        image_path.parent.mkdir(parents=True, exist_ok=True)
        image_path.write_bytes(image)
        evidence = {
            "backend_health": health,
            "readiness": ready,
            "model_info": model_info,
            "recommendation": recommendation,
            "generation": generation,
            "image": {
                **image_info,
                "content_type": content_type,
                "path": str(image_path.resolve()),
                "sha256": hashlib.sha256(image).hexdigest(),
            },
        }
    except Exception as exc:  # preserve the real failing boundary in the report
        error = f"{type(exc).__name__}: {exc}"

    success = error is None and bool(checks) and all(checks.values())
    report: dict[str, object] = {
        "schema_version": 1,
        "status": "success" if success else "failed",
        "scope": "real_rule_engine_backend_to_gpu_contract_probe_for_flutter",
        "generated_at_utc": generated_at.isoformat(),
        "backend_api_url": backend_api_url,
        "expected": {
            "base_model": EXPECTED_BASE_MODEL,
            "lora_identifier": EXPECTED_LORA_IDENTIFIER,
            "lora_sha256": EXPECTED_LORA_SHA256,
            "provider": "diffusers",
            "device": "cuda",
            "is_mock": False,
        },
        "checks": checks,
        "evidence": evidence,
        "error": error,
        "client_token_recorded": False,
        "training_performed": False,
        "automatic_quality_score_created": False,
    }
    _write_json(report_path, report)
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if success else 1


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Probe the real public backend-to-GPU image generation path."
    )
    parser.add_argument(
        "--backend-api-url",
        default=os.environ.get("BACKEND_API_BASE_URL", ""),
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("artifacts/e2e_inference/latest"),
    )
    parser.add_argument("--timeout", type=float, default=95.0)
    parser.add_argument(
        "--allow-http",
        action="store_true",
        help="Reserved for localhost contract tests; real evidence requires HTTPS.",
    )
    args = parser.parse_args()
    if not args.backend_api_url:
        print("BACKEND_API_BASE_URL or --backend-api-url is required.", file=sys.stderr)
        return 2
    return run_probe(
        args.backend_api_url,
        os.environ.get("BACKEND_VISUAL_API_TOKEN", ""),
        args.output_dir,
        timeout=args.timeout,
        allow_http=args.allow_http,
    )


if __name__ == "__main__":
    raise SystemExit(main())
