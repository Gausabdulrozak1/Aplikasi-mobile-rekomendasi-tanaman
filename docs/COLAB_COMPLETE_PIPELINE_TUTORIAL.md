# Tutorial Menjalankan Pipeline LoRA TaniAdaptif

Panduan ini menjalankan seluruh proses melalui Google Colab yang terhubung ke
VS Code. Stable Diffusion tidak dijalankan oleh CPU atau GPU laptop Windows.

Untuk versi yang lebih singkat dan mudah, baca
[`PANDUAN_MUDAH_LORA_COLAB.md`](PANDUAN_MUDAH_LORA_COLAB.md).

## 1. File yang Digunakan

Buka hanya notebook berikut:

```text
D:\TaniAdaptif\ml_pipeline\notebooks\00_run_complete_lora_pipeline_colab.ipynb
```

Dataset persisten sudah tersedia di Google Drive:

```text
MyDrive/skripsi_lora/datasets/dataset_multicrop_v1.zip
```

Notebook menyalinnya secara atomic menjadi ZIP kerja berikut di runtime:

```text
/content/dataset_multicrop_v1.zip
```

Identitas paket final:

```text
Nama     : dataset_multicrop_v1.zip
Ukuran   : 188356224 byte
SHA-256  : f6aa060658cf95e48996f10f0ffde200938d340dd15e6b60adace5bb5cecfb33
Isi      : 389 gambar; train 312; validation 77
```

Jangan ekstrak, edit, atau ganti nama ZIP Drive. Folder lokal
`artifacts\colab_upload\dataset_multicrop_v1_upload_parts` berisi 23 bagian
tervalidasi dan hanya dipakai sebagai fallback jika ZIP Drive tidak tersedia.
Notebook 01-03 tidak perlu dibuka atau di-upload karena notebook 00 sudah
membawa snapshot tervalidasi dari ketiga notebook tersebut.

## 2. Persiapan Singkat

Sebelum mulai, pastikan:

- koneksi internet stabil;
- VS Code tetap terbuka selama proses;
- extension resmi **Google Colab** sudah aktif;
- akun Google memiliki akses ke `MyDrive/skripsi_lora/`;
- tidak ada training Stable Diffusion lain yang berjalan;
- laptop tidak masuk mode sleep saat VS Code masih menjalankan notebook.

Training dilakukan pada GPU Colab. Laptop hanya menampilkan notebook dan
menerima log, sehingga AMD Ryzen 3 5300U tidak dipakai untuk komputasi model.

## 3. Buka Notebook Utama

1. Buka VS Code pada folder `D:\TaniAdaptif`.
2. Di Explorer, buka folder `ml_pipeline`.
3. Buka folder `notebooks`.
4. Klik `00_run_complete_lora_pipeline_colab.ipynb`.
5. Jangan menjalankan sel sebelum kernel Colab tersambung.

## 4. Hubungkan VS Code ke Colab

1. Jika server CPU pernah tersambung, tekan `Ctrl+Shift+P` dan jalankan
   **Colab: Remove Server**.
2. Tutup lalu buka kembali tab notebook 00.
3. Di kanan atas notebook, klik **Select Kernel**.
4. Pilih **Colab > New Colab Server**.
5. Pilih **GPU**, lalu **T4**.
6. Pilih **Standard** dan **Latest** jika opsi tersebut ditampilkan.
7. Beri alias `Tani-T4`, lalu pilih kernel Python 3 dari server tersebut.
8. Jika diminta login, pilih akun Google yang benar lalu tekan **Allow**.
9. Tunggu sampai nama server Colab GPU terlihat di kanan atas.

Jangan memilih **Auto Connect** setelah server CPU pernah dipakai karena opsi
itu dapat menyambungkan kembali server terakhir.

Jangan memilih kernel `.venv`, Python lokal, atau `.venv-ml-local`.

Referensi resmi extension:
[Google Colab VS Code Extension](https://marketplace.visualstudio.com/items?itemName=google.colab)
dan [User Guide](https://github.com/googlecolab/colab-vscode/wiki/User-Guide).

## 5. Sumber Dataset

Tidak ada upload dataset yang wajib dilakukan pada revision v6. Setelah Drive
diizinkan, notebook membaca:

```text
MyDrive/skripsi_lora/datasets/dataset_multicrop_v1.zip
```

Notebook memverifikasi SHA-256 sumber, menyalinnya ke
`/content/dataset_multicrop_v1.zip`, lalu memverifikasi salinan sekali lagi.
Jika ZIP Drive tidak tersedia atau checksum salah, notebook mencoba fallback
`/content/dataset_multicrop_v1_upload_parts/`.

Jangan meng-upload ZIP 188 MB secara langsung melalui extension. Log extension
membuktikan Jupyter Contents API menolaknya dengan `400 Bad Request`.

Tidak perlu meng-upload:

```text
dataset_multicrop_v1.sha256
01_prepare_public_multicrop_dataset_colab.ipynb
02_train_public_multicrop_lora_sd15_colab.ipynb
03_evaluate_public_multicrop_lora_colab.ipynb
```

## 6. Jalankan Pipeline Otomatis

1. Kembali ke notebook 00.
2. Klik **Run All** pada toolbar notebook.
3. Saat Google Drive meminta izin, buka tautan otorisasi resmi.
4. Pilih akun Google yang memiliki `MyDrive/skripsi_lora/`.
5. Tekan **Allow**, lalu tunggu mount selesai.
6. Jangan menjalankan notebook 02 secara terpisah selama notebook 00 aktif.
7. Jangan menghentikan proses hanya karena beberapa langkah tidak menampilkan
   output selama beberapa menit.

Urutan yang dijalankan otomatis:

```text
Pemeriksaan Colab dan CUDA
-> mount Google Drive
-> salin ZIP Drive atau rakit fallback runtime
-> validasi SHA-256 ZIP runtime
-> materialisasi notebook tahap di /content
-> preparation dataset
-> smoke training 100 langkah
-> validasi smoke
-> main training 1600 langkah
-> validasi main
-> evaluasi base versus LoRA
-> validasi evaluasi
```

## 7. Tanda Tahap Awal Berhasil

Pada pemeriksaan awal harus terlihat pola output berikut:

```text
Pipeline revision: 2026-08-14-drive-fallback-wandb-v6
ZIP valid disalin dari Google Drive: /content/drive/MyDrive/skripsi_lora/datasets/dataset_multicrop_v1.zip
Package input mode: google_drive
Dataset package SHA-256 valid: f6aa060658cf95e48996f10f0ffde200938d340dd15e6b60adace5bb5cecfb33
GPU: Tesla T4
VRAM GB: sekitar 14-16
Runtime stage notebooks validated: /content/taniadaptif_pipeline_notebooks
```

Preparation yang benar menampilkan:

```text
Training rows: 312
Prepared runtime dataset: /content/taniadaptif_dataset/multicrop_v1
[preparation] completed
```

Distribusi final tetap:

```text
padi          : 95
jagung        : 100
cabai         : 97
kacang_tanah : 97
```

Jika SHA-256 atau jumlah data berbeda, pipeline harus berhenti. Jangan mencoba
melewati pemeriksaan tersebut.

## 8. Smoke Test 100 Langkah

Smoke test harus selesai sebelum training utama boleh dimulai. Output persisten
berada di:

```text
MyDrive/skripsi_lora/outputs/smoke_test/
```

Bukti minimum smoke yang sah:

```text
checkpoint-100/
multisource_multicrop_smoke_lora.safetensors
pytorch_lora_weights.safetensors
training_manifest.json
training_environment_report.json
training.log
loss_log.csv
validation_images/
```

Notebook hanya melanjutkan ke main training jika validator smoke menyatakan
semua bukti valid. File `.safetensors` kosong tidak dihitung sebagai hasil.

## 9. Main Training 1600 Langkah

Setelah smoke lulus, main training dimulai otomatis. Checkpoint dibuat setiap
200 langkah dan maksimal empat checkpoint dipertahankan.

Output utama berada di:

```text
MyDrive/skripsi_lora/outputs/multicrop_v1/
```

Bukti minimum main training yang sah:

```text
checkpoint-1600/
multisource_multicrop_lora.safetensors
pytorch_lora_weights.safetensors
training_manifest.json
training_environment_report.json
training.log
loss_log.csv
validation_images/
```

Nama canonical berasal dari config final:

```text
smoke : multisource_multicrop_smoke_lora.safetensors
main  : multisource_multicrop_lora.safetensors
```

Notebook mempertahankan file default Diffusers
`pytorch_lora_weights.safetensors`, lalu membuat canonical copy yang hanya
diterima setelah ukuran, struktur SafeTensors, tensor data, metadata, dan hash
salinan valid.

## 10. Evaluasi Otomatis

Setelah main training valid, notebook membandingkan base SD 1.5 dengan LoRA
menggunakan prompt, seed, dan parameter yang sama.

Output berada di:

```text
MyDrive/skripsi_lora/evaluation/multicrop_v1/
```

Hasil yang diharapkan:

```text
36 gambar base
36 gambar LoRA
base_vs_lora_manifest.csv
automated_metrics.csv
class_confusion_proxy.csv
evaluation_summary.md
human_evaluation_template.csv
class_confusion_review.csv
4 contact sheet
```

Metrik otomatis adalah proxy. Skor manusia tetap harus diisi setelah gambar
dilihat langsung.

## 11. Cara Memastikan Pipeline Selesai

Buka file berikut di Google Drive:

```text
MyDrive/skripsi_lora/logs/complete_pipeline_state.json
```

Pipeline selesai hanya jika bagian akhirnya memuat:

```json
{
  "current_stage": "complete_pipeline",
  "status": "success"
}
```

Output terakhir notebook juga harus menampilkan:

```text
Complete pipeline succeeded.
Main LoRA: /content/drive/MyDrive/skripsi_lora/outputs/multicrop_v1/multisource_multicrop_lora.safetensors
Evaluation output: /content/drive/MyDrive/skripsi_lora/evaluation/multicrop_v1
```

Tanpa tiga bukti tersebut, jangan menyatakan training selesai.

## 12. Jika Runtime Terputus

Checkpoint tidak hilang karena berada di Google Drive.

1. Jangan hapus `outputs/`, `evaluation/`, atau `logs/` di Drive.
2. Hubungkan notebook 00 ke runtime Colab GPU baru.
3. Klik **Run All** kembali dan izinkan mount Drive.
4. Notebook menyalin ulang ZIP Drive secara otomatis.
5. Preparation akan membangun ulang dataset sementara.
6. Training membaca checkpoint valid terbaru dengan resume `latest`.
7. Tahap yang artefak finalnya sudah valid akan dilewati.

Jangan menyalin checkpoint smoke ke folder main atau sebaliknya.

## 13. Pesan STOP dan Solusi

### ZIP Drive dan fallback tidak ditemukan

```text
STOP: ZIP valid tidak ditemukan di Google Drive maupun runtime
```

Solusi utama: pastikan akun yang di-mount memiliki file
`MyDrive/skripsi_lora/datasets/dataset_multicrop_v1.zip`. Jika file Drive tidak
dapat dipakai, upload folder fallback
`artifacts\colab_upload\dataset_multicrop_v1_upload_parts` ke server T4.

### Satu bagian gagal di-upload

Notebook menyebut file `part-*` yang hilang atau checksum-nya salah.
Upload ulang file bagian tersebut ke folder
`/content/dataset_multicrop_v1_upload_parts/`, lalu jalankan ulang sel pertama.

### Checksum tidak cocok

```text
STOP: checksum ZIP tidak cocok
```

Solusi: hapus hanya ZIP runtime yang salah lalu **Run All**. Notebook akan
menyalin ulang ZIP Drive yang tervalidasi; jangan mengubah file sumbernya.

### CUDA tidak tersedia

```text
CUDA tidak tersedia. Di VS Code: hapus Colab server CPU melalui Colab: Remove
Server, tutup dan buka kembali notebook, lalu pilih Select Kernel > Colab >
New Colab Server > GPU > T4.
```

Solusi: lepaskan server CPU, buat Colab Server baru dengan GPU, lalu jalankan
ulang. Jangan memilih CPU fallback.

### Training gagal

```text
Training gagal dengan return code ...
```

Baca 10-30 baris terakhir yang dicetak, kemudian periksa:

```text
MyDrive/skripsi_lora/outputs/smoke_test/training.log
MyDrive/skripsi_lora/outputs/smoke_test/training_manifest.json
MyDrive/skripsi_lora/outputs/multicrop_v1/training.log
MyDrive/skripsi_lora/outputs/multicrop_v1/training_manifest.json
MyDrive/skripsi_lora/logs/complete_pipeline_state.json
```

Jangan membuat `training_manifest.json`, checkpoint, atau `.safetensors` secara
manual. Error asli pada `training.log` harus diperbaiki.

### Import W&B atau protobuf gagal

```text
ImportError: cannot import name 'Imports' from wandb.proto.wandb_telemetry_pb2
```

Ini adalah kegagalan revision v4 sebelum langkah smoke pertama, bukan error
dataset atau GPU. Tutup notebook lama tanpa menyimpan, buka revision
`2026-08-14-drive-fallback-wandb-v6`, lalu jalankan ulang. Revision v6 menghapus
integrasi W&B yang tidak dipakai dan menguji import entrypoint training sebelum
smoke dimulai. Jangan memasang W&B secara manual karena logging pipeline memakai
TensorBoard lokal.

### GPU T4 tidak tersedia

Colab Free Tier tidak menjamin jenis GPU atau durasi runtime. Lepaskan server,
tunggu kuota tersedia, lalu coba **New Colab Server** lagi. Jangan memindahkan
training 1600 langkah ke laptop.

## 14. Data yang Dikirim Saat Meminta Bantuan

Jika gagal lagi, kirimkan:

1. tahap terakhir yang terlihat pada notebook 00;
2. 30 baris terakhir `training.log` dari tahap yang gagal;
3. isi `training_manifest.json` tahap tersebut;
4. isi `complete_pipeline_state.json`;
5. nama GPU dan VRAM yang dicetak pada sel pertama.

Jangan mengirim token Google, cookie browser, file `.env`, atau credential.

## 15. Checklist Ringkas

```text
[ ] Buka 00_run_complete_lora_pipeline_colab.ipynb
[ ] Select Kernel > Colab > New Colab Server > GPU > T4
[ ] Pastikan GPU T4/CUDA tersedia
[ ] Klik Run All
[ ] Izinkan mount Google Drive
[ ] Pastikan sel pertama mencetak Package input mode: google_drive
[ ] Tunggu smoke 100 dan validasinya selesai
[ ] Tunggu main 1600 dan validasinya selesai
[ ] Tunggu evaluasi 72 gambar selesai
[ ] Periksa complete_pipeline_state.json berstatus success
[ ] Periksa multisource_multicrop_lora.safetensors valid
```
