from pathlib import Path
import json
import sys

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from apps.api.app.collectors.github import collect_github_search_source
from apps.api.app.db import database_status, init_database
from apps.api.app.repository import count_rows, list_recent_github_repos
from apps.api.app.sources import enabled_sources


def emit(value: object) -> None:
    print(json.dumps(value, ensure_ascii=True, default=str))


def main() -> None:
    init_database()
    results = []
    for source in enabled_sources("github_search"):
        results.append(collect_github_search_source(source, per_page=20))

    emit({"database": database_status(), "results": results})
    emit(
        {
            "repo_count": count_rows("github_repo"),
            "snapshot_count": count_rows("github_repo_snapshot"),
            "collector_run_count": count_rows("collector_run"),
        }
    )
    emit({"recent_repos": list_recent_github_repos(limit=10)})


if __name__ == "__main__":
    main()
