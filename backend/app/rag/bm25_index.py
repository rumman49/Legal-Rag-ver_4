"""In-memory BM25 over parent (full-section) chunks, stored as compact arrays.

rank_bm25 keeps one dict per document, which costs roughly a gigabyte at this corpus size (~72k parents,
~137 MB of text). Postings here are two typed arrays per term, so the index stays in the tens of megabytes.
"""
import heapq
import logging
import math
import re
import threading
from array import array
from collections import Counter
from typing import Dict, List, Optional, Tuple

from langchain_core.documents import Document

logger = logging.getLogger(__name__)

TOKEN_RE = re.compile(r"[a-z0-9]+|[ऀ-ॿ]+")
STOPWORDS = frozenset(
    "a an and are as at be been by for from has have had in is it its of on or shall may any such "
    "the to was were will with who whoever which this that these those under if not".split()
)
# Terms in more than this share of documents carry almost no signal and make scoring slow.
MAX_DF_SHARE = 0.5


def tokenize(text: str) -> List[str]:
    """Lowercase word tokens. Keeps section numbers and suffixes such as '65b' and '103a'."""
    out = []
    for m in TOKEN_RE.finditer(text.lower()):
        tok = m.group(0)
        if tok in STOPWORDS:
            continue
        if len(tok) > 1 or tok.isdigit():
            out.append(tok)
    return out


class SparseBM25:
    def __init__(self, k1: float = 1.5, b: float = 0.75):
        self.k1 = k1
        self.b = b
        self.vocab: Dict[str, int] = {}
        self.post_docs: List[array] = []
        self.post_tf: List[array] = []
        self.doc_len = array("I")
        self.avgdl = 1.0
        self.docs: List[Document] = []

    def build(self, docs: List[Document]) -> None:
        self.docs = docs
        for doc_id, doc in enumerate(docs):
            tokens = tokenize(doc.page_content)
            self.doc_len.append(len(tokens))
            for term, tf in Counter(tokens).items():
                tid = self.vocab.get(term)
                if tid is None:
                    tid = len(self.vocab)
                    self.vocab[term] = tid
                    self.post_docs.append(array("I"))
                    self.post_tf.append(array("H"))
                self.post_docs[tid].append(doc_id)
                self.post_tf[tid].append(min(tf, 65535))
        self.avgdl = (sum(self.doc_len) / len(self.doc_len)) if self.doc_len else 1.0

    def search(self, query: str, k: int = 40) -> List[Tuple[int, float]]:
        """Returns (doc_index, score) for the top-k documents."""
        n = len(self.doc_len)
        scores: Dict[int, float] = {}
        for term in set(tokenize(query)):
            tid = self.vocab.get(term)
            if tid is None:
                continue
            postings = self.post_docs[tid]
            df = len(postings)
            if df > MAX_DF_SHARE * n:
                continue
            idf = math.log(1 + (n - df + 0.5) / (df + 0.5))
            for doc_id, tf in zip(postings, self.post_tf[tid]):
                dl = self.doc_len[doc_id]
                norm = tf + self.k1 * (1 - self.b + self.b * dl / self.avgdl)
                scores[doc_id] = scores.get(doc_id, 0.0) + idf * tf * (self.k1 + 1) / norm
        return heapq.nlargest(k, scores.items(), key=lambda kv: kv[1])


def load_parent_documents(vectorstore) -> List[Document]:
    """Reads every parent chunk (full section text) from the Chroma collection in pages."""
    collection = vectorstore._collection
    out: List[Document] = []
    offset, page = 0, 5000
    while True:
        res = collection.get(where={"chunk_type": "parent"}, include=["documents", "metadatas"],
                             limit=page, offset=offset)
        texts = res.get("documents") or []
        if not texts:
            break
        for text, meta in zip(texts, res.get("metadatas") or []):
            out.append(Document(page_content=text or "", metadata=meta or {}))
        offset += len(texts)
        if len(texts) < page:
            break
    return out


_lock = threading.Lock()
_index: Optional[SparseBM25] = None


def get_bm25_index(vectorstore) -> SparseBM25:
    """Process-wide BM25 index, built on first use (about a minute at full corpus size)."""
    global _index
    with _lock:
        if _index is None:
            docs = load_parent_documents(vectorstore)
            index = SparseBM25()
            index.build(docs)
            _index = index
            logger.info(f"[BM25] Indexed {len(docs)} parent sections, {len(index.vocab)} terms.")
        return _index


def reset_bm25_index() -> None:
    """Drops the cached index so the next query rebuilds it, e.g. after new documents are ingested."""
    global _index
    with _lock:
        _index = None
