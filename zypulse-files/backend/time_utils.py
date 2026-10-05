"""Single clock policy: Singapore civil time and timezone-aware UTC storage."""

from datetime import datetime, timezone
from zoneinfo import ZoneInfo

SINGAPORE_TZ = ZoneInfo("Asia/Singapore")


def now_sg() -> datetime:
    return datetime.now(SINGAPORE_TZ)


def now_utc_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def today_sg_iso() -> str:
    return now_sg().date().isoformat()
