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


def _zone_metrics(facts: list[dict], enabled: set[str]) -> dict:
    """Quality-weighted exposure for one zone PLUS the parameters behind it.

    Splits the zone's detections into time segments (gap > 2.5 sample intervals),
    then sums mean(frame_weight) × duration_weight × duration per segment — the
    same shape as exposure.aggregate, but with the recomputed per-frame weight.
    Also returns the factor means / counts so the AI % is fully explainable.
    """
    n = len(facts)
    base = {
        "quality": 0.0, "detections": n, "segments": 0, "totalDuration": 0.0,
        "meanSize": 0.0, "meanPos": 0.0, "meanClarity": 0.0, "meanObb": 0.0,
        "meanFrameWeight": 0.0,
    }
    if not facts:
        return base

    base["meanSize"] = sum(f.get("size", 1.0) for f in facts) / n
    base["meanPos"] = sum(f.get("pos", 1.0) for f in facts) / n
    base["meanClarity"] = sum(f.get("clarity", 1.0) for f in facts) / n
    base["meanObb"] = sum(f.get("obb", 1.0) for f in facts) / n
    base["meanFrameWeight"] = sum(_frame_weight(f, enabled) for f in facts) / n

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

    quality = 0.0
    duration_total = 0.0
    for run in runs:
        duration = max(run[-1].get("t", 0.0) - run[0].get("t", 0.0) + dt, dt)
        weights = [_frame_weight(f, enabled) for f in run]
        mean_w = sum(weights) / len(weights)
        dw = _duration_weight(duration) if "durationWeight" in enabled else 1.0
        quality += mean_w * dw * duration
        duration_total += duration

    base["quality"] = quality
    base["segments"] = len(runs)
    base["totalDuration"] = duration_total
    return base


def _zones_by_id(facts: list[dict]) -> dict[str, list[dict]]:
    by_zone: dict[str, list[dict]] = defaultdict(list)
    for f in facts:
        zone = f.get("zone")
        if zone:
            by_zone[zone].append(f)
    return by_zone


def compute_zone_detail(facts: list[dict], enabled: list[str]) -> dict[str, dict]:
    """anchor zone id -> metrics dict (incl. `share` %), explaining the AI %."""
    enabled_set = {e for e in enabled if e in CRITERIA_KEYS}
    metrics = {z: _zone_metrics(fs, enabled_set) for z, fs in _zones_by_id(facts).items()}
    denom = sum(m["quality"] for m in metrics.values()) or 1.0
    for m in metrics.values():
        m["share"] = m["quality"] / denom * 100.0
    return metrics


def compute_zone_shares(facts: list[dict], enabled: list[str]) -> dict[str, float]:
    """anchor zone id -> % share of total quality exposure (sums to ~100)."""
    return {z: m["share"] for z, m in compute_zone_detail(facts, enabled).items()}


def _round_to_total(raw: dict[str, float], target: float = 100.0) -> dict[str, float]:
    """Round each value to 2 decimals so the rounded values sum EXACTLY to target.

    Largest-remainder method: floor every value to whole cents, then hand the few
    leftover cents to the entries with the biggest fractional remainder. Avoids
    the "sum shows 100.01 %" artefact of rounding each value independently.
    """
    total = sum(raw.values())
    if total <= 0:
        return {k: 0.0 for k in raw}
    # Normalise to `target` first (guards against float drift), in whole cents.
    cents = {k: int(v / total * target * 100) for k, v in raw.items()}  # floor (v >= 0)
    remainder = {k: (raw[k] / total * target * 100) - cents[k] for k in raw}
    deficit = int(round(target * 100)) - sum(cents.values())
    for k in sorted(remainder, key=lambda k: remainder[k], reverse=True)[:max(0, deficit)]:
        cents[k] += 1
    return {k: round(c / 100.0, 2) for k, c in cents.items()}


def compute_location_ai_percentages(
    facts: list[dict], enabled: list[str], anchor_by_location: dict[str, str]
) -> dict[str, float]:
    """location id -> AI %, normalised to EXACTLY 100 % across configured locations.

    Only quality exposure that lands on an anchor mapped to a location counts;
    exposure on unmapped anatomical zones (e.g. abdomen, opposite shoulder) is
    excluded, so the column totals 100 % over the locations the customer set up.
    When several locations map to the same anchor, that anchor's quality is split
    evenly between them. Final values are rounded so they sum to exactly 100.00.
    """
    detail = compute_zone_detail(facts, enabled)

    # Anchors actually mapped to at least one location, and how many share each.
    anchor_loc_count: dict[str, int] = defaultdict(int)
    for anchor in anchor_by_location.values():
        if anchor:
            anchor_loc_count[anchor] += 1

    # Raw (unrounded) share per location, over the mapped anchors only.
    raw: dict[str, float] = {}
    for loc_id, anchor in anchor_by_location.items():
        quality = detail.get(anchor, {}).get("quality", 0.0)
        n = anchor_loc_count.get(anchor, 1) or 1
        raw[loc_id] = quality / n

    return _round_to_total(raw, 100.0)
