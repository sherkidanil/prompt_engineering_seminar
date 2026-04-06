from __future__ import annotations

import ast
import io
import json
import re
from contextlib import redirect_stdout
from pathlib import Path

import nbformat

from interactive_seminar.schemas import Block, ExecutionResult, GradeResult


def sanitize_cell_source(source: str) -> str:
    kept_lines = []
    for line in source.splitlines(keepends=True):
        stripped = line.lstrip()
        if stripped.startswith("%") or stripped.startswith("!"):
            continue
        kept_lines.append(line)
    return "".join(kept_lines)


def apply_assignment_overrides(source: str, overrides: dict[str, object]) -> str:
    if not overrides:
        return source
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return source

    lines = source.splitlines(keepends=True)
    replacements: list[tuple[int, int, str]] = []
    for node in tree.body:
        if not isinstance(node, ast.Assign):
            continue
        if len(node.targets) != 1 or not isinstance(node.targets[0], ast.Name):
            continue
        name = node.targets[0].id
        if name not in overrides:
            continue
        start = _line_col_to_offset(lines, node.lineno, node.col_offset)
        end = _line_col_to_offset(lines, node.end_lineno, node.end_col_offset)
        replacement = f"{name} = {_render_assignment_value(overrides[name])}"
        replacements.append((start, end, replacement))

    updated = source
    for start, end, replacement in sorted(replacements, reverse=True):
        updated = updated[:start] + replacement + updated[end:]
    return updated


def execute_block(
    block: Block,
    overrides: dict[str, object],
    runner,
    *,
    credentials: str,
    model: str,
) -> ExecutionResult:
    notebook_path = Path(block.notebook_path)
    if not notebook_path.exists():
        raise FileNotFoundError(f"Notebook file not found: {notebook_path}")

    notebook = nbformat.read(notebook_path, as_version=4)
    namespace = {
        "__name__": "__interactive_seminar__",
        "re": re,
    }

    def get_completion(prompt_or_messages, system_prompt: str = "", prefill: str = "", stop_sequences=None):
        return runner.run(
            credentials=credentials,
            model=model,
            prompt_or_messages=prompt_or_messages,
            system_prompt=system_prompt,
            prefill=prefill,
            stop_sequences=stop_sequences,
        )

    namespace["get_completion"] = get_completion
    stdout_buffer = io.StringIO()

    with redirect_stdout(stdout_buffer):
        for cell_index in block.notebook_cell_indexes:
            cell = notebook.cells[cell_index]
            source = sanitize_cell_source(cell.source)
            source = apply_assignment_overrides(source, overrides)
            if not source.strip():
                continue
            exec(compile(source, f"{notebook_path.name}:{cell_index}", "exec"), namespace)

    response = namespace.get("response", "")
    grade_result = None
    grader = namespace.get("grade_exercise")
    if callable(grader) and response != "":
        grade_result = GradeResult(passed=bool(grader(response)))

    return ExecutionResult(
        prompt_preview=_as_text(namespace.get("PROMPT")),
        system_prompt=_as_text(namespace.get("SYSTEM_PROMPT")),
        prefill=_as_text(namespace.get("PREFILL")),
        response=_as_text(response) or "",
        stdout=stdout_buffer.getvalue(),
        grade=grade_result,
    )


def _line_col_to_offset(lines: list[str], lineno: int, col_offset: int) -> int:
    return sum(len(line) for line in lines[: lineno - 1]) + col_offset


def _render_assignment_value(value: object) -> str:
    if isinstance(value, str):
        return json.dumps(value, ensure_ascii=False)
    return repr(value)


def _as_text(value: object) -> str | None:
    if value is None:
        return None
    return str(value)
