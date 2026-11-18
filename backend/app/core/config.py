from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field
from pathlib import Path

# Base directory paths
BASE_DIR = Path(__file__).resolve().parents[3]
DEFAULT_CHROMA_DIR = str(BASE_DIR / "data" / "chromadb")


class Settings(BaseSettings):
    """Application configuration loaded from environment variables and .env file."""
    model_config = SettingsConfigDict(
        env_file=str(Path(__file__).resolve().parents[2] / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # LLM Providers
    GROQ_API_KEY: str = ""
    GEMINI_API_KEY: str = ""
    OLLAMA_BASE_URL: str = "http://localhost:11434"
    OLLAMA_MODEL: str = "qwen3:1:1.7b"
    DEFAULT_LLM_PROVIDER: str = "groq"


    # LangSmith Tracing
    LANGCHAIN_TRACING_V2: str = "false"
    LANGCHAIN_API_KEY: str = ""
    LANGCHAIN_PROJECT: str = "legal-rag-studio"

    # MySQL Database
    MYSQL_HOST: str = "localhost"
    MYSQL_PORT: int = 3306
    MYSQL_USER: str = "root"
    MYSQL_PASSWORD: str = "1234"
    MYSQL_DATABASE: str = "legal_rag_db_v4"

    # ChromaDB & Embeddings
    CHROMA_PERSIST_DIRECTORY: str = DEFAULT_CHROMA_DIR
    CHROMA_COLLECTION_NAME: str = "indian_legal_corpus"
    EMBEDDING_MODEL_NAME: str = "sentence-transformers/paraphrase-multilingual-mpnet-base-v2"
    LOCAL_MODELS_DIRECTORY: str = str(BASE_DIR / "data" / "models")
    LOCAL_CACHE_DIRECTORY: str = str(BASE_DIR / "data" / "cache")
    
    # Tavli API
    TAVILY_API_KEY: str = Field(default="", env="TAVILY_API_KEY")

    @property
    def mysql_url(self) -> str:
        """Constructs MySQL SQLAlchemy connection URL."""
        return f"mysql+pymysql://{self.MYSQL_USER}:{self.MYSQL_PASSWORD}@{self.MYSQL_HOST}:{self.MYSQL_PORT}/{self.MYSQL_DATABASE}"

    @property
    def chroma_persist_path(self) -> Path:
        """Ensures ChromaDB persistence directory is always absolute relative to BASE_DIR."""
        p = Path(self.CHROMA_PERSIST_DIRECTORY)
        if not p.is_absolute():
            return (BASE_DIR / p).resolve()
        return p.resolve()


settings = Settings()
