# Zero-Annotation-Growth Logo Analytics for Rugby Broadcast Video
## An Architecture Design Document

---

## 1. Restate the Real Problem

### The bottleneck, correctly stated

Your bottleneck is not detection accuracy. It is that in a classical supervised pipeline, **class knowledge lives inside detector weights**. Every new sponsor forces you to push knowledge into weights via gradient descent, and gradient descent eats annotated frames. Annotation cost therefore scales as:

```
Cost ∝ O(clubs × sponsors × jersey_variants × seasons × video_conditions)
```

That product grows multiplicatively while your labeling budget grows linearly at best. The system is structurally doomed regardless of which detector you pick.

The correct reframing: **this is not a detection problem, it is a localization + instance-recognition problem, and the two must be architecturally decoupled.**

- **Localization** ("something logo-like is here") is *class-agnostic*. The visual concept of "a logo on fabric/board" is closed, stable, and learnable once. It never needs to grow with your catalog.
- **Recognition** ("this blob is Sponsor X") is *open-set* but you have a unique advantage: **every class you will ever care about is known a priori as a clean reference image.** Sponsors hand you their logos. You never face truly unknown classes — you face unseen *renderings* of known references.

Once recognition is moved out of weights and into a **searchable index of reference embeddings**, adding a logo becomes a database insert, not a training run. Annotation cost per new class approaches zero *by construction*, not by cleverness.

### Assumptions I will challenge

1. **"I need a logo detector."** No — you need a logo *localizer* (trained once, class-agnostic) and a logo *matcher* (training-free, index-based). Conflating them is the root cause of the scaling problem.
2. **"Open-vocabulary detection solves this."** Only partially. Text-prompted OV detectors (the GroundingDINO family) recognize *semantic categories*, not *visual identities*. "Emirates logo" as a text prompt is nearly useless for a small red wordmark at 30px. Image-conditioned querying is the right primitive; text-conditioning is the wrong one for this domain.
3. **"The vocabulary at inference is huge."** False, and this is the single most under-exploited constraint in your problem. At any given match you know the two teams, hence the ~20–50 plausible on-jersey sponsors, plus a bounded set of perimeter-board advertisers. Your 8,000-logo problem is, per match, a **~50-logo problem with a strong prior**. Architect around this.
4. **"Annotation must be zero."** Near-zero is the right target. A few *minutes* of human verification per new club (accept/reject machine-proposed matches) buys enormous reliability and costs essentially nothing. Optimize annotation *leverage*, not just annotation count. The goal is O(1) human effort per new club — constant and tiny — rather than literally zero, which sacrifices auditability your sponsors will eventually demand (they are paying for these numbers; the numbers need a provenance story).
5. **"Accuracy vs. annotation is the trade-off."** Long term, the bigger trade is *engineering complexity vs. maintainability*. A pipeline with 9 models is a pipeline with 9 failure modes and 9 upgrade treadmills. I will weigh this heavily.

---

## 2. Why Current Logo Detection Pipelines Fail

A supervised closed-set detector (YOLO-class, DETR-class) fails your requirements for structural reasons, not tunable ones:

**Class coupling.** The classification head has one output per logo. New logo → new head → retraining → re-validation → redeployment. Adding club #101 can silently degrade clubs #1–100 (catastrophic forgetting, class imbalance shifts, NMS interactions between visually similar sponsors). You now need per-release regression testing across your entire catalog — the QA cost alone kills you before annotation does.

**Annotation is per-rendering, not per-class.** A logo on a chest, folded on a sleeve, motion-blurred at 720p, and printed white-on-navy vs. navy-on-white are effectively different visual entities to a supervised detector. You don't annotate "20 logos," you annotate "20 logos × every deformation regime," i.e., thousands of boxes per club to reach production robustness.

**Long-tail starvation.** Sponsor exposure follows a power law: the chest sponsor dominates screen time; the shorts sponsor appears in 0.5% of frames. Supervised training on natural footage systematically under-serves exactly the small sponsors whose analytics are hardest to eyeball — the ones your customers most need automation for.

**Version hell.** Season 2027: sponsor keeps the deal but refreshes the logotype. In a supervised world that is a new class, new annotation, new training. In an index world it is one new reference image with a validity date range.

**The economics.** At (say) 300 boxes/logo minimum and 20 logos/club, onboarding a club costs ~6,000 boxes ≈ 30–60 annotator-hours plus a training/eval cycle. At 500 clubs that is a seven-figure annotation program, permanently, because sponsors churn every season.

The pattern to internalize: **any architecture where marginal cost of a new class > 0 human-hours will eventually fail; any architecture where it is a metadata operation scales indefinitely.**

---

## 3. Survey of Existing Paradigms

| Paradigm | Strengths | Weaknesses for this problem |
|---|---|---|
| **Supervised detection** (YOLO/DETR fine-tune) | Best raw accuracy on seen classes; fast inference; mature tooling | Class-coupled weights; O(N) annotation; retrain-per-logo; forgetting; long-tail starvation (see §2) |
| **Open-vocabulary detection** (OWLv2, GroundingDINO, YOLO-World, T-Rex2/DINO-X) | Zero-shot on new categories; OWLv2 & T-Rex2 support *image* prompts (crucial); no retraining | Text prompts nearly useless for visual identities; recall collapses on <40px objects; confuses similar wordmarks; image-prompt quality sensitive; heavy (ViT-L+) for full-match video |
| **Retrieval-based recognition** (embedding + ANN index) | New class = DB insert; training-free growth; scales to 10⁶ classes (FAISS et al.); auditable (you can inspect nearest neighbors) | Needs an upstream localizer; embedding must be robust to blur/warp/scale — off-the-shelf CLIP-type embeddings are mediocre on tiny curved fabric logos; domain-gap between clean reference and broadcast crop must be bridged |
| **Classical image matching** (SIFT/ORB → LoFTR/OmniGlue) | Training-free; strong for textured logos; geometric verification gives near-zero false positives | Dies on tiny/blurred/textureless logos (flat color wordmarks); too slow as a primary detector; excellent as a *verifier* |
| **Synthetic data** (compositing → rendering → diffusion) | Labels are free and perfect; controllable long-tail; you own the generator; logos-as-SVG plug in directly | Domain gap (compositing) or engineering cost (Blender/UE cloth sim); if used to train a *closed-set* detector you've only moved the scaling problem from annotation to compute — synthetic data should feed *class-agnostic* or *embedding* training, or per-club distilled specialists, never a monolithic N-class head |
| **Pseudo-labeling / self-training** | Mines the effectively infinite unlabeled match archive; compounds over time | Confirmation bias (model teaches itself its own errors); needs orthogonal verification signals (temporal, geometric, cross-model) to be safe |
| **Foundation models as annotators** (SAM2, DINOv2, VLM judges) | SAM2 propagates masks through video superbly; VLMs are decent verifiers of crops ("is this the X logo?"); DINOv2-class features are strong generic descriptors | Foundation VLMs are unreliable as primary *detectors* of small logos (hallucinate, miss tiny instances); reliable as *verifiers/propagators*; must be QA'd via consensus + human spot-check |
| **Metric learning** (triplet/ArcFace-style on logo crops) | Purpose-built embedding beats generic CLIP for logo identity; one-time training on public logo data (LogoDet-3K, OpenLogo) + synthetic pairs; generalizes to unseen logos by design | Requires a curated one-time training set (public + synthetic — acceptable, it's O(1) not O(N)); hard-negative mining needed for lookalike wordmarks |
| **Visual search infra** (product-search stacks) | Proven at 10⁸-item scale; per-match vocabulary filtering trivial (metadata-filtered ANN) | Not a detector; solves exactly and only the recognition half — which is precisely why it belongs in the architecture |

**Synthesis:** every paradigm is weak alone and strong in a specific slot. Localization wants one-time class-agnostic supervised training (fed by synthetic + pseudo-labels). Recognition wants metric-learned retrieval. Robustness wants temporal propagation. Trust wants geometric/VLM verification plus micro-scale human audit. The architectures in §4 explore different ways to compose these — and different opinions about which slot dominates.

---

## 4. Five Fundamentally Different Architectures

### Architecture A — "Localize-Once, Recognize-Forever" (Class-Agnostic Proposer + Retrieval Index)

**Intuition.** Train a single binary detector for the concept *logo-on-surface* — a closed, stable visual concept — and never touch its weights again as the catalog grows. Identity assignment is pure retrieval against reference embeddings. The catalog lives in a database, where catalogs belong.

```
                          ┌──────────────────────────────┐
        reference PNGs ──▶│  Reference Factory (offline)  │
        /SVGs per club    │  render → warp/blur/light augs│
                          │  → embed → ANN index          │
                          └──────────────┬───────────────┘
                                         │ per-match vocabulary filter
                                         ▼
 video ──▶ shot seg ──▶ class-agnostic ──▶ crop ──▶ embedding ──▶ ANN ──▶ match
                        logo proposer      rectify   encoder       search   + score
                        (binary, trained                                    │
                         ONCE on synth +                                    ▼
                         public logo data)                        temporal smoothing
                                                                  over tracklets → analytics
```

**Training pipeline (one-time, class-agnostic):**
1. Proposer: train a small detector (RT-DETR/YOLO-class, single "logo" class) on the union of public logo datasets (LogoDet-3K, OpenLogo, FlickrLogos, SportsMOT-style frames) with class labels *discarded*, plus synthetic composites (§Q2). ~0 project-specific annotation.
2. Encoder: metric-learn an embedding (ViT-S/DINOv2 backbone, ArcFace head) where views of the same logo cluster and lookalike wordmarks repel. Positives generated synthetically: each reference logo rendered under 200+ augmentations (perspective, cloth-warp via TPS, motion blur, JPEG/720p degradation, partial occlusion crops). Hard negatives: nearest-neighbor wordmarks in font-space.

**Inference:** proposer at 3–10 fps on keyframes → crops → embed → filtered ANN lookup (only this match's plausible logos) → accept if cosine > τ with margin over 2nd-best → propagate across the tracklet.

**Annotation requirements:** zero boxes per new club/logo. New logo = drop PNG into Reference Factory. Optional: 5-minute human review of first-match matches.
**Scalability:** new class is O(1); index scales to 10⁵+ trivially.
**Expected accuracy:** high precision (retrieval + margin test is conservative); recall limited by proposer on tiny/extreme cases — expect 80–90% of supervised ceiling overall, better than supervised on rare sponsors.
**Engineering effort:** moderate — two models + index + reference tooling.
**Deployment:** proposer and encoder are small; runs on one consumer GPU per stream.
**Risks:** proposer misses what it can't see (sub-25px, heavy blur) — mitigated by temporal aggregation (a logo missed in frame t is caught in t+12 and back-filled along the track); near-duplicate sponsor wordmarks (banking + insurance both use blue sans-serif) — mitigated by hard-negative training and geometric verification on high-stakes confusions.

---

### Architecture B — Promptable Open-Vocabulary Foundation Detector (Image-Conditioned)

**Intuition.** Skip custom training entirely. Use an image-promptable OV detector (OWLv2-style image-conditioned querying; T-Rex2/DINO-X lineage): encode each reference logo as a *visual prompt*, run the frozen giant over frames, take what it gives you.

```
 reference logos ──▶ visual-prompt embeddings ─┐
                                               ▼
 video frames ─────▶ frozen OV detector (ViT-L/g) ──▶ boxes + prompt-similarity ──▶ analytics
```

**Training pipeline:** none. That is the whole point.
**Inference:** per frame, run detector conditioned on the match's ~50 prompts (batched).
**Annotation:** zero.
**Scalability (classes):** perfect — new logo = new prompt.
**Scalability (compute):** poor — ViT-L per frame × 50 prompts × full matches × hundreds of clubs is a large GPU bill; and you don't control the model's failure modes.
**Expected accuracy:** mediocre on this domain. Current image-prompted OV models are trained for object-level concepts; 30px deformed fabric logos sit far outside their sweet spot. Expect strong performance on perimeter boards and chest sponsors in close-ups, weak on sleeves/shorts/wide shots.
**Engineering effort:** lowest of all options.
**Risks:** you inherit a ceiling you cannot raise (frozen model, no domain adaptation path); model deprecation/licensing churn; per-frame cost.
**Verdict:** wrong as the *system*, right as the *bootstrap*: it is an excellent zero-day pseudo-label generator for Architectures A/E, and a fine "day-one demo" while the real pipeline trains.

---

### Architecture C — Synthetic-Data Factory + Auto-Distilled Specialists

**Intuition.** If labels must feed a supervised detector, make the labels free. Build a rendering factory that composites/simulates every club's actual kit + sponsor set onto broadcast-like footage, then *automatically* train a small per-league (or per-competition) specialist detector. Humans never label; machines never stop labeling.

```
 kit templates + sponsor SVGs + kit regulations
        │
        ▼
 ┌─────────────────────────────────────────────┐
 │ SYNTH FACTORY                                │
 │ Tier 1: 2D compositing on real broadcast     │
 │         frames (players via person seg,      │
 │         logos TPS-warped onto torso regions) │
 │ Tier 2: 3D cloth sim (Blender) on animated   │
 │         SMPL players, broadcast-camera rigs  │
 │ Tier 3: diffusion img2img "realism polish"   │
 │         (labels preserved from Tier 1/2 geometry) │
 └──────────────┬──────────────────────────────┘
                ▼
   auto-train league specialist (YOLO-class, N≈100 classes)
                ▼
   nightly eval on pseudo-gold set → auto-deploy or auto-rollback
```

**Annotation:** zero human boxes; kit templates/SVGs are the supervision.
**Scalability:** new club = new factory config + overnight retrain of one league specialist. Cost is compute, not humans. But note: this *re-couples classes to weights* — mitigated by sharding (per-league models of ~100 classes, retrained independently) rather than one 8,000-class monolith.
**Expected accuracy:** governed by the sim-to-real gap. Compositing alone historically gets you ~70–85% of real-data performance on logo tasks; adding real-background compositing + degradation modeling + a small real pseudo-labeled mix typically closes most of the rest. Realism bar (answering Q2): you need *degradation realism* (blur, compression, scale, lighting) and *placement realism* (cloth warp, occlusion statistics) far more than photorealism — detectors care about local texture statistics, not global scene beauty. Blender cloth-sim > NeRF/Gaussian-splatting here (you need *new* deformations, not re-renders of captured scenes); diffusion is useful only as a label-preserving style filter, never as a label generator.
**Engineering effort:** high up front (the factory is a real product), low marginal.
**Risks:** silent sim-to-real failures on unusual kits (metallic prints, camo patterns); retrain treadmill; regression risk on every auto-deploy. Needs the nightly-eval harness to be trustworthy — which itself needs some verified real data (chicken-and-egg resolved by Architecture E's mining).
**Verdict:** the factory is extremely valuable — but as a *data organ* feeding embeddings and proposers (A) and pseudo-label bootstraps (E), not as the primary architecture. As the primary architecture it merely converts the annotation treadmill into a retraining treadmill.

---

### Architecture D — Kit-Geometry Pipeline (Human Parsing → Jersey Canonicalization → Template Registration)

**Intuition.** Invert the problem. Don't search frames for logos; search for *players*, unwrap their jerseys into a canonical texture space, and *register* the known kit template against the unwrapped texture. Logos are then found by *where the kit says they are*, and even a 12px smear of the right color in the right place becomes attributable evidence. This is recognition-before-detection.

```
 video ─▶ player det+track ─▶ pose (HRNet/ViTPose) ─▶ human parsing ─▶ torso/sleeve/shorts UV-unwarp
                                                                            │
 kit template (front/back/sleeve layouts, ─────────────────────────────────▶ dense registration
 logo slots from kit regulations)                                           (template ↔ unwrapped texture)
                                                                            │
                                                                            ▼
                                                        per-slot evidence score per frame
                                                        → reproject slot to image → box + visibility
```

**Training:** all components are off-the-shelf, class-agnostic, and *never grow with the catalog* (person detection, pose, parsing are solved commodities in sports footage). The registration step is classical (dense correspondence / TPS fit) or a small self-supervised warp net trained on synthetic cloth renders.
**Annotation:** zero per club *if* kit templates exist; where they don't, the template itself can be auto-built by aggregating unwrapped jersey textures across one match (median texture over thousands of unwrapped torsos = a self-generated template — this answers Q4's hard case).
**Unique strengths:** (1) per-player attribution falls out for free (you know whose torso it is — jersey number OCR on the unwrapped back closes the loop); (2) detects *occluded/invisible* sponsor slots, i.e., can report "chest sponsor present but occluded 40% of its on-screen time" — an analytics dimension no detector-first approach offers, and one sponsors genuinely pay for; (3) extreme robustness on tiny logos because evidence accumulates in canonical space across hundreds of frames.
**Weaknesses:** covers only *on-kit* logos — perimeter boards, flags, on-screen graphics need a separate path; pipeline depth (det→pose→parse→unwarp→register) multiplies failure modes; scrums/mauls/rucks are parsing nightmares (though — usefully — they're exactly when logos are unreadable anyway, so failures correlate with zero-value frames); wide shots lack the pixels for parsing.
**Engineering effort:** highest of all options.
**Verdict:** too narrow to be *the* architecture, too powerful to skip: as a *branch* for on-kit analytics it delivers per-player stats and occlusion-aware exposure that pure detection cannot, and it converts kit regulations — data you sometimes get for free — into supervision.

---

### Architecture E — Temporal Mining Flywheel (Track-First + Pseudo-Labels + Micro-Verification)

**Intuition.** The archive of past matches is an unlabeled goldmine, and *time* is the cheapest supervision that exists. Detect sloppily but track tightly: any logo that is confidently identified in even 1% of a track's frames labels the *entire track* via SAM2-style mask propagation — a 100–1000× label amplifier. Feed amplified labels back to improve the sloppy detector. Humans only audit disagreements.

```
                    ┌────────────── weekly retrain ◀─────────────┐
                    ▼                                            │
 match video ─▶ cheap proposer ─▶ tracklets (ByteTrack/SAM2) ─▶ label amplification
                    ▲                    │                       (1 confident ID → whole track)
                    │                    ▼                              │
            bootstrap: OV model     consensus check:                   ▼
            (Arch B) on day one     retrieval ✓ geometric ✓ VLM ✓ ─▶ auto-accept ─▶ pseudo-label store
                                         │                                              │
                                         ▼                                              ▼
                                   disagreement ─▶ HUMAN QUEUE                 metrics + retraining
                                   (~50 crops/match, ~10 min)                  corpus (compounds forever)
```

**Annotation:** ~10 minutes of accept/reject clicks per match, decaying over time as consensus improves. This *is* the active-learning design (Q7): humans see only samples where verifiers disagree or where a *new* logo's first-week matches need sign-off — sampling by disagreement + novelty + exposure-value (a confusion on the title sponsor matters more than on a shorts logo). Expected annotation reduction vs. supervised: 100–1000× (clicks on pre-cropped candidates vs. drawn boxes on raw frames; each click labels a whole track).
**Scalability:** improves *with* scale — more footage = more free labels. This is the only architecture whose accuracy has positive feedback with business growth.
**Expected accuracy:** starts mediocre (bootstrap quality), compounds toward supervised-level within weeks of footage per league.
**Risks:** confirmation bias if consensus checks are correlated (mitigate: retrieval, geometric matching, and VLM judging are architecturally independent signals); tracker ID-switches poison amplified labels (mitigate: amplify only within high-confidence track segments, never across shot cuts).
**Verdict:** not a standalone architecture — it is the *learning loop* that should wrap whichever perception stack you choose.

---

### Architecture F (synthesis preview) — A + D-branch + C-as-data-organ + E-as-flywheel, bootstrapped by B

The five options above are deliberately pure-paradigm. §6 composes them: A is the spine (only architecture with true O(1) class growth *and* controllable accuracy), C feeds it synthetic training/reference views, E wraps it in a compounding improvement loop with micro-human-verification, D runs as a parallel branch for per-player/occlusion analytics where kit data exists, and B exists only for day-zero bootstrap.

---

## 5. Comparative Analysis

Scale: ●●●●● best → ● worst, for *this* problem (annotation-cost-dominant, 5–10 yr horizon).

| Criterion | A: Proposer+Retrieval | B: Frozen OV | C: Synth Factory | D: Kit Geometry | E: Flywheel (wrapping A) |
|---|---|---|---|---|---|
| Detection accuracy (steady state) | ●●●● | ●● | ●●●○ | ●●●● (on-kit only) | ●●●●● |
| Annotation cost | ●●●●● (0 boxes) | ●●●●● (0) | ●●●●● (0) | ●●●●○ | ●●●●○ (min/match) |
| Inference speed / cost | ●●●● | ● | ●●●●● | ●● | ●●●● |
| Engineering complexity | ●●●○ | ●●●●● (simplest) | ●● | ● (deepest) | ●●○ |
| Scalability to 8k logos | ●●●●● | ●●●○ (prompt cost) | ●● (retrain shards) | ●●●● | ●●●●● |
| Generalization to new conditions | ●●●● | ●●● | ●● (sim gap) | ●●● | ●●●●● (learns from footage) |
| Robustness (tiny/blur/occl.) | ●●● alone, ●●●● w/ temporal | ●● | ●●● | ●●●●● (canonical-space accumulation) | ●●●●● |
| Cost of adding a club | metadata + optional 5-min review | metadata | config + overnight retrain | template ingest (or auto-build) | metadata + first-match review |
| Cost of adding one logo | 1 DB insert | 1 prompt | shard retrain | template edit | 1 DB insert |
| Production readiness path | clear | immediate but capped | long | long | clear, staged |
| Maintenance cost | ●●●● (2 frozen-ish models + DB) | ●●● (model churn risk) | ●● (factory + retrain fleet) | ●● | ●●● |
| Expected failure cases | tiny-logo recall; lookalike wordmarks | small objects broadly; cost | unusual fabrics/prints; silent sim gaps | scrums, wide shots, no-template clubs | bootstrap-phase noise; tracker errors |
| 5-yr scalability | ●●●●● | ●●● | ●●● | ●●●● | ●●●●● |

Key trade-off rulings (per your final requirement):

- **A vs. supervised-anything:** A gives up perhaps 3–8 mAP at steady state versus a hypothetical fully-annotated supervised system, in exchange for reducing per-class human cost from ~40 hours to ~0. At your scaling ambitions this is not a close call — the supervised comparison point *cannot exist* at 8,000 classes anyway.
- **B's simplicity vs. its ceiling:** tempting, but a frozen ceiling on your core product metric is strategic malpractice for a 5–10 yr platform. Use it for bootstrap only.
- **D's accuracy vs. its depth:** run it where its unique outputs (per-player, occlusion-aware) are billable; don't put it on the critical path for basic presence/duration metrics.

---

## 6. Recommended Long-Term Architecture: "LARS" — Localize-Agnostic, Recognize-by-Search

*(Composition F, specified for production.)*

```
════════════════════════════ OFFLINE / CATALOG PLANE ════════════════════════════
 sponsor SVG/PNGs ─▶ REFERENCE FACTORY ─▶ multi-view renders (TPS cloth-warp, blur,   
 kit templates       (Arch C, Tier 1–2)    720p/4K degrade, lighting, partial crops)  
 kit regulations            │                                                          
                            ▼                                                          
                     EMBEDDING ENCODER (metric-learned once on public+synth logo data)
                            │                                                          
                            ▼                                                          
                     LOGO INDEX (ANN, FAISS-class) + CATALOG DB                        
                     {logo_id, club_id, valid_seasons, expected_slots, brand_group}    

════════════════════════════ ONLINE / MATCH PLANE ═══════════════════════════════
 match video + team sheet                                                              
   │                                                                                   
   ├─▶ shot segmentation ─▶ camera-type classifier (wide/close/replay/graphic)         
   │                                                                                   
   ├─▶ PLAYER BRANCH (Arch D): det+track ─▶ pose/parse ─▶ jersey unwarp ─▶            
   │     template registration ─▶ per-slot evidence + jersey-number OCR                
   │                                                                                   
   ├─▶ GENERIC BRANCH (Arch A): class-agnostic logo proposer (keyframes, 5fps) ─▶     
   │     rectify crop ─▶ embed ─▶ ANN search [filtered: this match's vocabulary        
   │     = both clubs' sponsors + competition + stadium advertisers] ─▶ match+margin   
   │                                                                                   
   ├─▶ TEMPORAL FUSION: tracklet-level identity voting; SAM2-style propagation         
   │     back-fills frames where proposer missed; per-track single identity            
   │                                                                                   
   ├─▶ VERIFICATION CASCADE (cheap→expensive, only on low-margin cases):               
   │     embedding margin ─▶ geometric match vs. reference ─▶ VLM judge ─▶ human queue 
   │                                                                                   
   ▼                                                                                   
 ANALYTICS ENGINE: presence, freq, duration, screen %, visibility score               
 (size × sharpness × occlusion × centrality), timeline, per-player (via branch D),     
 per-team, per-camera-type                                                             

════════════════════════════ LEARNING PLANE (Arch E) ════════════════════════════
 accepted matches ─▶ pseudo-label store ─▶ weekly: (a) refresh proposer,               
 (b) mine hard negatives for encoder, (c) add real crops as index side-views           
 human verdicts (~10 min/match, decaying) ─▶ gold eval set (grows free forever)        
```

### Module responsibilities and the two answers that matter

**Onboarding a new club (Q1) — the critical workflow, end to end:**
1. Ingest 20 sponsor PNGs/SVGs + club metadata (5 min, non-expert task).
2. Reference Factory renders ~200 synthetic views per logo; encoder embeds them; index insert. (Automatic, ~minutes of compute.)
3. First broadcast match runs through the *unchanged* pipeline — no weights were touched anywhere.
4. Real crops matched during match 1 get added to the index as additional views (the index self-enriches with real-domain exemplars; matching quality jumps at match 2).
5. A human spends ~10 minutes reviewing the verification queue for the new club's first match.
Total human cost: **~15 minutes per club**, constant in catalog size. Compare: ~40–60 hours supervised.

**Adding one new logo mid-season:** steps 1–2 only. Zero human minutes if you trust the flywheel; two if you don't.

**Logos as supervision (Q3):** yes — the SVG *is* the ground truth, in three distinct roles: (a) source geometry for synthetic reference views (vector → arbitrary resolutions/warps without artifacts); (b) canonical target for geometric verification (homography/TPS fit of the crop against the vector rendering — a near-zero-false-positive check); (c) structured metadata (dominant colors, aspect ratio, text content for OCR cross-checking — a wordmark crop whose OCR reads "EMIRATES" is verifiable without any learned model at all). The OCR cross-check on wordmark logos is an underused, essentially free orthogonal signal.

**Kit templates as supervision (Q4):** where available, they define slot priors that (a) boost proposer recall via spatial priors on parsed torsos, (b) enable occlusion-aware exposure metrics, (c) let branch D auto-verify branch A (a "chest" match on a region the template says is a sleeve is flagged). Where unavailable, the median-unwrapped-texture trick auto-builds one from a single match.

**Temporal propagation (Q5):** the single highest-leverage robustness mechanism: identity is decided per *track*, not per frame; one confident frame labels a 300-frame track; misses are back-filled; exposure duration comes from track lifespan (more accurate than per-frame detection counting, which undercounts blurred intervals).

**Foundation models as annotators (Q6):** used in exactly three contained roles — day-zero bootstrap (B), mask propagation (SAM2), and crop-level verification judging — never as the primary detector. Reliability is enforced by *decorrelated consensus*: a pseudo-label ships only when retrieval margin, geometric verification, and (for hard cases) the VLM judge agree; disagreements route to the human queue and become gold data. Trust is measured, not assumed: the growing human-verified set continuously scores each verifier's precision, and consensus weights adapt.

**Five-year evolution (Q9) — 500 clubs, 8,000 logos, many competitions:**
- The *architecture does not change*; the index and vocabulary filters grow. This is the point of the design.
- Vocabulary priors get richer: per-competition advertiser pools, stadium-specific perimeter inventories, season-validity windows — all metadata, all zero-training.
- Encoder/proposer get periodically *refreshed* (not extended — they were never class-coupled) using the multi-year pseudo-label corpus; each refresh is one model swap validated against the free-grown gold set.
- Brand-group handling emerges (Heineken vs. Heineken 0.0): the index becomes hierarchical (brand → variant), and analytics can report at either level — again metadata, not ML.
- Compute scales linearly with matches and is dominated by the cheap proposer; ANN search at 8k (or 8M) references is a rounding error.
- The moat, note, is no longer the models — it's the accumulated verified corpus and the reference/metadata catalog. Architect data ownership accordingly.

**Zero-budget variant (Q10):** if annotation budget is literally zero today: Arch B (image-prompted OWLv2/T-Rex2-class) + ByteTrack + per-match vocabulary filtering, shipped in ~2 weeks, while the Reference Factory and proposer train in the background from public data. Migrate to LARS module-by-module; nothing is thrown away because B's outputs seed E's pseudo-label store.

### Why LARS wins the stated trade-off

Every gradient step in LARS is class-agnostic; every class-specific fact lives in a database. Therefore: marginal human cost per club ≈ 15 min and *constant*; marginal cost per logo ≈ 0; no retraining cascade, no forgetting, no cross-catalog regression testing; and the accuracy gap versus an (unbuildable) fully-supervised oracle is actively closed over time by the flywheel — using footage you were going to process anyway.

---

## 7. Experimental Validation Plan

**Datasets.**
- *Public pretraining:* LogoDet-3K, OpenLogo, FlickrLogos-32 (proposer + encoder training, with held-out *classes* to measure open-set generalization — the split must be by class, not by image).
- *Rugby gold set (the only real annotation spend of the project):* 6–10 matches across resolutions (720p→4K), competitions, and weather; exhaustively annotated boxes + identities + occlusion flags. ~40–80 annotator-hours, one time, used **only for evaluation, never training** — it is the instrument, not the fuel.
- *Synthetic benches:* factory outputs with perfect labels for controlled ablations (scale/blur/occlusion sweeps).
- *Longitudinal set:* the flywheel's human-verified queue verdicts, accumulating free gold data monthly.

**Metrics.**
- *Open-set core:* mAP and recall@FP-rate on **classes never seen in any training**, as a function of logo pixel-height (buckets: <20px, 20–40, 40–80, >80) — the pixel-height curve is where this problem lives.
- *Business-facing:* exposure-duration error per sponsor (|predicted − gold| seconds), screen-share error, timeline IoU; these matter more to the product than mAP.
- *Scaling (the thesis metrics):* human-minutes per onboarded club; match-2 vs. match-1 accuracy for a new club (measures index self-enrichment); accuracy vs. catalog size (does club #200 degrade club #1? LARS predicts no; verify it).
- *Flywheel health:* pseudo-label precision vs. human verdicts over time; human-queue volume decay curve.

**Ablations.**
1. Encoder: generic DINOv2/CLIP vs. metric-learned; synthetic-view count per reference (10/50/200); real-crop index enrichment on/off (predicted: largest single win).
2. Proposer: public-data-only vs. +synthetic vs. +flywheel pseudo-labels; keyframe rate vs. recall (cost knob).
3. Vocabulary filtering: open-catalog (8k) vs. match-filtered (~50) search — quantifies the prior's value (predicted: large precision gain on lookalikes).
4. Temporal fusion on/off — predicted: +10–20 recall points on <40px bucket, the headline result.
5. Verification cascade: each verifier's marginal precision at fixed recall; consensus vs. single-verifier pseudo-label quality (tests confirmation-bias defense).
6. Synthetic realism tiers (compositing vs. cloth-sim vs. +diffusion polish) vs. downstream accuracy — expected: sharply diminishing returns after degradation-realistic compositing; this ablation caps factory over-investment.
7. Branch D value-add: per-player attribution accuracy and occlusion-aware exposure vs. branch-A-only.

**Success criteria (pre-registered).** Unseen-class recall ≥ 85% at ≥ 95% precision for logos > 40px; exposure-duration error < 10% for top-3 sponsors per club; onboarding ≤ 20 human-minutes per club; no measurable degradation of existing clubs when catalog grows 10×.

---

## 8. Future Research Directions

1. **Canonical-texture-space analytics as the primary representation.** Push Architecture D further: maintain a per-player, per-match *texture accumulation buffer* (the jersey as a slowly-completed image). Exposure analytics computed in texture space then reprojected may eventually obsolete frame-space detection for on-kit sponsors entirely — and enables "sponsor legibility" scoring (was the logo ever actually *readable*?), a more honest product metric than raw seconds.
2. **Retrieval-native detection heads.** Replace the propose-then-match two-step with a single-pass detector whose classification head *is* an ANN lookup over a frozen index (queries attend to reference embeddings as keys). Gets closed-set speed with open-set growth; the training recipe (class-agnostic, reference-conditioned) is a publishable contribution.
3. **Broadcast-domain self-supervised pretraining.** A DINO-style SSL pass over thousands of hours of unlabeled rugby broadcast before any task training — likely the cheapest global accuracy lever available, and it touches zero labels.
4. **Cross-match consistency as free supervision.** The same club's kit is identical across a season's matches. Embedding constraints ("this club's chest region should embed consistently across matches") provide season-scale self-supervision with no labels — and automatically flag mid-season kit changes as anomalies (which is itself a sellable alert).
5. **Uncertainty-priced analytics.** Report exposure as calibrated intervals, not point estimates; route human verification budget to the sponsors/intervals where uncertainty × contract-value is highest. Turns the remaining human effort from QA cost into a pricing feature ("audited-grade" vs. "standard" reports).
6. **Generative stress-testing.** Use the diffusion tier of the factory adversarially: search augmentation space for renderings that break the encoder, add them to training. An automated red-team that permanently replaces the "annotate more hard cases" reflex.
7. **VLM-native verification at scale.** As small VLMs get cheap, promote the VLM judge from tie-breaker to universal second opinion on every track — potentially deleting the human queue for all but novel-logo sign-off, taking marginal human cost per club from ~15 minutes toward ~2.

---

## Appendix: One-Line Answers to Q1–Q10

| Q | Answer |
|---|---|
| 1 | New club = PNG ingest → synthetic reference views → index insert → 10-min first-match review. No boxes, no training. (§6) |
| 2 | Yes, for class-agnostic and embedding training. Compositing + Blender cloth-sim; diffusion only as label-preserving polish; degradation realism ≫ photorealism. (§4C) |
| 3 | Yes — SVGs are ground truth for synthetic views, geometric verification targets, and OCR/color cross-checks. (§6) |
| 4 | Yes — slot priors, occlusion-aware metrics, cross-branch verification; auto-buildable from one match via median unwrapped texture. (§4D, §6) |
| 5 | Highest-leverage mechanism in the system: track-level identity voting, 100–1000× label amplification, back-filled misses. (§4E) |
| 6 | Reliable only in contained roles (bootstrap, propagation, crop judging) under decorrelated consensus, continuously scored against human verdicts. (§6) |
| 7 | Verification-not-annotation: humans accept/reject pre-cropped candidates sampled by verifier disagreement × novelty × exposure value; 100–1000× reduction. (§4E) |
| 8 | LARS: catalog plane (references→index), match plane (proposer→retrieval→temporal fusion→verification cascade), learning plane (flywheel). (§6) |
| 9 | Architecture unchanged; index, metadata priors, and verified corpus grow; models refreshed (never extended) from free pseudo-labels. (§6) |
| 10 | Ship image-prompted OV + tracking + vocabulary filter in 2 weeks; migrate module-wise to LARS; discard nothing. (§6) |
