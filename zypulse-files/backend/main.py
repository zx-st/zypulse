"""
ZyPulse Backend - FastAPI Application Entry Point

Central orchestration hub:
- Receives all frontend requests
- Routes to appropriate sub-components
- Enforces validation (Pydantic)
- Persists data (SQLite)
- Calls LLM (single call)
- Applies safety checks (C4)
- Returns responses

Run: uvicorn backend.main:app --reload --port 8000
"""

import asyncio
import os
import sys
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

# Add backend to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Local credentials stay outside source control in backend/.env.
load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))

from .routers.api import router as api_router
from .db.schema import init_db, DB_PATH
from .db.seed import seed_all
from .services.reminders import dispatch_due_reminders
from .time_utils import now_utc_iso

_reminder_task = None


async def _reminder_loop():
    """Run the persistent in-app reminder dispatcher once a minute."""
    from .db.data_access import get_db
    while True:
        try:
            dispatch_due_reminders(get_db(DB_PATH))
        except Exception as exc:
            print(f"[ZyPulse] reminder dispatcher error: {exc}")
        await asyncio.sleep(60)

app = FastAPI(
    title="ZyPulse API",
    description="Personalised AI Self-Care Companion for Type 2 Diabetes",
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS - allow frontend (Vite dev server on localhost:5173)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://localhost:3000",
        "http://127.0.0.1:5173",
        "http://127.0.0.1:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount API router
app.include_router(api_router, prefix="")


@app.on_event("startup")
async def startup_event():
    """Initialize database and seed data on startup."""
    print(f"[ZyPulse] Initializing database at {DB_PATH}")
    init_db(DB_PATH)

    # Seed synthetic data if database is empty
    from .db.data_access import get_db
    db = get_db(DB_PATH)
    test_records = db.get_health_records("mr_tan_001", limit=1)
    if not test_records:
        print("[ZyPulse] Database empty - seeding synthetic data...")
        seed_all(DB_PATH)
    else:
        print("[ZyPulse] Database already has data - skipping seed.")
    global _reminder_task
    _reminder_task = asyncio.create_task(_reminder_loop())


@app.on_event("shutdown")
async def shutdown_event():
    if _reminder_task:
        _reminder_task.cancel()


@app.get("/")
async def root():
    """Health check endpoint."""
    return {
        "name": "ZyPulse API",
        "version": "0.1.0",
        "status": "running",
        "description": "Personalised AI Self-Care Companion for Type 2 Diabetes",
        "safety_notice": "This is a self-care support prototype, not a medical device.",
        "docs": "/docs",
    }


@app.get("/health")
async def health():
    """Health check."""
    return {"status": "ok", "timestamp": now_utc_iso(), "timezone": "Asia/Singapore"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.main:app", host="0.0.0.0", port=8000, reload=True)
