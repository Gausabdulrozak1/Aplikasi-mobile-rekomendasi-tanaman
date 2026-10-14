# Autonomous Audit Report

Audit date: 2026-08-04 (Asia/Makassar)  
Repository: `D:\TaniAdaptif`

## Scope and Preservation

- Pre-work Git status was saved to `pre_work_git_status.txt` before edits.
- The worktree already consisted primarily of untracked project files. No reset,
  clean, raw-dataset deletion, or user-change rollback was performed.
- Inventory (excluding `.git`, `.venv`, `node_modules`, and `.dart_tool`
  internals): 1,268 files and 467,002,852 bytes.

## Toolchain

| Component | Actual result | Status |
| --- | --- | --- |
| Python | 3.11.9 via root `.venv` | ready |
| pip | 26.1.2 | ready |
| Node.js | 24.14.0 | ready |
| npm | 11.9.0 | ready |
| Flutter | 3.41.4 stable | ready |
| Dart | 3.11.1 | ready |
| Android SDK | 36.1.0; platform/build-tools 36.1 | ready |
| Java | JDK 21 supplied by Android Studio | ready through Flutter |
| Android licenses | accepted | ready |
| Android device | none connected | build possible; device test pending |
| Visual Studio | unavailable | irrelevant to Android build |
| Local NVIDIA GPU | not detected | unsuitable for LoRA training |

No large local ML dependency was installed during this audit.

## Dataset and ML Pipeline

- Raw dataset: 499 readable images, 186,141,724 bytes.
- Raw distribution: padi/public 219, padi/local_aikmel 30, jagung/public
  80, cabai/public 80, kacang_tanah/public 90.
- Aggregate raw SHA-256 before and after audit:
  `a863279be5df0a9c3a146bbb2912ffb06eaecbe5bc94cf9c08681fa8e5ee1939`.
- Technical audit: 499 valid/openable, zero invalid, zero exact duplicates,
  zero reported near duplicates, and zero cross-class duplicates.
- Reproducible technical candidate set: 350 images (padi 100, jagung 80,
  cabai 80, kacang_tanah 90).
- Manual review gate: 0 accepted, 0 rejected, 350 pending. Processed split,
  metadata, and research-final ZIP therefore do not yet exist.
- Provenance manifest has 499 rows. Source URL/license fields are unresolved for
  all rows and are recorded as warnings rather than fabricated values.
- Six notebooks parse successfully and contain preparation/training/evaluation
  guards. Training outputs and checkpoints do not exist.
- Dataset test suite before this run: 33 passed; Ruff check passed.

## Runtime Services

### BMKG and Rule Engine

- Live HTTPS request to BMKG for ADM4 `52.03.09.2002` succeeded during audit.
- Response identified Aikmel and contained 17 forecast points in the currently
  available partial horizon; `tp` was present in the observed response.
- Existing service already had a 15-second timeout, 30-minute in-memory cache,
  and last-known cache fallback.
- Audit found unsafe conversion of missing precipitation to zero and a fixed
  `3 days x 10` monthly projection. These were classified as high-priority
  correctness issues.
- Decision table contains 30 weather/water/previous-crop combinations and four
  allowed output crops. The original response lacked an explicit rule ID and
  auditable input summary; land type was validated but did not affect priority.

### Inference API

- FastAPI provider abstraction, mock provider, Diffusers provider, health,
  model-info, and generate routes already existed.
- Missing from the audited contract: `/ready`, structured agricultural request,
  request-ID continuity, bounded retry, and broader failure/timeout tests.
- Root virtual environment did not yet contain FastAPI runtime dependencies.
- No real LoRA artifact was found; real provider cannot be declared ready.

### Flutter

- Baseline `flutter pub get`: succeeded.
- Baseline `flutter analyze`: no issues.
- Baseline `flutter test`: 6 passed.
- Findings: localhost URLs were hardcoded, trigger tokens were stale, repository
  and weather cache abstractions were absent, Android INTERNET permission was
  absent, release build referenced debug signing, and Gradle requested 8 GB heap.

### Local Storage

- Node includes a local SQLite schema at `backend-nodejs/data/tani_adaptif.db`.
- Flutter stores visual history in SharedPreferences directly from the result
  screen; this requires extraction into a testable repository/cache layer.

## Credentials, Network, and Remote Compute

- Network checks to BMKG, Hugging Face, pub.dev, and Google Android endpoints on
  TCP 443 succeeded.
- No credential values were read or printed.
- Presence-only checks found no configured Kaggle token, Hugging Face token,
  Google Cloud credentials, cloud-provider credentials, Google Drive synced
  path, or configured SSH GPU target.
- `nvidia-smi` is unavailable locally and no authenticated remote GPU execution
  path is available. Stable Diffusion training must not run on this laptop CPU.

## Initial Risk Decisions

| Priority | Finding | Decision |
| --- | --- | --- |
| high | Missing BMKG rain became `0` | preserve null and expose coverage |
| high | Training would require unavailable GPU/auth | do not train locally; continue independent phases |
| high | Dataset provenance and human review incomplete | keep research-final split/package blocked |
| medium | Inference contract did not match app domain | implement structured request and tests |
| medium | Flutter localhost/signing/permission settings unsafe | use environment config; build debug only |
| medium | Rule decisions lacked traceability | add rule ID, reason, recommended crop, input summary |

This report records the pre-implementation audit. Later outcomes are recorded in
the final autonomous report and test artifacts; they do not retroactively alter
the initial observations above.
