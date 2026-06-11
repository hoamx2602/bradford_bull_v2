"""Audio muxing for rendered output videos (preview / body-seg overlay).

OpenCV's VideoWriter is video-only, so every rendered output would lose the
source's audio track. After rendering we COPY the video stream and mux the
ORIGINAL upload's audio back in with ffmpeg.

ffmpeg resolution order: system PATH, then the binary bundled by the
`imageio-ffmpeg` pip package (so Windows works without a manual ffmpeg
install). Everything degrades gracefully: no ffmpeg / silent source / mux
failure simply keeps the video-only file.
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


def _has_audio(src: Path, ffmpeg: str) -> bool:
    """True if the file has at least one audio stream (parsed from ffmpeg -i)."""
    try:
        proc = subprocess.run(
            [ffmpeg, "-hide_banner", "-i", str(src)],
            capture_output=True, text=True, timeout=30,
        )
    except Exception:
        return False
    # ffmpeg exits non-zero for "-i without output", stream info is on stderr.
    return "Audio:" in (proc.stderr or "")


def mux_audio(video_only: Path, audio_source: Path, out_path: Path) -> Path:
    """Mux `audio_source`'s audio onto `video_only` (video stream copied).

    Returns the muxed file, or `video_only` unchanged when there is no ffmpeg,
    no audio in the source, or the mux fails. `-shortest` trims the audio to
    the rendered length (previews are capped shorter than the full match).
    """
    ffmpeg = _ffmpeg_exe()
    if ffmpeg is None:
        log.info("audio mux skipped: ffmpeg not found (pip install imageio-ffmpeg)")
        return video_only
    if not _has_audio(audio_source, ffmpeg):
        return video_only

    cmd = [
        ffmpeg, "-y", "-hide_banner", "-loglevel", "error",
        "-i", str(video_only),
        "-i", str(audio_source),
        "-map", "0:v:0", "-map", "1:a:0",
        "-c:v", "copy",
        "-c:a", "aac", "-b:a", "128k",
        "-shortest",
        "-movflags", "+faststart",
        str(out_path),
    ]
    try:
        subprocess.run(cmd, check=True, capture_output=True, timeout=600)
    except Exception as exc:
        log.warning("audio mux failed (%s) — keeping silent video", exc)
        out_path.unlink(missing_ok=True)
        return video_only
    return out_path
