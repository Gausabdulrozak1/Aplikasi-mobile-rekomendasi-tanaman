from __future__ import annotations

from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]


def _load(relative_path: str) -> dict:
    return yaml.safe_load((ROOT / relative_path).read_text(encoding="utf-8"))


def test_public_padi_pilot_uses_the_requested_single_class_identity() -> None:
    config = _load("ml_pipeline/configs/pilot_padi.yaml")

    assert config["base_model"] == "stable-diffusion-v1-5/stable-diffusion-v1-5"
    assert config["dataset"]["selected_classes"] == ["padi"]
    assert config["dataset"]["minimum_width"] == 512
    assert config["dataset"]["minimum_height"] == 512
    assert config["caption"]["trigger_token"] == "gaus_padi_public"
    assert all("gaus_padi_public" in prompt for prompt in config["validation"]["prompts"])
    expected_training = {
        "resolution": 512,
        "seed": 42,
        "rank": 8,
        "batch_size": 1,
        "gradient_accumulation_steps": 4,
        "dataloader_num_workers": 0,
        "max_train_steps": 800,
        "checkpointing_steps": 200,
    }
    for key, value in expected_training.items():
        assert config["training"][key] == value


def test_pilot_identity_does_not_replace_final_multicrop_triggers() -> None:
    pilot = _load("ml_pipeline/configs/pilot_padi.yaml")
    final = _load("ml_pipeline/configs/dataset_public_multicrop.yaml")

    final_triggers = {item["trigger_token"] for item in final["classes"]}
    assert pilot["caption"]["trigger_token"] not in final_triggers
    assert final_triggers == {
        "taniadaptif_padi",
        "taniadaptif_jagung",
        "taniadaptif_cabai",
        "taniadaptif_kacang_tanah",
    }
