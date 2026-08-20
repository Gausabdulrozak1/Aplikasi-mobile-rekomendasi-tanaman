# Colab Runbook - Pilot dan Multicrop LoRA SD 1.5

Panduan langkah demi langkah untuk pipeline otomatis tersedia di
`docs/COLAB_COMPLETE_PIPELINE_TUTORIAL.md`.

Training dan evaluasi image generation hanya dilakukan di Google Colab GPU.
Laptop lokal dipakai untuk audit ringan, test, caption, dan dokumentasi.

## Pilot Pertama: Padi Publik

Sesuai rancangan pilot, jalankan tiga notebook berikut lebih dahulu:

1. `ml_pipeline/notebooks/01_prepare_dataset_colab.ipynb`
2. `ml_pipeline/notebooks/02_train_lora_sd15_colab.ipynb`
3. `ml_pipeline/notebooks/03_evaluate_lora_colab.ipynb`

Konfigurasi pilot adalah `ml_pipeline/configs/pilot_padi.yaml`: satu kelas
`padi`, trigger `gaus_padi_public`, seed 42, rank 8, 800 langkah, dan
checkpoint setiap 200 langkah. Dataset publik pilot tidak mewakili Aikmel.

Cara menjalankan untuk pemula:

1. Buka Google Colab, pilih **File > Upload notebook**, lalu pilih notebook 01.
2. Pilih **Runtime > Change runtime type > GPU** dan verifikasi CUDA/GPU dari
   sel pemeriksaan.
3. Jalankan mount Drive dan izinkan akses akun Google secara normal.
4. Sediakan repository melalui `REPO_URL` atau upload ke `/content/TaniAdaptif`.
5. Untuk folder lokal, taruh 80-100 gambar padi berlisensi di
   `MyDrive/TaniAdaptif/dataset_lora/pilot_padi/raw/padi/`.
6. Untuk Hugging Face, pilih config contoh dan masukkan token hanya melalui
   prompt `huggingface-cli login`. Untuk Kaggle, simpan `kaggle.json` di
   `MyDrive/TaniAdaptif/secrets/`; jangan menulis token di notebook.
   Set `TANIADAPTIF_CONFIG` ke path config yang sama sebelum menjalankan setiap
   notebook pilot; train dan evaluate menghormati pilihan tersebut.

Untuk contoh Hugging Face, jalankan sel ini di awal ketiga notebook:

```python
import os

os.environ["TANIADAPTIF_CONFIG"] = (
    "ml_pipeline/configs/pilot_padi_riceseg_hf.example.yaml"
)
```
7. Jalankan notebook 01 berurutan. Processed dataset disalin persisten ke
   `MyDrive/TaniAdaptif/datasets/pilot_padi_sd15_lora_public/`.
8. Buka notebook 02, jalankan berurutan, dan jangan menutup runtime saat proses
   aktif. Output/checkpoint tersimpan di
   `MyDrive/TaniAdaptif/lora_outputs/pilot_padi/`.
9. Untuk melanjutkan runtime terputus, set
   `RESUME_FROM_CHECKPOINT = "latest"`, mount Drive, lalu jalankan ulang setup
   dan training.
10. File pilot dianggap tersedia hanya jika
    `pytorch_lora_weights.safetensors` benar-benar ada. Jalankan notebook 03
    untuk baseline versus LoRA dan isi rubric manusia setelah melihat hasil.

Notebook training memblokir runtime non-Colab/CUDA, mencatat commit Diffusers,
memakai worker data 0, dan memakai full precision dengan peringatan bila
capability GPU tidak mendukung fp16.

## Final Multicrop Notebook

Hubungkan VS Code ke runtime Google Colab melalui extension resmi. Dataset
final sudah tersedia secara persisten di:

```text
MyDrive/skripsi_lora/datasets/dataset_multicrop_v1.zip
```

Kemudian buka notebook repository berikut dan jalankan **Run All**:

`00_run_complete_lora_pipeline_colab.ipynb`

Notebook orkestrator memverifikasi ZIP Drive, menyalinnya secara atomic ke
`/content/dataset_multicrop_v1.zip`, lalu menjalankan preparation, smoke test
100 langkah, validasi artefak smoke, training utama 1.600 langkah dengan resume
checkpoint `latest`, dan evaluasi otomatis. Folder 23 bagian runtime tetap
didukung sebagai fallback. State, checkpoint, log, model, dan hasil evaluasi
disimpan di Google Drive. Tiga notebook tahap tertanam dan diverifikasi oleh
orkestrator, sehingga folder notebook di Drive tidak diperlukan.

Untuk diagnosis per tahap, jalankan berurutan:

1. `ml_pipeline/notebooks/01_prepare_public_multicrop_dataset_colab.ipynb`
2. `ml_pipeline/notebooks/02_train_public_multicrop_lora_sd15_colab.ipynb`
3. `ml_pipeline/notebooks/03_evaluate_public_multicrop_lora_colab.ipynb`

Notebook training memiliki guard Google Colab dan berhenti jika CUDA tidak
tersedia.

## Struktur Google Drive

```text
MyDrive/
  skripsi_lora/
    outputs/
      smoke_test/
      multicrop_v1/
    evaluation/
      multicrop_v1/
    logs/
```

Drive menyimpan ZIP input dan output persisten. ZIP kerja serta dataset hasil
ekstraksi berada di runtime `/content`; saat runtime dihapus, jalankan ulang
notebook 00 dan sumber Drive akan disalin kembali. Checkpoint Drive tetap
digunakan untuk resume.

## Runtime

Pilih:

```text
Runtime > Change runtime type > GPU
```

Target awal adalah T4 16GB. Notebook mencatat nama GPU dan VRAM. Jika CUDA
tidak tersedia, jangan lanjutkan training.

## Preparation

Notebook pertama:

- menyalin ZIP Drive tervalidasi ke `/content/dataset_multicrop_v1.zip`, atau
  merakitnya dari bagian runtime sebagai fallback;
- membaca `/content/dataset_multicrop_v1.zip`;
- memverifikasi expected SHA-256 dan `PACKAGE_MANIFEST.json` sebelum ekstraksi;
- memeriksa metadata, source policy, jumlah minimum per kelas, dan duplicate
  leakage;
- mengekstrak hanya paket yang lolos validasi ke storage runtime Colab;
- menampilkan ringkasan kelas dan sumber tanpa mengubah paket asal.

Jika ZIP Drive maupun folder fallback tidak tersedia atau checksum tidak cocok,
notebook berhenti dengan pesan `STOP` dan tidak mengekstrak dataset.

Output:

```text
/content/taniadaptif_dataset/multicrop_v1/
MyDrive/skripsi_lora/logs/dataset_preparation/
```

## Smoke Test

Orkestrator memilih mode smoke melalui environment tervalidasi. Mode ini:

- menjalankan tepat 100 langkah;
- membuat checkpoint setiap 50 langkah;
- menyimpan keluaran terpisah di
  `outputs/smoke_test/`;
- merekam `training.log`, `loss_log.csv`, konfigurasi aktual, environment
  report, dan `training_manifest.json`;
- membuat satu validation image untuk setiap kelas;
- menulis `status: success` hanya setelah checkpoint langkah 100, LoRA,
  loss finite, empat validation image, dan laporan tersedia.

Jangan beralih ke main training jika manifest smoke tidak berstatus sukses.

## Main Training

Setelah smoke tervalidasi, ubah `SMOKE_TEST = False`. Mode utama memakai:

- `stable-diffusion-v1-5/stable-diffusion-v1-5`;
- Diffusers `train_text_to_image_lora.py`;
- satu dataset gabungan empat kelas;
- checkpoint setiap 200 langkah;
- maksimal empat checkpoint;
- batch size 1;
- gradient accumulation 4;
- fp16, gradient checkpointing, dan 8-bit Adam;
- dataloader worker 0.

Konfigurasi:

```text
ml_pipeline/configs/training_public_multicrop.yaml
```

Nama file LoRA canonical untuk smoke dan main hanya bersumber dari key
`lora_filename` pada config tersebut. Diffusers menyimpan keluaran awal sebagai
`pytorch_lora_weights.safetensors`; notebook mempertahankan file itu, menyalin
melalui file temporer, memverifikasi hash dan isi SafeTensors, lalu memasang
nama canonical secara atomic. Canonical yang sudah valid tidak memicu training
ulang. Jika hanya checkpoint akhir yang tersedia, notebook memakai resume
`latest` untuk menyelesaikan final-save.

Output yang harus benar-benar ada sebelum training dianggap selesai:

```text
MyDrive/skripsi_lora/outputs/multicrop_v1/multisource_multicrop_lora.safetensors
```

Notebook juga menyimpan config dan environment report. Jangan mengklaim
training berhasil jika file LoRA, checkpoint langkah 1600, loss log, empat
validation image, dan manifest sukses tidak terbentuk.

## Resume

Untuk resume eksplisit, set pada notebook training:

```python
RESUME_FROM_CHECKPOINT = "latest"
```

Saat `SMOKE_TEST = False`, nilai `None` otomatis menjadi `"latest"`. Notebook
mencari dan memvalidasi checkpoint bernomor paling tinggi hanya di direktori
mode yang sedang dipilih. Checkpoint smoke dan main tidak pernah dicampur.

## Evaluasi

Notebook ketiga menggunakan 12 prompt dan tiga seed per prompt. Base model dan
LoRA memakai prompt, negative prompt, seed, steps, guidance scale, serta ukuran
gambar yang identik.

Output:

```text
MyDrive/skripsi_lora/evaluation/multicrop_v1/
  evaluation_manifest.json
  base_vs_lora_manifest.csv
  automated_metrics.csv
  class_confusion_proxy.csv
  evaluation_summary.md
  human_evaluation_template.csv
  class_confusion_review.csv
  contact_sheet_padi.png
  contact_sheet_jagung.png
  contact_sheet_cabai.png
  contact_sheet_kacang_tanah.png
```

Skor dan kelas visual diisi setelah manusia melihat hasil. Notebook tidak
mengarang `predicted_visual_class`.

## Out of Memory

Jika T4 kehabisan VRAM:

1. restart runtime;
2. pastikan batch size tetap 1;
3. pastikan gradient checkpointing aktif;
4. kurangi rank dari 8 ke 4 sebagai eksperimen baru;
5. jangan membuka pipeline evaluasi bersamaan dengan training;
6. resume dari checkpoint terakhir.

Setiap perubahan konfigurasi harus disimpan sebagai bukti eksperimen.

## Secret

- Jangan hardcode token Hugging Face.
- Jangan commit `kaggle.json`.
- Jangan menyimpan `.env` atau credential di notebook.
- Jangan memasukkan dataset, checkpoint, atau `.safetensors` ke Git.
