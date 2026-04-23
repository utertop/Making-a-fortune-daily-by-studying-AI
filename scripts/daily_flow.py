from pathlib import Path
import argparse
import json
import sys
import time
from typing import Callable

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from apps.api.app.collectors.github import collect_github_search_source
from apps.api.app.collectors.rss import collect_rss_source
from apps.api.app.db import database_status, init_database
from apps.api.app.push.feishu import build_today_task_text, send_feishu_text
from apps.api.app.repository import (
    count_rows,
    ensure_today_tasks_from_top_signals,
    list_github_repo_scoring_inputs,
    list_top_signals,
    today_task_summary,
    upsert_signal,
)
from apps.api.app.scoring import score_github_repo
from apps.api.app.sources import enabled_sources


def emit(event: str, payload: object) -> None:
    print(json.dumps({"event": event, "payload": payload}, ensure_ascii=True, default=str))


def timed_step(name: str, action: Callable[[], object]) -> object:
    started_at = time.perf_counter()
    emit("step_started", {"step": name})
    try:
        result = action()
    except Exception as error:
        emit("step_failed", {"step": name, "error": str(error)})
        raise

    emit(
        "step_finished",
        {
            "step": name,
            "duration_ms": int((time.perf_counter() - started_at) * 1000),
            "result": result,
        },
    )
    return result


def collect_rss(max_entries: int) -> dict:
    results = [collect_rss_source(source, max_entries=max_entries) for source in enabled_sources("rss")]
    return {"source_count": len(results), "results": results, "signal_count": count_rows("signal")}


def collect_github(per_page: int) -> dict:
    results = [
        collect_github_search_source(source, per_page=per_page)
        for source in enabled_sources("github_search")
    ]
    return {
        "source_count": len(results),
        "results": results,
        "repo_count": count_rows("github_repo"),
        "snapshot_count": count_rows("github_repo_snapshot"),
    }


def score_github(limit: int) -> dict:
    scored = [score_github_repo(repo) for repo in list_github_repo_scoring_inputs()]
    scored.sort(key=lambda item: item["score"], reverse=True)

    created_count = 0
    for item in scored[:limit]:
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

    return {"created_signal_count": created_count, "top_repos": scored[:limit]}


def prepare_today_tasks(limit: int) -> dict:
    tasks = ensure_today_tasks_from_top_signals(limit=limit)
    return {"task_count": len(tasks), "summary": today_task_summary(tasks)}


def push_today(limit: int, send: bool) -> dict:
    signals = list_top_signals(limit=limit)
    text = build_today_task_text(signals)
    if not send:
        return {"dry_run": True, "signal_count": len(signals), "text": text}
    return {"dry_run": False, "signal_count": len(signals), "response": send_feishu_text(text)}


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the local daily AI Signal Radar workflow.")
    parser.add_argument("--skip-rss", action="store_true", help="Skip RSS collection")
    parser.add_argument("--skip-github", action="store_true", help="Skip GitHub collection")
    parser.add_argument("--skip-push", action="store_true", help="Skip Feishu preview/send step")
    parser.add_argument("--send", action="store_true", help="Actually send Feishu message")
    parser.add_argument("--rss-max-entries", type=int, default=20, help="Max RSS entries per source")
    parser.add_argument("--github-per-page", type=int, default=20, help="GitHub search result count per source")
    parser.add_argument("--limit", type=int, default=10, help="Top signal/task limit")
    args = parser.parse_args()

    timed_step("init_database", init_database)
    emit("database", database_status())

    if not args.skip_rss:
        timed_step("collect_rss", lambda: collect_rss(args.rss_max_entries))

    if not args.skip_github:
        timed_step("collect_github", lambda: collect_github(args.github_per_page))
        timed_step("score_github", lambda: score_github(args.limit))

    timed_step("prepare_today_tasks", lambda: prepare_today_tasks(args.limit))

    if not args.skip_push:
        timed_step("push_today", lambda: push_today(args.limit, args.send))

    emit(
        "done",
        {
            "workspace_url": "http://127.0.0.1:3100",
            "api_url": "http://127.0.0.1:8000",
            "sent": args.send and not args.skip_push,
        },
    )


if __name__ == "__main__":
    main()
