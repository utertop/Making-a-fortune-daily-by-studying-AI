from __future__ import annotations

from typing import Any

import httpx

from ..settings import get_env


def build_today_task_text(signals: list[dict[str, Any]], workspace_url: str = "http://127.0.0.1:3100") -> str:
    lines = [
        "今日 AI 学习任务",
        "",
        "已完成：",
        f"- 筛选出 {len(signals)} 条候选信号",
        "",
        "请你今天完成：",
        "1. 从候选信号里选择 1 到 3 条深挖",
        "2. 至少提交 1 篇 Markdown 知识库文档",
        "",
        "Top Signals：",
    ]
    for index, signal in enumerate(signals, start=1):
        score = int(signal.get("signal_score") or 0)
        lines.append(f"{index}. [{score}] {signal['title']}")
        lines.append(f"   {signal['url']}")
    lines.extend(["", "入口：", workspace_url])
    return "\n".join(lines)


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
