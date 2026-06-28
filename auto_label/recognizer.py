"""Phase 2 — Tầng 2 Recognizer: định danh brand bằng embedding + retrieval.

Triết lý (xem `../autolabel.md` §4, `../expert_review_and_plan.md`):
  crop logo (do Tầng 1 cắt) → embedding → so cosine với Template DB → brand gần
  nhất; nếu score < τ → "unknown". **Thêm brand mới = thêm vector, KHÔNG train lại.**

Cải tiến open-set (vá điểm yếu AUROC≈0.61 của raw DINO):
  #1 MASK nền: crop sát + xoá nền (theo alpha/mask SAM 3) trước khi embed → CLS
     token không còn bị nền/màu chi phối.
  #2 LOGO FINGERPRINT: fuse visual ⊕ color(hue-hist) ⊕ text(OCR) — kênh text tách
     được các logo "nhìn giống" nhưng chữ khác (yellow vs paints_laquers).

Encoder: DINO/SigLIP qua `transformers`. Mặc định `facebook/dinov2-base` (mở);
đổi `--model` sang DINOv3/SigLIP2. Vector store: numpy brute-force cosine.

Lệnh con:
  build  — embed logo gốc (+ gallery) → Template DB (.npz: vec ⊕ color ⊕ text)
  query  — embed crop → fuse → brand + score → JSONL cho `eval_recognition.py`

Crop để query (gt suy từ thư mục con; 'unknown' = logo ngoài DB). Crop có alpha
(PNG RGBA) → alpha dùng làm mask; nếu không có alpha thì không mask.
    crops/<brand>/*.png
    crops/unknown/*.png

Chạy:
    python auto_label/recognizer.py build --logos "Sponsor Logo" --out data/templates.npz
    python auto_label/recognizer.py query --db data/templates.npz \
        --crops data/gold/recognition/crops --out pred.jsonl --mask --w-color 0.2
    python auto_label/eval_recognition.py --pred pred.jsonl --tau 0.5
    python auto_label/recognizer.py selftest      # logic, không cần model
"""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

import numpy as np

try:
    import cv2
except Exception:
    cv2 = None

IMG_EXT = {".png", ".jpg", ".jpeg", ".bmp", ".webp"}
HUE_BINS = 12


# --------------------------------------------------------------------------- #
# Ảnh + mask
# --------------------------------------------------------------------------- #

def load_image(path: Path) -> "tuple[np.ndarray, np.ndarray | None] | None":
    """Đọc ảnh → (rgb, mask). mask = alpha>0 nếu có kênh alpha, else None."""
    img = cv2.imread(str(path), cv2.IMREAD_UNCHANGED)
    if img is None:
        return None
    mask = None
    if img.ndim == 3 and img.shape[2] == 4:
        mask = (img[:, :, 3] > 0).astype(np.uint8)
        bgr = img[:, :, :3].astype(np.float32)
        a = img[:, :, 3:4].astype(np.float32) / 255.0
        img = (bgr * a + 255.0 * (1 - a)).astype(np.uint8)   # blend nền trắng
    elif img.ndim == 2:
        img = cv2.cvtColor(img, cv2.COLOR_GRAY2BGR)
    return cv2.cvtColor(img, cv2.COLOR_BGR2RGB), mask


def bgra_to_rgb(img: np.ndarray) -> np.ndarray:
    """(Giữ cho test cũ) BGRA/Gray → RGB blend nền trắng."""
    if img.ndim == 2:
        img = cv2.cvtColor(img, cv2.COLOR_GRAY2BGR)
    if img.shape[2] == 4:
        bgr = img[:, :, :3].astype(np.float32)
        a = img[:, :, 3:4].astype(np.float32) / 255.0
        img = (bgr * a + 255.0 * (1 - a)).astype(np.uint8)
    return cv2.cvtColor(img, cv2.COLOR_BGR2RGB)


def prep_for_embed(rgb: np.ndarray, mask: "np.ndarray | None",
                   tight: bool = True, pad: float = 0.08,
                   neutral: int = 255) -> np.ndarray:
    """#1: crop sát foreground + xoá nền → embedding tập trung vào logo."""
    if mask is None or mask.max() == 0:
        return rgb
    ys, xs = np.where(mask > 0)
    out = rgb
    m = mask
    if tight:
        x0, x1, y0, y1 = xs.min(), xs.max(), ys.min(), ys.max()
        pw = int((x1 - x0) * pad); ph = int((y1 - y0) * pad)
        y0 = max(0, y0 - ph); y1 = min(rgb.shape[0], y1 + ph + 1)
        x0 = max(0, x0 - pw); x1 = min(rgb.shape[1], x1 + pw + 1)
        out = rgb[y0:y1, x0:x1]; m = mask[y0:y1, x0:x1]
    out = out.copy()
    out[m == 0] = neutral
    return out


def hue_hist(rgb: np.ndarray, mask: "np.ndarray | None", bins: int = HUE_BINS) -> np.ndarray:
    """Kênh color: histogram hue trên vùng logo, L2-normalize (cho cosine)."""
    hsv = cv2.cvtColor(rgb, cv2.COLOR_RGB2HSV)
    h = hsv[:, :, 0]
    h = h[mask > 0] if (mask is not None and mask.max() > 0) else h.ravel()
    if h.size == 0:
        return np.zeros(bins, np.float32)
    hist, _ = np.histogram(h, bins=bins, range=(0, 180))
    hist = hist.astype(np.float32)
    n = np.linalg.norm(hist)
    return hist / n if n > 0 else hist


# --------------------------------------------------------------------------- #
# Text channel (OCR) — backend tùy chọn, nạp trễ
# --------------------------------------------------------------------------- #

_TOK = re.compile(r"[a-z0-9]+")


def tokenize(s: str) -> set[str]:
    return {t for t in _TOK.findall((s or "").lower()) if len(t) > 1}


def text_sim(a: str, b: str) -> float:
    ta, tb = tokenize(a), tokenize(b)
    if not ta or not tb:
        return 0.0
    return len(ta & tb) / len(ta | tb)


class TextReader:
    """OCR cho crop logo. backends: none / easyocr / tesseract.
    none → trả "" (kênh text tắt). Cài `pip install easyocr` (hoặc tesseract)
    để bật — đây là kênh tách được logo 'nhìn giống nhưng chữ khác'."""

    def __init__(self, backend: str = "none"):
        self.backend = backend
        self.reader = None
        if backend == "easyocr":
            import easyocr  # type: ignore
            self.reader = easyocr.Reader(["en"], gpu=True)
        elif backend == "tesseract":
            import pytesseract  # type: ignore  # noqa: F401
            self.reader = "tesseract"

    def read(self, rgb: np.ndarray) -> str:
        if self.backend == "none" or rgb.size == 0:
            return ""
        if self.backend == "easyocr":
            return " ".join(self.reader.readtext(rgb, detail=0))
        if self.backend == "tesseract":
            import pytesseract
            return pytesseract.image_to_string(rgb)
        return ""


# --------------------------------------------------------------------------- #
# Embedder (transformers) — nạp trễ
# --------------------------------------------------------------------------- #

class Embedder:
    def __init__(self, model_id: str = "facebook/dinov2-base",
                 device: str | None = None, batch: int = 32):
        import torch
        from transformers import AutoImageProcessor, AutoModel
        self.torch = torch
        self.device = device or ("cuda" if torch.cuda.is_available() else "cpu")
        self.batch = batch
        self.proc = AutoImageProcessor.from_pretrained(model_id)
        self.model = AutoModel.from_pretrained(model_id).to(self.device).eval()
        self.model_id = model_id

    def embed(self, rgb_images: list[np.ndarray]) -> np.ndarray:
        from PIL import Image
        torch = self.torch
        vecs = []
        for i in range(0, len(rgb_images), self.batch):
            chunk = [Image.fromarray(x) for x in rgb_images[i:i + self.batch]]
            inp = self.proc(images=chunk, return_tensors="pt").to(self.device)
            with torch.no_grad():
                out = self.model(**inp)
            feat = out.last_hidden_state[:, 0]               # CLS token
            feat = torch.nn.functional.normalize(feat, dim=-1)
            vecs.append(feat.cpu().numpy().astype(np.float32))
        return np.concatenate(vecs, 0) if vecs else np.zeros((0, 1), np.float32)


# --------------------------------------------------------------------------- #
# Template DB (visual ⊕ color ⊕ text) + fusion
# --------------------------------------------------------------------------- #

class TemplateDB:
    def __init__(self, vecs, brands, paths, model_id="",
                 colors=None, texts=None):
        self.vecs = np.asarray(vecs, np.float32)
        self.brands = list(brands)
        self.paths = list(paths)
        self.model_id = model_id
        self.colors = (np.asarray(colors, np.float32)
                       if colors is not None else None)
        self.texts = list(texts) if texts is not None else None

    def fused_scores(self, qvecs, qcolors=None, qtexts=None,
                     w_color=0.0, w_text=0.0) -> np.ndarray:
        """(M,N) điểm fuse. visual luôn có; color/text cộng nếu bật + có dữ liệu."""
        s = self.vecs @ qvecs.T           # (N, M) visual cosine
        s = s.T.copy()                    # (M, N)
        wsum = np.ones(s.shape)           # trọng số visual = 1
        if w_color and self.colors is not None and qcolors is not None:
            s += w_color * (qcolors @ self.colors.T)
            wsum += w_color
        if w_text and self.texts is not None and qtexts is not None:
            T = np.array([[text_sim(qt, tt) for tt in self.texts]
                          for qt in qtexts], np.float32)
            s += w_text * T
            wsum += w_text
        return s / wsum

    def _groups(self):
        """(brand_order, [index_array]) — gom template theo brand (cache)."""
        if getattr(self, "_grp", None) is None:
            order, idx = [], {}
            for b in self.brands:
                if b not in idx:
                    idx[b] = len(order); order.append(b)
            groups = [[] for _ in order]
            for i, b in enumerate(self.brands):
                groups[idx[b]].append(i)
            self._grp = (order, [np.array(g) for g in groups])
        return self._grp

    def query_batch(self, qvecs, qcolors=None, qtexts=None,
                    w_color=0.0, w_text=0.0, score_mode="cosine"):
        """score_mode:
          - 'cosine': score = cosine fuse của brand gần nhất (thang tuyệt đối).
          - 'margin': score = (top1 − top2) giữa các BRAND → open-set robust hơn,
            không phụ thuộc thang tuyệt đối (logo lạ thường có margin nhỏ)."""
        if len(self.vecs) == 0:
            return [("unknown", 0.0)] * len(qvecs)
        s = self.fused_scores(qvecs, qcolors, qtexts, w_color, w_text)  # (M,N)
        order, groups = self._groups()
        M, B = s.shape[0], len(order)
        brand_max = np.full((M, B), -1e9, np.float32)
        for bi, idxs in enumerate(groups):
            brand_max[:, bi] = s[:, idxs].max(1)
        rank = np.argsort(-brand_max, axis=1)
        out = []
        for i in range(M):
            j1 = rank[i, 0]
            top1 = float(brand_max[i, j1])
            top2 = float(brand_max[i, rank[i, 1]]) if B > 1 else 0.0
            score = top1 if score_mode == "cosine" else (top1 - top2)
            out.append((order[j1], score))
        return out

    def query(self, qvec, **kw):
        return self.query_batch(qvec[None, :], **kw)[0]

    def save(self, p: Path) -> None:
        d = dict(vecs=self.vecs, brands=np.array(self.brands),
                 paths=np.array(self.paths), model_id=self.model_id)
        if self.colors is not None:
            d["colors"] = self.colors
        if self.texts is not None:
            d["texts"] = np.array(self.texts)
        np.savez(p, **d)

    @classmethod
    def load(cls, p: Path) -> "TemplateDB":
        z = np.load(p, allow_pickle=True)
        return cls(z["vecs"], list(z["brands"]), list(z["paths"]),
                   str(z["model_id"]) if "model_id" in z else "",
                   colors=z["colors"] if "colors" in z else None,
                   texts=list(z["texts"]) if "texts" in z else None)

    @property
    def n_brands(self) -> int:
        return len(set(self.brands))


# --------------------------------------------------------------------------- #
# brand key (tái dùng heuristic autolabeler)
# --------------------------------------------------------------------------- #

def _brand_key(name: str) -> str:
    try:
        from sam3_exemplar_autolabel import brand_key_from_filename
        return brand_key_from_filename(name)
    except Exception:
        return Path(name).stem.lower()


# --------------------------------------------------------------------------- #
# build / query
# --------------------------------------------------------------------------- #

def _collect(d: Path, brand_from: str, mask_on: bool, tight: bool,
             text_reader: "TextReader | None"):
    rgbs, colors, texts, brands, paths = [], [], [], [], []
    for p in sorted(d.rglob("*")):
        if p.suffix.lower() not in IMG_EXT:
            continue
        loaded = load_image(p)
        if loaded is None:
            continue
        rgb, mask = loaded
        prepped = prep_for_embed(rgb, mask, tight=tight) if mask_on else rgb
        rgbs.append(prepped)
        colors.append(hue_hist(rgb, mask))
        texts.append(text_reader.read(prepped) if text_reader else "")
        brands.append(_brand_key(p.name) if brand_from == "filename" else p.parent.name)
        paths.append(str(p))
    return rgbs, colors, texts, brands, paths


def cmd_build(a: argparse.Namespace) -> None:
    emb = Embedder(a.model, device=a.device, batch=a.batch)
    tr = TextReader(a.text_backend)
    rgbs, colors, texts, brands, paths = _collect(
        Path(a.logos), "filename", a.mask, a.tight, tr)
    if a.gallery:
        r2, c2, t2, b2, p2 = _collect(Path(a.gallery), "folder", a.mask, a.tight, tr)
        rgbs += r2; colors += c2; texts += t2; brands += b2; paths += p2
    if not rgbs:
        raise SystemExit("Không có ảnh template.")
    vecs = emb.embed(rgbs)
    db = TemplateDB(vecs, brands, paths, model_id=emb.model_id,
                    colors=np.array(colors, np.float32),
                    texts=texts if a.text_backend != "none" else None)
    db.save(Path(a.out))
    print(f"[build] {len(rgbs)} template, {db.n_brands} brand, dim={vecs.shape[1]}, "
          f"mask={a.mask}, text={a.text_backend} → {a.out}")
    print(f"  brands: {', '.join(sorted(set(brands)))}")


def cmd_query(a: argparse.Namespace) -> None:
    db = TemplateDB.load(Path(a.db))
    emb = Embedder(db.model_id or a.model, device=a.device, batch=a.batch)
    tr = TextReader(a.text_backend)
    crops = Path(a.crops)

    ids, gts, rgbs, colors, texts = [], [], [], [], []
    for p in sorted(crops.rglob("*")):
        if p.suffix.lower() not in IMG_EXT:
            continue
        loaded = load_image(p)
        if loaded is None:
            continue
        rgb, mask = loaded
        prepped = prep_for_embed(rgb, mask, tight=a.tight) if a.mask else rgb
        ids.append(f"{p.parent.name}/{p.stem}")
        gts.append(p.parent.name if p.parent != crops else "unknown")
        rgbs.append(prepped); colors.append(hue_hist(rgb, mask))
        texts.append(tr.read(prepped))
    if not ids:
        raise SystemExit(f"Không có crop trong {crops}")

    qv = emb.embed(rgbs)
    res = db.query_batch(qv, np.array(colors, np.float32), texts,
                         w_color=a.w_color, w_text=a.w_text, score_mode=a.score)
    out = Path(a.out); out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w") as f:
        for cid, gt, (pred, score) in zip(ids, gts, res):
            f.write(json.dumps({"id": cid, "gt": gt, "pred": pred,
                                "score": round(score, 4)}, ensure_ascii=False) + "\n")
    print(f"[query] {len(ids)} crop → {out}  "
          f"(mask={a.mask}, w_color={a.w_color}, w_text={a.w_text})")


def cmd_selftest(_a: argparse.Namespace) -> None:
    rng = np.random.default_rng(0)
    base = rng.standard_normal((3, 16)).astype(np.float32)
    base /= np.linalg.norm(base, axis=1, keepdims=True)
    db = TemplateDB(base, ["aon", "toyota", "klg"], ["a", "b", "c"])
    q = base[0] + 0.01 * rng.standard_normal(16).astype(np.float32)
    q /= np.linalg.norm(q)
    assert db.query(q)[0] == "aon"
    # prep: tight-crop + xoá nền
    rgb = np.full((10, 10, 3), 200, np.uint8)
    mask = np.zeros((10, 10), np.uint8); mask[3:6, 4:7] = 1
    out = prep_for_embed(rgb, mask, tight=True, pad=0.0, neutral=255)
    assert out.shape[0] == 3 and out.shape[1] == 3, out.shape
    # text fuse: visual hoà nhau, text quyết định
    V = np.stack([base[0], base[0]])  # 2 template visual giống hệt
    db2 = TemplateDB(V, ["yellow", "paints"], ["1", "2"],
                     texts=["yellow", "paints lacquers"])
    pred, _ = db2.query(base[0], qtexts=["paints lacquers ltd"], w_text=2.0)
    assert pred == "paints", pred
    print("  recognizer selftest: OK ✅")


def main() -> None:
    ap = argparse.ArgumentParser(description="Phase 2 — Tầng 2 Recognizer")
    sub = ap.add_subparsers(dest="cmd", required=True)

    def common(sp):
        sp.add_argument("--model", default="facebook/dinov2-base")
        sp.add_argument("--device", default=None)
        sp.add_argument("--batch", type=int, default=32)
        sp.add_argument("--mask", dest="mask", action="store_true", default=True,
                        help="crop sát + xoá nền theo alpha (mặc định bật)")
        sp.add_argument("--no-mask", dest="mask", action="store_false")
        sp.add_argument("--tight", action="store_true", default=True)
        sp.add_argument("--text-backend", default="none",
                        choices=["none", "easyocr", "tesseract"])

    b = sub.add_parser("build"); common(b)
    b.add_argument("--logos", required=True)
    b.add_argument("--gallery", default=None)
    b.add_argument("--out", required=True)
    b.set_defaults(func=cmd_build)

    q = sub.add_parser("query"); common(q)
    q.add_argument("--db", required=True)
    q.add_argument("--crops", required=True)
    q.add_argument("--out", required=True)
    q.add_argument("--w-color", dest="w_color", type=float, default=0.0)
    q.add_argument("--w-text", dest="w_text", type=float, default=0.0)
    q.add_argument("--score", choices=["cosine", "margin"], default="cosine",
                   help="điểm open-set: cosine (tuyệt đối) | margin (top1-top2)")
    q.set_defaults(func=cmd_query)

    s = sub.add_parser("selftest"); s.set_defaults(func=cmd_selftest)

    a = ap.parse_args()
    a.func(a)


if __name__ == "__main__":
    main()
