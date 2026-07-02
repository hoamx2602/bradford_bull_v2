"""Stage 1b eval — proposal recall của proposer class-agnostic trên gold jersey GT.

Protocol GIỐNG Stage 1a để so sánh công bằng:
  person crop (cache stage0, margin 5%) → proposer → map về frame coords
  → global NMS → recall class-agnostic trên GT trong person box, IoU≥0.5.

Gate GO (master plan): recall ≥ 0.85 với ≤10 proposal/person.

Chạy:
  conda run -n bradford_bulls python auto_label/stage1b_eval.py \
      --model runs/stage1b_proposer/weights/best.pt \
      --frames data/real/auto/images --gold data/real/auto/labels \
      --persons data/stage0/person_boxes.json --out data/stage1b_eval
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from pathlib import Path

import cv2
import numpy as np

sys.path.insert(0, str(Path(__file__).parent))
from stage0_error_analysis import load_gt, center_in_any, iou  # noqa: E402

IMG_EXT = {".jpg", ".jpeg", ".png"}
MIN_PERSON_W = 40
CROP_MARGIN = 0.05
THRESHOLDS = [0.05, 0.10, 0.15, 0.20, 0.25, 0.30, 0.40, 0.50]
SIZE_BINS = [(0, 30, "tiny <30px"), (30, 60, "small 30-60px"),
             (60, 120, "medium 60-120px"), (120, 1e9, "large >120px")]


def nms(dets: list[dict], thr: float = 0.45) -> list[dict]:
    dets = sorted(dets, key=lambda d: -d["score"])
    keep = []
    for d in dets:
        if all(iou(d["xyxy"], k["xyxy"]) < thr for k in keep):
            keep.append(d)
    return keep


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--model",   required=True, type=Path)
    ap.add_argument("--frames",  required=True, type=Path)
    ap.add_argument("--gold",    required=True, type=Path)
    ap.add_argument("--persons", required=True, type=Path)
    ap.add_argument("--out",     required=True, type=Path)
    ap.add_argument("--viz", type=int, default=4)
    a = ap.parse_args()
    (a.out / "labels").mkdir(parents=True, exist_ok=True)

    from ultralytics import YOLO
    model = YOLO(str(a.model))
    persons = json.loads(a.persons.read_text())
    frames = sorted(p for p in a.frames.iterdir() if p.suffix.lower() in IMG_EXT)

    n_crops = 0
    all_dets: dict[str, list[dict]] = {}
    for fp in frames:
        frame = cv2.imread(str(fp)); H, W = frame.shape[:2]
        dets: list[dict] = []
        pboxes = [b for b in persons.get(fp.stem, [])
                  if (b[2]-b[0]) >= MIN_PERSON_W]
        for pb in pboxes:
            mw, mh = (pb[2]-pb[0])*CROP_MARGIN, (pb[3]-pb[1])*CROP_MARGIN
            cx0, cy0 = int(max(0, pb[0]-mw)), int(max(0, pb[1]-mh))
            cx1, cy1 = int(min(W, pb[2]+mw)), int(min(H, pb[3]+mh))
            crop = frame[cy0:cy1, cx0:cx1]
            if crop.size == 0:
                continue
            res = model.predict(crop, conf=0.05, iou=0.5, verbose=False)[0]
            for b, s in zip(res.boxes.xyxy.cpu().numpy(),
                            res.boxes.conf.cpu().numpy()):
                dets.append({"xyxy": [float(b[0])+cx0, float(b[1])+cy0,
                                      float(b[2])+cx0, float(b[3])+cy0],
                             "score": float(s)})
            n_crops += 1
        dets = nms(dets)
        all_dets[fp.stem] = dets
        lines = [f"0 {(d['xyxy'][0]+d['xyxy'][2])/2/W:.6f} "
                 f"{(d['xyxy'][1]+d['xyxy'][3])/2/H:.6f} "
                 f"{(d['xyxy'][2]-d['xyxy'][0])/W:.6f} "
                 f"{(d['xyxy'][3]-d['xyxy'][1])/H:.6f} {d['score']:.4f}"
                 for d in dets]
        (a.out / "labels" / f"{fp.stem}.txt").write_text("\n".join(lines))

    # ── Eval ────────────────────────────────────────────────────────────────
    report = {"model": str(a.model), "n_crops": n_crops, "sweep": []}
    print(f"\n{'thr':>5} {'R_jersey':>9} {'prop/person':>12} {'#det':>7}")
    for thr in THRESHOLDS:
        n_gt = n_hit = n_det = 0
        bin_tot: dict = defaultdict(int); bin_hit: dict = defaultdict(int)
        for fp in frames:
            img = cv2.imread(str(fp)); H, W = img.shape[:2]
            pb = persons.get(fp.stem, [])
            gts = [g for g in load_gt(a.gold / f"{fp.stem}.txt", W, H)
                   if center_in_any(g, pb)]
            dets = [d["xyxy"] for d in all_dets[fp.stem] if d["score"] >= thr]
            n_det += len(dets); n_gt += len(gts)
            for g in gts:
                hit = any(iou(d, g) >= 0.5 for d in dets)
                longest = max(g[2]-g[0], g[3]-g[1])
                for lo, hi, name in SIZE_BINS:
                    if lo <= longest < hi:
                        bin_tot[name] += 1; bin_hit[name] += hit
                        break
                n_hit += hit
        rec = n_hit / max(n_gt, 1)
        ppp = n_det / max(n_crops, 1)
        print(f"{thr:>5} {rec:>9.3f} {ppp:>12.1f} {n_det:>7}")
        report["sweep"].append({
            "thr": thr, "recall_jersey": rec, "props_per_person": ppp,
            "n_det": n_det,
            "recall_by_bin": {n: bin_hit[n]/max(bin_tot[n], 1) for n in bin_tot}})

    b0 = report["sweep"][0]
    print(f"\nRecall theo size bin @ thr={THRESHOLDS[0]}:")
    for lo, hi, name in SIZE_BINS:
        if name in b0["recall_by_bin"]:
            print(f"  {name:<18} R={b0['recall_by_bin'][name]:.3f}")

    (a.out / "stage1b_report.json").write_text(json.dumps(report, indent=2))
    print(f"\n[json] {a.out / 'stage1b_report.json'}")

    if a.viz:
        viz_dir = a.out / "viz"; viz_dir.mkdir(exist_ok=True)
        for stem in list(all_dets)[:a.viz]:
            fp = a.frames / f"{stem}.jpg"
            img = cv2.imread(str(fp)); H, W = img.shape[:2]
            pb = persons.get(stem, [])
            gts = [g for g in load_gt(a.gold / f"{stem}.txt", W, H)
                   if center_in_any(g, pb)]
            for d in all_dets[stem]:
                if d["score"] >= 0.10:
                    x = [int(v) for v in d["xyxy"]]
                    cv2.rectangle(img, (x[0], x[1]), (x[2], x[3]), (0, 0, 255), 1)
            for g in gts:
                cv2.rectangle(img, (int(g[0]), int(g[1])),
                              (int(g[2]), int(g[3])), (0, 220, 255), 2)
            cv2.imwrite(str(viz_dir / f"{stem}.jpg"), img)
        print(f"[viz] → {viz_dir} (đỏ=proposal@0.10, vàng=jersey GT)")


if __name__ == "__main__":
    main()
