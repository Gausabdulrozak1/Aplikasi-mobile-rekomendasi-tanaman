# ruff: noqa: F821

SANITY_REQUEST_ID = "kaggle-sidang-sanity-42"
EXPECTED_SANITY_PROMPT = (
    "taniadaptif_padi, commercial agricultural photograph of a wooden bowl "
    "overflowing with uncooked white rice grains beside bundles of golden rice "
    "panicles, unmistakable rice harvest, paddy field background, realistic "
    "natural daylight"
)
SANITY_PAYLOAD = {
    "crop": "padi",
    "land_type": "sawah",
    "water_availability": "cukup",
    "previous_crop": "jagung",
    "weather_summary": "Cerah berawan; suhu 28 C; kelembaban 78 persen",
    "seed": 42,
    "request_id": SANITY_REQUEST_ID,
    "steps": 15,
    "guidance_scale": 7.5,
    "width": 512,
    "height": 512,
}

# Tunnel sudah dibuktikan lewat /health dan /ready pada cell sebelumnya.
if public_health.get("status") != "ok" or public_ready.get("status") != "ready":
    raise SystemExit("STOP: health/readiness publik belum PASS.")
if CLOUDFLARED_PROCESS.poll() is not None:
    raise SystemExit("STOP: proses Cloudflare tunnel sudah berhenti.")

# Inference dilakukan melalui loopback agar Kaggle tidak perlu memanggil
# Quick Tunnel miliknya sendiri. Ini tetap FastAPI + Diffusers + GPU + LoRA nyata.
local_health = request_json(f"{LOCAL_URL}/health", timeout=5)
local_ready = request_json(
    f"{LOCAL_URL}/ready",
    token=INFERENCE_API_TOKEN,
    timeout=15,
)
if local_health.get("status") != "ok" or local_ready.get("status") != "ready":
    raise SystemExit("STOP: FastAPI lokal tidak sehat sebelum sanity inference.")

sanity_response = request_json(
    f"{LOCAL_URL}/v1/generate",
    token=INFERENCE_API_TOKEN,
    method="POST",
    body=SANITY_PAYLOAD,
    timeout=180,
)

metadata = sanity_response.get("metadata") or {}
sanity_checks = {
    "success": sanity_response.get("success") is True,
    "request_id": sanity_response.get("request_id") == SANITY_REQUEST_ID,
    "response_crop": sanity_response.get("crop") == "padi",
    "metadata_crop": metadata.get("crop") == "padi",
    "trigger_token": metadata.get("trigger_token") == "taniadaptif_padi",
    "final_prompt": metadata.get("prompt") == EXPECTED_SANITY_PROMPT,
    "model": sanity_response.get("model") == BASE_MODEL,
    "provider": metadata.get("provider") == "diffusers",
    "device": metadata.get("device") == "cuda",
    "not_mock": metadata.get("is_mock") is False,
    "lora_sha256": metadata.get("lora_sha256") == LORA_SHA256,
}
if not all(sanity_checks.values()):
    raise SystemExit(
        "STOP: sanity metadata gagal: " + json.dumps(sanity_checks, indent=2)
    )

image_path_from_api = urllib.parse.urlsplit(
    str(sanity_response.get("image_url") or "")
).path
if not image_path_from_api.startswith("/static/generated/"):
    raise SystemExit("STOP: sanity image_url tidak menggunakan static/generated.")

local_image_url = urllib.parse.urljoin(LOCAL_URL, image_path_from_api)
image_request = urllib.request.Request(
    local_image_url,
    headers={
        "Accept": "image/png",
        "User-Agent": "TaniAdaptif-Sidang/1.0",
        "X-Inference-Token": INFERENCE_API_TOKEN,
    },
)
with urllib.request.urlopen(image_request, timeout=60) as response:
    image_content_type = response.headers.get_content_type()
    image_bytes = response.read()

if image_content_type != "image/png" or image_bytes[:8] != b"\x89PNG\r\n\x1a\n":
    raise SystemExit("STOP: sanity artifact bukan PNG valid.")
if len(image_bytes) < 24 or image_bytes[12:16] != b"IHDR":
    raise SystemExit("STOP: sanity PNG tidak memiliki IHDR valid.")

width = int.from_bytes(image_bytes[16:20], "big")
height = int.from_bytes(image_bytes[20:24], "big")
if (width, height) != (512, 512):
    raise SystemExit(f"STOP: dimensi sanity PNG salah: {width}x{height}")
if CLOUDFLARED_PROCESS.poll() is not None:
    raise SystemExit("STOP: tunnel berhenti selama sanity inference.")

SANITY_TRANSPORT = "local_fastapi_real_diffusers_after_public_tunnel_check"
SANITY_PATH = WORK_ROOT / "sanity_inference.png"
SANITY_PATH.write_bytes(image_bytes)
SANITY_SHA256 = hashlib.sha256(image_bytes).hexdigest()

print("Sanity inference PNG: PASS")
print("Sanity transport:", SANITY_TRANSPORT)
print("Sanity path:", SANITY_PATH)
print("Sanity bytes:", len(image_bytes))
print("Sanity SHA-256:", SANITY_SHA256)
print("FASTAPI_SELECTED_CROP=padi")
print("TRIGGER_TOKEN=taniadaptif_padi")
print("FINAL_PROMPT=" + EXPECTED_SANITY_PROMPT)
