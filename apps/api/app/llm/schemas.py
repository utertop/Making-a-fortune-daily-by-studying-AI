from __future__ import annotations

from typing import Any

AI_CATEGORIES = {
    "coding-agent",
    "rag",
    "model-serving",
    "evaluation",
    "workflow-automation",
    "developer-tool",
    "ai-ui",
    "research",
    "other",
}

PROJECT_TYPES = {
    "product",
    "framework",
    "library",
    "resource-list",
    "paper-implementation",
    "benchmark",
    "toy",
    "unknown",
}

RELEVANCE_VALUES = {"high", "medium", "low"}
PRIORITY_VALUES = {"must_read", "track", "skip"}
PRIORITY_SCORES = {"must_read": 90.0, "track": 65.0, "skip": 20.0}


def _clean_choice(value: Any, allowed: set[str], fallback: str) -> str:
    if isinstance(value, str):
        normalized = value.strip().lower().replace(" ", "-")
        if normalized in allowed:
            return normalized
    return fallback


def _clean_text(value: Any, max_length: int = 240) -> str:
    if not isinstance(value, str):
        return ""
    normalized = " ".join(value.strip().split())
    return normalized[:max_length]


def _clean_score(value: Any, priority: str) -> float:
    try:
        score = float(value)
    except (TypeError, ValueError):
        score = PRIORITY_SCORES[priority]
    return max(0.0, min(100.0, score))


def validate_signal_enrichment(value: dict[str, Any]) -> dict[str, Any]:
    priority = _clean_choice(value.get("priority"), PRIORITY_VALUES, "track")
    return {
        "ai_category": _clean_choice(value.get("ai_category"), AI_CATEGORIES, "other"),
        "project_type": _clean_choice(value.get("project_type"), PROJECT_TYPES, "unknown"),
        "relevance": _clean_choice(value.get("relevance"), RELEVANCE_VALUES, "medium"),
        "priority": priority,
        "llm_score": _clean_score(value.get("llm_score"), priority),
        "reason": _clean_text(value.get("reason")),
        "risk": _clean_text(value.get("risk")),
        "suggested_action": _clean_text(value.get("suggested_action"), max_length=160),
    }
