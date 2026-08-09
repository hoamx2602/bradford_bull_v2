"""M1b — Mine logo trên torso cầu thủ đội target bằng SAM3 (inventory, docs/12).

Chỉ mine cầu thủ đội target (team_assign + nhãn cụm), bbox đủ lớn (logo đọc được),
mỗi track lấy mẫu thưa (inventory không cần mọi frame). Mỗi logo box lưu:
  - crop RGBA (mask SAM3 làm alpha) → cluster/anchor sau
  - (u, v) tâm logo chuẩn hoá trong person bbox → binning slot
  - tid, fi → truy ngược track/frame

    python inventory/mine_jersey_logos.py --tracks data/inventory/tracks \
        --video data/real/yt/bradford_home.mp4 --teams 0,2 \
        --out data/inventory/jersey --min-h 220 --every-n 6
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
    ap.add_argument("--teams", default=None,
                    help="cluster ids của đội target, vd '0,2' (dùng team_assign.json)")
    ap.add_argument("--tids-file", default=None,
                    help="JSON list track-id target (vd bradford_strict.json) — ưu tiên hơn --teams")
    ap.add_argument("--out", required=True, type=Path)
    ap.add_argument("--weights", default="data/sam3/sam3.pt")
    ap.add_argument("--stride", type=int, default=2, help="vid_stride đã dùng khi track")
    ap.add_argument("--min-h", type=int, default=220, help="person bbox tối thiểu (px)")
    ap.add_argument("--every-n", type=int, default=6,
                    help="mỗi track chỉ mine 1/N detection đạt chuẩn")
    ap.add_argument("--conf", type=float, default=0.3)
    ap.add_argument("--quantize", type=int, default=16,
                    help="SAM3 weight quantization bits; 16 reduces VRAM use")
    ap.add_argument("--margin", type=float, default=0.06)
    a = ap.parse_args()
    crop_dir = a.out / "crops"; crop_dir.mkdir(parents=True, exist_ok=True)

    if a.tids_file:
        target_tids = {int(t) for t in json.loads(Path(a.tids_file).read_text())}
    else:
        team_ids = {int(x) for x in a.teams.split(",")}
        assign = json.loads((a.tracks / "team_assign.json").read_text())
        target_tids = {int(t) for t, c in assign.items() if c in team_ids}

    # chọn detection cần mine, nhóm theo frame để đọc video tuần tự
    per_frame: dict[int, list[dict]] = defaultdict(list)
    seen_count: dict[int, int] = defaultdict(int)
    for ln in (a.tracks / "tracks.jsonl").read_text().splitlines():
        d = json.loads(ln)
        if d["tid"] not in target_tids:
            continue
        if d["xyxy"][3] - d["xyxy"][1] < a.min_h:
            continue
        seen_count[d["tid"]] += 1
        if (seen_count[d["tid"]] - 1) % a.every_n != 0:
            continue
        per_frame[d["fi"] * a.stride].append(d)

    from ultralytics.models.sam import SAM3SemanticPredictor
    P = SAM3SemanticPredictor(overrides=dict(
        conf=a.conf, task="segment", mode="predict", model=a.weights,
        save=False, verbose=False, device="cuda", imgsz=644, quantize=a.quantize))

    cap = cv2.VideoCapture(a.video)
    meta = []
    n_crop = 0
    for fi_raw in sorted(per_frame):
        cap.set(cv2.CAP_PROP_POS_FRAMES, fi_raw)
        ok, frame = cap.read()
        if not ok:
            continue
        H, W = frame.shape[:2]
        for d in per_frame[fi_raw]:
            x0, y0, x1, y1 = (int(v) for v in d["xyxy"])
            mw, mh = int((x1 - x0) * a.margin), int((y1 - y0) * a.margin)
            cx0, cy0 = max(0, x0 - mw), max(0, y0 - mh)
            cx1, cy1 = min(W, x1 + mw), min(H, y1 + mh)
            pcrop = frame[cy0:cy1, cx0:cx1]
            if pcrop.size == 0:
                continue
            P.set_image(pcrop)
            r = P(text=["logo"])[0]
            if r.boxes is None or r.masks is None:
                continue
            masks = r.masks.data.cpu().numpy()
            for i, b in enumerate(r.boxes):
                if float(b.conf) < a.conf:
                    continue
                lx0, ly0, lx1, ly1 = (int(v) for v in b.xyxy[0].tolist())
                lx0, ly0 = max(0, lx0), max(0, ly0)
                if lx1 <= lx0 or ly1 <= ly0:
                    continue
                rgb = pcrop[ly0:ly1, lx0:lx1]
                m = (masks[i, ly0:ly1, lx0:lx1] > 0.5).astype(np.uint8) * 255
                if m.shape[:2] != rgb.shape[:2] or m.max() == 0:
                    continue
                # (u,v) tâm logo trong person crop (0..1)
                u = ((lx0 + lx1) / 2) / pcrop.shape[1]
                v = ((ly0 + ly1) / 2) / pcrop.shape[0]
                name = f"t{d['tid']:04d}_f{fi_raw:06d}_{i}"
                cv2.imwrite(str(crop_dir / f"{name}.png"), np.dstack([rgb, m]))
                meta.append({"name": name, "tid": d["tid"], "fi_raw": fi_raw,
                             "u": round(u, 4), "v": round(v, 4),
                             "wh": [lx1 - lx0, ly1 - ly0],
                             "person_h": cy1 - cy0,
                             "sam_conf": round(float(b.conf), 3)})
                n_crop += 1
    cap.release()
    (a.out / "meta.jsonl").write_text(
        "\n".join(json.dumps(m) for m in meta), encoding="utf-8")
    print(f"[mine] {len(per_frame)} frames, {n_crop} logo crops "
          f"(from {len(target_tids)} target tracks) -> {a.out}")


if __name__ == "__main__":
    main()
