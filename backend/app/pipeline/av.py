"""Finalise rendered output videos (preview / body-seg overlay / team-det).

Two jobs, both via ffmpeg:
  1. Ensure the video stream is browser-playable **H.264**. OpenCV's VideoWriter
     falls back to the `mp4v` (MPEG-4 Part 2) codec whenever it can't load an
     H.264 encoder — e.g. in the `rfdetr` conda env, whose OpenCV lacks the
     OpenH264 DLL. Browsers can't decode mp4v in <video>, so the player shows a
     BLACK picture even though the file plays/seeks. We transcode such files to
     H.264; files already H.264 are stream-copied (no re-encode).
  2. Mux the ORIGINAL upload's audio back in (VideoWriter output is video-only).

ffmpeg resolution order: system PATH, then the binary bundled by the
`imageio-ffmpeg` pip package (so Windows works without a manual ffmpeg install).
Everything degrades gracefully: no ffmpeg / silent source / mux failure simply
keeps the rendered file as-is.
"""
from __future__ import annotations

import logging
import shutil
import subprocess
from pathlib import Path

log = logging.getLogger("app.pipeline")


def _ffmpeg_exe() -> str | None:
    exe = shutil.which("ffmpeg")
    if exe:
        return exe
    try:
        import imageio_ffmpeg

        return imageio_ffmpeg.get_ffmpeg_exe()
    except Exception:
        return None


def _probe(src: Path, ffmpeg: str) -> str:
    """Return ffmpeg's stream-info text (on stderr) for `src`, or '' on error."""
    try:
        proc = subprocess.run(
            [ffmpeg, "-hide_banner", "-i", str(src)],
            capture_output=True, text=True, timeout=30,
        )
    except Exception:
        return ""
    return proc.stderr or ""


def _has_audio(src: Path, ffmpeg: str) -> bool:
    return "Audio:" in _probe(src, ffmpeg)


def _is_h264(src: Path, ffmpeg: str) -> bool:
    return "Video: h264" in _probe(src, ffmpeg)


def mux_audio(video_only: Path, audio_source: Path, out_path: Path) -> Path:
    """Ensure `video_only` is H.264 and carry over `audio_source`'s audio.

    Returns the finalised file, or `video_only` unchanged when there's nothing to
    do (already H.264 + silent source), no ffmpeg, or the ffmpeg call fails.
    `-shortest` trims audio to the rendered length (previews are capped shorter
    than the full match).
    """
    ffmpeg = _ffmpeg_exe()
    if ffmpeg is None:
        log.info("video finalise skipped: ffmpeg not found (pip install imageio-ffmpeg)")
        return video_only

    need_transcode = not _is_h264(video_only, ffmpeg)
    has_audio = _has_audio(audio_source, ffmpeg)
    if not need_transcode and not has_audio:
        return video_only  # already browser-friendly and silent — leave as-is

    cmd = [ffmpeg, "-y", "-hide_banner", "-loglevel", "error", "-i", str(video_only)]
    if has_audio:
        cmd += ["-i", str(audio_source), "-map", "0:v:0", "-map", "1:a:0"]
    else:
        cmd += ["-map", "0:v:0"]
    if need_transcode:
        cmd += ["-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "23", "-preset", "veryfast"]
    else:
        cmd += ["-c:v", "copy"]
    if has_audio:
        cmd += ["-c:a", "aac", "-b:a", "128k", "-shortest"]
    cmd += ["-movflags", "+faststart", str(out_path)]

    try:
        subprocess.run(cmd, check=True, capture_output=True, timeout=600)
    except Exception as exc:
        log.warning("video finalise failed (%s) — keeping rendered file", exc)
        out_path.unlink(missing_ok=True)
        return video_only
    return out_path
