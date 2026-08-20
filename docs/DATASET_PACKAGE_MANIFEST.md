# Dataset Package Manifest

- Version: `dataset_multicrop_v1`
- Date: 2026-08-13
- ZIP size: 188356224 bytes
- ZIP SHA-256: `f6aa060658cf95e48996f10f0ffde200938d340dd15e6b60adace5bb5cecfb33`
- Seed: 42
- Minimum resolution: 512x512
- Padi public: 70
- Padi local_aikmel: 25
- Jagung, cabai, and kacang_tanah are public-only by research design.

## Split Counts

| Class | Train | Validation |
| --- | ---: | ---: |
| padi | 76 | 19 |
| jagung | 80 | 20 |
| cabai | 78 | 19 |
| kacang_tanah | 78 | 19 |

## Triggers

- `padi`: `taniadaptif_padi`
- `jagung`: `taniadaptif_jagung`
- `cabai`: `taniadaptif_cabai`
- `kacang_tanah`: `taniadaptif_kacang_tanah`

## Main Files

- `processed/train/metadata.jsonl`
- `processed/validation/metadata.jsonl`
- `reports/curation_mapping.csv`
- `reports/split_manifest.csv`
- `reports/split_summary.json`
- `reports/split_summary.md`
- `reports/class_balance_report.csv`
- `reports/manual_review_summary.csv`
- `reports/metadata_validation_report.json`
- `reports/metadata_validation_report.md`
- `reports/final_curation_summary.md`
- `reports/additional_source_candidates.csv`
- `reports/additional_semantic_screening.csv`
- `reports/additional_semantic_summary.md`
- `reports/dataset_source_manifest.csv`
- `docs/DATASET_CARD.md`
