"""Runtime team-filter stage: person tracking + team voting + logo filtering.

Per sampled frame:
    1. Track persons (YOLO person model + BoT-SORT, persistent ids).
    2. Per person: jersey crop -> colour feature (every frame) + SigLIP
       embedding (refreshed every `team_siglip_every` frames per track, cached)
       -> fused classification -> quality-weighted vote on the track.
    3. Per logo detection: assign to its owner person (smallest containing
       bbox, else nearest within reach) and keep it only when the owner's
       stable label is TARGET.

Votes accumulate over a track's lifetime, so labels become more reliable as
the video progresses; early uncertain tracks are kept by default
(`team_keep_unknown`) to avoid losing data.
"""
from __future__ import annotations

import logging
import pickle
from dataclasses import dataclass
from pathlib import Path

import numpy as np

from app.config import get_settings
from app.models_zoo import registry
from app.pipeline.datatypes import Detection
from app.pipeline.teamid.classifier import OTHER, TARGET, TeamClassifier, VoteTracker
from app.pipeline.teamid.features import color_feature, encode_crops_masked
from app.pipeline.teamid.jersey import get_jersey_region, jersey_quality

log = logging.getLogger("app.teamid")


@dataclass
class TrackedPerson:
    xyxy: tuple[float, float, float, float]
    track_id: int
    team: str          # TARGET | OTHER (stable, hysteresis-voted)
    vote_mass: float   # total vote weight seen for this track

    @property
    def area(self) -> float:
        return max(0.0, self.xyxy[2] - self.xyxy[0]) * max(0.0, self.xyxy[3] - self.xyxy[1])


def assign_owner(det: Detection, persons: list[TrackedPerson]) -> TrackedPerson | None:
    """Owner = smallest person bbox containing the logo centre; otherwise the
    nearest person whose centre is within ~1.2 person-diagonals. None if no
    plausible owner (logo on an LED board, crowd, etc.)."""
    cx, cy = det.cx, det.cy

    containing = [
        p for p in persons
        if p.xyxy[0] <= cx <= p.xyxy[2] and p.xyxy[1] <= cy <= p.xyxy[3]
    ]
    if containing:
        return min(containing, key=lambda p: p.area)

    best, best_d = None, float("inf")
    for p in persons:
        px = (p.xyxy[0] + p.xyxy[2]) / 2
        py = (p.xyxy[1] + p.xyxy[3]) / 2
        diag = float(np.hypot(p.xyxy[2] - p.xyxy[0], p.xyxy[3] - p.xyxy[1]))
        d = float(np.hypot(cx - px, cy - py))
        if d < 1.2 * diag and d < best_d:
            best, best_d = p, d
    return best


class TeamTracker:
    """Stateful across one video. Create per job."""

    def __init__(self, refs: dict | None = None):
        """`refs` may come from the auto-bootstrap (built from the uploaded
        video); when None the refs file at TEAM_REFS_PATH is loaded."""
        self.settings = get_settings()
        self.device = registry.device()

        if refs is None:
            refs_path = Path(self.settings.resolved_team_refs())
            if not refs_path.exists():
                raise FileNotFoundError(
                    f"team refs not found: {refs_path} — enable TEAM_AUTO_REFS or build "
                    "them with `python scripts/build_team_refs.py --video <clip>`")
            with refs_path.open("rb") as f:
                refs = pickle.load(f)
        self.classifier = TeamClassifier.from_refs(refs)
        if TARGET not in self.classifier.teams:
            raise ValueError(f"team refs have no '{TARGET}' team")
        self.voter = VoteTracker(self.classifier.teams, hysteresis=self.settings.team_hysteresis)

        self.person_model = registry.get_person_model()

        self._frame_idx = 0
        # tid -> (frame_idx_of_embedding, emb) — SigLIP refreshed sparsely.
        self._emb_cache: dict[int, tuple[int, np.ndarray]] = {}

    # ── per-frame ────────────────────────────────────────────────────────

    def process(self, frame) -> list[TrackedPerson]:
        """Track + classify all persons in this frame; returns stable labels."""
        self._frame_idx += 1
        s = self.settings

        results = self.person_model.track(
            frame,
            persist=True,
            classes=[0],                      # COCO person
            conf=s.team_person_conf,
            imgsz=s.team_person_imgsz,
            device=self.device,
            tracker="botsort.yaml",
            verbose=False,
        )
        if not results:
            return []
        boxes = getattr(results[0], "boxes", None)
        if boxes is None or boxes.shape[0] == 0:
            return []

        ids = boxes.id
        xyxys = boxes.xyxy.cpu().numpy()
        tids = ids.int().cpu().tolist() if ids is not None else [-1] * len(xyxys)

        # Jersey features for every tracked person.
        regions, masks, quals = [], [], []
        for box in xyxys:
            region, mask = get_jersey_region(frame, box)
            regions.append(region)
            masks.append(mask)
            quals.append(jersey_quality(region, mask))

        # SigLIP — only tracks whose cached embedding is stale (or new).
        need_idx = [
            i for i, tid in enumerate(tids)
            if regions[i] is not None and tid >= 0 and (
                tid not in self._emb_cache
                or self._frame_idx - self._emb_cache[tid][0] >= s.team_siglip_every
            )
        ]
        if need_idx:
            embs = encode_crops_masked(
                [regions[i] for i in need_idx],
                [masks[i] for i in need_idx],
                self.device,
            )
            if embs is not None:
                for j, i in enumerate(need_idx):
                    self._emb_cache[tids[i]] = (self._frame_idx, embs[j])

        out: list[TrackedPerson] = []
        for i, tid in enumerate(tids):
            cf = color_feature(regions[i], masks[i])
            cached = self._emb_cache.get(tid)
            emb = cached[1] if cached is not None else None

            team, conf_cls, margin = self.classifier.classify(emb, cf)
            if tid >= 0 and team is not None:
                # Weight: crop quality × classification margin — ambiguous or
                # blurry frames barely move the vote.
                self.voter.update(tid, team, weight=quals[i] * (0.25 + margin))

            label = self.voter.label(tid) if tid >= 0 else (team or OTHER)
            out.append(TrackedPerson(
                xyxy=tuple(float(v) for v in xyxys[i]),
                track_id=tid,
                team=label,
                vote_mass=self.voter.mass(tid) if tid >= 0 else 0.0,
            ))
        return out

    def annotate(self, dets: list[Detection], persons: list[TrackedPerson]) -> None:
        """Set `on_target_team` on each logo detection (True = keep)."""
        s = self.settings
        for det in dets:
            owner = assign_owner(det, persons)
            if owner is None:
                det.on_target_team = bool(s.team_keep_unassigned)
            elif owner.team == TARGET:
                det.on_target_team = True
            elif owner.vote_mass < s.team_min_votes and s.team_keep_unknown:
                # Not enough evidence yet to trust an OTHER label — keep.
                det.on_target_team = True
            else:
                det.on_target_team = False
