"""Tier-2 exposure aggregation: segmenting, duration weights, quality seconds."""
from __future__ import annotations

from app.pipeline.datatypes import Detection
from app.pipeline import exposure


def _det(t, track_id=1, vis=0.5):
    d = Detection(
        t=t, class_id=1, raw_name="bartercard_home", brand_key="bartercard",
        brand_name="Bartercard", conf=0.8, xyxy=(0, 0, 10, 10),
        track_id=track_id, frame_w=100, frame_h=100,
    )
    d.visibility = vis
    return d


def test_continuous_track_forms_one_segment():
    # 6 frames at 2 fps (dt=0.5) -> ~3s continuous -> one segment, weight 1.0 band.
    dets = [_det(i * 0.5) for i in range(6)]
    logos = exposure.aggregate_logos(dets, sample_fps=2.0)
    assert len(logos) == 1
    logo = logos[0]
    assert logo["name"] == "Bartercard"
    assert logo["segmentCount"] == 1
    seg = logo["segments"][0]
    assert seg["startTime"] == 0.0
    assert seg["durationWeight"] == 1.0  # 2.5-3.0s falls in the 1-5s band


def test_time_gap_splits_segments():
    # Two bursts separated by a 3s gap -> two segments.
    dets = [_det(t) for t in (0.0, 0.5, 1.0)] + [_det(t) for t in (5.0, 5.5, 6.0)]
    logos = exposure.aggregate_logos(dets, sample_fps=2.0)
    assert logos[0]["segmentCount"] == 2


def test_long_segment_gets_premium_weight():
    dets = [_det(i * 0.5) for i in range(16)]  # ~8s
    logos = exposure.aggregate_logos(dets, sample_fps=2.0)
    assert logos[0]["segments"][0]["durationWeight"] == 1.2


def test_low_visibility_dropped():
    dets = [_det(i * 0.5, vis=0.001) for i in range(6)]
    logos = exposure.aggregate_logos(dets, sample_fps=2.0)
    assert logos == []  # all below visibility_floor -> no segments


def test_separate_tracks_same_brand_merge_into_one_logo():
    a = [_det(i * 0.5, track_id=1) for i in range(4)]
    b = [_det(i * 0.5, track_id=2) for i in range(4)]
    logos = exposure.aggregate_logos(a + b, sample_fps=2.0)
    assert len(logos) == 1
    assert logos[0]["segmentCount"] == 2  # one per track
