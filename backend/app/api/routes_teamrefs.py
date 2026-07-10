"""Team-reference endpoints — manual team selection from the dashboard.

Web port of team_detection/ref_build.py: extract isolated player crops from an
uploaded video, show them pre-labelled (Otsu luminance suggestion), let the
user fix the labels, and save the result as the GLOBAL team refs every
subsequent analysis uses. While data/team_refs.pkl exists the per-video auto
bootstrap is skipped entirely.

Extractions are cached in-process (features are heavy to recompute and the
worker is in-process anyway); only the most recent few are kept.
"""
from __future__ import annotations

import pickle
import time
import uuid
from collections import OrderedDict
from datetime import datetime
from pathlib import Path

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from sqlalchemy import select

from app.config import get_settings
from app.db.base import session_scope
from app.db.models import Job, JobStatus
from app.storage import get_storage

router = APIRouter(prefix="/api/team-refs", tags=["team-refs"])

# extract_id -> extraction dict (features + thumbs). Bounded LRU.
_extractions: OrderedDict[str, dict] = OrderedDict()
_MAX_CACHED = 3


class ExtractIn(BaseModel):
    storageKey: str
    kit: str = "away"


class SaveIn(BaseModel):
    extractId: str
    # Per-crop label: "target" | "other" | None (ignore)
    assignments: list[str | None]


class ClusterIn(BaseModel):
    extractId: str
    nClusters: int = 3


@router.get("/status")
def refs_status() -> dict:
    path = Path(get_settings().resolved_team_refs())
    if not path.exists():
        return {"exists": False}
    meta = {}
    try:
        with path.open("rb") as f:
            meta = pickle.load(f).get("meta", {})
    except Exception:
        pass
    return {
        "exists": True,
        "builtAt": datetime.fromtimestamp(path.stat().st_mtime).isoformat(),
        "mode": meta.get("bootstrap", "unknown"),
        "kit": meta.get("kit"),
        "nTarget": meta.get("n_target"),
        "nOther": meta.get("n_other"),
        "wColor": round(meta["w_color"], 2) if "w_color" in meta else None,
    }


@router.delete("")
def delete_refs() -> dict:
    path = Path(get_settings().resolved_team_refs())
    existed = path.exists()
    path.unlink(missing_ok=True)
    return {"deleted": existed}


@router.get("/videos")
def list_videos() -> list[dict]:
    """Uploaded source videos (one per job) to build refs from."""
    with session_scope() as s:
        jobs = list(s.scalars(
            select(Job).where(Job.status == JobStatus.done)
            .order_by(Job.created_at.desc())
        ))
        return [
            {
                "storageKey": j.storage_key,
                "eventName": j.event_name,
                "videoName": j.video_name,
                "kit": j.kit,
                "createdAt": j.created_at.isoformat(),
            }
            for j in jobs
        ]


@router.post("/extract")
def extract_crops(body: ExtractIn) -> dict:
    from app.pipeline.teamid.refbuild import extract_for_labeling

    try:
        video_path = get_storage().local_path(body.storageKey)
    except Exception:
        raise HTTPException(status_code=404, detail="Video not found")
    if not video_path.exists():
        raise HTTPException(status_code=404, detail="Video file missing")

    t0 = time.perf_counter()
    extraction = extract_for_labeling(video_path, body.kit)
    if extraction is None:
        raise HTTPException(
            status_code=422,
            detail="No usable isolated player crops in this video — try another clip",
        )

    extract_id = uuid.uuid4().hex[:12]
    _extractions[extract_id] = extraction
    while len(_extractions) > _MAX_CACHED:
        _extractions.popitem(last=False)

    return {
        "extractId": extract_id,
        "crops": [
            {"thumb": t, "suggested": sug}
            for t, sug in zip(extraction["thumbs"], extraction["suggested"])
        ],
        "tookSeconds": round(time.perf_counter() - t0, 1),
    }


@router.post("/cluster")
def cluster_refs(body: ClusterIn) -> dict:
    """Group the cached extraction's crops into kit clusters for team picking.

    Reuses the crops already extracted by /extract (referenced by extractId);
    the frontend maps the returned member indices back to the thumbs it holds.
    Saving still goes through /save with a per-crop assignments array the
    frontend expands from the chosen cluster -> team mapping.
    """
    from app.pipeline.teamid.refbuild import cluster_crops

    extraction = _extractions.get(body.extractId)
    if extraction is None:
        raise HTTPException(
            status_code=410,
            detail="Extraction expired — extract crops again",
        )
    clusters = cluster_crops(extraction, body.nClusters)
    if not clusters:
        raise HTTPException(
            status_code=422, detail="Too few crops to cluster — extract more first"
        )
    return {"clusters": clusters, "nCrops": len(extraction["color_feats"])}


@router.post("/save")
def save_refs(body: SaveIn) -> dict:
    from app.pipeline.teamid.refbuild import build_refs_from_labels

    extraction = _extractions.get(body.extractId)
    if extraction is None:
        raise HTTPException(
            status_code=410,
            detail="Extraction expired — extract crops again",
        )
    refs, err = build_refs_from_labels(extraction, body.assignments)
    if refs is None:
        raise HTTPException(status_code=422, detail=err)
    meta = refs["meta"]
    return {
        "saved": True,
        "nTarget": meta["n_target"],
        "nOther": meta["n_other"],
        "wColor": round(meta["w_color"], 2),
    }


@router.post("/build")
def build_refs(body: SaveIn) -> dict:
    """Build refs from labels and store them as a per-job blob (NOT global).

    Used by the inline upload team step: the returned `refsKey` is passed to
    POST /api/jobs so only that one analysis uses these references; the global
    refs file and other uploads are untouched.
    """
    import io
    import pickle

    from app.pipeline.teamid.refbuild import build_refs_from_labels

    extraction = _extractions.get(body.extractId)
    if extraction is None:
        raise HTTPException(
            status_code=410, detail="Extraction expired — extract crops again"
        )
    refs, err = build_refs_from_labels(extraction, body.assignments, persist=False)
    if refs is None:
        raise HTTPException(status_code=422, detail=err)

    key = get_storage().save(io.BytesIO(pickle.dumps(refs)), "team_refs.pkl")
    meta = refs["meta"]
    return {
        "refsKey": key,
        "nTarget": meta["n_target"],
        "nOther": meta["n_other"],
        "wColor": round(meta["w_color"], 2),
    }
