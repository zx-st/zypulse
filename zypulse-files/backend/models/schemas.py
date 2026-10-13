"""
Pydantic models for API request/response validation.
All inputs validated server-side; no untrusted data reaches the DB or LLM.
"""

from pydantic import BaseModel, Field, validator
from typing import Optional, List, Dict, Any
from datetime import date
from ..time_utils import today_sg_iso


# ============================================================
# HEALTH RECORDS
# ============================================================

class GlucoseLogRequest(BaseModel):
    user_id: str = Field(..., min_length=1, max_length=100)
    value: float = Field(..., ge=1.0, le=35.0, description="Glucose reading in mmol/L")
    period: str = Field("fasting", pattern="^(fasting|evening)$")
    recorded_date: str = Field(..., description="ISO date YYYY-MM-DD")
    notes: Optional[str] = Field(None, max_length=500)
    source: str = Field("user_entry", pattern="^(user_entry|DEMO/SYNTHETIC)$")
    photo_ref: Optional[str] = None
    # Opt-in only: the note is shown in the doctor visit summary when true.
    include_in_visit: bool = False

    @validator("recorded_date")
    def validate_date(cls, v):
        try:
            date.fromisoformat(v)
        except ValueError:
            raise ValueError("recorded_date must be YYYY-MM-DD format")
        return v


class MedicationLogRequest(BaseModel):
    user_id: str = Field(..., min_length=1, max_length=100)
    period: str = Field(..., pattern="^(morning|evening)$")
    status: str = Field(..., pattern="^(taken|missed|skipped)$")
    medication_name: str = Field("Metformin", max_length=100)
    dose: str = Field("500mg", max_length=50)
    recorded_date: str = Field(...)
    notes: Optional[str] = Field(None, max_length=500)
    photo_ref: Optional[str] = None
    # Optional free-text note for the doctor visit summary. Kept separate from
    # `notes`, which already carries the generated "name dose - status" summary.
    visit_note: Optional[str] = Field(None, max_length=500)
    include_in_visit: bool = False


class ActivityLogRequest(BaseModel):
    user_id: str = Field(..., min_length=1, max_length=100)
    activity_type: str = Field(..., max_length=50)
    duration_min: int = Field(..., ge=0, le=600)
    location: Optional[str] = Field(None, max_length=200)
    recorded_date: str = Field(...)
    notes: Optional[str] = Field(None, max_length=500)
    # Optional, user-entered only. ZyPulse never estimates a heart rate and
    # never infers intensity, fitness or clinical safety from it.
    avg_heart_rate: Optional[int] = Field(None, ge=20, le=250)
    # 'planned' -> stored as activity_planned and excluded from completed
    # activity trends; 'completed' -> existing behaviour.
    status: str = Field("completed", pattern="^(planned|completed)$")
    # Synthetic Healthy 365 demo event the entry was created from (dedupe key).
    source_event_id: Optional[str] = Field(None, max_length=60)
    # Optional free-text note for the doctor visit summary (stored in
    # visit_note; `notes` already holds the generated activity summary).
    visit_note: Optional[str] = Field(None, max_length=500)
    include_in_visit: bool = False


class ActivityUpdateRequest(BaseModel):
    activity_type: Optional[str] = Field(None, max_length=50)
    duration_min: Optional[int] = Field(None, ge=0, le=600)
    location: Optional[str] = Field(None, max_length=200)
    recorded_date: Optional[str] = Field(None, max_length=10)
    notes: Optional[str] = Field(None, max_length=500)
    avg_heart_rate: Optional[int] = Field(None, ge=20, le=250)
    # Set true to remove a previously stored average heart rate.
    clear_heart_rate: bool = False
    status: Optional[str] = Field(None, pattern="^(planned|completed)$")
    visit_note: Optional[str] = Field(None, max_length=500)
    include_in_visit: Optional[bool] = None


class VisitNoteUpdateRequest(BaseModel):
    """Edit the doctor-visit note and/or opt-in flag on any log record."""
    include_in_visit: Optional[bool] = None
    note: Optional[str] = Field(None, max_length=500)
    # Set true to clear the stored note text.
    clear_note: bool = False


# ============================================================
# MEAL LOG
# ============================================================

class MealItem(BaseModel):
    food_id: Optional[str] = None
    food_name: str = Field(..., min_length=1, max_length=120)
    portion_key: str = "1"  # 0.25, 0.5, 0.75, 1, 1.5, 2, custom
    portion_label: str = "1"
    carbs: float = Field(0.0, ge=0, le=1000)
    sugar: float = Field(0.0, ge=0, le=1000)
    is_sugary_drink: bool = False
    calories: Optional[float] = None  # nutrition estimate, may be None if unavailable
    protein: Optional[float] = None   # nutrition estimate, may be None if unavailable
    source: Optional[str] = None      # basis for the nutrition estimate


class MealLogRequest(BaseModel):
    user_id: str = Field(..., min_length=1, max_length=100)
    meal_type: str = Field(..., pattern="^(breakfast|lunch|dinner|snack)$")
    items: List[MealItem] = Field(..., min_length=1)
    notes: Optional[str] = Field(None, max_length=1000)
    include_in_visit: bool = False
    recorded_date: Optional[str] = None
    photo_ref: Optional[str] = None

    @validator("recorded_date", always=True)
    def default_date(cls, v):
        if v is None:
            return today_sg_iso()
        try:
            date.fromisoformat(v)
        except ValueError:
            raise ValueError("recorded_date must be YYYY-MM-DD format")
        return v

    @validator("items")
    def warn_estimate(cls, v):
        # Estimates are user/catalogue-derived, NOT clinically precise.
        return v


class MealUpdateRequest(BaseModel):
    meal_type: str = Field(..., pattern="^(breakfast|lunch|dinner|snack)$")
    items: List[MealItem] = Field(..., min_length=1)
    notes: Optional[str] = Field(None, max_length=1000)
    include_in_visit: bool = False


class FoodItemResponse(BaseModel):
    food_id: str
    name: str
    category: Optional[str] = None
    base_carbs: float
    base_sugar: float
    is_sugary_drink: bool = False
    portion_options: List[str] = ["0.25", "0.5", "0.75", "1", "1.5", "2", "custom"]
    tags: List[str] = []
    source: str = "DEMO/SYNTHETIC"


class PhotoAnalyzeRequest(BaseModel):
    user_id: str = Field(..., min_length=1, max_length=100)
    category: Optional[str] = Field(None, pattern="^(glucose|medication|meal)$")
    # Predefined demo sample id. When set, returns deterministic predefined extraction.
    sample_id: Optional[str] = None
    # Uploaded file name - NOT processed (no vision); used only to report unrecognised uploads.
    filename: Optional[str] = None


class PhotoAnalyzeResponse(BaseModel):
    recognized: bool = False
    simulated: bool = True
    category: Optional[str] = None
    sample_id: Optional[str] = None
    image: Optional[str] = None  # URL path to the bundled demo image (if recognised)
    extraction: Optional[Dict[str, Any]] = None  # structured category-specific result
    reason: Optional[str] = None  # set when not recognised (manual-entry fallback)
    disclaimer: str = (
        "SIMULATED recognition - no real vision model is connected. "
        "Review and confirm before saving."
    )


class PhotoUploadResponse(BaseModel):
    """Result of storing an uploaded original in private storage."""
    success: bool = True
    photo_key: str
    photo_ref: str            # value to store in health_records.photo_ref
    url: str                  # ownership-checked read endpoint (not a public asset URL)
    content_type: str
    byte_size: int
    original_name: Optional[str] = None
    status: str = "pending"   # becomes 'attached' once the confirmed log references it
    storage_notice: str = (
        "Stored in the application's private upload directory. It is not served "
        "as a public file and is removed if the linked record is deleted."
    )


class PhotoAttachResponse(BaseModel):
    success: bool = True
    photo_key: str
    record_id: Optional[int] = None
    attached: bool = False
    duplicate: bool = False
    message: Optional[str] = None


class Healthy365RegisterRequest(BaseModel):
    user_id: str = Field(..., min_length=1, max_length=100)
    event_id: str = Field(..., min_length=1, max_length=60)


class Healthy365RegisterResponse(BaseModel):
    success: bool = True
    simulated: bool = True
    duplicate: bool = False
    reg_id: Optional[int] = None
    confirmation_id: Optional[str] = None
    message: str
    event_id: str
    event_title: Optional[str] = None
    disclaimer: str = (
        "Demo simulation only. No real Healthy 365 registration or data transfer occurs."
    )


class HealthRecordResponse(BaseModel):
    record_id: int
    user_id: str
    record_type: str
    value_numeric: Optional[float]
    value_text: Optional[str]
    recorded_date: str
    recorded_at: str
    notes: Optional[str]
    source: str
    photo_ref: Optional[str] = None
    avg_heart_rate: Optional[int] = None
    visit_note: Optional[str] = None


# ============================================================
# CHAT
# ============================================================

class ChatRequest(BaseModel):
    user_id: str = Field(..., min_length=1, max_length=100)
    message: str = Field(..., min_length=1, max_length=1000, description="User message")
    language: str = Field("en", pattern="^(en|zh)$")


class ChatResponse(BaseModel):
    response: str
    language: str
    safety_status: str  # "allow", "blocked", "fallback"
    safety_detail: Optional[str] = None
    trends: Optional[Dict[str, Any]] = None
    audit_id: Optional[int] = None


class DailyBriefingRequest(BaseModel):
    user_id: str = Field(..., min_length=1, max_length=100)
    language: str = Field("en", pattern="^(en|zh)$")


class DailyBriefingResponse(BaseModel):
    analysis: str
    safety_status: str
    safety_detail: Optional[str] = None


# ============================================================
# PREFERENCES
# ============================================================

class PreferencesUpdate(BaseModel):
    language: Optional[str] = Field(None, pattern="^(en|zh)$")
    location_area: Optional[str] = None
    display_name: Optional[str] = Field(None, max_length=100)
    contact_email: Optional[str] = Field(None, max_length=200)
    contact_phone: Optional[str] = Field(None, max_length=50)
    accessibility_json: Optional[Dict[str, Any]] = None
    activity_types: Optional[List[str]] = None
    availability: Optional[List[str]] = None
    goals: Optional[List[str]] = None
    barriers: Optional[List[str]] = None
    reminder_settings: Optional[Dict[str, Any]] = None


class PreferencesResponse(BaseModel):
    user_id: str
    language: str
    location_area: Optional[str]
    display_name: Optional[str] = None
    contact_email: Optional[str] = None
    contact_phone: Optional[str] = None
    accessibility_json: Optional[Dict[str, Any]] = None
    activity_types: Optional[List[str]]
    availability: Optional[List[str]]
    goals: Optional[List[str]]
    barriers: Optional[List[str]]
    condition: Optional[str]
    reminder_settings: Optional[Dict[str, Any]] = None


# ============================================================
# NOTES FOR DOCTOR VISIT (user-created, deterministic storage)
# ============================================================

class NoteCreateRequest(BaseModel):
    user_id: str = Field(..., min_length=1, max_length=100)
    content: str = Field(..., min_length=1, max_length=1000)
    include_in_visit: bool = False
    recorded_date: Optional[str] = None


class NoteUpdateRequest(BaseModel):
    include_in_visit: bool


class NoteResponse(BaseModel):
    record_id: int
    user_id: str
    content: str
    include_in_visit: bool
    recorded_date: str
    recorded_at: str


# ============================================================
# TRENDS
# ============================================================

class TrendRequest(BaseModel):
    user_id: str
    metric: str = Field("glucose", pattern="^(glucose|medication|activity)$")
    period: str = Field("fasting", pattern="^(fasting|evening)$")
    days: int = Field(7, ge=1, le=90)


class TrendResponse(BaseModel):
    metric: str
    period: Optional[str]
    days_requested: int
    readings_count: int
    average: Optional[float]
    min_value: Optional[float]
    max_value: Optional[float]
    trend_direction: Optional[str]  # "increasing", "decreasing", "stable", "insufficient_data"
    trend_pct: Optional[float]
    source_records: List[Dict[str, Any]] = []
    insufficient_data: bool = False
    notes: Optional[str] = None
    # Medication-specific (returned by calculate_medication_adherence)
    adherence_rate: Optional[float] = None
    taken_doses: Optional[int] = None
    expected_doses: Optional[int] = None
    missed_doses: Optional[int] = None
    # Activity-specific (returned by calculate_activity_frequency)
    activity_days: Optional[int] = None
    total_duration_min: Optional[float] = None
    avg_duration_min: Optional[float] = None


# ============================================================
# ACTIVITIES
# ============================================================

class ActivitySearchRequest(BaseModel):
    user_id: str
    location_area: Optional[str] = None
    activity_type: Optional[str] = None
    intensity: Optional[str] = Field(None, pattern="^(low|moderate|sedentary)$")


class ActivityResponse(BaseModel):
    activity_id: str
    title: str
    organiser: str
    location: str
    datetime: str
    type: str
    intensity: str
    accessibility: str
    registration_status: str
    reward_status: str
    description: str
    source: str


# ============================================================
# CONSENT (5-step gate)
# ============================================================

class ConsentPreviewRequest(BaseModel):
    user_id: str
    activity_id: str


class ConsentPreviewResponse(BaseModel):
    activity_id: str
    activity_title: str
    fields_to_share: List[Dict[str, Any]]
    purpose: str
    can_edit: bool = True
    can_cancel: bool = True
    step: int = 1
    total_steps: int = 5
    warning: str = "SIMULATED - no information is sent to HPB or Healthy 365."


class ConsentConfirmRequest(BaseModel):
    user_id: str
    activity_id: str
    approved_fields: List[str]
    cancelled: bool = False


class ConsentConfirmResponse(BaseModel):
    success: bool
    confirmation_id: Optional[str]
    message: str
    simulated: bool = True


# ============================================================
# VISIT PREPARATION
# ============================================================

class VisitPrepRequest(BaseModel):
    user_id: str
    user_questions: List[str] = Field(default_factory=list)
    concerns: Optional[str] = None


class VisitPrepResponse(BaseModel):
    recorded_summary: str
    trend_summary: str
    user_questions: List[str]
    suggested_questions: List[str]
    editable: bool = True
    disclaimer: str = "This summary is for your own use and has not been shared with any healthcare professional."
