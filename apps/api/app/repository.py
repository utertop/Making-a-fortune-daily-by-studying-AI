from __future__ import annotations

import json
from typing import Any

from .db import get_connection, init_database


def _json_or_none(value: Any) -> str | None:
    if value is None:
        return None
    return json.dumps(value, ensure_ascii=False)


def upsert_source(source: dict[str, Any]) -> int:
    with get_connection() as connection:
        connection.execute(
            """
            insert into source (
                name, type, url, platform, priority, enabled, official, tags,
                poll_interval_minutes, allowlist_domain, metadata
            ) values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            on conflict(name, url) do update set
                type = excluded.type,
                platform = excluded.platform,
                priority = excluded.priority,
                enabled = excluded.enabled,
                official = excluded.official,
                tags = excluded.tags,
                poll_interval_minutes = excluded.poll_interval_minutes,
                allowlist_domain = excluded.allowlist_domain,
                metadata = excluded.metadata,
                updated_at = CURRENT_TIMESTAMP
            """,
            (
                source["name"],
                source["type"],
                source["url"],
                source.get("platform"),
                source.get("priority", "medium"),
                1 if source.get("enabled", True) else 0,
                1 if source.get("official", False) else 0,
                _json_or_none(source.get("tags")),
                source.get("poll_interval_minutes", 1440),
                source.get("allowlist_domain"),
                _json_or_none(source.get("metadata")),
            ),
        )
        row = connection.execute(
            "select id from source where name = ? and url = ?", (source["name"], source["url"])
        ).fetchone()
        return int(row["id"])


def upsert_github_repo(repo: dict[str, Any]) -> int:
    with get_connection() as connection:
        connection.execute(
            """
            insert into github_repo (full_name, url, description, language, topics, license)
            values (?, ?, ?, ?, ?, ?)
            on conflict(full_name) do update set
                url = excluded.url,
                description = excluded.description,
                language = excluded.language,
                topics = excluded.topics,
                license = excluded.license,
                updated_at = CURRENT_TIMESTAMP
            """,
            (
                repo["full_name"],
                repo["url"],
                repo.get("description"),
                repo.get("language"),
                _json_or_none(repo.get("topics")),
                repo.get("license"),
            ),
        )
        row = connection.execute(
            "select id from github_repo where full_name = ?", (repo["full_name"],)
        ).fetchone()
        return int(row["id"])


def create_github_repo_snapshot(repo_id: int, snapshot: dict[str, Any]) -> int:
    with get_connection() as connection:
        cursor = connection.execute(
            """
            insert into github_repo_snapshot (
                repo_id, stars, forks, open_issues, pushed_at, latest_release_at, captured_at
            ) values (?, ?, ?, ?, ?, ?, coalesce(?, CURRENT_TIMESTAMP))
            """,
            (
                repo_id,
                snapshot.get("stars", 0),
                snapshot.get("forks", 0),
                snapshot.get("open_issues", 0),
                snapshot.get("pushed_at"),
                snapshot.get("latest_release_at"),
                snapshot.get("captured_at"),
            ),
        )
        return int(cursor.lastrowid)


def create_collector_run(run: dict[str, Any]) -> int:
    with get_connection() as connection:
        cursor = connection.execute(
            """
            insert into collector_run (
                source_id, collector_type, started_at, finished_at, status,
                fetched_count, created_signal_count, error_message, duration_ms
            ) values (?, ?, coalesce(?, CURRENT_TIMESTAMP), ?, ?, ?, ?, ?, ?)
            """,
            (
                run.get("source_id"),
                run["collector_type"],
                run.get("started_at"),
                run.get("finished_at"),
                run.get("status", "running"),
                run.get("fetched_count", 0),
                run.get("created_signal_count", 0),
                run.get("error_message"),
                run.get("duration_ms"),
            ),
        )
        return int(cursor.lastrowid)


def count_rows(table: str) -> int:
    allowed = {
        "source",
        "github_repo",
        "github_repo_snapshot",
        "collector_run",
        "signal",
        "learning_task",
        "knowledge_document",
    }
    if table not in allowed:
        raise ValueError(f"Unsupported table: {table}")
    with get_connection() as connection:
        row = connection.execute(f"select count(*) as count from {table}").fetchone()
        return int(row["count"])


def upsert_signal(signal: dict[str, Any]) -> tuple[int, bool]:
    with get_connection() as connection:
        existing = connection.execute("select id from signal where url = ?", (signal["url"],)).fetchone()
        connection.execute(
            """
            insert into signal (
                title, url, source_id, source_type, raw_content, summary, published_at,
                fetched_at, signal_score, freshness_score, velocity_score, authority_score,
                resonance_score, relevance_score, actionability_score, status
            ) values (?, ?, ?, ?, ?, ?, ?, coalesce(?, CURRENT_TIMESTAMP), ?, ?, ?, ?, ?, ?, ?, ?)
            on conflict(url) do update set
                title = excluded.title,
                source_id = excluded.source_id,
                source_type = excluded.source_type,
                raw_content = excluded.raw_content,
                summary = excluded.summary,
                published_at = excluded.published_at,
                signal_score = excluded.signal_score,
                freshness_score = excluded.freshness_score,
                velocity_score = excluded.velocity_score,
                authority_score = excluded.authority_score,
                resonance_score = excluded.resonance_score,
                relevance_score = excluded.relevance_score,
                actionability_score = excluded.actionability_score,
                updated_at = CURRENT_TIMESTAMP
            """,
            (
                signal["title"],
                signal["url"],
                signal.get("source_id"),
                signal.get("source_type"),
                signal.get("raw_content"),
                signal.get("summary"),
                signal.get("published_at"),
                signal.get("fetched_at"),
                signal.get("signal_score", 0),
                signal.get("freshness_score", 0),
                signal.get("velocity_score", 0),
                signal.get("authority_score", 0),
                signal.get("resonance_score", 0),
                signal.get("relevance_score", 0),
                signal.get("actionability_score", 0),
                signal.get("status", "discovered"),
            ),
        )
        row = connection.execute("select id from signal where url = ?", (signal["url"],)).fetchone()
        return int(row["id"]), existing is None


def list_recent_signals(limit: int = 10) -> list[dict[str, Any]]:
    with get_connection() as connection:
        rows = connection.execute(
            """
            select id, title, url, source_type, published_at, signal_score, status
            from signal
            order by fetched_at desc, id desc
            limit ?
            """,
            (limit,),
        ).fetchall()
        return [dict(row) for row in rows]

def init() -> None:
    init_database()

