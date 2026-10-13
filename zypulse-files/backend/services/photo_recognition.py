"""
Simulated AI Photo Recognition Service (replaceable Vision-AI module).

This module is the ONLY place that "recognises" photos. It contains no real
vision model and performs no image processing. Instead it maps a predefined
sample id to a deterministic, hand-authored extraction result that matches what
is visibly shown on the bundled demo image.

Design intent (per spec section 9):
- A future real Vision API only needs to return the SAME structured `extraction`
  payload (and set `simulated=False`). The endpoint and the shared frontend
  component already consume this shape, so no UI changes would be required.
- Do NOT fabricate readings, medicines or nutrition. Only the predefined sample
  assets return a result; any other upload is reported as unrecognised so the
  UI can fall back to manual entry.

All values below are illustrative DEMO estimates, not clinically precise.
"""

import json
import os
from typing import Dict, Any, Optional, List

IMAGE_BASE = "/sample-photos"

# ---------------------------------------------------------------------------
# NUTRITION: reuse the application's existing food catalogue.
# The catalogue supplies carbohydrate and sugar per one standard serving only.
# It contains NO calorie and NO protein data, so those fields are returned as
# None and the UI shows "Estimate unavailable" instead of inventing values.
# ---------------------------------------------------------------------------
_CATALOGUE_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "food_catalogue.json")
_catalogue_cache: Optional[Dict[str, Dict[str, Any]]] = None

NO_DATA_MSG = "Estimate unavailable"


def _catalogue() -> Dict[str, Dict[str, Any]]:
    global _catalogue_cache
    if _catalogue_cache is None:
        try:
            with open(_CATALOGUE_PATH, encoding="utf-8") as fh:
                data = json.load(fh)
            _catalogue_cache = {f["food_id"]: f for f in data.get("foods", [])}
        except Exception:  # pragma: no cover - catalogue missing/unreadable
            _catalogue_cache = {}
    return _catalogue_cache


def _catalogue_item(food_id: Optional[str], fallback_name: str = "") -> Dict[str, Any]:
    """Build a reviewable meal item from the existing nutrition catalogue.

    Deterministic: same food_id -> same values, every time.
    """
    cat = _catalogue().get(food_id) if food_id else None
    if not cat:
        # Not present in the catalogue: no value is invented.
        return {
            "food_id": None,
            "food_name": fallback_name,
            "portion_key": "1",
            "portion_label": "1",
            "base_carbs": None,
            "base_sugar": None,
            "calories": None,
            "protein": None,
            "is_sugary_drink": False,
            "source": f"Not in nutrition catalogue - {NO_DATA_MSG}; enter values manually.",
        }
    return {
        "food_id": cat["food_id"],
        "food_name": cat["name"],
        "portion_key": "1",
        "portion_label": "1",
        "base_carbs": float(cat.get("base_carbs") or 0),
        "base_sugar": float(cat.get("base_sugar") or 0),
        "calories": None,  # catalogue has no calorie data
        "protein": None,  # catalogue has no protein data
        "is_sugary_drink": bool(cat.get("is_sugary_drink", False)),
        "source": (
            f"Source: {cat.get('source', 'DEMO/SYNTHETIC')} carbohydrate/sugar per 1 standard serving. "
            f"Calories and protein: {NO_DATA_MSG} (not in catalogue). Illustrative demo values, not clinically precise."
        ),
    }

# ---------------------------------------------------------------------------
# CONTROLLED DEMO LIBRARY
# Each entry is deterministic: the same sample_id ALWAYS returns the same result.
# `image` points to a bundled asset that visibly shows the extracted data.
# ---------------------------------------------------------------------------

SAMPLE_LIBRARY: Dict[str, Dict[str, Any]] = {
    # ----------------------------- GLUCOSE -----------------------------
    "glucose_clear_1": {
        "category": "glucose",
        "label": "Glucose meter (7.2 mmol/L)",
        "image": f"{IMAGE_BASE}/glucose_1.png",
        "extraction": {
            "reading": 7.2,
            "unit": "mmol/L",
            "datetime": "2025-06-15 08:12",
            "visible_in_photo": ["reading", "unit", "datetime"],
            "needs_review": False,
            "unclear": False,
        },
    },
    "glucose_clear_2": {
        "category": "glucose",
        "label": "Glucose meter (5.4 mmol/L)",
        "image": f"{IMAGE_BASE}/glucose_2.png",
        "extraction": {
            "reading": 5.4,
            "unit": "mmol/L",
            "datetime": "2025-06-15 19:40",
            "visible_in_photo": ["reading", "unit", "datetime"],
            "needs_review": False,
            "unclear": False,
        },
    },
    "glucose_unclear": {
        "category": "glucose",
        "label": "Glucose meter (reading unclear)",
        "image": f"{IMAGE_BASE}/glucose_unclear.png",
        "extraction": {
            "reading": None,
            "unit": "mmol/L",
            "datetime": None,
            "visible_in_photo": ["device"],
            "needs_review": True,
            "unclear": True,
            "note": "Reading is not legible in this photo. Enter the value yourself.",
        },
    },

    # --------------------------- MEDICATION ----------------------------
    "med_pkg_name": {
        "category": "medication",
        "label": "Metformin packaging (name & strength)",
        "image": f"{IMAGE_BASE}/med_pkg.png",
        "extraction": {
            "name": "Metformin",
            "strength": "500mg",
            "form": "tablet",
            "visible_qty": None,
            "unclear_qty": False,
            "from_saved_list": False,
            "visible_in_photo": ["name", "strength", "form"],
            "note": "Packaging shows name/strength; tablet count not verifiable from image.",
        },
    },
    "med_visible_tablets": {
        "category": "medication",
        "label": "Metformin blister (2 tablets visible)",
        "image": f"{IMAGE_BASE}/med_tablets.png",
        "extraction": {
            "name": "Metformin",
            "strength": "500mg",
            "form": "tablet",
            "visible_qty": 2,
            "unclear_qty": False,
            "from_saved_list": False,
            "visible_in_photo": ["name", "strength", "form", "quantity"],
        },
    },
    "med_unclear_qty": {
        "category": "medication",
        "label": "Medication (quantity unclear)",
        "image": f"{IMAGE_BASE}/med_unclear.png",
        "extraction": {
            "name": "Metformin",
            "strength": "500mg",
            "form": "tablet",
            "visible_qty": None,
            "unclear_qty": True,
            "from_saved_list": False,
            "visible_in_photo": ["name", "strength", "form"],
            "note": "Quantity not clearly visible. Enter the amount you actually took.",
        },
    },
    "med_saved_list": {
        "category": "medication",
        "label": "Metformin from your saved list",
        "image": f"{IMAGE_BASE}/med_saved.png",
        "extraction": {
            "name": "Metformin",
            "strength": "500mg",
            "form": "tablet",
            "visible_qty": None,
            "unclear_qty": False,
            "from_saved_list": True,
            "visible_in_photo": ["name", "strength", "form"],
            "note": "Matches your saved medication list. A photo does not prove intake.",
        },
    },

    # ------------------------------ MEAL -------------------------------
    # Nutrition values are illustrative DEMO estimates, not clinically precise.
    # `protein` is left null where no credible value is available -> UI shows
    # "Estimate unavailable".
    "meal_chicken_rice": {
        "category": "meal",
        "label": "Chicken Rice (1 plate)",
        "image": f"{IMAGE_BASE}/meal_chicken_rice.png",
        "extraction": {
            "visible_in_photo": ["plate contents", "food names"],
            "items": [_catalogue_item("chicken_rice", "Chicken Rice")],
        },
    },
    "meal_fish_soup": {
        "category": "meal",
        "label": "Fish Soup (1 bowl)",
        "image": f"{IMAGE_BASE}/meal_fish_soup.png",
        "extraction": {
            "visible_in_photo": ["bowl contents", "food names"],
            "items": [_catalogue_item("fish_soup", "Fish Soup")],
        },
    },
    "meal_nasi_lemak": {
        "category": "meal",
        "label": "Nasi Lemak (1 packet)",
        "image": f"{IMAGE_BASE}/meal_nasi_lemak.png",
        "extraction": {
            "visible_in_photo": ["plate contents", "food names"],
            "items": [_catalogue_item("nasi_lemak", "Nasi Lemak")],
        },
    },
    "meal_roti_teh": {
        "category": "meal",
        "label": "Roti Prata + Teh Tarik",
        "image": f"{IMAGE_BASE}/meal_roti_teh.png",
        "extraction": {
            "visible_in_photo": ["plate contents", "drink", "food names"],
            "items": [
                _catalogue_item("roti_prata", "Roti Prata"),
                _catalogue_item("teh_tarik", "Teh Tarik"),
            ],
        },
    },
    "meal_mooncake": {
        "category": "meal",
        "label": "Mooncake / Cookie snack",
        "image": f"{IMAGE_BASE}/meal_mooncake.png",
        "extraction": {
            "visible_in_photo": ["snack", "food names"],
            "items": [_catalogue_item(None, "Mooncake")],
        },
    },
}

DISCLAIMER = (
    "SIMULATED recognition - no real vision model is connected. "
    "Results are predefined demo data, not analysed from your photo. "
    "Review and confirm before saving."
)


def list_samples(category: Optional[str] = None) -> List[Dict[str, Any]]:
    """Return metadata for the sample picker (no extraction payload)."""
    out = []
    for sid, meta in SAMPLE_LIBRARY.items():
        if category and meta["category"] != category:
            continue
        ext = meta["extraction"]
        out.append({
            "sample_id": sid,
            "category": meta["category"],
            "label": meta["label"],
            "image": meta["image"],
            "unclear": bool(ext.get("unclear") or ext.get("unclear_qty")),
            "from_saved_list": bool(ext.get("from_saved_list")),
            "needs_review": bool(ext.get("needs_review")),
        })
    return out


def analyze(
    category: Optional[str] = None,
    sample_id: Optional[str] = None,
    filename: Optional[str] = None,
) -> Dict[str, Any]:
    """Simulated photo analysis.

    - Known sample_id  -> deterministic predefined extraction (recognised).
    - Anything else    -> not recognised; the UI must fall back to manual entry.
    """
    if sample_id and sample_id in SAMPLE_LIBRARY:
        meta = SAMPLE_LIBRARY[sample_id]
        return {
            "recognized": True,
            "simulated": True,
            "category": meta["category"],
            "sample_id": sample_id,
            "image": meta["image"],
            "extraction": meta["extraction"],
            "disclaimer": DISCLAIMER,
        }

    # No real vision capability: an arbitrary upload cannot be analysed.
    return {
        "recognized": False,
        "simulated": True,
        "category": category,
        "reason": (
            "This photo is not a recognised demo asset. Photo recognition is "
            "simulated in this prototype, so the image was not analysed. "
            "Please enter the details manually."
        ),
        "disclaimer": DISCLAIMER,
    }
