"""Adapter for Sport Singapore's public Sport Facilities dataset."""

import csv
import hashlib
import io
import os
import threading
import time
from collections import OrderedDict
from typing import Any, Dict, List

import requests


DATASET_ID = "d_2cfb0867cdeb2b7303068995699dc33b"
POLL_DOWNLOAD_URL = (
    "https://api-open.data.gov.sg/v1/public/api/datasets/"
    f"{DATASET_ID}/poll-download"
)
CACHE_TTL_SECONDS = 6 * 60 * 60
PLACEHOLDER_VENUE_NAMES = {"", "-", "n/a", "na", "null", "none"}


class SportFacilitiesProvider:
    """Fetch, normalise, and cache the public Sport Singapore facility data."""

    def __init__(self, cache_ttl_seconds: int = CACHE_TTL_SECONDS) -> None:
        self.cache_ttl_seconds = cache_ttl_seconds
        self._cached_facilities: List[Dict[str, Any]] = []
        self._cached_at = 0.0
        self._lock = threading.Lock()

    def list_facilities(self, activity_type: str | None = None) -> List[Dict[str, Any]]:
        facilities = self._get_facilities()
        if not activity_type:
            return facilities

        needle = activity_type.strip().lower()
        return [
            facility for facility in facilities
            if any(needle in sport.lower() for sport in facility["sports"])
        ]

    def _get_facilities(self) -> List[Dict[str, Any]]:
        now = time.monotonic()
        with self._lock:
            if self._cached_facilities and now - self._cached_at < self.cache_ttl_seconds:
                return self._cached_facilities

            try:
                facilities = self._download_and_normalise()
            except requests.RequestException:
                if self._cached_facilities:
                    return self._cached_facilities
                raise

            self._cached_facilities = facilities
            self._cached_at = now
            return facilities

    def _download_and_normalise(self) -> List[Dict[str, Any]]:
        # data.gov.sg's edge service rejects some default HTTP client user
        # agents; identify this server for both public requests and API-key use.
        headers = {"User-Agent": "ZyPulse/0.1"}
        api_key = os.getenv("DATA_GOV_SG_API_KEY")
        if api_key:
            headers["X-API-Key"] = api_key

        poll_response = requests.get(POLL_DOWNLOAD_URL, headers=headers, timeout=20)
        poll_response.raise_for_status()
        try:
            payload = poll_response.json()
        except ValueError as exc:
            raise requests.RequestException("data.gov.sg returned an invalid API response") from exc
        if payload.get("code") != 0 or not payload.get("data", {}).get("url"):
            raise requests.RequestException("data.gov.sg did not return a dataset download URL")

        csv_response = requests.get(payload["data"]["url"], timeout=30)
        csv_response.raise_for_status()
        return self._normalise_csv(csv_response.text)

    @staticmethod
    def _normalise_csv(csv_text: str) -> List[Dict[str, Any]]:
        grouped: "OrderedDict[tuple[str, str, str, str], Dict[str, Any]]" = OrderedDict()
        for row in csv.DictReader(io.StringIO(csv_text.lstrip("\ufeff"))):
            venue = (row.get("VenueName") or "").strip()
            facility_type = (row.get("SportsFacility") or "").strip()
            # The census includes many amenities whose venue is recorded as
            # "-". A postcode and coordinates alone are not a meaningful
            # facility card, so exclude them rather than rendering duplicates
            # with an unknown title.
            if venue.casefold() in PLACEHOLDER_VENUE_NAMES or not facility_type:
                continue

            postal_code = (row.get("PostalCode") or "").strip()
            latitude = (row.get("Latitude") or "").strip()
            longitude = (row.get("Longitude") or "").strip()
            key = (venue.casefold(), postal_code, latitude, longitude)
            if key not in grouped:
                digest = hashlib.sha256("|".join(key).encode("utf-8")).hexdigest()[:16]
                grouped[key] = {
                    "activity_id": f"sportsg-{digest}",
                    "title": venue,
                    "location": f"Singapore {postal_code}" if postal_code else "Singapore",
                    "postal_code": postal_code or None,
                    "latitude": SportFacilitiesProvider._to_float(latitude),
                    "longitude": SportFacilitiesProvider._to_float(longitude),
                    "sports": [],
                    "source": "Sport Singapore via data.gov.sg",
                }
            if facility_type not in grouped[key]["sports"]:
                grouped[key]["sports"].append(facility_type)

        facilities = list(grouped.values())
        for facility in facilities:
            facility["sports"].sort(key=str.casefold)
            facility["description"] = "Available facilities: " + ", ".join(facility["sports"])
        return sorted(facilities, key=lambda item: item["title"].casefold())

    @staticmethod
    def _to_float(value: str) -> float | None:
        try:
            return float(value) if value else None
        except ValueError:
            return None


sport_facilities_provider = SportFacilitiesProvider()
