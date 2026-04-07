# RAG Seminar Colab Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Update `RAG_seminar.ipynb` to use the current split LangChain/GigaChat packages and Colab-friendly setup while preserving the existing seminar flow.

**Architecture:** Treat the notebook as structured JSON and validate it with tests. First lock the desired package/import contract in tests, then update the notebook cells and the repo-level RAG requirements file to match. Keep the seminar logic intact; only change installation, imports, and outdated invocation patterns.

**Tech Stack:** Python, `pytest`, `json`, `RAG_seminar.ipynb`, LangChain split packages, GigaChat SDK, Google Colab install conventions

---

### Task 1: Lock The Notebook Contract In Tests

**Files:**
- Create: `interactive_seminar/tests/test_rag_notebook.py`
- Modify: `RAG_seminar.ipynb`

**Step 1: Write the failing test**

Add tests that parse `RAG_seminar.ipynb` and assert:
- required packages such as `langchain-classic`, `langchain-community`, `langchain-huggingface`, `langchain-gigachat`, `langchain-text-splitters`, `gigachat`, `pypdf`, and `playwright` appear in install cells
- deprecated strings such as `gigachain`, `pydantic==1.10.13`, `from langchain.embeddings import HuggingFaceEmbeddings`, `from langchain.text_splitter import RecursiveCharacterTextSplitter`, and `from langchain.chat_models.gigachat import GigaChat` do not appear
- deprecated calls such as `llm(` and `.get_relevant_documents(` are not present in code cells where the notebook should use `invoke`

**Step 2: Run test to verify it fails**

Run: `python -m pytest interactive_seminar/tests/test_rag_notebook.py -q`
Expected: FAIL because the current notebook still contains old packages/imports.

**Step 3: Write minimal implementation**

No implementation in this task.

**Step 4: Commit**

```bash
git add interactive_seminar/tests/test_rag_notebook.py
git commit -m "test: cover rag notebook colab compatibility"
```

### Task 2: Update Notebook Install Cells And Imports

**Files:**
- Modify: `RAG_seminar.ipynb`
- Test: `interactive_seminar/tests/test_rag_notebook.py`

**Step 1: Write the failing test**

Reuse the failing tests from Task 1 as the red state.

**Step 2: Run test to verify it fails**

Run: `python -m pytest interactive_seminar/tests/test_rag_notebook.py -q`
Expected: FAIL with missing current package names and/or forbidden old imports.

**Step 3: Write minimal implementation**

Update notebook code cells to:
- replace old `pip install` commands with Colab-friendly `%pip install -qU ...` commands using the current split package stack
- install Playwright Chromium explicitly
- import `HuggingFaceEmbeddings` from `langchain_huggingface`
- import `RecursiveCharacterTextSplitter` from `langchain_text_splitters`
- import `GigaChat` from `langchain_gigachat.chat_models`
- import chain classes from `langchain_classic` where required
- replace `llm(...)` with `llm.invoke(...)`
- replace `.get_relevant_documents(...)` with `.invoke(...)`

**Step 4: Run test to verify it passes**

Run: `python -m pytest interactive_seminar/tests/test_rag_notebook.py -q`
Expected: PASS.

**Step 5: Commit**

```bash
git add RAG_seminar.ipynb interactive_seminar/tests/test_rag_notebook.py
git commit -m "fix: modernize rag seminar notebook for colab"
```

### Task 3: Align Repo RAG Requirements And Run Smoke Verification

**Files:**
- Modify: `requirements_rag.txt`
- Test: `interactive_seminar/tests/test_rag_notebook.py`

**Step 1: Write the failing test**

Add or extend a test that checks `requirements_rag.txt` includes the same current package family required by the notebook.

**Step 2: Run test to verify it fails**

Run: `python -m pytest interactive_seminar/tests/test_rag_notebook.py -q`
Expected: FAIL if `requirements_rag.txt` still lags the notebook dependency contract.

**Step 3: Write minimal implementation**

Update `requirements_rag.txt` so it matches the notebook dependency stack closely enough for local setup and CI-style smoke checks.

**Step 4: Run tests and smoke checks**

Run:
- `python -m pytest interactive_seminar/tests/test_rag_notebook.py -q`
- `python - <<'PY' ...` import smoke script for the updated modules

Expected: tests pass and imports succeed.

**Step 5: Commit**

```bash
git add requirements_rag.txt interactive_seminar/tests/test_rag_notebook.py
git commit -m "chore: align rag requirements with notebook"
```
