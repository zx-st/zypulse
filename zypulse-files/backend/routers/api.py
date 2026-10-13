"""
ZyPulse API Router - Chat and Health Logging endpoints

Handles:
- POST /api/logs/glucose - Log a glucose reading
- POST /api/logs/medication - Log medication status
- POST /api/logs/activity - Log activity
- POST /api/chat - Chat with ZyPulse AI (the core MONITOR→COACH workflow)
- GET /api/trends - Get deterministic trend calculations
- GET /api/preferences - Get user preferences
- PUT /api/preferences - Update preferences
"""

import json
import os
from datetime import datetime
from fastapi import APIRouter, HTTPException, Request, UploadFile, File, Form
from fastapi.responses import FileResponse
from typing import Optional
import requests

from ..models.schemas import (
    GlucoseLogRequest, MedicationLogRequest, ActivityLogRequest,
    ChatRequest, ChatResponse, DailyBriefingRequest, DailyBriefingResponse,
    TrendRequest, TrendResponse,
    PreferencesUpdate, PreferencesResponse,
    NoteCreateRequest, NoteUpdateRequest, NoteResponse,
    MealLogRequest, MealUpdateRequest, MealItem,
    FoodItemResponse, PhotoAnalyzeRequest, PhotoAnalyzeResponse,
    PhotoUploadResponse, PhotoAttachResponse,
)
from ..db.data_access import get_db
from ..engine.calculations import CalculationEngine
from ..engine.safety import SafetyEngine
from ..engine.ai_orchestrator import AIOrchestrator
from ..services.sport_facilities import sport_facilities_provider
from ..services.reminders import dispatch_due_reminders
from ..services.ai_usage import ai_usage_guard
from ..services.photo_recognition import analyze as photo_analyze_svc, list_samples
from ..services import photo_storage
from ..time_utils import now_utc_iso, today_sg_iso

router = APIRouter(prefix="/api", tags=["zypulse"])

# Initialize engines (shared across requests)
safety_engine = SafetyEngine()
db = get_db()
calc_engine = CalculationEngine(db)
ai_orchestrator = AIOrchestrator(safety_engine)


def _with_user_context(summary: dict, user_id: str) -> dict:
    """Attach only user-saved preferences that can make AI language relevant."""
    preferences = db.get_preferences(user_id) or {}
    summary["user_context"] = {
        key: preferences.get(key)
        for key in ("display_name", "location_area", "goals", "barriers", "activity_types", "availability")
        if preferences.get(key)
    }
    return summary


def _client_id(request: Request, user_id: str) -> str:
    """Use the forwarded client address when Render's proxy provides it."""
    forwarded = request.headers.get("x-forwarded-for", "").split(",")[0].strip()
    address = forwarded or (request.client.host if request.client else "unknown")
    return f"{user_id}:{address}"


def _quota_message(language: str, reason: str, kind: str = "chat") -> str:
    if language == "zh":
        return "AI 助手使用过于频繁，请稍后再试。" if reason == "minute" else "今日 AI 助手使用次数已达上限，请明天再试。"
    return "AI assistant is being used too frequently. Please try again shortly." if reason == "minute" else "Today's AI assistant limit has been reached. Please try again tomorrow."


# ============================================================
# FOOD CATALOGUE (synthetic Singapore demo foods)
# ============================================================

_FOOD_CATALOGUE_PATH = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "data", "food_catalogue.json")
)


def _load_food_catalogue() -> dict:
    with open(_FOOD_CATALOGUE_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


# ============================================================
# HEALTH LOGGING (MONITOR phase)
# ============================================================

@router.post("/logs/glucose", response_model=dict)
async def log_glucose(req: GlucoseLogRequest):
    """Log a glucose reading. Deterministic storage, no AI."""
    record_type = f"glucose_{req.period}"
    record_id = db.add_health_record(
        user_id=req.user_id,
        record_type=record_type,
        recorded_date=req.recorded_date,
        value_numeric=req.value,
        value_text=f"{req.value} mmol/L",
        notes=req.notes,
        source=req.source,
        recorded_at=now_utc_iso(),
        photo_ref=req.photo_ref,
    )
    db.add_audit_event("glucose_logged", "allow", f"record_id={record_id}, value={req.value}", req.user_id)
    return {"success": True, "record_id": record_id, "message": "Glucose reading saved."}


@router.post("/logs/medication", response_model=dict)
async def log_medication(req: MedicationLogRequest):
    """Log medication status. Deterministic storage, no AI."""
    record_type = f"medication_{req.period}"
    record_id = db.add_health_record(
        user_id=req.user_id,
        record_type=record_type,
        recorded_date=req.recorded_date,
        value_text=req.status,
        notes=f"{req.medication_name} {req.dose} - {req.status}" + (f". {req.notes}" if req.notes else ""),
        source="user_entry",
        recorded_at=now_utc_iso(),
        photo_ref=req.photo_ref,
    )
    db.add_audit_event("medication_logged", "allow", f"record_id={record_id}, status={req.status}", req.user_id)
    return {"success": True, "record_id": record_id, "message": "Medication status saved."}


@router.post("/logs/activity", response_model=dict)
async def log_activity(req: ActivityLogRequest):
    """Log activity. Deterministic storage, no AI."""
    record_id = db.add_health_record(
        user_id=req.user_id,
        record_type="activity",
        recorded_date=req.recorded_date,
        value_numeric=req.duration_min,
        value_text=json.dumps({"type": req.activity_type, "location": req.location}),
        notes=f"{req.activity_type} - {req.duration_min}min" + (f" at {req.location}" if req.location else ""),
        source="user_entry",
        recorded_at=now_utc_iso(),
    )
    db.add_audit_event("activity_logged", "allow", f"record_id={record_id}, type={req.activity_type}", req.user_id)
    return {"success": True, "record_id": record_id, "message": "Activity saved."}


# ============================================================
# CHAT (COACH phase - the core AI workflow)
# ============================================================

@router.post("/chat", response_model=ChatResponse)
async def chat(req: ChatRequest, request: Request):
    """
    Core MONITOR→COACH workflow:
    user question → C3 calc → C4 input screen → C5 LLM → C4 output screen → response

    This is the single most important endpoint.
    """
    # STEP 1: C4 Safety Engine - input screening
    input_screen = safety_engine.screen_input(req.message)
    if not input_screen["allowed"]:
        # Input blocked - return redirect, do NOT call LLM
        db.add_audit_event(
            "safety_input_check", "block",
            f"category={input_screen['category']}, message={req.message[:100]}",
            req.user_id,
        )
        # Save the blocked message to AI memory with safety flag
        db.add_conversation(
            user_id=req.user_id, role="user", content=req.message,
            safety_flag=input_screen["category"],
        )
        db.add_conversation(
            user_id=req.user_id, role="assistant", content=input_screen["redirect"],
            safety_flag="blocked_input",
        )
        return ChatResponse(
            response=input_screen["redirect"],
            language=req.language,
            safety_status="blocked",
            safety_detail=input_screen["reason"],
            trends=None,
            audit_id=None,
        )

    allowed, reason = ai_usage_guard.consume("chat", _client_id(request, req.user_id))
    if not allowed:
        db.add_audit_event("ai_quota", "block", f"chat_{reason}_limit", req.user_id)
        return ChatResponse(
            response=_quota_message(req.language, reason), language=req.language,
            safety_status="rate_limited", safety_detail=f"chat {reason} quota reached",
            trends=None, audit_id=None,
        )

    # STEP 2: C3 Calculation Engine - compute deterministic trends
    context = _with_user_context(calc_engine.get_full_summary(req.user_id, days=7), req.user_id)

    # STEP 3: Get conversation history for continuity
    history = db.get_conversation_history(req.user_id, limit=6)

    # STEP 4: Save user message to AI memory
    db.add_conversation(
        user_id=req.user_id, role="user", content=req.message,
        safety_flag="none",
    )

    # STEP 5: C5 AI Orchestrator - generate response (with C4 output screening inside)
    result = ai_orchestrator.generate_response(
        user_message=req.message,
        context=context,
        language=req.language,
        conversation_history=history,
    )

    # STEP 6: Save AI response to memory
    db.add_conversation(
        user_id=req.user_id, role="assistant", content=result["response"],
        safety_flag=result["safety_status"],
    )

    # STEP 7: Log audit event
    audit_id = db.add_audit_event(
        "safety_output_check", result["safety_status"],
        f"detail={result['safety_detail']}",
        req.user_id,
    )

    return ChatResponse(
        response=result["response"],
        language=req.language,
        safety_status=result["safety_status"],
        safety_detail=result["safety_detail"],
        trends=context if result["safety_status"] != "blocked" else None,
        audit_id=audit_id,
    )


@router.post("/daily-briefing", response_model=DailyBriefingResponse)
async def daily_briefing(req: DailyBriefingRequest, request: Request):
    """Generate a safety-screened explanation of verified daily briefing data."""
    allowed, reason = ai_usage_guard.consume("briefing", _client_id(request, req.user_id))
    if not allowed:
        db.add_audit_event("ai_quota", "block", f"briefing_{reason}_limit", req.user_id)
        return DailyBriefingResponse(
            analysis=_quota_message(req.language, reason, "briefing"),
            safety_status="rate_limited", safety_detail=f"briefing {reason} quota reached",
        )
    context = _with_user_context(calc_engine.get_full_summary(req.user_id, days=7), req.user_id)
    result = ai_orchestrator.generate_briefing(context, req.language)
    db.add_audit_event(
        "daily_briefing_output_check", result["safety_status"], result["safety_detail"], req.user_id
    )
    return DailyBriefingResponse(
        analysis=result["response"],
        safety_status=result["safety_status"],
        safety_detail=result["safety_detail"],
    )


@router.get("/ai-usage", response_model=dict)
async def get_ai_usage(user_id: str, request: Request):
    """Return the public demo's remaining AI allowances for this visitor."""
    return ai_usage_guard.snapshot(_client_id(request, user_id))


# ============================================================
# TRENDS (deterministic, no AI)
# ============================================================

@router.get("/trends", response_model=TrendResponse)
async def get_trends(
    user_id: str,
    metric: str = "glucose",
    period: str = "fasting",
    days: int = 7,
):
    """Get deterministic trend calculations. No AI involved."""
    if metric == "glucose":
        result = calc_engine.calculate_glucose_trend(user_id, period, days)
    elif metric == "medication":
        result = calc_engine.calculate_medication_adherence(user_id, days)
    elif metric == "activity":
        result = calc_engine.calculate_activity_frequency(user_id, days)
    else:
        raise HTTPException(status_code=400, detail=f"Unknown metric: {metric}")

    return TrendResponse(
        metric=result["metric"],
        period=result.get("period"),
        days_requested=result["days_requested"],
        readings_count=result.get("readings_count", result.get("days_with_logs", 0)),
        average=result.get("average"),
        min_value=result.get("min_value"),
        max_value=result.get("max_value"),
        trend_direction=result.get("trend_direction"),
        trend_pct=result.get("trend_pct"),
        source_records=result.get("source_records", []),
        insufficient_data=result.get("insufficient_data", False),
        notes=result.get("notes"),
        # Pass through metric-specific fields (medication / activity)
        adherence_rate=result.get("adherence_rate"),
        taken_doses=result.get("taken_doses"),
        expected_doses=result.get("expected_doses"),
        missed_doses=result.get("missed_doses"),
        activity_days=result.get("activity_days"),
        total_duration_min=result.get("total_duration_min"),
        avg_duration_min=result.get("avg_duration_min"),
    )


# ============================================================
# PREFERENCES (UNDERSTAND phase)
# ============================================================

@router.get("/preferences", response_model=PreferencesResponse)
async def get_preferences(user_id: str):
    """Get user preferences."""
    prefs = db.get_preferences(user_id)
    if not prefs:
        raise HTTPException(status_code=404, detail="No preferences found for user")
    return PreferencesResponse(
        user_id=prefs["user_id"],
        language=prefs.get("language", "en"),
        location_area=prefs.get("location_area"),
        display_name=prefs.get("display_name"),
        contact_email=prefs.get("contact_email"),
        contact_phone=prefs.get("contact_phone"),
        accessibility_json=prefs.get("accessibility_json"),
        activity_types=prefs.get("activity_types"),
        availability=prefs.get("availability"),
        goals=prefs.get("goals"),
        barriers=prefs.get("barriers"),
        condition=prefs.get("condition"),
        reminder_settings=prefs.get("reminder_settings"),
    )


@router.put("/preferences", response_model=dict)
async def update_preferences(user_id: str, req: PreferencesUpdate):
    """Update user preferences."""
    update_data = {k: v for k, v in req.dict().items() if v is not None}
    db.upsert_preferences(user_id, **update_data)
    db.add_audit_event("preferences_updated", "allow", "preferences saved", user_id)
    return {"success": True, "message": "Preferences updated."}


@router.get("/notifications", response_model=list)
async def get_notifications(user_id: str, limit: int = 50):
    """Return persisted reminder deliveries; schedules are fixed to Asia/Singapore."""
    dispatch_due_reminders(db)
    return db.get_notifications(user_id, limit=min(limit, 100))


@router.put("/notifications/{notification_id}/read", response_model=dict)
async def read_notification(notification_id: int, user_id: str):
    if not db.mark_notification_read(notification_id, user_id):
        raise HTTPException(status_code=404, detail="Notification not found")
    db.add_audit_event("notification_read", "allow", f"notification_id={notification_id}", user_id)
    return {"success": True}


# ============================================================
# HISTORY (unified chronological view - reads existing log stores)
# ============================================================

_HISTORY_CATEGORY_MAP = {
    "all": None,
    "glucose": ["glucose_fasting", "glucose_evening"],
    "medication": ["medication_morning", "medication_evening"],
    "activity": ["activity"],
    "notes": ["note"],
    "meals": ["meal"],
}


@router.get("/history", response_model=list)
async def get_history(
    user_id: str,
    category: str = "all",
    limit: int = 200,
):
    """Get a unified chronological history across log categories.

    Reads directly from existing health_records store. No data duplication.
    """
    if category not in _HISTORY_CATEGORY_MAP:
        raise HTTPException(status_code=400, detail=f"Unknown category: {category}")
    record_types = _HISTORY_CATEGORY_MAP[category]
    records = db.get_unified_history(user_id, record_types=record_types, limit=limit)
    return records


# ============================================================
# NOTES FOR DOCTOR VISIT (user-created, deterministic storage)
# ============================================================

@router.post("/notes", response_model=NoteResponse)
async def create_note(req: NoteCreateRequest):
    """Create a user note. Stored deterministically; never sent to the LLM."""
    recorded_date = req.recorded_date or today_sg_iso()
    record_id = db.add_health_record(
        user_id=req.user_id,
        record_type="note",
        recorded_date=recorded_date,
        value_text=req.content,
        include_in_visit_summary=req.include_in_visit,
        source="user_entry",
        recorded_at=now_utc_iso(),
    )
    db.add_audit_event("note_created", "allow", f"record_id={record_id}", req.user_id)
    note = db.get_health_records(req.user_id, record_type="note", limit=1)
    note = note[0] if note else {}
    return NoteResponse(
        record_id=record_id,
        user_id=req.user_id,
        content=req.content,
        include_in_visit=bool(note.get("include_in_visit_summary", 0)),
        recorded_date=recorded_date,
        recorded_at=note.get("recorded_at", now_utc_iso()),
    )


@router.get("/notes/visit", response_model=list)
async def get_visit_notes(user_id: str):
    """Get notes flagged for inclusion in the doctor visit summary."""
    notes = db.get_visit_notes(user_id)
    return [
        NoteResponse(
            record_id=n["record_id"],
            user_id=n["user_id"],
            content=n.get("value_text", ""),
            include_in_visit=bool(n.get("include_in_visit_summary", 0)),
            recorded_date=n["recorded_date"],
            recorded_at=n.get("recorded_at", ""),
        )
        for n in notes
    ]


@router.put("/notes/{record_id}", response_model=dict)
async def update_note(record_id: int, req: NoteUpdateRequest):
    """Toggle the include_in_visit flag on a note."""
    db.update_note_visit_flag(record_id, req.include_in_visit)
    return {"success": True, "record_id": record_id, "include_in_visit": req.include_in_visit}


# ============================================================
# MEAL LOG (Quick Meal Log - Monitor phase)
# ============================================================

@router.get("/foods", response_model=list)
async def search_foods(q: Optional[str] = None, category: Optional[str] = None, limit: int = 30):
    """Search the synthetic Singapore food catalogue. All values are DEMO estimates."""
    catalogue = _load_food_catalogue()
    foods = catalogue.get("foods", [])
    if q:
        ql = q.lower()
        foods = [f for f in foods if ql in f["name"].lower() or any(ql in t.lower() for t in f.get("tags", []))]
    if category:
        foods = [f for f in foods if f.get("category") == category]
    for f in foods:
        f["source"] = "DEMO/SYNTHETIC - estimates not clinically precise"
    return [FoodItemResponse(**f) for f in foods[:limit]]


@router.get("/foods/recent", response_model=list)
async def recent_foods(user_id: str, limit: int = 12):
    """Return recent/favourite food tags derived from the user's logged meals."""
    return db.get_recent_foods(user_id, limit=limit)


@router.post("/meals", response_model=dict)
async def create_meal(req: MealLogRequest):
    """Log a meal (one or more foods/drinks). Deterministic storage, no AI."""
    items = [i.dict() for i in req.items]
    total_carbs = round(sum(float(i.get("carbs") or 0) for i in items), 1)
    total_sugar = round(sum(float(i.get("sugar") or 0) for i in items), 1)
    value_text = json.dumps({
        "meal_type": req.meal_type,
        "items": items,
        "totals": {"carbs": total_carbs, "sugar": total_sugar},
    }, ensure_ascii=False)
    record_id = db.add_health_record(
        user_id=req.user_id,
        record_type="meal",
        recorded_date=req.recorded_date,
        value_numeric=total_carbs,
        value_text=value_text,
        notes=req.notes,
        source="user_entry",
        recorded_at=now_utc_iso(),
        include_in_visit_summary=req.include_in_visit,
        photo_ref=req.photo_ref,
    )
    db.add_audit_event("meal_logged", "allow", f"record_id={record_id}, items={len(items)}, carbs={total_carbs}", req.user_id)
    return {"success": True, "record_id": record_id, "message": "Meal saved."}


@router.get("/meals", response_model=list)
async def list_meals(user_id: str, limit: int = 100):
    """List logged meals for editing/deleting."""
    return db.get_meals(user_id, limit=limit)


@router.put("/meals/{record_id}", response_model=dict)
async def update_meal_record(record_id: int, req: MealUpdateRequest):
    """Edit a previously logged meal."""
    items = [i.dict() for i in req.items]
    db.update_meal(record_id, req.meal_type, items, req.notes, req.include_in_visit)
    return {"success": True, "record_id": record_id, "message": "Meal updated."}


@router.delete("/meals/{record_id}", response_model=dict)
async def delete_meal_record(record_id: int):
    """Delete a logged meal."""
    db.delete_meal(record_id)
    return {"success": True, "record_id": record_id, "message": "Meal deleted."}


@router.get("/photo-samples", response_model=list)
async def photo_samples(category: Optional[str] = None):
    """List predefined demo photo samples for the picker UI."""
    return list_samples(category)


@router.post("/photo-analyze", response_model=PhotoAnalyzeResponse)
async def photo_analyze(req: PhotoAnalyzeRequest):
    """Simulated photo analysis (no real vision model).

    Recognises ONLY predefined demo samples via `sample_id`; the same sample id
    always returns the same deterministic extraction. Any other input (including
    arbitrary uploads) is reported as unrecognised so the UI can fall back to
    manual entry. This is the single replaceable seam for a future real Vision
    API: swap the body for a model call that returns the same `extraction` shape.
    """
    result = photo_analyze_svc(
        category=req.category,
        sample_id=req.sample_id,
        filename=req.filename,
    )
    return PhotoAnalyzeResponse(**result)


# ============================================================
# UPLOADED PHOTO ORIGINALS (private storage)
# ============================================================

@router.post("/photos/upload", response_model=PhotoUploadResponse)
async def upload_photo(
    file: UploadFile = File(...),
    user_id: str = Form(...),
):
    """Store an uploaded original in the app's private upload directory.

    The image is NOT analysed - recognition in this prototype is simulated and
    only knows the bundled demo samples. Uploading only reserves the file; it
    becomes `attached` when the user confirms the log entry that references it,
    and it is deleted automatically if that never happens.
    """
    if not user_id or len(user_id) > 100:
        raise HTTPException(status_code=400, detail="A valid user_id is required.")
    try:
        data = await file.read()
    except Exception as exc:  # pragma: no cover - client aborted
        raise HTTPException(status_code=400, detail="Upload could not be read.") from exc

    try:
        content_type = photo_storage.validate(file.content_type, data, file.filename)
    except ValueError as exc:
        raise HTTPException(status_code=415, detail=str(exc)) from exc

    meta = photo_storage.store(user_id, content_type, data, file.filename)
    try:
        db.create_photo_asset(
            user_id=user_id,
            photo_key=meta["photo_key"],
            content_type=meta["content_type"],
            byte_size=meta["byte_size"],
            stored_path=meta["stored_path"],
            checksum=meta["checksum"],
            original_name=meta["original_name"],
        )
    except Exception as exc:
        photo_storage.remove(meta["stored_path"])
        raise HTTPException(status_code=500, detail="Could not index the upload.") from exc

    db.add_audit_event(
        "photo_uploaded", "allow",
        f"photo_key={meta['photo_key']} bytes={meta['byte_size']} type={content_type}",
        user_id,
    )
    return PhotoUploadResponse(
        photo_key=meta["photo_key"],
        photo_ref=meta["photo_ref"],
        url=f"/api/photos/{meta['photo_key']}?user_id={user_id}",
        content_type=content_type,
        byte_size=meta["byte_size"],
        original_name=meta["original_name"] or file.filename,
    )


@router.get("/photos/{photo_key}")
async def get_photo(photo_key: str, user_id: str):
    """Serve an uploaded original only to the request that names its owner.

    PROTOTYPE LIMITATION - this is an OWNERSHIP CHECK, NOT AUTHENTICATION.
    The app has no login, session or token; `user_id` is a plain string supplied
    by the caller and cannot be verified. The check stops casual URL guessing
    (a key alone is not enough) but anyone who knows both the photo key and its
    user id can fetch the image. Do not use this to store real patients' photos.

    Bundled demo images are unaffected - they remain public static assets.
    """
    asset = db.get_photo_asset(photo_key)
    if not asset or asset["user_id"] != user_id:
        # Do not reveal whether the key exists.
        raise HTTPException(status_code=404, detail="Photo not found.")
    path = photo_storage.resolve(asset["stored_path"])
    if not path:
        raise HTTPException(status_code=404, detail="Photo not found.")
    return FileResponse(
        path,
        media_type=asset["content_type"],
        headers={
            "Cache-Control": "private, no-store",
            "Content-Disposition": f'inline; filename="{asset["photo_key"]}{photo_storage.ALLOWED_TYPES.get(asset["content_type"], ".img")}"',
            "X-ZyPulse-Photo-Owner": "checked",
        },
    )


@router.post("/photos/{photo_key}/attach", response_model=PhotoAttachResponse)
async def attach_photo(photo_key: str, user_id: str, record_id: int):
    """Link a stored upload to the confirmed log entry (once only)."""
    res = db.attach_photo_asset(photo_key, user_id, record_id)
    if not res.get("owned"):
        raise HTTPException(status_code=404, detail="Photo not found.")
    if res.get("duplicate"):
        return PhotoAttachResponse(
            photo_key=photo_key,
            record_id=res.get("record_id"),
            attached=False,
            duplicate=True,
            message="This photo is already attached to a log entry; nothing was duplicated.",
        )
    return PhotoAttachResponse(
        photo_key=photo_key, record_id=record_id, attached=True,
        message="Photo attached to the log entry.",
    )


@router.delete("/photos/{photo_key}", response_model=dict)
async def delete_photo(photo_key: str, user_id: str):
    """Discard an upload that was never confirmed (cancel / failed save)."""
    res = db.delete_photo_asset(photo_key, user_id)
    if not res.get("deleted"):
        raise HTTPException(
            status_code=409,
            detail="Photo not found, or it is already attached to a log entry.",
        )
    return {"success": True, "photo_key": photo_key, "message": "Upload discarded."}


# ============================================================
# ACTIVITIES (CONNECT phase)
# ============================================================

@router.get("/activities", response_model=list)
async def search_activities(
    user_id: str,
    location_area: Optional[str] = None,
    activity_type: Optional[str] = None,
    intensity: Optional[str] = None,
    limit: int = 100,
):
    """List real Singapore sports facilities and the facility types they offer.

    The public source contains venue data rather than class schedules, booking
    availability, or registrations. ``user_id`` is never sent to data.gov.sg.
    """
    try:
        facilities = sport_facilities_provider.list_facilities(activity_type=activity_type)
        # The public census has thousands of venues; cap results to keep the
        # mobile client responsive until a location-based search is added.
        return facilities[:max(1, min(limit, 200))]
    except requests.RequestException as exc:
        raise HTTPException(
            status_code=503,
            detail="Sports facility data is temporarily unavailable. Please try again later.",
        ) from exc
