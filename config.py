"""
App-wide configuration and constants.

Reads secrets in this order of priority:
1. Streamlit secrets (st.secrets) - used on Streamlit Community Cloud
2. Environment variable
3. User-entered value in the sidebar at runtime (handled in app.py, not here)
"""
from __future__ import annotations

import os

APP_NAME = "AI Residential MTO/BOQ Estimator"
APP_VERSION = "0.2.0-mvp"

# Groq model IDs. Kept in one place so they're easy to bump as Groq
# updates its free-tier vision-capable model lineup.
GROQ_VISION_MODEL = "qwen/qwen3.6-27b"
GROQ_TEXT_MODEL = "openai/gpt-oss-120b"

# Max dimension (px) we resize any page/image to before sending to Groq.
# Keeps base64 payloads small and inference fast/cheap.
MAX_IMAGE_DIMENSION = 1600

# Default currency for the rate book / cost estimate.
DEFAULT_CURRENCY = "PKR"
DEFAULT_CURRENCY_SYMBOL = "PKR "

# Default unit system shown on a fresh project ("SI" or "FPS" - see
# models.schemas.UnitSystem). The user can switch this per-project in
# Step 1; every internal calculation stays in SI regardless of this
# setting (see utils/units.py).
DEFAULT_UNIT_SYSTEM = "SI"

# Rate book provenance note shown in the UI (Step 5) and in exports, so
# users know how current/local the shipped default rates are.
RATE_BOOK_AS_OF = "September 2026"
RATE_BOOK_NOTE = (
    "Default rates are indicative Pakistani market rates (as of "
    f"{RATE_BOOK_AS_OF}), built up from published material prices "
    "(cement, steel, sand, crush, bricks, plaster, paint) plus standard "
    "nominal-mix/labour allowances - NOT a live feed and NOT city- or "
    "supplier-specific. Always override with your own current, local "
    "quotations before relying on the cost estimate."
)

# Supported upload types
SUPPORTED_FILE_TYPES = ["pdf", "png", "jpg", "jpeg"]

# Confidence levels used throughout the app (AI extraction + calculations)
CONFIDENCE_LEVELS = ["High", "Medium", "Low"]

# Full disclaimer - used in the Excel/PDF exports, where a complete,
# unambiguous legal caveat belongs in the deliverable itself.
DISCLAIMER_TEXT = (
    "This tool generates a PRELIMINARY, indicative Material Take-Off (MTO), "
    "Bill of Quantities (BOQ), and cost estimate using standard engineering "
    "thumb rules applied to AI-assisted drawing interpretation. It is NOT a "
    "structural design, NOT a certified quantity surveyor's estimate, and "
    "MUST NOT be used for tendering, construction, financing, or legal "
    "purposes without independent review and sign-off by a licensed "
    "structural engineer / qualified quantity surveyor. Always verify "
    "AI-extracted dimensions against the actual approved drawings."
)

# Short version shown in the Streamlit UI itself (sidebar / Step 5) as a
# low-key caption rather than a large warning banner - the full legal
# text above still appears in every exported Excel/PDF.
DISCLAIMER_TEXT_SHORT = (
    "Preliminary, AI-assisted estimate - not a certified structural or QS "
    "estimate. Verify before tendering, construction, or financing."
)


def get_secret(key: str, default: str | None = None) -> str | None:
    """Fetch a secret from Streamlit secrets first, then environment vars."""
    try:
        import streamlit as st

        if hasattr(st, "secrets") and key in st.secrets:
            return st.secrets[key]
    except Exception:
        pass
    return os.environ.get(key, default)
