# ruff: noqa: F821

EXPECTED_TRIGGER_TOKENS = {
    "padi": "taniadaptif_padi",
    "jagung": "taniadaptif_jagung",
    "cabai": "taniadaptif_cabai",
    "kacang_tanah": "taniadaptif_kacang_tanah",
}

# Gunakan loopback untuk menghindari Kaggle self-call ke Quick Tunnel.
model_info = request_json(
    f"{LOCAL_URL}/v1/model-info",
    token=INFERENCE_API_TOKEN,
    timeout=20,
)
if not (
    model_info.get("base_model") == BASE_MODEL
    and model_info.get("lora_identifier") == LORA_IDENTIFIER
    and model_info.get("provider") == "diffusers"
    and model_info.get("trigger_tokens") == EXPECTED_TRIGGER_TOKENS
):
    raise SystemExit(
        "STOP: model-info tidak sesuai model final: "
        + json.dumps(model_info, indent=2)
    )

final_local_health = request_json(f"{LOCAL_URL}/health", timeout=5)
final_local_ready = request_json(
    f"{LOCAL_URL}/ready",
    token=INFERENCE_API_TOKEN,
    timeout=15,
)
if final_local_health.get("status") != "ok" or final_local_ready.get("status") != "ready":
    raise SystemExit("STOP: FastAPI tidak sehat pada final gate.")
if public_health.get("status") != "ok" or public_ready.get("status") != "ready":
    raise SystemExit("STOP: bukti health/readiness publik tidak valid.")
if CLOUDFLARED_PROCESS.poll() is not None:
    raise SystemExit("STOP: proses Cloudflare tunnel sudah berhenti.")
if not SANITY_PATH.is_file() or SANITY_PATH.stat().st_size != len(image_bytes):
    raise SystemExit("STOP: artifact sanity final hilang atau ukurannya berubah.")

STATE_PATH = WORK_ROOT / "kaggle_live_inference_state.json"
state = {
    "status": "success",
    "training_performed": False,
    "gpu": gpu.name,
    "fastapi_port": FASTAPI_PORT,
    "kaggle_gpu_url": KAGGLE_GPU_URL,
    "health": public_health,
    "ready": public_ready,
    "base_model": BASE_MODEL,
    "lora_identifier": LORA_IDENTIFIER,
    "lora_sha256": LORA_SHA256,
    "trigger_tokens": EXPECTED_TRIGGER_TOKENS,
    "sanity_inference": {
        "status": "success",
        "transport": SANITY_TRANSPORT,
        "crop": "padi",
        "trigger_token": "taniadaptif_padi",
        "path": str(SANITY_PATH),
        "sha256": SANITY_SHA256,
        "bytes": len(image_bytes),
        "width": width,
        "height": height,
    },
    "secret_names": ["INFERENCE_API_TOKEN", "HF_TOKEN (optional)"],
    "secret_values_recorded": False,
}
STATE_PATH.write_text(json.dumps(state, indent=2) + "\n", encoding="utf-8")

print("GPU=" + gpu.name)
print("FASTAPI_PORT=" + str(FASTAPI_PORT))
print("SECRET_NAMES=INFERENCE_API_TOKEN,HF_TOKEN(optional)")
print("KAGGLE_GPU_URL=" + KAGGLE_GPU_URL)
print("HEALTH=PASS")
print("MODEL_INFO=PASS")
print("TRIGGER_MAPPING=PASS")
print("SANITY_INFERENCE=PASS")
print("STATUS=READY_FOR_SIDANG")
