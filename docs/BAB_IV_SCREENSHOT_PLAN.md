# Rencana Screenshot Android BAB IV

Status: seluruh slot menunggu inference GPU nyata dan pengujian pada perangkat Android. Mockup, provider mock, dan gambar evaluasi Kaggle tidak boleh digunakan sebagai pengganti screenshot aplikasi.

## Prasyarat Umum

1. `gpu_preflight.json` berstatus `success` pada host GPU.
2. Endpoint Express `/api/visual/ready` melaporkan provider `diffusers`, device `cuda`, dan `model_loaded=true`.
3. `real_inference_e2e_report.json` berstatus sukses dan hash LoRA sama dengan model final.
4. APK dijalankan dengan URL backend GPU yang benar dan token uji sementara.
5. Status bar boleh terlihat, tetapi token, URL privat, terminal, dan data rahasia tidak boleh tampil.
6. Setiap screenshot harus berasal dari satu alur penggunaan yang sama dan disimpan tanpa manipulasi isi.

## Daftar Screenshot

| No. | Nama file yang disarankan | Keadaan yang harus ditampilkan | Caption yang disarankan |
| --- | --- | --- | --- |
| 1 | `android_01_beranda_bmkg.png` | Halaman TaniAdaptif, lokasi Aikmel, kondisi cuaca BMKG, indikator sumber/cache, dan tombol rekomendasi | Tampilan beranda dan informasi cuaca BMKG wilayah Aikmel |
| 2 | `android_02_input_lahan.png` | Form jenis lahan, ketersediaan air, tanaman sebelumnya, dan ringkasan cuaca; seluruh label terbaca | Tampilan input kondisi lahan untuk proses rekomendasi |
| 3 | `android_03_hasil_rekomendasi.png` | Tanaman prioritas, alternatif, alasan, rule ID bila ditampilkan, dan kalender empat minggu | Tampilan hasil rekomendasi dari rule-based engine |
| 4 | `android_04_simulasi_lora_nyata.png` | Gambar hasil inference nyata sudah selesai dimuat, nama tanaman sesuai rekomendasi, request ID/model provenance bila tersedia | Tampilan simulasi visual Stable Diffusion 1.5 dengan LoRA pada aplikasi Android |
| 5 | `android_05_riwayat.png` | Daftar riwayat yang benar-benar dapat dibuka kembali, termasuk rekomendasi dan visual jika tersedia | Tampilan riwayat rekomendasi dan simulasi visual |

## Langkah Pengambilan

1. Mulai perekaman bukti setelah readiness GPU lulus.
2. Buka aplikasi dan refresh cuaca Aikmel; ambil screenshot 1.
3. Masuk ke form lahan dan isi satu skenario yang dicatat dalam laporan E2E; ambil screenshot 2.
4. Proses rekomendasi; pastikan keluaran berasal dari rule engine dan catat rule ID; ambil screenshot 3.
5. Tekan generate visual dan tunggu sampai PNG nyata selesai tampil; cocokkan request ID dengan laporan E2E; ambil screenshot 4.
6. Simpan hasil, buka layar riwayat, dan pastikan entri dapat dipanggil kembali; ambil screenshot 5.
7. Hitung SHA-256 lima PNG dan tambahkan ke evidence manifest final.

## Placeholder Aktif

- `[SCREENSHOT ANDROID BELUM TERSEDIA]` untuk beranda, input lahan, hasil rekomendasi, simulasi visual, dan riwayat.
- `[BUKTI E2E GPU BELUM TERSEDIA]` untuk readiness, latency, model provenance remote, dan PNG nyata.

Catatan: implementasi saat audit menyimpan riwayat visual, tetapi belum ditemukan layar Flutter khusus untuk menampilkan `loadVisualHistory()`. Screenshot nomor 5 baru dapat dibuat setelah layar riwayat benar-benar tersedia atau rancangan BAB III disesuaikan.
