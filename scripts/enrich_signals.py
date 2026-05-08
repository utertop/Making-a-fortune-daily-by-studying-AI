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


def emit(value: object) -> None:
    print(json.dumps(value, ensure_ascii=False, default=str))


def main() -> None:
    parser = argparse.ArgumentParser(description="Run optional LLM enrichment for top AI signals.")
    parser.add_argument("--limit", type=int, default=None, help="Maximum signals to enrich today")
    args = parser.parse_args()

    init_database()
    emit(enrich_top_signal_candidates(limit=args.limit))


if __name__ == "__main__":
    main()
