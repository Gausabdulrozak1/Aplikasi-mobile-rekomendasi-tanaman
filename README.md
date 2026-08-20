# TaniAdaptif

Aplikasi Mobile Berbasis Stable Diffusion dengan Fine-Tuning LoRA dan API BMKG
untuk Simulasi Rotasi Tanam Adaptif Iklim bagi Petani Aikmel

## Penulis
Gaus Abdul Rozak - NIM 220602210
Program Studi Teknik Informatika
Universitas Hamzanwadi - 2026

## Struktur Project
- `backend-nodejs/` : Server REST API (Node.js + Express)
- `backend-python/` : Prototype mock lama; bukan runtime inference aktif
- `mobile-flutter/` : Aplikasi Mobile (Flutter)
- `ml_pipeline/data/` : Raw dataset, manifest, dan laporan audit (output besar diabaikan Git)
- `dokumentasi/` : Dokumentasi teknis dan skripsi
- `ml_pipeline/` : Pipeline dataset, captioning, training notebook, dan evaluasi LoRA
- `inference_api/` : Runtime FastAPI aktif dengan provider mock dan Diffusers
- `docs/` : Dokumentasi teknis pipeline, eksperimen, API, dataset, dan bukti Bab IV
- `artifacts/` : Template laporan, sampel, dan hasil evaluasi ringan yang boleh disimpan

## Teknologi
- Frontend: Flutter
- Backend: Node.js, Express, SQLite
- AI: Python, Stable Diffusion 1.5, LoRA
- Data Cuaca: API BMKG

## Prinsip Arsitektur
- Rule-based engine dan API BMKG menentukan rekomendasi tanaman.
- Stable Diffusion/LoRA hanya membuat simulasi visual dari rekomendasi tersebut.
- Flutter memanggil satu Express backend; FastAPI GPU dan token internal tidak
  diekspos ke aplikasi Android.
- Training LoRA final dilakukan di Kaggle GPU, bukan di laptop lokal.
- Mode pengembangan lokal memakai mock inference agar laptop tetap ringan.
- Pipeline LoRA mendukung padi, jagung, cabai, dan kacang tanah.
- Padi menggabungkan gambar publik dan dokumentasi lokal Aikmel; jagung,
  cabai, dan kacang tanah menggunakan gambar publik saja.
- Trigger netral: `taniadaptif_padi`, `taniadaptif_jagung`, `taniadaptif_cabai`, dan
  `taniadaptif_kacang_tanah`.
- Pilot pertama tetap satu kelas padi publik dengan trigger eksperimen
  `gaus_padi_public`; trigger ini terpisah dari model final dan bukan klaim
  representasi Aikmel.
- Audit dan kurasi lokal hanya memakai Pillow/Python; training dilakukan di
  Kaggle GPU agar laptop tidak menanggung beban Stable Diffusion.

## Cara Menjalankan

Gunakan `docs/DEPLOYMENT_RUNBOOK.md` untuk stack lokal, konfigurasi Flutter,
dan profil deployment GPU. Status bukti aktual ada di `STATUS.md`.

Training final memakai
`ml_pipeline/notebooks/00_train_lora_multicrop_kaggle_final.ipynb` dan paket
`artifacts/dataset_packages/dataset_multicrop_v1_kaggle_fixed.zip`. Ikuti
`docs/KAGGLE_FINAL_RUN_GUIDE.md`.

Run Kaggle `20260820T143551Z` telah selesai: smoke 100 langkah, main 1.600
langkah, sanity empat kelas, dan 72 gambar evaluasi. Bukti tervalidasi dan
contact sheet tersedia di
`artifacts/model_evaluation/kaggle_run_20260820T143551Z/`; draf hasil untuk
skripsi ada di `docs/CHAPTER_IV_RESULT_TEMPLATE.md`. Penilaian manusia 72/72
sudah selesai dan analyzer berpasangan menghasilkan JSON, CSV, dan Markdown;
metrik proxy tetap dipisahkan dari skor manusia.

Untuk review 36 pasangan Base-vs-LoRA, jalankan `npm run lora-review`, lalu
buka `http://127.0.0.1:4174`. Aplikasi menyimpan ke CSV lokal secara atomik,
membuat backup sebelum perubahan, dan baru mengaktifkan ringkasan saat seluruh
72 gambar selesai dinilai. Panduan tersedia di
`docs/LORA_HUMAN_REVIEW_GUIDE.md`.
Hasil final dan laporan verifikasinya berada pada folder run yang sama.

Deployment real menggunakan paket dari
`deployment/runpod/build_bundle.ps1`, RunPod Secure Cloud GPU, backend proxy,
dan gerbang `inference_api/scripts/e2e_probe.py`. Ikuti
`docs/DEPLOYMENT_RUNBOOK.md`. Stable Diffusion tidak dijalankan di laptop.

Untuk review visual dataset, jalankan `npm run dataset-review`, lalu buka
`http://127.0.0.1:4173`. Panduan ringkas tersedia di
`docs/DATASET_REVIEW_GUIDE.md`.

## Dokumen Kerja
- `TASKS.md` : checklist implementasi pipeline.
- `STATUS.md` : status aktual, perintah yang dijalankan, hasil test, dan blocker.
- `dokumentasi/PANDUAN_LORA_STABLE_DIFFUSION.md` : panduan awal LoRA SD 1.5.
- `docs/RUN_COMMANDS.md` : kumpulan perintah PowerShell dan Kaggle.
- `docs/KAGGLE_FINAL_RUN_GUIDE.md` : panduan Run All training final di Kaggle.
- `docs/COLAB_RESOURCE_PLAN.md` : batas aman Colab T4 dan perlindungan laptop lokal.
- `docs/PYTHON_SETUP.md` : setup Python ringan untuk test dan mock API.
- `docs/LOCAL_MOCK_API_SMOKE.md` : smoke test inference API mock dan Flutter.
