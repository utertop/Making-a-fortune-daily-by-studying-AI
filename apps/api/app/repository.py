from __future__ import annotations

import json
from typing import Any

from .db import get_connection, init_database

TASK_STATUSES = {"pending", "pushed", "selected", "documented", "archived", "ignored"}


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

def list_recent_github_repos(limit: int = 10) -> list[dict[str, Any]]:
    with get_connection() as connection:
        rows = connection.execute(
            """
            select
                r.id,
                r.full_name,
                r.url,
                r.description,
                r.language,
                s.stars,
                s.forks,
                s.open_issues,
                s.captured_at
            from github_repo r
            join github_repo_snapshot s on s.repo_id = r.id
            where s.id = (
                select max(s2.id) from github_repo_snapshot s2 where s2.repo_id = r.id
            )
            order by s.captured_at desc, s.stars desc
            limit ?
            """,
            (limit,),
        ).fetchall()
        return [dict(row) for row in rows]

def list_github_repo_scoring_inputs() -> list[dict[str, Any]]:
    with get_connection() as connection:
        rows = connection.execute(
            """
            with first_snapshot as (
                select s.*
                from github_repo_snapshot s
                where s.id = (
                    select min(s2.id) from github_repo_snapshot s2 where s2.repo_id = s.repo_id
                )
            ),
            latest_snapshot as (
                select s.*
                from github_repo_snapshot s
                where s.id = (
                    select max(s2.id) from github_repo_snapshot s2 where s2.repo_id = s.repo_id
                )
            )
            select
                r.id,
                r.full_name,
                r.url,
                r.description,
                r.language,
                r.topics,
                r.license,
                latest_snapshot.stars as latest_stars,
                latest_snapshot.forks as latest_forks,
                latest_snapshot.open_issues as latest_open_issues,
                latest_snapshot.pushed_at as latest_pushed_at,
                latest_snapshot.captured_at as latest_captured_at,
                first_snapshot.stars as first_stars,
                first_snapshot.forks as first_forks,
                first_snapshot.captured_at as first_captured_at,
                latest_snapshot.stars - first_snapshot.stars as stars_delta,
                latest_snapshot.forks - first_snapshot.forks as forks_delta
            from github_repo r
            join first_snapshot on first_snapshot.repo_id = r.id
            join latest_snapshot on latest_snapshot.repo_id = r.id
            """
        ).fetchall()
        return [dict(row) for row in rows]

def list_top_signals(limit: int = 10) -> list[dict[str, Any]]:
    with get_connection() as connection:
        rows = connection.execute(
            """
            select id, title, url, source_type, summary, published_at, signal_score, status, raw_content
            from signal
            where status = 'discovered'
            order by signal_score desc, fetched_at desc, id desc
            limit ?
            """,
            (limit,),
        ).fetchall()
        return [dict(row) for row in rows]

def ensure_learning_task_for_signal(signal_id: int) -> int:
    with get_connection() as connection:
        existing = connection.execute(
            """
            select id
            from learning_task
            where signal_id = ? and task_type = 'knowledge_doc'
            order by id asc
            limit 1
            """,
            (signal_id,),
        ).fetchone()
        if existing:
            return int(existing["id"])

        signal = connection.execute(
            """
            select id, title, url, signal_score
            from signal
            where id = ?
            """,
            (signal_id,),
        ).fetchone()
        if signal is None:
            raise ValueError(f"Signal not found: {signal_id}")

        priority = "high" if float(signal["signal_score"] or 0) >= 50 else "medium"
        cursor = connection.execute(
            """
            insert into learning_task (
                signal_id, title, task_type, status, priority, source_url
            ) values (?, ?, 'knowledge_doc', 'pending', ?, ?)
            """,
            (signal["id"], signal["title"], priority, signal["url"]),
        )
        return int(cursor.lastrowid)

def ensure_today_tasks_from_top_signals(limit: int = 10) -> list[dict[str, Any]]:
    safe_limit = max(1, min(limit, 50))
    for signal in list_top_signals(limit=safe_limit):
        ensure_learning_task_for_signal(int(signal["id"]))
    return list_today_tasks(limit=safe_limit)

def list_today_tasks(limit: int = 10) -> list[dict[str, Any]]:
    safe_limit = max(1, min(limit, 50))
    with get_connection() as connection:
        rows = connection.execute(
            """
            select
                t.id,
                t.signal_id,
                t.title,
                t.task_type,
                t.status,
                t.priority,
                t.source_url,
                t.target_doc_path,
                t.selected_at,
                t.started_at,
                t.doc_submitted_at,
                t.reviewed_at,
                t.archived_at,
                t.created_at,
                t.updated_at,
                s.summary,
                s.signal_score,
                s.source_type,
                s.raw_content
            from learning_task t
            left join signal s on s.id = t.signal_id
            where t.task_type = 'knowledge_doc'
            order by
                case t.status
                    when 'pending' then 1
                    when 'pushed' then 2
                    when 'selected' then 3
                    when 'documented' then 4
                    when 'archived' then 5
                    when 'ignored' then 6
                    else 7
                end,
                s.signal_score desc,
                t.created_at desc,
                t.id desc
            limit ?
            """,
            (safe_limit,),
        ).fetchall()
        return [dict(row) for row in rows]

def today_task_summary(tasks: list[dict[str, Any]]) -> dict[str, Any]:
    counts = {status: 0 for status in TASK_STATUSES}
    for task in tasks:
        status = task.get("status") or "pending"
        if status in counts:
            counts[status] += 1

    done_count = counts["documented"] + counts["archived"] + counts["ignored"]
    actionable_count = max(0, len(tasks) - counts["ignored"])
    return {
        "total": len(tasks),
        "pending": counts["pending"],
        "pushed": counts["pushed"],
        "selected": counts["selected"],
        "documented": counts["documented"],
        "archived": counts["archived"],
        "ignored": counts["ignored"],
        "done_count": done_count,
        "actionable_count": actionable_count,
        "is_complete": actionable_count > 0 and done_count >= actionable_count,
    }

def update_learning_task_status(
    task_id: int,
    status: str,
    target_doc_path: str | None = None,
) -> dict[str, Any]:
    if status not in TASK_STATUSES:
        raise ValueError(f"Unsupported task status: {status}")

    timestamp_field = {
        "selected": "selected_at",
        "documented": "doc_submitted_at",
        "archived": "archived_at",
    }.get(status)

    with get_connection() as connection:
        task = connection.execute(
            "select id from learning_task where id = ?",
            (task_id,),
        ).fetchone()
        if task is None:
            raise ValueError(f"Task not found: {task_id}")

        if timestamp_field:
            connection.execute(
                f"""
                update learning_task
                set
                    status = ?,
                    target_doc_path = coalesce(?, target_doc_path),
                    {timestamp_field} = coalesce({timestamp_field}, CURRENT_TIMESTAMP),
                    updated_at = CURRENT_TIMESTAMP
                where id = ?
                """,
                (status, target_doc_path, task_id),
            )
        else:
            connection.execute(
                """
                update learning_task
                set
                    status = ?,
                    target_doc_path = coalesce(?, target_doc_path),
                    updated_at = CURRENT_TIMESTAMP
                where id = ?
                """,
                (status, target_doc_path, task_id),
            )

        row = connection.execute(
            """
            select
                t.id,
                t.signal_id,
                t.title,
                t.task_type,
                t.status,
                t.priority,
                t.source_url,
                t.target_doc_path,
                t.selected_at,
                t.started_at,
                t.doc_submitted_at,
                t.reviewed_at,
                t.archived_at,
                t.created_at,
                t.updated_at,
                s.summary,
                s.signal_score,
                s.source_type,
                s.raw_content
            from learning_task t
            left join signal s on s.id = t.signal_id
            where t.id = ?
            """,
            (task_id,),
        ).fetchone()
        return dict(row)

def init() -> None:
    init_database()




