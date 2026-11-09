import hashlib
import json
import os
from pathlib import Path
from typing import Any
from src.core.models import CanonicalTicket

_MEMORY_CACHE: dict[str, dict[str, Any]] = {}


def compute_ticket_hash(ticket: CanonicalTicket) -> str:
    """Computes a deterministic sha256 hash from a canonical ticket."""
    dumped = json.dumps(ticket.model_dump(mode="json"), sort_keys=True)
    return hashlib.sha256(dumped.encode("utf-8")).hexdigest()


class ClassificationCache:
    def __init__(self, cache_file: str | Path | None = None):
        self.cache_file = Path(cache_file) if cache_file else None
        if self.cache_file and self.cache_file.exists():
            try:
                with open(self.cache_file, "r", encoding="utf-8") as f:
                    disk_cache = json.load(f)
                    _MEMORY_CACHE.update(disk_cache)
            except Exception:
                pass

    def get(self, ticket_hash: str) -> dict[str, Any] | None:
        return _MEMORY_CACHE.get(ticket_hash)

    def set(self, ticket_hash: str, classification: dict[str, Any]) -> None:
        _MEMORY_CACHE[ticket_hash] = classification
        if self.cache_file:
            try:
                self.cache_file.parent.mkdir(parents=True, exist_ok=True)
                with open(self.cache_file, "w", encoding="utf-8") as f:
                    json.dump(_MEMORY_CACHE, f, indent=2)
            except Exception:
                pass


def _cache_file_from_env() -> str | None:
    """CLASSIFICATION_CACHE_PATH overrides the cache file; the value 'none' keeps the cache in memory only."""
    value = os.getenv("CLASSIFICATION_CACHE_PATH", "data/cache/classification_cache.json")
    return None if value.strip().lower() == "none" else value


_GLOBAL_CACHE = ClassificationCache(_cache_file_from_env())


def get_classification_cache() -> ClassificationCache:
    return _GLOBAL_CACHE



def cache_scope() -> str:
    """Fingerprint of the active provider configuration, appended to cache keys so one model's answers
    are never replayed for another. Empty when PROVIDER_ORDER is unset (legacy single-provider runs)."""
    if not os.getenv("PROVIDER_ORDER"):
        return ""
    from src.core.config import get_settings

    st = get_settings()
    raw = "|".join([",".join(st.provider_order), st.provider_strategy, st.groq_classify_model,
                    st.openrouter_model, st.gemini_model])
    return ":" + hashlib.sha1(raw.encode()).hexdigest()[:10]
