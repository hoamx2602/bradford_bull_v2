"""Runtime team-filter stage: person tracking + team voting + logo filtering.

Per sampled frame:
    1. Track persons (YOLO person model + BoT-SORT, persistent ids).
    2. Per person: jersey crop -> colour feature (every frame) + SigLIP
       embedding (refreshed every `team_siglip_every` frames per track, cached)
       -> fused classification -> quality-weighted vote on the track.
    3. Per logo detection: assign to its owner person (smallest containing
       bbox, else nearest within reach) and keep it only when the owner's
       stable label is TARGET.

Votes decay on accepted updates; a minimum mass and signed consensus margin
control abstention. Uncertain tracks follow the effective `team_keep_unknown`
setting, whose default is True. The home-kit branch uses colour rules only.
"""
from __future__ import annotations

import logging
import pickle
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import cv2

from app.config import get_settings
from app.models_zoo import registry
from app.pipeline.datatypes import Detection
from app.pipeline.teamid.classifier import OTHER, TARGET, UNKNOWN, TeamClassifier, VoteTracker
from app.pipeline.teamid.features import color_feature, encode_crops_masked
from app.pipeline.teamid.jersey import (
    box_trustworthy, boxes_contested, get_jersey_region, jersey_quality,
    bradford_home_evidence,
)

log = logging.getLogger("app.teamid")


@dataclass
class TrackedPerson:
    xyxy: tuple[float, float, float, float]
    track_id: int
    team: str          # TARGET | OTHER | UNKNOWN
    vote_mass: float   # total vote weight seen for this track
    vote_margin: float = 0.0  # signed lead of stable label / total vote mass

    @property
    def area(self) -> float:
        return max(0.0, self.xyxy[2] - self.xyxy[0]) * max(0.0, self.xyxy[3] - self.xyxy[1])


def assign_owner(det: Detection, persons: list[TrackedPerson]) -> TrackedPerson | None:
    """Owner = smallest person bbox containing the logo centre; otherwise the
    nearest person within a small box-edge tolerance. None if no
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
        d = float(np.hypot(cx - px, cy - py))
        # Only allow a small box-edge tolerance. A diagonal-radius search
        # attaches nearby advertising boards and other players' logos.
        bw, bh = p.xyxy[2] - p.xyxy[0], p.xyxy[3] - p.xyxy[1]
        near_box = (p.xyxy[0] - 0.2 * bw <= cx <= p.xyxy[2] + 0.2 * bw
                    and p.xyxy[1] - 0.05 * bh <= cy <= p.xyxy[3] + 0.05 * bh)
        if near_box and d < best_d:
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
        self.kit = refs.get("meta", {}).get("kit")
        if TARGET not in self.classifier.teams:
            raise ValueError(f"team refs have no '{TARGET}' team")
        self.voter = VoteTracker(self.classifier.teams, hysteresis=self.settings.team_hysteresis,
                                 decay=self.settings.team_vote_decay)

        self.person_model = registry.get_person_model()
        # A new job must not inherit BoT-SORT identities from a previous video.
        predictor = getattr(self.person_model, "predictor", None)
        for tracker in getattr(predictor, "trackers", []):
            tracker.reset()

        self._frame_idx = 0
        # tid -> (frame_idx_of_embedding, emb) — SigLIP refreshed sparsely.
        self._emb_cache: dict[int, tuple[int, np.ndarray]] = {}
        self._previous_scene = None

    def _scene_changed(self, frame) -> bool:
        small = cv2.resize(frame, (64, 36))
        hist = cv2.calcHist([cv2.cvtColor(small, cv2.COLOR_BGR2HSV)], [0, 1], None,
                            [16, 8], [0, 180, 0, 256])
        cv2.normalize(hist, hist)
        previous = self._previous_scene
        self._previous_scene = (small, hist)
        if previous is None:
            return False
        difference = float(np.abs(small.astype(np.float32) - previous[0]).mean())
        distance = cv2.compareHist(hist, previous[1], cv2.HISTCMP_BHATTACHARYYA)
        return difference > 20 and distance > .28

    # ── per-frame ────────────────────────────────────────────────────────

    def process(self, frame) -> list[TrackedPerson]:
        """Track + classify all persons in this frame; returns stable labels."""
        self._frame_idx += 1
        s = self.settings
        if self._scene_changed(frame):
            # Highlight reels cut abruptly between unrelated player identities.
            # Reset both identities and votes; a box ID must not carry an old
            # team's label across a broadcast cut.
            for tracker in getattr(getattr(self.person_model, "predictor", None), "trackers", []):
                tracker.reset()
            self.voter = VoteTracker(self.classifier.teams, hysteresis=s.team_hysteresis,
                                     decay=s.team_vote_decay)
            self._emb_cache.clear()

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

        # Jersey features for every tracked person. Two kinds of box get zero
        # vote weight (label still shown from accumulated votes):
        #   - untrustworthy: clipped at the frame top / squat partial bodies —
        #     their "shirt band" is some other body part (a touchline
        #     official's trousers mislabelled a whole track this way);
        #   - contested: heavily overlapped by another person box (tackles,
        #     mauls) — the band mixes both players' kits, so votes there are
        #     noise either way. Labels rely on clean, separated views.
        frame_h = frame.shape[0]
        contested = boxes_contested(xyxys)
        regions, masks, quals = [], [], []
        for i, box in enumerate(xyxys):
            region, mask = get_jersey_region(frame, box)
            regions.append(region)
            masks.append(mask)
            ok = box_trustworthy(box, frame_h) and not contested[i]
            quals.append(jersey_quality(region, mask) if ok else 0.0)

        # SigLIP — only tracks whose cached embedding is stale (or new).
        need_idx = [
            i for i, tid in enumerate(tids)
            if self.kit != "home" and regions[i] is not None and quals[i] > 0 and tid >= 0 and (
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
            if self.kit == "home":
                # The configured Bradford home kit has known white/red/yellow
                # colours. Generic cluster centroids mix shaded views, so use
                # explicit colour evidence and abstain when it is ambiguous.
                team = bradford_home_evidence(regions[i])
                margin = .75 if team is not None else 0.0
            if tid >= 0 and team is not None and margin >= 0.1:
                # Weight: crop quality × classification margin — ambiguous or
                # blurry frames barely move the vote.
                self.voter.update(tid, team, weight=quals[i] * (0.25 + margin))

            label = self.voter.label(tid) if tid >= 0 else UNKNOWN
            vote_margin = self.voter.margin(tid, label)
            if vote_margin < s.team_min_vote_margin:
                label = UNKNOWN
            out.append(TrackedPerson(
                xyxy=tuple(float(v) for v in xyxys[i]),
                track_id=tid,
                team=label,
                vote_mass=self.voter.mass(tid) if tid >= 0 else 0.0,
                vote_margin=vote_margin,
            ))
        return out

    def annotate(self, dets: list[Detection], persons: list[TrackedPerson]) -> None:
        """Set `on_target_team` on each logo detection (True = keep)."""
        s = self.settings
        for det in dets:
            owner = assign_owner(det, persons)
            if owner is None:
                det.on_target_team = bool(s.team_keep_unassigned)
            elif owner.team == UNKNOWN or owner.vote_mass < s.team_min_votes:
                det.on_target_team = bool(s.team_keep_unknown)
            elif owner.team == TARGET:
                det.on_target_team = True
            else:
                det.on_target_team = False
