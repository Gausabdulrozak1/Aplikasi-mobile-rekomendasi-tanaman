# Experiment Guide - Multisource Multicrop LoRA

## Pilot Padi Publik

Sebelum eksperimen multicrop, gunakan `pilot_padi.yaml` dan tiga notebook tanpa
suffix `public_multicrop`. Pilot hanya memiliki kelas padi, trigger
`gaus_padi_public`, seed 42, rank 8, 800 langkah, dan checkpoint setiap 200
langkah. Catat hasil sebagai pilot publik, bukan bukti representasi Aikmel.

## Baseline

- Experiment ID: `multisource_multicrop_lora_sd15`
- Base model: `stable-diffusion-v1-5/stable-diffusion-v1-5`
- Classes: padi, jagung, cabai, kacang tanah
- Trigger tokens: `taniadaptif_padi`, `taniadaptif_jagung`, `taniadaptif_cabai`,
  `taniadaptif_kacang_tanah`
- Resolution: 512
- Seed: 42
- Rank: 8
- Max train steps: 1600
- Checkpoint interval: 200

Parameter ini adalah baseline yang dapat diubah, bukan hasil optimasi terbaik.

## Urutan

1. Lengkapi provenance/lisensi dan review dataset yang sudah diaudit.
2. Jalankan notebook preparation multi-komoditas.
3. Periksa audit, lisensi, balance, duplicate, split, dan metadata.
4. Jalankan notebook training pada Colab GPU.
5. Pastikan `multisource_multicrop_lora.safetensors` benar-benar ada.
6. Jalankan notebook evaluasi dengan 12 prompt.
7. Isi rubric dan confusion review setelah melihat gambar.
8. Putuskan apakah satu LoRA cukup atau fallback perlu diuji.

## Bukti

- YAML dataset/training/evaluation.
- Commit Diffusers dan environment report.
- Screenshot GPU.
- Laporan dataset per kelas.
- Log dan checkpoint training.
- File LoRA akhir.
- Base versus LoRA contact sheet per kelas.
- Human evaluation dan class confusion review.

## Larangan

- Jangan mengarang skor, loss, checkpoint, atau output model.
- Jangan mengklaim gambar public sebagai dokumentasi lokal Aikmel.
- Jangan memakai Stable Diffusion untuk menentukan rekomendasi tanaman.
- Jangan menjalankan training pada laptop lokal.
