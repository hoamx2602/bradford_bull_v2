"""Stage 3 — logo detection + tracking.

Runs the fine-tuned logo detector on each sampled frame with track persistence so
detections of the same physical logo across frames share a track_id. That id is
what lets the exposure stage group frames into a single "exposure event" and
de-duplicate (Production-System-Design.MD §5).

Two interchangeable backends (config.logo_backend):
  * "yolo"   — fine-tuned YOLO26m via ultralytics, with built-in ByteTrack.
  * "rfdetr" — RF-DETR .pth checkpoint. DETR has no NMS and no built-in
               tracker, so tracking is added with supervision.ByteTrack.
Both return identical `Detection` lists, so the rest of the pipeline is unaware
of which detector produced them.
"""
from __future__ import annotations

from app.config import (
    display_name,
    get_settings,
    normalize_class,
    rfdetr_class_name,
)
from app.models_zoo import registry
from app.pipeline.datatypes import Detection

# A backend yields these raw rows; LogoDetector turns them into Detections.
# (class_id, raw_name, xyxy, confidence, track_id)  — track_id -1 = untracked.
RawBox = tuple[int, str, tuple[float, float, float, float], float, int]


def _iou(a, b) -> float:
    ax1, ay1, ax2, ay2 = a
    bx1, by1, bx2, by2 = b
    ix1, iy1 = max(ax1, bx1), max(ay1, by1)
    ix2, iy2 = min(ax2, bx2), min(ay2, by2)
    iw, ih = max(0.0, ix2 - ix1), max(0.0, iy2 - iy1)
    inter = iw * ih
    if inter <= 0:
        return 0.0
    area_a = max(0.0, ax2 - ax1) * max(0.0, ay2 - ay1)
    area_b = max(0.0, bx2 - bx1) * max(0.0, by2 - by1)
    return inter / (area_a + area_b - inter + 1e-9)


class _IoUTracker:
    """Greedy IoU tracker for the RF-DETR path.

    supervision.ByteTrack (deprecated in 0.28) drops detections after the first
    frame here, and its Kalman/motion model assumes ~30fps continuity that the
    2fps analytics sampling violates. This is a deterministic stand-in: match
    each detection to the highest-IoU surviving track above `iou_thr`, keep its
    id, and start a fresh id otherwise. Tracks persist for `max_age` frames so a
    one-frame miss doesn't split an exposure event.
    """

    def __init__(self, iou_thr: float = 0.2, max_age: int = 3):
        from collections import Counter

        self._Counter = Counter
        self.iou_thr = iou_thr
        self.max_age = max_age
        self._tracks: list[dict] = []  # {id, box, missed, votes:Counter}
        self._next_id = 1

    def update(self, dets: list[tuple]) -> list[tuple[int, int]]:
        """dets: list of (xyxy, class_id) in detection order.

        Returns (track_id, voted_class_id) per detection. The voted class is the
        majority brand over the track's life, so a single off-frame misread (DETR
        flipping e.g. klg<->mcp) doesn't change the reported brand.
        """
        boxes = [d[0] for d in dets]
        out: list[tuple[int, int]] = [(-1, dets[i][1]) for i in range(len(dets))]
        # Greedy: resolve the highest-IoU (detection, track) pairs first.
        pairs = []
        for di, box in enumerate(boxes):
            for ti, tr in enumerate(self._tracks):
                iou = _iou(box, tr["box"])
                if iou >= self.iou_thr:
                    pairs.append((iou, di, ti))
        pairs.sort(reverse=True)
        matched_det: set[int] = set()
        matched_trk: set[int] = set()
        for _, di, ti in pairs:
            if di in matched_det or ti in matched_trk:
                continue
            tr = self._tracks[ti]
            tr["box"] = boxes[di]
            tr["missed"] = 0
            tr["votes"][dets[di][1]] += 1
            out[di] = (tr["id"], tr["votes"].most_common(1)[0][0])
            matched_det.add(di)
            matched_trk.add(ti)
        # Age / evict tracks that went unmatched this frame.
        survivors = []
        for ti, tr in enumerate(self._tracks):
            if ti in matched_trk:
                survivors.append(tr)
            else:
                tr["missed"] += 1
                if tr["missed"] <= self.max_age:
                    survivors.append(tr)
        self._tracks = survivors
        # Spawn new tracks for unmatched detections.
        for di, box in enumerate(boxes):
            if di not in matched_det:
                cls = dets[di][1]
                self._tracks.append({"id": self._next_id, "box": box, "missed": 0,
                                     "votes": self._Counter({cls: 1})})
                out[di] = (self._next_id, cls)
                self._next_id += 1
        return out


class _YoloBackend:
    """Ultralytics YOLO with built-in ByteTrack."""

    def __init__(self):
        self.settings = get_settings()
        self.backend = registry.get_logo_backend()
        self.backend.reset()  # fresh tracker state per video
        self.names = self.backend.names  # {class_id: raw_name}

    def _to_detections(self, raw_boxes, t: float, w: int, h: int) -> list[Detection]:
        out: list[Detection] = []
        for b in raw_boxes:
            raw = self.names.get(b.cls_id, str(b.cls_id))
            out.append(
                Detection(
                    t=t,
                    class_id=b.cls_id,
                    raw_name=raw,
                    brand_key=normalize_class(raw),
                    brand_name=display_name(raw),
                    conf=b.conf,
                    xyxy=b.xyxy,  # type: ignore[arg-type]
                    track_id=b.track_id,
                    frame_w=w,
                    frame_h=h,
                )
            )
        return out

    def _rows(self, res, tracked: bool) -> list[RawBox]:
        boxes = getattr(res, "boxes", None)
        if boxes is None or boxes.shape[0] == 0:
            return []
        ids = boxes.id if tracked else None
        rows: list[RawBox] = []
        for i in range(boxes.shape[0]):
            cls_id = int(boxes.cls[i].item())
            raw = self.names.get(cls_id, str(cls_id))
            xyxy = tuple(float(v) for v in boxes.xyxy[i].tolist())
            track_id = int(ids[i].item()) if ids is not None else -1
            rows.append((cls_id, raw, xyxy, float(boxes.conf[i].item()), track_id))
        return rows

    def track(self, frame) -> list[RawBox]:
        results = self.model.track(
            frame,
            persist=True,
            tracker=self.settings.tracker,
            imgsz=self.settings.imgsz,
            conf=self.settings.conf,
            iou=self.settings.iou,
            device=self.device,
            verbose=False,
        )
        return self._rows(results[0], tracked=True) if results else []

    def predict(self, frame, imgsz: int | None = None) -> list[RawBox]:
        results = self.model.predict(
            frame,
            imgsz=imgsz or self.settings.imgsz,
            conf=self.settings.conf,
            iou=self.settings.iou,
            device=self.device,
            verbose=False,
        )
        return self._rows(results[0], tracked=False) if results else []


class _RFDETRBackend:
    """RF-DETR checkpoint + a lightweight IoU tracker for cross-frame ids.

    RF-DETR's predict takes an RGB image and a confidence `threshold` (no NMS/iou,
    no imgsz — the model runs at its native resolution). The tracker is stateful,
    so a single instance is kept for the analytics pass and reset by the caller
    between videos via `reset_tracker()`.
    """

    def __init__(self):
        self.settings = get_settings()
        self.model = registry.get_rfdetr_logo_model()
        self.offset = self.settings.rfdetr_class_offset
        self._tracker = _IoUTracker()

    def reset_tracker(self) -> None:
        self._tracker = _IoUTracker()

    def _predict(self, frame):
        import cv2

        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        return self.model.predict(rgb, threshold=self.settings.rfdetr_conf)

    def _rows(self, dets, track: bool) -> list[RawBox]:
        n = len(dets.xyxy) if dets.xyxy is not None else 0
        boxes = [tuple(float(v) for v in dets.xyxy[i].tolist()) for i in range(n)]
        raw_cls = [int(dets.class_id[i]) if dets.class_id is not None else -1 for i in range(n)]
        if track:
            tracked = self._tracker.update(list(zip(boxes, raw_cls)))
        else:
            tracked = [(-1, raw_cls[i]) for i in range(n)]
        rows: list[RawBox] = []
        for i in range(n):
            track_id, cls_id = tracked[i]            # cls_id = voted brand on the tracked path
            raw = rfdetr_class_name(cls_id, self.offset)
            conf = float(dets.confidence[i]) if dets.confidence is not None else 0.0
            rows.append((cls_id, raw, boxes[i], conf, track_id))
        return rows

    def track(self, frame) -> list[RawBox]:
        return self._rows(self._predict(frame), track=True)

    def predict(self, frame, imgsz: int | None = None) -> list[RawBox]:
        # imgsz is ignored: RF-DETR runs at its fixed native resolution.
        return self._rows(self._predict(frame), track=False)


class LogoDetector:
    def __init__(self):
        self.settings = get_settings()
        if self.settings.logo_backend.lower() == "rfdetr":
            self.backend = _RFDETRBackend()
        else:
            self.backend = _YoloBackend()

    def reset_tracker(self) -> None:
        """Reset cross-frame track state (RF-DETR only; YOLO persists internally)."""
        reset = getattr(self.backend, "reset_tracker", None)
        if reset:
            reset()

    def _to_detections(self, rows: list[RawBox], t: float, w: int, h: int) -> list[Detection]:
        out: list[Detection] = []
        for cls_id, raw, xyxy, conf, track_id in rows:
            out.append(
                Detection(
                    t=t,
                    class_id=cls_id,
                    raw_name=raw,
                    brand_key=normalize_class(raw),
                    brand_name=display_name(raw),
                    conf=conf,
                    xyxy=xyxy,  # type: ignore[arg-type]
                    track_id=track_id,
                    frame_w=w,
                    frame_h=h,
                )
            )
        return out

    def infer(self, frame, t: float) -> list[Detection]:
        """Detect + track logos in one BGR frame at timestamp `t`."""
        h, w = frame.shape[:2]
        return self._to_detections(self.backend.track(frame), t, w, h)

    def detect_boxes(self, frame, t: float, imgsz: int | None = None) -> list[Detection]:
        """Plain per-frame detection (no tracker) for the full-fps preview pass.

        Runs at `imgsz` (smaller than analytics for speed, YOLO only) and returns
        boxes with track_id=-1; the preview doesn't need tracking, just every
        frame drawn.
        """
        h, w = frame.shape[:2]
        return self._to_detections(self.backend.predict(frame, imgsz=imgsz), t, w, h)
