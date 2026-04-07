from __future__ import annotations

import ast
import html
import importlib.util
import re
import warnings
from pathlib import Path
from types import ModuleType

import markdown
import nbformat

from interactive_seminar.schemas import Block, BlockField, Part, SeminarManifest


EXERCISE_HEADING_RE = re.compile(r"^###\s+(Exercise.+)$", re.MULTILINE)
EXAMPLE_HEADING_RE = re.compile(r"^###\s+(Example.+)$", re.MULTILINE)
PART_HEADING_RE = re.compile(r"^##\s+(Part\s+\d+)\s*$", re.MULTILINE)
HINT_IMPORT_RE = re.compile(r"from\s+hints\s+import\s+([A-Za-z0-9_, ]+)")
EDITABLE_FIELD_NAMES = {
    "PROMPT",
    "SYSTEM_PROMPT",
    "PREFILL",
    "TASK_CONTEXT",
    "TONE_CONTEXT",
    "INPUT_DATA",
    "EXAMPLES",
    "TASK_DESCRIPTION",
    "IMMEDIATE_TASK",
    "PRECOGNITION",
    "OUTPUT_FORMATTING",
}
SPECIAL_EDITABLE_FIELD_NAMES = {
    "system_prompt_tools_specific_tools_sql",
}
GENERIC_CONTEXT_FIELD_NAMES = {
    "first_user",
    "second_user",
    "first_response",
    "prefill",
}


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

            if current_part and current_part.title == "Part 11" and source.startswith("### Examples"):
                current_part.blocks.append(_build_tool_use_demo_block(notebook, notebook_file))
                index = 228
                continue

            if current_part and source.startswith("### Examples"):
                next_index = _find_next_block_boundary(notebook.cells, index + 1)
                section_indexes = list(range(index, next_index))
                section_cells = [(i, notebook.cells[i]) for i in section_indexes]
                current_part.blocks.extend(
                    _build_generic_example_blocks(
                        current_part.title,
                        section_cells,
                        notebook_file,
                    )
                )
                index = next_index
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
    kind_override: str | None = None,
) -> Block:
    instructions = []
    notebook_cell_indexes = []
    editable_fields: list[BlockField] = []
    readonly_fields: list[BlockField] = []
    hint_text = None
    solution_text = None
    seen_field_names: set[str] = set()

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
        for field in _extract_assignment_fields(cell.source):
            if field.name in seen_field_names:
                continue
            seen_field_names.add(field.name)
            if field.editable:
                editable_fields.append(field)
            else:
                readonly_fields.append(field)

    kind = kind_override or "example"
    if kind_override is None and title.startswith("Exercise"):
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
        instructions_html=_render_markdown("\n\n".join(part for part in instructions if part)),
        editable_fields=editable_fields,
        readonly_fields=readonly_fields,
        hint=hint_text,
        hint_html=_render_markdown(hint_text) if hint_text else None,
        solution=solution_text,
        solution_html=_render_markdown(solution_text) if solution_text else None,
    )


def _build_generic_example_blocks(
    part_title: str,
    section_cells: list[tuple[int, object]],
    notebook_file: Path,
) -> list[Block]:
    blocks: list[Block] = []
    pending_markdown: list[str] = []
    example_number = 1
    previous_was_code = False
    code_cells = [(cell_index, cell) for cell_index, cell in section_cells if cell.cell_type == "code"]
    runtime_indexes_by_cell = _resolve_generic_example_runtime_indexes(code_cells)

    for cell_index, cell in section_cells:
        if cell.cell_type == "markdown":
            markdown_text = cell.source.strip()
            if previous_was_code:
                pending_markdown = []
            pending_markdown.append(markdown_text)
            previous_was_code = False
            continue

        if cell.cell_type != "code":
            continue

        instructions_markdown = "\n\n".join(part for part in pending_markdown if part)
        title = _generic_example_title(part_title, example_number, pending_markdown)
        editable_fields: list[BlockField] = []
        readonly_fields: list[BlockField] = []
        seen_field_names: set[str] = set()
        runtime_indexes = runtime_indexes_by_cell.get(cell_index, [cell_index])
        runtime_cells = {runtime_cell_index: runtime_cell for runtime_cell_index, runtime_cell in code_cells}
        for runtime_cell_index in runtime_indexes:
            runtime_cell = runtime_cells[runtime_cell_index]
            for field in _extract_assignment_fields_with_context(
                runtime_cell.source,
                extra_editable_names=GENERIC_CONTEXT_FIELD_NAMES,
            ):
                if field.name in seen_field_names:
                    continue
                seen_field_names.add(field.name)
                if field.editable:
                    editable_fields.append(field)
                else:
                    readonly_fields.append(field)

        blocks.append(
            Block(
                id=_slugify(title),
                title=title,
                kind="example",
                notebook_path=str(notebook_file),
                notebook_cell_indexes=runtime_indexes,
                instructions_markdown=instructions_markdown,
                instructions_html=_render_markdown(instructions_markdown),
                editable_fields=editable_fields,
                readonly_fields=readonly_fields,
            )
        )
        example_number += 1
        previous_was_code = True

    return blocks


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
            if stripped.startswith("### ") or stripped.startswith("## ") or stripped.startswith("---"):
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


def _extract_assignment_fields(source: str) -> list[BlockField]:
    return _extract_assignment_fields_with_context(source, extra_editable_names=None)


def _extract_assignment_fields_with_context(
    source: str,
    extra_editable_names: set[str] | None,
) -> list[BlockField]:
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", SyntaxWarning)
            tree = ast.parse(source)
    except SyntaxError:
        return []

    fields: list[BlockField] = []
    for node in tree.body:
        if not isinstance(node, ast.Assign):
            continue
        if len(node.targets) != 1 or not isinstance(node.targets[0], ast.Name):
            continue
        name = node.targets[0].id
        if not _should_expose_assignment(name, node.value, extra_editable_names):
            continue
        value_source = ast.get_source_segment(source, node.value) or ""
        fields.append(
            BlockField(
                name=name,
                value=value_source.strip(),
                editable=(
                    name in EDITABLE_FIELD_NAMES
                    or name in SPECIAL_EDITABLE_FIELD_NAMES
                    or (extra_editable_names is not None and name in extra_editable_names)
                ),
            )
        )
    if fields:
        return fields
    return _extract_inline_chat_fields(source)


def _extract_inline_chat_fields(source: str) -> list[BlockField]:
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", SyntaxWarning)
            tree = ast.parse(source)
    except SyntaxError:
        return []

    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        if not isinstance(node.func, ast.Name) or node.func.id != "Chat":
            continue
        messages_keyword = next((keyword for keyword in node.keywords if keyword.arg == "messages"), None)
        if messages_keyword is None:
            continue
        messages_expr = messages_keyword.value
        messages_source = ast.get_source_segment(source, messages_expr) or ""
        if not isinstance(messages_expr, ast.List):
            continue

        user_message_contents: list[ast.expr] = []
        for message_expr in messages_expr.elts:
            if not isinstance(message_expr, ast.Call):
                continue
            if not isinstance(message_expr.func, ast.Name) or message_expr.func.id != "Messages":
                continue
            role_keyword = next((keyword for keyword in message_expr.keywords if keyword.arg == "role"), None)
            content_keyword = next((keyword for keyword in message_expr.keywords if keyword.arg == "content"), None)
            if role_keyword is None or content_keyword is None:
                continue
            if _is_user_role_expr(role_keyword.value):
                user_message_contents.append(content_keyword.value)

        if len(messages_expr.elts) == 1 and len(user_message_contents) == 1:
            prompt_source = ast.get_source_segment(source, user_message_contents[0]) or ""
            if prompt_source:
                return [BlockField(name="PROMPT", value=prompt_source.strip(), editable=True)]

        if messages_source:
            return [BlockField(name="MESSAGES", value=messages_source.strip(), editable=True)]

    return []


def _is_user_role_expr(value: ast.expr) -> bool:
    return (
        isinstance(value, ast.Attribute)
        and isinstance(value.value, ast.Name)
        and value.value.id == "MessagesRole"
        and value.attr == "USER"
    ) or (isinstance(value, ast.Constant) and value.value == "user")


def _should_expose_assignment(
    name: str,
    value: ast.expr,
    extra_editable_names: set[str] | None,
) -> bool:
    if name.isupper() or name in SPECIAL_EDITABLE_FIELD_NAMES:
        return True
    if extra_editable_names is None or name not in extra_editable_names:
        return False
    return _is_context_editable_value(value)


def _is_context_editable_value(value: ast.expr) -> bool:
    return isinstance(value, (ast.Constant, ast.JoinedStr, ast.List, ast.Dict, ast.Tuple))


def _resolve_generic_example_runtime_indexes(
    code_cells: list[tuple[int, object]],
) -> dict[int, list[int]]:
    if not code_cells:
        return {}

    assigned_names_by_cell: dict[int, set[str]] = {}
    dependencies_by_cell: dict[int, set[str]] = {}
    all_defined_names: set[str] = set()
    for cell_index, cell in code_cells:
        assigned_names = _assigned_names(cell.source)
        assigned_names_by_cell[cell_index] = assigned_names
        all_defined_names.update(assigned_names)

    for cell_index, cell in code_cells:
        dependencies_by_cell[cell_index] = _loaded_names(cell.source) - assigned_names_by_cell[cell_index]
        dependencies_by_cell[cell_index] &= all_defined_names

    resolved: dict[int, list[int]] = {}
    for position, (cell_index, _) in enumerate(code_cells):
        needed = set(dependencies_by_cell[cell_index])
        runtime_indexes = [cell_index]
        for prior_index in range(position - 1, -1, -1):
            prior_cell_index, _ = code_cells[prior_index]
            prior_assigned = assigned_names_by_cell[prior_cell_index]
            if not (needed & prior_assigned):
                continue
            runtime_indexes.append(prior_cell_index)
            needed = (needed - prior_assigned) | dependencies_by_cell[prior_cell_index]
        resolved[cell_index] = sorted(runtime_indexes)
    return resolved


def _assigned_names(source: str) -> set[str]:
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", SyntaxWarning)
            tree = ast.parse(source)
    except SyntaxError:
        return set()

    assigned: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name):
                    assigned.add(target.id)
    return assigned


def _loaded_names(source: str) -> set[str]:
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", SyntaxWarning)
            tree = ast.parse(source)
    except SyntaxError:
        return set()

    return {
        node.id
        for node in ast.walk(tree)
        if isinstance(node, ast.Name) and isinstance(node.ctx, ast.Load)
    }


def _build_tool_use_demo_block(notebook, notebook_file: Path) -> Block:
    instruction_indexes = [212, 214, 216, 218, 220, 222, 224]
    runtime_indexes = [213, 215, 217, 219, 221, 223, 225]
    instructions = "\n\n".join(
        notebook.cells[index].source.strip()
        for index in instruction_indexes
        if notebook.cells[index].cell_type == "markdown"
    )
    return Block(
        id="tool-use-calculator-demo",
        title="Tool Use Calculator Demo",
        kind="tool_use_demo",
        notebook_path=str(notebook_file),
        notebook_cell_indexes=runtime_indexes,
        instructions_markdown=instructions,
        instructions_html=_render_markdown(instructions),
    )


def _render_markdown(text: str) -> str:
    safe_text = html.escape(text, quote=False)
    return markdown.markdown(
        safe_text,
        extensions=["fenced_code", "tables", "sane_lists"],
    )


def _generic_example_title(part_title: str, example_number: int, pending_markdown: list[str]) -> str:
    for markdown_text in reversed(pending_markdown):
        for line in markdown_text.splitlines():
            stripped = line.strip()
            if stripped.startswith("#### "):
                return f"{part_title} {stripped[5:].strip()}"
    return f"{part_title} Example {example_number}"
