"""Fixed-time Singapore reminder dispatcher.

Delivery is persisted in the in-app outbox; the web client polls that outbox and
may also display a browser notification while it is open.
"""

import json
from datetime import timedelta, timezone

from ..time_utils import now_sg

REMINDERS = {
    "medication": ("Medication reminder", "Time for your scheduled medication. (Reminder only - no dosing advice.)"),
    "meal_logging": ("Meal / logging reminder", "Don't forget to log today's meals and glucose readings."),
    "planned_activity": ("Planned activity reminder", "Time for your planned walk or activity. Stay hydrated!"),
}


def dispatch_due_reminders(db) -> int:
    """Create each due daily reminder once. Times are interpreted in Asia/Singapore."""
    now = now_sg()
    dispatched = 0
    for pref in db.get_all_reminder_preferences():
        try:
            settings = json.loads(pref["reminder_settings"])
        except (TypeError, json.JSONDecodeError):
            continue
        for key, cfg in settings.items():
            if key not in REMINDERS or not isinstance(cfg, dict) or not cfg.get("enabled"):
                continue
            try:
                hour, minute = map(int, str(cfg.get("time", "")).split(":"))
                due_local = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
            except (TypeError, ValueError):
                continue
            # Missed reminders are surfaced as overdue once, up to 24h late.
            if due_local > now or now - due_local > timedelta(days=1):
                continue
            title, body = REMINDERS[key]
            due_at = due_local.astimezone(timezone.utc).isoformat()
            status = "overdue" if now - due_local > timedelta(minutes=2) else "delivered"
            if db.create_notification(pref["user_id"], key, title, body, due_at, status):
                db.add_audit_event("reminder_dispatched", status, f"key={key}; due_at={due_at}", pref["user_id"])
                dispatched += 1
    return dispatched
