<!-- bmad:context -->
<!-- Verified 2026-10-14 against 7a15aba. Managed by bmad-project-context; edits inside this block are replaced on refresh. Keep anything you want preserved outside the markers. -->

## Legal-Rag-ver_4

Multilingual Legal RAG system for Indian law. FastAPI + LangChain + ChromaDB + Sentence-Transformers + MySQL, Python 3.12 managed via uv.

## Where things are

- Entry point: `main.py` (repo root) — path-hacks `backend/` onto `sys.path` and mounts `backend/app/api/routes.py`.
- RAG pipeline: `backend/app/rag/` — `chroma_manager.py` (vectorstore + embeddings), `hybrid_retriever.py` (BM25 + vector + exact-provision SQLite lookup + rerank), `reranker.py`, `rag_pipeline.py` (chain assembly).
- Ingestion: `backend/app/ingestion/pipeline.py` (parent/child hierarchical chunking). Only reachable via `POST /api/documents/upload` — no standalone ingestion script exists.
- Statutory transition mappings (IPC->BNS, CrPC->BNSS, IEA->BSA): `backend/app/rag/law_mapping_service.py` loads `data/mappings/transition_mappings.csv`. `data/mapping.csv` and `data/mappings/mapping.csv` are unused leftovers the candidate-path lookup never reaches.

## Running and verifying

- Run from repo root: `uv run main.py` — the root `.venv` has the installed deps, not `backend/.venv`.
- Start MySQL before running. `init_db()` only logs a warning and silently falls back to in-memory session history if MySQL is unreachable — treat that warning as a problem to fix, not an acceptable fallback.
- First run downloads the HuggingFace embedding model and FlashRank reranker into `data/models` / `data/cache` and keeps them there; a slow first startup is expected, later ones are not a bug.
- Default to the `groq` provider for local dev/testing (`DEFAULT_LLM_PROVIDER`); requires `GROQ_API_KEY` in `backend/.env`.

## Conventions that differ from defaults

- ChromaDB's underlying SQLite file is queried directly, read-only, for exact section/article lookups (`hybrid_retriever.py`). All writes go through `vectorstore.add_texts()` — never touch the SQLite file directly.

<!-- /bmad:context -->
