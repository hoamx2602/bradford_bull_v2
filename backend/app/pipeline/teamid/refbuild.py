"""Manual reference building — web port of team_detection/ref_build.py.

Flow (driven by the /api/team-refs endpoints):
    1. extract_for_labeling(): sample frames, keep ISOLATED player crops
       (same trust/quality gates as the auto bootstrap, plus an isolation
       rule), auto-suggest a team per crop via the Otsu luminance split.
    2. The dashboard shows the crops pre-coloured by suggestion; the user
       fixes any wrong ones and saves.
    3. build_refs_from_labels(): learn_weights over the human-confirmed
       assignments -> the same refs schema the auto bootstrap produces,
       written to TEAM_REFS_PATH so every subsequent analysis uses it.

Human labels beat any clustering: a clip with only one team visible, or two
kits a heuristic can't split, is still labelable by a person in seconds.
"""
from __future__ import annotations

import base64
import logging
from pathlib import Path

import cv2
import numpy as np

from app.config import get_settings
from app.models_zoo import registry
from app.pipeline.teamid.bootstrap import _kmeans, _luminance, _otsu_threshold
from app.pipeline.teamid.classifier import OTHER, TARGET, learn_weights
from app.pipeline.teamid.features import color_feature, encode_crops_masked
from app.pipeline.teamid.jersey import (
    box_iou, box_trustworthy, get_jersey_region, jersey_quality,
)

log = logging.getLogger("app.teamid")

MIN_QUALITY = 0.35      # ref_build.py default — looser than auto-bootstrap
                        # because a human verifies every crop anyway
MIN_HEIGHT_FRAC = 0.07  # min player height as a fraction of frame height
ISO_MAX_IOU = 0.25      # crop must not overlap any other person beyond this
THUMB_PX = 144
MAX_CROPS = 160


def _letterbox(img_bgr: np.ndarray, size: int = THUMB_PX, bg: int = 35) -> np.ndarray:
    ih, iw = img_bgr.shape[:2]
    s = min(size / iw, size / ih)
    nw, nh = max(1, int(iw * s)), max(1, int(ih * s))
    r = cv2.resize(img_bgr, (nw, nh))
    out = np.full((size, size, 3), bg, np.uint8)
    out[(size - nh) // 2:(size - nh) // 2 + nh,
        (size - nw) // 2:(size - nw) // 2 + nw] = r
    return out


def _jpeg_data_url(img_bgr: np.ndarray) -> str:
    ok, buf = cv2.imencode(".jpg", img_bgr, [cv2.IMWRITE_JPEG_QUALITY, 82])
    if not ok:
        return ""
    return "data:image/jpeg;base64," + base64.b64encode(buf.tobytes()).decode()


def extract_for_labeling(video_path: Path, kit: str, n_frames: int = 96) -> dict | None:
    """Collect isolated player crops + per-crop features and a suggested team.

    Returns {"thumbs": [data-url], "suggested": [TARGET|OTHER], features...}
    or None when the video yields nothing usable.
    """
    s = get_settings()
    device = registry.device()
    cap = cv2.VideoCapture(str(video_path))
    if not cap.isOpened():
        return None
    total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    frame_h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    idxs = np.linspace(0, max(0, total - 1), min(n_frames, max(1, total))).astype(int)
    min_h_px = int(MIN_HEIGHT_FRAC * frame_h)

    model = registry.get_person_model()
    player_crops: list[np.ndarray] = []   # full-player crops (what the user sees)
    regions, masks = [], []               # jersey bands (what the features use)
    for fi in idxs:
        if len(regions) >= MAX_CROPS:
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
        for bi, box in enumerate(boxes):
            if box[3] - box[1] < min_h_px:
                continue
            if not box_trustworthy(box, frame_h):
                continue
            if any(box_iou(box, boxes[bj]) > ISO_MAX_IOU
                   for bj in range(len(boxes)) if bj != bi):
                continue
            region, mask = get_jersey_region(frame, box)
            if region is None or jersey_quality(region, mask) < MIN_QUALITY:
                continue
            x1, y1, x2, y2 = (max(0, int(v)) for v in box)
            player_crops.append(frame[y1:y2, x1:x2].copy())
            regions.append(region)
            masks.append(mask)
    cap.release()

    if len(regions) < 4:
        return None

    color_feats = [color_feature(r, m) for r, m in zip(regions, masks)]
    keep = [i for i, c in enumerate(color_feats) if c is not None]
    player_crops = [player_crops[i] for i in keep]
    regions = [regions[i] for i in keep]
    masks = [masks[i] for i in keep]
    color_feats = [color_feats[i] for i in keep]
    embeddings = encode_crops_masked(regions, masks, device)

    # Otsu luminance suggestion — same rule as the auto bootstrap, but here a
    # wrong suggestion costs one click instead of a wrong analysis.
    lums = np.array([_luminance(c) for c in color_feats])
    thr = _otsu_threshold(lums)
    dark = (kit or "away").strip().lower() in {
        x.strip() for x in s.team_dark_kits.split(",")
    }
    suggested = [
        TARGET if ((l <= thr) if dark else (l > thr)) else OTHER for l in lums
    ]

    return {
        "thumbs": [_jpeg_data_url(_letterbox(c)) for c in player_crops],
        "suggested": suggested,
        "color_feats": color_feats,
        "embeddings": embeddings,   # (N, D) or None when SigLIP unavailable
        "kit": kit,
    }


def cluster_crops(extraction: dict, n_clusters: int = 3) -> list[dict]:
    """Group the extracted crops into kit clusters for fast team picking.

    Web port of the team_detection/ref_build.py auto-cluster step: instead of
    labelling 100+ crops one by one, the user picks which *cluster* is the
    target team and which is the opponent. KMeans runs on the SigLIP
    embeddings when available (semantic kit separation), else on the colour
    histograms. One cluster is suggested as TARGET — the one whose mean shirt
    luminance matches the uploaded kit (dark vs light) — so a correct pick is
    usually a single confirming click.

    Returns clusters sorted largest-first, each:
        {"id", "members": [crop idx...], "samples": [idx... closest to centroid],
         "size", "suggested": TARGET|OTHER}
    """
    color_feats = extraction["color_feats"]
    embeddings = extraction["embeddings"]
    n = len(color_feats)
    if n < 2:
        return []
    # 2 teams + (often) officials/refs; never more clusters than crops.
    n_clusters = max(2, min(int(n_clusters), 4, n))

    feats = embeddings if embeddings is not None else np.stack(color_feats)
    feats = np.asarray(feats, dtype=np.float64)
    labels, centers = _kmeans(feats, n_clusters)

    # Pick the single TARGET cluster by kit luminance, mirroring the auto
    # bootstrap's 1-D assumption: dark kit -> darkest cluster, light -> lightest.
    lums = np.array([_luminance(c) for c in color_feats])
    dark = (extraction.get("kit") or "away").strip().lower() in {
        x.strip() for x in get_settings().team_dark_kits.split(",")
    }
    present = sorted({int(l) for l in labels})
    cluster_lum = {cid: float(lums[labels == cid].mean()) for cid in present}
    target_cid = (min if dark else max)(cluster_lum, key=cluster_lum.get)

    clusters = []
    for cid in present:
        members = [i for i in range(n) if labels[i] == cid]
        d = np.linalg.norm(feats[members] - centers[cid], axis=1)
        order = np.argsort(d)
        clusters.append({
            "id": cid,
            "members": members,
            "samples": [members[j] for j in order[:6]],
            "size": len(members),
            "suggested": TARGET if cid == target_cid else OTHER,
        })
    clusters.sort(key=lambda c: -c["size"])
    return clusters


def build_refs_from_labels(
    extraction: dict, assignments: list[str | None], persist: bool = True
) -> tuple[dict | None, str]:
    """Build refs from human-confirmed labels.

    `assignments[i]` is TARGET, OTHER, or None (= ignore the crop).
    When `persist` is True the refs are written to the GLOBAL refs file (every
    later analysis uses them); when False they are only returned, so the caller
    can store them per-job (the inline upload team step does this).
    Returns (refs, error_message) — refs is None on validation failure.
    """
    color_feats = extraction["color_feats"]
    if len(assignments) != len(color_feats):
        return None, "assignments length mismatch"

    keep = [i for i, a in enumerate(assignments) if a in (TARGET, OTHER)]
    n_target = sum(1 for i in keep if assignments[i] == TARGET)
    n_other = len(keep) - n_target
    if n_target < 3 or n_other < 3:
        return None, (
            f"need at least 3 crops per team (got {n_target} target, {n_other} other)"
        )

    embeddings = extraction["embeddings"]
    sub_embs = embeddings[keep] if embeddings is not None else None
    sub_cfs = [color_feats[i] for i in keep]
    sub_assign = [assignments[i] for i in keep]

    w_color, w_siglip, centroids, colors = learn_weights(
        [TARGET, OTHER], sub_assign, sub_embs, sub_cfs)

    refs = {
        "schema": 3,
        "teams": {t: {"embedding": centroids.get(t), "color": colors.get(t)}
                  for t in (TARGET, OTHER)},
        "meta": {"w_color": w_color, "w_siglip": w_siglip,
                 "temp_c": 8.0, "temp_s": 15.0,
                 "bootstrap": "manual", "kit": extraction.get("kit", "away"),
                 "n_target": n_target, "n_other": n_other},
    }

    if persist:
        import pickle

        out = Path(get_settings().resolved_team_refs())
        out.parent.mkdir(parents=True, exist_ok=True)
        with out.open("wb") as f:
            pickle.dump(refs, f)
        log.info("manual team refs saved: %s (%d target / %d other, w_color %.2f)",
                 out, n_target, n_other, w_color)
    return refs, ""
