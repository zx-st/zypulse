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
from fastapi import FastAPI, HTTPException
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

# CORS - local origins by default; add deployed frontend URLs with the
# comma-separated FRONTEND_ORIGINS environment variable on Render.
frontend_origins = [
    "http://localhost:5173",
    "http://localhost:3000",
    "http://127.0.0.1:5173",
    "http://127.0.0.1:3000",
]
frontend_origins.extend(
    origin.strip()
    for origin in os.environ.get("FRONTEND_ORIGINS", "").split(",")
    if origin.strip()
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=frontend_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# The API router already owns the /api prefix. Mounting it without another
# prefix prevents deployed routes from becoming /api/api/... .
app.include_router(api_router)


# ---------------------------------------------------------------------------
# Single-service deployment: serve the compiled React/Vite frontend from
# FastAPI so the whole prototype runs on ONE Render Web Service.
#
# Route order matters and is intentionally:
#   /openapi.json, /docs, /redoc  (registered by FastAPI at construction)
#   -> /api/**                    (registered by include_router above)
#   -> /assets/**, /sample-photos/** and other built files (mounts below)
#   -> "/" and "/health"
#   -> SPA catch-all (registered last, at the bottom of this module)
# ---------------------------------------------------------------------------
FRONTEND_DIST = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "frontend", "dist")
)
SPA_INDEX = os.path.join(FRONTEND_DIST, "index.html")
SPA_AVAILABLE = os.path.isfile(SPA_INDEX)

if SPA_AVAILABLE:
    from fastapi.staticfiles import StaticFiles

    # Serve every top-level entry of the Vite build output (assets/,
    # sample-photos/, ...). Mounting per entry keeps "/" free for the SPA shell
    # and avoids shadowing the API routes above.
    for _entry in sorted(os.listdir(FRONTEND_DIST)):
        _src = os.path.join(FRONTEND_DIST, _entry)
        if os.path.isdir(_src):
            app.mount(
                f"/{_entry}",
                StaticFiles(directory=_src),
                name=f"spa-{_entry}",
            )
else:
    print(
        "[ZyPulse] frontend/dist not found - running API only. "
        "Run ./build.sh (or `pnpm build` in frontend/) to enable the web UI."
    )


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

    # Drop abandoned uploads (never confirmed) and uploads whose record was
    # deleted, so private photo files do not accumulate without an owner.
    try:
        from .db.data_access import get_db as _get_db
        purged = _get_db(DB_PATH).purge_orphan_photos()
        if purged["pending_expired"] or purged["missing_record"]:
            print(f"[ZyPulse] Purged orphan photos: {purged}")
    except Exception as exc:  # pragma: no cover - never block startup
        print(f"[ZyPulse] photo purge skipped: {exc}")

    global _reminder_task
    _reminder_task = asyncio.create_task(_reminder_loop())


@app.on_event("shutdown")
async def shutdown_event():
    if _reminder_task:
        _reminder_task.cancel()


_API_INFO = {
    "name": "ZyPulse API",
    "version": "0.1.0",
    "status": "running",
    "description": "Personalised AI Self-Care Companion for Type 2 Diabetes",
    "safety_notice": "This is a self-care support prototype, not a medical device.",
    "docs": "/docs",
    "ui": "React frontend served from / when frontend/dist exists",
}


@app.get("/api/info")
async def api_info():
    """Service metadata.

    Keeps the payload previously returned by "/" reachable once the compiled
    frontend takes over the root path.
    """
    return _API_INFO


@app.get("/")
async def root():
    """Serve the compiled React app, falling back to API metadata in dev."""
    if SPA_AVAILABLE:
        from fastapi.responses import FileResponse
        return FileResponse(SPA_INDEX)
    return _API_INFO


@app.get("/health")
async def health():
    """Health check."""
    return {"status": "ok", "timestamp": now_utc_iso(), "timezone": "Asia/Singapore"}


if SPA_AVAILABLE:
    from fastapi.responses import FileResponse

    @app.get("/{full_path:path}")
    async def spa_fallback(full_path: str):
        """Serve static files, then fall back to the SPA shell.

        Unknown GET paths return index.html so client-side navigation and deep
        links render instead of 404. Unknown /api paths still return a real 404
        so client error handling keeps working.
        """
        trimmed = (full_path or "").strip("/")
        if trimmed == "api" or trimmed.startswith("api/"):
            raise HTTPException(status_code=404, detail="Not Found")
        candidate = os.path.normpath(os.path.join(FRONTEND_DIST, trimmed))
        if candidate.startswith(FRONTEND_DIST) and os.path.isfile(candidate):
            return FileResponse(candidate)
        return FileResponse(SPA_INDEX)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "backend.main:app",
        host=os.environ.get("HOST", "0.0.0.0"),
        port=int(os.environ.get("PORT", "8000")),
        reload=False,
    )
