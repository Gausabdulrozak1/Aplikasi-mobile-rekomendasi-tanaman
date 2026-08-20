from __future__ import annotations

import ast
import base64
import gzip
import hashlib
import json
import os
import shutil
from pathlib import Path

import nbformat
import pytest
import yaml

ROOT = Path(__file__).resolve().parents[2]
NOTEBOOK_DIR = ROOT / "ml_pipeline" / "notebooks"
CONFIG_DIR = ROOT / "ml_pipeline" / "configs"
EXPECTED_SHA256 = "f6aa060658cf95e48996f10f0ffde200938d340dd15e6b60adace5bb5cecfb33"
RUNTIME_PACKAGE = "/content/dataset_multicrop_v1.zip"
RUNTIME_DATASET = "/content/taniadaptif_dataset/multicrop_v1"
STAGE_NOTEBOOKS = (
    "01_prepare_public_multicrop_dataset_colab.ipynb",
    "02_train_public_multicrop_lora_sd15_colab.ipynb",
    "03_evaluate_public_multicrop_lora_colab.ipynb",
)


def _notebook(filename: str) -> nbformat.NotebookNode:
    return nbformat.read(NOTEBOOK_DIR / filename, as_version=4)


def _code_source(filename: str) -> str:
    return "\n".join(cell.source for cell in _notebook(filename).cells if cell.cell_type == "code")


def _literal_assignment(source: str, name: str) -> object:
    module = ast.parse(source)
    for node in module.body:
        if (
            isinstance(node, ast.Assign)
            and len(node.targets) == 1
            and isinstance(node.targets[0], ast.Name)
            and node.targets[0].id == name
        ):
            return ast.literal_eval(node.value)
    raise AssertionError(f"Assignment not found: {name}")


def test_runtime_zip_is_the_only_dataset_package_input() -> None:
    orchestrator = _code_source("00_run_complete_lora_pipeline_colab.ipynb")
    preparation = _code_source("01_prepare_public_multicrop_dataset_colab.ipynb")
    training = _code_source("02_train_public_multicrop_lora_sd15_colab.ipynb")

    assert f'PACKAGE_PATH = Path("{RUNTIME_PACKAGE}")' in orchestrator
    assert 'PIPELINE_REVISION = "2026-08-14-imagefolder-probe-v8"' in orchestrator
    assert "def execute_notebook(path, stage, environment=None):" in orchestrator
    assert "def execute_notebook(path, stage, replacements" not in orchestrator
    assert f'PACKAGE_PATH = Path("{RUNTIME_PACKAGE}")' in preparation
    assert 'UPLOAD_PARTS_DIR = Path("/content/dataset_multicrop_v1_upload_parts")' in orchestrator
    assert "DRIVE_PACKAGE_PATH = Path(" in orchestrator
    assert '"/content/drive/MyDrive/skripsi_lora/datasets/dataset_multicrop_v1.zip"' in orchestrator
    assert 'return package_path, "google_drive"' in orchestrator
    assert 'UPLOAD_PARTS_DIR = Path("/content/dataset_multicrop_v1_upload_parts")' in preparation
    assert "assemble_runtime_package(" in orchestrator
    assert "assemble_runtime_package(" in preparation
    assert EXPECTED_SHA256 in orchestrator
    assert EXPECTED_SHA256 in preparation
    assert f'RUNTIME_DATASET_DIR = Path("{RUNTIME_DATASET}")' in preparation
    assert f'RUNTIME_DATASET_DIR = Path("{RUNTIME_DATASET}")' in training
    assert 'train_data_dir = RUNTIME_DATASET_DIR / "train"' in training

    combined = "\n".join((orchestrator, preparation, training))
    for forbidden in (
        'DRIVE_ROOT / "datasets"',
        'DRIVE_ROOT / "datasets/multicrop_v1/train"',
        "CHECKSUM_PATH",
        "DATASETS_DIR",
        'DRIVE_ROOT / "notebooks"',
    ):
        assert forbidden not in combined


def _load_upload_helpers(
    filename: str = "01_prepare_public_multicrop_dataset_colab.ipynb",
) -> dict[str, object]:
    helper_names = {"sha256_file", "assemble_runtime_package"}
    helpers = []
    for cell in _notebook(filename).cells:
        if cell.cell_type != "code":
            continue
        try:
            module = ast.parse(cell.source)
        except SyntaxError:
            continue
        helpers.extend(
            node
            for node in module.body
            if isinstance(node, ast.FunctionDef) and node.name in helper_names
        )
    found_names = {node.name for node in helpers}
    if found_names != helper_names:
        raise AssertionError(f"Upload helper definitions missing: {helper_names - found_names}")
    namespace: dict[str, object] = {
        "Path": Path,
        "hashlib": hashlib,
        "json": json,
        "os": os,
        "shutil": shutil,
    }
    exec(
        compile(ast.Module(body=helpers, type_ignores=[]), "runtime-package", "exec"),
        namespace,
    )
    return namespace


def test_missing_runtime_zip_stops_with_chunk_upload_instruction(tmp_path: Path) -> None:
    helpers = _load_upload_helpers()

    with pytest.raises(SystemExit, match=r"STOP: ZIP final belum tersedia.*Upload folder"):
        helpers["assemble_runtime_package"](
            tmp_path / "dataset_multicrop_v1.zip",
            tmp_path / "dataset_multicrop_v1_upload_parts",
            "fixture-sha256",
        )


def test_runtime_package_is_reassembled_and_hash_validated(tmp_path: Path) -> None:
    helpers = _load_upload_helpers()
    content = b"TaniAdaptif validated dataset fixture\n" * 100
    expected_sha256 = hashlib.sha256(content).hexdigest()
    package_path = tmp_path / "dataset_multicrop_v1.zip"
    parts_dir = tmp_path / "dataset_multicrop_v1_upload_parts"
    parts_dir.mkdir()
    part_records = []
    for index, offset in enumerate(range(0, len(content), 257)):
        part_content = content[offset : offset + 257]
        name = f"dataset_multicrop_v1.zip.part-{index:03d}"
        (parts_dir / name).write_bytes(part_content)
        part_records.append(
            {
                "name": name,
                "size_bytes": len(part_content),
                "sha256": hashlib.sha256(part_content).hexdigest(),
            }
        )
    (parts_dir / "upload_manifest.json").write_text(
        json.dumps(
            {
                "schema_version": 1,
                "source_filename": package_path.name,
                "source_size_bytes": len(content),
                "source_sha256": expected_sha256,
                "chunk_size_bytes": 257,
                "part_count": len(part_records),
                "parts": part_records,
            }
        ),
        encoding="utf-8",
    )

    result_path, mode = helpers["assemble_runtime_package"](
        package_path, parts_dir, expected_sha256
    )

    assert result_path == package_path
    assert mode == "assembled_parts"
    assert package_path.read_bytes() == content
    assert not (tmp_path / ".dataset_multicrop_v1.zip.assembling").exists()
    result_path, mode = helpers["assemble_runtime_package"](
        package_path, parts_dir, expected_sha256
    )
    assert result_path == package_path
    assert mode == "existing_zip"


def test_orchestrator_copies_valid_drive_package_atomically(tmp_path: Path) -> None:
    helpers = _load_upload_helpers("00_run_complete_lora_pipeline_colab.ipynb")
    content = b"TaniAdaptif persistent Drive package fixture\n" * 100
    expected_sha256 = hashlib.sha256(content).hexdigest()
    drive_package = tmp_path / "drive" / "dataset_multicrop_v1.zip"
    drive_package.parent.mkdir()
    drive_package.write_bytes(content)
    runtime_package = tmp_path / "runtime" / "dataset_multicrop_v1.zip"
    runtime_package.parent.mkdir()

    result_path, mode = helpers["assemble_runtime_package"](
        runtime_package,
        tmp_path / "missing-parts",
        expected_sha256,
        drive_package,
    )

    assert result_path == runtime_package
    assert mode == "google_drive"
    assert runtime_package.read_bytes() == content
    assert not (runtime_package.parent / ".dataset_multicrop_v1.zip.from-drive").exists()


def test_drive_paths_are_limited_to_persistent_outputs() -> None:
    training_config = yaml.safe_load(
        (CONFIG_DIR / "training_public_multicrop.yaml").read_text(encoding="utf-8")
    )
    evaluation_config = yaml.safe_load(
        (CONFIG_DIR / "evaluation_public_multicrop.yaml").read_text(encoding="utf-8")
    )

    drive_paths = (
        training_config["smoke_test"]["google_drive_directory"],
        training_config["output"]["google_drive_directory"],
        evaluation_config["output"]["google_drive_directory"],
    )
    allowed = (
        "/content/drive/MyDrive/skripsi_lora/outputs/",
        "/content/drive/MyDrive/skripsi_lora/evaluation/",
        "/content/drive/MyDrive/skripsi_lora/logs/",
    )
    assert all(any(path.startswith(prefix) for prefix in allowed) for path in drive_paths)

    preparation = _code_source("01_prepare_public_multicrop_dataset_colab.ipynb")
    assert '"outputs/smoke_test"' in preparation
    assert '"outputs/multicrop_v1"' in preparation
    assert '"evaluation"' in preparation
    assert '"logs"' in preparation
    assert '"datasets"' not in preparation
    assert '"notebooks"' not in preparation


def test_orchestrator_embeds_current_valid_stage_notebooks() -> None:
    notebook = _notebook("00_run_complete_lora_pipeline_colab.ipynb")
    cell = next(cell for cell in notebook.cells if cell.get("id") == "paths-and-package")
    payloads = _literal_assignment(cell.source, "EMBEDDED_NOTEBOOKS_GZIP_BASE64")
    checksums = _literal_assignment(cell.source, "EMBEDDED_NOTEBOOK_SHA256")

    assert set(payloads) == set(STAGE_NOTEBOOKS)
    assert set(checksums) == set(STAGE_NOTEBOOKS)
    for filename in STAGE_NOTEBOOKS:
        decoded = gzip.decompress(base64.b64decode(payloads[filename], validate=True))
        expected = (NOTEBOOK_DIR / filename).read_bytes()
        assert decoded == expected
        assert hashlib.sha256(decoded).hexdigest() == checksums[filename]
        embedded = nbformat.reads(decoded.decode("utf-8"), as_version=4)
        nbformat.validate(embedded)


def test_training_validates_runtime_dataset_and_evaluation_validates_canonical_lora() -> None:
    training = _code_source("02_train_public_multicrop_lora_sd15_colab.ipynb")
    evaluation = _code_source("03_evaluate_public_multicrop_lora_colab.ipynb")

    assert 'runtime_dataset_manifest.get("dataset_sha256")' in training
    assert 'runtime_dataset_manifest.get("train_rows") != 312' in training
    assert 'runtime_dataset_manifest.get("validation_rows") != 77' in training
    assert 'runtime_dataset_manifest.get("class_counts") != EXPECTED_CLASS_COUNTS' in training
    assert "def validate_runtime_split(split_root, expected_rows):" in training
    assert 'RUNTIME_DATASETS_CACHE_DIR = Path("/content/taniadaptif_hf_datasets_cache")' in training
    assert 'training_environment["HF_DATASETS_CACHE"] = str(' in training
    assert "shutil.rmtree(RUNTIME_DATASETS_CACHE_DIR)" in training
    assert "env=training_environment" in training
    assert 'load_dataset(\n    "imagefolder",' in training
    assert 'image = row["image"]' in training
    assert "ImageFolder decoder probe: passed" in training
    assert 'canonical_lora_filename = training_config["output"]["lora_filename"]' in evaluation
    assert "lora_path = require_valid_lora(lora_path)" in evaluation
    assert 'with safe_open(path, framework="pt", device="cpu")' in evaluation


def test_training_runtime_preflight_rejects_stale_image_references(tmp_path: Path) -> None:
    source = _code_source("02_train_public_multicrop_lora_sd15_colab.ipynb")
    module = ast.parse(source)
    helper = next(
        node
        for node in module.body
        if isinstance(node, ast.FunctionDef) and node.name == "validate_runtime_split"
    )
    namespace: dict[str, object] = {
        "Path": Path,
        "hashlib": hashlib,
        "json": json,
    }
    exec(
        compile(ast.Module(body=[helper], type_ignores=[]), "runtime-preflight", "exec"),
        namespace,
    )

    split_root = tmp_path / "train"
    image_path = split_root / "padi" / "padi_0001.jpg"
    image_path.parent.mkdir(parents=True)
    image_path.write_bytes(b"valid-image-fixture")
    metadata_path = split_root / "metadata.jsonl"
    valid_row = {"file_name": "padi/padi_0001.jpg", "class_id": "padi"}
    metadata_path.write_text(json.dumps(valid_row) + "\n", encoding="utf-8")

    rows, report = namespace["validate_runtime_split"](split_root, 1)
    assert rows == [valid_row]
    assert report["status"] == "valid"
    assert report["image_files"] == 1

    stale_row = {"file_name": "IMG_OLD_RUNTIME.jpg", "class_id": "padi"}
    metadata_path.write_text(json.dumps(stale_row) + "\n", encoding="utf-8")
    with pytest.raises(SystemExit, match="dataset runtime train tidak konsisten") as exc:
        namespace["validate_runtime_split"](split_root, 1)
    assert "gambar tidak ditemukan" in str(exc.value)
    assert "metadata menunjuk gambar yang tidak ada" in str(exc.value)


def test_success_claim_and_human_evaluation_boundaries_are_enforced() -> None:
    orchestrator = _code_source("00_run_complete_lora_pipeline_colab.ipynb")
    evaluation = _code_source("03_evaluate_public_multicrop_lora_colab.ipynb")
    final_markdown = _notebook("00_run_complete_lora_pipeline_colab.ipynb").cells[-1].source
    normalized_markdown = " ".join(final_markdown.split())

    success_record = 'record_stage("complete_pipeline", "success", pipeline_state["result"])'
    failed_record = 'record_stage(\n        "complete_pipeline",\n        "failed",'
    success_print = 'print("Complete pipeline succeeded.")'
    assert success_record in orchestrator
    assert "except BaseException as exc:" in orchestrator
    assert failed_record in orchestrator
    assert "    raise\n\n" in orchestrator
    assert orchestrator.index(success_record) < orchestrator.index(success_print)
    assert orchestrator.index("except BaseException as exc:") < orchestrator.index(success_print)

    assert "Metrik evaluasi otomatis adalah proxy" in normalized_markdown
    assert "template penilaian manusia tetap kosong sampai direview" in normalized_markdown
    assert "proxy otomatis CLIP/statistik gambar, bukan penilaian visual manusia" in evaluation
    assert "writer.writerow(record)" in evaluation
    assert "human evaluation template must contain 72 blank assessment rows" in orchestrator
    assert "class confusion review must contain 36 blank human-review rows" in orchestrator
