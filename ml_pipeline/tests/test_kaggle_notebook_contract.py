from __future__ import annotations

import ast
import csv
import hashlib
import json
import re
from pathlib import Path, PurePosixPath

import nbformat

ROOT = Path(__file__).resolve().parents[2]
NOTEBOOK_PATH = ROOT / "ml_pipeline/notebooks/00_train_lora_multicrop_kaggle_final.ipynb"
SOURCE_PATH = ROOT / "ml_pipeline/notebooks/00_train_lora_multicrop_kaggle_final.py"
CELL_MAP_PATH = ROOT / "docs/KAGGLE_NOTEBOOK_CELL_BY_CELL.md"
COPY_PASTE_PATH = ROOT / "docs/KAGGLE_CELLS_COPY_PASTE.txt"
FIXED_DATASET_SHA256 = "e232f79d2f8ae20b4fb765efb38435ce05e929406e88faba6b02aaaafd1ad42d"


def load_notebook():
    notebook = nbformat.read(NOTEBOOK_PATH, as_version=4)
    nbformat.validate(notebook)
    return notebook


def notebook_source(notebook) -> str:
    return "\n".join(cell.source for cell in notebook.cells)


def test_kaggle_notebook_has_exact_cell_contract() -> None:
    notebook = load_notebook()

    assert len(notebook.cells) == 52
    assert notebook.cells[0].cell_type == "markdown"
    assert all(cell.cell_type == "code" for cell in notebook.cells[1:])
    assert [cell.metadata["cell_number"] for cell in notebook.cells] == list(range(52))
    for cell in notebook.cells:
        assert cell.source.strip()
        assert cell.metadata["title"]
        assert cell.metadata["purpose"]
        assert cell.metadata["inputs"]
        assert cell.metadata["expected_output"]
        assert cell.metadata["stop_condition"]
        if cell.cell_type == "code":
            assert cell.execution_count is None
            assert cell.outputs == []


def test_all_kaggle_code_cells_compile_individually_and_together() -> None:
    notebook = load_notebook()
    code_cells = [cell.source for cell in notebook.cells if cell.cell_type == "code"]

    for index, source in enumerate(code_cells, 1):
        compile(source, f"kaggle-cell-{index:02d}", "exec")
    compile("\n\n".join(code_cells), str(NOTEBOOK_PATH), "exec")


def test_kaggle_notebook_uses_fixed_dataset_and_required_training_contract() -> None:
    source = notebook_source(load_notebook())
    required_fragments = (
        FIXED_DATASET_SHA256,
        "dataset_multicrop_v1_kaggle_fixed.zip",
        "kaggle_extracted_content",
        "manifests/kaggle_file_mapping.csv",
        "anchored_extracted_content",
        'Path("/kaggle/input")',
        'Path("/kaggle/working")',
        "stable-diffusion-v1-5/stable-diffusion-v1-5",
        "0f252be0ed42006c125ef4429156cb13ae6c1d60",
        '"smoke_steps": 100',
        '"main_steps": 1600',
        '"smoke_checkpointing_steps": 50',
        '"main_checkpointing_steps": 200',
        '"resolution": 512',
        '"rank": 8',
        '"gradient_accumulation_steps": 4',
        '"dataloader_num_workers": 0',
        '"mixed_precision": "fp16"',
        '"--cache_dir"',
        '"--use_8bit_adam"',
        'OPTIMIZER_ACTUAL = "adamw_8bit" if USE_8BIT_ADAM else "adamw_torch"',
        "materialize_checkpoint",
        "checkpoint_file_manifest",
        "copied_and_sha256_verified_from_kaggle_input",
        "pytorch_lora_weights.safetensors",
        "multisource_multicrop_lora.safetensors",
        "complete_pipeline_state.json",
        "FINAL STATUS: SUCCESS",
    )
    for fragment in required_fragments:
        assert fragment in source


def test_kaggle_notebook_excludes_colab_stale_paths_and_known_bad_names() -> None:
    source = notebook_source(load_notebook())
    forbidden_fragments = (
        "/content/drive",
        "drive.mount",
        "google.colab",
        "execute_notebook",
        "003_lahan_cabai.jpg",
        "IMG_20240923_181506.jpg",
        "D:\\TaniAdaptif",
        "RESUME_FROM_CHECKPOINT = None",
    )
    for fragment in forbidden_fragments:
        assert fragment not in source


def test_exact_diffusers_source_is_activated_in_current_notebook_kernel() -> None:
    notebook = load_notebook()
    acquire_cell = next(
        cell for cell in notebook.cells if cell.metadata["cell_number"] == 18
    )
    inference_cell = next(
        cell for cell in notebook.cells if cell.metadata["cell_number"] == 35
    )
    report_cell = next(
        cell for cell in notebook.cells if cell.metadata["cell_number"] == 47
    )

    required_fragments = (
        'DIFFUSERS_SRC = (DIFFUSERS_SOURCE / "src").resolve()',
        "sys.path.insert(0, diffusers_src_text)",
        "importlib.invalidate_caches()",
        'importlib.import_module("diffusers")',
        "CURRENT_KERNEL_DIFFUSERS_PATH",
        "CURRENT_KERNEL_DIFFUSERS_VERSION",
        "CURRENT_KERNEL_DIFFUSERS_DISTRIBUTION_VERSION",
        "DIFFUSERS_RUNTIME_REPORT",
        'LOGS_ROOT / "diffusers_runtime_report.json"',
        'getattr(\n    CURRENT_KERNEL_DIFFUSERS, "StableDiffusionPipeline", None\n)',
        "current kernel loaded Diffusers outside exact checkout",
    )
    for fragment in required_fragments:
        assert fragment in acquire_cell.source
    assert "from diffusers import StableDiffusionPipeline" in inference_cell.source
    assert '"diffusers_runtime": DIFFUSERS_RUNTIME_REPORT' in report_cell.source


def execute_dataset_identity_cells(input_root: Path) -> tuple[dict[str, object], list[dict]]:
    notebook = load_notebook()
    config_cell = next(cell for cell in notebook.cells if cell.metadata["cell_number"] == 4)
    config_module = ast.parse(config_cell.source)
    config_assignment = next(
        node
        for node in config_module.body
        if isinstance(node, ast.Assign)
        and len(node.targets) == 1
        and isinstance(node.targets[0], ast.Name)
        and node.targets[0].id == "CONFIG"
    )
    dataset_config_node = next(
        value
        for key, value in zip(
            config_assignment.value.keys,
            config_assignment.value.values,
            strict=True,
        )
        if ast.literal_eval(key) == "dataset"
    )
    config = {"dataset": ast.literal_eval(dataset_config_node)}
    events = []
    namespace = {
        "CONFIG": config,
        "INPUT_ROOT": input_root,
        "Path": Path,
        "PurePosixPath": PurePosixPath,
        "csv": csv,
        "hashlib": hashlib,
        "json": json,
        "record_event": lambda stage, status, details: events.append(
            {"stage": stage, "status": status, "details": details}
        ),
    }
    discovery_cell = next(cell for cell in notebook.cells if cell.metadata["cell_number"] == 5)
    identity_cell = next(cell for cell in notebook.cells if cell.metadata["cell_number"] == 6)

    exec(compile(discovery_cell.source, "kaggle-cell-05", "exec"), namespace)
    exec(compile(identity_cell.source, "kaggle-cell-06", "exec"), namespace)
    return namespace, events


def test_extracted_kaggle_input_is_discovered_and_fully_hash_validated() -> None:
    namespace, events = execute_dataset_identity_cells(ROOT / "artifacts/dataset_build")

    assert namespace["DATASET_ZIP"] is None
    assert namespace["DATASET_DISCOVERY_MODE"] == "kaggle_extracted_content"
    assert namespace["DATASET_IDENTITY_REPORT"]["status"] == "pass"
    assert namespace["DATASET_IDENTITY_REPORT"]["mode"] == "anchored_extracted_content"
    assert namespace["DATASET_IDENTITY_REPORT"]["mapping_rows"] == 389
    assert namespace["DATASET_IDENTITY_REPORT"]["image_hashes_validated"] == 389
    assert namespace["DATASET_IDENTITY_REPORT"]["mapping_split_counts"] == {
        "train": 312,
        "validation": 77,
    }
    assert events[-1]["stage"] == "dataset_identity"


def test_fixed_zip_input_still_uses_exact_package_sha256() -> None:
    namespace, events = execute_dataset_identity_cells(ROOT / "artifacts/dataset_packages")

    assert namespace["DATASET_ZIP"].name == "dataset_multicrop_v1_kaggle_fixed.zip"
    assert namespace["DATASET_DISCOVERY_MODE"] == "preferred"
    assert namespace["DATASET_IDENTITY_REPORT"] == {
        "status": "pass",
        "mode": "zip_sha256",
        "package_sha256": FIXED_DATASET_SHA256,
        "input_sha256": FIXED_DATASET_SHA256,
    }
    assert events[-1]["stage"] == "dataset_identity"


def test_kaggle_notebook_has_no_placeholder_source() -> None:
    source = notebook_source(load_notebook())
    assert "..." not in source
    assert "TODO" not in source
    assert "kode sama seperti di atas" not in source.casefold()
    assert re.search(r"\braise\s+NotImplementedError\b", source) is None


def test_cell_documents_cover_every_exact_cell_source() -> None:
    notebook = load_notebook()
    cell_map = CELL_MAP_PATH.read_text(encoding="utf-8")
    copy_paste = COPY_PASTE_PATH.read_text(encoding="utf-8")

    assert len(re.findall(r"^## Cell \d{2} - ", cell_map, flags=re.MULTILINE)) == 52
    assert (
        len(re.findall(r"^CELL \d{2} - (?:MARKDOWN|CODE)$", copy_paste, flags=re.MULTILINE)) == 52
    )
    for cell in notebook.cells:
        number = cell.metadata["cell_number"]
        assert f"## Cell {number:02d} - {cell.metadata['title']}" in cell_map
        assert f"CELL {number:02d} - {cell.cell_type.upper()}" in copy_paste
        assert cell.source.rstrip() in cell_map
        assert cell.source.rstrip() in copy_paste


def test_percent_source_and_rendered_notebook_are_synchronized() -> None:
    percent_source = SOURCE_PATH.read_text(encoding="utf-8")
    notebook = load_notebook()

    assert len(re.findall(r"^# %%", percent_source, flags=re.MULTILINE)) == 52
    assert notebook.metadata["taniadaptif"]["cell_count"] == 52
    assert notebook.metadata["taniadaptif"]["target_runtime"] == "Kaggle GPU"
