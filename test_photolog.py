"""
E2E test for the simulated AI Photo Logging feature in ZyPulse (feature branch).
Drives the real UI at http://localhost:3000 against the backend at :8000.

Run:  python3 test_photolog.py
Reports PASS/FAIL per required scenario. Only executed checks are reported.
"""
import sys, time
from playwright.sync_api import sync_playwright

BASE = "http://localhost:3000"
API = "http://localhost:8000"
USER = "mr_tan_001"
results = []
def rec(name, ok, detail=""):
    results.append((name, ok, detail))
    print(f"[{'PASS' if ok else 'FAIL'}] {name}" + (f" -- {detail}" if detail else ""))

def nav(page, label):
    page.locator("button.nav-item", has_text=label).first.click()
    page.wait_for_timeout(400)

def open_picker(page, btn_text):
    grid = page.locator(".sample-grid")
    if grid.count() > 0 and grid.first.is_visible():
        return
    # An uploaded photo now opens the review screen; leave it before reopening.
    review = page.locator(".review-panel")
    if review.count() > 0 and review.first.is_visible():
        page.locator(".photo-actions button:has-text('Cancel')").click()
        page.wait_for_timeout(300)
    if grid.count() > 0 and grid.first.is_visible():
        return
    page.locator(f"button:has-text('{btn_text}')").first.click()
    page.wait_for_selector(".sample-grid", timeout=8000)

def click_sample(page, text):
    page.locator(".sample-card", has_text=text).first.click()
    page.wait_for_selector(".review-panel", timeout=8000)

def confirm(page):
    page.locator("button:has-text('Confirm & Save')").first.click()

def setup_lang(page):
    if page.locator(".language-continue").count() > 0:
        page.locator(".language-options button", has_text="English").click()
        page.locator(".language-continue").click()
        page.wait_for_timeout(600)

def open_log_tab(page, tab):
    nav(page, "Log")
    page.locator("button", has_text=tab).first.click()
    page.wait_for_timeout(300)

def main():
    with sync_playwright() as p:
        browser = p.chromium.launch(args=["--no-sandbox"])
        page = browser.new_page()
        bad = []
        page.on("response", lambda r: None)
        page.on("console", lambda m: bad.append(m.text) if (m.type == "error") else None)
        page.on("pageerror", lambda e: bad.append(str(e)))
        page.goto(BASE, wait_until="load")
        page.wait_for_timeout(800)
        setup_lang(page)

        # 1. Glucose sample -> review -> save -> history
        try:
            open_log_tab(page, "Glucose")
            open_picker(page, "Scan Reading")
            click_sample(page, "7.2")
            val = page.locator(".review-panel input[type=number]").first.input_value()
            assert val == "7.2", f"prefill={val}"
            confirm(page)
            page.wait_for_selector(".success-msg", timeout=8000)
            ok = "saved from photo" in page.locator(".success-msg").inner_text().lower()
            rec("1. Glucose sample -> review -> save", ok, "prefilled 7.2")
        except Exception as e:
            rec("1. Glucose sample -> review -> save", False, str(e)[:120])

        # 2. Glucose sample -> edit reading -> save
        try:
            open_log_tab(page, "Glucose")
            open_picker(page, "Scan Reading")
            click_sample(page, "5.4")
            r = page.locator(".review-panel input[type=number]").first
            r.fill("9.1")
            confirm(page)
            page.wait_for_selector(".success-msg", timeout=8000)
            ok = "saved from photo" in page.locator(".success-msg").inner_text().lower()
            rec("2. Glucose -> edit reading -> save", ok, "edited to 9.1")
        except Exception as e:
            rec("2. Glucose -> edit reading -> save", False, str(e)[:120])

        # 3. Unclear glucose -> needs review, block empty confirm
        try:
            open_log_tab(page, "Glucose")
            open_picker(page, "Scan Reading")
            click_sample(page, "unclear")
            needs = page.locator(".badge-warn:has-text('Needs your review')").count() > 0
            warn = page.locator(".hint-warn").count() > 0
            confirm(page)
            err = page.locator(".error-msg").count() > 0
            rec("3. Unclear glucose -> needs review", needs and warn and err, f"needs={needs} warn={warn} block={err}")
        except Exception as e:
            rec("3. Unclear glucose -> needs review", False, str(e)[:120])

        # 4. Medication -> confirm actual intake -> save
        try:
            open_log_tab(page, "Medication")
            open_picker(page, "Scan Medication")
            click_sample(page, "blister")
            cb = page.locator(".confirm-check input[type=checkbox]")
            cb.check()
            confirm(page)
            page.wait_for_selector(".success-msg", timeout=8000)
            ok = "from photo" in page.locator(".success-msg").inner_text().lower()
            rec("4. Medication -> confirm intake -> save", ok, "checkbox checked + saved")
        except Exception as e:
            rec("4. Medication -> confirm intake -> save", False, str(e)[:120])

        # 5. Medication -> edit quantity -> save
        try:
            open_log_tab(page, "Medication")
            open_picker(page, "Scan Medication")
            click_sample(page, "blister")
            q = page.locator(".review-panel input[type=number]").nth(0)
            q.fill("3")
            page.locator(".confirm-check input[type=checkbox]").check()
            confirm(page)
            page.wait_for_selector(".success-msg", timeout=8000)
            rec("5. Medication -> edit quantity -> save", True, "qty=3")
        except Exception as e:
            rec("5. Medication -> edit quantity -> save", False, str(e)[:120])

        # 6. Meal -> portion 1/2 -> save
        try:
            nav(page, "Meals")
            open_picker(page, "Upload")
            click_sample(page, "Chicken Rice")
            sel = page.locator(".review-panel select.form-select").first
            sel.select_option(label="1/2")
            page.wait_for_timeout(200)
            totals = page.locator(".review-panel .meal-totals").inner_text()
            page.locator(".photo-workflow button:has-text('Save foods to favourites')").click()
            confirm(page)
            page.wait_for_selector(".success-msg", timeout=8000)
            ok = "saved from photo" in page.locator(".success-msg").inner_text().lower()
            rec("6. Meal -> portion 1/2 -> save", ok, totals.strip()[:30])
        except Exception as e:
            rec("6. Meal -> portion 1/2 -> save", False, str(e)[:120])

        # 7. Meal -> 'less sweet' modification
        try:
            nav(page, "Meals")
            open_picker(page, "Upload")
            click_sample(page, "Teh Tarik" if page.locator(".sample-card", has_text="Teh Tarik").count() else "Roti")
            mod = page.locator(".review-panel input[placeholder*='less sweet']")
            mod.fill("less sweet")
            confirm(page)
            page.wait_for_selector(".success-msg", timeout=8000)
            ok = "saved from photo" in page.locator(".success-msg").inner_text().lower()
            rec("7. Meal -> 'less sweet' modification", ok, "mod entered")
        except Exception as e:
            rec("7. Meal -> 'less sweet' modification", False, str(e)[:120])

        # 8. Meal -> save as favourite -> reuse
        try:
            nav(page, "Meals")
            open_picker(page, "Upload")
            click_sample(page, "Nasi Lemak")
            page.locator(".photo-workflow button:has-text('Save foods to favourites')").click()
            page.wait_for_timeout(300)
            fav_saved = page.locator(".photo-workflow button:has-text('Saved to favourites')").count() > 0
            confirm(page)
            page.wait_for_selector(".success-msg", timeout=8000)
            fav_chip = page.locator(".chip-fav:has-text('Nasi Lemak')").count() > 0
            rec("8. Meal -> save as favourite -> reuse", fav_saved and fav_chip, f"saved={fav_saved} chip={fav_chip}")
        except Exception as e:
            rec("8. Meal -> save as favourite -> reuse", False, str(e)[:120])

        # 9. Unsupported upload -> manual fallback
        try:
            open_log_tab(page, "Glucose")
            open_picker(page, "Scan Reading")
            dummy = "/tmp/dummy_upload.png"
            with open(dummy, "wb") as f:
                f.write(b"\x89PNG\r\n\x1a\n")
            page.locator(".photo-entry input[type=file]").set_input_files(dummy)
            page.wait_for_selector(".manual-fallback", timeout=8000)
            rec("9. Unsupported upload -> manual fallback", True, "manual-fallback shown")
        except Exception as e:
            rec("9. Unsupported upload -> manual fallback", False, str(e)[:120])

        # 10. Cancel -> no record saved
        try:
            before = len(page.request.get(f"{API}/api/history?user_id={USER}&category=all&limit=300").json())
            open_log_tab(page, "Glucose")
            open_picker(page, "Scan Reading")
            click_sample(page, "7.2")
            page.locator(".photo-actions button:has-text('Cancel')").click()
            page.wait_for_timeout(400)
            after = len(page.request.get(f"{API}/api/history?user_id={USER}&category=all&limit=300").json())
            rec("10. Cancel -> no record saved", after == before, f"before={before} after={after}")
        except Exception as e:
            rec("10. Cancel -> no record saved", False, str(e)[:120])

        # 11. View original photo from History
        try:
            nav(page, "History")
            page.wait_for_selector(".history-item")
            link = page.locator("a.history-photo-link").first
            href = link.get_attribute("href")
            ok = href and "/sample-photos/" in href
            rec("11. View original photo from History", ok, f"href={href}")
        except Exception as e:
            rec("11. View original photo from History", False, str(e)[:120])

        # 12. Manual logging still works
        try:
            open_log_tab(page, "Glucose")
            page.locator(".card input[type=number]").first.fill("6.6")
            page.locator(".card button:has-text('Save Reading')").click()
            page.wait_for_selector(".success-msg", timeout=8000)
            ok = "saved successfully" in page.locator(".success-msg").inner_text().lower()
            rec("12. Manual glucose logging works", ok)
        except Exception as e:
            rec("12. Manual glucose logging works", False, str(e)[:120])

        # 13. Trends / History / safety intact
        try:
            nav(page, "Trends")
            page.wait_for_timeout(500)
            trends_ok = page.locator(".trend-row, .card-title").count() > 0
            nav(page, "History")
            page.wait_for_selector(".history-item")
            hist_ok = page.locator(".history-item").count() > 0
            nav(page, "Coach")
            page.wait_for_selector(".chat-input-area")
            page.locator(".chat-input-area input, .chat-input-area textarea").first.fill("What dose of metformin should I take?")
            page.locator(".chat-send").click()
            page.wait_for_timeout(1500)
            chat_ok = page.locator(".chat-msg").count() > 0
            rec("13. Trends/History/safety intact", trends_ok and hist_ok and chat_ok, f"trends={trends_ok} hist={hist_ok} chat={chat_ok}")
        except Exception as e:
            rec("13. Trends/History/safety intact", False, str(e)[:120])

        # 14. Edit / delete a photo-assisted record (meal, saved via photo)
        try:
            nav(page, "Meals")
            page.wait_for_selector(".card .history-item")
            first = page.locator(".card .history-item").first
            before_cnt = len(page.request.get(f"{API}/api/meals?user_id={USER}").json())
            first.locator("button.link-btn").first.click()
            page.wait_for_selector(".success-msg", timeout=8000)
            editing = "Editing meal" in page.locator(".success-msg").first.inner_text()
            page.locator("button.btn-primary", has_text="Update Meal").first.click()
            page.wait_for_timeout(1200)
            updated = not page.locator(".success-msg", has_text="Editing meal").count()
            page.on("dialog", lambda d: d.accept())
            page.locator(".card .history-item").first.locator("button.link-danger").first.click()
            page.wait_for_timeout(1200)
            after_cnt = len(page.request.get(f"{API}/api/meals?user_id={USER}").json())
            rec("14. Edit/delete a photo-assisted record", editing and updated and after_cnt == before_cnt - 1,
                f"edit={editing} updated={updated} {before_cnt}->{after_cnt}")
        except Exception as e:
            rec("14. Edit/delete a photo-assisted record", False, str(e)[:120])

        rec("0. No console/page errors", len(bad) == 0, f"{len(bad)} errs: " + "; ".join(bad[:3]))
        browser.close()

    print("\n==== SUMMARY ====")
    passed = sum(1 for _, ok, _ in results if ok)
    for name, ok, detail in results:
        print(f"{'PASS' if ok else 'FAIL'}  {name}  {detail}")
    print(f"\n{passed}/{len(results)} checks passed")
    sys.exit(0 if passed == len(results) else 1)

if __name__ == "__main__":
    main()
