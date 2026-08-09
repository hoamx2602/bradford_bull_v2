"""Kênh ANCHOR #3 — geometric verification logo-PNG ↔ crop broadcast (docs/12).

Vì sao cần: anchor cũ chỉ có OCR-lexicon (kênh #1) → chỉ định danh được WORDMARK.
Logo THUẦN HÌNH (icon, không chữ) làm chuỗi inventory đứt ngay từ anchor (cold-start).
Kênh này bù đúng chỗ đó: khớp đặc trưng ORB + kiểm homography RANSAC giữa logo PNG
sạch và crop nét nhất của một bề mặt → đếm inlier. Có texture/góc cạnh (logo hình,
crest) → khớp tốt; FP gần-zero vì phải qua ràng buộc hình học nhất quán.

Bổ trợ (không thay thế) OCR: OCR mạnh ở wordmark, GEO mạnh ở logo-hình → decorrelated,
đúng tinh thần consensus của kiến trúc. Chạy tốt nhất trên crop ≥~60px (inventory
chọn frame nét nhất/bề mặt nên thoả) — logo phẳng cực nhỏ vẫn khó, đó là giới hạn thật.

    python inventory/geo_verify.py --logos "Sponsor Logo" --crops <dir> --out geo.jsonl
    python inventory/geo_verify.py --selftest        # không cần model/GPU
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import cv2
import numpy as np

IMG_EXT = {".png", ".jpg", ".jpeg"}

# --- tham số chốt (documented; cần validate trên gold người khi có) --------------
NFEATURES = 1000        # ORB keypoint tối đa / ảnh
RATIO = 0.75            # Lowe ratio test (loại match nhập nhằng)
RANSAC_THR = 5.0        # ngưỡng reprojection (px) cho findHomography
MIN_INLIERS = 8         # dưới mức này KHÔNG tính là một vote hợp lệ
WORK_MAX = 512          # cạnh dài chuẩn hoá để scale feature so sánh được
CROP_MIN = 200          # crop nhỏ hơn → upscale (logo broadcast thường <200px)


def _to_gray(im: np.ndarray) -> np.ndarray:
    """RGBA/BGR/GRAY → gray uint8, alpha blend lên nền trắng (giống load logo)."""
    if im.ndim == 2:
        return im
    if im.shape[2] == 4:
        a = im[:, :, 3:4] / 255.0
        im = (im[:, :, :3] * a + 255 * (1 - a)).astype(np.uint8)
    return cv2.cvtColor(im, cv2.COLOR_BGR2GRAY)


def _resize_long(g: np.ndarray, target: int) -> np.ndarray:
    h, w = g.shape[:2]
    if max(h, w) == target:
        return g
    s = target / max(h, w)
    interp = cv2.INTER_AREA if s < 1 else cv2.INTER_LANCZOS4
    return cv2.resize(g, (max(1, int(w * s)), max(1, int(h * s))), interpolation=interp)


def _orb():
    # fastThreshold thấp hơn mặc định để bắt được góc trên crop mờ/tương phản thấp
    return cv2.ORB_create(nfeatures=NFEATURES, fastThreshold=7, edgeThreshold=15)


def match_pair(logo_gray: np.ndarray, crop_gray: np.ndarray,
               ratio: float = RATIO, ransac_thr: float = RANSAC_THR) -> dict:
    """Khớp 1 logo với 1 crop → {inliers, good, conf}.

    conf = inliers / good  (tỉ lệ nhất quán hình học; thang [0,1], scale-free).
    inliers = số điểm sống sót homography RANSAC (độ mạnh tuyệt đối của vote).
    """
    lg = _resize_long(logo_gray, WORK_MAX)
    cg = _resize_long(crop_gray, WORK_MAX if max(crop_gray.shape[:2]) >= CROP_MIN
                      else CROP_MIN)
    orb = _orb()
    k1, d1 = orb.detectAndCompute(lg, None)
    k2, d2 = orb.detectAndCompute(cg, None)
    if d1 is None or d2 is None or len(k1) < MIN_INLIERS or len(k2) < MIN_INLIERS:
        return {"inliers": 0, "good": 0, "conf": 0.0}
    bf = cv2.BFMatcher(cv2.NORM_HAMMING)
    good = []
    for pair in bf.knnMatch(d1, d2, k=2):
        if len(pair) < 2:
            continue
        m, n = pair
        if m.distance < ratio * n.distance:
            good.append(m)
    if len(good) < MIN_INLIERS:
        return {"inliers": 0, "good": len(good), "conf": 0.0}
    src = np.float32([k1[m.queryIdx].pt for m in good]).reshape(-1, 1, 2)
    dst = np.float32([k2[m.trainIdx].pt for m in good]).reshape(-1, 1, 2)
    H, mask = cv2.findHomography(src, dst, cv2.RANSAC, ransac_thr)
    if H is None or mask is None:
        return {"inliers": 0, "good": len(good), "conf": 0.0}
    inl = int(mask.sum())
    return {"inliers": inl, "good": len(good), "conf": round(inl / max(len(good), 1), 3)}


def build_bank(logos_dir: str) -> dict[str, list[np.ndarray]]:
    """Sponsor Logo/*.png → {brand: [gray template, ...]} (một brand có thể nhiều file)."""
    import sys
    sys.path.insert(0, str(Path(__file__).parent.parent / "auto_label"))
    from sam3_exemplar_autolabel import brand_key_from_filename  # noqa

    bank: dict[str, list[np.ndarray]] = {}
    for p in sorted(Path(logos_dir).iterdir()):
        if p.suffix.lower() not in IMG_EXT or p.stat().st_size == 0:
            continue
        im = cv2.imread(str(p), cv2.IMREAD_UNCHANGED)
        if im is None:
            continue
        bank.setdefault(brand_key_from_filename(p.name), []).append(_to_gray(im))
    return bank


def verify(crop_gray: np.ndarray, bank: dict[str, list[np.ndarray]],
           min_inliers: int = MIN_INLIERS) -> list[dict]:
    """Crop → xếp hạng brand theo inlier. Chỉ giữ brand đạt min_inliers."""
    out = []
    for brand, tmpls in bank.items():
        best = {"inliers": 0, "good": 0, "conf": 0.0}
        for t in tmpls:
            r = match_pair(t, crop_gray)
            if r["inliers"] > best["inliers"]:
                best = r
        if best["inliers"] >= min_inliers:
            out.append({"brand": brand, **best})
    out.sort(key=lambda x: (-x["inliers"], -x["conf"]))
    return out


def cmd_run(a) -> None:
    bank = build_bank(a.logos)
    print(f"[geo] bank: {len(bank)} brand, "
          f"{sum(len(v) for v in bank.values())} template")
    crops = sorted(Path(a.crops).glob("*.png")) + sorted(Path(a.crops).glob("*.jpg"))
    rows = []
    for p in crops:
        im = cv2.imread(str(p), cv2.IMREAD_UNCHANGED)
        if im is None:
            continue
        ranked = verify(_to_gray(im), bank, a.min_inliers)
        top = ranked[0] if ranked else {"brand": "unknown", "inliers": 0, "conf": 0.0}
        rows.append({"id": p.stem, "pred": top["brand"],
                     "inliers": top["inliers"], "conf": top["conf"],
                     "top3": [(r["brand"], r["inliers"]) for r in ranked[:3]]})
    Path(a.out).write_text(
        "\n".join(json.dumps(r, ensure_ascii=False) for r in rows), encoding="utf-8")
    n_hit = sum(r["pred"] != "unknown" for r in rows)
    print(f"[geo] {len(rows)} crop, {n_hit} verified → {a.out}")


# --- selftest: không cần model/GPU/data thật -----------------------------------
def _synth_logo(seed: int, size: int = 256) -> np.ndarray:
    """Sinh pattern có texture (đủ góc cạnh cho ORB) deterministic theo seed."""
    rng = np.random.RandomState(seed)
    g = np.full((size, size), 255, np.uint8)
    for _ in range(24):
        x, y = rng.randint(20, size - 20, 2)
        w, h = rng.randint(12, 44, 2)
        cv2.rectangle(g, (x, y), (x + w, y + h), int(rng.randint(0, 120)), -1)
    for _ in range(10):
        c = tuple(rng.randint(20, size - 20, 2).tolist())
        cv2.circle(g, c, int(rng.randint(6, 20)), int(rng.randint(0, 120)), 2)
    return g


def _warp_degrade(g: np.ndarray, seed: int) -> np.ndarray:
    """Mô phỏng broadcast: perspective + blur + downscale-upscale (giống crop thật)."""
    rng = np.random.RandomState(seed + 999)
    h, w = g.shape
    d = 0.14 * w
    src = np.float32([[0, 0], [w, 0], [w, h], [0, h]])
    dst = src + rng.uniform(-d, d, src.shape).astype(np.float32)
    M = cv2.getPerspectiveTransform(src, dst)
    out = cv2.warpPerspective(g, M, (w, h), borderValue=255)
    out = cv2.GaussianBlur(out, (5, 5), 0)
    out = cv2.resize(out, (w // 4, h // 4))            # nén xuống ~64px
    return cv2.resize(out, (w, h), interpolation=cv2.INTER_LANCZOS4)


def selftest() -> None:
    a_logo, b_logo = _synth_logo(1), _synth_logo(2)
    bank = {"brand_a": [a_logo], "brand_b": [b_logo]}
    # crop = brand_a bị biến dạng + mờ → phải verify ĐÚNG brand_a
    crop_a = _warp_degrade(a_logo, 7)
    ranked = verify(crop_a, bank, MIN_INLIERS)
    assert ranked and ranked[0]["brand"] == "brand_a", f"geo miss self: {ranked}"
    # nhiễu thuần (không chứa logo nào) → không brand nào đạt ngưỡng inlier
    noise = np.random.RandomState(0).randint(0, 255, (200, 200), np.uint8)
    assert not verify(noise, bank, MIN_INLIERS), "geo FP trên nhiễu"
    # self-match vượt hẳn cross-match (tính phân biệt)
    s_self = match_pair(a_logo, crop_a)["inliers"]
    s_cross = match_pair(b_logo, crop_a)["inliers"]
    assert s_self > s_cross, f"self {s_self} !> cross {s_cross}"
    print(f"[selftest] OK — self inliers={s_self} > cross={s_cross}; "
          f"reject noise ✓; verify(brand_a)✓")


def main() -> None:
    ap = argparse.ArgumentParser(description="Geometric logo verification (ORB+RANSAC)")
    ap.add_argument("--logos", help="thư mục logo PNG (bank)")
    ap.add_argument("--crops", help="thư mục crop cần verify")
    ap.add_argument("--out", help="jsonl kết quả")
    ap.add_argument("--min-inliers", type=int, default=MIN_INLIERS)
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args()
    if a.selftest:
        selftest()
        return
    if not (a.logos and a.crops and a.out):
        ap.error("cần --logos --crops --out (hoặc --selftest)")
    cmd_run(a)


if __name__ == "__main__":
    main()
