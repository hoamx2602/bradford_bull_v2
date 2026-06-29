"""Bậc 1 — Copy-paste synthetic (logo thật + nền + domain randomization).

Thang synthetic (xem `../autolabel.md` §8): bậc thấp nhất, rẻ nhất, nhãn sạch 100%.
Dán logo THẬT (PNG alpha) lên nền (ảnh thật nếu có, else nền cỏ tổng hợp) với biến
đổi ngẫu nhiên (scale/xoay/perspective/màu/blur/JPEG) → ảnh train + nhãn OBB tự sinh
(toạ độ chính xác tuyệt đối vì ta tự dán). Nuôi Tầng 1 (localizer) + crop cho Tầng 2.

Nguyên tắc VÀNG: logo luôn là asset thật, không sinh mới → label fidelity tuyệt đối.

Output:
    out/images/*.jpg
    out/labels/*.txt    OBB "cls x1 y1 .. x4 y4" (class-agnostic 0, hoặc per-brand)
    out/crops/<brand>/  crop logo sạch cho Tầng 2 gallery
    out/data.yaml

Chạy:
    python auto_label/synth_copypaste.py --logos "Sponsor Logo" --out data/synth_b1 \
        --n 200 --backgrounds data/real/auto/images   # nền thật từ frame video
    python auto_label/synth_copypaste.py --selftest
"""
from __future__ import annotations

import argparse
import random
from pathlib import Path

import cv2
import numpy as np

IMG_EXT = {".png", ".jpg", ".jpeg", ".bmp", ".webp"}


def load_logo_rgba(p: Path) -> "np.ndarray | None":
    img = cv2.imread(str(p), cv2.IMREAD_UNCHANGED)
    if img is None:
        return None
    if img.ndim == 2:
        img = cv2.cvtColor(img, cv2.COLOR_GRAY2BGR)
    if img.shape[2] == 3:
        img = np.dstack([img, np.full(img.shape[:2], 255, np.uint8)])
    return img


def grass_bg(h: int, w: int) -> np.ndarray:
    base = (random.randint(20, 55), random.randint(75, 110), random.randint(20, 55))
    bg = np.full((h, w, 3), base, np.float32)
    bg += np.random.randn(h, w, 3) * 10.0
    for _ in range(random.randint(0, 2)):
        y = random.randint(0, h - 1)
        cv2.line(bg, (0, y), (w, y), (200, 200, 200), 1)
    return np.clip(bg, 0, 255).astype(np.uint8)


def paste_logo(bg: np.ndarray, logo_rgba: np.ndarray):
    """Dán 1 logo (scale+xoay) lên bg → trả (bg mới, quad 4 điểm pixel)."""
    H, W = bg.shape[:2]
    lh0, lw0 = logo_rgba.shape[:2]
    scale = random.uniform(0.06, 0.22) * W / lw0
    lw, lh = max(int(lw0 * scale), 10), max(int(lh0 * scale), 10)
    logo = cv2.resize(logo_rgba, (lw, lh))
    # color jitter nhẹ trên kênh BGR (giữ alpha)
    if random.random() < 0.5:
        logo[:, :, :3] = np.clip(logo[:, :, :3].astype(np.float32)
                                 * random.uniform(0.8, 1.2), 0, 255).astype(np.uint8)
    theta = random.uniform(-25, 25)
    M = cv2.getRotationMatrix2D((lw / 2, lh / 2), theta, 1.0)
    tx = random.randint(0, max(W - lw, 1)); ty = random.randint(0, max(H - lh, 1))
    M[0, 2] += tx; M[1, 2] += ty
    warp = cv2.warpAffine(logo, M, (W, H), flags=cv2.INTER_LINEAR,
                          borderValue=(0, 0, 0, 0))
    a = (warp[:, :, 3:4].astype(np.float32) / 255.0)
    out = (bg.astype(np.float32) * (1 - a) + warp[:, :, :3] * a).astype(np.uint8)
    src = np.array([[0, 0], [lw, 0], [lw, lh], [0, lh]], np.float32)
    quad = (M[:, :2] @ src.T).T + M[:, 2]
    return out, quad


def to_obb_line(quad, cls, W, H):
    coords = " ".join(f"{x / W:.6f} {y / H:.6f}" for x, y in quad)
    return f"{cls} {coords}"


def to_hbb_line(quad, cls, W, H):
    xs, ys = quad[:, 0], quad[:, 1]
    x0, y0, x1, y1 = xs.min(), ys.min(), xs.max(), ys.max()
    cx, cy = (x0 + x1) / 2 / W, (y0 + y1) / 2 / H
    return f"{cls} {cx:.6f} {cy:.6f} {(x1 - x0) / W:.6f} {(y1 - y0) / H:.6f}"


def brand_key(name: str) -> str:
    try:
        from sam3_exemplar_autolabel import brand_key_from_filename
        return brand_key_from_filename(name)
    except Exception:
        return Path(name).stem.lower()


def generate(logos_dir: Path, out: Path, n: int, bg_dir: "Path | None",
             max_per: int, obb: bool, class_agnostic: bool,
             size=(720, 1280), blur_p=0.4, jpeg_p=0.5, seed=0) -> dict:
    random.seed(seed); np.random.seed(seed)
    logos = []
    for p in sorted(Path(logos_dir).iterdir()):
        if p.suffix.lower() in IMG_EXT:
            im = load_logo_rgba(p)
            if im is not None:
                logos.append((brand_key(p.name), im))
    if not logos:
        raise SystemExit(f"Không có logo trong {logos_dir}")
    brands = sorted({b for b, _ in logos})
    bid = {b: i for i, b in enumerate(brands)}

    bgs = []
    if bg_dir:
        bgs = [p for p in Path(bg_dir).iterdir() if p.suffix.lower() in IMG_EXT]

    img_dir, lbl_dir, crop_dir = out / "images", out / "labels", out / "crops"
    for d in (img_dir, lbl_dir, crop_dir):
        d.mkdir(parents=True, exist_ok=True)
    writer = to_obb_line if obb else to_hbb_line

    nbox = 0
    for i in range(n):
        if bgs:
            bg = cv2.imread(str(random.choice(bgs)))
            bg = cv2.resize(bg, (size[1], size[0])) if bg is not None else grass_bg(*size)
        else:
            bg = grass_bg(*size)
        H, W = bg.shape[:2]
        lines = []
        for _ in range(random.randint(1, max_per)):
            brand, logo = random.choice(logos)
            bg, quad = paste_logo(bg, logo)
            cls = 0 if class_agnostic else bid[brand]
            lines.append(writer(quad, cls, W, H))
            x0, y0 = int(quad[:, 0].min()), int(quad[:, 1].min())
            x1, y1 = int(quad[:, 0].max()), int(quad[:, 1].max())
            crop = bg[max(y0, 0):y1, max(x0, 0):x1]
            if crop.size:
                bd = crop_dir / brand; bd.mkdir(exist_ok=True)
                cv2.imwrite(str(bd / f"{brand}_{i:05d}.jpg"), crop)
        if random.random() < blur_p:
            bg = cv2.GaussianBlur(bg, (3, 3), 0)
        if random.random() < jpeg_p:
            ok, enc = cv2.imencode(".jpg", bg, [cv2.IMWRITE_JPEG_QUALITY,
                                                random.randint(45, 90)])
            if ok:
                bg = cv2.imdecode(enc, cv2.IMREAD_COLOR)
        stem = f"synth_{i:05d}"
        cv2.imwrite(str(img_dir / f"{stem}.jpg"), bg)
        (lbl_dir / f"{stem}.txt").write_text("\n".join(lines))
        nbox += len(lines)

    if class_agnostic:
        names = "nc: 1\nnames:\n  0: logo"
    else:
        names = f"nc: {len(brands)}\nnames:\n" + "\n".join(
            f"  {i}: {b}" for b, i in bid.items())
    (out / "data.yaml").write_text(
        f"path: {out.resolve()}\ntrain: images\nval: images\n{names}\n")
    return {"images": n, "boxes": nbox, "brands": len(brands), "obb": obb}


def _selftest() -> None:
    # paste + quad đúng: dán logo đặc lên nền, quad bao vùng logo
    bg = np.zeros((100, 200, 3), np.uint8)
    logo = np.dstack([np.full((40, 40, 3), 255, np.uint8),
                      np.full((40, 40), 255, np.uint8)])
    random.seed(1); np.random.seed(1)
    out, quad = paste_logo(bg, logo)
    assert quad.shape == (4, 2)
    assert out.sum() > 0, "phải có pixel logo dán lên"
    # line format
    q = np.array([[0, 0], [10, 0], [10, 20], [0, 20]], np.float32)
    assert to_obb_line(q, 0, 100, 100).split()[0] == "0"
    assert len(to_obb_line(q, 0, 100, 100).split()) == 9
    assert len(to_hbb_line(q, 3, 100, 100).split()) == 5
    print("  synth_copypaste selftest: OK ✅")


def main() -> None:
    ap = argparse.ArgumentParser(description="Bậc 1 — copy-paste synthetic")
    ap.add_argument("--logos", help="thư mục logo PNG (alpha)")
    ap.add_argument("--out", default="data/synth_b1", type=Path)
    ap.add_argument("--n", type=int, default=200, help="số ảnh sinh")
    ap.add_argument("--backgrounds", default=None, help="thư mục nền thật (tùy chọn)")
    ap.add_argument("--max-per", dest="max_per", type=int, default=3,
                    help="số logo tối đa / ảnh")
    ap.add_argument("--hbb", action="store_true", help="xuất HBB thay vì OBB")
    ap.add_argument("--per-brand", dest="per_brand", action="store_true",
                    help="class theo brand (mặc định class-agnostic 'logo')")
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args()
    if a.selftest:
        _selftest(); return
    if not a.logos:
        ap.error("cần --logos (hoặc --selftest)")
    bg = Path(a.backgrounds) if a.backgrounds else None
    res = generate(Path(a.logos), a.out, a.n, bg, a.max_per,
                   obb=not a.hbb, class_agnostic=not a.per_brand, seed=a.seed)
    print(f"[synth-b1] {res['images']} ảnh, {res['boxes']} box, "
          f"{res['brands']} brand, {'OBB' if res['obb'] else 'HBB'} → {a.out}")


if __name__ == "__main__":
    main()
