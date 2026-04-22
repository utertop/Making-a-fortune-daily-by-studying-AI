from pathlib import Path
import sys

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from apps.api.app.db import database_status, init_database
from apps.api.app.repository import (
    count_rows,
    create_collector_run,
    create_github_repo_snapshot,
    upsert_github_repo,
    upsert_source,
)


def main() -> None:
    init_database()

    source_id = upsert_source(
        {
            "name": "Phase 2 Smoke Source",
            "type": "github_search",
            "url": "https://api.github.com/search/repositories?q=AI+agent",
            "priority": "high",
            "enabled": True,
            "official": True,
            "tags": ["github", "smoke-test"],
            "allowlist_domain": "api.github.com",
        }
    )

    repo_id = upsert_github_repo(
        {
            "full_name": "example/ai-signal-radar-smoke",
            "url": "https://github.com/example/ai-signal-radar-smoke",
            "description": "Smoke test repo for AI Signal Radar",
            "language": "Python",
            "topics": ["ai", "agent"],
            "license": "MIT",
        }
    )

    snapshot_id = create_github_repo_snapshot(
        repo_id,
        {
            "stars": 123,
            "forks": 12,
            "open_issues": 3,
            "pushed_at": "2026-04-22T00:00:00Z",
        },
    )

    run_id = create_collector_run(
        {
            "source_id": source_id,
            "collector_type": "smoke_test",
            "status": "success",
            "fetched_count": 1,
            "created_signal_count": 0,
            "duration_ms": 10,
        }
    )

    print(database_status())
    print(
        {
            "source_id": source_id,
            "repo_id": repo_id,
            "snapshot_id": snapshot_id,
            "collector_run_id": run_id,
            "source_count": count_rows("source"),
            "repo_count": count_rows("github_repo"),
            "snapshot_count": count_rows("github_repo_snapshot"),
            "collector_run_count": count_rows("collector_run"),
        }
    )


if __name__ == "__main__":
    main()
