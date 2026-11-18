"""Legal Document Reranker using FlashRank or CrossEncoder."""
from pathlib import Path
from typing import List
from langchain_core.documents import Document
from flashrank import Ranker, RerankRequest
from app.core.config import settings


_shared_reranker = None


def get_shared_reranker():
    """Returns singleton instance of LegalReranker to avoid expensive reload overhead."""
    global _shared_reranker
    if _shared_reranker is None:
        _shared_reranker = LegalReranker()
    return _shared_reranker


class LegalReranker:
    """Reranks retrieved legal context using FlashRank cross-encoder models."""

    def __init__(self, model_name: str = "ms-marco-MiniLM-L-12-v2"):
        cache_dir = Path(settings.LOCAL_CACHE_DIRECTORY).resolve()
        cache_dir.mkdir(parents=True, exist_ok=True)
        self.ranker = Ranker(model_name=model_name, cache_dir=str(cache_dir))

    def rerank(self, query: str, documents: List[Document], top_k: int = 4) -> List[Document]:
        """Reranks documents based on semantic relevance to the query."""
        if not documents:
            return []

        passages = [
            {"id": str(idx), "text": doc.page_content, "metadata": doc.metadata}
            for idx, doc in enumerate(documents)
        ]

        rerank_request = RerankRequest(query=query, passages=passages)
        results = self.ranker.rerank(rerank_request)

        reranked_docs: List[Document] = []
        for res in results[:top_k]:
            doc_idx = int(res["id"])
            original_doc = documents[doc_idx]
            original_doc.metadata["rerank_score"] = res.get("score", 0.0)
            reranked_docs.append(original_doc)

        return reranked_docs
