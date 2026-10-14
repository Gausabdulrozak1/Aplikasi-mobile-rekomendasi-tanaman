# Final Autonomous Report

Latest verification: 2026-08-05 (Asia/Makassar)

## 1. Final Status

TaniAdaptif is ready for local mock-stack and debug-APK testing. The Node rule
engine, live BMKG integration, FastAPI mock visual service, Flutter client,
automated tests, documentation, and debug APK are complete within the available
environment. Research-final dataset packaging and LoRA work remain gated by
human review/provenance and authenticated GPU access.

## 2. Initial Condition and Changes

The repository began almost entirely untracked, with an audited dataset
pipeline and unfinished/stale application evidence. This run preserved the
worktree and raw files, then finalized BMKG null/cache behavior, auditable rule
outputs, four-week recommendation projection, FastAPI contracts/providers,
Flutter cache/history/error flows, automated screening, Colab smoke/main
preparation, tests, security remediation, docs, instruments, and APK evidence.
The continuation also separated the one-class public-padi pilot trigger from
the final multicrop triggers, added a CPU-only Colab-artifact validator, and
added a bounded direct-prompt compatibility mode without changing the
rule-based recommendation flow used by Flutter.

## 3. Dataset Evidence

| Class | Raw public | Raw local Aikmel | Technical candidates | Manual accepted | Manual rejected | Manual pending | Final | Train | Validation |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | --- | --- | --- |
| padi | 219 | 30 | 100 (70 public, 30 local) | 0 | 0 | 100 | not created | not created | not created |
| jagung | 80 | 0 | 80 | 0 | 0 | 80 | not created | not created | not created |
| cabai | 80 | 0 | 80 | 0 | 0 | 80 | not created | not created | not created |
| kacang_tanah | 90 | 0 | 90 | 0 | 0 | 90 | not created | not created | not created |
| **Total** | **469** | **30** | **350** | **0** | **0** | **350** | **not created** | **not created** | **not created** |

- Technical audit: 499/499 valid, 0 invalid, 0 exact duplicate, 0 near
  duplicate at dHash threshold 5, and 0 cross-class/cross-source duplicate.
- Automated proxy: 322 proxy-pass and 28 proxy-review; 11 close-up and 17
  vegetation-not-detected flags. It is not human review.
- Raw aggregate SHA-256 remained
  `a863279be5df0a9c3a146bbb2912ffb06eaecbe5bc94cf9c08681fa8e5ee1939`.
- Provenance/license/source URL/identifier/access date remain incomplete for all
  499 rows. No value was invented.
- Jagung, cabai, and kacang tanah are public-only and are not claimed as Aikmel
  visual representation.
- Contact sheets: `artifacts/dataset_review/review_{class}.jpg`.
- Human review: `artifacts/dataset_review/manual_review_template.csv`.
- Train metadata, validation metadata, package ZIP, package checksum, and
  package manifest do not exist because the hard gate is active.

## 4. ML and GPU Status

- Six notebooks are valid nbformat-4 JSON and every code cell compiles.
- Pilot padi uses `gaus_padi_public`; the final multicrop pipeline continues to
  use the four `taniadaptif_*` triggers. Pilot config and notebook checks are
  covered by automated tests.
- Pilot preparation is configured to persist processed data to Drive. Pilot training is
  Colab/CUDA guarded, uses a pinned Diffusers revision, supports latest-checkpoint
  resume, and falls back from fp16 only when GPU capability requires it.
- The CPU-only external-artifact validator checks nonempty checkpoint content,
  SafeTensors header/tensor ranges, finite loss, fatal logs, GPU evidence, and
  readable validation PNGs; it does not load a diffusion model.
- Training notebook separates smoke 100/50 and main 1600/200 runs, outputs,
  resume checkpoints, logs, actual config, success manifest, and four validation
  images.
- No authenticated remote GPU was found. Local CPU training was not attempted.
- Smoke test: `not_run`. Main training: `not_run`.
- Checkpoint/LoRA/model location: none.
- Base-versus-LoRA evaluation and automatic metrics: `not_run`; templates are
  present but blank.
- Torch, torchvision, Diffusers, Transformers, Accelerate, xFormers, and
  BitsAndBytes remain absent locally.

## 5. Application Status

- Node backend: 16 tests passed; live health endpoint passed.
- BMKG: live Aikmel request returned 18 currently available points with complete
  precipitation values; timeout, fresh cache, stale fallback, null rain, source,
  and timestamp behavior are tested.
- Rule engine: all 30 decision-table keys produce deterministic, constrained
  crops with `recommendedCrop`, `ruleId`, `reason`, and `inputSummary`.
- Calendar: live response contains four weeks; weeks 2-4 are explicitly low-
  confidence projections from the short BMKG horizon.
- FastAPI: 16 tests passed; mock health/readiness/model-info/generate passed
  live for structured Flutter and direct pilot payloads. The mock output is
  labelled `is_mock=true` and `research_output=false`; direct prompt input does
  not become a crop recommendation.
- Flutter: analyze clean and 13 tests passed for DTO/service/repository/cache,
  history, form, and visual-failure behavior.
- Flutter doctor: Android SDK 36.1/JDK 21/licences/network passed. Visual Studio
  is absent, which affects optional Windows desktop builds, not Android APKs.

## 6. Security and Dependencies

- `npm audit --omit=dev`: 0 vulnerabilities after compatible transitive updates.
- `pip-audit`: exit 0, no known vulnerabilities found after updating secure
  Python pins.
- `pip check`, secret scan, preflight, Ruff lint, and Ruff format: passed.
- Final review: `artifacts/autonomous_run/FINAL_SECURITY_REVIEW.md`.

## 7. APK

- File: `artifacts/apk/taniadaptif-debug.apk`.
- Size: 152,840,310 bytes.
- SHA-256:
  `ffb15a9f38c4242d2482976d71e101f1564eab2cbbd48eda78b59b37409d2996`.
- Package/version: `com.hamzanwadi.tani_adaptif`, 1.0.0 (code 1).
- minSdk/targetSdk: 24/36; ABIs: arm64-v8a, armeabi-v7a, x86_64.
- APK Signature Scheme v2 and INTERNET permission verified.
- Release APK was not built without an authorized signing identity.
- Physical-device installation remains `pending-device-test`.

## 8. Automated Results

| Command group | Result |
| --- | --- |
| Dataset pytest | 38 passed |
| Inference pytest | 16 passed |
| Node tests | 16 passed |
| Flutter tests | 13 passed |
| Flutter analyze | no issues |
| Ruff | lint and format check passed; 54 files formatted |
| Notebook validation | 6 JSON valid; 57 code cells compile |
| npm/pip audits | 0 / no known vulnerabilities |
| Live integration | Node, BMKG, calendar, FastAPI structured/direct mock passed |

Actual logs are under `artifacts/test_reports/`. Material failed commands and
their resolutions are retained in `AUTONOMOUS_RUN_LOG.md`; no failure was
silently converted into a pass.

## 9. Documentation and Research Instruments

Architecture, API, decision table, deployment, Colab, user guide, black-box
evidence, dataset card, thesis evidence, and BAB III/IV templates are under
`docs/`. Blank Markdown/CSV instruments for observation, interview, expert
validation, black box, UAT, visual quality, consent, and recap are under
`docs/research_instruments/`. No respondent, expert, UAT, or interview result
was fabricated.

## 10. Remaining Risks and Human Gates

- Human dataset review and verifiable provenance/licenses are incomplete.
- Real Diffusers/LoRA, GPU stability, model quality, and model confusion are
  untested.
- Physical-device networking/UI/UAT and release signing are pending.
- Production requires HTTPS endpoints, edge rate/request-size controls, real
  deployment credentials, and operational monitoring.

Minimum next step: verify and record the source identity, URL, and license for
the public padi source in `ml_pipeline/data/dataset_source_manifest.csv`. This
unblocks a lawful pilot review before any Colab training claim.

## 11. Reproduction Commands

```powershell
cd D:\TaniAdaptif
.\.venv\Scripts\python.exe -m pytest ml_pipeline\tests inference_api\tests -q
.\.venv\Scripts\python.exe -m ruff check ml_pipeline inference_api
node ml_pipeline\scripts\validate_notebooks.mjs
node ml_pipeline\scripts\preflight_check.mjs
node ml_pipeline\scripts\security_scan.mjs
.\.venv\Scripts\python.exe -m ml_pipeline.src.training.validate_run --help

cd D:\TaniAdaptif\backend-nodejs
npm test
npm audit --omit=dev

cd D:\TaniAdaptif\mobile-flutter\tani_adaptif
flutter analyze
flutter test
flutter build apk --debug
```

Run commands for the local stack are in `docs/DEPLOYMENT_RUNBOOK.md`.
