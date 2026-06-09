"""Job endpoints: create (upload) and poll status."""
from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.api.schemas import JobCreated, JobStatusOut
from app.config import get_settings
from app.db.base import get_session
from app.db.repository import JobRepository
from app.jobs import get_queue
from app.pipeline.ingest import IngestError, validate_extension
from app.storage import get_storage

router = APIRouter(prefix="/api/jobs", tags=["jobs"])


@router.post("", response_model=JobCreated, status_code=201)
async def create_job(
    video: UploadFile = File(...),
    eventName: str = Form(...),
    audienceSize: int = Form(...),
    placementType: str = Form("Live Broadcast TV"),
    cpmBase: float = Form(22.0),
    session: Session = Depends(get_session),
) -> JobCreated:
    settings = get_settings()

    try:
        validate_extension(video.filename or "")
    except IngestError as exc:
        raise HTTPException(status_code=415, detail=str(exc)) from exc

    # Persist the upload via the storage backend (local now, S3 later).
    storage = get_storage()
    key = storage.save(video.file, video.filename or "upload.mp4")

    # Enforce size after write (UploadFile streams; checking here avoids buffering
    # the whole file in memory just to measure it).
    saved = storage.local_path(key)
    size_mb = saved.stat().st_size / 1e6
    if size_mb > settings.max_upload_mb:
        storage.delete(key)
        raise HTTPException(
            status_code=413,
            detail=f"File {size_mb:.0f} MB exceeds limit of {settings.max_upload_mb} MB",
        )

    job = JobRepository(session).create(
        event_name=eventName.strip(),
        video_name=Path(video.filename or "upload.mp4").name,
        storage_key=key,
        audience_size=audienceSize,
        placement_type=placementType,
        cpm_base=cpmBase,
    )

    get_queue().enqueue(job.id)
    return JobCreated(jobId=job.id, status=job.status.value)


@router.get("/{job_id}", response_model=JobStatusOut)
def get_job(job_id: str, session: Session = Depends(get_session)) -> JobStatusOut:
    job = JobRepository(session).get(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")
    return JobStatusOut(
        id=job.id,
        status=job.status.value,
        progress=job.progress,
        stage=job.stage,
        stageDetail=job.stage_detail,
        analysisId=job.analysis_id,
        error=job.error,
    )
