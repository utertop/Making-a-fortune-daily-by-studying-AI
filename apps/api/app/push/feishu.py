from __future__ import annotations

import json
from typing import Any

import httpx

from ..settings import get_env

ACTIVE_TASK_STATUSES = {"pending", "pushed", "selected", "draft_created", "review_pending"}
DONE_TASK_STATUSES = {"documented", "archived", "ignored"}
MAJOR_24H_STAR_DELTA = 1000
MAJOR_7D_STAR_DELTA = 3000


def _raw_details(signal: dict[str, Any]) -> dict[str, Any]:
    raw_content = signal.get("raw_content")
    if not isinstance(raw_content, str) or not raw_content.strip():
        return {}
    try:
        parsed = json.loads(raw_content)
    except json.JSONDecodeError:
        return {}
    return parsed if isinstance(parsed, dict) else {}


def _is_github(signal: dict[str, Any]) -> bool:
    return signal.get("source_type") == "github_repo"


def _task_status(signal: dict[str, Any]) -> str | None:
    status = signal.get("task_status")
    return str(status) if status else None


def _is_active_task(signal: dict[str, Any]) -> bool:
    return _task_status(signal) in ACTIVE_TASK_STATUSES


def _is_done_task(signal: dict[str, Any]) -> bool:
    return _task_status(signal) in DONE_TASK_STATUSES


def _is_new_signal(signal: dict[str, Any]) -> bool:
    details = _raw_details(signal)
    if _is_github(signal):
        return bool(details.get("newly_seen"))
    return True


def _stars_delta_24h(signal: dict[str, Any]) -> int:
    return int(_raw_details(signal).get("stars_delta_24h") or 0)


def _stars_delta_7d(signal: dict[str, Any]) -> int:
    return int(_raw_details(signal).get("stars_delta_7d") or 0)


def _momentum_value(signal: dict[str, Any]) -> int:
    details = _raw_details(signal)
    return max(
        int(details.get("stars_delta_24h") or 0),
        int(details.get("stars_delta_7d") or 0),
        int(details.get("stars_delta") or 0),
    )


def _has_major_change(signal: dict[str, Any]) -> bool:
    if not _is_github(signal):
        return False
    return _stars_delta_24h(signal) >= MAJOR_24H_STAR_DELTA or _stars_delta_7d(signal) >= MAJOR_7D_STAR_DELTA


def _status_label(status: str | None) -> str:
    labels = {
        "pending": "待处理",
        "pushed": "已推送",
        "selected": "已选择",
        "draft_created": "草稿已生成",
        "review_pending": "待审核",
        "documented": "已归档",
        "archived": "已收起",
        "ignored": "已跳过",
    }
    return labels.get(status or "", status or "未建任务")


def _compact_reason(signal: dict[str, Any]) -> str:
    details = _raw_details(signal)
    reasons: list[str] = []

    if _is_github(signal):
        delta_24h = _stars_delta_24h(signal)
        delta_7d = _stars_delta_7d(signal)
        if delta_24h:
            reasons.append(f"24 小时新增 {delta_24h} stars")
        if delta_7d:
            reasons.append(f"7 天新增 {delta_7d} stars")
        if details.get("newly_seen"):
            reasons.append("近期新进入雷达")
        if details.get("language"):
            reasons.append(f"{details['language']} 项目")
        if details.get("license") and details.get("license") != "NOASSERTION":
            reasons.append(f"{details['license']} license")
        if not reasons:
            reasons.append("近期仍活跃，分数靠前")
    else:
        raw_reasons = [str(item) for item in details.get("reasons", []) if item]
        keyword_reasons = [item.split(":")[0].replace("_", " ") for item in raw_reasons[:2]]
        if keyword_reasons:
            reasons.append("命中 " + "、".join(keyword_reasons))
        source_name = details.get("source_name")
        if source_name:
            reasons.append(f"来自 {source_name}")
        if not reasons:
            reasons.append("官方或社区来源，近期发布")

    return "；".join(reasons[:3]) + "。"


def _format_signal_line(index: int, signal: dict[str, Any], *, include_status: bool = False) -> list[str]:
    score = int(signal.get("signal_score") or 0)
    details = _raw_details(signal)
    suffix_parts: list[str] = []
    if _is_github(signal):
        delta_24h = _stars_delta_24h(signal)
        delta_7d = _stars_delta_7d(signal)
        if delta_24h:
            suffix_parts.append(f"24h +{delta_24h} stars")
        if delta_7d:
            suffix_parts.append(f"7d +{delta_7d} stars")
        if details.get("language"):
            suffix_parts.append(str(details["language"]))
    if include_status:
        suffix_parts.append(_status_label(_task_status(signal)))

    suffix = f" ({' / '.join(suffix_parts)})" if suffix_parts else ""
    return [
        f"{index}. [{score}] {signal['title']}{suffix}",
        f"   {signal['url']}",
        f"   理由：{_compact_reason(signal)}",
    ]


def _take_unique(candidates: list[dict[str, Any]], limit: int, used_urls: set[str]) -> list[dict[str, Any]]:
    chosen: list[dict[str, Any]] = []
    for signal in candidates:
        url = str(signal.get("url") or "")
        if not url or url in used_urls:
            continue
        chosen.append(signal)
        used_urls.add(url)
        if len(chosen) >= limit:
            break
    return chosen


def _score_sort(signal: dict[str, Any]) -> tuple[float, int]:
    return (float(signal.get("signal_score") or 0), _momentum_value(signal))


def build_today_task_text(
    signals: list[dict[str, Any]],
    workspace_url: str = "http://127.0.0.1:3100",
    title: str = "今日 AI 信号雷达",
    subtitle: str | None = None,
    carryover_lines: list[str] | None = None,
) -> str:
    active_tracking = sorted(
        [signal for signal in signals if _is_active_task(signal)],
        key=lambda item: (_momentum_value(item), float(item.get("signal_score") or 0)),
        reverse=True,
    )
    reactivated = sorted(
        [signal for signal in signals if _is_done_task(signal) and _has_major_change(signal)],
        key=lambda item: (_momentum_value(item), float(item.get("signal_score") or 0)),
        reverse=True,
    )
    fresh_pool = [
        signal
        for signal in signals
        if not _is_active_task(signal) and not _is_done_task(signal)
    ]

    github_fresh = sorted(
        [signal for signal in fresh_pool if _is_github(signal) and _is_new_signal(signal)],
        key=_score_sort,
        reverse=True,
    )
    github_rising = sorted(
        [signal for signal in fresh_pool if _is_github(signal) and not _is_new_signal(signal)],
        key=lambda item: (_momentum_value(item), float(item.get("signal_score") or 0)),
        reverse=True,
    )
    rss_signals = sorted(
        [signal for signal in fresh_pool if not _is_github(signal)],
        key=lambda item: (float(item.get("signal_score") or 0), str(item.get("published_at") or item.get("fetched_at") or "")),
        reverse=True,
    )

    used_urls: set[str] = set()
    tracking_signals = _take_unique(active_tracking, 5, used_urls)
    reactivated_signals = _take_unique(reactivated, 3, used_urls)
    new_github_signals = _take_unique(github_fresh, 3, used_urls)
    rising_signals = _take_unique(github_rising, 3, used_urls)
    source_signals = _take_unique(rss_signals, 3, used_urls)
    fallback_signals = _take_unique(
        sorted(fresh_pool, key=_score_sort, reverse=True),
        1,
        used_urls,
    )

    lines = [title]
    if subtitle:
        lines.append(subtitle)
    lines.extend(
        [
            "",
            "今天建议：",
            "1. 高能量项目如果还没归档，就继续追到闭环。",
            "2. 从新信号里再选 1 到 3 条深挖。",
            "3. 至少提交或更新 1 篇 Markdown 知识库文档。",
            "",
        ]
    )

    if carryover_lines:
        lines.extend(["昨日未完成：", *carryover_lines, ""])

    sections: list[tuple[str, list[dict[str, Any]], bool]] = [
        ("待深挖 / 待归档追踪", tracking_signals, True),
        ("已归档项目的新变化", reactivated_signals, True),
        ("新出现 GitHub", new_github_signals, False),
        ("持续升温 GitHub", rising_signals, False),
        ("官方 / RSS 动态", source_signals, False),
        ("补充候选", fallback_signals, False),
    ]
    for section_title, section_signals, include_status in sections:
        if not section_signals:
            continue
        lines.append(f"{section_title}：")
        for index, signal in enumerate(section_signals, start=1):
            lines.extend(_format_signal_line(index, signal, include_status=include_status))
        lines.append("")

    if not any(section_signals for _, section_signals, _ in sections):
        lines.extend(["暂无候选信号。", ""])

    lines.extend(["入口：", workspace_url])
    return "\n".join(lines).strip()


def build_text_payload(text: str) -> dict[str, Any]:
    return {"msg_type": "text", "content": {"text": text}}


def send_feishu_text(text: str, webhook_url: str | None = None) -> dict[str, Any]:
    url = webhook_url or get_env("FEISHU_WEBHOOK_URL")
    if not url:
        return {"sent": False, "reason": "missing_webhook", "payload": build_text_payload(text)}

    with httpx.Client(timeout=20) as client:
        response = client.post(url, json=build_text_payload(text))
        response.raise_for_status()
        data = response.json()
    return {"sent": True, "response": data}
