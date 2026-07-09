"""M2 — Gán nhãn cụm inventory bằng cầu nối ngoại hình anchor→cluster (docs/12).

Anchor (OCR full-frame, đã biết brand + box) → crop THẬT → embed DINOv2.
Cụm nào có mean-embedding gần anchor-crop (REAL↔REAL, chỗ DINOv2 làm tốt)
→ thừa hưởng brand. Cụm rác/không khớp → unlabeled. Đầu ra: nhãn cho từng
crop mined → nguyên liệu train student (M3).

    python inventory/label_clusters.py --clusters data/inventory/clusters \
        --jersey data/inventory/jersey --dets data/exposure_dense/detections.jsonl \
        --video data/real/yt/bradford_home.mp4 --out data/inventory/crop_labels.jsonl
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

import cv2
import numpy as np

sys.path.insert(0, str(Path(__file__).parent))
from cluster_slots import prep  # noqa

PAD = 0.25          # nới box anchor (OCR box ôm sát chữ, logo rộng hơn)
TAU = 0.60          # cosine tối thiểu anchor↔cluster
MIN_N = 20          # chỉ xét cụm đủ lớn


def embed_batch(imgs, proc, model, dev):
    import torch
    from PIL import Image
    with torch.no_grad():
        inp = proc(images=[Image.fromarray(x) for x in imgs],
                   return_tensors="pt").to(dev)
        f = model(**inp).last_hidden_state[:, 0]
        return torch.nn.functional.normalize(f, dim=-1).cpu().numpy()


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--clusters", required=True, type=Path)
    ap.add_argument("--jersey", required=True, type=Path)
    ap.add_argument("--dets", required=True)
    ap.add_argument("--video", required=True)
    ap.add_argument("--out", required=True, type=Path)
    ap.add_argument("--tau", type=float, default=TAU)
    a = ap.parse_args()

    import torch
    from transformers import AutoImageProcessor, AutoModel
    dev = "cuda" if torch.cuda.is_available() else "cpu"
    proc = AutoImageProcessor.from_pretrained("facebook/dinov2-small")
    model = AutoModel.from_pretrained("facebook/dinov2-small").to(dev).eval()

    # 1) anchor crops per brand (RGB, nền giữ nguyên — real thật)
    dets = [json.loads(l) for l in open(a.dets, encoding="utf-8")]
    cap = cv2.VideoCapture(a.video)
    anchor_imgs, anchor_brands = [], []
    for d in dets:
        cap.set(cv2.CAP_PROP_POS_FRAMES, d["frame"])
        ok, fr = cap.read()
        if not ok:
            continue
        x0, y0, x1, y1 = d["box"]
        pw, ph = int((x1 - x0) * PAD), int((y1 - y0) * PAD)
        H, W = fr.shape[:2]
        c = fr[max(0, y0 - ph):min(H, y1 + ph), max(0, x0 - pw):min(W, x1 + pw)]
        if c.size == 0:
            continue
        rgba = np.dstack([c, np.full(c.shape[:2], 255, np.uint8)])
        anchor_imgs.append(cv2.cvtColor(prep(rgba), cv2.COLOR_BGR2RGB))
        anchor_brands.append(d["brand"])
    cap.release()
    print(f"anchors: {len(anchor_imgs)} crops, brands={dict(Counter(anchor_brands))}")
    AV = embed_batch(anchor_imgs, proc, model, dev)

    # 2) cluster mean embeddings
    clusters = json.loads((a.clusters / "clusters.json").read_text(encoding="utf-8"))
    meta = {m["name"]: m for m in
            (json.loads(l) for l in (a.jersey / "meta.jsonl").read_text().splitlines())}
    cd = a.jersey / "crops"
    out_rows, labeled = [], {}
    for c in clusters:
        if c["n"] < MIN_N:
            continue
        mem = sorted(c["members"], key=lambda n: -max(meta[n]["wh"]))[:16]
        imgs = []
        for n in mem:
            im = cv2.imread(str(cd / f"{n}.png"), cv2.IMREAD_UNCHANGED)
            if im is not None and im.ndim == 3 and im.shape[2] == 4:
                imgs.append(cv2.cvtColor(prep(im), cv2.COLOR_BGR2RGB))
        if not imgs:
            continue
        V = embed_batch(imgs, proc, model, dev)
        q = V.mean(0); q /= np.linalg.norm(q)
        sims = AV @ q
        per = defaultdict(float)
        for s, b in zip(sims, anchor_brands):
            per[b] = max(per[b], float(s))
        best = max(per, key=per.get)
        top = per[best]
        second = max([v for b, v in per.items() if b != best], default=0.0)
        label = best if (top >= a.tau and top - second >= 0.03) else "unlabeled"
        labeled[c["cid"]] = label
        out_rows.append({"cid": c["cid"], "n": c["n"], "slot": c["slot"],
                         "label": label, "sim": round(top, 3),
                         "sims": {b: round(v, 3) for b, v in per.items()}})
        print(f"C{c['cid']:<4} n={c['n']:<4} {c['slot']:<9} -> {label:<10} "
              f"sim={top:.3f} {dict((b, round(v, 2)) for b, v in per.items())}")

    # 3) crop-level labels
    with a.out.open("w", encoding="utf-8") as f:
        n_lab = 0
        for c in clusters:
            lb = labeled.get(c["cid"], "unlabeled")
            for n in c["members"]:
                f.write(json.dumps({"name": n, "brand": lb,
                                    "cid": c["cid"], "slot": c["slot"]}) + "\n")
                n_lab += lb != "unlabeled"
    print(f"\n[labels] {n_lab} crop có brand -> {a.out}")
    (a.clusters / "cluster_labels.json").write_text(
        json.dumps(out_rows, ensure_ascii=False, indent=1), encoding="utf-8")


if __name__ == "__main__":
    main()
