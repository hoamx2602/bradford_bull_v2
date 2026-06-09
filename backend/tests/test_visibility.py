"""Tier-1 visibility scoring."""
from __future__ import annotations

from app.pipeline.datatypes import Detection
from app.pipeline import visibility


def _det(xyxy, conf=1.0, w=1000, h=1000):
    return Detection(
        t=0.0, class_id=1, raw_name="x_home", brand_key="x", brand_name="X",
        conf=conf, xyxy=xyxy, track_id=1, frame_w=w, frame_h=h,
    )


def test_scores_in_unit_range():
    d = _det((400, 400, 600, 600))
    assert 0.0 <= visibility.visibility_score(d) <= 1.0


def test_centre_beats_corner():
    centre = _det((450, 450, 550, 550))
    corner = _det((0, 0, 100, 100))
    assert visibility.position_score(centre) > visibility.position_score(corner)


def test_bigger_logo_higher_size_score():
    small = _det((480, 480, 520, 520))
    big = _det((300, 300, 700, 700))
    assert visibility.size_score(big) > visibility.size_score(small)


def test_confidence_scales_visibility():
    hi = _det((400, 400, 600, 600), conf=0.9)
    lo = _det((400, 400, 600, 600), conf=0.2)
    assert visibility.visibility_score(hi) > visibility.visibility_score(lo)
