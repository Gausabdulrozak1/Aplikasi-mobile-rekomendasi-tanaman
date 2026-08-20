# STATUS - TaniAdaptif

Tanggal verifikasi aktual: 2026-08-21

## Ringkasan

Review dataset selesai 475/475: 390 accepted, 85 rejected, 0 unsure, dan 0
pending. Seluruh kelas memenuhi minimum 80. Dataset final berisi 389 gambar,
metadata dan split valid, serta paket ZIP/checksum telah dibuat dan divalidasi.

Stable Diffusion tidak dilatih pada laptop. Percobaan Colab lama gagal pada
step 0 karena schema metadata membuat Hugging Face ImageFolder memperlakukan
`original_file_name` sebagai path media kedua. Jalur final kemudian dipindahkan
ke Kaggle dengan paket fixed yang telah melewati PIL full decode, Hugging Face
ImageFolder 312/312 + 77/77, dan probe loader 78 batch.

Kaggle version 1 berhasil menyelesaikan smoke 100 dan main 1600, tetapi berhenti
pada inference karena editable install Diffusers belum aktif pada kernel
Jupyter yang sudah berjalan. Source notebook diperbaiki agar exact checkout
ditambahkan ke `sys.path` current kernel. Kaggle version 2, run
`20260820T143551Z`, kemudian menyelesaikan seluruh 52 cell, 4 sanity image, 72
gambar evaluasi, export, dan final integrity dengan `FINAL STATUS: SUCCESS`.
ZIP unduhan dan LoRA sudah divalidasi ulang secara lokal tanpa menjalankan
Stable Diffusion.

Human review Base-vs-LoRA selesai 72/72 pada 36 pasangan dan telah melewati
validator serta analyzer. Seluruh pasangan memakai prompt dan seed identik,
masing-masing kelas memiliki 9 kondisi, dan tidak ada skor otomatis. Deployment
runtime kini memakai alur Flutter -> Express -> FastAPI GPU -> Express image
proxy; inference nyata masih menunggu host GPU terautentikasi.

## Dataset Final

| Kelas | Accepted manusia | Dipilih final | Train | Validation | Public final | Local Aikmel final |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| padi | 95 | 95 | 76 | 19 | 70 | 25 |
| jagung | 101 | 100 | 80 | 20 | 100 | 0 |
| cabai | 97 | 97 | 78 | 19 | 97 | 0 |
| kacang_tanah | 97 | 97 | 78 | 19 | 97 | 0 |
| **Total** | **390** | **389** | **312** | **77** | **364** | **25** |

Jagung dibatasi deterministik menjadi 100 gambar dengan seed 42. Split 80:20
bersifat stratified, mempertahankan distribusi sumber padi, dan tidak memiliki
duplicate-group leakage. Jagung, cabai, dan kacang tanah tetap public-only.

Trigger final:

- `taniadaptif_padi`
- `taniadaptif_jagung`
- `taniadaptif_cabai`
- `taniadaptif_kacang_tanah`

## Paket Dataset

- Status validator: `valid`
- Training diizinkan oleh gate dataset: `true`
- ZIP: `artifacts/dataset_packages/dataset_multicrop_v1.zip`
- Ukuran: 188356224 byte
- SHA-256: `f6aa060658cf95e48996f10f0ffde200938d340dd15e6b60adace5bb5cecfb33`
- Isi ZIP: 412 entry, tidak rusak, tanpa konten terlarang
- Train metadata: 312 baris valid
- Validation metadata: 77 baris valid
- Trigger silang: 0
- Duplicate leakage lintas split: 0

Laporan utama tersedia pada
`artifacts/dataset_packages/final_package_validation.md` dan `.json`.

Paket lama di atas dipertahankan sebagai bukti audit dan tidak ditimpa. Paket
aktif untuk Kaggle:

- ZIP: `artifacts/dataset_packages/dataset_multicrop_v1_kaggle_fixed.zip`
- Ukuran: 188302954 byte
- SHA-256: `e232f79d2f8ae20b4fb765efb38435ce05e929406e88faba6b02aaaafd1ad42d`
- Train/validation: 312/77, total 389
- Unresolved/ambiguous metadata mapping: 0/0
- PIL decode: train 312/312, validation 77/77
- ImageFolder decode: train 312/312, validation 77/77
- Diffusers-equivalent loader probe: 312 gambar dalam 78 batch
- Image bytes, caption, split, dan keputusan manusia berubah: 0
- `file_name` dinormalisasi pada 389 row; provenance tetap dipertahankan sebagai
  `source_original_name` agar tidak lagi cocok dengan reserved pattern
  `*_file_name` milik ImageFolder.

Laporan fixed tersedia pada
`artifacts/dataset_packages/KAGGLE_DATASET_PACKAGE_REPORT.md` dan `.json`.

## Kaggle Final Runtime

- Notebook: `ml_pipeline/notebooks/00_train_lora_multicrop_kaggle_final.ipynb`
- Source tunggal: `ml_pipeline/notebooks/00_train_lora_multicrop_kaggle_final.py`
- Dataset input: ZIP fixed atau folder hasil ekstraksi Kaggle di
  `/kaggle/input`, ditemukan tanpa hardcode username
- Mode folder mengunci SHA mapping + metadata dan memverifikasi SHA-256 seluruh
  389 gambar sebelum decode
- Runtime/output: hanya `/kaggle/working`, `/kaggle/input`, dan `/tmp`
- Base model: `stable-diffusion-v1-5/stable-diffusion-v1-5`
- Diffusers commit: `0f252be0ed42006c125ef4429156cb13ae6c1d60`
- CUDA dan internet merupakan hard gate; training CPU dilarang
- AdamW8bit hanya dipakai setelah CUDA optimizer probe; fallback adalah AdamW
  PyTorch
- Resume checkpoint eksternal dicopy atomik ke output lokal dan diverifikasi
  per-file SHA-256 karena source Diffusers hanya memuat checkpoint dari
  `output_dir`
- Full log dan root traceback disimpan bila subprocess `accelerate` gagal
- Panduan: `docs/KAGGLE_FINAL_RUN_GUIDE.md`
- Notebook remote: `gausabdul/notebook6b00d019aa`, version 2
- Run ID sukses: `20260820T143551Z`
- GPU: 2 x Tesla T4; CUDA 12.8; PyTorch 2.10.0+cu128
- Exact Diffusers commit:
  `0f252be0ed42006c125ef4429156cb13ae6c1d60`
- Waktu pipeline lengkap: 4.255,92 detik (70 menit 55,92 detik)

## LoRA dan Evaluasi

- Smoke test Kaggle: `pass`, 100/100 langkah, return code 0, 250,79 detik.
- Training utama: `success`, 1.600/1.600 langkah, return code 0,
  3.346,29 detik.
- Checkpoint akhir: checkpoint-100 smoke dan checkpoint-1600 main valid.
- LoRA canonical: `multisource_multicrop_lora.safetensors`, 6.414.992 byte,
  256 tensor.
- LoRA SHA-256:
  `0bda8908d577513110c22cf5ec1b8a7e008d2b26dd90525732a5c4e4b1bdd43a`.
- Kontrak filename telah diperbaiki: config training menjadi sumber tunggal,
  keluaran default Diffusers dinormalisasi dan divalidasi tanpa dihapus, serta
  canonical valid tidak memicu training ulang.
- Setup Kaggle mengaudit dependency sebelum perubahan, menjaga PyTorch/CUDA
  bawaan, mengunci dependency non-Torch, lalu menguji entrypoint dan loader pada
  fresh process sebelum training.
- Training memakai `--report_to tensorboard --logging_dir tensorboard`; tidak
  memerlukan layanan logging eksternal.
- Setup menghapus TorchAO bawaan Colab karena pipeline memakai LoRA standar dan
  Adam 8-bit, bukan quantization TorchAO.
- Loss aktual finite: 501 observasi smoke dan 8.001 observasi main. Rata-rata
  100 observasi terakhir main 0,180415; loss bukan skor kualitas visual.
- Sanity inference: 4/4 gambar valid.
- Evaluasi base vs LoRA: `complete`, 36 kondisi, 72/72 gambar valid.
- Metrik brightness/contrast/entropy selesai sebagai proxy deskriptif saja.
- Human review: 72/72 penilaian lengkap pada 36 pasangan, 9 kondisi per kelas,
  dengan prompt dan seed identik di setiap pasangan.
- Akurasi identifikasi Base: 31/36 (86,11%); LoRA: 34/36 (94,44%); selisih
  +8,33 poin persentase. Exact McNemar dua sisi menghasilkan p=0,25.
- Median kesesuaian konteks dan realisme keseluruhan: Base 4,5; LoRA 4,0.
  Kelas kacang tanah membaik dari 4/9 menjadi 7/9 identifikasi benar dan median
  2 menjadi 4; hasil per kelas lengkap ada di analyzer.
- Nilai `class_confusion` yang sama dengan kelas target dicatat sebagai
  konfirmasi target, bukan confusion. Cross-class/unclear aktual: Base 5 dan
  LoRA 2.
- Sumber penilaian `reviewer_entered_local_ui`; `automated_scores=false`.
  Identitas manusia tidak dapat diverifikasi independen oleh perangkat lunak.
- Aplikasi review lokal tersedia melalui `npm run lora-review` pada
  `http://127.0.0.1:4174`; progres final 72/72 dan tidak diisi otomatis.
- UI memvalidasi pasangan, nilai rubrik, path/PNG, membuat backup sebelum
  perubahan, dan membatalkan ringkasan lama jika penilaian diedit kembali.
- Analyzer menghasilkan `human_review_analysis.json`,
  `human_review_analysis.csv`, dan `BAB_IV_HUMAN_REVIEW_RESULTS.md` tanpa
  mencampur metrik proxy. Laporan lengkap:
  `artifacts/model_evaluation/kaggle_run_20260820T143551Z/POST_REVIEW_ANALYSIS_REPORT.md`.
- Input dan seluruh hasil analysis telah dibackup dengan manifest hash di
  `post_review_backups/20260820T181414Z/`.
- Tidak dilakukan retraining, fallback adapter, atau perubahan model final.
- Provider FastAPI lokal tetap mock untuk melindungi laptop. LoRA nyata sudah
  ditempatkan pada `artifacts/models/multisource_multicrop_lora_sd15/` untuk
  deployment ke host inference GPU.
- Flutter hanya memanggil Express backend. Express mengautentikasi dan
  membatasi endpoint visual, menyimpan token FastAPI, menyembunyikan URL
  upstream, dan meneruskan PNG melalui `/api/visual/images`.
- Artifact ZIP: 51.940.573 byte, SHA-256
  `54ee68fccbb88be07a089365c2e62f9e6004e2774992973debe665d5dc0eb26a`.
- Validator lokal: `valid=true`, 100 file, CRC/hash/manifest/status konsisten,
  76 PNG dapat dibuka, error 0.
- Paket review: `artifacts/model_evaluation/kaggle_run_20260820T143551Z/`.

## Regression Test

| Lapisan | Hasil aktual |
| --- | --- |
| Dataset/LoRA pipeline pytest | 96 passed |
| Inference API pytest | 29 passed |
| Python total | 125 passed dalam 147,21 detik |
| Backend Node | 23 passed |
| Flutter | 13 passed |
| Dataset Review UI Node | 11 passed |
| Dataset Review validator | valid, can_finalize=true |
| LoRA Review UI Node | 7 passed |
| LoRA Review UI visual QA | desktop 1440 dan mobile 390; tanpa overflow |
| LoRA Human Review validator | valid, complete=true, 72/72, 36 pairs |
| LoRA BAB IV analyzer | complete_validated_human_review; JSON/CSV/Markdown |
| Flutter analyze | No issues found |
| Dart format | 19 files, 0 changed |
| Ruff check | All checks passed |
| Ruff format scope pasca-review/deployment | 11 files already formatted |
| Ruff format repo-wide | 9 file legacy akan direformat; tidak diubah agar source notebook/final evidence tidak mengalami churn |
| Notebook JSON dan syntax | 8 notebook valid; Kaggle 52/52 cell compile |
| Preflight | All checks passed |
| Secret scan | No obvious secrets found |
| pip check | No broken requirements |
| pip-audit | No known vulnerabilities |
| npm audit backend | 0 vulnerabilities |

## Aplikasi dan APK

Rule-based engine tetap menentukan rekomendasi tanaman; Stable Diffusion hanya
akan membuat visual. FastAPI mock, backend BMKG/rule engine, Flutter, dan APK
debug lama tetap tersedia. Kontrak proxy lokal sudah diuji sampai pengembalian
PNG, tetapi bukti itu berprovider mock dan bukan inference nyata. Model final
sudah tersedia, tetapi provider Diffusers belum dijalankan pada host inference
GPU dan karena itu belum boleh diklaim aktif di aplikasi.

Paket RunPod, preflight GPU, startup supervisor, token internal, token klien
sementara, rate limit, dan real e2e probe sudah disiapkan. Host yang disarankan
adalah RunPod Secure Cloud On-Demand RTX A5000 24 GB. Panduan lengkap ada di
`docs/DEPLOYMENT_RUNBOOK.md`.

APK debug setelah integrasi proxy berhasil dibangun dan diverifikasi di
`artifacts/apk/taniadaptif-debug-proxy-20260821.apk` (152.840.310 byte,
SHA-256 `417604f6a2180401aef576c8f01bf5bc1997dadae27311c1841f1a58d48cedb5`).
APK ini tidak berisi URL/token produksi dan bukan bukti inference nyata.

## Blocker Aktual

Training dan export tidak lagi menjadi blocker: Cell 51 selesai tanpa exception,
menampilkan `FINAL STATUS: SUCCESS`, dan `complete_pipeline_state.json`
berstatus `success`. Human review dan analyzer juga tidak lagi menjadi blocker.
Pekerjaan yang masih membutuhkan akun/biaya eksternal atau perangkat adalah
deployment RunPod, real e2e probe, screenshot Android dengan gambar nyata, uji
perangkat fisik, validasi ahli, farmer UAT, dan signing release. BAB IV final
belum disusun karena gerbang inference nyata dan screenshot Android belum ada.
