"""Healthy 365 Connect demo catalogue + deterministic ranking.

Scope notes (important for safety review):
- The catalogue is SYNTHETIC. Nothing here is a real Healthy 365 activity,
  a real registration, a real Healthpoints reward, or official HPB content.
- No external Healthy 365 / HPB / Singpass call is made. Ranking is plain
  deterministic Python over the stored user preferences, never an AI model.
- Distances are NEVER invented. The demo catalogue only carries general area
  labels, so "Nearest First" degrades to area-based ordering and says so.
"""

import json
import os
from datetime import date, timedelta
from typing import Any, Dict, List, Optional

CATALOGUE_PATH = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "data", "healthy365_catalogue.json")
)

DEMO_SOURCE_LABEL = "SYNTHETIC/DEMO - not a real Healthy 365 activity"
DEMO_DISCLAIMER = (
    "Demo simulation only. No real Healthy 365 registration or data transfer occurs."
)
REGISTRATION_MESSAGE = (
    "Demo registration recorded locally — no actual registration was made."
)

WEEKDAYS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]

# Deterministic weights. Same input -> same order, every time. No randomness.
WEIGHTS = {
    "interest": 3,
    "goal": 2,
    "availability": 2,
    "area": 1,
}


def _load_catalogue() -> Dict[str, Any]:
    with open(CATALOGUE_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def _slot(weekday: str, start_time: str) -> str:
    """Map a weekday/time pair onto the availability vocabulary used in preferences."""
    day_part = "weekend" if weekday in ("Sat", "Sun") else "weekday"
    try:
        hour = int((start_time or "00:00").split(":")[0])
    except (ValueError, IndexError):
        hour = 0
    if hour < 12:
        time_part = "mornings"
    elif hour < 18:
        time_part = "afternoons"
    else:
        time_part = "evenings"
    return f"{day_part} {time_part}"


def _next_occurrence(weekday: str, from_date: date) -> date:
    """Next calendar date for this weekday, including today. Deterministic."""
    target = WEEKDAYS.index(weekday)
    delta = (target - from_date.weekday()) % 7
    return from_date + timedelta(days=delta)


def _as_list(value: Any) -> List[str]:
    if not value:
        return []
    if isinstance(value, list):
        return [str(v) for v in value if v]
    return [str(value)]


def _norm(value: str) -> str:
    return (value or "").strip().casefold()


class Healthy365Service:
    """Synthetic Healthy 365-style catalogue with deterministic ranking."""

    def __init__(self, db) -> None:
        self.db = db

    # ------------------------------------------------------------------
    # Catalogue
    # ------------------------------------------------------------------

    def _events(self, today: Optional[date] = None) -> List[Dict[str, Any]]:
        catalogue = _load_catalogue()
        today = today or date.today()
        events: List[Dict[str, Any]] = []
        for raw in catalogue.get("events", []):
            event_date = _next_occurrence(raw["weekday"], today)
            events.append({
                "event_id": raw["event_id"],
                "title": raw["title"],
                "activity_type": raw["activity_type"],
                "tags": list(raw.get("tags", [])),
                "location_area": raw["location_area"],
                "region": raw.get("region"),
                "venue_hint": raw.get("venue_hint"),
                "date": event_date.isoformat(),
                "weekday": raw["weekday"],
                "start_time": raw["start_time"],
                "duration_min": raw.get("duration_min"),
                "experience_level": raw.get("experience_level"),
                "demo_registration_status": raw.get("demo_registration_status"),
                "description": raw.get("description", ""),
                "slot": _slot(raw["weekday"], raw["start_time"]),
                "demo": True,
                "source": DEMO_SOURCE_LABEL,
                "disclaimer": DEMO_DISCLAIMER,
            })
        return events

    def get_event(self, event_id: str) -> Optional[Dict[str, Any]]:
        for event in self._events():
            if event["event_id"] == event_id:
                return event
        return None

    def event_detail(self, user_id: str, event_id: str) -> Optional[Dict[str, Any]]:
        event = self.get_event(event_id)
        if not event:
            return None
        event = dict(event)
        event["already_registered"] = self.has_registration(user_id, event_id)
        event["activity_log_entries"] = self.db.find_activity_by_event(user_id, event_id)
        return event

    def has_registration(self, user_id: str, event_id: str) -> bool:
        return len(self.db.get_registrations(user_id, event_id)) > 0

    # ------------------------------------------------------------------
    # Ranking
    # ------------------------------------------------------------------

    def list_events(
        self, user_id: str, mode: str = "recommended", limit: int = 20
    ) -> Dict[str, Any]:
        """Return the demo catalogue ordered by the requested mode.

        mode=recommended -> personalised score over STORED preferences;
        when no usable preference exists it reports a fallback and returns the
        general catalogue order.
        mode=nearest      -> area-based ordering (no distances are computed).
        """
        mode = mode if mode in ("recommended", "nearest") else "recommended"
        events = self._events()
        preferences = self.db.get_preferences(user_id) or {}

        if mode == "nearest":
            return self._nearest_first(events, preferences, limit)

        ranked, personalisation = self._recommended(events, preferences)
        if not personalisation["available"]:
            fallback = self._nearest_first(events, preferences, limit)
            fallback["mode"] = "recommended"
            fallback["mode_label"] = "Recommended for You (fallback: general catalogue)"
            fallback["personalisation"] = personalisation
            fallback["notice"] = (
                "No usable stored preferences were found, so ZyPulse is showing the "
                "general demo catalogue ordered by area instead of personalised ranking."
            )
            return fallback

        ranked = ranked[: max(1, min(limit, 50))]
        return {
            "mode": "recommended",
            "mode_label": "Recommended for You",
            "catalogue_notice": _load_catalogue()["notice"],
            "personalisation": personalisation,
            "notice": (
                "Ranked deterministically from your stored preferences. "
                "ZyPulse does not assess health suitability."
            ),
            "events": ranked,
        }

    def _recommended(
        self, events: List[Dict[str, Any]], preferences: Dict[str, Any]
    ) -> tuple:
        activity_types = [_norm(v) for v in _as_list(preferences.get("activity_types"))]
        availability = [_norm(v) for v in _as_list(preferences.get("availability"))]
        goals = _as_list(preferences.get("goals"))
        location_area = preferences.get("location_area")
        region = (location_area or "").split("(")[0].strip()

        used: List[str] = []
        scored: List[Dict[str, Any]] = []
        for event in events:
            reasons: List[str] = []
            score = 0

            event_terms = [event["activity_type"]] + list(event["tags"])
            matched_interest = next(
                (term for term in event_terms if _norm(term) in activity_types), None
            )
            if matched_interest:
                score += WEIGHTS["interest"]
                reasons.append(f"Matches your activity interest: {matched_interest}")
                used.append("activity_types")

            matched_goal = next(
                (
                    goal for goal in goals
                    if any(_norm(term) and _norm(term) in goal.casefold() for term in event_terms)
                ),
                None,
            )
            if matched_goal:
                score += WEIGHTS["goal"]
                reasons.append(f"Matches your goal: \"{matched_goal}\"")
                used.append("goals")

            if event["slot"] and _norm(event["slot"]) in availability:
                score += WEIGHTS["availability"]
                reasons.append(f"Fits your availability: {event['slot']}")
                used.append("availability")

            area_match = None
            if location_area and _norm(event["location_area"]) == _norm(location_area):
                area_match = "Same area as your profile"
                score += WEIGHTS["area"] + 1
            elif region and _norm(event.get("region") or "") == _norm(region):
                area_match = f"Same region as your profile area ({event.get('region')})"
                score += WEIGHTS["area"]
            if area_match:
                reasons.append(area_match)
                used.append("location_area")

            item = dict(event)
            item["match_score"] = score
            item["match_reasons"] = reasons
            item["location_match"] = area_match
            scored.append(item)

        # Deterministic tie-break: score desc, then date/time asc, then event_id.
        scored.sort(key=lambda e: (-e["match_score"], e["date"], e["start_time"], e["event_id"]))

        personalisation = {
            "available": bool(used),
            "factors_used": sorted(set(used)),
            "missing": [
                field for field in ("activity_types", "goals", "availability", "location_area")
                if field not in used
            ],
            "explanation": (
                "Ranking used these stored preferences: " + ", ".join(sorted(set(used)))
                if used else
                "No stored preferences could be matched."
            ),
            "ai_used": False,
        }
        return scored, personalisation

    def _nearest_first(
        self, events: List[Dict[str, Any]], preferences: Dict[str, Any], limit: int
    ) -> Dict[str, Any]:
        location_area = preferences.get("location_area")
        region = (location_area or "").split("(")[0].strip()

        ordered: List[Dict[str, Any]] = []
        for event in events:
            item = dict(event)
            item["match_score"] = None
            if location_area and _norm(event["location_area"]) == _norm(location_area):
                item["location_match"] = f"Same area as your profile ({event['location_area']})"
                item["area_rank"] = 0
            elif region and _norm(event.get("region") or "") == _norm(region):
                item["location_match"] = f"Same region as your profile area ({event.get('region')})"
                item["area_rank"] = 1
            else:
                item["location_match"] = f"Different area ({event['location_area']})"
                item["area_rank"] = 2
            item["distance_display"] = None  # never fabricate a distance
            item["match_reasons"] = [item["location_match"]]
            ordered.append(item)

        ordered.sort(key=lambda e: (e["area_rank"], e["date"], e["start_time"], e["event_id"]))
        ordered = ordered[: max(1, min(limit, 50))]

        return {
            "mode": "nearest",
            "mode_label": "Nearest First (area-based)",
            "catalogue_notice": _load_catalogue()["notice"],
            "distance_policy": (
                "No distances are shown. The demo catalogue has no coordinate data, so "
                "ZyPulse orders by area match against your stored general location."
            ),
            "personalisation_available": bool(location_area),
            "notice": (
                f"Ordered by area match to your stored location ({location_area})."
                if location_area else
                "No general location is stored, so all demo areas are listed."
            ),
            "events": ordered,
        }

    # ------------------------------------------------------------------
    # Simulated handoff / registration (local only, never transmitted)
    # ------------------------------------------------------------------

    def register(self, user_id: str, event_id: str) -> Dict[str, Any]:
        """Record a LOCAL demo registration. Nothing leaves the app."""
        event = self.get_event(event_id)
        if not event:
            raise KeyError(event_id)

        existing = self.db.get_registrations(user_id, event_id)
        if existing:
            self.db.add_audit_event(
                "healthy365_demo_registration", "allow",
                f"duplicate ignored, event_id={event_id}", user_id,
            )
            return {
                "success": True,
                "simulated": True,
                "duplicate": True,
                "confirmation_id": existing[0].get("confirmation_id"),
                "message": "Already recorded locally as a demo registration.",
                "event_id": event_id,
                "event_title": event["title"],
                "disclaimer": DEMO_DISCLAIMER,
            }

        reg_id = self.db.create_registration(
            user_id=user_id,
            activity_id=event_id,
            activity_title=event["title"],
            purpose="Healthy 365 demo handoff (simulated)",
            fields_shared=[],  # nothing is shared externally
            consent_given=1,
            consent_steps_completed=["viewed_demo_handoff", "confirmed_demo_registration"],
            confirmation_id=None,
            registered_at=None,
            source="DEMO/SYNTHETIC_HEALTHY365",
        )
        confirmation_id = f"DEMO-H365-{reg_id:04d}"
        self.db.set_confirmation(reg_id, confirmation_id)
        self.db.add_audit_event(
            "healthy365_demo_registration", "allow",
            f"event_id={event_id}, reg_id={reg_id}", user_id,
        )
        return {
            "success": True,
            "simulated": True,
            "duplicate": False,
            "reg_id": reg_id,
            "confirmation_id": confirmation_id,
            "message": REGISTRATION_MESSAGE,
            "event_id": event_id,
            "event_title": event["title"],
            "disclaimer": DEMO_DISCLAIMER,
        }
