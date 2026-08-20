# Black Box Test Plan

## Scope

Validate observable contracts across dataset preparation, BMKG/rule API,
inference API, Flutter repositories/UI behavior, and Android packaging. Test
fixtures are explicitly synthetic and are not research/UAT results.

| Case | Surface | Input/action | Expected |
| --- | --- | --- | --- |
| BB-01 | BMKG live | GET configured Aikmel ADM4 | source/location/timestamp and forecast points returned |
| BB-02 | BMKG missing rain | response point without `tp` | null estimate/category; no invented zero |
| BB-03 | BMKG cache | success, cached call, failed refresh | network, fresh-cache, stale-cache states |
| BB-04 | Rule engine | execute every configured key | valid crop, rule ID, reason, input summary |
| BB-05 | Rule validation | missing/invalid fields | HTTP 400 or service failure contract |
| BB-06 | Calendar | valid land input | deterministic four-week period |
| BB-07 | Inference liveness | GET health/ready in mock mode | HTTP 200 and ready |
| BB-08 | Inference generate | each of four crops | placeholder, final trigger, request ID, provenance |
| BB-09 | Inference validation | unsupported crop/dimension | structured HTTP 422 |
| BB-10 | Inference failure | provider exception | bounded retry then structured HTTP 503 |
| BB-11 | Inference timeout | slow provider | HTTP 504, no retry, readiness blocked |
| BB-12 | Flutter offline weather | network result then failure | last-known cache with stale label |
| BB-13 | Flutter cache scope | same and changed land input | same input loads; changed input does not |
| BB-14 | Flutter visual failure | generate returns failure | crop recommendation remains visible |
| BB-15 | Flutter history | save 25 visual entries | newest 20 load in order |
| BB-16 | APK build | debug build and Android inspection | valid signed APK, manifest permission/SDK/package |
| BB-17 | Physical device | install and exercise end-to-end | pending-device-test until a device is available |
| BB-18 | Human UAT | consented farmer workflow | pending-human-research; never automated |

## Environments

- Windows local toolchain versions: `artifacts/autonomous_run/AUDIT_REPORT.md`.
- Python tests use root `.venv` with no heavy ML packages.
- Node tests use built-in `node:test`; BMKG service calls are mocked except BB-01.
- Flutter tests use plugin mock storage and fake HTTP adapters.
- Android debug APK targets emulator networking through `10.0.2.2`.

## Entry and Exit

Entry requires available source/config files and lightweight dependencies. Exit
requires zero failing automated cases in scope, a checksum-verified debug APK,
and explicit pending status for physical-device and human-only work.
