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
import re
from collections import defaultdict
from pathlib import Path

NAME_ZONE_V = 0.24        # vùng in tên cầu thủ (lưng trên)
MIN_READS_CONFIRM = 4     # số lần đọc tối thiểu để CONFIRMED
MIN_TARGET_READS_CONFIRM = 4
# A full-frame OCR box may overlap two player boxes during contact shots, so
# target support is not exclusive.  Keep a majority requirement rather than a
# near-perfect ratio; the independent kit-sheet/review gate still protects the
# final inventory label.
MIN_TARGET_RATIO_CONFIRM = 0.60


def slot_name(u: float, v: float) -> str:
    if v < 0.16:  return "collar"
    if v < 0.40:  return "chest" if 0.25 <= u <= 0.75 else "sleeve"
    if v < 0.55:  return "abdomen"
    if v < 0.72:  return "shorts"
    return "legs"


def _is_suspect_player_name(brand: str, slot: str, texts: list[str], vs: list[float]) -> bool:
    """Reject a player surname that was fuzzy-matched to an auxiliary brand word."""
    name_zone = all(x < NAME_ZONE_V for x in vs) and slot in ("chest", "collar")
    single_token = bool(texts) and all(len(t.split()) <= 1 for t in texts)
    brand_words = set(re.findall(r"[a-z]+", brand.lower()))
    has_canonical_word = any(
        token in brand_words
        for text in texts
        for token in re.findall(r"[a-z]+", text.lower())
    )
    return single_token and (name_zone or not has_canonical_word)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--tracks", required=True, type=Path)
    ap.add_argument("--dets", required=True)
    ap.add_argument("--out", required=True, type=Path)
    ap.add_argument("--team-file", default=None,
                    help="JSON list tid đội target (mặc định: bradford_strict.json cạnh tracks)")
    ap.add_argument("--min-target-reads", type=int, default=MIN_TARGET_READS_CONFIRM,
                    help="minimum OCR reads that overlap a target-team track")
    ap.add_argument("--min-target-ratio", type=float, default=MIN_TARGET_RATIO_CONFIRM,
                    help="minimum target_reads / all_reads for a confirmed anchor")
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
        suspect_name = _is_suspect_player_name(brand, slot, v["texts"], v["vs"])
        target_ratio = v["target_reads"] / max(v["reads"], 1)
        if (v["reads"] >= MIN_READS_CONFIRM
                and v["target_reads"] >= a.min_target_reads
                and target_ratio >= a.min_target_ratio
                and not suspect_name):
            status = "CONFIRMED"
        elif suspect_name:
            status = "SUSPECT_PLAYER_NAME"
        elif v["reads"] >= MIN_READS_CONFIRM and target_ratio < a.min_target_ratio:
            status = "WEAK_NON_TARGET"
        else:
            status = "WEAK"
        inventory.append({"brand": brand, "slot": slot, "status": status,
                          "reads": v["reads"], "target_reads": v["target_reads"],
                          "target_ratio": round(target_ratio, 2),
                          "n_tracks": len(v["tids"]),
                          "sample_texts": v["texts"][:4]})
    a.out.write_text(json.dumps(inventory, ensure_ascii=False, indent=1),
                     encoding="utf-8")
    print(f"{'brand':10s} {'slot':8s} {'status':22s} reads(target) ratio tracks")
    for i in inventory:
        print(f"{i['brand']:10s} {i['slot']:8s} {i['status']:22s} "
              f"{i['reads']}({i['target_reads']}) {i['target_ratio']:.2f}  {i['n_tracks']}")
    print(f"\n[inventory] -> {a.out}")


if __name__ == "__main__":
    main()
