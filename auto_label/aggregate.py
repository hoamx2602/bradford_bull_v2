"""Phase 3 — Aggregation engine: detections per-frame → metric exposure per brand.

Vị trí trong pipeline (xem `../Production-System-Design.MD` §4, `../docs/03-pipeline.md`):
  Tầng1 (localizer) + Tầng2 (recognizer) cho ra detection mỗi frame
    → [engine này] temporal smoothing + de-dup + tổng hợp
    → exposure-seconds, visibility%, segments, EMV  (khớp `eval_exposure.py`)

Đây là nơi giá trị sản phẩm + nhiều edge case nằm — KHÔNG phụ thuộc model, thuần
logic, test được ngay. Xử lý: gộp nhiều instance/khung (coverage), bắc cầu flicker,
bỏ ghost 1-khung, image-clarity weighting, loại scene (replay/adbreak).

Input — detections JSONL (1 detection/dòng), tọa độ/area đã tính sẵn ở upstream:
    {"frame": 120, "brand": "aon", "conf": 0.83, "area_pct": 1.4,
     "scene": "play", "clarity": 0.9}
  - area_pct = diện tích box / diện tích frame × 100 (1 instance).
  - scene/clarity tùy chọn. Nhiều detection cùng (frame,brand) → coverage cộng dồn.

Chạy:
    python auto_label/aggregate.py --dets dets.jsonl --fps 25 --sample-fps 2.5 \
        --out result.json --bridge 0.8 --min-seg 0.4 --conf 0.3
    python auto_label/aggregate.py --selftest
Rồi: python auto_label/eval_exposure.py --pred result.json --gt gold.json
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path


# --------------------------------------------------------------------------- #
# Gộp interval (temporal smoothing core)
# --------------------------------------------------------------------------- #

def merge_intervals(times: list[float], dt: float, bridge: float):
    """Mỗi sample present tại t → [t, t+dt). Gộp các đoạn cách nhau ≤ bridge.
    Trả list (start, end). `times` không cần sort."""
    if not times:
        return []
    segs = [[t, t + dt] for t in sorted(times)]
    out = [segs[0][:]]
    for s, e in segs[1:]:
        if s - out[-1][1] <= bridge + 1e-9:        # bắc cầu flicker/khoảng ngắn
            out[-1][1] = max(out[-1][1], e)
        else:
            out.append([s, e])
    return [(round(s, 4), round(e, 4)) for s, e in out]


# --------------------------------------------------------------------------- #
# Aggregate
# --------------------------------------------------------------------------- #

def aggregate(dets: list[dict], fps: float, sample_fps: float,
              conf_thr: float = 0.3, bridge: float = 0.8, min_seg: float = 0.4,
              exclude_scenes: set[str] | None = None,
              rate_per_sec: float = 50.0, video: str = "?") -> dict:
    dt = 1.0 / sample_fps
    exclude_scenes = exclude_scenes or set()

    # gom theo brand → theo frame: coverage (cộng instance, clamp 100), conf max,
    # clarity trung bình.
    per_brand: dict[str, dict[int, dict]] = {}
    for d in dets:
        if float(d.get("conf", 1.0)) < conf_thr:
            continue
        if str(d.get("scene", "play")).lower() in exclude_scenes:
            continue
        brand = d["brand"]; fr = int(d["frame"])
        slot = per_brand.setdefault(brand, {}).setdefault(
            fr, {"cov": 0.0, "conf": 0.0, "clar": [], "n": 0})
        slot["cov"] = min(slot["cov"] + float(d.get("area_pct", 0.0)), 100.0)
        slot["conf"] = max(slot["conf"], float(d.get("conf", 1.0)))
        slot["clar"].append(float(d.get("clarity", 1.0)))
        slot["n"] += 1

    brands_out: dict[str, dict] = {}
    for brand, frames in per_brand.items():
        # thời điểm present + coverage/clarity tại mỗi sample
        present = {fr: (s["cov"], sum(s["clar"]) / len(s["clar"]))
                   for fr, s in frames.items()}
        times = [fr / fps for fr in present]
        segs = merge_intervals(times, dt, bridge)
        segs = [(s, e) for s, e in segs if (e - s) >= min_seg - 1e-9]  # bỏ ghost
        if not segs:
            continue

        # các sample rơi vào segment được giữ
        kept = []
        for fr, (cov, clar) in present.items():
            t = fr / fps
            if any(s - 1e-9 <= t < e for s, e in segs):
                kept.append((cov, clar))
        if not kept:
            continue
        covs = [c for c, _ in kept]; clars = [cl for _, cl in kept]
        exposure_sec = round(sum(e - s for s, e in segs), 3)
        visibility_pct = round(sum(covs) / len(covs), 3)             # mean coverage
        clarity_mean = sum(clars) / len(clars)
        quality_exposure_sec = round(exposure_sec * clarity_mean, 3)  # clarity-weighted
        peak_visibility = round(max(covs), 3)
        emv = round(quality_exposure_sec * (visibility_pct / 100.0) * rate_per_sec, 2)

        brands_out[brand] = {
            "exposure_sec": exposure_sec,
            "quality_exposure_sec": quality_exposure_sec,
            "visibility_pct": visibility_pct,
            "peak_visibility_pct": peak_visibility,
            "n_segments": len(segs),
            "segments": [list(s) for s in segs],
            "emv": emv,
        }

    return {"video": video, "fps": fps, "sample_fps": sample_fps,
            "params": {"conf": conf_thr, "bridge": bridge, "min_seg": min_seg,
                       "rate_per_sec": rate_per_sec,
                       "exclude_scenes": sorted(exclude_scenes)},
            "brands": brands_out}


# --------------------------------------------------------------------------- #
# I/O + report
# --------------------------------------------------------------------------- #

def load_dets(p: Path) -> list[dict]:
    return [json.loads(l) for l in p.read_text().splitlines() if l.strip()]


def report(res: dict) -> None:
    print(f"\n  [Aggregate] video={res['video']}  fps={res['fps']} "
          f"sample_fps={res['sample_fps']}  brands={len(res['brands'])}")
    print(f"  params: {res['params']}")
    print("  " + "-" * 66)
    print(f"  {'brand':<16}{'expo_s':>8}{'qual_s':>8}{'vis%':>7}"
          f"{'peak%':>7}{'#seg':>6}{'EMV':>9}")
    for b, m in sorted(res["brands"].items()):
        print(f"  {b:<16}{m['exposure_sec']:>8.2f}{m['quality_exposure_sec']:>8.2f}"
              f"{m['visibility_pct']:>7.2f}{m['peak_visibility_pct']:>7.2f}"
              f"{m['n_segments']:>6}{m['emv']:>9.2f}")
    print()


def _selftest() -> None:
    # bridge: gộp đoạn cách ngắn
    assert merge_intervals([0.0, 0.4], 0.4, 0.8) == [(0.0, 0.8)], "bridge sai"
    # không bridge khi gap > bridge
    assert merge_intervals([0.0, 5.0], 0.4, 0.8) == [(0.0, 0.4), (5.0, 5.4)]
    fps, sfps = 25.0, 2.5            # sample mỗi 10 frame → dt=0.4s
    dets = []
    # aon: present frame 0,10,20,30 (liên tục) → 1 segment ~1.6s
    for fr in (0, 10, 20, 30):
        dets.append({"frame": fr, "brand": "aon", "conf": 0.9,
                     "area_pct": 2.0, "clarity": 1.0})
    # ghost: toyota chỉ 1 sample → < min_seg 0.4? dt=0.4 == min → giữ; làm min 0.5 để bỏ
    dets.append({"frame": 100, "brand": "toyota", "conf": 0.9, "area_pct": 1.0})
    # low conf bị loại
    dets.append({"frame": 0, "brand": "klg", "conf": 0.1, "area_pct": 5.0})
    # replay scene bị loại
    dets.append({"frame": 0, "brand": "mcp", "conf": 0.9, "area_pct": 3.0,
                 "scene": "replay"})
    r = aggregate(dets, fps, sfps, conf_thr=0.3, bridge=0.8, min_seg=0.5,
                  exclude_scenes={"replay"})
    b = r["brands"]
    assert "aon" in b and abs(b["aon"]["exposure_sec"] - 1.6) < 1e-6, b["aon"]
    assert abs(b["aon"]["visibility_pct"] - 2.0) < 1e-6
    assert "toyota" not in b, "ghost 1-sample phải bị bỏ (min_seg>dt)"
    assert "klg" not in b, "low-conf phải bị loại"
    assert "mcp" not in b, "replay phải bị loại"
    print("  aggregate selftest: OK ✅")


def main() -> None:
    ap = argparse.ArgumentParser(description="Phase 3 — aggregation engine")
    ap.add_argument("--dets", type=Path, help="detections JSONL")
    ap.add_argument("--fps", type=float, help="fps gốc của video")
    ap.add_argument("--sample-fps", dest="sample_fps", type=float,
                    help="số frame được sample/giây (fps/every)")
    ap.add_argument("--out", type=Path, default=None)
    ap.add_argument("--conf", type=float, default=0.3)
    ap.add_argument("--bridge", type=float, default=0.8, help="bắc cầu gap ≤ (s)")
    ap.add_argument("--min-seg", dest="min_seg", type=float, default=0.4,
                    help="bỏ segment ngắn hơn (s) — chống ghost")
    ap.add_argument("--rate", type=float, default=50.0, help="EMV $/giây (placeholder)")
    ap.add_argument("--exclude-scenes", dest="exclude_scenes", default="",
                    help="scene loại trừ, phẩy ngăn cách (vd replay,adbreak)")
    ap.add_argument("--video", default="?")
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args()

    if a.selftest:
        _selftest(); return
    if not (a.dets and a.fps and a.sample_fps):
        ap.error("cần --dets --fps --sample-fps (hoặc --selftest)")

    excl = {s.strip().lower() for s in a.exclude_scenes.split(",") if s.strip()}
    res = aggregate(load_dets(a.dets), a.fps, a.sample_fps, conf_thr=a.conf,
                    bridge=a.bridge, min_seg=a.min_seg, exclude_scenes=excl,
                    rate_per_sec=a.rate, video=a.video)
    report(res)
    if a.out:
        a.out.parent.mkdir(parents=True, exist_ok=True)
        a.out.write_text(json.dumps(res, indent=2, ensure_ascii=False))
        print(f"  [json] {a.out}")


if __name__ == "__main__":
    main()
