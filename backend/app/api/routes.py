"""FastAPI API Routes for Ask, Sessions, Documents, and Stats."""
import json
import logging
from pathlib import Path
from typing import List, Optional, Any
from fastapi import APIRouter, Depends, UploadFile, File, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.db_service import (
    create_session,
    get_all_sessions,
    get_session_messages,
    save_message,
    delete_session,
    delete_all_sessions,
    clear_session_messages
)
from app.core.corpus_service import get_corpus_meter_stats, invalidate_corpus_cache
from app.rag.hybrid_retriever import LegalHybridRetriever, reset_retrieval_caches
from app.rag.rag_pipeline import run_legal_rag_chain, contextualize_query
from app.rag.chroma_manager import get_vectorstore
from app.ingestion.pipeline import ingest_file

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api")

ALLOWED_UPLOAD_EXTENSIONS = {".pdf", ".docx", ".md", ".txt"}
MAX_UPLOAD_BYTES = 50 * 1024 * 1024

# Lazy-loaded vectorstore & retriever singletons
_vectorstore = None
_retriever = None

def get_active_vectorstore():
    global _vectorstore
    if _vectorstore is None:
        _vectorstore = get_vectorstore()
    return _vectorstore


def get_active_retriever():
    global _retriever
    if _retriever is None:
        vs = get_active_vectorstore()
        _retriever = LegalHybridRetriever(vectorstore=vs, k=10)
    return _retriever



class AskRequest(BaseModel):
    query: Optional[str] = None
    question: Optional[str] = None
    session_id: Optional[str] = None
    provider: Optional[str] = None
    model_name: Optional[str] = None
    model: Optional[str] = None
    history: Optional[List[Any]] = None


class SessionCreateRequest(BaseModel):
    id: Optional[str] = None
    title: Optional[str] = "New Legal Query"
    model: Optional[str] = "groq"


@router.post("/ask")
def ask_legal_question(req: AskRequest, db: Session = Depends(get_db)):
    """Processes user legal question, runs Hybrid RAG chain, persists history, returns answer + citations."""
    user_query = (req.query or req.question or "").strip()
    if not user_query:
        raise HTTPException(status_code=400, detail="Query string cannot be empty.")

    selected_provider = (req.provider or req.model or "groq").lower()
    raw_model = req.model_name or req.model
    selected_model_name = raw_model if (raw_model and raw_model.lower() not in ["groq", "gemini", "ollama"]) else None

    # Retrieve history from request or session
    chat_history = req.history or []
    if not chat_history and req.session_id:
        try:
            db_msgs = get_session_messages(db, req.session_id)
            chat_history = [{"role": m.role, "content": m.content} for m in db_msgs]
        except Exception:
            chat_history = []

    try:
        # Contextualize query for retrieval if it's a conversational follow-up
        retrieval_query = user_query
        if chat_history:
            try:
                retrieval_query = contextualize_query(user_query, chat_history=chat_history, provider=selected_provider)
            except Exception:
                retrieval_query = user_query

        retrieved_docs = []
        try:
            retriever = get_active_retriever()
            retrieved_docs = retriever.retrieve(retrieval_query, top_k=4)
        except Exception:
            retrieved_docs = []

        # Execute RAG Chain with context & chat history
        result = run_legal_rag_chain(
            query=user_query,
            retrieved_documents=retrieved_docs,
            provider=selected_provider,
            model_name=selected_model_name,
            chat_history=chat_history
        )

        # Session persistence. A failure is logged and the answer is still returned;
        # the session_id is left as the client sent it (no fake placeholder id).
        session_id = req.session_id
        try:
            if not session_id:
                sess = create_session(db, title=user_query[:40], model=selected_provider)
                session_id = sess.id
            else:
                create_session(db, title=user_query[:40], model=selected_provider, session_id=session_id)

            save_message(db, session_id=session_id, role="user", content=user_query)
            save_message(db, session_id=session_id, role="assistant", content=result["answer"], citations=result["citations"])
        except Exception:
            db.rollback()
            logger.exception("Failed to persist chat messages (session=%s)", session_id)

        result["session_id"] = session_id
        # Standardize return format for sources/citations
        result["sources"] = result.get("citations") or []
        return result

    except Exception:
        logger.exception("Ask pipeline failed")
        raise HTTPException(status_code=500, detail="The question could not be processed. See server logs.")



@router.get("/sessions")
def list_sessions(db: Session = Depends(get_db)):
    """Returns list of chat sessions with message counts."""
    try:
        sessions = get_all_sessions(db)
        return [
            {
                "id": s.id,
                "title": s.title,
                "model": s.model,
                "created_at": s.created_at.isoformat(),
                "message_count": len(s.messages) if s.messages else 0
            }
            for s in sessions
        ]
    except Exception:
        logger.exception("Failed to list sessions")
        raise HTTPException(status_code=503, detail="Chat history database is unavailable.")


@router.post("/sessions")
def create_new_session(req: SessionCreateRequest, db: Session = Depends(get_db)):
    """Creates a new session with an optional user-defined ID."""
    try:
        sess = create_session(
            db,
            title=req.title or "New Legal Query",
            model=req.model or "groq",
            session_id=req.id
        )
        return {
            "id": sess.id,
            "title": sess.title,
            "model": sess.model,
            "created_at": sess.created_at.isoformat(),
            "message_count": len(sess.messages) if sess.messages else 0
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create session: {e}")


@router.delete("/sessions/{session_id}")
def delete_chat_session(session_id: str, db: Session = Depends(get_db)):
    """Deletes a single chat session and all its messages."""
    success = delete_session(db, session_id)
    if not success:
        raise HTTPException(status_code=404, detail="Session not found")
    return {"status": "deleted", "id": session_id}


@router.delete("/sessions/{session_id}/messages")
def clear_chat_session_messages(session_id: str, db: Session = Depends(get_db)):
    """Clears all messages inside a specific session."""
    clear_session_messages(db, session_id)
    return {"status": "cleared", "id": session_id}


@router.delete("/sessions")
def delete_all_chat_sessions(db: Session = Depends(get_db)):
    """Deletes all sessions and messages across the application."""
    count = delete_all_sessions(db)
    return {"status": "all_deleted", "count": count}


@router.get("/sessions/{session_id}/messages")
def get_messages(session_id: str, db: Session = Depends(get_db)):
    """Returns chat history for a given session."""
    try:
        messages = get_session_messages(db, session_id)
        return [
            {
                "id": m.id,
                "role": m.role,
                "content": m.content,
                "citations": json.loads(m.sources_json) if m.sources_json else [],
                "created_at": m.created_at.isoformat()
            }
            for m in messages
        ]
    except Exception:
        logger.exception("Failed to load messages (session=%s)", session_id)
        raise HTTPException(status_code=503, detail="Chat history database is unavailable.")


@router.post("/documents/upload")
async def upload_document(file: UploadFile = File(...)):
    """Uploads and indexes ad-hoc legal document into vector store."""
    # Strip any directory parts from the client-supplied name (blocks path traversal)
    safe_name = Path(file.filename or "").name
    if not safe_name or Path(safe_name).suffix.lower() not in ALLOWED_UPLOAD_EXTENSIONS:
        raise HTTPException(status_code=400, detail="Unsupported file type. Allowed: PDF, DOCX, MD, TXT.")

    content = await file.read(MAX_UPLOAD_BYTES + 1)
    if len(content) > MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=413, detail="File is larger than 50 MB.")

    upload_dir = Path(__file__).resolve().parents[3] / "data" / "raw"
    upload_dir.mkdir(parents=True, exist_ok=True)
    file_path = upload_dir / safe_name
    file_path.write_bytes(content)

    try:
        docs = ingest_file(file_path)
        vs = get_active_vectorstore()

        texts = [d.page_content for d in docs]
        metadatas = [d.metadata for d in docs]
        vs.add_texts(texts=texts, metadatas=metadatas)

        # Invalidate stats cache so meter immediately reflects the new document & chunks
        invalidate_corpus_cache()
        # The BM25 index is built from the corpus, so it must be rebuilt to see the new chunks
        reset_retrieval_caches()
    except Exception:
        logger.exception("Document ingestion failed (file=%s)", safe_name)
        raise HTTPException(status_code=500, detail="Document ingestion failed. See server logs.")

    return {
        "status": "success",
        "filename": safe_name,
        "chunks_added": len(docs)
    }


@router.get("/documents/stats")
def get_corpus_stats(refresh: bool = False):
    """Returns comprehensive corpus meter statistics (documents, chunks, parent/child split, top docs)."""
    try:
        return get_corpus_meter_stats(force_refresh=refresh)
    except Exception as e:
        return {
            "status": "error",
            "error": str(e),
            "total_documents": 0,
            "total_chunks": 0,
            "child_chunks": 0,
            "parent_chunks": 0,
            "child_percentage": 0.0,
            "parent_percentage": 0.0,
            "avg_chunks_per_doc": 0,
            "vector_store": "ChromaDB"
        }

