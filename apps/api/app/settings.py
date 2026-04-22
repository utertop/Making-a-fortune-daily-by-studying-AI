from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

from .config import REPO_ROOT

ENV_PATH = REPO_ROOT / ".env"
load_dotenv(ENV_PATH)


def get_env(name: str, default: str | None = None) -> str | None:
    return os.getenv(name, default)


def require_env(name: str) -> str:
    value = get_env(name)
    if not value:
        raise RuntimeError(f"Missing required environment variable: {name}")
    return value
