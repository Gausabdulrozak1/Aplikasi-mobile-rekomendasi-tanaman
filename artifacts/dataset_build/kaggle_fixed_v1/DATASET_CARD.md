# TaniAdaptif Multicrop LoRA Dataset - Kaggle Fixed v1

This package contains the final manually reviewed TaniAdaptif research dataset:
312 training images and 77 validation images across padi, jagung, cabai, and
kacang tanah. Image bytes, captions, class labels, triggers, split assignments,
human decisions, and provenance values are unchanged.

The training metadata renames `original_file_name` to `source_original_name`.
Hugging Face folder builders reserve both `file_name` and `*_file_name` columns
as physical media references. Keeping the old column name caused ImageFolder to
attempt to open provenance names such as `003_lahan_cabai.jpg`. The exact
original metadata is retained under `manifests/original_metadata_*.jsonl`.

Stable Diffusion is used only to generate recommendation visualizations. The
TaniAdaptif rule-based engine remains authoritative for crop recommendations.
