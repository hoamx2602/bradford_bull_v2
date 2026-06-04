"""
SigLIP encoder — shared by ref_build.py and process_video.py.

Provides a module-level singleton so the model is loaded once and reused
across calls within the same process.
"""
import cv2
import numpy as np
import torch
from PIL import Image

_processor = None
_model     = None


def load_siglip(model_name: str = 'google/siglip-base-patch16-224'):
    """Load (or return cached) SigLIP processor + model."""
    global _processor, _model
    if _model is not None:
        return _processor, _model

    from transformers import SiglipModel, SiglipProcessor

    device = 'cuda' if torch.cuda.is_available() else 'cpu'
    print(f"Loading SigLIP  ({model_name})  on {device} ...")
    _processor = SiglipProcessor.from_pretrained(model_name)
    _model     = SiglipModel.from_pretrained(model_name).to(device).eval()
    dim = _model.config.vision_config.hidden_size
    print(f"SigLIP ready — {dim}-dim embeddings")
    return _processor, _model


def encode_crops(crops_bgr: list, processor, model, batch_size: int = 32) -> np.ndarray:
    """
    Encode a list of BGR numpy crops with SigLIP.

    Returns
    -------
    np.ndarray, shape (N, D), float32, L2-normalised
    """
    if not crops_bgr:
        dim = model.config.vision_config.hidden_size
        return np.empty((0, dim), dtype=np.float32)

    device  = next(model.parameters()).device
    all_emb = []

    for i in range(0, len(crops_bgr), batch_size):
        batch  = crops_bgr[i: i + batch_size]
        images = [Image.fromarray(cv2.cvtColor(c, cv2.COLOR_BGR2RGB)) for c in batch]
        inputs = processor(images=images, return_tensors='pt').to(device)
        with torch.no_grad():
            feats = model.get_image_features(**inputs)
        feats = feats / feats.norm(dim=-1, keepdim=True)
        all_emb.append(feats.cpu().float().numpy())

    return np.concatenate(all_emb, axis=0)
