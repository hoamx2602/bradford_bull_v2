"""Data-access layer.

Routes and the worker go through these helpers instead of touching the ORM
directly, so the persistence choice stays swappable and the call sites stay
readable.
"""
from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import Analysis, Job, JobStatus


def _new_id() -> str:
    return uuid.uuid4().hex[:12]


class JobRepository:
    def __init__(self, session: Session):
        self.s = session

    def create(
        self,
        *,
        event_name: str,
        video_name: str,
        storage_key: str,
        audience_size: int,
        placement_type: str,
        cpm_base: float,
        kit: str = "away",
    ) -> Job:
        job = Job(
            id=_new_id(),
            status=JobStatus.queued,
            stage="queued",
            event_name=event_name,
            video_name=video_name,
            storage_key=storage_key,
            audience_size=audience_size,
            placement_type=placement_type,
            cpm_base=cpm_base,
            kit=kit,
        )
        self.s.add(job)
        self.s.commit()
        self.s.refresh(job)
        return job

    def get(self, job_id: str) -> Job | None:
        return self.s.get(Job, job_id)

    def update_progress(
        self, job_id: str, *, progress: int, stage: str, detail: str = ""
    ) -> None:
        job = self.s.get(Job, job_id)
        if job is None:
            return
        job.status = JobStatus.processing
        job.progress = max(0, min(100, progress))
        job.stage = stage
        job.stage_detail = detail
        self.s.commit()

    def mark_done(self, job_id: str, analysis_id: str) -> None:
        job = self.s.get(Job, job_id)
        if job is None:
            return
        job.status = JobStatus.done
        job.progress = 100
        job.stage = "done"
        job.stage_detail = "Analysis complete"
        job.analysis_id = analysis_id
        self.s.commit()

    def mark_error(self, job_id: str, message: str) -> None:
        job = self.s.get(Job, job_id)
        if job is None:
            return
        job.status = JobStatus.error
        job.error = message
        job.stage_detail = "Failed"
        self.s.commit()


class AnalysisRepository:
    def __init__(self, session: Session):
        self.s = session

    def create(
        self, result: dict, preview_key: str | None = None, bodyseg_key: str | None = None
    ) -> Analysis:
        analysis = Analysis(
            id=result["id"],
            event_name=result.get("eventName", ""),
            video_name=result.get("videoName", ""),
            video_duration_seconds=result.get("videoDurationSeconds", 0.0),
            total_emv_usd=result.get("totalEmvUsd", 0.0),
            logo_count=len(result.get("logos", [])),
            preview_key=preview_key,
            bodyseg_key=bodyseg_key,
            result_json=result,
        )
        self.s.add(analysis)
        self.s.commit()
        self.s.refresh(analysis)
        return analysis

    def get(self, analysis_id: str) -> Analysis | None:
        return self.s.get(Analysis, analysis_id)

    def list(self) -> list[Analysis]:
        stmt = select(Analysis).order_by(Analysis.analyzed_at.desc())
        return list(self.s.scalars(stmt))

    @staticmethod
    def new_id() -> str:
        return _new_id()
