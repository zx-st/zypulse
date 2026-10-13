"""
Private storage for user-uploaded health photos.

Why this module exists
----------------------
The bundled demo photos are static assets in `frontend/public/sample-photos`
and are served like any other public file. A photo the USER uploads is health
data and must not be published at a guessable public URL. Uploads are therefore:

  * written to a directory OUTSIDE the web root (`backend/var/uploads` by
    default, overridable with ZYPULSE_UPLOAD_DIR),
  * named with an opaque random key (never the user's filename),
  * indexed in the `photo_assets` table (owner, type, size, checksum, target
    record), and
  * only readable through `GET /api/photos/{photo_key}?user_id=...`, which
    refuses requests whose user_id does not own the asset.

Security limitation (prototype)
-------------------------------
There is **no authentication** in ZyPulse: `user_id` is an unverified string
sent by the client. The ownership check above therefore prevents accidental or
casual access only - it is not access control and must not be described as
secure authentication. Files are also stored unencrypted. This storage layer is
acceptable for synthetic demo data; it is **not** suitable for real users'
health photos until real authentication/authorisation is added.

Durability
----------
Files live on the server's local file system next to the SQLite database. That
is as durable as the database itself - and no more. On a host with an ephemeral
disk (for example a free-tier container that is rebuilt on redeploy) BOTH the
database and the uploads disappear together. There is no object storage, CDN or
external service involved, and this module makes no claim that uploads survive
a redeploy on such a host.

Cleanup
-------
`purge_orphans()` removes:
  * assets still `pending` (uploaded but never confirmed into a log entry) that
    are older than PENDING_TTL_HOURS, and
  * assets attached to a record that no longer exists (record deleted).
It is called on application startup and after a record is deleted, so cancelled
or abandoned uploads do not accumulate.
"""

import hashlib
import os
import secrets
import sqlite3
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any, List

# Sensitive uploads stay outside the served frontend directory.
DEFAULT_UPLOAD_DIR = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "var", "uploads")
)
UPLOAD_DIR = os.path.abspath(os.environ.get("ZYPULSE_UPLOAD_DIR") or DEFAULT_UPLOAD_DIR)

# Technical validation limits (image content is still never "recognised").
MAX_BYTES = 8 * 1024 * 1024  # 8 MB
ALLOWED_TYPES = {
    "image/png": ".png",
    "image/jpeg": ".jpg",
    "image/webp": ".webp",
}
# Magic bytes, so a renamed .exe cannot pass as an image.
_MAGIC = {
    "image/png": (b"\x89PNG\r\n\x1a\n", 0),
    "image/jpeg": (b"\xff\xd8\xff", 0),
    "image/webp": (b"RIFF", 0),
}
PENDING_TTL_HOURS = 24

PHOTO_REF_PREFIX = "photo:"


def ensure_dir() -> str:
    os.makedirs(UPLOAD_DIR, exist_ok=True)
    return UPLOAD_DIR


def validate(content_type: Optional[str], data: bytes, filename: Optional[str] = None) -> str:
    """Validate type and size. Raises ValueError with a user-safe message."""
    ct = (content_type or "").split(";")[0].strip().lower()
    if ct not in ALLOWED_TYPES:
        raise ValueError(
            "Unsupported file type. Upload a PNG, JPEG or WebP image."
        )
    if not data:
        raise ValueError("The selected file is empty.")
    if len(data) > MAX_BYTES:
        raise ValueError(f"Image is too large (max {MAX_BYTES // (1024 * 1024)} MB).")
    magic, offset = _MAGIC[ct]
    if data[offset:offset + len(magic)] != magic:
        raise ValueError("The file contents do not match an image file.")
    return ct


def store(user_id: str, content_type: str, data: bytes, original_name: Optional[str]) -> Dict[str, Any]:
    """Write the bytes to the private upload directory and return metadata."""
    ensure_dir()
    key = secrets.token_urlsafe(24)
    ext = ALLOWED_TYPES[content_type]
    safe_user = "".join(ch for ch in (user_id or "unknown") if ch.isalnum() or ch in "-_") or "unknown"
    user_dir = os.path.join(UPLOAD_DIR, safe_user)
    os.makedirs(user_dir, exist_ok=True)
    stored_path = os.path.join(user_dir, f"{key}{ext}")
    with open(stored_path, "wb") as fh:
        fh.write(data)
    return {
        "photo_key": key,
        "photo_ref": f"{PHOTO_REF_PREFIX}{key}",
        "content_type": content_type,
        "byte_size": len(data),
        "stored_path": stored_path,
        "checksum": hashlib.sha256(data).hexdigest(),
        "original_name": (original_name or "")[:200] or None,
    }


def resolve(stored_path: str) -> Optional[str]:
    """Return the absolute path only when it is inside the upload directory."""
    try:
        candidate = os.path.abspath(stored_path)
    except Exception:
        return None
    root = os.path.abspath(UPLOAD_DIR)
    if candidate == root or candidate.startswith(root + os.sep):
        return candidate if os.path.isfile(candidate) else None
    return None


def remove(stored_path: str) -> bool:
    path = resolve(stored_path)
    if not path:
        return False
    try:
        os.remove(path)
        return True
    except OSError:
        return False


def purge_orphans(conn: sqlite3.Connection) -> Dict[str, int]:
    """Delete abandoned uploads and assets whose record has been removed."""
    ensure_dir()
    cutoff = (datetime.now(timezone.utc) - timedelta(hours=PENDING_TTL_HOURS)).strftime(
        "%Y-%m-%dT%H:%M:%fZ"
    )
    removed = {"pending_expired": 0, "missing_record": 0}

    rows: List[sqlite3.Row] = conn.execute(
        "SELECT photo_key, stored_path FROM photo_assets WHERE status = 'pending' AND created_at < ?",
        (cutoff,),
    ).fetchall()
    for r in rows:
        remove(r["stored_path"])
        conn.execute("DELETE FROM photo_assets WHERE photo_key = ?", (r["photo_key"],))
        removed["pending_expired"] += 1

    rows = conn.execute(
        """
        SELECT p.photo_key, p.stored_path
        FROM photo_assets p
        LEFT JOIN health_records h ON h.record_id = p.record_id
        WHERE p.record_id IS NOT NULL AND h.record_id IS NULL
        """
    ).fetchall()
    for r in rows:
        remove(r["stored_path"])
        conn.execute("DELETE FROM photo_assets WHERE photo_key = ?", (r["photo_key"],))
        removed["missing_record"] += 1

    conn.commit()
    return removed


def parse_photo_ref(photo_ref: Optional[str]) -> Optional[str]:
    """Return the photo_key when a record's photo_ref points at an upload."""
    if not photo_ref or not photo_ref.startswith(PHOTO_REF_PREFIX):
        return None
    key = photo_ref[len(PHOTO_REF_PREFIX):].strip()
    return key or None
