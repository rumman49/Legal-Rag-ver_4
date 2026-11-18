"""LangChain document loaders for PDF, DOCX, MD, and TXT files."""
from pathlib import Path
from typing import List
from langchain_core.documents import Document
from langchain_community.document_loaders import (
    PDFPlumberLoader,
    PyPDFLoader,
    TextLoader,
    Docx2txtLoader,
)


def load_langchain_document(file_path: str | Path) -> List[Document]:
    """Loads document using standard LangChain loaders and returns List[Document]."""
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"File not found: {path}")

    suffix = path.suffix.lower()

    file_type = "txt"
    if suffix == ".md":
        file_type = "markdown"
        loader = TextLoader(str(path), encoding="utf-8", autodetect_encoding=True)
        docs = loader.load()
    elif suffix == ".txt":
        file_type = "txt"
        loader = TextLoader(str(path), encoding="utf-8", autodetect_encoding=True)
        docs = loader.load()
    elif suffix == ".docx":
        file_type = "docx"
        loader = Docx2txtLoader(str(path))
        docs = loader.load()
    elif suffix == ".pdf":
        file_type = "pdf"
        try:
            loader = PDFPlumberLoader(str(path))
            docs = loader.load()
        except Exception:
            loader = PyPDFLoader(str(path))
            docs = loader.load()
    else:
        raise ValueError(f"Unsupported file format: {suffix}. Allowed: .pdf, .docx, .md, .txt")

    # Standardize metadata source, document name, and file type
    for doc in docs:
        doc.metadata["source"] = str(path)
        doc.metadata["document_name"] = path.name
        doc.metadata["file_type"] = file_type

    return docs
