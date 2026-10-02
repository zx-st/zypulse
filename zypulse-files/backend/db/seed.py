"""
ZyPulse Database Seed Script

Loads synthetic Mr Tan 30-day data and activity catalogue into the database.
All data is clearly labelled with source = 'DEMO/SYNTHETIC'.
"""

import json
import os
from datetime import datetime

from .schema import init_db, DB_PATH
from .data_access import get_db

DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data")
DATA_DIR = os.path.abspath(DATA_DIR)


def load_json(filename: str) -> dict:
    filepath = os.path.join(DATA_DIR, filename)
    with open(filepath, "r", encoding="utf-8") as f:
        return json.load(f)


def seed_user_profile(db, profile: dict) -> None:
    """Seed user preferences from the profile data."""
    db.upsert_preferences(
        user_id=profile["user_id"],
        language=profile.get("language_preference", "en"),
        location_area=profile.get("location_general"),
        activity_types=profile.get("activity_preferences"),
        availability=profile.get("availability"),
        goals=profile.get("goals"),
        barriers=profile.get("barriers"),
        condition=profile.get("condition"),
        medications=profile.get("medications"),
        targets=profile.get("targets"),
        source="DEMO/SYNTHETIC",
    )


def seed_daily_records(db, user_id: str, daily_records: list) -> None:
    """Seed 30 days of health records from the daily_records array."""
    for day in daily_records:
        date = day["date"]

        # Fasting glucose
        if day.get("fasting_glucose") is not None:
            db.add_health_record(
                user_id=user_id,
                record_type="glucose_fasting",
                recorded_date=date,
                value_numeric=day["fasting_glucose"],
                value_text=f"{day['fasting_glucose']} mmol/L",
                source="DEMO/SYNTHETIC",
                recorded_at=f"{date}T07:00:00",
            )

        # Evening glucose
        if day.get("evening_glucose") is not None:
            db.add_health_record(
                user_id=user_id,
                record_type="glucose_evening",
                recorded_date=date,
                value_numeric=day["evening_glucose"],
                value_text=f"{day['evening_glucose']} mmol/L",
                source="DEMO/SYNTHETIC",
                recorded_at=f"{date}T20:00:00",
            )

        # Morning medication
        med_morning = day.get("medication_morning")
        if med_morning:
            db.add_health_record(
                user_id=user_id,
                record_type="medication_morning",
                recorded_date=date,
                value_text=med_morning,
                notes=f"Metformin 500mg - {med_morning}",
                source="DEMO/SYNTHETIC",
                recorded_at=f"{date}T07:30:00",
            )

        # Evening medication
        med_evening = day.get("medication_evening")
        if med_evening:
            db.add_health_record(
                user_id=user_id,
                record_type="medication_evening",
                recorded_date=date,
                value_text=med_evening,
                notes=f"Metformin 500mg - {med_evening}",
                source="DEMO/SYNTHETIC",
                recorded_at=f"{date}T19:30:00",
            )

        # Activity
        activity = day.get("activity")
        if activity:
            db.add_health_record(
                user_id=user_id,
                record_type="activity",
                recorded_date=date,
                value_numeric=activity.get("duration_min", 0),
                value_text=json.dumps(activity),
                notes=f"{activity['type']} - {activity.get('duration_min', 0)}min at {activity.get('location', 'unknown')}",
                source="DEMO/SYNTHETIC",
                recorded_at=f"{date}T18:00:00",
            )

        # Notes
        if day.get("notes"):
            db.add_health_record(
                user_id=user_id,
                record_type="note",
                recorded_date=date,
                value_text=day["notes"],
                source="DEMO/SYNTHETIC",
                recorded_at=f"{date}T21:00:00",
            )


def seed_conversation_history(db, user_id: str, history: list) -> None:
    """Seed initial conversation history."""
    for msg in history:
        db.add_conversation(
            user_id=user_id,
            role=msg["role"],
            content=msg["content"],
            timestamp=msg["timestamp"],
            safety_flag="none",
        )


def seed_all(db_path: str = None) -> dict:
    """Run the full seed process. Returns a summary."""
    if db_path is None:
        db_path = DB_PATH

    # Initialize schema
    init_db(db_path)

    db = get_db(db_path)

    # Load Mr Tan data
    mr_tan_data = load_json("mr_tan_30day.json")
    profile = mr_tan_data["user_profile"]
    user_id = profile["user_id"]

    seed_user_profile(db, profile)
    seed_daily_records(db, user_id, mr_tan_data["daily_records"])
    seed_conversation_history(db, user_id, mr_tan_data.get("conversation_history_seed", []))

    # Count records
    health_count = len(db.get_health_records(user_id, limit=10000))
    pref = db.get_preferences(user_id)
    conv_count = len(db.get_conversation_history(user_id, limit=1000))

    summary = {
        "user_id": user_id,
        "health_records_seeded": health_count,
        "preferences_seeded": pref is not None,
        "conversation_messages_seeded": conv_count,
        "source": "DEMO/SYNTHETIC",
        "status": "success",
    }

    print(f"Seed complete: {summary}")
    return summary


if __name__ == "__main__":
    seed_all()
