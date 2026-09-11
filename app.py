"""
AI Residential MTO/BOQ Estimator - Streamlit entrypoint.

A 5-step wizard:
  1. Project setup (technical inputs) + drawing upload
  2. AI drawing interpretation (Groq) -> structured JSON
  3. User verification/edit of every AI-extracted parameter
  4. Deterministic MTO calculation + traceability breakdown
  5. BOQ (rates + wastage) + cost estimate + Excel/PDF export

See README.md for the full architecture rationale.
"""
from __future__ import annotations

from io import BytesIO

import streamlit as st
from PIL import Image

import config
from ai.extraction import default_building_params, extract_building_params
from drawing_processing.image_processor import clean_drawing_image, estimate_is_drawing_like
from drawing_processing.ocr_engine import build_ocr_hint_text, ocr_available
from drawing_processing.pdf_processor import process_pdf
from engineering import rules
from export.excel_export import build_excel_workbook
from export.pdf_export import build_pdf_report
from models.schemas import ConfidenceLevel, ProjectInputs
from mto_boq.boq_generator import boq_to_dataframe, cost_by_category, generate_boq
from mto_boq.mto_generator import compute_reinforcement_summary, generate_mto, group_by_category, mto_to_dataframe
from ui.components import confidence_badge, render_estimate_input, render_rate_editor, render_wastage_editor
from ui.state import go_to_step, init_session_state, reset_project

st.set_page_config(page_title=config.APP_NAME, page_icon="\U0001f3d7\ufe0f", layout="wide")
init_session_state()

STEP_LABELS = ["1. Project Setup", "2. AI Analysis", "3. Verify Data", "4. MTO", "5. BOQ & Export"]

# ---------------------------------------------------------------------------
# Sidebar
# ---------------------------------------------------------------------------
with st.sidebar:
    st.title(config.APP_NAME)
    st.caption(f"v{config.APP_VERSION} \u00b7 MVP")

    st.session_state["groq_api_key"] = config.get_secret("GROQ_API_KEY", "")

    st.markdown("---")
    st.markdown("### Progress")
    for i, label in enumerate(STEP_LABELS, start=1):
        marker = "\u2705" if st.session_state["step"] > i else ("\u27a1\ufe0f" if st.session_state["step"] == i else "\u2b1c")
        st.markdown(f"{marker} {label}")

    st.markdown("---")
    if st.button("\U0001f504 Start New Project", use_container_width=True):
        reset_project()
        st.rerun()

    st.markdown("---")
    st.warning(config.DISCLAIMER_TEXT, icon="\u26a0\ufe0f")


# ---------------------------------------------------------------------------
# STEP 1 — Project setup + upload
# ---------------------------------------------------------------------------
def step_1():
    st.header("Step 1 \u00b7 Project Setup & Drawing Upload")
    st.write("Enter basic project details and upload a simple residential drawing (plan, structural layout, or section).")

    pi: ProjectInputs = st.session_state["project_inputs"]

    with st.form("project_setup_form"):
        c1, c2 = st.columns(2)
        with c1:
            project_name = st.text_input("Project Name", pi.project_name)
            client_name = st.text_input("Client Name (optional)", pi.client_name)
            location = st.text_input("Location / City", pi.location)
            soil_type = st.selectbox(
                "Soil Type", list(rules.SOIL_SIDE_SLOPE_FACTOR.keys()),
                index=list(rules.SOIL_SIDE_SLOPE_FACTOR.keys()).index(pi.soil_type) if pi.soil_type in rules.SOIL_SIDE_SLOPE_FACTOR else 1,
            )
            finish_level = st.selectbox("Finish Level", ["Basic", "Standard", "Premium"], index=["Basic", "Standard", "Premium"].index(pi.finish_level))
        with c2:
            concrete_grade = st.selectbox("Concrete Grade (structural members)", list(rules.CONCRETE_GRADE_NOMINAL_MIX.keys()), index=2)
            pcc_grade = st.selectbox("PCC Grade", ["M7.5", "M10", "M15"], index=1)
            steel_grade = st.selectbox("Steel Grade", ["Fe415", "Fe500", "Fe550"], index=1)
            wall_material = st.selectbox("Wall Material", list(rules.MASONRY_UNIT_SIZES_M.keys()))
            wall_thickness_mm = st.selectbox("Wall Thickness (mm)", [100, 115, 150, 200, 230], index=4)

        st.markdown("##### Finishes & scope toggles")
        t1, t2, t3, t4, t5 = st.columns(5)
        include_flooring = t1.checkbox("Flooring", value=pi.include_flooring)
        include_waterproofing = t2.checkbox("Waterproofing", value=pi.include_waterproofing)
        include_painting = t3.checkbox("Painting", value=pi.include_painting)
        include_dpc = t4.checkbox("DPC", value=pi.include_dpc)
        include_anti_termite = t5.checkbox("Anti-termite", value=pi.include_anti_termite)

        contingency_pct = st.slider("Contingency % (on total cost)", 0.0, 20.0, pi.contingency_pct, 0.5)

        st.markdown("##### Drawing Upload")
        uploaded = st.file_uploader("Upload drawing (PDF, PNG, or JPG)", type=config.SUPPORTED_FILE_TYPES)

        submitted = st.form_submit_button("Continue to AI Analysis \u2192", use_container_width=True, type="primary")

    if submitted:
        st.session_state["project_inputs"] = ProjectInputs(
            project_name=project_name or "Untitled Project",
            client_name=client_name,
            location=location,
            soil_type=soil_type,
            concrete_grade_footing=concrete_grade,
            concrete_grade_column=concrete_grade,
            concrete_grade_beam=concrete_grade,
            concrete_grade_slab=concrete_grade,
            pcc_grade=pcc_grade,
            steel_grade=steel_grade,
            wall_material=wall_material,
            wall_thickness_mm=wall_thickness_mm,
            finish_level=finish_level,
            include_flooring=include_flooring,
            include_waterproofing=include_waterproofing,
            include_painting=include_painting,
            include_dpc=include_dpc,
            include_anti_termite=include_anti_termite,
            contingency_pct=contingency_pct,
        )
        if uploaded is not None:
            st.session_state["uploaded_file_bytes"] = uploaded.getvalue()
            st.session_state["uploaded_file_name"] = uploaded.name
        go_to_step(2)
        st.rerun()


# ---------------------------------------------------------------------------
# STEP 2 — AI analysis
# ---------------------------------------------------------------------------
def _load_images_from_upload() -> list[Image.Image]:
    file_bytes = st.session_state.get("uploaded_file_bytes")
    file_name = st.session_state.get("uploaded_file_name") or ""
    if not file_bytes:
        return []

    images: list[Image.Image] = []
    if file_name.lower().endswith(".pdf"):
        result = process_pdf(file_bytes, dpi=200, max_pages=3)
        images = [p.image for p in result.pages]
    else:
        images = [Image.open(BytesIO(file_bytes))]
    return [clean_drawing_image(img) for img in images]


def step_2():
    st.header("Step 2 \u00b7 AI Drawing Analysis")

    if not st.session_state.get("uploaded_file_bytes"):
        st.info("No drawing was uploaded. You can go back to upload one, or skip straight to manual entry with standard defaults.")
        if st.button("\u2190 Back to Step 1"):
            go_to_step(1)
            st.rerun()
        if st.button("Skip AI \u2014 enter parameters manually", type="primary"):
            st.session_state["extracted_params"] = default_building_params()
            st.session_state["used_ai"] = False
            go_to_step(3)
            st.rerun()
        return

    if "uploaded_images" not in st.session_state or not st.session_state["uploaded_images"]:
        with st.spinner("Processing uploaded drawing..."):
            st.session_state["uploaded_images"] = _load_images_from_upload()

    images = st.session_state["uploaded_images"]
    st.write(f"**{len(images)} page/image(s)** processed from `{st.session_state['uploaded_file_name']}`")

    cols = st.columns(min(len(images), 4) or 1)
    for i, img in enumerate(images):
        with cols[i % len(cols)]:
            st.image(img, caption=f"Page {i+1}", use_container_width=True)
            if not estimate_is_drawing_like(img):
                st.caption("\u26a0\ufe0f This doesn't look like a typical line drawing \u2014 results may be unreliable.")

    if ocr_available():
        with st.expander("OCR text hints (used to help the AI, not for calculations)"):
            if not st.session_state.get("ocr_hint_text"):
                with st.spinner("Running OCR..."):
                    hints = [build_ocr_hint_text(img) for img in images]
                    st.session_state["ocr_hint_text"] = "\n".join(h for h in hints if h)
            st.text(st.session_state["ocr_hint_text"] or "No text detected.")
    else:
        st.caption("OCR engine not available in this environment \u2014 proceeding with vision-only AI analysis.")

    project_context = st.text_area(
        "Additional context for the AI (optional)",
        placeholder="e.g. 'This is a G+1 house, footings are isolated RCC pad footings, drawing is not to exact scale...'",
    )

    c1, c2 = st.columns(2)
    with c1:
        analyze_clicked = st.button("\U0001f9e0 Analyze with Groq AI", type="primary", use_container_width=True)
    with c2:
        skip_clicked = st.button("Skip AI \u2014 use standard defaults", use_container_width=True)

    if skip_clicked:
        st.session_state["extracted_params"] = default_building_params()
        st.session_state["used_ai"] = False
        go_to_step(3)
        st.rerun()

    if analyze_clicked:
        if not st.session_state["groq_api_key"]:
            st.error("AI analysis is currently unavailable. Please use 'Skip AI — use standard defaults' below, or contact the site administrator.")
        else:
            with st.spinner("Calling Groq vision model to interpret the drawing... this can take up to ~30s"):
                params, raw_text, errors = extract_building_params(
                    api_key=st.session_state["groq_api_key"],
                    images=images,
                    project_context=project_context,
                    ocr_hint=st.session_state.get("ocr_hint_text", ""),
                )
            st.session_state["extracted_params"] = params
            st.session_state["raw_ai_response"] = raw_text
            st.session_state["ai_errors"] = errors
            st.session_state["used_ai"] = True
            go_to_step(3)
            st.rerun()

    if st.button("\u2190 Back to Step 1"):
        go_to_step(1)
        st.rerun()


# ---------------------------------------------------------------------------
# STEP 3 — Verification / edit
# ---------------------------------------------------------------------------
def step_3():
    st.header("Step 3 \u00b7 Verify & Edit Extracted Parameters")
    params = st.session_state["extracted_params"]

    if st.session_state.get("ai_errors"):
        for e in st.session_state["ai_errors"]:
            st.error(e)

    if st.session_state.get("used_ai") and params.extraction_warnings:
        with st.expander("\u26a0\ufe0f AI extraction warnings", expanded=True):
            for w in params.extraction_warnings:
                st.warning(w)

    if params.overall_notes:
        st.info(f"**AI notes:** {params.overall_notes}")

    legend = " ".join(confidence_badge(c) for c in [ConfidenceLevel.HIGH, ConfidenceLevel.MEDIUM, ConfidenceLevel.LOW])
    st.markdown(
        "Review every value below and edit anything that doesn't match your actual drawing. "
        f"Confidence levels: {legend}",
        unsafe_allow_html=True,
    )

    with st.expander("General", expanded=True):
        c1, c2 = st.columns(2)
        with c1:
            params.num_floors = render_estimate_input("Number of RCC slab levels (incl. roof)", params.num_floors, "num_floors_inp", "floors", step=1.0)
        with c2:
            params.plinth_area_per_floor_sqm = render_estimate_input("Plinth/built-up area per floor", params.plinth_area_per_floor_sqm, "plinth_area_inp", "sqm", step=1.0)

    with st.expander("Footings", expanded=True):
        params.footings.footing_type = st.selectbox("Footing type", ["isolated", "strip", "raft", "combined"], index=["isolated", "strip", "raft", "combined"].index(params.footings.footing_type))
        c1, c2, c3, c4 = st.columns(4)
        with c1:
            params.footings.count = render_estimate_input("Count", params.footings.count, "ftg_count", "nos", step=1.0)
        with c2:
            params.footings.length_m = render_estimate_input("Length", params.footings.length_m, "ftg_len", "m", step=0.05)
        with c3:
            params.footings.width_m = render_estimate_input("Width", params.footings.width_m, "ftg_wid", "m", step=0.05)
        with c4:
            params.footings.depth_m = render_estimate_input("Depth", params.footings.depth_m, "ftg_dep", "m", step=0.05)

    with st.expander("Columns", expanded=True):
        c1, c2, c3, c4 = st.columns(4)
        with c1:
            params.columns.count = render_estimate_input("Count", params.columns.count, "col_count", "nos", step=1.0)
        with c2:
            params.columns.width_m = render_estimate_input("Width (b)", params.columns.width_m, "col_b", "m", step=0.01)
        with c3:
            params.columns.depth_m = render_estimate_input("Depth (d)", params.columns.depth_m, "col_d", "m", step=0.01)
        with c4:
            params.columns.height_per_floor_m = render_estimate_input("Height/floor", params.columns.height_per_floor_m, "col_h", "m", step=0.05)

    with st.expander("Beams", expanded=True):
        c1, c2, c3, c4 = st.columns(4)
        with c1:
            params.beams.count = render_estimate_input("Count per level", params.beams.count, "beam_count", "nos", step=1.0)
        with c2:
            params.beams.avg_length_m = render_estimate_input("Avg length", params.beams.avg_length_m, "beam_len", "m", step=0.1)
        with c3:
            params.beams.width_m = render_estimate_input("Width", params.beams.width_m, "beam_w", "m", step=0.01)
        with c4:
            params.beams.depth_m = render_estimate_input("Depth", params.beams.depth_m, "beam_d", "m", step=0.01)

    with st.expander("Slabs", expanded=True):
        c1, c2 = st.columns(2)
        with c1:
            params.slabs.area_per_floor_sqm = render_estimate_input("Area per floor", params.slabs.area_per_floor_sqm, "slab_area", "sqm", step=1.0)
        with c2:
            params.slabs.thickness_m = render_estimate_input("Thickness", params.slabs.thickness_m, "slab_t", "m", step=0.005)

    with st.expander("Walls / Masonry", expanded=True):
        c1, c2, c3 = st.columns(3)
        with c1:
            params.walls.total_length_per_floor_m = render_estimate_input("Total wall length/floor", params.walls.total_length_per_floor_m, "wall_len", "m", step=0.5)
        with c2:
            params.walls.height_m = render_estimate_input("Wall height", params.walls.height_m, "wall_h", "m", step=0.05)
        with c3:
            params.walls.thickness_m = render_estimate_input("Wall thickness", params.walls.thickness_m, "wall_t", "m", step=0.01)
        params.walls.wall_material = st.selectbox(
            "Wall material", list(rules.MASONRY_UNIT_SIZES_M.keys()),
            index=list(rules.MASONRY_UNIT_SIZES_M.keys()).index(params.walls.wall_material) if params.walls.wall_material in rules.MASONRY_UNIT_SIZES_M else 0,
        )

    with st.expander("Openings (doors/windows)", expanded=True):
        c1, c2, c3, c4 = st.columns(4)
        with c1:
            params.openings.door_count_per_floor = render_estimate_input("Doors/floor", params.openings.door_count_per_floor, "door_count", "nos", step=1.0)
        with c2:
            params.openings.avg_door_area_sqm = render_estimate_input("Avg door area", params.openings.avg_door_area_sqm, "door_area", "sqm", step=0.05)
        with c3:
            params.openings.window_count_per_floor = render_estimate_input("Windows/floor", params.openings.window_count_per_floor, "win_count", "nos", step=1.0)
        with c4:
            params.openings.avg_window_area_sqm = render_estimate_input("Avg window area", params.openings.avg_window_area_sqm, "win_area", "sqm", step=0.05)

    st.session_state["extracted_params"] = params

    c1, c2 = st.columns(2)
    with c1:
        if st.button("\u2190 Back to Step 2"):
            go_to_step(2)
            st.rerun()
    with c2:
        if st.button("Confirm & Calculate MTO \u2192", type="primary", use_container_width=True):
            with st.spinner("Running deterministic engineering calculations..."):
                st.session_state["mto_items"] = generate_mto(params, st.session_state["project_inputs"])
            go_to_step(4)
            st.rerun()


# ---------------------------------------------------------------------------
# STEP 4 — MTO
# ---------------------------------------------------------------------------
def step_4():
    st.header("Step 4 \u00b7 Material Take-Off (MTO)")
    mto_items = st.session_state["mto_items"]

    summary = compute_reinforcement_summary(mto_items)
    badge_color = "green" if summary["status"] == "OK" else "orange"
    st.markdown(f":{badge_color}[**Steel sanity check:** {summary['message']}]")

    df = mto_to_dataframe(mto_items)
    st.dataframe(df, use_container_width=True, hide_index=True)

    st.markdown("##### Calculation breakdown / traceability")
    grouped = group_by_category(mto_items)
    for category, items in grouped.items():
        with st.expander(f"{category} ({len(items)} item{'s' if len(items) != 1 else ''})"):
            for item in items:
                st.markdown(f"**{item.item_code} \u2014 {item.description}**  {confidence_badge(item.confidence)}", unsafe_allow_html=True)
                st.write(f"Quantity: **{item.quantity:,.3f} {item.unit}**")
                st.caption(f"Formula: {item.formula}")
                if item.inputs_used:
                    st.caption("Inputs used: " + ", ".join(f"{k}={v}" for k, v in item.inputs_used.items()))
                for a in item.assumptions:
                    st.caption(f"\u2022 {a}")
                st.markdown("---")

    c1, c2 = st.columns(2)
    with c1:
        if st.button("\u2190 Back to Step 3 (edit parameters)"):
            go_to_step(3)
            st.rerun()
    with c2:
        if st.button("Continue to BOQ & Cost Estimate \u2192", type="primary", use_container_width=True):
            go_to_step(5)
            st.rerun()


# ---------------------------------------------------------------------------
# STEP 5 — BOQ & export
# ---------------------------------------------------------------------------
def step_5():
    st.header("Step 5 \u00b7 BOQ, Cost Estimate & Export")

    pi = st.session_state["project_inputs"]

    with st.expander("Wastage / allowance factors", expanded=False):
        st.session_state["wastage_factors"] = render_wastage_editor(st.session_state["wastage_factors"])

    with st.expander("Material & labour rates", expanded=False):
        st.session_state["rate_book"] = render_rate_editor(st.session_state["rate_book"])

    contingency_pct = st.slider("Contingency % (final)", 0.0, 20.0, pi.contingency_pct, 0.5)
    pi.contingency_pct = contingency_pct
    st.session_state["project_inputs"] = pi

    if st.button("\U0001f4b0 Generate BOQ & Cost Estimate", type="primary"):
        boq_items, cost_summary = generate_boq(
            mto_items=st.session_state["mto_items"],
            rate_book=st.session_state["rate_book"],
            wastage=st.session_state["wastage_factors"],
            project_inputs=pi,
        )
        st.session_state["boq_items"] = boq_items
        st.session_state["cost_summary"] = cost_summary

    if st.session_state.get("boq_items"):
        boq_items = st.session_state["boq_items"]
        cost_summary = st.session_state["cost_summary"]

        df = boq_to_dataframe(boq_items)
        st.dataframe(df, use_container_width=True, hide_index=True)

        m1, m2, m3 = st.columns(3)
        m1.metric("Subtotal", f"{config.DEFAULT_CURRENCY_SYMBOL}{cost_summary.subtotal:,.0f}")
        m2.metric(f"Contingency ({cost_summary.contingency_pct:.1f}%)", f"{config.DEFAULT_CURRENCY_SYMBOL}{cost_summary.contingency_amount:,.0f}")
        m3.metric("Grand Total", f"{config.DEFAULT_CURRENCY_SYMBOL}{cost_summary.grand_total:,.0f}")

        st.markdown("##### Cost by category")
        cat_df = cost_by_category(boq_items)
        if not cat_df.empty:
            st.bar_chart(cat_df.set_index("Category"))

        st.markdown("##### Export")
        e1, e2 = st.columns(2)
        with e1:
            excel_bytes = build_excel_workbook(
                pi, st.session_state["extracted_params"], st.session_state["mto_items"], boq_items, cost_summary
            )
            st.download_button(
                "\U0001f4c5 Download Excel (MTO + BOQ)",
                data=excel_bytes,
                file_name=f"{pi.project_name.replace(' ', '_')}_MTO_BOQ.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True,
            )
        with e2:
            pdf_bytes = build_pdf_report(
                pi, st.session_state["extracted_params"], st.session_state["mto_items"], boq_items, cost_summary
            )
            st.download_button(
                "\U0001f4c4 Download PDF Report",
                data=pdf_bytes,
                file_name=f"{pi.project_name.replace(' ', '_')}_Estimate_Report.pdf",
                mime="application/pdf",
                use_container_width=True,
            )

        st.warning(config.DISCLAIMER_TEXT, icon="\u26a0\ufe0f")

    if st.button("\u2190 Back to Step 4 (MTO)"):
        go_to_step(4)
        st.rerun()


# ---------------------------------------------------------------------------
# Router
# ---------------------------------------------------------------------------
step = st.session_state["step"]
if step == 1:
    step_1()
elif step == 2:
    step_2()
elif step == 3:
    step_3()
elif step == 4:
    step_4()
elif step == 5:
    step_5()
else:
    st.session_state["step"] = 1
    st.rerun()
