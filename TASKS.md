# TASKS - TaniAdaptif Stable Diffusion LoRA Pipeline

## Audit dan Scaffolding

- [x] Audit struktur repository awal.
- [x] Identifikasi lokasi Flutter: `mobile-flutter/tani_adaptif`.
- [x] Identifikasi state management Flutter: `setState` langsung, belum memakai Provider/BLoC/Riverpod.
- [x] Identifikasi service HTTP Flutter: `lib/services/api_service.dart` memakai Dio.
- [x] Identifikasi halaman rekomendasi: `lib/screens/hasil_screen.dart`.
- [x] Identifikasi rule-based engine: `backend-nodejs/src/services/rekomendasiService.js`.
- [x] Identifikasi integrasi BMKG: `backend-nodejs/src/services/bmkgService.js`.
- [x] Identifikasi AI server awal: `backend-python/main.py` masih mock sederhana.
- [x] Buat struktur `ml_pipeline/`, `inference_api/`, `docs/`, dan `artifacts/`.
- [x] Update `.gitignore` untuk secret, dataset, archive, checkpoint, model, cache, dan generated image.
- [x] Buat `TASKS.md`.
- [x] Buat `STATUS.md`.

## Dataset Pipeline

- [x] Buat konfigurasi pilot padi `ml_pipeline/configs/pilot_padi.yaml`.
- [x] Pisahkan trigger pilot publik `gaus_padi_public` dari trigger final
  multicrop `taniadaptif_*`.
- [x] Buat source adapter untuk local directory, ZIP, Hugging Face, dan Kaggle.
- [x] Buat inventory gambar.
- [x] Buat validasi gambar rusak, resolusi, ekstensi, mode warna, file kosong, dan exact duplicate.
- [x] Buat deteksi duplikasi exact dan perceptual hash.
- [x] Buat kurasi dataset tanpa memodifikasi raw source.
- [x] Buat split train/validation reproducible.
- [x] Buat caption berbasis template ke `metadata.jsonl`.
- [x] Buat validasi metadata.
- [x] Buat dataset report JSON, CSV, dan Markdown.
- [x] Buat CLI `audit`, `prepare`, `caption`, dan `report`.
- [x] Buat fixture test gambar kecil.
- [x] Buat automated tests dataset pipeline.
- [x] Buat `docs/DATASET_CANDIDATES.md`.
- [x] Verifikasi ulang kandidat dataset publik melalui web pada 2026-07-28.
- [x] Tambahkan registry kandidat dataset terstruktur.
- [x] Tambahkan validator registry kandidat dataset.
- [x] Tambahkan batas `max_images_per_class` dan `max_images_total` untuk pilot 80-100 gambar.
- [x] Pindahkan cache unduhan Hugging Face/Kaggle ke `ml_pipeline/data/downloads/`.
- [x] Tambahkan contoh config Hugging Face RiceSEG gated untuk pilot padi.

## Google Colab Notebooks

- [x] Buat `ml_pipeline/notebooks/01_prepare_dataset_colab.ipynb`.
- [x] Buat `ml_pipeline/notebooks/02_train_lora_sd15_colab.ipynb`.
- [x] Buat `ml_pipeline/notebooks/03_evaluate_lora_colab.ipynb`.
- [x] Tambahkan checkpoint dan resume di notebook training.
- [x] Tambahkan validasi GPU/CUDA/VRAM/RAM/disk.
- [x] Tambahkan instruksi autentikasi Kaggle/Hugging Face tanpa token hardcoded.
- [x] Tambahkan flow clone/load repo yang jelas di seluruh notebook Colab.
- [x] Pastikan training notebook memakai `rank` dari config.
- [x] Buat `docs/COLAB_RUNBOOK.md`.
- [x] Persistensikan processed dataset pilot ke Drive dan tambahkan guard
  Colab/CUDA, pin Diffusers, serta fallback precision.
- [x] Tambahkan validator CPU-only untuk checkpoint, LoRA, loss, log,
  environment, manifest, dan validation image hasil Colab.

## Evaluasi dan Reproducibility

- [x] Buat modul evaluasi prompt YAML.
- [x] Buat manifest eksperimen.
- [x] Buat contact sheet.
- [x] Buat template penilaian manusia.
- [x] Buat report Markdown.
- [x] Tambahkan contoh prompt evaluasi ringan di `artifacts/samples/`.
- [x] Tambahkan template CSV evaluasi manusia di `artifacts/evaluation/`.
- [x] Buat `docs/EXPERIMENT_GUIDE.md`.
- [x] Buat `docs/MODEL_CARD.md`.
- [x] Buat `docs/THESIS_EVIDENCE.md`.
- [x] Buat `docs/RUN_COMMANDS.md`.
- [x] Buat `artifacts/reports/experiment_log_template.csv`.

## FastAPI Inference API

- [x] Buat FastAPI baru di `inference_api/`.
- [x] Implementasikan `MockImageGenerator`.
- [x] Implementasikan `DiffusersImageGenerator`.
- [x] Tambahkan endpoint `GET /health`.
- [x] Tambahkan endpoint `GET /v1/model-info`.
- [x] Tambahkan endpoint `POST /v1/generate`.
- [x] Dukung payload structured-context untuk Flutter dan payload direct-prompt
  terbatas untuk kompatibilitas pilot tanpa memindahkan rekomendasi ke AI.
- [x] Tambahkan static file serving untuk development.
- [x] Tambahkan `.env.example`.
- [x] Tambahkan Dockerfile.
- [x] Tambahkan pytest untuk health, generate, dan invalid input.
- [x] Tambahkan pre-load gate `LORA_SHA256` dan validasi SafeTensors agar host
  GPU menolak model rusak sebelum mengunduh base model.
- [x] Buat `gpu.env.example` dengan identifier dan SHA model final serta pin
  dependency inference non-Torch yang kompatibel.
- [x] Buat `docs/API_CONTRACT.md`.

## Integrasi Flutter

- [x] Buat model `GenerateVisualRequest`.
- [x] Buat model `GenerateVisualResponse`.
- [x] Buat service inference visual memakai Dio.
- [x] Gunakan `String.fromEnvironment` untuk base URL inference API.
- [x] Kirim konteks rekomendasi terstruktur dari Flutter dan bangun prompt serta
  trigger token di FastAPI.
- [x] Tambahkan loading, timeout, retry, error, dan fallback.
- [x] Pastikan kegagalan visual tidak menghilangkan rekomendasi.
- [x] Tambahkan test request serialization, response parsing, error parsing, dan prompt generator.
- [x] Tambahkan mock integration test untuk service inference visual.

## Validasi Akhir

- [x] Jalankan Python tests.
- [x] Tambahkan contoh `metadata.jsonl` yang aman disimpan di Git.
- [x] Tambahkan panduan Python lokal aman tanpa training SD.
- [x] Tambahkan panduan resource Colab T4 16GB.
- [x] Tambahkan smoke test mock API untuk PowerShell.
- [x] Jalankan notebook JSON validation.
- [x] Tambahkan dan jalankan `ml_pipeline/scripts/validate_notebooks.mjs`.
- [x] Tambahkan dan jalankan `ml_pipeline/scripts/security_scan.mjs`.
- [x] Tambahkan preflight checker ringan tanpa Python/GPU.
- [x] Jalankan secret scan sederhana.
- [x] Jalankan `dart format`.
- [x] Jalankan `flutter analyze`.
- [x] Jalankan `flutter test`.
- [x] Update `STATUS.md` dengan hasil aktual.

## Refactor Dataset Multisource Empat Komoditas

- [x] Audit ulang repository setelah Python 3.11 dan `.venv` tersedia.
- [x] Pertahankan pipeline pilot padi sebagai smoke test legacy.
- [x] Tetapkan padi sebagai public + local_aikmel.
- [x] Tetapkan jagung, cabai, dan kacang tanah sebagai public-only.
- [x] Gunakan trigger `taniadaptif_padi`, `taniadaptif_jagung`, `taniadaptif_cabai`, dan
  `taniadaptif_kacang_tanah`.
- [x] Refactor inventory ke metadata kelas dan kolom audit lengkap.
- [x] Buat inventory per kelas dan gabungan.
- [x] Deteksi exact duplicate dan near duplicate lintas kelas.
- [x] Pastikan raw dataset tidak dimodifikasi.
- [x] Buat kurasi nama konsisten empat digit dan mapping nama.
- [x] Buat class balance report dan peringatan target/balance.
- [x] Buat stratified split reproducible dengan duplicate-group isolation.
- [x] Buat `split_manifest.csv`, `split_summary.json`, dan `split_summary.md`.
- [x] Buat caption netral per kelas dan metadata train/validation.
- [x] Validasi missing caption, invalid JSON, class ID, dan trigger silang.
- [x] Tambahkan CLI `audit`, `prepare`, `validate`, dan `report`.
- [x] Tambahkan filter `--class` dan `--all-classes`.
- [x] Tambahkan fixture dinamis multisource dan 28 automated tests.
- [x] Tambahkan konfigurasi training/evaluation multi-komoditas.
- [x] Tambahkan tiga notebook Colab multi-komoditas.
- [x] Tambahkan 12 validation prompts dan confusion review.
- [x] Dokumentasikan fallback empat LoRA tanpa menjalankan training fallback.
- [x] Perbarui dokumentasi setup, dataset card, strategi, Colab, evaluasi,
  model card, dan bukti skripsi.
- [x] Validasi notebook dengan `nbformat`.
- [x] Jalankan Ruff lint dan format check.
- [x] Pastikan dependency ML besar tidak terpasang di `.venv`.

## Audit Dataset Nyata 2026-08-04

- [x] Audit 499 gambar raw tanpa memodifikasi sumber.
- [x] Buat dan isi struktur dasar 499 baris
  `ml_pipeline/data/dataset_source_manifest.csv` tanpa mengarang fakta.
- [x] Tambahkan laporan provenance, distribusi sumber, duplicate lintas sumber
  padi, duplicate lintas kelas, dan benturan nama.
- [x] Ganti average-hash yang menghasilkan false positive dengan
  difference-hash dua arah 128-bit.
- [x] Verifikasi 499 valid teknis, 0 invalid, 0 exact duplicate, dan 0 near
  duplicate pada ambang 5.
- [x] Kurasi staging 350 kandidat teknis: padi 100, jagung 80, cabai 80,
  kacang tanah 90.
- [x] Batalkan split pra-gerbang 280/70 agar tidak dianggap dataset final.
- [x] Terapkan hard gate review sebelum split, metadata final, dan packaging.
- [x] Buat 18 contact sheet berisi seluruh 350 kandidat, 20 gambar per halaman.
- [x] Buat 350 baris template review dan pastikan seluruh keputusan manusia
  tetap kosong.
- [x] Tambahkan kolom provenance URL, tanggal akses, dan fotografer tanpa
  mengarang nilainya.
- [x] Tambahkan audit EXIF orientation dan konten sama dengan ekstensi berbeda.
- [x] Tambahkan laporan `audit_summary.md` dan format mapping kurasi final.
- [x] Tambahkan guard paket untuk review belum selesai dan metadata invalid.
- [x] Ubah notebook preparation agar hanya membaca paket final tervalidasi.
- [x] Verifikasi sidik integritas raw identik sebelum/sesudah prepare.
- [x] Tambahkan `docs/THESIS_DATASET_REVISION_NOTES.md`.

## Pekerjaan Manual yang Belum Dilakukan

- [ ] Isi `source_name`, `source_identifier`, URL/ID, dan lisensi yang
  terverifikasi untuk gambar public pada source manifest.
- [ ] Isi tanggal, lokasi umum, izin, dan bukti hak penggunaan foto lokal padi.
- [x] Lakukan review manusia pada 350 kandidat tanpa mengarang hasil.
- [x] Terapkan hasil terima/tolak ke mapping lalu jalankan ulang prepare.
- [x] Tambahkan kandidat publik berlisensi untuk menutup kekurangan accepted:
  jagung 29, cabai 23, dan kacang tanah 18; siapkan lebih dari jumlah minimum
  karena kandidat tambahan tetap harus diaudit dan direview. Tersedia 50
  jagung, 40 cabai, dan 35 kacang tanah pada `additional_batch_v1`.
- [x] Review 125 kandidat `additional_batch_v1` tanpa mengulang 350 keputusan lama.
- [x] Buat split final hanya jika setiap kelas memiliki minimal 80 gambar
  diterima.
- [x] Validasi metadata final dan buat `dataset_multicrop_v1.zip` hanya setelah
  seluruh gate lulus.
- [x] Upload paket final dan checksum ke struktur Google Drive notebook.
  Struktur, ZIP 188.356.224 byte, checksum, dan empat notebook sudah tersedia.
- [x] Selaraskan kontrak Flutter/FastAPI dengan empat trigger final tanpa
  mengubah keputusan rule-based.
- [x] Jalankan training LoRA gabungan pada remote GPU Kaggle.
- [x] Verifikasi `multisource_multicrop_lora.safetensors` benar-benar terbentuk,
  berisi 256 tensor, dan hash canonical cocok.
- [x] Jalankan evaluasi base versus LoRA: 36 kondisi dan 72 gambar valid.
- [x] Isi rubric manusia dan class confusion review untuk 72/72 gambar.
- [ ] Putuskan kebutuhan fallback empat adapter dari hasil evaluasi nyata.

Tidak ada task untuk mengumpulkan foto lokal jagung, cabai, atau kacang tanah.

## Gerbang LoRA 2026-08-13

- [x] Validasi ulang 350 keputusan review: 265 yes, 85 no, 0 unsure, 0 pending.
- [x] Tambahkan perintah `validate-package` dan laporan final Markdown/JSON.
- [x] Catat status paket `blocked` tanpa membuat split/metadata/ZIP palsu.
- [x] Selaraskan notebook final dengan struktur Drive `outputs/`, checksum
  wajib, `SMOKE_TEST`, resume checkpoint tervalidasi, dan tiga seed evaluasi.
- [x] Siapkan output evaluasi base-vs-LoRA, metrik proxy, confusion proxy,
  ringkasan, contact sheet, dan template manusia kosong di notebook.
- [x] Deteksi akses GPU otomatis tanpa membaca atau menampilkan token; tidak
  ditemukan sesi remote GPU terautentikasi.
- [x] Tambahkan 125 kandidat publik berlisensi sebagai `additional_batch_v1`.
- [x] Review `additional_batch_v1` sampai setiap kelas mencapai minimum 80
  gambar diterima.
- [x] Jalankan ulang finalisasi dan pastikan `validate-package` berstatus valid.
- [x] Uji pendekatan awal upload ZIP/checksum ke Drive; pendekatan ini kemudian
  digantikan input runtime Colab langsung pada 2026-08-14.
- [x] Buat struktur output Drive dan empat notebook final; notebook/input Drive
  tidak lagi diwajibkan oleh orkestrator terbaru.
- [x] Buat dan unggah notebook orkestrator preparation, smoke test 100 langkah,
  validasi smoke, training utama 1.600 langkah, dan evaluasi otomatis.
- [x] Hilangkan kebutuhan clone repository dari notebook training/evaluation;
  config dibaca dari hasil preparation di Drive.
- [x] Siapkan 36 pasangan prompt/seed untuk evaluasi tanpa mengisi hasil palsu.
- [x] Jalankan smoke test final 100 langkah pada Kaggle, lalu validasi
  artefaknya.
- [x] Perbaiki kontrak filename default Diffusers versus nama LoRA canonical,
  termasuk normalisasi aman, resume checkpoint, dan regression test CPU-only.
- [x] Perbaiki konflik dependency Diffusers v0.35.1/PEFT dan source replacement
  orkestrator berdasarkan traceback aktual Google Drive.
- [x] Perbaiki kontrak logger Accelerate dari nilai `none` yang tidak didukung
  menjadi TensorBoard lokal dan tambahkan regression test.
- [x] Perbaiki konflik TorchAO 0.10.0 bawaan Colab dengan PEFT berdasarkan
  traceback aktual dan tambahkan dependency gate serta regression test.
- [x] Tambahkan tutorial lengkap rerun/resume pipeline Colab.
- [x] Jalankan training utama 1.600 langkah setelah smoke test lulus pada run
  Kaggle final.

## Gerbang Runtime Colab Langsung 2026-08-14

Catatan: item runtime Colab yang belum selesai di bagian ini dipertahankan
sebagai riwayat dan telah digantikan oleh jalur Kaggle final di bagian berikut.

- [x] Ubah input final menjadi `/content/dataset_multicrop_v1.zip` dan validasi
  SHA-256 sebelum preparation.
- [x] Pindahkan dataset kerja ke runtime Colab; batasi Drive untuk output,
  evaluasi, dan log persisten.
- [x] Jadikan notebook 00 mandiri dengan snapshot notebook 01-03 yang
  diverifikasi checksum dan nbformat.
- [x] Pertahankan smoke 100, main 1.600, checkpoint, resume `latest`, evaluasi
  base-vs-LoRA, dan filename LoRA canonical dari config.
- [x] Tambahkan regression test path runtime dan kontrak notebook tertanam.
- [x] Diagnosis upload ZIP tunggal yang ditolak Jupyter Contents API dengan
  `400 Bad Request`; siapkan 23 bagian 8 MiB beserta manifest dan rakitan atomic.
- [x] Diagnosis traceback smoke terbaru dari Drive: import W&B bawaan Colab
  gagal karena konflik protobuf sebelum step 1; isolasi W&B/TorchAO dan tambah
  import probe entrypoint training pada revision v5.
- [x] Tambahkan sumber dataset persisten dari ZIP tervalidasi yang sudah ada di
  Drive; folder potongan runtime tetap tersedia sebagai fallback revision v6.
- [ ] Jalankan notebook 00 revision v8 pada Colab T4 dan validasi smoke 100.

## Migrasi Kaggle Final 2026-08-14

- [x] Audit paket lama tanpa menimpa ZIP atau checksum bukti lama.
- [x] Temukan akar masalah schema `original_file_name` yang diperlakukan
  ImageFolder sebagai media path karena reserved pattern `*_file_name`.
- [x] Bangun physical image index dan resolve seluruh 389 metadata row secara
  deterministik dengan unresolved 0 dan ambiguous 0.
- [x] Buat staging flat 312 train dan 77 validation tanpa mengubah image bytes,
  caption, split, class, trigger, provenance, atau keputusan manusia.
- [x] Lakukan PIL verify/load 389/389.
- [x] Lakukan Hugging Face ImageFolder full decode train 312/312 dan validation
  77/77 dalam environment terisolasi.
- [x] Lakukan loader probe setara Diffusers sebanyak 78 batch/312 gambar.
- [x] Buat `dataset_multicrop_v1_kaggle_fixed.zip` dan checksum baru; pastikan
  deterministic rebuild menghasilkan SHA-256 identik.
- [x] Tambahkan 13 regression test mapping, image integrity, checkpoint,
  resume, dan SafeTensors.
- [x] Buat notebook Kaggle standalone 52 cell dari satu source yang sama.
- [x] Tambahkan CUDA/internet gate, fresh cache, dependency/import probe,
  bitsandbytes fallback, smoke 100, main 1600, checkpoint, dan resume aman.
- [x] Sesuaikan resume dengan perilaku Diffusers: materialize checkpoint Kaggle
  Input ke output lokal dan validasi SHA-256 sebelum launch.
- [x] Normalisasi LoRA default ke filename canonical secara atomik tanpa
  menghapus file default.
- [x] Tambahkan sanity empat kelas, evaluasi 36 kondisi, proxy metrics, template
  manusia kosong, report, export, integrity gate, dan final state.
- [x] Buat cell map lengkap, file copy-paste, dan panduan Run All Kaggle.
- [x] Tambahkan discovery ganda untuk ZIP atau folder yang diekstrak otomatis
  oleh Kaggle, dengan anchored metadata dan 389 image SHA validation.
- [x] Validasi nbformat, compile 52 cell, 84 test ML, notebook validator,
  preflight, Ruff, dan checksum package.
- [x] Upload ZIP fixed dan notebook ke Kaggle, aktifkan GPU + Internet, lalu
  jalankan Run All pada version 2.
- [x] Nyatakan training sukses setelah Cell 51 selesai dan
  `complete_pipeline_state.json` berstatus `success` pada run
  `20260820T143551Z`.
- [x] Unduh artifact ZIP dan validasi ulang CRC, SHA-256, SafeTensors, manifest,
  status, loss, 4 sanity PNG, dan 72 evaluation PNG secara lokal tanpa SD.
- [x] Materialisasi model canonical, contact sheet empat kelas, metrik proxy,
  dan template evaluasi manusia dengan path lokal.

## LoRA Human Review UI Lokal 2026-08-21

- [x] Bangun UI pasangan Base-vs-LoRA untuk 36 kondisi dan 72 gambar aktual.
- [x] Tambahkan rubrik wajib tanpa skor default, filter kelas/status, progres,
  navigasi, ekspor CSV, dan finalization gate 72/72.
- [x] Validasi schema, pasangan, nilai, path aman, signature PNG, dan role
  reviewer pada server lokal yang hanya bind ke `127.0.0.1`.
- [x] Terapkan write atomik, backup sebelum setiap edit/hapus, resume, dan
  invalidasi ringkasan final yang sudah kedaluwarsa.
- [x] Pisahkan `human_review_ui_progress.json` dari laporan validator Python
  `human_review_progress.json`.
- [x] Tambahkan 7 regression test dan visual QA desktop 1440/mobile 390 tanpa
  overflow horizontal atau kontrol terpotong.
- [x] Perketat validator Python untuk pasangan Base/LoRA, identitas prompt-seed,
  dan sembilan kondisi per kelas.
- [x] Tambahkan analyzer berpasangan yang menghasilkan JSON, CSV, dan Markdown
  BAB IV menggunakan exact McNemar dan exact sign test setelah gate 72/72.
- [x] Batalkan completion report dan seluruh analisis lama pada setiap koreksi
  skor agar hasil kedaluwarsa tidak dipakai.
- [x] Selesaikan keputusan visual reviewer nyata untuk 72/72 gambar.
- [x] Jalankan finalization UI, validator Python `--require-complete`, dan
  analyzer BAB IV.

## Pasca-Review dan Deployment GPU 2026-08-21

- [x] Verifikasi 72 penilaian, 36 pasangan, 9 kondisi per kelas, prompt/seed
  identik, field wajib lengkap, dan sumber skor manusia.
- [x] Koreksi semantik class confirmation versus cross-class/unclear tanpa
  mengubah keputusan reviewer.
- [x] Hasilkan JSON, CSV, Markdown, statistik Base-vs-LoRA, laporan path/hash,
  dan dua snapshot backup.
- [x] Verifikasi ulang LoRA final run `20260820T143551Z` dan SHA-256 canonical
  tanpa memuat Stable Diffusion atau mengubah model.
- [x] Pindahkan kontrak Flutter dari FastAPI langsung ke Express visual proxy.
- [x] Tambahkan token privat backend-to-FastAPI, token klien sementara, rate
  limit, proxy PNG, timeout, dan regression test.
- [x] Tambahkan GPU preflight, startup RunPod, deployment bundle, dan real e2e
  evidence gate yang menolak mock/CPU/hash salah.
- [x] Uji kontrak lokal Express -> FastAPI mock -> PNG proxy; bukti tetap
  ditandai mock dan bukan inference nyata.
- [ ] Deploy bundle pada RunPod Secure Cloud GPU terautentikasi.
- [ ] Jalankan `gpu_preflight.json` dan real e2e probe sampai berstatus success.
- [ ] Jalankan Flutter pada Android dengan backend HTTPS dan ambil screenshot
  setelah PNG nyata tampil.
- [ ] Susun BAB IV final hanya setelah dua gerbang sebelumnya selesai.

## Finalisasi Aplikasi 2026-08-04

- [x] Perbaiki parser BMKG agar nilai hujan hilang tetap `null` dan proyeksi
  hanya dibuat dari cakupan lengkap.
- [x] Tambahkan cache segar/stale, timeout, atribusi, timestamp, dan error
  terstruktur pada integrasi BMKG.
- [x] Finalkan decision table, rule ID, alasan, input summary, dan keluaran empat
  komoditas.
- [x] Tambahkan endpoint kalender empat minggu dengan metodologi dan tingkat
  keyakinan proyeksi yang eksplisit.
- [x] Tambahkan repository/cache/history dan offline last-known pada Flutter.
- [x] Finalkan FastAPI mock/real provider contract, readiness, request ID,
  timeout, batas dimensi, seed, dan provenance output.
- [x] Jalankan live integration Node, BMKG Aikmel, kalender, FastAPI mock, dan
  static image fetch.
- [x] Pisahkan smoke test 100 langkah dan main training 1.600 langkah pada
  notebook dengan output persisten terpisah.
- [x] Build dan verifikasi APK debug beserta SHA-256.
- [x] Siapkan dokumentasi implementasi, deployment, user guide, testing,
  evidence skripsi, dan instrumen penelitian kosong.
- [x] Jalankan final secret scan, dependency audit, preflight, lint, format,
  dan seluruh automated test yang tersedia.
- [ ] Uji instalasi APK dan alur jaringan pada perangkat Android fisik.
- [ ] Buat release APK setelah signing identity resmi tersedia.

## Verifikasi Lanjutan 2026-08-05

- [x] Validasi trigger pilot `gaus_padi_public` terpisah dari trigger final.
- [x] Sinkronkan notebook pilot `.ipynb` dan `.py`, persistensikan dataset ke
  Drive, serta validasi seluruh 57 code cell.
- [x] Tambahkan validator CPU-only untuk artefak training nyata dari Colab.
- [x] Perketat validator dengan struktur SafeTensors, isi checkpoint, loss
  finite, fatal log, environment GPU, dan gambar validasi yang dapat dibuka.
- [x] Tambahkan dan uji mode prompt langsung FastAPI tanpa mengubah alur
  rekomendasi rule-based Flutter.
- [x] Jalankan ulang 38 test ML/dataset, 16 test inference, 16 test Node, dan
  13 test Flutter.
- [x] Jalankan ulang live BMKG, kalender, FastAPI dua mode, security scan,
  dependency audit, analyzer, lint, dan preflight.
- [x] Bangun ulang dan verifikasi APK debug beserta signature dan SHA-256.

## Dataset Review UI Lokal 2026-08-05

- [x] Bangun review UI lokal berbasis Node.js tanpa framework besar.
- [x] Tampilkan 350 gambar beserta kelas, sumber, resolusi, ukuran, proxy,
  duplicate warning, status teknis, keputusan, dan catatan.
- [x] Terapkan filter, navigasi, lompat nomor, tombol keputusan, dan keyboard
  shortcut Y/N/U/J/K/Arrow/S.
- [x] Tambahkan alasan penolakan multi-pilih tanpa mengarang keputusan.
- [x] Terapkan autosave atomik, backup sebelum perubahan pertama, progress JSON,
  dan resume setelah aplikasi dibuka kembali.
- [x] Tambahkan validator `npm run dataset-review:validate`.
- [x] Kunci finalisasi selama masih ada pending atau unsure.
- [x] Hubungkan tombol finalisasi ke mapping review gabungan, test, validasi
  metadata, dan packaging otomatis tanpa training lokal.
- [x] Validasi ulang isi ZIP, konten terlarang, dan checksum.
- [x] Tambahkan 11 test Node untuk parser, validator, UI API, autosave, backup,
  resume, dan finalization gate.
- [x] Tambahkan test pipeline untuk unsure, minimum kelas, dan validasi ZIP.
- [x] Buat `docs/DATASET_REVIEW_GUIDE.md`.
- [x] Lakukan keputusan visual manusia pada seluruh 350 kandidat.
- [x] Jalankan finalisasi otomatis dan hentikan pipeline secara aman ketika
  jagung, cabai, dan kacang tanah berada di bawah minimum 80.
- [x] Catat accepted, rejected, proxy, sumber final, dan shortfall pada laporan
  kurasi serta class balance.
- [x] Cari dan verifikasi tiga sumber Mendeley CC BY 4.0 untuk jagung, cabai,
  dan kacang tanah.
- [x] Ekstrak selektif 187 gambar asli tanpa mengunduh arsip 5,4 GB penuh.
- [x] Stage 125 kandidat tambahan dan bandingkan SHA-256/dHash dengan 499 raw,
  350 kandidat review, serta processed dataset.
- [x] Tambahkan filter batch, provenance dataset, lisensi, dan progres per batch
  pada Review UI dengan default `additional_batch_v1`.
- [x] Pertahankan identitas, file, dan keputusan 350 kandidat awal serta buat
  backup sebelum append.
- [x] Tambahkan finalisasi gabungan dan fallback otomatis
  `additional_batch_v2` untuk kelas yang masih kurang.
- [x] Normalisasi orientasi 50 JPEG review jagung tanpa mengubah byte staging
  asli atau keputusan 350 kandidat lama.
- [x] Verifikasi UI review pada desktop dan emulasi mobile 390x844 tanpa
  overflow horizontal.
- [x] Jalankan dry run finalizer dan pastikan berhenti pada
  `manual_review_required` dengan `training_allowed=false`.
