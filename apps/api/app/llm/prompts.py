from __future__ import annotations

import json
from typing import Any

SYSTEM_PROMPT = """You are an AI technology signal analyst.
Return only valid JSON. Do not invent facts beyond the provided fields.
Classify the signal, judge whether it is worth deep research, and write one short reason."""


def build_signal_enrichment_messages(signal: dict[str, Any]) -> list[dict[str, str]]:
    payload = {
        "title": signal.get("title"),
        "url": signal.get("url"),
        "source_type": signal.get("source_type"),
        "summary": signal.get("summary"),
        "published_at": signal.get("published_at"),
        "signal_score": signal.get("signal_score"),
        "raw_content": signal.get("raw_content"),
    }
    user_prompt = {
        "task": "Analyze this AI signal for a daily AI learning radar.",
        "allowed_values": {
            "ai_category": [
                "coding-agent",
                "rag",
                "model-serving",
                "evaluation",
                "workflow-automation",
                "developer-tool",
                "ai-ui",
                "research",
                "other",
            ],
            "project_type": [
                "product",
                "framework",
                "library",
                "resource-list",
                "paper-implementation",
                "benchmark",
                "toy",
                "unknown",
            ],
            "relevance": ["high", "medium", "low"],
            "priority": ["must_read", "track", "skip"],
        },
        "output_schema": {
            "ai_category": "one allowed ai_category",
            "project_type": "one allowed project_type",
            "relevance": "high | medium | low",
            "priority": "must_read | track | skip",
            "llm_score": "0-100 number",
            "reason": "short Chinese reason based only on provided fields",
            "risk": "short Chinese risk or empty string",
            "suggested_action": "short Chinese next action",
        },
        "signal": payload,
    }
    return [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": json.dumps(user_prompt, ensure_ascii=False)},
    ]
