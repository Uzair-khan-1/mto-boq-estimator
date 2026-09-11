"""
CostLens visual theme: CSS injection + small branded UI helpers layered on
top of the native Streamlit theme (.streamlit/config.toml). Kept in its own
module so app.py stays focused on app flow, not styling.

Everything here is additive and defensive:
- Selectors target stable `data-testid` attributes, not Streamlit's
  auto-generated/versioned class names, so a Streamlit upgrade that
  changes internal class names won't break this.
- If a selector ever stops matching in some version, the app just falls
  back to plain Streamlit styling - nothing here is load-bearing for
  functionality, only for visual polish.
- No JS, no external component libraries - pure CSS injected via
  st.markdown(unsafe_allow_html=True), which is the one supported
  "custom styling" escape hatch within Streamlit's platform limits.
"""
from __future__ import annotations

import base64

import streamlit as st

import config

_CSS = f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Outfit:wght@400;500;600;700;800&display=swap');

html, body, [class*="css"] {{
    font-family: 'Outfit', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
}}

/* ---------------------------------------------------------------- *
 * Force the light palette EVEN IF Streamlit resolves to its own dark
 * theme (e.g. a viewer's browser is in dark mode, or they picked "Dark"
 * / "Use system setting" in the app's own Settings menu - both override
 * .streamlit/config.toml on a per-viewer basis and are a common reason a
 * Streamlit app can look "flat black with white text" even though its
 * config says base="light"). Overriding Streamlit's own CSS variables at
 * the root - not just individual elements - is what makes every native
 * widget resolve correctly regardless of that per-viewer setting.
 * ---------------------------------------------------------------- */
:root, .stApp, [data-theme="dark"], [data-theme="light"] {{
    --background-color: {config.BRAND_BG} !important;
    --secondary-background-color: {config.BRAND_CARD} !important;
    --text-color: {config.BRAND_TEXT} !important;
    --primary-color: {config.BRAND_TEAL} !important;
}}
html, body, .stApp,
[data-testid="stAppViewContainer"],
[data-testid="stHeader"],
[data-testid="stBottomBlockContainer"],
[data-testid="stMain"] {{
    background-color: {config.BRAND_BG} !important;
}}
[data-testid="stAppViewContainer"] > .main {{
    background: linear-gradient(180deg, {config.BRAND_BG} 0%, {config.BRAND_CARD} 360px);
}}
/* Body text: everything defaults to the softer slate ink, not
   Streamlit's own dark-mode white - headings/sidebar override this below. */
p, span, label, li, div, .stMarkdown, [data-testid="stMarkdownContainer"],
[data-testid="stMetricLabel"], [data-testid="stMetricValue"], [data-testid="stCaptionContainer"] {{
    color: {config.BRAND_TEXT};
}}

/* ---------------------------------------------------------------- *
 * Inputs (text/number/select/textarea/file-uploader) - forced to a
 * white "card" look so they never inherit a dark fallback either.
 * ---------------------------------------------------------------- */
[data-baseweb="input"], [data-baseweb="select"] > div, [data-baseweb="textarea"],
[data-baseweb="base-input"],
[data-testid="stFileUploaderDropzone"],
[data-testid="stTextInput"] input, [data-testid="stNumberInput"] input {{
    background-color: {config.BRAND_CARD} !important;
    color: {config.BRAND_TEXT} !important;
    border-radius: 8px !important;
    border-color: rgba(11, 30, 61, 0.18) !important;
}}
[data-testid="stDataFrame"], [data-testid="stTable"] {{
    background-color: {config.BRAND_CARD} !important;
    border-radius: 12px;
    overflow: hidden;
    box-shadow: 0 2px 10px rgba(11, 30, 61, 0.05);
}}

/* ---------------------------------------------------------------- *
 * Hero header banner (top of every step)
 * ---------------------------------------------------------------- */
.cl-hero {{
    display: flex;
    align-items: center;
    gap: 18px;
    padding: 18px 26px;
    margin: -1rem -1rem 1.5rem -1rem;
    background: linear-gradient(120deg, {config.BRAND_NAVY} 0%, {config.BRAND_NAVY_LIGHT} 100%);
    border-radius: 0 0 18px 18px;
    box-shadow: 0 6px 24px rgba(11, 30, 61, 0.18);
}}
.cl-hero img {{ height: 46px; display: block; }}
.cl-hero-text h1 {{
    color: #FFFFFF !important;
    font-size: 1.5rem !important;
    font-weight: 800 !important;
    margin: 0 !important;
    letter-spacing: -0.01em;
}}
.cl-hero-text p {{
    color: {config.BRAND_TEAL_BRIGHT} !important;
    font-size: 0.8rem !important;
    letter-spacing: 0.13em;
    text-transform: uppercase;
    margin: 2px 0 0 0 !important;
    font-weight: 600;
}}

/* ---------------------------------------------------------------- *
 * Headings
 * ---------------------------------------------------------------- */
h1, h2, h3 {{ color: {config.BRAND_NAVY}; font-weight: 700; }}

/* ---------------------------------------------------------------- *
 * Buttons - explicit background/text on EVERY variant (not just
 * primary), so a secondary button never falls back to Streamlit's own
 * dark-mode default (dark button + white text, which is what "Now:
 * Accent/Button = White" in a black UI usually means in practice).
 * ---------------------------------------------------------------- */
.stButton > button,
.stDownloadButton > button,
[data-testid="stFormSubmitButton"] button,
[data-testid="stBaseButton-secondary"] {{
    background-color: {config.BRAND_CARD} !important;
    color: {config.BRAND_NAVY} !important;
    border-radius: 10px;
    font-weight: 600;
    border: 1.5px solid rgba(11, 30, 61, 0.18) !important;
    transition: transform 0.06s ease-in-out, box-shadow 0.15s ease-in-out;
}}
.stButton > button:hover,
.stDownloadButton > button:hover,
[data-testid="stFormSubmitButton"] button:hover {{
    transform: translateY(-1px);
    box-shadow: 0 4px 14px rgba(13, 148, 136, 0.25);
    border-color: {config.BRAND_TEAL} !important;
    color: {config.BRAND_TEAL} !important;
}}
.stButton > button[kind="primary"],
[data-testid="stFormSubmitButton"] button[kind="primary"],
[data-testid="stBaseButton-primary"] {{
    background: linear-gradient(120deg, {config.BRAND_TEAL} 0%, #0F766E 100%) !important;
    border: none !important;
    color: #FFFFFF !important;
}}
.stButton > button[kind="primary"]:hover,
[data-testid="stBaseButton-primary"]:hover {{
    color: #FFFFFF !important;
    box-shadow: 0 4px 14px rgba(13, 148, 136, 0.4);
}}

/* ---------------------------------------------------------------- *
 * Metric cards (Step 4 procurement summary + Step 5 cost summary both
 * render exactly 3 st.metric()s in a row - nth-of-type gives each a
 * distinct accent color: teal (informational) -> gold (subtotal-ish/
 * highlight) -> orange (the final/grand-total figure), a small but
 * genuinely useful "construction orange" accent rather than a random one.
 * ---------------------------------------------------------------- */
[data-testid="stMetric"] {{
    background: {config.BRAND_CARD};
    border: 1px solid rgba(11, 30, 61, 0.08);
    border-left: 4px solid {config.BRAND_TEAL};
    border-radius: 12px;
    padding: 14px 18px;
    box-shadow: 0 2px 10px rgba(11, 30, 61, 0.06);
}}
[data-testid="column"]:nth-of-type(2) [data-testid="stMetric"] {{ border-left-color: {config.BRAND_GOLD}; }}
[data-testid="column"]:nth-of-type(3) [data-testid="stMetric"] {{ border-left-color: {config.BRAND_ORANGE}; }}
[data-testid="stMetricLabel"] {{ color: {config.BRAND_NAVY}; font-weight: 600; }}
[data-testid="stMetricValue"] {{ color: {config.BRAND_NAVY}; }}

/* ---------------------------------------------------------------- *
 * Expanders (Steps 3 / 4 / 5 rely on these heavily) + generic bordered
 * containers (st.container(border=True)) - the "white card, soft
 * shadow, 12px radius" treatment, applied consistently everywhere a
 * card-like grouping appears.
 * ---------------------------------------------------------------- */
[data-testid="stExpander"],
[data-testid="stVerticalBlockBorderWrapper"] {{
    background: {config.BRAND_CARD};
    border: 1px solid rgba(11, 30, 61, 0.08);
    border-radius: 12px;
    box-shadow: 0 1px 8px rgba(11, 30, 61, 0.05);
}}
[data-testid="stExpander"] summary {{ color: {config.BRAND_NAVY}; font-weight: 600; }}

/* ---------------------------------------------------------------- *
 * Sidebar logo (st.logo) - Streamlit renders this quite small by
 * default (~24-32px tall) regardless of the source image's actual
 * resolution. Force it larger here so it reads clearly; `size="large"`
 * is passed in app.py too for versions that support that parameter,
 * but this CSS is what actually guarantees the size across versions.
 * ---------------------------------------------------------------- */
[data-testid="stSidebarHeader"] {{
    padding-top: 1rem !important;
    padding-bottom: 0.75rem !important;
    align-items: center !important;
}}
[data-testid="stSidebarHeader"] img,
[data-testid="stLogo"],
[data-testid="stLogo"] img,
.stLogo,
.stLogo img {{
    height: 3.2rem !important;
    max-height: none !important;
    width: auto !important;
}}

/* ---------------------------------------------------------------- *
 * Sidebar
 * ---------------------------------------------------------------- */
[data-testid="stSidebar"] {{
    background: linear-gradient(180deg, {config.BRAND_NAVY} 0%, {config.BRAND_NAVY_LIGHT} 100%);
}}
[data-testid="stSidebar"] * {{ color: #E8EEF5 !important; }}
[data-testid="stSidebar"] hr {{ border-color: rgba(255, 255, 255, 0.15); }}
/* A solid teal fill reads far better against the navy sidebar than a
   near-transparent white tint (which is what makes a dark UI's buttons
   look like flat white-on-black with no real accent color). */
[data-testid="stSidebar"] .stButton > button {{
    background: {config.BRAND_TEAL} !important;
    border: none !important;
    color: #FFFFFF !important;
    font-weight: 700;
}}
[data-testid="stSidebar"] .stButton > button:hover {{
    background: {config.BRAND_TEAL_BRIGHT} !important;
    color: {config.BRAND_NAVY} !important;
    box-shadow: 0 4px 14px rgba(45, 212, 191, 0.35);
}}

/* ---------------------------------------------------------------- *
 * Disclaimer captions - a subtle construction-orange left border marks
 * them as "read this", distinct from ordinary gray captions elsewhere.
 * Applied via the .cl-disclaimer helper class (see app.py) rather than
 * a blanket caption selector, since not every caption is a disclaimer.
 * ---------------------------------------------------------------- */
.cl-disclaimer {{
    display: block;
    border-left: 3px solid {config.BRAND_ORANGE};
    padding: 4px 10px;
    border-radius: 0 6px 6px 0;
    background: rgba(249, 115, 22, 0.08);
    font-size: 0.78rem;
    opacity: 0.95;
}}
[data-testid="stSidebar"] .cl-disclaimer {{
    background: rgba(249, 115, 22, 0.14);
    color: #FFE8D9 !important;
}}

/* ---------------------------------------------------------------- *
 * Sidebar step tracker (replaces the plain emoji checklist)
 * ---------------------------------------------------------------- */
.cl-step {{
    display: flex;
    align-items: center;
    gap: 10px;
    padding: 7px 10px;
    border-radius: 8px;
    margin-bottom: 4px;
    font-size: 0.88rem;
}}
.cl-step-done {{ opacity: 0.6; }}
.cl-step-current {{
    background: rgba(45, 212, 191, 0.16);
    border: 1px solid rgba(45, 212, 191, 0.4);
    font-weight: 700 !important;
}}
.cl-step-upcoming {{ opacity: 0.4; }}
.cl-step-dot {{
    display: inline-flex;
    align-items: center;
    justify-content: center;
    width: 20px;
    height: 20px;
    border-radius: 50%;
    font-size: 0.72rem;
    font-weight: 700;
    flex-shrink: 0;
}}
.cl-step-done .cl-step-dot {{ background: {config.BRAND_TEAL}; color: #FFFFFF; }}
.cl-step-current .cl-step-dot {{ background: {config.BRAND_GOLD}; color: {config.BRAND_NAVY}; }}
.cl-step-upcoming .cl-step-dot {{ background: rgba(255, 255, 255, 0.15); color: #E8EEF5; }}
</style>
"""


def inject_theme() -> None:
    """Injects the CostLens CSS. Safe to call on every rerun - it's purely
    additive and idempotent (re-injecting the same <style> block has no
    side effects)."""
    st.markdown(_CSS, unsafe_allow_html=True)


def render_hero() -> None:
    """Branded header banner (logo + wordmark + tagline) shown above every
    step's content. Degrades to a text-only banner if the logo PNG is
    missing (e.g. assets/generate_logo.py hasn't been run in a fork)."""
    logo_html = ""
    try:
        with open(config.LOGO_ICON_PATH, "rb") as fh:
            b64 = base64.b64encode(fh.read()).decode("ascii")
        logo_html = f'<img src="data:image/png;base64,{b64}" alt="{config.APP_NAME} logo" />'
    except OSError:
        pass

    st.markdown(
        f"""
        <div class="cl-hero">
            {logo_html}
            <div class="cl-hero-text">
                <h1>{config.APP_NAME}</h1>
                <p>{config.APP_TAGLINE}</p>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_sidebar_steps(step_labels: list[str], current_step: int) -> None:
    """Branded HTML/CSS step tracker for the sidebar. Read-only by design -
    the wizard advances via its own Continue/Back buttons, not by clicking
    a step here."""
    rows = []
    for i, label in enumerate(step_labels, start=1):
        if current_step > i:
            state, dot = "cl-step-done", "✓"
        elif current_step == i:
            state, dot = "cl-step-current", str(i)
        else:
            state, dot = "cl-step-upcoming", str(i)
        rows.append(f'<div class="cl-step {state}"><span class="cl-step-dot">{dot}</span><span>{label}</span></div>')
    st.markdown("\n".join(rows), unsafe_allow_html=True)
