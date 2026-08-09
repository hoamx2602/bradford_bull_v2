# Logo Analytics Backend

Production pipeline that turns an uploaded broadcast video into sponsor-exposure
analytics for the `logo-analytics` dashboard: **logo detection → tracking →
visibility scoring → exposure aggregation → body-zone attribution → EMV pricing**.

Implements the algorithms in `../LOGOS_Exposure_Pricing_Algorithm.md` and the
architecture in `../Production-System-Design.MD`.

## Pipeline

```
upload ─▶ ingest ─▶ sample frames (2fps) ─▶ logo detect + tracking ─────────┐
                                            YOLO11-pose person + keypoints ──┤
                                                                            ▼
        EMV pricing ◀─ exposure aggregation ◀─ visibility scoring   body-zone attribution
              │                                                              │
              └──────────────────────▶ AnalysisResult (JSON) ◀──────────────┘
```

Stage code lives in `app/pipeline/`. Logo detection is selected with
`LOGO_BACKEND=yolo|rfdetr`; both backends return the same internal detection
records to the rest of the pipeline.

Body-zone attribution uses a **separate** stock **YOLO11-pose** model for human
keypoints — the logo model is detect-only and can't produce a skeleton, and
YOLO26 has no pose variant in ultralytics yet. Set `POSE_MODEL` /
`ENABLE_POSE=false` to change or disable it; it never touches logo detection.

## Legacy YOLO checkpoint compatibility

Some early pre-release YOLO26 checkpoints require Ultralytics 8.3.40. The
current `bradford_bulls` environment uses 8.4.x, so verify any selected `.pt`
checkpoint with a known frame before processing a full match. RF-DETR does not
depend on Ultralytics for logo detection, although the pose/person helpers do.

## Logo detector backend — YOLO (.pt) or RF-DETR (.pth)

Stage 3 is pluggable via `LOGO_BACKEND`:

- `yolo` (default) — fine-tuned YOLO26m `best.pt` via ultralytics ByteTrack.
- `rfdetr` — fine-tuned RF-DETR `checkpoint_best_ema.pth` (from
  `logo_detection/train_colab_rfdetr.ipynb`) via the `rfdetr` package, with
  `supervision.ByteTrack` for track persistence.

Switch by adding to `.env`:

```env
LOGO_BACKEND=rfdetr
RFDETR_MODEL_PATH=/path/to/checkpoint_best_ema.pth   # optional; auto-detects newest *.pth under logo_detection/runs
RFDETR_VARIANT=large                                 # must match how it was trained: nano|small|medium|base|large|2xlarge
```

Then install the extra deps (the YOLO path needs none of these):

```bash
pip install -e ".[rfdetr]"
```

Notes: RF-DETR resizes internally to the variant's default resolution, so
`IMGSZ` / `PREVIEW_IMGSZ` don't apply to it (leave `RFDETR_RESOLUTION=0`). The
class id → brand mapping comes from `RFDETR_BRAND_ORDER` in `config.py` (the
COCO category order used at train time); `RFDETR_CLASS_OFFSET=1` because the
training COCO had a placeholder category at id 0. The DINOv2 backbone has no MPS
path — on Apple Silicon RF-DETR runs on CPU.

## Run locally

The verified backend environment on this workstation is `bradford_bulls`. It
contains FastAPI, SQLAlchemy, CUDA-enabled Torch and RF-DETR 1.8.3:

```bash
conda activate bradford_bulls
cd backend
cp .env.example .env             # optional; defaults work out of the box
# Set LOGO_BACKEND=rfdetr in backend/.env to use the RF-DETR checkpoint.
python -m uvicorn app.main:app --reload --port 8000
```

To recreate a separate environment from the verified one:

```bash
conda create --clone bradford_bulls -n bradford_bulls_backend -y
conda activate bradford_bulls_backend
pip install -e ".[rfdetr]"
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

## Team filter — count only logos on the TARGET team (optional stage)

Shared sponsors appear on both teams' kits. This stage tracks every person
(YOLO person model + BoT-SORT), classifies each track's jersey against
pre-built kit references (colour histogram + SigLIP, fused), stabilises the
label with temporal voting, then keeps only logo detections whose owner is the
target team. Code: `app/pipeline/teamid/`.

### Windows + NVIDIA GPU setup (RTX 4500 Ada, CUDA 12.8)

```bat
:: 1. PyTorch with CUDA 12.8 wheels
pip install torch torchvision --index-url https://download.pytorch.org/whl/cu128

:: 2. Backend + team-filter extras (SigLIP + clustering)
cd backend
pip install -e . -e ".[team]"

:: 3. Verify the GPU is seen
python -c "import torch; print(torch.cuda.get_device_name(0))"
```

### Kit anchors — fully automatic target picking (recommended, one-time)

```bash
python scripts/make_kit_anchors.py
```

Slices the official kit sheets (`KIT/Home Kit.jpg`, `KIT/Away Kit.jpg`) into
jersey crops under `data/kit_anchors/{home,away}/`. With anchors present the
per-upload bootstrap picks the target cluster by similarity to the REAL kit
instead of the luminance heuristic — no manual confirmation step anywhere.
Re-run only when the kit design changes.

### Build kit references (once per kit)

```bat
:: Auto-cluster a short clip (~30-60s with both teams + referee visible):
python scripts\build_team_refs.py --video path\to\clip.mp4 --device 0

:: Collages are written to data\team_refs_review\cluster_*.jpg — open them,
:: then enter the Bradford cluster id at the prompt (or re-run with --pick N).
:: Output: data\team_refs.pkl
```

Build one refs file per kit and switch per match:
`python scripts\build_team_refs.py --video away_clip.mp4 --out data\team_refs_away.pkl`
then set `TEAM_REFS_PATH=data/team_refs_away.pkl`.

### macOS — Apple Silicon (M-series) preset

The same flow runs on MPS out of the box (`DEVICE=auto` resolves to `mps`);
SigLIP runs fp32 on MPS, fp16 on CUDA. Recommended `.env` for a MacBook Pro
M4 — smaller person model + sparser SigLIP keep the team stage cheap:

```ini
DEVICE=auto
TEAM_FILTER_ENABLED=true
TEAM_PERSON_MODEL=yolo11n.pt    # nano person model (yolo11m on desktop GPUs)
TEAM_PERSON_IMGSZ=640
TEAM_SIGLIP_EVERY=8             # re-embed each track every 8 sampled frames
TEAM_BOOTSTRAP_FRAMES=24
```

`pip install transformers` in the conda env enables SigLIP (optional — the
colour histogram alone separates black/white/referee kits well); without it
the stage runs colour-only automatically.

### Enable in `.env`

```ini
DEVICE=0
TEAM_FILTER_ENABLED=true
# TEAM_REFS_PATH=data/team_refs_away.pkl   # default: data/team_refs.pkl
```

Knobs (see `app/config.py`): `TEAM_PERSON_MODEL` (yolo11m.pt; bump to
yolo11l.pt on the RTX 4500), `TEAM_SIGLIP_EVERY` (5 — SigLIP refresh interval
per track), `TEAM_MIN_VOTES` / `TEAM_KEEP_UNKNOWN` (when an OTHER label is
trusted enough to drop logos), `TEAM_KEEP_UNASSIGNED` (logos not attached to
any person, e.g. LED boards — default dropped).

The analysis result gains a `teamFilter` summary (`kept` / `dropped` /
`dropRate`). If the refs file is missing or transformers isn't installed the
stage degrades gracefully (skipped / colour-only) and the pipeline still runs.

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
- Output videos (annotated preview, body-seg overlay) keep the ORIGINAL
  upload's audio: after rendering, the audio stream is muxed back in via
  ffmpeg (system PATH or the bundled `imageio-ffmpeg`). Silent uploads and
  missing ffmpeg degrade gracefully to video-only.
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
