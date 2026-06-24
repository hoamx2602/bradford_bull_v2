"""Data-access layer.

Routes and the worker go through these helpers instead of touching the ORM
directly, so the persistence choice stays swappable and the call sites stay
readable.
"""
from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import (
    Analysis,
    AppSetting,
    Job,
    JobStatus,
    LocationConfig,
    VideoLocationOverride,
)


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
        team_refs_key: str | None = None,
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
            team_refs_key=team_refs_key,
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
        self,
        result: dict,
        preview_key: str | None = None,
        bodyseg_key: str | None = None,
        teamdet_key: str | None = None,
        facts: list | None = None,
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
            teamdet_key=teamdet_key,
            result_json=result,
            facts_json=facts or [],
        )
        self.s.add(analysis)
        self.s.commit()
        self.s.refresh(analysis)
        return analysis

    def get(self, analysis_id: str) -> Analysis | None:
        return self.s.get(Analysis, analysis_id)

    def rename(
        self, analysis_id: str, *,
        event_name: str | None = None, video_name: str | None = None,
    ) -> Analysis | None:
        """Update the event/video name on both the columns (match list) and the
        result_json blob (detail view). Returns the row, or None if not found."""
        a = self.s.get(Analysis, analysis_id)
        if a is None:
            return None
        rj = dict(a.result_json or {})
        if event_name is not None:
            a.event_name = event_name
            rj["eventName"] = event_name
        if video_name is not None:
            a.video_name = video_name
            rj["videoName"] = video_name
        a.result_json = rj  # reassign so the JSON column is flagged dirty
        self.s.commit()
        self.s.refresh(a)
        return a

    def list(self) -> list[Analysis]:
        stmt = select(Analysis).order_by(Analysis.analyzed_at.desc())
        return list(self.s.scalars(stmt))

    @staticmethod
    def new_id() -> str:
        return _new_id()


class SettingsRepository:
    """Global location taxonomy, ai_criteria setting, and per-video overrides."""

    def __init__(self, session: Session):
        self.s = session

    # ── Location taxonomy (global mapping + human %) ──────────────────────
    def list_locations(self) -> list[LocationConfig]:
        stmt = select(LocationConfig).order_by(LocationConfig.order_index)
        return list(self.s.scalars(stmt))

    def replace_locations(self, rows: list[dict]) -> list[LocationConfig]:
        """Full replace of the taxonomy. Each row: id?, name, anchorId, brandKey,
        humanPercentage. Missing id -> slug from name."""
        for existing in self.list_locations():
            self.s.delete(existing)
        self.s.flush()
        out: list[LocationConfig] = []
        seen: set[str] = set()
        for i, r in enumerate(rows):
            lid = (r.get("id") or _slugify(r.get("name", ""))) or f"location-{i}"
            while lid in seen:
                lid = f"{lid}-{i}"
            seen.add(lid)
            row = LocationConfig(
                id=lid,
                name=(r.get("name") or "").strip(),
                order_index=i,
                anchor_id=(r.get("anchorId") or "").strip(),
                brand_key=(r.get("brandKey") or None),
                brand_key_away=(r.get("brandKeyAway") or None),
                human_percentage=float(r.get("humanPercentage") or 0.0),
            )
            self.s.add(row)
            out.append(row)
        self.s.commit()
        return out

    # ── AI criteria (which factors are enabled) ───────────────────────────
    def get_ai_criteria(self) -> list[str]:
        row = self.s.get(AppSetting, "ai_criteria")
        if row is None:
            return []
        return list(row.value.get("enabled", []))

    def set_ai_criteria(self, enabled: list[str]) -> list[str]:
        row = self.s.get(AppSetting, "ai_criteria")
        if row is None:
            row = AppSetting(key="ai_criteria", value={"enabled": enabled})
            self.s.add(row)
        else:
            row.value = {"enabled": enabled}
        self.s.commit()
        return enabled

    # ── Per-video overrides (incl. manual Human-AI %) ─────────────────────
    def get_overrides(self, analysis_id: str) -> dict[str, VideoLocationOverride]:
        stmt = select(VideoLocationOverride).where(
            VideoLocationOverride.analysis_id == analysis_id
        )
        return {o.location_id: o for o in self.s.scalars(stmt)}

    def save_overrides(self, analysis_id: str, rows: list[dict]) -> None:
        """Upsert per-location overrides. Each row: locationId, brandKey?,
        humanPercentage?, humanAiPercentage?, notes?."""
        existing = self.get_overrides(analysis_id)
        for r in rows:
            lid = r.get("locationId")
            if not lid:
                continue
            o = existing.get(lid)
            if o is None:
                o = VideoLocationOverride(analysis_id=analysis_id, location_id=lid)
                self.s.add(o)
            o.brand_key = r.get("brandKey") or None
            o.human_percentage = _opt_float(r.get("humanPercentage"))
            o.human_ai_percentage = _opt_float(r.get("humanAiPercentage"))
            o.notes = (r.get("notes") or "").strip()
        self.s.commit()


def _slugify(text: str) -> str:
    out = "".join(c if c.isalnum() else "-" for c in text.strip().lower())
    return "-".join(p for p in out.split("-") if p)


def _opt_float(v) -> float | None:
    if v is None or v == "":
        return None
    try:
        return float(v)
    except (TypeError, ValueError):
        return None
