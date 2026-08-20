# Dataset Setup - Multisource Multicrop

| Class ID | Trigger | Sumber | Target |
| --- | --- | --- | ---: |
| `padi` | `taniadaptif_padi` | `public`, `local_aikmel` | 80-100 |
| `jagung` | `taniadaptif_jagung` | `public` | 80-100 |
| `cabai` | `taniadaptif_cabai` | `public` | 80-100 |
| `kacang_tanah` | `taniadaptif_kacang_tanah` | `public` | 80-100 |

## Struktur Raw

Struktur logis:

```text
ml_pipeline/data/raw/padi/public/
ml_pipeline/data/raw/padi/local_aikmel/
ml_pipeline/data/raw/jagung/public/
ml_pipeline/data/raw/cabai/public/
ml_pipeline/data/raw/kacang_tanah/public/
```

Folder fisik jagung, cabai, dan kacang tanah saat ini menggunakan nama
`publik/`. Path tersebut dipetakan oleh YAML ke `source_type: public`; jangan
memindahkan raw hanya untuk menyeragamkan nama folder.

Tidak ada folder lokal yang perlu dibuat untuk tiga kelas public-only. Folder
`padi/local_aikmel` bersifat opsional agar pipeline tetap dapat diaudit saat
sumber lokal belum disalin.

## Provenance

Pipeline membuat atau memperbarui
`ml_pipeline/data/dataset_source_manifest.csv`. Nilai yang sudah dimasukkan
manusia dipertahankan pada rerun. Jangan mengisi URL, lisensi, pemilik, tanggal,
lokasi, atau izin berdasarkan tebakan.

## Dependency Lokal

```powershell
cd D:\TaniAdaptif
.\.venv\Scripts\python.exe -m pip install -r ml_pipeline\requirements\dev.txt
```

Dependency lokal tidak mencakup Torch, Diffusers, Transformers, Accelerate,
xFormers, atau BitsAndBytes.

## Perintah

```powershell
.\.venv\Scripts\python.exe -m ml_pipeline.src.dataset.cli audit --config ml_pipeline\configs\dataset_public_multicrop.yaml --all-classes
.\.venv\Scripts\python.exe -m ml_pipeline.src.dataset.cli prepare --config ml_pipeline\configs\dataset_public_multicrop.yaml --all-classes
.\.venv\Scripts\python.exe -m ml_pipeline.src.dataset.cli validate --config ml_pipeline\configs\dataset_public_multicrop.yaml --all-classes
.\.venv\Scripts\python.exe -m ml_pipeline.src.dataset.cli report --config ml_pipeline\configs\dataset_public_multicrop.yaml --all-classes
```

Gunakan `--class <id>` untuk audit satu kelas. Sumber public wajib tersedia;
sumber lokal padi tidak diwajibkan.

## Artefak

```text
ml_pipeline/data/processed/{train,validation}/<class>/
ml_pipeline/data/processed/{train,validation}/metadata.jsonl
ml_pipeline/data/reports/inventory_<class>.csv
ml_pipeline/data/reports/inventory_all_classes.csv
ml_pipeline/data/reports/invalid_images.csv
ml_pipeline/data/reports/exact_duplicates.csv
ml_pipeline/data/reports/near_duplicates.csv
ml_pipeline/data/reports/cross_source_duplicates_padi.csv
ml_pipeline/data/reports/cross_class_duplicates.csv
ml_pipeline/data/reports/provenance_warnings.csv
ml_pipeline/data/reports/source_distribution.csv
ml_pipeline/data/reports/curation_mapping.csv
ml_pipeline/data/reports/split_manifest.csv
ml_pipeline/data/reports/split_summary.json
artifacts/dataset_review/review_<class>.jpg
artifacts/dataset_review/manual_review_template.csv
```

Raw tidak diubah. `prepare` mengonversi salinan terkurasi ke JPEG, membatasi
80-100 per kelas, membagi train/validation 80/20 dengan seed 42, dan menjaga
kelompok duplikat tetap pada satu split.

## Caption

Caption default hanya menyatakan jenis tanaman, konteks pertanian umum, dan
pencahayaan alami. Cuaca, air, kelembapan, tahap tumbuh, dan lokasi tidak
ditambahkan tanpa provenance/observasi yang mendukung. Caption public tidak
pernah menyebut Aikmel.
