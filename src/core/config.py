import os
from functools import lru_cache
from pathlib import Path
from dotenv import load_dotenv
from pydantic import BaseModel, Field

# Load .env if present
load_dotenv()


class Settings(BaseModel):
    # Provider API Keys
    groq_api_key: str = Field(default_factory=lambda: os.getenv("GROQ_API_KEY", ""))
    gemini_api_key: str = Field(default_factory=lambda: os.getenv("GEMINI_API_KEY", ""))
    groq_base_url: str = Field(default_factory=lambda: os.getenv("GROQ_BASE_URL", "https://api.groq.com/openai/v1"))

    # Provider Models
    groq_gen_model: str = Field(
        default_factory=lambda: os.getenv("GROQ_GEN_MODEL")
        or os.getenv("GROQ_PRIMARY_MODEL")
        or "llama-3.3-70b-versatile"
    )
    groq_classify_model: str = Field(
        default_factory=lambda: os.getenv("GROQ_CLASSIFY_MODEL")
        or os.getenv("GROQ_SUMMARY_MODEL")
        or "llama-3.1-8b-instant"
    )
    gemini_model: str = Field(default_factory=lambda: os.getenv("GEMINI_MODEL", "gemini-2.5-flash"))

    # Thresholds & Parameters
    intent_confidence_threshold: float = Field(
        default_factory=lambda: float(os.getenv("INTENT_CONFIDENCE_THRESHOLD", "0.75"))
    )
    retrieval_similarity_floor: float = Field(
        default_factory=lambda: float(os.getenv("RETRIEVAL_SIMILARITY_FLOOR", "0.65"))
    )
    top_k_passages: int = Field(default_factory=lambda: int(os.getenv("TOP_K_PASSAGES", "3")))
    top_k_escalate: int = Field(default_factory=lambda: int(os.getenv("TOP_K_ESCALATE", "2")))
    provider_request_timeout: float = Field(
        default_factory=lambda: float(os.getenv("PROVIDER_REQUEST_TIMEOUT", "10.0"))
    )
    provider_max_retries: int = Field(default_factory=lambda: int(os.getenv("PROVIDER_MAX_RETRIES", "1")))
    backoff_base: float = Field(default_factory=lambda: float(os.getenv("BACKOFF_BASE", "1.0")))
    backoff_cap: float = Field(default_factory=lambda: float(os.getenv("BACKOFF_CAP", "8.0")))
    batch_delay: float = Field(default_factory=lambda: float(os.getenv("BATCH_DELAY", "1.5")))
    generation_temperature: float = Field(
        default_factory=lambda: float(os.getenv("GENERATION_TEMPERATURE", "0.0"))
    )

    # Storage Paths
    chroma_persist_dir: str = Field(default_factory=lambda: os.getenv("CHROMA_PERSIST_DIR", "data/chromadb"))
    decision_log_path: str = Field(default_factory=lambda: os.getenv("DECISION_LOG_PATH", "data/decision_log.db"))
    documentation_path: str = Field(
        default_factory=lambda: os.getenv("DOCUMENTATION_PATH", "05_Datasets/documentation.json")
    )


@lru_cache()
def get_settings() -> Settings:
    return Settings()
