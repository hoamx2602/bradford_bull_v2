"""
Fused team classifier — colour histogram  +  SigLIP, combined per detection.

Why fusion
----------
The two Bradford kits are white (home) vs black (away): a luminance/colour
histogram of the *shirt pixels* separates them almost perfectly and is immune
to grass.  SigLIP adds pattern/texture cues when colour is ambiguous (e.g. two
similarly-toned kits).  The relative weight of the two is *learned from the
reference crops themselves* (`learn_weights`), so colour dominates for
white-vs-black yet SigLIP can take over for harder kit pairs.

Scoring
-------
Each feature produces a softmax distribution over teams; the fused
distribution is `w_color * p_color + w_siglip * p_siglip`.  We return the
argmax team, its probability (confidence) and the top1-top2 margin so the
caller can down-weight or abstain on ambiguous frames.
"""
import cv2
import numpy as np

# Colour histogram layout: L (luminance) bins  +  H (hue) bins.
N_L = 8     # luminance bins  (white vs black lives here)
N_H = 12    # hue bins        (separates coloured kits)
SAT_MIN = 40   # only saturated pixels vote for hue

COLOR_DIM = N_L + N_H


# ── Colour feature ────────────────────────────────────────────────────────────

def color_feature(region_bgr: np.ndarray, pixel_mask: np.ndarray) -> np.ndarray | None:
    """
    L1-normalised [L-hist (N_L) | H-hist (N_H)] over the kept shirt pixels.
    Returns None if there are too few pixels to be meaningful.
    """
    if region_bgr is None or pixel_mask is None:
        return None
    m = pixel_mask.astype(bool)
    if m.sum() < 5:
        return None

    px_bgr = region_bgr[m].reshape(-1, 1, 3).astype(np.uint8)

    lab = cv2.cvtColor(px_bgr, cv2.COLOR_BGR2LAB).reshape(-1, 3)
    L   = lab[:, 0]
    l_hist, _ = np.histogram(L, bins=N_L, range=(0, 256))
    l_hist = l_hist.astype(np.float32)
    l_hist /= (l_hist.sum() + 1e-8)

    hsv = cv2.cvtColor(px_bgr, cv2.COLOR_BGR2HSV).reshape(-1, 3)
    sat_ok = hsv[:, 1] > SAT_MIN
    if sat_ok.sum() >= 3:
        Hh = hsv[sat_ok, 0]
        h_hist, _ = np.histogram(Hh, bins=N_H, range=(0, 180))
        h_hist = h_hist.astype(np.float32)
        h_hist /= (h_hist.sum() + 1e-8)
    else:
        h_hist = np.zeros(N_H, dtype=np.float32)

    return np.concatenate([l_hist, h_hist]).astype(np.float32)


def color_sim(fq: np.ndarray, fr: np.ndarray) -> float:
    """Histogram-intersection similarity in [0,1] (L-block weighted higher)."""
    Lq, Hq = fq[:N_L], fq[N_L:]
    Lr, Hr = fr[:N_L], fr[N_L:]
    sim_l = float(np.minimum(Lq, Lr).sum())
    sim_h = float(np.minimum(Hq, Hr).sum())
    return 0.65 * sim_l + 0.35 * sim_h


def _softmax(x: np.ndarray) -> np.ndarray:
    x = x - x.max()
    e = np.exp(x)
    return e / (e.sum() + 1e-8)


# ── Classifier ────────────────────────────────────────────────────────────────

class TeamClassifier:
    """Built from a saved refs dict; classifies one detection at a time."""

    def __init__(self, teams, centroids, colors,
                 w_color, w_siglip, temp_c=8.0, temp_s=15.0, min_margin=0.05):
        self.teams      = list(teams)
        self.centroids  = centroids          # team -> (D,) L2-normalised  | None
        self.colors     = colors             # team -> (COLOR_DIM,)        | None
        self.w_color    = float(w_color)
        self.w_siglip   = float(w_siglip)
        self.temp_c     = float(temp_c)
        self.temp_s     = float(temp_s)
        self.min_margin = float(min_margin)
        self._has_color = all(colors.get(t)    is not None for t in teams)
        self._has_sig   = all(centroids.get(t) is not None for t in teams)

    def classify(self, emb: np.ndarray | None, color_feat: np.ndarray | None):
        """
        Returns (team, confidence, margin) or (None, 0.0, 0.0) if neither
        feature is usable for this detection.
        """
        dists, weights = [], []

        if color_feat is not None and self._has_color and self.w_color > 0:
            s = np.array([color_sim(color_feat, self.colors[t]) for t in self.teams])
            dists.append(_softmax(self.temp_c * s));  weights.append(self.w_color)

        if emb is not None and self._has_sig and self.w_siglip > 0:
            s = np.array([float(emb @ self.centroids[t]) for t in self.teams])
            dists.append(_softmax(self.temp_s * s));   weights.append(self.w_siglip)

        if not dists:
            return None, 0.0, 0.0

        w = np.array(weights);  w /= w.sum()
        p = sum(wi * di for wi, di in zip(w, dists))

        order = np.argsort(p)[::-1]
        top   = int(order[0])
        margin = float(p[order[0]] - (p[order[1]] if len(order) > 1 else 0.0))
        return self.teams[top], float(p[top]), margin

    # ── (de)serialisation ─────────────────────────────────────────────────────

    @classmethod
    def from_refs(cls, refs: dict) -> 'TeamClassifier':
        teams     = list(refs['teams'].keys())
        centroids = {t: refs['teams'][t].get('embedding') for t in teams}
        colors    = {t: refs['teams'][t].get('color')     for t in teams}
        m         = refs.get('meta', {})
        return cls(teams, centroids, colors,
                   w_color=m.get('w_color', 0.5), w_siglip=m.get('w_siglip', 0.5),
                   temp_c=m.get('temp_c', 8.0),   temp_s=m.get('temp_s', 15.0),
                   min_margin=m.get('min_margin', 0.05))


# ── Weight learning (used by ref_build) ───────────────────────────────────────

def learn_weights(teams, assignments, embeddings, color_feats):
    """
    Decide w_color vs w_siglip from how well each feature *classifies* the
    labelled reference crops (nearest team-centroid accuracy).

    Accuracy is scale-free, so colour (histogram-intersection) and SigLIP
    (cosine) are compared fairly — unlike raw similarity gaps, which differ in
    magnitude and unfairly favour SigLIP.  For white-vs-black kits colour
    reaches ~100% accuracy and is weighted accordingly.

    Returns (w_color, w_siglip, team_centroids, team_colors).
    """
    idx_by_team = {t: [i for i, a in enumerate(assignments) if a == t] for t in teams}
    idx_by_team = {t: ix for t, ix in idx_by_team.items() if ix}
    valid_teams = list(idx_by_team.keys())

    # Team means.
    centroids, colors = {}, {}
    for t in teams:
        ix = idx_by_team.get(t, [])
        if not ix:
            centroids[t] = None; colors[t] = None; continue
        c = embeddings[ix].mean(axis=0)
        centroids[t] = c / (np.linalg.norm(c) + 1e-8)
        cf = [color_feats[i] for i in ix if color_feats[i] is not None]
        colors[t] = np.mean(cf, axis=0) if cf else None

    def accuracy(kind):
        if len(valid_teams) < 2:
            return 0.0
        correct = total = 0
        for t in valid_teams:
            for i in idx_by_team[t]:
                if kind == 'siglip':
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
                correct += int(pred == t); total += 1
        return correct / total if total else 0.0

    chance = 1.0 / max(len(valid_teams), 2)
    adv_c  = max(accuracy('color')  - chance, 1e-3)
    adv_s  = max(accuracy('siglip') - chance, 1e-3)
    w_color = float(np.clip(adv_c / (adv_c + adv_s), 0.1, 0.9))
    return w_color, 1.0 - w_color, centroids, colors
