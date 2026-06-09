"""Stage 4 — pose estimation.

Stock YOLO11-pose gives person boxes + COCO-17 keypoints per frame. The keypoints
drive body-zone reconstruction in bodyzones.py so we can attribute each logo to
the body region it sits on (chest / sleeve / shoulder ...).

This is intentionally a separate model from the YOLO26m logo detector: that model
is detect-only and cannot output human keypoints. YOLO26 has no pose variant in
ultralytics yet, so YOLO11-pose (the newest pose generation) is used here.
"""
from __future__ import annotations

from app.config import get_settings
from app.models_zoo import registry
from app.pipeline.datatypes import PersonPose


class PoseEstimator:
    def __init__(self):
        self.settings = get_settings()
        self.model = registry.get_pose_model()
        self.device = registry.device()

    def infer(self, frame) -> list[PersonPose]:
        results = self.model.predict(
            frame,
            imgsz=min(self.settings.imgsz, 960),  # pose doesn't need full 1280
            conf=0.35,
            device=self.device,
            verbose=False,
        )
        out: list[PersonPose] = []
        if not results:
            return out
        res = results[0]
        boxes = getattr(res, "boxes", None)
        kpts = getattr(res, "keypoints", None)
        if boxes is None or boxes.shape[0] == 0:
            return out

        kp_data = kpts.data if kpts is not None else None  # (n,17,3)
        for i in range(boxes.shape[0]):
            xyxy = tuple(float(v) for v in boxes.xyxy[i].tolist())
            keypoints: list[tuple[float, float, float]] = []
            if kp_data is not None and i < kp_data.shape[0]:
                for k in range(kp_data.shape[1]):
                    x, y, c = (float(v) for v in kp_data[i, k].tolist())
                    keypoints.append((x, y, c))
            out.append(PersonPose(xyxy=xyxy, keypoints=keypoints))  # type: ignore[arg-type]
        return out
