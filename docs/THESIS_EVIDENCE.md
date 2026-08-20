# Thesis Evidence Map

Evidence date: 2026-08-21. `actual` means the command/file exists in this run;
`pending` means the thesis must not claim a result yet.

| Claim/topic | Evidence file | Reproduction command/activity | Status | Actual result | Suggested BAB IV section |
| --- | --- | --- | --- | --- | --- |
| Local toolchain | `artifacts/autonomous_run/AUDIT_REPORT.md` | version and doctor commands in final report | actual | Python 3.11.9, Flutter 3.41.4, Android SDK 36.1 | implementation environment |
| Audited dataset population | `inventory_all_classes.csv`, `DATASET_CARD.md` | dataset CLI `audit` | actual | 624 technical files: 249 padi, 130 jagung, 120 cabai, 125 kacang tanah | dataset audit |
| Raw integrity | `DATASET_CARD.md` | compare aggregate raw SHA-256 | actual | unchanged digest `a863279...1939` | dataset integrity |
| Technical image audit | `ml_pipeline/data/reports/audit_summary.md` | dataset CLI `audit` | actual | 624 valid technical records; no final cross-split duplicate leakage | data cleaning |
| Provenance completeness | source manifest and `provenance_warnings.csv` | dataset CLI `audit` | actual limitation | 125 additions have verified source/license; older inventory warnings remain | limitations |
| Review candidates | `curation_mapping.csv` | dataset CLI `finalize-reviewed` | actual | 475 candidates: 100/130/120/125 | curation |
| Automated screening | `automated_semantic_review_summary.md` | dataset CLI `screen` | actual proxy | 447 proxy-pass, 28 proxy-review; not human validation | curation proxy |
| Human dataset review | `manual_review_template.csv`, `manual_review_summary.csv` | consented/manual review | actual | accepted 390, rejected 85, unsure 0, pending 0; per class accepted 95/101/97/97 | dataset curation |
| Final package validation | `artifacts/dataset_packages/final_package_validation.*` | dataset CLI `validate-package` | actual valid gate | 389 final, 312 train, 77 validation; ZIP/checksum/metadata/source policy/triggers/leakage valid | dataset result |
| Public-padi pilot design | `pilot_padi.yaml`, pilot notebooks | config/notebook validators | actual preparation | one class, `gaus_padi_public`, 800 steps, checkpoint 200; no training execution | pilot setup |
| Training artifact validator | `ml_pipeline/src/training/validate_run.py`, `validate_kaggle_export.py`, pytest | CPU-only fixture tests and final ZIP validation | actual software result | validates ZIP CRC/hash, canonical SafeTensors structure and 256 tensors, manifests, finite loss, statuses, and 76 readable images without loading Stable Diffusion | reproducibility tooling |
| Notebook validity | `00_train_lora_multicrop_kaggle_final.ipynb`, contract tests, Kaggle log | notebook validators and Kaggle Run All | actual execution | 52 cells parse/compile; version 2 completed through Cell 51 with `FINAL STATUS: SUCCESS` | experiment setup |
| LoRA smoke/main training | `artifacts/model_evaluation/kaggle_run_20260820T143551Z/` | Kaggle GPU run `20260820T143551Z` | actual | smoke 100 steps PASS; main 1600 steps SUCCESS; final canonical LoRA 6,414,992 bytes and 256 tensors; SHA-256 `0bda890...dd43a` | model training |
| Final export integrity | `artifacts/kaggle_runs/notebook6b00d019aa/version_2_success_20260820/local_export_validation.json` | `python -m ml_pipeline.src.training.validate_kaggle_export ...` | actual valid gate | 51,940,573-byte ZIP; SHA-256 `54ee68...b26a`; 100 files, all required manifests/hashes/statuses consistent; no errors | reproducibility |
| Model evaluation | `artifacts/model_evaluation/kaggle_run_20260820T143551Z/RESULTS.md` | Kaggle evaluation plus local evidence materialization | actual proxy only | 36 matched conditions, 36 base + 36 LoRA images, 4 sanity images; brightness/contrast/entropy proxy complete | model evaluation |
| Human LoRA evaluation | `human_evaluation_template_local.csv`, `human_review_completion.json`, paired contact sheets | reviewer completed and finalized 72 rows | actual human-entered evidence | 72/72 complete, 36 matched pairs, 9 conditions/class, prompt/seed identity valid, `automated_scores=false`; software cannot independently verify reviewer identity | visual validation |
| Paired human-review analysis | `human_review_analysis.json`, `.csv`, `BAB_IV_HUMAN_REVIEW_RESULTS.md`, `POST_REVIEW_ANALYSIS_REPORT.md` | validator `--require-complete` then analyzer | actual validated output | Base correct 31/36, LoRA 34/36, difference +8.33 pp, exact McNemar p=0.25; full class and ordinal summaries preserved in output | visual validation |
| BMKG integration | `artifacts/test_reports/node_bmkg_live_contract.json`, Node tests | `npm test`, live GET | actual | live Aikmel response had 18 available points with complete rain values; null-safe and cache states tested | weather integration |
| Decision table | `docs/DECISION_TABLE.md` | `npm test` | actual software result | all 30 rows deterministic; expert approval pending | recommendation result |
| Backend inference proxy | `backend_inference_proxy_live_contract.json`, Node regression tests | local Express -> authenticated FastAPI mock -> Express PNG | actual software result, mock only | private token forwarding, upstream URL hiding, client token, error mapping, and PNG delivery pass; not real SD evidence | visual integration |
| FastAPI mock | inference tests and `fastapi_live_contract.json` | pytest inference suite plus live HTTP | actual software result | provider/token/readiness/generate contracts pass; output is explicitly mock | visual integration |
| Real GPU inference | `gpu_preflight.json`, `real_inference_e2e_report.json`, real PNG | RunPod deployment and e2e probe | pending-external-gpu | deployment scripts and fail-closed probe ready; no authenticated GPU run exists yet | visual integration |
| Flutter integration | Flutter test logs | `flutter analyze`, `flutter test` | actual software result | Flutter calls only Express visual routes; cache/history/request ID/error behavior passes | application result |
| Visual failure isolation | widget test | Flutter visual-failure test | actual software result | recommendation remains visible | robustness |
| Debug APK | `artifacts/apk/APK_BUILD_REPORT.md` | Flutter build, apksigner, aapt2 | actual artifact | verified debug APK and checksum | deployment result |
| Physical-device test | black-box result and Android screenshot | install on device against real GPU backend | pending-device-test | no final real-inference screenshot exists yet | testing |
| Expert validation | blank validation instrument | agricultural expert review | pending-human-research | no score/signature | validation |
| Farmer UAT/interview | blank research instruments | consented field study | pending-human-research | no respondent/result | UAT |

Mock placeholders and synthetic test fixtures prove software behavior only.
They must never be reported as LoRA quality, farmer response, or field evidence.
