"""
Unit conversion utilities for SI <-> FPS (feet-pound-second / Pakistani
construction industry practice) display.

CRITICAL DESIGN RULE: engineering/calculations.py ALWAYS works internally in
SI units (meters, sqm, m3, kg) - none of that code changes based on unit
system. This module only converts values at the UI edges:
  - when the user types a dimension into an input field (display -> SI)
  - when a computed quantity/rate is shown or exported (SI -> display)

This keeps the calculation engine simple and auditable regardless of which
unit system the user picks, and avoids ever needing two parallel sets of
engineering formulas.

Unit conventions used for FPS ("Imperial") display, matching common
Pakistani/subcontinent construction practice:
  - Large/running dimensions (lengths, heights, spans)      -> feet (ft)
  - Cross-section / thickness dimensions (column b x d,      -> inches (in)
    beam b x d, wall thickness, slab thickness)
  - Areas (plinth area, plaster area, wall area, etc.)       -> square feet (sft)
  - Volumes (concrete, excavation, masonry, mortar)          -> cubic feet (cft)
  - Counts (footing/column/beam count, doors, windows,       -> unchanged (Nos)
    masonry units)
  - Steel reinforcement weight                                -> unchanged (kg)
    (kg is standard market practice for rebar even in
    FPS-based Pakistani estimation - it is never quoted in
    lb on site, so we deliberately do NOT convert this)
"""
from __future__ import annotations

M_PER_FT = 0.3048
M_PER_INCH = 0.0254
FT_PER_M = 1.0 / M_PER_FT
INCH_PER_M = 1.0 / M_PER_INCH
SFT_PER_M2 = 10.763910417
CFT_PER_M3 = 35.314666721

SI = "SI"
FPS = "FPS"


# --------------------------------------------------------------------------
# Single-value conversions (used by editable Estimate input widgets)
# --------------------------------------------------------------------------


def length_to_display(value_m: float, unit_system: str) -> float:
    """Running dimensions (lengths, heights, spans): m -> ft for FPS."""
    return value_m * FT_PER_M if unit_system == FPS else value_m


def length_from_display(value_disp: float, unit_system: str) -> float:
    return value_disp * M_PER_FT if unit_system == FPS else value_disp


def thickness_to_display(value_m: float, unit_system: str) -> float:
    """Cross-section / thickness dimensions: m -> inches for FPS."""
    return value_m * INCH_PER_M if unit_system == FPS else value_m


def thickness_from_display(value_disp: float, unit_system: str) -> float:
    return value_disp * M_PER_INCH if unit_system == FPS else value_disp


def area_to_display(value_sqm: float, unit_system: str) -> float:
    return value_sqm * SFT_PER_M2 if unit_system == FPS else value_sqm


def area_from_display(value_disp: float, unit_system: str) -> float:
    return value_disp / SFT_PER_M2 if unit_system == FPS else value_disp


def length_unit_label(unit_system: str) -> str:
    return "ft" if unit_system == FPS else "m"


def thickness_unit_label(unit_system: str) -> str:
    return "in" if unit_system == FPS else "m"


def area_unit_label(unit_system: str) -> str:
    return "sft" if unit_system == FPS else "sqm"


def volume_unit_label(unit_system: str) -> str:
    return "cft" if unit_system == FPS else "m3"


# --------------------------------------------------------------------------
# MTO/BOQ quantity conversion (SI quantity+unit -> display quantity+unit)
# --------------------------------------------------------------------------


def convert_quantity_unit(quantity: float, unit: str, unit_system: str) -> tuple[float, str]:
    """Convert a computed MTO/BOQ line item's SI quantity for display.

    Only m3 -> cft and m2 -> sft change. kg (steel), Nos (counts), and LS
    (lump-sum) are unit-system-agnostic and pass through unchanged.
    """
    if unit_system != FPS:
        return quantity, unit
    if unit == "m3":
        return quantity * CFT_PER_M3, "cft"
    if unit == "m2":
        return quantity * SFT_PER_M2, "sft"
    return quantity, unit
