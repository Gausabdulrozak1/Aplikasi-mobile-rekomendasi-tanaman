# Dataset Candidates

Tanggal peninjauan web: 2026-07-28

Dataset publik di dokumen ini hanya untuk pilot. Jangan klaim sebagai
representasi lokal Aikmel.

Status lisensi harus diverifikasi ulang tepat sebelum dataset diunduh. Jika
halaman resmi tidak memperlihatkan lisensi, jangan gunakan dataset tersebut
sampai lisensinya jelas.

Registry terstruktur:

```text
ml_pipeline/configs/dataset_candidates.json
```

## Prioritas Pilot Padi

| Candidate | Platform | Komoditas | Kesesuaian | Lisensi/status | Catatan |
| --- | --- | --- | --- | --- | --- |
| `PheniX-Lab/RiceSEG` | Hugging Face | Padi | Kuat | MIT, tetapi akses gated | Gambar RGB resolusi tinggi untuk rice segmentation. Perlu login HF dan accept conditions. |
| `devshaheen/100_crops_plants_object_detection_25k_image_dataset` | Hugging Face | Padi, jagung, cabai, kacang tanah | Sedang | MIT | Mencakup kategori Rice, Maize, Chili Pepper, Groundnut. Perlu kurasi frame. |
| `CVRPDataset/CVRP` | Hugging Face | Padi | Sedang | Perlu verifikasi | Field images dan panicle images, tetapi lisensi belum terlihat jelas di hasil akses. |
| `drtawfikrrahman/prediction-of-rice-ripening-and-plant-dataset` | Kaggle | Padi | Sedang | Perlu verifikasi | Terkait fase/ripening padi; cek lisensi dan sample visual di Kaggle. |
| `minhhuy2810/rice-diseases-image-dataset` | Kaggle | Padi | Fallback | MIT terlihat dari hasil pencarian | Cenderung disease/leaf; jangan jadikan sumber utama visual lahan. |

## Kandidat Jagung

| Candidate | Platform | Kesesuaian | Lisensi/status | Catatan |
| --- | --- | --- | --- | --- |
| `devshaheen/100_crops_plants_object_detection_25k_image_dataset` | Hugging Face | Sedang | MIT | Kategori Maize tersedia. Perlu ekstraksi dan kurasi. |
| `musfiqurtuhin/BCDD` | Hugging Face | Tidak direkomendasikan untuk LoRA visual 512 | CC BY-SA 4.0 | Dataset disease classification, gambar 96x96. |
| `tirtho149/SAGE` | Hugging Face | Tidak untuk pilot | MIT | Dataset sangat besar; streaming saja jika kelak dipakai. |

## Kandidat Cabai

| Candidate | Platform | Kesesuaian | Lisensi/status | Catatan |
| --- | --- | --- | --- | --- |
| `yashparalkar/chillicam-7k` | Kaggle | Kuat untuk kelas lanjutan | MIT terlihat dari hasil pencarian | Gambar cabai dari lingkungan budidaya nyata. |
| `devshaheen/100_crops_plants_object_detection_25k_image_dataset` | Hugging Face | Sedang | MIT | Kategori Chili Pepper tersedia. |
| `ravindubandara3002/chilli-plant-diseases-dataset` | Kaggle | Fallback | CC0 terlihat dari hasil pencarian | Cenderung penyakit; perlu cek framing tanaman penuh. |

## Kandidat Kacang Tanah / Groundnut

| Candidate | Platform | Kesesuaian | Lisensi/status | Catatan |
| --- | --- | --- | --- | --- |
| `devshaheen/100_crops_plants_object_detection_25k_image_dataset` | Hugging Face | Sedang | MIT | Kategori Groundnut tersedia. |
| `warcoder/groundnut-plant-leaf-data` | Kaggle | Fallback | CC BY 4.0 terlihat dari hasil pencarian | Leaf focused. |
| `muhammadazeemabbas/groundnut-leaves-dataset` | Kaggle | Fallback | CC BY 4.0 terlihat dari hasil pencarian | Leaf focused. |
| `abhimanuer/peanut-plant-leaf-disease` | Kaggle | Fallback | MIT terlihat dari hasil pencarian | Disease/leaf focused. |

## Keputusan Sementara

Pilot pertama mengikuti spesifikasi: satu kelas, `padi`.

Urutan yang disarankan:

1. Gunakan `PheniX-Lab/RiceSEG` jika akses Hugging Face disetujui dan lisensi
   MIT masih terlihat saat pengunduhan.
2. Jika akses gated menjadi hambatan, gunakan
   `devshaheen/100_crops_plants_object_detection_25k_image_dataset`, lalu kurasi
   hanya kelas Rice.
3. Jika dua opsi di atas belum praktis, gunakan ZIP lokal berisi 80-100 gambar
   padi yang sudah diverifikasi manual sumber dan lisensinya.

## Batas Kurasi Pilot

Konfigurasi pilot membatasi jumlah gambar:

```yaml
max_images_per_class: 100
max_images_total: 100
```

Batas ini menjaga eksperimen tetap sesuai spesifikasi 80-100 gambar dan mencegah
pipeline memproses dataset besar tanpa sengaja.

## Sumber yang Dicek

- `https://huggingface.co/datasets/PheniX-Lab/RiceSEG`
- `https://huggingface.co/datasets/devshaheen/100_crops_plants_object_detection_25k_image_dataset`
- `https://huggingface.co/datasets/CVRPDataset/CVRP`
- `https://huggingface.co/datasets/musfiqurtuhin/BCDD`
- `https://huggingface.co/datasets/tirtho149/SAGE`
- `https://www.kaggle.com/datasets/drtawfikrrahman/prediction-of-rice-ripening-and-plant-dataset`
- `https://www.kaggle.com/datasets/minhhuy2810/rice-diseases-image-dataset`
- `https://www.kaggle.com/datasets/yashparalkar/chillicam-7k`
- `https://www.kaggle.com/datasets/ravindubandara3002/chilli-plant-diseases-dataset`
- `https://www.kaggle.com/datasets/warcoder/groundnut-plant-leaf-data`
- `https://www.kaggle.com/datasets/muhammadazeemabbas/groundnut-leaves-dataset`
- `https://www.kaggle.com/datasets/abhimanuer/peanut-plant-leaf-disease`
