"""Target-team filter — chỉ giữ logo nằm trên cầu thủ ĐỘI MỤC TIÊU.

Vì sao (xem `../docs/04-team-filter.md`): highlight có cả 2 đội + trọng tài + biển
quảng cáo. Khách mua slot trên áo Bradford → chỉ đếm logo trên cầu thủ Bradford.

Cùng họ kỹ thuật top SoccerNet GSR: **reference-based, KHÔNG train model riêng**
(kit đối thủ đổi mỗi trận). Phân loại áo bằng color histogram (+ embedding tùy chọn)
so với reference của target; gán logo cho cầu thủ chứa nó; giữ nếu chủ là target.

Pipeline:
    person boxes (YOLO) ──► jersey band crop ──► feature(color [⊕ embedding])
        │                                              │
        │                                     classify vs refs → target/other
    logo box ──► owner = person nhỏ nhất chứa tâm logo (else gần nhất)
        │
    owner == target ? giữ : bỏ      (thiếu bằng chứng → giữ, an toàn doanh thu)

Self-contained core (color) test được không cần model. Person detect + embedding
là tùy chọn (lazy import ultralytics / recognizer.Embedder).
"""
from __future__ import annotations

import numpy as np

try:
    import cv2
except Exception:
    cv2 = None


# --------------------------------------------------------------------------- #
# Feature áo
# --------------------------------------------------------------------------- #

def jersey_band(person_xyxy, frame_shape, top=0.15, bot=0.45,
                xpad=0.2) -> tuple[int, int, int, int]:
    """Dải áo ngực: 15–45% chiều cao bbox, thu hẹp 2 bên (bớt nền/tay)."""
    x0, y0, x1, y1 = person_xyxy
    h = y1 - y0; w = x1 - x0
    bx0 = int(x0 + w * xpad); bx1 = int(x1 - w * xpad)
    by0 = int(y0 + h * top); by1 = int(y0 + h * bot)
    H, W = frame_shape[:2]
    return (max(bx0, 0), max(by0, 0), min(bx1, W), min(by1, H))


def color_feat(crop: np.ndarray, bins: int = 12) -> np.ndarray:
    """Histogram hue (bỏ pixel cỏ xanh + da gần trắng), L2-normalize."""
    if crop.size == 0:
        return np.zeros(bins, np.float32)
    hsv = cv2.cvtColor(crop, cv2.COLOR_BGR2HSV)
    h, s, v = hsv[:, :, 0], hsv[:, :, 1], hsv[:, :, 2]
    mask = (s > 40) & (v > 40)                       # bỏ pixel xám/đen/nhạt
    hh = h[mask]
    if hh.size == 0:
        hh = h.ravel()
    hist, _ = np.histogram(hh, bins=bins, range=(0, 180))
    hist = hist.astype(np.float32)
    n = np.linalg.norm(hist)
    return hist / n if n > 0 else hist


def cosine(a, b) -> float:
    na, nb = np.linalg.norm(a), np.linalg.norm(b)
    return float(a @ b / (na * nb)) if na > 0 and nb > 0 else 0.0


def classify(feat: np.ndarray, refs: dict[str, np.ndarray]) -> tuple[str, float]:
    """feat → (nhãn ref gần nhất, cosine)."""
    best, bs = "unknown", -1.0
    for lbl, rf in refs.items():
        s = cosine(feat, rf)
        if s > bs:
            best, bs = lbl, s
    return best, bs


# --------------------------------------------------------------------------- #
# Gán logo → chủ + lọc
# --------------------------------------------------------------------------- #

def _center(xyxy):
    return ((xyxy[0] + xyxy[2]) / 2, (xyxy[1] + xyxy[3]) / 2)


def _area(b):
    return max(b[2] - b[0], 0) * max(b[3] - b[1], 0)


def assign_owner(logo_xyxy, person_boxes) -> int:
    """Chủ logo = person nhỏ nhất chứa tâm logo; else person có tâm gần nhất."""
    cx, cy = _center(logo_xyxy)
    contain = [i for i, p in enumerate(person_boxes)
               if p[0] <= cx <= p[2] and p[1] <= cy <= p[3]]
    if contain:
        return min(contain, key=lambda i: _area(person_boxes[i]))
    if not person_boxes:
        return -1
    return min(range(len(person_boxes)),
               key=lambda i: (cx - _center(person_boxes[i])[0]) ** 2
               + (cy - _center(person_boxes[i])[1]) ** 2)


def filter_logos(logo_boxes, person_boxes, person_labels, target: str,
                 keep_unknown_owner: bool = True,
                 keep_unassigned: bool = False) -> list[dict]:
    """Trả list {idx, keep, owner, owner_label, reason} cho mỗi logo."""
    out = []
    for i, lb in enumerate(logo_boxes):
        owner = assign_owner(lb, person_boxes)
        if owner < 0:
            keep = keep_unassigned; reason = "unassigned"
            lbl = None
        else:
            lbl = person_labels[owner]
            if lbl == target:
                keep, reason = True, "target"
            elif lbl == "unknown":
                keep, reason = keep_unknown_owner, "owner_unknown"
            else:
                keep, reason = False, "other_team"
        out.append({"idx": i, "keep": keep, "owner": owner,
                    "owner_label": lbl, "reason": reason})
    return out


# --------------------------------------------------------------------------- #
# Lớp tiện dụng (build refs từ ảnh kit + person detect lazy)
# --------------------------------------------------------------------------- #

class TeamFilter:
    def __init__(self, refs: dict[str, np.ndarray], target: str,
                 person_model: str = "yolo11m.pt", device=None,
                 min_score: float = 0.0):
        self.refs = refs; self.target = target
        self.person_model = person_model; self.device = device
        self.min_score = min_score
        self._yolo = None

    @classmethod
    def from_kit_images(cls, kit_paths: dict[str, list[str]], target: str, **kw):
        """refs[label] = mean color_feat của các ảnh kit."""
        refs = {}
        for lbl, paths in kit_paths.items():
            feats = []
            for p in paths:
                img = cv2.imread(p)
                if img is not None:
                    feats.append(color_feat(img))
            if feats:
                m = np.mean(feats, 0); n = np.linalg.norm(m)
                refs[lbl] = m / n if n > 0 else m
        return cls(refs, target, **kw)

    def persons(self, frame):
        if self._yolo is None:
            from ultralytics import YOLO
            self._yolo = YOLO(self.person_model)
        r = self._yolo.predict(frame, classes=[0], device=self.device,
                               verbose=False)[0]
        return r.boxes.xyxy.cpu().numpy().tolist() if r.boxes is not None else []

    def label_persons(self, frame, person_boxes) -> list[str]:
        labels = []
        for pb in person_boxes:
            bx = jersey_band(pb, frame.shape)
            crop = frame[bx[1]:bx[3], bx[0]:bx[2]]
            lbl, sc = classify(color_feat(crop), self.refs)
            labels.append(lbl if sc >= self.min_score else "unknown")
        return labels

    def filter_frame(self, frame, logo_boxes) -> list[dict]:
        pb = self.persons(frame)
        pl = self.label_persons(frame, pb)
        return filter_logos(logo_boxes, pb, pl, self.target)


def _selftest() -> None:
    # classify: feat trùng ref target
    refs = {"bradford": np.array([1, 0, 0, 0], np.float32),
            "other": np.array([0, 1, 0, 0], np.float32)}
    lbl, _ = classify(np.array([0.9, 0.1, 0, 0], np.float32), refs)
    assert lbl == "bradford"
    # assign_owner: tâm logo trong person nhỏ
    persons = [[0, 0, 100, 200], [40, 40, 70, 120]]
    assert assign_owner([50, 50, 60, 60], persons) == 1  # box nhỏ chứa tâm
    assert assign_owner([500, 500, 510, 510], persons) in (0, 1)  # gần nhất
    # filter: target giữ, other bỏ, unknown-owner giữ
    # logo0 tâm (55,55) ⊂ person1(bradford) → giữ; logo1 tâm (15,15) ⊂ person0(other) → bỏ
    res = filter_logos([[50, 50, 60, 60], [10, 10, 20, 20]],
                       persons, ["other", "bradford"], target="bradford")
    keep = {r["idx"]: r["keep"] for r in res}
    assert keep[0] is True and keep[1] is False
    print("  team_filter selftest: OK ✅")


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser(description="Target-team filter")
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args()
    if a.selftest:
        _selftest()
    else:
        ap.error("module dùng qua import; --selftest để kiểm logic")
