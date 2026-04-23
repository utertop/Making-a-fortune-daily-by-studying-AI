from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .db import database_status
from .repository import list_top_signals

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
    safe_limit = max(1, min(limit, 50))
    return {"signals": list_top_signals(limit=safe_limit)}
