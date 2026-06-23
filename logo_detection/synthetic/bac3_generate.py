#!/usr/bin/env python3
"""
Bac 3 — Diffusion Inpainting / Harmonization, Bien the C (ControlNet + IP-Adapter).
"Diffusion Copy-Paste" for the class-agnostic Localizer (Tang 1) and, above all,
to feed diverse same-logo appearances to the Recognizer (Tang 2). See
bac3_diffusion_inpainting.md.

Golden rule (8.1): the LOGO is always the real asset, pixel-locked. Diffusion only
regenerates the CONTEXT around it. We enforce this twice:
  1. inpaint_mask = 255 - logo_mask  -> diffusion never denoises logo pixels.
  2. composite_back -> after generation, the original logo pixels are pasted back
     through the mask (insurance against edge bleed). Label = mask -> pixel-perfect.

Why TILE-based (not whole-frame)
--------------------------------
SDXL is trained at ~1024px. Diffusing a whole 1920x1080 frame distorts and makes
tiny logos vanish. Instead we crop a square window around each pasted logo, resize
to 1024, diffuse THAT, and paste it back. The rest of the frame stays the original
REAL footage (its real logos + old labels untouched) — only a small patch around
the new logo is harmonized. Most realistic + cheapest.

Usage
-----
    conda activate bradford_bulls
    python bac3_generate.py --n 8          # smoke test (downloads models 1st run)
    python bac3_generate.py --n 2000 --steps 30
    python bac3_generate.py --no-ip-adapter --no-bg-labels

First run downloads SDXL base + canny-controlnet + IP-Adapter (~10 GB) to the HF
cache. Needs a CUDA GPU with >=12 GB (RTX 4500 Ada 24 GB is plenty).
"""
import argparse
import random
from pathlib import Path
from types import SimpleNamespace

import cv2
import numpy as np

from gen_synthetic import (HERE, LOGO_ROOT, BG_IMAGES, BG_LABELS,
                           imread_unicode, imwrite_unicode, load_logos,
                           transform_logo, read_existing_boxes, to_yolo_line)

PROMPTS = [
    "professional rugby player wearing team jersey, stadium floodlights, "
    "photorealistic broadcast footage, sharp focus",
    "close-up of sports jersey fabric, fabric folds and wrinkles, sponsor board, "
    "stadium lighting, motion blur",
    "athlete running on a rugby pitch, dynamic action, wet from rain, "
    "broadcast camera, depth of field",
    "advertising perimeter board at a rugby stadium, crowd background, "
    "floodlit evening match, photorealistic",
]
NEG_PROMPT = ("blurry logo, distorted text, deformed letters, watermark, "
              "low quality, jpeg artifacts, extra logos, cartoon, drawing")


# --------------------------------------------------------------- compositing utils
def paste_logo_on_canvas(canvas, logo_rgba, x, y):
    """Composite a logo onto canvas at (x,y). Return (xyxy box, full-canvas uint8
    alpha mask of the logo)."""
    h, w = logo_rgba.shape[:2]
    H, W = canvas.shape[:2]
    if x < 0 or y < 0 or x + w > W or y + h > H:
        return None, None
    fg = logo_rgba[:, :, :3].astype(np.float32)
    a = logo_rgba[:, :, 3].astype(np.float32) / 255.0
    a3 = a[:, :, None]
    roi = canvas[y:y + h, x:x + w].astype(np.float32)
    canvas[y:y + h, x:x + w] = (a3 * fg + (1 - a3) * roi).astype(np.uint8)
    mask = np.zeros((H, W), np.uint8)
    mask[y:y + h, x:x + w] = logo_rgba[:, :, 3]
    ys, xs = np.where(mask > 10)
    if len(xs) == 0:
        return None, None
    return (int(xs.min()), int(ys.min()), int(xs.max()), int(ys.max())), mask


def square_window(box, W, H, expand, min_side):
    """Square crop fully inside the frame, centred on the logo box."""
    x1, y1, x2, y2 = box
    cx, cy = (x1 + x2) // 2, (y1 + y2) // 2
    side = int(max(x2 - x1, y2 - y1) * expand)
    side = max(side, min_side)
    side = min(side, W, H)
    x0 = int(np.clip(cx - side // 2, 0, W - side))
    y0 = int(np.clip(cy - side // 2, 0, H - side))
    return x0, y0, side


# -------------------------------------------------------------------- diffusion
def build_pipe(args):
    import torch
    from diffusers import (StableDiffusionXLControlNetInpaintPipeline,
                           ControlNetModel)
    dtype = torch.float16
    print("[model] loading canny controlnet ...")
    controlnet = ControlNetModel.from_pretrained(
        "diffusers/controlnet-canny-sdxl-1.0", torch_dtype=dtype)
    print("[model] loading SDXL inpaint pipeline ...")
    pipe = StableDiffusionXLControlNetInpaintPipeline.from_pretrained(
        "stabilityai/stable-diffusion-xl-base-1.0",
        controlnet=controlnet, torch_dtype=dtype, variant="fp16",
    )
    pipe = pipe.to("cuda")
    pipe.set_progress_bar_config(disable=True)
    if args.ip_adapter:
        try:
            pipe.load_ip_adapter("h94/IP-Adapter", subfolder="sdxl_models",
                                 weight_name="ip-adapter_sdxl.bin")
            pipe.set_ip_adapter_scale(args.ip_scale)
            print(f"[model] IP-Adapter ON (scale={args.ip_scale})")
        except Exception as e:
            print(f"[model] IP-Adapter unavailable -> OFF ({e})")
            args.ip_adapter = False
    try:
        pipe.enable_xformers_memory_efficient_attention()
    except Exception:
        pass
    pipe.enable_vae_tiling()
    return pipe


def harmonize_tile(pipe, tile_bgr, logo_mask_tile, ref_bgr, args, rng):
    """Diffuse the CONTEXT of one square tile, keep the logo locked, composite the
    real logo back. Inputs/outputs are BGR uint8 at the tile's native size."""
    import torch
    from PIL import Image
    S = args.sd_size
    src_size = tile_bgr.shape[0]

    pasted = cv2.resize(tile_bgr, (S, S), interpolation=cv2.INTER_AREA)
    lmask = cv2.resize(logo_mask_tile, (S, S), interpolation=cv2.INTER_NEAREST)
    lmask = cv2.dilate(lmask, np.ones((3, 3), np.uint8), iterations=1)  # protect edge
    inpaint_mask = 255 - lmask                                          # keep logo

    edge = cv2.Canny(pasted, 80, 160)
    control = Image.fromarray(cv2.cvtColor(edge, cv2.COLOR_GRAY2RGB))
    init = Image.fromarray(cv2.cvtColor(pasted, cv2.COLOR_BGR2RGB))
    mask_img = Image.fromarray(inpaint_mask)

    kw = dict(
        prompt=rng.choice(PROMPTS),
        negative_prompt=NEG_PROMPT,
        image=init,
        mask_image=mask_img,
        control_image=control,
        strength=args.strength,
        num_inference_steps=args.steps,
        guidance_scale=args.guidance,
        controlnet_conditioning_scale=args.cn_scale,
        generator=torch.Generator("cuda").manual_seed(rng.randrange(2**31)),
    )
    if args.ip_adapter and ref_bgr is not None:
        kw["ip_adapter_image"] = Image.fromarray(cv2.cvtColor(
            cv2.resize(ref_bgr, (S, S)), cv2.COLOR_BGR2RGB))

    gen = pipe(**kw).images[0]
    gen = cv2.cvtColor(np.array(gen), cv2.COLOR_RGB2BGR)

    # composite_back: original logo pixels win inside the logo mask (pixel-perfect)
    a = (lmask.astype(np.float32) / 255.0)[:, :, None]
    gen = (a * pasted.astype(np.float32) + (1 - a) * gen.astype(np.float32)).astype(np.uint8)

    return cv2.resize(gen, (src_size, src_size), interpolation=cv2.INTER_LINEAR)


# ----------------------------------------------------------------------------- main
def main(args):
    rng = random.Random(args.seed)
    np.random.seed(args.seed)

    logos = load_logos(args.logos, args.white_thresh)
    bgs = [p for p in Path(args.backgrounds).iterdir()
           if p.suffix.lower() in (".jpg", ".jpeg", ".png")]
    if not bgs:
        raise SystemExit(f"No background frames in {args.backgrounds}")
    print(f"[bg] {len(bgs)} background frames")

    out = Path(args.out)
    for sub in ("images/train", "images/val", "labels/train", "labels/val"):
        (out / sub).mkdir(parents=True, exist_ok=True)

    pipe = build_pipe(args)

    n_val = int(args.n * args.val_frac)
    made = 0
    for i in range(args.n):
        split = "val" if i < n_val else "train"
        bg_path = bgs[rng.randrange(len(bgs))]
        frame = imread_unicode(bg_path, cv2.IMREAD_COLOR)
        if frame is None:
            continue
        H, W = frame.shape[:2]

        boxes = read_existing_boxes(Path(args.bg_labels) / (bg_path.stem + ".txt"),
                                    W, H) if args.bg_labels else []

        canvas = frame.copy()
        new_boxes = []
        k = rng.randint(args.min_logos, args.max_logos)
        for _ in range(k):
            _, asset = logos[rng.randrange(len(logos))]
            t = transform_logo(asset, W, H, args, rng)
            h, w = t.shape[:2]
            if w >= W or h >= H or min(h, w) < 6:
                continue
            x, y = rng.randint(0, W - w), rng.randint(0, H - h)
            box, mask = paste_logo_on_canvas(canvas, t, x, y)
            if box is None:
                continue
            x0, y0, side = square_window(box, W, H, args.tile_expand, args.min_tile)
            tile = canvas[y0:y0 + side, x0:x0 + side].copy()
            mtile = mask[y0:y0 + side, x0:x0 + side].copy()
            ref = frame  # real frame as IP-Adapter style reference
            harm = harmonize_tile(pipe, tile, mtile, ref, args, rng)
            canvas[y0:y0 + side, x0:x0 + side] = harm
            new_boxes.append(box)

        if not new_boxes:
            continue

        stem = f"bac3_{i:06d}"
        imwrite_unicode(out / "images" / split / f"{stem}.jpg", canvas,
                        [cv2.IMWRITE_JPEG_QUALITY, 92])
        lines = [to_yolo_line(b, W, H) for b in (boxes + new_boxes)
                 if b[2] > b[0] and b[3] > b[1]]
        (out / "labels" / split / f"{stem}.txt").write_text("\n".join(lines))
        made += 1
        print(f"  [{made}/{args.n}] {stem}  (+{len(new_boxes)} logos)")

    (out / "data.yaml").write_text(
        f"path: {out.resolve().as_posix()}\n"
        "train: images/train\nval: images/val\nnc: 1\nnames: ['logo']\n")
    print(f"\n[done] {made} images -> {out.resolve()}")


def build_parser():
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--logos", default=str(LOGO_ROOT))
    p.add_argument("--backgrounds", default=str(BG_IMAGES))
    p.add_argument("--bg-labels", dest="bg_labels", default=str(BG_LABELS))
    p.add_argument("--no-bg-labels", dest="bg_labels", action="store_const", const="")
    p.add_argument("--out", default=str(HERE / "data_bac3"))
    p.add_argument("--n", type=int, default=2000)
    p.add_argument("--val-frac", type=float, default=0.10)
    p.add_argument("--seed", type=int, default=0)

    # logo placement / geometry (consumed by gen_synthetic.transform_logo)
    p.add_argument("--min-logos", type=int, default=1)
    p.add_argument("--max-logos", type=int, default=2)
    p.add_argument("--min-scale", type=float, default=0.05)
    p.add_argument("--max-scale", type=float, default=0.22)
    p.add_argument("--rotate", type=float, default=12.0)
    p.add_argument("--perspective", type=float, default=0.10)
    p.add_argument("--p-rotate", type=float, default=0.8)
    p.add_argument("--p-perspective", type=float, default=0.6)
    p.add_argument("--p-blur", type=float, default=0.0)   # diffusion adds realism
    p.add_argument("--p-occlude", type=float, default=0.0)
    p.add_argument("--white-thresh", type=int, default=245)

    # tiling
    p.add_argument("--tile-expand", type=float, default=2.8,
                   help="square tile side = logo_side * this")
    p.add_argument("--min-tile", type=int, default=384)
    p.add_argument("--sd-size", type=int, default=1024, help="SDXL working resolution")

    # diffusion
    p.add_argument("--steps", type=int, default=30)
    p.add_argument("--strength", type=float, default=0.9,
                   help="how much context is regenerated (logo stays locked by mask)")
    p.add_argument("--guidance", type=float, default=6.0)
    p.add_argument("--cn-scale", type=float, default=0.7, help="controlnet conditioning")
    p.add_argument("--ip-adapter", dest="ip_adapter", action="store_true", default=True)
    p.add_argument("--no-ip-adapter", dest="ip_adapter", action="store_false")
    p.add_argument("--ip-scale", type=float, default=0.5)
    return p


if __name__ == "__main__":
    main(build_parser().parse_args())
