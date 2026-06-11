"""Test config: point DB + storage at a throwaway temp dir before app import."""
from __future__ import annotations

import os
import tempfile
from pathlib import Path

# Must be set before app.config.get_settings() is first cached.
_TMP = Path(tempfile.mkdtemp(prefix="logoapi_test_"))
os.environ.setdefault("DB_URL", f"sqlite:///{(_TMP / 'test.db').as_posix()}")
os.environ.setdefault("STORAGE_DIR", str(_TMP / "uploads"))
os.environ.setdefault("SAMPLE_FPS", "2")
os.environ.setdefault("IMGSZ", "640")        # fast for the smoke test
os.environ.setdefault("ENABLE_POSE", "false")  # skip pose for the HTTP smoke test
os.environ.setdefault("ENABLE_BODYSEG", "false")  # skip heavy DensePose in tests

import cv2  # noqa: E402
import numpy as np  # noqa: E402
import pytest  # noqa: E402


@pytest.fixture(scope="session")
def synthetic_video() -> Path:
    """A tiny valid mp4 (no logos) — exercises the full HTTP/job flow cheaply."""
    path = _TMP / "synthetic.mp4"
    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    writer = cv2.VideoWriter(str(path), fourcc, 10.0, (64, 64))
    for i in range(20):  # 2 seconds at 10 fps
        frame = np.full((64, 64, 3), i * 5 % 255, dtype=np.uint8)
        writer.write(frame)
    writer.release()
    assert path.exists() and path.stat().st_size > 0
    return path
