"""AI-percentage per kit location, recomputed from stored exposure facts.

The location breakdown table (Location | Logo | Human % | AI % | Human-AI %) needs
the **AI %** column to react instantly when the user ticks/unticks algorithm
criteria in Settings — without re-running detection. So instead of a single baked
visibility number, the pipeline persists each detection's Tier-1 factor components
(`facts_json`), and this module recomputes the per-zone quality share under any
chosen subset of factors.

AI % semantics mirror the existing body-zone breakdown: each anchor zone's share
of the total quality-weighted exposure attributed to zones (≈100 % across zones).
A configured Location inherits its mapped anchor's share; when several locations
share one anchor (close neck/back slots COCO-17 can't separate) the share is split
evenly between them so the column still totals ~100 %.
"""
from __future__ import annotations

from collections import defaultdict

from app.pipeline.exposure import _duration_weight

# The tickable criteria. `scope` documents where each factor acts; `affectsShare`
# flags whether toggling it actually changes the per-location AI % (placement is
# applied uniformly to every logo so it cancels out of a share; category/prime-time
# need maps/clock we don't persist yet, so they're listed for transparency but are
# no-ops for the share today).
AI_CRITERIA: list[dict] = [
    {"key": "size", "label": "Size Score", "scope": "per-frame", "affectsShare": True,
     "description": "sqrt(box area / frame area) — bigger logos count more."},
    {"key": "position", "label": "Position Score", "scope": "per-frame", "affectsShare": True,
     "description": "Gaussian centre weighting — centre of frame counts more than corners."},
    {"key": "clarity", "label": "Clarity (Confidence)", "scope": "per-frame", "affectsShare": True,
     "description": "Detector confidence — sharper / clearer logos count more."},
    {"key": "obb", "label": "OBB Penalty", "scope": "per-frame", "affectsShare": True,
     "description": "Angle penalty for tilted logos (1.0 on the current HBB model)."},
    {"key": "durationWeight", "label": "Duration Weight", "scope": "per-segment", "affectsShare": True,
     "description": "Longer continuous exposure is weighted up (0.5 / 1.0 / 1.2)."},
    {"key": "placement", "label": "Placement Multiplier", "scope": "per-video", "affectsShare": False,
     "description": "Broadcast-type multiplier — applied to all logos equally, so it does not change the share."},
    {"key": "category", "label": "Category (Share of Voice)", "scope": "per-brand", "affectsShare": False,
     "description": "Sponsor-category exclusivity multiplier (needs a category map; reserved)."},
    {"key": "primeTime", "label": "Prime-time Multiplier", "scope": "per-segment", "affectsShare": False,
     "description": "Start/end-of-match boost (needs a reliable match clock; reserved)."},
]

CRITERIA_KEYS = {c["key"] for c in AI_CRITERIA}


def _frame_weight(fact: dict, enabled: set[str]) -> float:
    """Product of the enabled per-frame factors for one detection (disabled = 1.0)."""
    w = 1.0
    if "size" in enabled:
        w *= fact.get("size", 1.0)
    if "position" in enabled:
        w *= fact.get("pos", 1.0)
    if "clarity" in enabled:
        w *= fact.get("clarity", 1.0)
    if "obb" in enabled:
        w *= fact.get("obb", 1.0)
    return w


def _zone_quality(facts: list[dict], enabled: set[str]) -> float:
    """Quality-weighted exposure for one zone's facts.

    Splits the zone's detections into time segments (gap > 2.5 sample intervals),
    then sums mean(frame_weight) × duration_weight × duration per segment — the
    same shape as exposure.aggregate, but with the recomputed per-frame weight.
    """
    if not facts:
        return 0.0
    facts = sorted(facts, key=lambda f: f.get("t", 0.0))
    dt = facts[0].get("durSec", 0.5) or 0.5
    gap_limit = max(dt * 2.5, dt + 0.05)

    runs: list[list[dict]] = []
    cur: list[dict] = []
    for f in facts:
        if cur and (f.get("t", 0.0) - cur[-1].get("t", 0.0)) > gap_limit:
            runs.append(cur)
            cur = []
        cur.append(f)
    if cur:
        runs.append(cur)

    total = 0.0
    for run in runs:
        duration = max(run[-1].get("t", 0.0) - run[0].get("t", 0.0) + dt, dt)
        weights = [_frame_weight(f, enabled) for f in run]
        mean_w = sum(weights) / len(weights)
        dw = _duration_weight(duration) if "durationWeight" in enabled else 1.0
        total += mean_w * dw * duration
    return total


def compute_zone_shares(facts: list[dict], enabled: list[str]) -> dict[str, float]:
    """anchor zone id -> % share of total quality exposure (sums to ~100)."""
    enabled_set = {e for e in enabled if e in CRITERIA_KEYS}
    by_zone: dict[str, list[dict]] = defaultdict(list)
    for f in facts:
        zone = f.get("zone")
        if zone:
            by_zone[zone].append(f)

    quality = {zone: _zone_quality(fs, enabled_set) for zone, fs in by_zone.items()}
    denom = sum(quality.values()) or 1.0
    return {zone: q / denom * 100.0 for zone, q in quality.items()}


def compute_location_ai_percentages(
    facts: list[dict], enabled: list[str], anchor_by_location: dict[str, str]
) -> dict[str, float]:
    """location id -> AI %, derived from each location's mapped anchor's zone share.

    When several locations map to the same anchor, that anchor's share is split
    evenly between them so the column still totals ~100 %.
    """
    zone_shares = compute_zone_shares(facts, enabled)

    # How many locations share each anchor (for even splitting).
    anchor_loc_count: dict[str, int] = defaultdict(int)
    for anchor in anchor_by_location.values():
        if anchor:
            anchor_loc_count[anchor] += 1

    out: dict[str, float] = {}
    for loc_id, anchor in anchor_by_location.items():
        share = zone_shares.get(anchor, 0.0)
        n = anchor_loc_count.get(anchor, 1) or 1
        out[loc_id] = round(share / n, 2)
    return out
