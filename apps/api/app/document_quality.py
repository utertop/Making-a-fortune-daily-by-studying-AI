from __future__ import annotations

import re
from typing import Any

PLACEHOLDER_PATTERNS = (
    r"\bTODO\b",
    r"\bTBD\b",
    r"待补充",
    r"待确认",
)


def evaluate_markdown_quality(content: str | None, *, source_url: str | None = None) -> dict[str, Any]:
    text = content or ""
    issues: list[str] = []
    warnings: list[str] = []

    if not text.strip():
        issues.append("content_empty")

    if source_url and source_url not in text:
        issues.append("source_url_missing")
    elif not source_url and not re.search(r"https?://", text):
        issues.append("source_link_missing")

    heading_count = len(re.findall(r"(?m)^#{2,4}\s+\S+", text))
    if heading_count < 5:
        issues.append("too_few_sections")

    link_count = len(re.findall(r"https?://", text))
    if link_count < 2:
        warnings.append("too_few_links")

    placeholder_count = sum(len(re.findall(pattern, text, flags=re.IGNORECASE)) for pattern in PLACEHOLDER_PATTERNS)
    if placeholder_count >= 8:
        issues.append("too_many_placeholders")
    elif placeholder_count > 0:
        warnings.append("has_placeholders")

    if len(text.strip()) < 800:
        warnings.append("content_too_short")

    score = 100
    score -= 20 * len(issues)
    score -= 8 * len(warnings)
    score = max(0, score)

    if issues:
        status = "needs_work"
    elif warnings:
        status = "pass_with_warnings"
    else:
        status = "pass"

    return {
        "status": status,
        "score": score,
        "issues": issues,
        "warnings": warnings,
        "metrics": {
            "heading_count": heading_count,
            "link_count": link_count,
            "placeholder_count": placeholder_count,
            "character_count": len(text.strip()),
        },
    }
