# Interactive Seminar Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Build a local FastAPI-backed interactive web app that renders `PE_seminar.ipynb`, runs all examples and exercises against GigaChat, preserves notebook grading behavior, and provides a standalone sandbox.

**Architecture:** Parse `PE_seminar.ipynb` into a normalized manifest, then execute sanitized notebook code with user-provided variable overrides through a FastAPI API. Serve a no-build single-page frontend from the same Python app so local setup stays Python-only.

**Tech Stack:** Python, FastAPI, Jinja2, nbformat, markdown, GigaChat Python SDK, vanilla JavaScript, pytest, httpx

---

### Task 1: Add Service Skeleton And Dependencies

**Files:**
- Create: `interactive_seminar/__init__.py`
- Create: `interactive_seminar/app.py`
- Create: `run_interactive_seminar.py`
- Test: `interactive_seminar/tests/test_api.py`
- Modify: `requirements.txt`

**Step 1: Write the failing test**

```python
from fastapi.testclient import TestClient

from interactive_seminar.app import create_app


def test_healthcheck_endpoint_exists():
    client = TestClient(create_app())
    response = client.get('/api/health')
    assert response.status_code == 200
    assert response.json() == {'status': 'ok'}
```

**Step 2: Run test to verify it fails**

Run: `pytest interactive_seminar/tests/test_api.py::test_healthcheck_endpoint_exists -q`
Expected: `ModuleNotFoundError` for `interactive_seminar` or `ImportError` for `create_app`.

**Step 3: Write minimal implementation**

```python
from fastapi import FastAPI


def create_app() -> FastAPI:
    app = FastAPI()

    @app.get('/api/health')
    def healthcheck() -> dict[str, str]:
        return {'status': 'ok'}

    return app
```

```python
from interactive_seminar.app import create_app

app = create_app()
```

Add these packages to `requirements.txt`:

```text
fastapi
uvicorn
jinja2
nbformat
markdown
pytest
httpx
```

**Step 4: Run test to verify it passes**

Run: `pytest interactive_seminar/tests/test_api.py::test_healthcheck_endpoint_exists -q`
Expected: `1 passed`

**Step 5: Commit**

```bash
git add requirements.txt interactive_seminar/__init__.py interactive_seminar/app.py run_interactive_seminar.py interactive_seminar/tests/test_api.py
git commit -m "feat: scaffold interactive seminar service"
```

### Task 2: Parse The Notebook Into A Manifest

**Files:**
- Create: `interactive_seminar/schemas.py`
- Create: `interactive_seminar/notebook_loader.py`
- Test: `interactive_seminar/tests/test_notebook_loader.py`

**Step 1: Write the failing tests**

```python
from interactive_seminar.notebook_loader import load_manifest


def test_manifest_contains_all_exercises():
    manifest = load_manifest('PE_seminar.ipynb', 'hints.py')
    exercise_titles = [block.title for part in manifest.parts for block in part.blocks if block.kind.startswith('exercise')]
    assert 'Exercise 1.1 - Counting to Three' in exercise_titles
    assert 'Exercise 10.2.1 - SQL' in exercise_titles
    assert len(exercise_titles) == 20


def test_manifest_marks_graded_exercises_correctly():
    manifest = load_manifest('PE_seminar.ipynb', 'hints.py')
    graded_ids = {block.id for part in manifest.parts for block in part.blocks if block.kind == 'exercise_graded'}
    assert 'exercise-1-1-counting-to-three' in graded_ids
    assert 'exercise-8-1-prospectus-hallucination' in graded_ids
```

**Step 2: Run tests to verify they fail**

Run: `pytest interactive_seminar/tests/test_notebook_loader.py -q`
Expected: `ImportError` for `load_manifest` or assertion failures because parsing is not implemented.

**Step 3: Write minimal implementation**

Implement Pydantic models in `interactive_seminar/schemas.py`:

```python
class BlockField(BaseModel):
    name: str
    value: str
    editable: bool


class Block(BaseModel):
    id: str
    title: str
    kind: str
    notebook_cell_indexes: list[int]
    instructions_markdown: str
    editable_fields: list[BlockField] = []
    readonly_fields: list[BlockField] = []
    hint: str | None = None
    solution: str | None = None
```

Implement `load_manifest(...)` in `interactive_seminar/notebook_loader.py` to:
- load `PE_seminar.ipynb` with `nbformat`,
- detect parts and block headings from markdown,
- attach nearby code cells,
- classify `exercise_graded` when the code cell contains `def grade_exercise`,
- pull hint and solution text from `hints.py`,
- assign slug IDs like `exercise-1-1-counting-to-three`.

**Step 4: Run tests to verify they pass**

Run: `pytest interactive_seminar/tests/test_notebook_loader.py -q`
Expected: all manifest tests pass.

**Step 5: Commit**

```bash
git add interactive_seminar/schemas.py interactive_seminar/notebook_loader.py interactive_seminar/tests/test_notebook_loader.py
git commit -m "feat: parse seminar notebook manifest"
```

### Task 3: Build Notebook Execution And Grading For Simple Blocks

**Files:**
- Create: `interactive_seminar/gigachat_runner.py`
- Create: `interactive_seminar/executor.py`
- Test: `interactive_seminar/tests/test_executor.py`

**Step 1: Write the failing tests**

```python
from interactive_seminar.executor import sanitize_cell_source, apply_assignment_overrides


def test_sanitize_cell_source_removes_ipython_magics():
    source = '%store -r MODEL_NAME\nprint(MODEL_NAME)\n'
    assert sanitize_cell_source(source) == 'print(MODEL_NAME)\n'


def test_apply_assignment_overrides_replaces_prompt_assignment_only():
    source = 'PROMPT = "[Replace this text]"\nresponse = get_completion(PROMPT)\n'
    updated = apply_assignment_overrides(source, {'PROMPT': 'Count to 3.'})
    assert 'PROMPT = "Count to 3."' in updated
    assert 'response = get_completion(PROMPT)' in updated
```

Add one execution-path test with a fake runner:

```python
from interactive_seminar.executor import execute_block


def test_execute_graded_block_returns_grade(fake_manifest, fake_runner):
    result = execute_block(fake_manifest.block('exercise-1-1-counting-to-three'), {'PROMPT': 'Count to 3.'}, fake_runner)
    assert result.response == '1 2 3'
    assert result.grade.passed is True
```

**Step 2: Run tests to verify they fail**

Run: `pytest interactive_seminar/tests/test_executor.py -q`
Expected: missing functions and failing execution path.

**Step 3: Write minimal implementation**

Implement `gigachat_runner.py` with a small adapter:

```python
class GigaChatRunner:
    def run(self, *, credentials: str, model: str, prompt_or_messages, system_prompt: str = '', prefill: str = '', stop_sequences: list[str] | None = None) -> str:
        ...
```

Implement `executor.py` helpers to:
- strip notebook magics,
- replace editable uppercase assignments,
- execute setup cells in a fresh namespace,
- inject a `get_completion(...)` wrapper that delegates to the runner,
- capture `stdout`, `response`, `PROMPT`, `SYSTEM_PROMPT`, and `PREFILL`,
- execute `grade_exercise(response)` when present.

**Step 4: Run tests to verify they pass**

Run: `pytest interactive_seminar/tests/test_executor.py -q`
Expected: all basic executor tests pass.

**Step 5: Commit**

```bash
git add interactive_seminar/gigachat_runner.py interactive_seminar/executor.py interactive_seminar/tests/test_executor.py
git commit -m "feat: execute notebook blocks and graders"
```

### Task 4: Support Scaffold-Based Exercises And Prompt Preview

**Files:**
- Modify: `interactive_seminar/notebook_loader.py`
- Modify: `interactive_seminar/executor.py`
- Test: `interactive_seminar/tests/test_notebook_loader.py`
- Test: `interactive_seminar/tests/test_executor.py`

**Step 1: Write the failing tests**

```python
from interactive_seminar.notebook_loader import load_manifest


def test_manifest_exposes_part9_scaffold_fields():
    manifest = load_manifest('PE_seminar.ipynb', 'hints.py')
    block = manifest.block('exercise-9-1-financial-services-chatbot')
    editable_names = [field.name for field in block.editable_fields]
    assert editable_names == [
        'TASK_CONTEXT',
        'TONE_CONTEXT',
        'INPUT_DATA',
        'EXAMPLES',
        'TASK_DESCRIPTION',
        'IMMEDIATE_TASK',
        'PRECOGNITION',
        'OUTPUT_FORMATTING',
        'PREFILL',
        'PROMPT',
    ]
```

```python
from interactive_seminar.executor import execute_block


def test_execute_open_block_returns_compiled_prompt(fake_manifest, fake_runner):
    result = execute_block(fake_manifest.block('exercise-9-2-codebot'), {'TASK_CONTEXT': 'You are Codebot.'}, fake_runner)
    assert 'You are Codebot.' in result.prompt_preview
    assert result.grade is None
```

**Step 2: Run tests to verify they fail**

Run: `pytest interactive_seminar/tests/test_notebook_loader.py interactive_seminar/tests/test_executor.py -q`
Expected: scaffold fields are missing or prompt preview is not captured.

**Step 3: Write minimal implementation**

Update parser logic to:
- preserve editable field order from the notebook cell,
- mark long input variables like `QUESTION`, `TAX_CODE`, and `CODE` as read-only context,
- store enough source cell indexes for multi-cell scaffold exercises.

Update executor logic to:
- capture compiled `PROMPT` after execution,
- return read-only context values alongside editable field values,
- handle `exercise_open` blocks without expecting a grader.

**Step 4: Run tests to verify they pass**

Run: `pytest interactive_seminar/tests/test_notebook_loader.py interactive_seminar/tests/test_executor.py -q`
Expected: scaffold tests pass.

**Step 5: Commit**

```bash
git add interactive_seminar/notebook_loader.py interactive_seminar/executor.py interactive_seminar/tests/test_notebook_loader.py interactive_seminar/tests/test_executor.py
git commit -m "feat: support scaffold-based seminar exercises"
```

### Task 5: Add Tool-Use Demo And SQL Exercise Execution

**Files:**
- Modify: `interactive_seminar/notebook_loader.py`
- Modify: `interactive_seminar/executor.py`
- Test: `interactive_seminar/tests/test_executor.py`

**Step 1: Write the failing tests**

```python
from interactive_seminar.executor import construct_successful_function_run_injection_prompt, find_parameter


def test_find_parameter_extracts_tool_arguments():
    message = '<function_calls><invoke name="calculator"><antml:parameter name="first_operand">2</parameter></invoke>'
    assert find_parameter(message, 'first_operand') == '2'


def test_construct_successful_function_run_injection_prompt_formats_results():
    prompt = construct_successful_function_run_injection_prompt([{'tool_name': 'calculator', 'tool_result': 12}])
    assert '<function_results>' in prompt
    assert '<tool_name>calculator</tool_name>' in prompt
    assert '<stdout>\n12\n</stdout>' in prompt
```

Add one integration-style test:

```python
def test_execute_tool_use_demo_returns_intermediate_trace(fake_tool_manifest, fake_runner):
    result = execute_block(fake_tool_manifest.block('tool-use-calculator-demo'), {}, fake_runner)
    assert result.tool_trace.first_response.startswith('<function_calls>')
    assert result.tool_trace.function_results.startswith('<function_results>')
```

**Step 2: Run tests to verify they fail**

Run: `pytest interactive_seminar/tests/test_executor.py -q`
Expected: missing tool helper functions or no tool trace payload.

**Step 3: Write minimal implementation**

Extend executor logic to support the Part 11 recipes:
- calculator demo first call,
- parameter extraction,
- local arithmetic execution,
- function result injection,
- second model call,
- SQL exercise prompt testing with `stop_sequences=['</function_calls>']`.

Return a structured tool trace payload such as:

```python
{
    'first_response': ...,
    'tool_inputs': ...,
    'tool_result': ...,
    'function_results': ...,
    'final_response': ...,
}
```

**Step 4: Run tests to verify they pass**

Run: `pytest interactive_seminar/tests/test_executor.py -q`
Expected: tool-use tests pass.

**Step 5: Commit**

```bash
git add interactive_seminar/notebook_loader.py interactive_seminar/executor.py interactive_seminar/tests/test_executor.py
git commit -m "feat: support tool-use seminar blocks"
```

### Task 6: Expose Manifest And Execution APIs

**Files:**
- Modify: `interactive_seminar/app.py`
- Modify: `interactive_seminar/schemas.py`
- Test: `interactive_seminar/tests/test_api.py`

**Step 1: Write the failing tests**

```python
from fastapi.testclient import TestClient

from interactive_seminar.app import create_app


def test_manifest_endpoint_returns_parts():
    client = TestClient(create_app())
    response = client.get('/api/manifest')
    assert response.status_code == 200
    body = response.json()
    assert 'parts' in body
    assert any(part['title'] == 'Part 1' for part in body['parts'])
```

```python
def test_sandbox_endpoint_returns_response_shape():
    client = TestClient(create_app())
    payload = {
        'credentials': 'test-key',
        'model': 'GigaChat',
        'messages': [{'role': 'user', 'content': 'Hello'}],
        'system_prompt': '',
        'prefill': '',
        'stop_sequences': [],
    }
    response = client.post('/api/run/sandbox', json=payload)
    assert response.status_code in {200, 400}
    assert 'response' in response.json() or 'error' in response.json()
```

**Step 2: Run tests to verify they fail**

Run: `pytest interactive_seminar/tests/test_api.py -q`
Expected: missing endpoints or invalid response shapes.

**Step 3: Write minimal implementation**

Add endpoints to `interactive_seminar/app.py`:
- `GET /api/manifest`
- `POST /api/session/test-connection`
- `POST /api/run/block/{block_id}`
- `POST /api/run/sandbox`

Load the notebook manifest once during app startup and pass requests to the executor. Return normalized JSON with fields such as:

```python
{
    'prompt_preview': ...,
    'system_prompt': ...,
    'prefill': ...,
    'response': ...,
    'stdout': ...,
    'grade': {'passed': True, 'details': ...} | None,
    'tool_trace': ...,
}
```

**Step 4: Run tests to verify they pass**

Run: `pytest interactive_seminar/tests/test_api.py -q`
Expected: API tests pass.

**Step 5: Commit**

```bash
git add interactive_seminar/app.py interactive_seminar/schemas.py interactive_seminar/tests/test_api.py
git commit -m "feat: add interactive seminar api"
```

### Task 7: Build The Frontend Shell And Seminar UI

**Files:**
- Create: `interactive_seminar/templates/index.html`
- Create: `interactive_seminar/static/app.js`
- Create: `interactive_seminar/static/styles.css`
- Modify: `interactive_seminar/app.py`

**Step 1: Write the failing smoke check**

Add a simple API-backed UI test to `interactive_seminar/tests/test_api.py`:

```python
def test_root_serves_html_shell():
    client = TestClient(create_app())
    response = client.get('/')
    assert response.status_code == 200
    assert 'text/html' in response.headers['content-type']
    assert 'Interactive Prompt Engineering Seminar' in response.text
```

**Step 2: Run test to verify it fails**

Run: `pytest interactive_seminar/tests/test_api.py::test_root_serves_html_shell -q`
Expected: 404 or missing HTML marker text.

**Step 3: Write minimal implementation**

Create a server-rendered shell with these regions:
- left navigation for parts and blocks,
- center content panel for markdown lesson content,
- right runner panel for editable fields and results,
- top settings strip for API key, model, and connection testing,
- separate sandbox tab.

In `interactive_seminar/static/app.js`, implement:
- manifest fetch and initial render,
- localStorage persistence for credentials and settings,
- block rendering based on `kind`,
- block run and sandbox run actions,
- hint and solution toggles,
- tool trace rendering.

In `interactive_seminar/static/styles.css`, implement a distinctive responsive layout using CSS variables and a three-pane grid that collapses for mobile.

**Step 4: Run test to verify it passes**

Run: `pytest interactive_seminar/tests/test_api.py::test_root_serves_html_shell -q`
Expected: `1 passed`

Then run a manual smoke test:

```bash
python run_interactive_seminar.py
```

Expected: app starts locally and the browser UI can load the seminar manifest.

**Step 5: Commit**

```bash
git add interactive_seminar/templates/index.html interactive_seminar/static/app.js interactive_seminar/static/styles.css interactive_seminar/app.py interactive_seminar/tests/test_api.py
git commit -m "feat: add seminar web interface"
```

### Task 8: Update Docs And Verify End-To-End Behavior

**Files:**
- Modify: `README.md`

**Step 1: Write the failing verification checklist**

Create a local checklist in the commit message or scratch notes with these expected checks:
- `GET /api/manifest` returns all seminar parts
- one graded exercise returns `grade.passed`
- one Part 9 exercise returns a compiled prompt preview
- calculator demo returns a tool trace
- SQL exercise returns a function-call style first response
- sandbox can send a free-form prompt

**Step 2: Run project verification before docs changes**

Run:

```bash
pytest interactive_seminar/tests -q
```

Expected: all tests pass.

**Step 3: Write minimal documentation updates**

Add a new README section with:
- dependency installation,
- local server startup,
- browser URL,
- API key handling note,
- supported seminar scope,
- sandbox description.

Recommended commands to document:

```bash
pip install -r requirements.txt
python run_interactive_seminar.py
```

**Step 4: Run final verification**

Run:

```bash
pytest interactive_seminar/tests -q
python run_interactive_seminar.py
```

Expected: tests pass and the service boots cleanly.

**Step 5: Commit**

```bash
git add README.md
git commit -m "docs: document interactive seminar service"
```
