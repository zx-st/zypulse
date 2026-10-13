"""
Backend tests for ZyPulse (no browser required).

Runs the FastAPI app in-process with starlette's TestClient:
  * core logging / trends / preferences / notes / meals endpoints
  * the safety engine rules the README claims are enforced
  * simulated photo recognition (deterministic samples + unrecognised upload)
  * private upload storage (type/size validation, ownership check, cleanup)
  * test isolation: the developer's own database is never touched

Run:  python3 test_backend.py   (from the folder that contains zypulse-files/)

Isolation / startup
-------------------
Two things are set up BEFORE any backend module is imported:

  1. ZYPULSE_DB_PATH    -> a temporary database inside a temp directory
  2. ZYPULSE_UPLOAD_DIR -> a temporary upload directory

and the app is entered with `with TestClient(app) as client:`, which runs the
real FastAPI startup (lifespan) hook that creates and seeds the schema.
Creating the TestClient without that context manager skips startup, which is
exactly why the tables were missing ("no such table: health_records").
"""
import io
import os
import sys
import json
import shutil
import hashlib
import tempfile

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(_HERE, "zypulse-files"))

# --- isolate BEFORE importing backend modules (DB_PATH / UPLOAD_DIR are read at import) ---
_TMP = tempfile.mkdtemp(prefix="zypulse_test_")
os.environ["ZYPULSE_UPLOAD_DIR"] = os.path.join(_TMP, "uploads")
os.environ["ZYPULSE_DB_PATH"] = os.path.join(_TMP, "zypulse_test.db")

from backend.db.schema import DB_PATH  # noqa: E402
from backend.main import app  # noqa: E402
from backend.db.data_access import get_db  # noqa: E402
from backend.engine.safety import SafetyEngine  # noqa: E402
from backend.services.photo_recognition import analyze, list_samples  # noqa: E402
from backend.services import photo_storage  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

USER = "mr_tan_001"
results = []


def rec(name, ok, detail=""):
    results.append((name, bool(ok), detail))
    print(f"[{'PASS' if ok else 'FAIL'}] {name}" + (f" -- {detail}" if detail else ""))


def _fingerprint(path):
    """Stable hash of a database file, or None when it does not exist."""
    if not os.path.isfile(path):
        return None
    with open(path, "rb") as fh:
        return hashlib.sha256(fh.read()).hexdigest()


PNG = bytes.fromhex(
    "89504e470d0a1a0a0000000d49484452000000010000000108060000001f15c489"
    "0000000a49444154789c63000100000500010d0a2db40000000049454e44ae426082"
)

# The database the app would use without ZYPULSE_DB_PATH. It must be untouched.
DEFAULT_DB = os.path.abspath(
    os.path.join(_HERE, "zypulse-files", "backend", "zypulse.db")
)
DEFAULT_DB_BEFORE = _fingerprint(DEFAULT_DB)


def isolation_checks():
    rec("tests use a temporary database, not the project database",
        os.path.abspath(DB_PATH).startswith(os.path.abspath(_TMP)),
        f"db={os.path.basename(DB_PATH)}")
    rec("tests use a temporary upload directory",
        os.path.abspath(photo_storage.UPLOAD_DIR).startswith(os.path.abspath(_TMP)),
        f"uploads={os.path.basename(os.path.dirname(photo_storage.UPLOAD_DIR))}")


def main():
    with TestClient(app) as client:   # `with` triggers FastAPI startup (init_db + seed)
        isolation_checks()

        # ---- core endpoints ----
        rec("health", client.get("/health").status_code == 200)
        rec("api/info", client.get("/api/info").status_code == 200)

        TODAY = __import__("datetime").date.today().isoformat()
        r = client.post("/api/logs/glucose", json={"user_id": USER, "value": 7.1, "period": "fasting", "recorded_date": TODAY})
        rec("POST /api/logs/glucose", r.status_code == 200 and r.json().get("record_id"),
            f"status={r.status_code}")
        r = client.post("/api/logs/medication", json={
            "user_id": USER, "period": "morning", "status": "taken",
            "medication_name": "Metformin", "dose": "500mg", "recorded_date": TODAY})
        rec("POST /api/logs/medication", r.status_code == 200, f"status={r.status_code}")
        r = client.post("/api/logs/activity", json={
            "user_id": USER, "activity_type": "walking", "duration_min": 30, "recorded_date": TODAY})
        rec("POST /api/logs/activity", r.status_code == 200, f"status={r.status_code}")
        r = client.get("/api/trends", params={"user_id": USER, "metric": "glucose", "days": 30})
        rec("GET /api/trends", r.status_code == 200 and "average" in r.json(), f"status={r.status_code}")
        r = client.get("/api/preferences", params={"user_id": USER})
        rec("GET /api/preferences", r.status_code == 200, f"status={r.status_code}")
        r = client.get("/api/history", params={"user_id": USER, "category": "all", "limit": 50})
        rec("GET /api/history", r.status_code == 200 and len(r.json()) > 0, f"rows={len(r.json())}")
        r = client.post("/api/notes", json={"user_id": USER, "content": "Bring glucose log",
                                            "include_in_visit": True})
        rec("POST /api/notes", r.status_code == 200, f"status={r.status_code}")
        r = client.post("/api/chat", json={"user_id": USER, "message": "How are my glucose trends?"})
        rec("POST /api/chat (deterministic fallback)", r.status_code == 200, f"status={r.status_code}")

        # ---- safety engine rules claimed in the README ----
        se = SafetyEngine()
        cases = [
            ("Can I stop my metformin?", "stop_medication"),
            ("Should I increase my dose?", "dose_change"),
            ("Do I have diabetes?", "diagnosis_request"),
        ]
        for text, expected in cases:
            res = se.screen_input(text)
            ok = res.get("allowed") is False and res.get("category") == expected
            rec(f"safety blocks: '{text}'", ok, f"allowed={res.get('allowed')} category={res.get('category')}")
        allowed = se.screen_input("How can I walk more after dinner?")
        rec("safety allows ordinary self-care questions", allowed.get("allowed") is True,
            f"allowed={allowed.get('allowed')}")

        # ---- simulated photo recognition ----
        samples = list_samples()
        rec("photo-samples returns bundled samples", len(samples) >= 12, f"count={len(samples)}")
        r1 = analyze(category="glucose", sample_id="glucose_clear_1")
        r2 = analyze(category="glucose", sample_id="glucose_clear_1")
        rec("sample recognition is deterministic",
            r1 == r2 and r1["recognized"] and r1["extraction"]["reading"] == 7.2,
            f"reading={r1['extraction']['reading']}")
        bad = analyze(category="glucose", filename="my_own_photo.png")
        rec("arbitrary upload is NOT recognised", bad["recognized"] is False and bool(bad.get("reason")))

        # ---- private upload storage ----
        r = client.post("/api/photos/upload",
                        files={"file": ("a.png", io.BytesIO(PNG), "image/png")}, data={"user_id": USER})
        rec("POST /api/photos/upload (valid png)", r.status_code == 200, f"status={r.status_code}")
        up = r.json()
        key, ref = up["photo_key"], up["photo_ref"]

        rec("GET photo with wrong owner -> 404",
            client.get(f"/api/photos/{key}?user_id=intruder").status_code == 404)
        rec("GET photo without user_id -> 422 (query param required)",
            client.get(f"/api/photos/{key}").status_code == 422)
        ok = client.get(f"/api/photos/{key}?user_id={USER}")
        rec("GET photo as owner -> 200 image",
            ok.status_code == 200 and ok.headers["content-type"].startswith("image/")
            and ok.headers.get("cache-control") == "private, no-store")

        rec("reject non-image mime",
            client.post("/api/photos/upload",
                        files={"file": ("a.gif", io.BytesIO(b"GIF89a"), "image/gif")},
                        data={"user_id": USER}).status_code == 415)
        rec("reject non-image content",
            client.post("/api/photos/upload",
                        files={"file": ("a.png", io.BytesIO(b"definitely not png"), "image/png")},
                        data={"user_id": USER}).status_code == 415)
        rec("reject oversize",
            client.post("/api/photos/upload",
                        files={"file": ("big.png", io.BytesIO(b"\x89PNG\r\n\x1a\n" + b"0" * (9 * 1024 * 1024)), "image/png")},
                        data={"user_id": USER}).status_code == 415)

        meal = client.post("/api/meals", json={
            "user_id": USER, "meal_type": "lunch",
            "items": [{"food_name": "Test porridge", "carbs": 30, "sugar": 3}],
            "photo_ref": ref}).json()
        att = client.post(f"/api/photos/{key}/attach?user_id={USER}&record_id={meal['record_id']}").json()
        rec("attach photo to record", att.get("attached") is True)
        dup = client.post(f"/api/photos/{key}/attach?user_id={USER}&record_id={meal['record_id']}").json()
        rec("second attach is a no-op duplicate", dup.get("duplicate") is True)
        rec("attached photo cannot be discarded",
            client.delete(f"/api/photos/{key}?user_id={USER}").status_code == 409)

        upd = client.put(f"/api/meals/{meal['record_id']}", json={
            "meal_type": "lunch", "items": [{"food_name": "Test porridge v2", "carbs": 25, "sugar": 2}]}).json()
        after = client.get(f"/api/meals?user_id={USER}").json()[0]
        rec("editing a meal keeps the photo association",
            after["photo_ref"] == ref and "v2" in after["value_text"], f"ref={after['photo_ref']}")

        stored = get_db().get_photo_asset(key)
        existed = os.path.exists(stored["stored_path"]) if stored else False
        client.delete(f"/api/meals/{meal['record_id']}")
        rec("deleting the meal removes the stored original",
            existed and not os.path.exists(stored["stored_path"]))

        # pending (never confirmed) uploads can be discarded
        p = client.post("/api/photos/upload",
                        files={"file": ("p.png", io.BytesIO(PNG), "image/png")}, data={"user_id": USER}).json()
        path = get_db().get_photo_asset(p["photo_key"])["stored_path"]
        d = client.delete(f"/api/photos/{p['photo_key']}?user_id={USER}")
        rec("discarding an unconfirmed upload deletes the file",
            d.status_code == 200 and not os.path.exists(path))

    # ---- the developer's own database must be untouched ----
    rec("project database zypulse.db was not created or modified",
        _fingerprint(DEFAULT_DB) == DEFAULT_DB_BEFORE,
        f"path={DEFAULT_DB}")

    shutil.rmtree(_TMP, ignore_errors=True)

    print("\n==== SUMMARY ====")
    for name, ok, detail in results:
        print(f"{'PASS' if ok else 'FAIL'}  {name}  {detail}")
    passed = sum(1 for _, ok, _ in results if ok)
    print(f"\n{passed}/{len(results)} checks passed")
    sys.exit(0 if passed == len(results) else 1)


if __name__ == "__main__":
    main()
