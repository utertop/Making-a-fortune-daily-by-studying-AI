from __future__ import annotations

import os
from datetime import datetime, timedelta, timezone
from time import perf_counter
from typing import Any

import httpx

from ..repository import (
    create_collector_run,
    create_github_repo_snapshot,
    upsert_github_repo,
    upsert_source,
)
from ..sources import validate_allowlisted_url


def _license_name(repo: dict[str, Any]) -> str | None:
    license_info = repo.get("license")
    if not license_info:
        return None
    return license_info.get("spdx_id") or license_info.get("name")


def _repo_record(repo: dict[str, Any]) -> dict[str, Any]:
    return {
        "full_name": repo["full_name"],
        "url": repo["html_url"],
        "description": repo.get("description"),
        "language": repo.get("language"),
        "topics": repo.get("topics", []),
        "license": _license_name(repo),
    }


def _snapshot_record(repo: dict[str, Any]) -> dict[str, Any]:
    return {
        "stars": repo.get("stargazers_count", 0),
        "forks": repo.get("forks_count", 0),
        "open_issues": repo.get("open_issues_count", 0),
        "pushed_at": repo.get("pushed_at"),
    }


def _query_with_date_placeholders(query: str) -> str:
    today = datetime.now(timezone.utc).date()
    return query.format(
        today=today.isoformat(),
        date_1d=(today - timedelta(days=1)).isoformat(),
        date_7d=(today - timedelta(days=7)).isoformat(),
        date_14d=(today - timedelta(days=14)).isoformat(),
        date_30d=(today - timedelta(days=30)).isoformat(),
    )


def collect_github_search_source(source: dict[str, Any], per_page: int = 20) -> dict[str, Any]:
    validate_allowlisted_url(source["url"], source.get("allowlist_domain"))
    source_id = upsert_source(source)
    started = datetime.now(timezone.utc)
    started_timer = perf_counter()
    fetched_count = 0
    snapshot_count = 0
    status = "success"
    error_message = None

    try:
        headers = {
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
            "User-Agent": "ai-signal-radar-v0.1",
        }
        token = os.getenv("GITHUB_TOKEN")
        if token:
            headers["Authorization"] = f"Bearer {token}"

        query = _query_with_date_placeholders(source.get("query", "AI agent"))
        params = {
            "q": query,
            "sort": source.get("sort", "stars"),
            "order": source.get("order", "desc"),
            "per_page": min(int(source.get("per_page", per_page)), 50),
        }
        with httpx.Client(timeout=30) as client:
            response = client.get(source["url"], headers=headers, params=params)
            response.raise_for_status()
            payload = response.json()

        items = payload.get("items", [])
        fetched_count = len(items)
        for repo in items:
            repo_id = upsert_github_repo(_repo_record(repo))
            create_github_repo_snapshot(repo_id, _snapshot_record(repo))
            snapshot_count += 1
    except Exception as exc:  # noqa: BLE001 - collector records errors instead of crashing caller
        status = "failed"
        error_message = str(exc)

    finished = datetime.now(timezone.utc)
    duration_ms = int((perf_counter() - started_timer) * 1000)
    run_id = create_collector_run(
        {
            "source_id": source_id,
            "collector_type": "github_search",
            "started_at": started.isoformat(),
            "finished_at": finished.isoformat(),
            "status": status,
            "fetched_count": fetched_count,
            "created_signal_count": snapshot_count,
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
        "snapshot_count": snapshot_count,
        "error_message": error_message,
        "duration_ms": duration_ms,
    }
