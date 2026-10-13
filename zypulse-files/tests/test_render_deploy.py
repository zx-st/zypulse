"""Deployment smoke tests for the single-service ZyPulse build.

Starts nothing: expects uvicorn already listening on BASE (default 127.0.0.1:10000)
serving both the API and the compiled frontend.
"""
import json
import os
import sys
import urllib.error
import urllib.request

BASE = os.environ.get("BASE", "http://127.0.0.1:10000")
JS_NAME = os.environ.get("JS_NAME", "")

results = []


def rec(name, ok, note=""):
    results.append((ok, name, note))
    print(f"[{'PASS' if ok else 'FAIL'}] {name}" + (f" :: {note}" if note else ""))


def get(path):
    try:
        with urllib.request.urlopen(BASE + path, timeout=20) as r:
            return r.status, r.read(), r.headers.get("Content-Type", "")
    except urllib.error.HTTPError as e:
        return e.code, e.read(), e.headers.get("Content-Type", "")


def post(path, payload):
    data = json.dumps(payload).encode()
    req = urllib.request.Request(
        BASE + path, data=data, headers={"Content-Type": "application/json"}, method="POST"
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return r.status, r.read()
    except urllib.error.HTTPError as e:
        return e.code, e.read()


def j(body):
    try:
        return json.loads(body)
    except Exception:
        return None


# 1. Frontend shell
s, b, ct = get("/")
rec("GET / serves the React shell", s == 200 and b'id="root"' in b and "html" in ct, f"{s} {ct}")

# 2. Preserved routes
s, b, _ = get("/health")
rec("GET /health still returns JSON", s == 200 and (j(b) or {}).get("status") == "ok", str(s))
s, b, ct = get("/docs")
rec("GET /docs reachable", s == 200 and "html" in ct, str(s))
s, b, ct = get("/redoc")
rec("GET /redoc reachable", s == 200 and "html" in ct, str(s))
s, b, _ = get("/openapi.json")
rec("GET /openapi.json reachable", s == 200 and j(b) is not None, str(s))
s, b, _ = get("/api/info")
rec("GET /api/info returns service metadata", s == 200 and (j(b) or {}).get("name") == "ZyPulse API", str(s))

# 3. Static assets
_here = os.path.dirname(os.path.abspath(__file__))
assets_dir = ""
for _up in range(4):
    _cand = os.path.join(_here, *([".."] * _up), "frontend", "dist", "assets")
    if os.path.isdir(_cand):
        assets_dir = _cand
        break
js_files = sorted(f for f in os.listdir(assets_dir) if f.endswith(".js")) if assets_dir else []
if js_files:
    s, b, ct = get("/assets/" + js_files[0])
    rec("GET /assets/<bundle>.js served", s == 200 and "javascript" in ct, f"{s} {ct}")
else:
    rec("GET /assets/<bundle>.js served", False, "no bundle found in dist/assets")
s, b, ct = get("/sample-photos/glucose_1.png")
rec("GET /sample-photos/glucose_1.png served as image", s == 200 and "image/png" in ct, f"{s} {ct}")

# 4. SPA deep-link fallback
for deep in ("/history", "/log/glucose", "/trends/extra/segment"):
    s, b, _ = get(deep)
    rec(f"Deep link {deep} -> SPA shell", s == 200 and b'id="root"' in b, str(s))

# 5. API 404 is NOT swallowed by the SPA fallback
s, b, _ = get("/api/does-not-exist")
rec("Unknown /api path still 404", s == 404, str(s))

# 6. Core API still functional through the same origin
s, b = post("/api/logs/glucose", {"user_id": "mr_tan_001", "value": 6.9, "period": "fasting", "recorded_date": "2025-01-02"})
rec("POST /api/logs/glucose", s == 200 and (j(b) or {}).get("success") is True, f"{s}")
s, b = post("/api/photo-analyze", {"user_id": "mr_tan_001", "category": "glucose", "sample_id": "glucose_clear_1"})
d = j(b) or {}
rec("POST /api/photo-analyze (simulated) deterministic", s == 200 and d.get("recognized") and d.get("extraction", {}).get("reading") == 7.2, f"{s} reading={d.get('extraction', {}).get('reading')}")
s, b, _ = get("/api/photo-samples?category=meal")
rec("GET /api/photo-samples", s == 200 and len(j(b) or []) >= 5, f"{s} n={len(j(b) or [])}")
s, b, _ = get("/api/trends?user_id=mr_tan_001&days=30")
rec("GET /api/trends", s == 200 and j(b) is not None, str(s))
s, b, _ = get("/api/history?user_id=mr_tan_001&limit=5")
rec("GET /api/history", s == 200 and isinstance(j(b), list), str(s))
s, b, _ = get("/api/preferences?user_id=mr_tan_001")
rec("GET /api/preferences", s == 200 and j(b) is not None, str(s))

# 7. Simulated photo recognition (AI-simulation feature) intact + deterministic
for category in ("glucose", "medication", "meal"):
    s, b, _ = get(f"/api/photo-samples?category={category}")
    samples = j(b) or []
    rec(f"GET /api/photo-samples?category={category}", s == 200 and len(samples) >= 3, f"n={len(samples)}")
    all_ok = True
    for smp in samples:
        sid = smp.get("sample_id")
        s1, b1 = post("/api/photo-analyze", {"user_id": "mr_tan_001", "category": category, "sample_id": sid})
        s2, b2 = post("/api/photo-analyze", {"user_id": "mr_tan_001", "category": category, "sample_id": sid})
        d1, d2 = j(b1) or {}, j(b2) or {}
        if not (s1 == 200 and d1.get("recognized") and d1 == d2):
            all_ok = False
            rec(f"  sample {sid}", False, f"{s1} recognized={d1.get('recognized')} deterministic={d1 == d2}")
    rec(f"All '{category}' samples recognised deterministically", all_ok, f"{len(samples)} samples")

s, b = post("/api/photo-analyze", {"user_id": "mr_tan_001", "category": "glucose", "filename": "holiday.jpg"})
d = j(b) or {}
rec("Unrecognised upload -> manual-entry fallback", s == 200 and d.get("recognized") is False, str(d.get("reason"))[:60])

passed = sum(1 for ok, _, _ in results if ok)
print(f"\n==== {passed}/{len(results)} checks passed ====")
sys.exit(0 if passed == len(results) else 1)
