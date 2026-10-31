import hashlib
import json
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


_GLOBAL_CACHE = ClassificationCache("data/cache/classification_cache.json")


def get_classification_cache() -> ClassificationCache:
    return _GLOBAL_CACHE

