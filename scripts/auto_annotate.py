"""
Run PaddleOCR on the sharpest, clearest closeup frames from pipeline output.
Visualises every text detection (with sponsor-match status) so the user can
judge OCR quality before investing in full auto-annotation pipeline.

Usage:
    python scripts/auto_annotate.py
    python scripts/auto_annotate.py --video M06_black_1080p --n 10
    python scripts/auto_annotate.py --min-sharp 60 --min-h 0.50

Output:
    auto_annotate_output/<video_stem>/
        ├── <frame>_ocr.jpg     ← annotated frame: green = matched, yellow = unmatched
        ├── ocr_results.csv     ← all OCR detections with sponsor match
        └── summary.txt         ← precision / recall summary
"""
import argparse
import csv
import json
import sys
from pathlib import Path

import cv2
import numpy as np
from rapidfuzz import process, fuzz


# ── Sponsor dictionary ──────────────────────────────────────────────────────
# Add / edit Bradford-relevant sponsors here. Lowercased keys; canonical names
# in CANONICAL.  Levenshtein fuzzy-match with cutoff handles OCR noise.
SPONSOR_DICT = {
    'klg':     'KLG',
    'aon':     'AON',
    'mcp':     'MCP',
    'bulls':   'BULLS',
    'castore': 'CASTORE',
    'jcb':     'JCB',
    'ronseal': 'RONSEAL',
    'phantom': 'PHANTOM',  # Phantom Bulls TV bug
}
MIN_FUZZY_SCORE = 80  # 0-100, higher = stricter
MIN_OCR_CONF    = 0.55
MIN_TEXT_LEN    = 2


# ── Frame selection ─────────────────────────────────────────────────────────

def pick_sharpest(video_dir: Path, n: int, min_sharp: float, min_h: float) -> list[dict]:
    """Pick the top-N frames by sharpness, restricted to closeups with target_boxes."""
    data = json.loads((video_dir / 'selected.json').read_text())
    qualified = [d for d in data
                 if d['sharp'] >= min_sharp
                 and d['max_target_h'] >= min_h
                 and len(d['target_boxes']) > 0]
    qualified.sort(key=lambda d: -d['sharp'])
    return qualified[:n]


def find_frame_file(video_dir: Path, frame_idx: int) -> Path | None:
    """Locate the saved JPEG for a given frame index."""
    pattern = f'*_f{frame_idx:07d}.jpg'
    matches = list(video_dir.glob(pattern))
    return matches[0] if matches else None


# ── OCR helpers ─────────────────────────────────────────────────────────────

def fuzzy_match_sponsor(text: str) -> tuple[str, int] | None:
    """Match OCR text against sponsor dictionary. Returns (canonical, score) or None."""
    text = text.strip().lower()
    if len(text) < MIN_TEXT_LEN:
        return None
    match = process.extractOne(
        text, SPONSOR_DICT.keys(),
        scorer=fuzz.ratio, score_cutoff=MIN_FUZZY_SCORE,
    )
    if match is None:
        return None
    key, score, _ = match
    return SPONSOR_DICT[key], int(score)


def polygon_to_bbox(poly) -> tuple[int, int, int, int]:
    """Convert 4-point OCR polygon to axis-aligned bbox (x1, y1, x2, y2)."""
    pts = np.asarray(poly, dtype=np.float32).reshape(-1, 2)
    x1, y1 = pts.min(axis=0).astype(int)
    x2, y2 = pts.max(axis=0).astype(int)
    return int(x1), int(y1), int(x2), int(y2)


def expand_bbox(bbox: tuple, expand: float, frame_shape: tuple) -> tuple:
    """Expand bbox by `expand` fraction on each side, clipped to frame."""
    x1, y1, x2, y2 = bbox
    bw, bh = x2 - x1, y2 - y1
    pad_x = int(bw * expand)
    pad_y = int(bh * expand)
    H, W = frame_shape[:2]
    return (max(0, x1 - pad_x), max(0, y1 - pad_y),
            min(W, x2 + pad_x), min(H, y2 + pad_y))


# ── Visualisation ───────────────────────────────────────────────────────────

GREEN  = (0, 255,   0)
YELLOW = (0, 220, 255)
RED    = (0,   0, 255)


def draw_detection(img: np.ndarray, bbox: tuple, label: str, color: tuple) -> None:
    x1, y1, x2, y2 = bbox
    cv2.rectangle(img, (x1, y1), (x2, y2), color, 2)
    (tw, th), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 1)
    cv2.rectangle(img, (x1, max(0, y1 - th - 6)), (x1 + tw + 4, y1), color, -1)
    cv2.putText(img, label, (x1 + 2, y1 - 4),
                cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 0), 1, cv2.LINE_AA)


# ── Main ────────────────────────────────────────────────────────────────────

def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument('--video', default='M06_black_1080p',
                    help='Video stem under pipeline_output/ (default: M06_black_1080p)')
    ap.add_argument('--in-dir', type=Path, default=Path('pipeline_output'))
    ap.add_argument('--out-dir', type=Path, default=Path('auto_annotate_output'))
    ap.add_argument('--n', type=int, default=10,
                    help='Number of sharpest frames to OCR (default 10)')
    ap.add_argument('--min-sharp', type=float, default=50.0,
                    help='Min torso sharpness for frame selection (default 50)')
    ap.add_argument('--min-h', type=float, default=0.45,
                    help='Min max_target_h: only true closeups (default 0.45)')
    ap.add_argument('--expand', type=float, default=0.15,
                    help='Bbox expansion ratio (default 0.15)')
    args = ap.parse_args()

    video_dir = args.in_dir / args.video
    if not video_dir.exists():
        sys.exit(f'No pipeline output at {video_dir}')

    out_dir = args.out_dir / args.video
    out_dir.mkdir(parents=True, exist_ok=True)

    frames = pick_sharpest(video_dir, args.n, args.min_sharp, args.min_h)
    print(f'Picked {len(frames)} sharpest closeup frames from {video_dir}')

    # Lazy import: PaddleOCR is slow to load
    print('Loading PaddleOCR (first run downloads models, ~100MB)...')
    from paddleocr import PaddleOCR
    ocr = PaddleOCR(use_doc_orientation_classify=False,
                    use_doc_unwarping=False,
                    use_textline_orientation=False,
                    lang='en')
    print('  done.\n')

    # Aggregate stats
    rows: list[dict] = []
    n_match = n_unmatch = n_low_conf = 0

    for rec in frames:
        frame_path = find_frame_file(video_dir, rec['frame_idx'])
        if frame_path is None:
            print(f'  ! cannot find image for frame {rec["frame_idx"]}')
            continue
        img = cv2.imread(str(frame_path))
        if img is None:
            continue
        H, W = img.shape[:2]
        vis = img.copy()

        # Run OCR on torso crop of each target player
        # NOTE: target_boxes were computed on original 1080p frame, but the
        # saved JPEG is at display_scale=0.5 (960px wide).  Need to rescale.
        # Original frame size is known from FrameScore? No — we used scale 0.5.
        # Easiest: assume saved image is 0.5× original (true for our pipeline).
        scale = W / 1920.0  # 1080p → 1920 wide; saved at 0.5 → 960 wide

        for tb in rec['target_boxes']:
            x1, y1, x2, y2 = tb
            # Convert original coords to display coords
            x1, y1 = int(x1 * scale), int(y1 * scale)
            x2, y2 = int(x2 * scale), int(y2 * scale)
            bh = y2 - y1
            # Torso ROI = 15-80% of bbox vertically (covers jersey + sleeve)
            ty1 = max(0, y1 + int(0.10 * bh))
            ty2 = min(H, y1 + int(0.75 * bh))
            tx1 = max(0, x1)
            tx2 = min(W, x2)
            torso = img[ty1:ty2, tx1:tx2]
            if torso.size == 0 or min(torso.shape[:2]) < 20:
                continue

            # Upscale torso for OCR (small text is hard otherwise)
            target_h = max(torso.shape[0], 200)
            scale_up = target_h / torso.shape[0]
            torso_up = cv2.resize(torso, None, fx=scale_up, fy=scale_up,
                                  interpolation=cv2.INTER_CUBIC)

            results = ocr.predict(torso_up)
            if not results:
                continue
            res = results[0]
            polys  = res.get('rec_polys', [])
            texts  = res.get('rec_texts', [])
            scores = res.get('rec_scores', [])

            for poly, text, conf in zip(polys, texts, scores):
                if conf < MIN_OCR_CONF:
                    n_low_conf += 1
                    continue
                # Map poly back to display-frame coords
                poly_arr = np.asarray(poly, dtype=np.float32) / scale_up
                poly_arr += np.array([tx1, ty1], dtype=np.float32)
                bbox = polygon_to_bbox(poly_arr)
                bbox = expand_bbox(bbox, args.expand, img.shape)

                match = fuzzy_match_sponsor(text)
                if match:
                    sponsor, score = match
                    label = f'{sponsor} ({text}|{conf:.2f})'
                    draw_detection(vis, bbox, label, GREEN)
                    n_match += 1
                    rows.append(dict(
                        frame=frame_path.name, time_s=rec['time_s'],
                        text=text, sponsor=sponsor, fuzzy=score,
                        ocr_conf=round(conf, 3),
                        bbox=','.join(map(str, bbox)),
                        matched=True,
                    ))
                else:
                    label = f'?{text} ({conf:.2f})'
                    draw_detection(vis, bbox, label, YELLOW)
                    n_unmatch += 1
                    rows.append(dict(
                        frame=frame_path.name, time_s=rec['time_s'],
                        text=text, sponsor='', fuzzy=0,
                        ocr_conf=round(conf, 3),
                        bbox=','.join(map(str, bbox)),
                        matched=False,
                    ))

        out_path = out_dir / f'{frame_path.stem}_ocr.jpg'
        cv2.imwrite(str(out_path), vis, [cv2.IMWRITE_JPEG_QUALITY, 90])
        print(f'  saved {out_path.name}')

    # CSV
    csv_path = out_dir / 'ocr_results.csv'
    with open(csv_path, 'w', newline='') as f:
        if rows:
            w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
            w.writeheader()
            w.writerows(rows)
        else:
            f.write('no detections\n')

    # Summary
    total = n_match + n_unmatch
    summary = (
        f'Frames processed       : {len(frames)}\n'
        f'OCR detections (kept)  : {total}\n'
        f'  matched sponsor      : {n_match}\n'
        f'  unmatched text       : {n_unmatch}\n'
        f'Low-confidence dropped : {n_low_conf}  (<{MIN_OCR_CONF})\n'
        f'Sponsor dictionary     : {sorted(SPONSOR_DICT.values())}\n'
        f'\nMatch precision proxy  : {n_match}/{total} = '
        f'{(n_match/total*100 if total else 0):.0f}%\n'
        f'(Note: this is detection-level, not frame-level. Manual review of\n'
        f' the saved JPEGs gives the real signal.)\n'
    )
    (out_dir / 'summary.txt').write_text(summary)
    print('\n' + summary)
    print(f'Output → {out_dir}/')


if __name__ == '__main__':
    main()
