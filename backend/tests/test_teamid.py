"""Team-filter logic: colour features, classification, voting, logo ownership."""
from __future__ import annotations

import numpy as np

from app.pipeline.datatypes import Detection
from app.pipeline.teamid.classifier import OTHER, TARGET, TeamClassifier, VoteTracker, learn_weights
from app.pipeline.teamid.features import color_feature
from app.pipeline.teamid.tracker import TrackedPerson, assign_owner


def _flat_crop(bgr: tuple[int, int, int], size: int = 32):
    region = np.full((size, size, 3), bgr, dtype=np.uint8)
    mask = np.ones((size, size), dtype=bool)
    return region, mask


def _classifier_black_vs_white() -> TeamClassifier:
    """Colour-only classifier: target = black kit, other = white kit."""
    black = [color_feature(*_flat_crop((10, 10, 10))) for _ in range(4)]
    white = [color_feature(*_flat_crop((245, 245, 245))) for _ in range(4)]
    assignments = [TARGET] * 4 + [OTHER] * 4
    w_color, w_siglip, centroids, colors = learn_weights(
        [TARGET, OTHER], assignments, None, black + white)
    return TeamClassifier([TARGET, OTHER], centroids, colors, w_color, w_siglip)


def test_color_classifier_separates_black_and_white_kits():
    clf = _classifier_black_vs_white()

    team, conf, margin = clf.classify(None, color_feature(*_flat_crop((20, 20, 20))))
    assert team == TARGET and margin > 0.1

    team, conf, margin = clf.classify(None, color_feature(*_flat_crop((230, 230, 230))))
    assert team == OTHER and margin > 0.1


def test_vote_tracker_majority_and_hysteresis():
    v = VoteTracker([TARGET, OTHER], hysteresis=1.25)
    # Early noisy frame says OTHER...
    v.update(1, OTHER, 1.0)
    assert v.label(1) == OTHER
    # ...but sustained TARGET evidence out-votes it (needs 1.25x lead).
    v.update(1, TARGET, 1.0)
    assert v.label(1) == OTHER          # 1.0 vs 1.0 — no flip yet
    v.update(1, TARGET, 0.5)
    assert v.label(1) == TARGET         # 1.5 > 1.0 * 1.25


def _det(cx: float, cy: float) -> Detection:
    return Detection(
        t=0.0, class_id=0, raw_name="klg_away", brand_key="klg", brand_name="KLG",
        conf=0.9, xyxy=(cx - 5, cy - 5, cx + 5, cy + 5),
        track_id=1, frame_w=1000, frame_h=1000,
    )


def _person(x1, y1, x2, y2, team=TARGET, mass=10.0, tid=1) -> TrackedPerson:
    return TrackedPerson(xyxy=(x1, y1, x2, y2), track_id=tid, team=team, vote_mass=mass)


def test_assign_owner_prefers_smallest_containing_box():
    big = _person(0, 0, 400, 400, tid=1)
    small = _person(100, 100, 200, 300, tid=2)
    owner = assign_owner(_det(150, 200), [big, small])
    assert owner is small


def test_assign_owner_none_when_far_from_everyone():
    p = _person(0, 0, 50, 100)
    assert assign_owner(_det(900, 900), [p]) is None


def test_assign_owner_nearby_outside_box():
    # Logo centre just outside the bbox (e.g. flying shirt) still assigns.
    p = _person(100, 100, 160, 220)
    assert assign_owner(_det(170, 160), [p]) is p
