# Sponsor Exposure Analytics for the Rest of Us: An Open, Self-Hostable Framework for Small and Mid-Tier Sports Clubs

*Research proposal / paper outline*

## Abstract (draft)

- Sponsor logo exposure measurement and media-value (EMV) estimation is well served for
  clubs that can afford an enterprise vendor (Nielsen Sports, GumGum/Zoomph, Relo
  Metrics, Shikenso) or maintain an in-house data-science team; most clubs outside the
  top-revenue leagues can do neither.
- We present an end-to-end, self-hosted framework built entirely from open-source
  models/libraries, deployable on commodity hardware, validated on a real professional
  club (identity withheld for confidentiality).
- Beyond detection, the framework resolves two problems left open by prior published
  systems: (i) attributing each logo to the correct team when a sponsor appears on both
  sides' kits/boards/officials; (ii) pricing sponsor placements at the level of
  individual kit slots, not just aggregate screen time.
- We report the architecture, the design choices that keep deployment cost near zero,
  and experiments on detection accuracy, team-attribution reliability, and the measured
  value of team-attribution in preventing overcounted exposure.
- We position our exposure/EMV formula against existing pricing practice — both the
  manual Advertising/Earned Media Value Equivalency (AVE/EMV) methodology used across
  the sponsorship industry, and recent AI-driven valuation systems — and note that
  neither line of work prices exposure at the placement/slot level.

## 1. Introduction

- **Motivation.** Clubs sell advertising space on kits, but only the largest can verify
  what that space is worth. Our partner club — a professional club with no in-house
  analytics team and no enterprise measurement contract — is representative of most
  clubs outside the top handful of leagues.
- **Existing commercial layer.** Nielsen, GumGum/Zoomph, Relo Metrics, Shikenso serve
  this need, but as a closed, hosted service: footage goes to a third party, usually
  under a recurring contract.
- **What's still unsolved even with a working detector:**
  - Same sponsor often appears on both competing teams' kits, boards, or officials →
    raw detection overcounts exposure unless ownership is resolved per instance.
  - Sponsors are priced by placement (chest-centre ≠ sock), but no published system
    attributes exposure at that granularity.
- **Contributions:**
  1. Team-ownership resolution without training a separate model per opponent —
     reference-based bootstrap, no manual setup required.
  2. Placement-level pricing via eighteen kit-slot attribution (pose estimation).
  3. An architecture assembled entirely from open-source components, designed for
     near-zero starting infrastructure cost.
  4. Deployment and evaluation on real broadcast footage from a professional club.

## 2. Related Work

- **Logo detection.** Mature problem; we build on standard open detectors rather than
  proposing a new architecture.
- **ExposureEngine (2025) — closest published system.** Oriented-bounding-box detector +
  visibility/exposure analytics for soccer broadcasts. Does not address team/opponent
  overlap, placement-level pricing, or deployment cost.
- **Team classification / jersey re-identification.** Active line of work (color/
  embedding clustering, jersey-number recognition, joint re-ID + role classification).
  We build on this and add track-level temporal voting + automatic reference bootstrap.
- **Ad-board localization in broadcast video.** Older literature (virtual advertisement
  insertion, automated billboard detection) — solves *inserting/replacing* ads, a
  different problem from *measuring* existing ones.
- **Commercial vendors.** Nielsen, GumGum/Zoomph, Relo Metrics, Shikenso confirm the
  problem's commercial importance; methods are closed and unpublished.
- **Existing pricing/valuation models — manual.** The industry-standard approach is
  Advertising/Earned Media Value Equivalency (AVE/EMV): convert exposure size and
  placement into the cost of an equivalent paid ad slot, often via a hand-set
  multiplier. This is exactly the class of formula our Tier-3 pricing step belongs to
  (adapted from ExposureEngine/Relo Metrics/Shikenso-style practice), so we cite it
  directly rather than only as background. It is also, notably, the target of sustained
  industry criticism — AMEC, IPR, PRSA, PRCA, and ICCO have all published position
  statements rejecting AVE as unreliable, citing arbitrary multipliers, no
  content/sentiment signal, and treating all viewers as identical regardless of
  placement or audience quality. We use this critique directly: our placement-level
  (kit-slot) pricing is one concrete way to make the multiplier less arbitrary, though
  it does not address the audience-quality/sentiment criticisms, which we should state
  as an explicit limitation rather than imply we've solved.
- **Existing pricing/valuation models — AI-driven.** Recent systems apply machine
  learning directly to sponsorship valuation and forecasting: SSPAIN.ai (Texas A&M),
  trained on several thousand historical sponsorships to predict valuation; Relo
  Metrics' computer-vision-plus-ML pipeline for automated media value and dynamic
  pricing; and, more broadly, machine-learning-based dynamic pricing methods from
  e-commerce/advertising (regression/classification models reacting to real-time
  demand signals), which are methodologically related but not sports-sponsorship-
  specific. None of this AI-driven work, as far as published material shows, prices at
  the sub-jersey placement level or discusses low-cost/self-hosted deployability.
- **Gap:** no published work addresses team/opponent overlap + placement-level pricing +
  low-cost deployability together, and no pricing model in either the manual or AI-driven
  literature attributes value below the level of a whole brand's aggregate exposure.

## 3. System Overview

- Orchestrated pipeline, graceful degradation at every optional stage:
  1. Frame sampling
  2. Team-reference bootstrap
  3. Logo detection
  4. Team attribution
  5. Pose-based body-zone assignment
  6. Exposure aggregation
  7. EMV pricing
  8. Multi-match reporting dashboard
- Infrastructure abstracted behind swappable interfaces — local SQLite/disk by default,
  optional path to Postgres/S3/distributed queue — so a club starts at near-zero
  infrastructure cost and scales only if needed.

## 4. Method

- **Detection.** YOLO-family detector fine-tuned on manually annotated frames;
  model-assisted labeling loop (small hand-labeled seed → early model suggests boxes →
  human review) to cut annotation effort.
- **Team attribution.**
  - Track detected persons across frames; classify jersey crops by fusing color
    histogram + vision embedding.
  - Accumulate classification per track with hysteresis, so one blurred frame can't
    flip a team label.
  - Reference examples obtained automatically (official kit images if available,
    otherwise clustered from the video's own early frames) — no manual per-match setup.
  - Insufficient evidence → keep the detection rather than drop it (avoids silently
    understating a paying sponsor's exposure).
- **Exposure and pricing (3-tier, adapted from prior industry/academic formulas — same
  Advertising/Earned Media Value Equivalency family discussed in §2, not a new pricing
  theory):**
  1. Per-frame visibility score (size, position, confidence).
  2. Temporal aggregation into exposure segments per brand.
  3. Conversion to EMV via audience size, CPM, placement multiplier.
  - We recalibrate the visibility threshold used in prior work — as published, it
    discards most real, small, off-centre sponsor logos.
- **Placement-level pricing.** Each detection assigned to one of 18 kit slots via pose
  keypoints → exposure/price reported per placement, not just per brand.

## 5. Planned Experiments

- Detector accuracy on a **match-disjoint** test split (frame-level splits inflate
  accuracy — observed directly during development), with per-class breakdown.
- Team-attribution precision/recall on a labeled clip sample spanning more than one
  match/lighting condition.
- **Counterfactual test:** exposure/EMV with team-attribution on vs. off, on
  shared-sponsor clips — quantifies overcounting prevented.
- Exposure-time estimates checked against independent manual timing for ≥1 full match;
  EMV reported as a *consequence* of that validated measurement, not independently
  verified (CPM/audience are business inputs, not ground truth).
- End-to-end processing time on a named hardware configuration, and approximate
  annotation effort per new sponsor class — evidence for practical accessibility.

## 6. Discussion and Limitations

- Team attribution assumes a stable kit within a match; kit changes require a
  reference refresh.
- Color+embedding fusion not yet stress-tested across lighting conditions.
- Manual annotation remains the main cost when onboarding a new sponsor — the primary
  remaining barrier to full accessibility.
- Players tracked only as anonymous instances for kit-slot attribution; output is
  brand/media-value analytics, not player performance or biometric data.
- Placement-level pricing makes the AVE multiplier less arbitrary but does not answer
  the deeper industry critique of media-value-equivalency models (no signal for
  audience quality, sentiment, or actual brand-recall impact) — we improve one specific,
  known weakness of the AVE family, n