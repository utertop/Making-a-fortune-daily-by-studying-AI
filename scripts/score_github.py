from pathlib import Path
import json
import sys

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from apps.api.app.db import init_database
from apps.api.app.repository import list_github_repo_scoring_inputs, upsert_signal
from apps.api.app.scoring import score_github_repo


def emit(value: object) -> None:
    print(json.dumps(value, ensure_ascii=True, default=str))


def main() -> None:
    init_database()
    scored = [score_github_repo(repo) for repo in list_github_repo_scoring_inputs()]
    scored.sort(key=lambda item: item["score"], reverse=True)

    created_count = 0
    for item in scored[:10]:
        signal_id, created = upsert_signal(
            {
                "title": item["full_name"],
                "url": item["url"],
                "source_type": "github_repo",
                "raw_content": json.dumps(item, ensure_ascii=False),
                "summary": item.get("description"),
                "signal_score": item["score"],
                "velocity_score": min(max(item["stars_delta"], 0), 25),
                "relevance_score": 15 if any("ai_keyword_match" in reason for reason in item["reasons"]) else 0,
                "actionability_score": 5 if item.get("license") and item.get("license") != "NOASSERTION" else 0,
                "status": "discovered",
            }
        )
        item["signal_id"] = signal_id
        if created:
            created_count += 1

    emit({"created_signal_count": created_count, "top_repos": scored[:10]})


if __name__ == "__main__":
    main()
