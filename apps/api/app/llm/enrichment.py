from __future__ import annotations

import hashlib
import json
from typing import Any, Callable, Dict, List

from .client import complete_json, is_llm_enabled
from .prompts import build_signal_enrichment_messages
from .schemas import validate_signal_enrichment
from ..repository import (
    find_signal_enrichment_by_hash,
    list_signal_enrichment_candidates,
    upsert_signal_enrichment,
)
from ..settings import get_env

CompletionFn = Callable[[List[Dict[str, str]]], Dict[str, Any]]


def signal_input_hash(signal: dict[str, Any]) -> str:
    payload = {
        "title": signal.get("title"),
        "url": signal.get("url"),
        "source_type": signal.get("source_type"),
        "summary": signal.get("summary"),
        "signal_score": signal.get("signal_score"),
        "raw_content": signal.get("raw_content"),
    }
    serialized = json.dumps(payload, ensure_ascii=False, sort_keys=True)
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()


def enrich_signal(
    signal: dict[str, Any],
    *,
    completion_fn: CompletionFn = complete_json,
    provider: str = "openai-compatible",
    model: str | None = None,
) -> dict[str, Any]:
    input_hash = signal_input_hash(signal)
    cached = find_signal_enrichment_by_hash(int(signal["id"]), input_hash)
    if cached:
        return {**cached, "cached": True}

    messages = build_signal_enrichment_messages(signal)
    raw = completion_fn(messages)
    validated = validate_signal_enrichment(raw)
    row_id = upsert_signal_enrichment(
        {
            "signal_id": int(signal["id"]),
            "provider": provider,
            "model": model or get_env("OPENAI_MODEL", "unknown") or "unknown",
            "input_hash": input_hash,
            "raw_json": json.dumps(raw, ensure_ascii=False),
            **validated,
        }
    )
    return {"id": row_id, "signal_id": int(signal["id"]), "cached": False, **validated}


def enrich_top_signal_candidates(limit: int | None = None) -> dict[str, Any]:
    if not is_llm_enabled():
        return {"enabled": False, "processed": 0, "created": 0, "cached": 0, "errors": []}

    try:
        daily_limit = int(get_env("AI_SIGNAL_RADAR_LLM_DAILY_LIMIT", "20") or 20)
    except ValueError:
        daily_limit = 20
    safe_limit = max(1, min(limit or daily_limit, daily_limit, 50))
    signals = list_signal_enrichment_candidates(limit=safe_limit)
    processed = 0
    created = 0
    cached = 0
    errors: list[dict[str, Any]] = []
    for signal in signals:
        try:
            result = enrich_signal(signal)
        except Exception as exc:  # LLM enrichment must not break the radar.
            errors.append({"signal_id": signal.get("id"), "error": str(exc)})
            continue
        processed += 1
        if result.get("cached"):
            cached += 1
        else:
            created += 1
    return {
        "enabled": True,
        "processed": processed,
        "created": created,
        "cached": cached,
        "errors": errors,
    }
