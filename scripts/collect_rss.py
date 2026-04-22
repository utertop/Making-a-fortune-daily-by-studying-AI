from pathlib import Path
import json
import sys

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from apps.api.app.collectors.rss import collect_rss_source
from apps.api.app.db import database_status, init_database
from apps.api.app.repository import count_rows, list_recent_signals
from apps.api.app.sources import enabled_sources


def emit(value: object) -> None:
    print(json.dumps(value, ensure_ascii=True, default=str))


def main() -> None:
    init_database()
    results = []
    for source in enabled_sources("rss"):
        results.append(collect_rss_source(source, max_entries=20))

    emit({"database": database_status(), "results": results})
    emit({"signal_count": count_rows("signal")})
    emit({"recent_signals": list_recent_signals(limit=10)})


if __name__ == "__main__":
    main()
