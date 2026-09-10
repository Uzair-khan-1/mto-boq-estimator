"""
MTO (Material Take-Off) generation.

This module is a thin orchestration layer: it calls the deterministic
engineering functions (engineering/calculations.py) and organizes the
result for display/export. It performs NO calculation of its own -
that separation is intentional so all engineering formulas live in one
auditable place.
"""
from __future__ import annotations

from typing import Dict, List

import pandas as pd

from engineering.calculations import generate_all_quantities, steel_sanity_check
from models.schemas import ExtractedBuildingParams, ProjectInputs, QuantityLineItem


def generate_mto(params: ExtractedBuildingParams, project_inputs: ProjectInputs) -> List[QuantityLineItem]:
    return generate_all_quantities(params, project_inputs)


def group_by_category(items: List[QuantityLineItem]) -> Dict[str, List[QuantityLineItem]]:
    grouped: Dict[str, List[QuantityLineItem]] = {}
    for item in items:
        grouped.setdefault(item.category, []).append(item)
    return grouped


def mto_to_dataframe(items: List[QuantityLineItem]) -> pd.DataFrame:
    rows = [
        {
            "Item Code": i.item_code,
            "Category": i.category,
            "Description": i.description,
            "Unit": i.unit,
            "Quantity": i.quantity,
            "Confidence": i.confidence.value,
            "Formula": i.formula,
        }
        for i in items
    ]
    return pd.DataFrame(rows)


def compute_reinforcement_summary(items: List[QuantityLineItem]) -> dict:
    structural_categories = {"Footing", "Column", "Beam", "Slab"}
    structural_concrete = sum(
        i.quantity for i in items if i.category in structural_categories and i.unit == "m3"
    )
    total_steel = sum(i.quantity for i in items if i.category == "Reinforcement")
    return steel_sanity_check(structural_concrete, total_steel)
