from __future__ import annotations

import sqlite3
from contextlib import closing, contextmanager
from pathlib import Path
from typing import Iterator

from .config import DATA_DIR, DATABASE_PATH

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
    "user_feedback",
)


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
        connection.commit()


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

