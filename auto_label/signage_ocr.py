"""Signage WHAT tier — GENERIC OCR-lexicon brand ID (drop-in per team).

Luận điểm: đội mới = thả logo PNG → hệ tự dựng lexicon (KHÔNG hard-code). Cách:
  build-lex : OCR mỗi logo SẠCH (độ nét cao → đọc chuẩn) + token tên file → tập
              token/brand → lexicon.json.
  run       : OCR crop broadcast (mờ) → fuzzy-match token vào lexicon → brand | unknown.
              Out-of-roster (đối thủ/giải) tự thành 'unknown' vì không khớp token đội nào.

Temporal (khi chạy trên frame liên tiếp): gộp vote theo track/frame ở tầng gọi.

    python auto_label/signage_ocr.py build-lex --logos "Sponsor Logo" --out data/lexicon.json
    python auto_label/signage_ocr.py run --lex data/lexicon.json --crops <dir> --out pred.jsonl
"""
from __future__ import annotations
import argparse, json, re, sys
from pathlib import Path
from difflib import SequenceMatcher
import numpy as np, cv2

sys.path.insert(0, str(Path(__file__).parent))
from sam3_exemplar_autolabel import brand_key_from_filename  # noqa

IMG_EXT = {".png", ".jpg", ".jpeg"}
STOP = {"ltd", "the", "and", "for", "logo", "co", "uk", "yorkshire", "group",
        "services", "limited", "solutions",
        # đuôi file + màu + từ generic (nhiễu OCR tên file / biến thể)
        "png", "jpg", "jpeg", "rgb", "black", "white", "red", "blue", "green",
        "final", "new", "master", "transparent", "digital", "font", "number",
        "away", "home", "signature", "hire", "no", "in", "to", "with", "of",
        # từ generic hay xuất hiện trong ngữ cảnh tài trợ / sản phẩm (gây false-match)
        "support", "supporters", "supporter", "proud", "official", "partner",
        "partners", "sponsor", "sponsors", "love", "fall", "people", "legal",
        "safeguarding", "world", "your", "beds", "blinds", "carpet", "flooring",
        "industr", "tive", "final"}


def tok(s: str) -> list[str]:
    return [t for t in re.findall(r"[a-z]+", s.lower()) if len(t) >= 2]


def _reader():
    import easyocr
    return easyocr.Reader(["en"], gpu=True, verbose=False)


def load_rgb(p: Path):
    from PIL import Image
    try:
        im = Image.open(p); im.load()
    except Exception:
        return None
    if im.mode == "CMYK":
        im = im.convert("RGB")
    arr = np.array(im.convert("RGBA"))
    a = arr[:, :, 3:4] / 255.0
    return (arr[:, :, :3] * a + 255 * (1 - a)).astype(np.uint8)  # RGB blend trắng


def cmd_build_lex(a):
    reader = _reader()
    lex: dict[str, dict] = {}
    for p in sorted(Path(a.logos).iterdir()):
        if p.suffix.lower() not in IMG_EXT or p.stat().st_size == 0:
            continue
        brand = brand_key_from_filename(p.name)
        rgb = load_rgb(p)
        toks = set(t for t in tok(p.name) if t not in STOP)
        if rgb is not None:
            h, w = rgb.shape[:2]
            if max(h, w) < 400:
                rgb = cv2.resize(rgb, None, fx=400 / max(h, w), fy=400 / max(h, w))
            for t in reader.readtext(rgb, detail=0):
                toks |= set(x for x in tok(t) if x not in STOP)
        d = lex.setdefault(brand, {"tokens": set()})
        d["tokens"] |= toks
    out = {b: {"tokens": sorted(d["tokens"])} for b, d in lex.items() if d["tokens"]}
    Path(a.out).write_text(json.dumps(out, indent=1, ensure_ascii=False), encoding="utf-8")
    print(f"[build-lex] {len(out)} brand → {a.out}")
    for b, d in sorted(out.items()):
        print(f"  {b:16s} {d['tokens']}")


def classify(text: str, lex: dict, thr=0.82, min_len=3):
    """fuzzy-match token OCR crop vào lexicon. Trả (brand|'unknown', score)."""
    qs = [t for t in tok(text) if len(t) >= min_len]
    if not qs:
        return "unknown", 0.0
    best, bs = "unknown", 0.0
    for brand, d in lex.items():
        for q in qs:
            for t in d["tokens"]:
                if len(t) < min_len:
                    continue
                r = SequenceMatcher(None, q, t).ratio()
                if r >= thr and r > bs:
                    best, bs = brand, r
    return best, round(bs, 3)


def cmd_run(a):
    reader = _reader()
    lex = json.loads(Path(a.lex).read_text(encoding="utf-8"))
    crops = sorted(Path(a.crops).glob("*.png")) + sorted(Path(a.crops).glob("*.jpg"))
    out = []
    for p in crops:
        im = cv2.imread(str(p), cv2.IMREAD_UNCHANGED)
        if im is None:
            continue
        if im.ndim == 3 and im.shape[2] == 4:
            al = im[:, :, 3:4] / 255.0; im = (im[:, :, :3] * al + 255 * (1 - al)).astype(np.uint8)
        h, w = im.shape[:2]
        up = cv2.resize(im, None, fx=3, fy=3, interpolation=cv2.INTER_LANCZOS4) if max(h, w) < 200 else im
        text = " ".join(reader.readtext(up, detail=0))
        brand, sc = classify(text, lex, thr=a.thr)
        out.append({"id": p.stem, "text": text, "pred": brand, "score": sc})
    Path(a.out).write_text("\n".join(json.dumps(o, ensure_ascii=False) for o in out), encoding="utf-8")
    n_hit = sum(o["pred"] != "unknown" for o in out)
    print(f"[run] {len(out)} crop, {n_hit} matched roster → {a.out}")


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    b = sub.add_parser("build-lex"); b.add_argument("--logos", required=True); b.add_argument("--out", required=True)
    r = sub.add_parser("run"); r.add_argument("--lex", required=True); r.add_argument("--crops", required=True)
    r.add_argument("--out", required=True); r.add_argument("--thr", type=float, default=0.82)
    a = ap.parse_args()
    {"build-lex": cmd_build_lex, "run": cmd_run}[a.cmd](a)


if __name__ == "__main__":
    main()
