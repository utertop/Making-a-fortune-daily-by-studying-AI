from __future__ import annotations

from apps.api.app.collectors.rss import _score_entry
from apps.api.app.document_quality import evaluate_markdown_quality
from apps.api.app.push.feishu import build_today_task_text
from apps.api.app.scoring import score_github_repo
from scripts.local_scheduler import build_deadline_text


def test_rss_agent_content_scores_above_generic_marketing() -> None:
    source = {"name": "OpenAI News", "official": True}

    agent_item = _score_entry(
        source,
        "Validating agentic behavior with eval benchmarks",
        "A practical note on agent evaluation, model behavior, and inference quality.",
    )
    marketing_item = _score_entry(
        source,
        "Partner webinar announcement",
        "Join our partner event for a high-level customer story.",
    )

    assert agent_item["score"] > marketing_item["score"]
    assert any("agent" in reason for reason in agent_item["reasons"])
    assert marketing_item["risks"]


def test_github_score_uses_recent_delta_and_penalizes_completed_tasks() -> None:
    active_repo = {
        "id": 1,
        "full_name": "example/agent-lab",
        "url": "https://github.com/example/agent-lab",
        "description": "AI agent workflow framework",
        "language": "Python",
        "license": "MIT",
        "latest_stars": 5000,
        "latest_forks": 700,
        "latest_open_issues": 12,
        "stars_delta": 2500,
        "forks_delta": 250,
        "stars_delta_24h": 250,
        "forks_delta_24h": 20,
        "stars_delta_7d": 2200,
        "forks_delta_7d": 260,
        "newly_seen": False,
        "latest_task_status": None,
        "latest_pushed_at": "2099-01-01T00:00:00Z",
    }
    documented_repo = {**active_repo, "latest_task_status": "documented"}

    active_score = score_github_repo(active_repo)
    documented_score = score_github_repo(documented_repo)

    assert active_score["score"] > documented_score["score"]
    assert "stars_delta_24h > 100: +15" in active_score["reasons"]
    assert "stars_delta_7d > 1000: +12" in active_score["reasons"]
    assert "already_documented: -40" in documented_score["risks"]


def test_feishu_digest_tracks_unfinished_and_reactivates_major_completed_change() -> None:
    unfinished = {
        "title": "example/unfinished-agent",
        "url": "https://github.com/example/unfinished-agent",
        "source_type": "github_repo",
        "signal_score": 70,
        "task_status": "review_pending",
        "raw_content": '{"language":"TypeScript","license":"MIT","stars_delta_7d":1200}',
    }
    completed_quiet = {
        "title": "example/completed-quiet",
        "url": "https://github.com/example/completed-quiet",
        "source_type": "github_repo",
        "signal_score": 88,
        "task_status": "documented",
        "raw_content": '{"language":"Go","license":"MIT","stars_delta_7d":100}',
    }
    completed_changed = {
        "title": "example/completed-changed",
        "url": "https://github.com/example/completed-changed",
        "source_type": "github_repo",
        "signal_score": 91,
        "task_status": "documented",
        "raw_content": '{"language":"Python","license":"MIT","stars_delta_7d":4200}',
    }
    fresh = {
        "title": "example/fresh-agent",
        "url": "https://github.com/example/fresh-agent",
        "source_type": "github_repo",
        "signal_score": 60,
        "task_status": None,
        "raw_content": '{"language":"Python","license":"MIT","newly_seen":true}',
    }

    text = build_today_task_text([unfinished, completed_quiet, completed_changed, fresh])

    assert "待深挖 / 待归档追踪" in text
    assert "example/unfinished-agent" in text
    assert "已归档项目的新变化" in text
    assert "example/completed-changed" in text
    assert "example/completed-quiet" not in text
    assert "理由：" in text


def test_feishu_digest_shows_tracking_days_for_unfinished_tasks() -> None:
    unfinished = {
        "title": "example/unfinished-agent",
        "url": "https://github.com/example/unfinished-agent",
        "source_type": "github_repo",
        "signal_score": 70,
        "task_status": "review_pending",
        "task_created_at": "2000-01-01T00:00:00+00:00",
        "raw_content": '{"language":"TypeScript","license":"MIT","stars_delta_7d":1200}',
    }

    text = build_today_task_text([unfinished])

    assert "已追踪" in text
    assert "待审核" in text


def test_markdown_quality_flags_template_like_documents() -> None:
    poor = evaluate_markdown_quality(
        "## TL;DR\n\nTBD\n\n## Links\n\n- Source:\n\nTODO\n",
        source_url="https://github.com/example/project",
    )
    good = evaluate_markdown_quality(
        "\n".join(
            [
                "# Example Project",
                "Source: https://github.com/example/project",
                "Docs: https://docs.example.com",
                "## TL;DR",
                "This is a researched project note with concrete findings.",
                "## Why It Matters",
                "It helps compare agent workflow tradeoffs in practical teams.",
                "## Core Mechanism",
                "The project coordinates tools, state, and model calls.",
                "## Architecture",
                "The runtime has a CLI, API, workers, and persistent storage.",
                "## Risks",
                "The main risk is unclear maintenance and integration cost.",
                "## Links",
                "- https://github.com/example/project",
                "- https://docs.example.com",
                "Extra detail " * 80,
            ]
        ),
        source_url="https://github.com/example/project",
    )

    assert poor["status"] == "needs_work"
    assert "source_url_missing" in poor["issues"]
    assert "too_many_placeholders" in poor["issues"] or "has_placeholders" in poor["warnings"]
    assert good["status"] == "pass"


def test_deadline_report_summarizes_daily_closure_and_tracking_days() -> None:
    text = build_deadline_text(
        kind="hard",
        current=__import__("datetime").datetime(2026, 5, 8, tzinfo=__import__("datetime").timezone.utc),
        tasks=[
            {
                "title": "finished",
                "status": "documented",
                "created_at": "2026-05-08 00:00:00",
            },
            {
                "title": "needs review",
                "status": "review_pending",
                "created_at": "2026-05-06 00:00:00",
            },
            {
                "title": "still undecided",
                "status": "pushed",
                "created_at": "2026-05-07 00:00:00",
            },
        ],
    )

    assert text is not None
    assert "今日 AI 学习日报" in text
    assert "已完成：1" in text
    assert "needs review" in text
    assert "still undecided" in text
    assert "已追踪" in text
