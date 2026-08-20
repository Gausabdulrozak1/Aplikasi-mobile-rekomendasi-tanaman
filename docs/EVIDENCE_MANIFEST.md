# Evidence Manifest BAB IV

Tanggal: 21 Agustus 2026  
Run model final: `20260820T143551Z`

Manifest ini memetakan setiap klaim penting ke file sumber dan metode verifikasinya. Hash file hasil generasi tersedia di `thesis_output/evidence/bab_iv_generated_asset_manifest.json`.

| Klaim | Nilai/hasil | File sumber | Metode verifikasi |
| --- | --- | --- | --- |
| Pipeline training selesai | `status=success` | `artifacts/model_evaluation/kaggle_run_20260820T143551Z/complete_pipeline_state.json` | Parse JSON dan cocokkan run ID/status |
| Smoke test | 100 langkah, PASS, 250,79 detik | `smoke_validation.json` | Parse `actual_step`, `status`, `elapsed_seconds` |
| Main training | 1.600 langkah, SUCCESS, 3.346,29 detik | `main_validation.json` | Parse step/status/checkpoint/return code |
| Model dasar | `stable-diffusion-v1-5/stable-diffusion-v1-5` | `training_config.json` | Parse konfigurasi aktual |
| Dataset final | 389 gambar; 312 train; 77 validasi | `final_training_report.json`, `local_evidence_summary.json` | Cocokkan count dan validasi fisik |
| Distribusi kelas | padi 95, jagung 100, cabai 97, kacang tanah 97 | `local_evidence_summary.json` | Parse `dataset_counts.classes` |
| Model LoRA final | 6.414.992 byte; 256 tensor | `main_validation.json`, model lokal | Cek ukuran dan metadata SafeTensors dari validator |
| Hash model final | `0bda8908d577513110c22cf5ec1b8a7e008d2b26dd90525732a5c4e4b1bdd43a` | `artifacts/models/multisource_multicrop_lora_sd15/multisource_multicrop_lora.safetensors` | SHA-256 streaming |
| Loss main | 8.001 observasi; mean 0,186001; median 0,113000 | `main_loss_history.csv`, `local_evidence_summary.json` | Parse CSV tanpa mengubah data |
| Sanity inference training | 4/4 gambar valid | `final_training_report.json` | Parse hasil sanity |
| Desain evaluasi | 36 kondisi, 72 gambar, prompt/seed identik | `post_review_verification.json` | Seluruh pair checks harus `true` |
| Human review selesai | 72/72; 9 kondisi per komoditas | `human_review_completion.json`, `post_review_verification.json` | Validator `complete=true`, tidak ada sel wajib kosong |
| Sumber review | Evaluasi visual teknis oleh peneliti | `human_review_analysis.json` | `reviewer_role=Peneliti`; tidak disebut UAT/ahli |
| Skor otomatis | Tidak dimasukkan | `human_review_analysis.json` | `automated_scores_inserted=false` |
| Kesesuaian Base | 31/36 = 86,11% | `human_review_analysis.json` | Parse `overall.base.crop_correct` |
| Kesesuaian LoRA | 34/36 = 94,44% | `human_review_analysis.json` | Parse `overall.lora.crop_correct` |
| Selisih deskriptif | +8,33 poin persentase | `human_review_analysis.csv` | Baris overall `crop_correct` |
| Exact McNemar | `p=0,25` | `human_review_analysis.json` | Uji pasangan discordant dari analyzer |
| Konteks lahan | Base mean/median 4,0278/4,5; LoRA 3,8611/4,0 | `human_review_analysis.json` | Parse ringkasan ordinal |
| Realisme visual | Base mean/median 4,0278/4,5; LoRA 3,8611/4,0 | `human_review_analysis.json` | Parse ringkasan ordinal |
| Exact sign test keseluruhan | `p=0,6072387695` untuk konteks dan realisme | `human_review_analysis.json` | Exact sign test, tie dikeluarkan |
| Confusion/unclear | Base 5; LoRA 2 | `human_review_analysis.json` | `cross_class_or_unclear_count` |
| Kacang tanah | Base 4/9; LoRA 7/9; median 2 ke 4 | `human_review_analysis.json` | Parse hasil per kelas |
| BMKG live tercatat | 18 titik, 3 hari, 18 field hujan lengkap | `artifacts/test_reports/node_bmkg_live_contract.json` | Parse respons uji 5 Agustus 2026 |
| Kode Aikmel | ADM4 `52.03.09.2002` | `backend-nodejs/src/config/wilayah.js`, `node_bmkg_live_summary.json` | Cocokkan konfigurasi dan respons |
| Rule engine | 30 kunci deterministik; empat kelas keluaran | `backend-nodejs/src/config/aturanRotasi.js`, test backend | Enumerasi seluruh kunci dalam test |
| Rekomendasi dapat diaudit | rule ID, alasan, input summary | `rekomendasiService.js`, test backend | Uji kontrak output |
| Python tests | 125 passed | `thesis_output/evidence/software_verification_20260821.json` | Eksekusi pytest pada 21 Agustus 2026 |
| Backend tests | 23 passed | file verifikasi perangkat lunak | Eksekusi `npm test` |
| Flutter tests | 13 passed | file verifikasi perangkat lunak | Eksekusi `flutter test` |
| UI review tests | 18 passed (11+7) | file verifikasi perangkat lunak | Dua Node test suites |
| Static/lint/security | Flutter analyze, Ruff, preflight, notebook, secret scan lulus | file verifikasi perangkat lunak | Eksekusi command terkait |
| Dependency audit | pip-audit bersih; npm audit 0 vulnerability | file verifikasi perangkat lunak | Eksekusi audit 21 Agustus 2026 |
| APK debug | 152.840.310 byte; SHA-256 `417604f6...cedb5` | `artifacts/apk/taniadaptif-debug-proxy-20260821.apk` | Cek file dan SHA-256 |
| Kontrak visual lokal | Express ke FastAPI mock ke Express PNG lulus | `backend_inference_proxy_live_contract.json` | Cek `passed=true`, `real_stable_diffusion=false` |
| E2E GPU nyata | Belum tersedia | `gpu_preflight.json`, `real_inference_e2e_report.json` | File wajib belum ada; tidak boleh diklaim |
| Screenshot Android nyata | Belum tersedia | screenshot final dari perangkat | Bukti wajib belum ada; tidak boleh diganti mockup |

## Data Sumber Tabel dan Gambar

- `thesis_output/tables/source_main_loss_history.csv`
- `thesis_output/tables/source_human_review_analysis.csv`
- `thesis_output/tables/tabel_4_1_ringkasan_implementasi.csv` sampai `tabel_4_13_software_verification.csv`
- `thesis_output/figures/gambar_4_1_loss_main_training.png` sampai `gambar_4_6_contoh_pasangan_base_lora.png`
- `thesis_output/evidence/bab_iv_generated_asset_manifest.json`

## Batas Bukti

Rekomendasi tanaman berasal dari rule-based engine. Stable Diffusion 1.5 dan LoRA hanya menghasilkan simulasi visual. Review 72 gambar merupakan evaluasi visual teknis oleh peneliti, bukan UAT atau validasi ahli. Kontrak mock membuktikan perilaku perangkat lunak, bukan keberhasilan inference model nyata.
