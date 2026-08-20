# Panduan Mudah LoRA TaniAdaptif di VS Code

Panduan ini hanya memakai VS Code dan extension resmi Google Colab. Browser
tidak dipakai untuk menjalankan notebook.

## Masalah Sekarang

Pesan ini:

```text
SystemExit: CUDA tidak tersedia
```

berarti VS Code tersambung ke **Colab CPU**. Ini bukan kerusakan aplikasi atau
laptop. Notebook berhenti supaya training tidak berjalan di CPU.

Extension yang terpasang dan sudah diperiksa:

```text
Google Colab : 0.9.0
Jupyter      : 2025.9.1
Python       : 2026.4.0
```

## Tahap 0 - Trust Workspace

Jika Output VS Code menampilkan:

```text
Settings not found in the untrusted workspace folders
```

berarti `D:\TaniAdaptif` masih dibuka dalam Restricted Mode. Karena ini
repository milik sendiri, lakukan:

1. Tekan `Ctrl+Shift+P`.
2. Jalankan **Workspaces: Manage Workspace Trust**.
3. Pilih **Trust** untuk workspace `D:\TaniAdaptif`.
4. Tekan `Ctrl+Shift+P` lagi.
5. Jalankan **Developer: Reload Window**.

Trust harus diberikan sendiri melalui UI VS Code. Jangan mengubah database
trust secara manual. Setelah reload, pengaturan `.vscode/settings.json` akan
membuka `.ipynb` sebagai Jupyter Notebook.

Log berikut tidak berhubungan dengan LoRA:

```text
Cannot find org.netbeans.modules.java.lsp.server in the log
```

Itu berasal dari extension `oracle.oracle-java`. Jika tidak sedang mengerjakan
Java, buka Extensions, cari **Oracle Java**, klik roda gigi, lalu pilih
**Disable (Workspace)**. Tidak perlu uninstall dan tidak memengaruhi Colab.

## Tahap 1 - Hapus Server CPU

1. Jangan tekan **Run All** lagi pada server sekarang.
2. Tekan `Ctrl+Shift+P` di VS Code.
3. Ketik `Colab: Remove Server`.
4. Tekan Enter.
5. Pilih server Colab CPU yang sedang aktif.
6. Tunggu sampai server selesai dihapus.
7. Tutup tab notebook 00, lalu buka kembali file yang sama.

Menutup dan membuka kembali tab diperlukan agar kernel lama tidak tetap melekat
pada notebook.

Jika notebook terlihat sebagai teks JSON yang dimulai dengan `{ "cells":`,
klik kanan tab lalu pilih **Reopen Editor With... > Jupyter Notebook**. Jangan
menjalankan notebook dari tampilan Text Editor.

## Tahap 2 - Buat Server GPU T4

1. Buka:

```text
D:\TaniAdaptif\ml_pipeline\notebooks\00_run_complete_lora_pipeline_colab.ipynb
```

2. Klik **Select Kernel** di kanan atas notebook.
3. Pilih **Colab**.
4. Pilih **New Colab Server**.
5. Pilih **GPU**.
6. Pilih **T4**.
7. Jika ditanya memory/shape, pilih **Standard**.
8. Jika ditanya versi runtime, pilih **Latest**.
9. Jika diminta alias, isi `Tani-T4`.
10. Jika diminta kernel, pilih **Python 3** dari server `Tani-T4`.

Jangan pilih:

```text
Auto Connect
Colab CPU
.venv
.venv-ml-local
Python lokal
```

Setelah benar, bagian kanan atas notebook harus menunjukkan server Colab yang
baru, bukan `.venv` atau Python lokal.

## Tahap 3 - Dataset Otomatis dari Google Drive

Tidak perlu meng-upload dataset ke `/content`. Revision v6 memakai file yang
sudah tersedia di akun Google Drive Anda:

```text
MyDrive/skripsi_lora/datasets/dataset_multicrop_v1.zip
```

Notebook memverifikasi checksum sumber, menyalinnya ke runtime, lalu
memverifikasi salinan lagi. Folder berikut hanya fallback jika ZIP Drive tidak
tersedia:

```text
D:\TaniAdaptif\artifacts\colab_upload\dataset_multicrop_v1_upload_parts
```

Jangan upload ZIP 188 MB secara langsung: extension Colab 0.9.0 sebelumnya
menerima `400 Bad Request` untuk file tersebut.

## Tahap 4 - Uji GPU Sebelum Run All

1. Kembali ke notebook 00.
2. Jalankan hanya code cell pertama dengan tombol segitiga di kiri cell.
3. Izinkan mount Google Drive saat diminta.
4. Tunggu checksum dataset selesai dihitung.

Kondisi benar harus menampilkan pola seperti:

```text
Pipeline revision: 2026-08-14-drive-fallback-wandb-v6
ZIP valid disalin dari Google Drive: /content/drive/MyDrive/skripsi_lora/datasets/dataset_multicrop_v1.zip
Package input mode: google_drive
Dataset package SHA-256 valid: f6aa060658cf95e48996f10f0ffde200938d340dd15e6b60adace5bb5cecfb33
GPU: Tesla T4
VRAM GB: sekitar 14-16
```

Jika masih menampilkan `CUDA tidak tersedia`, jangan lanjut. Periksa kembali
bahwa kernel kanan atas berasal dari server `Tani-T4`, bukan CPU atau lokal.

## Tahap 5 - Jalankan Pipeline

Setelah code cell pertama menampilkan `GPU: Tesla T4`:

1. Klik **Run All** di toolbar notebook.
2. Izinkan Google Drive saat diminta.
3. Pilih akun Google yang menyimpan folder `MyDrive/skripsi_lora`.
4. Biarkan VS Code terbuka dan laptop tidak masuk sleep.
5. Jangan membuka atau menjalankan notebook 02 secara terpisah.

## Tahap 6 - Pahami Urutan Otomatis

### A. Preparation

ZIP diperiksa dan dataset disiapkan. Belum ada training.

```text
389 gambar
312 train
77 validation
```

### B. Smoke Test

Training percobaan 100 langkah. Tahap ini memastikan dependency, GPU,
checkpoint, loss, dan penyimpanan LoRA bekerja.

Jika smoke gagal, main training tidak akan dimulai.

### C. Main Training

Setelah smoke valid, training utama berjalan 1600 langkah. Checkpoint disimpan
setiap 200 langkah ke Google Drive.

### D. Evaluasi

Setelah model valid, notebook membuat 36 gambar base dan 36 gambar LoRA untuk
dibandingkan.

### E. Selesai

Output terakhir harus menampilkan:

```text
Complete pipeline succeeded.
```

Model final berada di:

```text
MyDrive/skripsi_lora/outputs/multicrop_v1/multisource_multicrop_lora.safetensors
```

Status akhir berada di:

```text
MyDrive/skripsi_lora/logs/complete_pipeline_state.json
```

Status yang benar:

```json
{
  "current_stage": "complete_pipeline",
  "status": "success"
}
```

## Jika Runtime Terputus

1. Buat atau sambungkan kembali server GPU T4.
2. Klik **Run All** pada notebook 00 dan izinkan mount Drive.
3. Jangan hapus dataset atau folder output di Google Drive.

Notebook otomatis memakai checkpoint valid terbaru dengan resume `latest`.

## Jika T4 Tidak Muncul

Colab Free Tier tidak menjamin GPU selalu tersedia. Jangan memilih CPU atau
menjalankan training di laptop. Tunggu kuota tersedia, lalu ulangi:

```text
Select Kernel > Colab > New Colab Server > GPU > T4
```

## Jika Muncul Error `wandb_telemetry_pb2`

Error `cannot import name 'Imports'` berasal dari paket W&B bawaan Colab yang
tidak dipakai pipeline. Notebook revision v5 mencopot paket tersebut dan
menjalankan import probe sebelum training. Tutup tab notebook lama tanpa
menyimpan, buka kembali notebook 00, pastikan revision
`2026-08-14-drive-fallback-wandb-v6`, kemudian jalankan **Run All**. Jangan menginstal
W&B secara manual; pipeline menggunakan TensorBoard lokal.

## Jika Muncul `Parameter source tidak unik`

Pesan berikut berasal dari notebook orkestrator lama:

```text
RuntimeError: Parameter source tidak unik
execute_notebook(path, stage, replacements)
```

Versi terbaru tidak memakai `replacements`. Lakukan ini:

1. Hentikan eksekusi notebook lama.
2. Tutup tab notebook tanpa menimpa file repository jika VS Code menanyakan
   konflik perubahan.
3. Tekan `Ctrl+Shift+P` dan jalankan **Developer: Reload Window**.
4. Buka ulang file lokal ini:

```text
D:\TaniAdaptif\ml_pipeline\notebooks\00_run_complete_lora_pipeline_colab.ipynb
```

5. Pastikan bagian atas notebook menampilkan:

```text
Revision: 2026-08-14-drive-fallback-wandb-v6
```

6. Sambungkan kembali kernel `Tani-T4`.
7. Jalankan code cell pertama dan pastikan output memuat:

```text
Pipeline revision: 2026-08-14-drive-fallback-wandb-v6
```

Jika nomor revisi tidak muncul, tab yang dibuka masih bukan file terbaru.

## Jika Masih Gagal

Kirimkan tiga informasi berikut:

```text
1. Nama kernel yang terlihat di kanan atas notebook
2. Screenshot daftar pilihan setelah New Colab Server
3. Pesan error penuh dari code cell pertama
```

Jika training sudah sempat dimulai, sertakan juga:

```text
MyDrive/skripsi_lora/logs/complete_pipeline_state.json
MyDrive/skripsi_lora/outputs/smoke_test/training_manifest.json
30 baris terakhir outputs/smoke_test/training.log
```

Jangan mengirim password, token Google, cookie, atau file `.env`.

## Checklist Singkat

```text
[ ] Trust workspace D:\TaniAdaptif dan Reload Window
[ ] Colab: Remove Server untuk menghapus CPU
[ ] Tutup dan buka kembali notebook 00
[ ] Select Kernel > Colab > New Colab Server
[ ] Pilih GPU > T4 > Standard > Latest
[ ] Jalankan code cell pertama
[ ] Izinkan mount Google Drive
[ ] Pastikan Package input mode: google_drive
[ ] Pastikan output GPU: Tesla T4
[ ] Klik Run All
[ ] Tunggu smoke 100, main 1600, dan evaluasi
[ ] Pastikan complete_pipeline_state.json berstatus success
```
