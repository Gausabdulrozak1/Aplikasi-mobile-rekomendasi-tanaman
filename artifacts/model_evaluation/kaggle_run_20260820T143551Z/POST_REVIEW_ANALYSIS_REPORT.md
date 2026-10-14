# Laporan Analisis Pasca-Review LoRA

Run: `20260820T143551Z`  
Status analyzer: `complete_validated_human_review`  
Tanggal verifikasi: 2026-08-21 (Asia/Makassar)

## Gerbang Data

Kedua validator independen lulus dengan hasil berikut:

- 72 baris penilaian dan 72 assessment lengkap;
- 0 assessment parsial dan 0 field wajib kosong;
- 36 kondisi, masing-masing tepat satu Base dan satu LoRA;
- prompt, seed, dan kelas identik di dalam setiap pasangan;
- 9 kondisi untuk padi, jagung, cabai, dan kacang tanah;
- seluruh 72 PNG dapat dibuka;
- `automated_scores_inserted=false` pada completion report dan analyzer;
- `reviewer_role=Peneliti` pada 72 baris;
- 72 catatan reviewer kosong, tetapi kolom tersebut bersifat opsional;
- identitas reviewer tidak diverifikasi secara independen oleh perangkat lunak.

SHA-256 CSV review yang dianalisis:
`0fdfb5ec26f6f11cbfcea79cc6f46a778e92b90827da958201b8b9feb57b3aa7`.

## Koreksi Semantik Confusion

CSV review tidak diubah. Ringkasan awal menghitung semua nilai selain `none`
sebagai confusion, termasuk label yang sama dengan kelas target. Data mentah
menunjukkan reviewer memakai label kelas target untuk hasil yang benar dan
`unclear` untuk hasil yang salah. Definisi laporan diperbaiki menjadi:

- label yang sama dengan kelas target: konfirmasi kelas;
- `none`: tidak ada confusion eksplisit;
- label lain, `mixed`, atau `unclear`: cross-class/unclear.

Setelah koreksi, Base memiliki 31 konfirmasi dan 5 `unclear`; LoRA memiliki 34
konfirmasi dan 2 `unclear`. Completion report lama tetap tersimpan pada snapshot
input sebagai jejak audit. Tidak ada keputusan reviewer yang diedit.

## Ringkasan Statistik

| Metrik | Base | LoRA | Selisih LoRA-Base | Arah pasangan LoRA/seri/Base | p exact |
| --- | ---: | ---: | ---: | ---: | ---: |
| Komoditas sesuai | 31/36 (86,111%) | 34/36 (94,444%) | +8,333 poin persentase | 3/33/0 | 0,250000 |
| Kualitas konteks, mean; median | 4,028; 4,500 | 3,861; 4,000 | -0,167 mean | 6/21/9 | 0,607239 |
| Realisme, mean; median | 4,028; 4,500 | 3,861; 4,000 | -0,167 mean | 6/21/9 | 0,607239 |

Exact McNemar digunakan pada ketepatan komoditas dan exact sign test pada skor
ordinal dengan tie dikeluarkan. Nilai p bersifat eksploratif dan tidak
membuktikan ketepatan agronomi atau hubungan kausal.

| Kelas | N | Benar Base | Benar LoRA | Median konteks Base/LoRA | Median realisme Base/LoRA | Unclear Base/LoRA |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| padi | 9 | 100,000% | 100,000% | 4/4 | 4/4 | 0/0 |
| jagung | 9 | 100,000% | 100,000% | 5/4 | 5/4 | 0/0 |
| cabai | 9 | 100,000% | 100,000% | 5/5 | 5/5 | 0/0 |
| kacang tanah | 9 | 44,444% | 77,778% | 2/4 | 2/4 | 5/2 |

Peningkatan ketepatan kelas terutama muncul pada kacang tanah. Hasil ini tidak
mendukung klaim bahwa LoRA unggul pada setiap dimensi: skor konteks dan realisme
keseluruhan sedikit lebih rendah, terutama pada jagung. Kesimpulan final tetap
menunggu inference end-to-end nyata, screenshot Android, dan penyelarasan dengan
metode pada BAB I-III.

## Artefak Utama

Semua path berada di
`D:\TaniAdaptif\artifacts\model_evaluation\kaggle_run_20260820T143551Z\`.

| File | Byte | SHA-256 |
| --- | ---: | --- |
| `human_evaluation_template_local.csv` | 16.318 | `0fdfb5ec26f6f11cbfcea79cc6f46a778e92b90827da958201b8b9feb57b3aa7` |
| `human_review_progress.json` | 3.439 | `d34b6dc3283b9a51df88644c0ddd79b2391155c5050d4ef27163004143dd4efe` |
| `human_review_completion.json` | 3.617 | `382341715980af2831b2fa1dfc7a9f1daf73592b3d373fa683aaf579363b7d87` |
| `HUMAN_REVIEW_RESULTS.md` | 857 | `2ff1c0c37cee44eb6769c6a5025eff007102039bd417be547f708d368dd76ff0` |
| `human_review_analysis.json` | 19.685 | `cc00d98ce965be585b066c0b492c98db74ff88bf32ca08d61e139e18a56c0080` |
| `human_review_analysis.csv` | 2.001 | `ed1297494c335f4b590957fbf41e8da7b03ee2f2d4ccb7731a4f6997b8b61539` |
| `BAB_IV_HUMAN_REVIEW_RESULTS.md` | 1.773 | `c1ee5d6caffc1cbc8c2209b2d1894bb24da524d26faea82d1c450de1cff83f82` |
| `post_review_verification.json` | 3.887 | `b5fce0024eea991c33d801e00831062a0acb5a324164acf4ea76b5b01aa917bd` |

Backup tervalidasi:
`post_review_backups/20260820T181414Z/input_snapshot/` dan
`post_review_backups/20260820T181414Z/analysis_snapshot/`.

## Model Referensi

Model tidak dimuat, dilatih ulang, atau diubah pada tahap ini.

- File: `artifacts/models/multisource_multicrop_lora_sd15/multisource_multicrop_lora.safetensors`
- Ukuran: 6.414.992 byte
- SHA-256: `0bda8908d577513110c22cf5ec1b8a7e008d2b26dd90525732a5c4e4b1bdd43a`

## Perintah yang Lulus

```powershell
node tools/lora_review_ui/src/cli.mjs --require-complete

.\.venv\Scripts\python.exe -m ml_pipeline.src.evaluation.validate_human_review `
  --review-csv artifacts\model_evaluation\kaggle_run_20260820T143551Z\human_evaluation_template_local.csv `
  --report-json artifacts\model_evaluation\kaggle_run_20260820T143551Z\human_review_progress.json `
  --require-complete

.\.venv\Scripts\python.exe -m ml_pipeline.src.evaluation.analyze_human_review `
  --review-csv artifacts\model_evaluation\kaggle_run_20260820T143551Z\human_evaluation_template_local.csv `
  --output-dir artifacts\model_evaluation\kaggle_run_20260820T143551Z
```
