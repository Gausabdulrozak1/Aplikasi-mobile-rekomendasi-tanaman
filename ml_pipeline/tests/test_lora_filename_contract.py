from __future__ import annotations

import ast
import csv
import hashlib
import json
import math
import os
import re
import shutil
import tempfile
from pathlib import Path

import nbformat
import pytest
import yaml

ROOT = Path(__file__).resolve().parents[2]
NOTEBOOK_DIR = ROOT / "ml_pipeline" / "notebooks"
TRAINING_CONFIG_PATH = ROOT / "ml_pipeline" / "configs" / "training_public_multicrop.yaml"
VALID_LORA_BYTES = b"TANIADAPTIF_VALID_SAFETENSORS_FIXTURE" * 64
PLACEHOLDER_LORA_BYTES = b"TANIADAPTIF_PLACEHOLDER_SAFETENSORS_FIXTURE" * 64


class _FixtureTensor:
    def numel(self) -> int:
        return 1


class _FixtureSafeOpen:
    def __init__(self, path: Path | str, **_: object) -> None:
        self.path = Path(path)
        self.data = b""

    def __enter__(self) -> _FixtureSafeOpen:
        self.data = self.path.read_bytes()
        if self.data not in {VALID_LORA_BYTES, PLACEHOLDER_LORA_BYTES}:
            raise ValueError("invalid SafeTensors fixture")
        return self

    def __exit__(self, *_: object) -> None:
        return None

    def keys(self) -> list[str]:
        return [f"fixture.lora.weight.{index}" for index in range(8)]

    def get_tensor(self, _: str) -> _FixtureTensor:
        return _FixtureTensor()

    def metadata(self) -> dict[str, str]:
        if self.data == PLACEHOLDER_LORA_BYTES:
            return {"artifact": "placeholder"}
        return {"format": "pt"}


def _notebook_source(filename: str) -> str:
    notebook = nbformat.read(NOTEBOOK_DIR / filename, as_version=4)
    return "\n".join(
        cell.source for cell in notebook.cells if cell.cell_type == "code"
    )


def _load_notebook_artifact_contract() -> dict[str, object]:
    notebook = nbformat.read(
        NOTEBOOK_DIR / "02_train_public_multicrop_lora_sd15_colab.ipynb",
        as_version=4,
    )
    helper_cell = next(
        cell for cell in notebook.cells if cell.get("id") == "lora-artifact-contract"
    )
    namespace: dict[str, object] = {
        "Path": Path,
        "hashlib": hashlib,
        "json": json,
        "os": os,
        "safe_open": _FixtureSafeOpen,
        "shutil": shutil,
        "tempfile": tempfile,
    }
    exec(compile(helper_cell.source, "lora-artifact-contract", "exec"), namespace)
    return namespace


def _load_checkpoint_helpers() -> dict[str, object]:
    source = _notebook_source("02_train_public_multicrop_lora_sd15_colab.ipynb")
    module = ast.parse(source)
    helper_module = ast.Module(
        body=[
            node
            for node in module.body
            if isinstance(node, ast.FunctionDef)
            and node.name in {"checkpoint_is_valid", "newest_checkpoint"}
        ],
        type_ignores=[],
    )
    namespace: dict[str, object] = {"re": re}
    exec(compile(helper_module, "checkpoint-resume-contract", "exec"), namespace)
    return namespace


def _load_orchestrator_validators() -> dict[str, object]:
    notebook = nbformat.read(
        NOTEBOOK_DIR / "00_run_complete_lora_pipeline_colab.ipynb",
        as_version=4,
    )
    validator_cell = next(
        cell for cell in notebook.cells if cell.get("id") == "artifact-validators"
    )
    namespace: dict[str, object] = {
        "Path": Path,
        "csv": csv,
        "json": json,
        "math": math,
        "re": re,
        "safe_open": _FixtureSafeOpen,
        "EXPECTED_SHA256": "fixture-sha256",
        "utc_now": lambda: "2026-08-13T00:00:00+00:00",
    }
    exec(compile(validator_cell.source, "artifact-validators", "exec"), namespace)
    return namespace


def _load_orchestrator_execution_helpers() -> tuple[dict[str, object], list[object]]:
    notebook = nbformat.read(
        NOTEBOOK_DIR / "00_run_complete_lora_pipeline_colab.ipynb",
        as_version=4,
    )
    helper_cell = next(
        cell for cell in notebook.cells if cell.get("id") == "orchestration-helpers"
    )
    module = ast.parse(helper_cell.source)
    helper_module = ast.Module(
        body=[
            node
            for node in module.body
            if isinstance(node, ast.FunctionDef)
            and node.name in {"load_and_validate_notebook", "execute_notebook"}
        ],
        type_ignores=[],
    )
    recorded_stages: list[object] = []
    namespace: dict[str, object] = {
        "nbformat": nbformat,
        "os": os,
        "record_stage": lambda *args: recorded_stages.append(args),
    }
    exec(compile(helper_module, "orchestrator-execution-helpers", "exec"), namespace)
    return namespace, recorded_stages


def test_diffusers_default_is_copied_to_canonical_and_retained(tmp_path: Path) -> None:
    contract = _load_notebook_artifact_contract()
    normalize = contract["normalize_diffusers_lora"]
    default_name = contract["DIFFUSERS_DEFAULT_LORA_FILENAME"]
    canonical_name = "multisource_multicrop_smoke_lora.safetensors"
    default_path = tmp_path / str(default_name)
    canonical_path = tmp_path / canonical_name
    default_path.write_bytes(VALID_LORA_BYTES)

    result_path, report, action = normalize(tmp_path, canonical_name, require_source=True)

    assert result_path == canonical_path
    assert report["valid"] is True
    assert action == "normalized_diffusers_default"
    assert canonical_path.read_bytes() == VALID_LORA_BYTES
    assert default_path.read_bytes() == VALID_LORA_BYTES
    assert not list(tmp_path.glob("*.copying"))

    default_path.write_bytes(PLACEHOLDER_LORA_BYTES)
    result_path, report, action = normalize(tmp_path, canonical_name, require_source=True)
    assert result_path == canonical_path
    assert report["valid"] is True
    assert action == "existing_canonical"
    assert canonical_path.read_bytes() == VALID_LORA_BYTES


def test_placeholder_default_never_becomes_canonical(tmp_path: Path) -> None:
    contract = _load_notebook_artifact_contract()
    normalize = contract["normalize_diffusers_lora"]
    default_name = contract["DIFFUSERS_DEFAULT_LORA_FILENAME"]
    canonical_name = "multisource_multicrop_lora.safetensors"
    default_path = tmp_path / str(default_name)
    default_path.write_bytes(PLACEHOLDER_LORA_BYTES)

    with pytest.raises(RuntimeError, match="No valid LoRA artifact"):
        normalize(tmp_path, canonical_name, require_source=True)

    assert default_path.read_bytes() == PLACEHOLDER_LORA_BYTES
    assert not (tmp_path / canonical_name).exists()


def test_canonical_directory_is_rejected_without_touching_default(tmp_path: Path) -> None:
    contract = _load_notebook_artifact_contract()
    normalize = contract["normalize_diffusers_lora"]
    default_name = contract["DIFFUSERS_DEFAULT_LORA_FILENAME"]
    canonical_name = "multisource_multicrop_lora.safetensors"
    default_path = tmp_path / str(default_name)
    default_path.write_bytes(VALID_LORA_BYTES)
    (tmp_path / canonical_name).mkdir()

    with pytest.raises(RuntimeError, match="not a regular file"):
        normalize(tmp_path, canonical_name, require_source=True)

    assert default_path.read_bytes() == VALID_LORA_BYTES
    assert (tmp_path / canonical_name).is_dir()


def test_checkpoint_100_is_selected_when_final_lora_is_missing(tmp_path: Path) -> None:
    contract = _load_notebook_artifact_contract()
    normalize = contract["normalize_diffusers_lora"]
    _, report, action = normalize(
        tmp_path,
        "multisource_multicrop_smoke_lora.safetensors",
        require_source=False,
    )
    assert report["valid"] is False
    assert action == "missing"

    checkpoint = tmp_path / "checkpoint-100"
    checkpoint.mkdir()
    for filename in ("optimizer.bin", "scheduler.bin", "random_states_0.pkl"):
        (checkpoint / filename).write_bytes(b"checkpoint-state")
    helpers = _load_checkpoint_helpers()

    assert helpers["checkpoint_is_valid"](checkpoint) is True
    assert helpers["newest_checkpoint"](tmp_path) == checkpoint


def test_orchestrator_rejects_missing_lora_and_surfaces_training_error(
    tmp_path: Path,
) -> None:
    validators = _load_orchestrator_validators()
    log_path = tmp_path / "training.log"
    log_path.write_text("accelerate exited\nactual diffusers failure\n", encoding="utf-8")
    (tmp_path / "training_manifest.json").write_text(
        json.dumps(
            {
                "status": "failed",
                "target_steps": 100,
                "return_code": 1,
                "error": "actual diffusers failure",
                "training_log": str(log_path),
            }
        ),
        encoding="utf-8",
    )

    report = validators["inspect_training_run"](
        tmp_path,
        100,
        "multisource_multicrop_smoke_lora.safetensors",
    )

    assert report["valid"] is False
    assert report["lora_valid"] is False
    assert report["training_failure"]["return_code"] == 1
    assert report["training_failure"]["error"] == "actual diffusers failure"
    assert "actual diffusers failure" in report["training_failure"]["training_log_tail"]
    with pytest.raises(RuntimeError, match="actual diffusers failure"):
        validators["require_training_run"](
            tmp_path,
            100,
            "multisource_multicrop_smoke_lora.safetensors",
            "validation.json",
        )


def test_orchestrator_uses_temporary_environment_without_source_replacement(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    helpers, recorded_stages = _load_orchestrator_execution_helpers()
    observed_path = tmp_path / "observed.json"
    child_notebook_path = tmp_path / "child.ipynb"
    child_notebook = nbformat.v4.new_notebook(
        cells=[
            nbformat.v4.new_code_cell(
                "\n".join(
                    (
                        "import json, os",
                        "from pathlib import Path",
                        "Path(os.environ['CONTRACT_OUTPUT']).write_text(",
                        "    json.dumps({",
                        "        'mode': os.environ['TANIADAPTIF_RUN_MODE'],",
                        "        'resume': os.environ['TANIADAPTIF_RESUME_FROM_CHECKPOINT'],",
                        "    }),",
                        "    encoding='utf-8',",
                        ")",
                    )
                )
            )
        ]
    )
    nbformat.write(child_notebook, child_notebook_path)
    monkeypatch.setenv("TANIADAPTIF_RUN_MODE", "original")
    monkeypatch.delenv("TANIADAPTIF_RESUME_FROM_CHECKPOINT", raising=False)

    helpers["execute_notebook"](
        child_notebook_path,
        "fixture_stage",
        environment={
            "CONTRACT_OUTPUT": str(observed_path),
            "TANIADAPTIF_RUN_MODE": "smoke",
            "TANIADAPTIF_RESUME_FROM_CHECKPOINT": "latest",
        },
    )

    assert json.loads(observed_path.read_text(encoding="utf-8")) == {
        "mode": "smoke",
        "resume": "latest",
    }
    assert os.environ["TANIADAPTIF_RUN_MODE"] == "original"
    assert "TANIADAPTIF_RESUME_FROM_CHECKPOINT" not in os.environ
    assert "CONTRACT_OUTPUT" not in os.environ
    assert recorded_stages == [
        ("fixture_stage", "completed", {"notebook": str(child_notebook_path)})
    ]


def test_notebooks_use_config_as_canonical_filename_source() -> None:
    config = yaml.safe_load(TRAINING_CONFIG_PATH.read_text(encoding="utf-8"))
    smoke_filename = config["smoke_test"]["lora_filename"]
    main_filename = config["output"]["lora_filename"]
    assert smoke_filename == "multisource_multicrop_smoke_lora.safetensors"
    assert main_filename == "multisource_multicrop_lora.safetensors"
    assert smoke_filename != main_filename

    orchestrator_source = _notebook_source("00_run_complete_lora_pipeline_colab.ipynb")
    assert 'SMOKE_LORA = smoke_config["lora_filename"]' in orchestrator_source
    assert 'MAIN_LORA = main_config["lora_filename"]' in orchestrator_source
    assert f'SMOKE_LORA = "{smoke_filename}"' not in orchestrator_source
    assert f'MAIN_LORA = "{main_filename}"' not in orchestrator_source
    assert '"lora_valid": lora_validation["valid"]' in orchestrator_source
    assert '"training_failure": report["training_failure"]' in orchestrator_source
    assert "replacements" not in orchestrator_source
    assert '"TANIADAPTIF_RUN_MODE": "smoke"' in orchestrator_source
    assert '"TANIADAPTIF_RUN_MODE": "main"' in orchestrator_source
    assert '"TANIADAPTIF_RESUME_FROM_CHECKPOINT": "latest"' in orchestrator_source

    training_source = _notebook_source(
        "02_train_public_multicrop_lora_sd15_colab.ipynb"
    )
    assert training_source.count('"pytorch_lora_weights.safetensors"') == 1
    assert 'output_lora_filename = smoke_config["lora_filename"]' in training_source
    assert 'output_lora_filename = config["output"]["lora_filename"]' in training_source
    assert "normalize_diffusers_lora(" in training_source
    assert 'if RESUME_FROM_CHECKPOINT is None:\n    RESUME_FROM_CHECKPOINT = "latest"' in training_source
    assert "if SKIP_TRAINING:" in training_source
    assert "COLAB_TRAINING_REQUIREMENTS" in training_source
    assert '"peft>=0.17.0,<1"' in training_source
    assert '"transformers>=4.41.2,<5"' in training_source
    assert "dependency_probe_source" in training_source
    assert "examples/text_to_image/requirements.txt" not in training_source

    evaluation_source = _notebook_source(
        "03_evaluate_public_multicrop_lora_colab.ipynb"
    )
    assert (
        'canonical_lora_filename = training_config["output"]["lora_filename"]'
        in evaluation_source
    )
    assert "/ canonical_lora_filename" in evaluation_source
    assert "lora_path = require_valid_lora(lora_path)" in evaluation_source


def test_training_notebook_uses_supported_local_logging() -> None:
    training_source = _notebook_source(
        "02_train_public_multicrop_lora_sd15_colab.ipynb"
    )

    assert 'TRAINING_REPORT_TO = "tensorboard"' in training_source
    assert 'TRAINING_LOGGING_DIR = "tensorboard"' in training_source
    assert '"--report_to",\n    TRAINING_REPORT_TO,' in training_source
    assert '"--logging_dir",\n    TRAINING_LOGGING_DIR,' in training_source
    assert '"--report_to",\n    "none",' not in training_source


def test_training_notebook_removes_unused_incompatible_optional_packages() -> None:
    training_source = _notebook_source(
        "02_train_public_multicrop_lora_sd15_colab.ipynb"
    )

    assert 'UNUSED_CONFLICTING_PACKAGES = ("torchao", "wandb")' in training_source
    assert '"uninstall",\n        "--yes",' in training_source
    assert '*UNUSED_CONFLICTING_PACKAGES' in training_source
    assert 'for unused_package in ("torchao", "wandb")' in training_source
    assert "importlib.util.find_spec(unused_package)" in training_source
    assert "inject_adapter_in_model(" in training_source
    assert 'resolved["peft_adapter_probe"] = "passed"' in training_source
    assert 'resolved["torchao"] = "not installed"' in training_source
    assert 'resolved["wandb"] = "not installed"' in training_source
    assert 'str(training_script), "--help"' in training_source
    assert 'print("Training entrypoint import probe: passed")' in training_source
