<!-- Converted from LogoLens_MSc_Dissertation_v14.docx. The Word source remains unchanged. -->

**UNIVERSITY OF BRADFORD**

**FACULTY OF MANAGEMENT, SCIENCES AND ENGINEERING**

**MSc Thesis**

**MAI XUAN HOA**

**LOGOLENS: A LOW-COST COMPUTER-VISION SYSTEM FOR MEASURING AND VALUING SPONSOR-LOGO EXPOSURE IN SPORTS BROADCASTS**

Words: 11,851

<!-- page break -->

**﻿LOGOLENS: A LOW-COST COMPUTER-VISION SYSTEM FOR MEASURING AND VALUING SPONSOR-LOGO EXPOSURE IN SPORTS BROADCASTS**

*MAI XUAN HOA*

*[Insert student ID]*

A dissertation submitted in partial fulfilment of the requirements for the degree of

**MSc Applied Artificial Intelligence and Data Analytics**

Faculty of Engineering and Digital Technologies

University of Bradford

Supervisor: *[Insert supervisor name]*

*[Month] 2026*

<!-- page break -->

## Declaration

I declare that this dissertation is my own work and has not been submitted, in whole or in part, for any other degree or qualification. All sources of information have been acknowledged, and all external material has been cited in accordance with the University of Bradford's academic-integrity regulations. The system described in this dissertation was designed and implemented by the author. Where third-party open-source models and libraries have been used, they are identified in the text. Any figures reproduced from software tools are attributed in their captions.

Signed: \_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_  Date: \_\_\_\_\_\_\_\_\_\_\_\_\_\_

<!-- page break -->

## Abstract

Sports sponsorship is a multi-billion-pound advertising channel whose value depends on how prominently and for how long a sponsor's logo is visible during a broadcast. Measuring this exposure and converting it into a monetary estimate has traditionally required either painstaking manual review or expensive commercial services, both of which are out of reach for smaller, mid-tier clubs. This dissertation designs, implements and evaluates **LogoLens**, an end-to-end computer-vision system that automatically measures sponsor-logo exposure in rugby-league broadcasts and converts it into an Equivalent Media Value (EMV) estimate, using only consumer-grade hardware. The system couples a fine-tuned YOLO detector with a reference-based team-attribution filter, pose-based assignment of logos to sellable kit positions, and a three-tier visibility-to-value model, all orchestrated behind a web dashboard.

The work follows a design-science methodology combined with an experimental evaluation on real broadcast footage from Bradford Bulls. The evaluation is deliberately conservative. Under a leakage-controlled, clip-disjoint split the detector achieves a mean Average Precision (mAP@0.5) of 0.745, whereas a naive random-frame split inflates this to 0.862; the honest figure is reported as the headline result. A stratified manual audit finds that team attribution is correct in 91.8% of 184 sampled cases, and the attribution filter removes 44% of detections that would otherwise inflate the value estimate. Characterising the exposure signal shows that 63% of frames carry two or more sponsor logos, that each covers a median of 0.145% of the screen at a median height of 46 pixels, and, from a second audit of 153 logos, that 30.7% are partly or heavily obscured — more often when the mark is rendered large, since close-up framing coincides with contact. A sensitivity analysis quantifies how the value estimate responds to key thresholds, and a controlled experiment shows that sparse frame sampling over-measures exposure by 63% relative to native-rate processing, a bias disclosed rather than hidden. A data-efficiency analysis across the seventeen sponsor classes relates annotation effort to accuracy, finding that per-class accuracy rises by 0.169 AP for each tenfold increase in annotated instances and that classes above roughly 500 instances outperform those below by 0.084 AP, which yields a concrete labelling budget for onboarding a new sponsor.

The dissertation contributes a reproducible, low-cost pipeline for sponsorship measurement, an honest evaluation methodology in a domain lacking public ground truth, and a discussion of how automated valuation relates to the wider debate on artificial intelligence in advertising. The findings support the feasibility of democratising a measurement capability previously confined to well-resourced organisations, while being candid about the system's limitations.

**Keywords:** computer vision, object detection, sponsorship measurement, media valuation, data efficiency, sports analytics.

<!-- page break -->

## Acknowledgements

I thank my supervisor for guidance throughout this project and, in particular, for encouraging me to situate the technical work within the broader discussion of artificial intelligence in advertising. I am grateful to Bradford Bulls and the associated stakeholders for the business context and the official kit materials that made the case study concrete. I acknowledge the open-source community — notably the developers of Ultralytics, Segment Anything, and DINOv2 — whose tools made a project of this scope achievable by a single student. Finally, I thank my family for their support.

<!-- page break -->

## Table of Contents

Right-click and choose “Update Field” to build the table of contents.

<!-- page break -->

## List of Abbreviations

| **Abbreviation** | **Meaning** |
| --- | --- |
| AP / mAP | Average Precision / mean Average Precision |
| API | Application Programming Interface |
| BoT-SORT | Robust multi-object tracker (Bag-of-Tricks SORT) |
| CI | Confidence Interval |
| CPM | Cost Per Mille (cost per thousand impressions) |
| DETR | Detection Transformer (object-detection family) |
| EMV | Equivalent Media Value |
| FPS | Frames Per Second |
| GPU | Graphics Processing Unit |
| IoU | Intersection over Union |
| OBB | Oriented Bounding Box |
| OCR | Optical Character Recognition |
| P / R | Precision / Recall |
| RQ | Research Question |
| SMV | Sponsorship Media Value |
| YOLO | You Only Look Once (object-detection family) |

<!-- page break -->

## List of Figures

*All figures are generated from the project's own data, tools, running system or annotation platform. Where a figure shows broadcast footage, club-identifying overlays and any caption naming an individual are blurred, in line with the position set out in Section 3.5.*

- **Figure 1.** High-value frame selection for annotation — §3.3.1

- **Figure 2.** Model-assisted annotation workflow — §3.3.2

- **Figure 3.** Overall system architecture — §4.1

- **Figure 4.** The three-tier valuation model — §4.6

- **Figure 5.** Per-class instance distribution — §5.2

- **Figure 6.** Logos per frame, screen coverage and rendered resolution — §5.2.1

- **Figure 7.** Accuracy under three splitting protocols — §5.3

- **Figure 8.** Normalised confusion matrix — §5.3

- **Figure 9.** Qualitative detection evidence on validation-export frames — §5.3

- **Figure 10.** Team-attribution output — §5.4

- **Figure 11.** Effect of the team-attribution filter — §5.4

- **Figure 12.** Parameter sensitivity — §5.6

- **Figure 13.** Sampling-rate bias — §5.6

- **Figure 14.** Annotation effort against per-class accuracy — §5.7

- **Figure 15.** Occlusion by mark size and per-class accuracy — §5.8

## List of Tables

- **Table 1.** Specified activities and outputs, and where each is addressed — §1.4

- **Table 2.** Detection accuracy under three splitting protocols — §5.3

- **Table 3.** RF-DETR validation metrics at the best checkpoint — §5.3.1

- **Table 4.** Club pricing share and AI exposure share across eight highlight videos — §5.5.1

- **Table 5.** Data efficiency across the seventeen sponsor classes — §5.7

- **Table 6.** Occlusion audit summary — §5.8

- **Table A.1.** Key system configuration — Appendix A

- **Table B.1.** Summary of experimental results — Appendix B

- **Table C.1.** Class distribution and per-class accuracy — Appendix C

<!-- page break -->

<!-- page break -->

# Chapter 1. Introduction

## 1.1 Background and motivation

Commercial sponsorship is one of the principal ways professional sport is financed. Brands pay for their logos to appear on players' kit, on perimeter boards and on other surfaces visible during a televised match. Unlike a conventional advertisement, which has a fixed duration and a published rate, the value a sponsorship delivers is implicit: it is distributed across thousands of fleeting appearances that vary in size, position, sharpness and duration with the camera work and the run of play. The question a sponsor wants answered is therefore deceptively simple: *how much was my logo seen, how clearly, and what is that worth?*

The industry answers using Sponsorship Media Value (SMV) and Equivalent Media Value (EMV), which express exposure as the cost of buying approximately equivalent paid-media attention. Nielsen's published description combines quality-weighted exposure, audience data and advertising rates, while the exact commercial algorithms remain proprietary (Nielsen, n.d.). Producing such an estimate at scale means measuring, for every brand, the total quality-weighted time its logo was on screen.

The stakes are not trivial. Kit and perimeter sponsorship is a primary revenue stream for clubs outside the top tier, where broadcast and matchday income are modest, and evidencing delivered value is often the difference between renewing a local sponsor and losing one. Yet it is exactly these clubs that cannot justify commercial analytics, so the organisations with the greatest relative need for measurement have the least access to it. This dissertation is motivated by that mismatch.

The exclusion is not merely budgetary; it reflects a structural property of the underlying vision problem. Sponsor logos are small, deformable marks on moving fabric, frequently occluded during play, and so hard to detect reliably. The same sponsor often appears on both teams' kit, on perimeter boards and in broadcast graphics, so a correctly detected logo may still be attributed to the party who did not pay for it, inflating the estimate. And each competition and season introduces a different sponsor set, so a closed-set detector must be re-annotated whenever the roster changes, with the annotation cost growing at every deployment. Together these make a general, low-cost measurement system genuinely hard to build rather than a routine engineering exercise.

The wider context is the rapid adoption of AI in advertising. Much of that discussion — the call for research on *AI and the future of advertising creativity* (Journal of Advertising Research, 2026), for instance — concentrates on generative systems that produce content. This dissertation addresses the complementary side: using AI not to *create* advertising but to *measure and value* it. The framing is motivation, not a contribution to advertising theory.

## 1.2 Problem statement

The problem is the design and honest evaluation of an automated system that measures the on-screen exposure of sponsor logos on players and converts it into a defensible monetary estimate, under three constraints that distinguish it from commercial solutions: it must attribute exposure only to the paying party, run on affordable hardware, and be reproducible and transparent enough to be audited. A subsidiary problem is what the recurring cost of manual annotation — the main barrier to scaling across competitions — actually amounts to.

## 1.3 Aim and objectives

The **aim** of the dissertation is to design, implement and critically evaluate a low-cost, reproducible computer-vision system that measures and values sponsor-logo exposure in sports broadcasts, using Bradford Bulls rugby league as a case study.

The aim is pursued through the following **objectives**:

1.    To review the literature in logo detection, tracking, team attribution, sponsorship-value measurement and weakly-supervised learning, and identify the gap the system addresses.

2.    To design a modular pipeline that detects sponsor logos, attributes each to the correct team, assigns it to a sellable kit position and aggregates exposure into a media-value estimate.

3.    To implement it as a working system with a processing backend and analytics frontend, on open-source models and consumer hardware.

4.    To characterise the exposure signal empirically — logos per frame, share of screen, rendered resolution, frequency of occlusion — and to evaluate the system on real footage under leakage-controlled protocols and human audits, quantifying its sensitivity to key parameters.

5.    To quantify how annotated data per sponsor class affects the accuracy achieved on that class, and derive a practical labelling budget for adding a new sponsor.

6.    To discuss the results against the wider debate on AI in advertising, and identify limitations and future work.

## 1.4 Research questions

The evaluation is organised around four answerable research questions, following the measurement chain from detection to exposure and value, then asking what the system costs to extend. The broader AI-in-advertising context remains an interpretive objective rather than a separate research question because it is not independently tested by the experiments.

- **RQ1.** To what extent can a pipeline deployed on consumer hardware accurately detect sponsor logos in unseen broadcast clips under a leakage-controlled protocol and attribute each detection to the correct team?

- **RQ2.** What are the measurable properties of sponsor-logo exposure in broadcast footage — how many logos appear at once, what share of the screen they occupy, at what resolution they are rendered, and how often they are obscured — and what do those properties imply for the measurement?

- **RQ3.** How can per-frame detections be operationalised as a transparent, quality- and duration-weighted media-value estimate, and how sensitive is that estimate to key parameters and temporal sampling?

- **RQ4.** What association is observed between per-class annotation volume and held-out detection accuracy, and what indicative onboarding budget follows within this case study?

The questions were framed to cover the project's specified activities and outputs, and Table 1 records where each is addressed, so that the correspondence can be checked directly rather than inferred.

| **Specified activity** | **Research question** | **Where addressed** |
| --- | --- | --- |
| Train and evaluate logo detection models | RQ1 | §4.3, §5.3, §5.3.1 |
| Detect multiple logos simultaneously | RQ2 | §4.2, §5.2.1 |
| Analyse logo size and screen coverage | RQ2 | §5.2, §5.2.1 |
| Measure occlusion levels | RQ2 | §3.4, §5.8 |
| Assess image quality and readability | RQ2 | §5.2.1 |
| Measure visibility duration | RQ3 | §4.6, §5.6 |
| Develop a Logo Visibility Score | RQ3 | §4.6, §5.5 |
| *Output:* logo detection engine | RQ1 | §4.1–§4.3 |
| *Output:* visibility scoring framework | RQ3 | §4.6 |
| *Output:* performance evaluation reports | RQ1, RQ3 | Chapter 5, §4.7 |

*Table 1. Specified activities and outputs, and where each is addressed.*

## 1.5 Scope and delimitations

The dissertation focuses on sponsor logos carried on players' kit (jersey sponsorship) in rugby league, with Bradford Bulls as the primary case. Perimeter advertising boards and broadcast graphics are handled by exclusion rather than being valued in their own right. EMV is treated as an industry-standard proxy for advertising attention, not as an actual transaction price; the dissertation does not attempt to model sponsorship revenue econometrically. No identification of individual players or spectators is performed, for reasons discussed in the methodology. All quantitative results are obtained at the scale of a single-student project — one sport, one primary club, and a modest number of matches — so claims about generality across sports and clubs are treated as design intentions to be tested rather than as demonstrated outcomes.

## 1.6 Contributions

The dissertation makes the following contributions:

1.    **A reproducible, low-cost measurement system** coupling logo detection, team attribution, position assignment and three-tier valuation on consumer hardware.

2.    **An evaluation methodology without public ground truth**, combining leakage-controlled splits, a stratified attribution audit, sensitivity analysis and measured sampling bias.

3.    **An empirical characterisation of exposure**, including concurrent marks, screen coverage, rendered resolution and occlusion.

4.    **A sponsor-level data-efficiency curve** converting annotation cost into a practical labelling budget.

<!-- page break -->

# Chapter 2. Literature Review

## 2.1 Object detection and its evaluation

Two detector families are relevant. The single-stage YOLO family, introduced by Redmon et al. (2016) and maintained through the open-source Ultralytics implementations (Jocher et al., 2023), frames detection as a single regression from pixels to boxes and class probabilities, prioritising inference speed while steadily improving accuracy — attractive for video on modest hardware. The transformer-based DETR line removes hand-designed components such as non-maximum suppression at the cost of higher computational demand. For a system processing long broadcasts on a single consumer GPU the trade-off favours YOLO, and a recent YOLO variant is adopted here.

Performance is conventionally reported as Average Precision at a given IoU threshold and its mean over classes, mAP (Everingham et al., 2010; Lin et al., 2014). A recurring pitfall, acute for video, is data leakage: because consecutive frames are highly correlated, a random frame-level split puts near-duplicates on both sides and produces optimistic scores that do not reflect performance on unseen footage. The importance of clip-disjoint splitting is well established in sports video (Deliège et al., 2021) and is treated as a first-class concern in Chapter 3.

## 2.2 Logo detection and recognition

Logos differ from generic objects: they are small relative to the frame, appear against cluttered backgrounds, deform on fabric and belong to a large open-ended class set. Early work relied on curated datasets such as FlickrLogos-32 (Romberg et al., 2011); Su et al. (2018) introduced the OpenLogo benchmark and drew attention to two persistent obstacles, the scarcity of annotated examples for most brands and the *open-set* nature of the task, in which a deployed system inevitably meets brands it was never trained on.

Two design responses appear. The conventional *closed-set* detector is fine-tuned on a fixed set of brand classes, achieving high accuracy within that set but unable to recognise a new brand without re-annotation and retraining. *Open-set logo retrieval* instead matches detected regions against a gallery of reference exemplars, so new brands are added by inserting exemplars; retrieval approaches fusing visual features with text read from the logo scale to large brand sets. The present system uses a closed-set detector, justified because a club's roster is small and stable within a season. That makes the cost of admitting a new brand explicit rather than eliminating it, and Section 5.7 measures what that cost actually is; the retrieval alternative, which trades annotation cost for gallery maintenance, is returned to in the future work.

Sponsor logos are also, in the technical sense, *small objects* — a recognised weak point of general detectors, since the features available for a target a few pixels across are limited and easily lost through successive downsampling. The standard mitigations of higher input resolution, multi-scale aggregation and input tiling trade computation for the ability to resolve small marks, and the choices made in Chapter 4 follow directly from this. The prevalence of small logos also affects evaluation: a fixed pixel-area threshold reasonable for everyday objects would discard most genuine sponsor logos, which is why the visibility model uses a deliberately low floor, justified empirically in Chapter 5.

From the standpoint of valuation, a limitation of this literature is that it treats detection and recognition as ends in themselves. It rarely addresses *attribution* — which party a detected logo belongs to — even though a correctly detected logo on the wrong shirt is a costly error. Attribution is therefore treated as a distinct sub-problem here, and is reviewed next.

## 2.3 Multi-object tracking and team attribution in sports video

Attributing a logo to the correct team means knowing which player wears it and which team that player belongs to, connecting this work to the literature on player tracking and team identification. Tracking-by-detection is standard: a detector locates people per frame and a tracker associates them into consistent tracks. ByteTrack (Zhang et al., 2022) improved association by retaining low-confidence detections during matching, and BoT-SORT (Aharon et al., 2022) added camera-motion compensation and appearance features — both relevant to fast, camera-panned rugby-league footage.

Team identification is complicated because opponents' kits change from match to match, making a per-team trained classifier impractical. Leading SoccerNet Game-State-Reconstruction solutions (Deliège et al., 2021) instead cluster players by colour and appearance and assign labels by majority vote over each track, adapting per match without additional training; colour histograms remain strong when kits differ in luminance, while learned embeddings from CLIP-style encoders (Radford et al., 2021) and the sigmoid-loss variant SigLIP (Zhai et al., 2023) help when colours are similar. That reference-based philosophy is adopted directly in Chapter 4. What this literature does not consider is the *financial* consequence of an attribution error, which motivates the revenue-safe policy introduced here.

## 2.4 Measuring sponsorship exposure and media value

The rationale for measuring exposure *quality* rather than counting appearances rests on the sponsorship-effectiveness literature, which treats sponsorship as a distinct channel whose effects are indirect and contextual (Cornwell, 2019; Cornwell & Kwon, 2020). Experimental work on how viewers process on-screen sponsorship signals repeatedly finds that recognition and recall depend on the size, duration, centrality, motion and contrast of the stimulus (Breuer & Rumpf, 2012; Rumpf et al., 2020) — the theoretical justification for weighting each detection by a visibility score rather than treating all appearances equally.

Translating weighted exposure into money is done through EMV/SMV. CPM is the cost of one thousand impressions (Google Ads, n.d.); in broadcast valuation it must be tied to a defined advertising unit rather than multiplied directly by seconds. The GumGum Sports patent describes a 30-second commercial-cost equivalent discounted by duration, prominence, size, clarity and position, while Nielsen describes a proprietary Quality Index combined with audience and advertising rates (Katz et al., 2024; Nielsen, n.d.). LogoLens therefore treats its quality-weighted seconds as fractions of a 30-second reference spot. The result is a transparent scenario proxy for paid-media equivalence, not a transaction price or behavioural outcome.

ExposureEngine (Sarkhoosh et al., 2025) addresses the upstream visibility problem rather than publishing an EMV formula: its oriented boxes reduce geometric overstatement under rotation and perspective. LogoLens retains an oriented-box correction as an extension point but uses axis-aligned detections in the reported experiments. A structural obstacle common to both systems is the absence of a public benchmark with sponsorship-ownership labels, forcing each valuation pipeline to construct its own evaluation procedure.

The limitations of EMV as a construct should be explicit, since the dissertation adopts it. EMV measures *opportunity to see* rather than any behavioural or attitudinal outcome: it says nothing about whether a viewer attended to the logo, remembered it or acted on it, and it inflates if technically-visible but psychologically-negligible appearances are counted. Frameworks that bridge this gap weight exposure with attention or recall models derived from eye-tracking (Rumpf et al., 2020), but require data a low-cost system cannot obtain. The pragmatic justification for retaining EMV is that it is the language in which clubs and sponsors actually negotiate, so a transparent estimate is directly useful even as an imperfect proxy. The three-tier quality-weighting is best understood as a cheap partial approximation of the attention weighting the recall literature would recommend — the system automates the industry-standard proxy at low cost, and neither claims nor requires that the proxy be a perfect measure of advertising effect.

Sponsorship valuation has progressed from manual timing and advertising-rate equivalence, through brittle rule-based logging, to computer vision that weights appearances by size, position, duration and clarity. Foundation models now promise to reduce the remaining annotation burden. This dissertation contributes no new valuation theory; it demonstrates a transparent, low-cost implementation and measures the supervision required per sponsor before proposing its removal.

## 2.5 Reducing annotation cost: weak supervision, foundation models and synthetic data

Three research lines could reduce the linear annotation cost of a closed-set detector. *Programmatic weak supervision*, exemplified by Snorkel (Ratner et al., 2017), combines noisy labelling sources while estimating their reliability. *Foundation models* provide such sources: Grounding DINO (Liu et al., 2023) and Segment Anything (Kirillov et al., 2023; Ravi et al., 2024) generate pseudo-labels, while DINOv2 features (Oquab et al., 2023) support crop clustering and exemplar-driven tracking through video. *Synthetic data*, including scenes reconstructed with 3D Gaussian Splatting (Kerbl et al., 2023), can add controlled rare conditions with exact labels.

What this literature does not supply is a figure for what it is worth avoiding. Weak-supervision papers argue from the premise that manual annotation is prohibitive, but the premise is rarely quantified for a specific application, so a practitioner cannot tell whether the machinery is warranted. In the sponsorship setting the question is unusually concrete, since annotation is incurred per sponsor and a roster changes by one or two brands a season rather than wholesale. This work therefore takes the complementary route: rather than adopting these techniques and asserting a saving, it measures the supervised baseline's data efficiency directly (Section 5.7). That figure is what makes it possible to judge whether the extra complexity would pay for itself, and it is the basis on which the annotation-free route is proposed as future work rather than as a result.

## 2.6 Artificial intelligence in advertising

Forward-looking analyses (Davenport et al., 2020; Huang & Rust, 2021) anticipated that AI would reshape marketing across the value chain, and a Journal of Advertising Research special-issue call (2026) frames generative AI as transforming how advertising is imagined, produced and evaluated. This is used as motivation and a discussion lens, not as a claimed contribution to advertising theory.

## 2.7 Research gap and positioning

The gap lies at the intersection of these strands. Logo-detection research provides strong detectors but largely ignores attribution and valuation. Sports-video research solves team attribution without considering its financial consequences. The sponsorship-measurement literature has a sound theory of exposure value but relies on manual methods or proprietary tools and lacks public ground truth. Weak supervision offers cheaper labelling but argues from an annotation cost asserted rather than measured. No existing work combines a reproducible, low-cost, end-to-end pipeline with an evaluation methodology suited to a domain without ground truth, and none states what supervising such a system costs per sponsor. This dissertation targets that gap.

<!-- page break -->

# Chapter 3. Research Methodology

The design of the artefact itself is deferred to Chapter 4; the concern here is with method.

## 3.1 Research design and philosophy

The dissertation adopts a **design-science** approach (Hevner et al., 2004), in which knowledge is produced by building an artefact that addresses a real problem and then rigorously evaluating it. This is appropriate because the central output is a functioning system and the research questions concern what such a system can achieve, rather than testing a pre-existing theory. It is combined with **experimental evaluation** for the quantitative components, measured under controlled conditions with defined metrics.

Two epistemological commitments follow from the domain. Because there is no public ground truth for sponsorship attribution or value (Section 2.4), the strongest evidence available for some claims is a controlled human audit rather than an automatic benchmark, so the methodology treats such audits as planned instruments rather than afterthoughts. And a clear line is drawn between *operational* claims (what the system produces, measured by its own output), *accuracy* claims (whether that output is correct, asserted only against independent human judgement) and *value* claims (the economic meaning of an EMV figure, always stated with its assumptions). The separation prevents the circular error of validating a system against its own predictions.

## 3.2 Development approach and tools

The system was developed iteratively, with each component prototyped, tested on real footage, and revised in light of observed failures. This iterative style is reflected in the evaluation, which reports not only final results but also the intermediate failures that shaped the design, on the grounds that in design-science research the reasoning behind a design is itself a contribution.

The implementation uses the Python scientific and deep-learning ecosystem. Object detection and pose estimation use the Ultralytics framework; tracking uses ByteTrack and BoT-SORT; appearance features use CLIP-family encoders; auto-labelling experiments use promptable segmentation and DINOv2 embeddings. The processing backend is built with FastAPI and the analytics frontend with Next.js. Model training was performed on rented cloud GPUs, while all inference and evaluation were performed on a single consumer workstation (an RTX 5060 Ti 16 GB GPU with an Intel i5-13400F CPU and 16 GB RAM), reflecting the target deployment environment. Software versions were pinned to ensure that trained weights remain loadable, and configuration is controlled through environment variables so that experiments are repeatable.

## 3.3 Data collection and preparation

The primary data are full-match Bradford Bulls broadcasts from publicly available streams, spanning daytime and floodlit matches, higher- and lower-quality streams, and fixtures in which both teams wore dark kit. That variety was deliberately retained so the evaluation reflects realistic difficulty rather than a curated best case. Official kit imagery and the club's kit-regulation document supplied the sponsor roster and physical logo positions; the club also supplied fixed commercial weights used to price those positions.

Broadcast frames were manually annotated with axis-aligned bounding boxes and brand labels. Axis-aligned boxes were a practical choice rather than a principled one — they are what the annotation platform and detector families support natively, and an oriented-box workflow would have raised the per-instance cost on a budget already identified as the binding constraint. The choice has a known cost, since a rotated mark is enclosed by a box larger than itself, over-stating its area and therefore its visibility; Section 4.6 explains how the visibility model is structured to accept an oriented-box correction, and Section 6.4 treats the resulting bias as a threat to validity. Annotation conventions kept the labels consistent: every visible instance was boxed, including partially occluded ones down to a legibility limit, with the home/away kit variant recorded as part of the class. The effort was deliberately kept modest, because a mid-tier club could not fund large-scale labelling and the system is only useful within that constraint; the resulting variation in how much data each class received is what makes the analysis of Section 5.7 possible.

Two properties of the preparation are methodologically important. Kit variants are distinguished, each brand carrying a home/away suffix, because the same sponsor occupies different positions against different backgrounds on the two strips. More importantly, the train/test split is **clip-disjoint**, so that no passage of play contributes frames to both sides. As Section 2.1 noted and Section 5.3 demonstrates, a random frame-level split leaks correlated frames across the boundary and inflates reported accuracy; the clip-disjoint split is the honest protocol and is used for all headline detection figures.

### 3.3.1 High-value frame selection for annotation

A full match holds on the order of a hundred thousand frames, most unsuitable for annotation: replays, crowd shots, graphics, blurred transitions, or frames with no target-team player prominently visible. Annotating at random would spend most of the budget on low-value images and under-sample exactly the sharp, logo-bearing frames the detector needs. A dedicated **frame-selection procedure** therefore extracts roughly two hundred high-value frames per video through the eight steps of Figure 1. It is distinct from the sparse frame *sampling* used at inference time (Section 4.2): this is an offline, one-off selection of training images.

Two of those steps carry most of the benefit. The static-overlay mask is estimated from the temporal standard deviation of a few hundred frames, since pixels that barely change correspond to fixed graphics such as the scoreboard and watermark, which are then excluded from scoring. And the sharpness score is a weighted Laplacian computed specifically on target-team torsos — where the logos are — with overlay and opponent regions masked out, so a frame is scored on the sharpness of the parts that matter rather than of the whole image. The remaining steps gate on shot type, player count and kit colour, then de-duplicate; the net effect is to concentrate annotation on sharp, logo-rich, non-redundant frames of the correct team.

![Figure 1](LogoLens_MSc_Dissertation_v14_media/figure_01.png)

**Figure 1. *****High-value frame selection for annotation. From each match video, an eight-step procedure — adaptive sampling, static-overlay masking, shot-type gating, person detection, target-colour filtering, weighted sharpness scoring, de-duplication and export — yields roughly two hundred high-value frames for annotation rather than a random sample.***

### 3.3.2 Annotation with Roboflow and model-assisted labelling

The selected frames were annotated on **Roboflow**, which also handled the split, resizing and augmentation. Annotating thousands of small logos by hand would have been prohibitively slow, so a **model-assisted** strategy — a form of active learning — was used (Figure 2). A seed set of roughly fifty to eighty clean, close-up frames was annotated entirely by hand, ensuring every class appeared several times; a first detector trained on that seed pre-populated predicted boxes for the annotator to accept, correct or supplement. No timing log was kept, so the workflow is reported as a practical annotation aid rather than a quantified speed-up.

![Figure 2](LogoLens_MSc_Dissertation_v14_media/figure_02.png)

**Figure 2. *****Model-assisted annotation workflow. A manually annotated seed set trains an initial model that pre-labels new frames; the annotator corrects the suggestions and feeds verified labels back into the next iteration.***

Conventions were applied throughout: every legible sponsor instance boxed, including partially occluded and motion-blurred ones; illegible or replay-embedded logos and broadcast overlays excluded; boxes kept tight. The dataset was configured with a 70/20/10 split, letterbox resizing to 1280 pixels to preserve logo aspect ratios, and a moderate augmentation policy (horizontal flip, limited rotation, brightness and blur variation) that avoids transformations distorting a logo's identity, such as vertical flips or strong colour shifts.

## 3.4 Evaluation methods and metrics

The evaluation combines four instruments, each aligned to a research question.

**Detection accuracy (RQ1).** Precision, recall and mean Average Precision at IoU 0.5 (Everingham et al., 2010; Lin et al., 2014). Reporting all three matters because they have asymmetric commercial consequences: a false positive credits a sponsor for exposure that did not occur, a false negative merely under-counts. Results are given under three splitting protocols — random-frame, clip-disjoint and extended clip-aware — precisely to expose leakage, and a per-class confusion matrix characterises the *type* of error, since a missed logo is far less harmful than one attributed to the wrong brand.

**Attribution accuracy (RQ1).** With no ground truth for team attribution, it is evaluated by **stratified manual audit**: three frames per match, at the 55%, 75% and 95% points of each clip so that team-voting has stabilised, across nine matches, giving 184 attributed detections each checked by eye against shirt colour and categorised.

**Exposure characterisation (RQ2).** Logos per frame, share of screen and rendered resolution are computed exhaustively from the annotation files, since every instance is already boxed. Occlusion is the exception — not annotated, not recoverable from a box — so it is judged by eye through the same instrument: nine instances per class under a fixed seed, 153 in all. Stratifying by class rather than proportionally is deliberate, since the question is whether occlusion differs *between* sponsors. Each item is shown with its surroundings visible, because the rater must see what covers the mark, in shuffled order so the class is not a cue, and rated unobstructed, partially covered but readable, or heavily covered; size, blur and distance are excluded from the judgement. Ratings are then set against objective per-instance features and against the per-class accuracy residuals of the data-efficiency analysis. As with the attribution audit, the single rater is a limitation recorded in Section 6.4.

**Value sensitivity (RQ3).** Since EMV cannot be validated against a true price, the model is evaluated for *structural plausibility* and *sensitivity*: exposure across brands and kit positions is examined for plausibility, and retained quality-exposure measured as the visibility and confidence floors are swept. A controlled experiment compares sparse sampling against the native frame rate on the same segment, to quantify sampling-induced bias. For commercial triangulation, within-video AI exposure shares from eight highlight analyses are also compared with the club's fixed position-pricing weights after normalising the latter from their source total of 95% to 100%.

**Data efficiency (RQ4).** Annotation effort against accuracy is examined per sponsor class, the level at which a club incurs the cost. For each of the 17 classes the training-instance count is paired with the AP achieved on the held-out partition, and two things estimated: the strength of the association, by Pearson and Spearman correlation, and its shape, by least-squares fit of AP against the base-ten logarithm of the count — logarithmic because vision learning curves are conventionally close to linear in log data volume (Sun et al., 2017). Classes are then split at a threshold and group means compared with Welch's *t*-test, converting the curve into what a practitioner needs: a number of boxes. With only 17 classes, effect sizes carry their uncertainty and the analysis is indicative of magnitude rather than precise.

Throughput (video-minutes processed per wall-clock minute) is measured on the target workstation to substantiate the low-cost, real-time claim.

Three design goals additionally function as qualitative criteria. **Generality** requires that another club could use the system by supplying its own logos and footage without code changes, assessed by whether the mechanisms are reference-based rather than hard-coded. **Revenue-safety** requires that under uncertainty the system errs towards not deducting exposure from a client, assessed by inspecting the attribution policy. **Measurement integrity** requires every reported figure to be traceable to a transparent procedure and unmeasured quantities to be labelled as such, assessed by the audit records and the explicit disclosure of biases.

## 3.5 Ethical, legal and professional considerations

Four considerations shaped the work. **Privacy**: although the footage contains people, the system performs no identification of individuals — it analyses brand exposure, not persons — which is a design constraint rather than an omission. **Disclosure in reporting**: because the case study is a specific, identifiable club, figures reproduced from broadcast footage have club-identifying overlays and any caption naming an individual blurred, while sponsor logos, the object of study and publicly displayed, are retained. **Provenance and licensing**: the source footage is publicly available, and some foundation-model components carry research-only licences that a commercial deployment would need to replace. **Professional integrity**: results are reported conservatively, unmeasured quantities are not presented as measured, and a bias unfavourable to the commercial narrative (Section 5.6) is disclosed rather than concealed. These align with the ethical expectations of the University of Bradford and with professional codes for computing practitioners.

## 3.6 Reproducibility

Pipeline configuration is externalised, model versions pinned, evaluation splits constructed by explicit rules and audit judgements recorded, so reported accuracies can be reconstructed. The primary limitation is that the source broadcasts are third-party material that cannot be redistributed; the collection and preparation process is described in enough detail for the study to be repeated on comparable footage.

<!-- page break -->

# Chapter 4. System Design and Implementation

## 4.1 Architecture overview

The system is divided into two loosely coupled parts that communicate over an HTTP API (Figure 3). The **backend** is the processing engine: a FastAPI application that accepts an uploaded video, runs it through the analysis pipeline as a background job, and exposes the results as JSON together with rendered media. The **frontend** is a Next.js dashboard that submits jobs, polls their progress, and presents the results as interactive analytics across multiple matches.

![Figure 3](LogoLens_MSc_Dissertation_v14_media/figure_03.png)

**Figure 3. *****LogoLens overall system architecture. The frontend submits jobs and polls the backend over an HTTP API; the backend runs a pipeline orchestrator and keeps the database, file storage, job queue and model zoo behind interfaces, so each can be replaced by a production equivalent through configuration alone.***

All infrastructure lies behind interfaces by design. The database (SQLite in development), file storage (local) and job queue (in-process) are each abstracted so a production equivalent — PostgreSQL, object storage, a distributed queue — replaces them through configuration alone, without altering pipeline logic. This supports the generality criterion at the infrastructure level and keeps development light enough for a single machine.

## 4.2 The processing pipeline

One upload is processed through eight job stages: metadata reading, team-reference bootstrap, detection and tracking, exposure aggregation, pricing, annotated preview, body segmentation and persistence. The central detection stage samples frames, scores visibility, applies the team filter and assigns kit positions. Optional rendering stages degrade gracefully: a failure is logged and the analytical result can still be returned.

Two separate detection passes serve different purposes. The *analytics* pass samples sparsely at two frames per second, because estimating exposure *duration* does not require every frame and sparse sampling is far cheaper; it is the source of all value figures. The *preview* pass runs at full frame rate, capped, to render a smooth review video in which boxes track each logo closely. Measurement and presentation have different frequency requirements. That the sampling rate affects the measured value is examined experimentally in Section 5.6 and is not treated as neutral.

## 4.3 Logo detection

The pipeline exposes interchangeable YOLO and RF-DETR logo backends. The headline leakage-controlled experiment uses the fine-tuned YOLO checkpoint at 1280-pixel input; RF-DETR is evaluated separately in Section 5.3.1 and is also runnable in the local bradford\_bulls environment through LOGO\_BACKEND=rfdetr. Both emit an axis-aligned box, brand class and confidence score. The detector is closed-set, appropriate for a season's known sponsor roster, while Section 5.7 quantifies the data required to add a new brand.

## 4.4 Team attribution

This component decides, per detected logo, whether it belongs to the target club. It follows the reference-based philosophy of Section 2.3 and trains no dedicated model, because opponents' kits change each match. Per sampled frame a person detector locates players and BoT-SORT maintains a stable identity across frames; a torso band is cropped, excluding grass and skin, and classified by fusing a colour histogram with a learned appearance embedding, weighted towards colour when kits differ strongly in luminance. Votes accumulate per track with hysteresis, so a single blurred frame cannot flip a label. Each logo is assigned to the player whose box most tightly contains it, and kept only if that player is on the target team.

Kit references are obtained without a mandatory manual step, at one of three levels of preference: an existing hand-built reference file if present; otherwise an automatic bootstrap that clusters players in the opening frames and selects the cluster most similar to the official kit image; and, failing that, a luminance rule for dark away kits.

The keep/drop policy embodies the revenue-safety criterion, and its asymmetry is deliberate:

\`

for each detected logo L in frame:

owner = tracked player whose box most tightly contains centre(L),

else nearest tracked player within a distance threshold, else NONE

if owner is NONE:                       drop L    # board, crowd, graphic

elif team\_vote[owner] == TARGET:        keep L

elif team\_vote[owner] == OTHER

and votes >= MIN\_VOTES:            drop L

else:                                   drop L    # conservative crediting

\`

The experimental configuration sets both TEAM\_KEEP\_UNKNOWN and TEAM\_KEEP\_UNASSIGNED to false: a detection is credited only when its owner is attributed to the target team. This reduces false credit at the cost of additional under-counting during the first frames of a track or when player assignment fails. The configuration is recorded explicitly because reversing it changes the commercial error direction.

## 4.5 Position assignment

Rather than treating all jersey logos as equivalent, each detection is assigned to one of eighteen sellable kit positions using pose estimation. Keypoints define regions corresponding to commercial slots — chest-centre, back-upper, sleeve, shorts-front, sock — rather than anatomical parts, and skin regions carry no slot so a logo is never assigned to bare skin. The exposure accruing to each slot is the basis for pricing positions differently, turning "where on the kit" into a priced variable.

## 4.6 The three-tier valuation model

The valuation model converts the detection stream into a monetary estimate in three tiers (Figure 4), each introducing a correction grounded in the sponsorship-effectiveness literature (Section 2.4).

![Figure 4](LogoLens_MSc_Dissertation_v14_media/figure_04.png)

**Figure 4. *****The three-tier valuation model. A per-frame detection stream is refined into a monetary estimate, each tier adding a correction: spatial visibility quality, then temporal and recall structure, then broadcast and competitive context.***

**Tier 1 — visibility**, per detection, is the product of a size term (the square root of the box-to-frame area ratio, so one close-up does not dominate), a position term (a Gaussian centred on the screen, since central logos attract more attention) and a clarity term (detector confidence). The implementation carries a fourth factor, an oriented-box penalty that would discount a logo skewed by camera angle, but because the deployed detector emits axis-aligned boxes (Section 4.3) it is fixed at 1.0 and inert — retained as a declared extension point so that training an oriented-box model later changes one constant rather than the model's structure. Every visibility figure in Chapter 5 therefore comes from three active terms, and the over-statement for rotated logos is assessed in Section 6.4. A low visibility floor of 0.02 keeps negligible detections from forming a segment; that value, far below the 0.1 sometimes used, is justified empirically in Section 5.6.

**Tier 2 — exposure**, computed per brand, links the surviving detections into continuous segments using track identity and sums, over segments, the product of duration, mean visibility and a duration weight. Segments shorter than half a second are discarded as flicker, and the duration weight encodes the recall finding that very short appearances are less memorable and sustained ones more so.

**Tier 3 — EMV** converts quality-weighted seconds into 30-second advertising equivalents before applying CPM, audience and a broadcast-scenario multiplier:

EMV = (quality-exposure seconds / 30) × (CPM / 1,000) × audience × scenario multiplier.

The normalisation is required by the units: CPM is a cost per thousand impressions, while broadcast media costs are represented here by a 30-second commercial equivalent. The GumGum Sports patent describes sponsorship media value in terms of 30-second commercial cost, audience and an attribution percentage based on duration and prominence; Nielsen similarly describes QI Media Value as quality-weighted exposure combined with audience data and advertising rates (Katz et al., 2024; Nielsen, n.d.). Tier 1 and Tier 2 supply LogoLens's quality attribution, so no separate unsupported global sponsorship discount is added. The scenario multiplier remains an explicit project assumption; where a channel-specific CPM is available it should be set to 1.0.

For example, 120 quality-weighted seconds at a CPM of US$22 and an audience of 40,000 gives (120/30) × (22/1,000) × 40,000 = US$3,520 for a 1.0 scenario multiplier. Using 200 raw seconds instead gives US$5,866.67, an overstatement of two-thirds. CPM and audience enter linearly and are therefore user-supplied scenario inputs to be justified, not quantities inferred by the system.

## 4.7 The analytics dashboard

The frontend turns the JSON result into five views: a multi-match overview; a per-match evidence view with preview, timeline and team-filter statistics; a sponsor profile; a report with PDF/CSV export; and a body-position view. These views support traceability from aggregate values back to detection evidence, but screenshots are omitted because they document implementation rather than answer a research question.

All charts are implemented directly in SVG rather than through a charting library, which trades development effort for full control of the visualisations and a smaller dependency surface; when no backend is present, the dashboard displays clearly labelled demonstration data.

The dashboard is the point at which the measurement becomes commercially usable, and several design choices reflect that. Brand colours are held stable across every view, so a sponsor is recognisable at a glance through a multi-match analysis. The match view places the team-filter statistics directly alongside the value figures, so a user can see at once whether attribution behaved sensibly; an unusually low or high drop rate signals that the kit-reference bootstrap may have misfired, and surfacing it supports the measurement-integrity criterion. The report view plots each brand's exposure duration against its mean visibility, separating "premium" inventory — long, prominent exposure — from frequent but low-quality appearances, which gives a club a defensible basis for differential pricing. Export to PDF and CSV lets the figures go into a sponsor report or spreadsheet, which is how a club would actually use them.

## 4.8 Output data model and interface

Analysing one video persists a single structured record, read by both the dashboard and any external consumer through the API. It captures, per brand, the segments with their start and end times, mean visibility and duration weight, plus aggregate quality-exposure, average visibility, segment count, longest segment and EMV; it also stores per-slot exposure percentages, the team-filter statistics and a per-brand timeline driving the interactive player, alongside the rendered preview and body-part overlay. Exposing all of this through a small API — create a job, poll it, retrieve the analysis and media — keeps the frontend a thin presentation layer and lets a different client or an automated reporting process consume the same outputs unmodified. Separating the record from its presentation is deliberate: the numbers a club relies on are computed once, stored, and never recomputed differently for display, which makes any figure in a sponsor report reproducible and auditable.

## 4.9 Implementation constraints

Implementation surfaced constraints that illustrate the gap between an algorithm and a running system. Training required specific settings to avoid platform-specific memory failures, and text output required explicit UTF-8 handling. Rendering the preview video and the body-part overlay proved more expensive than the detection pass itself on long inputs, which is why both are optional stages that a failure can skip without losing the analysis. Two failure modes had to be handled explicitly rather than by tuning: a tracker identity switch during a tackle can carry a brand across to an opposing player, and a player's surname printed above the sponsor mark can be picked up as a similar-looking brand. Each was addressed by a control gate rather than by a threshold, because the failure is categorical rather than a matter of degree. The need for these gates is itself evidence, discussed in Chapter 6, that automating measurement redistributes rather than removes the human role.

<!-- page break -->

# Chapter 5. Experiments and Results

Results are organised by research question. Following the methodology, operational and accuracy claims are kept distinct and unvalidated quantities identified as such.

## 5.1 Experimental setup

All inference and evaluation ran on the target workstation (RTX 5060 Ti 16 GB, i5-13400F, 16 GB RAM); training used rented cloud GPUs. Detection metrics are reported under three splitting protocols to expose leakage, attribution by the stratified audit of Section 3.4, and value-model experiments over the analytics pass across nine matches. Unless stated otherwise, figures are drawn from the project's experimental records and reconstructable from them.

## 5.2 Dataset characterisation

The extended clip-aware training set contains **10,654 annotated logo instances across 17 sponsor classes**. The class distribution is strongly imbalanced (Figure 5): the most frequent class holds 1,667 instances and the rarest 182, a ratio of 9.2 to 1. This reflects how often different kit positions appear in the footage and predicts the per-class gap observed later.

![Figure 5](LogoLens_MSc_Dissertation_v14_media/figure_05.png)

**Figure 5. *****Per-class instance distribution of the extended clip-aware training set (17 classes, 10,654 boxes). The distribution is heavily skewed, with an imbalance ratio of roughly 9.2 to 1 between the most and least frequent classes, reflecting how often each sponsor position appears in broadcast. Counted directly from the dataset's annotation files.***

### 5.2.1 Multi-logo frames, screen coverage and rendered resolution (RQ2)

Three further properties of the material shape the measurement task, each quantified from the annotation files across all 4,113 frames and 12,960 instances (Figure 6).

**Sponsor logos appear in groups, not singly.** 63.1% of annotated frames contain two or more logos and 25.9% five or more; the mean is 3.15 per frame, rising to 3.82 among frames where any sponsor is visible, with a maximum of 27. These are usually different brands rather than repeats: 61.6% of frames carry two or more distinct sponsors, a mean of 2.54. Simultaneous multi-brand detection is therefore the ordinary case, which is why the pipeline treats each frame as a set of independent detections — each separately scored, attributed and assigned to a slot — rather than resolving it to one dominant logo. It also has the valuation consequence Section 6.1 returns to: sponsors sharing a frame share the viewer's attention, which the per-detection model does not discount for. A further 17.5% of frames show no sponsor at all, a reminder that on-screen time and sponsor-visible time are different quantities.

**Individual logos occupy a very small share of the screen.** The median covers 0.145% of the frame area, 87.3% cover under 0.5% and 95.7% under 1%; the largest single instance reaches only 12.1%. Summed across a frame, sponsor marks still occupy a mean of 0.84% and 3.3% at the ninety-fifth percentile. This is a demanding small-object problem, and the empirical justification for two Chapter 4 decisions: the 1280-pixel detector input, without which these marks reduce to a handful of pixels, and the low 0.02 visibility floor, since a floor set for large objects would discard essentially the whole inventory.

**Rendered resolution sets the ceiling on readability.** In these 1080-pixel-high frames the median mark is 46 pixels tall and 68 wide; 18.7% are under 32 tall and 2.6% under 20, while only 26.3% reach 64 or more. Thirty pixels carries enough shape for a trained detector to classify but not enough for reliable text reading, which is why the pipeline identifies brands by learned appearance rather than by reading the wordmark, and why the clarity term (Section 4.6) uses detector confidence as its proxy for legibility. Image sharpness was also examined via the Laplacian variance of each crop but proved unusable: it is confounded by crop size, falling fivefold from the smallest marks to the largest (*r* = −0.45 against log pixel height) because a large crop contains proportionally more smooth fabric between the strokes, and contrast normalisation did not remove the dependence. Rendered resolution is reported instead, being exact and scale-free; no sharpness statistic is claimed.

![Figure 6](LogoLens_MSc_Dissertation_v14_media/figure_06.png)

**Figure 6. *****What a broadcast frame contains. Left: the number of sponsor logos per frame — most frames carry several, and 63% carry two or more; the grey bar is frames with no visible sponsor. Centre: the share of frame area occupied by each logo, on a logarithmic scale; 96% fall below one per cent of the frame. Right: the height at which each mark is rendered in the 1080-pixel frame, which sets the ceiling on readability. Computed from the annotation files.***

## 5.3 Detection accuracy and the effect of leakage (RQ1)

Detection accuracy depends strongly on the splitting protocol (Table 2, Figure 7). A random-frame split reports 0.862 mAP@0.5, inflated because correlated adjacent frames fall on both sides. The clip-disjoint split gives 0.702, and the extended clip-aware set 0.745 with precision 0.65 and recall 0.74; the latter is the leakage-controlled headline estimate.

| **Split protocol** | **mAP@0.5** | **Note** |
| --- | --- | --- |
| Random-frame | 0.862 | Inflated by adjacent-frame leakage |
| Clip-disjoint | 0.702 | Honest |
| Extended clip-aware | 0.745 (P 0.65, R 0.74) | Headline result |

*Table 2. Detection accuracy under three splitting protocols.*

![Figure 7](LogoLens_MSc_Dissertation_v14_media/figure_07.png)

**Figure 7. *****Detection accuracy under three splitting protocols. Random-frame splitting reports 0.862 mAP@0.5, while leakage-controlled clip-disjoint and extended clip-aware protocols report 0.702 and 0.745.***

Validation metrics converge early and then hold broadly flat, while the widening train/validation box-loss gap indicates mild overfitting. The normalised confusion matrix (Figure 8) is almost purely diagonal apart from the background row: the detector rarely confuses one brand with another, and its errors are predominantly misses concentrated on the least-represented classes.

![Figure 8](LogoLens_MSc_Dissertation_v14_media/figure_08.png)

**Figure 8. *****Normalised confusion matrix for the clip-disjoint split. The matrix is almost purely diagonal apart from the bottom background row, indicating that the detector rarely confuses brands and that its errors are misses into the background, concentrated on rare classes. Authentic framework output.***

This structure matters because a missed logo and a wrong brand have different downstream effects. The near-absence of off-diagonal mass indicates that the measured shortfall is mainly recall loss rather than brand substitution. It does not establish exposure-level accuracy, however; that requires future comparison against manual timing rather than inference from frame-level mAP.

Figure 9 provides qualitative evidence from two images in the retained validation export, reprocessed with the clip-disjoint checkpoint at 1280-pixel input. Panel A contains 11 detections in a dense multi-player scene; Panel B contains 10 detections across a close-up home-kit view. The plate is not used to calculate accuracy and is labelled separately from the leakage-controlled metric evaluation. Colours identify brands, labels report confidence and broadcast overlays are blurred.

![Figure 9](LogoLens_MSc_Dissertation_v14_media/figure_09.png)

**Figure 9. *****Qualitative output from the clip-disjoint YOLO checkpoint on two validation-export frames: (A) eleven detections during a dense multi-player scene; (B) ten detections in a close-up view showing scale variation. Colours denote brand and labels report detector confidence.***

### 5.3.1 Alternative architecture benchmark: RF-DETR

An RF-DETR model was trained on the same sponsor dataset to test whether a heavier, transformer-based detector would improve accuracy. Its best checkpoint reached 0.771 mAP@0.5 (Table 3). Per-class AP follows the same data-imbalance pattern as YOLO, while the validation score rises quickly and then plateaus.

| **Metric** | **RF-DETR (best)** |
| --- | --- |
| mAP@0.5 | 0.771 (EMA 0.778) |
| mAP@0.75 | 0.505 |
| mAP@[.5:.95] | 0.458 (EMA 0.465) |
| Precision | 0.730 |
| Recall | 0.711 |
| F1 | 0.710 |

*Table 3. RF-DETR validation metrics at the best checkpoint.*

The comparison rests on this model having been evaluated under the same discipline as the headline detector, so how its data were partitioned matters. The annotation platform's default export is a random split, which would have leaked correlated frames in precisely the way Section 5.3 warns against; that default was not used. The images were instead pooled across the platform's splits and re-partitioned by source, grouping every frame under its match or clip identifier and holding out whole groups — the 4,113 images fall into 46 such groups, of which 14 (741 images, 18.0%) were held out. No evaluation frame therefore shares a passage of play with any training frame, and because most groups are whole matches, much of the held-out data is unseen fixtures rather than merely unseen clips. The reported 0.771 is leakage-controlled and comparable in kind to 0.745.

Two residual optimisms should be declared: the held-out partition serves as both validation and test set, so the best checkpoint is selected on the data that reports the score, and the group assignment was chosen among 300 shuffles to leave fewest classes starved, slightly favouring the rarer ones. The reading is that a heavier transformer reaches accuracy comparable to, and probably a little above, the deployed detector. The latter was retained because the throughput budget of Section 5.9 leaves no headroom for a substantially heavier model and the difference sits within what these protocols can resolve. Inference cost was not measured on the target hardware, so the trade-off is argued rather than demonstrated; quantifying it is noted in the future work.

## 5.4 Team attribution (RQ1)

Figure 10 shows the stage in operation on one frame, each tracked player carrying its own decision. The stratified audit of 184 detections across nine matches found attribution correct in **91.8%** of cases (169 of 184), balanced between the target-team subset (90.7%) and the other (92.9%), above the 90% audit threshold. Errors clustered around officials or stewards, the first seconds after kickoff and one fixture where both teams wore dark kit.

![Figure 10](LogoLens_MSc_Dissertation_v14_media/figure_10.png)

**Figure 10. *****The attribution stage on one frame, as rendered by the pipeline's own overlay. Every tracked player carries a track identity and a decision: gold for the target club, grey for opponents and match officials, with a third state held for tracks that have not yet accumulated enough votes. The lower panel magnifies the defensive line, where target and opponent players stand adjacent. Because the decision is made per track rather than per frame, a single blurred frame cannot flip a label.***

The filter's practical importance shows in the detection count (Figure 11): across nine matches it removed **44%** of detections (11,161 of 25,153, ranging from 21% to 78% per match) as belonging to opponents, officials or unattributable surfaces. Without the filter, raw credited detection volume would be about 80% higher; the monetary effect depends on the quality weights of the removed detections.

![Figure 11](LogoLens_MSc_Dissertation_v14_media/figure_11.png)

**Figure 11. *****Effect of the team-attribution filter across nine matches. Of 25,153 raw detections, 11,161 (44%) are removed as not belonging to the target team, over a per-match range of 21–78%.***

## 5.5 Valuation plausibility and quality-weighting (RQ3)

Since EMV cannot be validated against a true price, the model is assessed for structural plausibility and for how its quality-weighting behaves. Exposure across brands is strongly skewed, the leading sponsor carrying about 41% of total weighted exposure across eight matches, as expected when a main chest or shorts logo dominates. Across kit positions the ratio between the highest- and lowest-exposure slots is on the order of 27 to 1 in duration, enough to justify pricing positions differently rather than at a flat rate — the practical output of the position-assignment component.

Detections below 0.4 confidence are 29% of the raw count but contribute only 9.5% of quality-weighted exposure, while those at or above 0.8 contribute 64%. The model therefore discounts uncertain, fleeting appearances rather than counting them equally.

### 5.5.1 Club pricing weights and measured exposure

Table 4 compares the club's ex-ante commercial weights with the AI share observed separately in all eight available highlight-video results. The club weights are fixed across files and sum to 95%, so they are normalised to 100% before comparison. Because absolute exposure totals and video durations are absent from these exports, Mean AI is the unweighted mean of the eight within-video shares rather than a duration-weighted portfolio estimate.

| **Kit position** | **Club %** | **M02** | **M03** | **M04** | **M05** | **M06** | **M07** | **M08** | **M11** | **Mean AI %** | **Gap (pp)** |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Main Sponsor | 27.37 | 14.18 | 15.13 | 8.24 | 16.44 | 12.54 | 10.10 | 13.43 | 17.55 | 13.45 | -13.92 |
| Collar Back (unmapped) | 8.42 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | -8.42 |
| Collar Bone | 8.42 | 4.67 | 3.87 | 4.30 | 3.69 | 4.54 | 4.14 | 1.70 | 9.10 | 4.50 | -3.92 |
| Chest (opp. badge) | 7.37 | 1.10 | 6.37 | 2.24 | 1.40 | 6.60 | 3.14 | 3.79 | 4.55 | 3.65 | -3.72 |
| Sleeve 1 | 4.21 | 5.46 | 3.27 | 8.54 | 9.07 | 3.69 | 8.05 | 6.40 | 2.97 | 5.93 | +1.72 |
| Sleeve 2 | 11.58 | 1.11 | 2.44 | 2.76 | 4.88 | 1.60 | 2.95 | 2.99 | 1.40 | 2.52 | -9.06 |
| Sleeve 3 | 4.21 | 13.06 | 23.19 | 13.15 | 31.83 | 21.51 | 15.77 | 17.78 | 18.66 | 19.37 | +15.16 |
| Top Back | 5.26 | 5.57 | 3.49 | 3.11 | 1.85 | 3.68 | 4.94 | 3.55 | 1.71 | 3.49 | -1.78 |
| Nape Neck | 3.16 | 5.57 | 3.49 | 3.10 | 1.84 | 3.68 | 4.94 | 3.54 | 1.71 | 3.48 | +0.33 |
| Bottom Back | 3.16 | 9.94 | 7.22 | 10.01 | 4.14 | 11.68 | 7.13 | 7.88 | 7.09 | 8.14 | +4.98 |
| Top Back Shorts | 5.26 | 23.54 | 17.43 | 15.20 | 15.00 | 11.86 | 19.80 | 18.51 | 14.30 | 16.96 | +11.69 |
| Shorts Front | 3.16 | 6.77 | 3.37 | 8.85 | 5.67 | 5.54 | 6.13 | 4.84 | 6.35 | 5.94 | +2.78 |
| Shorts Back 1 | 3.16 | 4.37 | 5.73 | 4.05 | 1.46 | 2.40 | 3.39 | 3.58 | 4.22 | 3.65 | +0.49 |
| Shorts Back 2 | 3.16 | 2.05 | 3.52 | 5.00 | 0.36 | 5.69 | 4.61 | 5.05 | 5.77 | 4.01 | +0.85 |
| Socks front | 1.05 | 1.14 | 0.94 | 5.91 | 1.28 | 2.46 | 1.91 | 3.42 | 2.20 | 2.41 | +1.35 |
| Socks back | 1.05 | 1.47 | 0.54 | 5.54 | 1.09 | 2.53 | 3.00 | 3.54 | 2.42 | 2.52 | +1.46 |
| **Total** | **100.00** | **100.00** | **100.00** | **100.00** | **100.00** | **100.00** | **100.00** | **100.00** | **100.00** | **100.00** | **0.00** |

*Table 4. Club pricing share and within-video AI exposure share (%). Gap is Mean AI minus Club share in percentage points. Collar Back had no mapped sponsor logo in any source workbook, so its zero is inventory status rather than measured under-delivery.*

Among the fifteen mapped positions, alignment is limited descriptively (Spearman *ρ* = 0.32; mean absolute gap 4.88 percentage points). Sleeve 3 and Top Back Shorts receive respectively 15.16 and 11.69 points more exposure than their price shares, while Main Sponsor and Sleeve 2 receive 13.92 and 9.06 points less. This does not establish mispricing: highlight editing, non-broadcast rights, logo area and exclusivity can rationally affect the club's rates. It does show that fixed commercial weights and measured broadcast visibility represent different constructs, making the comparison useful decision support rather than model validation.

## 5.6 Parameter sensitivity and sampling bias (RQ3)

Sweeping the visibility floor over 13,439 detections shows that raising it from 0.02 to 0.05 removes 71% of quality exposure and raising it to 0.1 removes 98%, whereas raising the confidence floor from 0.25 to 0.6 loses under 5% (Figure 12). The result shows that this score is far more sensitive to the visibility floor than to the confidence floor; it supports retaining signal at 0.02 but does not validate that threshold against human attention.

![Figure 12](LogoLens_MSc_Dissertation_v14_media/figure_12.png)

**Figure 12. *****Parameter sensitivity over 13,439 detections. Raising the visibility floor from 0.02 to 0.1 removes up to 98% of quality exposure, whereas raising the confidence floor from 0.25 to 0.6 removes under 5%.***

A controlled experiment on one three-minute segment compared exposure at the deployed two frames per second against the native fifty (Figure 13). In that segment the sparse rate over-measured exposure by 63%, because each isolated sample is quantised to a half-second block and short gaps are bridged. The result establishes a local bias, not a global correction factor; production reporting should either repeat the test over more footage or disclose the sampling assumption.

![Figure 13](LogoLens_MSc_Dissertation_v14_media/figure_13.png)

**Figure 13. *****Sampling-rate bias on a three-minute segment. Sparse two-frames-per-second analytics sampling over-measures total exposure by 63% relative to native fifty-frames-per-second processing, because isolated samples are quantised to half-second blocks and gaps are bridged.***

## 5.7 Annotation effort and per-class accuracy (RQ4)

Annotation is the dominant recurring cost of operating the system, and it is incurred per sponsor. This section pairs each class's training-instance count with the Average Precision achieved on it (Figure 14); the seventeen pairs are given in Appendix C.

The association is clear and in the expected direction (Table 5): accuracy rises by 0.169 AP per tenfold increase in annotated instances (95% CI [0.064, 0.275], *R*² = 0.44), about 0.05 AP per doubling. The logarithmic form matters commercially as much as statistically: the first few hundred boxes for a new sponsor buy far more accuracy than the next few hundred, and beyond a point further annotation is a poor use of a limited budget.

![Figure 14](LogoLens_MSc_Dissertation_v14_media/figure_14.png)

**Figure 14. *****Annotation effort against per-class accuracy across the seventeen sponsor classes. Left: Average Precision rises with the number of annotated training instances, close to linearly in the logarithm of the count; each tenfold increase in data is worth about 0.17 AP. Right: the nine classes with at least 500 annotated instances average 0.498 AP against 0.414 for the eight below that level, a difference of 0.084 (Welch ******t******-test, p = 0.009). Each dot is one sponsor class.***

Converting the curve into a budget gives a usable planning figure. Reaching the dataset's own mean of 0.458 AP requires on the order of 500 annotated instances, and splitting the classes there separates them cleanly: the nine at or above 500 average 0.498 AP against 0.414 for the eight below, a difference of 0.084 surviving a Welch *t*-test (*p* = 0.009). The working recommendation for a new sponsor is therefore approximately **500 annotated instances**. At this dataset's density of about 1.2 instances per frame in which a class appears at all, that is roughly 400 annotated frames — within reach of the model-assisted labelling of Section 3.3.2, and a far smaller commitment than the whole-dataset re-annotation the framing of the annotation-cost problem tends to imply.

Two qualifications apply. Data quantity explains under half the variance: fairway lies 0.10 AP below the fitted line while cch lies 0.07 above it, so difficult marks may require more than the stated budget. The proportional split also gives rare classes fewer validation examples, making their AP less precise. The slope therefore indicates an order of magnitude — hundreds rather than thousands of boxes — not an exact coefficient; a fixed validation set with varied training counts is needed to separate learning from evaluation noise.

| **Statistic** | **Value** |
| --- | --- |
| Classes analysed | 17 |
| Pearson *r* (AP vs instances) | +0.73 (*p* = 0.001) |
| Pearson *r* (AP vs log₁₀ instances) | +0.66 (*p* = 0.004) |
| Spearman *ρ* | +0.60 (*p* = 0.012) |
| Fitted slope | +0.169 AP per 10× data (95% CI [0.064, 0.275]) |
| Variance explained (*R*²) | 0.44 |
| Mean AP, ≥ 500 instances (9 classes) | 0.498 |
| Mean AP, < 500 instances (8 classes) | 0.414 |
| Difference | +0.084 (Welch *t*-test, *p* = 0.009) |

*Table 5. Data efficiency across the seventeen sponsor classes.*

## 5.8 Occlusion (RQ2)

Sponsor logos on a moving player are routinely covered by an opposing player, the wearer's own arm, the ball or the frame edge. Occlusion is not annotated and cannot be derived from box geometry, so it was measured as team attribution was, by stratified manual audit under a fixed rule (Section 3.4): nine instances per class, 153 in all, each shown with its surroundings and rated unobstructed, partially covered but readable, or heavily covered.

**Occlusion is common but rarely severe.** **30.7% of the 153 audited logos are covered to some degree** (Wilson 95% CI 24.0–38.4%), but only 3.9% heavily (Table 6): one appearance in three is compromised, one in twenty-five badly. This matters in a specific way. A partially covered logo is still detected and scored as an ordinary appearance whose box happens to be smaller, and the model cannot distinguish a mark that was small because the player was distant from one that was large but half-hidden. The two are worth different amounts to a sponsor; the system charges the same for both.

**Larger, closer logos are covered more often, not less** (Figure 15, left; Table 6). A logo is rendered large when the camera is close, often during tackles and rucks where bodies overlap. The Tier 1 size term therefore rewards some appearances that are also more likely to be partly hidden.

![Figure 15](LogoLens_MSc_Dissertation_v14_media/figure_15.png)

**Figure 15. *****Occlusion measured by a stratified manual audit of 153 logos. Left: coverage rate by rendered pixel height. Right: per-class occlusion against the residual from the data-efficiency fit in Figure 14; the relationship is flat.***

**Occlusion does not explain why some sponsors are harder than others.** The audit does not support an association with the data-efficiency residual (Figure 15, right): *r* = +0.20, *p* = 0.45 and Spearman *ρ* = +0.11. Adding occlusion raises raw *R*² from 0.441 to 0.463 but lowers adjusted *R*² from 0.404 to 0.386.

The negative result is reported because it is informative: it rules out the most plausible single explanation for the unexplained half of the per-class variance. Two limits qualify it — nine instances per class gives a standard error near 15 percentage points, so a moderate association could hide in that noise, and one rater carries the judgement-bias caveat of Section 6.4. What the audit establishes firmly is the aggregate rate, where 153 observations give a usefully tight interval, and the size relationship, which is significant and has a clear mechanism.

| **Measure** | **Value** |
| --- | --- |
| Logos audited | 153 (9 per class × 17 classes) |
| Unobstructed | 106 (69.3%) |
| Partially covered | 41 (26.8%) |
| Heavily covered | 6 (3.9%) |
| **Covered to any degree** | **47 (30.7%), Wilson 95% CI 24.0–38.4%** |
| Covered, marks under 32 px tall | 21.9% |
| Covered, marks 72 px tall and over | 54.8% |
| Median height, covered vs unobstructed | 52 px vs 44 px (Mann–Whitney *p* = 0.009) |
| Per-class rate, range | 0% – 77.8% (SE ≈ 15 pp per class) |
| Correlation with data-efficiency residual | *r* = +0.20 (*p* = 0.45); adjusted *R*² falls when added |

*Table 6. Occlusion audit summary.*

## 5.9 Throughput

On the target workstation the system processed footage at approximately real time (87.7 video-minutes in 88.4 wall-clock minutes, a range of 0.81–1.12 times real time across jobs). This substantiates the claim that the system is feasible on consumer-grade hardware, which is a necessary condition for making the capability affordable to smaller clubs.

## 5.10 Summary of results

The evidence supports three claims at differing levels of confidence. With high confidence, the production system measures exposure and value at approximately real time on affordable hardware, attributes exposure to the correct team in about 92% of audited cases, and its attribution filter makes a large quantitative difference. With medium confidence, the valuation model produces plausible distributions and responds to its parameters in a controlled and now-quantified way, although it lacks a ground-truth price against which absolute error could be measured. With lower confidence, accuracy on a sponsor rises with the annotation spent on it at a rate of roughly 0.17 AP per tenfold increase, giving a working budget of about 500 instances per sponsor; the direction and rough magnitude are firm, but seventeen classes and a confounded validation size make the coefficient itself provisional.

<!-- page break -->

# Chapter 6. Discussion

## 6.1 Interpretation of the principal findings

The results answer the four research questions with differing degrees of certainty, and in each case the interpretation matters more than the headline number.

For **RQ1**, what is informative is not the 0.745 mAP@0.5 but the *shape* of the error and the *effect* of attribution. The near-diagonal confusion matrix shows the detector's mistakes are overwhelmingly misses rather than brand confusions — the benign mode for valuation, since a miss under-counts slightly whereas a confusion would misdirect money. And removing 44% of raw detections shows attribution is not a refinement but a first-order determinant of the estimate: a logo-detection system without it would systematically over-value sponsorship. This supports the argument of Section 2.2, that the sponsorship problem is mis-framed if treated as detection alone.

For **RQ2**, three findings have consequences the valuation model does not absorb. Occlusion rises with the rendered *size* of the mark rather than its smallness, because large means close and close means contact, so the visibility model rewards through its size term precisely the appearances most likely to be obscured. Occlusion does *not* explain why some sponsors are detected more accurately than others — a negative result worth as much as a positive one, since it removes the most convenient explanation for the variance left unexplained under RQ4. And because the model scores each detection independently, a sponsor appearing alone and one appearing alongside six others receive the same per-detection visibility; attention is finite and shared, and with 63.1% of frames carrying two or more logos, crowded frames are over-valued relative to isolated ones. That bias occupies the same position as the sampling bias — direction knowable, size not — so it is disclosed here and a competition-for-attention term proposed in the future work.

For **RQ3**, the sensitivity analysis matters more than the value distributions, because it converts an opaque number into one whose behaviour is understood: the estimate is dominated by the visibility floor, comparatively robust to the confidence floor, and biased upward by the deployed sampling rate. None of this validates the *absolute* estimate, which without a ground-truth price cannot be validated, but it makes the estimate interpretable and its assumptions explicit — the appropriate standard in a domain without ground truth.

For **RQ4**, a club can now be told what onboarding a new sponsor costs — on the order of 500 instances, some 400 frames — instead of being told that annotation is expensive. The more interesting implication is what remains unexplained: data quantity accounts for slightly under half the variance in per-class accuracy, and the obvious candidate for the rest has been tested and rejected. The surviving candidates are properties of the mark itself, its contrast against the kit, the fineness of its lettering, its consistency across strips, none of which this dissertation measures. Sponsorship inventory is therefore not uniformly measurable, the differences between sponsors are real and substantial, and their cause is not established. That is a finding about the commercial object rather than only the model, and it argues for setting measurement expectations per sponsor — while stopping short of saying which property to price on.

## 6.2 Relation to prior work

The dependence of reported accuracy on the splitting protocol reproduces, in the logo-detection setting, leakage concerns long recognised in sports video (Deliège et al., 2021). The reference-based approach to attribution follows leading SoccerNet solutions but adds a consideration absent there — the financial asymmetry of attribution errors — operationalised as a revenue-safe keep/drop policy. Against the sponsorship-measurement literature, the system reproduces quality-weighting, though not the oriented-box correction, while adding attribution, position-based valuation and, most importantly, reproducibility and low cost, answering the criticism that existing tools are proprietary and opaque.

The data-efficiency result meets the weak-supervision literature of Section 2.5 from an unusual direction. That literature argues from the premise that annotation is prohibitively expensive; the measurement here puts a number on the premise, and the number is modest enough — hundreds of instances per sponsor, not tens of thousands — that the case for elaborate label-free machinery rests on scale rather than on the single-club setting. The log-linear shape itself reproduces, on a small domain-specific dataset, the relationship Sun et al. (2017) reported at web scale, which is mild evidence that it is a property of the learning problem rather than of this dataset.

## 6.3 Automated valuation in the context of AI in advertising

The debate of Section 2.6 concerns mostly AI that *produces* advertising content; this system sits on the complementary side, AI that *measures and values* it. The two are connected: as generative tools lower the cost of producing creative variants, measuring which of them earns attention becomes more important, not less, because measurement turns an abundance of options into a set of priced, comparable choices. Position-based valuation is a small concrete instance, turning "where on the kit a logo sits" into a measured variable that could inform a placement decision.

Two observations emerge from building it. The first concerns the human role: automation relocated the contribution rather than removing it, from timing appearances by hand to auditing samples and designing the control gates that catch structured errors — officials mistaken for players, a surname mistaken for a sponsor. Those errors need human contextual understanding to anticipate, which suggests the human is not a step awaiting automation but the source of the semantic constraints the system needs. The second concerns access: running at approximately real time on a consumer GPU lowers the barrier for a mid-tier club to measure sponsorship value itself rather than buying an expensive service, mirroring on the measurement side what generative AI does on the production side.

## 6.4 Threats to validity

The principal **construct-validity** threat is that EMV proxies advertising *attention*, not business *outcome*, and is not validated against any true price; the results measure exposure quality, not commercial return. The main **external-validity** threat is scale — one sport, one primary club, a modest number of matches — so the sport-agnostic claim is a design intention rather than a demonstrated outcome. The club-price comparison is further limited to edited highlights: its shares reflect editorial camera selection and cannot be generalised to full-match delivery.

Four **measurement** threats affect the visibility score, the first three sharing a direction. The axis-aligned box encloses a rotated mark in more area than it occupies, over-stating visibility exactly where exposure is most valuable, and the correction that would remove this is provided for but inert (Section 4.6). Competition for attention within a frame is not modelled, over-valuing the 63% of frames carrying more than one logo. And the sampling rate over-measures by 63% (Section 5.6). All three inflate and none is corrected, so **every EMV figure here should be read as an upper bound**. That they point the same way is worth naming: each simplification was adopted because it was cheaper, and the cheaper choice happens each time to flatter the sponsor — a pattern a measurement system built for a commercially interested party should expect and disclose rather than net off.

The fourth threat is **occlusion**, measured but not corrected for. A covered logo is either detected with a smaller box and scored as less valuable, or missed; neither outcome distinguishes a mark that was small and distant from one large but half-hidden, and Section 5.8 shows the latter is not rare. Its direction is ambiguous — under-valued for lost area, or over-valued because the appearance is a prominent close-up — so it is not folded into the upper-bound argument. Resolving it needs occlusion labels on a held-out set large enough to compare detection outcomes across levels, which the present audit, at 26 held-out items, cannot support; that experiment is identified in Section 7.2.

Both audits rest on a **single rater**, so systematic misjudgement cannot be excluded; sampling rules and ratings are retained for replication, but no inter-rater agreement is reported. The occlusion audit is further limited by size, supporting the aggregate rate well but per-class rates only indicatively, so its null result on class difficulty is an absence of a *large* effect rather than evidence of no effect.

The components differ in how exposed they are to the generalisation threat, which is worth separating out. Reference-based attribution is sport- and club-agnostic by construction, since it learns kit references per match rather than from a fixed training set; the valuation model is likewise domain-general, its inputs being geometric and temporal. The exposed component is the closed-set detector, which would need retraining for a new roster — and Section 5.7 puts a price on clearing that bottleneck, at roughly 500 annotated instances per sponsor. A second-club deployment would therefore be limited by detector training data rather than by the attribution or valuation logic, though only the second-club experiment identified in the future work would test that properly.

## 6.5 Practical and ethical implications

For a club, the practical implication is that a credible sponsorship report can be produced in-house at low cost, provided its assumptions and biases are disclosed. For practitioners, four lessons transfer: evaluate detection under clip-disjoint splits; treat attribution as a first-order component with a revenue-safe policy; characterise the data before trusting the model; and disclose sensitivities rather than reporting a single headline value.

Three implications deserve brief reflection beyond the privacy measures of the methodology. A measurement instrument is not neutral: the visibility floor, the duration weights and the placement multipliers encode a particular theory of what counts as valuable attention, and different choices would produce different valuations. Making them explicit and their sensitivities measurable is therefore an ethical requirement as much as good science, because a black-box valuation used to set prices between parties concentrates unaccountable power in whoever controls the parameters. The sampling bias of Section 5.6 shows how easily such a valuation could be tuned, deliberately or otherwise, to favour the party commissioning it; measuring and disclosing biases is what separates a legitimate analytics tool from a persuasive one. And democratising the capability cuts both ways, since the affordability that empowers a small club also lowers the barrier to producing inflated or selectively reported valuations — which is precisely why the transparent, auditable methodology advocated here matters.

<!-- page break -->

# Chapter 7. Conclusion and Future Work

## 7.1 Conclusion

This dissertation set out to design, implement and critically evaluate a low-cost, reproducible computer-vision system for measuring and valuing sponsor-logo exposure in sports broadcasts, with Bradford Bulls as the case study. The resulting system, LogoLens, couples a fine-tuned detector with reference-based team attribution, pose-based assignment to sellable kit positions and a three-tier visibility-to-value model behind a web dashboard, running at approximately real time on consumer hardware.

Evaluated under leakage-controlled protocols, it achieves 0.745 mAP@0.5 detection, 91.8% team-attribution accuracy by stratified audit, and an attribution filter removing 44% of otherwise mis-credited detections. Characterising the exposure signal showed that most frames carry several marks from more than one brand, each occupying a median 0.145% of the screen at 46 pixels of height, and that roughly one in three is partly covered — more often when the mark is large. The value estimate is interpretable and its sensitivities quantified, the deployed sampling rate carries a disclosed positive bias, and per-class accuracy rises with per-class annotation at roughly 0.169 AP per tenfold increase, giving a budget of about 500 instances for a new sponsor. Against the research questions, the work demonstrates a working, affordable pipeline (RQ1, RQ3), establishes the measurable properties of the exposure it rests on (RQ2), and quantifies the cost of extending it to a new sponsor (RQ4). The discussion separately situates automated valuation within the AI-in-advertising debate, addressing the sixth objective without presenting that contextual analysis as an empirical research question.

The overall conclusion is that measuring and valuing sponsorship exposure to a useful standard is achievable at low cost and with transparent methods, and that doing so honestly — reporting conservative figures, disclosing biases, and distinguishing what has been measured from what has not — is both possible and necessary in a domain lacking public ground truth. The contribution is therefore as much methodological as technical: alongside a working system, the dissertation offers a template for evaluating one credibly when no ground truth exists. The main limitation is the absence of an absolute value validation; the main opportunity is to prove generality across clubs and sports and to reduce the annotation cost now measured.

## 7.2 Future work

The directions that follow divide into work that would firm up what has been claimed and work that would extend it.

Firming up. First, compare value estimates with stratified manual timing to measure absolute error. Second, hold validation data fixed while varying training counts to isolate the data-efficiency curve. Third, expand the occlusion audit enough to compare recall and confidence across coverage levels. Fourth, test whether kit contrast, lettering stroke width or design consistency explains residual per-class accuracy. Finally, benchmark transformer inference cost on the target hardware.

Extending. Applying the system to a second club and a second sport with no code changes would test the generality claim directly. Training an **oriented-box detector** would activate the correction term Section 4.6 provides for and remove the area over-statement on rotated logos. Adding a dedicated **officials class** would remove the largest identified source of attribution error. And modelling **competition for attention** when several logos share a frame would allocate value more fairly among sponsors appearing together, removing the second of the three inflationary biases.

### Reducing the annotation requirement

The most substantial extension follows from what Section 5.7 measured: if each new sponsor costs on the order of 500 annotated instances, can that cost be met without manual boxes? The techniques of Section 2.5 suggest a design, set out here as a proposal rather than a result.

The design would use sponsor artwork as exemplars, a known match roster as a small candidate set, and video redundancy to propagate one confident label through a track. A heavy teacher could combine exemplar-prompted segmentation, OCR and self-supervised crop clustering through a Snorkel-style label model, then distil a real-time student. Kit regulation adds a useful constraint: once a logo is identified at a known position on a season's strip, blurred crops can inherit the label geometrically. Synthetic scenes could supply rare conditions.

Preliminary work along these lines was carried out but is not reported as a result, not having been evaluated to the standard applied elsewhere. Two obstacles should shape any continuation. Automatic labels are useful only above a purity threshold, and the failure modes that degrade purity — a tracker identity switch carrying a brand to an opposing player, a segmenter firing on a fabric fold — are categorical rather than gradual, so they need explicit control gates rather than tuned thresholds. And any evaluation must be track-disjoint, since validation frames sharing a track with training frames leak almost completely. The measured budget gives this work the success criterion it would otherwise lack: an automatic route is worth its complexity only if it yields, for a new sponsor, something approaching the 500 usable instances manual annotation is now known to require.

The most ambitious direction of all is to close the loop between measurement and creative decision-making, using position-level valuation to inform kit-design and placement choices — connecting this work directly to the creative side of the advertising debate that motivated it.

<!-- page break -->

# References

*Industry sources are used only for their published methodology descriptions; parameter values that remain project assumptions are labelled as such.*

Aharon, N., Orfaig, R., & Bobrovsky, B.-Z. (2022). *BoT-SORT: Robust associations multi-pedestrian tracking*. arXiv. https://arxiv.org/abs/2206.14651

Breuer, C., & Rumpf, C. (2012). The viewer's reception and processing of sponsorship information in sport telecasts. *Journal of Sport Management, 26*(6), 521–531. https://doi.org/10.1123/jsm.26.6.521

Cornwell, T. B. (2019). Less "sponsorship as advertising" and more sponsorship-linked marketing as authentic engagement. *Journal of Advertising, 48*(1), 49–60. https://doi.org/10.1080/00913367.2019.1588809

Cornwell, T. B., & Kwon, Y. (2020). Sponsorship-linked marketing: Research surpluses and shortages. *Journal of the Academy of Marketing Science, 48*(4), 607–629. https://doi.org/10.1007/s11747-019-00654-w

Davenport, T., Guha, A., Grewal, D., & Bressgott, T. (2020). How artificial intelligence will change the future of marketing. *Journal of the Academy of Marketing Science, 48*(1), 24–42. https://doi.org/10.1007/s11747-019-00696-0

Deliège, A., Cioppa, A., Giancola, S., Seikavandi, M. J., Dueholm, J. V., Nasrollahi, K., Ghanem, B., Moeslund, T. B., & Van Droogenbroeck, M. (2021). SoccerNet-v2: A dataset and benchmarks for holistic understanding of broadcast soccer videos. In *Proceedings of the IEEE/CVF Conference on Computer Vision and Pattern Recognition Workshops (CVPRW)* (pp. 4508–4519). https://arxiv.org/abs/2011.13367

Everingham, M., Van Gool, L., Williams, C. K. I., Winn, J., & Zisserman, A. (2010). The PASCAL Visual Object Classes (VOC) challenge. *International Journal of Computer Vision, 88*(2), 303–338. https://doi.org/10.1007/s11263-009-0275-4

Hevner, A. R., March, S. T., Park, J., & Ram, S. (2004). Design science in information systems research. *MIS Quarterly, 28*(1), 75–105. https://doi.org/10.2307/25148625

Huang, M.-H., & Rust, R. T. (2021). A strategic framework for artificial intelligence in marketing. *Journal of the Academy of Marketing Science, 49*(1), 30–50. https://doi.org/10.1007/s11747-020-00749-9

Jocher, G., Chaurasia, A., & Qiu, J. (2023). *Ultralytics YOLO* [Computer software]. https://github.com/ultralytics/ultralytics

Journal of Advertising Research. (2026). *AI and the future of advertising creativity* [Call for papers, special issue]. Taylor & Francis. https://think.taylorandfrancis.com/special\_issues/ai-and-the-future-of-advertising-creativity/

Kerbl, B., Kopanas, G., Leimkühler, T., & Drettakis, G. (2023). 3D Gaussian splatting for real-time radiance field rendering. *ACM Transactions on Graphics, 42*(4), 1–14. https://doi.org/10.1145/3592433

Kirillov, A., Mintun, E., Ravi, N., Mao, H., Rolland, C., Gustafson, L., Xiao, T., Whitehead, S., Berg, A. C., Lo, W.-Y., Dollár, P., & Girshick, R. (2023). Segment anything. In *Proceedings of the IEEE/CVF International Conference on Computer Vision (ICCV)* (pp. 4015–4026). https://arxiv.org/abs/2304.02643

Lin, T.-Y., Maire, M., Belongie, S., Hays, J., Perona, P., Ramanan, D., Dollár, P., & Zitnick, C. L. (2014). Microsoft COCO: Common objects in context. In *Proceedings of the European Conference on Computer Vision (ECCV)* (pp. 740–755). https://arxiv.org/abs/1405.0312

Liu, S., Zeng, Z., Ren, T., Li, F., Zhang, H., Yang, J., Li, C., Yang, J., Su, H., Zhu, J., & Zhang, L. (2023). *Grounding DINO: Marrying DINO with grounded pre-training for open-set object detection*. arXiv. https://arxiv.org/abs/2303.05499

Katz, J. B., Carter, C. N., & Kim, B. J. (2024). *Automated media analysis for sponsor valuation* (U.S. Patent No. 12,124,509). United States Patent and Trademark Office. https://image-ppubs.uspto.gov/dirsearch-public/print/downloadPdf/12124509

Nielsen. (n.d.). *Sponsorship media value benchmarking report*. https://www.nielsen.com/report/sponsorship-media-value-benchmarking-report/

Oquab, M., Darcet, T., Moutakanni, T., Vo, H., Szafraniec, M., Khalidov, V., Fernandez, P., Haziza, D., Massa, F., El-Nouby, A., Assran, M., Ballas, N., Galuba, W., Howes, R., Huang, P.-Y., Li, S.-W., Misra, I., Rabbat, M., Sharma, V., … Bojanowski, P. (2023). *DINOv2: Learning robust visual features without supervision*. arXiv. https://arxiv.org/abs/2304.07193

Radford, A., Kim, J. W., Hallacy, C., Ramesh, A., Goh, G., Agarwal, S., Sastry, G., Askell, A., Mishkin, P., Clark, J., Krueger, G., & Sutskever, I. (2021). Learning transferable visual models from natural language supervision. In *Proceedings of the 38th International Conference on Machine Learning (ICML)* (pp. 8748–8763). https://arxiv.org/abs/2103.00020

Ratner, A., Bach, S. H., Ehrenberg, H., Fries, J., Wu, S., & Ré, C. (2017). Snorkel: Rapid training data creation with weak supervision. *Proceedings of the VLDB Endowment, 11*(3), 269–282. https://doi.org/10.14778/3157794.3157797

Ravi, N., Gabeur, V., Hu, Y.-T., Hu, R., Ryali, C., Ma, T., Khedr, H., Rädle, R., Rolland, C., Gustafson, L., Mintun, E., Pan, J., Alwala, K. V., Carion, N., Wu, C.-Y., Girshick, R., Dollár, P., & Feichtenhofer, C. (2024). *SAM 2: Segment anything in images and videos*. arXiv. https://arxiv.org/abs/2408.00714

Redmon, J., Divvala, S., Girshick, R., & Farhadi, A. (2016). You only look once: Unified, real-time object detection. In *Proceedings of the IEEE Conference on Computer Vision and Pattern Recognition (CVPR)* (pp. 779–788). https://arxiv.org/abs/1506.02640

Romberg, S., Pueyo, L. G., Lienhart, R., & van Zwol, R. (2011). Scalable logo recognition in real-world images. In *Proceedings of the 1st ACM International Conference on Multimedia Retrieval (ICMR)* (pp. 1–8). https://doi.org/10.1145/1991996.1992021

Rumpf, C., Boronczyk, F., & Breuer, C. (2020). Predicting consumer gaze behavior toward sponsorship stimuli in sport broadcasts. *European Sport Management Quarterly, 20*(4), 461–479. https://doi.org/10.1080/16184742.2019.1620838

Su, H., Zhu, X., & Gong, S. (2018). Open logo detection challenge. In *Proceedings of the British Machine Vision Conference (BMVC)*. https://arxiv.org/abs/1807.01964

Sun, C., Shrivastava, A., Singh, S., & Gupta, A. (2017). Revisiting unreasonable effectiveness of data in deep learning era. In *Proceedings of the IEEE International Conference on Computer Vision (ICCV)* (pp. 843–852). https://arxiv.org/abs/1707.02968

Zhai, X., Mustafa, B., Kolesnikov, A., & Beyer, L. (2023). Sigmoid loss for language image pre-training. In *Proceedings of the IEEE/CVF International Conference on Computer Vision (ICCV)*. https://arxiv.org/abs/2303.15343

Zhang, Y., Sun, P., Jiang, Y., Yu, D., Weng, F., Yuan, Z., Luo, P., Liu, W., & Wang, X. (2022). ByteTrack: Multi-object tracking by associating every detection box. In *Proceedings of the European Conference on Computer Vision (ECCV)* (pp. 1–21). https://arxiv.org/abs/2110.06864

Google Ads. (n.d.). *Cost-per-thousand impressions (CPM): Definition*. https://support.google.com/google-ads/answer/6310?hl=en

Sarkhoosh, M. H., Øye, F., Sørlie, H. N., Vu, N. H., Johansen, D., Midoglu, C., Kupka, T., & Halvorsen, P. (2025). *ExposureEngine: Oriented logo detection and sponsor visibility analytics in sports broadcasts*. arXiv:2510.04739. https://arxiv.org/abs/2510.04739

<!-- page break -->

# Appendices

## Appendix A — Key system configuration

| **Parameter** | **Default** | **Meaning** |
| --- | --- | --- |
| Analytics sampling rate | 2 fps | Frame sampling for the analytics pass |
| Detection input size | 1280 px | Detector input resolution |
| Visibility floor | 0.02 | Minimum visibility to form a segment |
| Minimum segment length | 0.5 s | Shorter segments discarded as flicker |
| Duration weight | 0.5 / 1.0 / 1.2 | For segments <1 s / 1–5 s / >5 s |
| CPM scenario input | US$22.0 | Project input, not a claimed market benchmark |
| Reference advertising slot | 30 s | Converts quality seconds to spot equivalents |
| Placement multiplier | 1.0 / 1.4 / 0.85 / 0.7 | Project scenarios: live TV / highlight / stream / social |
| Reported detector | YOLO clip-disjoint checkpoint | RF-DETR evaluated separately |
| Current local backend option | RF-DETR 1.8.3, confidence 0.20 | LOGO\_BACKEND=rfdetr in bradford\_bulls env |
| Keep-unknown / unassigned | disabled / disabled | Credit only detections attributed to target team |
| Minimum votes (attribution) | 2.0 | Vote mass before trusting an "other-team" label |
| Vote hysteresis | 1.25 | Stickiness of the voted team label |
| Bootstrap frames | 32 | Frames sampled when bootstrapping kit references |

## Appendix B — Summary of experimental results

| **Metric** | **Value** | **Source / condition** |
| --- | --- | --- |
| mAP@0.5 (random-frame) | 0.862 | Inflated by leakage; not cited as true performance |
| mAP@0.5 (clip-disjoint) | 0.702 | Leakage-controlled protocol |
| mAP@0.5 (extended clip-aware) | 0.745 (P 0.65, R 0.74) | Headline result |
| RF-DETR mAP@0.5 (clip/match-disjoint) | 0.771 (EMA 0.778) | 18% group holdout; checkpoint selected on same partition |
| RF-DETR mAP@[.5:.95] / P / R | 0.458 / 0.730 / 0.711 | Best checkpoint |
| Team-attribution accuracy | 91.8% (169/184) | Stratified human audit, 3 frames × 9 matches |
| Attribution filter removal rate | 44% (11,161/25,153) | 9 matches, per-match range 21–78% |
| Low-confidence detections (conf < 0.4) | 29% of count / 9.5% of weighted exposure | 8 matches |
| High-confidence detections (conf ≥ 0.8) | 64% of weighted exposure | 8 matches |
| Visibility-floor sensitivity (0.02→0.1) | up to 98% of exposure removed | 13,439 detections |
| Confidence-floor sensitivity (0.25→0.6) | under 5% lost | 13,439 detections |
| Sampling bias (2 fps vs 50 fps) | +63% over-measurement | 3-minute segment |
| Throughput | ~1.0× real time (0.81–1.12×) | RTX 5060 Ti 16 GB workstation |
| Logos per frame | 63.1% of frames carry ≥2; mean 3.15 | 4,113 annotated frames |
| Screen coverage per logo | median 0.145% of frame area; 95.7% under 1% | 12,960 instances |
| Rendered resolution | median 46 px tall; 18.7% under 32 px | 12,960 instances; 1080p source |
| Occlusion, any degree | 30.7% (Wilson 95% CI 24.0–38.4%) | Stratified audit, 153 logos, 9 per class |
| Occlusion, heavy | 3.9% | Same audit |
| Occlusion vs mark size | 54.8% covered at ≥72 px vs 21.9% under 32 px | Mann–Whitney *p* = 0.009 |
| Occlusion vs per-class accuracy | *r* = +0.20 (*p* = 0.45) — no association | Adjusted *R*² falls when added |
| Data efficiency, AP vs instances | Pearson *r* = +0.73 (*p* = 0.001) | 17 sponsor classes |
| Data efficiency, fitted slope | +0.169 AP per 10× data (95% CI [0.064, 0.275]) | *R*² = 0.44 |
| Mean AP, ≥ 500 vs < 500 instances | 0.498 vs 0.414 (+0.084) | Welch *t*-test, *p* = 0.009 |

## Appendix C — Class distribution and per-class accuracy

Per-class annotated instance counts for the extended clip-aware set (17 classes; 10,654 training and 2,306 held-out instances), with the Average Precision achieved on each class at the best checkpoint. These are the seventeen pairs analysed in Section 5.7. Brand names are the model's internal class labels; the held-out column is reported because it is the confound discussed there — a class with few training instances also has few instances on which its accuracy is measured.

| **Class** | **Training instances** | **Held-out instances** | **AP@[.5:.95]** |
| --- | --- | --- | --- |
| klg | 1,667 | 341 | 0.606 |
| paints\_lacquers | 1,170 | 218 | 0.474 |
| mcp | 1,106 | 318 | 0.576 |
| romantica | 886 | 226 | 0.498 |
| aon | 749 | 102 | 0.452 |
| ellgren | 718 | 161 | 0.394 |
| acs\_group | 700 | 154 | 0.474 |
| bartercard | 612 | 159 | 0.479 |
| top\_notch | 582 | 138 | 0.529 |
| floor\_tonic | 446 | 71 | 0.490 |
| atm | 431 | 108 | 0.382 |
| em\_workwear | 385 | 64 | 0.422 |
| fairway | 313 | 86 | 0.319 |
| mna\_support\_service | 249 | 50 | 0.408 |
| mna\_cladding | 240 | 44 | 0.401 |
| chadlaw | 218 | 25 | 0.432 |
| cch | 182 | 41 | 0.454 |
| **Total / mean** | **10,654** | **2,306** | **0.458** |

## Appendix D — Note on assumptions and transparency

The following assumptions are stated for the reader: the institution and programme details on the title page are filled in by the author; a small number of very recent or industry sources are flagged for verification in the reference list; EMV is treated as an industry-standard proxy for advertising attention rather than an actual price; and a small number of derived figures (for example the per-match filter range and the slot-exposure ratio) are indicative and should be read alongside the underlying experimental records. Quantitative figures are drawn from the project's records and may change as the dataset is scaled.

<!--
Word comments preserved from the source file. These comments were present in comments.xml but were not anchored to visible text in version 14:
- Mai Hoa (2026-07-28T10:43:00Z): "change this one"
- Mai Hoa (2026-07-28T10:44:07Z): "remove this part/ consider remove in the Research Questions also."
-->
