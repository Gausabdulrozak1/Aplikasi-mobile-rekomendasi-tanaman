import ast
import base64
import hashlib
import io
import json
import zipfile
from pathlib import Path

import nbformat

ROOT = Path(__file__).resolve().parents[2]
NOTEBOOK_PATH = ROOT / "ml_pipeline/notebooks/09_kaggle_live_inference_sidang.ipynb"
KERNEL_METADATA_PATH = ROOT / "artifacts/kaggle_sidang_kernel/kernel-metadata.json"


def _load_notebook() -> nbformat.NotebookNode:
    notebook = nbformat.read(NOTEBOOK_PATH, as_version=4)
    nbformat.validate(notebook)
    return notebook


def _code_source() -> str:
    return "\n".join(
        cell.source for cell in _load_notebook().cells if cell.cell_type == "code"
    )


def test_live_notebook_uses_private_secret_fallback_after_user_secret() -> None:
    source = _code_source()
    metadata = json.loads(KERNEL_METADATA_PATH.read_text(encoding="utf-8"))

    assert metadata["is_private"] == "true"
    assert metadata["dataset_sources"] == [
        "gausabdul/taniadaptif-final-lora-sidang",
        "gausabdul/taniadaptif-sidang-secret-private",
    ]
    assert source.index('secrets.get_secret("INFERENCE_API_TOKEN")') < source.index(
        "SECRET_FALLBACK_PATH.read_text"
    )
    assert "TOKEN LENGTH=64" in source
    assert "print(INFERENCE_API_TOKEN" not in source


def test_live_notebook_retries_transient_public_readiness_failures() -> None:
    source = _code_source()

    assert "deadline = time.time() + 120" in source
    assert "except (urllib.error.URLError, TimeoutError, OSError) as exc:" in source
    assert "readiness publik bukan ready setelah retry" in source
    assert "if exc.code in {401, 403}:" in source


def test_live_notebook_registers_and_probes_png_save_handler() -> None:
    dependency_cell = _load_notebook().cells[2].source

    assert "Image.init()" in dependency_cell
    assert 'if "PNG" not in Image.SAVE:' in dependency_cell
    assert 'pillow_probe.save(pillow_buffer, format="PNG")' in dependency_cell
    assert "PIL PNG SAVE: PASS" in dependency_cell


def test_live_notebook_recovers_from_a_stale_fastapi_port() -> None:
    notebook = _load_notebook()
    server_cell = notebook.cells[7].source
    sanity_cell = notebook.cells[9].source
    state_cell = notebook.cells[10].source
    keep_alive_cell = notebook.cells[11].source

    assert "range(5000, 5011)" in server_cell
    assert "port_is_available" in server_cell
    assert "previous_server.should_exit = True" in server_cell
    assert 'f"{LOCAL_URL}/v1/generate"' in sanity_cell
    assert 'f"{KAGGLE_GPU_URL}/v1/generate"' not in sanity_cell
    assert 'f"{LOCAL_URL}/v1/model-info"' in state_cell
    assert "UVICORN_THREAD.is_alive()" not in keep_alive_cell


def test_live_notebook_code_cells_compile() -> None:
    for cell in _load_notebook().cells:
        if cell.cell_type == "code":
            ast.parse(cell.source)


def test_live_notebook_embeds_current_inference_source() -> None:
    archive_cell = next(
        cell for cell in _load_notebook().cells if "RUNTIME_ARCHIVE_B64" in cell.source
    )
    tree = ast.parse(archive_cell.source)
    values = {
        node.targets[0].id: ast.literal_eval(node.value)
        for node in tree.body
        if isinstance(node, ast.Assign)
        and isinstance(node.targets[0], ast.Name)
        and node.targets[0].id.startswith("RUNTIME_ARCHIVE_")
    }
    payload = base64.b64decode(values["RUNTIME_ARCHIVE_B64"], validate=True)
    manifest_json = next(
        ast.literal_eval(node.value)
        for node in tree.body
        if isinstance(node, ast.Assign)
        and isinstance(node.targets[0], ast.Name)
        and node.targets[0].id == "RUNTIME_SOURCE_MANIFEST"
        and isinstance(node.value, ast.Constant)
    )
    manifest = json.loads(manifest_json)

    assert hashlib.sha256(payload).hexdigest() == values["RUNTIME_ARCHIVE_SHA256"]
    with zipfile.ZipFile(io.BytesIO(payload)) as archive:
        assert len(archive.namelist()) == 17
        assert set(archive.namelist()) == set(manifest)
        for name in archive.namelist():
            archive_bytes = archive.read(name)
            assert archive_bytes == (ROOT / name).read_bytes()
            assert hashlib.sha256(archive_bytes).hexdigest() == manifest[name]
