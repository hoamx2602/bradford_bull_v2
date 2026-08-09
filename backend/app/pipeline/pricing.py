"""Tier 3 — time-normalised Equivalent Media Value (EMV).

Implements LOGOS_Exposure_Pricing_Algorithm.md §Tầng 3:

    EMV = (quality_exposure_seconds / reference_spot_seconds)
        x (CPM_base / 1000)
        x audience_size
        x placement_multiplier
        x category_multiplier
        x prime_time_multiplier

CPM is a cost per thousand *impressions*, not a cost per exposure-second.  The
division by a reference advertising slot is therefore required to make the
units consistent.  A 30-second slot is used because broadcast media costs are
commonly reported as 30-second commercial equivalents.  The quality exposure
already discounts the full media equivalent for size, position, clarity and
duration, so no additional unsupported global "sponsorship discount" is used.

Category and prime-time default to 1.0 here (they need a sponsor-category map
and a reliable match clock respectively); the hooks remain explicit.
"""
from __future__ import annotations

from app.config import get_settings


REFERENCE_SPOT_SECONDS = 30.0

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
    reference_spot_seconds: float = REFERENCE_SPOT_SECONDS,
) -> float:
    if reference_spot_seconds <= 0:
        raise ValueError("reference_spot_seconds must be greater than zero")
    return (
        (quality_exposure_seconds / reference_spot_seconds)
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
    reference_spot_seconds: float = REFERENCE_SPOT_SECONDS,
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
            reference_spot_seconds=reference_spot_seconds,
        )
        logo["emvUsd"] = round(emv, 2)
    return p_mult
