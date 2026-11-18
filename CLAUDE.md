# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

Project conventions (read-only Chroma SQLite, MySQL must be running, Groq as the dev default) are in `AGENTS.md`. This file covers commands and the cross-file architecture.

## Commands

Run everything from the repo root. The root `.venv` has the installed dependencies, not `backend/.venv`.

- Start the app (MySQL must be up first): `uv run main.py`. This starts uvicorn on `0.0.0.0:8000` with reload enabled, watching `backend/app/`. The UI is served at `/`, the OpenAPI docs at `/docs`.
- Smoke-test the query path: `curl -X POST localhost:8000/api/ask -H "Content-Type: application/json" -d "{\"query\":\"What is Article 44?\"}"`
- Dependencies are declared in `backend/pyproject.toml`. The repo root has no pyproject.
- Config is read from `backend/.env` by `backend/app/core/config.py`. Do not print its values. The keys that matter are `GROQ_API_KEY`, `DEFAULT_LLM_PROVIDER`, and the `MYSQL_*` group.
- First startup downloads the embedding model into `data/models` and the FlashRank reranker into `data/cache`. A slow first start is expected.
- There is no build step, lint or format config, or test suite for the application code. The only `test_*.py` files live under `.agents/skills/*/scripts/tests` and belong to the BMad skills, not the app. So there is no single-test command for the app.

## Architecture

The whole system is one FastAPI process. Start with `main.py`, which does three things:
- Puts `backend/` on `sys.path`, so every module is imported as `app.*`.
- Mounts `app.api.routes.router` under `/api` and serves `static/`.
- On startup, calls `init_db()`, then pre-warms the embeddings, the Chroma vectorstore, and the reranker. Pre-warm errors are printed, not raised.

Process-wide singletons (the `get_*` functions in `rag/chroma_manager.py` and `rag/reranker.py`, plus `_vectorstore` and `_retriever` in `routes.py`) hold the models and the retriever for the life of the process.

### Query path: `POST /api/ask`

1. History comes from the request body or, if a `session_id` is given, from MySQL.
2. If there is history, `contextualize_query` (`rag/rag_pipeline.py`) rewrites the follow-up into a standalone retrieval query.
3. `LegalHybridRetriever.retrieve` (`rag/hybrid_retriever.py`) routes on the parsed query:
   - `rag/legal_refs.py` is the single source for statute references and act aliases (BNS, BNSS, BSA, IPC, CrPC, CPC, IEA, NI, Constitution, Hindi forms). It parses `section 103 BNS`, `BNS 103`, `103 of the BNS`, `Sections 103 and 104`, `Article 21(1)`, `Order 7 rule 11`, and `धारा 103`. `extract_references` is also used by follow-up rewriting in `rag_pipeline.py`.
   - A reference with a named act is answered only from that act's provision, via a read-only SQLite lookup against Chroma's `chroma.sqlite3`. If the act isn't indexed (BNSS today), `law_mapping_service.lookup_section` gives the old-law section (BNSS 173 → CrPC 154). If nothing matches, the function returns `[]` and never substitutes another act.
   - A reference with no act is a ranking boost only.
   - Everything else runs vector search and BM25 (`rag/bm25_index.py`, a compact in-memory index over parent sections, built lazily or at startup). The two are fused with reciprocal rank fusion, restricted to any strongly named act, then reranked by FlashRank.
4. `run_legal_rag_chain` (`rag/rag_pipeline.py`) builds the answer:
   - Greetings and identity questions return canned replies without retrieval or an LLM call.
   - If retrieval returned nothing, it returns a fixed decline message and makes no LLM call. This is the gate that keeps the model from answering without statutory context.
   - Otherwise it builds a prompt from a language-aware system prompt, the last 6 history turns, and the retrieved context. It uses only the primary provider (`DEFAULT_LLM_PROVIDER`) unless `LLM_FALLBACK_PROVIDERS` in `.env` lists fallbacks (comma-separated, tried in order). The requested model name applies only to the primary provider.
   - It builds the `citations` list from document metadata, mapping raw scores to display percentages.
5. The route writes the user and assistant messages to MySQL (`core/db_service.py`).

### Ingestion path: `POST /api/documents/upload`

The upload is saved to `data/raw/`. Then `ingestion/pipeline.py` runs:
- `loaders.py` loads PDF, DOCX, MD, or TXT.
- `metadata_extractor.LegalHierarchyParser` recovers the Act, Chapter, Section, and Article hierarchy.
- `chunker.HierarchicalChunker` emits parent and child Documents that are linked by `parent_id`.
- The route calls `vectorstore.add_texts()` and then `invalidate_corpus_cache()` (`core/corpus_service.py`).

This is the only ingestion entry point. There is no CLI script.

### State

- ChromaDB persists under `data/chromadb`, collection `indian_legal_corpus`. All writes go through `add_texts()`.
- MySQL holds chat sessions and messages (`core/database.py`, `core/db_service.py`, `core/models.py`).
- `core/corpus_service.py` caches corpus stats for `/api/documents/stats`.

### Gotchas

- The BM25 index covers parent chunks only and is rebuilt after `/api/documents/upload` (`reset_retrieval_caches()`). The first build takes about 25 seconds at the current corpus size, and startup pre-warms it.
- Plain-language queries rerank about 30 candidates on CPU, so they take several seconds. Section-named queries do not reach the reranker.
- `query_exact_provisions_sqlite` opens Chroma's SQLite file with `mode=ro&immutable=1` only. There is no writable fallback.
- `/api/ask` swallows MySQL persistence errors and returns `session_fallback` as the session id. `AGENTS.md` says the in-memory fallback is a problem to fix, not an acceptable state.
- Ingestion stores children and parents as separate documents, so retrieval results can contain both. Dedup keys on `parent_id`, `chunk_type`, and the chunk indices.
- `data/mapping.csv` and `data/mappings/mapping.csv` are unused. Only `data/mappings/transition_mappings.csv` is read.
- **BNSS is not in the vector store** (no `act_name` matching "Nagarik" in `chroma.sqlite3`). BNS, BSA, IPC, CrPC, and the Constitution are present. Queries about BNSS sections get the old-law mapping plus an honest "not in context" answer until BNSS is ingested.
- When a section or article is named, `retrieve()` returns only the matching provisions (deduped to one parent chunk per section). It does not pad with unrelated vector hits. Exact-marking requires the act named in the query.
