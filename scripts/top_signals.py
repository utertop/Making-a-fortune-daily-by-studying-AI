from pathlib import Path
import json
import sys

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from apps.api.app.db import init_database
from apps.api.app.repository import list_top_signals


def emit(value: object) -> None:
    print(json.dumps(value, ensure_ascii=True, default=str))


def main() -> None:
    init_database()
    emit({"top_signals": list_top_signals(limit=10)})


if __name__ == "__main__":
    main()
