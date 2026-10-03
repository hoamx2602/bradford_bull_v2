"""Rank validation images for a compact qualitative detection figure."""
from __future__ import annotations

import argparse
from pathlib import Path

from ultralytics import YOLO


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "training-result" / "data" / "valid"
WEIGHTS = ROOT / "logo_detection" / "runs" / "logo_yolo26m_clipsplit" / "weights" / "best.pt"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=200)
    parser.add_argument("--top", type=int, default=25)
    args = parser.parse_args()

    model = YOLO(str(WEIGHTS))
    rows = []
    for path in sorted(DATA.glob("*.jpg"))[: args.limit]:
        result = model.predict(path, imgsz=1280, conf=0.25, device=0, verbose=False)[0]
        confidences = [float(box.conf) for box in result.boxes]
        brands = {model.names[int(box.cls)].rsplit("_", 1)[0] for box in result.boxes}
        rows.append(
            (
                len(confidences),
                len(brands),
                min(confidences, default=1.0),
                max(confidences, default=0.0),
                path.name,
            )
        )

    for row in sorted(rows, reverse=True)[: args.top]:
        print(row)


if __name__ == "__main__":
    main()
