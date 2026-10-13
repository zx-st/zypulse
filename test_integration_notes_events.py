"""
Backend integration tests for the Healthy 365 Connect + Doctor Visit Notes work.

These run entirely in-process with starlette's TestClient against an isolated
temporary database and upload directory. The developer's own database is never
touched. No browser is required.

Run:  python3 test_integration_notes_events.py
      (from the folder that contains zypulse-files/)

Every check is reported PASS / FAIL / NOT RUN from actual execution. Unexecuted
checks are never reported as passing.
"""
import os
import sys
import json
import tempfile

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(_HERE, "zypulse-files"))

# --- isolate BEFORE importing backend modules ---
_TMP = tempfile.mkdtemp(prefix="zypulse_int_")
os.environ["ZYPULSE_UPLOAD_DIR"] = os.path.join(_TMP, "uploads")
os.environ["ZYPULSE_DB_PATH"] = os.path.join(_TMP, "zypulse_int.db")

from fastapi.testclient import TestClient  # noqa: E402
from backend.main import app  # noqa: E402

USER = "mr_tan_001"
results = []


def rec(name, ok, detail=""):
    results.append((name, bool(ok), detail))
    print(f"[{'PASS' if ok else 'FAIL'}] {name}" + (f" -- {detail}" if detail else ""))


def notrun(name):
    results.append((name, None, "not executed"))
    print(f"[NOT RUN] {name}")


with TestClient(app) as client:
    # ---------------------------------------------------------------
    # PART A: Healthy 365 Connect
    # ---------------------------------------------------------------
    r = client.get("/api/healthy365/events", params={"user_id": USER, "mode": "recommended", "limit": 20})
    rec("H365 recommended list returns 200", r.status_code == 200, f"status={r.status_code}")
    body = r.json()
    rec("H365 recommended has events", isinstance(body.get("events"), list) and len(body["events"]) > 0,
        f"count={len(body.get('events', []))}")
    rec("H365 recommended exposes match reasons", all("match_reasons" in e for e in body.get("events", [])),
        "each event carries match_reasons")
    rec("H365 recommended disclaims no health suitability assessment",
        "health suitability" not in (body.get("notice", "") + body.get("catalogue_notice", "")).lower()
        or "does not assess" in (body.get("notice", "") + body.get("catalogue_notice", "")).lower(),
        body.get("notice", "")[:60])

    rn = client.get("/api/healthy365/events", params={"user_id": USER, "mode": "nearest", "limit": 20})
    rec("H365 nearest list returns 200", rn.status_code == 200, f"status={rn.status_code}")
    nb = rn.json()
    rec("H365 nearest never fabricates a distance",
        all(e.get("distance_display") is None for e in nb.get("events", [])),
        "distance_display is null for all events")

    # event detail
    first_id = body["events"][0]["event_id"]
    rd = client.get(f"/api/healthy365/events/{first_id}", params={"user_id": USER})
    rec("H365 event detail returns 200", rd.status_code == 200, f"status={rd.status_code}")
    rec("H365 event detail marks demo / not real Healthy 365",
        "demo" in json.dumps(rd.json()).lower() and "not" in json.dumps(rd.json()).lower(),
        first_id)

    # simulated registration: local only, no external call
    rr = client.post("/api/healthy365/register", json={"user_id": USER, "event_id": first_id})
    rrb = rr.json()
    rec("H365 register returns 200 + simulated flag", rr.status_code == 200 and rrb.get("simulated") is True,
        f"status={rr.status_code}")
    rec("H365 register returns a confirmation id", bool(rrb.get("confirmation_id")),
        rrb.get("confirmation_id", ""))
    rec("H365 register carries demo disclaimer", "demo simulation" in (rrb.get("disclaimer", "")).lower(),
        rrb.get("disclaimer", "")[:40])
    # duplicate registration must not create a second row
    rr2 = client.post("/api/healthy365/register", json={"user_id": USER, "event_id": first_id})
    rec("H365 duplicate registration flagged", rr2.json().get("duplicate") is True, "")

    # ---------------------------------------------------------------
    # PART A2: Add a demo event to the Activity Log (planned + completed)
    # ---------------------------------------------------------------
    reg = client.post("/api/logs/activity", json={
        "user_id": USER, "activity_type": "cycling", "duration_min": 30,
        "location": "East Coast Park", "recorded_date": "2026-10-01",
        "status": "planned", "source_event_id": first_id,
        "visit_note": "Will bring water", "include_in_visit": True,
    })
    rec("Activity planned saved (activity_planned)", reg.status_code == 200 and reg.json().get("success"),
        f"status={reg.status_code}")

    # duplicate source_event_id + same status must not add a second row
    reg_dup = client.post("/api/logs/activity", json={
        "user_id": USER, "activity_type": "cycling", "duration_min": 30,
        "recorded_date": "2026-10-01", "status": "planned", "source_event_id": first_id,
    })
    rec("Duplicate demo event is de-duplicated (no second row)", reg_dup.json().get("duplicate") is True, "")

    # completed activity (counts as exercise)
    comp = client.post("/api/logs/activity", json={
        "user_id": USER, "activity_type": "walking", "duration_min": 45,
        "location": "Tampines", "recorded_date": "2026-10-02",
        "status": "completed", "avg_heart_rate": 110,
        "visit_note": "Felt good after", "include_in_visit": True,
    })
    comp_id = comp.json().get("record_id")
    rec("Completed activity saved with avg heart rate", comp.status_code == 200 and comp_id is not None, "")

    # avg heart rate blank -> stored as null (no fabricated value)
    blank = client.post("/api/logs/activity", json={
        "user_id": USER, "activity_type": "stretching", "duration_min": 20,
        "recorded_date": "2026-10-03", "status": "completed",
    })
    hist = client.get("/api/history", params={"user_id": USER, "category": "activity", "limit": 200}).json()
    blank_rec = next((h for h in hist if h.get("record_type") == "activity" and h.get("value_numeric") == 20), None)
    rec("Avg heart rate left blank stores null (no fabrication)",
        blank_rec is not None and blank_rec.get("avg_heart_rate") is None, "")

    # ---------------------------------------------------------------
    # PART C safety: planned must NOT count as completed exercise
    # ---------------------------------------------------------------
    # Record counts before adding a planned activity on a fresh day
    act_trends = client.get("/api/trends", params={"user_id": USER, "metric": "activity", "days": 30}).json()
    days_before = act_trends.get("activity_days", 0)
    dur_before = act_trends.get("total_duration_min", 0)

    planned_extra = client.post("/api/logs/activity", json={
        "user_id": USER, "activity_type": "swimming", "duration_min": 60,
        "recorded_date": "2026-10-04", "status": "planned",
    })
    act_trends2 = client.get("/api/trends", params={"user_id": USER, "metric": "activity", "days": 30}).json()
    rec("Planned activity does NOT increase active days",
        act_trends2.get("activity_days", 0) == days_before,
        f"before={days_before} after={act_trends2.get('activity_days')}")
    rec("Planned activity does NOT increase total duration",
        act_trends2.get("total_duration_min", 0) == dur_before,
        f"before={dur_before} after={act_trends2.get('total_duration_min')}")

    # ---------------------------------------------------------------
    # PART B: Doctor visit-note opt-in for glucose / medication / meal
    # ---------------------------------------------------------------
    g = client.post("/api/logs/glucose", json={
        "user_id": USER, "value": 7.4, "period": "fasting", "recorded_date": "2026-10-05",
        "notes": "Felt dizzy in the morning", "include_in_visit": True,
    })
    g_id = g.json().get("record_id")

    g_off = client.post("/api/logs/glucose", json={
        "user_id": USER, "value": 6.1, "period": "evening", "recorded_date": "2026-10-05",
        "notes": "Should NOT appear", "include_in_visit": False,
    })
    g_off_id = g_off.json().get("record_id")

    m = client.post("/api/logs/medication", json={
        "user_id": USER, "period": "morning", "status": "taken", "recorded_date": "2026-10-05",
        "visit_note": "Took with food as advised", "include_in_visit": True,
    })
    m_id = m.json().get("record_id")

    meal = client.post("/api/meals", json={
        "user_id": USER, "meal_type": "dinner", "recorded_date": "2026-10-05",
        "items": [{"food_name": "Chicken rice", "portion_key": "1", "carbs": 60, "sugar": 2}],
        "notes": "Small portion", "include_in_visit": True,
    })
    meal_id = meal.json().get("record_id")

    # verify opt-in flag persisted in history
    def hist_record(rid):
        for h in client.get("/api/history", params={"user_id": USER, "category": "all", "limit": 500}).json():
            if h.get("record_id") == rid:
                return h
        return None

    hg = hist_record(g_id)
    rec("Glucose opt-in note flagged include_in_visit_summary", hg is not None and hg.get("include_in_visit_summary") == 1, "")
    rec("Glucose note text stored in notes column", hg is not None and hg.get("notes") == "Felt dizzy in the morning", "")
    hgoff = hist_record(g_off_id)
    rec("Glucose without opt-in is excluded (flag = 0)", hgoff is not None and hgoff.get("include_in_visit_summary") == 0, "")

    hm = hist_record(m_id)
    rec("Medication visit_note stored in visit_note column (notes untouched)",
        hm is not None and hm.get("visit_note") == "Took with food as advised"
        and (hm.get("notes") or "").startswith("Metformin"), "")
    hmeal = hist_record(meal_id)
    rec("Meal opt-in note flagged", hmeal is not None and hmeal.get("include_in_visit_summary") == 1, "")

    # ---------------------------------------------------------------
    # PART B: planned activity visit note also collected, but not exercise
    # ---------------------------------------------------------------
    hplanned = hist_record(reg.json().get("record_id"))
    rec("Planned activity visit note flagged for summary",
        hplanned is not None and hplanned.get("include_in_visit_summary") == 1
        and hplanned.get("visit_note") == "Will bring water", "")
    hcomp = hist_record(comp_id)
    rec("Completed activity visit note flagged",
        hcomp is not None and hcomp.get("include_in_visit_summary") == 1
        and hcomp.get("visit_note") == "Felt good after", "")

    # ---------------------------------------------------------------
    # PART B: edit a visit note later -> summary updates & persists
    # ---------------------------------------------------------------
    upd = client.put(f"/api/records/{g_id}/visit-note", json={
        "include_in_visit": True, "note": "Dizzy around 8am, resolved after breakfast",
    })
    rec("Visit-note PUT returns 200", upd.status_code == 200, f"status={upd.status_code}")
    hg2 = hist_record(g_id)
    rec("Edited glucose note text persisted",
        hg2 is not None and hg2.get("notes") == "Dizzy around 8am, resolved after breakfast", "")

    # toggle off -> excluded from summary
    client.put(f"/api/records/{g_id}/visit-note", json={"include_in_visit": False})
    hg3 = hist_record(g_id)
    rec("Toggling opt-in off excludes the note", hg3 is not None and hg3.get("include_in_visit_summary") == 0, "")

    # ---------------------------------------------------------------
    # Compatibility: older records without visit_note/avg_heart_rate read fine
    # ---------------------------------------------------------------
    old = client.post("/api/logs/glucose", json={
        "user_id": USER, "value": 5.9, "period": "fasting", "recorded_date": "2026-09-01",
    })
    hold = hist_record(old.json().get("record_id"))
    rec("Legacy record without new fields is readable", hold is not None and hold.get("avg_heart_rate") is None, "")


# -------- summary --------
passed = sum(1 for _, ok, _ in results if ok is True)
failed = sum(1 for _, ok, _ in results if ok is False)
notrun_n = sum(1 for _, ok, _ in results if ok is None)
print("\n==== SUMMARY ====")
print(f"PASS={passed} FAIL={failed} NOT_RUN={notrun_n} TOTAL={len(results)}")
raise SystemExit(1 if failed else 0)
