"""
Data Access Layer - the ONLY module that reads/writes to the database.

Enforces data-category separation: health records are never joined with
preferences or registration data unless explicitly required and consented.
"""

import sqlite3
import json
from datetime import datetime
from typing import Optional, List, Dict, Any

from .schema import get_connection
from ..time_utils import now_utc_iso
from ..services import photo_storage


class DataAccess:
    """Singleton-style data access. All DB operations go through here."""

    def __init__(self, db_path: str = None):
        self.db_path = db_path

    def _conn(self) -> sqlite3.Connection:
        return get_connection(self.db_path)

    # ================================================================
    # HEALTH RECORDS (Table 1 - SENSITIVE)
    # ================================================================

    def add_health_record(
        self,
        user_id: str,
        record_type: str,
        recorded_date: str,
        value_numeric: Optional[float] = None,
        value_text: Optional[str] = None,
        notes: Optional[str] = None,
        source: str = "user_entry",
        recorded_at: Optional[str] = None,
        include_in_visit_summary: bool = False,
        photo_ref: Optional[str] = None,
    ) -> int:
        """Insert a single health record."""
        if recorded_at is None:
            recorded_at = now_utc_iso()

        valid_types = [
            "glucose_fasting", "glucose_evening",
            "medication_morning", "medication_evening",
            "activity", "note", "meal",
        ]
        if record_type not in valid_types:
            raise ValueError(f"Invalid record_type: {record_type}. Must be one of {valid_types}")

        conn = self._conn()
        cursor = conn.execute(
            """
            INSERT INTO health_records
                (user_id, record_type, value_numeric, value_text,
                 recorded_date, recorded_at, notes, source, include_in_visit_summary, photo_ref)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (user_id, record_type, value_numeric, value_text,
             recorded_date, recorded_at, notes, source,
             1 if include_in_visit_summary else 0, photo_ref),
        )
        record_id = cursor.lastrowid
        conn.commit()
        conn.close()
        return record_id

    def get_health_records(
        self,
        user_id: str,
        record_type: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        """Retrieve health records with optional filters."""
        query = "SELECT * FROM health_records WHERE user_id = ?"
        params: list = [user_id]

        if record_type:
            query += " AND record_type = ?"
            params.append(record_type)
        if start_date:
            query += " AND recorded_date >= ?"
            params.append(start_date)
        if end_date:
            query += " AND recorded_date <= ?"
            params.append(end_date)

        query += " ORDER BY recorded_date DESC LIMIT ?"
        params.append(limit)

        conn = self._conn()
        rows = conn.execute(query, params).fetchall()
        conn.close()
        return [dict(row) for row in rows]

    def get_glucose_readings(
        self, user_id: str, period: str = "fasting", days: int = 7
    ) -> List[Dict[str, Any]]:
        """Get glucose readings for a specific period over N days."""
        record_type = f"glucose_{period}"
        conn = self._conn()
        rows = conn.execute(
            """
            SELECT * FROM health_records
            WHERE user_id = ? AND record_type = ? AND value_numeric IS NOT NULL
            ORDER BY recorded_date DESC
            LIMIT ?
            """,
            (user_id, record_type, days),
        ).fetchall()
        conn.close()
        return [dict(row) for row in rows]

    def get_medication_logs(
        self, user_id: str, days: int = 30
    ) -> List[Dict[str, Any]]:
        """Get medication logs for adherence calculation."""
        conn = self._conn()
        rows = conn.execute(
            """
            SELECT * FROM health_records
            WHERE user_id = ? AND record_type IN ('medication_morning', 'medication_evening')
            ORDER BY recorded_date DESC
            LIMIT ?
            """,
            (user_id, days * 2),
        ).fetchall()
        conn.close()
        return [dict(row) for row in rows]

    def get_activity_logs(
        self, user_id: str, days: int = 30
    ) -> List[Dict[str, Any]]:
        """Get activity logs for frequency calculation."""
        conn = self._conn()
        rows = conn.execute(
            """
            SELECT * FROM health_records
            WHERE user_id = ? AND record_type = 'activity' AND value_numeric IS NOT NULL
            ORDER BY recorded_date DESC
            LIMIT ?
            """,
            (user_id, days),
        ).fetchall()
        conn.close()
        return [dict(row) for row in rows]

    def get_unified_history(
        self,
        user_id: str,
        record_types: Optional[List[str]] = None,
        limit: int = 200,
    ) -> List[Dict[str, Any]]:
        """Get a unified chronological history across log categories.

        Does NOT duplicate data - reads directly from the existing health_records store.
        """
        query = "SELECT * FROM health_records WHERE user_id = ?"
        params: list = [user_id]
        if record_types:
            placeholders = ", ".join(["?"] * len(record_types))
            query += f" AND record_type IN ({placeholders})"
            params.extend(record_types)
        query += " ORDER BY recorded_date DESC, recorded_at DESC LIMIT ?"
        params.append(limit)

        conn = self._conn()
        rows = conn.execute(query, params).fetchall()
        conn.close()
        return [dict(row) for row in rows]

    def get_visit_notes(self, user_id: str) -> List[Dict[str, Any]]:
        """Get user notes flagged for inclusion in the doctor visit summary."""
        conn = self._conn()
        rows = conn.execute(
            """
            SELECT * FROM health_records
            WHERE user_id = ? AND record_type = 'note' AND include_in_visit_summary = 1
            ORDER BY recorded_date DESC, recorded_at DESC
            """,
            (user_id,),
        ).fetchall()
        conn.close()
        return [dict(row) for row in rows]

    def update_note_visit_flag(self, record_id: int, include: bool) -> bool:
        """Toggle the include_in_visit_summary flag on a note record."""
        conn = self._conn()
        conn.execute(
            "UPDATE health_records SET include_in_visit_summary = ? WHERE record_id = ? AND record_type = 'note'",
            (1 if include else 0, record_id),
        )
        conn.commit()
        conn.close()
        return True

    # ---- Meals (logged as a single 'meal' record; items stored as JSON in value_text) ----

    def get_meals(self, user_id: str, limit: int = 100) -> List[Dict[str, Any]]:
        """Get logged meals, newest first."""
        conn = self._conn()
        rows = conn.execute(
            """
            SELECT * FROM health_records
            WHERE user_id = ? AND record_type = 'meal'
            ORDER BY recorded_date DESC, recorded_at DESC LIMIT ?
            """,
            (user_id, limit),
        ).fetchall()
        conn.close()
        return [dict(row) for row in rows]

    def update_meal(
        self, record_id: int,
        meal_type: str, items: List[Dict[str, Any]],
        notes: Optional[str], include_in_visit: bool,
        photo_ref: Optional[str] = None,
    ) -> bool:
        """Update an existing meal record."""
        conn = self._conn()
        row = conn.execute(
            "SELECT record_id FROM health_records WHERE record_id = ? AND record_type = 'meal'",
            (record_id,),
        ).fetchone()
        if not row:
            conn.close()
            raise ValueError(f"Meal record {record_id} not found")
        total_carbs = round(sum(float(i.get("carbs") or 0) for i in items), 1)
        value_text = json.dumps({"meal_type": meal_type, "items": items}, ensure_ascii=False)
        set_clause = "value_text = ?, value_numeric = ?, notes = ?, include_in_visit_summary = ?, created_at = ?"
        params = [value_text, total_carbs, notes, 1 if include_in_visit else 0, now_utc_iso()]
        if photo_ref is not None:
            set_clause += ", photo_ref = ?"
            params.append(photo_ref)
        set_clause += " WHERE record_id = ?"
        params.append(record_id)
        conn.execute(f"UPDATE health_records SET {set_clause}", params)
        conn.commit()
        conn.close()
        return True

    def delete_meal(self, record_id: int) -> bool:
        """Delete a meal record.

        Follows the existing deletion behaviour (hard delete of the row) and
        applies it consistently to a photo the user uploaded for that meal:
        the stored original is removed together with the record.
        """
        conn = self._conn()
        row = conn.execute(
            "SELECT photo_ref FROM health_records WHERE record_id = ? AND record_type = 'meal'",
            (record_id,),
        ).fetchone()
        conn.execute(
            "DELETE FROM health_records WHERE record_id = ? AND record_type = 'meal'",
            (record_id,),
        )
        conn.commit()
        conn.close()
        if row:
            self.delete_photo_for_record(record_id, photo_ref=row["photo_ref"])
        return True

    # ---- Photo assets (private uploaded originals) ----

    def create_photo_asset(
        self, user_id: str, photo_key: str, content_type: str, byte_size: int,
        stored_path: str, checksum: Optional[str], original_name: Optional[str],
    ) -> None:
        conn = self._conn()
        conn.execute(
            """
            INSERT INTO photo_assets
                (photo_key, user_id, original_name, content_type, byte_size,
                 stored_path, checksum, status)
            VALUES (?, ?, ?, ?, ?, ?, ?, 'pending')
            """,
            (photo_key, user_id, original_name, content_type, byte_size,
             stored_path, checksum),
        )
        conn.commit()
        conn.close()

    def get_photo_asset(self, photo_key: str) -> Optional[Dict[str, Any]]:
        conn = self._conn()
        row = conn.execute(
            "SELECT * FROM photo_assets WHERE photo_key = ?", (photo_key,)
        ).fetchone()
        conn.close()
        return dict(row) if row else None

    def attach_photo_asset(self, photo_key: str, user_id: str, record_id: int) -> Dict[str, Any]:
        """Link an uploaded photo to the record it was confirmed into.

        Returns {'attached': bool, 'duplicate': bool, 'owned': bool}.
        A photo can only be attached to ONE record, so confirming the same
        upload twice cannot create a second log entry pointing at it.
        """
        conn = self._conn()
        row = conn.execute(
            "SELECT user_id, record_id, status FROM photo_assets WHERE photo_key = ?",
            (photo_key,),
        ).fetchone()
        if not row:
            conn.close()
            return {"attached": False, "duplicate": False, "owned": False}
        if row["user_id"] != user_id:
            conn.close()
            return {"attached": False, "duplicate": False, "owned": False}
        if row["record_id"] is not None:
            conn.close()
            return {
                "attached": False,
                "duplicate": True,
                "owned": True,
                "record_id": row["record_id"],
            }
        conn.execute(
            "UPDATE photo_assets SET record_id = ?, status = 'attached', attached_at = ? "
            "WHERE photo_key = ?",
            (record_id, now_utc_iso(), photo_key),
        )
        conn.commit()
        conn.close()
        return {"attached": True, "duplicate": False, "owned": True, "record_id": record_id}

    def delete_photo_asset(self, photo_key: str, user_id: str) -> Dict[str, Any]:
        """Delete a photo that is not attached to any record (cancel/rollback)."""
        conn = self._conn()
        row = conn.execute(
            "SELECT user_id, record_id, stored_path FROM photo_assets WHERE photo_key = ?",
            (photo_key,),
        ).fetchone()
        if not row or row["user_id"] != user_id or row["record_id"] is not None:
            conn.close()
            return {"deleted": False, "reason": "not found or already attached"}
        photo_storage.remove(row["stored_path"])
        conn.execute("DELETE FROM photo_assets WHERE photo_key = ?", (photo_key,))
        conn.commit()
        conn.close()
        return {"deleted": True}

    def delete_photo_for_record(self, record_id: int, photo_ref: Optional[str] = None) -> bool:
        """Remove the uploaded original attached to a record (used on delete)."""
        key = photo_storage.parse_photo_ref(photo_ref)
        if not key:
            return False
        conn = self._conn()
        row = conn.execute(
            "SELECT stored_path FROM photo_assets WHERE photo_key = ?", (key,)
        ).fetchone()
        if row:
            photo_storage.remove(row["stored_path"])
            conn.execute("DELETE FROM photo_assets WHERE photo_key = ?", (key,))
            conn.commit()
        conn.close()
        return bool(row)

    def purge_orphan_photos(self) -> Dict[str, int]:
        conn = self._conn()
        try:
            return photo_storage.purge_orphans(conn)
        finally:
            conn.close()

    def get_recent_foods(self, user_id: str, limit: int = 12) -> List[Dict[str, Any]]:
        """Derive recent/favourite food tags from previously logged meals.
        Does not duplicate data - reads existing meal records only."""
        conn = self._conn()
        rows = conn.execute(
            """
            SELECT value_text FROM health_records
            WHERE user_id = ? AND record_type = 'meal'
            ORDER BY recorded_at DESC LIMIT 100
            """,
            (user_id,),
        ).fetchall()
        conn.close()
        counts: Dict[str, Dict[str, Any]] = {}
        for r in rows:
            try:
                data = json.loads(r["value_text"] or "{}")
            except (json.JSONDecodeError, TypeError):
                continue
            for it in data.get("items", []):
                name = it.get("food_name")
                if not name:
                    continue
                key = name
                if key not in counts:
                    counts[key] = {
                        "food_name": name,
                        "food_id": it.get("food_id"),
                        "is_sugary_drink": bool(it.get("is_sugary_drink", False)),
                        "count": 0,
                    }
                counts[key]["count"] += 1
        ranked = sorted(counts.values(), key=lambda x: -x["count"])
        return ranked[:limit]

    # ================================================================
    # USER PREFERENCES (Table 2 - non-PHI)
    # ================================================================

    def upsert_preferences(self, user_id: str, **kwargs) -> bool:
        """Insert or update user preferences. JSON fields are serialized."""
        json_fields = ["activity_types", "availability", "goals", "barriers", "medications", "reminder_settings", "targets", "accessibility_json"]
        for field in json_fields:
            if field in kwargs and kwargs[field] is not None and not isinstance(kwargs[field], str):
                kwargs[field] = json.dumps(kwargs[field])

        conn = self._conn()
        existing = conn.execute(
            "SELECT user_id FROM user_preferences WHERE user_id = ?", (user_id,)
        ).fetchone()

        if existing:
            set_clauses = []
            params = []
            for key, val in kwargs.items():
                if val is not None:
                    set_clauses.append(f"{key} = ?")
                    params.append(val)
            if set_clauses:
                set_clauses.append("updated_at = ?")
                params.append(now_utc_iso())
                params.append(user_id)
                conn.execute(
                    f"UPDATE user_preferences SET {', '.join(set_clauses)} WHERE user_id = ?",
                    params,
                )
        else:
            columns = ["user_id"] + list(kwargs.keys())
            placeholders = ", ".join(["?"] * len(columns))
            values = [user_id] + list(kwargs.values())
            conn.execute(
                f"INSERT INTO user_preferences ({', '.join(columns)}) VALUES ({placeholders})",
                values,
            )
        conn.commit()
        conn.close()
        return True

    def get_preferences(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Get user preferences. JSON fields are deserialized."""
        conn = self._conn()
        row = conn.execute(
            "SELECT * FROM user_preferences WHERE user_id = ?", (user_id,)
        ).fetchone()
        conn.close()
        if not row:
            return None
        result = dict(row)
        json_fields = ["activity_types", "availability", "goals", "barriers", "medications", "reminder_settings", "targets", "accessibility_json"]
        for field in json_fields:
            if result.get(field) and isinstance(result[field], str):
                try:
                    result[field] = json.loads(result[field])
                except json.JSONDecodeError:
                    pass
        return result

    # ================================================================
    # AI MEMORY (Table 3)
    # ================================================================

    def add_conversation(
        self, user_id: str, role: str, content: str,
        conversation_id: Optional[str] = None,
        timestamp: Optional[str] = None,
        safety_flag: str = "none",
    ) -> int:
        if timestamp is None:
            timestamp = now_utc_iso()
        conn = self._conn()
        cursor = conn.execute(
            """
            INSERT INTO ai_memory (user_id, role, content, conversation_id, timestamp, safety_flag)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (user_id, role, content, conversation_id, timestamp, safety_flag),
        )
        memory_id = cursor.lastrowid
        conn.commit()
        conn.close()
        return memory_id

    def get_conversation_history(
        self, user_id: str, limit: int = 20
    ) -> List[Dict[str, Any]]:
        conn = self._conn()
        rows = conn.execute(
            """
            SELECT role, content, timestamp FROM ai_memory
            WHERE user_id = ? ORDER BY timestamp DESC LIMIT ?
            """,
            (user_id, limit),
        ).fetchall()
        conn.close()
        history = [dict(row) for row in reversed(rows)]
        return history

    # ================================================================
    # REGISTRATION INFO (Table 4)
    # ================================================================

    def create_registration(
        self, user_id: str, activity_id: str, activity_title: str,
        purpose: str, fields_shared: List[str],
        consent_given: int = 0, consent_steps_completed: Optional[List[str]] = None,
        confirmation_id: Optional[str] = None, registered_at: Optional[str] = None,
    ) -> int:
        conn = self._conn()
        cursor = conn.execute(
            """
            INSERT INTO registration_info
                (user_id, activity_id, activity_title, consent_given,
                 consent_steps_completed, fields_shared, purpose,
                 confirmation_id, registered_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (user_id, activity_id, activity_title, consent_given,
             json.dumps(consent_steps_completed or []),
             json.dumps(fields_shared),
             purpose, confirmation_id, registered_at),
        )
        reg_id = cursor.lastrowid
        conn.commit()
        conn.close()
        return reg_id

    def update_consent(
        self, reg_id: int, consent_given: int,
        consent_steps_completed: List[str], confirmation_id: Optional[str] = None,
    ) -> bool:
        conn = self._conn()
        conn.execute(
            """
            UPDATE registration_info
            SET consent_given = ?, consent_steps_completed = ?,
                confirmation_id = ?, registered_at = ?
            WHERE reg_id = ?
            """,
            (consent_given, json.dumps(consent_steps_completed), confirmation_id, now_utc_iso(), reg_id),
        )
        conn.commit()
        conn.close()
        return True

    # ================================================================
    # SHARING APPROVED (Table 5)
    # ================================================================

    def add_approved_share(
        self, user_id: str, field_name: str, field_value: str,
        field_category: str, reg_id: Optional[int] = None, approved: bool = False,
    ) -> int:
        conn = self._conn()
        cursor = conn.execute(
            """
            INSERT INTO sharing_approved
                (user_id, reg_id, field_name, field_value, field_category, approved, approved_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (user_id, reg_id, field_name, field_value, field_category,
             1 if approved else 0, now_utc_iso() if approved else None),
        )
        share_id = cursor.lastrowid
        conn.commit()
        conn.close()
        return share_id

    # ================================================================
    # AUDIT LOG (safety decisions)
    # ================================================================

    def add_audit_event(
        self, event_type: str, decision: str = "", detail: str = "",
        user_id: Optional[str] = None,
    ) -> int:
        conn = self._conn()
        cursor = conn.execute(
            """
            INSERT INTO audit_log (user_id, event_type, decision, detail, timestamp)
            VALUES (?, ?, ?, ?, ?)
            """,
            (user_id, event_type, decision, detail, now_utc_iso()),
        )
        audit_id = cursor.lastrowid
        conn.commit()
        conn.close()
        return audit_id

    # ================================================================
    # NOTIFICATIONS (in-app delivery outbox)
    # ================================================================

    def get_all_reminder_preferences(self) -> List[Dict[str, Any]]:
        conn = self._conn()
        rows = conn.execute(
            "SELECT user_id, reminder_settings FROM user_preferences WHERE reminder_settings IS NOT NULL"
        ).fetchall()
        conn.close()
        return [dict(row) for row in rows]

    def create_notification(self, user_id: str, reminder_key: str, title: str, body: str, due_at: str, status: str = "delivered") -> bool:
        conn = self._conn()
        cursor = conn.execute(
            """INSERT OR IGNORE INTO notifications
               (user_id, reminder_key, title, body, due_at, status, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (user_id, reminder_key, title, body, due_at, status, now_utc_iso()),
        )
        conn.commit()
        conn.close()
        return cursor.rowcount > 0

    def get_notifications(self, user_id: str, limit: int = 50) -> List[Dict[str, Any]]:
        conn = self._conn()
        rows = conn.execute(
            "SELECT * FROM notifications WHERE user_id = ? ORDER BY due_at DESC LIMIT ?", (user_id, limit)
        ).fetchall()
        conn.close()
        return [dict(row) for row in rows]

    def mark_notification_read(self, notification_id: int, user_id: str) -> bool:
        conn = self._conn()
        cursor = conn.execute(
            "UPDATE notifications SET status = 'read', read_at = ? WHERE notification_id = ? AND user_id = ?",
            (now_utc_iso(), notification_id, user_id),
        )
        conn.commit()
        conn.close()
        return cursor.rowcount > 0


# Module-level instance for convenience
_default_db: Optional[DataAccess] = None

def get_db(db_path: str = None) -> DataAccess:
    """Get the default DataAccess instance."""
    global _default_db
    if _default_db is None or db_path is not None:
        _default_db = DataAccess(db_path)
    return _default_db
