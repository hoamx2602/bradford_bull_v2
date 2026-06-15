"""Team-detection overlay video.

Renders what the team filter "sees": every tracked person gets a box coloured
by their voted team — TARGET (Bradford kit) vs OTHER (opponents / refs) — plus
the persistent track id and the vote state. It runs the SAME TeamTracker stack
the logo filter uses (YOLO person model + BoT-SORT + colour/SigLIP voting), but
on every native frame so the boxes are smooth, making the filter's behaviour
inspectable on its own instead of only as kept/dropped logo counts.
"""
from __future__ import annotations

import logging
from pathlib import Path

import cv2

from app.pipeline.teamid.classifier import TARGET
from app.pipeline.teamid.tracker import TeamTracker, TrackedPerson

log = logging.getLogger("app.teamid")

# BGR box colours per state.
_C_TARGET = (10, 190, 255)    # Bradford amber/gold
_C_OTHER = (170, 170, 170)    # grey
_C_PENDING = (210, 160, 60)   # steel blue — not enough votes yet


def _open_writer(path: Path, fps: float, size: tuple[int, int]) -> cv2.VideoWriter | None:
    for codec in ("avc1", "mp4v"):
        w = cv2.VideoWriter(str(path), cv2.VideoWriter_fourcc(*codec), fps, size)
        if w.isOpened():
            if codec != "avc1":
                log.warning("teamdet: H.264 unavailable, using %s", codec)
            return w
    return None


def _style(p: TrackedPerson, min_votes: float) -> tuple[tuple[int, int, int], str]:
    # Below the vote floor the label is a default, not a decision — claim
    # nothing rather than flash "TARGET?" at half the field on early frames.
    if p.vote_mass < min_votes:
        return _C_PENDING, "?"
    if p.team == TARGET:
        return _C_TARGET, "TARGET"
    return _C_OTHER, "OTHER"


def _draw(img, persons: list[TrackedPerson], sx: float, sy: float, min_votes: float) -> None:
    for p in persons:
        x1, y1 = int(p.xyxy[0] * sx), int(p.xyxy[1] * sy)
        x2, y2 = int(p.xyxy[2] * sx), int(p.xyxy[3] * sy)
        color, tag = _style(p, min_votes)
        thick = 2 if tag == "TARGET" else 1
        cv2.rectangle(img, (x1, y1), (x2, y2), color, thick)

        label = f"#{p.track_id} {tag}" if p.track_id >= 0 else tag
        (tw, th), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.45, 1)
        ty = y1 - 4 if y1 - th - 8 > 0 else y2 + th + 6
        cv2.rectangle(img, (x1, ty - th - 4), (x1 + tw + 6, ty + 3), color, -1)
        cv2.putText(img, label, (x1 + 3, ty), cv2.FONT_HERSHEY_SIMPLEX, 0.45,
                    (20, 20, 20), 1, cv2.LINE_AA)

    # Legend (top-left).
    for i, (c, txt) in enumerate(
        [(_C_TARGET, "TARGET team"), (_C_OTHER, "Other / refs"), (_C_PENDING, "Undecided")]
    ):
        y = 22 + 22 * i
        cv2.rectangle(img, (12, y - 11), (26, y + 3), c, -1)
        cv2.putText(img, txt, (32, y), cv2.FONT_HERSHEY_SIMPLEX, 0.45,
                    (255, 255, 255), 1, cv2.LINE_AA)


def render_teamdet_video(
    video_path: Path,
    tracker: TeamTracker,
    src_fps: float,
    width: int,
    height: int,
    out_path: Path,
    *,
    max_frames: int,
    max_width: int,
) -> tuple[Path | None, dict]:
    """Write the team-detection overlay video. Returns (path, stats)."""
    if src_fps <= 0 or width <= 0 or height <= 0:
        return None, {}

    scale = min(1.0, max_width / width)
    ow, oh = int(round(width * scale)), int(round(height * scale))
    ow -= ow % 2
    oh -= oh % 2
    size = (max(2, ow), max(2, oh))
    sx, sy = size[0] / width, size[1] / height

    writer = _open_writer(out_path, max(1.0, src_fps), size)
    if writer is None:
        return None, {}
    cap = cv2.VideoCapture(str(video_path))
    if not cap.isOpened():
        writer.release()
        return None, {}

    # The person model is shared with the sampled analytics pass; reset BoT-SORT
    # so this fresh pass over the same footage doesn't resume stale tracks.
    try:
        for t in tracker.person_model.predictor.trackers:
            t.reset()
    except Exception:
        pass

    min_votes = tracker.settings.team_min_votes
    track_team: dict[int, str] = {}
    written = 0
    try:
        while written < max_frames:
            ok, frame = cap.read()
            if not ok:
                break
            persons = tracker.process(frame)
            for p in persons:
                if p.track_id >= 0 and p.vote_mass >= min_votes:
                    track_team[p.track_id] = p.team
            img = cv2.resize(frame, size) if scale != 1.0 else frame
            _draw(img, persons, sx, sy, min_votes)
            writer.write(img)
            written += 1
    finally:
        cap.release()
        writer.release()

    if written == 0:
        out_path.unlink(missing_ok=True)
        return None, {}

    stats = {
        "frames": written,
        "targetTracks": sum(1 for t in track_team.values() if t == TARGET),
        "otherTracks": sum(1 for t in track_team.values() if t != TARGET),
    }
    return out_path, stats
