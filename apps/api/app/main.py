from fastapi import FastAPI

from .db import database_status

app = FastAPI(title="AI Signal Radar API", version="0.1.0")


@app.get("/health")
def health() -> dict:
    return {
        "status": "ok",
        "service": "ai-signal-radar-api",
        "version": "0.1.0",
        "database": database_status(),
    }
