from __future__ import annotations

from pathlib import Path
from urllib.parse import urlparse
from typing import Any

import yaml

from .config import REPO_ROOT

SOURCES_PATH = REPO_ROOT / "config" / "sources.yaml"


def load_sources(path: Path = SOURCES_PATH) -> list[dict[str, Any]]:
    data = yaml.safe_load(path.read_text(encoding="utf-8-sig")) or {}
    sources = data.get("sources", [])
    if not isinstance(sources, list):
        raise ValueError("sources.yaml must contain a sources list")
    return sources


def enabled_sources(source_type: str | None = None) -> list[dict[str, Any]]:
    sources = [source for source in load_sources() if source.get("enabled", True)]
    if source_type is not None:
        sources = [source for source in sources if source.get("type") == source_type]
    return sources


def validate_allowlisted_url(url: str, allowlist_domain: str | None) -> None:
    if not allowlist_domain:
        return
    hostname = urlparse(url).hostname
    if hostname != allowlist_domain:
        raise ValueError(f"URL host {hostname!r} does not match allowlist domain {allowlist_domain!r}")
