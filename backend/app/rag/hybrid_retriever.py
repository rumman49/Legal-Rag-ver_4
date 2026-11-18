"""Statutory retrieval: exact provision lookup, vector + BM25 fusion (reciprocal rank), FlashRank rerank.

Routing:
- A section/article named together with its act is answered only from that provision. The read-only
  Chroma SQLite lookup is exact and fast. If the act is not in the corpus (e.g. BNSS), the transition
  mapping gives the old-law equivalent (e.g. CrPC 154). If nothing matches, nothing is returned.
  Other acts are never substituted, since that is how wrong-statute answers happen.
- A section/article named without an act is a candidate boost, not a pin: the reranker decides.
- Everything else goes through vector + BM25 fused by reciprocal rank (RRF), restricted to any strongly
  named act, then reranked.

ChromaDB writes stay in vectorstore.add_texts(); this module only reads the SQLite file.
"""
import logging
import sqlite3
from pathlib import Path
from typing import Dict, List, Optional

from langchain_core.documents import Document

from app.core.corpus_service import find_chroma_sqlite_path
from app.rag.bm25_index import get_bm25_index, reset_bm25_index
from app.rag.legal_refs import extract_references, strong_acts
from app.rag.reranker import get_shared_reranker

logger = logging.getLogger(__name__)

RRF_K = 60            # standard reciprocal-rank-fusion constant
CANDIDATE_POOL = 40   # per-retriever candidates before fusion
RERANK_POOL = 30      # fused candidates passed to the reranker
EXACT_POOL_CAP = 12   # cap on unpinned exact hits so they cannot crowd out semantic candidates
NEW_LAW_CODES = {"BNS", "BNSS", "BSA"}


def provision_key(meta: Dict) -> str:
    """Identifies the provision a chunk belongs to, so parent and child chunks of one section collapse."""
    act = (meta.get("act_name") or meta.get("document_name") or "").lower()
    ref = (
        meta.get("section_no") or meta.get("article_no") or meta.get("rule_no")
        or meta.get("regulation_no") or meta.get("order_no")
    )
    if ref:
        return f"{act}|{ref}"
    return f"{act}|{meta.get('parent_id') or meta.get('legal_reference') or ''}"


def dedupe_provisions(docs: List[Document]) -> List[Document]:
    """One document per provision, preferring the parent (full-text) chunk, keeping first-seen order."""
    best: Dict[str, Document] = {}
    order: List[str] = []
    for d in docs:
        key = provision_key(d.metadata)
        if key not in best:
            best[key] = d
            order.append(key)
        elif d.metadata.get("chunk_type") == "parent" and best[key].metadata.get("chunk_type") != "parent":
            best[key] = d
    return [best[k] for k in order]


def _open_chroma_sqlite(path: Path) -> sqlite3.Connection:
    """Opens Chroma's SQLite file strictly read-only."""
    return sqlite3.connect(f"file:{path.as_posix()}?mode=ro&immutable=1", uri=True, timeout=3.0)


def reset_retrieval_caches() -> None:
    """Call after ingesting documents so the BM25 index is rebuilt from the updated corpus."""
    reset_bm25_index()


def query_exact_provisions_sqlite(
    section_no: Optional[str] = None,
    article_no: Optional[str] = None,
    rule_no: Optional[str] = None,
    regulation_no: Optional[str] = None,
    act_needle: Optional[str] = None,
    limit: int = 12,
) -> List[Document]:
    """Exact provision lookup in Chroma's SQLite metadata. Parent (full-text) chunks come first."""
    path = find_chroma_sqlite_path()
    if not path:
        return []

    criteria = [
        ("section_no", section_no), ("article_no", article_no),
        ("rule_no", rule_no), ("regulation_no", regulation_no),
    ]
    criteria = [(k, str(v)) for k, v in criteria if v]
    if not criteria:
        return []

    docs: List[Document] = []
    try:
        conn = _open_chroma_sqlite(path)
        try:
            cur = conn.cursor()
            chunk_ids: List[int] = []
            for key, val in criteria:
                if act_needle:
                    cur.execute(
                        """SELECT e1.id FROM embedding_metadata e1
                           JOIN embedding_metadata e2 ON e2.id = e1.id
                           WHERE e1.key = ? AND e1.string_value = ?
                             AND e2.key = 'act_name' AND e2.string_value LIKE ?
                           LIMIT ?""",
                        (key, val, f"%{act_needle}%", limit),
                    )
                else:
                    cur.execute(
                        "SELECT id FROM embedding_metadata WHERE key = ? AND string_value = ? LIMIT ?",
                        (key, val, limit),
                    )
                chunk_ids.extend(r[0] for r in cur.fetchall())

            for chunk_id in dict.fromkeys(chunk_ids):
                meta = dict(cur.execute(
                    "SELECT key, string_value FROM embedding_metadata WHERE id = ?", (chunk_id,)
                ).fetchall())
                text = meta.pop("chroma:document", "")
                if text:
                    docs.append(Document(page_content=text, metadata=meta))
        finally:
            conn.close()
    except Exception as e:
        logger.warning(f"Exact provision lookup failed: {e}")
        return []

    docs.sort(key=lambda d: d.metadata.get("chunk_type") != "parent")  # stable: parents first
    return docs


class LegalHybridRetriever:
    """Routes a query to exact lookup, or to fused vector + BM25 retrieval followed by reranking."""

    def __init__(self, vectorstore, documents: Optional[List[Document]] = None, k: int = 10):
        # `documents` is accepted for backward compatibility; BM25 is built from the corpus itself.
        self.vectorstore = vectorstore
        self.k = k
        self.reranker = get_shared_reranker()

    def retrieve(self, query: str, top_k: int = 4) -> List[Document]:
        refs = extract_references(query)
        pinned, pool = self._exact_candidates(query, refs)

        if any(r.get("act_needle") for r in refs):
            # The user named a provision and its act: answer from that provision or nothing.
            if pinned:
                return dedupe_provisions(pinned)[:top_k]
            logger.info(f"No provision found for named reference(s) {[r['raw'] for r in refs]}; declining.")
            return []

        return self._hybrid(query, top_k, pool)

    # ----- exact / structured candidates -------------------------------------------------------

    def _exact_candidates(self, query: str, refs: List[Dict]):
        """Returns (pinned, pool). Pinned docs answer a named act's provision; pool docs only boost ranking."""
        pinned: List[Document] = []
        pool: List[Document] = []

        for ref in refs:
            kwargs = self._ref_kwargs(ref)
            if not kwargs:
                continue
            needle = ref.get("act_needle")
            if needle:
                found = query_exact_provisions_sqlite(act_needle=needle, **kwargs)
                if not found and ref["type"] == "section":
                    found = self._mapped_old_law(ref)
                for d in found:
                    d.metadata["is_exact_match"] = True
                    d.metadata["rerank_score"] = 0.99
                pinned.extend(found)
            else:
                pool.extend(query_exact_provisions_sqlite(**kwargs, limit=6))

        # Offense-catalog bridge for plain-language crime queries ("murder", "cheating"): boost only.
        try:
            from app.rag.law_mapping_service import get_law_mapping_service
            for om in get_law_mapping_service().match_offense_catalog(query):
                for sec in om.get("new_sections", [])[:2]:
                    pool.extend(query_exact_provisions_sqlite(section_no=sec, act_needle=om["new_act"], limit=2))
                for sec in om.get("old_sections", [])[:1]:
                    pool.extend(query_exact_provisions_sqlite(section_no=sec, act_needle=om["old_act"], limit=2))
        except Exception as e:
            logger.warning(f"Offense catalog lookup error: {e}")

        return dedupe_provisions(pinned), dedupe_provisions(pool)[:EXACT_POOL_CAP]

    @staticmethod
    def _ref_kwargs(ref: Dict) -> Dict:
        if ref["type"] == "section" and ref.get("section_no"):
            return {"section_no": ref["section_no"]}
        if ref["type"] == "article" and ref.get("article_no"):
            return {"article_no": ref["article_no"]}
        if ref["type"] == "rule" and ref.get("rule_no"):
            return {"rule_no": ref["rule_no"]}
        if ref["type"] == "regulation" and ref.get("regulation_no"):
            return {"regulation_no": ref["regulation_no"]}
        return {}

    def _mapped_old_law(self, ref: Dict) -> List[Document]:
        """For a new-law section whose act is not indexed, returns the old-law section it replaced."""
        code = (ref.get("act_code") or "").upper()
        if code not in NEW_LAW_CODES:
            return []
        try:
            from app.rag.law_mapping_service import get_law_mapping_service
            row = get_law_mapping_service().lookup_section(code.lower(), ref["section_no"])
        except Exception as e:
            logger.warning(f"Transition mapping lookup failed: {e}")
            return []
        if not row or str(row.get("to_section")) != str(ref["section_no"]):
            return []
        if (row.get("relation") or "none").lower() == "none":
            return []
        old_acts = strong_acts(row.get("from_act", ""))
        if not old_acts or not row.get("from_section"):
            return []
        logger.info(f"{code} {ref['section_no']} not indexed; using old-law {old_acts[0].code} {row['from_section']}.")
        return query_exact_provisions_sqlite(section_no=str(row["from_section"]), act_needle=old_acts[0].needle)

    # ----- semantic hybrid ----------------------------------------------------------------------

    def _hybrid(self, query: str, top_k: int, pool: List[Document]) -> List[Document]:
        vector_docs = self.vectorstore.similarity_search(query, k=CANDIDATE_POOL)

        bm25 = get_bm25_index(self.vectorstore)
        bm25_docs = [bm25.docs[i] for i, _ in bm25.search(query, k=CANDIDATE_POOL)]

        fused: Dict[str, float] = {}
        rep: Dict[str, Document] = {}
        for ranked in (pool, vector_docs, bm25_docs):
            for rank, doc in enumerate(ranked, 1):
                key = provision_key(doc.metadata) or doc.page_content[:100]
                fused[key] = fused.get(key, 0.0) + 1.0 / (RRF_K + rank)
                current = rep.get(key)
                if current is None or (
                    doc.metadata.get("chunk_type") == "parent" and current.metadata.get("chunk_type") != "parent"
                ):
                    rep[key] = doc

        candidates = [rep[k] for k in sorted(fused, key=fused.get, reverse=True)]

        named = strong_acts(query)
        if named:
            needles = [a.needle.lower() for a in named]
            candidates = [
                d for d in candidates
                if any(n in (d.metadata.get("act_name") or "").lower() for n in needles)
            ]
            if not candidates:
                logger.info(f"No indexed provisions for act(s) named in query: {[a.code for a in named]}.")
                return []

        # Copies, so reranker metadata writes never leak into the shared BM25 documents.
        pool_docs = [Document(page_content=d.page_content, metadata=dict(d.metadata))
                     for d in candidates[:RERANK_POOL]]
        return self.reranker.rerank(query, pool_docs, top_k=top_k)
