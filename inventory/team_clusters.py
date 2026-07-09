"""M1a(2) — Phân đội theo màu áo (few-shot: người/agent soi montage đặt tên cụm).

KMeans trên color feature per-track → montage torso mẫu mỗi cụm → gán nhãn cụm
(bradford / opponent / ref / other) bằng mắt, ghi vào team_labels.json.

    python inventory/team_clusters.py --tracks data/inventory/tracks \
        --video data/real/yt/bradford_home.mp4 --k 4
"""
from __future__ import annotations

import argparse
import json
from collections import defaultdict
from pathlib import Path

import cv2
import numpy as np


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--tracks", required=True, type=Path)
    ap.add_argument("--video", required=True)
    ap.add_argument("--k", type=int, default=4)
    ap.add_argument("--per-cluster", type=int, default=12)
    a = ap.parse_args()

    feats = json.loads((a.tracks / "track_color_feats.json").read_text())
    tids = sorted(feats, key=int)
    X = np.stack([np.array(feats[t], np.float32) for t in tids])

    # KMeans (numpy thuần — tránh phụ thuộc sklearn)
    rng = np.random.default_rng(0)
    C = X[rng.choice(len(X), a.k, replace=False)]
    for _ in range(50):
        d = ((X[:, None] - C[None]) ** 2).sum(-1)
        lab = d.argmin(1)
        newC = np.stack([X[lab == i].mean(0) if (lab == i).any() else C[i]
                         for i in range(a.k)])
        if np.allclose(newC, C):
            break
        C = newC
    assign = {t: int(l) for t, l in zip(tids, lab)}
    (a.tracks / "team_assign.json").write_text(json.dumps(assign), encoding="utf-8")

    # dets theo track để cắt mẫu torso
    by_tid = defaultdict(list)
    for ln in (a.tracks / "tracks.jsonl").read_text().splitlines():
        d = json.loads(ln)
        by_tid[str(d["tid"])].append(d)

    cap = cv2.VideoCapture(a.video)
    stride_guess = None
    cells_per = defaultdict(list)
    for ci in range(a.k):
        members = [t for t in tids if assign[t] == ci]
        # ưu tiên track dài (ổn định), lấy bbox to nhất của mỗi track
        members.sort(key=lambda t: -len(by_tid[t]))
        for t in members[:a.per_cluster]:
            d = max(by_tid[t], key=lambda x: x["xyxy"][3] - x["xyxy"][1])
            # fi trong tracks.jsonl là chỉ số SAU stride → cần nhân stride thật.
            # stride không lưu — suy từ meta: dùng fi*2 (mặc định stride=2).
            fi_raw = d["fi"] * (stride_guess or 2)
            cap.set(cv2.CAP_PROP_POS_FRAMES, fi_raw)
            ok, fr = cap.read()
            if not ok:
                continue
            x0, y0, x1, y1 = (int(v) for v in d["xyxy"])
            h = y1 - y0
            crop = fr[y0:y0 + int(h * 0.6), x0:x1]  # nửa trên (áo)
            if crop.size == 0:
                continue
            s = 120 / max(crop.shape[:2])
            crop = cv2.resize(crop, (max(1, int(crop.shape[1] * s)),
                                     max(1, int(crop.shape[0] * s))))
            cell = np.full((130, 100, 3), 245, np.uint8)
            cell[:min(120, crop.shape[0]), :min(100, crop.shape[1])] = \
                crop[:120, :100]
            cv2.putText(cell, f"t{t}", (2, 128), cv2.FONT_HERSHEY_SIMPLEX,
                        0.35, (0, 0, 255), 1)
            cells_per[ci].append(cell)
    cap.release()

    rows = []
    for ci in range(a.k):
        cells = cells_per[ci]
        if not cells:
            continue
        while len(cells) < a.per_cluster:
            cells.append(np.full((130, 100, 3), 245, np.uint8))
        strip = np.hstack(cells[:a.per_cluster])
        head = np.full((26, strip.shape[1], 3), 255, np.uint8)
        n_mem = sum(1 for t in tids if assign[t] == ci)
        cv2.putText(head, f"CLUSTER {ci}  ({n_mem} tracks)", (6, 19),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.55, (180, 60, 0), 2)
        rows += [head, strip]
    mont = np.vstack(rows)
    out = a.tracks / "team_clusters.png"
    cv2.imwrite(str(out), mont)
    n_per = {ci: sum(1 for t in tids if assign[t] == ci) for ci in range(a.k)}
    print(f"[team] {len(tids)} tracks -> {a.k} clusters {n_per}; montage: {out}")


if __name__ == "__main__":
    main()
