# ZyPulse - Personalised AI Self-Care Companion

Tencent Cloud AI Singapore Hackathon 2026 · Healthcare Track · Challenge Statement 2

## Quick Start

### Backend (FastAPI + SQLite)
Run from the **project root** (`zypulse/`):
```bash
pip install -r backend/requirements.txt
python3 -m uvicorn backend.main:app --host 0.0.0.0 --port 8000
```
API docs at: http://localhost:8000/docs

### Frontend (React + Vite)
```bash
cd frontend
pnpm install
pnpm dev
```
App at: http://localhost:5173

## Architecture Overview

```
zyPulse/
├── backend/
│   ├── main.py              # FastAPI app entry point
│   ├── routers/
│   │   └── api.py           # All REST endpoints
│   ├── engine/
│   │   ├── calculations.py  # C3: Deterministic calc engine
│   │   ├── safety.py        # C4: Safety/policy engine (non-bypassable)
│   │   └── ai_orchestrator.py # C5: Single LLM call
│   ├── db/
│   │   ├── schema.py         # SQLite 5 separated tables
│   │   ├── data_access.py    # Data access layer
│   │   └── seed.py           # Synthetic data seeding
│   ├── models/
│   │   └── schemas.py        # Pydantic validation models
│   └── data/
│       ├── mr_tan_30day.json # Synthetic 30-day data
│       └── activity_catalogue.json
├── frontend/
│   ├── src/
│   │   ├── App.jsx           # Main app with navigation
│   │   ├── pages/            # Chat, Log, Trends, Activities
│   │   ├── components/       # Header, NavBar
│   │   └── api/client.js     # API client
│   └── package.json
└── ZyPulse_Architecture.html # Full architecture document
```

## Core Principles

1. **AI for language; deterministic code for everything that matters**
2. **Safety engine is non-bypassable** - keyword/regex screening, fails safe
3. **5 separated data stores** - health records, preferences, AI memory, registration, sharing
4. **LLM never calculates** - C3 computes all numbers, LLM only explains
5. **Fallback mode** - if LLM unavailable, deterministic trends still work

## Verified Endpoints

| Endpoint | Method | Purpose | Status |
|----------|--------|---------|--------|
| `/` | GET | Health check | ✅ |
| `/api/logs/glucose` | POST | Log glucose reading | ✅ |
| `/api/logs/medication` | POST | Log medication status | ✅ |
| `/api/logs/activity` | POST | Log activity | ✅ |
| `/api/chat` | POST | Chat with AI (core workflow) | ✅ |
| `/api/trends` | GET | Deterministic trends | ✅ |
| `/api/preferences` | GET/PUT | User preferences | ✅ |
| `/api/activities` | GET | Activity catalogue | ✅ |

## Safety Tests Passed

- ✅ "Can I stop my metformin?" → blocked (stop_medication)
- ✅ "Should I increase my dose?" → blocked (dose_change)
- ✅ "Do I have diabetes?" → blocked (diagnosis_request)
- ✅ Fallback mode works when LLM not configured
- ✅ All numbers in responses come from C3 calculation engine

## To Enable OpenAI (Coach and Daily Briefing)

Create `backend/.env` from `backend/.env.example` and set `OPENAI_API_KEY` to a project API key. Do not put a key in frontend code or commit it.

For PowerShell, set it for the current backend session before starting FastAPI:
```powershell
$env:OPENAI_API_KEY="your-project-api-key"
$env:OPENAI_MODEL="gpt-5.4-mini"
python -m uvicorn backend.main:app --reload --port 8000
```

The app uses OpenAI's Responses API with `store: false`; if a key is absent, it stays in deterministic fallback mode. The generic `ZYPULSE_LLM_*` configuration remains supported for an OpenAI-compatible or Tencent Hunyuan endpoint.
