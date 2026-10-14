# LORA Phase Report

- Tanggal: 2026-08-13
- Status fase: **dataset ready, remote training pending**
- Gate dataset mengizinkan training: **True**
- Training Stable Diffusion lokal: **tidak dilakukan**

## 1-6. Dataset dan Paket

| Kelas | Accepted | Rejected | Final | Train | Validation |
| --- | ---: | ---: | ---: | ---: | ---: |
| padi | 95 | 5 | 95 | 76 | 19 |
| jagung | 101 | 29 | 100 | 80 | 20 |
| cabai | 97 | 23 | 97 | 78 | 19 |
| kacang_tanah | 97 | 28 | 97 | 78 | 19 |
| **Total** | **390** | **85** | **389** | **312** | **77** |

- Unsure/pending: 0/0.
- Padi final: 70 public dan 25 local_aikmel.
- ZIP: `artifacts/dataset_packages/dataset_multicrop_v1.zip`.
- Ukuran ZIP: 188356224 byte.
- SHA-256: `f6aa060658cf95e48996f10f0ffde200938d340dd15e6b60adace5bb5cecfb33`.
- Package validator: `valid`; checksum, metadata, trigger, source policy, dan
  duplicate leakage seluruhnya lulus.

## 7-8. Notebook dan Remote GPU

- Preparation, training, dan evaluation notebook valid JSON/syntax.
- Training/evaluation memakai config yang diekstrak preparation ke Drive;
  repository clone tidak diperlukan lagi.
- Google Drive terautentikasi dan struktur `MyDrive/skripsi_lora/` dibuat.
- Checksum dan tiga notebook sudah diunggah dan dibaca kembali.
- ZIP belum terunggah setelah dua timeout connector 60 detik.
- Runtime GPU terautentikasi: tidak ditemukan.
- Tidak tersedia Colab execution API/CLI, Kaggle config, gcloud, CUDA, atau SSH
  remote GPU config.

Drive root:
https://drive.google.com/drive/folders/11OtZXChqKb4SMt4j5ebwBcFHDVCMN6__

## 9-17. Training dan Evaluasi

| Item | Hasil aktual |
| --- | --- |
| Smoke test | `not_run`; 0/100 langkah |
| Loss smoke | tidak tersedia |
| Training utama | `not_run`; 0/1600 langkah |
| Checkpoint | tidak tersedia |
| LoRA | tidak tersedia |
| Ukuran LoRA | tidak tersedia |
| Evaluasi otomatis | `not_run`; tidak ada metrik aktual |
| Template manusia | 36 pasangan prompt/seed, seluruh penilaian kosong |
| Keputusan model | multicrop/fallback pending; fallback tidak dijalankan |

Skema `base_vs_lora_manifest.csv`, `automated_metrics.csv`, dan
`class_confusion_proxy.csv` tersedia tanpa data palsu. Evaluation notebook
menargetkan 3 prompt x 3 seed x 4 kelas untuk base dan LoRA.

## 18-21. API, Flutter, Test, dan APK

- Real FastAPI: implementasi `DiffusersImageGenerator` tersedia tetapi provider
  aktif tetap mock karena model final tidak ada.
- Flutter: konfigurasi mock/real siap; 13 test lulus dan analyze bersih.
- Test: ML/dataset 44, FastAPI 16, backend Node 16, Review UI 11, Flutter 13.
- Ruff, enam notebook, preflight, secret scan, pip check, pip-audit, dan npm
  audit lulus.
- APK LoRA final: tidak dibuat; APK lama tidak dihapus.

## 22. Blocker

- ZIP final perlu ditempatkan pada `MyDrive/skripsi_lora/datasets/`.
- Google Colab perlu dibuka secara interaktif dengan GPU T4 dan mount Drive
  disetujui pengguna.
- Smoke test harus lulus sebelum main training, evaluasi, real provider, dan
  APK LoRA boleh dilanjutkan.

## 23. Tindakan Manusia Minimum

1. Unggah `dataset_multicrop_v1.zip` ke folder Drive `datasets`, lalu buka
   notebook preparation/training di Google Colab GPU T4 dan izinkan mount
   Google Drive untuk menjalankan preparation serta smoke test.

Tidak ada checkpoint, model, metrik evaluasi, atau hasil manusia yang diklaim
tanpa bukti file nyata.
