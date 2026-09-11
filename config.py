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
APP_VERSION = "0.1.0-mvp"

# Groq model IDs. Kept in one place so they're easy to bump as Groq
# updates its free-tier vision-capable model lineup.
GROQ_VISION_MODEL = "meta-llama/llama-4-scout-17b-16e-instruct"
GROQ_TEXT_MODEL = "llama-3.3-70b-versatile"

# Max dimension (px) we resize any page/image to before sending to Groq.
# Keeps base64 payloads small and inference fast/cheap.
MAX_IMAGE_DIMENSION = 1600

# Default currency for the rate book / cost estimate.
DEFAULT_CURRENCY = "PKR"
DEFAULT_CURRENCY_SYMBOL = "Rs. "

# Supported upload types
SUPPORTED_FILE_TYPES = ["pdf", "png", "jpg", "jpeg"]

# Confidence levels used throughout the app (AI extraction + calculations)
CONFIDENCE_LEVELS = ["High", "Medium", "Low"]

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


def get_secret(key: str, default: str | None = None) -> str | None:
    """Fetch a secret from Streamlit secrets first, then environment vars."""
    try:
        import streamlit as st

        if hasattr(st, "secrets") and key in st.secrets:
            return st.secrets[key]
    except Exception:
        pass
    return os.environ.get(key, default)
