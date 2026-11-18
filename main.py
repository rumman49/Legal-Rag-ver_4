"""Legal RAG Studio - Main FastAPI Application."""
import logging
import sys
from contextlib import asynccontextmanager
from pathlib import Path
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

# Ensure backend directory is in sys.path so 'app.*' modules resolve seamlessly
BACKEND_DIR = Path(__file__).resolve().parent / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.api.routes import router
from app.core.config import settings
from app.core.db_service import init_db

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logger = logging.getLogger("legal_rag")


@asynccontextmanager
async def lifespan(_app: FastAPI):
    """Initializes the database and pre-warms AI models once at startup."""
    init_db()
    try:
        from app.rag.chroma_manager import get_vectorstore
        from app.rag.reranker import get_shared_reranker
        logger.info("Pre-warming embeddings and ChromaDB...")
        get_vectorstore()
        logger.info("Pre-warming FlashRank reranker...")
        get_shared_reranker()
        logger.info("Building BM25 keyword index over parent sections...")
        from app.rag.bm25_index import get_bm25_index
        get_bm25_index(get_vectorstore())
        logger.info("Models and vector index pre-warmed.")
    except Exception:
        logger.exception("Model pre-warming failed; the first query will load them instead")
    yield


app = FastAPI(
    title="Multilingual Legal RAG Studio",
    description="RAG system for Indian law",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS is opt-in: the bundled UI is served from this same origin.
_cors_origins = [o.strip() for o in settings.CORS_ORIGINS.split(",") if o.strip()]
if _cors_origins:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=_cors_origins,
        allow_credentials=False,
        allow_methods=["GET", "POST", "DELETE"],
        allow_headers=["Content-Type"],
    )

# Register API routes
app.include_router(router)

# Mount static files directory
STATIC_DIR = Path(__file__).resolve().parent / "static"
if STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


@app.get("/")
def serve_index():
    """Serves main frontend UI."""
    index_path = STATIC_DIR / "index.html"
    if index_path.exists():
        return FileResponse(str(index_path))
    return {"message": "Legal RAG Studio API Backend is active. Visit /docs for OpenAPI specifications."}


if __name__ == "__main__":
    import uvicorn
    app_dir = BACKEND_DIR / "app"
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        reload_dirs=[str(app_dir)],
        reload_excludes=["*.sqlite", "*.sqlite3", "*.db", "data/*", "logs/*", "*.log", "__pycache__/*", "*.tmp"]
    )
