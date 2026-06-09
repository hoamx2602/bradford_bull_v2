"""Tier-3 EMV / pricing."""
from __future__ import annotations

from app.pipeline import pricing


def test_placement_multipliers():
    assert pricing.placement_multiplier("Live Broadcast TV") == 1.0
    assert pricing.placement_multiplier("Live Stream") == 0.85
    assert pricing.placement_multiplier("Highlight Clip") == 1.4
    assert pricing.placement_multiplier("Social Media") == 0.7
    assert pricing.placement_multiplier("unknown") == 1.0  # safe default


def test_emv_formula():
    # 10 quality-seconds, $20 CPM, 1,000,000 viewers, live (x1.0)
    # EMV = 10 * (20/1000) * 1_000_000 * 1.0 = 200_000
    emv = pricing.emv_for_logo(
        10.0, cpm_base=20.0, audience_size=1_000_000, placement_mult=1.0
    )
    assert emv == 200_000.0


def test_price_logos_fills_emv():
    logos = [{"_qualityRaw": 5.0}, {"_qualityRaw": 0.0}]
    mult = pricing.price_logos(
        logos, cpm_base=22.0, audience_size=2_000_000, placement_type="Live Stream"
    )
    assert mult == 0.85
    assert logos[0]["emvUsd"] == round(5.0 * 0.022 * 2_000_000 * 0.85, 2)
    assert logos[1]["emvUsd"] == 0.0
