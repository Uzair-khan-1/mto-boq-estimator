"""
BOQ (Bill of Quantities) generation.

Takes the deterministic MTO quantities and applies:
1. Category-specific wastage/allowance percentages (editable)
2. Unit rates (editable rate book)
3. A "Preliminaries & rough MEP allowance" lump-sum line, because a
   residential estimate that silently omits site overheads, plumbing, and
   electrical rough-in would understate cost significantly - the MVP does
   not compute MEP quantities, so this is clearly flagged as a placeholder.
4. Overall contingency percentage -> grand total

No AI involvement here either - pure arithmetic over user-approved inputs.
"""
from __future__ import annotations

from typing import Dict, List

import pandas as pd

from models.schemas import (
    BOQLineItem,
    ConfidenceLevel,
    CostSummary,
    MaterialRate,
    ProjectInputs,
    QuantityLineItem,
    WastageFactors,
)

# Maps a quantity item's category to the relevant wastage-factor field name
CATEGORY_TO_WASTAGE_FIELD = {
    "Excavation": None,  # no wastage applied to excavated earth
    "PCC": "concrete_pct",
    "Footing": "concrete_pct",
    "Column": "concrete_pct",
    "Beam": "concrete_pct",
    "Slab": "concrete_pct",
    "Reinforcement": "steel_pct",
    "Formwork": "formwork_pct",
    "Masonry": "brick_block_pct",
    "Plaster": "plaster_pct",
    "Flooring": "flooring_pct",
    "Waterproofing": "misc_pct",
    "Painting": "paint_pct",
    "DPC": "concrete_pct",
    "Anti-termite": "misc_pct",
}

PRELIMINARIES_PCT_OF_CIVIL_SUBTOTAL = 8.0


def _wastage_for(item: QuantityLineItem, wastage: WastageFactors) -> float:
    field = CATEGORY_TO_WASTAGE_FIELD.get(item.category, "misc_pct")
    if field is None:
        return 0.0
    return getattr(wastage, field, wastage.misc_pct)


def generate_boq(
    mto_items: List[QuantityLineItem],
    rate_book: Dict[str, MaterialRate],
    wastage: WastageFactors,
    project_inputs: ProjectInputs,
    include_preliminaries: bool = True,
    preliminaries_pct: float = PRELIMINARIES_PCT_OF_CIVIL_SUBTOTAL,
) -> tuple[List[BOQLineItem], CostSummary]:
    boq_items: List[BOQLineItem] = []

    for item in mto_items:
        wastage_pct = _wastage_for(item, wastage)
        qty_with_wastage = item.quantity * (1 + wastage_pct / 100.0)

        rate_row = rate_book.get(item.item_code)
        if rate_row is None:
            rate = 0.0
            remarks = "No rate found in rate book - please add a rate."
        else:
            rate = rate_row.rate
            remarks = ""

        amount = qty_with_wastage * rate
        boq_items.append(
            BOQLineItem(
                item_code=item.item_code,
                description=item.description,
                category=item.category,
                unit=item.unit,
                quantity=round(item.quantity, 3),
                wastage_pct=wastage_pct,
                quantity_with_wastage=round(qty_with_wastage, 3),
                rate=rate,
                amount=round(amount, 2),
                confidence=item.confidence,
                remarks=remarks,
            )
        )

    civil_subtotal = sum(b.amount for b in boq_items)

    if include_preliminaries:
        prelim_amount = civil_subtotal * preliminaries_pct / 100.0
        boq_items.append(
            BOQLineItem(
                item_code="PRELIM-01",
                description=(
                    f"Preliminaries, site overheads & rough MEP allowance "
                    f"({preliminaries_pct:.1f}% of civil subtotal - placeholder, NOT a detailed MEP estimate)"
                ),
                category="Preliminaries",
                unit="LS",
                quantity=1.0,
                wastage_pct=0.0,
                quantity_with_wastage=1.0,
                rate=round(prelim_amount, 2),
                amount=round(prelim_amount, 2),
                confidence=ConfidenceLevel.LOW,
                remarks="Lump-sum placeholder only. Electrical/plumbing/HVAC quantities are NOT computed in this MVP.",
            )
        )

    subtotal = sum(b.amount for b in boq_items)
    contingency_amount = subtotal * project_inputs.contingency_pct / 100.0
    grand_total = subtotal + contingency_amount

    cost_summary = CostSummary(
        subtotal=round(subtotal, 2),
        contingency_pct=project_inputs.contingency_pct,
        contingency_amount=round(contingency_amount, 2),
        grand_total=round(grand_total, 2),
        currency=project_inputs.currency,
    )
    return boq_items, cost_summary


def boq_to_dataframe(items: List[BOQLineItem]) -> pd.DataFrame:
    rows = [
        {
            "Item Code": i.item_code,
            "Category": i.category,
            "Description": i.description,
            "Unit": i.unit,
            "Quantity": i.quantity,
            "Wastage %": i.wastage_pct,
            "Qty incl. Wastage": i.quantity_with_wastage,
            "Rate": i.rate,
            "Amount": i.amount,
            "Confidence": i.confidence.value,
            "Remarks": i.remarks,
        }
        for i in items
    ]
    return pd.DataFrame(rows)


def cost_by_category(items: List[BOQLineItem]) -> pd.DataFrame:
    df = boq_to_dataframe(items)
    if df.empty:
        return df
    grouped = df.groupby("Category", as_index=False)["Amount"].sum().sort_values("Amount", ascending=False)
    return grouped
