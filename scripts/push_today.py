from pathlib import Path
import argparse
import json
import sys
from datetime import datetime, timedelta, timezone

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from apps.api.app.db import init_database
from apps.api.app.llm.enrichment import enrich_top_signal_candidates, push_enrichment_enabled, push_enrichment_limit
from apps.api.app.push.feishu import build_today_task_text, send_feishu_text
from apps.api.app.repository import list_signal_digest_candidates, record_push_run

ARCHIVE_TIMEZONE = timezone(timedelta(hours=8))


def emit(value: object) -> None:
    print(json.dumps(value, ensure_ascii=False, default=str))


def main() -> None:
    parser = argparse.ArgumentParser(description="Preview or send today's Feishu AI learning task push.")
    parser.add_argument("--send", action="store_true", help="Send to FEISHU_WEBHOOK_URL instead of dry-run preview")
    enrich_group = parser.add_mutually_exclusive_group()
    enrich_group.add_argument("--enrich", action="store_true", help="Force LLM enrichment before building the push")
    enrich_group.add_argument("--no-enrich", action="store_true", help="Disable LLM enrichment for this run")
    parser.add_argument("--limit", type=int, default=10, help="Number of top signals to include")
    args = parser.parse_args()

    init_database()
    should_enrich = args.enrich or (push_enrichment_enabled() and not args.no_enrich)
    enrichment = None
    if should_enrich:
        enrichment = enrich_top_signal_candidates(limit=push_enrichment_limit(args.limit))
    signals = list_signal_digest_candidates(github_limit=max(args.limit * 3, 30), source_limit=10)
    text = build_today_task_text(signals)
    if not args.send:
        emit({"dry_run": True, "enrichment": enrichment, "text": text})
        return
    response = send_feishu_text(text)
    archive_now = datetime.now(ARCHIVE_TIMEZONE)
    push_run_id = record_push_run(
        {
            "archive_date": archive_now.date().isoformat(),
            "job_name": "manual_push_today",
            "channel": "feishu",
            "status": "sent" if response.get("sent") else response.get("reason", "not_sent"),
            "title": "Manual today push",
            "task_count": len(signals),
            "sent_at": archive_now.isoformat() if response.get("sent") else None,
            "payload": {"enrichment": enrichment, "response": response},
        }
    )
    emit({"push_run_id": push_run_id, **response})


if __name__ == "__main__":
    main()
