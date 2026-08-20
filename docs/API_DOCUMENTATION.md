# API Documentation

## Express API (default port 3000)

| Method | Path | Purpose |
| --- | --- | --- |
| GET | `/api/kesehatan` | service health |
| GET | `/api/cuaca/info` | Aikmel region metadata |
| GET | `/api/cuaca/desa` | configured villages |
| GET | `/api/cuaca/{adm4}` | BMKG forecast, rain coverage, timestamp, cache state |
| GET | `/api/rekomendasi/tanaman` | four supported crops |
| POST | `/api/rekomendasi` | manual-category rule decision |
| POST | `/api/rekomendasi/otomatis` | BMKG category plus rule decision |
| POST | `/api/rekomendasi/kalender` | decision plus four-week activity calendar |
| GET | `/api/visual/ready` | private GPU readiness through Express |
| GET | `/api/visual/model-info` | non-secret model identity through Express |
| POST | `/api/visual/generate` | visual generation for a rule-engine result |
| GET | `/api/visual/images/{name}.png` | generated PNG streamed by Express |

Calendar body:

```json
{
  "kodeWilayah": "52.03.09.2002",
  "ketersediaanAir": "cukup",
  "tanamanSebelumnya": "padi",
  "jenisLahan": "sawah"
}
```

An incomplete BMKG precipitation horizon returns HTTP 422 with code
`DATA_CURAH_HUJAN_TIDAK_TERSEDIA`; callers must not substitute zero.

Remote `/api/visual/*` routes require the temporary `X-Client-Token` and apply
a request rate limit. The development profile leaves this disabled. The
complete public payload and error contract is in `docs/API_CONTRACT.md`.

## Private FastAPI (default port 5000)

Endpoints are `GET /health`, `GET /ready`, `GET /v1/model-info`, and
`POST /v1/generate`. Express is its only application caller. With the GPU
profile, every route except `/health` requires `X-Inference-Token`, port 5000
binds to `127.0.0.1`, and the port is not exposed publicly.
The endpoint accepts mutually exclusive `structured_context` (used by Flutter)
and bounded `direct_prompt` (pilot tooling) payloads. Direct prompt mode is
visual-only and does not select a crop recommendation.

## Flutter Configuration

Use `--dart-define-from-file=config/development.example.json` for an emulator,
or create ignored `config/production.local.json` for the controlled RunPod
test. Flutter receives only `BACKEND_API_BASE_URL` and the temporary
`BACKEND_VISUAL_API_TOKEN`; it never receives `INFERENCE_API_BASE_URL` or
`INFERENCE_API_TOKEN`.

The temporary client token is embedded in a test APK and therefore is not a
long-term production credential. Never commit the local config file.
