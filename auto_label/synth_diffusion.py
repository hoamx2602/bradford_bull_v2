"""Bậc 3 — Diffusion inpainting/harmonization (logo thật + context sinh).

Xem `../bac3_diffusion_inpainting.md`. Paste logo THẬT lên nền, rồi cho SDXL inpaint
sinh lại CONTEXT quanh logo (vải/nếp/ánh sáng/nền) theo prompt; ControlNet-canny ép
viền logo đúng layout. **Logo nằm trong vùng khoá** → không bị sinh lại.

Hai luồng (theo phân tích `../expert_review_and_plan.md` §0.3):
  - Tầng 1 (localizer): `composite_back` dán logo gốc trở lại → label fidelity tuyệt đối.
  - Tầng 2 (recognizer): BỎ composite_back, GIỮ biến thể (cong/mờ/ướt), gate bằng
    embedding-distance QC (cosine với logo gốc > ngưỡng) → đa dạng positive cho encoder.

Diffusion là dependency nặng (diffusers + SDXL ~7GB) → import LAZY. Phần logic
composite/mask/QC test được không cần GPU.

Cài để chạy thật:
    pip install diffusers controlnet_aux accelerate
Chạy:
    python auto_label/synth_diffusion.py --logos "Sponsor Logo" \
        --backgrounds data/real/auto/images --out data/synth_b3 --n 100 --device cuda
    python auto_label/synth_diffusion.py --selftest      # logic, không cần diffusers
"""
from __future__ import annotations

import argparse
import random
from pathlib import Path

import cv2
import numpy as np

PROMPTS = [
    "rugby player wearing team jersey, stadium floodlights, photorealistic, broadcast",
    "close-up sports jersey fabric with sponsor logo, motion blur, rain, tv broadcast",
    "athlete on rugby pitch, dynamic pose, jersey folds, broadcast camera, grain",
]


# --------------------------------------------------------------------------- #
# Paste + mask (logo thật)
# --------------------------------------------------------------------------- #

def paste_with_mask(bg: np.ndarray, logo_rgba: np.ndarray):
    """Dán logo (scale+xoay) → (ảnh paste, logo_mask uint8 0/255, quad)."""
    H, W = bg.shape[:2]
    lh0, lw0 = logo_rgba.shape[:2]
    scale = random.uniform(0.10, 0.28) * W / lw0
    lw, lh = max(int(lw0 * scale), 12), max(int(lh0 * scale), 12)
    logo = cv2.resize(logo_rgba, (lw, lh))
    theta = random.uniform(-20, 20)
    M = cv2.getRotationMatrix2D((lw / 2, lh / 2), theta, 1.0)
    tx = random.randint(0, max(W - lw, 1)); ty = random.randint(0, max(H - lh, 1))
    M[0, 2] += tx; M[1, 2] += ty
    warp = cv2.warpAffine(logo, M, (W, H), borderValue=(0, 0, 0, 0))
    a = (warp[:, :, 3:4].astype(np.float32) / 255.0)
    pasted = (bg.astype(np.float32) * (1 - a) + warp[:, :, :3] * a).astype(np.uint8)
    logo_mask = (warp[:, :, 3] > 10).astype(np.uint8) * 255
    src = np.array([[0, 0], [lw, 0], [lw, lh], [0, lh]], np.float32)
    quad = (M[:, :2] @ src.T).T + M[:, 2]
    return pasted, logo_mask, quad


def inpaint_mask_from_logo(logo_mask: np.ndarray, dilate: int = 0) -> np.ndarray:
    """Mask cho diffusion = MỌI NƠI TRỪ logo (inverted). dilate>0 chừa viền."""
    m = logo_mask.copy()
    if dilate > 0:
        m = cv2.dilate(m, np.ones((dilate, dilate), np.uint8))
    return 255 - m


def composite_back(generated: np.ndarray, pasted: np.ndarray,
                   logo_mask: np.ndarray, feather: int = 3) -> np.ndarray:
    """Trả logo gốc (từ pasted) vào ảnh sinh qua mask, blend mềm viền (chống seam)."""
    m = logo_mask.astype(np.float32) / 255.0
    if feather > 0:
        m = cv2.GaussianBlur(m, (2 * feather + 1, 2 * feather + 1), 0)
    m = m[:, :, None]
    return (generated.astype(np.float32) * (1 - m)
            + pasted.astype(np.float32) * m).astype(np.uint8)


# --------------------------------------------------------------------------- #
# QC — embedding distance gate (cho luồng Tầng 2)
# --------------------------------------------------------------------------- #

def embedding_qc(crop_gen: np.ndarray, crop_ref: np.ndarray, embedder,
                 thr: float = 0.6) -> tuple[bool, float]:
    """Giữ biến thể nếu embedding(crop sinh) ~ embedding(logo gốc) (cosine > thr)."""
    import numpy as _np
    def rgb(x): return cv2.cvtColor(x, cv2.COLOR_BGR2RGB)
    v = embedder.embed([rgb(crop_gen), rgb(crop_ref)])
    cos = float(v[0] @ v[1] / (_np.linalg.norm(v[0]) * _np.linalg.norm(v[1]) + 1e-9))
    return cos >= thr, cos


# --------------------------------------------------------------------------- #
# Diffusion pipeline (lazy)
# --------------------------------------------------------------------------- #

def load_pipe(model: str, controlnet: str, device: str):
    import torch
    from diffusers import (StableDiffusionXLControlNetInpaintPipeline,
                           ControlNetModel)
    cn = ControlNetModel.from_pretrained(controlnet, torch_dtype=torch.float16)
    pipe = StableDiffusionXLControlNetInpaintPipeline.from_pretrained(
        model, controlnet=cn, torch_dtype=torch.float16, variant="fp16")
    pipe = pipe.to(device)
    return pipe


def generate_one(pipe, pasted, logo_mask, strength=0.85, steps=30, cscale=0.7):
    from PIL import Image
    from controlnet_aux import CannyDetector
    canny = CannyDetector()
    edge = canny(Image.fromarray(cv2.cvtColor(pasted, cv2.COLOR_BGR2RGB)))
    inpaint = inpaint_mask_from_logo(logo_mask)
    gen = pipe(
        prompt=random.choice(PROMPTS),
        image=Image.fromarray(cv2.cvtColor(pasted, cv2.COLOR_BGR2RGB)),
        mask_image=Image.fromarray(inpaint),
        control_image=edge,
        strength=strength, controlnet_conditioning_scale=cscale,
        num_inference_steps=steps,
    ).images[0]
    return cv2.cvtColor(np.array(gen), cv2.COLOR_RGB2BGR)


def run(a) -> None:
    from synth_copypaste import load_logo_rgba, grass_bg, brand_key, to_obb_line, IMG_EXT
    random.seed(a.seed); np.random.seed(a.seed)
    logos = [(brand_key(p.name), load_logo_rgba(p))
             for p in sorted(Path(a.logos).iterdir()) if p.suffix.lower() in IMG_EXT]
    logos = [(b, im) for b, im in logos if im is not None]
    bgs = ([p for p in Path(a.backgrounds).iterdir() if p.suffix.lower() in IMG_EXT]
           if a.backgrounds else [])
    out = Path(a.out); (out / "images").mkdir(parents=True, exist_ok=True)
    (out / "labels").mkdir(exist_ok=True); (out / "crops").mkdir(exist_ok=True)

    pipe = load_pipe(a.model, a.controlnet, a.device)   # nặng — chỉ khi chạy thật
    n_ok = 0
    for i in range(a.n):
        bg = (cv2.resize(cv2.imread(str(random.choice(bgs))), (1024, 1024))
              if bgs else grass_bg(1024, 1024))
        brand, logo = random.choice(logos)
        pasted, lmask, quad = paste_with_mask(bg, logo)
        gen = generate_one(pipe, pasted, lmask, strength=a.strength)
        final = composite_back(gen, pasted, lmask) if not a.tier2 else gen
        H, W = final.shape[:2]
        stem = f"b3_{i:05d}"
        cv2.imwrite(str(out / "images" / f"{stem}.jpg"), final)
        (out / "labels" / f"{stem}.txt").write_text(to_obb_line(quad, 0, W, H))
        n_ok += 1
    (out / "data.yaml").write_text(
        f"path: {out.resolve()}\ntrain: images\nval: images\nnc: 1\nnames:\n  0: logo\n")
    print(f"[synth-b3] {n_ok} ảnh diffusion → {out} "
          f"({'Tầng2 giữ biến thể' if a.tier2 else 'Tầng1 composite_back'})")


def _selftest() -> None:
    bg = np.zeros((64, 64, 3), np.uint8)
    logo = np.dstack([np.full((20, 20, 3), 200, np.uint8),
                      np.full((20, 20), 255, np.uint8)])
    random.seed(0); np.random.seed(0)
    pasted, lmask, quad = paste_with_mask(bg, logo)
    assert lmask.max() == 255 and quad.shape == (4, 2)
    # inpaint mask = inverted
    inv = inpaint_mask_from_logo(lmask)
    assert np.all((inv == 0) == (lmask == 255)), "inpaint mask phải đảo logo"
    # composite_back: vùng logo lấy lại đúng từ pasted (giả 'generated' khác hẳn)
    gen = np.full_like(pasted, 99)
    out = composite_back(gen, pasted, lmask, feather=0)
    logo_px = lmask == 255
    assert np.array_equal(out[logo_px], pasted[logo_px]), "logo phải khôi phục đúng"
    assert np.all(out[~logo_px] == 99), "ngoài logo giữ ảnh sinh"
    print("  synth_diffusion selftest: OK ✅")


def main() -> None:
    ap = argparse.ArgumentParser(description="Bậc 3 — diffusion inpainting")
    ap.add_argument("--logos")
    ap.add_argument("--backgrounds", default=None)
    ap.add_argument("--out", default="data/synth_b3")
    ap.add_argument("--n", type=int, default=100)
    ap.add_argument("--model", default="stabilityai/stable-diffusion-xl-base-1.0")
    ap.add_argument("--controlnet", default="diffusers/controlnet-canny-sdxl-1.0")
    ap.add_argument("--strength", type=float, default=0.85)
    ap.add_argument("--tier2", action="store_true",
                    help="BỎ composite_back, giữ biến thể cho Tầng 2 (embedding-gate)")
    ap.add_argument("--device", default="cuda")
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args()
    if a.selftest:
        _selftest(); return
    if not a.logos:
        ap.error("cần --logos (hoặc --selftest)")
    run(a)


if __name__ == "__main__":
    main()
