# Dataset Card Template - Multisource Multicrop

Status: isi dari bukti sumber dan laporan pipeline; jangan gunakan perkiraan.

## Identitas

- Nama eksperimen: `multisource_multicrop_lora`
- Konfigurasi: `ml_pipeline/configs/dataset_public_multicrop.yaml`
- Tanggal audit:
- Penanggung jawab kurasi:
- Tujuan: simulasi visual LoRA empat komoditas

## Sumber

Isi satu bagian untuk setiap sumber:

- `source_type` (`public` atau `local_aikmel`):
- Nama sumber:
- Pemilik/penerbit:
- URL atau identifier resmi:
- Lisensi:
- Bukti lisensi:
- Tanggal akses/capture:
- Lokasi umum (jika terdokumentasi):
- Status izin (khusus dokumentasi lokal):
- Kelas yang diambil:
- Jumlah file:
- Catatan:

Jangan menyimpulkan sumber dari nama file. `local_aikmel` hanya sah untuk padi.

## Ringkasan

| Class ID | Trigger | Sumber | Raw | Valid | Duplicate | Rejected | Curated | Train | Validation |
| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| padi | taniadaptif_padi | public + local_aikmel |  |  |  |  |  |  |  |
| jagung | taniadaptif_jagung | public |  |  |  |  |  |  |  |
| cabai | taniadaptif_cabai | public |  |  |  |  |  |  |  |
| kacang_tanah | taniadaptif_kacang_tanah | public |  |  |  |  |  |  |  |

## Kriteria Inklusi

- Komoditas benar berdasarkan review manusia.
- Konteks pertanian relevan.
- Resolusi minimal 512x512 dan format didukung.
- Sumber/lisensi/izin dapat dipertanggungjawabkan.
- Tidak rusak dan bukan duplicate yang ditolak.

## Review Manual

- Reviewer:
- Tanggal:
- Jumlah diperiksa per kelas:
- Jumlah diterima/ditolak:
- Alasan penolakan:
- Bukti contact sheet dan CSV:

Jangan mengisi hasil sebelum gambar dilihat.

## Caption

- Template:
- Bukti caption public tidak menyebut Aikmel:
- Bukti kondisi cuaca/air/tahap tumbuh tidak ditebak:
- Koreksi manual:

## Keterbatasan

- Kelengkapan provenance/lisensi:
- Bias geografis, kamera, musim, dan variasi visual:
- Ketidakseimbangan kelas:
- Keterbatasan review:
- Dataset tidak menentukan rekomendasi agronomi.

## Artefak Audit

- `dataset_source_manifest.csv`:
- `inventory_all_classes.csv`:
- `invalid_images.csv`:
- `exact_duplicates.csv`:
- `near_duplicates.csv`:
- `cross_source_duplicates_padi.csv`:
- `cross_class_duplicates.csv`:
- `provenance_warnings.csv`:
- `source_distribution.csv`:
- `curation_mapping.csv`:
- `split_manifest.csv`:
- `split_summary.json`:
- `manual_review_template.csv`:
