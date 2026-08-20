"""Render the canonical Kaggle percent source into notebook and cell documents."""

from __future__ import annotations

import argparse
import json
import re
from dataclasses import dataclass
from pathlib import Path

import nbformat

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_SOURCE = REPOSITORY_ROOT / "ml_pipeline/notebooks/00_train_lora_multicrop_kaggle_final.py"
DEFAULT_NOTEBOOK = DEFAULT_SOURCE.with_suffix(".ipynb")
DEFAULT_CELL_MAP = REPOSITORY_ROOT / "docs/KAGGLE_NOTEBOOK_CELL_BY_CELL.md"
DEFAULT_COPY_PASTE = REPOSITORY_ROOT / "docs/KAGGLE_CELLS_COPY_PASTE.txt"
MARKER_PATTERN = re.compile(r"^# %%(?P<markdown> \[markdown\])? (?P<metadata>\{.*\})$")
REQUIRED_METADATA = (
    "cell_number",
    "title",
    "purpose",
    "inputs",
    "expected_output",
    "stop_condition",
)


@dataclass(frozen=True)
class SourceCell:
    """One parsed cell plus its user-facing contract metadata."""

    cell_type: str
    metadata: dict[str, object]
    source: str


def markdown_from_percent(source: str) -> str:
    """Convert comment-prefixed percent source back to Markdown."""

    output = []
    for line in source.splitlines():
        if line == "#":
            output.append("")
        elif line.startswith("# "):
            output.append(line[2:])
        else:
            raise ValueError(f"Markdown source line is not comment-prefixed: {line!r}")
    return "\n".join(output).rstrip() + "\n"


def parse_percent_source(path: Path) -> list[SourceCell]:
    """Parse strict percent markers and reject incomplete cell contracts."""

    cells: list[SourceCell] = []
    current_type: str | None = None
    current_metadata: dict[str, object] | None = None
    current_lines: list[str] = []

    def finish_current() -> None:
        if current_type is None or current_metadata is None:
            return
        raw_source = "\n".join(current_lines).rstrip() + "\n"
        source = markdown_from_percent(raw_source) if current_type == "markdown" else raw_source
        cells.append(SourceCell(current_type, current_metadata, source))

    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        marker = MARKER_PATTERN.fullmatch(line)
        if marker:
            finish_current()
            try:
                metadata = json.loads(marker.group("metadata"))
            except json.JSONDecodeError as exc:
                raise ValueError(f"Invalid marker JSON at {path}:{line_number}: {exc}") from exc
            missing = [key for key in REQUIRED_METADATA if key not in metadata]
            if missing:
                raise ValueError(f"Cell marker at {path}:{line_number} misses {missing}")
            current_type = "markdown" if marker.group("markdown") else "code"
            current_metadata = metadata
            current_lines = []
        else:
            if current_type is None:
                raise ValueError(f"Content before first cell marker at {path}:{line_number}")
            current_lines.append(line)
    finish_current()
    validate_cells(cells)
    return cells


def validate_cells(cells: list[SourceCell]) -> None:
    """Enforce the fixed 00-51 topology and statically compile every code cell."""

    if len(cells) != 52:
        raise ValueError(f"Expected 52 cells, found {len(cells)}")
    numbers = [cell.metadata["cell_number"] for cell in cells]
    if numbers != list(range(52)):
        raise ValueError(f"Cell numbers must be contiguous 0-51, found {numbers}")
    if cells[0].cell_type != "markdown":
        raise ValueError("Cell 00 must be Markdown")
    non_code = [index for index, cell in enumerate(cells[1:], 1) if cell.cell_type != "code"]
    if non_code:
        raise ValueError(f"Cells 01-51 must be code; invalid cells: {non_code}")
    for cell in cells:
        if not cell.source.strip():
            raise ValueError(f"Cell {cell.metadata['cell_number']:02d} is empty")
        if cell.cell_type == "code":
            compile(
                cell.source,
                f"00_train_lora_multicrop_kaggle_final.ipynb:cell-{cell.metadata['cell_number']:02d}",
                "exec",
            )


def render_notebook(cells: list[SourceCell], output_path: Path) -> None:
    """Write a clean nbformat 4 notebook without stale execution state."""

    notebook_cells = []
    for cell in cells:
        metadata = dict(cell.metadata)
        if cell.cell_type == "markdown":
            notebook_cells.append(nbformat.v4.new_markdown_cell(cell.source, metadata=metadata))
        else:
            notebook_cells.append(nbformat.v4.new_code_cell(cell.source, metadata=metadata))
    notebook = nbformat.v4.new_notebook(
        cells=notebook_cells,
        metadata={
            "kernelspec": {
                "display_name": "Python 3",
                "language": "python",
                "name": "python3",
            },
            "language_info": {"name": "python", "version": "3"},
            "taniadaptif": {
                "authoritative_source": str(DEFAULT_SOURCE.relative_to(REPOSITORY_ROOT)).replace(
                    "\\", "/"
                ),
                "target_runtime": "Kaggle GPU",
                "cell_count": 52,
            },
        },
    )
    nbformat.validate(notebook)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    nbformat.write(notebook, output_path)
    parsed = nbformat.read(output_path, as_version=4)
    nbformat.validate(parsed)


def fenced_source(cell: SourceCell) -> str:
    language = "markdown" if cell.cell_type == "markdown" else "python"
    return f"```{language}\n{cell.source.rstrip()}\n```"


def render_cell_map(cells: list[SourceCell], output_path: Path) -> None:
    """Write the complete cell contract and source for review or manual recovery."""

    sections = [
        "# Kaggle Notebook Cell by Cell",
        "",
        "Dokumen ini dihasilkan dari source yang sama dengan notebook final. Setiap cell",
        "memuat kontrak eksekusi dan source lengkap, tanpa state hasil training.",
        "",
    ]
    for cell in cells:
        metadata = cell.metadata
        sections.extend(
            [
                f"## Cell {metadata['cell_number']:02d} - {metadata['title']}",
                "",
                f"- Type: {cell.cell_type.title()}",
                f"- Tujuan: {metadata['purpose']}",
                f"- Input: {metadata['inputs']}",
                f"- Expected output: {metadata['expected_output']}",
                f"- Stop condition: {metadata['stop_condition']}",
                "",
                fenced_source(cell),
                "",
            ]
        )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text("\n".join(sections).rstrip() + "\n", encoding="utf-8")


def render_copy_paste(cells: list[SourceCell], output_path: Path) -> None:
    """Write plain cell separators and exact content for Kaggle copy-paste."""

    blocks = [
        "TANIADAPTIF KAGGLE NOTEBOOK - COMPLETE COPY-PASTE CELLS",
        "Generated from the same authoritative source as the final IPYNB.",
        "",
    ]
    for cell in cells:
        blocks.extend(
            [
                "=" * 66,
                f"CELL {cell.metadata['cell_number']:02d} - {cell.cell_type.upper()}",
                "=" * 66,
                "",
                cell.source.rstrip(),
                "",
            ]
        )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text("\n".join(blocks).rstrip() + "\n", encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=DEFAULT_SOURCE)
    parser.add_argument("--notebook", type=Path, default=DEFAULT_NOTEBOOK)
    parser.add_argument("--cell-map", type=Path, default=DEFAULT_CELL_MAP)
    parser.add_argument("--copy-paste", type=Path, default=DEFAULT_COPY_PASTE)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    cells = parse_percent_source(args.source.resolve())
    render_notebook(cells, args.notebook.resolve())
    render_cell_map(cells, args.cell_map.resolve())
    render_copy_paste(cells, args.copy_paste.resolve())
    print(f"Rendered notebook: {args.notebook} ({len(cells)} cells)")
    print(f"Rendered cell map: {args.cell_map}")
    print(f"Rendered copy-paste cells: {args.copy_paste}")


if __name__ == "__main__":
    main()
