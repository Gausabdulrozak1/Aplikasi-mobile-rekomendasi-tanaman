# MANIFEST LAMPIRAN SKRIPSI FINAL

Status hanya menggunakan `ADA`, `MANUAL`, atau `TIDAK TERSEDIA`. Path sumber mengacu pada repository `D:\TaniAdaptif`.

| No | Lampiran | Judul | Sumber file | Status | Perlu screenshot manual? | Nama screenshot | Keterangan |
| ---: | --- | --- | --- | --- | --- | --- | --- |
| 1 | 1.1 | Beranda dan informasi cuaca | `artifacts/sidang_live/phone_home.png` | ADA | YA, opsional pembaruan | `L1_01_Beranda_Cuaca.png` | Kandidat lokal disalin sebagai `L1_01_Beranda_Cuaca_existing.png` |
| 2 | 1.2 | Input kondisi lahan | Belum ada screenshot final lokal | MANUAL | YA | `L1_02_Input_Kondisi_Lahan.png` | Ikuti SS-02 |
| 3 | 1.3 | Hasil rekomendasi | Belum ada screenshot final lokal | MANUAL | YA | `L1_03_Hasil_Rekomendasi.png` | Ikuti SS-03 |
| 4 | 1.4 | Simulasi visual | `artifacts/sidang_live/phone_e2e_visual.png` | ADA | YA, opsional pembaruan | `L1_04_Simulasi_Visual.png` | Kandidat lokal disalin sebagai `L1_04_Simulasi_Visual_existing.png` |
| 5 | 1.5 | Riwayat | Belum ada screenshot final lokal | MANUAL | YA | `L1_05_Riwayat.png` | Ikuti SS-05 |
| 6 | 2.1 | Health backend | `artifacts/test_reports/node_backend_tests.txt` | ADA | TIDAK | - | Gunakan ringkasan, bukan dump log |
| 7 | 2.2 | Validasi rekomendasi | `artifacts/test_reports/node_backend_tests.txt` | ADA | TIDAK | - | Memuat bukti input dan rule ID |
| 8 | 2.3 | Decision table 30 kunci | `artifacts/test_reports/node_backend_tests.txt` | ADA | TIDAK | - | Empat kelas keluaran tercakup |
| 9 | 2.4 | Parser dan cache BMKG | `artifacts/test_reports/node_backend_tests.txt` | ADA | TIDAK | - | Nilai tidak tersedia tetap null |
| 10 | 2.5 | Inference API | `thesis_output/evidence/software_verification_20260821.json` | ADA | TIDAK | - | 29 test inference tercatat |
| 11 | 2.6 | Proxy visual | `artifacts/test_reports/backend_inference_proxy_live_contract.json` | ADA | TIDAK | - | Bukti kontrak provider mock |
| 12 | 2.7 | Riwayat Flutter | `artifacts/test_reports/flutter_tests.txt` | ADA | TIDAK | - | Bukti service/widget lokal |
| 13 | 2.8 | Screenshot ringkasan test | `thesis_output/evidence/software_verification_20260821.json` | MANUAL | YA | `L8_01_Ringkasan_Pengujian.png` | Ikuti SS-08 tanpa menjalankan test ulang |
| 14 | 3.1 | Integrasi BMKG Aikmel | `artifacts/test_reports/node_bmkg_live_summary.json` | ADA | TIDAK | - | ADM4, 18 titik, 3 hari |
| 15 | 3.2 | Respons BMKG lengkap | `artifacts/test_reports/live_bmkg_aikmel.json` | ADA | TIDAK | - | Gunakan bagian ringkas bila ditempel ke Word |
| 16 | 4.1 | Decision table readable | `docs/DECISION_TABLE.md` | ADA | TIDAK | - | 30 aturan dan batas validasi ahli |
| 17 | 4.2 | Contoh rule ID live | `artifacts/test_reports/node_bmkg_live_summary.json` | ADA | TIDAK | - | `ROT-RENDAH-CUKUP-PADI-SAWAH` |
| 18 | 5.1 | Distribusi dataset final | `docs/DATASET_CARD.md` | ADA | TIDAK | - | 389 total; 312 train; 77 validation |
| 19 | 5.2 | Training final dan LoRA | `artifacts/model_evaluation/kaggle_run_20260820T143551Z/RESULTS.md` | ADA | TIDAK | - | Run final dan hash terverifikasi |
| 20 | 5.3 | Grafik loss main | `thesis_output/figures/gambar_4_1_loss_main_training.png` | ADA | TIDAK | `L5_01_Loss_Main_Training.png` | Gambar existing disalin |
| 21 | 5.4 | Screenshot Kaggle training | Tidak tersedia sebagai screenshot lokal final | MANUAL | YA | `L5_03_Kaggle_Training_Final.png` | Ikuti SS-06; jangan jalankan ulang |
| 22 | 6.1 | Hasil analyzer review | `artifacts/model_evaluation/kaggle_run_20260820T143551Z/POST_REVIEW_ANALYSIS_REPORT.md` | ADA | TIDAK | - | 72 penilaian dan 36 pasangan |
| 23 | 6.2 | Verifikasi review | `artifacts/model_evaluation/kaggle_run_20260820T143551Z/post_review_verification.json` | ADA | TIDAK | - | Seluruh check bernilai true |
| 24 | 6.3 | Contact sheet padi | `artifacts/model_evaluation/kaggle_run_20260820T143551Z/contact_sheets/padi_base_vs_lora.jpg` | ADA | TIDAK | `L6_01_Padi_Base_vs_LoRA.jpg` | Gambar existing disalin |
| 25 | 6.4 | Contact sheet jagung | `artifacts/model_evaluation/kaggle_run_20260820T143551Z/contact_sheets/jagung_base_vs_lora.jpg` | ADA | TIDAK | `L6_02_Jagung_Base_vs_LoRA.jpg` | Gambar existing disalin |
| 26 | 6.5 | Contact sheet cabai | `artifacts/model_evaluation/kaggle_run_20260820T143551Z/contact_sheets/cabai_base_vs_lora.jpg` | ADA | TIDAK | `L6_03_Cabai_Base_vs_LoRA.jpg` | Gambar existing disalin |
| 27 | 6.6 | Contact sheet kacang tanah | `artifacts/model_evaluation/kaggle_run_20260820T143551Z/contact_sheets/kacang_tanah_base_vs_lora.jpg` | ADA | TIDAK | `L6_04_Kacang_Tanah_Base_vs_LoRA.jpg` | Gambar existing disalin |
| 28 | 6.7 | Grafik kesesuaian keseluruhan | `thesis_output/figures/gambar_4_2_kesesuaian_komoditas_overall.png` | ADA | TIDAK | `L6_05_Kesesuaian_Overall.png` | Gambar existing disalin |
| 29 | 6.8 | Grafik per komoditas | `thesis_output/figures/gambar_4_4_kesesuaian_per_komoditas.png` | ADA | TIDAK | `L6_06_Kesesuaian_Per_Komoditas.png` | Gambar existing disalin |
| 30 | 7.1 | E2E tampil di Android | `artifacts/sidang_live/phone_e2e_visual.png` | ADA | TIDAK | `L1_04_Simulasi_Visual_existing.png` | Bukti fungsional, bukan kualitas semantik universal |
| 31 | 7.2 | PNG backend 512 x 512 | `artifacts/sidang_live/e2e_backend_padi.png` | ADA | TIDAK | `L7_01_E2E_Backend_PNG.png` | Gambar existing disalin |
| 32 | 7.3 | Provider Diffusers/CUDA/hash final | Tidak ada screenshot runtime lengkap di folder lokal | MANUAL | YA | `L7_02_Runtime_GPU_Ready.png` | Ikuti SS-07; rahasiakan token dan URL |
| 33 | 8.1 | Ringkasan pengujian | `thesis_output/evidence/software_verification_20260821.json` | ADA | YA, bila perlu gambar | `L8_01_Ringkasan_Pengujian.png` | Ikuti SS-08 tanpa rerun |
| 34 | 8.2 | APK debug terverifikasi | `artifacts/apk/APK_PROXY_BUILD_REPORT.md` | ADA | TIDAK | - | Package, size, hash, SDK, dan signature tercatat |
| 35 | 8.3 | APK release terbaru | `mobile-flutter/tani_adaptif/build/app/outputs/flutter-apk/app-release.apk` | ADA | TIDAK | - | File dan SHA-1 sidecar ada; laporan package/signature setara TIDAK TERSEDIA |
| 36 | Batas | UAT/responden/validasi ahli | Tidak pernah dilakukan | TIDAK TERSEDIA | TIDAK | - | Jangan dibuat atau diklaim |

## Artefak yang Disalin

1. `L1_01_Beranda_Cuaca_existing.png`
2. `L1_04_Simulasi_Visual_existing.png`
3. `L5_01_Loss_Main_Training.png`
4. `L6_01_Padi_Base_vs_LoRA.jpg`
5. `L6_02_Jagung_Base_vs_LoRA.jpg`
6. `L6_03_Cabai_Base_vs_LoRA.jpg`
7. `L6_04_Kacang_Tanah_Base_vs_LoRA.jpg`
8. `L6_05_Kesesuaian_Overall.png`
9. `L6_06_Kesesuaian_Per_Komoditas.png`
10. `L7_01_E2E_Backend_PNG.png`

