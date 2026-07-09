"""Bước 1 (WHERE) — dataset 1 lớp 'logo trên người' từ pseudo-label SAM3.

Gộp nhiều lần mine (nhiều video), mỗi (tid, frame) = 1 ảnh person-crop, box =
mọi logo SAM3. Lọc: sam_conf, size tối thiểu, và LOẠI đồ hoạ broadcast theo
vùng màn hình cố định (scorebug, watermark) — toạ độ frame = origin person + box.

    python inventory/build_where_ds.py --out data/inventory/where_ds \
      --src data/inventory/jersey,data/inventory/tracks,data/real/yt/bradford_home.mp4,train \
      --src data/inventory/jersey26,data/inventory/tracks26,data/real/yt/bradford_sthelens26.mp4,val
"""
from __future__ import annotations

import argparse
import json
from collections import defaultdict
from pathlib import Path

import cv2

# vùng đồ hoạ cố định (normalized frame): scorebug trái-dưới, watermark phải-trên
EXCLUDE = [(0.0, 0.80, 0.40, 1.0), (0.72, 0.0, 1.0, 0.15)]
MIN_PX = 12
MIN_CONF = 0.40


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--src", action="append", required=True,
                    help="jerseyDir,tracksDir,video,split")
    ap.add_argument("--out", required=True, type=Path)
    a = ap.parse_args()
    import shutil
    if a.out.exists():
        shutil.rmtree(a.out)
    for sp in ("train", "val"):
        (a.out / f"images/{sp}").mkdir(parents=True)
        (a.out / f"labels/{sp}").mkdir(parents=True)

    tot = {"train": 0, "val": 0}
    for src in a.src:
        jd, td, video, split = src.split(",")
        jd, td = Path(jd), Path(td)
        meta = [json.loads(l) for l in (jd / "meta.jsonl").read_text().splitlines()]
        tr = defaultdict(dict)
        for ln in (td / "tracks.jsonl").read_text().splitlines():
            d = json.loads(ln)
            tr[d["tid"]][d["fi"] * 2] = d["xyxy"]
        by_img = defaultdict(list)
        for m in meta:
            if m["sam_conf"] < MIN_CONF or max(m["wh"]) < MIN_PX:
                continue
            by_img[(m["tid"], m["fi_raw"])].append(m)
        cap = cv2.VideoCapture(video)
        W = cap.get(cv2.CAP_PROP_FRAME_WIDTH); H = cap.get(cv2.CAP_PROP_FRAME_HEIGHT)
        tag = jd.name
        for (tid, fr), items in sorted(by_img.items()):
            if fr not in tr[tid]:
                continue
            x0, y0, x1, y1 = tr[tid][fr]
            mw, mh = (x1 - x0) * 0.06, (y1 - y0) * 0.06
            cx0, cy0 = int(max(0, x0 - mw)), int(max(0, y0 - mh))
            cx1, cy1 = int(min(W, x1 + mw)), int(min(H, y1 + mh))
            cap.set(cv2.CAP_PROP_POS_FRAMES, fr)
            ok, frame = cap.read()
            if not ok:
                continue
            crop = frame[cy0:cy1, cx0:cx1]
            if crop.size == 0:
                continue
            ch, cw = crop.shape[:2]
            lines = []
            for m in items:
                # toạ độ frame của tâm logo → filter đồ hoạ
                fx = (cx0 + m["u"] * cw) / W
                fy = (cy0 + m["v"] * ch) / H
                if any(ex0 <= fx <= ex1 and ey0 <= fy <= ey1
                       for ex0, ey0, ex1, ey1 in EXCLUDE):
                    continue
                lines.append(f"0 {m['u']:.5f} {m['v']:.5f} "
                             f"{m['wh'][0]/cw:.5f} {m['wh'][1]/ch:.5f}")
            if not lines:
                continue
            stem = f"{tag}_t{tid}_f{fr}"
            cv2.imwrite(str(a.out / f"images/{split}/{stem}.jpg"), crop)
            (a.out / f"labels/{split}/{stem}.txt").write_text("\n".join(lines))
            tot[split] += 1
        cap.release()
        print(f"[{tag}] -> {split}: cumulative {tot[split]} imgs")
    (a.out / "data.yaml").write_text(
        f"path: {a.out.resolve().as_posix()}\ntrain: images/train\nval: images/val\n"
        f"names:\n  0: logo\n")
    print(f"[where_ds] train={tot['train']} val={tot['val']} -> {a.out}")


if __name__ == "__main__":
    main()
