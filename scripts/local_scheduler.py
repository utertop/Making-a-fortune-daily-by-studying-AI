from __future__ import annotations

import argparse
import json
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS_DIR = REPO_ROOT / "scripts"
sys.path.insert(0, str(REPO_ROOT))
sys.path.insert(0, str(SCRIPTS_DIR))

from apps.api.app.db import init_database
from apps.api.app.push.feishu import build_today_task_text, send_feishu_text
from apps.api.app.repository import (
    ensure_learning_task_for_signal,
    get_learning_tasks_by_ids,
    list_signal_digest_candidates,
    list_today_tasks,
    update_learning_task_status,
)
from daily_flow import collect_github, collect_rss, prepare_today_tasks, score_github

SHANGHAI_TZ = timezone(timedelta(hours=8))
STATE_PATH = REPO_ROOT / "data" / "local_scheduler_state.json"
WORKSPACE_URL = "http://127.0.0.1:3100"
TASK_DONE_STATUSES = {"documented", "archived", "ignored"}
MORNING_JOB = "morning_push"
AFTERNOON_JOB = "afternoon_push"
SOFT_DEADLINE_JOB = "soft_deadline"
HARD_DEADLINE_JOB = "hard_deadline"
LOGIN_CATCHUP_JOB = "login_catchup"
GRACE_MINUTES = 15

JOB_SCHEDULES = {
    MORNING_JOB: (8, 0),
    AFTERNOON_JOB: (14, 0),
    SOFT_DEADLINE_JOB: (21, 30),
    HARD_DEADLINE_JOB: (23, 0),
}

SCHEDULED_JOBS = (MORNING_JOB, AFTERNOON_JOB, SOFT_DEADLINE_JOB, HARD_DEADLINE_JOB)


def now_shanghai() -> datetime:
    return datetime.now(SHANGHAI_TZ)


def log(message: str) -> None:
    timestamp = now_shanghai().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[scheduler {timestamp}] {message}", flush=True)


def load_state() -> dict[str, Any]:
    if not STATE_PATH.exists():
        return {"last_run": {}, "carryover": None}
    try:
        return json.loads(STATE_PATH.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {"last_run": {}, "carryover": None}


def save_state(state: dict[str, Any]) -> None:
    STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    STATE_PATH.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")


def is_weekend(current: datetime) -> bool:
    return current.weekday() >= 5


def limit_for_job(job_name: str, current: datetime) -> int:
    weekend = is_weekend(current)
    if job_name == MORNING_JOB:
        return 5 if weekend else 10
    if job_name == AFTERNOON_JOB:
        return 3 if weekend else 5
    return 10


def should_run_job(state: dict[str, Any], job_name: str, current: datetime) -> bool:
    hour, minute = JOB_SCHEDULES[job_name]
    scheduled = current.replace(hour=hour, minute=minute, second=0, microsecond=0)
    already_ran = state.get("last_run", {}).get(job_name) == current.date().isoformat()
    return not already_ran and scheduled <= current < scheduled + timedelta(minutes=GRACE_MINUTES)


def find_missed_jobs(state: dict[str, Any], current: datetime) -> list[str]:
    today = current.date().isoformat()
    missed: list[tuple[datetime, str]] = []
    for job_name in SCHEDULED_JOBS:
        hour, minute = JOB_SCHEDULES[job_name]
        scheduled = current.replace(hour=hour, minute=minute, second=0, microsecond=0)
        already_ran = state.get("last_run", {}).get(job_name) == today
        if not already_ran and current >= scheduled:
            missed.append((scheduled, job_name))
    missed.sort(key=lambda item: item[0])
    return [job_name for _, job_name in missed]


def run_collection_pipeline(limit: int) -> None:
    collect_rss(max_entries=20)
    collect_github(per_page=20)
    score_github(limit=max(limit, 10))
    prepare_today_tasks(limit=max(limit, 10))


def ensure_top_signal_tasks_pushed(signals: list[dict[str, Any]]) -> list[int]:
    signal_ids = [int(signal["id"]) for signal in signals if signal.get("id") is not None]
    for signal_id in signal_ids:
        ensure_learning_task_for_signal(signal_id)

    tasks = list_today_tasks(limit=50)
    tasks_by_signal = {
        int(task["signal_id"]): task
        for task in tasks
        if task.get("signal_id") is not None
    }

    pushed_task_ids: list[int] = []
    for signal_id in signal_ids:
        task = tasks_by_signal.get(signal_id)
        if not task:
            continue
        if task["status"] == "pending":
            update_learning_task_status(int(task["id"]), "pushed")
            pushed_task_ids.append(int(task["id"]))
    return pushed_task_ids


def build_signal_digest_text(
    *,
    title: str,
    subtitle: str,
    signals: list[dict[str, Any]],
    carryover_lines: list[str] | None = None,
) -> str:
    lines = [
        title,
        subtitle,
        "",
    ]
    if carryover_lines:
        lines.extend(["昨日未完成提醒：", *carryover_lines, ""])

    lines.extend(
        [
            "今天建议：",
            "1. 从候选信号中选择 1 到 3 条深挖",
            "2. 至少确认提交 1 篇深度知识库文档",
            "",
            "Top Signals：",
        ]
    )

    for index, signal in enumerate(signals, start=1):
        score = int(signal.get("signal_score") or 0)
        lines.append(f"{index}. [{score}] {signal['title']}")
        lines.append(f"   {signal['url']}")

    lines.extend(["", "入口：", WORKSPACE_URL])
    return "\n".join(lines)


def categorize_tasks(tasks: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    return {
        "done": [task for task in tasks if task["status"] in TASK_DONE_STATUSES],
        "follow_up": [
            task
            for task in tasks
            if task["status"] in {"selected", "draft_created", "review_pending"}
        ],
        "undecided": [task for task in tasks if task["status"] in {"pending", "pushed"}],
    }


def status_label(status: str) -> str:
    labels = {
        "pending": "待决策",
        "pushed": "已推送待决策",
        "selected": "已选择跟进",
        "draft_created": "草稿待补全",
        "review_pending": "待确认提交",
        "documented": "已确认提交",
        "archived": "已归档",
        "ignored": "已忽略",
    }
    return labels.get(status, status)


def build_deadline_text(*, kind: str, tasks: list[dict[str, Any]]) -> str | None:
    groups = categorize_tasks(tasks)
    if not groups["follow_up"] and not groups["undecided"]:
        return None

    title = "今日 AI 学习进展提醒（soft deadline）" if kind == "soft" else "今日 AI 学习最终提醒（hard deadline）"
    lines = [title, ""]
    lines.append(f"已完成：{len(groups['done'])} 条")

    if groups["follow_up"]:
        lines.extend(["", "跟进未闭环："])
        for task in groups["follow_up"]:
            lines.append(f"- [{status_label(task['status'])}] {task['title']}")

    if groups["undecided"]:
        lines.extend(["", "仍待决策："])
        for task in groups["undecided"]:
            lines.append(f"- [{status_label(task['status'])}] {task['title']}")

    lines.extend(["", "入口：", WORKSPACE_URL])
    if kind == "soft":
        lines.extend(["", "请在 23:00 hard deadline 前完成处理。"])
    else:
        lines.extend(["", "这是今天最后一次 deadline 提醒。"])

    return "\n".join(lines)


def unresolved_carryover_lines(state: dict[str, Any], current: datetime) -> list[str]:
    carryover = state.get("carryover")
    if not carryover:
        return []

    source_date = carryover.get("source_date")
    reminded_at = carryover.get("reminded_at")
    task_ids = carryover.get("task_ids") or []

    if not source_date or source_date == current.date().isoformat() or reminded_at:
        return []

    unresolved = [
        task
        for task in get_learning_tasks_by_ids([int(task_id) for task_id in task_ids])
        if task["status"] not in TASK_DONE_STATUSES
    ]
    if not unresolved:
        state["carryover"] = None
        return []

    return [f"- [{status_label(task['status'])}] {task['title']}" for task in unresolved]


def update_carryover_after_morning(state: dict[str, Any], current: datetime) -> None:
    carryover = state.get("carryover")
    if not carryover or carryover.get("source_date") == current.date().isoformat():
        return
    if carryover.get("reminded_at"):
        return
    carryover["reminded_at"] = current.isoformat()


def store_hard_deadline_carryover(state: dict[str, Any], tasks: list[dict[str, Any]], current: datetime) -> None:
    unresolved = [task for task in tasks if task["status"] not in TASK_DONE_STATUSES]
    if not unresolved:
        state["carryover"] = None
        return

    state["carryover"] = {
        "source_date": current.date().isoformat(),
        "task_ids": [int(task["id"]) for task in unresolved],
        "reminded_at": None,
    }


def send_text(text: str, preview: bool) -> dict[str, Any]:
    if preview:
        print(text)
        return {"sent": False, "preview": True}
    return send_feishu_text(text)


def should_record_run(result: dict[str, Any]) -> bool:
    if result.get("skipped"):
        return True
    response = result.get("response")
    if response is None:
        return True
    if response.get("preview"):
        return False
    return bool(response.get("sent"))


def run_signal_push_job(job_name: str, state: dict[str, Any], current: datetime, preview: bool) -> dict[str, Any]:
    limit = limit_for_job(job_name, current)
    run_collection_pipeline(limit=limit)
    signals = list_signal_digest_candidates(github_limit=max(limit * 3, 30), source_limit=10)
    if not preview:
        ensure_top_signal_tasks_pushed(signals[:limit])

    title = "今日 AI 信号早报（08:00）" if job_name == MORNING_JOB else "今日 AI 信号补充推送（14:00）"
    subtitle = f"{'周末' if is_weekend(current) else '工作日'} Top {limit}"
    carryover_lines = unresolved_carryover_lines(state, current) if job_name == MORNING_JOB else []
    text = build_today_task_text(
        title=title,
        subtitle=subtitle,
        signals=signals,
        carryover_lines=carryover_lines,
    )
    response = send_text(text, preview=preview)
    if job_name == MORNING_JOB:
        update_carryover_after_morning(state, current)
    return {"signal_count": len(signals), "limit": limit, "response": response}


def run_deadline_job(job_name: str, state: dict[str, Any], current: datetime, preview: bool) -> dict[str, Any]:
    tasks = list_today_tasks(limit=50)
    kind = "soft" if job_name == SOFT_DEADLINE_JOB else "hard"
    text = build_deadline_text(kind=kind, tasks=tasks)
    if text is None:
        if kind == "hard":
            store_hard_deadline_carryover(state, tasks, current)
        return {"skipped": True, "reason": "all_tasks_complete"}

    response = send_text(text, preview=preview)
    if kind == "hard":
        store_hard_deadline_carryover(state, tasks, current)
    return {"task_count": len(tasks), "response": response}


def run_job(job_name: str, state: dict[str, Any], preview: bool) -> dict[str, Any]:
    current = now_shanghai()
    init_database()

    if job_name in {MORNING_JOB, AFTERNOON_JOB}:
        result = run_signal_push_job(job_name, state, current, preview)
    else:
        result = run_deadline_job(job_name, state, current, preview)

    if should_record_run(result):
        state.setdefault("last_run", {})[job_name] = current.date().isoformat()
        save_state(state)
    return result


def run_catchup_jobs(state: dict[str, Any], preview: bool) -> dict[str, Any]:
    current = now_shanghai()
    init_database()

    missed_jobs = find_missed_jobs(state, current)
    if not missed_jobs:
        return {"skipped": True, "reason": "no_missed_jobs"}

    results: list[dict[str, Any]] = []
    for job_name in missed_jobs:
        result = run_job(job_name, state, preview=preview)
        results.append({"job": job_name, "result": result})

    state.setdefault("last_run", {})[LOGIN_CATCHUP_JOB] = current.date().isoformat()
    save_state(state)
    return {"skipped": False, "jobs": results}


def loop_forever(interval_seconds: int, preview: bool) -> None:
    log("local scheduler started")
    while True:
        state = load_state()
        current = now_shanghai()
        for job_name in SCHEDULED_JOBS:
            if should_run_job(state, job_name, current):
                try:
                    log(f"running job: {job_name}")
                    result = run_job(job_name, state, preview=preview)
                    log(f"job finished: {job_name} -> {json.dumps(result, ensure_ascii=False)}")
                except Exception as error:  # pragma: no cover - runtime guard
                    log(f"job failed: {job_name} -> {error}")
        time.sleep(max(5, interval_seconds))


def main() -> None:
    parser = argparse.ArgumentParser(description="Run local scheduled Feishu pushes for AI Signal Radar.")
    parser.add_argument(
        "--run-now",
        choices=list(SCHEDULED_JOBS),
        help="Run one scheduler job immediately, bypassing the time window.",
    )
    parser.add_argument(
        "--run-catchup-now",
        action="store_true",
        help="Run all missed jobs for the current day once, in scheduled order.",
    )
    parser.add_argument("--preview", action="store_true", help="Print the message without sending it to Feishu.")
    parser.add_argument("--interval-seconds", type=int, default=20, help="Scheduler loop interval in seconds.")
    args = parser.parse_args()

    if args.run_now:
        state = load_state()
        result = run_job(args.run_now, state, preview=args.preview)
        print(json.dumps({"job": args.run_now, "result": result}, ensure_ascii=False, indent=2))
        return

    if args.run_catchup_now:
        state = load_state()
        result = run_catchup_jobs(state, preview=args.preview)
        print(json.dumps({"job": LOGIN_CATCHUP_JOB, "result": result}, ensure_ascii=False, indent=2))
        return

    loop_forever(interval_seconds=args.interval_seconds, preview=args.preview)


if __name__ == "__main__":
    main()
