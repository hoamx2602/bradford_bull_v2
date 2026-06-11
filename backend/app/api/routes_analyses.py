"""Analysis endpoints: list (match selector), detail, CSV export."""
from __future__ import annotations

import csv
import io

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse, StreamingResponse
from sqlalchemy.orm import Session

from app.api.schemas import MatchEntryOut
from app.db.base import get_session
from app.db.models import Analysis
from app.db.repository import AnalysisRepository
from app.storage import get_storage

router = APIRouter(prefix="/api/analyses", tags=["analyses"])


@router.get("", response_model=list[MatchEntryOut])
def list_analyses(session: Session = Depends(get_session)) -> list[MatchEntryOut]:
    rows = AnalysisRepository(session).list()
    return [
        MatchEntryOut(
            id=a.id,
            eventName=a.event_name,
            date=a.result_json.get("analyzedAt", a.analyzed_at.isoformat()),
            videoName=a.video_name,
            durationSeconds=a.video_duration_seconds,
            logoCount=a.logo_count,
            totalEmv=a.total_emv_usd,
            result=a.result_json,
        )
        for a in rows
    ]


@router.get("/{analysis_id}")
def get_analysis(analysis_id: str, session: Session = Depends(get_session)) -> dict:
    a = AnalysisRepository(session).get(analysis_id)
    if a is None:
        raise HTTPException(status_code=404, detail="Analysis not found")
    return a.result_json


@router.get("/{analysis_id}/video")
def get_preview_video(analysis_id: str, session: Session = Depends(get_session)):
    """Annotated preview MP4 (logo boxes drawn). FileResponse handles HTTP Range
    requests so the <video> element can seek."""
    a: Analysis | None = AnalysisRepository(session).get(analysis_id)
    if a is None or not a.preview_key:
        raise HTTPException(status_code=404, detail="No preview video for this analysis")
    path = get_storage().local_path(a.preview_key)
    if not path.exists():
        raise HTTPException(status_code=404, detail="Preview file missing")
    # No `filename=` -> inline (Content-Disposition: inline) so <video> plays it.
    return FileResponse(path, media_type="video/mp4")


@router.get("/{analysis_id}/bodyseg-video")
def get_bodyseg_video(analysis_id: str, session: Session = Depends(get_session)):
    """DensePose body-part segmentation overlay MP4 (Range-enabled, inline)."""
    a: Analysis | None = AnalysisRepository(session).get(analysis_id)
    if a is None or not a.bodyseg_key:
        raise HTTPException(status_code=404, detail="No body-segmentation video for this analysis")
    path = get_storage().local_path(a.bodyseg_key)
    if not path.exists():
        raise HTTPException(status_code=404, detail="Body-segmentation file missing")
    return FileResponse(path, media_type="video/mp4")


@router.get("/{analysis_id}/export.csv")
def export_csv(analysis_id: str, session: Session = Depends(get_session)):
    a = AnalysisRepository(session).get(analysis_id)
    if a is None:
        raise HTTPException(status_code=404, detail="Analysis not found")

    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(
        [
            "brand", "class", "total_exposure_seconds", "quality_exposure_seconds",
            "avg_visibility_score", "segment_count", "longest_segment_seconds", "emv_usd",
        ]
    )
    for logo in a.result_json.get("logos", []):
        writer.writerow(
            [
                logo["name"], logo["class"], logo["totalExposureSeconds"],
                logo["qualityExposureSeconds"], logo["avgVisibilityScore"],
                logo["segmentCount"], logo["longestSegmentSeconds"], logo.get("emvUsd", 0),
            ]
        )
    buf.seek(0)
    filename = f"{a.event_name or 'analysis'}.csv".replace(" ", "_")
    return StreamingResponse(
        iter([buf.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
