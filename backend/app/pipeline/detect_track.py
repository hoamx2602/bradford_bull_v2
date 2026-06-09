"""Stage 3 — logo detection + tracking.

Runs the fine-tuned YOLO26m on each sampled frame with ByteTrack persistence so
detections of the same physical logo across frames share a track_id. That id is
what lets the exposure stage group frames into a single "exposure event" and
de-duplicate (Production-System-Design.MD §5).
"""
from __future__ import annotations

from app.config import display_name, get_settings, normalize_class
from app.models_zoo import registry
from app.pipeline.datatypes import Detection


class LogoDetector:
    def __init__(self):
        self.settings = get_settings()
        self.model = registry.get_logo_model()
        self.device = registry.device()
        self.names = self.model.names  # {class_id: raw_name}

    def infer(self, frame, t: float) -> list[Detection]:
        """Detect + track logos in one BGR frame at timestamp `t`."""
        h, w = frame.shape[:2]
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
        out: list[Detection] = []
        if not results:
            return out
        res = results[0]
        boxes = getattr(res, "boxes", None)
        if boxes is None or boxes.shape[0] == 0:
            return out

        ids = boxes.id
        for i in range(boxes.shape[0]):
            cls_id = int(boxes.cls[i].item())
            raw = self.names.get(cls_id, str(cls_id))
            xyxy = tuple(float(v) for v in boxes.xyxy[i].tolist())
            track_id = int(ids[i].item()) if ids is not None else -1
            out.append(
                Detection(
                    t=t,
                    class_id=cls_id,
                    raw_name=raw,
                    brand_key=normalize_class(raw),
                    brand_name=display_name(raw),
                    conf=float(boxes.conf[i].item()),
                    xyxy=xyxy,  # type: ignore[arg-type]
                    track_id=track_id,
                    frame_w=w,
                    frame_h=h,
                )
            )
        return out
