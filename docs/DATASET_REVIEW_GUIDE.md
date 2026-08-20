# Panduan Review Dataset

## Mulai Review

1. Buka PowerShell pada `D:\TaniAdaptif`, lalu jalankan:

   ```powershell
   npm run dataset-review
   ```

2. Buka `http://127.0.0.1:4173`.
3. Lihat gambar dan informasi kandidat.
4. Tekan **Terima** atau **Tolak**. Gunakan **Ragu** hanya untuk kandidat yang
   perlu diperiksa kembali.
5. Ulangi sampai seluruh kandidat memiliki keputusan Terima atau Tolak.
6. Klik **Finalisasi Review**.
7. Tunggu status pipeline selesai pada aplikasi review.
8. Lihat hasil pada `ml_pipeline/data/reports/` dan, jika seluruh kelas
   memenuhi minimum, `artifacts/dataset_packages/`.

Keputusan tersimpan otomatis. Aplikasi dapat ditutup lalu dilanjutkan kembali.
Backup dibuat sebelum perubahan pertama di
`artifacts/dataset_review/backups/`, sedangkan progres berada di
`artifacts/dataset_review/review_progress.json`.

## Keputusan

- **Terima**: komoditas dan tanaman terlihat, dapat dikenali, cukup jelas, dan
  memberi variasi visual yang berguna.
- **Tolak**: kelas salah, tanaman tidak terlihat, hanya hasil panen/makanan,
  gambar pasar, terlalu buram, watermark besar, tertutup berat, tidak terkait,
  atau jelas sintetis.
- **Ragu**: keputusan sementara. Status ini memblokir finalisasi sampai diubah
  menjadi Terima atau Tolak.

Untuk penolakan, pilih satu atau lebih alasan yang tersedia sebelum menekan
Tolak bila sesuai. Jangan menebak alasan yang tidak terlihat pada gambar.

## Validasi

Validasi struktur CSV tanpa mengubah keputusan:

```powershell
npm run dataset-review:validate
```

Finalisasi otomatis hanya berjalan ketika 350 kandidat valid dan semuanya
berstatus `yes` atau `no`. Jika kelas memiliki kurang dari 80 gambar diterima,
pipeline melaporkan kekurangan secara tepat dan tidak membuat ZIP. Pipeline ini
tidak menjalankan training Stable Diffusion pada laptop.
