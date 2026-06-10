"""Detection timeline — per-brand on-screen intervals.

This is built from the RAW detections (exactly what gets drawn on the preview
video), NOT from the EMV-weighted exposure segments. That's deliberate: the
timeline under the player must match the boxes the viewer sees, so it must not
apply the visibility floor / min-segment filtering that the business metric uses.

Adjacent sampled hits of the same brand are merged into one interval (a small
gap tolerance bridges a single dropped frame so bars don't fragment).
"""
from __future__ import annotations

from collections import defaultdict

from app.pipeline.colors import brand_hex
from app.pipeline.datatypes import Detection


def build_detection_timeline(detections: list[Detection], fps: float) -> list[dict]:
    frame_dt = 1.0 / max(0.1, fps)
    # Bridge brief dropouts so bars don't fragment (≥0.25s tolerance works for
    # both the full-fps preview pass and the 2fps fallback).
    gap_limit = max(frame_dt * 2.0, 0.25)

    times_by_brand: dict[str, list[float]] = defaultdict(list)
    names: dict[str, str] = {}
    for d in detections:
        times_by_brand[d.brand_key].append(d.t)
        names[d.brand_key] = d.brand_name

    out: list[dict] = []
    for key, times in times_by_brand.items():
        times.sort()
        intervals: list[dict] = []
        start = prev = times[0]
        for t in times[1:]:
            if t - prev > gap_limit:
                intervals.append({"start": round(start, 2), "end": round(prev + frame_dt, 2)})
                start = t
            prev = t
        intervals.append({"start": round(start, 2), "end": round(prev + frame_dt, 2)})

        total = sum(i["end"] - i["start"] for i in intervals)
        out.append({
            "name": names[key],
            "class": key,
            "color": brand_hex(key),
            "intervals": intervals,
            "_total": total,
        })

    out.sort(key=lambda b: b["_total"], reverse=True)
    for b in out:
        b.pop("_total")
    return out
