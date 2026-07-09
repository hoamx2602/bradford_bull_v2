"""M1a(3) — Phân đội bằng rule màu (few-shot: rule định nghĩa từ soi montage).

Trận bradford_home: Bradford = vàng-hổ-phách sọc đen; đối thủ = trắng sọc xanh
nhạt; trọng tài = xanh lá; nhân viên = hi-vis. Dùng hist HS (12 hue×4 sat, đã lưu
khi track): amber = hue[0..1]&sat cao, blue = hue[6..7], green = hue[3..4].

    python inventory/team_rule.py --tracks data/inventory/tracks \
        --video data/real/yt/bradford_home.mp4
"""
from __future__ import annotations

import argparse
import json
from collections import defaultdict
from pathlib import Path

import cv2
import numpy as np


def scores(hist48: np.ndarray) -> dict:
    h = hist48.reshape(12, 4)  # hue bins 15° × sat bins 64
    return {
        "amber": float(h[0:2, 2:4].sum()),   # H 0-30°, S cao (vàng/cam đậm)
        "blue":  float(h[6:8, 1:4].sum()),   # H 90-120°
        "green": float(h[3:5, 2:4].sum()),   # H 45-75° (áo trọng tài; nền cỏ đã
                                             # loãng do lấy median nhiều mẫu)
    }


def classify(s: dict) -> str:
    vals = sorted(s.values(), reverse=True)
    top = vals[0]
    if top < 0.12:
        return "other"           # trắng/xám chủ đạo, không màu đặc trưng
    if s["amber"] == top and s["amber"] > 1.3 * s["blue"]:
        return "bradford"
    if s["blue"] == top and s["blue"] > 1.3 * s["amber"]:
        return "opponent"
    if s["green"] == top:
        return "refgreen"
    return "other"


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--tracks", required=True, type=Path)
    ap.add_argument("--video", required=True)
    ap.add_argument("--montage-n", type=int, default=16)
    a = ap.parse_args()

    feats = json.loads((a.tracks / "track_color_feats.json").read_text())
    labels = {t: classify(scores(np.array(v, np.float32)))
              for t, v in feats.items()}
    (a.tracks / "team_labels.json").write_text(json.dumps(labels), encoding="utf-8")
    cnt = defaultdict(int)
    for l in labels.values():
        cnt[l] += 1
    print(f"[team-rule] {dict(cnt)}")

    # montage kiểm tra lớp bradford (và opponent để đối chiếu)
    by_tid = defaultdict(list)
    for ln in (a.tracks / "tracks.jsonl").read_text().splitlines():
        d = json.loads(ln)
        by_tid[str(d["tid"])].append(d)
    cap = cv2.VideoCapture(a.video)
    rows = []
    for cls in ("bradford", "opponent"):
        tids = [t for t, l in labels.items() if l == cls]
        tids.sort(key=lambda t: -len(by_tid[t]))
        cells = []
        for t in tids[:a.montage_n]:
            d = max(by_tid[t], key=lambda x: x["xyxy"][3] - x["xyxy"][1])
            cap.set(cv2.CAP_PROP_POS_FRAMES, d["fi"] * 2)
            ok, fr = cap.read()
            if not ok:
                continue
            x0, y0, x1, y1 = (int(v) for v in d["xyxy"])
            crop = fr[y0:y0 + int((y1 - y0) * 0.6), x0:x1]
            if crop.size == 0:
                continue
            s = 120 / max(crop.shape[:2])
            crop = cv2.resize(crop, (max(1, int(crop.shape[1] * s)),
                                     max(1, int(crop.shape[0] * s))))
            cell = np.full((130, 100, 3), 245, np.uint8)
            cell[:min(120, crop.shape[0]), :min(100, crop.shape[1])] = crop[:120, :100]
            cv2.putText(cell, f"t{t}", (2, 128), cv2.FONT_HERSHEY_SIMPLEX,
                        0.35, (0, 0, 255), 1)
            cells.append(cell)
        if not cells:
            continue
        while len(cells) < a.montage_n:
            cells.append(np.full((130, 100, 3), 245, np.uint8))
        strip = np.hstack(cells[:a.montage_n])
        head = np.full((26, strip.shape[1], 3), 255, np.uint8)
        cv2.putText(head, f"{cls.upper()} ({len(tids)} tracks)", (6, 19),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.55, (180, 60, 0), 2)
        rows += [head, strip]
    cap.release()
    out = a.tracks / "team_rule_check.png"
    cv2.imwrite(str(out), np.vstack(rows))
    print(f"montage: {out}")


if __name__ == "__main__":
    main()
