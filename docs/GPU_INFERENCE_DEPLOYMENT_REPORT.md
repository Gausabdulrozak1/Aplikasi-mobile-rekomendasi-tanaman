# GPU Inference Deployment Readiness Report

Date: 2026-08-21  
Final model run: `20260820T143551Z`  
Status: **prepared, not yet proven by a real GPU end-to-end run**

## Ready

| Area | Verified state |
| --- | --- |
| Final LoRA | 6,414,992-byte SafeTensors file, 256 tensors, exact SHA-256 `0bda8908d577513110c22cf5ec1b8a7e008d2b26dd90525732a5c4e4b1bdd43a` |
| Human review | 72/72 assessments, 36 pairs, 9 conditions/class, analyzer JSON/CSV/Markdown complete |
| FastAPI | Diffusers provider, CUDA requirement, exact LoRA validation, readiness, timeout, one-generation lock, private token |
| Express | readiness/model/generate/image proxy, private inference token, upstream URL hiding, client token, rate limit, error mapping |
| Flutter | one backend URL, structured recommendation context, client token header, authenticated image download, no inference URL/token |
| RunPod package | bootstrap, runtime environment template, startup supervisor, persistent directories, final model bundle |
| Evidence gate | GPU preflight and e2e probe reject CPU, mock, wrong model/hash, wrong route/crop, or invalid PNG; crop comes from the rule engine |
| Local contract test | Express -> authenticated FastAPI mock -> Express PNG passed; explicitly labelled mock-only |

No training or Stable Diffusion execution was performed on the laptop while
preparing these components. The final model was not changed.

## Not Yet Ready

The following evidence does not exist and must not be claimed:

| Missing evidence | Required proof |
| --- | --- |
| Authenticated remote GPU | a running Pod owned by the user |
| Remote CUDA environment | `/workspace/taniadaptif-evidence/gpu_preflight.json` with `status=success` |
| Real model startup | backend `/api/visual/ready` reports `diffusers`, `cuda`, and `model_loaded=true` |
| Real generation | local `real_inference_e2e_report.json` with every check true and a real 512 x 512 PNG |
| Android end-to-end display | screenshot after the same PNG is visibly rendered in the result screen |
| Public production security | real user authentication, distributed rate limiting, monitoring, and long-term secret management |

## Recommended Host

Use **RunPod Secure Cloud On-Demand, RTX A5000 24 GB**. This is the preferred
host for the current thesis test because the workload is SD 1.5 at 512 x 512,
the Pod offers persistent `/workspace`, and Express port 3000 can use the
RunPod HTTPS proxy. The official price page lists about USD 0.27/hour on
2026-08-21; the live console remains authoritative.

Primary sources:

- [RunPod GPU pricing](https://www.runpod.io/pricing)
- [RunPod port exposure and 100-second proxy timeout](https://docs.runpod.io/pods/configuration/expose-ports)
- [RunPod storage behavior](https://docs.runpod.io/pods/storage/types)
- [RunPod official template overview](https://docs.runpod.io/pods/templates/overview)

L4 24 GB is the first fallback. A4000 16 GB is acceptable with less headroom.
A100/H100 would add cost without a requirement from this model profile.

## Deployment Files

| Purpose | Repository path |
| --- | --- |
| Complete tutorial | `docs/DEPLOYMENT_RUNBOOK.md` |
| Public/private API contract | `docs/API_CONTRACT.md` |
| Bundle builder | `deployment/runpod/build_bundle.ps1` |
| Remote dependency bootstrap | `deployment/runpod/bootstrap_runpod.sh` |
| Remote stack supervisor | `deployment/runpod/start_stack.sh` |
| Remote environment template | `deployment/runpod/runtime.env.example` |
| GPU validation | `inference_api/scripts/gpu_preflight.py` |
| Real e2e validation | `inference_api/scripts/e2e_probe.py` |
| FastAPI safe example | `inference_api/gpu.env.example` |
| Express safe example | `backend-nodejs/.env.example` |
| Flutter safe example | `mobile-flutter/tani_adaptif/config/production.example.json` |
| Final LoRA | `artifacts/models/multisource_multicrop_lora_sd15/multisource_multicrop_lora.safetensors` |

Generated bundle files:

```text
artifacts/deployment/taniadaptif_runpod_deployment.zip
artifacts/deployment/taniadaptif_runpod_deployment.zip.sha256
artifacts/deployment/DEPLOYMENT_BUNDLE_REPORT.md
```

Current validated bundle: 6,056,545 bytes, 48 non-directory entries, SHA-256
`56296a9ee1d7d5db426b2ebc0d98847c4b0cc45ba7554ac3cfe53ccd1b421ed9`.
The LoRA entry inside the ZIP was streamed and hashed independently; it matches
the final model SHA-256. The archive has zero empty files, zero `.env` files,
zero dataset entries, and zero checkpoint entries.

## Environment Ownership

| Variable | Owner | Notes |
| --- | --- | --- |
| `BACKEND_API_BASE_URL` | Flutter | public RunPod HTTPS URL ending `/api` |
| `BACKEND_VISUAL_API_TOKEN` | Flutter + Express | short-lived controlled-test token; never use as durable public auth |
| `INFERENCE_API_BASE_URL` | Express | fixed to `http://127.0.0.1:5000` on the Pod |
| `INFERENCE_API_TOKEN` | Express + FastAPI | private random token; never place in Flutter |
| `LORA_PATH` | FastAPI | exact final file under persistent `/workspace` |
| `LORA_SHA256` | FastAPI | exact expected hash; startup fails on mismatch |
| `HF_HOME` | FastAPI | persistent base-model cache under `/workspace` |
| `PUBLIC_API_BASE_URL` | Express | derived from RunPod Pod ID by the startup script |

## User Actions Remaining

1. Build and verify the deployment ZIP on Windows.
2. Create the RunPod Pod, expose port 3000 only for the application, and upload
   the ZIP to `/workspace`.
3. Run `bootstrap_runpod.sh`, create two independent random tokens in
   `/workspace/taniadaptif-secrets/runtime.env`, and start the stack.
4. Wait until remote GPU preflight and `/ready` pass.
5. Run `e2e_probe.py` from Windows and retain its JSON plus PNG.
6. Create ignored `config/production.local.json`, run Flutter on Android, and
   capture the final result screen after the image loads.
7. Back up evidence and stop the Pod immediately to stop GPU compute charges.

Exact copy-paste commands are in `docs/DEPLOYMENT_RUNBOOK.md`.

## Claim Boundary

The analyzer and software preparation are complete. Real inference, final
Android screenshot, expert validation, and farmer UAT are pending. Therefore:

- do not claim that Diffusers + LoRA is active in Android yet;
- do not treat the local mock PNG as model evidence;
- do not invent latency, GPU, or image-quality results;
- do not finalize Chapter IV until real e2e JSON and Android screenshot exist.
