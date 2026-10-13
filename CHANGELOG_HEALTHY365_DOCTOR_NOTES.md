# CHANGELOG — Healthy 365 Connect + Doctor Visit Notes

**Branch / source of truth:** `feature/healthy365-doctor-notes` (ZIP A = authoritative app source)
**Reference only:** ZIP B (`zypulse-healthy365.zip`) — used solely to identify reusable Healthy 365 building blocks; it was **not** copied over ZIP A.
**Date:** 2026-10-13

## 1. Features integrated (from ZIP B → re-applied onto ZIP A's newer code)
- **Healthy 365 Connect** restored inside the existing *Nearby Sports Facilities / Discover Activities* page (`ActivitiesPage`).
  - Existing facilities features, filters, search and the data.gov.sg source note are **untouched**.
  - Two deterministic, preference-driven modes: **Recommended for You** and **Nearest First**.
  - Ranking is **deterministic** (no AI): weighted match on stored `activity_types`, `goals`, `availability`, `location_area` (weights interest 3 / goal 2 / availability 2 / area 1). Each recommended event carries explicit `match_reasons`.
  - No distance is ever fabricated: `distance_display` is always `null`; "Nearest First" orders by area match only.
  - **Safe fallback** when usable preferences are missing (reports the fallback to the user instead of pretending to personalise).
  - Events are clearly labelled **synthetic/demo**, not real Healthy 365 activities, not bookable, and no Healthpoints/partnership/data transfer is implied.
  - Event detail + a **simulated handoff screen** explicitly labelled *"Demo simulation — no actual Healthy 365 registration occurs."* The simulated registration stores a **local-only** record (`source = DEMO/SYNTHETIC_HEALTHY365`), issues a `DEMO-H365-####` confirmation id, and makes **no external call**.
- A demo event can be added to the **Activity Log** as *Planned* or *Completed*, pre-filled but still editable before saving.

## 2. Doctor-visit note features added (new, beyond ZIP B)
- **Opt-in note on Glucose, Medication, and Exercise/Activity logs** using the **exact** checkbox label *"Include this note in visit summary for my doctor"* (default **unchecked**, editable later, persisted; **meal log unchanged** and verified).
- Notes are stored in the column each record type already owns, so nothing is migrated/duplicated and older rows are unaffected:
  - `note` → `value_text`; `meal` / `glucose_*` → `notes`; `medication_*` / `activity*` → new `visit_note` column (their `notes` already holds a generated summary that must not be overwritten).
- A completed **Healthy 365 demo event** can carry an activity note; **Planned** activities are **excluded** from completed-exercise calculations (`get_activity_logs` filters `record_type = 'activity'`).
- **Doctor summary (SummaryPage)** reuses the existing page/export (no second summary). It collects every opted-in note from all log types and labels each by **log type + date/time**, renders user text via React escaping (cannot alter the page, questions, or any calculation), and never invents a diagnosis, treatment, or interpretation.
- History lets you **edit/delete** saved activities and edit any doctor-visit note + opt-in flag.

## 3. Schema / data-layer changes (backward compatible, additive only)
- `health_records` gains two optional columns: `avg_heart_rate INTEGER` and `visit_note TEXT` (added only if absent).
- The legacy `CHECK(record_type)` rebuild now carries `photo_ref`, `avg_heart_rate`, `visit_note` so older rows stay readable.
- New API: `GET /healthy365/events`, `GET /healthy365/events/{id}`, `POST /healthy365/register`, `PUT /logs/activity/{id}`, `DELETE /logs/activity/{id}`, `PUT /records/{id}/visit-note`.

## 4. Files added / modified / deleted
**Added (inside `zypulse-files/`):**
- `backend/services/healthy365.py`
- `backend/data/healthy365_catalogue.json`
- `frontend/src/components/Healthy365Section.jsx`
- `frontend/src/components/Healthy365Handoff.jsx`

**Added (repo root):**
- `test_healthy365.py` (E2E, from reference ZIP B)
- `test_integration_notes_events.py` (new backend integration suite — see §6)
- `CHANGELOG_HEALTHY365_DOCTOR_NOTES.md` (this file)

**Modified:**
- `backend/db/schema.py` — additive migrations + widened CHECK rebuild
- `backend/db/data_access.py` — `VISIT_NOTE_TEXT_FIELD` map; `add_health_record` accepts `avg_heart_rate`/`visit_note`/`activity_planned`; new `find_activity_by_event`, `update_activity_record`, `delete_activity_record`, `set_record_visit_note`, `create_registration(..., source=)`
- `backend/models/schemas.py` — `include_in_visit`/`visit_note` on glucose/medication/activity; `ActivityUpdateRequest`, `VisitNoteUpdateRequest`, Healthy 365 request/response models; `avg_heart_rate` 20–250 validation
- `backend/routers/api.py` — Healthy 365 endpoints; activity planned/completed + dedup/promote; visit-note edit; photo routes from ZIP A preserved
- `frontend/src/api/client.js` — `getHealthy365Events/Event`, `registerHealthy365`, `updateActivity`, `deleteActivity`, `updateVisitNote` (photo helpers preserved)
- `frontend/src/App.jsx` — `activityDraft` + `addToActivityLog` wiring; starts on Activity Log when a draft is set
- `frontend/src/pages/ActivitiesPage.jsx` — renders `Healthy365Section` above the unchanged facilities card
- `frontend/src/pages/LogPage.jsx` — status (Planned/Completed), optional avg heart rate (20–250), demo-event prefill, visit-note checkbox on glucose/medication/activity
- `frontend/src/pages/HistoryPage.jsx` — edit/delete activities; visit-note + opt-in editing; `photoHref` retention preserved
- `frontend/src/pages/SummaryPage.jsx` — collects opted-in notes from all log types, labels by type + date/time, safe rendering, excludes unopted notes
- `frontend/src/i18n.jsx` — Healthy 365 + new labels (incl. exact checkbox label, heart-rate strings, edit/delete)
- `frontend/src/styles/global.css` — Healthy 365 + visit-note-edit styles

**Deleted:** none.

## 5. Conflicts & resolutions
- **ZIP B is an older snapshot** of ZIP A for the shared files (no `photo_assets`, no `ZYPULSE_DB_PATH`, no SPA static serving, no `python-multipart`, no `tests/`, older photo-retention code). Resolution: only the 4 net-new Healthy 365 files were copied from B; every behaviour was **re-ported onto ZIP A's newer modules**. ZIP A's newer features (simulated AI photo logging, photo retention, manual logs, History, Trends, medication safety, DB isolation) are preserved.
- Medication/activity already use `notes` for a generated summary, so the doctor note lives in the new `visit_note` column (not `notes`) — avoids clobbering the summary.

## 6. Test results (executed; PASS/FAIL/{NOT RUN} only from real runs)
Local preview was brought up with an **isolated temp DB and upload dir**; the project's real database and any user/synthetic demo data were never touched.

| Suite | Command | Result |
|---|---|---|
| Backend unit/integration | `python3 test_backend.py` | **33/33 PASS** |
| New Healthy 365 + doctor-notes integration | `python3 test_integration_notes_events.py` | **29/29 PASS** |
| Frontend production build | `pnpm install --frozen-lockfile && pnpm run build` | **BUILD OK** (49 modules, ~255 kB JS / 28 kB CSS) |
| Healthy 365 E2E (Playwright, real UI) | `python3 test_healthy365.py` | **16/16 PASS** |
| Simulated AI photo logging E2E | `python3 test_photolog.py` | **15/15 PASS** |
| Photo retention E2E | `python3 test_photo_retention.py` | **13/13 PASS** |
| Render deploy verification | `tests/test_render_deploy.py` (and `test_render_browser.py`) | **NOT RUN** — requires a deployed Render target on :10000; explicitly excluded by the no-deploy rule |

New integration suite (`test_integration_notes_events.py`) covers: Healthy 365 recommended/nearest/match-reasons/no-fabricated-distance, event detail + demo disclaimer, local-only simulated registration + duplicate handling, planned-vs-completed activity dedup, avg heart rate save/blank (no fabrication), **planned not counted as completed exercise**, glucose/medication/meal/activity visit-note opt-in flag + correct storage column, edit-then-persist, toggle-off exclusion, and legacy-record readability.

## 7. Remaining limitations / never-claims
- **Prototype only.** The photo-storage `user_id` ownership check is **not authentication**; there is still no login system. Do **not** use this for real users' health photos.
- Healthy 365 is **synthetic/demo** with no real API, no real registration, no Healthpoints, no partnership, and no data transfer. A simulated registration is **not attendance** and never creates or completes an activity record on its own.
- Recommendations are preference-based and explicitly state they **do not assess medical suitability**. No diagnosis, treatment, or medication recommendation is ever generated; user note text cannot change system instructions or calculations.
- Verified with isolated temp data and synthetic demo records; **no real health photos** were required or used.

## 8. Local preview (no Render/GitHub needed)
```bash
# Backend (FastAPI)
cd zypulse-files/backend
pip install -r requirements.txt
export ZYPULSE_DB_PATH=/tmp/zypulse.db        # isolated; gets seeded with demo data
export ZYPULSE_UPLOAD_DIR=/tmp/zypulse_uploads
python3 -m uvicorn backend.main:app --host 127.0.0.1 --port 8000

# Frontend (Vite dev, proxies /api -> :8000)
cd ../frontend
pnpm install
pnpm dev --port 3000
# open http://127.0.0.1:3000
```
Run the tests from the folder that contains `zypulse-files/`:
```bash
python3 test_backend.py
python3 test_integration_notes_events.py
python3 test_healthy365.py          # needs both servers above running
python3 test_photolog.py            # needs both servers above running
python3 test_photo_retention.py     # needs both servers above running
```

## 9. Manual verification recommended before merge
- Click through Healthy 365 → Recommended/Nearest → event detail → simulated handoff → "Add to Activity Log" (Planned & Completed) and confirm the entry appears in History with the right icon/label.
- Log a glucose/medication/activity with the visit-note checkbox ticked; open Health Summary → "Notes for My Doctor" and confirm the note appears labelled by type + date/time.
- Untick the checkbox (or edit the note in History) and confirm the summary updates and excludes the note.
- Confirm a **Planned** activity does **not** show up as completed exercise in Trends/Summary.
