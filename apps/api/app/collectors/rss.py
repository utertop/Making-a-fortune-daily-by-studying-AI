from __future__ import annotations

import json
from datetime import datetime, timezone
from time import perf_counter
from typing import Any

import feedparser

from ..repository import create_collector_run, upsert_signal, upsert_source
from ..sources import validate_allowlisted_url

HIGH_VALUE_KEYWORDS = {
    "agent": 8,
    "agentic": 8,
    "codex": 8,
    "model": 6,
    "models": 6,
    "eval": 6,
    "evaluation": 6,
    "benchmark": 6,
    "inference": 6,
    "open source": 5,
    "github copilot": 5,
    "rag": 5,
    "mcp": 5,
    "workflow": 4,
    "automation": 4,
    "release": 4,
    "api": 3,
}

LOW_VALUE_KEYWORDS = {
    "customer story": -5,
    "case study": -4,
    "partner": -3,
    "event": -3,
    "webinar": -3,
    "announcement": -2,
}


def _entry_published(entry: Any) -> str | None:
    parsed = getattr(entry, "published_parsed", None) or getattr(entry, "updated_parsed", None)
    if not parsed:
        return None
    return datetime(*parsed[:6], tzinfo=timezone.utc).isoformat()


def _entry_summary(entry: Any) -> str | None:
    summary = getattr(entry, "summary", None)
    if summary:
        return str(summary)
    description = getattr(entry, "description", None)
    if description:
        return str(description)
    return None


def _score_entry(source: dict[str, Any], title: str, summary: str | None) -> dict[str, Any]:
    text = f"{title}\n{summary or ''}".lower()
    score = 8
    reasons: list[str] = []
    risks: list[str] = []

    if source.get("official"):
        score += 8
        reasons.append("official_source: +8")

    for keyword, value in HIGH_VALUE_KEYWORDS.items():
        if keyword in text:
            score += value
            reasons.append(f"{keyword}: +{value}")

    for keyword, value in LOW_VALUE_KEYWORDS.items():
        if keyword in text:
            score += value
            risks.append(f"{keyword}: {value}")

    if len(text.strip()) < 120:
        score -= 3
        risks.append("thin_summary: -3")

    if not reasons:
        score -= 5
        risks.append("weak_ai_relevance: -5")

    return {
        "score": max(0, score),
        "reasons": reasons,
        "risks": risks,
    }


def collect_rss_source(source: dict[str, Any], max_entries: int = 20) -> dict[str, Any]:
    validate_allowlisted_url(source["url"], source.get("allowlist_domain"))
    source_id = upsert_source(source)
    started = datetime.now(timezone.utc)
    started_timer = perf_counter()
    fetched_count = 0
    created_count = 0
    status = "success"
    error_message = None

    try:
        feed = feedparser.parse(source["url"])
        if getattr(feed, "bozo", False):
            exception = getattr(feed, "bozo_exception", None)
            if exception:
                raise ValueError(str(exception))

        entries = list(getattr(feed, "entries", []))[:max_entries]
        fetched_count = len(entries)
        for entry in entries:
            link = getattr(entry, "link", None)
            title = getattr(entry, "title", None)
            if not link or not title:
                continue
            summary = _entry_summary(entry)
            scoring = _score_entry(source, str(title), summary)
            _, created = upsert_signal(
                {
                    "title": str(title),
                    "url": str(link),
                    "source_id": source_id,
                    "source_type": source["type"],
                    "raw_content": json.dumps(
                        {
                            "source_name": source["name"],
                            "reasons": scoring["reasons"],
                            "risks": scoring["risks"],
                        },
                        ensure_ascii=False,
                    ),
                    "summary": summary,
                    "published_at": _entry_published(entry),
                    "authority_score": 10 if source.get("official") else 0,
                    "relevance_score": max(0, scoring["score"] - 8),
                    "actionability_score": 2,
                    "signal_score": scoring["score"],
                    "status": "discovered",
                }
            )
            if created:
                created_count += 1
    except Exception as exc:  # noqa: BLE001 - collector records errors instead of crashing caller
        status = "failed"
        error_message = str(exc)

    finished = datetime.now(timezone.utc)
    duration_ms = int((perf_counter() - started_timer) * 1000)
    run_id = create_collector_run(
        {
            "source_id": source_id,
            "collector_type": "rss",
            "started_at": started.isoformat(),
            "finished_at": finished.isoformat(),
            "status": status,
            "fetched_count": fetched_count,
            "created_signal_count": created_count,
            "error_message": error_message,
            "duration_ms": duration_ms,
        }
    )
    return {
        "source_id": source_id,
        "source_name": source["name"],
        "run_id": run_id,
        "status": status,
        "fetched_count": fetched_count,
        "created_signal_count": created_count,
        "error_message": error_message,
        "duration_ms": duration_ms,
    }
