"""Cinematic demo renderer for the LogoLense marketing video.

Produces a single annotated clip that BUILDS THE PIPELINE UP IN LAYERS on top of
the original footage — exactly the "cumulative overlay" used in section 5 of the
demo-video script:

    raw video -> + player detection -> + tracking IDs -> + logo boxes
              -> + per-logo visibility score + live analytics HUD

Each layer is revealed after a configurable delay (``--reveal``) so the viewer
sees the system reason about the frame one stage at a time, then everything
stays on for the rest of the clip. Pass ``--no-reveal`` to draw every layer from
frame 1 (useful for B-roll where you cut between several short takes).

This reuses the real pipeline models (same weights the analytics run uses), so
the footage is genuine system output, not a mock-up:

    * player boxes  -> YOLO11-pose (app.pipeline.pose.PoseEstimator)
    * logo boxes/IDs-> fine-tuned YOLO26m / RF-DETR with ByteTrack
                       (app.pipeline.detect_track.LogoDetector)
    * visibility    -> Size x Position x Clarity (app.pipeline.visibility)

Run from the backend/ dir inside the logo conda env, e.g.:

    conda run -n bradford_bulls_logo python scripts/render_demo.py \
        --input data/uploads/match.mp4 --output demo_out.mp4 \
        --max-seconds 25 --reveal 3
"""
from __future__ import annotations

import argparse
import time
from pathlib import Path

import cv2

# --- repo imports (run from backend/) ------------------------------------
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.pipeline import visibility  # noqa: E402
from app.pipeline.colors import brand_bgr  # noqa: E402
from app.pipeline.datatypes import Detection  # noqa: E402

# Stage labels shown in the HUD chip as each layer comes online.
STAGES = [
    "INPUT VIDEO",
    "PLAYER DETECTION",
    "MULTI-OBJECT TRACKING",
    "LOGO DETECTION",
    "VISIBILITY ANALYTICS",
]

WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
ACCENT = (60, 180, 255)   # Bradford amber-ish (BGR)
PLAYER_CLR = (200, 200, 200)


def _panel(img, x1, y1, x2, y2, alpha=0.55, color=BLACK) -> None:
    """Draw a translucent rounded-ish panel in place."""
    x1, y1 = max(0, x1), max(0, y1)
    x2, y2 = min(img.shape[1], x2), min(img.shape[0], y2)
    if x2 <= x1 or y2 <= y1:
        return
    roi = img[y1:y2, x1:x2]
    overlay = roi.copy()
    overlay[:] = color
    cv2.addWeighted(overlay, alpha, roi, 1 - alpha, 0, roi)


def _text(img, s, org, scale=0.55, color=WHITE, thick=1, shadow=True):
    if shadow:
        cv2.putText(img, s, (org[0] + 1, org[1] + 1), cv2.FONT_HERSHEY_SIMPLEX,
                    scale, BLACK, thick + 2, cv2.LINE_AA)
    cv2.putText(img, s, org, cv2.FONT_HERSHEY_SIMPLEX, scale, color, thick, cv2.LINE_AA)


def _draw_players(img, persons, scale: float) -> None:
    for p in persons:
        x1, y1, x2, y2 = (int(v * scale) for v in p.xyxy)
        cv2.rectangle(img, (x1, y1), (x2, y2), PLAYER_CLR, 1)
        _text(img, "Player", (x1, y1 - 4), scale=0.4, color=PLAYER_CLR)


def _draw_logos(img, dets: list[Detection], scale: float, *,
                show_track: bool, show_vis: bool) -> None:
    for d in dets:
        x1, y1, x2, y2 = (int(v * scale) for v in d.xyxy)
        color = brand_bgr(d.brand_key)
        cv2.rectangle(img, (x1, y1), (x2, y2), color, 2)

        bits = [d.brand_name, f"{d.conf:.0%}"]
        if show_track and d.track_id >= 0:
            bits.append(f"ID{d.track_id}")
        label = "  ".join(bits)
        (tw, th), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.45, 1)
        _panel(img, x1, y1 - th - 8, x1 + tw + 8, y1, alpha=0.75, color=color)
        _text(img, label, (x1 + 4, y1 - 5), scale=0.45, color=BLACK, shadow=False)

        if show_vis:
            # little visibility bar under the box
            bw = x2 - x1
            vfrac = max(0.0, min(1.0, d.visibility / 0.5))  # 0.5 ~ very visible
            cv2.rectangle(img, (x1, y2 + 3), (x2, y2 + 9), (40, 40, 40), -1)
            cv2.rectangle(img, (x1, y2 + 3), (x1 + int(bw * vfrac), y2 + 9), color, -1)
            _text(img, f"vis {d.visibility:.0%}", (x1, y2 + 22), scale=0.4, color=color)


def _draw_hud(img, *, stage: str, t: float, n_frames: int, brands: set[str],
              top_vis: float, reveal_idx: int) -> None:
    h, w = img.shape[:2]
    # top bar
    _panel(img, 0, 0, w, 46, alpha=0.5)
    _text(img, "LogoLense", (16, 30), scale=0.8, color=WHITE, thick=2)
    # stage chip
    chip = f"  {stage}  "
    (cw, _), _ = cv2.getTextSize(chip, cv2.FONT_HERSHEY_SIMPLEX, 0.55, 1)
    _panel(img, w - cw - 24, 10, w - 12, 36, alpha=0.85, color=ACCENT)
    _text(img, stage, (w - cw - 16, 28), scale=0.55, color=BLACK, shadow=False)

    # pipeline progress dots
    for i, s in enumerate(STAGES):
        cx = 16 + i * 26
        on = i <= reveal_idx
        cv2.circle(img, (cx, h - 18), 6, ACCENT if on else (90, 90, 90), -1)

    # bottom-left stats panel
    _panel(img, 0, h - 78, 250, h - 30, alpha=0.5)
    _text(img, f"t = {t:5.1f}s   frame {n_frames}", (12, h - 56), scale=0.5)
    _text(img, f"brands seen: {len(brands)}", (12, h - 38), scale=0.5, color=ACCENT)
    if top_vis > 0:
        _text(img, f"peak visibility: {top_vis:.0%}", (w - 230, h - 38),
              scale=0.5, color=ACCENT)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--input", required=True, type=Path)
    ap.add_argument("--output", required=True, type=Path)
    ap.add_argument("--max-seconds", type=float, default=25.0,
                    help="trim the clip to this many seconds")
    ap.add_argument("--max-width", type=int, default=1280)
    ap.add_argument("--reveal", type=float, default=3.0,
                    help="seconds between each layer turning on (0 = all at once)")
    ap.add_argument("--no-reveal", action="store_true",
                    help="draw every layer from frame 1")
    ap.add_argument("--no-pose", action="store_true",
                    help="skip player-detection layer (faster)")
    args = ap.parse_args()

    from app.pipeline.detect_track import LogoDetector
    detector = LogoDetector()
    poser = None
    if not args.no_pose:
        from app.pipeline.pose import PoseEstimator
        poser = PoseEstimator()

    cap = cv2.VideoCapture(str(args.input))
    if not cap.isOpened():
        raise SystemExit(f"cannot open {args.input}")
    fps = cap.get(cv2.CAP_PROP_FPS) or 25.0
    W = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    H = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

    scale = min(1.0, args.max_width / W)
    ow, oh = int(W * scale) & ~1, int(H * scale) & ~1
    fourcc = cv2.VideoWriter_fourcc(*"avc1")
    writer = cv2.VideoWriter(str(args.output), fourcc, fps, (ow, oh))
    if not writer.isOpened():
        writer = cv2.VideoWriter(str(args.output),
                                 cv2.VideoWriter_fourcc(*"mp4v"), fps, (ow, oh))

    reveal = 0.0 if args.no_reveal else args.reveal
    brands: set[str] = set()
    peak_vis = 0.0
    i = 0
    t0 = time.time()
    while True:
        ok, frame = cap.read()
        if not ok:
            break
        t = i / fps
        if t > args.max_seconds:
            break

        # which layers are live at this timestamp
        reveal_idx = len(STAGES) - 1 if reveal == 0 else min(len(STAGES) - 1, int(t // reveal))
        show_players = reveal_idx >= 1 and poser is not None
        show_track = reveal_idx >= 2
        show_logos = reveal_idx >= 3
        show_vis = reveal_idx >= 4

        dets = detector.infer(frame, t)
        visibility.annotate(dets)
        for d in dets:
            brands.add(d.brand_key)
            peak_vis = max(peak_vis, d.visibility)

        img = cv2.resize(frame, (ow, oh)) if scale != 1.0 else frame

        if show_players:
            _draw_players(img, poser.infer(frame), scale)
        if show_logos:
            _draw_logos(img, dets, scale, show_track=show_track, show_vis=show_vis)

        _draw_hud(img, stage=STAGES[reveal_idx], t=t, n_frames=i, brands=brands,
                  top_vis=peak_vis, reveal_idx=reveal_idx)
        writer.write(img)

        i += 1
        if i % 30 == 0:
            print(f"  {t:5.1f}s  ({i} frames, {len(brands)} brands)  "
                  f"{i / (time.time() - t0):.1f} fps", flush=True)

    cap.release()
    writer.release()
    print(f"done -> {args.output}  ({i} frames, brands={sorted(brands)})")
    print("tip: remux original audio with:")
    print(f"  ffmpeg -i {args.output} -i {args.input} -map 0:v -map 1:a "
          f"-c:v copy -shortest {args.output.with_name(args.output.stem + '_audio.mp4')}")


if __name__ == "__main__":
    main()
