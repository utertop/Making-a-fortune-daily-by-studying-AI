from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .db import get_connection, init_database
from .document_quality import evaluate_markdown_quality
from .markdown_drafts import resolve_knowledge_path

TASK_STATUSES = {
    "pending",
    "pushed",
    "selected",
    "draft_created",
    "review_pending",
    "documented",
    "archived",
    "ignored",
}

DETECTION_STATUSES = {
    "idle",
    "waiting_for_file",
    "waiting_for_update",
    "updated",
    "documented",
    "ignored",
    "archived",
}

TASK_SELECT_SQL = """
    select
        t.id,
        t.signal_id,
        t.title,
        t.task_type,
        t.status,
        t.priority,
        t.source_url,
        t.target_doc_path,
        t.generated_prompt,
        t.draft_created_at,
        t.draft_initial_hash,
        t.last_detected_hash,
        t.last_detected_at,
        t.review_pending_at,
        t.ignored_reason,
        t.detection_status,
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
        s.raw_content,
        d.id as document_id,
        d.title as document_title,
        d.path as document_path,
        d.summary as document_summary
    from learning_task t
    left join signal s on s.id = t.signal_id
    left join knowledge_document d on d.path = t.target_doc_path
"""


def _json_or_none(value: Any) -> str | None:
    if value is None:
        return None
    return json.dumps(value, ensure_ascii=False)


def _slugify(value: str) -> str:
    slug = re.sub(r"[^a-zA-Z0-9]+", "-", value.lower()).strip("-")
    return slug or "knowledge-doc"


def _fetch_task_row(connection, task_id: int) -> dict[str, Any]:
    row = connection.execute(
        f"""
        {TASK_SELECT_SQL}
        where t.id = ?
        """,
        (task_id,),
    ).fetchone()
    if row is None:
        raise ValueError(f"Task not found: {task_id}")
    return dict(row)


def _record_task_event(
    connection,
    task_id: int,
    event_type: str,
    previous_status: str | None = None,
    new_status: str | None = None,
    payload: dict[str, Any] | None = None,
) -> None:
    connection.execute(
        """
        insert into task_event (
            task_id, event_type, previous_status, new_status, payload
        ) values (?, ?, ?, ?, ?)
        """,
        (task_id, event_type, previous_status, new_status, _json_or_none(payload)),
    )


def _sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as file_handle:
        for chunk in iter(lambda: file_handle.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _iso_from_timestamp(timestamp: float) -> str:
    return datetime.fromtimestamp(timestamp, tz=timezone.utc).isoformat()


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
            "select id from source where name = ? and url = ?",
            (source["name"], source["url"]),
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
            "select id from github_repo where full_name = ?",
            (repo["full_name"],),
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
        "task_event",
    }
    if table not in allowed:
        raise ValueError(f"Unsupported table: {table}")
    with get_connection() as connection:
        row = connection.execute(f"select count(*) as count from {table}").fetchone()
        return int(row["count"])


def upsert_signal(signal: dict[str, Any]) -> tuple[int, bool]:
    with get_connection() as connection:
        existing = connection.execute(
            "select id from signal where url = ?",
            (signal["url"],),
        ).fetchone()
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
                fetched_at = coalesce(excluded.fetched_at, CURRENT_TIMESTAMP),
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
        row = connection.execute(
            "select id from signal where url = ?",
            (signal["url"],),
        ).fetchone()
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
                latest_snapshot.forks - first_snapshot.forks as forks_delta,
                case
                    when snapshot_24h.id is not null then latest_snapshot.stars - snapshot_24h.stars
                    else 0
                end as stars_delta_24h,
                case
                    when snapshot_24h.id is not null then latest_snapshot.forks - snapshot_24h.forks
                    else 0
                end as forks_delta_24h,
                case
                    when snapshot_7d.id is not null then latest_snapshot.stars - snapshot_7d.stars
                    else 0
                end as stars_delta_7d,
                case
                    when snapshot_7d.id is not null then latest_snapshot.forks - snapshot_7d.forks
                    else 0
                end as forks_delta_7d,
                case
                    when julianday(latest_snapshot.captured_at) - julianday(first_snapshot.captured_at) <= 2
                    then 1
                    else 0
                end as newly_seen,
                latest_task.status as latest_task_status
            from github_repo r
            join first_snapshot on first_snapshot.repo_id = r.id
            join latest_snapshot on latest_snapshot.repo_id = r.id
            left join github_repo_snapshot snapshot_24h on snapshot_24h.id = (
                select max(s2.id)
                from github_repo_snapshot s2
                where
                    s2.repo_id = r.id
                    and julianday(s2.captured_at) <= julianday(latest_snapshot.captured_at) - 1
                    and julianday(s2.captured_at) >= julianday(latest_snapshot.captured_at) - 2
            )
            left join github_repo_snapshot snapshot_7d on snapshot_7d.id = (
                select max(s2.id)
                from github_repo_snapshot s2
                where
                    s2.repo_id = r.id
                    and julianday(s2.captured_at) <= julianday(latest_snapshot.captured_at) - 7
                    and julianday(s2.captured_at) >= julianday(latest_snapshot.captured_at) - 10
            )
            left join signal gs on gs.url = r.url
            left join learning_task latest_task on latest_task.id = (
                select max(t2.id)
                from learning_task t2
                where t2.signal_id = gs.id
            )
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


def list_signal_digest_candidates(github_limit: int = 30, source_limit: int = 10) -> list[dict[str, Any]]:
    with get_connection() as connection:
        github_rows = connection.execute(
            """
            select
                s.id,
                s.title,
                s.url,
                s.source_type,
                s.summary,
                s.published_at,
                s.fetched_at,
                s.signal_score,
                s.status,
                s.raw_content,
                latest_task.id as task_id,
                latest_task.status as task_status,
                latest_task.created_at as task_created_at,
                latest_task.updated_at as task_updated_at,
                latest_task.doc_submitted_at as task_doc_submitted_at,
                latest_task.archived_at as task_archived_at,
                latest_task.ignored_reason as task_ignored_reason
            from signal s
            left join learning_task latest_task on latest_task.id = (
                select max(t2.id)
                from learning_task t2
                where t2.signal_id = s.id
            )
            where s.status = 'discovered' and s.source_type = 'github_repo'
            order by s.signal_score desc, s.fetched_at desc, s.id desc
            limit ?
            """,
            (max(1, min(github_limit, 100)),),
        ).fetchall()
        source_rows = connection.execute(
            """
            select
                s.id,
                s.title,
                s.url,
                s.source_type,
                s.summary,
                s.published_at,
                s.fetched_at,
                s.signal_score,
                s.status,
                s.raw_content,
                latest_task.id as task_id,
                latest_task.status as task_status,
                latest_task.created_at as task_created_at,
                latest_task.updated_at as task_updated_at,
                latest_task.doc_submitted_at as task_doc_submitted_at,
                latest_task.archived_at as task_archived_at,
                latest_task.ignored_reason as task_ignored_reason
            from signal s
            left join learning_task latest_task on latest_task.id = (
                select max(t2.id)
                from learning_task t2
                where t2.signal_id = s.id
            )
            where s.status = 'discovered' and coalesce(s.source_type, '') != 'github_repo'
            order by coalesce(s.published_at, s.fetched_at) desc, s.signal_score desc, s.id desc
            limit ?
            """,
            (max(1, min(source_limit, 50)),),
        ).fetchall()

    candidates: list[dict[str, Any]] = []
    seen_urls: set[str] = set()
    for row in [*github_rows, *source_rows]:
        item = dict(row)
        url = str(item.get("url") or "")
        if url in seen_urls:
            continue
        candidates.append(item)
        seen_urls.add(url)
    return candidates


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
                signal_id, title, task_type, status, priority, source_url, detection_status
            ) values (?, ?, 'knowledge_doc', 'pending', ?, ?, 'idle')
            """,
            (signal["id"], signal["title"], priority, signal["url"]),
        )
        task_id = int(cursor.lastrowid)
        _record_task_event(
            connection,
            task_id=task_id,
            event_type="task_created",
            new_status="pending",
            payload={"signal_id": signal_id},
        )
        return task_id


def ensure_today_tasks_from_top_signals(limit: int = 10) -> list[dict[str, Any]]:
    safe_limit = max(1, min(limit, 50))
    for signal in list_top_signals(limit=safe_limit):
        ensure_learning_task_for_signal(int(signal["id"]))
    return list_today_tasks(limit=safe_limit)


def list_today_tasks(limit: int = 10) -> list[dict[str, Any]]:
    safe_limit = max(1, min(limit, 50))
    with get_connection() as connection:
        rows = connection.execute(
            f"""
            {TASK_SELECT_SQL}
            where t.task_type = 'knowledge_doc'
            order by
                case t.status
                    when 'pending' then 1
                    when 'pushed' then 2
                    when 'selected' then 3
                    when 'draft_created' then 4
                    when 'review_pending' then 5
                    when 'documented' then 6
                    when 'archived' then 7
                    when 'ignored' then 8
                    else 9
                end,
                s.signal_score desc,
                t.created_at desc,
                t.id desc
            limit ?
            """,
            (safe_limit,),
        ).fetchall()
        return [dict(row) for row in rows]


def get_learning_tasks_by_ids(task_ids: list[int]) -> list[dict[str, Any]]:
    unique_ids: list[int] = []
    seen: set[int] = set()
    for task_id in task_ids:
        if task_id not in seen:
            unique_ids.append(task_id)
            seen.add(task_id)

    if not unique_ids:
        return []

    placeholders = ", ".join("?" for _ in unique_ids)
    with get_connection() as connection:
        rows = connection.execute(
            f"""
            {TASK_SELECT_SQL}
            where t.id in ({placeholders})
            """,
            unique_ids,
        ).fetchall()
        row_by_id = {int(row["id"]): dict(row) for row in rows}
        return [row_by_id[task_id] for task_id in unique_ids if task_id in row_by_id]


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
        "draft_created": counts["draft_created"],
        "review_pending": counts["review_pending"],
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
    ignored_reason: str | None = None,
) -> dict[str, Any]:
    if status not in TASK_STATUSES:
        raise ValueError(f"Unsupported task status: {status}")
    if status == "ignored" and not (ignored_reason or "").strip():
        raise ValueError("Ignored tasks require a reason")

    with get_connection() as connection:
        current = _fetch_task_row(connection, task_id)
        previous_status = current["status"]
        normalized_reason = ignored_reason.strip() if ignored_reason else None
        next_target_doc_path = target_doc_path or current.get("target_doc_path")

        if (
            previous_status == status
            and next_target_doc_path == current.get("target_doc_path")
            and normalized_reason == current.get("ignored_reason")
        ):
            return current

        updates = [
            "status = ?",
            "target_doc_path = coalesce(?, target_doc_path)",
            "updated_at = CURRENT_TIMESTAMP",
        ]
        params: list[Any] = [status, target_doc_path]

        detection_status = current.get("detection_status") or "idle"
        if status == "selected":
            updates.append("selected_at = coalesce(selected_at, CURRENT_TIMESTAMP)")
            detection_status = "idle"
        elif status == "draft_created":
            updates.append("draft_created_at = coalesce(draft_created_at, CURRENT_TIMESTAMP)")
            updates.append("started_at = coalesce(started_at, CURRENT_TIMESTAMP)")
            updates.append("selected_at = coalesce(selected_at, CURRENT_TIMESTAMP)")
            detection_status = "waiting_for_update"
        elif status == "review_pending":
            updates.append("review_pending_at = coalesce(review_pending_at, CURRENT_TIMESTAMP)")
            detection_status = "updated"
        elif status == "documented":
            updates.append("doc_submitted_at = coalesce(doc_submitted_at, CURRENT_TIMESTAMP)")
            detection_status = "documented"
        elif status == "archived":
            updates.append("archived_at = coalesce(archived_at, CURRENT_TIMESTAMP)")
            detection_status = "archived"
        elif status == "ignored":
            updates.append("ignored_reason = ?")
            params.append(normalized_reason)
            detection_status = "ignored"

        updates.append("detection_status = ?")
        params.append(detection_status)
        params.append(task_id)

        connection.execute(
            f"""
            update learning_task
            set {", ".join(updates)}
            where id = ?
            """,
            params,
        )
        _record_task_event(
            connection,
            task_id=task_id,
            event_type="status_changed",
            previous_status=previous_status,
            new_status=status,
            payload={
                "target_doc_path": next_target_doc_path,
                "ignored_reason": normalized_reason,
                "detection_status": detection_status,
            },
        )
        return _fetch_task_row(connection, task_id)


def get_task_for_markdown_draft(task_id: int) -> dict[str, Any]:
    with get_connection() as connection:
        row = connection.execute(
            """
            select
                t.id,
                t.signal_id,
                t.title,
                t.status,
                t.source_url,
                t.target_doc_path,
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
        if row is None:
            raise ValueError(f"Task not found: {task_id}")
        return dict(row)


def attach_draft_document_to_task(
    task_id: int,
    title: str,
    path: str,
    content: str,
    summary: str | None = None,
    tags: list[str] | None = None,
) -> dict[str, Any]:
    clean_title = title.strip()
    clean_path = path.strip()
    if not clean_title:
        raise ValueError("Document title is required")
    if not clean_path:
        raise ValueError("Document path is required")

    draft_hash = _sha256_text(content)
    with get_connection() as connection:
        task = connection.execute(
            """
            select id, status, source_url
            from learning_task
            where id = ?
            """,
            (task_id,),
        ).fetchone()
        if task is None:
            raise ValueError(f"Task not found: {task_id}")

        existing_document = connection.execute(
            "select slug from knowledge_document where path = ?",
            (clean_path,),
        ).fetchone()
        slug = existing_document["slug"] if existing_document else f"{_slugify(clean_title)}-{task_id}"

        connection.execute(
            """
            insert into knowledge_document (
                title, slug, type, path, source_url, content, summary,
                tags, confidence, created_by_agent
            ) values (?, ?, 'project_note', ?, ?, ?, ?, ?, 'draft', 'template')
            on conflict(path) do update set
                title = excluded.title,
                source_url = excluded.source_url,
                content = excluded.content,
                summary = excluded.summary,
                tags = excluded.tags,
                confidence = excluded.confidence,
                created_by_agent = excluded.created_by_agent,
                updated_at = CURRENT_TIMESTAMP
            """,
            (
                clean_title,
                slug,
                clean_path,
                task["source_url"],
                content,
                summary,
                _json_or_none(tags or ["ai", "github", "signal"]),
            ),
        )

        previous_status = task["status"]
        connection.execute(
            """
            update learning_task
            set
                status = 'draft_created',
                target_doc_path = ?,
                draft_created_at = CURRENT_TIMESTAMP,
                draft_initial_hash = ?,
                last_detected_hash = null,
                last_detected_at = null,
                review_pending_at = null,
                selected_at = coalesce(selected_at, CURRENT_TIMESTAMP),
                started_at = coalesce(started_at, CURRENT_TIMESTAMP),
                detection_status = 'waiting_for_update',
                updated_at = CURRENT_TIMESTAMP
            where id = ?
            """,
            (clean_path, draft_hash, task_id),
        )
        _record_task_event(
            connection,
            task_id=task_id,
            event_type="draft_created",
            previous_status=previous_status,
            new_status="draft_created",
            payload={
                "path": clean_path,
                "draft_initial_hash": draft_hash,
            },
        )
        return _fetch_task_row(connection, task_id)


def submit_knowledge_document_for_task(
    task_id: int,
    title: str,
    path: str,
    summary: str | None = None,
    tags: list[str] | None = None,
    confidence: str | None = None,
    content: str | None = None,
    created_by_agent: str | None = None,
) -> dict[str, Any]:
    clean_title = title.strip()
    clean_path = path.strip()
    if not clean_title:
        raise ValueError("Document title is required")
    if not clean_path:
        raise ValueError("Document path is required")

    quality_content = content
    if quality_content is None:
        try:
            resolved_path = resolve_knowledge_path(clean_path)
            if resolved_path.exists():
                quality_content = resolved_path.read_text(encoding="utf-8")
        except ValueError:
            quality_content = None

    with get_connection() as connection:
        task = connection.execute(
            """
            select id, title, source_url, status
            from learning_task
            where id = ?
            """,
            (task_id,),
        ).fetchone()
        if task is None:
            raise ValueError(f"Task not found: {task_id}")

        existing_document = connection.execute(
            "select id, slug from knowledge_document where path = ?",
            (clean_path,),
        ).fetchone()
        slug = existing_document["slug"] if existing_document else f"{_slugify(clean_title)}-{task_id}"

        connection.execute(
            """
            insert into knowledge_document (
                title, slug, type, path, source_url, content, summary,
                tags, confidence, created_by_agent
            ) values (?, ?, 'project_note', ?, ?, ?, ?, ?, ?, ?)
            on conflict(path) do update set
                title = excluded.title,
                source_url = excluded.source_url,
                content = excluded.content,
                summary = excluded.summary,
                tags = excluded.tags,
                confidence = excluded.confidence,
                created_by_agent = excluded.created_by_agent,
                updated_at = CURRENT_TIMESTAMP
            """,
            (
                clean_title,
                slug,
                clean_path,
                task["source_url"],
                content,
                summary,
                _json_or_none(tags),
                confidence,
                created_by_agent,
            ),
        )

        previous_status = task["status"]
        quality = evaluate_markdown_quality(quality_content, source_url=task["source_url"])
        connection.execute(
            """
            update learning_task
            set
                status = 'documented',
                target_doc_path = ?,
                doc_submitted_at = coalesce(doc_submitted_at, CURRENT_TIMESTAMP),
                detection_status = 'documented',
                updated_at = CURRENT_TIMESTAMP
            where id = ?
            """,
            (clean_path, task_id),
        )
        _record_task_event(
            connection,
            task_id=task_id,
            event_type="document_confirmed",
            previous_status=previous_status,
            new_status="documented",
            payload={
                "path": clean_path,
                "confidence": confidence,
                "created_by_agent": created_by_agent,
                "document_quality": quality,
            },
        )
        result = _fetch_task_row(connection, task_id)
        result["document_quality"] = quality
        return result


def detect_document_for_task(task_id: int) -> dict[str, Any]:
    with get_connection() as connection:
        task = _fetch_task_row(connection, task_id)
        current_status = task["status"]
        if current_status in {"documented", "ignored", "archived"}:
            detection_status = {
                "documented": "documented",
                "ignored": "ignored",
                "archived": "archived",
            }[current_status]
            connection.execute(
                """
                update learning_task
                set detection_status = ?, updated_at = CURRENT_TIMESTAMP
                where id = ?
                """,
                (detection_status, task_id),
            )
            refreshed = _fetch_task_row(connection, task_id)
            return {"task": refreshed, "changed": False, "reason": detection_status}

        target_doc_path = task.get("target_doc_path")
        if not target_doc_path:
            connection.execute(
                """
                update learning_task
                set detection_status = 'idle', updated_at = CURRENT_TIMESTAMP
                where id = ?
                """,
                (task_id,),
            )
            refreshed = _fetch_task_row(connection, task_id)
            return {"task": refreshed, "changed": False, "reason": "no_target_doc_path"}

        resolved_path = resolve_knowledge_path(target_doc_path)
        if not resolved_path.exists():
            connection.execute(
                """
                update learning_task
                set detection_status = 'waiting_for_file', updated_at = CURRENT_TIMESTAMP
                where id = ?
                """,
                (task_id,),
            )
            refreshed = _fetch_task_row(connection, task_id)
            return {"task": refreshed, "changed": False, "reason": "missing_file"}

        current_hash = _sha256_file(resolved_path)
        draft_initial_hash = task.get("draft_initial_hash")
        modified_at = _iso_from_timestamp(resolved_path.stat().st_mtime)
        draft_created_at = task.get("draft_created_at")
        has_real_update = current_hash != draft_initial_hash
        if draft_created_at:
            has_real_update = has_real_update and modified_at > draft_created_at

        if not has_real_update:
            connection.execute(
                """
                update learning_task
                set
                    detection_status = 'waiting_for_update',
                    updated_at = CURRENT_TIMESTAMP
                where id = ?
                """,
                (task_id,),
            )
            refreshed = _fetch_task_row(connection, task_id)
            return {"task": refreshed, "changed": False, "reason": "waiting_for_update"}

        previous_status = current_status
        changed = current_status != "review_pending" or task.get("last_detected_hash") != current_hash
        connection.execute(
            """
            update learning_task
            set
                status = 'review_pending',
                review_pending_at = coalesce(review_pending_at, CURRENT_TIMESTAMP),
                last_detected_hash = ?,
                last_detected_at = ?,
                detection_status = 'updated',
                updated_at = CURRENT_TIMESTAMP
            where id = ?
            """,
            (current_hash, modified_at, task_id),
        )
        if changed:
            _record_task_event(
                connection,
                task_id=task_id,
                event_type="document_detected",
                previous_status=previous_status,
                new_status="review_pending",
                payload={
                    "path": target_doc_path,
                    "last_detected_hash": current_hash,
                    "last_detected_at": modified_at,
                },
            )
        refreshed = _fetch_task_row(connection, task_id)
        return {"task": refreshed, "changed": changed, "reason": "review_pending"}


def detect_documents(limit: int = 50) -> dict[str, Any]:
    safe_limit = max(1, min(limit, 200))
    with get_connection() as connection:
        rows = connection.execute(
            f"""
            {TASK_SELECT_SQL}
            where
                t.task_type = 'knowledge_doc'
                and t.status in ('selected', 'draft_created', 'review_pending')
                and t.target_doc_path is not null
            order by t.updated_at desc, t.id desc
            limit ?
            """,
            (safe_limit,),
        ).fetchall()
        task_ids = [int(row["id"]) for row in rows]

    results = [detect_document_for_task(task_id) for task_id in task_ids]
    changed_tasks = [result["task"] for result in results if result["changed"]]
    return {
        "checked": len(results),
        "changed": len(changed_tasks),
        "tasks": changed_tasks,
        "results": results,
    }


def init() -> None:
    init_database()
