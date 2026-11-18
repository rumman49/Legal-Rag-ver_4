"""Unified Document Ingestion Pipeline with Hierarchical Parent/Child and Semantic Chunking."""
from pathlib import Path
from typing import List, Optional, Tuple, Any
from langchain_core.documents import Document
from app.ingestion.loaders import load_langchain_document
from app.ingestion.metadata_extractor import LegalHierarchyParser
from app.ingestion.chunker import HierarchicalChunker


def ingest_file_hierarchical(
    file_path: str | Path,
    custom_act_name: Optional[str] = None,
    embedding_model: Optional[Any] = None
) -> Tuple[List[Document], List[Document]]:
    """Ingests legal documents (PDF, DOCX, MD, TXT) and returns (parents, children) Documents linked by parent_id."""
    langchain_docs = load_langchain_document(file_path)
    all_parents: List[Document] = []
    all_children: List[Document] = []
    chunker = HierarchicalChunker(embedding_model=embedding_model)

    for doc in langchain_docs:
        doc_name = doc.metadata.get("document_name", Path(file_path).name)
        file_type = doc.metadata.get("file_type", Path(file_path).suffix.lstrip(".").lower())
        blocks = LegalHierarchyParser.parse_document_content(doc.page_content, doc_name)

        if custom_act_name:
            for b in blocks:
                b["metadata"]["act_name"] = custom_act_name

        parents, children = chunker.chunk_blocks(blocks, embedding_model=embedding_model)
        for p in parents:
            p.metadata["source"] = doc.metadata.get("source", str(file_path))
            p.metadata["document_name"] = doc_name
            p.metadata["file_type"] = file_type
            all_parents.append(p)

        for c in children:
            c.metadata["source"] = doc.metadata.get("source", str(file_path))
            c.metadata["document_name"] = doc_name
            c.metadata["file_type"] = file_type
            all_children.append(c)

    return all_parents, all_children


def ingest_file(
    file_path: str | Path,
    custom_act_name: Optional[str] = None,
    embedding_model: Optional[Any] = None
) -> List[Document]:
    """Ingests file and returns all chunks (children + parents)."""
    parents, children = ingest_file_hierarchical(file_path, custom_act_name, embedding_model=embedding_model)
    return children + parents
