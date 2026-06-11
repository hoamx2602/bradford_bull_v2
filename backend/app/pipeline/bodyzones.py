"""Body-zone attribution.

Reconstructs 18 KIT SPONSOR SLOTS (matching the dashboard's 3D model) from
COCO-17 pose keypoints, then assigns each logo detection to the slot it sits
on. Accumulated per-zone visibility becomes the percentage breakdown the 3D
body viewer renders.

Zones are the saleable placements on the playing kit (jersey front/back,
shorts front/back, sleeves, socks) — NOT anatomical regions. Skin areas
(head, hands, bare thigh, boots) carry no zone, so logos are never
attributed there.

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

# Canonical 18 kit slots — id -> display name. Order/ids match lib/mock-data.ts.
# Away-kit reference (KIT/Away Kit.jpg): chest-center = Floor Tonic (main),
# back-top = MCP/Fairway, back-center = ACS Group, shorts-back = KLG,
# shorts-leg-l/r = Paints & Lacquers / AON, shorts-front-l = Cedar Court,
# sock = EM Workwear, shoulders = MNA Cladding / MNA Support Services.
ZONES: list[tuple[str, str]] = [
    ("chest-center", "Chest Centre"),
    ("chest-l", "Chest Upper L"), ("chest-r", "Chest Upper R"),
    ("shoulder-l", "Shoulder L"), ("shoulder-r", "Shoulder R"),
    ("sleeve-l", "Sleeve L"), ("sleeve-r", "Sleeve R"),
    ("abdomen", "Abdomen"),
    ("back-top", "Back Top"), ("back-center", "Back Centre"),
    ("back-lower", "Back Lower"),
    ("shorts-front-l", "Shorts Front L"), ("shorts-front-r", "Shorts Front R"),
    ("shorts-back", "Shorts Back"),
    ("shorts-leg-l", "Shorts Leg L"), ("shorts-leg-r", "Shorts Leg R"),
    ("sock-l", "Sock L"), ("sock-r", "Sock R"),
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
    """Image-space anchor point for each kit slot we can place from keypoints.

    Slots whose keypoints are missing are simply omitted (a logo never gets
    assigned to a region we can't locate). Skin regions (head, hands, bare
    thigh, boots) intentionally have NO anchor — they're not saleable.
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

    # Shoulders (MNA Cladding / MNA Support Services)
    if sho_l:
        a["shoulder-l"] = sho_l
    if sho_r:
        a["shoulder-r"] = sho_r

    def torso_point(sho, hip, frac):
        if sho is None or hip is None:
            return None
        return (sho[0] + (hip[0] - sho[0]) * frac, sho[1] + (hip[1] - sho[1]) * frac)

    # Centre-line of the torso: shoulders midpoint -> hips midpoint.
    sho_mid = _mid(sho_l, sho_r)
    hip_mid = _mid(hip_l, hip_r)

    def spine_point(frac):
        return torso_point(sho_mid, hip_mid, frac)

    if back:
        # Jersey back: sponsor block above the number / below the number / hem.
        for zid, frac in (("back-top", 0.18), ("back-center", 0.45), ("back-lower", 0.75)):
            p = spine_point(frac)
            if p:
                a[zid] = p
        # Seat of the shorts (KLG) sits just below the hip line.
        seat = spine_point(1.05)
        if seat:
            a["shorts-back"] = seat
    else:
        # Jersey front: upper-chest side panels + main centre slot + abdomen.
        chest_l = torso_point(sho_l, hip_l, 0.28)
        chest_r = torso_point(sho_r, hip_r, 0.28)
        if chest_l:
            a["chest-l"] = chest_l
        if chest_r:
            a["chest-r"] = chest_r
        cc = spine_point(0.42)
        if cc:
            a["chest-center"] = cc
        abd = spine_point(0.75)
        if abd:
            a["abdomen"] = abd

    centre = spine_point(0.5)
    centre_x = centre[0] if centre else None

    # Sleeves: shoulder -> elbow midpoint (viewer side resolved by x).
    for elb_i, sho in ((L_ELB, l_sho), (R_ELB, r_sho)):
        ua = _mid(sho, _kp(person, elb_i))
        if ua is None:
            continue
        side = "l" if (centre_x is None or ua[0] <= centre_x) else "r"
        a.setdefault(f"sleeve-{side}", ua)

    # Shorts legs (front: Cedar Court / crest; back: Paints & Lacquers / AON)
    # and socks (EM Workwear). Knee/ankle COCO sides may not equal viewer
    # side; resolve by x.
    for hip, kne_i, ank_i, side in (
        (hip_l, L_KNE, L_ANK, "l"), (hip_r, R_KNE, R_ANK, "r")
    ):
        kne = _kp(person, kne_i)
        ank = _kp(person, ank_i)
        thigh = _mid(hip, kne)
        calf = _mid(kne, ank)
        if thigh is not None:
            s = side if centre_x is None else ("l" if thigh[0] <= centre_x else "r")
            a.setdefault(f"shorts-leg-{s}" if back else f"shorts-front-{s}", thigh)
        if calf is not None:
            s = side if centre_x is None else ("l" if calf[0] <= centre_x else "r")
            a.setdefault(f"sock-{s}", calf)

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
        """18 kit slots with percentage of total attributed exposure."""
        denom = self.attributed or 1.0
        out = []
        for zid, name in ZONES:
            pct = round(self.totals[zid] / denom * 100, 1)
            out.append({"id": zid, "name": name, "percentage": pct, "color": ""})
        return out
