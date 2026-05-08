from __future__ import annotations

import json
from typing import Any

import httpx

from ..settings import get_env


class LLMNotConfigured(RuntimeError):
    pass


def is_llm_enabled() -> bool:
    enabled = str(get_env("AI_SIGNAL_RADAR_LLM_ENABLED", "false")).lower() in {"1", "true", "yes", "on"}
    return enabled and bool(get_env("OPENAI_API_KEY")) and bool(get_env("OPENAI_MODEL"))


def _env_int(name: str, default: int) -> int:
    try:
        return int(get_env(name, str(default)) or default)
    except ValueError:
        return default


def _env_float(name: str, default: float) -> float:
    try:
        return float(get_env(name, str(default)) or default)
    except ValueError:
        return default


def complete_json(messages: list[dict[str, str]]) -> dict[str, Any]:
    if not is_llm_enabled():
        raise LLMNotConfigured("LLM enrichment is disabled or missing OPENAI_API_KEY / OPENAI_MODEL")

    base_url = (get_env("OPENAI_BASE_URL", "https://api.openai.com/v1") or "").rstrip("/")
    payload = {
        "model": get_env("OPENAI_MODEL"),
        "messages": messages,
        "temperature": _env_float("AI_SIGNAL_RADAR_LLM_TEMPERATURE", 0.2),
        "max_tokens": _env_int("AI_SIGNAL_RADAR_LLM_MAX_OUTPUT_TOKENS", 500),
        "response_format": {"type": "json_object"},
    }
    headers = {
        "Authorization": f"Bearer {get_env('OPENAI_API_KEY')}",
        "Content-Type": "application/json",
    }
    with httpx.Client(timeout=_env_int("AI_SIGNAL_RADAR_LLM_TIMEOUT_SECONDS", 20)) as client:
        response = client.post(f"{base_url}/chat/completions", headers=headers, json=payload)
        response.raise_for_status()
        data = response.json()

    content = data["choices"][0]["message"]["content"]
    parsed = json.loads(content)
    if not isinstance(parsed, dict):
        raise ValueError("LLM response must be a JSON object")
    return parsed
