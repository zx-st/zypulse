"""Browser check of the single-service deployment (UI + API on one origin)."""
import os
import sys

from playwright.sync_api import sync_playwright

BASE = os.environ.get("BASE", "http://127.0.0.1:10000")
results = []


def rec(name, ok, note=""):
    results.append(ok)
    print(f"[{'PASS' if ok else 'FAIL'}] {name}" + (f" :: {note}" if note else ""))


with sync_playwright() as pw:
    browser = pw.chromium.launch(args=["--no-sandbox"])
    page = browser.new_page()
    errors = []
    page.on("console", lambda m: errors.append(m.text) if m.type == "error" else None)
    page.on("pageerror", lambda e: errors.append(str(e)))
    failed = []
    page.on("requestfailed", lambda r: failed.append(r.url))

    page.goto(BASE + "/", wait_until="networkidle")
    rec("SPA loads from FastAPI root", page.locator("#root").count() == 1)

    # Language gate
    if page.locator("text=English").count():
        page.locator("text=English").first.click()
    for sel in ("button:has-text('Continue')", "text=Continue"):
        if page.locator(sel).count():
            page.locator(sel).first.click()
            break
    page.wait_for_timeout(600)

    body = page.locator("body").inner_text()
    rec("App shell rendered (nav visible)", "Today" in body or "Log" in body, body[:60].replace("\n", " "))

    # Navigate by clicking the bottom nav - exercises same-origin API calls
    visited = []
    for label in ("Trends", "History", "Log", "Meals", "Today"):
        try:
            page.locator(f"button:has-text('{label}'), a:has-text('{label}')").first.click(timeout=4000)
            page.wait_for_timeout(1200)
            txt = page.locator("main").inner_text()
            ok = "Unable to load" not in txt and "request failed" not in txt
            visited.append((label, ok, txt[:50].replace("\n", " ")))
        except Exception as e:
            visited.append((label, False, f"click error {e}"))
    for label, ok, note in visited:
        rec(f"Page '{label}' loads via same-origin API", ok, note)

    # Photo logging (AI simulation) still works end to end on the single origin
    try:
        page.locator("nav button:has-text('Log')").first.click()
        page.wait_for_timeout(900)
        page.locator("main button:has-text('Scan Reading')").first.click()
        page.wait_for_timeout(600)
        rec("Glucose 'Scan Reading' opens photo workflow",
            page.locator("main button.sample-card").count() >= 3,
            f"sample cards={page.locator('main button.sample-card').count()}")

        rec("Sample library lists demo scenarios", page.locator("main button.sample-card").count() >= 3,
            f"cards={page.locator('main button.sample-card').count()}")

        page.locator("main button.sample-card").first.click()
        page.wait_for_timeout(900)
        review = page.locator("main").inner_text()
        rec("Simulated review step shown", "Simulated" in review and "Confirm & Save" in review)

        page.locator("main button:has-text('Confirm & Save')").first.click()
        page.wait_for_timeout(1600)
        rec("Photo log saved through same-origin API", "saved" in page.locator("main").inner_text().lower()
            or page.locator("main button.sample-card").count() == 0)
    except Exception as e:
        rec("Glucose photo workflow end-to-end", False, str(e)[:120])

    # History shows the linked photo
    try:
        page.locator("nav button:has-text('History')").first.click()
        page.wait_for_timeout(1500)
        hist = page.locator("main").inner_text()
        rec("History shows 'View original photo' link", "View original photo" in hist, hist[:80].replace("\n", " "))
    except Exception as e:
        rec("History photo link", False, str(e)[:120])

    bad = [e for e in errors if "favicon" not in e.lower()]
    rec("No console/page errors", len(bad) == 0, "; ".join(bad[:3]))
    rec("No failed network requests (same origin)", len(failed) == 0, "; ".join(failed[:3]))

    browser.close()

passed = sum(results)
print(f"\n==== {passed}/{len(results)} checks passed ====")
sys.exit(0 if passed == len(results) else 1)
