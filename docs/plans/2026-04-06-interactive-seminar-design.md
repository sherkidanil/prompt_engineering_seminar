# Interactive Prompt Engineering Seminar Design

## Goal

Turn `PE_seminar.ipynb` into a local interactive web application that preserves the existing seminar structure and behavior as closely as possible.

The local service must let a user:
- open the seminar in a browser,
- paste a GigaChat API key locally,
- choose a model,
- run examples and exercises from the notebook,
- see the same prompt scaffolding, outputs, hints, and possible solutions,
- get the same grading behavior for the graded exercises,
- use a separate sandbox without exercise constraints.

## Constraints

- `PE_seminar.ipynb` is the source of truth.
- The service should avoid manually reauthoring seminar content.
- The UI should expose only the fields that the notebook expects the learner to edit.
- GigaChat credentials must not be written to disk or committed.
- The first version must include the entire prompt engineering seminar, including the tool use section and SQL exercise.
- `RAG_seminar.ipynb` is out of scope for this feature.

## Recommended Approach

Use a notebook-driven architecture with a Python backend and a no-build frontend.

### Why this approach

A notebook-driven runner minimizes content drift. The notebook already contains:
- the lesson text,
- the example prompts,
- the exercise scaffolding,
- the grading functions,
- the hint and solution references,
- the tool use demo flow.

Instead of copying that logic into a separate app-specific data model by hand, the service should parse the notebook for structure and execute sanitized notebook code for runtime behavior.

## Architecture

### Backend

Use FastAPI for the local web service.

Responsibilities:
- load and parse `PE_seminar.ipynb`,
- expose a structured seminar manifest to the frontend,
- run notebook-backed examples and exercises with user overrides,
- call GigaChat with the same request defaults as the notebook,
- execute grader logic for graded exercises,
- run the tool use demo chain for Part 11,
- serve the frontend assets.

### Frontend

Use a server-served single-page interface without a Node build step.

Responsibilities:
- render the seminar navigation,
- render markdown lesson content,
- render exercise and example editors,
- store API key and user preferences in browser local storage,
- show model responses, grading results, hints, solutions, and execution traces,
- provide a standalone sandbox tab.

This keeps local setup simple: Python dependencies only.

## Content Model

The backend should convert the notebook into a normalized manifest with these entities:

- `SeminarManifest`
- `Part`
- `Block`

Each `Block` should have a `type` such as:
- `markdown`
- `example`
- `exercise_graded`
- `exercise_open`
- `tool_use_demo`
- `unsupported`

Each interactive block should expose:
- stable `id`,
- title,
- source notebook cell indexes,
- visible instructions,
- editable fields,
- read-only scaffold fields,
- hint text if present,
- possible solution text if present,
- execution mode.

## Notebook Parsing Strategy

### Structure extraction

Parse `PE_seminar.ipynb` with `nbformat`.

Detect:
- parts from markdown headings like `## Part 1`,
- exercises from markdown headings like `### Exercise 4.2 - ...`,
- examples from markdown headings like `### Example - ...`,
- associated code cells by position,
- hint cells via `from hints import ...`,
- solution cells via `from hints import ..._solution` or notebook code cells that print a solution.

### Editable-field extraction

Interactive cells should be analyzed for top-level uppercase assignments such as:
- `PROMPT`
- `SYSTEM_PROMPT`
- `PREFILL`
- `TASK_CONTEXT`
- `EXAMPLES`
- `INPUT_DATA`
- `system_prompt_tools_specific_tools_sql`

The parser should expose only the intended learner-editable fields for each block.

### Special-case support

Some sections are structurally different and should use explicit recipes:
- Part 9 scaffold-based prompt builders,
- Part 11 calculator tool-use chain,
- Exercise 10.2.1 SQL tool definition exercise.

This is still notebook-driven because the source content remains in the notebook; the app only adds execution recipes where the notebook layout is not regular enough for pure heuristics.

## Runtime Execution Model

### Common execution flow

For an example or exercise run:
1. Create a fresh execution namespace.
2. Execute required setup cells after sanitizing notebook-only IPython magic lines.
3. Inject runtime helpers for output capture.
4. Patch notebook cell source with user-provided overrides for editable variables.
5. Execute the original notebook cell or cell sequence.
6. Capture stdout, derived prompt text, response text, and grading result if present.

### Sanitization

The executor should strip or ignore notebook-only lines such as `%store`.

### Variable override model

Assignment replacement should be source-aware, not string-fragile. Use AST-based or line-precise replacement so that a user override changes only the intended variable assignment while preserving the rest of the notebook cell logic.

### Graded exercises

For graded exercises, execute the original `grade_exercise(...)` function from the notebook cell and report:
- response,
- boolean pass/fail,
- raw grader output when useful.

### Open-ended exercises

For non-graded exercises, reproduce notebook behavior without inventing a new grader:
- show the compiled prompt,
- show the model response,
- expose hint and solution actions.

### Tool use demos

Support the notebook's multi-step tool flow:
- first model call with `stop_sequences`,
- extraction of requested tool parameters,
- local execution of the demonstration tool,
- injection of `<function_results>`,
- second model call for final response.

The UI should expose each stage so the learner can inspect the chain.

## GigaChat Integration

Create a small backend wrapper that mirrors the notebook helper:
- same `temperature=0.0`,
- same `max_tokens=2000`,
- support for `system_prompt`, `prefill`, `messages`, `stop_sequences`.

Differences from the notebook:
- credentials come from the browser request instead of `.env`,
- model name comes from user settings in the UI,
- error handling should return structured API errors.

## API Surface

Planned endpoints:
- `GET /` - serve the app shell
- `GET /api/manifest` - return parsed seminar manifest
- `POST /api/session/test-connection` - validate credentials and model with a lightweight GigaChat request
- `POST /api/run/block/{block_id}` - execute an example, exercise, or tool-use block
- `POST /api/run/sandbox` - execute free-form sandbox requests

The block execution response should include:
- normalized prompt or message chain,
- system prompt,
- prefill,
- response text,
- stdout trace,
- grading result if available,
- tool-call trace if applicable,
- surfaced hint and solution metadata.

## Frontend UX

### Layout

Use a three-pane desktop layout that collapses on mobile:
- left: seminar navigation,
- center: lesson content,
- right: interactive runner.

### Setup panel

Provide:
- API key input,
- model selector,
- temperature and max token fields with notebook defaults prefilled,
- connection test button.

Store settings in browser local storage only.

### Example runner

Show:
- editable fields,
- read-only scaffold,
- run button,
- compiled prompt preview,
- model response,
- stdout captured from notebook execution.

### Exercise runner

Show:
- exercise instructions,
- editable fields only,
- reset-to-default action,
- run button,
- grading card for graded exercises,
- hint button,
- possible solution button when available.

### Sandbox

Provide a separate workspace with:
- system prompt editor,
- user message or multi-message editor,
- prefill field,
- stop sequences field,
- model response output,
- prompt preview.

No grading should be attached to sandbox runs.

## Security and Local Safety

- Never persist the API key on disk.
- Do not log request bodies that contain credentials.
- Use a restricted execution namespace for notebook runtime logic.
- Allow notebook execution only from the checked-in seminar notebook, not from arbitrary uploaded notebooks.
- Keep tool execution for Part 11 restricted to the demonstration functions defined by the app.

## Testing Strategy

### Parser tests

Verify that parsing finds:
- all seminar parts,
- all exercise titles,
- all graded exercise blocks,
- all hint and solution references expected by the notebook.

### Executor tests

Verify that:
- editable assignment overrides are applied correctly,
- notebook magics are sanitized safely,
- graded exercise code can run without the notebook shell,
- tool use demo helpers produce the expected formatted outputs.

### API tests

Verify:
- manifest endpoint shape,
- block execution response shape,
- sandbox response shape,
- graceful error handling for invalid credentials or invalid model names.

### Manual smoke tests

Verify at least:
- one early example,
- one graded exercise,
- one scaffold-based exercise from Part 9,
- the calculator tool-use demo,
- Exercise 10.2.1 SQL prompt testing,
- sandbox mode.

## Initial File Layout

Recommended new files:
- `interactive_seminar/__init__.py`
- `interactive_seminar/app.py`
- `interactive_seminar/schemas.py`
- `interactive_seminar/notebook_loader.py`
- `interactive_seminar/executor.py`
- `interactive_seminar/gigachat_runner.py`
- `interactive_seminar/templates/index.html`
- `interactive_seminar/static/app.js`
- `interactive_seminar/static/styles.css`
- `interactive_seminar/tests/test_notebook_loader.py`
- `interactive_seminar/tests/test_executor.py`
- `interactive_seminar/tests/test_api.py`
- `run_interactive_seminar.py`

Files to update:
- `requirements.txt`
- `README.md`

## Tradeoffs

### Why not wrap Jupyter directly

A direct notebook wrapper would reduce implementation effort, but it would make the local app harder to control, harder to style well, and harder to extend with sandbox mode and structured grading output.

### Why not rewrite the seminar by hand

Manual rewriting would give total UI control but would immediately create drift from the notebook and hints. That is the exact failure mode this design avoids.

## Success Criteria

The first version is successful if a user can:
- start a local Python service,
- open the seminar in a browser,
- enter a GigaChat API key,
- run and edit all prompt engineering seminar sections from `PE_seminar.ipynb`,
- see the expected grader results for the graded exercises,
- inspect the Part 11 tool-use chain,
- use a separate sandbox without exercise constraints.
