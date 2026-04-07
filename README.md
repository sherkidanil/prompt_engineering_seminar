# GigaChat Seminar Repository

This repository now contains three seminar tracks:

- prompt engineering in [PE_seminar.ipynb](/Users/daniilserki/Documents/Workspace/AIMLEI/prompt_engineering_seminar/.worktrees/interactive-seminar/PE_seminar.ipynb)
- RAG in [RAG_seminar.ipynb](/Users/daniilserki/Documents/Workspace/AIMLEI/prompt_engineering_seminar/.worktrees/interactive-seminar/RAG_seminar.ipynb)
- function calling + MCP in `Function_Calling_MCP_seminar/`

The prompt engineering seminar is also available as a local interactive web app powered by the same notebook content.

## Contents

- `PE_seminar.ipynb` — source notebook for the prompt engineering seminar
- `RAG_seminar.ipynb` — source notebook for the RAG seminar
- `Function_Calling_MCP_seminar/` — function calling and MCP seminar materials
- `hints.py` — exercise hints and solution snippets
- `interactive_seminar/` — local FastAPI app, notebook parser, executor, frontend assets, and tests
- `run_interactive_seminar.py` — local web server entrypoint
- `requirements.txt` — install every seminar profile into one environment
- `requirements_prompt_engineering.txt` — prompt engineering notebook + interactive UI dependencies
- `requirements_rag.txt` — RAG seminar dependencies
- `requirements_mcp.txt` — function calling + MCP seminar dependencies

## Install

Create and activate a virtual environment, then install dependencies:

```bash
pip install -r requirements.txt
```

If you only need one seminar profile, install it directly:

```bash
pip install -r requirements_prompt_engineering.txt
pip install -r requirements_rag.txt
pip install -r requirements_mcp.txt
```

For the RAG seminar, you may also need browser binaries after installation:

```bash
playwright install
```

## Run The Interactive App

Start the local service:

```bash
python run_interactive_seminar.py
```

Then open:

```text
http://127.0.0.1:8000
```

In the UI you can:

- paste a GigaChat API key locally in the browser
- choose the model to run
- open seminar parts, examples, and exercises parsed from `PE_seminar.ipynb`
- edit only the intended prompt fields for each block
- run graded exercises and see pass/fail output
- inspect the Part 11 tool-use demo chain
- use a standalone sandbox without exercise constraints

## Notebook Usage

If you prefer the original notebook flow, configure the access key and model name via environment variables or `.env`:

```env
API_KEY=your_access_key
MODEL_NAME=GigaChat
```

The notebook also supports `GIGACHAT_CREDENTIALS` as an alternative variable name.

## Notes

- A valid GigaChat access key is required for real model calls.
- The interactive app keeps the API key in browser state and sends it only with the request being executed; it does not write the key to the repository.
- The seminar content for the app is parsed directly from `PE_seminar.ipynb` and `hints.py`, so notebook updates can be reflected in the web UI.
