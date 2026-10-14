# Kaggle LoRA Evidence - Run 20260820T143551Z

## Validated Result

- Pipeline status: `success`
- Artifact ZIP SHA-256: `54ee68fccbb88be07a089365c2e62f9e6004e2774992973debe665d5dc0eb26a`
- Dataset SHA-256: `e232f79d2f8ae20b4fb765efb38435ce05e929406e88faba6b02aaaafd1ad42d`
- GPU: `2 x Tesla T4`
- Smoke: `pass`, 100 steps, 4 min 10.79 sec
- Main: `success`, 1600 steps, 55 min 46.29 sec
- LoRA: `multisource_multicrop_lora.safetensors`, 6414992 bytes, 256 tensors
- LoRA SHA-256: `0bda8908d577513110c22cf5ec1b8a7e008d2b26dd90525732a5c4e4b1bdd43a`
- Sanity images: 4/4 valid
- Evaluation: 36 conditions, 72 images valid
- Human evaluation: pending; all 72 assessment rows remain blank

## Loss Evidence

| Run | Observations | First | Last | Mean | Median | First 100 mean | Last 100 mean |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Smoke | 501 | 0.782000 | 0.288000 | 0.196618 | 0.129000 | 0.198757 | 0.191906 |
| Main | 8001 | 0.782000 | 0.004310 | 0.186001 | 0.113000 | 0.198757 | 0.180415 |

The loss series is noisy training evidence and is not a perceptual-quality score.

## Automated Proxy Metrics

| Variant | Images | Brightness mean | Contrast mean | Entropy mean |
| --- | ---: | ---: | ---: | ---: |
| base | 36 | 90.883615 | 60.444080 | 9.008533 |
| lora | 36 | 97.651167 | 62.275424 | 9.104648 |

Brightness, contrast, and entropy are descriptive proxies only. They do not prove crop
identity, realism, agronomic correctness, or superiority over the base model.

## Human Review Files

- `contact_sheets/`: four paired base-versus-LoRA sheets.
- `human_evaluation_template_local.csv`: 72 blank rows with local image paths.
- `generated/evaluation/`: 36 base and 36 LoRA PNG files.
- `proxy_metrics_summary.csv`: grouped descriptive proxy statistics.

Do not fill blank human fields automatically. A real reviewer must inspect each pair.
