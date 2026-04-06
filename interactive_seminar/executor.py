from __future__ import annotations

import ast
import io
import json
import re
from contextlib import redirect_stdout
from dataclasses import dataclass
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
    execution_state = {"last_model_text": None}
    client = _NotebookClientProxy(
        runner,
        execution_state,
        credentials=credentials,
        model=model,
    )
    namespace = {
        "__name__": "__interactive_seminar__",
        "re": re,
        "Chat": NotebookChat,
        "Messages": NotebookMessage,
        "MessagesRole": NotebookMessagesRole,
        "client": client,
        "MODEL_NAME": model,
    }

    def get_completion(prompt_or_messages, system_prompt: str = "", prefill: str = "", stop_sequences=None):
        text = runner.run(
            credentials=credentials,
            model=model,
            prompt_or_messages=prompt_or_messages,
            system_prompt=system_prompt,
            prefill=prefill,
            stop_sequences=stop_sequences,
        )
        execution_state["last_model_text"] = text
        return text

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

    response = (
        execution_state.get("last_model_text")
        or namespace.get("final_response")
        or namespace.get("function_calling_response")
        or namespace.get("response")
        or ""
    )
    grade_result = None
    grader = namespace.get("grade_exercise")
    if callable(grader) and response != "":
        grade_result = GradeResult(passed=bool(grader(response)))

    tool_trace = None
    if block.kind == "tool_use_demo" or namespace.get("function_calling_response") is not None:
        tool_trace = {
            "first_response": _as_text(namespace.get("function_calling_response")) or "",
            "tool_inputs": {
                "first_operand": _as_text(namespace.get("first_operand")),
                "second_operand": _as_text(namespace.get("second_operand")),
                "operator": _as_text(namespace.get("operator")),
            },
            "tool_result": _as_text(namespace.get("result")),
            "function_results": _as_text(namespace.get("function_results")) or "",
            "final_response": _as_text(namespace.get("final_response")) or "",
        }

    return ExecutionResult(
        prompt_preview=_as_text(namespace.get("PROMPT")),
        system_prompt=_as_text(namespace.get("SYSTEM_PROMPT")),
        prefill=_as_text(namespace.get("PREFILL")),
        response=_as_text(response) or "",
        stdout=stdout_buffer.getvalue(),
        grade=grade_result,
        tool_trace=tool_trace,
    )


def _line_col_to_offset(lines: list[str], lineno: int, col_offset: int) -> int:
    return sum(len(line) for line in lines[: lineno - 1]) + col_offset


class NotebookMessagesRole:
    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"


@dataclass
class NotebookMessage:
    role: str
    content: str


@dataclass
class NotebookChat:
    model: str
    max_tokens: int
    temperature: float
    messages: list[NotebookMessage]


@dataclass
class _NotebookChoiceMessage:
    content: str


@dataclass
class _NotebookChoice:
    message: _NotebookChoiceMessage


@dataclass
class _NotebookResponse:
    choices: list[_NotebookChoice]


class _NotebookClientProxy:
    def __init__(self, runner, execution_state: dict[str, object], *, credentials: str, model: str):
        self._runner = runner
        self._execution_state = execution_state
        self._credentials = credentials
        self._model = model

    def chat(self, chat: NotebookChat) -> _NotebookResponse:
        messages = [
            {"role": message.role, "content": message.content}
            for message in chat.messages
        ]
        text = self._runner.run(
            credentials=self._credentials,
            model=chat.model or self._model,
            prompt_or_messages=messages,
            system_prompt="",
            prefill="",
            stop_sequences=None,
        )
        self._execution_state["last_model_text"] = text
        return _NotebookResponse(choices=[_NotebookChoice(message=_NotebookChoiceMessage(content=text))])


def find_parameter(message: str, parameter_name: str) -> str | None:
    pattern = re.compile(
        rf'name="{re.escape(parameter_name)}">\s*(.*?)\s*</parameter>',
        re.DOTALL,
    )
    match = pattern.search(message)
    if not match:
        return None
    return match.group(1)


def construct_successful_function_run_injection_prompt(invoke_results: list[dict[str, object]]) -> str:
    constructed_prompt = (
        "<function_results>\n"
        + "\n".join(
            (
                f"<result>\n"
                f"<tool_name>{result['tool_name']}</tool_name>\n"
                f"<stdout>\n{result['tool_result']}\n</stdout>\n"
                f"</result>"
            )
            for result in invoke_results
        )
        + "\n</function_results>"
    )
    return constructed_prompt


def _render_assignment_value(value: object) -> str:
    if isinstance(value, dict) and "__raw__" in value:
        return str(value["__raw__"])
    if isinstance(value, str):
        return json.dumps(value, ensure_ascii=False)
    return repr(value)


def _as_text(value: object) -> str | None:
    if value is None:
        return None
    return str(value)
