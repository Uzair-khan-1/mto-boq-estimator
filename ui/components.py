"""
Reusable Streamlit widgets shared across app.py steps.
"""
from __future__ import annotations

from typing import Dict

import pandas as pd
import streamlit as st

from models.schemas import ConfidenceLevel, Estimate, MaterialRate, Source, WastageFactors

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


def render_estimate_input(
    label: str,
    estimate: Estimate,
    key: str,
    unit: str = "",
    step: float = 0.01,
    min_value: float = 0.0,
    help_text: str | None = None,
) -> Estimate:
    """Render one editable numeric field with its confidence badge + note,
    and return a (possibly updated) Estimate reflecting the user's edit.
    """
    col1, col2 = st.columns([3, 1])
    with col1:
        new_value = st.number_input(
            f"{label} ({unit})" if unit else label,
            value=float(estimate.value),
            step=step,
            min_value=min_value,
            key=key,
            help=help_text or estimate.note,
        )
    with col2:
        st.markdown("<div style='margin-top:1.8rem'></div>" + confidence_badge(estimate.confidence), unsafe_allow_html=True)

    if estimate.note:
        st.caption(f"\u2139\ufe0f {estimate.note}")

    if new_value != estimate.value:
        return estimate.with_value(new_value)
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
    st.caption("Edit unit rates below to match your local market before generating the final BOQ cost.")
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
