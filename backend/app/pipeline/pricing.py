"""Tier 3 — Equivalent Media Value (EMV).

Implements LOGOS_Exposure_Pricing_Algorithm.md §Tầng 3:

    EMV = quality_exposure_seconds
        x (CPM_base / 1000)
        x audience_size
        x placement_multiplier
        x category_multiplier
        x prime_time_multiplier

category and prime-time default to 1.0 here (they need a sponsor-category map and
a reliable match clock respectively); the hooks are left explicit so they can be
switched on without touching the formula.
"""
from __future__ import annotations

from app.config import get_settings

# Maps the frontend's placement labels (sent verbatim in the upload form) to
# multipliers from the pricing doc.
PLACEMENT_MULTIPLIERS: dict[str, float] = {
    "live broadcast tv": 1.00,
    "live stream": 0.85,
    "live stream online": 0.85,
    "highlight clip": 1.40,
    "highlight": 1.40,
    "social media": 0.70,
    "social media clip": 0.70,
}


def placement_multiplier(placement_type: str) -> float:
    return PLACEMENT_MULTIPLIERS.get(placement_type.strip().lower(), 1.0)


def emv_for_logo(
    quality_exposure_seconds: float,
    *,
    cpm_base: float,
    audience_size: int,
    placement_mult: float,
    category_mult: float = 1.0,
    prime_time_mult: float = 1.0,
) -> float:
    return (
        quality_exposure_seconds
        * (cpm_base / 1000.0)
        * audience_size
        * placement_mult
        * category_mult
        * prime_time_mult
    )


def price_logos(
    logos: list[dict],
    *,
    cpm_base: float,
    audience_size: int,
    placement_type: str,
) -> float:
    """Fill emvUsd on each logo in place; return placement multiplier used."""
    get_settings()  # reserved for future toggles (prime-time, category)
    p_mult = placement_multiplier(placement_type)
    for logo in logos:
        emv = emv_for_logo(
            logo["_qualityRaw"],
            cpm_base=cpm_base,
            audience_size=audience_size,
            placement_mult=p_mult,
        )
        logo["emvUsd"] = round(emv, 2)
    return p_mult
