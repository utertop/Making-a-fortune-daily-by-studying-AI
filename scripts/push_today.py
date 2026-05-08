from pathlib import Path
import argparse
import json
import sys

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from apps.api.app.db import init_database
from apps.api.app.llm.enrichment import enrich_top_signal_candidates
from apps.api.app.push.feishu import build_today_task_text, send_feishu_text
from apps.api.app.repository import list_signal_digest_candidates


def emit(value: object) -> None:
    print(json.dumps(value, ensure_ascii=False, default=str))


def main() -> None:
    parser = argparse.ArgumentParser(description="Preview or send today's Feishu AI learning task push.")
    parser.add_argument("--send", action="store_true", help="Send to FEISHU_WEBHOOK_URL instead of dry-run preview")
    parser.add_argument("--enrich", action="store_true", help="Run optional LLM enrichment before building the push")
    parser.add_argument("--limit", type=int, default=10, help="Number of top signals to include")
    args = parser.parse_args()

    init_database()
    enrichment = None
    if args.enrich:
        enrichment = enrich_top_signal_candidates(limit=max(args.limit * 2, 10))
    signals = list_signal_digest_candidates(github_limit=max(args.limit * 3, 30), source_limit=10)
    text = build_today_task_text(signals)
    if not args.send:
        emit({"dry_run": True, "enrichment": enrichment, "text": text})
        return
    emit(send_feishu_text(text))


if __name__ == "__main__":
    main()
