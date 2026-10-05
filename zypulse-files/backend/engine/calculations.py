"""
C3: Deterministic Calculation Engine

ALL numerical health trends originate here. The LLM is NEVER asked to calculate.
It may only explain numbers this engine has already computed.

Safety restrictions:
- Never fabricates values
- Returns insufficient_data if fewer than 3 readings
- Never claims causation
- Never compares to clinical targets unless clinician-set target exists
"""

from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
from ..time_utils import now_utc_iso


class CalculationEngine:
    """Pure Python deterministic calculations. No AI. No LLM. No internet."""

    def __init__(self, db):
        self.db = db

    def calculate_glucose_trend(
        self, user_id: str, period: str = "fasting", days: int = 7
    ) -> Dict[str, Any]:
        """
        Calculate glucose trend for a given period over N days.

        Returns structured JSON with:
        - average, min, max
        - trend_direction: increasing/decreasing/stable/insufficient_data
        - trend_pct: percentage change vs previous period
        - source_records: list of readings used (for traceability)
        - insufficient_data: flag
        """
        # Get readings for current period
        readings = self.db.get_glucose_readings(user_id, period=period, days=days)

        # Also get previous period for comparison
        prev_readings = self._get_previous_period_readings(user_id, period, days)

        if len(readings) < 3:
            return {
                "metric": "glucose",
                "period": period,
                "days_requested": days,
                "readings_count": len(readings),
                "average": None,
                "min_value": None,
                "max_value": None,
                "trend_direction": "insufficient_data",
                "trend_pct": None,
                "source_records": [self._format_record(r) for r in readings],
                "insufficient_data": True,
                "notes": f"Only {len(readings)} reading(s) available. Need at least 3 for trend calculation.",
            }

        values = [r["value_numeric"] for r in readings if r["value_numeric"] is not None]

        avg = sum(values) / len(values)
        min_val = min(values)
        max_val = max(values)

        # Trend direction: compare current period average to previous period
        trend_direction, trend_pct = self._compute_trend(values, prev_readings)

        return {
            "metric": "glucose",
            "period": period,
            "days_requested": days,
            "readings_count": len(values),
            "average": round(avg, 1),
            "min_value": round(min_val, 1),
            "max_value": round(max_val, 1),
            "trend_direction": trend_direction,
            "trend_pct": round(trend_pct, 1) if trend_pct is not None else None,
            "source_records": [self._format_record(r) for r in readings],
            "insufficient_data": False,
            "notes": self._generate_glucose_notes(avg, trend_direction, period),
        }

    def calculate_medication_adherence(
        self, user_id: str, days: int = 30
    ) -> Dict[str, Any]:
        """
        Calculate medication adherence rate.

        adherence_rate = (taken doses) / (expected doses) * 100
        Expected = 2 doses per day (morning + evening)
        """
        logs = self.db.get_medication_logs(user_id, days=days)

        # Group by date
        by_date: Dict[str, Dict[str, str]] = {}
        for log in logs:
            date = log["recorded_date"]
            rtype = log["record_type"]  # medication_morning or medication_evening
            status = log["value_text"]  # taken, missed, skipped
            if date not in by_date:
                by_date[date] = {}
            by_date[date][rtype] = status

        expected_doses = len(by_date) * 2  # morning + evening
        if expected_doses == 0:
            return {
                "metric": "medication",
                "days_requested": days,
                "days_with_logs": 0,
                "expected_doses": 0,
                "taken_doses": 0,
                "adherence_rate": None,
                "missed_doses": 0,
                "trend_direction": "insufficient_data",
                "source_records": [],
                "insufficient_data": True,
                "notes": "No medication logs found.",
            }

        taken = 0
        missed = 0
        skipped = 0

        for date, doses in by_date.items():
            for rtype in ["medication_morning", "medication_evening"]:
                status = doses.get(rtype)
                if status == "taken":
                    taken += 1
                elif status == "missed":
                    missed += 1
                elif status == "skipped":
                    skipped += 1

        adherence_rate = (taken / expected_doses * 100) if expected_doses > 0 else 0

        return {
            "metric": "medication",
            "days_requested": days,
            "days_with_logs": len(by_date),
            "expected_doses": expected_doses,
            "taken_doses": taken,
            "missed_doses": missed,
            "skipped_doses": skipped,
            "adherence_rate": round(adherence_rate, 1),
            "trend_direction": "stable" if adherence_rate >= 80 else "below_target",
            "source_records": [self._format_record(r) for r in logs],
            "insufficient_data": len(by_date) < 3,
            "notes": self._generate_medication_notes(adherence_rate, missed, len(by_date)),
        }

    def calculate_activity_frequency(
        self, user_id: str, days: int = 30
    ) -> Dict[str, Any]:
        """
        Calculate activity frequency and total duration.
        """
        logs = self.db.get_activity_logs(user_id, days=days)

        if len(logs) < 1:
            return {
                "metric": "activity",
                "days_requested": days,
                "activity_days": 0,
                "total_duration_min": 0,
                "avg_duration_min": None,
                "source_records": [],
                "insufficient_data": True,
                "notes": "No activity logs found.",
            }

        durations = [r["value_numeric"] for r in logs if r["value_numeric"] is not None]
        total_duration = sum(durations)
        avg_duration = total_duration / len(durations) if durations else 0

        # Count unique days with activity
        unique_days = set(r["recorded_date"] for r in logs)

        return {
            "metric": "activity",
            "days_requested": days,
            "activity_days": len(unique_days),
            "total_duration_min": total_duration,
            "avg_duration_min": round(avg_duration, 1),
            "source_records": [self._format_record(r) for r in logs],
            "insufficient_data": len(unique_days) < 2,
            "notes": self._generate_activity_notes(len(unique_days), total_duration, days),
        }

    def get_full_summary(self, user_id: str, days: int = 7) -> Dict[str, Any]:
        """Get a combined summary of all metrics for AI context."""
        glucose_fasting = self.calculate_glucose_trend(user_id, "fasting", days)
        glucose_evening = self.calculate_glucose_trend(user_id, "evening", days)
        med_adherence = self.calculate_medication_adherence(user_id, 30)
        activity = self.calculate_activity_frequency(user_id, 30)

        return {
            "glucose_fasting": glucose_fasting,
            "glucose_evening": glucose_evening,
            "medication_adherence": med_adherence,
            "activity": activity,
            "generated_at": now_utc_iso(),
            "generated_by": "deterministic_engine",
            "note": "All values calculated by deterministic Python code. AI may explain but not recalculate.",
        }

    # ============================================================
    # PRIVATE HELPERS
    # ============================================================

    def _get_previous_period_readings(
        self, user_id: str, period: str, days: int
    ) -> List[Dict[str, Any]]:
        """Get readings from the previous period for trend comparison."""
        current_readings = self.db.get_glucose_readings(user_id, period=period, days=days * 2)

        if len(current_readings) <= days:
            # Take first half as "previous"
            return current_readings[len(current_readings) // 2:]
        else:
            # Split: first `days` are older (previous), rest are current
            return current_readings[days:]

    def _compute_trend(
        self, current_values: List[float], prev_readings: List[Dict[str, Any]]
    ) -> tuple:
        """Compute trend direction and percentage change."""
        if not prev_readings or len(prev_readings) < 3:
            return "stable", 0.0

        prev_values = [r["value_numeric"] for r in prev_readings if r["value_numeric"] is not None]
        if len(prev_values) < 3:
            return "stable", 0.0

        current_avg = sum(current_values) / len(current_values)
        prev_avg = sum(prev_values) / len(prev_values)

        if prev_avg == 0:
            return "stable", 0.0

        pct_change = ((current_avg - prev_avg) / prev_avg) * 100

        # Threshold: 5% change to declare trend
        if pct_change > 5:
            return "increasing", pct_change
        elif pct_change < -5:
            return "decreasing", pct_change
        else:
            return "stable", pct_change

    def _format_record(self, record: Dict[str, Any]) -> Dict[str, Any]:
        """Format a DB record for the source_records list."""
        return {
            "date": record.get("recorded_date"),
            "value": record.get("value_numeric"),
            "type": record.get("record_type"),
            "notes": record.get("notes"),
        }

    def _generate_glucose_notes(self, avg: float, direction: str, period: str) -> str:
        """Generate plain-language notes (deterministic, no medical advice)."""
        period_label = "fasting (before breakfast)" if period == "fasting" else "evening"
        return f"Average {period_label} glucose over this period was {avg:.1f} mmol/L. Trend: {direction}."

    def _generate_medication_notes(self, rate: float, missed: int, days: int) -> str:
        """Generate medication adherence notes."""
        if rate >= 80:
            return f"Adherence rate: {rate:.1f}% over {days} days with {missed} missed dose(s). Good consistency."
        elif rate >= 50:
            return f"Adherence rate: {rate:.1f}% over {days} days with {missed} missed dose(s). Some room for improvement."
        else:
            return f"Adherence rate: {rate:.1f}% over {days} days with {missed} missed dose(s). Consider discussing reminder strategies."

    def _generate_activity_notes(self, active_days: int, total_min: float, period_days: int) -> str:
        """Generate activity frequency notes."""
        return f"Activity logged on {active_days} day(s) over {period_days} days. Total: {total_min:.0f} minutes."
