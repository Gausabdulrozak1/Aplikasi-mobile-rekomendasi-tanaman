# ruff: noqa: F821

SANITY_REQUEST_ID = "kaggle-sidang-sanity-42"
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

# Cell sebelumnya wajib sudah membuktikan tunnel health dan readiness publik.
if public_health.get("status") != "ok":
    raise SystemExit("STOP: health publik belum PASS. Jalankan ulang cell tunnel.")
if public_ready.get("status") != "ready":
    raise SystemExit("STOP: readiness publik belum PASS. Jalankan ulang cell tunnel.")
if CLOUDFLARED_PROCESS.poll() is not None:
    raise SystemExit("STOP: proses Cloudflare tunnel sudah berhenti.")
if not UVICORN_THREAD.is_alive():
    raise SystemExit("STOP: FastAPI lokal sudah berhenti.")


def is_connectivity_error(exc):
    reason = getattr(exc, "reason", exc)
    error_number = getattr(reason, "errno", None)
    return error_number in {-3, 101, 110, 111, 113}


def generate_with_public_first():
    last_error = None
    for attempt in range(1, 7):
        try:
            response = request_json(
                f"{KAGGLE_GPU_URL}/v1/generate",
                token=INFERENCE_API_TOKEN,
                method="POST",
                body=SANITY_PAYLOAD,
                timeout=180,
            )
            return response, "public_tunnel"
        except urllib.error.HTTPError:
            # HTTP error berarti request mencapai server. Jangan disamarkan dengan fallback.
            raise
        except urllib.error.URLError as exc:
            if not is_connectivity_error(exc):
                raise
            last_error = exc
            print(f"Public sanity connectivity retry {attempt}/6")
            time.sleep(min(2 * attempt, 10))

    print(
        "Public self-call unavailable after retries; "
        "running real Diffusers inference through local FastAPI."
    )
    response = request_json(
        f"{LOCAL_URL}/v1/generate",
        token=INFERENCE_API_TOKEN,
        method="POST",
        body=SANITY_PAYLOAD,
        timeout=180,
    )
    return response, f"local_fastapi_after_{type(last_error).__name__}"


sanity_response, SANITY_TRANSPORT = generate_with_public_first()
metadata = sanity_response.get("metadata") or {}
sanity_checks = {
    "success": sanity_response.get("success") is True,
    "request_id": sanity_response.get("request_id") == SANITY_REQUEST_ID,
    "response_crop": sanity_response.get("crop") == "padi",
    "metadata_crop": metadata.get("crop") == "padi",
    "trigger_token": metadata.get("trigger_token") == "taniadaptif_padi",
    "prompt_uses_trigger": "taniadaptif_padi" in str(metadata.get("prompt") or ""),
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


def download_generated_image(base_url):
    image_url = urllib.parse.urljoin(base_url, image_path_from_api)
    image_request = urllib.request.Request(
        image_url,
        headers={
            "Accept": "image/png",
            "User-Agent": "TaniAdaptif-Sidang/1.0",
            "X-Inference-Token": INFERENCE_API_TOKEN,
        },
    )
    with urllib.request.urlopen(image_request, timeout=60) as response:
        return response.headers.get_content_type(), response.read()


image_base_url = KAGGLE_GPU_URL if SANITY_TRANSPORT == "public_tunnel" else LOCAL_URL
try:
    image_content_type, image_bytes = download_generated_image(image_base_url)
except urllib.error.URLError as exc:
    if image_base_url != KAGGLE_GPU_URL or not is_connectivity_error(exc):
        raise
    print("Public image self-download unavailable; reading the same artifact locally.")
    image_content_type, image_bytes = download_generated_image(LOCAL_URL)
    SANITY_TRANSPORT += "+local_image"

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
