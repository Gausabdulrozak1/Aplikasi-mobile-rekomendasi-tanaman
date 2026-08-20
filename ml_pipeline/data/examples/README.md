# Metadata Examples

Folder ini hanya berisi contoh teks metadata untuk review. Tidak ada gambar
training nyata di folder ini.

Metadata runtime dibuat pada:

```text
ml_pipeline/data/processed/train/metadata.jsonl
ml_pipeline/data/processed/validation/metadata.jsonl
```

Setiap baris memiliki `file_name`, `text`, `class_id`, `trigger_token`,
`source_type`, `is_local_aikmel`, `location_general`, dan `duplicate_group`.
Caption berisi tepat satu trigger kelas:

```text
taniadaptif_padi
taniadaptif_jagung
taniadaptif_cabai
taniadaptif_kacang_tanah
```

Lihat `metadata_multicrop_example.jsonl`. Kondisi cuaca, air, tahap tumbuh,
dan lokasi tidak ditambahkan tanpa bukti provenance/observasi.
