# Chapter III Implementation Notes

These notes describe implemented method details and are not a replacement for
the thesis document.

## Dataset Method

- Four classes: padi, jagung, cabai, and kacang tanah.
- Padi sources: 219 public and 30 local Aikmel raw images.
- Other classes: public only (80 jagung, 80 cabai, 90 kacang tanah).
- Immutable raw audit: format, decoding, dimensions, mode, EXIF, SHA-256,
  perceptual hash, cross-source/class duplicates, and provenance fields.
- Reproducible technical selection seed: 42; 350 candidates.
- Automated Pillow screening is a technical-semantic proxy only.
- Human review and verified provenance are hard gates before an 80/20 final split.

## Recommendation Method

BMKG supplies a short forecast horizon. The application preserves missing `tp`
as null, records coverage and cache freshness, and only projects a monthly
equivalent from complete horizon data. The category enters a deterministic
30-row decision table with land type, water availability, and previous crop.
Each result exposes a traceable rule ID and reason. Expert validation remains a
separate research activity.

## Visual Method

Stable Diffusion 1.5 plus LoRA is scoped to visual simulation. Trigger tokens are
`taniadaptif_padi`, `taniadaptif_jagung`, `taniadaptif_cabai`, and
`taniadaptif_kacang_tanah`; they are identifiers, not geographic claims. Planned
baseline training is resolution 512, batch 1, accumulation 4, rank 8, fp16,
gradient checkpointing, seed 42, and 1,600 steps on an authenticated GPU.

No training result is available yet. The FastAPI mock provider exists to test
system integration without making model-quality claims.

## Software Verification

Tests cover dataset gates, metadata policy, API validation, provider timeout and
failure, all decision rules, BMKG cache/missing rain, Flutter repository cache,
history, structured inference requests, and recommendation persistence on visual
failure. Debug APK metadata and signature are checked with Android build tools.
