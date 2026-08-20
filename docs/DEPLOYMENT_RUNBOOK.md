# Deployment Runbook

## Safety Boundary

- Training final is complete and must not be repeated for deployment.
- The Ryzen laptop runs only Node, Flutter, mock inference, validation, and an
  HTTP probe. It must not load Stable Diffusion or install the Diffusers GPU
  dependency set.
- Real Stable Diffusion 1.5 + LoRA inference runs only on the remote GPU.
- The only accepted final model is run `20260820T143551Z`, filename
  `multisource_multicrop_lora.safetensors`, SHA-256
  `0bda8908d577513110c22cf5ec1b8a7e008d2b26dd90525732a5c4e4b1bdd43a`.

## Local Mock Stack

Terminal 1:

```powershell
cd D:\TaniAdaptif
$env:INFERENCE_PROVIDER = "mock"
.\.venv\Scripts\python.exe -m uvicorn inference_api.app.main:app --host 127.0.0.1 --port 5000
```

Terminal 2:

```powershell
cd D:\TaniAdaptif\backend-nodejs
npm start
```

Terminal 3, Android emulator:

```powershell
cd D:\TaniAdaptif\mobile-flutter\tani_adaptif
flutter run --dart-define-from-file=config/development.example.json
```

Verify the same application boundary used in production:

```powershell
Invoke-RestMethod http://localhost:3000/api/kesehatan
Invoke-RestMethod http://localhost:3000/api/visual/ready
Invoke-RestMethod http://localhost:3000/api/visual/model-info
```

Mock PNGs are placeholders and cannot be used as real inference or visual
quality evidence.

## Recommended GPU Host

Use a RunPod **Secure Cloud, On-Demand Pod** with one **RTX A5000 24 GB** and
the official RunPod PyTorch template. It is the best fit for this controlled
thesis deployment because it provides enough VRAM for SD 1.5, persistent
`/workspace`, a normal Linux environment for FastAPI and Express, and automatic
HTTPS for an exposed HTTP port. As of 2026-08-21, RunPod lists the RTX A5000
Secure Cloud rate at about USD 0.27/hour; confirm the live console price before
deploying.

Official references:

- [RunPod pricing](https://www.runpod.io/pricing)
- [HTTP proxy and its 100-second limit](https://docs.runpod.io/pods/configuration/expose-ports)
- [Pod storage persistence](https://docs.runpod.io/pods/storage/types)
- [Official templates](https://docs.runpod.io/pods/templates/overview)

Use an L4 24 GB as the first fallback when A5000 capacity is unavailable. An
A4000-class 16 GB GPU is sufficient for this 512 x 512 SD 1.5 profile but has
less memory headroom. An A100/H100 is unnecessary for this workload.

## 1. Build the Upload Bundle

Run on Windows. This validates and packages the final LoRA without loading it
into Stable Diffusion:

```powershell
cd D:\TaniAdaptif
powershell -ExecutionPolicy Bypass -File deployment\runpod\build_bundle.ps1
Get-Content artifacts\deployment\taniadaptif_runpod_deployment.zip.sha256
```

Files produced:

```text
artifacts/deployment/taniadaptif_runpod_deployment.zip
artifacts/deployment/taniadaptif_runpod_deployment.zip.sha256
artifacts/deployment/DEPLOYMENT_BUNDLE_REPORT.md
```

The ZIP contains only the runtime source, deployment scripts, safe examples,
and the validated final LoRA. It excludes dataset, checkpoints, generated
images, `.env`, and credentials.

## 2. Create the RunPod Pod

1. Add a small controlled balance and note the live hourly price.
2. Select **Pods > Deploy**, **Secure Cloud**, and **On-Demand**.
3. Select **RTX A5000 24 GB** and the latest official RunPod PyTorch template.
4. Allocate at least 30 GB container disk and 40 GB volume disk.
5. Expose HTTP port `3000`. Do not expose port `5000`.
6. Deploy, open **Connect**, then open JupyterLab or the Web Terminal.
7. Upload `taniadaptif_runpod_deployment.zip` to `/workspace`.

The public application URL will be:

```text
https://POD_ID-3000.proxy.runpod.net/api
```

## 3. Extract and Bootstrap

Run in the RunPod terminal:

```bash
cd /workspace
python -m zipfile -e taniadaptif_runpod_deployment.zip /workspace
cd /workspace/TaniAdaptif
bash deployment/runpod/bootstrap_runpod.sh
```

Bootstrap installs only remote runtime dependencies. It does not train or
modify the LoRA.

## 4. Create Secrets

Generate two different tokens in the RunPod terminal:

```bash
python -c "import secrets; print(secrets.token_urlsafe(48))"
python -c "import secrets; print(secrets.token_urlsafe(48))"
```

Then create the private runtime file:

```bash
mkdir -p /workspace/taniadaptif-secrets
cp deployment/runpod/runtime.env.example /workspace/taniadaptif-secrets/runtime.env
chmod 600 /workspace/taniadaptif-secrets/runtime.env
```

Open `/workspace/taniadaptif-secrets/runtime.env` in JupyterLab and replace:

- `INFERENCE_API_TOKEN` with the first token. It stays inside the Pod.
- `BACKEND_VISUAL_API_TOKEN` with the second, temporary client token.

Leave `PUBLIC_API_BASE_URL` blank; `start_stack.sh` derives the RunPod HTTPS
URL from `RUNPOD_POD_ID`. Do not paste either token into logs, Git, reports, or
screenshots.

## 5. Start the GPU Stack

Run:

```bash
cd /workspace/TaniAdaptif
nohup bash deployment/runpod/start_stack.sh \
  >/workspace/taniadaptif-logs/stack-supervisor.log 2>&1 &
echo $!
tail -f /workspace/taniadaptif-logs/stack-supervisor.log
```

The first startup downloads the SD 1.5 base model into persistent
`/workspace/huggingface`; it can take several minutes. The startup sequence:

1. validates CUDA and at least 12 GiB VRAM;
2. validates exact dependency versions;
3. opens and hashes the final SafeTensors LoRA;
4. starts one private FastAPI worker at `127.0.0.1:5000`;
5. waits for the real model to become ready;
6. starts Express publicly on port `3000`.

Generated files and logs remain under `/workspace`. `GENERATION_TIMEOUT_SECONDS`
is 80 and the backend timeout is 85 seconds, both below the RunPod HTTP proxy's
100-second request limit.

## 6. Run the Real End-to-End Gate

On Windows, set the public URL and temporary client token only for the current
PowerShell process:

```powershell
cd D:\TaniAdaptif
$env:BACKEND_API_BASE_URL = "https://POD_ID-3000.proxy.runpod.net/api"
$env:BACKEND_VISUAL_API_TOKEN = "PASTE_TEMPORARY_CLIENT_TOKEN"
.\.venv\Scripts\python.exe inference_api\scripts\e2e_probe.py `
  --output-dir artifacts\e2e_inference\runpod_real
Remove-Item Env:BACKEND_VISUAL_API_TOKEN
```

Success is valid only when this file has `status: success` and every check is
`true`:

```text
artifacts/e2e_inference/runpod_real/real_inference_e2e_report.json
```

The same folder will contain a real generated PNG. A report marked `mock`,
`cpu`, wrong hash, wrong URL path, or failed PNG validation is not accepted.
The probe first obtains `recommendedCrop` from the Express rule engine and then
uses that exact crop for GPU generation.

## 7. Run Flutter Android

Create the ignored file
`mobile-flutter/tani_adaptif/config/production.local.json`:

```json
{
  "APP_ENV": "production",
  "MOCK_MODE": "false",
  "BACKEND_API_BASE_URL": "https://POD_ID-3000.proxy.runpod.net/api",
  "BACKEND_VISUAL_API_TOKEN": "PASTE_TEMPORARY_CLIENT_TOKEN"
}
```

List devices and run on the selected Android target:

```powershell
cd D:\TaniAdaptif\mobile-flutter\tani_adaptif
flutter devices
flutter run -d DEVICE_ID --dart-define-from-file=config/production.local.json
```

Complete one recommendation, generate the visual, and confirm the result screen
shows `Provider: diffusers`, the final LoRA identifier, and the generated image.
Capture screenshots only after the image is visibly rendered. Do not include
terminal windows or token files in screenshots.

## 8. Stop Cost and Preserve Evidence

After testing:

1. Download `/workspace/taniadaptif-evidence/gpu_preflight.json` and relevant
   logs with secrets redacted.
2. Keep the Windows e2e JSON, PNG, and Android screenshots in the research
   artifact folder.
3. Stop the Pod in the RunPod console immediately. Stopping releases GPU
   compute but volume storage continues to incur a small charge.
4. Terminate only after all required files are backed up; terminating deletes
   a Pod volume unless a separate network volume is used.

## Completion Gate

Deployment is not complete until all of these exist:

- remote `gpu_preflight.json` with `status=success`;
- local `real_inference_e2e_report.json` with `status=success`;
- real PNG returned through `/api/visual/images/...`;
- an Android screenshot showing the generated image;
- no evidence of local Stable Diffusion execution.

The human-review analysis may be cited as completed research evidence, but the
final Chapter IV must wait for this real inference gate and Android screenshot.
