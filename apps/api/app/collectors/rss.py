from __future__ import annotations

from datetime import datetime, timezone
from time import perf_counter
from typing import Any

import feedparser

from ..repository import create_collector_run, upsert_signal, upsert_source
from ..sources import validate_allowlisted_url


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
            _, created = upsert_signal(
                {
                    "title": str(title),
                    "url": str(link),
                    "source_id": source_id,
                    "source_type": source["type"],
                    "raw_content": _entry_summary(entry),
                    "summary": _entry_summary(entry),
                    "published_at": _entry_published(entry),
                    "authority_score": 10 if source.get("official") else 0,
                    "relevance_score": 5,
                    "actionability_score": 2,
                    "signal_score": 17 if source.get("official") else 7,
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
