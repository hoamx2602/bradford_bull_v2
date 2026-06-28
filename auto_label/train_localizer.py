"""Phase 1 — distill pseudo-label SAM 3 → YOLOv11-OBB localizer (class-agnostic).

Tầng 1 trong kiến trúc 2 tầng (xem `../autolabel.md`, `../expert_review_and_plan.md`).
Teacher = SAM 3 (exemplar auto-label, OBB từ mask). Student = YOLOv11-OBB nhẹ,
chạy real-time, **1 lớp `logo`** → tổng quát giữa club/môn; định danh brand để
Tầng 2 (embedding) lo.

Hai lệnh con:
  train    — huấn luyện YOLOv11-OBB trên dataset auto-label
  predict  — chạy model lên ảnh gold → xuất nhãn OBB (+conf) cho `eval_obb.py`

Tiền đề dataset (do `sam3_exemplar_autolabel.py --obb --class-agnostic` sinh):
    data/auto_label/
      images/*.jpg
      labels/*.txt        # "0 x1 y1 x2 y2 x3 y3 x4 y4"  (OBB normalized)
      data.yaml           # nc: 1 / names: {0: logo}

Chạy (máy GPU):
    # 1) auto-label OBB class-agnostic
    python auto_label/sam3_exemplar_autolabel.py --video V.mp4 --logos "Sponsor Logo" \
        --backend sam3 --weights sam3.pt --device cuda:0 --obb --class-agnostic \
        --out data/auto_label
    # 2) train student
    python auto_label/train_localizer.py train --data data/auto_label/data.yaml \
        --model yolo11n-obb.pt --epochs 100 --imgsz 1280 --device 0
    # 3) chấm trên gold set → eval
    python auto_label/train_localizer.py predict --weights runs/obb/train/weights/best.pt \
        --images data/gold/images --out data/pred --imgsz 1280 --conf 0.25
    python auto_label/eval_obb.py --gold data/gold --pred data/pred

Smoke-test không cần weights (kiểm orchestration ghi nhãn):
    python auto_label/train_localizer.py selftest-predict --out /tmp/p
"""
from __future__ import annotations

import argparse
from pathlib import Path

IMG_EXT = {".jpg", ".jpeg", ".png", ".bmp"}


# --------------------------------------------------------------------------- #
# train
# --------------------------------------------------------------------------- #

def cmd_train(a: argparse.Namespace) -> None:
    from ultralytics import YOLO  # import trễ: chỉ cần khi train thật

    if not Path(a.data).is_file():
        raise SystemExit(f"Không thấy data.yaml: {a.data}")
    model = YOLO(a.model)  # vd. yolo11n-obb.pt / yolo11s-obb.pt
    # project tuyệt đối → tránh Ultralytics lồng vào runs_dir mặc định
    project = Path(a.project).resolve()
    model.train(
        data=str(a.data),
        epochs=a.epochs,
        imgsz=a.imgsz,
        batch=a.batch,
        device=a.device,
        project=str(project),
        name=a.name,
        # blur-robustness: tăng augmentation mô phỏng broadcast (xem Motion-blur.MD)
        # — KHÔNG deblur lúc train; cho model thấy frame mờ.
        degrees=a.degrees,      # xoay nhẹ (logo nghiêng)
        translate=0.1, scale=0.5, fliplr=0.5,
        mosaic=1.0, close_mosaic=10,
    )
    save_dir = getattr(model.trainer, "save_dir", project / a.name)
    print(f"[train] xong → {save_dir}/weights/best.pt")


# --------------------------------------------------------------------------- #
# predict → nhãn OBB cho eval_obb.py
# --------------------------------------------------------------------------- #

def _write_obb_label(out_lbl: Path, stem: str, rows: list[str]) -> None:
    (out_lbl / f"{stem}.txt").write_text("\n".join(rows))


def _obb_rows_from_result(res, class_agnostic: bool) -> list[str]:
    """Result Ultralytics OBB → list dòng 'cls x1 y1 ... x4 y4 conf' (normalized)."""
    h, w = res.orig_shape  # (H, W)
    rows: list[str] = []
    obb = getattr(res, "obb", None)
    if obb is not None and getattr(obb, "xyxyxyxy", None) is not None and len(obb):
        polys = obb.xyxyxyxy.cpu().numpy()        # (N,4,2) pixel
        confs = obb.conf.cpu().numpy()
        clss = obb.cls.cpu().numpy().astype(int)
        for poly, c, cl in zip(polys, confs, clss):
            cid = 0 if class_agnostic else int(cl)
            coords = " ".join(f"{x / w:.6f} {y / h:.6f}" for x, y in poly)
            rows.append(f"{cid} {coords} {float(c):.6f}")
        return rows
    # fallback: model HBB thường → quy box thành quad axis-aligned
    boxes = getattr(res, "boxes", None)
    if boxes is not None and len(boxes):
        xyxy = boxes.xyxy.cpu().numpy()
        confs = boxes.conf.cpu().numpy()
        clss = boxes.cls.cpu().numpy().astype(int)
        for (x0, y0, x1, y1), c, cl in zip(xyxy, confs, clss):
            cid = 0 if class_agnostic else int(cl)
            quad = [(x0, y0), (x1, y0), (x1, y1), (x0, y1)]
            coords = " ".join(f"{x / w:.6f} {y / h:.6f}" for x, y in quad)
            rows.append(f"{cid} {coords} {float(c):.6f}")
    return rows


def cmd_predict(a: argparse.Namespace) -> None:
    from ultralytics import YOLO

    imgs = sorted(p for p in Path(a.images).iterdir() if p.suffix.lower() in IMG_EXT)
    if not imgs:
        raise SystemExit(f"Không có ảnh trong {a.images}")
    out_lbl = Path(a.out) / "labels"
    out_lbl.mkdir(parents=True, exist_ok=True)

    model = YOLO(a.weights)
    n_box = 0
    for p in imgs:
        res = model.predict(str(p), imgsz=a.imgsz, conf=a.conf,
                            device=a.device, verbose=False)[0]
        rows = _obb_rows_from_result(res, a.class_agnostic)
        _write_obb_label(out_lbl, p.stem, rows)
        n_box += len(rows)
    print(f"[predict] {len(imgs)} ảnh → {n_box} box  ({out_lbl})")
    print(f"[next] python auto_label/eval_obb.py --gold <gold> --pred {a.out}")


def cmd_selftest_predict(a: argparse.Namespace) -> None:
    """Kiểm orchestration ghi nhãn mà KHÔNG cần ultralytics/weights/GPU:
    dùng một result giả mô phỏng interface .obb của Ultralytics."""
    import numpy as np

    class _OBB:
        def __init__(self):
            self.xyxyxyxy = _T(np.array([[[10, 10], [50, 12], [48, 40], [8, 38]]],
                                        dtype=float))
            self.conf = _T(np.array([0.87]))
            self.cls = _T(np.array([0]))
        def __len__(self): return 1

    class _T:
        def __init__(self, a): self.a = a
        def cpu(self): return self
        def numpy(self): return self.a

    class _Res:
        orig_shape = (100, 200)
        obb = _OBB()
        boxes = None

    out_lbl = Path(a.out) / "labels"; out_lbl.mkdir(parents=True, exist_ok=True)
    rows = _obb_rows_from_result(_Res(), class_agnostic=True)
    _write_obb_label(out_lbl, "frame_000001", rows)
    assert len(rows) == 1 and rows[0].startswith("0 ") and rows[0].count(" ") == 9
    txt = (out_lbl / "frame_000001.txt").read_text().strip()
    print("  wrote:", txt)
    print("  selftest-predict: OK ✅ (9 token sau class, có conf cuối)")


# --------------------------------------------------------------------------- #
# CLI
# --------------------------------------------------------------------------- #

def main() -> None:
    ap = argparse.ArgumentParser(description="Phase 1 — YOLOv11-OBB localizer")
    sub = ap.add_subparsers(dest="cmd", required=True)

    t = sub.add_parser("train", help="huấn luyện YOLOv11-OBB")
    t.add_argument("--data", required=True, help="data.yaml (nc:1 names:{0:logo})")
    t.add_argument("--model", default="yolo11n-obb.pt",
                   help="weights khởi tạo (yolo11{n,s,m}-obb.pt)")
    t.add_argument("--epochs", type=int, default=100)
    t.add_argument("--imgsz", type=int, default=1280, help="logo nhỏ → ảnh lớn")
    t.add_argument("--batch", type=int, default=16)
    t.add_argument("--device", default="0")
    t.add_argument("--degrees", type=float, default=10.0, help="xoay augmentation")
    t.add_argument("--project", default="runs/obb")
    t.add_argument("--name", default="train")
    t.set_defaults(func=cmd_train)

    p = sub.add_parser("predict", help="chấm gold → nhãn OBB cho eval_obb.py")
    p.add_argument("--weights", required=True)
    p.add_argument("--images", required=True, help="thư mục ảnh (vd gold/images)")
    p.add_argument("--out", required=True, help="thư mục pred (sẽ tạo labels/)")
    p.add_argument("--imgsz", type=int, default=1280)
    p.add_argument("--conf", type=float, default=0.25)
    p.add_argument("--device", default="0")
    p.add_argument("--class-agnostic", dest="class_agnostic", action="store_true",
                   default=True, help="ép mọi class về 0 (mặc định bật cho Tầng 1)")
    p.add_argument("--keep-class", dest="class_agnostic", action="store_false",
                   help="giữ class gốc của model")
    p.set_defaults(func=cmd_predict)

    s = sub.add_parser("selftest-predict",
                       help="kiểm ghi nhãn OBB không cần ultralytics/GPU")
    s.add_argument("--out", required=True)
    s.set_defaults(func=cmd_selftest_predict)

    a = ap.parse_args()
    a.func(a)


if __name__ == "__main__":
    main()
