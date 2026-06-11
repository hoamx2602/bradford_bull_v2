"""Audio muxing for rendered output videos."""
from __future__ import annotations

import subprocess

import pytest

from app.pipeline.av import _ffmpeg_exe, _has_audio, mux_audio

ffmpeg = _ffmpeg_exe()
needs_ffmpeg = pytest.mark.skipif(ffmpeg is None, reason="ffmpeg not available")


@pytest.fixture()
def silent_video(tmp_path):
    """1s test video WITHOUT audio."""
    p = tmp_path / "silent.mp4"
    subprocess.run(
        [ffmpeg, "-y", "-hide_banner", "-loglevel", "error",
         "-f", "lavfi", "-i", "testsrc=duration=1:size=64x64:rate=10",
         "-pix_fmt", "yuv420p", str(p)],
        check=True,
    )
    return p


@pytest.fixture()
def sound_video(tmp_path):
    """1s test video WITH a sine audio track (like a real broadcast upload)."""
    p = tmp_path / "sound.mp4"
    subprocess.run(
        [ffmpeg, "-y", "-hide_banner", "-loglevel", "error",
         "-f", "lavfi", "-i", "testsrc=duration=1:size=64x64:rate=10",
         "-f", "lavfi", "-i", "sine=frequency=440:duration=1",
         "-c:a", "aac", "-pix_fmt", "yuv420p", "-shortest", str(p)],
        check=True,
    )
    return p


@needs_ffmpeg
def test_has_audio_detection(silent_video, sound_video):
    assert _has_audio(sound_video, ffmpeg) is True
    assert _has_audio(silent_video, ffmpeg) is False


@needs_ffmpeg
def test_mux_copies_audio_from_source(silent_video, sound_video, tmp_path):
    # silent_video plays the role of the OpenCV-rendered preview;
    # sound_video is the original upload whose audio must be restored.
    out = tmp_path / "muxed.mp4"
    result = mux_audio(silent_video, sound_video, out)
    assert result == out and out.exists()
    assert _has_audio(out, ffmpeg) is True


@needs_ffmpeg
def test_mux_noop_when_source_silent(silent_video, tmp_path):
    out = tmp_path / "muxed.mp4"
    result = mux_audio(silent_video, silent_video, out)
    # No audio in the source -> keep the video-only file untouched.
    assert result == silent_video
    assert not out.exists()
