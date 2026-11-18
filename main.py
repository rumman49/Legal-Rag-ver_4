"""Legal RAG Studio - Main FastAPI Application."""
import sys
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
from app.core.db_service import init_db

app = FastAPI(
    title="Multilingual Legal RAG Studio",
    description="Production-grade RAG System optimized for Indian Law",
    version="1.0.0"
)

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
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


@app.on_event("startup")
def on_startup():
    """Initializes database tables and pre-warms AI models into memory on application launch."""
    init_db()
    try:
        from app.rag.chroma_manager import get_vectorstore
        from app.rag.reranker import get_shared_reranker
        print("[STARTUP] Pre-warming persistent HuggingFace embeddings & ChromaDB...")
        get_vectorstore()
        print("[STARTUP] Pre-warming FlashRank reranker...")
        get_shared_reranker()
        print("[STARTUP] Building BM25 keyword index over parent sections...")
        from app.rag.bm25_index import get_bm25_index
        get_bm25_index(get_vectorstore())
        print("[STARTUP] All AI models and vector index successfully pre-warmed in memory.")
    except Exception as e:
        print(f"[STARTUP] Model pre-warming notice: {e}")


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
