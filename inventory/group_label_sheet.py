"""Group-to-label sheet — nhóm logo theo (ĐỘI × SLOT), để NGƯỜI label một lần (docs/12).

Ý tưởng (user 2026-07-19): SAM3 detect mọi logo class-agnostic → KHÔNG auto-đặt tên
(khâu dễ vỡ: OCR fail top_notch, RF-DETR closed-set). Thay vào đó gom theo khóa VẬT LÝ
bất biến của Kit Regulation — **(đội, slot)** ⇒ mỗi nhóm = đúng MỘT logo — rồi người
nhìn montage nhóm, điền tên MỘT lần/nhóm (O(1)/club, 100% đúng). KHÔNG dùng DINOv2
(đã chứng minh bẩn ở 20-50px); dùng vị trí làm khóa chính.

  đội   : màu torso cầu thủ (trắng=Bradford / xanh=đối thủ / khác=trọng tài…)
  slot  : vị trí (u,v) trên thân → collar/chest/abdomen/shorts/legs
  quality-gate: bỏ crop nhỏ/mờ (SAM3 over-fire nếp vải)

    python inventory/group_label_sheet.py --jersey data/inventory/jersey_wak \
        --tracks data/inventory/tracks_wak --video data/real/yt/bradford_wakefield26.mp4 \
        --out data/inventory/label_sheet_wak
"""
from __future__ import annotations

import argparse
import json
from collections import defaultdict
from pathlib import Path

import cv2
import numpy as np

SLOTS = ["collar", "sleeve", "chest", "abdomen", "shorts", "legs"]
# từ cần loại khỏi nhóm logo (số áo lo riêng): logo GIẢI / board / generic
STOP_WORDS = {"betfred", "super", "league", "rfl", "rugby", "football", "premier",
              "proud", "official", "partner", "sponsor", "supporters"}


def slot_of(u: float, v: float) -> str:
    if v < 0.14:  return "collar"
    # rìa ngang ở tầm thân trên = tay áo (sleeve), tách khỏi ngực/bụng
    if v < 0.55 and (u < 0.26 or u > 0.74):  return "sleeve"
    if v < 0.40:  return "chest"
    if v < 0.55:  return "abdomen"
    if v < 0.72:  return "shorts"
    return "legs"


def _classify_crop(text: str, lex_tokens: set, v: float) -> str:
    """OCR text của crop → 'logo' (giữ) / 'number' / 'name' / 'league' (loại)."""
    import re
    t = text.strip()
    digits = re.sub(r"[^0-9]", "", t)
    letters = re.findall(r"[A-Za-z]+", t)
    if digits and len(digits) <= 2 and len("".join(letters)) <= 1:
        return "number"                       # số áo
    toks = [w.lower() for w in letters]
    if any(w in STOP_WORDS for w in toks):
        return "league"                       # BETFRED / SUPER LEAGUE …
    # 1 từ IN HOA vùng tên (lưng trên) không thuộc sponsor lexicon → tên cầu thủ
    if (len(toks) == 1 and len(toks[0]) >= 5 and t.isupper()
            and toks[0] not in lex_tokens and v < 0.34):
        return "name"
    return "logo"


def team_of_color(bgr) -> str:
    """torso mean BGR → đội. Trắng=Bradford, xanh navy=đối thủ, xanh lá=trọng tài."""
    b, g, r = float(bgr[0]), float(bgr[1]), float(bgr[2])
    mn, mx = min(b, g, r), max(b, g, r)
    if mn > 115 and (mx - mn) < 70:
        return "white"            # kit trắng (Bradford 25/26)
    if b > r + 22 and b > g + 8:
        return "blue"             # navy (đối thủ)
    if g > r + 20 and g > b + 10:
        return "green"            # trọng tài hi-vis
    return "other"


def team_per_track(tracks_dir: Path, video: str, stride: int, tids_needed: set) -> dict:
    """Mỗi track: lấy person-box TO nhất, sample màu torso → gán đội (cache/track)."""
    best_box = {}   # tid -> (area, fi_raw, xyxy)
    for ln in (tracks_dir / "tracks.jsonl").read_text().splitlines():
        d = json.loads(ln)
        if d["tid"] not in tids_needed:
            continue
        x0, y0, x1, y1 = d["xyxy"]
        area = (x1 - x0) * (y1 - y0)
        if d["tid"] not in best_box or area > best_box[d["tid"]][0]:
            best_box[d["tid"]] = (area, d["fi"] * stride, d["xyxy"])
    # đọc video theo frame để sample màu
    by_frame = defaultdict(list)
    for tid, (_, fr, xyxy) in best_box.items():
        by_frame[fr].append((tid, xyxy))
    cap = cv2.VideoCapture(video)
    team = {}
    for fr in sorted(by_frame):
        cap.set(cv2.CAP_PROP_POS_FRAMES, fr)
        ok, frame = cap.read()
        if not ok:
            continue
        for tid, (x0, y0, x1, y1) in ((t, [int(v) for v in b]) for t, b in by_frame[fr]):
            h = y1 - y0
            t = frame[y0 + int(h * 0.18):y0 + int(h * 0.45), x0:x1]
            team[tid] = team_of_color(t.reshape(-1, 3).mean(0)) if t.size else "other"
    cap.release()
    return team


def _load_on_white(p: Path):
    im = cv2.imread(str(p), cv2.IMREAD_UNCHANGED)
    if im is None:
        return None
    if im.ndim == 3 and im.shape[2] == 4:
        a = im[:, :, 3:4] / 255.0
        im = (im[:, :, :3] * a + 255 * (1 - a)).astype(np.uint8)
    return im


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--jersey", required=True, type=Path)
    ap.add_argument("--tracks", required=True, type=Path)
    ap.add_argument("--video", required=True)
    ap.add_argument("--out", required=True, type=Path)
    ap.add_argument("--stride", type=int, default=2)
    ap.add_argument("--min-px", type=int, default=26, help="quality-gate cạnh dài")
    ap.add_argument("--min-lap", type=float, default=45.0, help="quality-gate độ nét")
    ap.add_argument("--teams", default="white,blue", help="đội hiển thị (bỏ green/other)")
    ap.add_argument("--per-group", type=int, default=12)
    ap.add_argument("--filter-ocr", action="store_true", default=True,
                    help="OCR lọc số áo/tên cầu thủ/logo giải khỏi nhóm logo")
    ap.add_argument("--no-filter-ocr", dest="filter_ocr", action="store_false")
    ap.add_argument("--lex", default="data/lexicon.json")
    a = ap.parse_args()
    a.out.mkdir(parents=True, exist_ok=True)
    crop_dir = a.jersey / "crops"

    meta = [json.loads(l) for l in (a.jersey / "meta.jsonl").read_text().splitlines()]
    tids = {m["tid"] for m in meta}
    team = team_per_track(a.tracks, a.video, a.stride, tids)
    from collections import Counter
    print(f"[team] {dict(Counter(team.values()))} trên {len(team)} track")

    # gom theo (đội, slot) + quality-gate
    groups: dict[tuple, list] = defaultdict(list)
    for m in meta:
        tm = team.get(m["tid"], "other")
        if max(m["wh"]) < a.min_px:
            continue
        im = _load_on_white(crop_dir / f"{m['name']}.png")
        if im is None:
            continue
        g = cv2.cvtColor(im, cv2.COLOR_BGR2GRAY)
        if cv2.Laplacian(g, cv2.CV_64F).var() < a.min_lap:
            continue
        groups[(tm, slot_of(m["u"], m["v"]))].append((max(m["wh"]), im, m["name"], m["v"]))

    # OCR-filter: bỏ số áo / tên cầu thủ / logo giải khỏi nhóm logo
    reader = lex_tokens = None
    if a.filter_ocr:
        import sys
        sys.path.insert(0, str(Path(__file__).parent.parent / "auto_label"))
        from signage_ocr import _reader, tok
        reader = _reader()
        lexj = json.loads(Path(a.lex).read_text(encoding="utf-8")) if Path(a.lex).exists() else {}
        lex_tokens = {t for d in lexj.values() for t in d.get("tokens", [])}
        lex_tokens |= {t for b in lexj for t in tok(b)}

    show_teams = a.teams.split(",")
    order = [(tm, sl) for tm in show_teams for sl in SLOTS if (tm, sl) in groups]
    CELL, NC = 104, a.per_group
    rows = []
    label_rows = []
    for (tm, sl) in order:
        cand = sorted(groups[(tm, sl)], key=lambda x: -x[0])
        items, dropped = [], defaultdict(int)
        for size, im, name, v in cand:
            if reader is not None:
                txt = " ".join(reader.readtext(im if max(im.shape[:2]) >= 90 else
                               cv2.resize(im, None, fx=3, fy=3), detail=0))
                kind = _classify_crop(txt, lex_tokens, v)
                if kind != "logo":
                    dropped[kind] += 1
                    continue
            items.append((size, im, name))
            if len(items) >= NC:
                break
        cells = []
        for _, im, _n in items:
            h, w = im.shape[:2]; s = (CELL - 8) / max(h, w)
            r = cv2.resize(im, (max(1, int(w * s)), max(1, int(h * s))),
                           interpolation=cv2.INTER_LANCZOS4 if s > 1 else cv2.INTER_AREA)
            c = np.full((CELL, CELL, 3), 250, np.uint8)
            yo, xo = (CELL - r.shape[0]) // 2, (CELL - r.shape[1]) // 2
            c[yo:yo + r.shape[0], xo:xo + r.shape[1]] = r
            cv2.rectangle(c, (0, 0), (CELL - 1, CELL - 1), (225, 225, 225), 1)
            cells.append(c)
        while len(cells) < NC:
            cells.append(np.full((CELL, CELL, 3), 255, np.uint8))
        strip = np.hstack(cells)
        head = np.full((30, strip.shape[1], 3), (70, 50, 30), np.uint8)
        n_tot = len(groups[(tm, sl)])
        drop = "  ".join(f"-{k}:{n}" for k, n in dropped.items()) if dropped else ""
        cv2.putText(head, f"{tm.upper()} / {sl}   (n={n_tot} {drop})   ->  ____________",
                    (8, 20), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (255, 255, 255), 2)
        rows += [head, strip, np.full((8, strip.shape[1], 3), 255, np.uint8)]
        label_rows.append({"team": tm, "slot": sl, "n": n_tot,
                           "dropped": dict(dropped), "brand": ""})

    if rows:
        cv2.imwrite(str(a.out / "label_sheet.png"), np.vstack(rows))
    (a.out / "label_sheet.json").write_text(
        json.dumps(label_rows, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"[sheet] {len(order)} nhóm (đội×slot) -> {a.out/'label_sheet.png'}")
    for lr in label_rows:
        print(f"   {lr['team']:6} {lr['slot']:8} n={lr['n']}")


if __name__ == "__main__":
    main()
