from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from typing import Any, Callable, Dict, List, Optional

from .client import complete_json, is_llm_enabled
from .prompts import SIGNAL_ENRICHMENT_PROMPT_VERSION, build_signal_enrichment_messages
from .schemas import validate_signal_enrichment
from ..repository import (
    find_signal_enrichment_by_hash,
    get_signal_for_task_enrichment,
    list_llm_rerun_candidates,
    list_signal_enrichment_candidates,
    record_task_llm_rerun,
    upsert_signal_enrichment,
)
from ..settings import get_env

CompletionFn = Callable[[List[Dict[str, str]]], Dict[str, Any]]


def _env_bool(name: str, default: bool = False) -> bool:
    raw = get_env(name)
    if raw is None:
        return default
    return str(raw).strip().lower() in {"1", "true", "yes", "on"}


def push_enrichment_enabled(default: bool = False) -> bool:
    return _env_bool("AI_SIGNAL_RADAR_PUSH_ENRICH_ENABLED", default)


def push_enrichment_limit(limit: int) -> int:
    try:
        multiplier = int(get_env("AI_SIGNAL_RADAR_PUSH_ENRICH_LIMIT_MULTIPLIER", "2") or 2)
    except ValueError:
        multiplier = 2
    return max(limit, limit * max(1, multiplier), 10)


def signal_input_hash(signal: dict[str, Any], prompt_version: str = SIGNAL_ENRICHMENT_PROMPT_VERSION) -> str:
    payload = {
        "prompt_version": prompt_version,
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
    model: Optional[str] = None,
    force_refresh: bool = False,
) -> dict[str, Any]:
    prompt_version = SIGNAL_ENRICHMENT_PROMPT_VERSION
    base_input_hash = signal_input_hash(signal, prompt_version=prompt_version)
    if not force_refresh:
        cached = find_signal_enrichment_by_hash(int(signal["id"]), base_input_hash)
    else:
        cached = None
    if cached:
        return {**cached, "cached": True}

    input_hash = base_input_hash
    if force_refresh:
        rerun_key = f"{base_input_hash}:{datetime.now(timezone.utc).isoformat()}"
        input_hash = hashlib.sha256(rerun_key.encode("utf-8")).hexdigest()

    messages = build_signal_enrichment_messages(signal)
    raw = completion_fn(messages)
    validated = validate_signal_enrichment(raw)
    row_id = upsert_signal_enrichment(
        {
            "signal_id": int(signal["id"]),
            "provider": provider,
            "model": model or get_env("OPENAI_MODEL", "unknown") or "unknown",
            "input_hash": input_hash,
            "prompt_version": prompt_version,
            "raw_json": json.dumps(raw, ensure_ascii=False),
            **validated,
        }
    )
    return {"id": row_id, "signal_id": int(signal["id"]), "cached": False, **validated}


def rerun_task_signal_enrichment(task_id: int) -> dict[str, Any]:
    if not is_llm_enabled():
        raise RuntimeError("LLM enrichment is disabled or missing configuration")

    signal = get_signal_for_task_enrichment(task_id)
    result = enrich_signal(signal, force_refresh=True)
    task = record_task_llm_rerun(task_id, result)
    return {"enabled": True, "task": task, "enrichment": result}


def rerun_low_quality_signal_enrichments(limit: Optional[int] = None) -> dict[str, Any]:
    if not is_llm_enabled():
        return {"enabled": False, "processed": 0, "rerun": 0, "errors": [], "tasks": []}

    safe_limit = max(1, min(limit or 5, 20))
    candidates = list_llm_rerun_candidates(limit=safe_limit)
    processed = 0
    rerun = 0
    errors: list[dict[str, Any]] = []
    tasks: list[dict[str, Any]] = []
    for candidate in candidates:
        task_id = int(candidate["task_id"])
        try:
            result = rerun_task_signal_enrichment(task_id)
        except Exception as exc:  # Batch reruns should report per-task failures.
            errors.append({"task_id": task_id, "error": str(exc)})
            continue
        processed += 1
        rerun += 1
        tasks.append(result["task"])
    return {
        "enabled": True,
        "processed": processed,
        "rerun": rerun,
        "errors": errors,
        "tasks": tasks,
    }


def enrich_top_signal_candidates(limit: Optional[int] = None) -> dict[str, Any]:
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
