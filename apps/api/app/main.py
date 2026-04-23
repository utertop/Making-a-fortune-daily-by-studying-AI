from __future__ import annotations

from typing import List, Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from .db import database_status, ensure_database
from .repository import (
    TASK_STATUSES,
    ensure_today_tasks_from_top_signals,
    list_top_signals,
    submit_knowledge_document_for_task,
    today_task_summary,
    update_learning_task_status,
)


class TaskStatusUpdate(BaseModel):
    status: str
    target_doc_path: Optional[str] = Field(default=None, max_length=500)


class KnowledgeDocumentSubmit(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    path: str = Field(min_length=1, max_length=500)
    summary: Optional[str] = Field(default=None, max_length=2000)
    tags: List[str] = Field(default_factory=list)
    confidence: Optional[str] = Field(default=None, max_length=50)
    content: Optional[str] = None
    created_by_agent: Optional[str] = Field(default=None, max_length=100)


app = FastAPI(title="AI Signal Radar API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://127.0.0.1:3100",
        "http://localhost:3100",
        "http://127.0.0.1:3000",
        "http://localhost:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health() -> dict:
    return {
        "status": "ok",
        "service": "ai-signal-radar-api",
        "version": "0.1.0",
        "database": database_status(),
    }


@app.get("/signals/top")
def top_signals(limit: int = 10) -> dict:
    ensure_database()
    safe_limit = max(1, min(limit, 50))
    return {"signals": list_top_signals(limit=safe_limit)}


@app.get("/tasks/today")
def today_tasks(limit: int = 10) -> dict:
    ensure_database()
    safe_limit = max(1, min(limit, 50))
    tasks = ensure_today_tasks_from_top_signals(limit=safe_limit)
    return {
        "tasks": tasks,
        "summary": today_task_summary(tasks),
        "allowed_statuses": sorted(TASK_STATUSES),
    }


@app.post("/tasks/{task_id}/status")
def update_task_status(task_id: int, payload: TaskStatusUpdate) -> dict:
    ensure_database()
    if payload.status not in TASK_STATUSES:
        raise HTTPException(status_code=400, detail=f"Unsupported status: {payload.status}")

    try:
        task = update_learning_task_status(
            task_id=task_id,
            status=payload.status,
            target_doc_path=payload.target_doc_path,
        )
    except ValueError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error

    return {"task": task}


@app.post("/tasks/{task_id}/document")
def submit_task_document(task_id: int, payload: KnowledgeDocumentSubmit) -> dict:
    ensure_database()
    try:
        task = submit_knowledge_document_for_task(
            task_id=task_id,
            title=payload.title,
            path=payload.path,
            summary=payload.summary,
            tags=payload.tags,
            confidence=payload.confidence,
            content=payload.content,
            created_by_agent=payload.created_by_agent,
        )
    except ValueError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error

    return {"task": task}
