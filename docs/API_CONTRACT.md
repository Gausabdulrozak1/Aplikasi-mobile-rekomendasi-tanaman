# Visual Inference API Contract

## Public Application Boundary

Flutter communicates only with the Express backend. Development API base URL:
`http://localhost:3000/api`. A deployed Android build uses the HTTPS URL in
`BACKEND_API_BASE_URL`.

The remote testing profile requires `X-Client-Token` on every `/api/visual/*`
request, including image download. Flutter reads this temporary token from
`BACKEND_VISUAL_API_TOKEN` at build time. This is appropriate for a controlled
thesis test, but an APK token is not a substitute for user authentication in a
public production service.

| Method | Public path | Purpose |
| --- | --- | --- |
| GET | `/api/visual/ready` | GPU provider readiness through the backend |
| GET | `/api/visual/model-info` | non-secret model and LoRA identity |
| POST | `/api/visual/generate` | create a visual for an existing recommendation |
| GET | `/api/visual/images/{name}.png` | stream the generated PNG through the backend |

The backend enforces a configurable rate limit and never returns the private
FastAPI host or its token.

## Generate Visual

`POST /api/visual/generate` accepts the result context of the rule engine:

```json
{
  "selected_crop": "padi",
  "land_type": "sawah",
  "water_availability": "cukup",
  "previous_crop": "jagung",
  "weather_summary": "Cerah berawan; suhu 28 C; kelembaban 78 persen",
  "seed": 42,
  "request_id": "flutter-padi-001",
  "steps": 25,
  "guidance_scale": 7.5,
  "width": 512,
  "height": 512
}
```

The inference service does not choose a crop. Flutter requires the user to
select exactly one item from the rule-engine recommendations and sends it as
`selected_crop`: `padi`, `jagung`, `cabai`, or `kacang_tanah`. Express validates
and normalizes that scalar, then maps it to the private FastAPI `crop` field.
FastAPI builds the visual prompt with the matching `taniadaptif_*` trigger.
Arrays and conflicting `selected_crop`/legacy `crop` values are rejected.

Successful public response:

```json
{
  "success": true,
  "request_id": "flutter-padi-001",
  "selected_crop": "padi",
  "crop": "padi",
  "image_url": "https://pod-id-3000.proxy.runpod.net/api/visual/images/sd15_flutter-padi-001.png",
  "image_id": "sd15_flutter-padi-001",
  "seed": 42,
  "generation_time_seconds": 4.25,
  "model": "stable-diffusion-v1-5/stable-diffusion-v1-5",
  "metadata": {
    "provider": "diffusers",
    "device": "cuda",
    "is_mock": false,
    "lora_identifier": "multisource_multicrop_lora_sd15_20260820T143551Z",
    "lora_sha256": "0bda8908d577513110c22cf5ec1b8a7e008d2b26dd90525732a5c4e4b1bdd43a",
    "delivery_path": "backend_proxy",
    "upstream_image_url_exposed": false
  }
}
```

Structured error response:

```json
{
  "success": false,
  "request_id": "flutter-padi-001",
  "error": {
    "code": "INFERENCE_TIMEOUT",
    "message": "Layanan GPU melewati batas waktu backend.",
    "retryable": true
  }
}
```

Validation failures use HTTP 422, client authentication uses 401, rate limiting
uses 429, timeout uses 504, and provider failure uses 503. `request_id` allows
letters, numbers, dot, dash, and underscore, up to 64 characters. Seed range is
0-2147483647; steps 1-50; guidance 1.0-15.0; dimensions are 256-768 in
multiples of 64.

## Private GPU Boundary

FastAPI binds to `127.0.0.1:5000` in the single-Pod deployment and is not an
exposed RunPod HTTP port. Express alone calls:

| Method | Private path |
| --- | --- |
| GET | `/health` |
| GET | `/ready` |
| GET | `/v1/model-info` |
| POST | `/v1/generate` |
| GET | `/static/generated/{name}.png` |

Except for liveness `/health`, these routes require `X-Inference-Token`. The
value is held by the backend and FastAPI environment only. It must never be put
in Flutter configuration or a screenshot.

The private structured request retains the field name `crop` for backward
compatibility. Express is the sole translation boundary from public
`selected_crop` to private `crop`; the value must remain identical in the
FastAPI response metadata and prompt trigger.

Pilot tooling may send a bounded direct-prompt payload to the private generate
contract through an authorized backend test. That mode only creates a visual;
it does not select or alter an agronomic recommendation.

## Evidence Gate

Mock responses use `provider=mock`, `is_mock=true`, and are development-only.
Real end-to-end success is valid only when
`inference_api/scripts/e2e_probe.py` records all checks as true, including
`provider=diffusers`, `device=cuda`, `is_mock=false`, the exact final LoRA hash,
the backend image route, and a valid 512 x 512 PNG.
