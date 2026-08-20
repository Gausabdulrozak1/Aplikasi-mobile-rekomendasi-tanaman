# Colab Resource Plan

Target runtime adalah Google Colab Free Tier dengan GPU T4 16GB. Laptop AMD
Ryzen 3 5300U hanya dipakai untuk kode, audit dataset kecil, test, backend,
Flutter, dan mock API.

## Tidak Dijalankan di Laptop

- training Stable Diffusion;
- inference Diffusers GPU;
- instalasi dependency ML besar;
- pemrosesan dataset besar berjam-jam;
- penyimpanan base model atau checkpoint.

## Baseline Colab

- Model: Stable Diffusion 1.5.
- Dataset: 80-100 gambar per kelas, empat kelas.
- Resolution: 512.
- Batch size: 1.
- Gradient accumulation: 4.
- Rank: 8.
- Steps: 1600.
- Checkpoint interval: 200.
- Checkpoint limit: 4.
- Precision: fp16.
- Gradient checkpointing: aktif.
- 8-bit Adam: aktif.
- Dataloader workers: 0.

Smoke test wajib dijalankan lebih dahulu dengan 100 langkah, checkpoint setiap
50 langkah, dan direktori output terpisah.

Baseline ini dapat disesuaikan setelah bukti runtime tersedia.

## Jalur Runtime dan Drive

```text
/content/dataset_multicrop_v1.zip
/content/taniadaptif_dataset/multicrop_v1/
MyDrive/skripsi_lora/outputs/smoke_test/
MyDrive/skripsi_lora/outputs/multicrop_v1/
MyDrive/skripsi_lora/evaluation/multicrop_v1/
MyDrive/skripsi_lora/logs/
```

Kedua path `/content` bersifat sementara dan harus dibuat kembali pada runtime
baru. Google Drive hanya menyimpan output, evaluasi, dan log persisten.

## Batas Aman

- Jangan menaikkan resolusi di atas 512 pada baseline T4.
- Pertahankan batch size 1.
- Gunakan checkpoint dan resume saat runtime terputus.
- Hentikan jika CUDA tidak tersedia.
- Jika OOM, restart runtime dan uji rank 4 sebagai eksperimen baru.
- Jangan menjalankan training bersamaan dengan pipeline evaluasi.

Output akhir yang harus diverifikasi:

```text
MyDrive/skripsi_lora/outputs/multicrop_v1/multisource_multicrop_lora.safetensors
```

Untuk development lokal, gunakan provider mock.
