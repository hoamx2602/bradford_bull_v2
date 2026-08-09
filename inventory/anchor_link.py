"""Per-cluster anchoring — LIÊN KẾT OCR full-frame về đúng CỤM (docs/12, fix coupling).

Vấn đề audit 2026-07-18 phơi ra: OCR per-SLOT (`anchor_slots.py`) dán cùng brand lên
MỌI cụm cùng slot → CONFIRMED ảo (C28 "CUSTOMS"→klg). Còn OCR per-crop
(`anchor_clusters.py`) thì câm vì crop 20-50px không đọc nổi.

Lời giải: OCR đọc trên FULL-FRAME (chữ đủ to) NHƯNG gắn mỗi read về đúng cụm qua
liên kết hình học **(track-id, vị trí (u,v) trên thân)** — vị trí logo trên cơ thể ổn
định suốt track nên không cần trùng frame (chỉ 15/150 read trùng frame mined crop).

  read (frame, box) ──project vào person bbox──► (tid, u_read, v_read, brand)
        │  match crop cùng tid, (u,v) gần nhất (< tol)
        ▼
  crop ──(clusters.members)──► cid   ⇒  cụm đó (và CHỈ cụm đó) nhận vote brand

Chỉ cụm THẬT SỰ chứa crop được anchor mới có nhãn OCR; cụm vải trơn → không → UNKNOWN.

    python inventory/anchor_link.py --dets data/exposure26/detections.jsonl \
        --tracks data/inventory/tracks26 --jersey data/inventory/jersey26 \
        --clusters data/inventory/clusters26/clusters.json \
        --out data/inventory/cluster_ocr26.json
    python inventory/anchor_link.py --selftest
"""
from __future__ import annotations

import argparse
import json
import re
from collections import Counter, defaultdict
from pathlib import Path

MARGIN = 0.06            # margin person-crop khi mine (mine_jersey_logos.py) → đổi toạ độ
UV_TOL = 0.15           # bán kính khớp (u,v) read↔crop (bbox-relative)
NAME_ZONE_V = 0.24      # vùng tên áo (lưng trên) — chống nhầm họ cầu thủ


def _crop_uv_to_bbox(u_crop: float, v_crop: float) -> tuple[float, float]:
    """(u,v) trong person-crop (có margin MARGIN) → (u,v) trong person BBOX (không margin).

    pcrop rộng (1+2m)×bbox, gốc lệch -m·bbox ⇒ u_bbox = (1+2m)·u_crop − m.
    """
    k = 1 + 2 * MARGIN
    return k * u_crop - MARGIN, k * v_crop - MARGIN


def _suspect_name(brand: str, text: str, u: float, v: float) -> bool:
    """Read đơn-token ở vùng tên áo, token không thuộc brand chính → nghi họ cầu thủ."""
    if v >= NAME_ZONE_V or not (0.25 <= u <= 0.75):
        return False
    toks = re.findall(r"[a-z]+", text.lower())
    if len(toks) != 1:
        return False
    brand_words = set(re.findall(r"[a-z]+", brand.lower()))
    return toks[0] not in brand_words


def body_filter_dets(dets: list[dict], video: str, body_thr: float = 0.5) -> list[dict]:
    """Giữ read có box nằm TRÊN THÂN cầu thủ (foreground person-mask) ≥ body_thr.

    Gỡ NHIỄM BIỂN: biển quảng cáo (kể cả mcp/klg cũng là nhà QC sân) nằm ở nền/rìa
    sân → box read trên background → body-frac thấp → loại. Đo thực 2026-07: mcp
    23/129, klg 17/71 on-body (phần lớn là biển); mna_cladding 0/11; acs 6/6 jersey.
    Chạy trên FULL-FRAME (box chính xác), không phải crop tái tạo (đã chứng minh nhiễu).
    """
    import cv2
    import numpy as np
    from collections import defaultdict
    from ultralytics import YOLO

    by_frame = defaultdict(list)
    for d in dets:
        by_frame[d["frame"]].append(d)
    seg = YOLO("yolo11n-seg.pt")
    cap = cv2.VideoCapture(video)
    kept = []
    for fr in sorted(by_frame):
        cap.set(cv2.CAP_PROP_POS_FRAMES, fr)
        ok, frame = cap.read()
        if not ok:
            continue
        H, W = frame.shape[:2]
        r = seg(frame, classes=[0], verbose=False)[0]
        m = np.zeros((H, W), np.uint8)
        if r.masks is not None:
            for poly in r.masks.xy:
                if len(poly) >= 3:
                    cv2.fillPoly(m, [poly.astype(np.int32)], 1)
        for d in by_frame[fr]:
            x0, y0, x1, y1 = (int(v) for v in d["box"])
            x0, y0 = max(0, x0), max(0, y0)
            x1, y1 = min(W, x1), min(H, y1)
            if x1 <= x0 or y1 <= y0:
                continue
            if float(m[y0:y1, x0:x1].mean()) >= body_thr:
                kept.append(d)
    cap.release()
    print(f"[body-filter] {len(kept)}/{len(dets)} read on-body (thr={body_thr}) — bỏ biển")
    return kept


def project_reads(dets: list[dict], tracks_dir: Path, stride: int = 2):
    """Mỗi det → (tid, u_bbox, v_bbox, brand, text) nếu tâm rơi vào một person bbox."""
    by_frame: dict[int, list] = defaultdict(list)
    for ln in (tracks_dir / "tracks.jsonl").read_text().splitlines():
        d = json.loads(ln)
        by_frame[d["fi"] * stride].append(d)
    reads = []
    for d in dets:
        bx = (d["box"][0] + d["box"][2]) / 2
        by = (d["box"][1] + d["box"][3]) / 2
        for p in by_frame.get(d["frame"], []):
            x0, y0, x1, y1 = p["xyxy"]
            if x0 <= bx <= x1 and y0 <= by <= y1:
                u, v = (bx - x0) / (x1 - x0), (by - y0) / (y1 - y0)
                reads.append((p["tid"], u, v, d["brand"], d.get("text", ""),
                              d["frame"], float(d.get("ocr_conf", 0.0))))
                break
    return reads


def link_to_clusters(reads, jersey_meta: dict, clusters: list[dict],
                     uv_tol: float = UV_TOL,
                     frame_window: int | None = None) -> dict[int, Counter]:
    """Gắn mỗi read về cụm của crop cùng tid gần nhất (u,v). → {cid: Counter(brand)}.

    frame_window: nếu đặt, CHỈ khớp crop có |fi_raw − frame_read| ≤ window. Chống
    mislink: read on-body ở frame F khớp nhầm crop BIỂN cùng track ở frame F' khi cầu
    thủ đã dịch chuyển (bug C261). Vị trí logo trên thân ổn định nên crop đúng ở gần frame.
    """
    name2cid = {name: c["cid"] for c in clusters for name in c["members"]}
    crops_by_tid: dict[int, list] = defaultdict(list)
    for name, m in jersey_meta.items():
        if name not in name2cid:
            continue
        ub, vb = _crop_uv_to_bbox(m["u"], m["v"])
        crops_by_tid[m["tid"]].append((name, ub, vb, m["fi_raw"]))

    cluster_votes: dict[int, Counter] = defaultdict(Counter)
    links: dict[int, list] = defaultdict(list)   # cid -> [{crop, brand, dframe, uv_dist, ocr_conf}]
    n_linked = 0
    for tid, u, v, brand, text, frame, ocr_conf in reads:
        if _suspect_name(brand, text, u, v):
            continue
        best, bestd, bestcf = None, uv_tol, None
        for name, ub, vb, cf in crops_by_tid.get(tid, []):
            if frame_window is not None and abs(cf - frame) > frame_window:
                continue
            d = ((ub - u) ** 2 + (vb - v) ** 2) ** 0.5
            if d < bestd:
                bestd, best, bestcf = d, name, cf
        if best is not None:
            cid = name2cid[best]
            cluster_votes[cid][brand] += 1
            links[cid].append({"crop": best, "brand": brand,
                               "dframe": abs(bestcf - frame), "uv_dist": round(bestd, 3),
                               "ocr_conf": round(ocr_conf, 2)})
            n_linked += 1
    cluster_votes["_stats"] = {"reads": len(reads), "linked": n_linked}  # type: ignore
    return cluster_votes, dict(links)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dets")
    ap.add_argument("--tracks", type=Path)
    ap.add_argument("--jersey", type=Path)
    ap.add_argument("--clusters", type=Path)
    ap.add_argument("--out", type=Path)
    ap.add_argument("--stride", type=int, default=2)
    ap.add_argument("--uv-tol", type=float, default=UV_TOL)
    ap.add_argument("--video", default=None,
                    help="video nguồn → lọc read theo body-mask (gỡ nhiễm biển)")
    ap.add_argument("--body-thr", type=float, default=0.5)
    ap.add_argument("--body-cache", default=None,
                    help="lưu/đọc read đã lọc biển (khỏi seg lại mỗi lần)")
    ap.add_argument("--frame-window", type=int, default=None,
                    help="chỉ khớp crop có |fi_raw−frame_read|≤N (chống mislink biển cùng track)")
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args()
    if a.selftest:
        selftest()
        return
    if not (a.dets and a.tracks and a.jersey and a.clusters and a.out):
        ap.error("cần --dets --tracks --jersey --clusters --out (hoặc --selftest)")

    cache = Path(a.body_cache) if a.body_cache else None
    if cache and cache.exists():
        dets = json.loads(cache.read_text(encoding="utf-8"))
        print(f"[body-filter] dùng cache: {len(dets)} read on-body ({cache})")
    else:
        dets = [json.loads(l) for l in open(a.dets, encoding="utf-8")]
        if a.video:
            dets = body_filter_dets(dets, a.video, a.body_thr)
            if cache:
                cache.write_text(json.dumps(dets, ensure_ascii=False), encoding="utf-8")
    jersey_meta = {m["name"]: m for m in
                   (json.loads(l) for l in
                    (a.jersey / "meta.jsonl").read_text(encoding="utf-8").splitlines())}
    clusters = json.loads(a.clusters.read_text(encoding="utf-8"))
    reads = project_reads(dets, a.tracks, a.stride)
    votes, links = link_to_clusters(reads, jersey_meta, clusters, a.uv_tol, a.frame_window)
    stats = votes.pop("_stats")
    out = {str(cid): dict(cnt) for cid, cnt in
           sorted(votes.items(), key=lambda x: -sum(x[1].values()))}
    a.out.write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    links_path = a.out.with_suffix(".links.json")
    links_path.write_text(json.dumps({str(k): v for k, v in links.items()},
                                     ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"[anchor-link] {stats['reads']} reads projected, {stats['linked']} linked "
          f"to crops; {len(out)} cụm có anchor OCR (links → {links_path.name})")
    for cid, cnt in list(out.items())[:20]:
        slot = next((c["slot"] for c in clusters if c["cid"] == int(cid)), "?")
        print(f"  C{cid:<4} {slot:<10} {cnt}")
    print(f"[anchor-link] -> {a.out}")


def selftest() -> None:
    # 1 track (tid=7) với 2 bề mặt: ngực (v≈0.30) và bụng (v≈0.50); 2 cụm tương ứng.
    # read 'mcp' ở ngực phải về cụm ngực; 'klg' ở bụng về cụm bụng — KHÔNG lẫn.
    tracks = {"fi": 5, "tid": 7, "xyxy": [100, 100, 200, 400]}  # bbox 100x300
    (Path(".selftest_tracks")).mkdir(exist_ok=True)
    (Path(".selftest_tracks") / "tracks.jsonl").write_text(json.dumps(tracks))
    # dets: mcp ở (u≈0.5,v≈0.30) → abs x=150,y=190 ; klg ở (u≈0.5,v≈0.50) → y=250
    dets = [{"frame": 10, "brand": "mcp", "text": "Mcp", "box": [146, 186, 154, 194]},
            {"frame": 10, "brand": "klg", "text": "KLG", "box": [146, 246, 154, 254]}]
    reads = project_reads(dets, Path(".selftest_tracks"))
    assert len(reads) == 2 and reads[0][0] == 7 and reads[0][5] == 10 and len(reads[0]) == 7, reads
    # crops: 2 crop cùng tid 7, (u,v)crop khớp (đảo _crop_uv_to_bbox): u_crop=(u_bbox+m)/(1+2m)
    m = MARGIN
    def inv(ub, vb): return (ub + m) / (1 + 2 * m), (vb + m) / (1 + 2 * m)
    uc_c, vc_c = inv(0.5, 0.30); uc_a, va_a = inv(0.5, 0.50)
    jersey = {"chestcrop": {"name": "chestcrop", "tid": 7, "u": uc_c, "v": vc_c, "fi_raw": 10},
              "abdocrop":  {"name": "abdocrop",  "tid": 7, "u": uc_a, "v": va_a, "fi_raw": 10}}
    clusters = [{"cid": 1, "slot": "chest", "members": ["chestcrop"]},
                {"cid": 2, "slot": "abdomen", "members": ["abdocrop"]}]
    votes, links = link_to_clusters(reads, jersey, clusters)
    votes.pop("_stats")
    assert votes[1] == Counter({"mcp": 1}), dict(votes.get(1, {}))
    assert votes[2] == Counter({"klg": 1}), dict(votes.get(2, {}))
    assert links[1][0]["crop"] == "chestcrop" and links[1][0]["brand"] == "mcp", links
    # read ở tid khác (không có crop) → không link
    r2 = [(99, 0.5, 0.3, "mcp", "Mcp", 10, 0.9)]
    v2, _ = link_to_clusters(r2, jersey, clusters); v2.pop("_stats")
    assert not v2, dict(v2)
    # FRAME-WINDOW: read frame 10; crop 'near' fi_raw 10 vs 'far' fi_raw 500 cùng tid+uv.
    # window=50 → phải khớp crop GẦN (chống mislink biển cùng track ở frame xa).
    jf = {"near": {"name": "near", "tid": 7, "u": uc_c, "v": vc_c, "fi_raw": 10},
          "far":  {"name": "far",  "tid": 7, "u": uc_c, "v": vc_c, "fi_raw": 500}}
    clf = [{"cid": 1, "slot": "chest", "members": ["near"]},
           {"cid": 9, "slot": "chest", "members": ["far"]}]
    vf, _ = link_to_clusters([(7, 0.5, 0.30, "mcp", "Mcp", 10, 0.9)], jf, clf, frame_window=50)
    vf.pop("_stats")
    assert 1 in vf and 9 not in vf, dict(vf)
    # suspect name: đơn token 'LAWRENCE' vùng ngực v<0.24 → bỏ
    assert _suspect_name("chadlaw", "LAWRENCE", 0.5, 0.15)
    assert not _suspect_name("mcp", "Mcp", 0.5, 0.30)     # ngoài name-zone
    import shutil
    shutil.rmtree(".selftest_tracks", ignore_errors=True)
    print("[selftest] OK — link (tid,uv)→cụm tách ngực/bụng đúng, reject tid lạ + họ cầu thủ ✓")


if __name__ == "__main__":
    main()
