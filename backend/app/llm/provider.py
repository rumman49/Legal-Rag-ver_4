"""Unified Multi-Provider LLM Switcher (Groq, Gemini, Ollama)."""
from typing import Optional
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_groq import ChatGroq
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_ollama import ChatOllama
from app.core.config import settings


def get_llm(provider: Optional[str] = None, model_name: Optional[str] = None) -> BaseChatModel:
    """Returns initialized LangChain ChatModel instance with fallback handling."""
    selected_provider = (provider or settings.DEFAULT_LLM_PROVIDER).lower()

    if selected_provider == "groq":
        target_model = model_name if (model_name and model_name.lower() != "groq") else "qwen/qwen3.8-27b"
        if not settings.GROQ_API_KEY:
            raise ValueError("GROQ_API_KEY is not set in environment or .env file.")
        
        return ChatGroq(
            groq_api_key=settings.GROQ_API_KEY,
            model_name=target_model,
            temperature=0.1,
            max_tokens=800
        )

    elif selected_provider == "gemini":
        target_model = model_name if (model_name and model_name.lower() != "gemini") else "gemini-flash-latest"
        if not settings.GEMINI_API_KEY:
            raise ValueError("GEMINI_API_KEY is not set in environment or .env file.")
        return ChatGoogleGenerativeAI(
            google_api_key=settings.GEMINI_API_KEY,
            model=target_model,
            temperature=0.1
        )

    elif selected_provider == "ollama":
        target_model = model_name if (model_name and model_name.lower() != "ollama") else (settings.OLLAMA_MODEL or "qwen3:1:1.7b")
        return ChatOllama(
            base_url=settings.OLLAMA_BASE_URL,
            model=target_model,
            temperature=0.1
        )


    else:
        raise ValueError(f"Unsupported LLM provider: {selected_provider}. Allowed: 'groq', 'gemini', 'ollama'")

