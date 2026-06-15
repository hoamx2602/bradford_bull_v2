#!/usr/bin/env python3
"""
Train the sponsor-logo detector (17 brand classes) on 1080p rugby frames.

    conda activate bradford_bulls
    python train.py                       # yolo26m @ 1280, tuned defaults
    python train.py --model yolo26l.pt    # more capacity (only if underfitting)
    python train.py --epochs 200 --batch 12

Dataset: ~2456 frames, 17 brand classes (home/away merged via
scripts/merge_home_away.py — downstream is kit-agnostic), RTX 4500 Ada 20GB.
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

After the home/away merge the smallest class is cch=74 instances (was cch_home=7),
so imbalance is much milder. Still judge the model on the well-sampled brands +
false-positive rate; cch / mna_* remain the thinnest and benefit most from more data.
"""
import argparse
import os

# Must be set BEFORE torch/CUDA initializes (i.e. before importing ultralytics).
# Reduces fragmentation OOM ("reserved but unallocated") on the 24GB card.
os.environ.setdefault("PYTORCH_CUDA_ALLOC_CONF", "expandable_segments:True")

from pathlib import Path

from ultralytics import YOLO

HERE = Path(__file__).resolve().parent


def patch_motion_blur(mb_p=0.30, blur_limit=(3, 15)):
    """Inject MotionBlur into Ultralytics' Albumentations pipeline.

    Ultralytics only runs Albumentations if the package is installed, and its
    built-in set (Blur/MedianBlur/ToGray/CLAHE at p=0.01) has NO motion blur. Our
    frames are broadcast sampled at ~2 fps -> heavy motion blur on moving players,
    and recall on blurred logos is the weak point. MotionBlur is a PIXEL-level
    transform (it does not move boxes), so we add it without touching bbox_params.
    blur_limit is kept moderate so the ~10% of boxes that are tiny (<32 px) are not
    smeared into nothing — they must stay learnable. p<1 keeps sharp examples too.
    Returns True if the patch was applied.
    """
    if mb_p <= 0:
        print("[aug] motion blur OFF (mb_p=0)")
        return False
    try:
        import albumentations as A
        from ultralytics.data import augment as aug
    except ImportError:
        print("[aug] albumentations not installed — motion blur OFF "
              "(pip install albumentations)")
        return False

    _orig_init = aug.Albumentations.__init__

    def __init__(self, p=1.0, transforms=None):
        if transforms is None:  # mirror Ultralytics' defaults + MotionBlur
            transforms = [
                A.Blur(p=0.01),
                A.MedianBlur(p=0.01),
                A.ToGray(p=0.01),
                A.CLAHE(p=0.01),
                A.MotionBlur(blur_limit=blur_limit, p=mb_p),
            ]
        _orig_init(self, p, transforms)

    aug.Albumentations.__init__ = __init__
    print(f"[aug] MotionBlur injected (blur_limit={blur_limit}, p={mb_p})")
    return True


def init_wandb(args):
    """Pre-init wandb with a clean project name.

    ultralytics 8.4.45's wb callback passes `args.project` (here a Windows path
    'C:\\...\\runs') straight to wandb as the project NAME, which wandb rejects
    (it forbids '\\' and ':'). Its callback skips init if a run already exists, so
    we create the run first with a valid name and it reuses ours. Set the project
    via $env:WANDB_PROJECT, else default below. No-op if wandb isn't enabled.
    """
    try:
        from ultralytics.utils import SETTINGS
        if not SETTINGS.get("wandb"):
            return
        import wandb
        if wandb.run is None:
            wandb.init(
                project=os.environ.get("WANDB_PROJECT", "bradford-logo-detection"),
                name=args.name,
            )
            print(f"[wandb] logging to project "
                  f"'{os.environ.get('WANDB_PROJECT', 'bradford-logo-detection')}'")
    except Exception as e:  # never let logging block training
        print(f"[wandb] disabled ({e})")


def main(args):
    data = (HERE / args.data).resolve()
    if not data.exists():
        raise SystemExit(f"{data} not found — run resplit_data.py / prepare first.")

    init_wandb(args)
    patch_motion_blur(args.mb_p)        # 2 fps broadcast -> simulate motion blur
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
    p.add_argument("--mb_p", type=float, default=0.30,
                   help="MotionBlur probability (0 disables). Matches 2 fps broadcast blur.")
    p.add_argument("--name", default="logo_yolo26m_17cls")
    main(p.parse_args())
