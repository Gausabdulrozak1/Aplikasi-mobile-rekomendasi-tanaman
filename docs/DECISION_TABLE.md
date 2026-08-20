# Decision Table Rotasi Tanam

Status: implemented and automatically tested on 2026-08-04. Agronomic expert
validation is not yet claimed.

## Inputs and Outputs

- Weather/rain category: `tinggi`, `sedang`, or `rendah`.
- Land type: `sawah`, `tegalan`, or `kebun_campur`.
- Water availability: `cukup`, `terbatas`, or `kurang`.
- Previous crop: `padi`, `jagung`, `cabai`, `kacang_tanah`, or `kosong`.
- Outputs are restricted to `padi`, `jagung`, `cabai`, and `kacang_tanah`.

Every response contains `recommendedCrop`, `ruleId`, `reason`, and
`inputSummary`. The source of truth is
`backend-nodejs/src/config/aturanRotasi.js`; this table is its readable view.

## Base Rules

| Key | Rain | Water | Previous crop | Ordered output |
| --- | --- | --- | --- | --- |
| `tinggi_cukup_padi` | tinggi | cukup | padi | padi, jagung |
| `sedang_cukup_padi` | sedang | cukup | padi | padi, jagung, kacang_tanah |
| `rendah_cukup_padi` | rendah | cukup | padi | cabai, kacang_tanah, padi |
| `tinggi_terbatas_padi` | tinggi | terbatas | padi | padi, jagung, kacang_tanah |
| `sedang_terbatas_padi` | sedang | terbatas | padi | jagung, kacang_tanah, padi |
| `rendah_terbatas_padi` | rendah | terbatas | padi | kacang_tanah, cabai, jagung |
| `tinggi_cukup_jagung` | tinggi | cukup | jagung | padi, jagung, kacang_tanah |
| `sedang_cukup_jagung` | sedang | cukup | jagung | padi, jagung, kacang_tanah |
| `rendah_cukup_jagung` | rendah | cukup | jagung | cabai, kacang_tanah, jagung |
| `tinggi_terbatas_jagung` | tinggi | terbatas | jagung | padi, jagung, kacang_tanah |
| `sedang_terbatas_jagung` | sedang | terbatas | jagung | jagung, kacang_tanah, padi |
| `rendah_terbatas_jagung` | rendah | terbatas | jagung | kacang_tanah, cabai, jagung |
| `tinggi_cukup_cabai` | tinggi | cukup | cabai | padi, jagung, cabai |
| `sedang_cukup_cabai` | sedang | cukup | cabai | padi, jagung, kacang_tanah |
| `rendah_cukup_cabai` | rendah | cukup | cabai | cabai, kacang_tanah, jagung |
| `tinggi_terbatas_cabai` | tinggi | terbatas | cabai | padi, jagung, kacang_tanah |
| `sedang_terbatas_cabai` | sedang | terbatas | cabai | jagung, kacang_tanah, cabai |
| `rendah_terbatas_cabai` | rendah | terbatas | cabai | kacang_tanah, cabai, jagung |
| `tinggi_cukup_kacang_tanah` | tinggi | cukup | kacang_tanah | padi, jagung, kacang_tanah |
| `sedang_cukup_kacang_tanah` | sedang | cukup | kacang_tanah | padi, jagung, cabai |
| `rendah_cukup_kacang_tanah` | rendah | cukup | kacang_tanah | cabai, jagung, padi |
| `tinggi_terbatas_kacang_tanah` | tinggi | terbatas | kacang_tanah | padi, jagung, kacang_tanah |
| `sedang_terbatas_kacang_tanah` | sedang | terbatas | kacang_tanah | jagung, padi, kacang_tanah |
| `rendah_terbatas_kacang_tanah` | rendah | terbatas | kacang_tanah | cabai, kacang_tanah, jagung |
| `tinggi_cukup_kosong` | tinggi | cukup | kosong | padi, jagung, kacang_tanah |
| `sedang_cukup_kosong` | sedang | cukup | kosong | padi, jagung, cabai |
| `rendah_cukup_kosong` | rendah | cukup | kosong | cabai, kacang_tanah, padi |
| `tinggi_terbatas_kosong` | tinggi | terbatas | kosong | padi, jagung, kacang_tanah |
| `sedang_terbatas_kosong` | sedang | terbatas | kosong | jagung, kacang_tanah, padi |
| `rendah_terbatas_kosong` | rendah | terbatas | kosong | kacang_tanah, cabai, jagung |

## Normalization and Land Adjustment

- `kurang` uses the `terbatas` base row and appends a strong low-water warning.
- For `sawah`, the base order is retained.
- For `tegalan` and `kebun_campur`, padi moves behind non-padi options when
  present because the project crop data marks padi as high-water and primarily
  suitable for sawah. It is not silently removed.
- A generated rule ID combines the base key and land type, for example
  `ROT-SEDANG-CUKUP-PADI-SAWAH`.
- A missing configured key uses an explicit default and sets
  `menggunakanAturanDefault=true`; invalid public input is rejected before this.

## BMKG Mapping

The BMKG service sums `tp` only when every point in the available horizon has a
numeric precipitation value. It projects the observed daily average to 30 days
and labels this as an application projection, not a BMKG monthly forecast:

- `> 200 mm`: tinggi;
- `100-200 mm`: sedang;
- `< 100 mm`: rendah.

If `tp` coverage is incomplete, the estimate and category are `null`; automatic
recommendation returns HTTP 422 instead of treating missing rainfall as zero.
The manual recommendation endpoint remains available.

## Validation Boundary

Automated tests execute all 30 rows, invalid/missing input, deterministic output,
default lookup, land adjustment, and four-class output constraints. The empty
expert-validation sheet is in `docs/research_instruments/`; no expert approval
has been fabricated.
