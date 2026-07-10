# Paper Outline v4 — Accessible Sponsor-Exposure Analytics for Small/Mid-Tier Clubs

> Full outline, English, framing = **accessibility/democratization** (agreed direction):
> large/rich clubs already have enterprise vendors (Nielsen, GumGum/Zoomph, Relo Metrics,
> Shikenso) or in-house data teams; small/mid-tier clubs (like Bradford Bulls) don't.
> This framework is an open, self-hostable, commodity-hardware alternative built from
> open-source components. Every place a real number/measurement is needed is marked
> **[NEED DATA: ...]** — fill these in before drafting prose.

---

## Title (candidates)

1. "Sponsor Exposure Analytics for the Rest of Us: An Open, Self-Hostable Framework for
   Small and Mid-Tier Sports Clubs"
2. "Who Owns This Logo? Team-Attribution and Slot-Level Pricing in an Accessible
   Sponsor-Analytics Framework"
3. "Beyond Enterprise Vendors: A Commodity-Hardware, Open-Source Pipeline for Sponsor
   Exposure and Media Valuation in Sports Broadcasts"

> Recommendation: #1 leads with the accessibility hook (strong, memorable); #2 keeps the
> technical differentiator (team-attribution) in the title if the venue skews technical.

---

## Abstract — what to write

Four moves, in this order:

1. **Problem + who is underserved.** Sponsor exposure measurement (turning broadcast
   video into exposure-seconds / visibility% / EMV) is a solved problem for clubs that
   can afford Nielsen Sports, GumGum/Zoomph, Relo Metrics, or Shikenso — or that build an
   in-house data-science team. The majority of professional clubs outside the top-revenue
   leagues can do neither.
2. **What's actually hard, not just "detection".** Two obstacles remain even with a
   working detector: (a) the same sponsor often appears on *both* competing teams' kits
   / boards / referees, so raw detection over-counts unless ownership is resolved; (b)
   sponsors are priced by *placement* (chest-centre vs. sock), not just aggregate
   screen-time, and no published system attributes exposure at that granularity.
3. **What you built.** An end-to-end, self-hosted framework — fine-tuned open-weight
   detector, training-free team-attribution (reference bootstrap + vote hysteresis), a
   3-tier visibility→exposure→EMV pipeline, 18-slot body-zone pricing, and a
   multi-match dashboard — assembled entirely from open-source models/libraries,
   deployable on commodity hardware, deployed and validated on a real rugby-league club.
4. **Evidence + scope statement.** One or two headline numbers **[NEED DATA: pick the
   2 strongest — likely clip-split detector mAP and a team-filter precision figure once
   you have it across more than 2 clips]**, then one sentence stating this is a systems/
   accessibility contribution, not an accuracy record (you are not claiming SOTA
   detection).

**[NEED DATA before finalizing abstract]**: final clip-split mAP@0.5 (currently 0.65,
confirm on a larger held-out set); team-filter precision/recall across ≥10–20 clips;
at least one concrete hardware/cost data point (e.g., "runs end-to-end on a single
consumer GPU / an M-series Mac" — you already support this, just need to state which
config you'll cite); one annotation-time number (hours spent per sponsor class).

---

## 1. Introduction

**Opening anecdote (write this first — it's your strongest hook):** open with Bradford
Bulls specifically, not "small clubs" in the abstract. One or two sentences: a
professional rugby-league club that sells sponsor slots on its kit but, like most clubs
outside the top handful of leagues, has no in-house data-science team and no enterprise
sponsorship-analytics contract.

**Then, the access gap, evidenced not asserted:**
- Name the existing commercial layer (Nielsen Sponsorship Media Value Benchmarking
  report as evidence the category exists; GumGum/Zoomph, Relo Metrics, Shikenso as SaaS
  vendors) — cite them as "the category is served by proprietary platforms," not as
  "these companies are too expensive" (you cannot verify pricing, so don't assert it).
- State the two structural costs of enterprise/in-house systems that this paper targets
  directly: (i) vendor lock-in / recurring SaaS cost / sending your video+commercial
  data to a third party (data-sovereignty angle — a genuinely underused argument, worth
  a full sentence); (ii) requiring in-house ML expertise most clubs don't have.
- **Be precise about which kind of "accessible" you mean.** Self-hosting removes cost
  and vendor lock-in, but it does *not* remove technical setup effort — running this
  stack still requires someone who can manage Python/GPU/ffmpeg/model versions
  (`docs/09-operations.md` alone lists several version-pinning gotchas). Don't let the
  Introduction imply "any club, zero technical skill" — the honest claim is "clubs with
  *some* technical capacity but no analytics budget or vendor contract," which is a
  narrower, more defensible scope. State this explicitly rather than let a reviewer
  infer the gap themselves.

**Then pivot to the technical gap** (this is where the paper earns its place next to
ExposureEngine, arXiv 2510.04739): even a good open detector alone doesn't solve
sponsor-exposure measurement, because of team-attribution (same sponsor on both kits)
and placement-based pricing (no published system does slot-level attribution).

**Contributions list** (numbered, ends the Introduction):
- C1 — Team-attribution formulation + training-free solution (reference bootstrap,
  color+embedding fusion, vote hysteresis, revenue-safe default policy).
- C2 — Zero-manual-setup, 3-tier reference bootstrap (manual override → kit-anchor
  auto-cluster → luminance heuristic).
- C3 — Body-zone / slot-level pricing (18 slots via pose keypoints) — the placement-aware
  pricing granularity missing from prior systems.
- C4 — **An open reference architecture assembled entirely from open-source
  models/libraries, deployable on commodity hardware, with infra abstracted behind
  swappable interfaces (SQLite→Postgres, local disk→S3, in-process queue→Celery) so a
  club can start at near-zero infrastructure cost and scale only if/when needed** — this
  is the accessibility contribution, stated as a concrete engineering property, not a
  slogan. **Caveat: whether this counts as a "contribution" vs. an engineering choice
  depends on the target venue/track (systems/applications vs. pure CV/ML) — decide this
  with your advisor before drafting Method, since it changes how much space C4 deserves.**
- C5 — Production-grade design lessons (2-pass sampled/full-fps detection, graceful
  degradation) and calibration lessons (leakage-prone vs honest train/test split;
  literature-default visibility thresholds too strict for real broadcast logos).

> **Scope check:** five contributions may be too many for one paper to argue with equal
> weight. Before drafting, pick 2–3 as headline claims (likely candidates: C1
> team-attribution + C3 slot-pricing + the accessibility framing) and demote the rest
> (C2, C5) to supporting material inside Method/Discussion. Confirm this split with your
> advisor — it affects how the abstract and contributions list should read.

---

## 2. Related Work — what to write in each paragraph

1. **General logo detection.** One paragraph, cite the logo-detection survey literature;
   conclusion: detection is a mostly-solved building block, not the contribution.
2. **Team classification / jersey-based re-identification in sports video — do not
   skip this, it is directly relevant to C1's method, not just background.** This is an
   established sub-field with recent work: "Multi-task Learning for Joint
   Re-identification, Team Affiliation, and Role Classification for Sports Visual
   Tracking" (arXiv 2401.09942); "Single-Stage Uncertainty-Aware Jersey Number
   Recognition in Soccer" (CVPR 2025 workshop, CVSPORTS); "Soccer player recognition
   using spatial constellation features and jersey number recognition" (ScienceDirect);
   general surveys such as "A Comprehensive Review of Computer Vision in Sports" (arXiv
   2203.02281). Most of this literature does color-histogram or embedding clustering for
   team assignment *per frame*; your contribution on top is the **track-level vote with
   hysteresis + the zero-manual-setup kit-anchor bootstrap + the revenue-safe keep/drop
   policy** — say this explicitly, as the differentiation, not just "we also do team
   classification."
3. **Virtual advertising insertion / billboard detection in sports broadcasts — classic,
   decades-old area, also currently missing.** E.g. "Implanting Virtual Advertisement
   into Broadcast Soccer Video"; "Automated Billboard Insertion in Video"; "Billboard
   advertisement detection in sport TV" (HAL). This line of work already solves
   *locating* static ad surfaces via homography/planar-surface detection — relevant
   context for your billboard/board-side handling (as opposed to jersey logos), and
   worth one sentence distinguishing your problem (measuring exposure of *existing* real
   ads) from theirs (inserting/replacing ads).
4. **ExposureEngine (arXiv 2510.04739) — closest academic work.** Summarize honestly:
   OBB detector, mAP@0.5 0.859, soccer, visibility/exposure analytics + NL "agentic"
   query layer. State plainly what it does *not* cover: team/opponent-overlap
   attribution, placement-level pricing, and it does not discuss deployability/cost —
   its framing is purely technical-accuracy, not access.
5. **Commercial/industry systems.** Nielsen, GumGum/Zoomph, Relo Metrics, Shikenso,
   relevant patents (e.g. brand screen-time patents). Frame as: proven the market exists
   and the problem is commercially important, but methods are closed, unpublished,
   non-reproducible, and — as far as public material shows — targeted at top-tier
   properties with the budget for a vendor contract.
6. **Closing sentence — the actual gap statement:** no published work simultaneously
   addresses (a) team/opponent overlap, (b) placement-level pricing, and (c) deployment
   accessibility for clubs without enterprise budgets or in-house ML teams.

**[NEED DATA: none for the gap-statement logic]**, but two real to-dos: (a) the search
behind items 2–3 above was a handful of targeted queries, not a systematic literature
review — do a proper pass (DBLP/Google Scholar, keywords: "team classification sports
video", "jersey re-identification", "billboard detection broadcast", also check
MMSports/CVsports workshop proceedings directly) before finalizing; (b) double-check
ExposureEngine's final published venue/version before submission (it was last confirmed
"submitted to IEEE" as of Oct 2025 — verify acceptance status closer to your submission
date).

---

## 3. System Architecture

One figure (pipeline diagram: upload → orchestrator stages → detect → team-filter →
pose/body-zone → exposure aggregation → EMV pricing → dashboard), one paragraph per
stage, plus one paragraph explicitly on the **accessibility-relevant engineering
choices**: infra behind swappable interfaces, sensible defaults (SQLite, local storage,
in-process job queue) that require zero setup, optional promotion path to
Postgres/S3/Celery only when a club's volume actually needs it, CPU/MPS/CUDA device
fallback (so a club without a GPU server can still run it, slower).

**[NEED DATA]**: pick one concrete deployment configuration to report as a worked
example, e.g. "single RTX 5060 Ti" or "Apple M-series, CPU/MPS fallback" — state
end-to-end processing time for a fixed video length on that hardware (minutes of video
in vs. wall-clock minutes out). This single number is probably your best piece of
accessibility evidence — prioritize measuring it.

---

## 4. Method

### 4.1 Detector (manual annotation, open-weight model)
Describe: YOLO26 fine-tune, 16 sponsor classes, model-assisted labeling loop (annotate
50–80 clean images → train v1 → Label-Assist-suggested boxes → accept/fix → retrain),
Roboflow-based workflow, augmentation policy, 70/20/10 split.
**[NEED DATA]**: final class count and per-class instance counts in the training set
you'll report in the paper; confirm which run (`logo_yolo26m_clipsplit` or a newer one)
is the one you're citing as "final."

### 4.2 Team-attribution (C1/C2)
Describe the pipeline: YOLO11 person + BoT-SORT track → jersey crop → fuse(color
histogram, SigLIP embedding) → VoteTracker with hysteresis → owner resolution → keep/drop
policy (insufficient evidence → keep, i.e. never silently reduce a customer's counted
exposure without positive evidence of opponent ownership). State the 3-tier bootstrap
(manual refs → kit-anchor auto-cluster → luminance heuristic) as the "zero manual setup"
claim.
Explicitly relate this subsection to the team-classification literature added in
Related Work (§2 item 2): state what's standard (color/embedding clustering for team
assignment) vs. what's yours (track-level hysteresis voting, zero-manual-setup
bootstrap, revenue-safe policy) — don't let 4.2 read as if team classification itself is
novel.

**[NEED DATA]**: quantitative precision/recall of team-attribution over a labeled sample
of clips (see Experiments — currently only 2 case-study clips exist; need more before
this subsection can cite a real number instead of "we observed correct attribution in
early testing"). Sample must cover more than one lighting condition/opponent kit, not
just repeats of the same match — a precision number from 15 near-identical clips has
weak external validity and will be an easy target in review.

### 4.3 Visibility → Exposure → EMV (3-tier formula)
**Open with an explicit attribution sentence**: this 3-tier formula is *adapted from*
ExposureEngine / Relo Metrics / Shikenso industry practice (cite them here, not just in
Related Work) — it is not being presented as a novel formula. State clearly what you
changed vs. inherited: (a) recalibrated the visibility floor for real, small,
off-centre broadcast logos (literature default ~0.1 discards nearly everything; you use
a much lower, empirically-set floor); (b) extended the formula down to slot level (C3),
which the source formulas don't do. Failing to say this plainly risks the subsection
reading as claiming the base formula as your own — flag this to your advisor explicitly
before drafting, it's an easy fix now and a hard one to explain later.
**[NEED DATA]**: the actual visibility-floor value you'll defend in the paper (currently
0.02 in code) plus, ideally, a small sensitivity plot/table of exposure-seconds vs.
threshold value to justify the choice quantitatively rather than just asserting it.

### 4.4 Body-zone / slot-level pricing (C3)
Describe pose-keypoint-driven assignment into 18 kit slots, and how slot-level exposure
share feeds placement-based pricing (a slot shown more often should be priced higher).
**[NEED DATA]**: any measurement of body-zone assignment accuracy (how often is a
detection assigned to the correct slot vs. ground truth) — currently not measured
anywhere in the project logs; likely needs a small manual-audit sample.

---

## 5. Experiments — table of what exists vs. what to measure

**Already have (real numbers, cite directly):**

| Item | Number | Source |
|---|---|---|
| Detector, frame-level split (optimistic, leakage risk) | mAP50 0.84 | `logo_yolo26m` |
| Detector, clip-level split (honest, no leakage) | mAP50 0.65 | `logo_yolo26m_clipsplit` |
| Team-filter case study, clip A | kept 6 / dropped 0, correct zone | `docs/04-team-filter.md` |
| Team-filter case study, clip B | kept 15 / dropped 1, correct zone despite only 8/39 bootstrap crops from target team | `docs/04-team-filter.md` |
| Real per-match exposure output | `exposure_report.csv` (M05 match) | production run |

**Must measure before submission — this is the actual to-do list, prioritized for the
accessibility framing:**

1. **[NEED DATA] Hardware/cost benchmark** (highest priority for this framing): wall-clock
   processing time per minute of video on at least one concrete, named commodity
   configuration (e.g. single consumer GPU, or CPU-only/Mac). This is the single most
   important number the accessibility argument needs and currently doesn't have.
2. **[NEED DATA] Annotation time cost**: actual hours spent annotating per sponsor class
   with the model-assisted loop, vs. a naive full-manual estimate — turns "our annotation
   burden is modest" from a claim into a number.
3. **[NEED DATA] Team-attribution precision/recall** on ≥10–20 labeled clips spanning
   more than one match/lighting condition/opponent kit (currently 2 case studies only,
   s