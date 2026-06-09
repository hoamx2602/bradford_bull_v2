"""Body-zone reconstruction + logo attribution."""
from __future__ import annotations

from app.pipeline.datatypes import Detection, PersonPose
from app.pipeline import bodyzones
from app.pipeline.bodyzones import BodyZoneAccumulator


def _front_person() -> PersonPose:
    """A front-facing player centred around x=500, with COCO-17 keypoints."""
    kp = [(0.0, 0.0, 0.0)] * 17
    kp[bodyzones.NOSE] = (500, 100, 0.9)
    kp[bodyzones.L_EYE] = (510, 95, 0.9)
    kp[bodyzones.R_EYE] = (490, 95, 0.9)
    kp[bodyzones.L_SHO] = (560, 200, 0.9)   # viewer right (bigger x)
    kp[bodyzones.R_SHO] = (440, 200, 0.9)   # viewer left
    kp[bodyzones.L_ELB] = (590, 300, 0.9)
    kp[bodyzones.R_ELB] = (410, 300, 0.9)
    kp[bodyzones.L_WRI] = (600, 400, 0.9)
    kp[bodyzones.R_WRI] = (400, 400, 0.9)
    kp[bodyzones.L_HIP] = (540, 450, 0.9)
    kp[bodyzones.R_HIP] = (460, 450, 0.9)
    kp[bodyzones.L_KNE] = (545, 650, 0.9)
    kp[bodyzones.R_KNE] = (455, 650, 0.9)
    kp[bodyzones.L_ANK] = (548, 850, 0.9)
    kp[bodyzones.R_ANK] = (452, 850, 0.9)
    return PersonPose(xyxy=(400, 80, 600, 880), keypoints=kp)


def _logo_at(cx, cy) -> Detection:
    d = Detection(
        t=0.0, class_id=1, raw_name="x_home", brand_key="x", brand_name="X",
        conf=0.8, xyxy=(cx - 10, cy - 10, cx + 10, cy + 10),
        track_id=1, frame_w=1000, frame_h=1000,
    )
    d.visibility = 0.5
    return d


def test_anchors_include_front_torso_not_back():
    anchors = bodyzones.build_anchors(_front_person())
    assert "chest-l" in anchors and "chest-r" in anchors
    assert "head" in anchors and "neck" in anchors
    assert "spine" not in anchors  # face visible -> front view


def test_chest_logo_attributed_to_chest():
    # Logo on the upper torso, viewer-left half (x<500).
    acc = BodyZoneAccumulator()
    acc.add_frame([_logo_at(470, 260)], [_front_person()])
    result = {z["id"]: z["percentage"] for z in acc.result()}
    assert result["chest-l"] == 100.0  # all weight on one zone


def test_back_view_uses_back_zones():
    p = _front_person()
    # Blank out face keypoints -> back view.
    for i in (bodyzones.NOSE, bodyzones.L_EYE, bodyzones.R_EYE):
        p.keypoints[i] = (0.0, 0.0, 0.0)
    anchors = bodyzones.build_anchors(p)
    assert "spine" in anchors
    assert "back-l" in anchors and "back-r" in anchors
    assert "chest-l" not in anchors


def test_result_has_27_zones():
    acc = BodyZoneAccumulator()
    assert len(acc.result()) == 27
