# Kaggle Live Inference Sidang

Notebook: `ml_pipeline/notebooks/09_kaggle_live_inference_sidang.ipynb`

## Sekali Saja

1. Buka notebook `gausabdul/taniadaptif-live-inference-sidang`.
2. Aktifkan GPU `NvidiaTeslaT4` dan Internet.
3. Pasang input dataset private LoRA final.
4. Buat Kaggle User Secret `INFERENCE_API_TOKEN` minimal 32 karakter.
5. Isi nilai yang sama pada `backend-nodejs/.env` sebagai `INFERENCE_API_TOKEN`.
6. `HF_TOKEN` hanya diperlukan jika unduhan base model meminta autentikasi.

## Saat Sidang

1. Run All notebook dan tunggu `STATUS=READY_FOR_SIDANG`.
2. Salin baris `KAGGLE_GPU_URL=https://...trycloudflare.com`.
3. Dari root repository jalankan:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\sidang_set_gpu_url.ps1 `
  -GpuUrl "https://xxxxx.trycloudflare.com"
```

4. Hubungkan HP dan jalankan `scripts/sidang_start.ps1`.
5. Pastikan notebook dan cell keep-alive tetap berjalan selama demo.
6. Buka rekomendasi tersimpan lalu tekan `Simulasi Visual`.

Quick Tunnel berubah setiap notebook dijalankan ulang. Ulangi langkah pengaturan URL setelah restart Kaggle.
