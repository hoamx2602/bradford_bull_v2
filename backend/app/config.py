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


def _default_rfdetr_model() -> str:
    """RF-DETR checkpoint (.pth). Picks the newest checkpoint_best_ema.pth under
    logo_detection/runs/*; overridable via RFDETR_MODEL_PATH."""
    runs = REPO_ROOT / "logo_detection" / "runs"
    cands = sorted(runs.glob("*/weights/checkpoint_best*.pth"), key=lambda p: p.stat().st_mtime)
    if cands:
        return str(cands[-1])
    return str(runs / "rfdetr_large" / "weights" / "checkpoint_best_ema.pth")


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
    # Logo detector backend: "yolo" = fine-tuned YOLO26m (ultralytics, built-in
    # ByteTrack), "rfdetr" = RF-DETR .pth checkpoint (no NMS; tracking added via
    # supervision.ByteTrack). Swap with LOGO_BACKEND=rfdetr.
    logo_backend: str = "yolo"
    model_path: str = ""            # filled by _default_logo_model() if empty
    # RF-DETR weights + variant (only used when logo_backend=rfdetr). The .pth
    # has no class names baked in, so brands come from RFDETR_CLASS_NAMES below
    # (must match the training class order). resolution=0 -> use the variant's
    # native size (don't override; RF-DETR has an interpolation bug otherwise).
    rfdetr_model_path: str = ""     # filled by _default_rfdetr_model() if empty
    rfdetr_variant: str = "large"   # large | 2xlarge | base | nano | small | medium
    rfdetr_resolution: int = 0      # 0 = model default (Large 704 / 2XLarge 880)
    # RF-DETR confidence floor — SEPARATE from `conf` (which is tuned for YOLO).
    # DETR sigmoid-focal scores run much lower than YOLO's; real logos score
    # ~0.1-0.3. 0.10 maximises recall but lets weak, flickery boxes through
    # (false hits on opponent kit + rapid brand-flipping); 0.20 is a calmer
    # precision/recall balance. Lower toward 0.10 if real logos get missed.
    rfdetr_conf: float = 0.20
    # category_id of the FIRST brand in the model's output. The training COCO had
    # id 0 = 'logos' placeholder and brands at 1..17, so predicted class_id is
    # 1-indexed into RFDETR_CLASS_NAMES. Set to 0 if your brand names come out
    # shifted by one.
    rfdetr_class_offset: int = 1
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
    # Temporal smoothing of the preview: track boxes across frames, vote each
    # box's brand, and "coast" (hold) a box for a few frames when detection
    # drops — kills the per-frame flicker / brand-flipping that RF-DETR's
    # low-confidence boxes produce. Applies to both backends.
    preview_stabilize: bool = True
    preview_stab_coast: int = 4     # frames to keep drawing a box after it drops
    preview_stab_min_hits: int = 2  # frames a box must persist before it's drawn
    preview_width: int = 960        # downscale preview frames to this width
    preview_imgsz: int = 960        # detection size for the preview pass (speed)
    # Preview runs detection on EVERY frame at native fps (smooth, like the YOLO
    # notebook), separate from the sampled analytics pass. Cap total frames so a
    # long match doesn't trigger full-fps inference over hours — 1800 native
    # frames ≈ first 60–72s of footage.
    preview_max_frames: int = 1800

    # ── Body-part segmentation (DensePose / Detectron2) ──────────────────
    # Heavy + needs detectron2+densepose (CUDA recommended). The stage is
    # skipped gracefully if those aren't importable, so the rest of the
    # pipeline always runs. On CPU keep fps/frames low.
    enable_bodyseg: bool = True
    # Engine: "yolo" = YOLO11-seg + pose (runs on MPS/GPU, fast, segments every
    # frame → smooth, multi-person). "densepose" = DensePose (CUDA/CPU only,
    # pixel-perfect, no MPS). Default yolo so Apple GPUs are used.
    bodyseg_engine: str = "yolo"
    bodyseg_seg_model: str = "yolo11n-seg.pt"  # ultralytics seg weights (yolo engine)
    bodyseg_fps: float = 3.0          # DensePose-only: refresh rate/sec (overlay
                                      # held between runs). yolo runs every frame.
    bodyseg_max_frames: int = 900     # cap on native output frames (~30s @30fps)
    bodyseg_width: int = 960          # downscale output width
    bodyseg_alpha: float = 0.55       # overlay opacity over the frame
    bodyseg_conf: float = 0.7         # person detection threshold
    bodyseg_config: str = ""          # densepose yaml path; empty -> auto-detect
    bodyseg_weights: str = (
        "https://dl.fbaipublicfiles.com/densepose/"
        "densepose_rcnn_R_50_FPN_s1x/165712039/model_final_162be9.pkl"
    )

    # ── Team filter (count only logos on TARGET-team players) ────────────
    # Filters logo detections to those worn by the target team (Bradford),
    # dropping opponent/referee/board hits of shared sponsors. Runs as part of
    # the standard upload flow: if no refs file exists, references are
    # AUTO-BOOTSTRAPPED from the uploaded video (cluster jerseys, pick the
    # target cluster via kit anchors or kit luminance). Designed for CUDA
    # (DEVICE=0); SigLIP falls back to colour-only if transformers is missing;
    # any failure disables the stage gracefully (analysis runs unfiltered).
    team_filter_enabled: bool = True
    team_auto_refs: bool = True           # bootstrap refs from the video itself
    # Frames sampled for the bootstrap. Generous because crops that are
    # overlapped (tackles), clipped at the frame edge, or blurry are discarded
    # — busy clips can yield only a handful of usable crops per frame.
    team_bootstrap_frames: int = 96
    # Kits considered dark for the luminance pick (csv). Bradford away = black.
    team_dark_kits: str = "away"
    team_refs_path: str = ""              # default: data/team_refs.pkl
    team_person_model: str = "yolo11m.pt" # person detector (auto-downloaded)
    team_person_conf: float = 0.35
    team_person_imgsz: int = 960
    team_siglip_every: int = 5            # re-embed each track every N sampled frames
    team_hysteresis: float = 1.25         # vote lead needed to flip a track's label
    team_min_votes: float = 2.0           # vote mass before an OTHER label may drop logos
    team_keep_unknown: bool = True        # keep logos on not-yet-confident tracks
    team_keep_unassigned: bool = False    # keep logos not attached to any person

    # ── Team-detection overlay video ─────────────────────────────────────
    # Standalone video showing the team filter's view: tracked persons boxed
    # by voted team (TARGET vs OTHER). Runs a fresh tracking pass at native
    # fps, capped like the preview so long matches stay cheap.
    teamdet_video_enabled: bool = True
    teamdet_max_frames: int = 900         # native output frames (~30s @30fps)
    teamdet_width: int = 960              # downscale output width

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

    def resolved_rfdetr_model_path(self) -> str:
        return self.rfdetr_model_path or _default_rfdetr_model()

    def resolved_team_refs(self) -> str:
        return self.team_refs_path or str(BACKEND_DIR / "data" / "team_refs.pkl")

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


# ── RF-DETR class order ──────────────────────────────────────────────────
# Unlike the YOLO weights, an RF-DETR .pth has no class names embedded. This is
# the 17-brand order used when the COCO dataset was built (train_colab_rfdetr.ipynb,
# BRAND_ORDER); the model emits a numeric class_id that indexes into this list
# (offset by Settings.rfdetr_class_offset). Keep in sync with the training recipe.
RFDETR_CLASS_NAMES: list[str] = [
    "acs_group", "aon", "atm", "bartercard", "cch", "chadlaw", "ellgren",
    "em_workwear", "fairway", "floor_tonic", "klg", "mcp", "mna_cladding",
    "mna_support_service", "paints_lacquers", "romantica", "top_notch",
]


def rfdetr_class_name(class_id: int, offset: int = 1) -> str:
    """Map an RF-DETR predicted class_id to its raw brand name.

    `offset` is the category_id of the first brand (1 when a placeholder class 0
    exists, as in the training COCO). Out-of-range ids fall back to the numeric
    id so an unexpected class never crashes the pipeline.
    """
    idx = class_id - offset
    if 0 <= idx < len(RFDETR_CLASS_NAMES):
        return RFDETR_CLASS_NAMES[idx]
    return str(class_id)
