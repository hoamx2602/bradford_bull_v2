"""Tier 2 — per-logo exposure aggregation.

Implements LOGOS_Exposure_Pricing_Algorithm.md §Tầng 2:
- Group consecutive frames of the same physical logo into segments.
- Drop sub-0.5s flickers.
- Weight each segment by duration band (0.5 / 1.0 / 1.2).
- quality_seconds = Σ mean(visibility) x duration_weight x segment_duration.

Grouping key is (brand_key, track_id): the ByteTrack id ties one logo across
frames so the same exposure event isn't double counted. A logo briefly lost and
re-found gets a new track id (a new segment), which is the desired behaviour.
"""
from __future__ import annotations

from collections import defaultdict

from app.config import get_settings
from app.pipeline.datatypes import Detection


def _duration_weight(duration: float) -> float:
    if duration < 1.0:
        return 0.5
    if duration <= 5.0:
        return 1.0
    return 1.2


def _build_segments_for_track(dets: list[Detection], sample_dt: float) -> list[dict]:
    """One track's detections -> one or more segments split on time gaps.

    A gap larger than ~2 sample intervals means the logo disappeared and came
    back; we split there so each visible stretch is its own segment.
    """
    settings = get_settings()
    dets = sorted(dets, key=lambda d: d.t)
    gap_limit = max(sample_dt * 2.5, sample_dt + 0.05)

    runs: list[list[Detection]] = []
    cur: list[Detection] = []
    for d in dets:
        if d.visibility <= settings.visibility_floor:
            continue
        if cur and (d.t - cur[-1].t) > gap_limit:
            runs.append(cur)
            cur = []
        cur.append(d)
    if cur:
        runs.append(cur)

    segments: list[dict] = []
    for run in runs:
        start = run[0].t
        # Each sampled frame represents ~sample_dt of screen time; extend the end
        # by one interval so a single-frame hit still has a real duration.
        end = run[-1].t + sample_dt
        duration = max(end - start, sample_dt)
        if duration < settings.min_segment_seconds:
            continue
        vis = [d.visibility for d in run]
        mean_vis = sum(vis) / len(vis)
        weight = _duration_weight(duration)
        segments.append(
            {
                "startTime": round(start, 2),
                "endTime": round(end, 2),
                "avgVisibility": round(mean_vis, 3),
                "durationWeight": weight,
                "_duration": duration,
                "_quality": mean_vis * weight * duration,
            }
        )
    return segments


def aggregate_logos(detections: list[Detection], sample_fps: float) -> list[dict]:
    """Return one record per brand with segments + Tier-2 metrics."""
    sample_dt = 1.0 / max(0.1, sample_fps)

    # brand_key -> track_id -> [detections]
    by_brand: dict[str, dict[int, list[Detection]]] = defaultdict(lambda: defaultdict(list))
    display: dict[str, str] = {}
    raw_classes: dict[str, set[str]] = defaultdict(set)
    for d in detections:
        by_brand[d.brand_key][d.track_id].append(d)
        display[d.brand_key] = d.brand_name
        raw_classes[d.brand_key].add(d.raw_name)

    logos: list[dict] = []
    for idx, (brand_key, tracks) in enumerate(sorted(by_brand.items())):
        segments: list[dict] = []
        for _track_id, dets in tracks.items():
            segments.extend(_build_segments_for_track(dets, sample_dt))
        if not segments:
            continue
        segments.sort(key=lambda s: s["startTime"])

        total_exposure = sum(s["_duration"] for s in segments)
        quality_exposure = sum(s["_quality"] for s in segments)
        avg_vis = sum(s["avgVisibility"] for s in segments) / len(segments)
        longest = max(s["_duration"] for s in segments)

        public_segments = [
            {k: v for k, v in s.items() if not k.startswith("_")} for s in segments
        ]
        logos.append(
            {
                "id": f"logo-{idx}",
                "name": display[brand_key],
                "class": brand_key,
                "rawClasses": sorted(raw_classes[brand_key]),
                "segments": public_segments,
                "totalExposureSeconds": round(total_exposure, 1),
                "qualityExposureSeconds": round(quality_exposure, 2),
                "avgVisibilityScore": round(avg_vis, 2),
                "segmentCount": len(segments),
                "longestSegmentSeconds": round(longest, 1),
                "_qualityRaw": quality_exposure,  # unrounded, for pricing
            }
        )

    # Sort brands by quality exposure (most-seen first), keep stable logo-N ids.
    logos.sort(key=lambda l: l["_qualityRaw"], reverse=True)
    for i, logo in enumerate(logos):
        logo["id"] = f"logo-{i}"
    return logos
