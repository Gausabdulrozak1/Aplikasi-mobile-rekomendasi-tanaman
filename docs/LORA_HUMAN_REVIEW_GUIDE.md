# Panduan Review Visual LoRA

Review ini menilai 36 kondisi. Setiap kondisi mempunyai dua gambar terpisah:
Base SD 1.5 dan LoRA Multicrop. Total yang wajib dinilai adalah 72 gambar.
Jangan mengubah prompt, seed, atau file gambar selama review.

## Jalankan Aplikasi Review

Dari root repository pada terminal VS Code:

```powershell
Set-Location D:\TaniAdaptif
npm run lora-review
```

Biarkan terminal tersebut tetap berjalan, lalu buka:

`http://127.0.0.1:4174`

Aplikasi hanya menerima koneksi lokal pada `127.0.0.1`. Training dan Stable
Diffusion tidak dijalankan oleh aplikasi review ini.

## Urutan Penilaian

1. Isi **Peran reviewer** dengan peran nyata, misalnya `peneliti` atau
   `ahli pertanian`.
2. Bandingkan gambar Base dan LoRA untuk kondisi yang sama.
3. Isi seluruh kontrol pada panel Base, lalu klik **Simpan Penilaian**.
4. Isi panel LoRA secara terpisah, lalu klik **Simpan Penilaian**.
5. Pindah dengan tombol **Berikutnya** atau pilih kondisi pada daftar.
6. Gunakan filter kelas dan status untuk menemukan pasangan yang belum lengkap.
7. Setelah progres mencapai 72/72, klik **Validasi 72 Penilaian**.

Tidak ada skor bawaan. Catatan boleh kosong, tetapi komoditas, dua skor,
class confusion, dan peran reviewer wajib diisi. Tombol **Hapus** mengosongkan
satu penilaian setelah konfirmasi.

Setiap simpan dan hapus membuat backup CSV lebih dahulu. Perubahan setelah
finalisasi otomatis membatalkan ringkasan lama sehingga hasil harus divalidasi
ulang. Tombol **Ekspor CSV** hanya mengunduh salinan; sumber kerja tetap:

`artifacts/model_evaluation/kaggle_run_20260820T143551Z/human_evaluation_template_local.csv`

## Rubrik

| Isian | Nilai yang sah |
| --- | --- |
| Komoditas sesuai | `Ya` bila komoditas benar, selain itu `Tidak` |
| Kualitas konteks lahan | 1-5 untuk kewajaran konteks pertanian/lahan |
| Realisme visual | 1-5 untuk realisme dan minim artefak |
| Hasil identifikasi / confusion | tidak ada, kelas yang terlihat, tanaman bercampur, atau tidak dikenali |
| Peran reviewer | peran reviewer nyata, minimal dua karakter |
| Catatan | catatan singkat; boleh kosong |

Gunakan skala 1 = sangat buruk, 2 = buruk, 3 = cukup, 4 = baik, dan 5 = sangat
baik. Nilai Base dan LoRA secara independen. Jangan menyalin metrik otomatis dan
jangan menganggap gambar yang cerah atau tajam pasti benar kelas.

Perhatikan salah kelas, tanaman campuran, bentuk daun atau buah yang tidak
wajar, gambar hasil panen atau makanan saat prompt meminta tanaman di lahan,
watermark, teks, dan konteks non-pertanian.

Nilai identifikasi yang sama dengan kelas target dihitung sebagai konfirmasi,
bukan confusion. Confusion hanya dihitung bila nilainya bukan `none` dan bukan
kelas target, termasuk `mixed` atau `unclear`.

## Validasi Akhir

Periksa progres UI dari terminal lain:

```powershell
npm run lora-review:validate
```

Gerbang lengkap UI:

```powershell
node tools/lora_review_ui/src/cli.mjs --require-complete
```

Lakukan pemeriksaan silang dengan validator Python:

```powershell
.\.venv\Scripts\python.exe -m ml_pipeline.src.evaluation.validate_human_review `
  --review-csv artifacts\model_evaluation\kaggle_run_20260820T143551Z\human_evaluation_template_local.csv `
  --report-json artifacts\model_evaluation\kaggle_run_20260820T143551Z\human_review_progress.json `
  --require-complete
```

Setelah kedua validator lulus, buat tabel analisis yang siap dipindahkan ke
BAB IV:

```powershell
.\.venv\Scripts\python.exe -m ml_pipeline.src.evaluation.analyze_human_review `
  --review-csv artifacts\model_evaluation\kaggle_run_20260820T143551Z\human_evaluation_template_local.csv `
  --output-dir artifacts\model_evaluation\kaggle_run_20260820T143551Z
```

Perintah tersebut menghasilkan:

- `human_review_analysis.json` untuk bukti terstruktur;
- `human_review_analysis.csv` untuk tabel perbandingan;
- `BAB_IV_HUMAN_REVIEW_RESULTS.md` untuk narasi dan tabel skripsi.

Gerbang final hanya lulus bila 72 baris lengkap, nilainya sah, tidak ada baris
duplikat atau parsial, dan semua gambar dapat dibuka. Setelah tombol validasi UI
berhasil, ringkasan manusia tersimpan sebagai `HUMAN_REVIEW_RESULTS.md` dan
`human_review_completion.json`. Metrik proxy tetap berada pada laporan terpisah.
Analisis memakai exact McNemar untuk benar/salah komoditas dan exact sign test
untuk skor berpasangan. Nilai p dilaporkan sebagai eksplorasi, bukan bukti
ketepatan agronomi atau hubungan kausal.

Tekan `Ctrl+C` pada terminal server untuk menghentikan aplikasi setelah review.
