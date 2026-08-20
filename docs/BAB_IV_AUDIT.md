# Audit Penyusunan BAB IV TaniAdaptif

Tanggal audit: 21 Agustus 2026  
Status: siap disusun sebagai draft pra-E2E, dengan batas klaim eksplisit.

## Sumber yang Diaudit

| Sumber | Path | SHA-256 | Penggunaan |
| --- | --- | --- | --- |
| Naskah BAB I-III | `D:\referensi skripsi\SKRIPSI.docx` | `f0568581e5b63113a4b38fb22fb6d5acbde02b0620324539a909188a44ed0d63` | Judul, rumusan masalah, tujuan, batasan, metode, rancangan, gaya naskah |
| Panduan Fakultas Teknik 2026 | `D:\referensi skripsi\PANDUAN SKRIPSI FAKULTAS TEKNIK 20 JULI 2026.pdf` | `129fb90e836e1843ddfa37256033a35b7dbde26fff3a6feaf2d01691c3b7a8f8` | Struktur BAB IV dan format halaman |
| Artefak model final | `artifacts/model_evaluation/kaggle_run_20260820T143551Z/` | Lihat manifest bukti | Training, evaluasi, dan review visual |
| Implementasi aplikasi | `backend-nodejs/`, `inference_api/`, `mobile-flutter/` | Berdasarkan file kerja saat audit | Hasil implementasi dan pengujian |

File sumber skripsi dan panduan dibaca tanpa ditimpa atau diubah.

## Konsistensi Penelitian

Judul yang dipakai dalam draft BAB IV sama dengan judul pada naskah sumber:

> RANCANG BANGUN APLIKASI MOBILE BERBASIS STABLE DIFFUSION DENGAN FINE-TUNING LoRA DAN API BMKG UNTUK SIMULASI ROTASI TANAM ADAPTIF IKLIM DI WILAYAH AIKMEL

| Unsur BAB I-III | Temuan audit | Implikasi untuk BAB IV |
| --- | --- | --- |
| Rumusan masalah 1 | Meminta aplikasi mobile yang mengintegrasikan BMKG, kondisi lahan, dan rule-based engine | Dibahas pada 4.1.1-4.1.5 dan diuji pada 4.2 |
| Rumusan masalah 2 | Meminta fine-tuning LoRA untuk simulasi visual empat komoditas | Dibahas pada 4.1.6-4.1.8 dengan run final saja |
| Rumusan masalah 3 | Meminta pengujian fungsional dan evaluasi teknis model | Dibahas pada 4.1.7, 4.2, dan 4.3 |
| Tujuan penelitian | Satu-ke-satu dengan tiga rumusan masalah | Pemetaan ketercapaian disajikan di 4.3.1 |
| Batasan penelitian | Empat komoditas, Aikmel, Flutter, BMKG, rule engine, LoRA sebagai visual | Seluruh klaim BAB IV dibatasi pada ruang tersebut |
| Metode | Research and Development (R&D) | Hasil diposisikan sebagai implementasi dan pengujian produk |
| Sumber rekomendasi | Rule-based engine | Tidak ada bagian yang menyatakan Stable Diffusion menentukan rekomendasi |
| Peran Stable Diffusion | Simulasi visual setelah rekomendasi | Hasil model dipisahkan dari evaluasi rule engine |
| Evaluasi manusia | Tidak ada UAT, responden petani, wawancara, kuesioner, atau validasi ahli | Review 72 gambar disebut hanya sebagai evaluasi visual teknis oleh peneliti |

## Kepatuhan Format Kampus

Panduan menetapkan BAB IV dengan struktur 4.1 Hasil Perancangan Sistem, 4.2 Pengujian Sistem, dan 4.3 Pembahasan. Naskah draft mengikuti struktur tersebut. Format DOCX menggunakan A4, margin atas/kiri 4 cm, bawah/kanan 3 cm, Times New Roman 12 pt, rata kiri-kanan, spasi 1,5, dan inden baris pertama 1 cm. Judul tabel ditempatkan di atas; caption gambar di bawah.

## Temuan yang Perlu Revisi Sebelum Naskah Final

### 1. Decision table BAB III tidak sama dengan implementasi final

Tabel 3.6 pada naskah sumber berisi 12 contoh dan menggunakan istilah `basah`, `sedang`, dan `kering`. Implementasi pada `backend-nodejs/src/config/aturanRotasi.js` memiliki 30 kunci utama dan menggunakan `tinggi`, `sedang`, dan `rendah`. Ketersediaan air `kurang` dinormalisasi ke `terbatas` untuk pencarian aturan, sedangkan jenis lahan memengaruhi urutan prioritas dan rule ID.

Tindakan final: perbarui uraian dan Tabel 3.6 pada naskah utama agar mencerminkan implementasi 30 kunci, atau tegaskan bahwa 12 baris tersebut hanya contoh rancangan. BAB IV melaporkan kontrak implementasi aktual dan tidak menutupi perbedaan ini.

### 2. Riwayat tersimpan tetapi belum memiliki layar khusus

`LocalStorageService` menyimpan riwayat visual dan membatasinya pada 20 entri; pengujian otomatis lulus. Namun, tidak ditemukan layar Flutter yang memanggil `loadVisualHistory()` untuk menampilkan daftar riwayat. Klaim yang sah saat ini adalah penyimpanan riwayat telah diterapkan, sedangkan tampilan riwayat khusus belum lengkap.

Tindakan final: implementasikan layar riwayat atau ubah rancangan BAB III dan caption screenshot agar sesuai dengan kemampuan aktual.

### 3. Inference GPU nyata belum terbukti end-to-end

Kontrak Flutter, Express, FastAPI, autentikasi, retry, timeout, dan pengiriman PNG telah diuji dengan provider mock. Model final telah tersedia, tetapi `gpu_preflight.json`, `real_inference_e2e_report.json`, PNG E2E nyata, dan screenshot Android final belum ada.

Tindakan final: pertahankan placeholder `[BUKTI E2E GPU BELUM TERSEDIA]` dan `[SCREENSHOT ANDROID BELUM TERSEDIA]` sampai bukti nyata dibuat.

### 4. Proyeksi empat minggu bukan prakiraan bulanan BMKG

BMKG menyediakan horizon jangka pendek. Implementasi hanya menghitung proyeksi setara mingguan/bulanan ketika cakupan curah hujan horizon lengkap. Minggu 2-4 diberi tingkat keyakinan rendah. BAB IV harus menyebutnya proyeksi berbasis rata-rata horizon yang tersedia, bukan prakiraan bulanan resmi BMKG.

## Gerbang Klaim

- Model final hanya run `20260820T143551Z`.
- LoRA final harus ber-SHA-256 `0bda8908d577513110c22cf5ec1b8a7e008d2b26dd90525732a5c4e4b1bdd43a`.
- Peningkatan kesesuaian komoditas dilaporkan deskriptif; exact McNemar `p=0,25` tidak signifikan pada alpha 0,05.
- Mean skor konteks/realisme bersifat deskriptif; median adalah ringkasan utama untuk skor ordinal.
- Metrik brightness, contrast, dan entropy hanya proxy teknis.
- Tidak ada klaim hasil panen, akurasi agronomi lapangan, efektivitas pada petani, penerimaan pengguna, atau penerapan di masyarakat.
- Instrumen UAT/validasi ahli yang kosong tidak digunakan sebagai hasil penelitian.

## Kesimpulan Audit

BAB IV dapat disusun hampir final dari bukti training, evaluasi visual, implementasi, dan pengujian perangkat lunak yang tersedia. Finalisasi penuh masih bergantung pada inference GPU nyata, screenshot Android, serta keputusan peneliti mengenai konsistensi decision table BAB III dan layar riwayat.
