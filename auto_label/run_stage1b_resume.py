"""Resume Stage 1b proposer training từ checkpoint last.pt.

Dùng khi train bị ngắt (vd session teardown). Ultralytics đọc lại toàn bộ
args gốc từ checkpoint (epochs=60, workers=0, ...) nên không cần truyền lại.

    python auto_label/run_stage1b_resume.py
"""
from __future__ import annotations

from pathlib import Path

from ultralytics import YOLO

CKPT = Path("runs/detect/runs/stage1b_proposer/weights/last.pt")


def main() -> None:
    model = YOLO(str(CKPT))
    model.train(resume=True)


if __name__ == "__main__":
    main()
