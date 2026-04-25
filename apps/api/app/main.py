from __future__ import annotations

from typing import List, Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from .db import database_status, ensure_database
from .markdown_drafts import build_project_markdown, default_project_doc_path, write_markdown_draft
from .repository import (
    TASK_STATUSES,
    attach_draft_document_to_task,
    detect_document_for_task,
    detect_documents,
    ensure_today_tasks_from_top_signals,
    get_task_for_markdown_draft,
    list_top_signals,
    submit_knowledge_document_for_task,
    today_task_summary,
    update_learning_task_status,
)


class TaskStatusUpdate(BaseModel):
    status: str
    target_doc_path: Optional[str] = Field(default=None, max_length=500)
    ignored_reason: Optional[str] = Field(default=None, max_length=100)


class KnowledgeDocumentSubmit(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    path: str = Field(min_length=1, max_length=500)
    summary: Optional[str] = Field(default=None, max_length=2000)
    tags: List[str] = Field(default_factory=list)
    confidence: Optional[str] = Field(default=None, max_length=50)
    content: Optional[str] = None
    created_by_agent: Optional[str] = Field(default=None, max_length=100)


class MarkdownDraftGenerate(BaseModel):
    path: Optional[str] = Field(default=None, max_length=500)
    overwrite: bool = False


class DocumentDetectRequest(BaseModel):
    limit: int = Field(default=50, ge=1, le=200)


app = FastAPI(title="AI Signal Radar API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://127.0.0.1:3100",
        "http://localhost:3100",
        "http://127.0.0.1:3000",
        "http://localhost:3000",
    ],
    allow_origin_regex=r"^http://(10\.\d+\.\d+\.\d+|192\.168\.\d+\.\d+|172\.(1[6-9]|2\d|3[0-1])\.\d+\.\d+):3100$",
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
            ignored_reason=payload.ignored_reason,
        )
    except ValueError as error:
        status_code = 400 if str(error).startswith("Unsupported") or "require" in str(error).lower() else 404
        raise HTTPException(status_code=status_code, detail=str(error)) from error

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


@app.post("/tasks/{task_id}/draft")
def generate_task_markdown_draft(task_id: int, payload: MarkdownDraftGenerate) -> dict:
    ensure_database()
    try:
        task_for_draft = get_task_for_markdown_draft(task_id)
        path = payload.path or default_project_doc_path(task_for_draft["title"], task_id)
        content = build_project_markdown(task_for_draft)
        draft = write_markdown_draft(path=path, content=content, overwrite=payload.overwrite)
        task = attach_draft_document_to_task(
            task_id=task_id,
            title=f"{task_for_draft['title']} \u6df1\u5ea6\u9879\u76ee\u77e5\u8bc6\u6863\u6848",
            path=draft["path"],
            content=content,
            summary=task_for_draft.get("summary"),
        )
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error

    return {"draft": draft, "task": task}


@app.post("/tasks/{task_id}/detect-document")
def detect_task_document(task_id: int) -> dict:
    ensure_database()
    try:
        result = detect_document_for_task(task_id)
    except ValueError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
    return result


@app.post("/tasks/detect-documents")
def detect_task_documents(payload: DocumentDetectRequest) -> dict:
    ensure_database()
    return detect_documents(limit=payload.limit)
