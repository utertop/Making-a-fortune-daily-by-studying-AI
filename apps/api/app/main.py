from __future__ import annotations

from typing import List, Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from .db import database_status, ensure_database
from .llm.client import llm_status
from .llm.enrichment import enrich_top_signal_candidates, rerun_low_quality_signal_enrichments, rerun_task_signal_enrichment
from .markdown_drafts import build_project_markdown, default_project_doc_path, write_markdown_draft
from .repository import (
    TASK_STATUSES,
    attach_draft_document_to_task,
    check_document_quality_for_task,
    detect_document_for_task,
    detect_documents,
    ensure_today_tasks_from_top_signals,
    get_task_for_markdown_draft,
    list_task_archive_days,
    list_tasks_for_archive_day,
    list_today_tasks,
    list_top_signals,
    llm_feedback_summary,
    refresh_archive_day_index,
    record_llm_feedback,
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


class DocumentQualityCheckRequest(BaseModel):
    path: Optional[str] = Field(default=None, max_length=500)
    content: Optional[str] = None


class SignalEnrichRequest(BaseModel):
    limit: int = Field(default=10, ge=1, le=50)


class LlmBatchRerunRequest(BaseModel):
    limit: int = Field(default=5, ge=1, le=20)


class LlmFeedbackSubmit(BaseModel):
    feedback_type: str = Field(max_length=40)


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


@app.get("/llm/status")
def get_llm_status() -> dict:
    return llm_status()


@app.get("/signals/top")
def top_signals(limit: int = 10) -> dict:
    ensure_database()
    safe_limit = max(1, min(limit, 50))
    return {"signals": list_top_signals(limit=safe_limit)}


@app.post("/signals/enrich")
def enrich_signals(payload: SignalEnrichRequest) -> dict:
    ensure_database()
    return enrich_top_signal_candidates(limit=payload.limit)


@app.get("/llm/feedback-summary")
def get_llm_feedback_summary() -> dict:
    ensure_database()
    return llm_feedback_summary()


@app.post("/llm/rerun-low-quality")
def rerun_low_quality_llm_enrichments(payload: LlmBatchRerunRequest) -> dict:
    ensure_database()
    result = rerun_low_quality_signal_enrichments(limit=payload.limit)
    return {**result, "summary": llm_feedback_summary()}


@app.get("/tasks/today")
def today_tasks(limit: int = 10) -> dict:
    ensure_database()
    safe_limit = max(1, min(limit, 50))
    tasks = list_today_tasks(limit=safe_limit)
    return {
        "tasks": tasks,
        "summary": today_task_summary(tasks),
        "allowed_statuses": sorted(TASK_STATUSES),
    }


@app.post("/tasks/today/refresh")
def refresh_today_tasks(limit: int = 10) -> dict:
    ensure_database()
    safe_limit = max(1, min(limit, 50))
    tasks = ensure_today_tasks_from_top_signals(limit=safe_limit)
    return {
        "tasks": tasks,
        "summary": today_task_summary(tasks),
        "allowed_statuses": sorted(TASK_STATUSES),
    }


@app.get("/archives")
def archives(limit: int = 120) -> dict:
    ensure_database()
    return {"days": list_task_archive_days(limit=limit)}


@app.post("/archives/refresh")
def refresh_archives(limit: int = 120) -> dict:
    ensure_database()
    safe_limit = max(1, min(limit, 365))
    return {"days": refresh_archive_day_index()[:safe_limit]}


@app.get("/tasks/archive")
def archive_tasks(date: str, limit: int = 50) -> dict:
    ensure_database()
    try:
        tasks = list_tasks_for_archive_day(archive_date=date, limit=limit)
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
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


@app.post("/tasks/{task_id}/llm-feedback")
def submit_task_llm_feedback(task_id: int, payload: LlmFeedbackSubmit) -> dict:
    ensure_database()
    try:
        feedback = record_llm_feedback(task_id, payload.feedback_type)
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    return {"feedback": feedback, "summary": llm_feedback_summary()}


@app.post("/tasks/{task_id}/llm-rerun")
def rerun_task_llm_enrichment(task_id: int) -> dict:
    ensure_database()
    try:
        result = rerun_task_signal_enrichment(task_id)
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    except RuntimeError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    return {**result, "summary": llm_feedback_summary()}


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


@app.post("/tasks/{task_id}/quality-check")
def check_task_document_quality(task_id: int, payload: DocumentQualityCheckRequest) -> dict:
    ensure_database()
    try:
        result = check_document_quality_for_task(
            task_id=task_id,
            path=payload.path,
            content=payload.content,
        )
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    return result


@app.post("/tasks/detect-documents")
def detect_task_documents(payload: DocumentDetectRequest) -> dict:
    ensure_database()
    return detect_documents(limit=payload.limit)
