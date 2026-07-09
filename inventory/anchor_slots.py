"""M1e(v2) — Anchor slot bằng OCR full-frame chiếu vào bbox cầu thủ (docs/12).

Nguyên lý inventory: anchor đến từ BẤT KỲ khoảnh khắc nét nào trong video —
ở đây là các lần OCR full-frame 1080p đọc được brand (exposure detections),
chiếu vào person bbox đang track → (u,v) → slot → consensus per (brand, slot).

Chống nhầm tên cầu thủ: vùng tên áo (lưng trên, v<0.24) — brand có token trùng
họ người (surname-like, 1 token đơn) bị đánh UNCERTAIN trừ khi khớp ≥2 token.

    python inventory/anchor_slots.py --tracks data/inventory/tracks \
        --dets data/exposure/detections.jsonl \
        --out data/inventory/bradford_inventory.json
"""
from __future__ import annotations

import argparse
import json
from collections import defaultdict
from pathlib import Path

NAME_ZONE_V = 0.24        # vùng in tên cầu thủ (lưng trên)
MIN_READS_CONFIRM = 4     # số lần đọc tối thiểu để CONFIRMED


def slot_name(u: float, v: float) -> str:
    if v < 0.16:  return "collar"
    if v < 0.40:  return "chest" if 0.25 <= u <= 0.75 else "sleeve"
    if v < 0.55:  return "abdomen"
    if v < 0.72:  return "shorts"
    return "legs"


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--tracks", required=True, type=Path)
    ap.add_argument("--dets", required=True)
    ap.add_argument("--out", required=True, type=Path)
    ap.add_argument("--team-file", default=None,
                    help="JSON list tid đội target (mặc định: bradford_strict.json cạnh tracks)")
    a = ap.parse_args()

    dets = [json.loads(l) for l in open(a.dets, encoding="utf-8")]
    by_frame = defaultdict(list)
    for ln in (a.tracks / "tracks.jsonl").read_text().splitlines():
        d = json.loads(ln)
        by_frame[d["fi"] * 2].append(d)
    tf = a.team_file or (a.tracks / "bradford_strict.json")
    target = {int(t) for t in json.loads(Path(tf).read_text())}

    agg = defaultdict(lambda: {"reads": 0, "target_reads": 0, "texts": [],
                               "tids": set(), "vs": []})
    for d in dets:
        fr = d["frame"]
        bx = (d["box"][0] + d["box"][2]) / 2
        by = (d["box"][1] + d["box"][3]) / 2
        for p in by_frame.get(fr, []):
            x0, y0, x1, y1 = p["xyxy"]
            if not (x0 <= bx <= x1 and y0 <= by <= y1):
                continue
            u, v = (bx - x0) / (x1 - x0), (by - y0) / (y1 - y0)
            k = (d["brand"], slot_name(u, v))
            agg[k]["reads"] += 1
            agg[k]["target_reads"] += int(p["tid"] in target)
            agg[k]["texts"].append(d["text"][:20])
            agg[k]["tids"].add(p["tid"])
            agg[k]["vs"].append(round(v, 2))

    inventory = []
    for (brand, slot), v in sorted(agg.items(), key=lambda x: -x[1]["reads"]):
        # nghi tên cầu thủ: 1-token đọc được nằm vùng tên áo
        name_zone = all(x < NAME_ZONE_V for x in v["vs"]) and slot in ("chest", "collar")
        single_token = all(len(t.split()) <= 1 for t in v["texts"])
        suspect_name = name_zone and single_token
        if v["reads"] >= MIN_READS_CONFIRM and not suspect_name:
            status = "CONFIRMED"
        elif suspect_name:
            status = "SUSPECT_PLAYER_NAME"
        else:
            status = "WEAK"
        inventory.append({"brand": brand, "slot": slot, "status": status,
                          "reads": v["reads"], "target_reads": v["target_reads"],
                          "n_tracks": len(v["tids"]),
                          "sample_texts": v["texts"][:4]})
    a.out.write_text(json.dumps(inventory, ensure_ascii=False, indent=1),
                     encoding="utf-8")
    print(f"{'brand':10s} {'slot':8s} {'status':22s} reads(target) tracks")
    for i in inventory:
        print(f"{i['brand']:10s} {i['slot']:8s} {i['status']:22s} "
              f"{i['reads']}({i['target_reads']})        {i['n_tracks']}")
    print(f"\n[inventory] -> {a.out}")


if __name__ == "__main__":
    main()
