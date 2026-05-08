from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

AI_KEYWORDS = (
    "ai",
    "agent",
    "llm",
    "mcp",
    "rag",
    "inference",
    "model",
    "workflow",
    "automation",
    "assistant",
)


def _parse_datetime(value: str | None) -> datetime | None:
    if not value:
        return None
    normalized = value.replace("Z", "+00:00")
    try:
        parsed = datetime.fromisoformat(normalized)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed


def _contains_ai_keyword(*values: str | None) -> bool:
    text = " ".join(value or "" for value in values).lower()
    return any(keyword in text for keyword in AI_KEYWORDS)


def score_github_repo(repo: dict[str, Any]) -> dict[str, Any]:
    reasons: list[str] = []
    risks: list[str] = []
    score = 0

    stars_delta = int(repo.get("stars_delta") or 0)
    forks_delta = int(repo.get("forks_delta") or 0)
    stars_delta_24h = int(repo.get("stars_delta_24h") or 0)
    forks_delta_24h = int(repo.get("forks_delta_24h") or 0)
    stars_delta_7d = int(repo.get("stars_delta_7d") or 0)
    forks_delta_7d = int(repo.get("forks_delta_7d") or 0)
    latest_stars = int(repo.get("latest_stars") or 0)
    latest_forks = int(repo.get("latest_forks") or 0)
    open_issues = int(repo.get("latest_open_issues") or 0)
    newly_seen = bool(repo.get("newly_seen"))

    if stars_delta_24h > 1000:
        score += 25
        reasons.append("stars_delta_24h > 1000: +25")
    elif stars_delta_24h > 100:
        score += 15
        reasons.append("stars_delta_24h > 100: +15")
    elif stars_delta_24h > 0:
        score += 5
        reasons.append("stars_delta_24h > 0: +5")

    if stars_delta_7d > 3000:
        score += 20
        reasons.append("stars_delta_7d > 3000: +20")
    elif stars_delta_7d > 1000:
        score += 12
        reasons.append("stars_delta_7d > 1000: +12")
    elif stars_delta_7d > 100:
        score += 6
        reasons.append("stars_delta_7d > 100: +6")

    if forks_delta_7d > 200:
        score += 10
        reasons.append("forks_delta_7d > 200: +10")
    elif forks_delta_24h > 0 or forks_delta_7d > 0:
        score += 5
        reasons.append("forks_delta_recent > 0: +5")

    if latest_stars > 10000:
        score += 5
        reasons.append("stars > 10000: +5")
    elif latest_stars > 1000:
        score += 3
        reasons.append("stars > 1000: +3")

    if latest_forks > 1000:
        score += 3
        reasons.append("forks > 1000: +3")

    if newly_seen:
        score += 15
        reasons.append("newly_seen_repo: +15")

    license_value = repo.get("license")
    if license_value and license_value != "NOASSERTION":
        score += 5
        reasons.append("has_license: +5")
    else:
        score -= 10
        risks.append("no_clear_license: -10")

    if repo.get("language"):
        score += 2
        reasons.append("has_language: +2")

    if _contains_ai_keyword(repo.get("full_name"), repo.get("description"), repo.get("topics")):
        score += 15
        reasons.append("ai_keyword_match: +15")
    else:
        score -= 15
        risks.append("weak_ai_relevance: -15")

    pushed_at = _parse_datetime(repo.get("latest_pushed_at"))
    if pushed_at:
        age_days = (datetime.now(timezone.utc) - pushed_at).days
        if age_days <= 14:
            score += 10
            reasons.append("latest_commit within 14 days: +10")
        elif age_days > 180:
            score -= 20
            risks.append("stale_repo_over_180_days: -20")

    if open_issues > 5000:
        score -= 10
        risks.append("very_high_open_issues: -10")

    task_status = repo.get("latest_task_status")
    if task_status in {"documented", "archived", "ignored"}:
        score -= 40
        risks.append(f"already_{task_status}: -40")
    elif task_status in {"pushed", "selected", "draft_created", "review_pending"}:
        score -= 15
        risks.append(f"already_in_workflow_{task_status}: -15")

    return {
        "repo_id": repo["id"],
        "full_name": repo["full_name"],
        "url": repo["url"],
        "description": repo.get("description"),
        "language": repo.get("language"),
        "license": repo.get("license"),
        "latest_stars": latest_stars,
        "latest_forks": latest_forks,
        "latest_open_issues": open_issues,
        "stars_delta": stars_delta,
        "forks_delta": forks_delta,
        "stars_delta_24h": stars_delta_24h,
        "forks_delta_24h": forks_delta_24h,
        "stars_delta_7d": stars_delta_7d,
        "forks_delta_7d": forks_delta_7d,
        "newly_seen": newly_seen,
        "latest_task_status": task_status,
        "score": score,
        "reasons": reasons,
        "risks": risks,
    }

