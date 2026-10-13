"""
E2E test for ORIGINAL PHOTO RETENTION in ZyPulse.

Drives the real UI at http://localhost:3000 against the backend at :8000.
Every check below is executed; nothing is reported unless it ran.

Run:  python3 test_photo_retention.py
"""
import glob
import os
import sys

from PIL import Image, ImageDraw
from playwright.sync_api import sync_playwright

BASE = "http://localhost:3000"
API = "http://localhost:8000"
USER = "mr_tan_001"
UPLOAD_GLOB = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "zypulse-files", "backend", "var", "uploads", "**", "*",
)

results = []


def rec(name, ok, detail=""):
    results.append((name, bool(ok), detail))
    print(f"[{'PASS' if ok else 'FAIL'}] {name}" + (f" -- {detail}" if detail else ""))


def make_png(path, label):
    img = Image.new("RGB", (240, 140), (245, 248, 250))
    d = ImageDraw.Draw(img)
    d.rectangle([8, 8, 232, 132], outline=(37, 99, 235), width=3)
    d.text((24, 40), label, fill=(15, 23, 42))
    d.text((24, 70), "UPLOADED TEST IMAGE", fill=(100, 116, 139))
    img.save(path)
    return path


def stored_files():
    return sorted(p for p in glob.glob(UPLOAD_GLOB, recursive=True) if os.path.isfile(p))


def nav(page, label):
    page.locator("button.nav-item", has_text=label).first.click()
    page.wait_for_timeout(400)


def setup_lang(page):
    if page.locator(".language-continue").count() > 0:
        page.locator(".language-options button", has_text="English").click()
        page.locator(".language-continue").click()
        page.wait_for_timeout(600)


def open_picker(page, btn_text):
    if page.locator(".sample-grid").count() > 0 and page.locator(".sample-grid").first.is_visible():
        return
    page.locator(f"button:has-text('{btn_text}')").first.click()
    page.wait_for_selector(".sample-grid", timeout=8000)


def history(page, category="all"):
    return page.request.get(f"{API}/api/history?user_id={USER}&category={category}&limit=300").json()


def main():
    png = make_png("/tmp/zypulse_upload_test.png", "Glucose 6.4")
    gif = "/tmp/zypulse_upload_bad.gif"
    with open(gif, "wb") as fh:
        fh.write(b"GIF89a" + b"\x00" * 40)

    with sync_playwright() as p:
        browser = p.chromium.launch(args=["--no-sandbox"])
        page = browser.new_page()
        errors = []
        page.on("console", lambda m: errors.append(m.text) if m.type == "error" else None)
        page.on("pageerror", lambda e: errors.append(str(e)))
        page.goto(BASE, wait_until="load")
        page.wait_for_timeout(800)
        setup_lang(page)

        before_records = len(history(page))
        files_before = len(stored_files())

        # 1. Upload -> original shown, not recognised, manual entry required
        try:
            nav(page, "Log")
            page.locator("button", has_text="Glucose").first.click()
            open_picker(page, "Scan Reading")
            page.locator(".photo-entry input[type=file]").set_input_files(png)
            page.wait_for_selector(".review-panel", timeout=8000)
            img_src = page.locator(".review-panel .photo-preview img").first.get_attribute("src")
            fallback = page.locator(".review-panel .manual-fallback").count() > 0
            empty_value = page.locator(".review-panel input[type=number]").first.input_value() == ""
            rec("1. Upload shows original + 'not analysed' + empty manual fields",
                bool(img_src and img_src.startswith("blob:")) and fallback and empty_value,
                f"blob={str(img_src)[:12]} fallback={fallback} empty={empty_value}")
        except Exception as e:
            rec("1. Upload shows original + 'not analysed' + empty manual fields", False, str(e)[:140])

        # 2. Nothing is stored before confirm (cancel leaves no file)
        try:
            page.locator(".photo-actions button:has-text('Cancel')").click()
            page.wait_for_timeout(600)
            rec("2. Cancel after upload stores no file / no record",
                len(stored_files()) == files_before and len(history(page)) == before_records,
                f"files {files_before}->{len(stored_files())} records {before_records}->{len(history(page))}")
        except Exception as e:
            rec("2. Cancel after upload stores no file / no record", False, str(e)[:140])

        # 3. Unsupported type is rejected client-side
        try:
            nav(page, "Log")
            page.locator("button", has_text="Glucose").first.click()
            open_picker(page, "Scan Reading")
            page.locator(".photo-entry input[type=file]").set_input_files(gif)
            page.wait_for_selector(".manual-fallback", timeout=8000)
            msg = page.locator(".manual-fallback").first.inner_text()
            still_picker = page.locator(".sample-grid").count() > 0
            rec("3. Unsupported file type rejected before storage",
                "Unsupported file type" in msg and still_picker and len(stored_files()) == files_before,
                msg.strip()[:60])
        except Exception as e:
            rec("3. Unsupported file type rejected before storage", False, str(e)[:140])

        # 4. Upload + manual glucose value -> saved, file stored, owner can read it
        try:
            nav(page, "Log")
            page.locator("button", has_text="Glucose").first.click()
            open_picker(page, "Scan Reading")
            page.locator(".photo-entry input[type=file]").set_input_files(png)
            page.wait_for_selector(".review-panel", timeout=8000)
            page.locator(".review-panel input[type=number]").first.fill("6.4")
            page.locator(".photo-actions button:has-text('Confirm & Save')").click()
            page.wait_for_selector(".success-msg", timeout=10000)
            files_after = len(stored_files())
            rec("4. Confirm saves record and stores the original",
                files_after == files_before + 1 and len(history(page)) == before_records + 1,
                f"files {files_before}->{files_after} records +{len(history(page)) - before_records}")
        except Exception as e:
            rec("4. Confirm saves record and stores the original", False, str(e)[:140])

        # 5. History links to the ownership-checked endpoint (not a public asset)
        try:
            nav(page, "History")
            page.wait_for_selector(".history-item")
            href = page.locator("a.history-photo-link").first.get_attribute("href")
            rec("5. History 'View original photo' uses /api/photos/<key>?user_id=",
                bool(href) and "/api/photos/" in href and "user_id=" in href, f"href={href}")
        except Exception as e:
            rec("5. History 'View original photo' uses /api/photos/<key>?user_id=", False, str(e)[:140])

        # 6. Photo is NOT public: no user_id -> not readable
        try:
            key = href.split("/api/photos/")[1].split("?")[0]
            anon = page.request.get(f"{API}/api/photos/{key}")
            other = page.request.get(f"{API}/api/photos/{key}?user_id=someone_else")
            rec("6. Photo not readable without the owning user_id",
                anon.status in (404, 422) and other.status == 404,
                f"anon={anon.status} wrong_user={other.status}")
        except Exception as e:
            rec("6. Photo not readable without the owning user_id", False, str(e)[:140])

        # 7. Reload the app -> original still accessible (persisted, DB + disk)
        try:
            page.goto(BASE, wait_until="load")
            page.wait_for_timeout(800)
            setup_lang(page)
            nav(page, "History")
            page.wait_for_selector(".history-item")
            href2 = page.locator("a.history-photo-link").first.get_attribute("href")
            resp = page.request.get(href2 if href2.startswith("http") else f"{API}{href2}")
            rec("7. Original still accessible after a full page reload",
                resp.status == 200 and resp.headers.get("content-type", "").startswith("image/"),
                f"status={resp.status} type={resp.headers.get('content-type')} bytes={len(resp.body())}")
        except Exception as e:
            rec("7. Original still accessible after a full page reload", False, str(e)[:140])

        # 8. Uploaded meal -> manual name/values -> saved with photo
        try:
            nav(page, "Meals")
            open_picker(page, "Upload")
            page.locator(".photo-entry input[type=file]").set_input_files(png)
            page.wait_for_selector(".review-panel", timeout=8000)
            page.locator(".review-panel .food-row-head input").first.fill("Home cooked porridge")
            page.locator(".review-panel .food-row-controls input[type=number]").first.fill("35")
            n_before = len(page.request.get(f"{API}/api/meals?user_id={USER}").json())
            page.locator(".photo-actions button:has-text('Confirm & Save')").click()
            page.wait_for_selector(".success-msg", timeout=10000)
            n_after = len(page.request.get(f"{API}/api/meals?user_id={USER}").json())
            rec("8. Uploaded meal: manual entry saved with photo",
                n_after == n_before + 1, f"meals {n_before}->{n_after}")
        except Exception as e:
            rec("8. Uploaded meal: manual entry saved with photo", False, str(e)[:140])

        # 8b. Uploaded medication -> manual name/quantity -> saved and photo attached
        try:
            nav(page, "Log")
            page.locator("button", has_text="Medication").first.click()
            open_picker(page, "Scan Medication")
            page.locator(".photo-entry input[type=file]").set_input_files(png)
            page.wait_for_selector(".review-panel", timeout=8000)
            page.locator(".review-panel .form-group input.form-input").first.fill("Metformin")
            page.locator(".review-panel input[type=number]").first.fill("1")
            page.locator(".review-panel .confirm-check input[type=checkbox]").check()
            med_before = len(history(page, "medication"))
            page.locator(".photo-actions button:has-text('Confirm & Save')").click()
            page.wait_for_selector(".success-msg", timeout=10000)
            rows = history(page, "medication")
            ref = (rows[0].get("photo_ref") or "") if rows else ""
            status = 0
            if ref.startswith("photo:"):
                status = page.request.get(
                    f"{API}/api/photos/{ref.split('photo:', 1)[1]}?user_id={USER}").status
            rec("8b. Uploaded medication: saved with its own photo attached",
                len(rows) == med_before + 1 and ref.startswith("photo:") and status == 200,
                f"meds {med_before}->{len(rows)} ref={ref[:16]} photo={status}")
        except Exception as e:
            rec("8b. Uploaded medication: saved with its own photo attached", False, str(e)[:140])

        # 9. Deleting that meal removes its stored photo (no orphan)
        try:
            files_pre = len(stored_files())
            meal_id = page.request.get(f"{API}/api/meals?user_id={USER}").json()[0]["record_id"]
            page.request.delete(f"{API}/api/meals/{meal_id}")
            files_post = len(stored_files())
            rec("9. Deleting the meal deletes its stored original",
                files_post == files_pre - 1, f"files {files_pre}->{files_post}")
        except Exception as e:
            rec("9. Deleting the meal deletes its stored original", False, str(e)[:140])

        # 10. Existing records preserved (seeded data untouched)
        try:
            now = len(history(page))
            rec("10. Existing records preserved", now >= before_records,
                f"{before_records} -> {now} records")
        except Exception as e:
            rec("10. Existing records preserved", False, str(e)[:140])

        # 11. Manual logging + trends still work
        try:
            nav(page, "Log")
            page.locator("button", has_text="Glucose").first.click()
            page.locator(".card input[type=number]").first.fill("6.9")
            page.locator(".card button:has-text('Save Reading')").click()
            page.wait_for_selector(".success-msg", timeout=8000)
            nav(page, "Trends")
            page.wait_for_timeout(500)
            rec("11. Manual logging + Trends still work",
                page.locator(".trend-row, .card-title").count() > 0)
        except Exception as e:
            rec("11. Manual logging + Trends still work", False, str(e)[:140])

        rec("12. No console/page errors", len(errors) == 0, f"{len(errors)} errs: " + "; ".join(errors[:3]))
        browser.close()

    print("\n==== SUMMARY ====")
    for name, ok, detail in results:
        print(f"{'PASS' if ok else 'FAIL'}  {name}  {detail}")
    passed = sum(1 for _, ok, _ in results if ok)
    print(f"\n{passed}/{len(results)} checks passed")
    sys.exit(0 if passed == len(results) else 1)


if __name__ == "__main__":
    main()
