"""ANCHOR đa tín hiệu — fusion 3 kênh decorrelated, đồng thuận ≥2 (docs/12).

Lỗ hổng đang vá (đánh giá chuyên gia 2026-07-18): chuỗi inventory phụ thuộc lấy
được ≥1 định danh chắc chắn / bề mặt. Anchor cũ = CHỈ OCR-lexicon → chỉ phủ
wordmark; logo THUẦN HÌNH làm cold-start đứt. Giải: 3 kênh độc lập về cơ chế,
chấp nhận brand cho bề mặt khi ≥2 kênh đồng thuận:

  #1 OCR-lexicon   (signage_ocr.classify)  — mạnh trên chữ/wordmark
  #2 GEO           (geo_verify, ORB+RANSAC) — mạnh trên logo hình có texture
  #3 KIT-sheet     (kit_map.json)           — prior vị-trí từ ảnh kit sạch (regulation)

KIT là prior độc lập từ ảnh kit chính thức: cùng Kit Regulation ⇒ slot→brand dùng
chung toàn league (build 1 lần/regulation). Ở đây KIT vừa *đề xuất* (khi slot chỉ
có 1 brand) vừa *chứng thực* (khi khớp đề xuất của OCR/GEO).

Đầu vào: cụm inventory (mỗi cụm = 1 bề mặt) + crop nét nhất/cụm. Đầu ra: mỗi bề mặt
một nhãn CONFIRMED / UNCERTAIN / UNKNOWN kèm chi tiết từng kênh (auditable).

    python inventory/multi_anchor.py \
        --clusters data/inventory/clusters/clusters.json \
        --jersey   data/inventory/jersey \
        --logos    "Sponsor Logo" \
        --lex      data/lexicon.json \
        --kitmap   data/inventory/kitmap_home.json \
        --out      data/inventory/anchor_fused.json
    python inventory/multi_anchor.py --selftest        # chỉ logic consensus, không model
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

# cluster.slot (v-based, KHÔNG tách trước/sau) → dải dọc "band". KIT khớp theo band
# hợp nhất front+back vì OCR đọc "chest" có thể là ngực (front_chest) HOẶC lưng trên
# (back_upper) — cùng một dải cao độ trên bbox. Đây là cầu nối coarse-slot ↔ fine-kit-slot.
SLOT_TO_BANDS = {
    "collar": ("upper",), "collar/head": ("upper",), "chest": ("upper",),
    # mid/dưới: logo shorts (klg/aon) lọt lên cạp + **logo TAY (sleeve) khi cánh tay
    # đưa xuống tầm bụng/hông** (bartercard/atm/chadlaw). KHÔNG gồm upper (back_upper=mcp
    # ở cao, không thể xuống bụng) → vẫn loại đúng mcp@abdomen (board/misread).
    "abdomen": ("lower", "sleeve"), "shorts": ("lower", "sleeve"), "legs": ("lower", "sleeve"),
    "sleeve": ("sleeve",),
}
# Guard: prior quá rộng KHÔNG phải bằng chứng → bỏ. lower+sleeve ≈ 9/14 brand (0.64):
# vẫn LOẠI band upper (5 brand) nên còn phân biệt → giữ ngưỡng 0.7 để không rớt.
KIT_PRIOR_MAX_FRAC = 0.7


def _band_of_kitslot(name: str) -> str:
    """Tên slot kit (front_chest_main, back_upper, shorts_back_main…) → band dọc."""
    n = name.lower()
    if "sleeve" in n:
        return "sleeve"
    if any(k in n for k in ("shorts", "socks", "lower")):   # back_lower, shorts_*, socks_*
        return "lower"
    return "upper"                                          # chest/upper/collar/crest/patch/band


# ============================================================================
# LÕI: hàm consensus thuần (không I/O, không model) — testable độc lập
# ============================================================================
def fuse(ocr: tuple | None, geo: tuple | None, kit_set: set[str] | None,
         min_agree: int = 2, ocr_strong: bool = True) -> dict:
    """Hợp nhất 3 kênh → (status, brand, support, detail).

    ocr, geo : (brand, strength) hoặc None nếu kênh không đề xuất.
    kit_set  : tập brand kit-sheet kỳ vọng ở slot này (có thể rỗng/None).
    ocr_strong: bằng chứng OCR đủ mạnh (≥2 read/cụm). Nếu đạt support nhưng OCR chỉ
                1 read (yếu) → hạ CONFIRMED thành **LIKELY** (chờ người duyệt) — đo được
                single-read precision ~50% (cách B), KHÔNG nhận vơ là CONFIRMED.
    support(brand) = #kênh-đề-xuất{ocr,geo} chọn brand  +  (1 nếu brand ∈ kit_set).

    ≥min_agree: CONFIRMED (OCR mạnh) / LIKELY (OCR 1-read). Chưa đủ → UNCERTAIN. Không gì → UNKNOWN.
    KIT đơn (đúng 1 brand) mà OCR+GEO câm vẫn cho UNCERTAIN (prior yếu, không tự CONFIRMED).
    """
    kit_set = set(kit_set or [])
    votes: dict[str, int] = {}           # brand → #kênh {ocr,geo} đề xuất
    # rank độ tin cậy kênh (cross-channel strength KHÔNG so sánh được — reads vs
    # inliers khác thang): khi support hoà, ưu tiên kênh chính xác hơn. OCR
    # full-frame > GEO (GEO nhiễu ở crop <~60px, đo thực 2026-07).
    rank: dict[str, int] = {}
    for ch, prio in ((ocr, 2), (geo, 1)):
        if ch and ch[0] and ch[0] != "unknown":
            b = ch[0]
            votes[b] = votes.get(b, 0) + 1
            rank[b] = max(rank.get(b, 0), prio)

    def support(b: str) -> int:
        return votes.get(b, 0) + (1 if b in kit_set else 0)

    # KIT chỉ CORROBORATE brand mà OCR/GEO đã đề xuất (identity source). KIT một mình
    # KHÔNG định danh được TRỪ KHI singleton (đúng 1 brand ⇒ prior vị trí = identity).
    cands = set(votes)
    if len(kit_set) == 1:
        cands |= kit_set
    if not cands:
        return {"status": "UNKNOWN", "brand": None, "support": 0,
                "detail": _detail(ocr, geo, kit_set)}
    # xếp: support cao trước, rồi kênh tin cậy nhất đề xuất, rồi tên (ổn định)
    best = max(cands, key=lambda b: (support(b), rank.get(b, 0), b))
    sup = support(best)
    if sup >= min_agree:
        # OCR 1-read (yếu) là kênh mang best → LIKELY (chờ duyệt), không CONFIRMED
        weak_single = (ocr is not None and ocr[0] == best and not ocr_strong)
        status = "LIKELY" if weak_single else "CONFIRMED"
    else:
        status = "UNCERTAIN"
    return {"status": status, "brand": best, "support": sup,
            "detail": _detail(ocr, geo, kit_set)}


def _detail(ocr, geo, kit_set) -> dict:
    return {"ocr": list(ocr) if ocr else None,
            "geo": list(geo) if geo else None,
            "kit": sorted(kit_set) if kit_set else []}


# ============================================================================
# Kênh KIT: kitmap.json → {garment: set(brand)}
# ============================================================================
def kit_slot_brands(kitmap: dict) -> dict[str, set[str]]:
    """{garment_slot_name: set(brand)} — hỗ trợ 2 format kit_map:

    (B) 'final' đã chỉnh tay: {"slots": [{"slot": "front_chest_main", "brand": ...}]}
    (A) raw kit_map.py       : {"names": {cid: gname}, "hits": [{brand, comp}]}
    """
    if kitmap.get("slots"):                              # format B
        out: dict[str, set[str]] = {}
        for s in kitmap["slots"]:
            out.setdefault(str(s["slot"]).lower(), set()).add(s["brand"])
        return out
    names = kitmap.get("names", {}) or {}                # format A
    comp2brands: dict[int, set[str]] = {}
    for h in kitmap.get("hits", []):
        comp2brands.setdefault(h.get("comp", -1), set()).add(h["brand"])
    out = {}
    for cid_str, gname in names.items():
        brands = comp2brands.get(int(cid_str), set())
        out.setdefault(str(gname).lower(), set()).update(brands)
    return out


def ocr_by_slot(anchor_inv: list[dict]) -> dict[str, tuple[str, int]]:
    """anchor_slots.py output (full-frame OCR) → {slot: (brand, reads)}.

    Kênh OCR ĐÚNG = OCR full-frame 1080p chiếu vào bbox (anchor_slots.py), KHÔNG
    phải OCR crop nhỏ (~20-48px không đọc nổi). Lấy brand nhiều reads nhất/slot,
    bỏ trạng thái nghi ngờ (tên cầu thủ / non-target).
    """
    best: dict[str, tuple[str, int]] = {}
    for e in anchor_inv:
        if e.get("status") in ("SUSPECT_PLAYER_NAME", "WEAK_NON_TARGET"):
            continue
        slot, reads = e["slot"], e.get("reads", 0)
        if slot not in best or reads > best[slot][1]:
            best[slot] = (e["brand"], reads)
    return best


def kit_zone_brands(garment_brands: dict[str, set[str]]) -> dict[str, set[str]]:
    """{slotname: {brand}} → {band: {brand}} (bỏ marker cấu trúc '_club_crest'…)."""
    zones: dict[str, set[str]] = {}
    for sname, brands in garment_brands.items():
        band = _band_of_kitslot(sname)
        zones.setdefault(band, set()).update(b for b in brands if not b.startswith("_"))
    return zones


def kit_expected(cluster_slot: str, zone_brands: dict[str, set[str]]) -> set[str]:
    """Tập brand kit kỳ vọng ở dải dọc của slot (hợp nhất front+back)."""
    exp: set[str] = set()
    for band in SLOT_TO_BANDS.get(cluster_slot, ("upper",)):
        exp |= zone_brands.get(band, set())
    return exp


# ============================================================================
# Chọn crop nét nhất / cụm (Laplacian var × kích thước) rồi chạy OCR + GEO
# ============================================================================
def _sharpness(crop_dir: Path, name: str):
    import cv2
    import numpy as np
    im = cv2.imread(str(crop_dir / f"{name}.png"), cv2.IMREAD_UNCHANGED)
    if im is None:
        return None, 0.0, 0
    if im.ndim == 3 and im.shape[2] == 4:
        a = im[:, :, 3:4] / 255.0
        rgb = (im[:, :, :3] * a + 255 * (1 - a)).astype(np.uint8)
    else:
        rgb = im
    g = cv2.cvtColor(rgb, cv2.COLOR_BGR2GRAY) if rgb.ndim == 3 else rgb
    lap = float(cv2.Laplacian(g, cv2.CV_64F).var())
    return im, lap, max(g.shape[:2])


def run_channels(clusters: list[dict], jersey: Path, logos: str, lex_path: str | None,
                 kitmap: dict | None, topk: int, ocr_thr: float,
                 min_inliers: int, min_agree: int,
                 anchor_ocr: list[dict] | None = None,
                 cluster_ocr: dict | None = None, min_ocr_votes: int = 2,
                 use_geo: bool = False,
                 cluster_links: dict | None = None, min_ocr_conf: float = 0.6,
                 geo_chest: bool = False, geo_min_px: int = 55,
                 geo_slots: tuple = ("chest", "collar", "collar/head")) -> list[dict]:
    import sys
    sys.path.insert(0, str(Path(__file__).parent.parent / "auto_label"))
    import geo_verify

    crop_dir = jersey / "crops"
    meta = {}
    for ln in (jersey / "meta.jsonl").read_text(encoding="utf-8").splitlines():
        d = json.loads(ln)
        meta[d["name"]] = d

    # KÊNH OCR (#1): ưu tiên full-frame anchor (anchor_slots.py) — đã chứng minh
    # đọc được mcp/klg; OCR crop nhỏ chỉ là fallback (yếu ở <~60px, đo thực 2026-07).
    ocr_slot = ocr_by_slot(anchor_ocr) if anchor_ocr else {}
    reader = lex = classify = None
    if not anchor_ocr and not cluster_ocr and not cluster_links:
        from signage_ocr import classify, _reader, cmd_build_lex  # noqa
        if lex_path and Path(lex_path).exists():
            lex = json.loads(Path(lex_path).read_text(encoding="utf-8"))
        else:
            tmp = Path(logos).parent / "_lex_auto.json"
            cmd_build_lex(argparse.Namespace(logos=logos, out=str(tmp)))
            lex = json.loads(tmp.read_text(encoding="utf-8"))
        reader = _reader()

    # kênh GEO (#2) — chỉ dùng khi có close-up (≥~60px); ở crop broadcast nhỏ GEO là
    # NHIỄU (acs/paints hút inlier giả) → mặc định TẮT, tránh geo+kit thành false CONFIRMED.
    bank = geo_verify.build_bank(logos) if (use_geo or geo_chest) else {}
    zone_brands = kit_zone_brands(kit_slot_brands(kitmap)) if kitmap else {}
    n_kit_brands = len(set().union(*zone_brands.values())) if zone_brands else 0

    import cv2
    import numpy as np
    results = []
    for c in clusters:
        # top-K crop nét & to nhất trong cụm
        scored = []
        for name in c["members"]:
            im, lap, longpx = _sharpness(crop_dir, name)
            if im is None:
                continue
            size = max(meta.get(name, {}).get("wh", [longpx, longpx]))
            scored.append((lap * size, im, name, size))
        scored.sort(key=lambda x: -x[0])
        picks = scored[:topk]
        top_px = max((p[3] for p in picks), default=0)

        # --- kênh OCR ---
        ocr_strong = True
        if cluster_links is not None:                # PER-CLUSTER + conf-gate (cách B)
            agg: dict[str, list] = {}                # brand -> [n, max_conf]
            for lk in cluster_links.get(str(c["cid"]), []):
                a2 = agg.setdefault(lk["brand"], [0, 0.0])
                a2[0] += 1
                a2[1] = max(a2[1], lk.get("ocr_conf", 0.0))
            if agg:
                b = max(agg, key=lambda k: (agg[k][0], agg[k][1]))
                n, cf = agg[b]
                # ≥2 read tự tin cậy; 1 read chỉ tính nếu OCR full-frame đủ chắc (conf-gate)
                ocr = (b, n) if (n >= min_ocr_votes or (n >= 1 and cf >= min_ocr_conf)) else None
                ocr_strong = n >= min_ocr_votes      # 1-read → LIKELY (chờ duyệt)
            else:
                ocr = None
        elif cluster_ocr is not None:                # PER-CLUSTER (không conf-gate)
            cnt = cluster_ocr.get(str(c["cid"]), {})
            if cnt:
                b, n = max(cnt.items(), key=lambda x: x[1])
                ocr = (b, n) if n >= min_ocr_votes else None
            else:
                ocr = None
        elif anchor_ocr is not None:
            ocr = ocr_slot.get(c["slot"])            # (brand, reads) full-frame per-SLOT
        else:
            ocr_votes: dict[str, float] = {}
            for _, im, _name, _sz in picks:
                if im.ndim == 3 and im.shape[2] == 4:
                    a = im[:, :, 3:4] / 255.0
                    rgb = (im[:, :, :3] * a + 255 * (1 - a)).astype(np.uint8)
                else:
                    rgb = im
                h, w = rgb.shape[:2]
                up = (cv2.resize(rgb, None, fx=3, fy=3, interpolation=cv2.INTER_LANCZOS4)
                      if max(h, w) < 200 else rgb)
                text = " ".join(reader.readtext(up, detail=0))
                brand, sc = classify(text, lex, thr=ocr_thr)
                if brand != "unknown":
                    ocr_votes[brand] = ocr_votes.get(brand, 0.0) + sc
            ocr = max(ocr_votes.items(), key=lambda x: x[1]) if ocr_votes else None

        # --- kênh GEO --- (toàn cục nếu use_geo; hoặc CÓ MỤC TIÊU cho chest close-up:
        # top_notch ∞ OCR không đọc → geo khớp logo-PNG trên crop ngực đủ to ≥ geo_min_px)
        geo = None
        geo_active = bool(bank) and (use_geo or
                        (geo_chest and c["slot"] in geo_slots and top_px >= geo_min_px))
        if geo_active:
            geo_votes: dict[str, int] = {}
            for _, im, _name, _sz in picks:
                for r in geo_verify.verify(geo_verify._to_gray(im), bank, min_inliers):
                    geo_votes[r["brand"]] = geo_votes.get(r["brand"], 0) + r["inliers"]
            geo = max(geo_votes.items(), key=lambda x: x[1]) if geo_votes else None

        # --- kênh KIT --- (bỏ prior quá rộng → không phải bằng chứng)
        kit_set = kit_expected(c["slot"], zone_brands) if zone_brands else set()
        if kit_set and len(kit_set) > KIT_PRIOR_MAX_FRAC * max(n_kit_brands, 1):
            kit_set = set()

        fused = fuse(ocr, geo, kit_set, min_agree, ocr_strong)
        results.append({"cid": c["cid"], "slot": c["slot"], "n": c["n"],
                        "u": c.get("u"), "v": c.get("v"),
                        "n_crops_used": len(picks), **fused})
    return results


def _print_table(results: list[dict]) -> None:
    print(f"{'cid':>5} {'slot':10} {'status':10} {'brand':12} sup  "
          f"ocr / geo / kit")
    for r in results:
        d = r["detail"]
        ocr = f"{d['ocr'][0]}:{d['ocr'][1]}" if d["ocr"] else "-"
        geo = f"{d['geo'][0]}:{d['geo'][1]}" if d["geo"] else "-"
        kit = ",".join(d["kit"]) or "-"
        print(f"{r['cid']:>5} {r['slot']:10} {r['status']:10} "
              f"{str(r['brand']):12} {r['support']:>2}   {ocr} / {geo} / {kit}")
    def nst(s):
        return sum(r["status"] == s for r in results)
    print(f"\n[fused] {len(results)} bề mặt → CONFIRMED {nst('CONFIRMED')}, "
          f"LIKELY {nst('LIKELY')} (chờ duyệt), UNCERTAIN {nst('UNCERTAIN')}, "
          f"UNKNOWN {nst('UNKNOWN')}")


# ============================================================================
# selftest — chỉ luật consensus, không I/O/model
# ============================================================================
def selftest() -> None:
    # ≥2 đồng thuận (ocr+geo cùng brand) → CONFIRMED
    r = fuse(("klg", 0.9), ("klg", 40), set(), min_agree=2)
    assert r["status"] == "CONFIRMED" and r["brand"] == "klg", r
    # ocr + kit đồng thuận (geo câm) → CONFIRMED (kênh khác cơ chế)
    r = fuse(("mcp", 0.8), None, {"mcp"}, min_agree=2)
    assert r["status"] == "CONFIRMED" and r["brand"] == "mcp", r
    # OCR 1-read (ocr_strong=False) + kit → LIKELY (chờ duyệt), KHÔNG auto-CONFIRMED
    r = fuse(("klg", 1), None, {"klg"}, min_agree=2, ocr_strong=False)
    assert r["status"] == "LIKELY" and r["brand"] == "klg", r
    # OCR ≥2 read (ocr_strong=True) + kit → CONFIRMED
    r = fuse(("klg", 2), None, {"klg"}, min_agree=2, ocr_strong=True)
    assert r["status"] == "CONFIRMED", r
    # chỉ 1 kênh (geo) đề xuất → UNCERTAIN
    r = fuse(None, ("crest", 30), set(), min_agree=2)
    assert r["status"] == "UNCERTAIN" and r["brand"] == "crest", r
    # OCR vs GEO mâu thuẫn, không kit → hoà support: ưu tiên OCR (tin cậy hơn),
    # KHÔNG so inlier thô 129>9. Đây là fix lỗi cross-channel strength.
    r = fuse(("mcp", 9), ("acs", 129), set(), min_agree=2)
    assert r["status"] == "UNCERTAIN" and r["brand"] == "mcp", r
    # ocr vs geo mâu thuẫn, kit nghiêng về geo → geo được kit chứng thực → CONFIRMED geo
    r = fuse(("aon", 0.7), ("klg", 20), {"klg"}, min_agree=2)
    assert r["status"] == "CONFIRMED" and r["brand"] == "klg", r
    # không kênh nào → UNKNOWN
    r = fuse(None, None, set(), min_agree=2)
    assert r["status"] == "UNKNOWN" and r["brand"] is None, r
    # KIT đơn nhưng OCR/GEO câm → prior yếu, chỉ UNCERTAIN (không tự CONFIRMED)
    r = fuse(None, None, {"top_notch"}, min_agree=2)
    assert r["status"] == "UNCERTAIN" and r["brand"] == "top_notch", r
    # KIT nhiều brand + không OCR/GEO → KHÔNG định danh được → UNKNOWN (không rubber-stamp)
    r = fuse(None, None, {"acs", "aon", "klg", "paints_laquers"}, min_agree=2)
    assert r["status"] == "UNKNOWN" and r["brand"] is None, r
    # KIT band-mapping (schema 'final' 25/26): mcp=back_upper → band 'upper',
    # klg=shorts_back → 'lower'. slot 'chest' phải kỳ vọng mcp (lưng trên nhìn từ sau).
    km = {"slots": [{"slot": "front_chest_main", "brand": "top_notch"},
                    {"slot": "back_upper", "brand": "mcp"},
                    {"slot": "back_lower", "brand": "acs"},
                    {"slot": "shorts_back_main", "brand": "klg"},
                    {"slot": "front_crest", "brand": "_club_crest"},
                    {"slot": "sleeve_right_low", "brand": "bartercard"}]}
    zb = kit_zone_brands(kit_slot_brands(km))
    assert zb["upper"] == {"top_notch", "mcp"}, zb          # front_chest + back_upper, bỏ _crest
    assert zb["lower"] == {"acs", "klg"} and zb["sleeve"] == {"bartercard"}, zb
    assert kit_expected("chest", zb) == {"top_notch", "mcp"}, kit_expected("chest", zb)
    # lower slots gồm cả sleeve-band (tay với xuống): bartercard=sleeve → vào abdomen/shorts
    assert kit_expected("shorts", zb) == {"acs", "klg", "bartercard"}, kit_expected("shorts", zb)
    assert kit_expected("abdomen", zb) == {"acs", "klg", "bartercard"}, kit_expected("abdomen", zb)
    # end-to-end: OCR đọc mcp ở 'chest' + KIT có mcp ở band upper → CONFIRMED
    r = fuse(("mcp", 3), None, kit_expected("chest", zb), min_agree=2)
    assert r["status"] == "CONFIRMED" and r["brand"] == "mcp", r
    print("[selftest] OK — consensus ≥2, kit band-map (front+back), OCR⊕KIT→CONFIRMED ✓")


def main() -> None:
    ap = argparse.ArgumentParser(description="Multi-signal anchor fusion (OCR⊕GEO⊕KIT)")
    ap.add_argument("--clusters", type=Path)
    ap.add_argument("--jersey", type=Path)
    ap.add_argument("--logos")
    ap.add_argument("--lex", default=None)
    ap.add_argument("--anchor-ocr", default=None,
                    help="bradford_inventory.json (anchor_slots full-frame OCR) = kênh OCR #1 per-SLOT")
    ap.add_argument("--cluster-ocr", default=None,
                    help="cluster_ocr.json (anchor_link per-CLUSTER) — ưu tiên, đã fix coupling")
    ap.add_argument("--cluster-links", default=None,
                    help="*.links.json (anchor_link) — per-cluster + conf-gate cho single read (cách B)")
    ap.add_argument("--min-ocr-votes", type=int, default=2,
                    help="số read full-frame để OCR thành vote KHÔNG cần conf-gate")
    ap.add_argument("--min-ocr-conf", type=float, default=0.6,
                    help="ocr_conf tối thiểu để 1 read đơn được tính (cách B)")
    ap.add_argument("--kitmap", default=None)
    ap.add_argument("--out", type=Path)
    ap.add_argument("--topk", type=int, default=5, help="số crop nét nhất/cụm")
    ap.add_argument("--ocr-thr", type=float, default=0.82)
    ap.add_argument("--min-inliers", type=int, default=8)
    ap.add_argument("--min-agree", type=int, default=2, help="số kênh tối thiểu để CONFIRMED")
    ap.add_argument("--use-geo", action="store_true",
                    help="bật kênh GEO toàn cục (chỉ khi có close-up ≥60px; mặc định TẮT vì geo nhiễu ở crop nhỏ)")
    ap.add_argument("--geo-chest", action="store_true",
                    help="bật GEO CÓ MỤC TIÊU cho chest close-up (ID top_notch ∞ mà OCR không đọc)")
    ap.add_argument("--geo-min-px", type=int, default=55, help="crop tối thiểu để geo-chest chạy")
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args()
    if a.selftest:
        selftest()
        return
    if not (a.clusters and a.jersey and a.logos and a.out):
        ap.error("cần --clusters --jersey --logos --out (hoặc --selftest)")
    clusters = json.loads(a.clusters.read_text(encoding="utf-8"))
    kitmap = (json.loads(Path(a.kitmap).read_text(encoding="utf-8"))
              if a.kitmap and Path(a.kitmap).exists() else None)
    anchor_ocr = (json.loads(Path(a.anchor_ocr).read_text(encoding="utf-8"))
                  if a.anchor_ocr and Path(a.anchor_ocr).exists() else None)
    cluster_ocr = (json.loads(Path(a.cluster_ocr).read_text(encoding="utf-8"))
                   if a.cluster_ocr and Path(a.cluster_ocr).exists() else None)
    cluster_links = (json.loads(Path(a.cluster_links).read_text(encoding="utf-8"))
                     if a.cluster_links and Path(a.cluster_links).exists() else None)
    results = run_channels(clusters, a.jersey, a.logos, a.lex, kitmap,
                           a.topk, a.ocr_thr, a.min_inliers, a.min_agree, anchor_ocr,
                           cluster_ocr, a.min_ocr_votes, a.use_geo,
                           cluster_links, a.min_ocr_conf, a.geo_chest, a.geo_min_px)
    a.out.write_text(json.dumps(results, ensure_ascii=False, indent=1), encoding="utf-8")
    _print_table(results)
    print(f"[fused] -> {a.out}")


if __name__ == "__main__":
    main()
