"""Automatic kit-reference bootstrap — no manual CLI step per match.

When a video is uploaded and no refs file exists, the pipeline builds the
references from the video itself:

    1. Sample frames spread across the video, detect + crop players.
    2. Cluster jersey features (SigLIP embeddings when available, colour
       histograms otherwise) with a small numpy KMeans — no sklearn needed.
    3. Pick the TARGET cluster:
         a. If anchor crops exist (data/kit_anchors/<kit>/*.jpg) — the cluster
            most similar to them wins.
         b. Otherwise by kit luminance: the uploaded match's kit (form field)
            maps to dark/light, e.g. Bradford away = black -> darkest cluster.
    4. learn_weights() -> refs dict (same schema as scripts/build_team_refs.py).

A debug copy is written to data/auto_refs/ so a bad pick can be inspected and
overridden by building refs manually.
"""
from __future__ import annotations

import logging
import pickle
from pathlib import Path

import cv2
import numpy as np

from app.config import BACKEND_DIR, get_settings
from app.models_zoo import registry
from app.pipeline.teamid.classifier import OTHER, TARGET, learn_weights
from app.pipeline.teamid.features import N_L, color_feature, color_sim, encode_crops_masked
from app.pipeline.teamid.jersey import get_jersey_region, jersey_quality

log = logging.getLogger("app.teamid")

MIN_QUALITY = 0.45      # reference crops must be sharp + well-covered
MIN_CROPS = 24          # below this, bootstrap refuses (video too short/empty)
MIN_TARGET_FRAC = 0.10  # target cluster must hold >=10% of crops


def _kmeans(X: np.ndarray, k: int, iters: int = 30, seed: int = 0):
    """Tiny numpy KMeans (k-means++ init) — avoids a sklearn dependency."""
    rng = np.random.default_rng(seed)
    # k-means++ seeding
    centers = [X[rng.integers(len(X))]]
    for _ in range(1, k):
        d2 = np.min([(np.linalg.norm(X - c, axis=1) ** 2) for c in centers], axis=0)
        p = d2 / (d2.sum() + 1e-12)
        centers.append(X[rng.choice(len(X), p=p)])
    C = np.stack(centers)

    labels = np.zeros(len(X), dtype=int)
    for _ in range(iters):
        d = ((X[:, None, :] - C[None, :, :]) ** 2).sum(-1)
        new_labels = d.argmin(1)
        if (new_labels == labels).all():
            break
        labels = new_labels
        for j in range(k):
            m = labels == j
            if m.any():
                C[j] = X[m].mean(0)
    return labels, C


def _luminance(color_feat: np.ndarray) -> float:
    """Expected luminance in [0,1] from the L-histogram block."""
    L = color_feat[:N_L]
    centers = (np.arange(N_L) + 0.5) / N_L
    return float((L * centers).sum() / (L.sum() + 1e-8))


def _collect_crops(video_path: Path, n_frames: int, device: str):
    """Sample frames + detect persons -> (regions, masks)."""
    s = get_settings()
    cap = cv2.VideoCapture(str(video_path))
    if not cap.isOpened():
        return [], []
    total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    idxs = np.linspace(0, max(0, total - 1), n_frames).astype(int)

    model = registry.get_person_model()
    regions, masks = [], []
    for fi in idxs:
        cap.set(cv2.CAP_PROP_POS_FRAMES, int(fi))
        ok, frame = cap.read()
        if not ok:
            continue
        res = model.predict(frame, classes=[0], conf=s.team_person_conf,
                            imgsz=s.team_person_imgsz, device=device, verbose=False)
        if not res or res[0].boxes is None:
            continue
        for box in res[0].boxes.xyxy.cpu().numpy():
            region, mask = get_jersey_region(frame, box)
            if region is None or jersey_quality(region, mask) < MIN_QUALITY:
                continue
            regions.append(region)
            masks.append(mask)
    cap.release()
    return regions, masks


def _anchor_features(kit: str, device: str):
    """Features of user-provided anchor crops, or (None, None) if none exist."""
    anchor_dir = BACKEND_DIR / "data" / "kit_anchors" / kit
    if not anchor_dir.is_dir():
        return None, None
    regions, masks = [], []
    for p in sorted(anchor_dir.iterdir()):
        if p.suffix.lower() not in {".jpg", ".jpeg", ".png", ".webp"}:
            continue
        img = cv2.imread(str(p))
        if img is None:
            continue
        h, w = img.shape[:2]
        region, mask = get_jersey_region(img, (0, 0, w, h))
        if region is not None:
            regions.append(region)
            masks.append(mask)
    if not regions:
        return None, None
    embs = encode_crops_masked(regions, masks, device)
    emb = None
    if embs is not None:
        emb = embs.mean(0)
        emb /= (np.linalg.norm(emb) + 1e-8)
    cfs = [c for c in (color_feature(r, m) for r, m in zip(regions, masks)) if c is not None]
    cf = np.mean(cfs, axis=0) if cfs else None
    return emb, cf


def build_refs_from_video(video_path: Path, kit: str) -> dict | None:
    """Returns a refs dict (TeamClassifier schema) or None when bootstrap fails."""
    s = get_settings()
    device = registry.device()
    kit = (kit or "away").strip().lower()

    regions, masks = _collect_crops(video_path, s.team_bootstrap_frames, device)
    if len(regions) < MIN_CROPS:
        log.warning("team bootstrap: only %d usable crops — skipping", len(regions))
        return None

    color_feats = [color_feature(r, m) for r, m in zip(regions, masks)]
    embeddings = encode_crops_masked(regions, masks, device)

    # Cluster on the best feature space we have.
    if embeddings is not None:
        feats = embeddings
    else:
        keep = [i for i, c in enumerate(color_feats) if c is not None]
        if len(keep) < MIN_CROPS:
            return None
        regions = [regions[i] for i in keep]
        color_feats = [color_feats[i] for i in keep]
        feats = np.stack(color_feats)

    k = 3 if len(feats) >= 3 * 8 else 2   # 2 teams + officials when enough data
    labels, _ = _kmeans(feats, k)

    # ── Pick the target cluster ──────────────────────────────────────────
    a_emb, a_cf = _anchor_features(kit, device)
    scores = []
    for j in range(k):
        ix = np.where(labels == j)[0]
        if len(ix) == 0:
            scores.append(-1e9)
            continue
        if a_emb is not None or a_cf is not None:
            sim = 0.0
            n_terms = 0
            if a_emb is not None and embeddings is not None:
                c = embeddings[ix].mean(0)
                c /= (np.linalg.norm(c) + 1e-8)
                sim += float(c @ a_emb)
                n_terms += 1
            if a_cf is not None:
                cfs = [color_feats[i] for i in ix if color_feats[i] is not None]
                if cfs:
                    sim += color_sim(np.mean(cfs, axis=0), a_cf)
                    n_terms += 1
            scores.append(sim / max(1, n_terms))
        else:
            # Luminance rule: dark kits -> darkest cluster wins (negated lum).
            cfs = [color_feats[i] for i in ix if color_feats[i] is not None]
            if not cfs:
                scores.append(-1e9)
                continue
            lum = _luminance(np.mean(cfs, axis=0))
            dark = kit in {x.strip() for x in s.team_dark_kits.split(",")}
            scores.append(-lum if dark else lum)

    pick = int(np.argmax(scores))
    n_pick = int((labels == pick).sum())
    if n_pick < MIN_TARGET_FRAC * len(labels):
        log.warning("team bootstrap: target cluster too small (%d/%d) — skipping",
                    n_pick, len(labels))
        return None

    mode = "anchors" if (a_emb is not None or a_cf is not None) else "luminance"
    log.info("team bootstrap: %d crops, k=%d, target=cluster %d (%d crops, by %s)",
             len(labels), k, pick, n_pick, mode)

    assignments = [TARGET if l == pick else OTHER for l in labels]
    w_color, w_siglip, centroids, colors = learn_weights(
        [TARGET, OTHER], assignments, embeddings, color_feats)

    refs = {
        "schema": 3,
        "teams": {
            t: {"embedding": centroids.get(t), "color": colors.get(t)}
            for t in (TARGET, OTHER)
        },
        "meta": {"w_color": w_color, "w_siglip": w_siglip,
                 "temp_c": 8.0, "temp_s": 15.0,
                 "bootstrap": mode, "kit": kit},
    }

    # Debug copy for inspection / reuse.
    try:
        dbg = BACKEND_DIR / "data" / "auto_refs"
        dbg.mkdir(parents=True, exist_ok=True)
        with (dbg / f"{video_path.stem}-{kit}.pkl").open("wb") as f:
            pickle.dump(refs, f)
    except OSError:
        pass
    return refs
