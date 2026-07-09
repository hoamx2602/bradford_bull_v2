"""Stage 2 — Sinh template DB augment degradation-heavy cho recognizer.

Vì sao: logo gallery là vector sạch/nét; crop SAM3 từ broadcast thì nhỏ (p50 ~32px),
mờ (motion blur + nén + biến dạng vải + scale_fill bóp ngang của SAM3). Embed logo
sạch → so cosine với crop mờ = đúng sim-gap đã giết Stage 1a/1b. Fix (theo review
chuyên gia): augment mỗi logo thành nhiều biến thể mô phỏng ĐỘ SUY BIẾN broadcast,
GIỮ alpha để recognizer.prep_for_embed xoá nền → template và query cùng "logo trên
nền xám trung tính".

Recipe / biến thể:
  geometric   : perspective (jitter 4 góc), xoay ±12°, bóp ngang 0.6–1.0 (mô phỏng
                scale_fill của SAM3), aspect jitter
  degradation : downscale cạnh dài về s∈{14,20,28,40,60,90}px rồi Lanczos-upscale
                (KHỚP độ mờ crop thật) + gaussian/motion blur + JPEG Q∈[25,60]
  photometric : brightness/contrast, hue ±10

Xuất RGBA PNG: <out_db>/<brand>/*.png (vào DB) và <out_val>/<brand>/*.png (held-out
để đo synthetic val + calibrate τ, KHÔNG nằm trong DB).

Chạy:
  python auto_label/gallery_augment.py --logos "Sponsor Logo" \
      --out-db data/gallery_aug --out-val data/gallery_val --n-db 48 --n-val 12
"""
from __future__ import annotations

import argparse
import io
import sys
from pathlib import Path

import cv2
import numpy as np
from PIL import Image

sys.path.insert(0, str(Path(__file__).parent))
from sam3_exemplar_autolabel import brand_key_from_filename  # noqa: E402

IMG_EXT = {".png", ".jpg", ".jpeg"}
DOWNSCALE_SIZES = [14, 20, 28, 40, 60, 90]


# --------------------------------------------------------------------------- #
# Load logo → RGBA tight-cropped (xử lý alpha thật / auto-mask JPG / CMYK / hỏng)
# --------------------------------------------------------------------------- #
def load_rgba(p: Path) -> "np.ndarray | None":
    if p.stat().st_size == 0:
        return None
    try:
        im = Image.open(p)
        im.load()
    except Exception:
        return None
    if im.mode == "CMYK":
        im = im.convert("RGB")
    arr = np.array(im.convert("RGBA"))  # HxWx4 uint8, RGB(A)
    a = arr[:, :, 3]
    if a.min() == 255:  # không alpha thật → auto-mask theo màu 4 góc
        rgb = arr[:, :, :3].astype(np.int16)
        corners = np.stack([rgb[0, 0], rgb[0, -1], rgb[-1, 0], rgb[-1, -1]])
        bg = np.median(corners, axis=0)
        diff = np.abs(rgb - bg).sum(axis=2)
        mask = (diff > 40).astype(np.uint8) * 255
        arr[:, :, 3] = mask
    # tight crop theo alpha
    ys, xs = np.where(arr[:, :, 3] > 10)
    if len(ys) == 0:
        return None
    y0, y1, x0, x1 = ys.min(), ys.max() + 1, xs.min(), xs.max() + 1
    return arr[y0:y1, x0:x1]


# --------------------------------------------------------------------------- #
# Augment (giữ alpha xuyên suốt)
# --------------------------------------------------------------------------- #
def _perspective(rgba, rng, strength=0.18):
    h, w = rgba.shape[:2]
    j = strength
    src = np.float32([[0, 0], [w, 0], [w, h], [0, h]])
    dst = src + rng.uniform(-j, j, (4, 2)) * [w, h]
    M = cv2.getPerspectiveTransform(src, dst.astype(np.float32))
    return cv2.warpPerspective(rgba, M, (w, h), flags=cv2.INTER_LINEAR,
                               borderMode=cv2.BORDER_CONSTANT, borderValue=(0, 0, 0, 0))


def _rotate(rgba, rng, deg=12):
    h, w = rgba.shape[:2]
    ang = rng.uniform(-deg, deg)
    M = cv2.getRotationMatrix2D((w / 2, h / 2), ang, 1.0)
    return cv2.warpAffine(rgba, M, (w, h), flags=cv2.INTER_LINEAR,
                          borderMode=cv2.BORDER_CONSTANT, borderValue=(0, 0, 0, 0))


def _squash(rgba, rng):
    """Bóp ngang 0.6–1.0 (mô phỏng LetterBox scale_fill của SAM3) + aspect jitter."""
    h, w = rgba.shape[:2]
    sx = rng.uniform(0.6, 1.0)
    sy = rng.uniform(0.9, 1.1)
    return cv2.resize(rgba, (max(2, int(w * sx)), max(2, int(h * sy))),
                      interpolation=cv2.INTER_LINEAR)


def _motion_blur(rgb, rng):
    k = int(rng.integers(3, 10))
    kern = np.zeros((k, k), np.float32)
    kern[k // 2, :] = 1.0
    ang = rng.uniform(0, 180)
    M = cv2.getRotationMatrix2D((k / 2, k / 2), ang, 1.0)
    kern = cv2.warpAffine(kern, M, (k, k))
    s = kern.sum()
    if s > 0:
        kern /= s
    return cv2.filter2D(rgb, -1, kern)


def _degrade(rgba, rng):
    """downscale-upscale (mờ chuẩn broadcast) + blur + JPEG. Giữ alpha."""
    rgb = rgba[:, :, :3].copy()
    a = rgba[:, :, 3].copy()
    h, w = rgb.shape[:2]
    # 1) downscale cạnh dài về s rồi upscale lại (KHỚP crop nhỏ mờ)
    s = int(rng.choice(DOWNSCALE_SIZES))
    long = max(h, w)
    if long > s:
        f = s / long
        small = (max(2, int(w * f)), max(2, int(h * f)))
        rgb = cv2.resize(cv2.resize(rgb, small, interpolation=cv2.INTER_AREA),
                         (w, h), interpolation=cv2.INTER_LANCZOS4)
        a = cv2.resize(cv2.resize(a, small, interpolation=cv2.INTER_AREA),
                       (w, h), interpolation=cv2.INTER_LANCZOS4)
    # 2) blur nhẹ
    if rng.random() < 0.6:
        rgb = _motion_blur(rgb, rng)
    if rng.random() < 0.4:
        kk = int(rng.choice([3, 5]))
        rgb = cv2.GaussianBlur(rgb, (kk, kk), 0)
    # 3) photometric
    alpha = rng.uniform(0.8, 1.2)   # contrast
    beta = rng.uniform(-20, 20)     # brightness
    rgb = np.clip(rgb.astype(np.float32) * alpha + beta, 0, 255).astype(np.uint8)
    hsv = cv2.cvtColor(rgb, cv2.COLOR_RGB2HSV).astype(np.int16)
    hsv[:, :, 0] = (hsv[:, :, 0] + int(rng.uniform(-10, 10))) % 180
    rgb = cv2.cvtColor(np.clip(hsv, 0, 255).astype(np.uint8), cv2.COLOR_HSV2RGB)
    # 4) JPEG
    q = int(rng.integers(25, 61))
    ok, enc = cv2.imencode(".jpg", cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR),
                           [cv2.IMWRITE_JPEG_QUALITY, q])
    if ok:
        rgb = cv2.cvtColor(cv2.imdecode(enc, cv2.IMREAD_COLOR), cv2.COLOR_BGR2RGB)
    out = np.dstack([rgb, a])
    return out


def augment_one(rgba, rng):
    x = rgba
    if rng.random() < 0.8:
        x = _perspective(x, rng)
    if rng.random() < 0.7:
        x = _rotate(x, rng)
    if rng.random() < 0.7:
        x = _squash(x, rng)
    x = _degrade(x, rng)
    # tight-crop lại theo alpha
    ys, xs = np.where(x[:, :, 3] > 10)
    if len(ys) == 0:
        return None
    return x[ys.min():ys.max() + 1, xs.min():xs.max() + 1]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--logos", default="Sponsor Logo")
    ap.add_argument("--out-db", default="data/gallery_aug")
    ap.add_argument("--out-val", default="data/gallery_val")
    ap.add_argument("--n-db", type=int, default=48)
    ap.add_argument("--n-val", type=int, default=12)
    ap.add_argument("--seed", type=int, default=0)
    a = ap.parse_args()

    rng = np.random.default_rng(a.seed)
    logo_dir = Path(a.logos)
    db_dir, val_dir = Path(a.out_db), Path(a.out_val)
    for d in (db_dir, val_dir):
        d.mkdir(parents=True, exist_ok=True)

    brands: dict[str, int] = {}
    skipped, n_db, n_val = [], 0, 0
    for p in sorted(logo_dir.iterdir()):
        if p.suffix.lower() not in IMG_EXT:
            continue
        rgba = load_rgba(p)
        if rgba is None:
            skipped.append(p.name)
            continue
        brand = brand_key_from_filename(p.name)
        brands[brand] = brands.get(brand, 0) + 1
        (db_dir / brand).mkdir(exist_ok=True)
        (val_dir / brand).mkdir(exist_ok=True)
        base = Path(p.name).stem.replace(" ", "_")
        for i in range(a.n_db + a.n_val):
            v = augment_one(rgba, rng)
            if v is None:
                continue
            tgt = (db_dir if i < a.n_db else val_dir) / brand / f"{base}_{i:03d}.png"
            Image.fromarray(v, "RGBA").save(tgt)
            if i < a.n_db:
                n_db += 1
            else:
                n_val += 1

    print(f"[augment] {len(brands)} brand, {n_db} DB variant, {n_val} val variant")
    print(f"  brands: {', '.join(sorted(brands))}")
    if skipped:
        print(f"  skipped (hỏng/0-byte): {skipped}")


if __name__ == "__main__":
    main()
