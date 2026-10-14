# Runbook Sidang TaniAdaptif: HP + Express + Kaggle GPU

Dokumen ini menjelaskan cara menjalankan TaniAdaptif pada HP Android dengan
Express di laptop dan inference Stable Diffusion + LoRA di Kaggle GPU.

## Arsitektur

```text
HP Android Flutter
  -> http://127.0.0.1:3000/api melalui adb reverse
  -> Express pada laptop
  -> URL Cloudflare Quick Tunnel Kaggle
  -> FastAPI + Diffusers + CUDA + LoRA
  -> PNG kembali ke Express dan HP
```

URL Kaggle tidak dimasukkan ke Flutter. URL tersebut hanya dikonfigurasikan
sebagai `INFERENCE_API_BASE_URL` pada Express.

## Prasyarat

- Notebook Kaggle inference sudah `STATUS=READY_FOR_SIDANG`.
- GPU Kaggle aktif dan cell `KEEP_ALIVE` masih berjalan.
- HP terhubung melalui USB dengan USB debugging aktif.
- Android package adalah `com.hamzanwadi.tani_adaptif`.
- File `mobile-flutter/tani_adaptif/config/production.local.json` tersedia.
- Jangan memakai `production.example.json` untuk APK sidang.

## Saat Sidang

### 1. Jalankan Kaggle

Run All notebook inference dan tunggu sampai model siap. Salin URL yang
dicetak pada output:

```text
KAGGLE_GPU_URL=https://nama-tunnel.trycloudflare.com
```

Biarkan cell `KEEP_ALIVE` berjalan selama demonstrasi. URL Quick Tunnel dapat
berubah jika session Kaggle dijalankan ulang.

### 2. Sambungkan Kaggle ke Express

Buka PowerShell. Perintah ini dapat dijalankan dari folder mana pun:

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "D:\TaniAdaptif\scripts\sidang_set_gpu_url.ps1" -GpuUrl "https://nama-tunnel.trycloudflare.com"
```

Ganti URL contoh dengan URL terbaru dari Kaggle. Jangan menambahkan `/health`
atau path lain pada nilai `-GpuUrl`.

Output yang diharapkan:

```text
Backend health: PASS
GPU readiness: PASS (diffusers/cuda)
```

Script ini memperbarui `backend-nodejs/.env`, merestart Express, dan
memvalidasi provider `diffusers`, device `cuda`, serta model yang sudah dimuat.
Token backend dibaca oleh script dan tidak perlu ditempel ke Flutter.

### 3. Build APK

Build ulang jika source Flutter atau asset berubah. Untuk HP fisik gunakan
`127.0.0.1`, karena Express diteruskan dengan `adb reverse`.

```powershell
cd D:\TaniAdaptif\mobile-flutter\tani_adaptif
flutter pub get
flutter build apk --debug --dart-define-from-file=config/production.local.json --dart-define=BACKEND_API_BASE_URL=http://127.0.0.1:3000/api --dart-define=DEMO_FALLBACK_ENABLED=true
```

Jangan menampilkan isi `production.local.json` dan jangan memasukkannya ke
Git. File tersebut hanya digunakan lokal saat build APK sidang.

### 4. Cek HP

```powershell
adb devices
```

Status perangkat harus `device`. Jika `adb` belum masuk PATH, gunakan:

```powershell
& "C:\Users\azulf\AppData\Local\Android\Sdk\platform-tools\adb.exe" devices
```

### 5. Preflight, instal, dan buka aplikasi

Jalankan satu per satu dari PowerShell. Path script harus memakai nama
berikut, bukan `scripts\sidang\_preflight.ps1`.

```powershell
$apk = "D:\TaniAdaptif\mobile-flutter\tani_adaptif\build\app\outputs\flutter-apk\app-debug.apk"
```

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "D:\TaniAdaptif\scripts\sidang_preflight.ps1" -ApkPath $apk
```

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "D:\TaniAdaptif\scripts\sidang_install.ps1" -ApkPath $apk
```

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "D:\TaniAdaptif\scripts\sidang_start.ps1"
```

Script instalasi dan start menyiapkan:

```text
adb reverse tcp:3000 tcp:3000
APK com.hamzanwadi.tani_adaptif
aplikasi terbuka pada HP
```

## Urutan Demo Aplikasi

1. Buka beranda TaniAdaptif.
2. Buka halaman BMKG dan ambil data cuaca.
3. Isi jenis lahan, ketersediaan air, dan tanaman sebelumnya.
4. Jalankan rekomendasi rule-based.
5. Buka `Simulasi Visual`.
6. Pilih komoditas yang direkomendasikan.
7. Tekan `Buat Simulasi`.
8. Pastikan gambar tampil dengan keterangan `Inference live`.
9. Tekan `Simpan ke Riwayat`.
10. Buka halaman riwayat dan tampilkan kembali hasilnya.

Identitas komoditas tetap:

```text
padi         -> taniadaptif_padi
jagung       -> taniadaptif_jagung
cabai        -> taniadaptif_cabai
kacang_tanah -> taniadaptif_kacang_tanah
```

## Verifikasi Cepat

```powershell
Invoke-RestMethod -Uri "http://127.0.0.1:3000/api/kesehatan"
```

```powershell
& "C:\Users\azulf\AppData\Local\Android\Sdk\platform-tools\adb.exe" -s R9RRA03WDXE reverse --list
```

Output reverse harus memuat:

```text
tcp:3000 tcp:3000
```

## Penanganan Error

### URL Kaggle tidak aktif

Jalankan kembali notebook Kaggle sampai `READY_FOR_SIDANG`, salin URL baru,
lalu ulangi langkah `sidang_set_gpu_url.ps1`. Tidak perlu mengubah Flutter.

### HP `unauthorized`

Buka kunci HP, terima dialog USB debugging, lalu jalankan `adb devices` lagi.

### HP `offline`

Cabut dan pasang kembali kabel USB, lalu aktifkan ulang USB debugging.

### Backend sehat tetapi visual HTTP 401

Pastikan APK dibangun menggunakan `config/production.local.json`. Jangan
menaruh `INFERENCE_API_TOKEN` di Flutter.

### Port 3000 bermasalah

Jalankan `sidang_set_gpu_url.ps1` dari root repo. Script hanya menghentikan
proses Node TaniAdaptif yang sesuai dan tidak menghentikan proses lain.

## Validasi Sesi Terakhir

Pada 27 Agustus 2026, validasi lokal berhasil dengan hasil:

```text
ADB device       = R9RRA03WDXE
Backend health   = PASS
GPU readiness    = PASS (diffusers/cuda)
Provider         = diffusers
Device           = cuda
Model loaded     = true
APK installed    = true
adb reverse      = tcp:3000 tcp:3000
App launch       = PASS
Visual screen    = Cabai, Inference live
Package          = com.hamzanwadi.tani_adaptif
```

Pada setiap sesi sidang, URL tunnel harus diambil ulang dari Kaggle. Jangan
mengandalkan URL pada validasi sebelumnya.

