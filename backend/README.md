# Logo Analytics Backend

Production pipeline that turns an uploaded broadcast video into sponsor-exposure
analytics for the `logo-analytics` dashboard: **logo detection → tracking →
visibility scoring → exposure aggregation → body-zone attribution → EMV pricing**.

Implements the algorithms in `../LOGOS_Exposure_Pricing_Algorithm.md` and the
architecture in `../Production-System-Design.MD`.

## Pipeline

```
upload ─▶ ingest ─▶ sample frames (2fps) ─▶ YOLO26 logo detect + ByteTrack ─┐
                                            YOLO11-pose person + keypoints ──┤
                                                                            ▼
        EMV pricing ◀─ exposure aggregation ◀─ visibility scoring   body-zone attribution
              │                                                              │
              └──────────────────────▶ AnalysisResult (JSON) ◀──────────────┘
```

Stage code lives in `app/pipeline/`. **Logo detection uses your fine-tuned
YOLO26m** at `../logo_detection/runs/logo_yolo26m/weights/best.pt` (auto-discovered;
retrain at a different size and it's picked up automatically).

Body-zone attribution uses a **separate** stock **YOLO11-pose** model for human
keypoints — the logo model is detect-only and can't produce a skeleton, and
YOLO26 has no pose variant in ultralytics yet. Set `POSE_MODEL` /
`ENABLE_POSE=false` to change or disable it; it never touches logo detection.

## ⚠️ ultralytics version is pinned to 8.3.40

The fine-tuned `best.pt` was trained against a **pre-release** YOLO26 architecture
that only loads correctly on **ultralytics 8.3.40**. On 8.4.x (the official YOLO26
release) the weights load without error but **detect nothing** (silent break) —
verified on both 8.4.33 and 8.4.62. Keep this env on 8.3.40 until the logo model
is retrained on 8.4.x. (Retraining on 8.4.x is also the prerequisite for using
`yolo26*-pose.pt`; see the pose note above.)

## Run locally

The project uses a dedicated conda env `bradford_bulls_logo` (a clone of
`bradford_bulls` with ultralytics pinned to 8.3.40 + the web deps):

```bash
conda activate bradford_bulls_logo
cd backend
cp .env.example .env             # optional; defaults work out of the box
python -m uvicorn app.main:app --reload --port 8000
```

To recreate that env from scratch:

```bash
conda create --clone bradford_bulls -n bradford_bulls_logo -y
conda activate bradford_bulls_logo
pip install "ultralytics==8.3.40" fastapi "uvicorn[standard]" python-multipart \
            pydantic-settings SQLAlchemy lapx
```

API docs at http://localhost:8000/docs. Then run the frontend with
`NEXT_PUBLIC_API_URL=http://localhost:8000` (see `../logo-analytics`).

### Docker

```bash
docker compose up --build        # serves on :8000, mounts the trained weights
```

## API

| Method | Path | Purpose |
|--------|------|---------|
| POST | `/api/jobs` | multipart upload (`video` + `eventName,audienceSize,placementType,cpmBase`) → `{jobId}` |
| GET  | `/api/jobs/{id}` | poll `{status, progress, stage, stageDetail, analysisId?, error?}` |
| GET  | `/api/analyses` | list (dashboard match selector) |
| GET  | `/api/analyses/{id}` | full `AnalysisResult` (matches `lib/types.ts`) |
| GET  | `/api/analyses/{id}/video` | annotated preview MP4 (logo boxes drawn), HTTP-Range enabled |
| GET  | `/api/analyses/{id}/export.csv` | per-brand CSV |
| GET  | `/api/health` | device / model info |

## Body-part segmentation — optional stage (two engines)

The Body tab can show a body-part overlay video (every player pixel coloured by
region, 8 groups). `ENABLE_BODYSEG=false` turns the stage off. Pick the engine
with `BODYSEG_ENGINE`:

- **`yolo`** (default) — `app/pipeline/bodyseg_yolo.py`: YOLO11-seg person masks
  + YOLO11-pose, each mask pixel labelled by nearest skeleton bone. Runs on
  **MPS / CUDA**, fast enough to segment **every frame → smooth**, multi-person.
  Part boundaries are skeleton-derived (not pixel-perfect). No extra install.
- **`densepose`** — `app/pipeline/bodyseg.py`: pixel-perfect 24-part DensePose.
  **CUDA/CPU only — no Apple-MPS path** (≈1s/frame on Mac CPU), so it's sampled
  (`BODYSEG_FPS`, default 3, overlay held between → output still native fps) and
  needs the build below.

### DensePose install (only for `BODYSEG_ENGINE=densepose`)

```bash
git clone --depth=1 https://github.com/facebookresearch/detectron2 /tmp/detectron2_repo
# macOS only: newer Xcode/clang rejects torch headers — suppress that one error:
export CFLAGS="-Wno-invalid-specialization -Wno-error=invalid-specialization"
export CXXFLAGS="$CFLAGS"
pip install --no-build-isolation -e /tmp/detectron2_repo
pip install --no-build-isolation /tmp/detectron2_repo/projects/DensePose
```

The DensePose config is bundled (`app/models_zoo/densepose_configs/`), so it
works after the clone is gone. Override the model via `BODYSEG_CONFIG` /
`BODYSEG_WEIGHTS`.

## Tests

```bash
pytest -q              # 16 fast unit tests + 1 HTTP smoke test (loads the model)
pytest tests/test_exposure.py -q   # just the Tier-2 logic, no model needed
```

## Tuning

Everything is env-driven (`app/config.py`). Common knobs:

- `SAMPLE_FPS` (default 2.0) — lower for faster/cheaper runs.
- `IMGSZ` (default 1280) — lower (e.g. 960) for speed; the model was trained at 1280.
- `DEVICE` — `auto` picks CUDA → Apple MPS → CPU.
- `ENABLE_POSE` — set `false` to skip body-zone attribution.
- `VISIBILITY_FLOOR` (default 0.02) — minimum per-frame visibility to count.
- `PREVIEW_ENABLED` (default true) — render the annotated detection video by
  detecting on **every frame** at native fps (smooth, like `model.predict(...,
  stream=True)`), separate from the sampled analytics pass. Tune `PREVIEW_WIDTH`
  (960), `PREVIEW_IMGSZ` (960, detection size for speed) and `PREVIEW_MAX_FRAMES`
  (1800 ≈ first ~60–72s — caps full-fps inference on long matches).

## Scaling to full production

The infra is behind interfaces so promotion is config-only:

| Concern | Now | Production | Swap |
|---------|-----|------------|------|
| DB | SQLite | Postgres/TimescaleDB | set `DB_URL` |
| Storage | local FS | S3/MinIO | add `app/storage/s3.py`, `STORAGE_BACKEND=s3` |
| Queue | in-process threads | Celery + Redis | add `app/jobs/celery_app.py`, `QUEUE_BACKEND=celery` |
| Compute | 1 node | autoscaled GPU workers | scale the `worker` service |

The pipeline (`app/pipeline/orchestrator.run_analysis`) is the single entry point
both the in-process worker and a future Celery task call, so none of this touches
the analysis logic. See the commented services in `docker-compose.yml`.

## Notes / future work (per Production-System-Design.MD)

- **Brand names**: the model emits raw classes (`bartercard_home`); `app/config.py`
  `BRAND_DISPLAY` maps them to clean names and collapses `_home/_away` kits.
- **OBB penalty** is `1.0` (the model is horizontal-box). Train an OBB model and
  set it in `visibility.py` to discount angle-skewed logos.
- Not yet implemented (architected for, but out of scope): scene classification
  (play/replay/ad-break), OCR text logos, LED-board cycling, multi-tenant auth,
  real-time/livestream ingestion.
