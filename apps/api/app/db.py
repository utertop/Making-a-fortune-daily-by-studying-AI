from __future__ import annotations

import json
import re
import sqlite3
from contextlib import closing, contextmanager
from pathlib import Path
from typing import Iterator

from .config import DATA_DIR, DATABASE_PATH, KNOWLEDGE_BASE_DIR

SCHEMA_PATH = Path(__file__).with_name("schema.sql")
REQUIRED_TABLES = (
    "source",
    "signal",
    "entity",
    "github_repo",
    "github_repo_snapshot",
    "learning_task",
    "knowledge_document",
    "collector_run",
    "reminder",
    "task_event",
    "user_feedback",
)

LEARNING_TASK_COLUMNS = {
    "draft_created_at": "ALTER TABLE learning_task ADD COLUMN draft_created_at TEXT",
    "draft_initial_hash": "ALTER TABLE learning_task ADD COLUMN draft_initial_hash TEXT",
    "last_detected_hash": "ALTER TABLE learning_task ADD COLUMN last_detected_hash TEXT",
    "last_detected_at": "ALTER TABLE learning_task ADD COLUMN last_detected_at TEXT",
    "review_pending_at": "ALTER TABLE learning_task ADD COLUMN review_pending_at TEXT",
    "ignored_reason": "ALTER TABLE learning_task ADD COLUMN ignored_reason TEXT",
    "detection_status": "ALTER TABLE learning_task ADD COLUMN detection_status TEXT",
}

DEEP_DOSSIER_SUFFIX = "深度项目知识档案"
LEGACY_NOTE_SUFFIX = "技术笔记"


def connect() -> sqlite3.Connection:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(DATABASE_PATH)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


@contextmanager
def get_connection() -> Iterator[sqlite3.Connection]:
    connection = connect()
    try:
        yield connection
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()


def init_database() -> None:
    with closing(connect()) as connection:
        schema = SCHEMA_PATH.read_text(encoding="utf-8-sig")
        connection.executescript(schema)
        _apply_migrations(connection)
        connection.commit()


def _apply_migrations(connection: sqlite3.Connection) -> None:
    existing_columns = {
        row["name"]
        for row in connection.execute("PRAGMA table_info(learning_task)").fetchall()
    }
    for column, statement in LEARNING_TASK_COLUMNS.items():
        if column not in existing_columns:
            connection.execute(statement)

    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS task_event (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            task_id INTEGER NOT NULL,
            event_type TEXT NOT NULL,
            previous_status TEXT,
            new_status TEXT,
            payload TEXT,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(task_id) REFERENCES learning_task(id)
        )
        """
    )
    connection.execute(
        "CREATE INDEX IF NOT EXISTS idx_learning_task_detection_status ON learning_task(detection_status)"
    )
    connection.execute(
        "CREATE INDEX IF NOT EXISTS idx_task_event_task_time ON task_event(task_id, created_at DESC)"
    )
    _migrate_legacy_deep_dossier_records(connection)


def _slugify(value: str) -> str:
    slug = re.sub(r"[^a-zA-Z0-9]+", "-", value.lower()).strip("-")
    return slug or "knowledge-doc"


def _canonical_deep_dossier_path(title: str, task_id: int, current_path: str) -> str:
    clean_path = (current_path or "").strip().replace("\\", "/")
    if clean_path.startswith("knowledge-base/"):
        relative_path = clean_path[len("knowledge-base/") :]
    else:
        relative_path = clean_path

    parent = Path(relative_path).parent
    if not str(parent) or str(parent) == ".":
        parent = Path("daily")

    return (
        "knowledge-base/"
        f"{parent.as_posix()}/"
        f"{_slugify(title)}-deep-dossier-{task_id}.md"
    )


def _clean_document_title(value: str | None) -> str:
    clean_title = (value or "").strip()
    clean_title = clean_title.replace("???????", "").replace("????????", "").strip()
    clean_title = re.sub(r"[?？�]+", " ", clean_title).strip()
    if clean_title.endswith(DEEP_DOSSIER_SUFFIX):
        clean_title = clean_title[: -len(DEEP_DOSSIER_SUFFIX)].strip()
    if clean_title.endswith(LEGACY_NOTE_SUFFIX):
        clean_title = clean_title[: -len(LEGACY_NOTE_SUFFIX)].strip()
    return clean_title


def _deep_document_title(task_title: str, current_title: str | None = None) -> str:
    base_title = _clean_document_title(current_title) or task_title.strip()
    return f"{base_title} {DEEP_DOSSIER_SUFFIX}"


def _migrate_legacy_deep_dossier_records(connection: sqlite3.Connection) -> None:
    rows = connection.execute(
        """
        select
            t.id,
            t.title,
            t.target_doc_path,
            d.id as document_id,
            d.path as document_path,
            d.title as document_title
        from learning_task t
        left join knowledge_document d on d.path = t.target_doc_path
        where t.target_doc_path is not null
          and t.target_doc_path <> ''
        """
    ).fetchall()

    repo_root = KNOWLEDGE_BASE_DIR.parent.resolve()

    for row in rows:
        current_path = row["target_doc_path"]
        task_title = row["title"]
        task_id = int(row["id"])
        canonical_path = _canonical_deep_dossier_path(task_title, task_id, current_path)
        path_changed = canonical_path != current_path

        old_absolute = (repo_root / current_path).resolve()
        new_absolute = (repo_root / canonical_path).resolve()
        old_exists = old_absolute.exists()
        new_exists = new_absolute.exists()

        if path_changed and old_exists and not new_exists:
            new_absolute.parent.mkdir(parents=True, exist_ok=True)
            old_absolute.replace(new_absolute)
            new_exists = True

        document_id = row["document_id"]
        title_changed = False
        if document_id is not None:
            deep_title = _deep_document_title(task_title, row["document_title"])
            existing_canonical_doc = connection.execute(
                "select id from knowledge_document where path = ?",
                (canonical_path,),
            ).fetchone()

            if existing_canonical_doc is None:
                connection.execute(
                    """
                    update knowledge_document
                    set path = ?, title = ?, updated_at = CURRENT_TIMESTAMP
                    where id = ?
                    """,
                    (canonical_path, deep_title, document_id),
                )
                title_changed = row["document_title"] != deep_title
            elif int(existing_canonical_doc["id"]) != int(document_id):
                connection.execute(
                    """
                    update knowledge_document
                    set title = ?, updated_at = CURRENT_TIMESTAMP
                    where id = ?
                    """,
                    (deep_title, int(existing_canonical_doc["id"])),
                )
                connection.execute("delete from knowledge_document where id = ?", (document_id,))
                title_changed = True
            else:
                connection.execute(
                    """
                    update knowledge_document
                    set title = ?, updated_at = CURRENT_TIMESTAMP
                    where id = ?
                    """,
                    (deep_title, document_id),
                )
                title_changed = row["document_title"] != deep_title

        if path_changed:
            connection.execute(
                """
                update learning_task
                set target_doc_path = ?, updated_at = CURRENT_TIMESTAMP
                where id = ?
                """,
                (canonical_path, task_id),
            )

        if path_changed or title_changed:
            connection.execute(
                """
                insert into task_event (
                    task_id, event_type, previous_status, new_status, payload
                ) values (?, ?, ?, ?, ?)
                """,
                (
                    task_id,
                    "path_migrated" if path_changed else "title_normalized",
                    None,
                    None,
                    json.dumps(
                        {
                            "from": current_path,
                            "to": canonical_path,
                            "title": _deep_document_title(task_title, row["document_title"]),
                            "old_exists": old_exists,
                            "new_exists": new_exists,
                        },
                        ensure_ascii=False,
                    ),
                ),
            )


def ensure_database() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    init_database()


def list_tables() -> list[str]:
    with closing(connect()) as connection:
        rows = connection.execute(
            "select name from sqlite_master where type = 'table' and name not like 'sqlite_%' order by name"
        ).fetchall()
    return [row["name"] for row in rows]


def database_status() -> dict:
    ensure_database()
    tables = list_tables()
    missing_tables = [table for table in REQUIRED_TABLES if table not in tables]
    return {
        "path": str(DATABASE_PATH),
        "connected": True,
        "initialized": not missing_tables,
        "tables": tables,
        "missing_tables": missing_tables,
    }
