"""
Reusable Streamlit widgets shared across app.py steps.
"""
from __future__ import annotations

from typing import Dict

import pandas as pd
import streamlit as st

from models.schemas import ConfidenceLevel, Estimate, MaterialRate, Source, WastageFactors
from utils import units as u

CONFIDENCE_COLORS = {
    ConfidenceLevel.HIGH: "#1a7f37",
    ConfidenceLevel.MEDIUM: "#9a6700",
    ConfidenceLevel.LOW: "#c0392b",
}
CONFIDENCE_BG = {
    ConfidenceLevel.HIGH: "#dafbe1",
    ConfidenceLevel.MEDIUM: "#fff8c5",
    ConfidenceLevel.LOW: "#ffebe9",
}


def confidence_badge(confidence: ConfidenceLevel) -> str:
    color = CONFIDENCE_COLORS.get(confidence, "#555")
    bg = CONFIDENCE_BG.get(confidence, "#eee")
    return (
        f'<span style="background-color:{bg};color:{color};padding:2px 8px;'
        f'border-radius:10px;font-size:0.75rem;font-weight:600;">{confidence.value}</span>'
    )


# Dimension-type -> (to_display, from_display, unit_label_fn, default_step)
_DIMENSION_HANDLERS = {
    "length": (u.length_to_display, u.length_from_display, u.length_unit_label, {"SI": 0.05, "FPS": 0.5}),
    "thickness": (u.thickness_to_display, u.thickness_from_display, u.thickness_unit_label, {"SI": 0.005, "FPS": 0.25}),
    "area": (u.area_to_display, u.area_from_display, u.area_unit_label, {"SI": 1.0, "FPS": 5.0}),
}


def render_estimate_input(
    label: str,
    estimate: Estimate,
    key: str,
    dimension_type: str = "length",
    unit_system: str = "SI",
    step: float | None = None,
    min_value: float = 0.0,
    help_text: str | None = None,
) -> Estimate:
    """Render one editable numeric field with its confidence badge + note,
    converting between SI (stored internally) and the user's chosen display
    unit system (SI or FPS), and return a (possibly updated) Estimate whose
    `.value` is always in SI - callers never need to think about units.

    dimension_type controls the conversion applied:
      - "length"    -> m <-> ft   (spans, heights, footing/beam lengths)
      - "thickness" -> m <-> in   (cross-sections: column/beam b&d, wall &
                                    slab thickness)
      - "area"      -> sqm <-> sft
      - "count"     -> no conversion (Nos)
      - "weight"    -> no conversion (kg)
    """
    if dimension_type in _DIMENSION_HANDLERS:
        to_disp, from_disp, unit_label_fn, step_map = _DIMENSION_HANDLERS[dimension_type]
        unit_label = unit_label_fn(unit_system)
        display_value = to_disp(estimate.value, unit_system)
        resolved_step = step if step is not None else step_map.get(unit_system, 0.1)
    else:
        # "count" or "weight" - no unit conversion
        unit_label = "nos" if dimension_type == "count" else "kg"
        display_value = estimate.value
        resolved_step = step if step is not None else 1.0

        def to_disp(v, _s):
            return v

        def from_disp(v, _s):
            return v

    col1, col2 = st.columns([3, 1])
    with col1:
        new_display_value = st.number_input(
            f"{label} ({unit_label})",
            value=float(display_value),
            step=float(resolved_step),
            min_value=min_value,
            key=key,
            help=help_text or estimate.note,
        )
    with col2:
        st.markdown("<div style='margin-top:1.8rem'></div>" + confidence_badge(estimate.confidence), unsafe_allow_html=True)

    if estimate.note:
        st.caption(f"\u2139\ufe0f {estimate.note}")

    new_si_value = from_disp(new_display_value, unit_system)

    if abs(new_si_value - estimate.value) > 1e-9:
        return estimate.with_value(new_si_value)
    return estimate


def render_wastage_editor(wastage: WastageFactors) -> WastageFactors:
    st.caption("Adjust wastage/allowance percentages applied when converting MTO quantities into BOQ order quantities.")
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        concrete_pct = st.slider("Concrete wastage %", 0.0, 15.0, wastage.concrete_pct, 0.5)
        steel_pct = st.slider("Steel wastage %", 0.0, 15.0, wastage.steel_pct, 0.5)
    with c2:
        brick_block_pct = st.slider("Brick/block wastage %", 0.0, 15.0, wastage.brick_block_pct, 0.5)
        plaster_pct = st.slider("Plaster wastage %", 0.0, 20.0, wastage.plaster_pct, 0.5)
    with c3:
        formwork_pct = st.slider("Formwork wastage %", 0.0, 15.0, wastage.formwork_pct, 0.5)
        flooring_pct = st.slider("Flooring wastage %", 0.0, 15.0, wastage.flooring_pct, 0.5)
    with c4:
        paint_pct = st.slider("Paint wastage %", 0.0, 15.0, wastage.paint_pct, 0.5)
        misc_pct = st.slider("Misc/other wastage %", 0.0, 15.0, wastage.misc_pct, 0.5)

    return WastageFactors(
        concrete_pct=concrete_pct,
        steel_pct=steel_pct,
        brick_block_pct=brick_block_pct,
        plaster_pct=plaster_pct,
        formwork_pct=formwork_pct,
        flooring_pct=flooring_pct,
        paint_pct=paint_pct,
        misc_pct=misc_pct,
    )


def render_rate_editor(rate_book: Dict[str, MaterialRate]) -> Dict[str, MaterialRate]:
    st.caption(
        "Rates are stored per cft / sft / kg (standard Pakistani market convention) and are "
        "automatically converted to an equivalent per-m3/per-m2 rate in the BOQ if you selected "
        "the SI unit system. Edit the Rate column below to match current local supplier quotes."
    )
    df = pd.DataFrame(
        [
            {"Item Code": r.item_code, "Description": r.description, "Unit": r.unit, "Category": r.category, "Rate": r.rate}
            for r in rate_book.values()
        ]
    )
    edited = st.data_editor(
        df,
        key="rate_editor",
        num_rows="fixed",
        use_container_width=True,
        hide_index=True,
        column_config={
            "Item Code": st.column_config.TextColumn(disabled=True),
            "Description": st.column_config.TextColumn(disabled=True),
            "Unit": st.column_config.TextColumn(disabled=True),
            "Category": st.column_config.TextColumn(disabled=True),
            "Rate": st.column_config.NumberColumn(min_value=0.0, step=1.0, format="%.2f"),
        },
    )
    updated: Dict[str, MaterialRate] = {}
    for _, row in edited.iterrows():
        code = row["Item Code"]
        original = rate_book[code]
        updated[code] = MaterialRate(
            item_code=code,
            description=original.description,
            unit=original.unit,
            category=original.category,
            rate=float(row["Rate"]),
        )
    return updated
