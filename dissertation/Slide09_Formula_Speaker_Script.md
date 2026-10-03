# LogoLens — Full Presentation & Defense Script
### ~10-minute supervisor meeting: ~7–8 min walkthrough + prepared answers for the discussion that follows

Pairs with `LogoLens_WP1_Summary.pptx` (10 slides). Each slide section below gives: a target time, the spoken script, and — where a slide carries a number or a formula — what it means and where it came from, with real links to the sources cited in the dissertation.

---

## Timing overview

| Slide | Content | Target time |
|---|---|---:|
| 1 | Title | 15 s |
| 2 | The measurement gap | 40 s |
| 3 | Aim & research questions | 35 s |
| 4 | Dataset & leakage-aware split | 55 s |
| 5 | RF-DETR vs. YOLO26 | 55 s |
| 6 | Headline result & reliability checks | 65 s |
| 7 | Where detection breaks down | 55 s |
| 8 | Logo Visibility Score — worked example | 100 s |
| 9 | Formula provenance & evaluation status | 100 s |
| 10 | Thank you | 10 s |
| **Total presentation** | | **~8 min** |
| Discussion / defense | using the prepared answers below | remaining ~2 min+ |

---

## SLIDE 1 — Title (15 s)

> "Good [morning/afternoon]. This is LogoLens, my dissertation work on Work Package 1: logo detection and visibility intelligence. I'll walk through the system, the headline results, and where the visibility-scoring side of it currently stands — about eight minutes, then happy to take questions."

---

## SLIDE 2 — The measurement gap (40 s)

> "The starting problem: every broadcast is already a complete visual record of which sponsor logos appeared — but sponsorship is still priced on precedent, not on that evidence. Commercial platforms — Nielsen, Relo Metrics, Blinkfire — prove automated tracking is feasible, but their methods and data are proprietary, so a club can't check a number against the footage.
>
> The number that motivates the whole dissertation is on the right: the same detector recovers 90% of marks in close and medium shots, but only 50% in wide tactical shots. Same shirt position, very different outcome — that asymmetry is what the rest of the talk explains."

**Sources behind this slide** (full citations in the dissertation's reference list):
- Nielsen vBrand — [nielsen.com/news-center/2017/…vbrand](https://www.nielsen.com/news-center/2017/nielsen-acquires-artificial-intelligence-powered-sports-marketing-startup-vbrand/)
- Nielsen Sports Reports — [nielsen.com/marketplace/sports-reports](https://www.nielsen.com/marketplace/sports-reports/)
- Relo Metrics — [relometrics.com/sponsorship-measurement-platform](https://relometrics.com/sponsorship-measurement-platform)
- Blinkfire — [blinkfire.com/d/landing/mediaanalytics](https://www.blinkfire.com/d/landing/mediaanalytics)
- Two Circles, sports IP revenue estimate — [twocircles.com/…sports-ip-revenue-league](https://twocircles.com/gb/articles/sports-ip-revenue-league-methodology-and-references/)

---

## SLIDE 3 — Aim & research questions (35 s)

> "Two questions, then a third about what to do with the answer. RQ1: can the system detect multiple sponsor logos accurately on matches it has never seen? RQ2: where does that accuracy break down — size, camera distance, lighting, resolution? RQ3: how do you turn those detections into a visibility measure that's honest about what it hasn't proven yet? The table on screen maps each RQ straight onto the Work Package 1 activities — detection and multi-logo work under RQ1, size/occlusion/quality under RQ2, duration and the Logo Visibility Score under RQ3."

---

## SLIDE 4 — Dataset & leakage-aware split (55 s)

> "584 images, 1,903 boxes, 16 sponsor classes, 15 separate matches. The methodological decision that matters most here: the unit of split is the **match**, not the frame. I found this the hard way — an earlier frame-level split let 51 of 56 validation frames share a training frame from the same clip within two seconds. That's not testing generalisation, that's testing memory.
>
> So the final design assigns whole matches to train, validation or test — never split within a match. And the number at the bottom proves why that mattered: run the same checkpoint on *familiar* footage and it scores 0.998 mAP. Run it on genuinely unseen matches and it drops to 0.933. That 6.5-point gap is evaluation optimism a naive split would have hidden completely."

---

## SLIDE 5 — RF-DETR vs. YOLO26 (55 s)

> "With the split fixed, I ran a controlled comparison: RF-DETR Small against three YOLO26 baselines — nano, small, medium — all on the same images, same 896-pixel input, same scoring code. RF-DETR Small wins by 16.1 points at mAP@0.50 and, more tellingly, by 24.4 points at the stricter mAP@0.75 — the gap widens as the overlap requirement gets stricter, which points to better localisation, not just better classification.
>
> One caveat I want to state myself before anyone else raises it: pre-training, parameter count and the augmentation recipe are not equal between the two families — RF-DETR carries DINOv2 pre-training that YOLO26 doesn't get. So this is a *system-level* result — 'RF-DETR Small worked better here, under these recipes' — not a general claim that transformers beat convolutional detectors."

**Sources:**
- RF-DETR — Robinson et al., 2025 — [arxiv.org/abs/2511.09554](https://arxiv.org/abs/2511.09554)
- YOLO26 — Jocher et al., 2026 — [arxiv.org/abs/2606.03748](https://arxiv.org/abs/2606.03748)
- DINOv2 backbone — Oquab et al., 2023 — [arxiv.org/abs/2304.07193](https://arxiv.org/abs/2304.07193)

---

## SLIDE 6 — Headline result & reliability checks (65 s)

> "So the headline: 0.933 mAP@0.50, 0.917 at the stricter threshold, F1 of 0.898, and inference at 19.8 frames per second on a consumer GPU. The image on the left is a real held-out frame — not a cherry-picked demo, an actual test image — with all 12 logos across 6 different sponsor brands correctly matched, zero false positives. That's what 'multiple logos simultaneously' looks like in practice.
>
> But I don't want to leave a single number unqualified, so three checks sit alongside it. The leakage check you've already seen — 0.998 to 0.933. The support check: four of fifteen classes have fewer than five test boxes between them, so I report a restricted mean over the eleven better-supported classes — 0.917 — right alongside the conventional 0.9335. And the stability check: per-match scores of 0.973, 0.934 and 0.976, so the result isn't being carried by one lucky match."

---

## SLIDE 7 — Where detection breaks down (55 s)

> "RQ2: where does it fail? Camera distance is the clearest answer. Recall is around 0.90 in close and medium shots, and falls to 0.500 in wide tactical shots. What's important is *how* it fails — precision on wide shots stays at 1.000. The detector isn't hallucinating logos, it's simply not seeing the small, distant ones. That's a predictable, one-directional bias: any duration estimate built on this detector will under-count exposure specifically in passages dominated by wide camera work — which matters because full match broadcasts contain a lot more wide play than the highlight clips this dataset draws from."

---

## SLIDE 8 — Logo Visibility Score: a worked example (100 s)

> "This is where detections stop being just boxes and start becoming a visibility number. The formula on screen —
>
> **V_i = clip₍₀,₁₎( √(A_i / A_f) × exp[ −d_i² / (0.3W)² ] × c_i )**
>
> — has three multiplied terms, and I want to be precise about what each one is:
>
> - **√(A_i / A_f) — the size term.** A_i is the predicted box's area in pixels, A_f is the whole frame's area. So this fraction is literally 'what share of the screen does the logo occupy' — and the square root is there deliberately, to compress that share so one very large, close-up mark doesn't completely dominate the score on its own.
> - **exp[ −d_i² / (0.3W)² ] — the position term.** d_i is the straight-line distance, in pixels, from the box's centre to the frame's centre; W is the frame width. This is a Gaussian — a bell curve centred on the middle of the screen — so a logo dead-centre scores close to 1, and the score falls off smoothly the further it drifts toward the edge. The 0.3W is the width of that bell curve: how forgiving it is before position starts really hurting the score.
> - **c_i — the confidence term.** This is just the detector's own output confidence for that box — how sure the model is that this is really a KLG mark and not something else.
>
> Multiplying all three, rather than adding them, is itself a choice: it means a low score on *any one* term drags the whole thing down — a large, dead-centre, low-confidence detection still scores badly.
>
> Now the worked example, using a real detection from the held-out test set: a KLG logo, match M_CAS, 21 seconds into the clip. The model was confident — 0.925 — and accurate — IoU 0.85 against the ground-truth box, a genuine true positive. But because the box sits 578 pixels off-centre in a 1920-pixel-wide medium shot, the position term collapses to 0.365, and the size term — because the box is only 0.2% of the frame — caps out around 0.046 before you even multiply anything else in. The final score: **V_i = 0.016**. Low, even though the detection itself was excellent.
>
> That's the point of showing this example rather than just the formula: a low visibility score does not mean the detector failed. It means the *appearance* was small and off-centre — which is exactly the kind of distinction a club needs, and exactly why every term stays traceable back to the source frame instead of being collapsed into one opaque number."

---

## SLIDE 9 — Formula provenance & evaluation status (100 s)

> "Two questions follow immediately from that worked example: where did this formula come from, and how much should anyone trust it? This slide answers both directly, because I'd rather raise it myself than have it raised for me.
>
> **Where it comes from.** Three sources in the literature name the same broad ingredients. ExposureEngine, a 2025 paper, derives on-screen coverage and exposure duration directly from detector geometry — the same starting point I use. A GumGum sponsor-valuation patent names size, clarity, duration and position as candidate quality factors. And Nielsen's own public description of their vBrand product names the same three: duration, size, image clarity.
>
> What none of those three sources does is publish the actual combination rule — the functional form. Nobody tells you *how* to turn size, position and confidence into one number. So this equation is **literature-informed, not literature-derived**: the choice of inputs comes from the literature, but the square root, the Gaussian, the 0.3W scale, and the decision to multiply rather than add — those are mine, designed and disclosed, not copied from a validated source, because no validated source publishing this exists yet.
>
> **How I evaluate it.** I split every component into three categories by how much evidence actually backs it. Box area and centre distance are **measured geometry** — read directly off the prediction, the most reliable part of the whole score. Confidence is a **model-derived proxy** — it tells you the detector's certainty, not whether a human being could actually read the logo; those are not the same thing. And the transformations themselves — square root, Gaussian, the 0.3W constant, multiplication — are **researcher-defined design choices**: reasonable, documented, but not fitted to any data and not yet checked against a human judgement.
>
> So the honest status, in one line: **transparent and fully reproducible, but not yet a validated measure of visibility quality.** Three things stand between it and that status — component-removal analysis, to check whether each term is actually pulling its weight; comparison against manually timed footage, at several sampling rates; and a proper two-rater human readability study. That's not a hand-wave — it's the top item on the future-work priority list in Chapter 6, precisely because it's the biggest evidentiary gap left in the whole dissertation."

**Sources — read these before the meeting if there's time:**
- ExposureEngine (on-screen coverage & duration from geometry) — Sarkhoosh et al., 2025 — [arxiv.org/abs/2510.04739](https://arxiv.org/abs/2510.04739)
- GumGum Sports automated sponsor-valuation patent — Katz, Carter & Kim, 2024, US 12,124,509 B2 — [patents.google.com/patent/US12124509B2](https://patents.google.com/patent/US12124509B2/en)
- Nielsen vBrand acquisition / product description — [nielsen.com/news-center/2017/…vbrand](https://www.nielsen.com/news-center/2017/nielsen-acquires-artificial-intelligence-powered-sports-marketing-startup-vbrand/)

**What the Logo Visibility Score becomes over time (in case it's asked, not on the slide):** individual V_i values are grouped into continuous segments per brand; each segment gets a duration weight (0.5× under 1 s, 1.0× from 1–5 s, 1.2× above 5 s) and contributes `Q = Σ (mean segment visibility) × (duration weight) × (segment length)`. Q is reported alongside raw on-screen seconds, never alone — same "prototype, not validated" caveat applies to the weights and the gap-tolerance rule used to build segments.

---

## SLIDE 10 — Thank you (10 s)

> "That's the walkthrough — detection is strong and honestly bounded, the visibility layer is implemented and traceable but explicitly not yet validated. Happy to take questions."

---

## Extended Q&A / defense preparation

Grouped by theme so you can find the right answer fast if the discussion jumps around.

### Methodology & the leakage result

**Q: "How confident are you that match-disjoint splitting is enough — could there still be leakage?"**
> "It removes the failure mode I could actually measure — 51 of 56 validation frames sharing a training frame within two seconds. I can't rule out subtler leakage, like recurring camera rigs or broadcast graphics across matches, but the 6.5-point drop between familiar and unseen material is the direct evidence that the leakage I removed was real and large."

**Q: "Why only three test matches?"**
> "Data availability and annotation cost — one researcher, mostly manual annotation. It's flagged explicitly as external validity threat in Chapter 6, and 'add independent matches' is priority #2 in the future-work list, specifically to grow the six-box wide-shot subset, which is the thinnest part of the evidence right now."

### Detector comparison

**Q: "Is RF-DETR just better because of DINOv2 pre-training, not the architecture?"**
> "Possibly, and I say so directly — pre-training, capacity and augmentation are not controlled, only images, split, resolution and scoring code are. What the result does support is a *practical implementer's choice* for this task; it doesn't support a general architectural claim. A matched efficiency benchmark — latency, memory, on the same hardware — is priority #3 in future work, because right now only RF-DETR's runtime is actually measured."

**Q: "Why 896px input instead of YOLO's default 640?"**
> "To keep the comparison fair to both systems rather than fair to YOLO's own default — small sponsor marks lose the most resolution at 640. Appendix B in the dissertation shows the controlled resolution sweep (512→768→896) that motivated this."

### The Logo Visibility Score

**Q: "Doesn't an unvalidated formula undermine the whole visibility contribution?"**
> "Only if I claimed it was validated. I don't — the contribution is the *traceable measurement chain*, not a claim that 0.016 is objectively correct. Every number in that chain — box area, distance, confidence — remains inspectable back to the source frame. The validation study is named as the next required step, not assumed away."

**Q: "What would change if you added blur or occlusion to the score?"**
> "Nothing yet — deliberately. Chapter 2 lists them as relevant but *unsupported constructs*: I don't have a validated way to estimate visible-area loss under occlusion or human-perceived blur from a horizontal box alone. Adding them without validation would make the score look more sophisticated without making it more true — so they're future work, not current inputs."

**Q: "Is there any EMV / monetary output?"**
> "Only as an explicitly optional, clearly-labelled scenario layer — never a validated output. Chapter 2 shows the illustrative EMV calculation and states its reliability can never exceed the reliability of the duration, quality weights, audience estimate and media rate underneath it. LogoLens reports traceable exposure as the primary output; monetisation is kept separate on purpose."

### Generalisation & future work

**Q: "Would this work for football, or a different club?"**
> "As a hypothesis, plausibly — the small-object constraint and the wide-shot recall problem both follow from shirt-mounted sponsorship and camera distance generally, not from rugby league specifically. But it's untested; extending to a new club currently means new manual annotation, which is exactly why the regulation-guided auto-annotation idea is in future work — same-league kit regulations fix where a sponsor mark sits relative to seams and panels, so a reference kit's annotations could seed candidate boxes for a new club's kit, cutting the annotation cost of testing that hypothesis."

**Q: "What's the single most important next step?"**
> "Manual-timing and readability validation of the visibility layer — everything else in future work is either strengthening evidence that's already solid (more test matches, a matched latency benchmark) or is downstream of this one. Until duration and the score are checked against a human reference, the detection result stands on its own but the visibility framework stays a prototype by design."

---

*Prepared for: LogoLens WP1 supervisor meeting. Companion to `LogoLens_WP1_Summary.pptx`.*
