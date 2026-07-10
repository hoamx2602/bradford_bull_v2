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


def _store_upload(video: UploadFile) -> str:
    """Validate + persist an upload, returning its storage key."""
    settings = get_settings()
    try:
        validate_extension(video.filename or "")
    except IngestError as exc:
        raise HTTPException(status_code=415, detail=str(exc)) from exc

    storage = get_storage()
    key = storage.save(video.file, video.filename or "upload.mp4")

    # Enforce size after write (UploadFile streams; checking here avoids buffering
    # the whole file in memory just to measure it).
    size_mb = storage.local_path(key).stat().st_size / 1e6
    if size_mb > settings.max_upload_mb:
        storage.delete(key)
        raise HTTPException(
            status_code=413,
            detail=f"File {size_mb:.0f} MB exceeds limit of {settings.max_upload_mb} MB",
        )
    return key


@router.post("/upload", status_code=201)
async def upload_video(video: UploadFile = File(...)) -> dict:
    """Persist a video WITHOUT starting analysis, returning its storage key.

    The inline upload flow uploads first, lets the user pick teams from the
    clustered crops (via /api/team-refs/extract+cluster+build), then calls
    POST /api/jobs with the storageKey + chosen teamRefsKey.
    """
    return {
        "storageKey": _store_upload(video),
        "videoName": Path(video.filename or "upload.mp4").name,
    }


@router.post("", response_model=JobCreated, status_code=201)
async def create_job(
    video: UploadFile | None = File(None),
    storageKey: str | None = Form(None),
    teamRefsKey: str | None = Form(None),
    videoName: str | None = Form(None),
    eventName: str = Form(...),
    audienceSize: int = Form(...),
    placementType: str = Form("Live Broadcast TV"),
    cpmBase: float = Form(22.0),
    kit: str = Form("away"),
    session: Session = Depends(get_session),
) -> JobCreated:
    # Either a fresh upload (legacy one-shot path) or a key from /upload (the
    # inline team-selection flow, which may also carry per-job team refs).
    if storageKey:
        key = storageKey
        video_name = (videoName or Path(storageKey).name).strip()
    elif video is not None:
        key = _store_upload(video)
        video_name = Path(video.filename or "upload.mp4").name
    else:
        raise HTTPException(status_code=422, detail="Provide a video file or storageKey")

    kit_norm = kit.strip().lower()
    if kit_norm not in {"home", "away"}:
        kit_norm = "away"

    job = JobRepository(session).create(
        event_name=eventName.strip(),
        video_name=video_name,
        storage_key=key,
        audience_size=audienceSize,
        placement_type=placementType,
        cpm_base=cpmBase,
        kit=kit_norm,
        team_refs_key=teamRefsKey or None,
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
