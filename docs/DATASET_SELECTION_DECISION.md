# Dataset Selection Decision

Tanggal keputusan: 2026-08-04

## Keputusan Final Tipe Sumber

| Kelas | Tipe sumber final |
| --- | --- |
| padi | gabungan `public` dan `local_aikmel` |
| jagung | `public` saja |
| cabai | `public` saja |
| kacang_tanah | `public` saja |

Tidak ada tugas, warning, atau blocker untuk mengumpulkan foto lokal jagung,
cabai, dan kacang tanah. Satu-satunya tipe lokal yang sah adalah
`local_aikmel` untuk kelas padi.

Target hasil kurasi tetap 80-100 gambar per kelas. Audit 2026-08-04 menemukan
499 kandidat raw dan menghasilkan 350 gambar terkurasi: padi 100, jagung 80,
cabai 80, dan kacang tanah 90.

## Status Identitas Sumber

Keputusan tipe sumber sudah final, tetapi identitas dataset publik, URL/ID,
lisensi, tanggal akses, dan pemilik belum tersedia dalam repository. Informasi
tersebut tidak boleh ditebak dari nama file. Foto lokal padi juga masih perlu
data tanggal, lokasi umum, izin, dan status review.

Registry kandidat lama di `ml_pipeline/configs/dataset_candidates.json`
bersifat referensi historis. Kandidat di registry tidak otomatis dianggap
sebagai sumber gambar raw yang sekarang tersedia tanpa pemetaan provenance
yang eksplisit.

## Aturan Penggunaan

- Sumber dan lisensi dicatat per gambar di
  `ml_pipeline/data/dataset_source_manifest.csv`.
- Gambar public tidak boleh diberi klaim Aikmel dalam caption.
- Gambar lokal hanya boleh masuk kelas padi.
- Gambar sintetis tidak digunakan untuk menutup kekurangan kelas.
- Raw tidak dipindahkan atau dihapus oleh pipeline.
- Review manusia tetap diperlukan untuk identitas tanaman, konteks pertanian,
  kualitas, dan dugaan duplikat.

## Trigger

Trigger final adalah `taniadaptif_padi`, `taniadaptif_jagung`,
`taniadaptif_cabai`, dan `taniadaptif_kacang_tanah`. Trigger netral ini
menggantikan keluarga `public_*`; tidak ada trigger `aikmel_*`.
