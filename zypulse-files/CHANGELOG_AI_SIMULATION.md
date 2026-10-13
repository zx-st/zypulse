# ZyPulse — Simulated AI Photo Logging (feature/AI-simulation)

Targeted feature addition on top of the uploaded `feature/AI-simulation` ZIP.
Architecture, navigation, styling, existing manual logging, trends, safety rules and the
conversational AI are unchanged. No external AI API, key or paid service is used.

---

## 1. Files added

| File | Purpose |
|---|---|
| `backend/services/photo_recognition.py` | **The single replaceable simulated-Vision-AI module.** Holds the deterministic `SAMPLE_LIBRARY`, reuses the existing `backend/data/food_catalogue.json`, and exposes `analyze()` / `list_samples()`. |
| `frontend/src/components/PhotoLogWorkflow.jsx` | **One shared workflow component** used by glucose, medication and meal: sample picker → upload → simulated extraction → review/edit → confirm → save. |
| `frontend/public/sample-photos/*.png` (12 files) | Bundled demo image assets: `glucose_1/2/unclear`, `med_pkg/med_tablets/med_unclear/med_saved`, `meal_chicken_rice/meal_fish_soup/meal_nasi_lemak/meal_roti_teh/meal_mooncake`. |

## 2. Files modified

| File | Change (minimal, additive) |
|---|---|
| `backend/db/schema.py` | Additive migration adds a nullable `photo_ref` column to `health_records`. No existing column/row changed. |
| `backend/db/data_access.py` | `add_health_record()` and `update_meal()` accept an optional `photo_ref`. Existing calls unchanged. |
| `backend/models/schemas.py` | `photo_ref` added to `GlucoseLogRequest`, `MedicationLogRequest`, `MealLogRequest`, `HealthRecordResponse`; `calories` / `protein` / `source` added to `MealItem`; `PhotoAnalyzeRequest`/`Response` extended to the new extraction contract. |
| `backend/routers/api.py` | Import of the photo service; new `GET /api/photo-samples`; `POST /api/photo-analyze` rewritten to delegate to the service; `photo_ref` passed through the glucose, medication and meal create endpoints. |
| `frontend/src/api/client.js` | `getPhotoSamples(category)` added. |
| `frontend/src/pages/LogPage.jsx` | "📷 Scan Reading" and "📷 Scan Medication" buttons + wiring of the shared component. Manual forms untouched. |
| `frontend/src/pages/MealLogPage.jsx` | The previous bespoke fixed-stub photo block is replaced by the shared component; photo-log favourites (localStorage) quick-add added with nutrition values preserved. |
| `frontend/src/pages/HistoryPage.jsx` | Small "📷 View original photo" link rendered only when a record has a photo reference. |
| `frontend/src/styles/global.css` | Minimal styles for the workflow (sample grid, review panel, badges, nutrition rows). Existing classes untouched. |

No changes were made to: safety engine, trend calculations, AI orchestrator / Ask ZyPulse, reminders, sport facilities, navigation, routing, database records or seed data.

## 3. Functions implemented

- `photo_recognition.list_samples(category)` — sample metadata for the picker (label, image, unclear / needs-review / saved-list flags).
- `photo_recognition.analyze(category, sample_id, filename)` — returns `{recognized, simulated, category, sample_id, image, extraction, reason, disclaimer}`. Known `sample_id` → identical predefined extraction every time; anything else → `recognized=False` + reason so the UI falls back to manual entry. No random values.
- `photo_recognition._catalogue_item()` — builds meal items from the **existing** `food_catalogue.json` (carbohydrate + sugar per 1 standard serving). Calories and protein are absent from that catalogue, so they are returned as `null`.
- `PhotoLogWorkflow` — file-type/size validation, duplicate-save guard (`busy` state), editable review fields, unit support (mmol/L ↔ mg/dL with deterministic conversion), portion factors ¼/½/¾/1/1½/2/custom, medication "actually took" confirmation, meal modification note, favourites hook.
- `LogPage.confirmGlucosePhoto` / `confirmMedPhoto`, `MealLogPage.savePhotoMeal` — call the **existing** create endpoints and attach `photo_ref`.

## 4. Demo scenarios (12 samples)

- **Glucose (3):** 7.2 mmol/L (clear), 5.4 mmol/L (clear, different value), unreadable display (needs review → user must type the value; nothing is guessed).
- **Medication (4):** packaging with name + strength, blister with 2 tablets visible, unclear quantity, match with the user's saved medication list.
- **Meal (5):** Chicken Rice, Fish Soup, Nasi Lemak, Roti Prata + Teh Tarik (2 items in one meal), Mooncake snack.

## 5. Tests (executed against the running app)

`python3 test_photolog.py` — Playwright (sync) driving the real UI at `http://localhost:3000` against the backend at `http://localhost:8000`.

| # | Scenario | Result |
|---|---|---|
| 1 | Glucose sample → review → save | PASS (prefilled 7.2) |
| 2 | Glucose sample → edit reading (9.1) → save | PASS |
| 3 | Unclear glucose → "Needs your review" + blocks empty confirm | PASS |
| 4 | Medication sample → confirm actual intake → save | PASS |
| 5 | Medication sample → edit quantity (3) → save | PASS |
| 6 | Meal sample → portion ½ → save (total ~25 g carbs) | PASS |
| 7 | Meal sample → "less sweet" modification | PASS |
| 8 | Meal sample → save favourite → reuse from quick-add chip | PASS |
| 9 | Unsupported uploaded image → manual-entry fallback message | PASS |
| 10 | Cancel → no record created (206 → 206) | PASS |
| 11 | "View original photo" link in History | PASS |
| 12 | Existing manual glucose logging still works | PASS |
| 13 | Trends / History / Ask ZyPulse still functional | PASS |
| 14 | Edit + delete a photo-assisted meal record (22 → 21) | PASS |
| 0 | No console / page errors during the run | PASS |

**15/15 passed.** Frontend production build (`npx vite build`) also passes: 47 modules, `dist/assets/index-*.js` 226 kB.

## 6. Known limitations

1. **Demo images are generated illustrations**, not photographs of real meters, packaging or food. Each is clearly labelled "(demo)" on the image itself and in the UI. No stock photos were available offline.
2. **No real image recognition.** Only the 12 bundled sample ids return an extraction; any other upload is reported as unrecognised and the user enters data manually. This is stated in the UI, never hidden.
3. **Calories and protein are "Estimate unavailable"** for every sample, because the existing `food_catalogue.json` contains only carbohydrate and sugar. Both fields remain user-editable. No values were invented.
4. **Photo storage is a reference, not an uploaded file** *(superseded — see "Maintenance follow-up: original photo retention" below)*. At that point `photo_ref` stored the path of the bundled demo asset (or nothing for manual fallback). Arbitrary uploaded images were **not** persisted — the prototype had no blob/image store, so uploaded photos could not be re-opened later. This is reported rather than presented as working.
5. **Medication samples use Metformin only**, matching the existing demo persona; strength is never confused with quantity, and intake must be confirmed explicitly — a photo never marks a dose as taken.
6. The photo workflow is English-labelled; the existing i18n dictionary is untouched, so untranslated strings fall back to English in other languages.
7. Test runs add demo records to the local SQLite database; the exported ZIP contains no database file (the app re-seeds on startup, as in the original project).

---

## Maintenance follow-up: original photo retention (later change)

The limitation recorded in point 4 above has since been addressed. Uploaded
originals are now stored privately and reopened from History.

### Added
- `backend/services/photo_storage.py` — private upload directory, type/size/magic-byte validation, orphan purge.
- `photo_assets` table in `backend/db/schema.py` — owner, checksum, linked record, status.
- `POST /api/photos/upload`, `GET /api/photos/{key}`, `DELETE /api/photos/{key}`, `POST /api/photos/{key}/attach` in `backend/routers/api.py`.
- `PhotoUploadResponse` / `PhotoAttachResponse` in `backend/models/schemas.py`.
- `test_photo_retention.py`, `test_backend.py` (parent folder).

### Modified
- `backend/db/schema.py` — the legacy `CHECK(record_type …)` rebuild now carries `photo_ref` over, so an older database no longer loses photo references during migration.
- `backend/db/data_access.py` — photo asset CRUD, `delete_meal` now removes the stored original, `purge_orphan_photos()`.
- `backend/main.py` — purges abandoned uploads on startup.
- `backend/requirements.txt` — adds `python-multipart` (required for multipart uploads).
- `frontend/src/components/PhotoLogWorkflow.jsx` — local preview of the upload, client-side type/size validation, upload on confirm, rollback on failure, editable manual meal items.
- `frontend/src/pages/HistoryPage.jsx` — renders `photo:<key>` references through the ownership-checked endpoint.
- `frontend/src/pages/LogPage.jsx`, `frontend/src/pages/MealLogPage.jsx` — return the new `record_id` so the photo can be attached.
- `frontend/src/api/client.js`, `frontend/src/i18n.jsx`, `.gitignore`, `README.md`, `test_photolog.py` (navigation helper only).

### Still true
- Recognition remains simulated: uploads are never analysed, only stored.
- Uploads persist as far as the host's disk does. On an ephemeral host (Render Free) they are lost together with the database on redeploy.

---

## Maintenance follow-up 2: verification pass (test isolation, security wording, retention proof)

No feature, UI or architecture change. This pass fixes how the photo-retention
work is tested and documented.

### 1. Backend test initialisation (bug fix)
- **Bug:** `test_backend.py` failed with `sqlite3.OperationalError: no such table:
  health_records`. Two causes:
  1. `TestClient(app)` was created without a context manager, so FastAPI's
     startup hook (which calls `init_db()` + `seed_all()`) never ran;
  2. the test did not isolate the database, so it would have used (or created)
     the developer's `backend/zypulse.db`.
- **Fix:** the test now sets `ZYPULSE_DB_PATH` and `ZYPULSE_UPLOAD_DIR` to a
  temporary directory **before** importing any backend module, and enters the app
  with `with TestClient(app) as client:` so the real startup/lifespan hook runs.
- `backend/db/schema.py` now honours `ZYPULSE_DB_PATH` (default unchanged:
  `backend/zypulse.db`).
- Two new assertions prove isolation: the temporary database is in the temp
  directory, and the project's `zypulse.db` is byte-identical (or still absent)
  after the run.
- Result: **33/33 PASS**.

### 2. Photo access is documented as a prototype limitation, not as security
- `GET /api/photos/{key}` performs an **ownership check**, not authentication:
  `user_id` is an unverified string supplied by the caller; there is no login,
  session or token anywhere in ZyPulse.
- Wording corrected in `backend/routers/api.py`, `backend/services/photo_storage.py`
  and `README.md`. The README now states plainly that the build is **not suitable
  for storing real users' health photos** until real authentication,
  authorisation, transport security, encryption at rest and audit controls exist.
- No login system was added — out of scope for this pass.

### 3. Photo retention verified end to end
`test_photo_retention.py` now has **13 checks** (12 + medication), all executed:
PNG upload → nothing stored before confirm → confirm stores exactly one file →
History links to `/api/photos/<key>?user_id=` → wrong/absent owner gets 404/422 →
still readable after a full reload → glucose, medication and meal records each
carry their own photo → deleting the meal deletes its stored original → manual
logging, trends and the sample-photo simulation still work → no console errors.

### 4. Tests actually executed for this pass
| Suite | Result |
|---|---|
| `python3 test_backend.py` | **33/33 PASS** |
| `python3 test_photolog.py` | **15/15 PASS** |
| `python3 test_photo_retention.py` | **13/13 PASS** |
| `python3 tests/test_render_deploy.py` | **25/25 PASS** |
| `python3 tests/test_render_browser.py` | **14/14 PASS** |
| `cd frontend && pnpm run build` | **PASS** (47 modules) |
| Real Render deployment | **NOT TESTED** (no account/CLI access; GitHub/Render operations excluded) |
| Camera capture on a device | **NOT TESTED** (no device; uploads driven with a generated PNG) |
