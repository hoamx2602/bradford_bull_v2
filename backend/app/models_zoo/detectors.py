"""Logo-detector backends behind one interface.

Stage 3 (detect_track.py) used to call the ultralytics YOLO API directly. To let
the same pipeline run a fine-tuned **RF-DETR** checkpoint (.pth) instead of the
YOLO26m (.pt), per-frame inference is abstracted here. Each backend returns a
list of `RawBox` (class id, confidence, xyxy, track id) and the detector stage
builds the uniform `Detection` objects on top.

- `YoloBackend`   — ultralytics `.track()/.predict()` (default, unchanged path).
- `RFDetrBackend` — `rfdetr` model + `supervision.ByteTrack` for persistence.

The RF-DETR deps (`rfdetr`, `supervision`) are imported lazily so the YOLO path
never pays for them; install with `pip install -e ".[rfdetr]"`.
"""
from __future__ import annotations

import logging
from typing import NamedTuple

from app.config import RFDETR_CLASS_NAMES

log = logging.getLogger("app.models")


class RawBox(NamedTuple):
    cls_id: int
    conf: float
    xyxy: tuple[float, float, float, float]
    track_id: int


class LogoBackend:
    """Common surface used by `LogoDetector`."""

    names: dict[int, str]

    def track(self, frame) -> list[RawBox]:
        """Detect + track in one BGR frame (track ids persist across calls)."""
        raise NotImplementedError

    def detect(self, frame, imgsz: int | None = None) -> list[RawBox]:
        """Plain per-frame detection (no tracker); track_id is -1."""
        raise NotImplementedError

    def reset(self) -> None:
        """Drop tracker state so a new video starts fresh."""


# ── YOLO (ultralytics) ────────────────────────────────────────────────────
class YoloBackend(LogoBackend):
    def __init__(self, settings, device: str):
        from ultralytics import YOLO

        self.settings = settings
        self.device = device
        path = settings.resolved_model_path()
        log.info("loading logo model (yolo): %s", path)
        self.model = YOLO(path)
        self.names = self.model.names  # {class_id: raw_name}

    def track(self, frame) -> list[RawBox]:
        s = self.settings
        results = self.model.track(
            frame,
            persist=True,
            tracker=s.tracker,
            imgsz=s.imgsz,
            conf=s.conf,
            iou=s.iou,
            device=self.device,
            verbose=False,
        )
        return self._boxes(results, with_id=True)

    def detect(self, frame, imgsz: int | None = None) -> list[RawBox]:
        s = self.settings
        results = self.model.predict(
            frame,
            imgsz=imgsz or s.imgsz,
            conf=s.conf,
            iou=s.iou,
            device=self.device,
            verbose=False,
        )
        return self._boxes(results, with_id=False)

    @staticmethod
    def _boxes(results, with_id: bool) -> list[RawBox]:
        out: list[RawBox] = []
        if not results:
            return out
        boxes = getattr(results[0], "boxes", None)
        if boxes is None or boxes.shape[0] == 0:
            return out
        ids = boxes.id if with_id else None
        for i in range(boxes.shape[0]):
            cls_id = int(boxes.cls[i].item())
            xyxy = tuple(float(v) for v in boxes.xyxy[i].tolist())
            track_id = int(ids[i].item()) if ids is not None else -1
            out.append(RawBox(cls_id, float(boxes.conf[i].item()), xyxy, track_id))  # type: ignore[arg-type]
        return out


# ── RF-DETR (rfdetr + supervision) ────────────────────────────────────────
_RFDETR_VARIANTS = {
    "nano": "RFDETRNano",
    "small": "RFDETRSmall",
    "medium": "RFDETRMedium",
    "base": "RFDETRBase",
    "large": "RFDETRLarge",
    "2xlarge": "RFDETR2XLarge",
}


class RFDetrBackend(LogoBackend):
    def __init__(self, settings, device: str):
        import rfdetr  # lazy: optional dependency
        import supervision as sv

        self.settings = settings
        self._sv = sv

        variant = settings.rfdetr_variant.lower()
        cls_name = _RFDETR_VARIANTS.get(variant)
        if cls_name is None:
            raise ValueError(
                f"unknown rfdetr_variant {variant!r}; choose from {sorted(_RFDETR_VARIANTS)}"
            )
        ModelCls = getattr(rfdetr, cls_name)

        path = settings.resolved_rfdetr_model_path()
        # rfdetr auto-uses CUDA when present; the DINOv2 backbone has no MPS path,
        # so anything that isn't CUDA falls back to CPU.
        rf_device = "cuda" if device in ("0", "cuda") or device.isdigit() else "cpu"
        kwargs: dict = {"pretrain_weights": path, "device": rf_device}
        if settings.rfdetr_resolution:
            kwargs["resolution"] = settings.rfdetr_resolution
        if variant == "2xlarge":
            kwargs["accept_platform_model_license"] = True

        log.info("loading logo model (rfdetr/%s) on %s: %s", variant, rf_device, path)
        self.model = ModelCls(**kwargs)
        try:
            self.model.optimize_for_inference()
        except Exception as exc:  # pragma: no cover - best-effort speedup
            log.debug("rfdetr optimize_for_inference skipped: %s", exc)

        # COCO categories were [placeholder(id 0), brand_1 .. brand_17]; the model
        # emits the category id, so class_id - offset indexes RFDETR_BRAND_ORDER.
        off = settings.rfdetr_class_offset
        self.names = {i + off: b for i, b in enumerate(RFDETR_CLASS_NAMES)}
        self.tracker = sv.ByteTrack()

    def reset(self) -> None:
        self.tracker = self._sv.ByteTrack()

    def _predict(self, frame):
        # rfdetr expects RGB; OpenCV frames are BGR.
        # Channel reversal creates a negative-stride NumPy view; torchvision's
        # to_tensor cannot consume that layout, so materialise a contiguous copy.
        rgb = frame[:, :, ::-1].copy()
        return self.model.predict(rgb, threshold=self.settings.rfdetr_conf)

    def detect(self, frame, imgsz: int | None = None) -> list[RawBox]:
        # RF-DETR resizes internally to the variant resolution; imgsz is ignored.
        return self._to_boxes(self._predict(frame), track_ids=None)

    def track(self, frame) -> list[RawBox]:
        dets = self.tracker.update_with_detections(self._predict(frame))
        return self._to_boxes(dets, track_ids=getattr(dets, "tracker_id", None))

    @staticmethod
    def _to_boxes(dets, track_ids) -> list[RawBox]:
        out: list[RawBox] = []
        n = len(dets)
        for i in range(n):
            x1, y1, x2, y2 = (float(v) for v in dets.xyxy[i])
            cls_id = int(dets.class_id[i]) if dets.class_id is not None else -1
            conf = float(dets.confidence[i]) if dets.confidence is not None else 0.0
            tid = int(track_ids[i]) if track_ids is not None and track_ids[i] is not None else -1
            out.append(RawBox(cls_id, conf, (x1, y1, x2, y2), tid))
        return out


def load_logo_backend(settings, device: str) -> LogoBackend:
    backend = (settings.logo_backend or "yolo").lower()
    if backend == "rfdetr":
        return RFDetrBackend(settings, device)
    if backend == "yolo":
        return YoloBackend(settings, device)
    raise ValueError(f"unknown DETECTOR_BACKEND {backend!r}; expected 'yolo' or 'rfdetr'")
