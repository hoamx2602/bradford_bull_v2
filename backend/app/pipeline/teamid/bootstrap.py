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
from app.pipeline.teamid.jersey import (
    box_trustworthy, boxes_contested, get_jersey_region, jersey_quality,
)

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


def _otsu_threshold(vals: np.ndarray, bins: int = 64) -> float:
    """Classic Otsu split of a 1-D sample in [0,1] — threshold that maximises
    inter-class variance between the two sides."""
    hist, edges = np.histogram(np.clip(vals, 0.0, 1.0), bins=bins, range=(0.0, 1.0))
    hist = hist.astype(np.float64)
    centers = (edges[:-1] + edges[1:]) / 2
    total = hist.sum()
    best_thr, best_var = 0.5, -1.0
    w0 = cum0 = 0.0
    mean_all = float((hist * centers).sum() / (total + 1e-12))
    for i in range(bins - 1):
        w0 += hist[i]
        cum0 += hist[i] * centers[i]
        w1 = total - w0
        if w0 <= 0 or w1 <= 0:
            continue
        m0, m1 = cum0 / w0, (mean_all * total - cum0) / w1
        var = w0 * w1 * (m0 - m1) ** 2
        if var > best_var:
            best_var, best_thr = var, float(edges[i + 1])
    return best_thr


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
    enough = 150  # plenty for a stable Otsu split / centroids
    for fi in idxs:
        if len(regions) >= enough:
            break
        cap.set(cv2.CAP_PROP_POS_FRAMES, int(fi))
        ok, frame = cap.read()
        if not ok:
            continue
        res = model.predict(frame, classes=[0], conf=s.team_person_conf,
                            imgsz=s.team_person_imgsz, device=device, verbose=False)
        if not res or res[0].boxes is None:
            continue
        boxes = res[0].boxes.xyxy.cpu().numpy()
        contested = boxes_contested(boxes)
        for bi, box in enumerate(boxes):
            if contested[bi] or not box_trustworthy(box, frame.shape[0]):
                continue
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
    a_emb, a_cf = _anchor_features(kit, device)

    # Both pick rules need colour features, so drop crops without one.
    keep = [i for i, c in enumerate(color_feats) if c is not None]
    if len(keep) < MIN_CROPS:
        return None
    regions = [regions[i] for i in keep]
    color_feats = [color_feats[i] for i in keep]
    if embeddings is not None:
        embeddings = embeddings[keep]

    if a_emb is not None or a_cf is not None:
        # ── Anchor mode: cluster, pick the cluster most similar to anchors ─
        feats = embeddings if embeddings is not None else np.stack(color_feats)
        k = 3 if len(feats) >= 3 * 8 else 2   # 2 teams + officials
        labels, _ = _kmeans(feats, k)
        scores = []
        for j in range(k):
            ix = np.where(labels == j)[0]
            # A real team holds a sizeable share of crops; tiny clusters are
            # outliers (shadowed crops, officials) and must not win the pick.
            if len(ix) < MIN_TARGET_FRAC * len(labels):
                scores.append(-1e9)
                continue
            sim = 0.0
            n_terms = 0
            if a_emb is not None and embeddings is not None:
                c = embeddings[ix].mean(0)
                c /= (np.linalg.norm(c) + 1e-8)
                sim += float(c @ a_emb)
                n_terms += 1
            if a_cf is not None:
                sim += color_sim(np.mean([color_feats[i] for i in ix], axis=0), a_cf)
                n_terms += 1
            scores.append(sim / max(1, n_terms))
        pick = int(np.argmax(scores))
        assignments = [TARGET if l == pick else OTHER for l in labels]
        mode = "anchors"
    else:
        # ── Luminance mode: 1-D Otsu split on shirt luminance ─────────────
        # No kmeans here: with one team dominating the crops (e.g. a try
        # celebration) kmeans splits the dominant kit into two clusters and
        # blends the real opponent into "other", dragging both centroids to
        # the middle and flipping half the squad. The luminance assumption
        # is one-dimensional, so split it one-dimensionally.
        lums = np.array([_luminance(c) for c in color_feats])
        thr = _otsu_threshold(lums)
        dark_mean = float(lums[lums <= thr].mean())
        light_mean = float(lums[lums > thr].mean())
        if light_mean - dark_mean < 0.10:
            log.warning("team bootstrap: kits not separable by luminance "
                        "(dark %.2f vs light %.2f) — add kit anchors. Skipping",
                        dark_mean, light_mean)
            return None
        dark = kit in {x.strip() for x in s.team_dark_kits.split(",")}
        is_target = (lums <= thr) if dark else (lums > thr)
        assignments = [TARGET if t else OTHER for t in is_target]
        mode = "luminance"

    n_pick = sum(1 for a in assignments if a == TARGET)
    if not (MIN_TARGET_FRAC * len(assignments)
            <= n_pick
            <= (1 - MIN_TARGET_FRAC) * len(assignments)):
        log.warning("team bootstrap: implausible target share (%d/%d) — skipping",
                    n_pick, len(assignments))
        return None

    log.info("team bootstrap: %d crops, target=%d crops (by %s)",
             len(assignments), n_pick, mode)
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
