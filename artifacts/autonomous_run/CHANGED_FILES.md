# Changed Files

Run date: 2026-08-04; continuation 2026-08-05

## Git Attribution Limitation

The pre-work and post-work Git status show nearly the entire repository as
untracked. Git therefore cannot distinguish prior user files from files touched
in this run. No commit was created because it would risk mixing user work. The
list below is reconstructed from the autonomous work log and command history.

## Application and Tests

- `backend-nodejs/src/app.js`, `src/index.js`, BMKG/recommendation services and
  routes, `package.json`, `package-lock.json`, plus backend tests/fixtures.
- `inference_api/app/` structured API, providers, prompt/generation services,
  settings/errors/schemas, tests, requirements, examples, Dockerfile, README.
- Flutter config, DTOs, services, repository/storage, dashboard/form/result
  screens, Android manifests/Gradle settings, tests, and environment examples
  under `mobile-flutter/tani_adaptif/`.
- FastAPI schemas, prompt builder, generation route/service, tests, and API docs
  now support mutually exclusive structured Flutter and direct pilot payloads.
  Whitespace-only prompts are rejected after normalization.

## Dataset and ML Preparation

- Dataset audit, provenance, curation, package gates, semantic-screening code,
  tests, reports, source manifest, and four exact-name contact sheets.
- `ml_pipeline/configs/training_public_multicrop.yaml` with separated smoke/main
  settings.
- `02_train_public_multicrop_lora_sd15_colab.ipynb` with smoke/main selection,
  persistent log/config/manifest, final checkpoint verification, finite-loss
  validation, and four validation images.
- Notebook/preflight/security validators and lightweight dependency pins.
- Pilot configs/tests now use `gaus_padi_public` independently from final
  multicrop tokens; pilot notebooks persist to Drive and are synchronized with
  their Python mirrors. The selected config propagates through prepare,
  training, and evaluation with worker 0 and disabled external reporters.
- `ml_pipeline/src/training/validate_run.py` and tests validate real external
  training artifacts without loading an ML framework locally, including
  SafeTensors structure, checkpoint contents, and readable validation images.
- Explicit `not_run` Colab/model-evaluation reports and blank human-evaluation
  template under `artifacts/`.

## Documentation and Evidence

- `STATUS.md`, `TASKS.md`, `REQUIRED_HUMAN_ACTIONS.md`, `.gitignore`.
- Architecture, API, deployment, Colab, user, decision-table, testing, dataset,
  thesis implementation/result/evidence documents under `docs/`.
- Blank paired Markdown/CSV research instruments in
  `docs/research_instruments/`.
- Audit, execution plan/log, security review, final reports, and command logs
  under `artifacts/autonomous_run/` and `artifacts/test_reports/`.
- Verified debug APK, checksum, and build report under `artifacts/apk/`.

## Preserved Data

- No raw image was deleted, renamed, overwritten, or moved.
- The aggregate raw fingerprint remained
  `a863279be5df0a9c3a146bbb2912ffb06eaecbe5bc94cf9c08681fa8e5ee1939`.
- No model/checkpoint/dataset ZIP, credential, release key, or fabricated
  research response was created.
