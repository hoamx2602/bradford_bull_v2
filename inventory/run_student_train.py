"""M3 smoke-test — train YOLO student trên crop nhãn-sạch bootstrap vòng 1.

Windows: __main__ guard + workers=0 (xem MIGRATION_WINDOWS.md).

    python inventory/run_student_train.py
"""
from __future__ import annotations

from ultralytics import YOLO


def main() -> None:
    model = YOLO("yolo26n.pt")
    model.train(
        data="data/inventory/student_ds/data.yaml",
        epochs=80,
        imgsz=640,
        batch=16,
        project="runs",
        name="student_v1",
        patience=25,
        workers=0,
        exist_ok=True,
    )


if __name__ == "__main__":
    main()
