#!/usr/bin/env python3
"""
Train a yolo26 logo detector on the prepared dataset.

Run prepare_data.py first to build data/data.yaml, then:
    python train.py                         # yolo26m @ 1280, sensible defaults
    python train.py --model yolo26s.pt      # lighter / faster
    python train.py --epochs 200 --batch 8

Notes for this dataset (≈230 train imgs, 17 small-logo classes, RTX 4500 Ada 24GB)
--------------------------------------------------------------------------------
* yolo26m is the sweet spot: enough capacity for small logos without the overfit
  risk of l/x on a small dataset. Use yolo26s if you see train/val divergence.
* imgsz 1280 matters more than model size here — logos are tiny. The 24GB card
  handles 1280 comfortably (batch auto-fits).
* High patience + the val set drive early stopping; best.pt is what you deploy.
* mAP on the 3 rare logos (aon_away/cch/chadlaw) is meaningless — too few samples.
  Judge the model on the common logos and on false-positive rate.
"""
import argparse
from pathlib import Path

from ultralytics import YOLO

HERE = Path(__file__).resolve().parent


def main(args):
    data = (HERE / args.data).resolve()
    if not data.exists():
        raise SystemExit(
            f"{data} not found — run `python prepare_data.py` first.")

    model = YOLO(args.model)
    model.train(
        data=str(data),
        imgsz=args.imgsz,
        epochs=args.epochs,
        batch=args.batch,
        patience=args.patience,
        device=args.device,
        project=str(HERE / 'runs'),
        name=args.name,
        # small-object / small-dataset friendly settings
        cos_lr=True,
        close_mosaic=15,        # turn off mosaic for the last epochs to settle boxes
        mosaic=1.0,
        scale=0.5,
        fliplr=0.5,
        # logos are not vertically symmetric and orientation is meaningful → no flipud
        flipud=0.0,
        seed=0,
        plots=True,
    )
    print(f"\nBest weights → {HERE / 'runs' / args.name / 'weights' / 'best.pt'}")
    print("Validate / inspect with:")
    print(f"  yolo detect val  model=runs/{args.name}/weights/best.pt data={data}")
    print(f"  yolo detect predict model=runs/{args.name}/weights/best.pt "
          f"source=<img_or_video> imgsz={args.imgsz} conf=0.25")


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('--data',     default='data/data.yaml')
    p.add_argument('--model',    default='yolo26m.pt',
                   choices=['yolo26n.pt', 'yolo26s.pt', 'yolo26m.pt', 'yolo26l.pt'])
    p.add_argument('--imgsz',    type=int, default=1280)
    p.add_argument('--epochs',   type=int, default=150)
    p.add_argument('--batch',    type=int, default=-1,
                   help='-1 = auto-fit to GPU memory')
    p.add_argument('--patience', type=int, default=40,
                   help='Early-stop after N epochs without val improvement')
    p.add_argument('--device',   default='0')
    p.add_argument('--name',     default='logo_yolo26m')
    main(p.parse_args())
