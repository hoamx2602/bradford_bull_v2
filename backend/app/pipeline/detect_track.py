"""Stage 3 — logo detection + tracking.

Runs the fine-tuned logo detector on each sampled frame with tracking so
detections of the same physical logo across frames share a track_id. That id is
what lets the exposure stage group frames into a single "exposure event" and
de-duplicate (Production-System-Design.MD §5).

The detector itself is pluggable (DETECTOR_BACKEND): YOLO26m (.pt) via
ultralytics ByteTrack, or RF-DETR (.pth) via supervision ByteTrack. Both are
exposed through `app.models_zoo.detectors.LogoBackend` returning `RawBox`es, so
this stage builds the uniform `Detection` objects the same way for either model.
"""
from __future__ import annotations

from app.config import display_name, get_settings, normalize_class
from app.models_zoo import registry
from app.pipeline.datatypes import Detection


class LogoDetector:
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

    def infer(self, frame, t: float) -> list[Detection]:
        """Detect + track logos in one BGR frame at timestamp `t`."""
        h, w = frame.shape[:2]
        return self._to_detections(self.backend.track(frame), t, w, h)

    def detect_boxes(self, frame, t: float, imgsz: int | None = None) -> list[Detection]:
        """Plain per-frame detection (no tracker) for the full-fps preview pass.

        Runs at `imgsz` (smaller than analytics for speed, where the backend
        supports it) and returns boxes with track_id=-1; the preview doesn't need
        tracking, just every frame drawn.
        """
        h, w = frame.shape[:2]
        return self._to_detections(self.backend.detect(frame, imgsz), t, w, h)
