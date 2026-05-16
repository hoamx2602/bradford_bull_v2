# Bradford Bulls — Solution Architecture v4

> **Status:** Pre-implementation feasibility document — final spec for green-light
> **Date:** 2026-05-15 (revised after Q&A round)
> **Replaces:** PROJECT_SPECIFICATION.md (outdated taxonomy), plan-2026-04-17.md (incorporated + corrected)
> **Purpose:** Single source of truth describing WHAT we are building, WHY each design choice was made, and HOW it grounds in published industry/academic practice — BEFORE writing any production code.
> **Important:** No production code exists yet. Earlier docs (`plan-2026-04-17.md`, `frame_extraction_techniques.md`, etc.) are DESIGN documents describing what to build, not what was already built. This v4 is the canonical implementation spec.

---

## 0. TL;DR (1 page)

We are building an AI system that, given a 90-minute rugby league broadcast video, outputs a per-sponsor exposure report (seconds on screen, weighted by visibility quality) that the club can use to objectively re-rank current pricing of jersey/shorts/sock sponsor positions.

**Five insights from the Q&A round shaped the final spec:**

1. **Brand-centric, not position-centric taxonomy.** The classifier learns the *visual identity* of each brand (TopNotch, AON, KLG, MCP, Floor Tonic …) defined by the canonical files in `/Sponsor Logo/`, regardless of where on the kit it appears. Position is computed downstream as metadata from each detection's bbox center within its player crop.
2. **Keep ALL canonical brands as classes**, even those not visible on the current 2025/26 kit (Paints & Lacquers, Cedar Court Hotels, etc.). User clarified: future matches may surface them; classes with 0 detections in current matches are accepted "low-confidence / placeholder" classes that gain training data when kit changes.
3. **Color variants are separate classes** (e.g., `mcp_dark` vs `mcp_white`). User explicit. Visually distinct artwork = distinct class.
4. **The pricing CSV is fixed and is the OUTPUT-side reference, not an input.** We never assert "logo X = £Y." We measure exposure per BRAND, aggregate per POSITION as metadata, then the club uses that evidence to re-allocate the existing % weights — that re-allocation IS the product output.
5. **The current spec doc is partially wrong.** Audit of the actual 2025/26 KIT vs. spec found: AON is on shorts (not chest); TopNotch is the HOME main sponsor on chest (not on socks); Floor Tonic is the AWAY main sponsor (no position in spec); EM Workwear is the sock sponsor; "Fairway Flooring" file actually shows "Fairway Roofing"; one logo file is 0 bytes. We rebuild the taxonomy.

**The pipeline (5 stages, each grounded in a published source):**

| Stage | What | Grounded in |
|-------|------|-------------|
| 1. Smart frame extraction | Tiered torso-sharpness, overlay-masked, team-aware quota selection | **To build from scratch.** Design from `frame_extraction_techniques.md` + `team_aware_frame_extraction_proposal.md` |
| 2. Annotation + temporal propagation | OBB on Roboflow, ±3 frame propagation, hard-negative + LED + opponent + crowd background mining | ExposureEngine (arXiv 2510.04739) uses OBB; hard-negative is canonical FP-control technique |
| 3. Detection model | YOLOv11-Medium with OBB head, imgsz 1280, Varifocal loss, motion-blur augmentation | ExposureEngine SOTA: 0.859 mAP@0.5 on Swedish elite soccer with 1,103 frames |
| 4. Inference: Crop-and-Detect + Track-and-Infer | YOLOv11l person detect → BoT-SORT track → crop player → logo OBB on crop → per-track binding → temporal inference | SoccerNet 2023 tracking SOTA uses YOLOv8l + DeepOC-SORT++; crop-and-detect is industry consensus for small-object detection |
| 5. 4-Layer exposure measurement | Dedupe → smoothing → Quality Index → reporting (with configurable min-duration filter, default 2s per MRC) | MRC viewability standard (50% pixels × **2 continuous seconds**); Nielsen QI Score concept (proprietary weights, public concept) |

**Feasibility verdict:** **Achievable.** ExposureEngine (Oct 2025) demonstrated 0.859 mAP@0.5 on a comparable problem with only 1,103 annotated frames and a single A100. We currently have **3 videos** (M01 102min HOME 1080p, M02 96min HOME 720p, M06 11.5min AWAY highlights 1080p) — sufficient for POC per user direction. We can match or exceed ExposureEngine's detection accuracy and add capabilities they lack: tracking, replay handling, scoreboard masking, configurable min-duration thresholding.

**Effort estimate:** 12-14 weeks from zero to a defensible per-match report (revised up since no existing code); +4 weeks for a polished dashboard.

---

## 1. Problem statement (revised)

### 1.1 Business question
For each sponsor brand visible on Bradford Bulls' kit during a broadcast match, **how much screen time does it actually accumulate, weighted by how visible it is**, and how does that compare to the share of fee that brand currently pays under the existing pricing card?

### 1.2 Output
- **Per-match report** with:
  - Total on-screen time per brand (seconds)
  - Number of "impact events" (continuous segments ≥ 2s) per brand
  - **100% Equivalent Time** = Σ (second × QI of that second)
  - Position metadata aggregated from detections (chest / sleeve / shorts / socks / collar)
  - Relative ranking and current-fee comparison
- **Per-sponsor scorecard** (subset of the per-match)
- **Cross-match aggregation** when ≥3 matches available

### 1.3 What we are explicitly NOT doing in v1
- Eye-tracking validation against viewer recall (out of scope; flagged as future work)
- Open-vocabulary detection (we have a fixed brand set)
- Real-time inference (we are post-broadcast)
- Multi-club generalisation (POC then SaaS layer later)

### 1.4 Critical constraint
The system must be **defensible to commercial sponsors**. Every numeric choice (QI weights, minimum duration, conversion rates) needs either:
(a) a published industry/academic citation, or
(b) a documented internal validation experiment.

This rules out fabricated weights, "Nielsen claims X" without a URL, or hand-tuned numbers without a sanity check.

---

## 2. Industry & academic grounding

### 2.1 ExposureEngine (Yerlikaya et al., arXiv [2510.04739](https://arxiv.org/abs/2510.04739), Oct 2025) — closest published analogue

| Aspect | Their choice | Result |
|--------|------------|--------|
| Sport | Swedish elite soccer | n/a |
| Dataset | 1,103 frames, 670 unique sponsor logos, sampled @ 1 FPS from 97 highlight clips | n/a |
| Annotation | OBB (oriented bounding boxes) in Label Studio | n/a |
| Train/val/test | 80 / 10 / 10 | n/a |
| Detector | YOLOv11-Medium with OBB head, 26.4M params | best in their comparison |
| Input resolution | 1280×720 | n/a |
| Optimiser | AdamW, lr 0.001, batch 32, 200 epochs | n/a |
| Loss | Varifocal Loss (α=0.75, γ=2.0) for class imbalance | down-weights easy negatives |
| Augmentation | random rotation, scaling, contrast | n/a |
| **mAP@0.5** | **0.859** | precision 0.96, recall 0.87 |
| Tracking | none — frame-by-frame | future work |
| Exposure formula | Eℓ = (Σ visible-frame indicators) × Δt; per-frame coverage = clipped OBB area / frame area | published in paper |
| Replay handling | not addressed | gap |
| Scoreboard / LED handling | not addressed | gap |
| Min duration threshold | not used | gap |
| Hardware | 3× A100 80GB | overkill — 1 GPU suffices for training |

**Implication for us:** Their architecture is the right starting point. Our pipeline is **strictly a superset**: we add tracking, replay handling, scoreboard masking, and the MRC minimum-duration filter — i.e., we should be able to match ≥0.85 mAP and produce a more credible exposure report.

### 2.2 SoccerNet 2023 Tracking Challenge — 3rd place (MOT4MOT, arXiv [2308.16651](https://arxiv.org/abs/2308.16651))

| Aspect | Their choice |
|--------|------------|
| Player detector | YOLOv8l fine-tuned on SoccerNet, 576×1024, NMS IoU 0.45 |
| Tracker | DeepOC-SORT++ (slightly better than StrongSORT++) |
| Team-based ID consistency | jersey-number metadata used to merge tracks |
| Final HOTA | 66.27 (DetA 70.32, AssA 62.62) |
| Dense-cluster handling | post-processing track merging, IDs created/terminated only near image boundaries |

**Implication for us:** YOLO-large person detection + appearance-aware tracker is the SOTA recipe. We will use YOLOv11l (newer than v8l) + BoTSORT (industry-balanced choice — slightly behind DeepOC-SORT++ in HOTA but faster and well-supported in `supervision` / Ultralytics).

### 2.3 MRC Viewability Standard for Video Ads (Media Rating Council, [v2 2015](https://mediaratingcouncil.org/sites/default/files/Standards/081815%20Viewable%20Ad%20Impression%20Guideline_v2.0_Final.pdf))

The published standard for a "viewable" video ad impression:

> **50% of the ad's pixels must be in the viewable space for a minimum of 2 continuous seconds.**
> Larger ads (> 242,000 pixels) qualify at 30% area for 1 second.

**Implication for us:** This is the cleanest defensible source for a minimum-duration threshold. We adopt **2 continuous seconds** as the threshold for an "Impact Event" in our Layer-2 report, identical to MRC. (A logo flashing for 0.4s does not count as a sponsor impression; a logo on screen for 2.1s does.)

### 2.4 Nielsen Sports — MIV / QI Score

Nielsen's flagship sports media valuation methodology is publicly described as:
- Combine **AI-detected exposure metrics** + **proprietary QI Score** + **audience metrics** + **ad rates** → **MIV (Media Impact Value)**
- QI components named in marketing material: size, position, clarity, clutter, exclusivity (specific weights are proprietary and not public)

Sources: [Nielsen Media Valuation page](https://nielsensports.com/media-valuation/), [Nielsen 2025 Global Sports Report](https://www.nielsen.com/insights/2025/global-sports-report-2025/).

**Implication for us:** We mirror the *concept* of QI without claiming Nielsen's exact weights. Our weights are explicitly disclosed and tunable, which sponsors find more credible than a black-box proprietary number anyway.

### 2.5 GumGum Sports / Relo Metrics (spinoff)

GumGum Sports → spun off into Relo Metrics in 2021 ([AdExchanger article](https://www.adexchanger.com/tv/how-this-analytics-startup-a-spinoff-of-gumgum-tackles-sports-sponsorship-measurement/)). Methodology is proprietary; their public claim is "Sponsor Media Value" using "amount of time × visibility × clutter context." No formula is published.

**Implication for us:** Same as Nielsen — we mirror the concept, not the secret sauce.

---

## 3. End-to-end pipeline

```
                    ┌─────────────────────────────────────┐
                    │     INPUT: Match video (90 min)     │
                    │     1080p or 720p, broadcast .mp4   │
                    └────────────────┬────────────────────┘
                                     │
        ┌────────────────────────────▼─────────────────────────────┐
        │  STAGE 1 — Smart frame extraction (TO BUILD)              │
        │  Plan: src/frame_extraction/{pipeline,helpers,overlay,    │
        │        calibration,selection}.py                          │
        │  • Auto-overlay mask via temporal variance (20-frame      │
        │    variance baseline → mask scoreboard + watermark)       │
        │  • Auto team calibration via K-Means + user pick          │
        │    (sample 50 frames → 200 torso crops → 3 clusters →     │
        │     user picks Bradford cluster, becomes learned palette) │
        │  • Pass 1 (fast scan @ every 5th frame) → quality segments│
        │    where target player area > threshold                   │
        │  • Pass 2 (full scan in segments) → tiered Gold/Silver/   │
        │    Bronze per torso sharpness + foreground filter         │
        │  • Quota-based selection by category (target close-up,    │
        │    medium, mixed, opponent, wide)                          │
        │  Output: ~400-600 candidate frames per match              │
        └────────────────────────────┬─────────────────────────────┘
                                     │
        ┌────────────────────────────▼─────────────────────────────┐
        │  STAGE 2 — Annotation + temporal propagation              │
        │  • Roboflow project, OBB labels, brand-centric taxonomy   │
        │    (~15-20 classes, see §6)                               │
        │  • 400 manual frames per kit (HOME / AWAY) — first        │
        │  • Temporal propagation: each annotated frame T → ±3      │
        │    neighbour frames via template matching (≥0.5 NCC)      │
        │    yields ~2,000 effective training frames per kit        │
        │  • Background mining (15%): pure crowd, pure pitch, LED   │
        │    boards, fans wearing Bradford colours, opponent close- │
        │    ups → empty annotation = hard negatives                │
        │  Output: ~2,000-3,000 OBB-annotated frames per kit        │
        └────────────────────────────┬─────────────────────────────┘
                                     │
        ┌────────────────────────────▼─────────────────────────────┐
        │  STAGE 3 — Logo detection model training                  │
        │  YOLOv11-Medium with OBB head, matches ExposureEngine     │
        │  • imgsz 1280 (vs ExposureEngine 1280×720)                │
        │  • Varifocal Loss (α=0.75, γ=2.0)                         │
        │  • AdamW lr 0.001, batch 16-32, 150-200 epochs            │
        │  • Patience 30, AMP fp16                                  │
        │  • Augment: motion blur 0.35p, JPEG compression 0.3p,     │
        │    HSV jitter, mosaic 1.0, mixup 0.1, copy-paste 0.15,    │
        │    rotate ±10°, scale 0.4, coarse dropout                 │
        │  Target: mAP@0.5 ≥ 0.80, per-class AP ≥ 0.50              │
        │  Hardware: 1× A100 (Colab Pro) ~3-6 hours                 │
        └────────────────────────────┬─────────────────────────────┘
                                     │
        ┌────────────────────────────▼─────────────────────────────┐
        │  STAGE 4 — Inference engine (Crop-and-Detect + Track+Infer)│
        │  Pass 1: YOLOv11l person detect on every frame (full HD)  │
        │  Pass 2: BoT-SORT tracking → stable track_ids (3s buffer) │
        │  Pass 3: HSV-histogram team classifier (calibrated palette│
        │          re-used) → bradford / opponent / referee / GK    │
        │  Pass 4: keyframe selection — every frame for new tracks; │
        │          every 5 if binding unstable; every 15 if stable  │
        │  Pass 5: per-keyframe → crop padded player → resize 640 → │
        │          YOLOv11m OBB logo inference                       │
        │  Pass 6: LogoTracker accumulates per (track_id × class)   │
        │          counts + confidences; binds when count ≥ 3       │
        │  Pass 7: temporal inference — for every frame where a     │
        │          tracked Bradford player is visible AND has ≥1   │
        │          bound logo, attribute the logo as exposed (with │
        │          0.7× weight if not directly detected on frame)  │
        │  Output: per-frame detection records + bound-logo events │
        └────────────────────────────┬─────────────────────────────┘
                                     │
        ┌────────────────────────────▼─────────────────────────────┐
        │  STAGE 5 — 4-Layer exposure measurement (Nielsen-style)   │
        │  L1 Dedupe: same logo detected on N players in same frame │
        │     → 1 frame-event with logo_count = N (count saved as  │
        │     QI bonus, not duration)                                │
        │  L2 Smoothing: bridge gaps ≤0.5s; split events at scene   │
        │     cuts; **STORE all events regardless of duration**     │
        │     (filtering is a reporter concern, not storage)        │
        │  L3 QI per frame:                                          │
        │    QI = 0.35·size + 0.20·position + 0.20·clarity          │
        │       + 0.15·(1-clutter) + 0.10·exclusivity               │
        │    (weights are starting points — to be re-validated      │
        │     against manual ground-truth, see §4)                  │
        │  L4 Reporting (all metrics computed; user picks which     │
        │     to show):                                              │
        │    • total_raw_seconds   = Σ event.duration  (NO filter) │
        │    • total_impact_seconds= Σ event.duration where ≥ 2s   │
        │      (default per MRC; configurable threshold)            │
        │    • total_equivalent_seconds = Σ second × QI(second)    │
        │    • impact_events_count = count of events ≥ 2s          │
        │    • £-MAV deferred to v2 (no Super League CPM available) │
        └────────────────────────────┬─────────────────────────────┘
                                     │
        ┌────────────────────────────▼─────────────────────────────┐
        │  OUTPUT: per-match report (CSV + JSON + matplotlib PDF)   │
        └─────────────────────────────────────────────────────────────┘
```

---

## 4. Quality Index — design and validation

### 4.1 Components

```
QI_logo_in_frame = 0.35·size_score
                 + 0.20·position_score
                 + 0.20·clarity_score
                 + 0.15·(1 - clutter_score)
                 + 0.10·exclusivity_score
```

| Component | Formula | Rationale / source |
|-----------|---------|--------------------|
| size_score | min(1, OBB_area / frame_area · k); k chosen so that a 5%-screen logo scores ≈0.5 | matches ExposureEngine `cℓ,i = min(1, Aℓ,i / Af)` |
| position_score | Gaussian centred at screen centre (σ_x = 0.30, σ_y = 0.30, both in normalised coords) | Nielsen QI public description "centre receives higher attention"; eye-tracking studies on TV viewing show centre-fixation bias |
| clarity_score | confidence × min(1, Laplacian_var / 300) of the OBB crop | confidence calibrates detector certainty; Laplacian penalises motion blur; Nielsen QI lists "clarity" as a component |
| clutter_score | min(1, n_other_brand_OBBs_in_frame / 10) | Nielsen QI lists "clutter" — competing brands in frame split attention; 10 is a soft cap |
| exclusivity_score | 1 if no other brand visible; else max(0, 1 - 0.1·n_other_brands_visible) | Nielsen QI lists "exclusivity" — sole brand on screen commands more attention |

### 4.2 Weight justification & tunability
- The starting weights (35/20/20/15/10) are **deliberately published in this document** so sponsors can audit them.
- They sum to 1.0.
- They will be **re-validated** in Stage 4 by:
  1. Manual annotation of a 5-minute "gold" segment by a human analyst (who flags each visible logo and rates its prominence on a 1-5 scale)
  2. Tune weights to maximise Spearman correlation between QI and human prominence rating
- Final weights will be reported in the per-match report so the methodology travels with the data.
- **Multi-sport / multi-club extensibility:** The 5 components are sport-agnostic. When extending to soccer, basketball, F1, etc., the same formula applies but weights can be re-tuned per sport. For example, basketball has more close-up replays → reduce `size` weight; F1 sponsors are stuck on a stationary car → bump `exclusivity`. The weights are explicit per-sport YAML config, not hardcoded — this is exactly how Nielsen MIV ports between sports.

### 4.3 Min-duration handling — store everything, filter at report
**User direction:** "Có logo thì mình sẽ track, còn xuất hiện bao nhiêu giây sau này đánh giá sau."

Implementation:
- **Storage layer** stores every detected event (start_frame, end_frame, duration, QI). No threshold applied here.
- **Reporter layer** computes all 3 metrics simultaneously per logo:
  - `total_raw_seconds`     = Σ duration (everything, even 0.1s flashes)
  - `total_impact_seconds`  = Σ duration where duration ≥ `impact_threshold_seconds`
  - `total_equivalent_seconds` = Σ (second × QI)
- `impact_threshold_seconds` is a **report-time parameter**, default **2.0** (per MRC). Configurable in the report YAML — the same data can be re-rendered with threshold 0.5, 1.0, or 3.0.
- Sponsor-facing reports use 2.0 (defensible). Internal "ranking" analyses can use raw seconds (more sensitive).

### 4.4 Why we do NOT publish a £-MAV in v1
- We do not have access to a Super League / rugby league CPM benchmark.
- ExposureEngine, Nielsen, GumGum/Relo all keep their £-conversion proprietary precisely because it is the most contested number.
- Our v1 report uses **relative ranking and Equivalent Time**, not £. The pricing CSV % weights remain the club's authority — we propose re-allocations of those weights based on relative exposure, not absolute fees.
- A future v2 can layer a £-rate on top once the club provides a per-second TV equivalent rate (or we contract Nielsen for one).

---

## 5. Validation strategy

| Question | Method | Pass criterion |
|----------|--------|----------------|
| Does the detector generalise across matches? | Train on 80% of matches, test on 20% holdout. Per-class AP per match. | mAP@0.5 holdout ≥ 0.75; no per-class AP < 0.40 on the holdout match |
| Does the inference pipeline match human counts? | 3× 5-minute segments (open play / set piece / fast play) annotated frame-by-frame by a human; pipeline run on same. | Per-logo exposure deviation < 15%; Spearman ρ on logo ranking ≥ 0.90 |
| Does the QI rank logos the way a human would? | 5-min "gold" segment labelled by a human with 1-5 prominence per visible logo. Compare QI rank vs human rank. | Spearman ρ ≥ 0.85; weights re-tuned if not |
| Are the false positives sponsor-credible? | Sample 100 detections at conf 0.5+. Manual yes/no. | Precision @ 0.5 ≥ 0.92 |
| Does the system handle replays? | Manually flag replay segments in 1 match; check exposure double-counting. | Replays auto-flagged in report; "main + replay" split available |

---

## 6. Class taxonomy (CONFIRMED — brand-centric, all-canonical-brands)

**Confirmed by user 2026-05-15.** Detection classes are built from `/Sponsor Logo/` files. Color variants are kept as **separate classes** because visually distinct artwork = distinct class. ALL canonical brands are kept (even those not visible on the current 2025/26 kit) because future matches may surface them; classes with 0 detections in current matches become "low-confidence / placeholder" reportables until kit changes.

### 6.1 Sponsor brand classes (all train; some may currently be placeholders)

| ID | class_code | display_name | reference file in /Sponsor Logo/ | training status |
|----|-----------|--------------|-----------------------------------|-----------------|
| 0  | `aon_red`               | Aon (red on light)        | `1 - aon_logo_signature_red_rgb (2).png` | active (HOME shorts) |
| 1  | `aon_white`             | Aon (white on dark)       | `1 - aon_logo_white_rgb (3).png`         | active (AWAY shorts) |
| 2  | `atm_hospitality`       | ATM Hospitality           | `2 - ATM-Hospitality-Logo-New-Font.png`  | candidate sleeve/collar |
| 3  | `cch_black`             | Cedar Court Hotels (black)| `3 - CCH - Master Logo Black [A3 Digital].png` | active per user; position TBD |
| 4  | `cch_white`             | Cedar Court Hotels (white)| `3 - CCH - Master Logo White [A3 Digital].png` | active per user; position TBD |
| 5  | `chadlaw`               | Chadwick Lawrence         | `4 - ChadLaw1.png`                       | active (front lower / hip) |
| 6  | `em_workwear`           | EM Workwear               | `5 - EM workwear logo.png`               | **active (socks)** |
| 7  | `fairway_flooring`      | Fairway (Flooring/Roofing — name TBD with club) | `6 - Fairway Flooring Ltd Logo nO NUMBER.jpg` | active (nape/top back); filename says "Flooring" but artwork reads "Roofing" — naming to confirm with club |
| 8  | `klg`                   | KLG Europe                | `7 - KLG Transparent Final.png`          | active (shorts both kits) |
| 9  | `mcp_away`              | MCP (away/white variant)  | `8 - MCP Away.png`                       | active (AWAY upper back) |
| 10 | `mcp_home`              | MCP (home/dark variant)   | `9 - MCP.png`                            | active (HOME upper back) |
| 11 | `mna_cladding`          | MNA Cladding              | `10 - MNA Cladding.png`                  | candidate shorts/sleeve |
| 12 | `mna_support`           | MNA Support Services      | `11 - MNA Support Services.png`          | candidate shorts/sleeve |
| 13 | `paints_lacquers_yellow`| Paints & Lacquers (yellow)| `12 - yellow.jpg`                        | placeholder (not visible 2025/26; kept for future) |
| 14 | `top_notch`             | TopNotch                  | `13 - Top Notch Logo.png`                | **active (HOME front chest — main sponsor)** |
| 15 | `bartercard`            | Bartercard                | `Bartercard.jpg`                         | candidate sleeve |
| 16 | `floor_tonic`           | Floor Tonic               | `Floor tonic Logo.jpg`                   | **active (AWAY front chest — main sponsor)** |
| 17 | `paints_lacquers_red`   | Paints & Lacquers (red)   | `Paints & Laquers Logo FINAL.jpg`        | placeholder (kept for future) |
| 18 | `romantica_white`       | Romantica Beds (white)    | `Romantica Beds - Logo FINAL WHITE.jpg`  | active (back lower) |
| 19 | `romantica_black`       | Romantica Beds (black)    | `romantica black.jpg` **(0-byte; needs replacement)** | placeholder until file replaced |
| 20 | `acs_group`             | ACS Group                 | `acs_group.jpg`                          | active (mid back) |

**21 sponsor classes total** (matching the original spec count, but with corrected identities).

### 6.2 Context class (non-sponsor; trained for FP suppression + Bradford-player confirmation)

| ID | class_code | display_name | reference | reported in MAV? |
|----|-----------|--------------|-----------|------------------|
| 21 | `bulls_crest` | Bradford Bulls club crest | derived from kit photo / official club asset | NO — context only |

**Skipped (per user 2026-05-15):** Ellgren manufacturer mark, player name+number. Reason: limited gain for v1 complexity.

### 6.3 Implementation notes from user clarifications

- **Position metadata, not class.** `position` (chest / sleeve / shorts / socks / collar) is computed from each detection's bbox center within its player crop, NOT from the class name. A class can move position match-to-match.
- **Placeholder classes train with 0 data initially.** They appear in the schema and in reports as "no detections this match" — informative for the club. When a future kit surfaces them, the annotator labels them and we retrain incrementally.
- **Romantica black file (0 bytes)** — class is placeholder until user supplies a non-empty file. We do NOT block on this; training proceeds without it.
- **Color-variant separation** (mcp_dark vs mcp_white, aon_red vs aon_white, cch_black vs cch_white, romantica_white vs romantica_black) is per user explicit. Each variant trains separately. Reporter aggregates by parent brand: e.g., `mcp_total_seconds = mcp_home + mcp_away`.

---

## 7. Compute & storage budget

| Stage | Per-match time (T4) | Per-match time (A100) | Storage out |
|-------|---------------------|----------------------|-------------|
| Frame extraction (Pass 1+2) | ~30-45 min | ~10 min | 200 MB frames + 1 MB metadata |
| Annotation | n/a (human ~5h per kit) | n/a | 50 MB labels (Roboflow) |
| Training (per kit) | not feasible | 3-6 h | 50 MB weights |
| Person detection + tracking | ~15-20 min | ~8 min | 30 MB tracks JSONL |
| Logo detection on keyframes | ~30-50 min | ~15 min | 100 MB detections |
| Exposure computation | ~1 min | ~30 s | 5 MB report CSV/JSON |
| **Total per match (inference only)** | **~75-115 min** | **~25-35 min** | **~340 MB** |

Free Colab (T4) can comfortably handle a single match per session. Production: Colab Pro+ (A100) recommended for batch.

---

## 8. Risk register & mitigation

| # | Risk | Severity | Mitigation |
|---|------|----------|------------|
| R1 | Per-class data imbalance — TopNotch will appear far more than MNA Cladding | High | Varifocal Loss; class-weighted sampling; targeted "minority class" frame extraction in Pass 2 |
| R2 | Logos in `/Sponsor Logo/` folder don't all appear on the 2025/26 kit (Paints & Lacquers, possibly CCH) | Medium | Drop unverified classes after kit photo review; confirm with user (§10) |
| R3 | Sleeve/collar logos are below 15px in wide shots | Medium | Crop-and-detect magnifies 4-6×; tiled inference fallback if still small; report low-detection-rate classes with confidence intervals |
| R4 | LED board sponsor logos confused with jersey logos | Low (architecture) | Crop-and-detect inherently solves — logo inference only on player crops |
| R5 | Crowd wearing Bradford colours triggers false positives | Medium | Foreground player filter (existing); 15% background hard-negative mining including crowd close-ups |
| R6 | Replay segments double-count exposure | Medium | Detect replay via scoreboard-overlay disappearance + scene-cut + frame similarity to recent past; report main vs replay separately |
| R7 | Track-ID swaps in rucks/scrums attribute exposure to wrong player | Medium | BoT-SORT 3s buffer; freeze logo binding updates during ruck (high IoU cluster); post-hoc track merging |
| R8 | Different broadcast quality (1080p vs 720p, AV1 vs H.264) hurts cross-match | Medium | Strong augmentation (JPEG compression 40-95, resolution scale 0.4); test cross-quality validation |
| R9 | Goalkeeper / alternate kit changes logo set | Low | 4-way team classifier (home / away / GK / opponent); GK gets separate brand binding |
| R10 | Methodology challenged by sponsor | High | All weights/thresholds traced to public sources in this doc; manual ground-truth report attached to per-match output |

---

## 9. Roadmap (12-14 weeks from zero)

| Week | Deliverable | Notes |
|------|-------------|-------|
| 0 (this week) | This document — Solution Architecture v4 (final spec) | ✅ Drafted, taxonomy + QI confirmed |
| 1 | Project skeleton: `requirements.txt`, `src/` package layout, `config.py` (21 sponsor classes + bulls_crest), Colab + local MPS setup | from scratch |
| 2 | Implement Stage 1A: video I/O + YOLOv11l person detection + auto overlay-mask + auto team calibration K-Means UI | from scratch |
| 3 | Implement Stage 1B: tiered torso-sharpness + foreground filter + quota selection + frame export | from scratch; first extraction run on M01 |
| 3-4 | Annotate ~400 HOME frames in Roboflow (OBB), ~400 AWAY frames | manual effort ~5h per kit |
| 4 | Implement temporal propagation script → ~2,000 effective training frames | from scratch |
| 5 | Train YOLOv11m-OBB on Colab Pro (A100); first per-class AP report | iterative until mAP@0.5 ≥ 0.75 |
| 6 | Cross-match validation (train M01+M02 → test M06; or vice versa); retrain weak classes | iterative |
| 7-8 | Stage 3 inference engine: person detect → BoT-SORT → team classifier → keyframe selection → crop-and-detect → LogoTracker | from scratch |
| 9 | Stage 4 measurement layer: dedupe → smoothing → QI computation → event store | from scratch |
| 10 | Stage 5 reporter: CSV/JSON + matplotlib PDF report (raw / impact / equivalent metrics) | from scratch |
| 11 | End-to-end validation: 3× 5-min ground-truth segments, Spearman ρ ≥ 0.90, tune QI weights | manual effort + tuning |
| 12 | Per-match report delivered for M01, M02, M06; user review | first deliverable |
| 13-14 | Iteration on weak spots; documentation; handover | refine |
| (later) | Multi-club / multi-sport extension; £-MAV layer; Web dashboard (Next.js + FastAPI) | deferred per user direction |

---

## 10. Open questions — RESOLVED 2026-05-15

All blocking taxonomy questions answered by user. Summary:

| # | Question | User decision |
|---|----------|---------------|
| 1 | Paints & Lacquers — drop? | **Keep both variants** — placeholder until they appear on a kit. |
| 2 | Cedar Court Hotels — drop? | **Keep** — sponsor still active per user. |
| 3 | Fairway — Roofing or Flooring? | **Keep filename naming for now**, naming TBD with club. |
| 4 | romantica_black.jpg 0-byte file | **Keep class as placeholder**; user replaces file later. |
| 5 | Bulls crest + Ellgren context classes? | **Bulls crest YES** (1 context class). **Ellgren NO**. |
| 6 | Player name + number class? | **NO** for v1. |
| 7 | Sleeve/collar small logos resolution | **Skip kit-photo analysis.** Trust annotators to label from actual video frames using brand reference cards. |
| 8 | Pricing CSV semantics | **Confirmed:** fixed-position weights; we report exposure per BRAND, aggregate per POSITION as metadata, never bind class→price upfront. |
| 9 | Color variants merged or separate? | **Separate** — every variant is its own class. |
| 10 | Other ~7 videos — upload now? | **Stay with current 3** for POC. Scale after pipeline proves out. |

**Net result:** Taxonomy is **21 sponsor classes + 1 context class (`bulls_crest`)** = 22 total. See §6.

**Outstanding non-blocking items:**
- Bradford Bulls crest reference asset — derive from kit photo or request official asset from club.
- Romantica black variant — non-blocking; user will replace `romantica black.jpg` when convenient.
- Fairway "Roofing vs Flooring" naming — non-blocking; resolve before final report.
- Annotator brand-reference card — produce a 1-page PDF showing all 21 logo references for annotators (Stage 2 prep).

---

## 11. Why this v4 supersedes earlier iterations

| Doc | Status under v4 |
|-----|------------------|
| `PROJECT_SPECIFICATION.md` | Outdated — taxonomy partially wrong (AON / TopNotch / Floor Tonic positions). v4 corrects. |
| `PLAN.md` | Superseded as primary plan; some sections (rugby-specific edge cases) folded in. |
| `plan-16-04-2026.md` | Good architectural intent; superseded by `plan-2026-04-17.md` and v4. |
| `plan-2026-04-17.md` | **Foundation of v4.** Architecture preserved (Crop-and-Detect + Track+Infer). v4 adds: industry grounding, corrected taxonomy, MRC threshold, OBB direction, validation criteria. |
| `pipeline_final_review.md` | All 8 pitfalls preserved as risk mitigations in v4 §8. |
| `new-optimization.md` | RVRT video deblurring kept as **optional Stage 1c** for Phase 2 — only run on annotation-target frames where torso sharpness < bronze threshold but the segment is otherwise valuable. |
| `team_aware_frame_extraction_proposal.md` | Implemented in `src/frame_extraction/calibration.py`. v4 reuses as-is. |
| `frame_extraction_techniques.md` | Accurate description of existing code; no change needed. |
| `valuation_methodology_{en,vn}.md` | Conceptually aligned with v4 Stage 5. v4 makes the weights explicit and grounds the 2s threshold in MRC. |
| `implementation_plan.md` | Useful business context (negative examples, replay handling, valuation engine). v4 incorporates. SaaS section deferred. |
| `TECHNICAL_CHARACTERISTICS.md` | Accurate snapshot of frame-selection logic; reused. |

---

## 12. References (verifiable URLs)

1. ExposureEngine paper — Yerlikaya et al., arXiv 2510.04739, Oct 2025. https://arxiv.org/abs/2510.04739
2. SoccerNet 2023 Tracking — MOT4MOT Team Report, arXiv 2308.16651. https://arxiv.org/abs/2308.16651
3. Media Rating Council — Viewable Ad Impression Measurement Guidelines v2.0, 2015. https://mediaratingcouncil.org/sites/default/files/Standards/081815%20Viewable%20Ad%20Impression%20Guideline_v2.0_Final.pdf
4. Nielsen Sports — Media Valuation overview. https://nielsensports.com/media-valuation/
5. Nielsen — 2025 Global Sports Report. https://www.nielsen.com/insights/2025/global-sports-report-2025/
6. AdExchanger — GumGum Sports / Relo Metrics spinoff. https://www.adexchanger.com/tv/how-this-analytics-startup-a-spinoff-of-gumgum-tackles-sports-sponsorship-measurement/
7. BoT-SORT — Aharon et al. https://github.com/NirAharon/BoT-SORT
8. Veroke — Multi-object tracker comparison (BoT-SORT / ByteTrack / StrongSORT in real-world scenarios). https://www.veroke.com/insights/how-top-ai-multi-object-trackers-perform-in-real-world-scenarios/

---

## 13. Sign-off checklist (before starting Stage 1)

- [x] User has answered the 10 open questions in §10 — **resolved 2026-05-15**
- [x] User has confirmed the corrected taxonomy in §6 — **22 classes total (21 sponsor + 1 context)**
- [x] User has agreed the QI weight starting points in §4 (35/20/20/15/10, subject to validation)
- [x] User has acknowledged the £-MAV deferral in §4.4
- [x] User has confirmed video scope (3 videos for POC; scale later)
- [x] User has confirmed min-duration storage strategy (store all, filter at report; default 2s per MRC)
- [ ] (next step) Project skeleton scaffolding — `requirements.txt`, `src/` layout, `config.py` with the 22 classes

**All blocking decisions resolved.** Next concrete step is Week 1 of §9 — project skeleton + Stage 1A code (video I/O + person detection + overlay mask + team calibration).
