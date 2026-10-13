"""
ZyPulse Database Schema - SQLite with 5 separated data stores.

Per architecture document C7:
1. health_records    - glucose readings, medication logs, activity logs, notes (sensitive)
2. user_preferences  - language, activity type, area, availability, goals, reminder settings
3. ai_memory         - conversation history, coaching context, identified barriers
4. registration_info - mock registration confirmations, consent audit events
5. sharing_approved  - specific fields approved for external sharing per registration event

All synthetic data is labelled with source = 'DEMO/SYNTHETIC'.
"""

import sqlite3
import os

# Default: backend/zypulse.db (a local prototype file, never committed).
# ZYPULSE_DB_PATH lets a test run point at an isolated temporary database so it
# can never read or overwrite the developer's own database.
DB_PATH = os.path.abspath(
    os.environ.get("ZYPULSE_DB_PATH")
    or os.path.join(os.path.dirname(__file__), "..", "zypulse.db")
)

SCHEMA_SQL = """
-- ============================================================
-- TABLE 1: health_records (SENSITIVE - PHI)
-- ============================================================
CREATE TABLE IF NOT EXISTS health_records (
    record_id      INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id        TEXT NOT NULL,
    record_type    TEXT NOT NULL,  -- validated in Python (DataAccess.add_health_record)
    value_numeric  REAL,
    value_text     TEXT,
    recorded_date  TEXT NOT NULL,      -- ISO date YYYY-MM-DD
    recorded_at    TEXT NOT NULL,      -- ISO datetime
    notes          TEXT,
    source         TEXT DEFAULT 'user_entry',  -- 'user_entry' or 'DEMO/SYNTHETIC'
    include_in_visit_summary INTEGER NOT NULL DEFAULT 0,  -- 1 if user flagged note for doctor visit summary
    created_at     TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now'))
);

CREATE INDEX IF NOT EXISTS idx_health_user_date ON health_records(user_id, recorded_date);
CREATE INDEX IF NOT EXISTS idx_health_type ON health_records(record_type);

-- ============================================================
-- TABLE 2: user_preferences (non-PHI)
-- ============================================================
CREATE TABLE IF NOT EXISTS user_preferences (
    pref_id         INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id         TEXT NOT NULL UNIQUE,
    language        TEXT DEFAULT 'en',   -- en, zh
    location_area   TEXT,
    display_name    TEXT,                -- fictional preferred/display name (no NRIC)
    contact_email   TEXT,                -- optional prototype contact field
    contact_phone   TEXT,                -- optional prototype contact field
    accessibility_json TEXT,            -- JSON object as string (settings)
    activity_types  TEXT,                -- JSON array as string
    availability    TEXT,                -- JSON array as string
    goals           TEXT,                -- JSON array as string
    barriers        TEXT,                -- JSON array as string
    reminder_settings TEXT,              -- JSON object as string
    condition       TEXT,
    medications     TEXT,                -- JSON array as string
    targets         TEXT,                -- JSON object as string
    source          TEXT DEFAULT 'user_entry',
    created_at      TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
    updated_at      TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now'))
);

-- ============================================================
-- TABLE 3: ai_memory (conversation + coaching context)
-- ============================================================
CREATE TABLE IF NOT EXISTS ai_memory (
    memory_id      INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id        TEXT NOT NULL,
    role           TEXT NOT NULL CHECK(role IN ('user', 'assistant', 'system')),
    content        TEXT NOT NULL,
    conversation_id TEXT,
    timestamp      TEXT NOT NULL,
    safety_flag    TEXT DEFAULT 'none',  -- none, blocked_input, blocked_output, warning
    source         TEXT DEFAULT 'ai_generated',
    created_at     TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now'))
);

CREATE INDEX IF NOT EXISTS idx_memory_user ON ai_memory(user_id);

-- ============================================================
-- TABLE 4: registration_info (mock registration + consent audit)
-- ============================================================
CREATE TABLE IF NOT EXISTS registration_info (
    reg_id          INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id         TEXT NOT NULL,
    activity_id     TEXT NOT NULL,
    activity_title  TEXT,
    consent_given   INTEGER NOT NULL DEFAULT 0,  -- 0=pending, 1=confirmed, -1=cancelled
    consent_steps_completed TEXT,                -- JSON array of completed steps
    fields_shared   TEXT,                        -- JSON array of field names shared
    purpose         TEXT,
    registered_at   TEXT,
    confirmation_id TEXT,                        -- mock confirmation ID
    source          TEXT DEFAULT 'DEMO/SYNTHETIC',
    created_at      TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now'))
);

CREATE INDEX IF NOT EXISTS idx_reg_user ON registration_info(user_id);

-- ============================================================
-- TABLE 5: sharing_approved (field-level external sharing log)
-- ============================================================
CREATE TABLE IF NOT EXISTS sharing_approved (
    share_id        INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id         TEXT NOT NULL,
    reg_id          INTEGER,
    field_name      TEXT NOT NULL,
    field_value     TEXT,
    field_category  TEXT NOT NULL CHECK(field_category IN ('preference', 'contact', 'activity', 'health_summary')),
    approved        INTEGER NOT NULL DEFAULT 0,
    approved_at     TEXT,
    source          TEXT DEFAULT 'DEMO/SYNTHETIC',
    created_at      TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now'))
);

CREATE INDEX IF NOT EXISTS idx_share_user ON sharing_approved(user_id);

-- ============================================================
-- AUDIT LOG (safety decisions - separate from AI memory)
-- ============================================================
CREATE TABLE IF NOT EXISTS audit_log (
    audit_id        INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id         TEXT,
    event_type      TEXT NOT NULL,   -- safety_input_check, safety_output_check, llm_call, consent_step, fallback_triggered
    decision        TEXT,            -- allow, block, flag
    detail          TEXT,
    timestamp       TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now'))
);

-- In-app notification outbox. Reminder times are always Asia/Singapore time.
CREATE TABLE IF NOT EXISTS notifications (
    notification_id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id         TEXT NOT NULL,
    reminder_key    TEXT NOT NULL,
    title           TEXT NOT NULL,
    body            TEXT NOT NULL,
    due_at          TEXT NOT NULL,
    status          TEXT NOT NULL DEFAULT 'delivered' CHECK(status IN ('delivered', 'read', 'overdue')),
    created_at      TEXT NOT NULL,
    read_at         TEXT,
    UNIQUE(user_id, reminder_key, due_at)
);
CREATE INDEX IF NOT EXISTS idx_notifications_user ON notifications(user_id, due_at DESC);

-- ============================================================
-- PHOTO ASSETS (user-uploaded originals attached to a log entry)
-- ------------------------------------------------------------
-- Uploaded health photos are stored OUTSIDE the web root (see
-- services/photo_storage.py) and are only readable through
-- GET /api/photos/{photo_key}?user_id=... , which checks ownership.
-- The row is the metadata index; the bytes live in the upload directory.
-- ============================================================
CREATE TABLE IF NOT EXISTS photo_assets (
    photo_key      TEXT PRIMARY KEY,        -- opaque random key used in photo_ref
    user_id        TEXT NOT NULL,           -- owner; enforced on every read
    original_name  TEXT,
    content_type   TEXT NOT NULL,
    byte_size      INTEGER NOT NULL,
    stored_path    TEXT NOT NULL,           -- absolute path outside the web root
    checksum       TEXT,                    -- sha256, used for dedupe reporting
    record_id      INTEGER,                 -- health_records.record_id once attached
    status         TEXT NOT NULL DEFAULT 'pending' CHECK(status IN ('pending', 'attached')),
    created_at     TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
    attached_at    TEXT
);

CREATE INDEX IF NOT EXISTS idx_photo_user ON photo_assets(user_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_photo_record ON photo_assets(record_id);
"""


def init_db(db_path: str = None) -> sqlite3.Connection:
    """Initialize the database with the full schema. Safe to call multiple times."""
    if db_path is None:
        db_path = DB_PATH
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.executescript(SCHEMA_SQL)
    conn.commit()
    # Additive migrations for existing databases (never drop data)
    _run_additive_migrations(conn)
    return conn


def _run_additive_migrations(conn: sqlite3.Connection) -> None:
    """Add columns introduced after the initial schema without losing data."""
    health_cols = {row[1] for row in conn.execute("PRAGMA table_info(health_records)")}
    if "include_in_visit_summary" not in health_cols:
        conn.execute(
            "ALTER TABLE health_records ADD COLUMN include_in_visit_summary INTEGER NOT NULL DEFAULT 0"
        )

    health_cols = {row[1] for row in conn.execute("PRAGMA table_info(health_records)")}
    if "photo_ref" not in health_cols:
        conn.execute(
            "ALTER TABLE health_records ADD COLUMN photo_ref TEXT"
        )

    # Optional average heart rate (bpm) for activity records. Stays NULL unless
    # the user enters it - ZyPulse never fabricates a reading and never infers
    # intensity, fitness or clinical safety from it.
    health_cols = {row[1] for row in conn.execute("PRAGMA table_info(health_records)")}
    if "avg_heart_rate" not in health_cols:
        conn.execute(
            "ALTER TABLE health_records ADD COLUMN avg_heart_rate INTEGER"
        )

    # Optional free-text note the user opted into sharing in the doctor visit
    # summary. Used for medication and activity records, whose `notes` column
    # already holds a generated summary. NULL = no note, so old rows are
    # untouched and unreadable-by-design.
    health_cols = {row[1] for row in conn.execute("PRAGMA table_info(health_records)")}
    if "visit_note" not in health_cols:
        conn.execute(
            "ALTER TABLE health_records ADD COLUMN visit_note TEXT"
        )

    pref_cols = {row[1] for row in conn.execute("PRAGMA table_info(user_preferences)")}
    pref_additions = {
        "display_name": "TEXT",
        "contact_email": "TEXT",
        "contact_phone": "TEXT",
        "accessibility_json": "TEXT",
    }
    for col, col_type in pref_additions.items():
        if col not in pref_cols:
            conn.execute(f"ALTER TABLE user_preferences ADD COLUMN {col} {col_type}")

    # Only English and Chinese are supported by the client and API. Normalise
    # legacy preference values so an older profile cannot reintroduce a removed locale.
    conn.execute(
        "UPDATE user_preferences SET language = 'en' WHERE language IS NULL OR language NOT IN ('en', 'zh')"
    )

    # Remove the legacy CHECK constraint on health_records.record_type if still present.
    # Record-type validation is enforced in Python (DataAccess.add_health_record),
    # so the DB constraint is redundant and would block new types like 'meal'.
    row = conn.execute(
        "SELECT sql FROM sqlite_master WHERE type='table' AND name='health_records'"
    ).fetchone()
    if row and row[0] and "CHECK" in row[0].upper():
        # Columns added by later migrations (photo_ref, avg_heart_rate,
        # visit_note) must survive the rebuild, otherwise existing photo
        # references, heart rates and visit notes would be dropped.
        old_cols = {c[1] for c in conn.execute("PRAGMA table_info(health_records)")}
        optional_cols = [
            c for c in ("photo_ref", "avg_heart_rate", "visit_note") if c in old_cols
        ]
        optional_types = {"photo_ref": "TEXT", "visit_note": "TEXT", "avg_heart_rate": "INTEGER"}
        optional_ddl = "".join(
            f",\n                {c} {optional_types[c]}" for c in optional_cols
        )
        optional_names = "".join(f", {c}" for c in optional_cols)

        conn.execute("ALTER TABLE health_records RENAME TO _hr_old")
        conn.execute(
            f"""
            CREATE TABLE health_records (
                record_id      INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id        TEXT NOT NULL,
                record_type    TEXT NOT NULL,
                value_numeric  REAL,
                value_text     TEXT,
                recorded_date  TEXT NOT NULL,
                recorded_at    TEXT NOT NULL,
                notes          TEXT,
                source         TEXT DEFAULT 'user_entry',
                include_in_visit_summary INTEGER NOT NULL DEFAULT 0,
                created_at     TEXT NOT NULL DEFAULT (datetime('now', 'localtime')){optional_ddl}
            )
            """
        )
        conn.execute(
            f"""
            INSERT INTO health_records
                (record_id, user_id, record_type, value_numeric, value_text,
                 recorded_date, recorded_at, notes, source, include_in_visit_summary, created_at{optional_names})
            SELECT record_id, user_id, record_type, value_numeric, value_text,
                 recorded_date, recorded_at, notes, source, include_in_visit_summary, created_at{optional_names}
            FROM _hr_old
            """
        )
        conn.execute("DROP TABLE _hr_old")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_health_user_date ON health_records(user_id, recorded_date)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_health_type ON health_records(record_type)")

    conn.commit()


def get_connection(db_path: str = None) -> sqlite3.Connection:
    """Get a database connection with row factory enabled."""
    if db_path is None:
        db_path = DB_PATH
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def reset_db(db_path: str = None):
    """Drop and recreate all tables. Use for development/testing only."""
    if db_path is None:
        db_path = DB_PATH
    conn = sqlite3.connect(db_path)
    conn.executescript("""
        DROP TABLE IF EXISTS health_records;
        DROP TABLE IF EXISTS user_preferences;
        DROP TABLE IF EXISTS ai_memory;
        DROP TABLE IF EXISTS registration_info;
        DROP TABLE IF EXISTS sharing_approved;
        DROP TABLE IF EXISTS audit_log;
    """)
    conn.close()
    return init_db(db_path)


if __name__ == "__main__":
    print(f"Initializing database at: {DB_PATH}")
    conn = init_db()
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
    tables = [row[0] for row in cursor.fetchall()]
    print(f"Tables created: {tables}")
    conn.close()
    print("Database initialization complete.")
