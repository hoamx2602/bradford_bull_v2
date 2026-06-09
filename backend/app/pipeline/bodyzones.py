"""Body-zone attribution.

Reconstructs 27 body zones (matching the dashboard's 3D model) from COCO-17
pose keypoints, then assigns each logo detection to the body region it sits on.
Accumulated per-zone visibility becomes the percentage breakdown the 3D body
viewer renders.

Side convention follows the frontend (components/dashboard/body-segmentation-3d.tsx):
"-l" = viewer's LEFT (smaller image x), "-r" = viewer's RIGHT. We assign sides by
image position, not anatomy, so it's robust to which way the player faces.
"""
from __future__ import annotations

import math

from app.pipeline.datatypes import Detection, PersonPose

# COCO-17 keypoint indices
NOSE = 0
L_EYE, R_EYE, L_EAR, R_EAR = 1, 2, 3, 4
L_SHO, R_SHO = 5, 6
L_ELB, R_ELB = 7, 8
L_WRI, R_WRI = 9, 10
L_HIP, R_HIP = 11, 12
L_KNE, R_KNE = 13, 14
L_ANK, R_ANK = 15, 16

KP_CONF = 0.3  # ignore keypoints below this confidence

# Canonical 27 zones — id -> display name. Order/ids match lib/mock-data.ts.
ZONES: list[tuple[str, str]] = [
    ("head", "Head"), ("neck", "Neck"),
    ("shoulder-l", "Shoulder L"), ("shoulder-r", "Shoulder R"),
    ("chest-l", "Chest Left"), ("chest-r", "Chest Right"),
    ("abdomen-l", "Abdomen Left"), ("abdomen-r", "Abdomen Right"),
    ("upper-arm-l", "Upper Arm L"), ("upper-arm-r", "Upper Arm R"),
    ("forearm-l", "Forearm L"), ("forearm-r", "Forearm R"),
    ("hand-l", "Hand L"), ("hand-r", "Hand R"),
    ("spine", "Spine"), ("back-l", "Back L"), ("back-r", "Back R"),
    ("lowerback-l", "Low Back L"), ("lowerback-r", "Low Back R"),
    ("hip-l", "Hip L"), ("hip-r", "Hip R"),
    ("upper-leg-l", "Upper Leg L"), ("upper-leg-r", "Upper Leg R"),
    ("lower-leg-l", "Lower Leg L"), ("lower-leg-r", "Lower Leg R"),
    ("foot-l", "Foot L"), ("foot-r", "Foot R"),
]
ZONE_IDS = [z[0] for z in ZONES]


def _kp(person: PersonPose, idx: int) -> tuple[float, float] | None:
    if idx >= len(person.keypoints):
        return None
    x, y, c = person.keypoints[idx]
    return (x, y) if c >= KP_CONF else None


def _mid(a, b):
    if a is None or b is None:
        return None
    return ((a[0] + b[0]) / 2, (a[1] + b[1]) / 2)


def _is_back_view(person: PersonPose) -> bool:
    """Facing away if the face keypoints are unreliable but shoulders exist."""
    face = sum(1 for i in (NOSE, L_EYE, R_EYE) if _kp(person, i))
    shoulders = _kp(person, L_SHO) and _kp(person, R_SHO)
    return face == 0 and bool(shoulders)


def build_anchors(person: PersonPose) -> dict[str, tuple[float, float]]:
    """Image-space anchor point for each zone we can place from keypoints.

    Zones whose keypoints are missing are simply omitted (a logo never gets
    assigned to a region we can't locate).
    """
    a: dict[str, tuple[float, float]] = {}

    l_sho, r_sho = _kp(person, L_SHO), _kp(person, R_SHO)
    l_hip, r_hip = _kp(person, L_HIP), _kp(person, R_HIP)

    # Resolve viewer-left vs viewer-right by image x (smaller x = viewer left).
    def lr(p1, p2):
        if p1 is None or p2 is None:
            return p1 or p2, p1 or p2
        return (p1, p2) if p1[0] <= p2[0] else (p2, p1)

    sho_l, sho_r = lr(l_sho, r_sho)   # viewer left / right shoulders
    hip_l, hip_r = lr(l_hip, r_hip)
    back = _is_back_view(person)

    # Head / neck
    nose = _kp(person, NOSE)
    ears = _mid(_kp(person, L_EAR), _kp(person, R_EAR))
    head = nose or ears or _mid(_kp(person, L_EYE), _kp(person, R_EYE))
    if head:
        a["head"] = head
    neck = _mid(sho_l, sho_r)
    if neck:
        a["neck"] = neck

    # Shoulders
    if sho_l:
        a["shoulder-l"] = sho_l
    if sho_r:
        a["shoulder-r"] = sho_r

    # Torso: split into upper (chest/back) and lower (abdomen/lowerback) thirds.
    def torso_point(sho, hip, frac):
        if sho is None or hip is None:
            return None
        return (sho[0] + (hip[0] - sho[0]) * frac, sho[1] + (hip[1] - sho[1]) * frac)

    chest_l = torso_point(sho_l, hip_l, 0.30)
    chest_r = torso_point(sho_r, hip_r, 0.30)
    abd_l = torso_point(sho_l, hip_l, 0.70)
    abd_r = torso_point(sho_r, hip_r, 0.70)
    if back:
        # Same physical spots, but they're the player's back.
        if chest_l: a["back-l"] = chest_l
        if chest_r: a["back-r"] = chest_r
        if abd_l: a["lowerback-l"] = abd_l
        if abd_r: a["lowerback-r"] = abd_r
        spine = _mid(_mid(sho_l, sho_r), _mid(hip_l, hip_r))
        if spine: a["spine"] = spine
    else:
        if chest_l: a["chest-l"] = chest_l
        if chest_r: a["chest-r"] = chest_r
        if abd_l: a["abdomen-l"] = abd_l
        if abd_r: a["abdomen-r"] = abd_r

    # Arms (viewer side resolved per limb by elbow/wrist x vs body centre)
    centre_x = None
    mids = _mid(_mid(sho_l, sho_r), _mid(hip_l, hip_r))
    if mids:
        centre_x = mids[0]

    def arm(elb_idx, wri_idx, sho):
        elb = _kp(person, elb_idx)
        wri = _kp(person, wri_idx)
        ua = _mid(sho, elb)
        fa = _mid(elb, wri)
        return ua, fa, wri

    for elb_i, wri_i, sho in ((L_ELB, L_WRI, l_sho), (R_ELB, R_WRI, r_sho)):
        ua, fa, wri = arm(elb_i, wri_i, sho)
        for pt, base in ((ua, "upper-arm"), (fa, "forearm"), (wri, "hand")):
            if pt is None:
                continue
            side = "l" if (centre_x is None or pt[0] <= centre_x) else "r"
            a.setdefault(f"{base}-{side}", pt)

    # Hips / legs
    if hip_l: a["hip-l"] = hip_l
    if hip_r: a["hip-r"] = hip_r
    for hip, kne_i, ank_i, side in (
        (hip_l, L_KNE, L_ANK, "l"), (hip_r, R_KNE, R_ANK, "r")
    ):
        kne = _kp(person, kne_i)
        ank = _kp(person, ank_i)
        # knee/ankle COCO sides may not equal viewer side; resolve by x.
        ul = _mid(hip, kne)
        ll = _mid(kne, ank)
        for pt, base in ((ul, "upper-leg"), (ll, "lower-leg"), (ank, "foot")):
            if pt is None:
                continue
            s = side if centre_x is None else ("l" if pt[0] <= centre_x else "r")
            a.setdefault(f"{base}-{s}", pt)

    return a


class BodyZoneAccumulator:
    """Sums quality-weighted exposure per body zone across all frames."""

    def __init__(self):
        self.totals: dict[str, float] = {zid: 0.0 for zid in ZONE_IDS}
        self.attributed = 0.0  # weight assigned to a zone
        self.total = 0.0       # all logo weight seen (incl. unattributed)

    def add_frame(self, detections: list[Detection], persons: list[PersonPose]) -> None:
        anchors = [(p, build_anchors(p)) for p in persons]
        for det in detections:
            weight = max(det.visibility, 1e-6)
            self.total += weight
            zone = self._assign(det, anchors)
            if zone is not None:
                det.body_zone = zone
                self.totals[zone] += weight
                self.attributed += weight

    @staticmethod
    def _assign(det: Detection, anchors) -> str | None:
        if not anchors:
            return None
        # Pick the best person: prefer one whose bbox contains the logo centre,
        # then by smallest centre distance. Rank key = (not_inside, distance).
        def person_rank(item):
            person, _ = item
            x1, y1, x2, y2 = person.xyxy
            inside = x1 <= det.cx <= x2 and y1 <= det.cy <= y2
            pcx, pcy = (x1 + x2) / 2, (y1 + y2) / 2
            dist = (det.cx - pcx) ** 2 + (det.cy - pcy) ** 2
            return (0 if inside else 1, dist)

        _, zmap = min(anchors, key=person_rank)
        if not zmap:
            return None
        # Nearest zone anchor to the logo centre.
        return min(zmap, key=lambda z: (det.cx - zmap[z][0]) ** 2 + (det.cy - zmap[z][1]) ** 2)

    def result(self) -> list[dict]:
        """27 zones with percentage of total attributed exposure."""
        denom = self.attributed or 1.0
        out = []
        for zid, name in ZONES:
            pct = round(self.totals[zid] / denom * 100, 1)
            out.append({"id": zid, "name": name, "percentage": pct, "color": ""})
        return out
