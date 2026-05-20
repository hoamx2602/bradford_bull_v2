import numpy as np
import torch
from ultralytics import YOLO


class PersonDetector:
    def __init__(
        self,
        weights: str = 'yolov8n.pt',
        conf: float = 0.35,
        device: str | None = None,
    ) -> None:
        if device is None:
            device = 'cuda' if torch.cuda.is_available() else 'cpu'
        self.device = device
        self.conf = conf
        self.model = YOLO(weights)
        self.model.to(device)
        self.model.predict(
            np.zeros((640, 640, 3), dtype=np.uint8),
            verbose=False, classes=[0],
        )

    def detect(
        self,
        frame_bgr: np.ndarray,
        min_height_frac: float = 0.08,
    ) -> list[tuple[int, int, int, int]]:
        """Return [(x1,y1,x2,y2)] for every person whose height >= min_height_frac * frame height."""
        H = frame_bgr.shape[0]
        res = self.model.predict(
            frame_bgr, classes=[0], verbose=False,
            imgsz=640, conf=self.conf, device=self.device,
        )
        boxes = res[0].boxes
        if boxes is None or len(boxes) == 0:
            return []
        xyxy = boxes.xyxy.cpu().numpy().astype(int)
        return [
            (int(x1), int(y1), int(x2), int(y2))
            for x1, y1, x2, y2 in xyxy
            if (y2 - y1) >= H * min_height_frac
        ]
