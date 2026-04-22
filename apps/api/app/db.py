import sqlite3
from contextlib import closing

from .config import DATA_DIR, DATABASE_PATH


def ensure_database() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    with closing(sqlite3.connect(DATABASE_PATH)) as connection:
        connection.execute("select 1")


def database_status() -> dict:
    ensure_database()
    return {"path": str(DATABASE_PATH), "connected": True}
