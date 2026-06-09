"""Central runtime configuration.

Every tunable lives here so the pipeline code never hard-codes a path, threshold,
or infrastructure choice. Swapping to the full production stack later means
changing env vars (DB_URL, STORAGE_BACKEND, QUEUE_BACKEND) — not editing logic.
"""
from __future__ import annotations

import re
from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

# backend/ root (this file is backend/app/config.py)
BACKEND_DIR = Path(__file__).resolve().parent.parent
REPO_ROOT = BACKEND_DIR.parent


def _default_logo_model() -> str:
    """Resolve the newest fine-tuned logo weights under logo_detection/runs/*.

    The user retrains the same model at different sizes, so we pick the latest
    `best.pt` rather than pinning one run. Overridable via MODEL_PATH.
    """
    runs = REPO_ROOT / "logo_detection" / "runs"
    candidates = sorted(runs.glob("*/weights/best.pt"), key=lambda p: p.stat().st_mtime)
    if candidates:
        return str(candidates[-1])
    return str(runs / "logo_yolo26m" / "weights" / "best.pt")


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(BACKEND_DIR / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # ── Service ──────────────────────────────────────────────────────────
    app_name: str = "Logo Analytics API"
    cors_origins: str = "http://localhost:3000,http://127.0.0.1:3000"

    # ── Storage (swap STORAGE_BACKEND=s3 + add storage/s3.py later) ──────
    storage_backend: str = "local"
    storage_dir: Path = BACKEND_DIR / "data" / "uploads"

    # ── Database (swap DB_URL -> postgresql+psycopg://... later) ─────────
    db_url: str = f"sqlite:///{(BACKEND_DIR / 'data' / 'app.db').as_posix()}"

    # ── Queue (swap QUEUE_BACKEND=celery + add jobs/celery_app.py later) ─
    queue_backend: str = "inprocess"
    worker_concurrency: int = 1

    # ── Models ───────────────────────────────────────────────────────────
    model_path: str = ""            # filled by _default_logo_model() if empty
    # Pose model is a SEPARATE stock checkpoint used only for body-zone
    # attribution — the fine-tuned logo model is detect-only and can't produce
    # human keypoints. YOLO26 has no pose variant yet, so we use YOLO11-pose
    # (newest available generation). Bump to yolo11m/x-pose.pt for better zones.
    pose_model: str = "yolo11n-pose.pt"   # auto-downloaded by ultralytics
    device: str = "auto"            # auto | cpu | mps | cuda | 0

    # ── Inference / sampling ─────────────────────────────────────────────
    sample_fps: float = 2.0         # frames analysed per second of video
    imgsz: int = 1280               # model was trained at 1280; lower for speed
    conf: float = 0.25              # detection confidence floor
    iou: float = 0.5
    tracker: str = "bytetrack.yaml"
    enable_pose: bool = True        # body-zone attribution

    # ── Annotated preview video ──────────────────────────────────────────
    preview_enabled: bool = True
    preview_width: int = 960        # downscale preview frames to this width
    # Preview is rendered at the video's native fps (smooth, boxes interpolated
    # between sampled detections). Cap total output frames so a long match
    # doesn't blow up file size — 1800 native frames ≈ 60–72s of footage.
    preview_max_frames: int = 1800

    # ── Upload limits ────────────────────────────────────────────────────
    max_upload_mb: int = 2048
    allowed_ext: str = ".mp4,.mov,.avi,.mkv"

    # ── Exposure / pricing defaults (see LOGOS_Exposure_Pricing_Algorithm.md)
    # Below this a detection doesn't count toward a segment. The pricing doc
    # suggests 0.1, but with the sqrt(area/frame_area) size term a real sponsor
    # logo (small, off-centre) scores ~0.03-0.08, so 0.1 would discard almost
    # everything. 0.02 keeps genuine logos while still dropping near-zero noise.
    visibility_floor: float = 0.02
    min_segment_seconds: float = 0.5
    prime_time_enabled: bool = False  # off by default; needs reliable match clock

    def resolved_model_path(self) -> str:
        return self.model_path or _default_logo_model()

    @property
    def cors_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def allowed_ext_set(self) -> set[str]:
        return {e.strip().lower() for e in self.allowed_ext.split(",") if e.strip()}


@lru_cache
def get_settings() -> Settings:
    return Settings()


# ── Brand display-name mapping ───────────────────────────────────────────
# The fine-tuned model emits raw class names (e.g. "bartercard_home"). The
# dashboard wants clean brand names. We strip _home/_away kit suffixes and look
# up a friendly label, defaulting to Title Case so unknown future sponsors still
# render acceptably.
BRAND_DISPLAY: dict[str, str] = {
    "bradford-bulls": "Bradford Bulls",
    "aon": "Aon",
    "asc_group": "ASC Group",
    "atm": "ATM Hospitality",
    "bartercard": "Bartercard",
    "cch": "CCH",
    "chadlaw": "Chadlaw",
    "ellgren": "Ellgren",
    "em_workwear": "EM Workwear",
    "fairway": "Fairway",
    "klg": "KLG",
    "mcp": "MCP",
    "mna_cladding": "MNA Cladding",
    "mna_support_service": "MNA Support Services",
    "paints_lacquers": "Paints & Lacquers",
    "romatica": "Romatica",
    "top_notch": "Top Notch",
}

_KIT_SUFFIX = re.compile(r"_(home|away|alt|third)$")


def normalize_class(raw_name: str) -> str:
    """Canonical brand key: lowercase, kit suffix stripped.

    `aon_home` and `aon_away` both collapse to `aon` so a brand's exposure is
    aggregated across kits.
    """
    return _KIT_SUFFIX.sub("", raw_name.strip().lower())


def display_name(raw_name: str) -> str:
    key = normalize_class(raw_name)
    if key in BRAND_DISPLAY:
        return BRAND_DISPLAY[key]
    # Fallback: prettify "some_brand" -> "Some Brand"
    return key.replace("-", " ").replace("_", " ").title()
