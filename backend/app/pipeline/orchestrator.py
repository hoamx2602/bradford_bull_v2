"""Pipeline orchestrator — runs all stages for one job and persists the result.

Emits coarse `stage`/`progress` updates that map onto the four steps the
processing screen shows: Frame extraction -> YOLO26 logo detection (incl. pose
/ body zones) -> Computing exposure -> Calculating media value.

This is the single entry point both the in-process worker and any future Celery
task call, so the queue choice never leaks into the analysis logic.
"""
from __future__ import annotations

import logging

from app.db.base import session_scope
from app.db.repository import AnalysisRepository, JobRepository
from app.config import get_settings
from app.pipeline import aggregate, exposure, frames, ingest, pricing, visibility
from app.pipeline.bodyzones import BodyZoneAccumulator
from app.storage import get_storage

log = logging.getLogger("app.pipeline")

# Progress budget per stage (must sum to ~100). Detection dominates wall-clock.
P_INGEST = 5
P_DETECT_START = 5
P_DETECT_END = 80
P_EXPOSURE = 92
P_PRICING = 98


def run_analysis(job_id: str) -> None:
    settings = get_settings()
    storage = get_storage()

    # 1. Load job + locate the uploaded file.
    with session_scope() as s:
        job = JobRepository(s).get(job_id)
        if job is None:
            log.error("run_analysis: job %s not found", job_id)
            return
        ctx = {
            "event_name": job.event_name,
            "video_name": job.video_name,
            "storage_key": job.storage_key,
            "audience_size": job.audience_size,
            "placement_type": job.placement_type,
            "cpm_base": job.cpm_base,
        }

    try:
        video_path = storage.local_path(ctx["storage_key"])

        # 2. Ingest / probe.
        _update(job_id, P_INGEST, "frames", "Reading video metadata")
        meta = ingest.probe(video_path)

        total = frames.expected_sample_count(meta, settings.sample_fps)

        # 3. Detection + pose over sampled frames (single decode pass).
        from app.pipeline.detect_track import LogoDetector
        from app.pipeline.pose import PoseEstimator

        detector = LogoDetector()
        poser = PoseEstimator() if settings.enable_pose else None
        body = BodyZoneAccumulator()

        # Per-sampled-frame detections, kept for the smooth preview second pass.
        frames_data: list[tuple[float, list]] = []

        all_dets = []
        n = 0
        for t, frame in frames.iter_sampled_frames(video_path, meta, settings.sample_fps):
            dets = detector.infer(frame, t)
            visibility.annotate(dets)
            if poser is not None:
                persons = poser.infer(frame)
                body.add_frame(dets, persons)
            if settings.preview_enabled:
                frames_data.append((t, dets))
            all_dets.extend(dets)

            n += 1
            if n % 10 == 0 or n == total:
                frac = min(1.0, n / max(1, total))
                pct = int(P_DETECT_START + frac * (P_DETECT_END - P_DETECT_START))
                _update(
                    job_id, pct, "detect",
                    f"{n}/{total} frames · {len(set(d.brand_key for d in all_dets))} brands",
                )

        # 4. Exposure aggregation (Tier 2).
        _update(job_id, P_EXPOSURE, "exposure", "Quality-weighted segments")
        logos = exposure.aggregate_logos(all_dets, settings.sample_fps)

        # 5. Pricing (Tier 3).
        _update(job_id, P_PRICING, "pricing", "Computing EMV per brand")
        pricing.price_logos(
            logos,
            cpm_base=ctx["cpm_base"],
            audience_size=ctx["audience_size"],
            placement_type=ctx["placement_type"],
        )

        # 6. Render the smooth annotated preview (full-fps second pass) -> storage.
        preview_key = None
        if settings.preview_enabled and frames_data:
            _update(job_id, P_PRICING, "preview", "Rendering annotated video")
            from app.pipeline.annotate import render_preview

            preview_tmp = video_path.parent / f"{video_path.stem}_preview.mp4"
            preview_path = render_preview(
                video_path, meta.fps, meta.width, meta.height, frames_data, preview_tmp,
                max_width=settings.preview_width, max_frames=settings.preview_max_frames,
            )
            if preview_path is not None:
                with preview_path.open("rb") as fh:
                    preview_key = storage.save(fh, preview_path.name)
                preview_path.unlink(missing_ok=True)

        # 7. Assemble + persist.
        analysis_id = AnalysisRepository.new_id()
        result = aggregate.build_analysis_result(
            analysis_id=analysis_id,
            event_name=ctx["event_name"],
            video_name=ctx["video_name"],
            video_duration_seconds=meta.duration_seconds,
            audience_size=ctx["audience_size"],
            placement_type=ctx["placement_type"],
            cpm_base=ctx["cpm_base"],
            logos=logos,
            body_zones=body.result(),
            frames_analyzed=n,
        )
        result["previewAvailable"] = preview_key is not None

        with session_scope() as s:
            AnalysisRepository(s).create(result, preview_key=preview_key)
            JobRepository(s).mark_done(job_id, analysis_id)
        log.info("job %s done -> analysis %s (%d brands)", job_id, analysis_id, len(logos))

    except Exception as exc:  # report failure to the job so the UI can show it
        log.exception("job %s failed", job_id)
        with session_scope() as s:
            JobRepository(s).mark_error(job_id, str(exc))


def _update(job_id: str, pct: int, stage: str, detail: str) -> None:
    with session_scope() as s:
        JobRepository(s).update_progress(job_id, progress=pct, stage=stage, detail=detail)
