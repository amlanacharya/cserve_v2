"""Deterministic queue priority (PRD FR-08): higher-tier and more urgent tickets sort first."""
from src.core.types import Urgency

_BASE = {"LOW": 25, "MEDIUM": 50, "HIGH": 85, "CRITICAL": 95}
_TIER_BONUS = {"enterprise": 10, "business": 5}


def compute_priority(urgency: Urgency, customer_tier: str | None) -> tuple[int, str]:
    score = min(100, _BASE.get(urgency, 50) + _TIER_BONUS.get((customer_tier or "").lower(), 0))
    level = "critical" if score >= 95 else "high" if score >= 85 else "medium" if score >= 50 else "low"
    return score, level
