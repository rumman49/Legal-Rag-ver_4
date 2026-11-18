"""Service to inspect and meter ChromaDB corpus (documents, chunks, parent/child distribution)."""
import time
import sqlite3
import logging
from pathlib import Path
from typing import Dict, Any, Optional

from app.core.config import settings

logger = logging.getLogger("corpus_service")

# In-memory cache for fast UI response
_cached_stats: Optional[Dict[str, Any]] = None
_cache_timestamp: float = 0.0
CACHE_TTL_SECONDS = 30.0


def find_chroma_sqlite_path() -> Optional[Path]:
    """Finds chroma.sqlite3 path across possible directory resolutions."""
    candidates = [
        settings.chroma_persist_path / "chroma.sqlite3",
        Path(__file__).resolve().parents[3] / "data" / "chromadb" / "chroma.sqlite3",
        Path(__file__).resolve().parents[2] / "data" / "chromadb" / "chroma.sqlite3",
    ]
    for c in candidates:
        try:
            if c.exists():
                return c.resolve()
        except Exception:
            continue
    return None


def invalidate_corpus_cache():
    """Forces cache refresh on next query (e.g., after document upload)."""
    global _cached_stats, _cache_timestamp
    _cached_stats = None
    _cache_timestamp = 0.0


def get_corpus_meter_stats(force_refresh: bool = False, limit_docs: int = 1000) -> Dict[str, Any]:
    """
    Computes precise corpus metrics: total chunks, unique documents, child vs parent
    distribution, top documents by chunk count, and database size.
    """
    global _cached_stats, _cache_timestamp

    now = time.time()
    if not force_refresh and _cached_stats is not None and (now - _cache_timestamp) < CACHE_TTL_SECONDS:
        return _cached_stats

    sqlite_path = find_chroma_sqlite_path()

    if not sqlite_path or not sqlite_path.exists():
        logger.warning(f"chroma.sqlite3 not found at {sqlite_path}. Returning fallback stats.")
        fallback = {
            "status": "empty",
            "total_documents": 0,
            "total_chunks": 0,
            "child_chunks": 0,
            "parent_chunks": 0,
            "child_percentage": 0.0,
            "parent_percentage": 0.0,
            "avg_chunks_per_doc": 0,
            "total_acts": 0,
            "db_size_mb": 0.0,
            "vector_store": "ChromaDB",
            "collection_name": settings.CHROMA_COLLECTION_NAME,
            "embedding_model": settings.EMBEDDING_MODEL_NAME.split("/")[-1],
            "embedding_dimension": 768,
            "top_documents": [],
            "last_updated": time.strftime("%Y-%m-%d %H:%M:%S")
        }
        _cached_stats = fallback
        _cache_timestamp = now
        return fallback

    conn = None
    try:
        # Use immutable=1 mode to avoid Windows file lock contention
        try:
            uri = f"file:{sqlite_path.as_posix()}?mode=ro&immutable=1"
            conn = sqlite3.connect(uri, uri=True, timeout=5.0)
        except Exception:
            conn = sqlite3.connect(str(sqlite_path), timeout=10.0)

        cur = conn.cursor()

        # 1. Total Chunks
        cur.execute("SELECT count(*) FROM embeddings")
        total_chunks = cur.fetchone()[0]

        # 2. Total Unique Documents
        cur.execute("SELECT COUNT(DISTINCT string_value) FROM embedding_metadata WHERE key = 'document_name'")
        total_documents = cur.fetchone()[0]

        # 3. Total Unique Acts
        try:
            cur.execute("SELECT COUNT(DISTINCT string_value) FROM embedding_metadata WHERE key = 'act_name'")
            total_acts = cur.fetchone()[0]
        except Exception:
            total_acts = total_documents

        # 4. Chunk Types Breakdown (child vs parent)
        child_chunks = 0
        parent_chunks = 0
        try:
            cur.execute("SELECT string_value, COUNT(*) FROM embedding_metadata WHERE key = 'chunk_type' GROUP BY string_value")
            for chunk_type, cnt in cur.fetchall():
                if chunk_type == 'child':
                    child_chunks = cnt
                elif chunk_type == 'parent':
                    parent_chunks = cnt
        except Exception as e:
            logger.warning(f"Error querying chunk_type: {e}")

        # Compute percentages
        child_pct = round((child_chunks / total_chunks * 100), 1) if total_chunks > 0 else 0.0
        parent_pct = round((parent_chunks / total_chunks * 100), 1) if total_chunks > 0 else 0.0
        avg_chunks = round(total_chunks / total_documents, 1) if total_documents > 0 else 0.0

        # 5. Top Documents with chunk counts & legal categories
        top_documents = []
        try:
            cur.execute(
                "SELECT string_value, count(*) as c FROM embedding_metadata "
                "WHERE key = 'act_name' AND string_value IS NOT NULL AND string_value != '' "
                "GROUP BY string_value ORDER BY c DESC LIMIT ?",
                (limit_docs,)
            )
            act_rows = cur.fetchall()
            if act_rows:
                for act_name, cnt in act_rows:
                    category = "Bare Act"
                    low = act_name.lower()
                    if "constitution" in low:
                        category = "Constitutional"
                    elif any(w in low for w in ["penal", "criminal", "bns", "bnss", "police", "arms"]):
                        category = "Criminal Law"
                    elif any(w in low for w in ["civil", "procedure", "evidence", "bsa", "arbitration"]):
                        category = "Civil & Procedure"
                    elif any(w in low for w in ["tax", "finance", "customs", "excise", "gst"]):
                        category = "Taxation & Finance"
                    elif any(w in low for w in ["company", "companies", "insolvency", "securities", "contract", "negotiable"]):
                        category = "Corporate Law"
                    elif any(w in low for w in ["marriage", "succession", "divorce", "family", "guardian"]):
                        category = "Family Law"
                    elif any(w in low for w in ["rule", "regulation"]):
                        category = "Rules & Regulations"

                    top_documents.append({
                        "document_name": act_name,
                        "title": act_name,
                        "category": category,
                        "pages": max(1, round(cnt / 4)),
                        "chunk_count": cnt
                    })
            else:
                cur.execute(
                    "SELECT string_value, count(*) as c FROM embedding_metadata "
                    "WHERE key = 'document_name' GROUP BY string_value ORDER BY c DESC LIMIT ?",
                    (limit_docs,)
                )
                for doc_name, cnt in cur.fetchall():
                    clean_title = doc_name.replace(".txt", "").replace(".pdf", "").replace(".docx", "").replace(".md", "").replace("_", " ")
                    top_documents.append({
                        "document_name": doc_name,
                        "title": clean_title,
                        "category": "Bare Act",
                        "pages": max(1, round(cnt / 4)),
                        "chunk_count": cnt
                    })
        except Exception as e:
            logger.warning(f"Error querying top documents: {e}")

        # 6. Database file size
        db_size_mb = 0.0
        try:
            db_size_mb = round(sqlite_path.stat().st_size / (1024 * 1024), 2)
        except Exception:
            pass

        stats = {
            "status": "active" if total_chunks > 0 else "empty",
            "total_documents": total_documents,
            "total_chunks": total_chunks,
            "child_chunks": child_chunks,
            "parent_chunks": parent_chunks,
            "child_percentage": child_pct,
            "parent_percentage": parent_pct,
            "avg_chunks_per_doc": avg_chunks,
            "total_acts": total_acts,
            "db_size_mb": db_size_mb,
            "vector_store": "ChromaDB",
            "collection_name": settings.CHROMA_COLLECTION_NAME,
            "embedding_model": settings.EMBEDDING_MODEL_NAME.split("/")[-1],
            "embedding_dimension": 768,
            "top_documents": top_documents,
            "last_updated": time.strftime("%Y-%m-%d %H:%M:%S")
        }

        _cached_stats = stats
        _cache_timestamp = now
        return stats

    except Exception as e:
        logger.error(f"Failed to read ChromaDB stats from {sqlite_path}: {e}")
        # If cache exists, return stale cache instead of failure
        if _cached_stats is not None:
            return _cached_stats
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
            "total_acts": 0,
            "db_size_mb": 0.0,
            "vector_store": "ChromaDB",
            "collection_name": settings.CHROMA_COLLECTION_NAME,
            "embedding_model": settings.EMBEDDING_MODEL_NAME.split("/")[-1],
            "embedding_dimension": 768,
            "top_documents": [],
            "last_updated": time.strftime("%Y-%m-%d %H:%M:%S")
        }
    finally:
        if conn:
            try:
                conn.close()
            except Exception:
                pass
