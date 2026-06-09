"""ORM models.

Two tables: `jobs` (lifecycle of one upload+analysis request) and `analyses`
(the finished result). The rich nested result (logos[], segments[], bodyZones[])
is stored as a JSON blob — it's read whole and rendered whole by the dashboard,
so a document column is the pragmatic fit. Promote hot fields to real columns /
TimescaleDB if time-series querying is needed later.
"""
from __future__ import annotations

import enum
from datetime import datetime, timezone

from sqlalchemy import JSON, DateTime, Enum, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class JobStatus(str, enum.Enum):
    queued = "queued"
    processing = "processing"
    done = "done"
    error = "error"


class Job(Base):
    __tablename__ = "jobs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    status: Mapped[JobStatus] = mapped_column(
        Enum(JobStatus, native_enum=False, length=16), default=JobStatus.queued, index=True
    )
    progress: Mapped[int] = mapped_column(Integer, default=0)        # 0..100
    stage: Mapped[str] = mapped_column(String(64), default="queued")  # maps to UI step
    stage_detail: Mapped[str] = mapped_column(String(255), default="")
    error: Mapped[str | None] = mapped_column(Text, nullable=True)

    # request inputs
    event_name: Mapped[str] = mapped_column(String(255), default="")
    video_name: Mapped[str] = mapped_column(String(512), default="")
    storage_key: Mapped[str] = mapped_column(String(512), default="")
    audience_size: Mapped[int] = mapped_column(Integer, default=0)
    placement_type: Mapped[str] = mapped_column(String(64), default="Live Broadcast TV")
    cpm_base: Mapped[float] = mapped_column(Float, default=22.0)

    analysis_id: Mapped[str | None] = mapped_column(
        ForeignKey("analyses.id"), nullable=True
    )

    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=_utcnow, onupdate=_utcnow
    )


class Analysis(Base):
    __tablename__ = "analyses"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    event_name: Mapped[str] = mapped_column(String(255), default="")
    video_name: Mapped[str] = mapped_column(String(512), default="")
    video_duration_seconds: Mapped[float] = mapped_column(Float, default=0.0)
    total_emv_usd: Mapped[float] = mapped_column(Float, default=0.0)
    logo_count: Mapped[int] = mapped_column(Integer, default=0)
    analyzed_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)

    # Storage key of the annotated preview video (boxes drawn), if produced.
    preview_key: Mapped[str | None] = mapped_column(String(512), nullable=True)

    # Full AnalysisResult payload (already camelCase, ready for the frontend).
    result_json: Mapped[dict] = mapped_column(JSON, default=dict)
