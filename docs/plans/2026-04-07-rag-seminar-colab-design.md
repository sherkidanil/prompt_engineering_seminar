# RAG Seminar Colab Design

**Date:** 2026-04-07

## Goal

Make `RAG_seminar.ipynb` install and run cleanly in Google Colab using current package structure and imports, without rewriting the seminar into a different architecture.

## Current Problems

- The notebook installs `gigachain`, which is no longer the right package for the current LangChain/GigaChat split ecosystem.
- Install cells pin `pydantic==1.10.13`, which conflicts with the current `gigachat` SDK line.
- Several imports use deprecated or removed paths such as `langchain.embeddings`, `langchain.text_splitter`, and `langchain.chat_models.gigachat`.
- Some examples still use deprecated invocation style such as `llm(...)` and `get_relevant_documents(...)`.
- Colab-specific setup is incomplete: browser install, PDF dependencies, and package installation order are not explicit enough.

## Chosen Approach

Use the current split-package stack while preserving the seminar flow:

- `langchain-classic` for chain APIs still used by the notebook
- `langchain-community` for loaders, vector stores, and retrievers
- `langchain-huggingface` for embeddings
- `langchain-gigachat` for the GigaChat LangChain integration
- `langchain-text-splitters` for text splitting
- `gigachat` SDK for direct API support

Notebook cells will be updated in place so that the seminar remains recognizable and runnable in Colab.

## Alternatives Considered

### 1. Full rewrite to the newest LangChain 1.x style

Pros:
- Most future-facing API surface

Cons:
- Unnecessary churn for a teaching notebook
- Higher risk of semantic drift from the current seminar
- Larger review surface

Rejected.

### 2. Minimal patching with old imports left in place

Pros:
- Fastest edit count

Cons:
- Still brittle against current package releases
- Does not actually solve the Colab compatibility problem

Rejected.

### 3. Current-compatible split packages with targeted API updates

Pros:
- Keeps the notebook structure intact
- Matches the modern package layout
- Lowest-risk path to a runnable Colab notebook

Chosen.

## Scope

### In scope

- Update install cells to current package names and Colab-friendly commands
- Update notebook imports to current package/module locations
- Replace deprecated invocation patterns that are likely to break or warn heavily
- Add notebook-structure tests that assert the intended install/import contract
- Align `requirements_rag.txt` with the notebook dependency stack if needed for repo consistency

### Out of scope

- Rewriting the seminar content or exercise flow
- Converting the notebook into a standalone app
- Replacing all `RetrievalQA`/chain abstractions with a different orchestration style
- Guaranteeing third-party sites always respond inside Colab runtime limits

## Testing Strategy

- Add tests that parse `RAG_seminar.ipynb` and assert required package names/import paths
- Assert old package names and deprecated paths are removed from code cells
- Run syntax compilation over code cells that were changed structurally where practical
- Perform targeted smoke verification by installing the updated dependency set and importing the modules used by the notebook

## Risks

- Colab runtime package ecosystem can drift again later; exact pins reduce drift but increase maintenance cost.
- `playwright` and document parsing dependencies remain the most environment-sensitive parts of the notebook.
- External content loaders may still fail for network reasons unrelated to code correctness.
