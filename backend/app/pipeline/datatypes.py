"""Shared value objects passed between pipeline stages."""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class VideoMeta:
    duration_seconds: float
    fps: float
    width: int
    height: int
    frame_count: int


@dataclass
class Detection:
    """One logo detection in one sampled frame."""

    t: float                 # timestamp in seconds
    class_id: int
    raw_name: str            # model class name, e.g. "bartercard_home"
    brand_key: str           # normalized, e.g. "bartercard"
    brand_name: str          # display name, e.g. "Bartercard"
    conf: float
    xyxy: tuple[float, float, float, float]
    track_id: int            # -1 if the tracker produced no id this frame
    frame_w: int
    frame_h: int
    visibility: float = 0.0  # filled by visibility stage
    body_zone: str | None = None  # filled by body-zone stage
    # Team-filter verdict: True = on a target-team player (keep), False = on an
    # opponent/referee or unattached (drop). None = stage disabled.
    on_target_team: bool | None = None

    @property
    def cx(self) -> float:
        return (self.xyxy[0] + self.xyxy[2]) / 2

    @property
    def cy(self) -> float:
        return (self.xyxy[1] + self.xyxy[3]) / 2

    @property
    def area(self) -> float:
        return max(0.0, self.xyxy[2] - self.xyxy[0]) * max(0.0, self.xyxy[3] - self.xyxy[1])


@dataclass
class PersonPose:
    """One detected person with COCO-17 keypoints in one frame."""

    xyxy: tuple[float, float, float, float]
    # 17 keypoints, each (x, y, conf). COCO order.
    keypoints: list[tuple[float, float, float]] = field(default_factory=list)
