"""Small in-memory AI quota guard for the public demo.

This deliberately limits LLM-triggering endpoints before an API call is made.
For the hackathon's single Render instance, memory is sufficient; quotas reset
on a service restart and are not intended as an authentication system.
"""

from collections import defaultdict, deque
from datetime import timedelta
from threading import RLock

from ..time_utils import now_sg, today_sg_iso

CHAT_PER_MINUTE = 5
CHAT_PER_DAY = 25
BRIEFING_PER_DAY = 5


class AiUsageGuard:
    def __init__(self):
        self._events = defaultdict(deque)
        self._lock = RLock()

    def _prune(self, key, window):
        cutoff = now_sg() - window
        queue = self._events[key]
        while queue and queue[0] <= cutoff:
            queue.popleft()
        return queue

    def _key(self, kind, client_id, period):
        return f"{today_sg_iso()}:{kind}:{period}:{client_id}"

    def snapshot(self, client_id):
        with self._lock:
            chat_day = len(self._prune(self._key("chat", client_id, "day"), timedelta(days=1)))
            chat_minute = len(self._prune(self._key("chat", client_id, "minute"), timedelta(minutes=1)))
            briefing_day = len(self._prune(self._key("briefing", client_id, "day"), timedelta(days=1)))
            return {
                "chat": {"used_today": chat_day, "daily_limit": CHAT_PER_DAY, "remaining_today": max(0, CHAT_PER_DAY - chat_day), "used_this_minute": chat_minute, "minute_limit": CHAT_PER_MINUTE},
                "briefing": {"used_today": briefing_day, "daily_limit": BRIEFING_PER_DAY, "remaining_today": max(0, BRIEFING_PER_DAY - briefing_day)},
            }

    def consume(self, kind, client_id):
        with self._lock:
            snapshot = self.snapshot(client_id)
            if kind == "chat":
                if snapshot["chat"]["used_this_minute"] >= CHAT_PER_MINUTE:
                    return False, "minute"
                if snapshot["chat"]["remaining_today"] <= 0:
                    return False, "day"
                self._events[self._key("chat", client_id, "minute")].append(now_sg())
                self._events[self._key("chat", client_id, "day")].append(now_sg())
                return True, None
            if snapshot["briefing"]["remaining_today"] <= 0:
                return False, "day"
            self._events[self._key("briefing", client_id, "day")].append(now_sg())
            return True, None


ai_usage_guard = AiUsageGuard()
