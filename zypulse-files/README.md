# ZyPulse - Personalised AI Self-Care Companion

Tencent Cloud AI Singapore Hackathon 2026 · Healthcare Track · Challenge Statement 2

## Project layout

This project is **not** at the repository root. All commands below run from the
folder that contains `backend/` and `frontend/`:

```
<repository>/
└── zypulse-files/
    ├── backend/     # FastAPI + SQLite
    ├── frontend/    # React 18 + Vite 5 + pnpm
    ├── build.sh     # optional single-service build script
    ├── render.yaml  # optional Render Blueprint
    └── tests/       # deployment smoke tests
```

Working directory for every command in this README: `zypulse-files/`.

```bash
cd zypulse-files
```

## Run locally (two processes)

### 1. Backend (FastAPI + SQLite)
```bash
pip install -r backend/requirements.txt
python3 -m uvicorn backend.main:app --host 0.0.0.0 --port 8000
```
API docs: <http://localhost:8000/docs> · Health: <http://localhost:8000/health>

### 2. Frontend (React + Vite)
```bash
cd frontend
pnpm install --frozen-lockfile
pnpm dev --port 3000          # or: env PORT=3000 pnpm dev
```
App: <http://localhost:3000> (Vite proxies `/api` to `localhost:8000`).

The SQLite database (`backend/zypulse.db`) is created and seeded with 156
synthetic records for the demo user `mr_tan_001` on first start.

### Optional: one process (backend serves the built frontend)
```bash
cd frontend && pnpm install --frozen-lockfile && pnpm run build && cd ..
python3 -m uvicorn backend.main:app --host 0.0.0.0 --port 10000
# open http://localhost:10000
```
`backend/main.py` mounts `frontend/dist` when it exists and serves `index.html`
for unknown paths (deep links), while `/api/**`, `/health`, `/docs` and `/redoc`
keep working. The service metadata that `GET /` used to return is now at
`GET /api/info`.

## Simulated AI photo logging

**There is no real vision model anywhere in this project.** Recognition is a
deterministic, replaceable module (`backend/services/photo_recognition.py`) that
maps a *known sample id* to a hand-authored extraction payload. The same sample
always returns the same values.

### Bundled sample photos (reliable demo path)
12 illustrated PNGs in `frontend/public/sample-photos/`:

| Category | Samples |
|---|---|
| Glucose | `glucose_1.png` (7.2 mmol/L), `glucose_2.png` (5.4 mmol/L), `glucose_unclear.png` (not legible → you must type the value) |
| Medication | `med_pkg.png` (name/strength), `med_tablets.png` (2 tablets visible), `med_unclear.png` (quantity unclear), `med_saved.png` (matches saved list) |
| Meal | `meal_chicken_rice.png`, `meal_fish_soup.png`, `meal_nasi_lemak.png`, `meal_roti_teh.png`, `meal_mooncake.png` |

Nutrition values come from the existing `backend/data/food_catalogue.json`,
which has carbohydrate and sugar per standard serving only. Calories and
protein are **not** invented — the UI shows "Estimate unavailable" and you can
type a value if you have one.

### Arbitrary uploads (manual fallback)
Any other photo is reported as **not recognised**:

> "This photo is not a recognised demo asset. Photo recognition is simulated in
> this prototype, so the image was not analysed. Please enter the details
> manually."

The uploaded original is still shown in the review screen, and every field
(reading, medication, or meal items/portion/carbs) is yours to fill in. Nothing
is read out of the image, and no value is ever guessed from it.

## How uploaded photos are stored (and the limits)

| Aspect | Behaviour |
|---|---|
| When | The file is stored **only after you press "Confirm & Save"**. Picking or cancelling a photo never writes a file. |
| Where | `backend/var/uploads/<user_id>/<random key>.<ext>` — outside the web root, never in `frontend/public`. Override with `ZYPULSE_UPLOAD_DIR`. |
| Index | A row in the `photo_assets` table (owner, type, size, sha256, linked record, status). |
| Read access | `GET /api/photos/{key}?user_id=...` only. A guessed key alone returns 404; the caller must also repeat the owning `user_id`. Responses are `Cache-Control: private, no-store`. Bundled demo images stay public static assets. **This is an ownership check, not authentication — see the security limitation below.** |
| Record link | The record's `photo_ref` is `photo:<key>`; History renders it as "View original photo". |
| Editing | Editing a meal keeps the photo association (the update only touches the fields it is given). |
| Deleting | Deleting a meal deletes its stored original, so no orphan is left behind. |
| Cleanup | On startup the app deletes uploads never confirmed (older than 24 h) and uploads whose record no longer exists. |
| Validation | PNG / JPEG / WebP only, max 8 MB, magic bytes checked server-side. |
| Duplicates | A photo can be attached to one record only; attaching twice is a no-op, so a repeated confirm cannot duplicate the entry. |

> **Security limitation (important — read before storing anything real):**
> ZyPulse has **no login, no password, no session and no token**. Every request
> (records, preferences, photos) identifies the user with a plain `user_id`
> string that the caller supplies — the API cannot verify who is calling. The
> photo endpoint therefore provides an **ownership check, not authentication**:
> it stops accidental or casual URL guessing, and nothing more. Anyone who knows
> or guesses a valid `photo_key` **and** its `user_id` can download that image,
> and the same applies to every other `/api` route in this prototype.
>
> Consequently this build is **not suitable for storing real users' health
> photos or real personal health data**. It is a synthetic-demo prototype: use
> the bundled sample photos and the fictional `mr_tan_001` dataset. Before any
> real-patient use it would need real authentication (sessions/OIDC),
> authorisation on every route, transport security, encryption at rest, audit
> and retention controls — none of which exist here. Uploads are additionally
> stored unencrypted on local disk.

> **Persistence limitation (important):** uploads live on the same local disk as
> the SQLite database. On a host with an ephemeral file system — including a
> Render Free instance, which is rebuilt on every deploy — **both the database
> and the uploaded photos are lost on redeploy or restart**, after which the app
> re-seeds the synthetic dataset. The app does **not** use object storage and
> makes no claim that uploads survive a redeploy. For durable photos, point
> `ZYPULSE_UPLOAD_DIR` at a mounted persistent disk.

## Tests actually executed for this release

All commands run from `zypulse-files` unless stated. Backend on `:8000`,
frontend dev server on `:3000`.

| Suite | Command | Result |
|---|---|---|
| Backend + safety + photo storage + test isolation | `python3 test_backend.py` (from the parent folder) | **33/33 PASS** |
| Photo logging UI (samples, manual fallback, edit/delete) | `python3 test_photolog.py` | **15/15 PASS** |
| Original photo retention (upload → save → History → reload) | `python3 test_photo_retention.py` | **13/13 PASS** |
| Single-service deployment smoke | `python3 tests/test_render_deploy.py` | **25/25 PASS** |
| Single-service browser check | `python3 tests/test_render_browser.py` | **14/14 PASS** |
| Frontend production build | `cd frontend && pnpm run build` | **PASS** |

How to reproduce (backend on `:8000`, frontend dev server on `:3000`, then run
each suite from the folder that contains `zypulse-files/`):

```bash
cd zypulse-files
ZYPULSE_DB_PATH=/tmp/zypulse_e2e.db python3 -m uvicorn backend.main:app --host 0.0.0.0 --port 8000 &
cd frontend && pnpm install --frozen-lockfile && pnpm dev --port 3000 &
cd ../.. && python3 test_backend.py && python3 test_photolog.py && python3 test_photo_retention.py
```

Notes on test fidelity:

- `test_backend.py` creates a **temporary** SQLite database and upload directory
  (`ZYPULSE_DB_PATH`, `ZYPULSE_UPLOAD_DIR`) before importing the app, and enters
  it with `with TestClient(app)` so the real FastAPI startup hook creates and
  seeds the schema. It also asserts that the project's own `zypulse.db` was not
  created or changed. It previously failed with `sqlite3.OperationalError: no such
  table: health_records` because the startup hook never ran.
- `test_photolog.py` was adjusted in one place only: its `open_picker` helper now
  leaves the review screen before reopening the picker, because an uploaded
  photo now opens the review screen instead of staying on the picker. No
  assertion was weakened.
- Safety rules are asserted against `SafetyEngine.screen_input`: stopping
  medication, dose changes and diagnosis requests are blocked; ordinary
  self-care questions pass.
- Photo retention is asserted end to end: PNG upload → nothing stored before
  confirm → confirm stores one file → History links to the owner-checked
  endpoint → reload keeps it readable → meal/medication records carry their own
  photo → deleting the meal deletes its file.
- **NOT TESTED:** a real deployment on Render (no account/CLI access, and this
  task explicitly excludes GitHub/Render operations) and camera capture on a
  physical device (no device available — uploads are driven with a generated PNG
  file instead).

## Deploying to Render (advice only — nothing is deployed here)

The FastAPI backend serves the compiled React/Vite frontend, so a single Web
Service hosts UI + API on one domain. No paid add-ons, no external AI service,
no extra database.

| Setting | Value |
|---|---|
| **Root Directory** | The folder that contains `backend/` and `frontend/` — in this archive that is `zypulse-files`. If those folders sit at your repository root, use `.` |
| **Environment** | `Python 3` |
| **Build Command** | `./build.sh` |
| **Start Command** | `python -m uvicorn backend.main:app --host 0.0.0.0 --port $PORT` |
| **Health Check Path** | `/health` |

`build.sh` installs `backend/requirements.txt`, ensures Node.js + pnpm are
available, then runs `pnpm install --frozen-lockfile && pnpm run build`.

`render.yaml` is an **optional** Blueprint for the same setup. Render reads a
Blueprint from the **repository root**, so if you keep it, either move it to the
root and set `rootDir: zypulse-files`, or delete it and configure the service by
hand with the table above. A Blueprint inside `zypulse-files/` is ignored by
Render's automatic detection.

### Environment variables

| Key | Required | Value / notes |
|---|---|---|
| `PORT` | Auto | Injected by Render; the app binds `0.0.0.0:$PORT` |
| `NODE_VERSION` | **Yes** | `22` — makes Render install a Node toolchain on a Python service |
| `PYTHON_VERSION` | Recommended | `3.11` |
| `FRONTEND_ORIGINS` | No | Extra CORS origins, comma separated. Not needed for same-origin single-service deploys |
| `OPENAI_API_KEY` | No | Optional conversational AI. Absent → deterministic fallback. Never commit the value |
| `OPENAI_MODEL` | No | e.g. `gpt-5.4-mini` |
| `ZYPULSE_UPLOAD_DIR` | No | Private upload directory. Defaults to `backend/var/uploads` |
| `ZYPULSE_DB_PATH` | No | SQLite file location. Defaults to `backend/zypulse.db`. Tests use it to point at a temporary database so your own database is never touched |

`backend/.env` is never committed (see `.gitignore`).

### Deployment risks

- SQLite and uploaded photos live on Render's **ephemeral** disk. Data written
  at runtime is lost on redeploy or restart; the app then re-creates and
  re-seeds the synthetic demo dataset. Attach a Render Disk (and point
  `ZYPULSE_UPLOAD_DIR` at it) if you need data to survive.
- The frontend calls `/api` relatively, so no host is hard-coded.
- `/api/**`, `/health`, `/docs` and `/redoc` are untouched by the SPA fallback;
  unknown `/api` paths still return a real 404.
- `react-router-dom` is listed in `frontend/package.json` but the app switches
  pages with React state, so there are no router URLs to deep link. The SPA
  fallback still serves `index.html` for unknown paths.

## Architecture Overview

```
zypulse-files/
├── backend/
│   ├── main.py              # FastAPI app entry point (+ optional SPA serving)
│   ├── routers/
│   │   └── api.py           # All REST endpoints
│   ├── engine/
│   │   ├── calculations.py  # C3: Deterministic calc engine
│   │   ├── safety.py        # C4: Safety/policy engine (non-bypassable)
│   │   └── ai_orchestrator.py # C5: Single LLM call
│   ├── services/
│   │   ├── photo_recognition.py # Simulated, replaceable vision module
│   │   ├── photo_storage.py     # Private storage for uploaded originals
│   │   └── sport_facilities.py  # Sport Singapore public facility-data adapter
│   ├── db/
│   │   ├── schema.py         # SQLite tables + additive migrations
│   │   ├── data_access.py    # Data access layer
│   │   └── seed.py           # Synthetic data seeding
│   ├── models/
│   │   └── schemas.py        # Pydantic validation models
│   └── data/
│       ├── mr_tan_30day.json   # Synthetic 30-day data
│       ├── food_catalogue.json # Carbs/sugar per serving
│       └── activity_catalogue.json
├── frontend/
│   ├── public/sample-photos/  # 12 bundled demo images
│   ├── src/
│   │   ├── App.jsx           # Main app with navigation
│   │   ├── pages/            # Today, Log, Meals, Trends, History, Coach, Activities
│   │   ├── components/       # Header, NavBar, PhotoLogWorkflow
│   │   └── api/client.js     # API client
│   └── package.json
└── tests/                    # Single-service deployment smoke tests
```

## Core Principles

1. **AI for language; deterministic code for everything that matters**
2. **Safety engine is non-bypassable** - keyword/regex screening, fails safe
3. **Separated data stores** - health records, preferences, AI memory, registration, sharing, photo assets
4. **LLM never calculates** - C3 computes all numbers, LLM only explains
5. **Fallback mode** - if LLM unavailable, deterministic trends still work

## Endpoints

| Endpoint | Method | Purpose |
|---|---|---|
| `/health` | GET | Health check |
| `/api/info` | GET | Service metadata |
| `/api/logs/glucose` | POST | Log glucose reading (`recorded_date` required) |
| `/api/logs/medication` | POST | Log medication status (`recorded_date` required) |
| `/api/logs/activity` | POST | Log activity (`recorded_date` required) |
| `/api/meals` | GET/POST | List / create meals |
| `/api/meals/{id}` | PUT/DELETE | Edit / delete a meal (deletes its uploaded photo) |
| `/api/chat` | POST | Chat with AI (core workflow) |
| `/api/daily-briefing` | POST | Deterministic + optional LLM briefing |
| `/api/trends` | GET | Deterministic trends |
| `/api/preferences` | GET/PUT | User preferences |
| `/api/notes` | POST | Notes for doctor |
| `/api/activities` | GET | Sport Singapore facility catalogue |
| `/api/photo-samples` | GET | Bundled demo samples |
| `/api/photo-analyze` | POST | Simulated recognition (samples only) |
| `/api/photos/upload` | POST | Store an uploaded original (multipart: `file`, `user_id`) |
| `/api/photos/{key}` | GET/DELETE | Owner-checked read / discard of an unconfirmed upload |
| `/api/photos/{key}/attach` | POST | Link an upload to its confirmed record |

## To Enable OpenAI (Coach and Daily Briefing)

Create `backend/.env` from `backend/.env.example` and set `OPENAI_API_KEY` to a
project API key. Do not put a key in frontend code or commit it.

```powershell
$env:OPENAI_API_KEY="your-project-api-key"
$env:OPENAI_MODEL="gpt-5.4-mini"
python -m uvicorn backend.main:app --reload --port 8000
```

The app uses OpenAI's Responses API with `store: false`; if a key is absent, it
stays in deterministic fallback mode. The generic `ZYPULSE_LLM_*` configuration
remains supported for an OpenAI-compatible or Tencent Hunyuan endpoint.

## Sports facility data

`GET /api/activities` retrieves the public Sport Singapore `Sport Facilities`
dataset through data.gov.sg, then caches and groups its facility types by venue.
It contains facility capabilities, not class schedules or booking availability.
For production, set `DATA_GOV_SG_API_KEY` in `backend/.env` to use a registered
data.gov.sg API key; the source is public and also works without one for testing.
