"""Fused team classifier + temporal voting.

TeamClassifier: each feature (colour, SigLIP) produces a softmax distribution
over teams; fused as w_color*p_color + w_siglip*p_siglip. Weights are learned
from the reference crops (learn_weights) so colour dominates for white-vs-black
kits while SigLIP can take over for harder pairs.

VoteTracker: per-track majority voting with hysteresis — one bad frame can't
flip a player's team, and the shown label never flickers.
"""
from __future__ import annotations

import numpy as np

from app.pipeline.teamid.features import color_sim, softmax

TARGET = "target"
OTHER = "other"


class TeamClassifier:
    """Built from a saved refs dict; classifies one jersey crop at a time."""

    def __init__(self, teams, centroids, colors,
                 w_color: float, w_siglip: float,
                 temp_c: float = 8.0, temp_s: float = 15.0):
        self.teams = list(teams)
        self.centroids = centroids   # team -> (D,) L2-normalised | None
        self.colors = colors         # team -> (COLOR_DIM,) | None
        self.w_color = float(w_color)
        self.w_siglip = float(w_siglip)
        self.temp_c = float(temp_c)
        self.temp_s = float(temp_s)
        self._has_color = all(colors.get(t) is not None for t in teams)
        self._has_sig = all(centroids.get(t) is not None for t in teams)

    def classify(self, emb: np.ndarray | None, color_feat: np.ndarray | None):
        """Returns (team, confidence, margin), or (None, 0, 0) if no usable feature."""
        dists, weights = [], []

        if color_feat is not None and self._has_color and self.w_color > 0:
            s = np.array([color_sim(color_feat, self.colors[t]) for t in self.teams])
            dists.append(softmax(self.temp_c * s))
            weights.append(self.w_color)

        if emb is not None and self._has_sig and self.w_siglip > 0:
            s = np.array([float(emb @ self.centroids[t]) for t in self.teams])
            dists.append(softmax(self.temp_s * s))
            weights.append(self.w_siglip)

        if not dists:
            return None, 0.0, 0.0

        w = np.array(weights)
        w /= w.sum()
        p = sum(wi * di for wi, di in zip(w, dists))

        order = np.argsort(p)[::-1]
        top = int(order[0])
        margin = float(p[order[0]] - (p[order[1]] if len(order) > 1 else 0.0))
        return self.teams[top], float(p[top]), margin

    @classmethod
    def from_refs(cls, refs: dict) -> "TeamClassifier":
        if "teams" not in refs:
            raise ValueError(
                "Invalid team refs file — rebuild with scripts/build_team_refs.py")
        teams = list(refs["teams"].keys())
        centroids = {t: refs["teams"][t].get("embedding") for t in teams}
        colors = {t: refs["teams"][t].get("color") for t in teams}
        m = refs.get("meta", {})
        return cls(
            teams, centroids, colors,
            w_color=m.get("w_color", 0.5), w_siglip=m.get("w_siglip", 0.5),
            temp_c=m.get("temp_c", 8.0), temp_s=m.get("temp_s", 15.0),
        )


class VoteTracker:
    """Per-track vote accumulation + hysteresis-stabilised label."""

    def __init__(self, teams: list[str], hysteresis: float = 1.25):
        self.teams = list(teams)
        self.hyst = hysteresis
        self.votes: dict[int, np.ndarray] = {}   # tid -> vote mass per team
        self.shown: dict[int, str] = {}          # tid -> stable label

    def update(self, tid: int, team: str | None, weight: float) -> None:
        v = self.votes.setdefault(tid, np.zeros(len(self.teams)))
        if team is not None and weight > 0:
            v[self.teams.index(team)] += weight

    def label(self, tid: int) -> str:
        v = self.votes.get(tid)
        if v is None or v.sum() == 0:
            return self.shown.get(tid, self.teams[0])
        top = int(np.argmax(v))
        cur = self.shown.get(tid)
        if cur is None:
            self.shown[tid] = self.teams[top]
        else:
            ci = self.teams.index(cur)
            if top != ci and v[top] > v[ci] * self.hyst:
                self.shown[tid] = self.teams[top]
        return self.shown[tid]

    def mass(self, tid: int) -> float:
        """Total vote weight seen for this track — confidence proxy."""
        v = self.votes.get(tid)
        return float(v.sum()) if v is not None else 0.0


def learn_weights(teams, assignments, embeddings, color_feats):
    """Learn w_color vs w_siglip from labelled reference crops.

    Each feature's weight is proportional to its advantage over chance when
    classifying the reference crops by nearest team centroid. Accuracy is
    scale-free so colour (hist-intersection) and SigLIP (cosine) compare fairly.

    Returns (w_color, w_siglip, team_centroids, team_colors).
    `embeddings` may be None (colour-only refs).
    """
    idx_by_team = {t: [i for i, a in enumerate(assignments) if a == t] for t in teams}
    idx_by_team = {t: ix for t, ix in idx_by_team.items() if ix}
    valid_teams = list(idx_by_team.keys())

    centroids: dict[str, np.ndarray | None] = {}
    colors: dict[str, np.ndarray | None] = {}
    for t in teams:
        ix = idx_by_team.get(t, [])
        if not ix:
            centroids[t] = None
            colors[t] = None
            continue
        if embeddings is not None:
            c = embeddings[ix].mean(axis=0)
            centroids[t] = c / (np.linalg.norm(c) + 1e-8)
        else:
            centroids[t] = None
        cf = [color_feats[i] for i in ix if color_feats[i] is not None]
        colors[t] = np.mean(cf, axis=0) if cf else None

    def accuracy(kind: str) -> float:
        if len(valid_teams) < 2:
            return 0.0
        correct = total = 0
        for t in valid_teams:
            for i in idx_by_team[t]:
                if kind == "siglip":
                    if embeddings is None:
                        continue
                    scores = {o: float(embeddings[i] @ centroids[o])
                              for o in valid_teams if centroids[o] is not None}
                else:
                    if color_feats[i] is None:
                        continue
                    scores = {o: color_sim(color_feats[i], colors[o])
                              for o in valid_teams if colors[o] is not None}
                if not scores:
                    continue
                pred = max(scores, key=scores.get)
                correct += int(pred == t)
                total += 1
        return correct / total if total else 0.0

    chance = 1.0 / max(len(valid_teams), 2)
    adv_c = max(accuracy("color") - chance, 1e-3)
    adv_s = max(accuracy("siglip") - chance, 1e-3)
    if embeddings is None:
        return 1.0, 0.0, centroids, colors
    w_color = float(np.clip(adv_c / (adv_c + adv_s), 0.1, 0.9))
    return w_color, 1.0 - w_color, centroids, colors
