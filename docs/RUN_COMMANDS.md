# Run Commands

Kumpulan perintah copy-pasteable untuk Windows PowerShell dan Kaggle.

## Validasi Pipeline Python

```powershell
cd D:\TaniAdaptif
.\.venv\Scripts\python.exe -m pytest ml_pipeline\tests inference_api\tests -v
.\.venv\Scripts\python.exe -m ruff check ml_pipeline inference_api
.\.venv\Scripts\python.exe -m ruff format --check ml_pipeline inference_api
```

## Validasi Flutter

```powershell
cd D:\TaniAdaptif\mobile-flutter\tani_adaptif
dart format lib test
flutter analyze
flutter test
```

## Validasi Backend Node.js

```powershell
cd D:\TaniAdaptif\backend-nodejs
npm test
npm audit --omit=dev
```

## Siapkan Dataset Empat Kelas

```powershell
cd D:\TaniAdaptif
.\.venv\Scripts\python.exe -m pip install -r ml_pipeline\requirements\dev.txt
.\.venv\Scripts\python.exe -m ml_pipeline.src.dataset.cli audit --config ml_pipeline\configs\dataset_public_multicrop.yaml --all-classes
.\.venv\Scripts\python.exe -m ml_pipeline.src.dataset.cli prepare --config ml_pipeline\configs\dataset_public_multicrop.yaml --all-classes
.\.venv\Scripts\python.exe -m ml_pipeline.src.dataset.cli validate --config ml_pipeline\configs\dataset_public_multicrop.yaml --all-classes
.\.venv\Scripts\python.exe -m ml_pipeline.src.dataset.cli report --config ml_pipeline\configs\dataset_public_multicrop.yaml --all-classes
```

## Uji Pipeline Pilot Padi Publik

```powershell
cd D:\TaniAdaptif
.\.venv\Scripts\python.exe -m ml_pipeline.src.dataset.cli audit --config ml_pipeline\configs\pilot_padi.yaml
.\.venv\Scripts\python.exe -m ml_pipeline.src.dataset.cli prepare --config ml_pipeline\configs\pilot_padi.yaml
.\.venv\Scripts\python.exe -m ml_pipeline.src.dataset.cli caption --config ml_pipeline\configs\pilot_padi.yaml
.\.venv\Scripts\python.exe -m ml_pipeline.src.dataset.cli report --config ml_pipeline\configs\pilot_padi.yaml
```

Perintah ini memakai trigger pilot `gaus_padi_public`; ia tidak mengubah
trigger final multicrop.

## Jalankan Stack Mock melalui Backend

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

Terminal 3, cek dan generate melalui Express:

```powershell
$body = @{
  crop = "padi"
  land_type = "sawah"
  water_availability = "cukup"
  previous_crop = "jagung"
  weather_summary = "Cerah berawan; suhu 28 C"
  seed = 42
  request_id = "powershell-smoke-001"
  steps = 25
  guidance_scale = 7.5
  width = 512
  height = 512
} | ConvertTo-Json

Invoke-RestMethod `
  -Method Post `
  -Uri http://localhost:3000/api/visual/generate `
  -ContentType "application/json" `
  -Body $body
```

## Jalankan Flutter ke Backend Mock

```powershell
cd D:\TaniAdaptif\mobile-flutter\tani_adaptif
flutter run -d chrome --dart-define=BACKEND_API_BASE_URL=http://localhost:3000/api
```

Flutter tidak menerima alamat FastAPI. Kontrak prompt langsung hanya untuk alat
pilot terotorisasi dan bukan alur aplikasi.

## Siapkan Deployment GPU RunPod

```powershell
cd D:\TaniAdaptif
powershell -ExecutionPolicy Bypass -File deployment\runpod\build_bundle.ps1
Get-Content artifacts\deployment\taniadaptif_runpod_deployment.zip.sha256
```

Ikuti `docs/DEPLOYMENT_RUNBOOK.md`. Setelah Pod siap, jalankan gerbang nyata:

```powershell
$env:BACKEND_API_BASE_URL = "https://POD_ID-3000.proxy.runpod.net/api"
$env:BACKEND_VISUAL_API_TOKEN = "PASTE_TEMPORARY_CLIENT_TOKEN"
.\.venv\Scripts\python.exe inference_api\scripts\e2e_probe.py `
  --output-dir artifacts\e2e_inference\runpod_real
Remove-Item Env:BACKEND_VISUAL_API_TOKEN
```

## Kaggle GPU - Training Final

Run final `20260820T143551Z` sudah selesai sukses. Bagian ini dipertahankan untuk
reproduksi; jangan rerun hanya untuk mendapatkan model yang sama.

File yang diunggah sebagai Kaggle Dataset private:

```text
artifacts/dataset_packages/dataset_multicrop_v1_kaggle_fixed.zip
```

Notebook yang diimport:

```text
ml_pipeline/notebooks/00_train_lora_multicrop_kaggle_final.ipynb
```

Di Kaggle, lakukan **Add Input**, aktifkan **GPU**, aktifkan **Internet**, lalu
klik **Run All**. Download hasil hanya bila Cell 51 menampilkan sukses:

```text
/kaggle/working/taniadaptif_lora_artifacts.zip
/kaggle/working/taniadaptif_lora_artifacts.sha256
```

Panduan lengkap: `docs/KAGGLE_FINAL_RUN_GUIDE.md`.

Validasi ulang ZIP hasil tanpa memuat Stable Diffusion:

```powershell
.\.venv\Scripts\python.exe -m ml_pipeline.src.training.validate_kaggle_export `
  --artifact-zip artifacts\kaggle_runs\notebook6b00d019aa\version_2_success_20260820\taniadaptif_lora_artifacts.zip `
  --sha256-file artifacts\kaggle_runs\notebook6b00d019aa\version_2_success_20260820\taniadaptif_lora_artifacts.sha256
```

Materialisasi bukti dan model canonical secara idempotent:

```powershell
.\.venv\Scripts\python.exe -m ml_pipeline.scripts.materialize_kaggle_evidence `
  --artifact-zip artifacts\kaggle_runs\notebook6b00d019aa\version_2_success_20260820\taniadaptif_lora_artifacts.zip `
  --output-dir artifacts\model_evaluation\kaggle_run_20260820T143551Z `
  --model-dir artifacts\models\multisource_multicrop_lora_sd15
```

Materializer tidak menimpa CSV review manusia yang sudah tersedia.

## Review Visual LoRA Lokal

Jalankan aplikasi review tanpa memuat Stable Diffusion:

```powershell
Set-Location D:\TaniAdaptif
npm run lora-review
```

Buka `http://127.0.0.1:4174`. Setelah seluruh 72 gambar dinilai, jalankan:

```powershell
node tools/lora_review_ui/src/cli.mjs --require-complete

.\.venv\Scripts\python.exe -m ml_pipeline.src.evaluation.validate_human_review `
  --review-csv artifacts\model_evaluation\kaggle_run_20260820T143551Z\human_evaluation_template_local.csv `
  --report-json artifacts\model_evaluation\kaggle_run_20260820T143551Z\human_review_progress.json `
  --require-complete

.\.venv\Scripts\python.exe -m ml_pipeline.src.evaluation.analyze_human_review `
  --review-csv artifacts\model_evaluation\kaggle_run_20260820T143551Z\human_evaluation_template_local.csv `
  --output-dir artifacts\model_evaluation\kaggle_run_20260820T143551Z
```

Panduan rubrik lengkap: `docs/LORA_HUMAN_REVIEW_GUIDE.md`.

## Google Colab - Legacy

Bagian ini dipertahankan sebagai riwayat percobaan. Entry point final berada di
Kaggle dan tidak memerlukan notebook Colab berikut.
Dataset dibaca otomatis dari:

```text
MyDrive/skripsi_lora/datasets/dataset_multicrop_v1.zip
```

Setelah itu jalankan:

```text
ml_pipeline/notebooks/00_run_complete_lora_pipeline_colab.ipynb
```

Fallback jika ZIP Drive tidak tersedia:

```text
/content/dataset_multicrop_v1_upload_parts/
```

Notebook menyalin atau merakit lalu memvalidasi
`/content/dataset_multicrop_v1.zip` sebelum preparation. Jangan upload ZIP
188 MB secara langsung melalui extension.

Output smoke dan LoRA utama:

```text
MyDrive/skripsi_lora/outputs/smoke_test/multisource_multicrop_smoke_lora.safetensors
MyDrive/skripsi_lora/outputs/multicrop_v1/multisource_multicrop_lora.safetensors
```

Setelah output Colab disinkronkan ke Windows, validasi bukti tanpa memuat model:

```powershell
.\.venv\Scripts\python.exe -m ml_pipeline.src.training.validate_run `
  --output-dir D:\path\to\synced_output `
  --expected-steps 100 `
  --lora-filename multisource_multicrop_smoke_lora.safetensors
```

## Dokumen Pendukung

```text
docs/PYTHON_SETUP.md
docs/COLAB_RESOURCE_PLAN.md
docs/LOCAL_MOCK_API_SMOKE.md
```
