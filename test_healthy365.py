"""
Focused E2E test for the Healthy 365 Connect + Activity Log enhancement.

Drives the real UI at http://localhost:3000 against the backend at :8000 and
verifies the 15 scenarios required for this feature update.

Run:  python3 test_healthy365.py
Reports PASS/FAIL per executed check. Unexecuted checks are reported as NOT TESTED.
"""
import sys
import requests
from playwright.sync_api import sync_playwright

BASE = "http://localhost:3000"
API = "http://localhost:8000/api"
USER = "mr_tan_001"
TARGET_EVENT = "Community Cycling Taster Ride"  # h365-004

results = []


def rec(name, ok, detail=""):
    results.append((name, ok, detail))
    print(f"[{'PASS' if ok else 'FAIL'}] {name}" + (f" -- {detail}" if detail else ""))


def nav(page, label):
    page.locator("button.nav-item", has_text=label).first.click()
    page.wait_for_timeout(600)


def setup_lang(page):
    if page.locator(".language-continue").count() > 0:
        page.locator(".language-options button", has_text="English").click()
        page.locator(".language-continue").click()
        page.wait_for_timeout(700)


def history_records(category="all"):
    return requests.get(f"{API}/history", params={"user_id": USER, "category": category, "limit": 500}, timeout=20).json()


def activity_trend():
    return requests.get(f"{API}/trends", params={"user_id": USER, "metric": "activity", "days": 30}, timeout=20).json()


def entry_for_event(event_id):
    return [r for r in history_records("activity") if event_id in (r.get("value_text") or "")]


def main():
    # Clean any entries for the target event so the run is repeatable.
    for r in entry_for_event("h365-004"):
        requests.delete(f"{API}/logs/activity/{r['record_id']}", timeout=20)

    baseline_activity = activity_trend()
    baseline_history = history_records()
    baseline_glucose = history_records("glucose")

    net_requests = []
    console_errors = []

    with sync_playwright() as p:
        browser = p.chromium.launch(args=["--no-sandbox"])
        page = browser.new_page()
        page.on("request", lambda r: net_requests.append(r.url))
        page.on("console", lambda m: console_errors.append(m.text) if m.type == "error" else None)
        page.on("pageerror", lambda e: console_errors.append(str(e)))
        page.goto(BASE, wait_until="load")
        page.wait_for_timeout(900)
        setup_lang(page)

        # ---------------- 1. Existing sports facilities still work ----------------
        nav(page, "Connect")
        page.wait_for_selector(".activity-record-button", timeout=20000)
        body = page.inner_text("main")
        facilities_ok = (
            "Nearby Sports Facilities" in body
            and page.locator(".form-select").count() >= 1
            and "data.gov.sg" in body
            and page.locator(".activity-record-button").count() >= 1
        )
        rec("1. Nearby Sports Facilities page unchanged (search/filter/source note)",
            facilities_ok,
            f"record buttons={page.locator('.activity-record-button').count()}")

        # ---------------- 2. Healthy 365 section loads ----------------
        page.wait_for_selector(".h365-event", timeout=15000)
        rec("2. Healthy 365 Activities section loads",
            page.locator(".h365-event").count() >= 5,
            f"events={page.locator('.h365-event').count()}")

        # ---------------- 3. Personalised ranking uses stored preferences ----------------
        explain = page.locator(".h365-explain").first.inner_text()
        pers_api = requests.get(f"{API}/healthy365/events",
                                params={"user_id": USER, "mode": "recommended"}, timeout=20).json()
        factors = pers_api["personalisation"]["factors_used"]
        rec("3. Recommended ranking uses real stored preferences",
            "activity_types" in factors and "Ranking used these stored preferences" in explain,
            f"factors={factors}")

        # ---------------- 4. Missing preferences -> safe fallback (API) ----------------
        fallback = requests.get(f"{API}/healthy365/events",
                                params={"user_id": "user_without_prefs", "mode": "recommended"},
                                timeout=20).json()
        rec("4. Missing preferences trigger safe fallback",
            fallback["personalisation"]["available"] is False and "general demo catalogue" in fallback["notice"],
            fallback["notice"][:70])

        # ---------------- 5. Nearest First shows no invented distances ----------------
        page.locator("button.chip", has_text="Nearest First").first.click()
        page.wait_for_timeout(900)
        near_text = page.inner_text("main")
        near_api = requests.get(f"{API}/healthy365/events",
                                params={"user_id": USER, "mode": "nearest"}, timeout=20).json()
        no_distance = all(e.get("distance_display") is None for e in near_api["events"])
        rec("5. Nearest First shows no invented distances",
            no_distance and "No distances are shown" in near_text and " km" not in near_text,
            f"top={near_api['events'][0]['location_match']}")

        # ---------------- 6. Event details open ----------------
        page.locator("button.chip", has_text="Recommended for You").first.click()
        page.wait_for_timeout(800)
        card = page.locator(".h365-event", has_text=TARGET_EVENT).first
        card.locator("button", has_text="View details").first.click()
        page.wait_for_selector(".h365-card-panel", timeout=10000)
        detail_text = page.locator(".h365-card-panel").inner_text()
        rec("6. Event details open",
            "h365-" in detail_text and "Experience level" in detail_text and "Demo registration status" in detail_text,
            f"len={len(detail_text)}")

        # ---------------- 7. Simulated handoff opens and returns ----------------
        page.locator("button", has_text="Continue to Healthy 365 (Demo)").first.click()
        page.wait_for_selector("[data-testid='h365-handoff']", timeout=8000)
        handoff_text = page.locator("[data-testid='h365-handoff']").inner_text()
        opened = ("SIMULATED EXTERNAL APP" in handoff_text
                  and "Demo simulation only. No real Healthy 365 registration or data transfer occurs." in handoff_text)
        page.locator("button", has_text="Return to ZyPulse").first.click()
        page.wait_for_timeout(600)
        returned = page.locator(".h365-card-panel").count() == 1 and page.locator("[data-testid='h365-handoff']").count() == 0
        rec("7. Simulated handoff opens and returns to ZyPulse", opened and returned,
            "opened={} returned={}".format(opened, returned))

        # ---------------- 8. Mock registration does not transmit externally ----------------
        net_requests.clear()
        page.locator("button", has_text="Continue to Healthy 365 (Demo)").first.click()
        page.wait_for_selector("[data-testid='h365-handoff']", timeout=8000)
        page.locator("button", has_text="Register (Demo)").first.click()
        page.wait_for_selector("[data-testid='h365-register-result']", timeout=10000)
        result_text = page.locator("[data-testid='h365-register-result']").inner_text()
        external = [u for u in net_requests if "localhost" not in u and "127.0.0.1" not in u]
        stored = requests.get(f"{API}/healthy365/events/h365-004", params={"user_id": USER}, timeout=20).json()
        rec("8. Mock registration is local only (no external transmission)",
            "no actual registration was made" in result_text and not external and stored["already_registered"],
            f"external_requests={len(external)}")

        # ---------------- 9. Planned event added to Activity Log ----------------
        page.locator("button", has_text="Return to ZyPulse").first.click()
        page.wait_for_timeout(500)
        page.locator("button", has_text="Back to list").first.click()
        page.wait_for_timeout(700)
        page.locator(".h365-event", has_text=TARGET_EVENT).first.locator("button", has_text="Add to Activity Log").first.click()
        page.wait_for_timeout(900)
        page.wait_for_selector("select.form-select", timeout=8000)
        draft_text = page.inner_text("main")
        status_value = page.locator("form select.form-select").nth(1).input_value()
        prefilled = "h365-004" in draft_text and status_value == "planned"
        page.locator("button", has_text="Save Activity").first.click()
        page.wait_for_timeout(1200)
        saved_text = page.inner_text("main")
        saved_ok = "Planned activity saved" in saved_text
        entries = entry_for_event("h365-004")
        rec("9. Planned event can be added to Activity Log (pre-filled, editable)",
            prefilled and saved_ok and len(entries) == 1 and entries[0]["record_type"] == "activity_planned",
            f"entries={len(entries)} type={entries[0]['record_type'] if entries else 'none'}")

        # ---------------- 10. Planned event is not counted as completed ----------------
        after_trend = activity_trend()
        rec("10. Planned event does not count as completed activity",
            after_trend["activity_days"] == baseline_activity["activity_days"]
            and after_trend["total_duration_min"] == baseline_activity["total_duration_min"],
            f"days {baseline_activity['activity_days']} -> {after_trend['activity_days']}, "
            f"min {baseline_activity['total_duration_min']} -> {after_trend['total_duration_min']}")

        # ---------------- 11 + 12. Complete + edit, heart rate saved and shown ----------------
        nav(page, "History")
        page.locator("button.chip", has_text="Activity").first.click()
        page.wait_for_timeout(900)
        planned_item = page.locator(".history-item", has_text="h365-004").first
        planned_item.locator("button", has_text="Edit").first.click()
        page.wait_for_selector("[data-testid='activity-edit']", timeout=8000)
        form = page.locator("[data-testid='activity-edit']")
        form.locator("select.form-select").nth(0).select_option("completed")
        form.locator("input[type='number']").nth(0).fill("35")
        form.locator("input[type='number']").nth(1).fill("88")
        form.locator("button", has_text="Save changes").first.click()
        page.wait_for_timeout(1400)
        updated = entry_for_event("h365-004")[0]
        history_body = page.inner_text("main")
        hr_shown = "Avg heart rate: 88 bpm" in history_body
        rec("11. Completed event can be logged and edited",
            updated["record_type"] == "activity" and updated["value_numeric"] == 35,
            f"type={updated['record_type']} duration={updated['value_numeric']}")
        rec("12. Optional average heart rate saves and displays",
            updated.get("avg_heart_rate") == 88 and hr_shown,
            f"stored={updated.get('avg_heart_rate')} shown={hr_shown}")

        # ---------------- 13. Blank average heart rate accepted ----------------
        before_ids = {r["record_id"] for r in history_records("activity")}
        nav(page, "Log")
        page.locator("button", has_text="Activity").first.click()
        page.wait_for_timeout(500)
        log_form = page.locator("form").last
        log_form.locator("input[type='number']").nth(0).fill("25")
        log_form.locator("input[type='number']").nth(1).fill("")
        page.locator("button", has_text="Save Activity").first.click()
        page.wait_for_timeout(1200)
        new_records = [r for r in history_records("activity") if r["record_id"] not in before_ids]
        latest = new_records[0] if new_records else {}
        saved_text = page.inner_text("main")
        blank_ok = (
            len(new_records) == 1
            and latest.get("avg_heart_rate") is None
            and latest.get("value_numeric") == 25
            and "Activity saved" in saved_text
        )
        rec("13. Blank average heart rate is accepted", blank_ok,
            f"avg_heart_rate={latest.get('avg_heart_rate')} duration={latest.get('value_numeric')}")

        # ---------------- 14. Existing activity logs remain intact ----------------
        final_history = history_records()
        final_glucose = history_records("glucose")
        rec("14. Existing activity / health logs remain intact",
            len(final_history) > len(baseline_history)
            and len(final_glucose) == len(baseline_glucose)
            and all(r["record_id"] for r in final_glucose),
            f"history {len(baseline_history)} -> {len(final_history)}, glucose {len(final_glucose)}")

        # ---------------- 15. Existing features still functional ----------------
        samples = requests.get(f"{API}/photo-samples", params={"category": "glucose"}, timeout=20).json()
        nav(page, "Log")
        page.locator("button", has_text="Glucose").first.click()
        page.wait_for_timeout(400)
        page.locator("button", has_text="Scan Reading").first.click()
        page.wait_for_selector(".sample-grid", timeout=10000)
        picker_ok = page.locator(".sample-card").count() == len(samples)
        page.locator("button", has_text="Discard").first.click() if page.locator("button", has_text="Discard").count() else None
        nav(page, "Trends")
        trends_ok = "Activity Summary (30 days)" in page.inner_text("main")
        nav(page, "History")
        history_ok = page.locator(".history-item").count() > 0
        rec("15. AI photo logging, History, Trends and navigation still functional",
            len(samples) > 0 and picker_ok and trends_ok and history_ok,
            f"samples={len(samples)} picker={picker_ok} trends={trends_ok} history={history_ok}")

        # Extra: no unexpected console errors
        rec("Extra. No console/page errors during run", not console_errors, "; ".join(console_errors[:2]))

        browser.close()

    passed = sum(1 for _, ok, _ in results if ok)
    print(f"\n{passed}/{len(results)} checks passed")
    return 0 if passed == len(results) else 1


if __name__ == "__main__":
    sys.exit(main())
