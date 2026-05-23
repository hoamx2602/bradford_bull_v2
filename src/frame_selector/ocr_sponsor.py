"""Shared OCR + sponsor-matching utilities.

Wraps PaddleOCR and a fuzzy sponsor dictionary so both the auto-annotation
prototype and the production exposure aggregator use identical logic.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from rapidfuzz import process, fuzz


# ── Sponsor dictionary ──────────────────────────────────────────────────────
# Lowercased OCR-text keys → canonical sponsor name. Fuzzy match tolerates
# OCR noise (e.g. 'KLC' → 'KLG', 'A0N' → 'AON').
#
# Built from Bradford Bulls 2025/26 Home + Away kit and the official Sponsor Logo
# pack. Each sponsor may emit several OCR tokens (multi-word logos, abbreviations)
# so we map every likely-detected token to one canonical name.
#
# NOTE — logos that OCR will struggle with (symbol/cursive, handle via YOLO/template):
#   • EM workwear      — monogram inside laurel wreath
#   • Paints & Lacquers — heavy cursive script
#   • acs group        — stylised lowercase + triangle mark
#   • Bull crest        — pure graphic
SPONSOR_DICT: dict[str, str] = {
    # Main jersey sponsors  (fragments + concatenated forms — OCR does both)
    'topnotch':  'TOPNOTCH',     'top notch': 'TOPNOTCH', 'notch': 'TOPNOTCH',
    'floor':     'FLOOR TONIC',  'tonic':     'FLOOR TONIC', 'floortonic': 'FLOOR TONIC',
    'klg':       'KLG',          'klg europe': 'KLG',     'klgeurope': 'KLG',
    'aon':       'AON',
    'mcp':       'MCP',
    'fairway':   'FAIRWAY',
    'acs':       'ACS GROUP',     'acs group': 'ACS GROUP', 'acsgroup': 'ACS GROUP',
    # Shoulder / chest / collar
    'mna':       'MNA',          'cladding':  'MNA',
    'bartercard':'BARTERCARD',   'barte':     'BARTERCARD',
    'romantica': 'ROMANTICA',    'domantica': 'ROMANTICA',
    'chadwick':  'CHADWICK',     'chadlaw':   'CHADWICK',
    'atm':       'ATM',
    # Shorts / hotel
    'cch':       'CEDAR COURT',  'cedar court': 'CEDAR COURT', 'cedarcourt': 'CEDAR COURT',
    # Manufacturer / kit brand
    'ellgren':   'ELLGREN',
    'fourex':    'FOUREX',
    # Team mark (text)
    'bulls':     'BULLS',
}

MIN_FUZZY_SCORE = 80   # 0-100, higher = stricter
MIN_OCR_CONF    = 0.55
MIN_TEXT_LEN    = 2


@dataclass
class Detection:
    """One sponsor detection in one frame."""
    sponsor: str
    text: str          # raw OCR text
    conf: float        # OCR confidence
    fuzzy: int         # fuzzy match score
    bbox: tuple        # (x1, y1, x2, y2) in frame coords
    area_pct: float    # bbox area / frame area * 100
    cx: float          # bbox center x (normalised 0-1)
    cy: float          # bbox center y (normalised 0-1)


# Common OCR character confusions → fold digits/symbols back to letters.
_OCR_FIX = str.maketrans({'0': 'o', '1': 'i', '|': 'i', '5': 's', '8': 'b'})

# Despaced keys let concatenated OCR ('floortonic') match multi-word logos ('floor tonic').
_DESPACED_DICT: dict[str, str] = {
    k.replace(' ', ''): v for k, v in SPONSOR_DICT.items()
}


def _normalize(text: str) -> str:
    return text.strip().lower().translate(_OCR_FIX)


def fuzzy_match_sponsor(text: str) -> tuple[str, int] | None:
    """Match OCR text against the sponsor dictionary. Returns (canonical, score) or None.

    Robust to OCR digit/letter confusion (0→o, 1→i, ...) and to multi-word logos
    that OCR concatenates ('floortonic' → 'FLOOR TONIC').
    """
    t = _normalize(text)
    if len(t) < MIN_TEXT_LEN:
        return None

    best: tuple[str, int] | None = None
    for table in (SPONSOR_DICT, _DESPACED_DICT):
        m = process.extractOne(
            t, table.keys(),
            scorer=fuzz.ratio, score_cutoff=MIN_FUZZY_SCORE,
        )
        if m is not None:
            key, score, _ = m
            if best is None or score > best[1]:
                best = (table[key], int(score))
    return best


def polygon_to_bbox(poly) -> tuple[int, int, int, int]:
    """Convert a 4-point OCR polygon to an axis-aligned bbox."""
    pts = np.asarray(poly, dtype=np.float32).reshape(-1, 2)
    x1, y1 = pts.min(axis=0).astype(int)
    x2, y2 = pts.max(axis=0).astype(int)
    return int(x1), int(y1), int(x2), int(y2)


def expand_bbox(bbox: tuple, expand: float, frame_shape: tuple) -> tuple:
    """Expand a bbox by `expand` fraction on each side, clipped to frame bounds."""
    x1, y1, x2, y2 = bbox
    bw, bh = x2 - x1, y2 - y1
    px, py = int(bw * expand), int(bh * expand)
    H, W = frame_shape[:2]
    return (max(0, x1 - px), max(0, y1 - py),
            min(W, x2 + px), min(H, y2 + py))


class SponsorOCR:
    """Lazy PaddleOCR wrapper that returns canonical sponsor Detections."""

    def __init__(
        self,
        lang: str = 'en',
        min_conf: float = MIN_OCR_CONF,
        device: str | None = None,
    ) -> None:
        """device: 'gpu' / 'cpu' / None (auto-detect via paddle.is_compiled_with_cuda)."""
        from paddleocr import PaddleOCR
        if device is None:
            try:
                import paddle
                device = 'gpu' if paddle.is_compiled_with_cuda() else 'cpu'
            except Exception:
                device = 'cpu'
        self.device = device
        self.ocr = PaddleOCR(
            use_doc_orientation_classify=False,
            use_doc_unwarping=False,
            use_textline_orientation=False,
            lang=lang,
            device=device,
        )
        self.min_conf = min_conf

    def read(
        self,
        crop_bgr: np.ndarray,
        frame_shape: tuple,
        offset: tuple[int, int] = (0, 0),
        upscale_to: int = 200,
        expand: float = 0.15,
        matched_only: bool = True,
    ) -> list[Detection]:
        """Run OCR on a crop and return sponsor detections in FRAME coordinates.

        offset       — (x, y) of crop's top-left in the full frame.
        upscale_to   — min crop height before OCR (small text needs upscaling).
        matched_only — if True, drop OCR text that doesn't match a sponsor.
        """
        if crop_bgr.size == 0 or min(crop_bgr.shape[:2]) < 10:
            return []

        import cv2
        scale_up = max(1.0, upscale_to / crop_bgr.shape[0])
        if scale_up > 1.0:
            crop_bgr = cv2.resize(crop_bgr, None, fx=scale_up, fy=scale_up,
                                  interpolation=cv2.INTER_CUBIC)

        results = self.ocr.predict(crop_bgr)
        if not results:
            return []
        res = results[0]
        polys  = res.get('rec_polys', [])
        texts  = res.get('rec_texts', [])
        scores = res.get('rec_scores', [])

        H, W = frame_shape[:2]
        frame_area = float(H * W)
        ox, oy = offset
        out: list[Detection] = []

        for poly, text, conf in zip(polys, texts, scores):
            if conf < self.min_conf:
                continue
            match = fuzzy_match_sponsor(text)
            if match is None and matched_only:
                continue

            poly_arr = np.asarray(poly, dtype=np.float32) / scale_up
            poly_arr += np.array([ox, oy], dtype=np.float32)
            bbox = expand_bbox(polygon_to_bbox(poly_arr), expand, frame_shape)
            x1, y1, x2, y2 = bbox
            area_pct = (x2 - x1) * (y2 - y1) / frame_area * 100.0

            sponsor, fscore = match if match else ('', 0)
            out.append(Detection(
                sponsor=sponsor, text=text, conf=float(conf), fuzzy=fscore,
                bbox=bbox, area_pct=area_pct,
                cx=(x1 + x2) / 2 / W, cy=(y1 + y2) / 2 / H,
            ))
        return out
