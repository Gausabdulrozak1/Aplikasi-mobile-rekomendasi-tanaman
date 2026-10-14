# CHECKLIST SCREENSHOT MANUAL

Gunakan instruksi berikut hanya untuk dokumentasi. Jangan mengubah data, menjalankan training ulang, atau menampilkan token, secret, `.env`, credential, maupun URL privat.

## SS-01

**Lampiran:** Lampiran 1.1  
**Judul:** Halaman Beranda dan Informasi Cuaca

**Saya harus membuka:** Aplikasi TaniAdaptif di HP.

**Langkah:**
1. Aktifkan mode Jangan Ganggu agar notifikasi pribadi tidak muncul.
2. Buka aplikasi TaniAdaptif.
3. Tunggu data cuaca tampil.
4. Pastikan lokasi Aikmel dan sumber BMKG terlihat.
5. Ambil screenshot layar penuh.

**Yang HARUS terlihat:** nama aplikasi, lokasi Aikmel, kondisi cuaca, suhu, kelembapan, dan sumber BMKG.  
**Yang TIDAK boleh terlihat:** notifikasi pribadi, nomor telepon, akun, atau data sensitif.  
**Nama file:** `L1_01_Beranda_Cuaca.png`  
**Caption Word:** Lampiran 1.1 Tampilan Halaman Beranda dan Informasi Cuaca

## SS-02

**Lampiran:** Lampiran 1.2  
**Judul:** Halaman Input Kondisi Lahan

**Saya harus membuka:** Aplikasi TaniAdaptif di HP, menu input kondisi.

**Langkah:**
1. Dari beranda, tekan tombol menuju input kondisi.
2. Tampilkan seluruh pilihan jenis lahan, ketersediaan air, dan tanaman sebelumnya.
3. Jangan menutup label field dengan keyboard.
4. Ambil screenshot layar penuh.

**Yang HARUS terlihat:** judul halaman dan tiga kelompok input utama.  
**Yang TIDAK boleh terlihat:** keyboard yang menutupi field atau notifikasi pribadi.  
**Nama file:** `L1_02_Input_Kondisi_Lahan.png`  
**Caption Word:** Lampiran 1.2 Tampilan Halaman Input Kondisi Lahan

## SS-03

**Lampiran:** Lampiran 1.3  
**Judul:** Halaman Hasil Rekomendasi

**Saya harus membuka:** Hasil rekomendasi setelah input kondisi diproses.

**Langkah:**
1. Isi input kondisi dengan skenario yang akan dijelaskan dalam skripsi.
2. Jalankan proses rekomendasi.
3. Tampilkan tanaman prioritas, alternatif, alasan, dan kalender jika muat.
4. Ambil satu atau dua screenshot berurutan jika halaman lebih panjang dari layar.

**Yang HARUS terlihat:** tanaman rekomendasi, alasan, alternatif, dan rule ID bila ditampilkan.  
**Yang TIDAK boleh terlihat:** pesan error yang tidak berkaitan atau data pribadi.  
**Nama file:** `L1_03_Hasil_Rekomendasi.png`  
**Caption Word:** Lampiran 1.3 Tampilan Hasil Rekomendasi Rule-Based Engine

## SS-04

**Lampiran:** Lampiran 1.4 dan 7.1  
**Judul:** Halaman Simulasi Visual

**Saya harus membuka:** Halaman Simulasi Visual pada aplikasi TaniAdaptif.

**Langkah:**
1. Buka simulasi dari tanaman yang direkomendasikan.
2. Tunggu gambar selesai dimuat.
3. Pastikan nama tanaman dan gambar terlihat utuh.
4. Pastikan label provider/model terlihat jika tersedia.
5. Ambil screenshot layar penuh.

**Yang HARUS terlihat:** nama tanaman, gambar simulasi, dan keterangan bahwa visual tidak menentukan rekomendasi.  
**Yang TIDAK boleh terlihat:** token, URL privat, credential, atau notifikasi pribadi.  
**Nama file:** `L1_04_Simulasi_Visual.png`  
**Caption Word:** Lampiran 1.4 Tampilan Simulasi Visual Stable Diffusion 1.5 dan LoRA

## SS-05

**Lampiran:** Lampiran 1.5  
**Judul:** Halaman Riwayat

**Saya harus membuka:** Menu Riwayat pada aplikasi TaniAdaptif.

**Langkah:**
1. Simpan satu hasil rekomendasi atau simulasi terlebih dahulu jika daftar kosong.
2. Buka menu Riwayat.
3. Tampilkan minimal satu entri lengkap.
4. Ambil screenshot layar penuh.

**Yang HARUS terlihat:** judul Riwayat dan data rekomendasi/simulasi yang tersimpan.  
**Yang TIDAK boleh terlihat:** data pribadi atau notifikasi.  
**Nama file:** `L1_05_Riwayat.png`  
**Caption Word:** Lampiran 1.5 Tampilan Riwayat Rekomendasi dan Simulasi Visual

## SS-06

**Lampiran:** Lampiran 5.3  
**Judul:** Ringkasan Training Final LoRA pada Kaggle

**Saya harus membuka:** Notebook Kaggle yang menghasilkan run final `20260820T143551Z`.

**Langkah:**
1. Buka versi output yang sudah selesai; jangan jalankan ulang cell.
2. Cari cell ringkasan akhir atau output validasi final.
3. Tampilkan run ID, smoke 100 steps, main 1.600 steps, nama file LoRA, ukuran, tensor, dan SHA-256.
4. Bila seluruh informasi tidak muat, ambil dua screenshot berurutan.

**Yang HARUS terlihat:** status sukses, run ID, jumlah steps, file LoRA, dan hash final.  
**Yang TIDAK boleh terlihat:** Kaggle Secret, token, `.env`, credential, atau notebook lain yang tidak berkaitan.  
**Nama file:** `L5_03_Kaggle_Training_Final.png`  
**Caption Word:** Lampiran 5.2 Ringkasan Run Training Final LoRA pada GPU Kaggle

## SS-07

**Lampiran:** Lampiran 7.2  
**Judul:** Status Runtime Inference GPU

**Saya harus membuka:** Output notebook live inference yang sudah pernah berhasil.

**Langkah:**
1. Buka output versi yang berhasil; jangan menjalankan ulang cell.
2. Cari cell status akhir atau output pemeriksaan health/ready.
3. Tampilkan provider `diffusers`, device `cuda`, model loaded, LoRA SHA final, FastAPI ready, dan sanity inference.
4. Potong area URL tunnel jika tidak diperlukan.

**Yang HARUS terlihat:** provider, CUDA, status model, hash LoRA, FastAPI, health/ready, dan sanity inference.  
**Yang TIDAK boleh terlihat:** nilai `INFERENCE_API_TOKEN`, secret, credential, `.env`, atau URL privat.  
**Nama file:** `L7_02_Runtime_GPU_Ready.png`  
**Caption Word:** Lampiran 7.3 Status Provider Diffusers dan LoRA pada Runtime GPU

## SS-08

**Lampiran:** Lampiran 2.1 dan 8.1  
**Judul:** Ringkasan Pengujian Otomatis

**Saya harus membuka:** File lokal `thesis_output/evidence/software_verification_20260821.json` di VS Code.

**Langkah:**
1. Buka file tersebut tanpa menjalankan test ulang.
2. Tampilkan bagian hasil 125 test Python, 23 backend, 13 Flutter, serta Flutter analyze.
3. Besarkan font editor agar teks terbaca.
4. Ambil screenshot hanya pada bagian ringkasan penting.

**Yang HARUS terlihat:** jumlah test, status lulus, dan `No issues found`.  
**Yang TIDAK boleh terlihat:** `.env`, token, secret, atau terminal dengan perintah sensitif.  
**Nama file:** `L8_01_Ringkasan_Pengujian.png`  
**Caption Word:** Lampiran 8.1 Ringkasan Hasil Pengujian Otomatis TaniAdaptif

