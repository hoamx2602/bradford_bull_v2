"""Stage 1b — Build dataset copy-paste-on-real cho proposer class-agnostic.

Thiết kế theo kết luận Stage 1a (H1 bác bỏ — appearance gap, không phải scale):
degradation-heavy augmentation để proposer học "logo-ness" ở điều kiện broadcast
(motion blur, biến dạng vải, nén), thay vì dựa zero-shot template matching.

Pipeline:
  1. Trích frame từ match.mp4 (từ frame 1000+ — KHÔNG đụng 40 gold frame 0-975)
  2. YOLOv8 person detect → person crop (như protocol eval 1a)
  3. Paste 1-4 logo template/crop: perspective + cloth-warp (sine) + motion blur
     + downscale-upscale + JPEG + color jitter
  4. Ghi YOLO labels 1 lớp `logo` + ~15% crop negative (không paste)

Chạy:
  conda run -n bradford_bulls python auto_label/stage1b_dataset.py \
      --video data/real/match.mp4 --logos "Sponsor Logo" \
      --out data/stage1b_ds --n-frames 700 --start-frame 1000
"""
from __future__ import annotations

import argparse
import io
import random
from pathlib import Path

import cv2
import numpy as np
from PIL import Image

MIN_PERSON_W = 60          # px — chỉ dùng person đủ lớn làm nền train
CROP_MARGIN = 0.05
NEG_FRAC = 0.15            # tỷ lệ crop negative (không logo)
VAL_FRAC = 0.10
IMG_EXT = {".png", ".jpg", ".jpeg"}


# --------------------------------------------------------------------------- #
# Logo loading (tight-crop, bỏ file hỏng)
# --------------------------------------------------------------------------- #

def load_logos(logo_dir: Path) -> list[np.ndarray]:
    """Load logo → list RGBA numpy (tight-cropped)."""
    out = []
    for p in sorted(logo_dir.iterdir()):
        if p.suffix.lower() not in IMG_EXT:
            continue
        try:
            img = Image.open(p).convert("RGBA")
        except Exception:
            continue
        arr = np.array(img)
        # tight crop theo alpha hoặc theo vùng khác màu nền góc
        a = arr[:, :, 3]
        if a.min() == 255:  # không alpha thật → dùng độ lệch so màu góc
            rgb = arr[:, :, :3].astype(np.int16)
            corner = rgb[0, 0]
            diff = np.abs(rgb - corner).sum(axis=2)
            mask = diff > 40
        else:
            mask = a > 10
        ys, xs = np.where(mask)
        if len(xs) < 100:
            continue
        x0, x1, y0, y1 = xs.min(), xs.max(), ys.min(), ys.max()
        crop = arr[y0:y1+1, x0:x1+1]
        if crop.shape[0] < 20 or crop.shape[1] < 20:
            continue
        out.append(crop)
    return out


# --------------------------------------------------------------------------- #
# Augment: warp + degradation (điểm mấu chốt sau Stage 1a)
# --------------------------------------------------------------------------- #

def cloth_warp(logo: np.ndarray, rng: random.Random) -> np.ndarray:
    """Sine displacement dọc — mô phỏng vải nhăn/cuộn."""
    h, w = logo.shape[:2]
    amp = rng.uniform(0.01, 0.06) * h
    freq = rng.uniform(0.5, 2.0)
    phase = rng.uniform(0, 2*np.pi)
    map_x, map_y = np.meshgrid(np.arange(w, dtype=np.float32),
                               np.arange(h, dtype=np.float32))
    map_y = map_y + amp * np.sin(2*np.pi*freq*map_x/w + phase)
    return cv2.remap(logo, map_x, map_y, cv2.INTER_LINEAR,
                     borderMode=cv2.BORDER_CONSTANT, borderValue=(0, 0, 0, 0))


def perspective_warp(logo: np.ndarray, rng: random.Random) -> np.ndarray:
    h, w = logo.shape[:2]
    d = 0.18
    src = np.float32([[0, 0], [w, 0], [w, h], [0, h]])
    dst = src + np.float32([[rng.uniform(-d, d)*w, rng.uniform(-d, d)*h]
                            for _ in range(4)])
    M = cv2.getPerspectiveTransform(src, dst)
    return cv2.warpPerspective(logo, M, (w, h), borderMode=cv2.BORDER_CONSTANT,
                               borderValue=(0, 0, 0, 0))


def motion_blur(img: np.ndarray, rng: random.Random) -> np.ndarray:
    k = rng.choice([3, 5, 7, 9])
    kernel = np.zeros((k, k), np.float32)
    ang = rng.uniform(0, np.pi)
    cx = cy = k // 2
    dx, dy = np.cos(ang), np.sin(ang)
    for t in np.linspace(-cx, cx, 2*k):
        x, y = int(round(cx + t*dx)), int(round(cy + t*dy))
        if 0 <= x < k and 0 <= y < k:
            kernel[y, x] = 1
    kernel /= max(kernel.sum(), 1)
    return cv2.filter2D(img, -1, kernel)


def paste_logo(crop: np.ndarray, logo: np.ndarray,
               rng: random.Random) -> tuple[np.ndarray, tuple] | None:
    """Paste 1 logo đã augment vào crop. Trả (crop mới, bbox xyxy) hoặc None."""
    ch, cw = crop.shape[:2]
    # scale: bề rộng logo = 12-45% bề rộng crop (khớp phân bố GT)
    lw = int(rng.uniform(0.12, 0.45) * cw)
    ar = logo.shape[1] / logo.shape[0]
    lh = max(8, int(lw / ar))
    if lw < 10 or lh >= ch // 2:
        return None
    lg = cv2.resize(logo, (lw, lh), interpolation=cv2.INTER_AREA)
    lg = perspective_warp(lg, rng)
    lg = cloth_warp(lg, rng)

    # vị trí: nửa trên+giữa crop (vùng jersey), tránh mép
    px = rng.randint(0, max(1, cw - lw))
    py = rng.randint(int(0.10*ch), max(int(0.10*ch)+1, int(0.65*ch) - lh))

    alpha = (lg[:, :, 3:4].astype(np.float32) / 255.0)
    # color jitter + độ mờ blend nhẹ (logo in trên vải không bao giờ 100% nét)
    rgb = lg[:, :, :3].astype(np.float32)
    rgb *= rng.uniform(0.7, 1.15)
    alpha *= rng.uniform(0.85, 1.0)
    region = crop[py:py+lh, px:px+lw].astype(np.float32)
    if region.shape[:2] != rgb.shape[:2]:
        return None
    crop[py:py+lh, px:px+lw] = np.clip(
        region * (1 - alpha) + np.clip(rgb, 0, 255) * alpha, 0, 255
    ).astype(np.uint8)
    return crop, (px, py, px+lw, py+lh)


def degrade(crop: np.ndarray, rng: random.Random) -> np.ndarray:
    """Degradation toàn crop — trái tim của bài học Stage 1a."""
    if rng.random() < 0.7:
        crop = motion_blur(crop, rng)
    if rng.random() < 0.8:                      # downscale-upscale
        f = rng.uniform(0.35, 0.8)
        h, w = crop.shape[:2]
        small = cv2.resize(crop, (max(8, int(w*f)), max(8, int(h*f))))
        crop = cv2.resize(small, (w, h))
    if rng.random() < 0.8:                      # JPEG nén
        q = rng.randint(30, 75)
        ok, enc = cv2.imencode(".jpg", crop, [cv2.IMWRITE_JPEG_QUALITY, q])
        if ok:
            crop = cv2.imdecode(enc, cv2.IMREAD_COLOR)
    return crop


# --------------------------------------------------------------------------- #
# Main
# --------------------------------------------------------------------------- #

def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--video",  required=True, type=Path)
    ap.add_argument("--logos",  required=True, type=Path)
    ap.add_argument("--out",    required=True, type=Path)
    ap.add_argument("--n-frames", type=int, default=700)
    ap.add_argument("--start-frame", type=int, default=1000)
    ap.add_argument("--seed", type=int, default=42)
    a = ap.parse_args()
    rng = random.Random(a.seed)

    for split in ("train", "val"):
        (a.out / "images" / split).mkdir(parents=True, exist_ok=True)
        (a.out / "labels" / split).mkdir(parents=True, exist_ok=True)

    logos = load_logos(a.logos)
    print(f"[logos] {len(logos)} template usable")

    # 1. Trích frame + person detect
    from ultralytics import YOLO
    person_model = YOLO("yolov8m.pt")

    cap = cv2.VideoCapture(str(a.video))
    total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    idxs = np.linspace(a.start_frame, total - 1, a.n_frames).astype(int)
    print(f"[video] {total} frames, lấy {len(idxs)} frame từ {a.start_frame}")

    n_img = n_pos = n_neg = 0
    for fi in idxs:
        cap.set(cv2.CAP_PROP_POS_FRAMES, int(fi))
        ok, frame = cap.read()
        if not ok:
            continue
        H, W = frame.shape[:2]
        res = person_model.predict(frame, classes=[0], conf=0.35, verbose=False)[0]
        for b in res.boxes.xyxy.cpu().numpy():
            x0, y0, x1, y1 = b[:4]
            if (x1 - x0) < MIN_PERSON_W:
                continue
            mw, mh = (x1-x0)*CROP_MARGIN, (y1-y0)*CROP_MARGIN
            cx0, cy0 = int(max(0, x0-mw)), int(max(0, y0-mh))
            cx1, cy1 = int(min(W, x1+mw)), int(min(H, y1+mh))
            crop = frame[cy0:cy1, cx0:cx1].copy()
            ch, cw = crop.shape[:2]
            if ch < 60 or cw < 40:
                continue

            boxes = []
            if rng.random() > NEG_FRAC:              # positive: paste 1-4 logo
                for _ in range(rng.randint(1, 4)):
                    r = paste_logo(crop, rng.choice(logos), rng)
                    if r is not None:
                        crop, bb = r
                        boxes.append(bb)
            crop = degrade(crop, rng)

            split = "val" if rng.random() < VAL_FRAC else "train"
            stem = f"f{fi:05d}_p{n_img:06d}"
            cv2.imwrite(str(a.out / "images" / split / f"{stem}.jpg"), crop)
            lines = [f"0 {(bb[0]+bb[2])/2/cw:.6f} {(bb[1]+bb[3])/2/ch:.6f} "
                     f"{(bb[2]-bb[0])/cw:.6f} {(bb[3]-bb[1])/ch:.6f}"
                     for bb in boxes]
            (a.out / "labels" / split / f"{stem}.txt").write_text("\n".join(lines))
            n_img += 1
            n_pos += len(boxes)
            n_neg += (0 if boxes else 1)
    cap.release()

    (a.out / "data.yaml").write_text(
        f"path: {a.out.resolve()}\ntrain: images/train\nval: images/val\n"
        f"names:\n  0: logo\n")
    print(f"[done] {n_img} crop ({n_neg} negative), {n_pos} logo instance")
    print(f"[yaml] {a.out / 'data.yaml'}")


if __name__ == "__main__":
    main()
