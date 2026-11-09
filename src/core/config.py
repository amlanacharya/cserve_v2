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
    gemini_api_key: str = Field(default_factory=lambda: os.getenv("GEMINI_API_KEY") or os.getenv("GEMINI", ""))
    groq_base_url: str = Field(default_factory=lambda: os.getenv("GROQ_BASE_URL", "https://api.groq.com/openai/v1"))
    openrouter_api_key: str = Field(
        default_factory=lambda: os.getenv("OPENROUTER_API_KEY") or os.getenv("OPENROUTER", "")
    )
    openrouter_base_url: str = Field(
        default_factory=lambda: os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1")
    )
    openrouter_model: str = Field(default_factory=lambda: os.getenv("OPENROUTER_MODEL", "openai/gpt-oss-20b"))
    # Tier order, e.g. "openrouter,groq,gemini". PRIMARY_PROVIDER (older setting) is kept as a shortcut.
    provider_order: list[str] = Field(
        default_factory=lambda: [
            x.strip().lower()
            for x in (os.getenv("PROVIDER_ORDER") or os.getenv("PRIMARY_PROVIDER", "groq")).split(",")
            if x.strip()
        ]
    )
    # "failover" (default) or "roundrobin"
    provider_strategy: str = Field(default_factory=lambda: os.getenv("PROVIDER_STRATEGY", "failover").lower())
    max_spend_usd: float = Field(default_factory=lambda: float(os.getenv("MAX_SPEND_USD", "0")))  # 0 = no cap

    # Provider Models
    groq_gen_model: str = Field(
        default_factory=lambda: os.getenv("GROQ_GEN_MODEL")
        or os.getenv("GROQ_PRIMARY_MODEL")
        or "openai/gpt-oss-20b"
    )
    groq_classify_model: str = Field(
        default_factory=lambda: os.getenv("GROQ_CLASSIFY_MODEL")
        or os.getenv("GROQ_SUMMARY_MODEL")
        or "openai/gpt-oss-20b"
    )
    gemini_model: str = Field(default_factory=lambda: os.getenv("GEMINI_MODEL", "gemini-3.1-flash-lite"))

    # Thresholds & Parameters
    intent_confidence_threshold: float = Field(
        default_factory=lambda: float(os.getenv("INTENT_CONFIDENCE_THRESHOLD", "0.75"))
    )
    retrieval_similarity_floor: float = Field(
        default_factory=lambda: float(os.getenv("RETRIEVAL_SIMILARITY_FLOOR", "0.4"))
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
