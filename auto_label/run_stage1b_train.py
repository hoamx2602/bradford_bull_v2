"""Stage 1b proposer training — Windows-safe launcher.

Chạy YOLO26n class-agnostic proposer trên data/stage1b_ds.
Dùng __main__ guard (bắt buộc cho multiprocessing 'spawn' của Windows để
DataLoader workers không deadlock). Chạy trực tiếp bằng python.exe của env,
KHÔNG qua `conda run ... | tail` (đã gây treo).

    python auto_label/run_stage1b_train.py
"""
from __future__ import annotations

from ultralytics import YOLO


def main() -> None:
    model = YOLO("yolo26n.pt")
    model.train(
        data="data/stage1b_ds/data.yaml",
        model="yolo26n.pt",
        epochs=60,
        imgsz=640,
        batch=32,
        project="runs",
        name="stage1b_proposer",
        patience=15,
        workers=0,  # Windows: spawn workers re-import torch → paging-file OOM (WinError 1455)
        exist_ok=True,
    )


if __name__ == "__main__":
    main()
