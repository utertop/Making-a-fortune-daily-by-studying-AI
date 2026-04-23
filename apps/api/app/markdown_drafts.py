from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from .config import KNOWLEDGE_BASE_DIR


def slugify(value: str) -> str:
    slug = re.sub(r"[^a-zA-Z0-9]+", "-", value.lower()).strip("-")
    return slug or "knowledge-doc"


def default_project_doc_path(title: str, task_id: int) -> str:
    return f"knowledge-base/projects/{slugify(title)}-{task_id}.md"


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


def build_project_markdown(task: dict[str, Any]) -> str:
    title = task["title"]
    source_url = task.get("source_url") or ""
    summary = task.get("summary") or "TBD"
    signal_score = task.get("signal_score") or 0
    source_type = task.get("source_type") or "unknown"
    raw_content = task.get("raw_content") or "{}"

    return f"""# {title}

## Metadata

- Source: {source_url}
- Source type: {source_type}
- Signal score: {signal_score}
- Status: draft
- Confidence: medium
- Tags: ai, github, signal

## TL;DR

{summary}

## Why It Matters

- TODO: Explain why this signal matters now.
- TODO: Describe the engineering or product shift behind it.
- TODO: Note whether this is worth hands-on follow-up.

## Quick Start

```bash
# TODO: Add install or clone commands
```

## Core Concepts

- TODO: Concept 1
- TODO: Concept 2
- TODO: Concept 3

## Architecture

```mermaid
flowchart LR
    User[User] --> Tool[Tool / Project]
    Tool --> Model[AI Model / Runtime]
    Tool --> Data[Docs / Repo / External APIs]
    Model --> Output[Workflow Output]
```

## Evaluation Notes

| Dimension | Notes |
| --- | --- |
| Use case | TODO |
| Docs quality | TODO |
| Code quality | TODO |
| Activity | TODO |
| License | TODO |
| Risk | TODO |

## Hands-on Notes

- TODO: Record setup result.
- TODO: Record useful commands.
- TODO: Record blockers.

## Links

- Source: {source_url}

## Raw Signal Snapshot

```json
{raw_content}
```
"""


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
