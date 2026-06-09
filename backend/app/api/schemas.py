"""API response models (camelCase, matching logo-analytics/lib/types.ts).

The heavy AnalysisResult is stored already-camelCased as a JSON blob and returned
as-is, so we only model the thin envelopes (job status, match list entry) here.
"""
from __future__ import annotations

from typing import Any

from pydantic import BaseModel


class JobCreated(BaseModel):
    jobId: str
    status: str


class JobStatusOut(BaseModel):
    id: str
    status: str                 # queued | processing | done | error
    progress: int               # 0..100
    stage: str
    stageDetail: str
    analysisId: str | None = None
    error: str | None = None


class MatchEntryOut(BaseModel):
    """Matches the frontend MatchEntry shape for the dashboard match selector."""

    id: str
    eventName: str
    date: str
    videoName: str
    durationSeconds: float
    logoCount: int
    totalEmv: float
    result: dict[str, Any]
