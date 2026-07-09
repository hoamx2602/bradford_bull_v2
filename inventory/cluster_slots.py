"""M1c/d — Gom crop logo jersey về cụm inventory (docs/12).

Embed DINOv2 (REAL↔REAL — vai trò đúng của nó; real↔template mới là chỗ fail cũ)
→ leader-clustering cosine → cụm = 1 bề mặt/slot ứng viên. Tên gợi ý theo median
(u,v) trên person bbox. Gate M1: cụm ngực thuần ≥90% (soi montage).

    python inventory/cluster_slots.py --jersey data/inventory/jersey \
        --out data/inventory/clusters --tau 0.65
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import cv2
import numpy as np


def prep(rgba: np.ndarray, size: int = 224) -> np.ndarray:
    """mask→nền xám 114, tight-crop, letterbox vuông, Lanczos (theo review CV)."""
    rgb, a = rgba[:, :, :3], rgba[:, :, 3]
    ys, xs = np.where(a > 10)
    if len(ys) == 0:
        return cv2.resize(rgb, (size, size), interpolation=cv2.INTER_LANCZOS4)
    y0, y1, x0, x1 = ys.min(), ys.max() + 1, xs.min(), xs.max() + 1
    rgb, a = rgb[y0:y1, x0:x1].copy(), a[y0:y1, x0:x1]
    rgb[a <= 10] = 114
    h, w = rgb.shape[:2]
    s = size / max(h, w)
    rgb = cv2.resize(rgb, (max(1, int(w * s)), max(1, int(h * s))),
                     interpolation=cv2.INTER_LANCZOS4)
    out = np.full((size, size, 3), 114, np.uint8)
    yo, xo = (size - rgb.shape[0]) // 2, (size - rgb.shape[1]) // 2
    out[yo:yo + rgb.shape[0], xo:xo + rgb.shape[1]] = rgb
    return out


def slot_name(u: float, v: float) -> str:
    if v < 0.16:  return "collar/head"
    if v < 0.40:  return "chest" if 0.25 <= u <= 0.75 else "sleeve"
    if v < 0.55:  return "abdomen"
    if v < 0.72:  return "shorts"
    return "legs"


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--jersey", required=True, type=Path)
    ap.add_argument("--out", required=True, type=Path)
    ap.add_argument("--model", default="facebook/dinov2-small")
    ap.add_argument("--tau", type=float, default=0.65, help="cosine để nhập cụm")
    ap.add_argument("--min-px", type=int, default=14, help="bỏ crop nhỏ hơn (cạnh dài)")
    ap.add_argument("--montage-top", type=int, default=14)
    a = ap.parse_args()
    a.out.mkdir(parents=True, exist_ok=True)

    meta = [json.loads(l) for l in
            (a.jersey / "meta.jsonl").read_text().splitlines()]
    crop_dir = a.jersey / "crops"

    import torch
    from transformers import AutoImageProcessor, AutoModel
    from PIL import Image
    dev = "cuda" if torch.cuda.is_available() else "cpu"
    proc = AutoImageProcessor.from_pretrained(a.model)
    model = AutoModel.from_pretrained(a.model).to(dev).eval()

    keep, imgs = [], []
    for m in meta:
        if max(m["wh"]) < a.min_px:
            continue
        im = cv2.imread(str(crop_dir / f"{m['name']}.png"), cv2.IMREAD_UNCHANGED)
        if im is None or im.ndim != 3 or im.shape[2] != 4:
            continue
        keep.append(m)
        imgs.append(cv2.cvtColor(prep(im), cv2.COLOR_BGR2RGB))
    print(f"embedding {len(keep)} crops (of {len(meta)})")

    vecs = []
    B = 64
    with torch.no_grad():
        for i in range(0, len(imgs), B):
            inp = proc(images=[Image.fromarray(x) for x in imgs[i:i + B]],
                       return_tensors="pt").to(dev)
            f = model(**inp).last_hidden_state[:, 0]
            vecs.append(torch.nn.functional.normalize(f, dim=-1).cpu().numpy())
    V = np.concatenate(vecs, 0).astype(np.float32)

    # leader clustering: duyệt theo kích thước crop giảm dần (crop to = leader nét)
    order = sorted(range(len(keep)), key=lambda i: -max(keep[i]["wh"]))
    leaders: list[int] = []
    assign = np.full(len(keep), -1, int)
    for i in order:
        if leaders:
            sims = V[np.array(leaders)] @ V[i]
            j = int(np.argmax(sims))
            if sims[j] >= a.tau:
                assign[i] = j
                continue
        assign[i] = len(leaders)
        leaders.append(i)

    # gộp thống kê cụm
    clusters = []
    for ci in range(len(leaders)):
        idx = np.where(assign == ci)[0]
        if len(idx) < 3:
            continue
        us = np.median([keep[i]["u"] for i in idx])
        vs = np.median([keep[i]["v"] for i in idx])
        clusters.append({"cid": ci, "n": int(len(idx)),
                         "u": round(float(us), 3), "v": round(float(vs), 3),
                         "slot": slot_name(us, vs),
                         "members": [keep[i]["name"] for i in idx]})
    clusters.sort(key=lambda c: -c["n"])
    (a.out / "clusters.json").write_text(
        json.dumps(clusters, ensure_ascii=False, indent=1), encoding="utf-8")

    # montage top clusters
    name2img = {m["name"]: im for m, im in zip(keep, imgs)}
    rows = []
    for c in clusters[:a.montage_top]:
        cells = []
        # ưu tiên crop to
        mem = sorted(c["members"],
                     key=lambda n: -max(next(m["wh"] for m in keep if m["name"] == n)))
        for n in mem[:12]:
            im = cv2.cvtColor(name2img[n], cv2.COLOR_RGB2BGR)
            im = cv2.resize(im, (96, 96))
            cells.append(im)
        while len(cells) < 12:
            cells.append(np.full((96, 96, 3), 245, np.uint8))
        strip = np.hstack(cells)
        head = np.full((24, strip.shape[1], 3), 255, np.uint8)
        cv2.putText(head, f"C{c['cid']}  n={c['n']}  slot={c['slot']}  "
                          f"(u={c['u']}, v={c['v']})", (6, 17),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (180, 60, 0), 1)
        rows += [head, strip]
    cv2.imwrite(str(a.out / "clusters_top.png"), np.vstack(rows))
    print(f"[clusters] {len(clusters)} cụm (n>=3) từ {len(keep)} crop; "
          f"top: {[(c['slot'], c['n']) for c in clusters[:8]]}")
    print(f"montage: {a.out / 'clusters_top.png'}")


if __name__ == "__main__":
    main()
