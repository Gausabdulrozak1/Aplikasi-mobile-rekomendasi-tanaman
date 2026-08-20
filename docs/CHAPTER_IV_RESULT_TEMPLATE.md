# Draf Bukti Hasil BAB IV

Status: dokumen kerja, bukan BAB IV final. Finalisasi narasi menunggu inference
end-to-end nyata dan screenshot Android.

Tanggal bukti: 2026-08-21. Dokumen ini memuat hasil teknis yang sudah tersedia.
Sesuaikan penomoran dan gaya bahasa dengan BAB I-III skripsi sebelum dimasukkan
ke naskah final. Nilai human review visual sudah tersedia; validasi ahli dan
UAT tetap kosong sampai kegiatan tersebut benar-benar dilakukan.

## 4.1 Lingkungan Implementasi

| Item | Hasil aktual | Bukti |
| --- | --- | --- |
| Perangkat lokal | Python 3.11 dan toolchain aplikasi tersedia; tidak dipakai untuk training Stable Diffusion | `STATUS.md` |
| Runtime training | Kaggle, run `20260820T143551Z` | `artifacts/model_evaluation/kaggle_run_20260820T143551Z/final_training_report.json` |
| GPU | 2 x Tesla T4; VRAM GPU utama yang dilaporkan 14,56 GiB | `final_training_report.json` |
| CUDA/PyTorch | CUDA 12.8; PyTorch 2.10.0+cu128 | `final_training_report.json` |
| Base model | `stable-diffusion-v1-5/stable-diffusion-v1-5` | `training_config.json` |
| Diffusers | exact commit `0f252be0ed42006c125ef4429156cb13ae6c1d60` | `final_training_report.json`, log Kaggle |
| Smoke test | 100 langkah, 250,79 detik (4 menit 10,79 detik) | `smoke_validation.json` |
| Training utama | 1.600 langkah, 3.346,29 detik (55 menit 46,29 detik) | `main_validation.json` |
| Pipeline lengkap | 4.255,92 detik (70 menit 55,92 detik) | timestamp event awal dan `complete_pipeline_state.json` |

Pipeline dijalankan sepenuhnya pada GPU Kaggle. Laptop AMD Ryzen 3 5300U hanya
dipakai untuk sinkronisasi notebook, pemantauan log, pengunduhan, pemeriksaan
hash, dan penyusunan bukti.

## 4.2 Hasil Dataset

| Kelas | Diaudit | Kandidat review | Diterima manusia | Final | Train | Validation |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| padi | 249 | 100 | 95 | 95 | 76 | 19 |
| jagung | 130 | 130 | 101 | 100 | 80 | 20 |
| cabai | 120 | 120 | 97 | 97 | 78 | 19 |
| kacang_tanah | 125 | 125 | 97 | 97 | 78 | 19 |
| **Total** | **624** | **475** | **390** | **389** | **312** | **77** |

Review menghasilkan 390 gambar diterima, 85 ditolak, 0 unsure, dan 0 pending.
Jagung dibatasi secara deterministik menjadi 100 gambar dengan seed 42. Data
padi final terdiri atas 70 gambar publik dan 25 gambar lokal Aikmel, sedangkan
tiga kelas lain hanya menggunakan gambar publik.

Paket awal `dataset_multicrop_v1.zip` berukuran 188.356.224 byte dengan SHA-256
`f6aa060658cf95e48996f10f0ffde200938d340dd15e6b60adace5bb5cecfb33`.
Untuk Kaggle dibuat paket fixed dengan logical SHA-256
`e232f79d2f8ae20b4fb765efb38435ce05e929406e88faba6b02aaaafd1ad42d`.
Perbaikan hanya menormalkan nama kolom/path metadata yang bertabrakan dengan
konvensi Hugging Face ImageFolder; byte dari seluruh 389 gambar, caption, kelas, split,
trigger, provenance, dan keputusan review tidak diubah. Validasi fisik berhasil
untuk 312/312 gambar train dan 77/77 gambar validation.

## 4.3 Rule Engine dan BMKG

Mesin aturan Node.js tetap menjadi sumber keputusan rekomendasi. Stable
Diffusion dan LoRA hanya menghasilkan visualisasi tanaman yang sudah dipilih
oleh mesin aturan. Uraikan 30 baris decision table, rule ID, timestamp BMKG,
perilaku nilai hujan kosong, cache fallback, serta keterbatasan horizon prakiraan
dengan mengutip `docs/DECISION_TABLE.md`. Jangan menyatakan validasi ahli
agronomi sebelum lembar bertanda tangan tersedia.

## 4.4 Training LoRA

Training menggunakan resolusi 512 x 512, rank 8, batch size 1, gradient
accumulation 4, learning rate 0,0001, seed 42, mixed precision fp16, dan
optimizer AdamW 8-bit. Smoke test mencapai checkpoint-100 dan berstatus `pass`.
Training utama kemudian mencapai checkpoint-1600 dan berstatus `success`.
Keduanya memiliki return code 0, loss finite, checkpoint valid, dan output LoRA
canonical valid.

| Bukti loss | Smoke | Main |
| --- | ---: | ---: |
| Observasi log | 501 | 8.001 |
| Nilai pertama | 0,782000 | 0,782000 |
| Nilai terakhir | 0,288000 | 0,004310 |
| Rata-rata | 0,196618 | 0,186001 |
| Median | 0,129000 | 0,113000 |
| Rata-rata 100 awal | 0,198757 | 0,198757 |
| Rata-rata 100 akhir | 0,191906 | 0,180415 |

Loss bersifat fluktuatif dan hanya digunakan sebagai bukti proses optimisasi;
nilai ini bukan skor kualitas perseptual.

Model akhir bernama `multisource_multicrop_lora.safetensors`, berukuran
6.414.992 byte, berisi 256 tensor, dan memiliki SHA-256
`0bda8908d577513110c22cf5ec1b8a7e008d2b26dd90525732a5c4e4b1bdd43a`.
Empat sanity image berhasil dibuat dan divalidasi. ZIP hasil berukuran
51.940.573 byte dengan SHA-256
`54ee68fccbb88be07a089365c2e62f9e6004e2774992973debe665d5dc0eb26a`.
Validator lokal menguji CRC ZIP, 100 file, seluruh hash manifest, struktur
SafeTensors, 76 PNG, CSV, JSON, loss, dan status pipeline tanpa memuat model.

## 4.5 Evaluasi Otomatis dan Visual

Evaluasi menghasilkan 36 kondisi, masing-masing memakai satu gambar base dan
satu gambar LoRA dengan prompt, seed, langkah inferensi, guidance, dan resolusi
yang sama. Total 72/72 gambar valid.

| Variant | Gambar | Brightness mean | Contrast mean | Entropy mean |
| --- | ---: | ---: | ---: | ---: |
| Base | 36 | 90,883615 | 60,444080 | 9,008533 |
| LoRA | 36 | 97,651167 | 62,275424 | 9,104648 |

Brightness, contrast, dan entropy adalah statistik proxy deskriptif. Ketiganya
tidak membuktikan identitas tanaman, realisme, ketepatan agronomi, atau bahwa
LoRA lebih baik daripada base model. Contact sheet per kelas tersedia di
`artifacts/model_evaluation/kaggle_run_20260820T143551Z/contact_sheets/`.

Pemeriksaan QA pendahuluan tidak digunakan sebagai skor. Review manusia final
telah disimpan pada `human_evaluation_template_local.csv`; provenance analyzer
menyatakan `automated_scores=false`.

### 4.5.1 Evaluasi Manusia Berpasangan

Review 72/72 dan analyzer telah selesai dengan status
`complete_validated_human_review`. Input terdiri dari 36 pasangan Base-vs-LoRA
dengan prompt dan seed identik serta sembilan kondisi per kelas. Hasil resmi
tersedia di `human_review_analysis.json`, `human_review_analysis.csv`, dan
`BAB_IV_HUMAN_REVIEW_RESULTS.md` pada folder run `20260820T143551Z`.

Ringkasan aktual: identifikasi benar Base 31/36 (86,11%) dan LoRA 34/36
(94,44%), selisih +8,33 poin persentase, exact McNemar p=0,25. Median konteks
dan realisme keseluruhan adalah 4,5 untuk Base dan 4,0 untuk LoRA. Statistik per
kelas dan exact sign test harus diambil langsung dari output analyzer.

Ketepatan komoditas dibandingkan dengan exact McNemar pada pasangan discordant.
Skor konteks lahan dan realisme bersifat ordinal, sehingga median menjadi
ringkasan utama dan arah perbedaan diuji menggunakan exact sign test dengan tie
dikeluarkan. Mean tetap ditampilkan secara deskriptif. Nilai p harus disebut
eksploratif dan tidak boleh ditafsirkan sebagai validasi agronomi atau hubungan
kausal. Hasil ini belum menjadikan dokumen sebagai BAB IV final karena gerbang
aplikasi nyata masih tertunda.

## 4.6 Verifikasi Aplikasi

Provider FastAPI lokal tetap `mock` agar laptop tidak memuat Stable Diffusion.
Kontrak Flutter -> Express -> FastAPI mock -> Express PNG telah lulus, tetapi
bukan bukti model nyata. `DiffusersImageGenerator` belum boleh dilaporkan aktif
sebelum `gpu_preflight.json` dan `real_inference_e2e_report.json` berstatus
`success`, lalu screenshot Android memperlihatkan gambar yang selesai dimuat.
Fixture otomatis bukan UAT petani; validasi ahli dan UAT tetap memerlukan bukti
manusia.

## 4.7 Diskusi dan Keterbatasan

Keterbatasan yang wajib disebutkan meliputi horizon prakiraan BMKG, ketidakpastian
proyeksi mingguan, dominasi sumber publik, citra lokal hanya pada sebagian data
padi, warning provenance lama, ukuran sampel empat kelas, keterbatasan visual
generatif, potensi class confusion, ukuran review, serta belum tersedianya bukti
inference Android nyata. Deployment memakai model gabungan final tanpa
retraining. Kebutuhan adapter fallback tidak diuji pada tahap ini dan tidak
boleh diklaim dari metrik proxy saja.
