# Catatan Revisi Dataset untuk BAB III

Tanggal verifikasi terakhir: 2026-08-13

## Pernyataan Sumber Final

> Dataset visual penelitian terdiri atas gambar publik untuk padi, jagung,
> cabai, dan kacang tanah. Dokumentasi lokal Aikmel digunakan sebagai tambahan
> pada kelas padi. Kelas jagung, cabai, dan kacang tanah menggunakan dataset
> publik dan tidak dimaksudkan sebagai representasi visual khusus wilayah
> Aikmel.

Tidak ada foto lokal jagung, cabai, atau kacang tanah. Ketidakhadiran sumber
lokal pada tiga kelas tersebut bukan kegagalan dataset.

## Populasi, Review, dan Kurasi

Audit final mencakup 624 gambar teknis: padi 249, jagung 130, cabai 120, dan
kacang tanah 125. Sebanyak 475 gambar masuk review manusia. Hasil review adalah
390 accepted, 85 rejected, 0 unsure, dan 0 pending.

| Kelas | Kandidat review | Accepted | Rejected | Dipilih final |
| --- | ---: | ---: | ---: | ---: |
| padi | 100 | 95 | 5 | 95 |
| jagung | 130 | 101 | 29 | 100 |
| cabai | 120 | 97 | 23 | 97 |
| kacang_tanah | 125 | 97 | 28 | 97 |

Satu gambar jagung dikeluarkan oleh batas maksimum 100 secara deterministik
dengan seed 42, bukan karena keputusan reviewer diubah. Dataset final berisi
389 gambar. Screening CPU mencatat 447 proxy-pass dan 28 proxy-review; status
proxy bukan keputusan manusia.

## Audit dan Provenance

Audit memeriksa Pillow decoding, truncation, format, mode warna, resolusi
minimum, SHA-256, perceptual hash, exact/near duplicate, duplicate lintas
sumber/kelas, benturan nama, dan EXIF orientation. Tidak ada duplicate-group
yang bocor antara train dan validation.

Provenance 125 kandidat tambahan berasal dari tiga dataset Mendeley CC BY 4.0
dan tercatat lengkap. Sebagian baris inventori lama masih memiliki warning
provenance; nilai yang tidak diketahui tidak diisi dengan asumsi.

## Split, Caption, dan Trigger

Split final memakai rasio 80:20 dan seed 42:

| Kelas | Train | Validation |
| --- | ---: | ---: |
| padi | 76 | 19 |
| jagung | 80 | 20 |
| cabai | 78 | 19 |
| kacang tanah | 78 | 19 |

Padi train memuat 56 public dan 20 local_aikmel; validation memuat 14 public
dan 5 local_aikmel. Tiga kelas lain public-only.

Trigger final adalah `taniadaptif_padi`, `taniadaptif_jagung`,
`taniadaptif_cabai`, dan `taniadaptif_kacang_tanah`. Trigger merupakan
identifier model, bukan klaim lokasi. Caption tidak menebak cuaca, curah hujan,
kelembapan, air, fase tumbuh, jenis tanah, atau lokasi gambar publik.

## Paket Final

- File: `dataset_multicrop_v1.zip`
- Ukuran: 188356224 byte
- SHA-256: `f6aa060658cf95e48996f10f0ffde200938d340dd15e6b60adace5bb5cecfb33`
- Metadata train: 312 baris valid
- Metadata validation: 77 baris valid
- Trigger silang: 0
- Duplicate leakage: 0
- Status validator: valid; `training_allowed=true`

## Batas Klaim

- LoRA hanya akan menghasilkan simulasi visual.
- Rekomendasi tanaman tetap berasal dari rule-based engine dan data BMKG.
- Audit teknis tidak membuktikan validasi ahli atau respons petani.
- Tiga kelas public-only tidak mewakili visual khusus Aikmel.
- Training dan evaluasi belum dilakukan; kualitas LoRA belum dapat diklaim.
- Google Drive sudah disiapkan, tetapi runtime Colab GPU belum tersedia dan ZIP
  besar masih perlu diunggah secara interaktif.
