# TaniAdaptif Inference API

FastAPI service for visual simulation. The default `mock` provider runs safely
on CPU and marks every placeholder as non-research output. Crop recommendation
always remains in the Express rule engine.

## Local Setup

```powershell
cd D:\TaniAdaptif
.\.venv\Scripts\python.exe -m pip install -r inference_api\requirements.txt
.\.venv\Scripts\python.exe -m uvicorn inference_api.app.main:app --host 127.0.0.1 --port 5000
```

Endpoints: `/health`, `/ready`, `/v1/model-info`, `/v1/generate`, and `/docs`.
Generate accepts structured crop/land/water/previous-crop/weather context. The
server builds prompts with final `taniadaptif_*` triggers and returns request ID,
seed, model, provider, and output provenance.

For the one-class public-padi pilot, `/v1/generate` also accepts a bounded
direct prompt using `gaus_padi_public`. This compatibility mode is marked
`request_mode=direct_prompt` and never chooses a recommendation. Flutter uses
the structured mode only.

Flutter does not call these routes directly. Express owns the public
`/api/visual/*` contract, forwards a private `X-Inference-Token`, and streams
generated PNGs back to Android.

## Tests

```powershell
.\.venv\Scripts\python.exe -m pytest inference_api\tests -q
.\.venv\Scripts\python.exe -m ruff check inference_api
```

The Diffusers provider is prepared for an authenticated GPU host and lazily
reports not-ready if dependencies, CUDA, or the configured LoRA are absent. Do
not install `requirements-diffusers.txt` or run SD 1.5 on the local Ryzen CPU.
See `docs/API_CONTRACT.md` and `docs/DEPLOYMENT_RUNBOOK.md`.

On the GPU host, set both `LORA_PATH` and `LORA_SHA256`. Artifact validation is
performed before the provider imports Diffusers or downloads the base model.
Use `deployment/runpod/bootstrap_runpod.sh` with the official RunPod PyTorch
template, then validate the host using `inference_api/scripts/gpu_preflight.py`.
