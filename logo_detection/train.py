#!/usr/bin/env python3
"""
Train the sponsor-logo detector (32 classes) on 1080p rugby frames.

    conda activate bradford_bulls
    python train.py                       # yolo26m @ 1280, tuned defaults
    python train.py --model yolo26l.pt    # more capacity (only if underfitting)
    python train.py --epochs 200 --batch 12

Dataset: ~2456 frames, 32 classes (home/away sponsor logos), RTX 4500 Ada 20GB.
Split is CLIP-LEVEL (scripts/resplit_data.py) so val mAP is an honest estimate of
performance on unseen matches — NOT a near-duplicate echo of train. Optimize against
val mAP; if train mAP >> val mAP the model is overfitting.

Why the augmentation is tuned the way it is (these are deliberate, non-default):
  * fliplr = 0.0  -> many logos are WORDMARKS (aon, klg, mcp, top_notch...). A
    horizontal flip creates mirror-text that never occurs in footage and corrupts
    the brand signature. (Ultralytics default is 0.5 — wrong for fine-grained logos.)
  * hsv_h = 0.010 -> *_home vs *_away is the SAME logo distinguished mostly by
    jersey color. Large hue jitter pushes one team's color toward the other's, so
    keep it small. Saturation/brightness jitter stays generous for broadcast light.
  * imgsz 1280 + mosaic + scale jitter -> logos are tiny and appear at many sizes
    (player near vs far); resolution and scale aug matter more than model size.
  * erasing 0.40 -> rugby has heavy occlusion (players block logos).
  * mixup 0.10   -> light regularizer against overfitting on a small dataset.

Rare classes (cch_home=7, chadlaw_home=22, mna_cladding_home=29 instances) are
data-starved; their per-class mAP is statistical noise no matter the settings.
Judge the model on the well-sampled classes + false-positive rate, and collect
more data for the rare `*_home` logos.
"""
import argparse
from pathlib import Path

from ultralytics import YOLO

HERE = Path(__file__).resolve().parent


def main(args):
    data = (HERE / args.data).resolve()
    if not data.exists():
        raise SystemExit(f"{data} not found — run resplit_data.py / prepare first.")

    model = YOLO(args.model)
    model.train(
        # ---- data / model ----
        data=str(data),
        imgsz=args.imgsz,            # 1280: 1080p source + small logos
        pretrained=True,             # COCO transfer -> better on limited data
        project=str(HERE / "runs"),
        name=args.name,
        device=args.device,
        seed=0,
        deterministic=True,

        # ---- schedule / anti-overfit ----
        epochs=args.epochs,          # high ceiling; patience decides the real stop
        patience=args.patience,      # early-stop on val mAP plateau
        batch=args.batch,            # -1 = auto-fit (~60% VRAM)
        optimizer="auto",
        cos_lr=True,                 # smooth LR decay
        lr0=0.01, lrf=0.01,
        weight_decay=0.0005,
        warmup_epochs=3.0,
        close_mosaic=25,             # last 25 epochs on real layouts (no mosaic)
        cache=args.cache,

        # ---- loss ----
        box=7.5,
        cls=0.5,                     # raise ~0.7 if confusion matrix shows brand mixups
        dfl=1.5,

        # ---- augmentation (tuned — see module docstring) ----
        hsv_h=0.010,                 # LOW: protect home/away color identity
        hsv_s=0.70,
        hsv_v=0.50,
        degrees=5.0,                 # slight tilt (bodies lean)
        translate=0.10,
        scale=0.50,                  # multi-size small-logo robustness
        shear=0.0,
        perspective=0.0,
        flipud=0.0,                  # logos never upside down
        fliplr=0.0,                  # OFF: mirror-text breaks wordmark identity
        mosaic=1.0,
        mixup=0.10,                  # light regularizer
        copy_paste=0.0,
        erasing=0.40,                # occlusion robustness

        val=True,
        plots=True,
    )

    best = HERE / "runs" / args.name / "weights" / "best.pt"
    print(f"\nBest weights -> {best}")
    print("\n=== Honest eval on clip-level val set (best.pt) ===")
    m = YOLO(str(best)).val(data=str(data), imgsz=args.imgsz, plots=True)
    print(f"mAP50-95 {m.box.map:.4f}   mAP50 {m.box.map50:.4f}   "
          f"P {m.box.mp:.3f}  R {m.box.mr:.3f}")
    print("Per-class mAP50-95 (watch the low ones = need more data):")
    for i, ap in enumerate(m.box.maps):
        print(f"  {m.names[i]:<28} {ap:.4f}")


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--data", default="data/data.yaml")
    p.add_argument("--model", default="yolo26m.pt",
                   choices=["yolo26n.pt", "yolo26s.pt", "yolo26m.pt", "yolo26l.pt"])
    p.add_argument("--imgsz", type=int, default=1280)
    p.add_argument("--epochs", type=int, default=300)
    p.add_argument("--batch", type=int, default=-1, help="-1 = auto-fit VRAM")
    p.add_argument("--patience", type=int, default=60)
    p.add_argument("--device", default="0")
    p.add_argument("--cache", default=False,
                   help="False | 'ram' | 'disk' — 'ram' speeds I/O if you have spare RAM")
    p.add_argument("--name", default="logo_yolo26m_clipsplit")
    main(p.parse_args())
