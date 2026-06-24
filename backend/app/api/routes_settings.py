"""Settings endpoints: location taxonomy/mapping, brands, anchors, AI criteria.

Backs the /settings page: the global Location→Logo→Human% table, the pose anchors
a location can map to, the sponsor brand list, and which algorithm factors are
enabled for the AI-percentage computation.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.config import SPONSOR_DISPLAY
from app.db.base import get_session
from app.db.repository import SettingsRepository
from app.pipeline.bodyzones import ZONES
from app.pipeline.location_breakdown import AI_CRITERIA

router = APIRouter(prefix="/api/settings", tags=["settings"])


class LocationIn(BaseModel):
    id: str | None = None
    name: str
    anchorId: str = ""
    brandKey: str | None = None
    brandKeyAway: str | None = None
    humanPercentage: float = 0.0


class LocationOut(LocationIn):
    orderIndex: int = 0


def _to_out(row) -> LocationOut:
    return LocationOut(
        id=row.id,
        name=row.name,
        anchorId=row.anchor_id,
        brandKey=row.brand_key,
        brandKeyAway=row.brand_key_away,
        humanPercentage=row.human_percentage,
        orderIndex=row.order_index,
    )


@router.get("/locations", response_model=list[LocationOut])
def get_locations(session: Session = Depends(get_session)) -> list[LocationOut]:
    return [_to_out(r) for r in SettingsRepository(session).list_locations()]


@router.put("/locations", response_model=list[LocationOut])
def put_locations(
    rows: list[LocationIn], session: Session = Depends(get_session)
) -> list[LocationOut]:
    saved = SettingsRepository(session).replace_locations([r.model_dump() for r in rows])
    return [_to_out(r) for r in saved]


@router.get("/anchors")
def get_anchors() -> list[dict]:
    """Pose anchors a location can map to (id + display name)."""
    return [{"id": zid, "name": name} for zid, name in ZONES]


@router.get("/brands")
def get_brands() -> list[dict]:
    """Sponsor brands for the Logo dropdown (key + display name)."""
    return [{"key": k, "name": v} for k, v in sorted(SPONSOR_DISPLAY.items(), key=lambda kv: kv[1])]


@router.get("/ai-criteria/options")
def get_ai_criteria_options() -> list[dict]:
    """All tickable algorithm factors with labels + descriptions."""
    return AI_CRITERIA


class AiCriteriaIn(BaseModel):
    enabled: list[str]


@router.get("/ai-criteria")
def get_ai_criteria(session: Session = Depends(get_session)) -> dict:
    return {"enabled": SettingsRepository(session).get_ai_criteria()}


@router.put("/ai-criteria")
def put_ai_criteria(
    body: AiCriteriaIn, session: Session = Depends(get_session)
) -> dict:
    valid = {c["key"] for c in AI_CRITERIA}
    enabled = [k for k in body.enabled if k in valid]
    return {"enabled": SettingsRepository(session).set_ai_criteria(enabled)}


class AiAdjustIn(BaseModel):
    weight: float


@router.get("/ai-adjust")
def get_ai_adjust(session: Session = Depends(get_session)) -> dict:
    """Blend weight β for the AI Adjusted column (0 = pure AI, 1 = pure human)."""
    return {"weight": SettingsRepository(session).get_ai_adjust_weight()}


@router.put("/ai-adjust")
def put_ai_adjust(
    body: AiAdjustIn, session: Session = Depends(get_session)
) -> dict:
    return {"weight": SettingsRepository(session).set_ai_adjust_weight(body.weight)}
