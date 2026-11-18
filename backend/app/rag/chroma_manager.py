"""ChromaDB Vector Store Manager with persistent local offline HuggingFace embedding weights."""
import os
import logging
from pathlib import Path
from langchain_chroma import Chroma
from langchain_huggingface import HuggingFaceEmbeddings
from sentence_transformers import SentenceTransformer
from app.core.config import settings

logger = logging.getLogger(__name__)

# Ensure HF hub doesn't emit noisy symlink warnings on Windows
os.environ["HF_HUB_DISABLE_SYMLINKS_WARNING"] = "1"
os.environ["TOKENIZERS_PARALLELISM"] = "false"

_embeddings_instance = None
_vectorstore_instance = None


def get_local_model_path(model_name: str, base_models_dir: Path) -> Path:
    """Returns the persistent local directory path for a HuggingFace model."""
    folder_name = model_name.split("/")[-1]
    return base_models_dir / folder_name


def ensure_local_embedding_model(model_name: str = settings.EMBEDDING_MODEL_NAME) -> str:
    """
    Checks if Hugging Face embedding weights exist locally in data/models.
    If not, downloads and saves the model once to local disk so it is never
    re-fetched over the network again. Returns local folder path string.
    """
    # If already a direct local directory path that exists
    if Path(model_name).exists() and (Path(model_name) / "config.json").exists():
        return str(Path(model_name).resolve())

    models_dir = Path(settings.LOCAL_MODELS_DIRECTORY).resolve()
    models_dir.mkdir(parents=True, exist_ok=True)
    local_path = get_local_model_path(model_name, models_dir)

    # Check if complete model weights exist locally
    has_config = (local_path / "config.json").exists()
    has_weights = (
        (local_path / "model.safetensors").exists()
        or (local_path / "pytorch_model.bin").exists()
        or (local_path / "modules.json").exists()
    )

    if local_path.exists() and has_config and has_weights:
        logger.info(f"[LOCAL CACHE] Using locally saved HuggingFace model from: {local_path}")
        return str(local_path)

    # If not found locally, download once and save to local directory
    logger.info(f"[DOWNLOAD] Downloading HuggingFace embedding model '{model_name}' once to local disk at: {local_path} ...")
    print(f"[SETUP] Downloading HuggingFace embedding model '{model_name}' to {local_path} (one-time setup)...")

    local_path.mkdir(parents=True, exist_ok=True)
    st_model = SentenceTransformer(model_name)
    st_model.save(str(local_path))

    logger.info(f"[OK] HuggingFace model successfully saved locally to: {local_path}")
    print(f"[OK] HuggingFace model successfully saved locally to: {local_path}")
    return str(local_path)


def get_embedding_function() -> HuggingFaceEmbeddings:
    """Initializes sentence-transformers 768-dim multilingual embedding model from local disk (cached)."""
    global _embeddings_instance
    if _embeddings_instance is None:
        local_model_path = ensure_local_embedding_model(settings.EMBEDDING_MODEL_NAME)
        _embeddings_instance = HuggingFaceEmbeddings(
            model_name=local_model_path,
            model_kwargs={"device": "cpu"},
            encode_kwargs={"normalize_embeddings": True}
        )
    return _embeddings_instance


def get_vectorstore() -> Chroma:
    """Loads persistent ChromaDB collection from local data directory (cached singleton)."""
    global _vectorstore_instance
    if _vectorstore_instance is None:
        persist_dir = settings.chroma_persist_path
        persist_dir.mkdir(parents=True, exist_ok=True)
        embeddings = get_embedding_function()
        _vectorstore_instance = Chroma(
            collection_name=settings.CHROMA_COLLECTION_NAME,
            embedding_function=embeddings,
            persist_directory=str(persist_dir)
        )
    return _vectorstore_instance

