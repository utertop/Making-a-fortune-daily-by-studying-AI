import os
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
DATA_DIR = REPO_ROOT / "data"
DATABASE_PATH = Path(os.getenv("AI_SIGNAL_RADAR_DATABASE_PATH", str(DATA_DIR / "local.db")))
KNOWLEDGE_BASE_DIR = REPO_ROOT / "knowledge-base"
