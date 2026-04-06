from __future__ import annotations

import importlib.util
import re
from pathlib import Path
from types import ModuleType

import nbformat

from interactive_seminar.schemas import Block, Part, SeminarManifest


EXERCISE_HEADING_RE = re.compile(r"^###\s+(Exercise.+)$", re.MULTILINE)
EXAMPLE_HEADING_RE = re.compile(r"^###\s+(Example.+)$", re.MULTILINE)
PART_HEADING_RE = re.compile(r"^##\s+(Part\s+\d+)\s*$", re.MULTILINE)
HINT_IMPORT_RE = re.compile(r"from\s+hints\s+import\s+([A-Za-z0-9_, ]+)")


def load_manifest(notebook_path: str, hints_path: str) -> SeminarManifest:
    notebook_file = _resolve_path(notebook_path)
    hints_file = _resolve_path(hints_path)
    notebook = nbformat.read(notebook_file, as_version=4)
    hints_module = _load_hints_module(hints_file)

    manifest = SeminarManifest(
        title=_extract_notebook_title(notebook.cells),
        notebook_path=str(notebook_file),
        hints_path=str(hints_file),
    )

    current_part: Part | None = None
    index = 0
    while index < len(notebook.cells):
        cell = notebook.cells[index]
        source = cell.source.strip()

        if cell.cell_type == "markdown":
            part_title = _match_first_line(PART_HEADING_RE, source)
            if part_title:
                current_part = Part(id=_slugify(part_title), title=part_title)
                manifest.parts.append(current_part)
                index += 1
                continue

            block_title = _match_first_line(EXERCISE_HEADING_RE, source) or _match_first_line(EXAMPLE_HEADING_RE, source)
            if current_part and block_title:
                next_index = _find_next_block_boundary(notebook.cells, index + 1)
                section_indexes = list(range(index, next_index))
                section_cells = [(i, notebook.cells[i]) for i in section_indexes]
                block = _build_block(block_title, section_cells, hints_module, notebook_file)
                current_part.blocks.append(block)
                index = next_index
                continue

        index += 1

    return manifest


def _build_block(
    title: str,
    section_cells: list[tuple[int, object]],
    hints_module: ModuleType,
    notebook_file: Path,
) -> Block:
    instructions = []
    notebook_cell_indexes = []
    hint_text = None
    solution_text = None

    for cell_index, cell in section_cells:
        if cell.cell_type == "markdown":
            if not cell.source.strip().startswith("❓"):
                instructions.append(cell.source.strip())
            continue

        imported_names = _imported_hint_names(cell.source)
        if imported_names:
            for name in imported_names:
                value = getattr(hints_module, name, None)
                if value is None:
                    continue
                if name.endswith("_hint"):
                    hint_text = value
                elif name.endswith("_solution"):
                    solution_text = value
            continue

        notebook_cell_indexes.append(cell_index)

    kind = "example"
    if title.startswith("Exercise"):
        kind = "exercise_graded" if any(
            "def grade_exercise" in cell.source
            for _, cell in section_cells
            if cell.cell_type == "code"
        ) else "exercise_open"

    return Block(
        id=_slugify(title),
        title=title,
        kind=kind,
        notebook_path=str(notebook_file),
        notebook_cell_indexes=notebook_cell_indexes,
        instructions_markdown="\n\n".join(part for part in instructions if part),
        hint=hint_text,
        solution=solution_text,
    )


def _extract_notebook_title(cells: list[object]) -> str:
    for cell in cells:
        if cell.cell_type == "markdown":
            for line in cell.source.splitlines():
                line = line.strip()
                if line.startswith("# "):
                    return line[2:].strip()
    return "Interactive Prompt Engineering Seminar"


def _find_next_block_boundary(cells: list[object], start_index: int) -> int:
    index = start_index
    while index < len(cells):
        cell = cells[index]
        if cell.cell_type == "markdown":
            stripped = cell.source.strip()
            if stripped.startswith("### ") or PART_HEADING_RE.search(stripped):
                return index
        index += 1
    return len(cells)


def _resolve_path(path_str: str) -> Path:
    path = Path(path_str)
    if path.is_absolute():
        return path
    return (Path.cwd() / path).resolve()


def _load_hints_module(hints_path: Path) -> ModuleType:
    spec = importlib.util.spec_from_file_location("interactive_seminar_hints", hints_path)
    if spec is None or spec.loader is None:
        raise ImportError(f"Unable to load hints module from {hints_path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _imported_hint_names(source: str) -> list[str]:
    match = HINT_IMPORT_RE.search(source)
    if not match:
        return []
    return [name.strip() for name in match.group(1).split(",")]


def _match_first_line(pattern: re.Pattern[str], source: str) -> str | None:
    match = pattern.search(source)
    if not match:
        return None
    return match.group(1).strip()


def _slugify(text: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
    return slug
