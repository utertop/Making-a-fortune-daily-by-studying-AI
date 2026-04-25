from __future__ import annotations

import re
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from .config import KNOWLEDGE_BASE_DIR


def slugify(value: str) -> str:
    slug = re.sub(r"[^a-zA-Z0-9]+", "-", value.lower()).strip("-")
    return slug or "knowledge-doc"


def default_project_doc_path(title: str, task_id: int) -> str:
    today = datetime.now(timezone(timedelta(hours=8)))
    return (
        "knowledge-base/daily/"
        f"{today:%Y}/{today:%m}/{today:%Y-%m-%d}/"
        f"{slugify(title)}-deep-dossier-{task_id}.md"
    )


def resolve_knowledge_path(path: str) -> Path:
    clean_path = path.strip().replace("\\", "/")
    if not clean_path:
        raise ValueError("Document path is required")
    if not clean_path.endswith(".md"):
        raise ValueError("Document path must end with .md")

    if clean_path.startswith("knowledge-base/"):
        relative_path = clean_path[len("knowledge-base/") :]
    else:
        relative_path = clean_path

    resolved_path = (KNOWLEDGE_BASE_DIR / relative_path).resolve()
    base_path = KNOWLEDGE_BASE_DIR.resolve()
    if resolved_path != base_path and base_path not in resolved_path.parents:
        raise ValueError("Document path must stay inside knowledge-base")
    return resolved_path


def to_repo_relative_path(path: Path) -> str:
    return path.resolve().relative_to(KNOWLEDGE_BASE_DIR.parent.resolve()).as_posix()


def _load_deep_dossier_template() -> str:
    template_path = KNOWLEDGE_BASE_DIR / "templates" / "deep-project-dossier.md"
    return template_path.read_text(encoding="utf-8")


def build_project_markdown(task: dict[str, Any]) -> str:
    title = task["title"]
    source_url = task.get("source_url") or ""
    summary = task.get("summary") or "TBD"
    signal_score = task.get("signal_score") or 0
    source_type = task.get("source_type") or "unknown"
    raw_content = task.get("raw_content") or "{}"
    today = datetime.now(timezone(timedelta(hours=8)))
    content = _load_deep_dossier_template()

    replacements = {
        r"^# .+$": f"# {title} 深度项目知识档案",
        r"^- Source:\s*$": f"- Source: {source_url}",
        r"^- Source type:\s*$": f"- Source type: {source_type}",
        r"^- Project type:\s*$": "- Project type: ai_project",
        r"^- Signal score:\s*$": f"- Signal score: {signal_score}",
        r"^- Last reviewed at:\s*$": f"- Last reviewed at: {today:%Y-%m-%d}",
        r"^- Tags:\s*$": "- Tags: ai, github, deep-dossier",
        r"### TL;DR\s*\n\s*TBD": f"### TL;DR\n\n{summary}",
        r"```json\s*\n\{\}\s*\n```": f"```json\n{raw_content}\n```",
    }

    for pattern, replacement in replacements.items():
        content = re.sub(pattern, replacement, content, count=1, flags=re.MULTILINE)

    return content


def write_markdown_draft(path: str, content: str, overwrite: bool = False) -> dict[str, Any]:
    resolved_path = resolve_knowledge_path(path)
    if resolved_path.exists() and not overwrite:
        return {
            "created": False,
            "path": to_repo_relative_path(resolved_path),
            "message": "Draft already exists",
        }

    resolved_path.parent.mkdir(parents=True, exist_ok=True)
    resolved_path.write_text(content, encoding="utf-8")
    return {
        "created": True,
        "path": to_repo_relative_path(resolved_path),
        "message": "Draft created",
    }
