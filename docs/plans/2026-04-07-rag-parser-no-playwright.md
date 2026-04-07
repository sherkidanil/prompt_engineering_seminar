# RAG Parser No-Playwright Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Remove Playwright from the PubMed parser step in `RAG_seminar.ipynb` and replace it with a Colab-friendly `requests + BeautifulSoup` implementation.

**Architecture:** Treat the notebook as structured JSON. First lock the desired parser contract in tests, then update the markdown/setup/parser cells and the RAG requirements/docs to match. Keep downstream notebook behavior and output files unchanged.

**Tech Stack:** Python, `pytest`, notebook JSON editing, `requests`, `beautifulsoup4`

---

### Task 1: Lock the no-Playwright parser contract in tests

**Files:**
- Modify: `interactive_seminar/tests/test_rag_notebook.py`
- Modify: `RAG_seminar.ipynb`

**Step 1: Write the failing test**

Add tests asserting:
- the parser flow no longer contains `AsyncChromiumLoader`
- the parser cell imports `requests`
- the parser cell extracts links via `BeautifulSoup`
- the Playwright install cell is gone from this parser flow
- `requirements_rag.txt` no longer requires `playwright`

**Step 2: Run test to verify it fails**

Run: `python -m pytest interactive_seminar/tests/test_rag_notebook.py -q`
Expected: FAIL because the notebook still contains Playwright-based parser setup.

**Step 3: Write minimal implementation**

No implementation in this task.

**Step 4: Commit**

```bash
git add interactive_seminar/tests/test_rag_notebook.py
git commit -m "test: cover no-playwright rag parser"
```

### Task 2: Replace the parser implementation in the notebook

**Files:**
- Modify: `RAG_seminar.ipynb`
- Test: `interactive_seminar/tests/test_rag_notebook.py`

**Step 1: Write the failing test**

Reuse the failing tests from Task 1.

**Step 2: Run test to verify it fails**

Run: `python -m pytest interactive_seminar/tests/test_rag_notebook.py -q`
Expected: FAIL with Playwright-specific parser expectations unmet.

**Step 3: Write minimal implementation**

Update notebook cells to:
- remove Playwright install usage from the parser flow
- rewrite the parser markdown description to explain the `requests + BeautifulSoup` approach
- rewrite `parser.py` to fetch HTML synchronously and write `page.html`/`links.txt`

**Step 4: Run test to verify it passes**

Run: `python -m pytest interactive_seminar/tests/test_rag_notebook.py -q`
Expected: PASS.

**Step 5: Commit**

```bash
git add RAG_seminar.ipynb interactive_seminar/tests/test_rag_notebook.py
git commit -m "fix: remove playwright from rag parser"
```

### Task 3: Align requirements and docs

**Files:**
- Modify: `requirements_rag.txt`
- Modify: `README.md`
- Test: `interactive_seminar/tests/test_rag_notebook.py`

**Step 1: Write the failing test**

Extend tests to assert `requirements_rag.txt` no longer includes `playwright`.

**Step 2: Run test to verify it fails**

Run: `python -m pytest interactive_seminar/tests/test_rag_notebook.py -q`
Expected: FAIL until requirements are aligned.

**Step 3: Write minimal implementation**

- remove `playwright` from `requirements_rag.txt`
- update README commands if they still mention Playwright setup for the RAG notebook

**Step 4: Run tests and smoke checks**

Run:
- `python -m pytest interactive_seminar/tests -q`
- notebook syntax smoke script

Expected: all tests pass and code cells compile.

**Step 5: Commit**

```bash
git add requirements_rag.txt README.md interactive_seminar/tests/test_rag_notebook.py
git commit -m "docs: align rag parser setup"
```
