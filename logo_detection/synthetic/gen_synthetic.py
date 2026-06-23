#!/usr/bin/env python3
"""
Synthetic copy-paste generator for the CLASS-AGNOSTIC logo Localizer (autolabel.md
Tang 1, Bac 1 — section 3.2(a) / 8.2).

What it does
------------
Paste REAL logo assets (PNG/SVG-exported with alpha) onto REAL match frames with
heavy domain randomization, and emit YOLO labels with a SINGLE class `logo`.
Boxes are generated automatically from the pasted alpha mask -> pixel-perfect, zero
hand annotation.

Golden rule (autolabel.md 8.1): the logo itself is ALWAYS the real asset. We only
randomize the *context* (scale, rotation, perspective, light, blur, occlusion,
compression). We never let a generative model invent the logo.

Why paste onto the existing annotated frames
--------------------------------------------
The old closed-set dataset (logo_detection/data) already has ~4100 frames with
17-class boxes. Those frames already CONTAIN real logos. If we pasted synthetic
logos and labeled only the pasted ones, the real logos would become unlabeled
positives -> the detector is taught "logo = background" on them. So we READ each
frame's existing label, collapse all 17 classes -> class 0 (`logo`), and ADD the
pasted boxes on top. Result: every logo in the output image is labeled `logo`.

(You can also point --backgrounds at clean, logo-free frames; then leave
--bg-labels empty and only the pasted boxes are written.)

Usage
-----
    conda activate bradford_bulls
    python gen_synthetic.py                 # 4000 imgs, real frames as bg, 90/10 split
    python gen_synthetic.py --n 8000 --max-logos 5
    python gen_synthetic.py --no-bg-labels  # ignore old labels (clean-bg mode)

Output (default logo_detection/synthetic/data_synth):
    images/train/*.jpg  labels/train/*.txt
    images/val/*.jpg    labels/val/*.txt
    data.yaml           (nc: 1, names: ['logo'])
"""
import argparse
import math
import random
from pathlib import Path

import cv2
import numpy as np

HERE = Path(__file__).resolve().parent
LOGO_ROOT = (HERE / ".." / ".." / "Sponsor Logo").resolve()
BG_IMAGES = (HERE / ".." / "data" / "train" / "images").resolve()
BG_LABELS = (HERE / ".." / "data" / "train" / "labels").resolve()


# ----------------------------------------------------------------------------- IO
def imread_unicode(path, flags=cv2.IMREAD_UNCHANGED):
    """cv2.imread that survives Windows paths with spaces/brackets/non-ascii."""
    data = np.fromfile(str(path), dtype=np.uint8)
    if data.size == 0:
        return None
    return cv2.imdecode(data, flags)


def imwrite_unicode(path, img, params=None):
    ext = Path(path).suffix
    ok, buf = cv2.imencode(ext, img, params or [])
    if ok:
        buf.tofile(str(path))
    return ok


# -------------------------------------------------------------------- logo assets
def to_rgba(img, white_thresh):
    """Return HxWx4 uint8. If the asset has no alpha (JPG / flattened PNG), make a
    mask by knocking out a near-white background — most sponsor sheets are white bg.
    """
    if img is None:
        return None
    if img.ndim == 2:
        img = cv2.cvtColor(img, cv2.COLOR_GRAY2BGR)
    if img.shape[2] == 4:
        return img
    bgr = img[:, :, :3]
    # near-white -> transparent
    white = np.all(bgr >= white_thresh, axis=2)
    alpha = np.where(white, 0, 255).astype(np.uint8)
    # if "white removal" nuked almost everything, the asset wasn't on white -> keep opaque
    if alpha.mean() < 8:
        alpha = np.full(bgr.shape[:2], 255, np.uint8)
    return np.dstack([bgr, alpha])


def tight_crop(rgba):
    """Crop to the non-transparent bounding box so scaling is to the real mark."""
    a = rgba[:, :, 3]
    ys, xs = np.where(a > 10)
    if len(xs) == 0:
        return rgba
    return rgba[ys.min():ys.max() + 1, xs.min():xs.max() + 1]


def load_logos(logo_dir, white_thresh):
    assets = []
    for f in sorted(Path(logo_dir).iterdir()):
        if f.suffix.lower() not in (".png", ".jpg", ".jpeg", ".webp"):
            continue
        if f.stat().st_size == 0:        # e.g. romantica black.jpg is 0 bytes
            print(f"[skip] empty file: {f.name}")
            continue
        raw = imread_unicode(f)
        rgba = to_rgba(raw, white_thresh)
        if rgba is None or min(rgba.shape[:2]) < 8:
            print(f"[skip] unreadable: {f.name}")
            continue
        assets.append((f.stem, tight_crop(rgba)))
    if not assets:
        raise SystemExit(f"No usable logos found in {logo_dir}")
    print(f"[logos] loaded {len(assets)} assets from {logo_dir}")
    return assets


# ------------------------------------------------------------ domain randomization
def jitter_color(rgba, rng):
    bgr = rgba[:, :, :3].astype(np.float32)
    bgr *= rng.uniform(0.75, 1.20)                       # brightness
    mean = bgr.mean(axis=(0, 1), keepdims=True)
    bgr = mean + (bgr - mean) * rng.uniform(0.7, 1.3)    # contrast
    for c in range(3):                                   # mild per-channel tint
        bgr[:, :, c] *= rng.uniform(0.92, 1.08)
    rgba = rgba.copy()
    rgba[:, :, :3] = np.clip(bgr, 0, 255).astype(np.uint8)
    return rgba


def motion_blur(rgba, rng, k):
    ang = rng.uniform(0, math.pi)
    kern = np.zeros((k, k), np.float32)
    cx = k // 2
    for i in range(k):
        x = int(round(cx + (i - cx) * math.cos(ang)))
        y = int(round(cx + (i - cx) * math.sin(ang)))
        if 0 <= x < k and 0 <= y < k:
            kern[y, x] = 1
    s = kern.sum()
    if s == 0:
        return rgba
    kern /= s
    return cv2.filter2D(rgba, -1, kern)


def warp_perspective(rgba, rng, strength):
    h, w = rgba.shape[:2]
    src = np.float32([[0, 0], [w, 0], [w, h], [0, h]])
    d = strength
    dst = src + np.random.uniform(-d, d, src.shape).astype(np.float32) * np.float32([w, h])
    M = cv2.getPerspectiveTransform(src, dst)
    xs, ys = dst[:, 0], dst[:, 1]
    nw, nh = int(math.ceil(xs.max() - xs.min())), int(math.ceil(ys.max() - ys.min()))
    M[0, 2] -= xs.min()
    M[1, 2] -= ys.min()
    nw, nh = max(nw, 1), max(nh, 1)
    return cv2.warpPerspective(rgba, M, (nw, nh), flags=cv2.INTER_LINEAR,
                               borderMode=cv2.BORDER_CONSTANT, borderValue=(0, 0, 0, 0))


def occlude(rgba, rng):
    """Knock a chunk out of the alpha to mimic players blocking the logo."""
    h, w = rgba.shape[:2]
    ow, oh = int(w * rng.uniform(0.2, 0.5)), int(h * rng.uniform(0.2, 0.5))
    x, y = rng.randint(0, max(w - ow, 1)), rng.randint(0, max(h - oh, 1))
    rgba = rgba.copy()
    rgba[y:y + oh, x:x + ow, 3] = 0
    return rgba


def transform_logo(rgba, bg_w, bg_h, args, rng):
    rgba = rgba.copy()
    # scale: target width as a fraction of the frame width (logos run tiny->medium)
    tw = rng.uniform(args.min_scale, args.max_scale) * bg_w
    s = tw / rgba.shape[1]
    nh = max(int(rgba.shape[0] * s), 4)
    nw = max(int(rgba.shape[1] * s), 4)
    rgba = cv2.resize(rgba, (nw, nh), interpolation=cv2.INTER_AREA if s < 1 else cv2.INTER_LINEAR)

    if rng.random() < 0.9:
        rgba = jitter_color(rgba, rng)
    if rng.random() < args.p_perspective:
        rgba = warp_perspective(rgba, rng, args.perspective)
    if rng.random() < args.p_rotate:
        ang = rng.uniform(-args.rotate, args.rotate)
        h, w = rgba.shape[:2]
        M = cv2.getRotationMatrix2D((w / 2, h / 2), ang, 1.0)
        cos, sin = abs(M[0, 0]), abs(M[0, 1])
        nW, nH = int(h * sin + w * cos), int(h * cos + w * sin)
        M[0, 2] += nW / 2 - w / 2
        M[1, 2] += nH / 2 - h / 2
        rgba = cv2.warpAffine(rgba, M, (nW, nH), flags=cv2.INTER_LINEAR,
                              borderMode=cv2.BORDER_CONSTANT, borderValue=(0, 0, 0, 0))
    if rng.random() < args.p_occlude:
        rgba = occlude(rgba, rng)
    if rng.random() < args.p_blur:
        if rng.random() < 0.5:
            kk = rng.choice([3, 5, 7])
            rgba = cv2.GaussianBlur(rgba, (kk, kk), 0)
        else:
            rgba = motion_blur(rgba, rng, rng.choice([5, 7, 9, 11]))
    return tight_crop(rgba)


# -------------------------------------------------------------------- compositing
def alpha_paste(bg, rgba, x, y, global_alpha):
    h, w = rgba.shape[:2]
    H, W = bg.shape[:2]
    if x < 0 or y < 0 or x + w > W or y + h > H:
        return None
    fg = rgba[:, :, :3].astype(np.float32)
    a = (rgba[:, :, 3].astype(np.float32) / 255.0) * global_alpha
    a3 = a[:, :, None]
    roi = bg[y:y + h, x:x + w].astype(np.float32)
    bg[y:y + h, x:x + w] = (a3 * fg + (1 - a3) * roi).astype(np.uint8)
    ys, xs = np.where(rgba[:, :, 3] > 10)
    if len(xs) == 0:
        return None
    return (x + xs.min(), y + ys.min(), x + xs.max(), y + ys.max())


def iou(a, b):
    ix1, iy1 = max(a[0], b[0]), max(a[1], b[1])
    ix2, iy2 = min(a[2], b[2]), min(a[3], b[3])
    iw, ih = max(0, ix2 - ix1), max(0, iy2 - iy1)
    inter = iw * ih
    if inter == 0:
        return 0.0
    ua = (a[2] - a[0]) * (a[3] - a[1]) + (b[2] - b[0]) * (b[3] - b[1]) - inter
    return inter / ua if ua > 0 else 0.0


# -------------------------------------------------------------------------- labels
def read_existing_boxes(label_path, W, H):
    """Existing YOLO labels (any class) -> abs-pixel xyxy, collapsed to class `logo`."""
    boxes = []
    if not label_path.exists():
        return boxes
    for line in label_path.read_text().splitlines():
        p = line.split()
        if len(p) < 5:
            continue
        _, cx, cy, w, h = map(float, p[:5])
        x1, y1 = (cx - w / 2) * W, (cy - h / 2) * H
        x2, y2 = (cx + w / 2) * W, (cy + h / 2) * H
        boxes.append((x1, y1, x2, y2))
    return boxes


def to_yolo_line(box, W, H):
    x1, y1, x2, y2 = box
    cx, cy = (x1 + x2) / 2 / W, (y1 + y2) / 2 / H
    w, h = (x2 - x1) / W, (y2 - y1) / H
    return f"0 {cx:.6f} {cy:.6f} {w:.6f} {h:.6f}"


# ----------------------------------------------------------------------------- main
def main(args):
    rng = random.Random(args.seed)
    np.random.seed(args.seed)

    logos = load_logos(args.logos, args.white_thresh)
    bgs = [p for p in Path(args.backgrounds).iterdir()
           if p.suffix.lower() in (".jpg", ".jpeg", ".png")]
    if not bgs:
        raise SystemExit(f"No background frames in {args.backgrounds}")
    print(f"[bg] {len(bgs)} background frames from {args.backgrounds}")

    out = Path(args.out)
    for sub in ("images/train", "images/val", "labels/train", "labels/val"):
        (out / sub).mkdir(parents=True, exist_ok=True)

    n_val = int(args.n * args.val_frac)
    made = 0
    for i in range(args.n):
        split = "val" if i < n_val else "train"
        bg_path = bgs[rng.randrange(len(bgs))]
        bg = imread_unicode(bg_path, cv2.IMREAD_COLOR)
        if bg is None:
            continue
        H, W = bg.shape[:2]

        boxes = []
        if args.bg_labels:
            lbl = Path(args.bg_labels) / (bg_path.stem + ".txt")
            boxes = read_existing_boxes(lbl, W, H)

        k = rng.randint(args.min_logos, args.max_logos)
        for _ in range(k):
            _, asset = logos[rng.randrange(len(logos))]
            t = transform_logo(asset, W, H, args, rng)
            h, w = t.shape[:2]
            if w >= W or h >= H:
                continue
            placed = False
            for _try in range(args.place_tries):
                x, y = rng.randint(0, W - w), rng.randint(0, H - h)
                cand = (x, y, x + w, y + h)
                if args.max_overlap < 1.0 and any(
                        iou(cand, b) > args.max_overlap for b in boxes):
                    continue
                box = alpha_paste(bg, t, x, y, rng.uniform(args.min_opacity, 1.0))
                if box:
                    boxes.append(box)
                    placed = True
                break
            if not placed:
                continue

        if args.p_jpeg > 0 and rng.random() < args.p_jpeg:   # broadcast compression
            q = rng.randint(args.jpeg_min, 95)
            ok, enc = cv2.imencode(".jpg", bg, [cv2.IMWRITE_JPEG_QUALITY, q])
            if ok:
                bg = cv2.imdecode(enc, cv2.IMREAD_COLOR)

        stem = f"synth_{i:06d}"
        imwrite_unicode(out / "images" / split / f"{stem}.jpg", bg,
                        [cv2.IMWRITE_JPEG_QUALITY, 92])
        lines = [to_yolo_line(b, W, H) for b in boxes
                 if b[2] > b[0] and b[3] > b[1]]
        (out / "labels" / split / f"{stem}.txt").write_text("\n".join(lines))
        made += 1
        if made % 200 == 0:
            print(f"  generated {made}/{args.n}")

    yaml = out / "data.yaml"
    yaml.write_text(
        f"path: {out.resolve().as_posix()}\n"
        "train: images/train\n"
        "val: images/val\n"
        "nc: 1\n"
        "names: ['logo']\n"
    )
    print(f"\n[done] {made} images -> {out.resolve()}")
    print(f"[done] dataset config -> {yaml.resolve()}")
    print("\nNext: train the class-agnostic Localizer on it, e.g.")
    print(f"    python ../train.py --data synthetic/{out.name}/data.yaml "
          "--name logo_localizer_synth")


def build_parser():
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--logos", default=str(LOGO_ROOT))
    p.add_argument("--backgrounds", default=str(BG_IMAGES))
    p.add_argument("--bg-labels", dest="bg_labels", default=str(BG_LABELS),
                   help="dir of existing YOLO labels for the bg frames (collapsed to "
                        "class 0). Pass --no-bg-labels for clean-background mode.")
    p.add_argument("--no-bg-labels", dest="bg_labels", action="store_const", const="")
    p.add_argument("--out", default=str(HERE / "data_synth"))
    p.add_argument("--n", type=int, default=4000, help="number of images to generate")
    p.add_argument("--val-frac", type=float, default=0.10)
    p.add_argument("--seed", type=int, default=0)

    p.add_argument("--min-logos", type=int, default=1)
    p.add_argument("--max-logos", type=int, default=4)
    p.add_argument("--min-scale", type=float, default=0.02,
                   help="pasted logo width as fraction of frame width (min)")
    p.add_argument("--max-scale", type=float, default=0.22)
    p.add_argument("--rotate", type=float, default=15.0)
    p.add_argument("--perspective", type=float, default=0.12)
    p.add_argument("--min-opacity", type=float, default=0.80,
                   help="<1 mimics faded ad-boards / semi-transparent overlays")
    p.add_argument("--max-overlap", type=float, default=0.35,
                   help="max IoU a new logo may have with an existing box (1=allow any)")
    p.add_argument("--place-tries", type=int, default=10)

    p.add_argument("--p-rotate", type=float, default=0.8)
    p.add_argument("--p-perspective", type=float, default=0.6)
    p.add_argument("--p-blur", type=float, default=0.5)
    p.add_argument("--p-occlude", type=float, default=0.3)
    p.add_argument("--p-jpeg", type=float, default=0.5)
    p.add_argument("--jpeg-min", type=int, default=40)
    p.add_argument("--white-thresh", type=int, default=245,
                   help="pixels with all BGR >= this on alpha-less assets -> transparent")
    return p


if __name__ == "__main__":
    main(build_parser().parse_args())
