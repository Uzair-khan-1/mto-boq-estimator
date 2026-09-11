"""
Loads and manages the editable material/labour rate book.

Rates start from `data/material_rates.json` but are fully editable in the
Streamlit session (see ui/components.py) before BOQ costing runs. Nothing
here calls the AI - rates are either the shipped defaults or user-entered.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, List

from models.schemas import MaterialRate
from utils import units as u

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
RATE_FILE = DATA_DIR / "material_rates.json"


def load_default_rates() -> List[MaterialRate]:
    with open(RATE_FILE, "r", encoding="utf-8") as f:
        payload = json.load(f)
    return [MaterialRate(**row) for row in payload["rates"]]


def rates_to_dict(rates: List[MaterialRate]) -> Dict[str, MaterialRate]:
    return {r.item_code: r for r in rates}


def load_default_assumptions() -> dict:
    with open(DATA_DIR / "default_assumptions.json", "r", encoding="utf-8") as f:
        return json.load(f)


def rate_for_unit_system(rate: MaterialRate, unit_system: str) -> MaterialRate:
    """Rates in the rate book are stored FPS-native (per cft / per sft),
    matching standard Pakistani estimation practice. If the user selected
    the SI unit system instead, convert the *rate itself* to an equivalent
    per-m3 / per-m2 price (rather than maintaining two separate rate
    books), so it still multiplies correctly against SI-unit quantities.

    kg (steel), Nos (counts), and LS (lump-sum) rates are unit-system-
    agnostic and pass through unchanged.
    """
    if unit_system != u.SI:
        return rate
    if rate.unit == "cft":
        return MaterialRate(
            item_code=rate.item_code,
            description=rate.description,
            unit="m3",
            category=rate.category,
            rate=rate.rate * u.CFT_PER_M3,
        )
    if rate.unit == "sft":
        return MaterialRate(
            item_code=rate.item_code,
            description=rate.description,
            unit="m2",
            category=rate.category,
            rate=rate.rate * u.SFT_PER_M2,
        )
    return rate
