"""Assemble the final AnalysisResult document (camelCase, ready for the frontend).

Shape matches logo-analytics/lib/types.ts AnalysisResult, plus a `bodyZones`
field (added to the frontend types) and a few diagnostic extras the UI ignores.
"""
from __future__ import annotations

from datetime import datetime, timezone

from app.pipeline.pricing import placement_multiplier


def build_analysis_result(
    *,
    analysis_id: str,
    event_name: str,
    video_name: str,
    video_duration_seconds: float,
    audience_size: int,
    placement_type: str,
    cpm_base: float,
    logos: list[dict],
    body_zones: list[dict],
    detection_timeline: list[dict],
    frames_analyzed: int,
) -> dict:
    # Strip private helper keys before serialising.
    clean_logos = []
    for logo in logos:
        clean_logos.append({k: v for k, v in logo.items() if not k.startswith("_")})

    total_emv = round(sum(l.get("emvUsd", 0.0) for l in clean_logos), 2)
    total_quality = round(sum(l["qualityExposureSeconds"] for l in clean_logos), 2)
    avg_vis = (
        round(sum(l["avgVisibilityScore"] for l in clean_logos) / len(clean_logos), 2)
        if clean_logos
        else 0.0
    )

    return {
        "id": analysis_id,
        "eventName": event_name,
        "videoName": video_name,
        "videoDurationSeconds": round(video_duration_seconds, 1),
        "analyzedAt": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "metadata": {
            "audienceSize": audience_size,
            "placementType": placement_type,
            "cpmBase": cpm_base,
            "placementMultiplier": placement_multiplier(placement_type),
            "framesAnalyzed": frames_analyzed,
        },
        "logos": clean_logos,
        "bodyZones": body_zones,
        "detectionTimeline": detection_timeline,
        "totalEmvUsd": total_emv,
        "totalQualityExposureSeconds": total_quality,
        "avgVisibilityScore": avg_vis,
    }
