# Black Box Test Results

Latest execution date: 2026-08-05. These are actual automated/tool results; no physical
device, farmer UAT, expert validation, training, or human visual rating occurred.

| Case | Status | Actual result/evidence |
| --- | --- | --- |
| BB-01 | pass | Live BMKG Aikmel request returned 18 points across the currently available three-day horizon; all 18 included `tp`; `artifacts/test_reports/node_bmkg_live_contract.json` |
| BB-02 | pass | Node parser test preserved missing `tp` as null and did not estimate monthly rain |
| BB-03 | pass | Node test observed network, fresh-cache, then stale-cache fallback |
| BB-04 | pass | All 30 decision-table keys returned constrained output and audit fields |
| BB-05 | pass | Missing/invalid recommendation input and API payload rejected |
| BB-06 | pass | Calendar test returned four stable weekly ranges |
| BB-07 | pass | FastAPI mock health and ready returned HTTP 200 |
| BB-08 | pass | FastAPI generated labelled mock PNGs for four crops with final trigger/request ID |
| BB-09 | pass | Unsupported crop and invalid dimensions returned structured HTTP 422 |
| BB-10 | pass | Fixture provider failed twice (one bounded retry) then returned HTTP 503 |
| BB-11 | pass | Slow fixture returned HTTP 504, was not retried, and readiness became false |
| BB-12 | pass | Flutter repository loaded cached weather after simulated offline error |
| BB-13 | pass | Flutter recommendation cache loaded only for the same signature |
| BB-14 | pass | Widget test retained `Jagung` after visual provider failure |
| BB-15 | pass | Storage test retained newest 20 of 25 fixture history entries |
| BB-16 | pass | Clean debug build, SHA-256, APK v2 signature, SDK/package/permission verified; `artifacts/apk/APK_BUILD_REPORT.md` |
| BB-17 | pending-device-test | No Android device connected; no installation claim made |
| BB-18 | pending-human-research | UAT questionnaire prepared but no respondent or score exists |
| BB-19 | pass | FastAPI accepted the exact public-padi pilot trigger in bounded direct-prompt mode while preserving structured Flutter mode; `artifacts/test_reports/fastapi_live_contract.json` |

## Final Automated Suite Summary

- Dataset pytest: 38 passed.
- Inference pytest: 16 passed.
- Node test runner: 16 entries passed (one fixture module discovery entry).
- Flutter suite: 13 tests passed, including the visual-failure widget case.
- Flutter analyze: no issues.
- Debug APK: 152,840,310 bytes; SHA-256
  `ffb15a9f38c4242d2482976d71e101f1564eab2cbbd48eda78b59b37409d2996`.

- Live Node health, BMKG, four-week calendar, FastAPI health/readiness/model
  info/generate, and generated-image HTTP fetch passed.

Full command output is retained in `artifacts/test_reports/`. The physical
device and human-research rows remain pending and are not counted as passes.
