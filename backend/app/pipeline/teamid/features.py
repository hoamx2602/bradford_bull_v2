"""Per-crop features: colour histogram (always) + SigLIP embedding (optional).

Colour: L1-normalised [L-hist | H-hist] over kept shirt pixels — separates
white-vs-black Bradford kits almost perfectly and is immune to grass.

SigLIP: 768-dim semantic embedding of the background-masked crop. Loaded
lazily; if `transformers` isn't installed everything still works colour-only.
On CUDA the model runs fp16.
"""
from __future__ import annotations

import logging

import cv2
import numpy as np

log = logging.getLogger("app.teamid")

# Colour histogram layout: L (luminance) bins + H (hue) bins.
N_L = 8      # luminance bins (white vs black lives here)
N_H = 12     # hue bins (separates coloured kits, e.g. referee green)
SAT_MIN = 40  # only saturated pixels vote for hue

COLOR_DIM = N_L + N_H


def color_feature(region_bgr: np.ndarray | None, pixel_mask: np.ndarray | None) -> np.ndarray | None:
    """L1-normalised [L-hist (N_L) | H-hist (N_H)] over kept shirt pixels."""
    if region_bgr is None or pixel_mask is None:
        return None
    m = pixel_mask.astype(bool)
    if m.sum() < 5:
        return None

    px_bgr = region_bgr[m].reshape(-1, 1, 3).astype(np.uint8)

    lab = cv2.cvtColor(px_bgr, cv2.COLOR_BGR2LAB).reshape(-1, 3)
    l_hist, _ = np.histogram(lab[:, 0], bins=N_L, range=(0, 256))
    l_hist = l_hist.astype(np.float32)
    l_hist /= (l_hist.sum() + 1e-8)

    hsv = cv2.cvtColor(px_bgr, cv2.COLOR_BGR2HSV).reshape(-1, 3)
    sat_ok = hsv[:, 1] > SAT_MIN
    if sat_ok.sum() >= 3:
        h_hist, _ = np.histogram(hsv[sat_ok, 0], bins=N_H, range=(0, 180))
        h_hist = h_hist.astype(np.float32)
        h_hist /= (h_hist.sum() + 1e-8)
    else:
        h_hist = np.zeros(N_H, dtype=np.float32)

    return np.concatenate([l_hist, h_hist]).astype(np.float32)


def color_sim(fq: np.ndarray, fr: np.ndarray) -> float:
    """Histogram-intersection similarity in [0,1] (L-block weighted higher)."""
    sim_l = float(np.minimum(fq[:N_L], fr[:N_L]).sum())
    sim_h = float(np.minimum(fq[N_L:], fr[N_L:]).sum())
    return 0.65 * sim_l + 0.35 * sim_h


def softmax(x: np.ndarray) -> np.ndarray:
    x = x - x.max()
    e = np.exp(x)
    return e / (e.sum() + 1e-8)


# ── SigLIP (lazy singleton) ──────────────────────────────────────────────

_processor = None
_model = None
_torch_device = None
_unavailable = False


def _resolve_torch_device(device: str) -> str:
    """Map the ultralytics-style device string ('0', 'cuda', 'mps', 'cpu')."""
    if device.isdigit():
        return f"cuda:{device}"
    return device


def siglip_available() -> bool:
    if _unavailable:
        return False
    try:
        import transformers  # noqa: F401
        return True
    except ImportError:
        return False


def load_siglip(device: str, model_name: str = "google/siglip-base-patch16-224"):
    """Load (or return cached) SigLIP processor + model. None if unavailable."""
    global _processor, _model, _torch_device, _unavailable
    if _model is not None:
        return _processor, _model
    if _unavailable:
        return None, None
    try:
        import torch  # noqa: F401
        # Vision tower only — SiglipProcessor/SiglipModel would pull in the
        # text tokenizer (needs sentencepiece) which we never use.
        from transformers import SiglipImageProcessor, SiglipVisionModel

        _torch_device = _resolve_torch_device(device)
        log.info("loading SigLIP vision tower (%s) on %s", model_name, _torch_device)
        _processor = SiglipImageProcessor.from_pretrained(model_name)
        _model = SiglipVisionModel.from_pretrained(model_name).to(_torch_device).eval()
        if _torch_device.startswith("cuda"):
            _model = _model.half()
        return _processor, _model
    except Exception as exc:  # ImportError, download failure, OOM, ...
        log.warning("SigLIP unavailable (%s) — team filter runs colour-only", exc)
        _unavailable = True
        return None, None


def _mask_background(crop_bgr: np.ndarray, pixel_mask: np.ndarray | None) -> np.ndarray:
    if pixel_mask is None or pixel_mask.shape != crop_bgr.shape[:2]:
        return crop_bgr
    out = crop_bgr.copy()
    out[~pixel_mask.astype(bool)] = 0
    return out


def encode_crops_masked(
    crops_bgr: list[np.ndarray],
    pixel_masks: list[np.ndarray | None],
    device: str,
    batch_size: int = 32,
) -> np.ndarray | None:
    """SigLIP-encode background-masked crops. (N, D) float32 L2-normalised,
    or None when SigLIP isn't available."""
    processor, model = load_siglip(device)
    if model is None or not crops_bgr:
        return None

    import torch
    from PIL import Image

    masked = [_mask_background(c, m) for c, m in zip(crops_bgr, pixel_masks)]
    images = [Image.fromarray(cv2.cvtColor(c, cv2.COLOR_BGR2RGB)) for c in masked]

    embs: list[np.ndarray] = []
    with torch.no_grad():
        for i in range(0, len(images), batch_size):
            batch = images[i:i + batch_size]
            inputs = processor(images=batch, return_tensors="pt").to(_torch_device)
            if _torch_device.startswith("cuda"):
                inputs = {k: v.half() if v.is_floating_point() else v for k, v in inputs.items()}
            # pooler_output == SiglipModel.get_image_features (attention-pooled)
            feats = model(**inputs).pooler_output
            feats = feats / feats.norm(dim=-1, keepdim=True)
            embs.append(feats.float().cpu().numpy())
    return np.concatenate(embs, axis=0).astype(np.float32)
