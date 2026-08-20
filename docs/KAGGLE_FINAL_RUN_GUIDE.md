# Panduan Final Training LoRA di Kaggle

> Status 2026-08-21: run final `20260820T143551Z` sudah selesai dengan
> `FINAL STATUS: SUCCESS`. Gunakan panduan ini untuk reproduksi atau training
> baru yang memang diperlukan, bukan untuk mengulang artefak yang sama.

Panduan ini memakai paket dataset dan notebook final berikut:

- Dataset: `artifacts/dataset_packages/dataset_multicrop_v1_kaggle_fixed.zip`
- SHA-256: `e232f79d2f8ae20b4fb765efb38435ce05e929406e88faba6b02aaaafd1ad42d`
- Notebook: `ml_pipeline/notebooks/00_train_lora_multicrop_kaggle_final.ipynb`

Laptop hanya dipakai untuk mengunggah file dan memantau Kaggle. Training berjalan
pada GPU Kaggle, bukan pada AMD Ryzen 3 5300U di laptop.

## Menyiapkan Dataset

1. Login ke `https://www.kaggle.com/`.
2. Pilih **Datasets**, lalu **New Dataset**.
3. Upload satu file bernama `dataset_multicrop_v1_kaggle_fixed.zip`.
4. Kaggle boleh menampilkan ZIP sebagai satu file atau mengekstraknya menjadi
   folder `train/`, `validation/`, dan `manifests/`; notebook mendukung keduanya.
5. Atur visibility menjadi **Private**.
6. Klik **Create** dan tunggu proses upload selesai.

Jangan memakai `dataset_multicrop_v1.zip` lama. Untuk ZIP, notebook mengunci
checksum paket fixed. Untuk input yang diekstrak Kaggle, notebook mengunci hash
mapping dan metadata lalu memverifikasi SHA-256 seluruh 389 gambar.

## Menjalankan Notebook

1. Pilih **Code**, lalu **New Notebook**.
2. Gunakan menu **File > Import Notebook** untuk mengimpor
   `00_train_lora_multicrop_kaggle_final.ipynb`.
3. Klik **Add Input**, cari dataset private yang baru dibuat, lalu tambahkan.
4. Buka **Notebook options** atau **Session options**.
5. Atur **Accelerator** ke **GPU**. Notebook mendeteksi GPU aktual dan tidak
   mengasumsikan tipe T4.
6. Atur **Internet** ke **On** agar model dan dependency resmi dapat diakses.
7. Klik **Run All**. Jangan menambah, menghapus, atau mengubah cell.
8. Biarkan tab aktif selama smoke 100 langkah dan main 1600 langkah berjalan.

Urutan otomatisnya adalah validasi checksum dan 389 gambar, ImageFolder decode,
loader probe, dependency/import gate, smoke training, main training, sanity empat
kelas, evaluasi, lalu export.

Cell 05 harus menampilkan salah satu mode berikut:

- `preferred`: Kaggle mempertahankan file ZIP.
- `kaggle_extracted_content`: Kaggle mengekspos isi ZIP sebagai folder.

Jika Cell 05 tetap menulis `fixed dataset input not found`, dataset belum
terpasang melalui **Add Input** atau dataset yang dipilih bukan paket fixed.

## Hasil Yang Diunduh

Status sukses hanya sah bila Cell 51 selesai tanpa exception, menampilkan
`FINAL STATUS: SUCCESS`, dan file `complete_pipeline_state.json` di dalam artefak
berstatus `success`.

Download dari panel **Output** atau **Files**:

- `/kaggle/working/taniadaptif_lora_artifacts.zip`
- `/kaggle/working/taniadaptif_lora_artifacts.sha256`

ZIP memuat LoRA canonical, checksum model, konfigurasi training, manifest smoke
dan main, loss history, log penting, sanity images, evaluation manifest, template
penilaian manusia yang masih kosong, serta report final.

## Bila Training Berhenti

Pesan terakhir dari `accelerate` sering hanya pembungkus. Notebook ini mengambil
traceback proses training yang pertama dan menaruhnya di:

- `/kaggle/working/taniadaptif_lora/outputs/smoke_test/training_manifest.json`
- `/kaggle/working/taniadaptif_lora/outputs/multicrop_v1/training_manifest.json`
- `/kaggle/working/taniadaptif_lora/logs/smoke_training.log`
- `/kaggle/working/taniadaptif_lora/logs/main_training.log`

Jangan menjalankan main bila smoke gagal. Perbaiki berdasarkan `root_error` dan
`failure_category`, bukan berdasarkan baris `CalledProcessError` paling bawah.
Jika cell dijalankan ulang pada sesi yang sama, notebook memilih checkpoint
numerik tertinggi yang manifestnya cocok. Checkpoint dari Kaggle Input dicopy ke
output lokal dan diverifikasi SHA-256 sebelum diteruskan, sesuai perilaku resume
source Diffusers yang dikunci.

Metrik evaluasi otomatis hanya proxy statistik gambar. Template evaluasi manusia
tetap kosong sampai benar-benar direview; rekomendasi tanaman tetap ditentukan
oleh rule-based engine TaniAdaptif.
