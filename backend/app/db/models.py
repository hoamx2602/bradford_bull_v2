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
    # Which target-team kit this match uses (drives the team filter's
    # reference bootstrap): "away" (black) or "home" (white).
    kit: Mapped[str] = mapped_column(String(16), default="away")
    # Storage key of refs picked manually for THIS upload (inline team step).
    # When set, the pipeline uses these instead of the global file / auto guess.
    team_refs_key: Mapped[str | None] = mapped_column(String(512), nullable=True)

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
    # Storage key of the body-part segmentation overlay video (DensePose).
    bodyseg_key: Mapped[str | None] = mapped_column(String(512), nullable=True)
    # Storage key of the team-detection overlay video (TARGET vs OTHER boxes).
    teamdet_key: Mapped[str | None] = mapped_column(String(512), nullable=True)

    # Full AnalysisResult payload (already camelCase, ready for the frontend).
    result_json: Mapped[dict] = mapped_column(JSON, default=dict)

    # Per-detection Tier-1 factor components (list of dicts). Kept OUT of
    # result_json (which the dashboard reads whole) so it doesn't bloat every
    # dashboard load; only the location-breakdown endpoint reads it, to recompute
    # AI-percentage under any subset of enabled factors.
    facts_json: Mapped[list] = mapped_column(JSON, default=list)


class LocationConfig(Base):
    """Global, configurable kit-placement taxonomy (the dashboard's Location list).

    Each location is the customer's name for a placement on the kit, mapped to an
    internal pose anchor (`anchor_id` ∈ bodyzones.ZONE_IDS) so AI-percentage can be
    derived, plus the default sponsor (`brand_key`) and the customer's contractual
    `human_percentage`. Per-video tweaks live in VideoLocationOverride.
    """

    __tablename__ = "location_configs"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)   # slug
    name: Mapped[str] = mapped_column(String(128), default="")
    order_index: Mapped[int] = mapped_column(Integer, default=0)
    anchor_id: Mapped[str] = mapped_column(String(64), default="")  # bodyzones zone id
    brand_key: Mapped[str | None] = mapped_column(String(64), nullable=True)
    human_percentage: Mapped[float] = mapped_column(Float, default=0.0)


class AppSetting(Base):
    """Singleton key/value JSON store for app-wide settings (e.g. ai_criteria)."""

    __tablename__ = "app_settings"

    key: Mapped[str] = mapped_column(String(64), primary_key=True)
    value: Mapped[dict] = mapped_column(JSON, default=dict)


class VideoLocationOverride(Base):
    """Per-analysis override of a location row + the manual Human-AI percentage.

    Null fields fall back to the global LocationConfig. `human_ai_percentage` is
    the value the user types after eyeballing the whole video.
    """

    __tablename__ = "video_location_overrides"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    analysis_id: Mapped[str] = mapped_column(
        ForeignKey("analyses.id"), index=True
    )
    location_id: Mapped[str] = mapped_column(ForeignKey("location_configs.id"))
    brand_key: Mapped[str | None] = mapped_column(String(64), nullable=True)
    human_percentage: Mapped[float | None] = mapped_column(Float, nullable=True)
    human_ai_percentage: Mapped[float | None] = mapped_column(Float, nullable=True)
    notes: Mapped[str] = mapped_column(String(512), default="")
