"""Analysis endpoints: list (match selector), detail, CSV export."""
from __future__ import annotations

import csv
import io

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse, StreamingResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.api.schemas import MatchEntryOut
from app.api.xlsx_export import build_location_workbook
from app.config import SPONSOR_DISPLAY, display_name
from app.db.base import get_session
from app.db.models import Analysis, Job
from app.db.repository import AnalysisRepository, SettingsRepository
from app.pipeline.location_breakdown import (
    compute_location_ai_percentages,
    compute_zone_detail,
)
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


class AnalysisPatch(BaseModel):
    eventName: str | None = None
    videoName: str | None = None


@router.patch("/{analysis_id}")
def update_analysis(
    analysis_id: str, body: AnalysisPatch, session: Session = Depends(get_session)
) -> dict:
    """Rename an analysis (event and/or video name). Blank values are ignored."""
    ev = body.eventName.strip() if body.eventName else None
    vn = body.videoName.strip() if body.videoName else None
    if not ev and not vn:
        raise HTTPException(status_code=422, detail="Nothing to update")
    a = AnalysisRepository(session).rename(analysis_id, event_name=ev, video_name=vn)
    if a is None:
        raise HTTPException(status_code=404, detail="Analysis not found")
    return {"id": a.id, "eventName": a.event_name, "videoName": a.video_name}


def _brand_label(brand_key: str | None) -> str:
    if not brand_key:
        return ""
    return SPONSOR_DISPLAY.get(brand_key, display_name(brand_key))


def _analysis_kit(session: Session, analysis_id: str) -> str:
    """Which kit this analysis was run on ("home" / "away").

    Read from the originating job (drives which main sponsor is on the chest:
    Top Notch on home/white, Floor Tonic on away/black). Defaults to "away".
    """
    job = (
        session.query(Job)
        .filter(Job.analysis_id == analysis_id)
        .order_by(Job.created_at.desc())
        .first()
    )
    return (job.kit if job and job.kit else "away")


def _build_breakdown(
    session: Session, a: Analysis, criteria: str | None
) -> tuple[list[str], str, list[dict], dict[str, dict]]:
    """Shared builder for the breakdown table + the per-anchor AI detail.

    Returns (enabled_criteria, kit, rows, zone_detail). `rows` matches the JSON
    the breakdown endpoint returns; `zone_detail` maps anchor id -> factor
    metrics (used by the Excel export to explain each AI %).
    """
    settings_repo = SettingsRepository(session)
    locations = settings_repo.list_locations()
    overrides = settings_repo.get_overrides(a.id)
    kit = _analysis_kit(session, a.id)

    if criteria is not None:
        enabled = [c.strip() for c in criteria.split(",") if c.strip()]
    else:
        enabled = settings_repo.get_ai_criteria()

    facts = getattr(a, "facts_json", None) or []
    anchor_by_location = {loc.id: loc.anchor_id for loc in locations}
    ai_pct = compute_location_ai_percentages(facts, enabled, anchor_by_location)
    zone_detail = compute_zone_detail(facts, enabled)

    rows = []
    for loc in locations:
        ov = overrides.get(loc.id)
        # Default sponsor is kit-aware (away override falls back to the home one);
        # a per-video manual override beats both.
        default_brand = (
            loc.brand_key_away if (kit == "away" and loc.brand_key_away) else loc.brand_key
        )
        brand_key = (ov.brand_key if ov and ov.brand_key else default_brand)
        human = (ov.human_percentage if ov and ov.human_percentage is not None
                 else loc.human_percentage)
        human_ai = ov.human_ai_percentage if ov else None
        rows.append({
            "locationId": loc.id,
            "locationName": loc.name,
            "anchorId": loc.anchor_id,
            "brandKey": brand_key,
            "logo": _brand_label(brand_key),
            "humanPercentage": round(human, 2),
            "aiPercentage": ai_pct.get(loc.id, 0.0),
            "humanAiPercentage": human_ai,
            "notes": ov.notes if ov else "",
        })
    return enabled, kit, rows, zone_detail


@router.get("/{analysis_id}/location-breakdown")
def location_breakdown(
    analysis_id: str,
    criteria: str | None = None,
    session: Session = Depends(get_session),
) -> dict:
    """Per-location table: Location | Logo | Human % | AI % | Human-AI %.

    Merges the global location taxonomy with this analysis's overrides, and
    recomputes AI % from the stored exposure facts. `criteria` (comma-separated
    factor keys) previews a different criteria set without saving; omitted, the
    saved ai_criteria setting is used.
    """
    a: Analysis | None = AnalysisRepository(session).get(analysis_id)
    if a is None:
        raise HTTPException(status_code=404, detail="Analysis not found")
    enabled, kit, rows, _ = _build_breakdown(session, a, criteria)
    return {"analysisId": analysis_id, "kit": kit, "enabledCriteria": enabled, "rows": rows}


@router.get("/{analysis_id}/location-export.xlsx")
def export_location_xlsx(
    analysis_id: str,
    criteria: str | None = None,
    session: Session = Depends(get_session),
):
    """Excel workbook of the location breakdown + the parameters behind each AI %."""
    a: Analysis | None = AnalysisRepository(session).get(analysis_id)
    if a is None:
        raise HTTPException(status_code=404, detail="Analysis not found")
    enabled, kit, rows, zone_detail = _build_breakdown(session, a, criteria)
    content = build_location_workbook(
        analysis=a, rows=rows, zone_detail=zone_detail, enabled=enabled, kit=kit
    )
    filename = f"{a.event_name or a.video_name or 'analysis'}_locations.xlsx".replace(" ", "_")
    return StreamingResponse(
        iter([content]),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


class LocationOverrideIn(BaseModel):
    locationId: str
    brandKey: str | None = None
    humanPercentage: float | None = None
    humanAiPercentage: float | None = None
    notes: str | None = None


@router.put("/{analysis_id}/location-overrides")
def save_location_overrides(
    analysis_id: str,
    rows: list[LocationOverrideIn],
    session: Session = Depends(get_session),
) -> dict:
    a = AnalysisRepository(session).get(analysis_id)
    if a is None:
        raise HTTPException(status_code=404, detail="Analysis not found")
    SettingsRepository(session).save_overrides(
        analysis_id, [r.model_dump() for r in rows]
    )
    return {"saved": True, "count": len(rows)}


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


@router.get("/{analysis_id}/teamdet-video")
def get_teamdet_video(analysis_id: str, session: Session = Depends(get_session)):
    """Team-detection overlay MP4 (tracked persons boxed TARGET vs OTHER)."""
    a: Analysis | None = AnalysisRepository(session).get(analysis_id)
    if a is None or not getattr(a, "teamdet_key", None):
        raise HTTPException(status_code=404, detail="No team-detection video for this analysis")
    path = get_storage().local_path(a.teamdet_key)
    if not path.exists():
        raise HTTPException(status_code=404, detail="Team-detection file missing")
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
