<!--
Version 16. Rewritten from version 15 against a complete re-measurement of the
final checkpoint carried out in August 2026.

What changed relative to version 15:
- one independent evaluation now produces mAP@0.50, mAP@0.75, mAP@[.50:.95] and
  the confidence sweep together, so the stricter metric is no longer borrowed
  from a second evaluator; the three evaluation paths are reported side by side;
- the sparse-class problem is treated quantitatively rather than as a caveat:
  support-restricted means, a support-weighted mean and exact binomial intervals;
- a controlled architecture comparison against three YOLO26 baselines, trained on
  the same split at the same resolution and scored with the same protocol;
- condition-stratified held-out results by camera distance, lighting, source
  resolution, ground-truth logo size and individual match, which give RQ2 its
  first measured evidence;
- input-geometry measurements taken from the annotation file rather than quoted.

Evidence rule, unchanged from version 15:
- figures reported as results must be reproducible from the current repository;
- legacy June 2026 full-video spreadsheets are not treated as RF-DETR results;
- incomplete readability and duration-validation studies are stated explicitly;
- team attribution, body segmentation and kit-location pricing are out of scope.
-->

**UNIVERSITY OF BRADFORD**

**FACULTY OF ENGINEERING AND DIGITAL TECHNOLOGIES**

**MSc Dissertation**

**MAI XUAN HOA**

# Developing and Evaluating a Computer Vision Framework for Sponsor-Logo Detection and Visibility-Quality Assessment in Sports Broadcasts

A dissertation submitted in partial fulfilment of the requirements for the degree of

**MSc Applied Artificial Intelligence and Data Analytics**

Student ID: *[insert student ID]*  
Supervisor: *[insert supervisor name]*  
Submission date: *[insert date]*

---

## Declaration

I declare that this dissertation is my own work and has not been submitted, in whole or in part, for another degree or qualification. All external sources are acknowledged. Third-party models, libraries and services are identified where they are discussed. Artificial-intelligence assistance used to produce the conceptual infographic in Figure 1 is disclosed in Appendix E; every quantitative chart was generated from recorded project measurements by the script named in that appendix, and each was checked against the experiment output it draws on.

## Abstract

Sports clubs need credible evidence that sponsor logos were visible in broadcast and highlight footage, but exposure is difficult to measure when marks are small, distorted by fabric, partly hidden and present in several locations at once. Commercial sponsorship-analytics services demonstrate that automated logo tracking is already feasible, including for marks on players. Their methods, costs and evaluation data are not normally transparent, however, which limits what a smaller club can reproduce locally. This dissertation develops and evaluates LogoLens, a computer-vision framework for detecting a known roster of Bradford Bulls sponsor logos and converting detections into traceable measures of visibility quality and duration. The contribution is measurement rather than pricing: visibility is kept separate from audience attention, return on investment and sponsorship revenue.

The study follows a design-science approach with a quantitative single-club case evaluation. The final dataset contains 584 images and 1,903 annotated boxes across 16 sponsor classes drawn from 15 disjoint match groups. Matches, rather than neighbouring frames, form the units of the train, validation and test split. RF-DETR Small was fine-tuned on native-aspect broadcast frames at an input resolution of 896 pixels. On 61 images and 165 boxes from three unseen matches, one independent evaluation produced mAP@0.50 of 0.933, mAP@0.75 of 0.917 and mAP@[0.50:0.95] of 0.747, with a best F1 of 0.898 at a confidence threshold of 0.35 (precision 0.912; recall 0.885). Three separate evaluation paths agree to within 0.007 mAP@0.50. Under the same split, the same 896-pixel input and the same scoring code, three YOLO26 baselines reached 0.551, 0.772 and 0.747 mAP@0.50, and the margin widened at the stricter threshold. Inference averaged 50.5 ms per image, or 19.8 frames per second, on an RTX 5060 Ti 16 GB GPU, excluding file-system and video-decoding costs.

The experiments show that input geometry, match diversity and evaluation design matter more than model capacity. Letterboxing a 1208 × 1280 frame made 47% of the input black, while native-frame training at 896 pixels raised the effective median logo area 3.7 times relative to the original pipeline. Evaluation on familiar match material gave mAP@0.50 of 0.998 and F1 of 0.988, illustrating what frame-level leakage conceals. Held-out accuracy was stable across the three unseen matches (0.934 to 0.976) but fell sharply on wide tactical shots, where recall halved to 0.500. Four classes carrying seven of the 165 test boxes scored an apparent AP of 1.000 or close to it and lift the headline by 1.7 points; restricting the mean to the eleven classes with at least five boxes gives 0.917, and this restricted figure is treated as the honest reading. The implemented visibility framework combines size, screen position, detector confidence and temporal segments into quality-weighted seconds. The new detector has not yet been re-run and manually timed across the complete highlight-video set, and a planned human-readability study remains incomplete. The dissertation therefore supports the feasibility of accurate closed-set logo detection on consumer hardware, while treating duration accuracy and the final Logo Visibility Score as implemented but not yet validated outcomes.

**Keywords:** computer vision; logo detection; RF-DETR; small-object detection; sports sponsorship; visibility measurement; design science.

## Acknowledgements

I thank my supervisor for guidance on narrowing the dissertation towards the computer-vision and model-development work package. I am grateful to Bradford Bulls for the applied case context and to the open-source communities supporting RF-DETR, Ultralytics, PyTorch, DINOv2 and the associated evaluation tools. I also thank my family for their support throughout the project.

## List of Abbreviations

| Abbreviation | Meaning |
| --- | --- |
| AP / mAP | Average Precision / mean Average Precision |
| COCO | Common Objects in Context evaluation convention |
| CPM | Cost per thousand impressions |
| DETR | Detection Transformer |
| EMA | Exponential Moving Average of model weights |
| EMV | Equivalent Media Value |
| F1 | Harmonic mean of precision and recall |
| FPS | Frames per second |
| GPU | Graphics Processing Unit |
| IoU | Intersection over Union |
| LVS | Logo Visibility Score |
| OBB | Oriented Bounding Box |
| RF-DETR | Roboflow Detection Transformer |
| RQ | Research Question |
| ROI | Return on Investment |
| YOLO | You Only Look Once detector family |

## List of Figures

1. Research framework: sponsorship need, computer vision and transparent evidence.
2. Leakage-aware data and model-development workflow.
3. Dataset design and the effect of temporal leakage.
4. LogoLens system architecture and evidence flow.
5. Frame-level visibility and temporal aggregation.
6. Input geometry: the median sponsor logo as the model receives it.
7. Optimisation trajectory and inference-resolution experiment.
8. Training support against held-out accuracy.
9. Confidence sweep and the cost of the operating point.
10. Per-class AP@0.50, its support, and the effect of sparse classes on the mean.
11. Detector families scored under one protocol.
12. Held-out performance by camera distance, lighting and logo size.
13. Held-out success and error examples selected by predefined rules.

## List of Tables

1. Research questions and evidence required.
2. Selected literature and its relevance to this study.
3. Final match-disjoint dataset.
4. Composition of the held-out test set.
5. Final RF-DETR configuration and reproducibility details.
6. Optimisation stages and their evaluation protocols.
7. Final held-out test and inference results.
8. Agreement between three evaluation paths.
9. Effect of a minimum-support rule on the reported mean.
10. Detector families under one evaluation protocol.
11. Held-out results by condition of appearance.
12. Research-question conclusions and evidence limits.

---

---

# Chapter 1: Introduction

## 1.1 Sponsorship, association and the record it leaves behind

**Sponsorship is a commercial agreement in which an organisation pays a rights holder - a club, a competition, an event or an individual - for the right to associate itself with that property and to receive an agreed package of promotional benefits.** What separates it from advertising is not the size of the cheque but the nature of what is bought. An advertiser buys space and controls the message; a sponsor buys association, and accepts that the message will be carried by someone else's activity, audience and reputation. Cornwell (2019) argues that the field is better understood as sponsorship-linked marketing, in which value arises from authentic engagement with an audience rather than from the repetition of a claim.

That is precisely what makes sponsorship attractive, and precisely what makes it difficult to account for. The association reaches people inside content they have chosen to watch rather than in an interruption they may avoid, and it borrows an emotional attachment the audience already holds. But an association is diffuse in a way that a purchased advertising slot is not, and the agreements reflect this: naming rights, branding on kit and venue signage, exposure during broadcast and highlights coverage, hospitality, digital content and community programmes are bundled together and priced as a whole. For the rights holder the same agreement is not a marketing activity at all but a revenue stream, and commercial income of this kind is a material component of financial sustainability rather than a discretionary extra (Department for Culture, Media and Sport, 2023).

The sums exchanged on this basis are considerable. Two Circles (2025) estimates that organisations owning sports intellectual property generated approximately US$174 billion in annualised revenue in 2025, with sponsorship rights among the principal routes by which that value is realised. No single figure for global sponsorship expenditure is quoted here, because the available totals originate with commercial market-research firms that do not publish their sampling frames or their method; citing such a number as established fact would breach the same evidential standard this dissertation applies to vendor accuracy claims in Section 2.1. Sport commands a disproportionate share of promotional spending for structural reasons that do not depend on the exact total: sporting events are consumed live and at scale, they generate repeated rather than one-off contact, and they attach a brand to a relationship that is emotional, habitual and geographically identifiable.

Sport also has one further property, less often remarked upon, that matters more to this dissertation than any of the others. It leaves a complete visual record of itself. Every match that is broadcast, streamed or cut into highlights is a permanent account of which sponsor marks appeared, when, for how long and how clearly. The evidence that would settle what a sponsorship actually delivered is therefore produced automatically, as a by-product of the sport being watched.

## 1.2 The measurement gap

That evidence is almost never used. Sponsorship continues to be priced on precedent and professional judgement: what a comparable property charged last season, adjusted by negotiation, relationship history and the commercial confidence of the parties. Inventory is described in terms of what is offered - a shirt position, a number of perimeter rotations, a package of hospitality - rather than in terms of what an audience demonstrably saw. Post-season reporting is typically a presentation assembled from selected examples, aggregate audience figures and the experience of the people who produced it.

The gap this leaves is specific rather than general. What is invoiced is a position on a shirt; what is delivered is visibility, and the two are not the same thing. The same nominal position yields a mark that is large and legible when a player is the subject of a close-up, and a few indistinct pixels when play moves to the far touchline; it disappears in a tackle, blurs when the camera pans, and appears far more often for a player who happens to be involved in the passages that broadcasters choose to show. The measurements in Chapter 5 put numbers on exactly this asymmetry: within a single held-out test set, the same detector recovers 90% of the marks in close and medium shots and half of them in wide tactical shots. Two clubs charging the same price for the same shirt position may therefore deliver materially different value, and under current practice neither they nor their sponsors have any independent means of telling. Cornwell and Kwon (2020), reviewing sponsorship-linked marketing research, identify persistent shortages in precisely this area of measurement and accountability.

Being exact about the target matters here, because the claim is narrower than it may first appear. Visibility is not attention, recall, brand attitude or sales; research on how viewers process sponsorship stimuli in broadcast sport shows that response depends on the conditions of exposure and on the viewer's involvement, not merely on whether a mark was present (Breuer and Rumpf, 2012; Rumpf et al., 2020). What can be said is firmer for being narrower: visibility is the first link in that chain and the only one that can be observed directly rather than inferred, so everything inferred from it inherits whatever error it contains.

Where the money is largest, the market has already responded. Nielsen describes a valuation process combining automated detection, human analysts, quality-weighted exposure and media rates (Nielsen, n.d.-a; Nielsen, 2017), and Relo Metrics and Blinkfire offer comparable platforms (Relo Metrics, n.d.; Blinkfire, n.d.). Their existence confirms both that the problem is real and that it is tractable. It does not make it solved for most rights holders. These services are specified and priced for major properties, and their methods are proprietary: the club receiving the report cannot see how a figure was produced or check it against the footage. The organisations least able to absorb a mispriced sponsorship are thus the ones still negotiating on assertion.

## 1.3 From judgement to evidence

The obstacle, then, has never been the absence of evidence. As the previous sections have set out, the footage already contains a complete account of what appeared on screen; what has been missing is an affordable way to examine it. That work has traditionally meant a person watching a match in real time, producing judgements that differ between reviewers and cannot be re-checked without repeating the effort from the beginning.

Automation changes that cost, and this is where artificial intelligence enters the argument - though not in its most discussed form. Work on AI in marketing has concentrated on prediction, personalisation and content generation (Davenport et al., 2020; Huang and Rust, 2021). The application here is more modest and more immediately tractable: not deciding what a customer will do, but observing reliably what has already happened. Computer vision suits the task because the record is visual and highly repetitive, and because once the examination is automated the same footage can be re-examined indefinitely at negligible additional cost.

The commercial consequence is not primarily speed. It is that a claim about visibility can be traced back to the moments of footage that produced it, which is what turns a number into an argument a sponsor is able to check. That, in turn, sets a condition on any system built for this purpose: accuracy alone is insufficient if the resulting figure cannot be inspected, because an unverifiable number simply reproduces the limitation of the proprietary platforms it was meant to replace. The same discipline applies in the other direction, since a measure that quietly overstates its own reach is no more useful than one that cannot be checked at all. Chapter 5 applies that discipline to this project's own headline result.

## 1.4 Aim, research questions and contribution

Two questions follow from the preceding argument. Can sponsor visibility be measured automatically and accurately enough to be commercially useful? And can it be measured transparently and cheaply enough to be usable by an organisation that has neither a specialist technical team nor an enterprise contract?

This dissertation addresses both, using a professional rugby league club, Bradford Bulls, as its case study. Rugby league is a demanding but representative setting: sponsor marks appear on moving players as well as on static signage, several sponsors compete for attention within a single frame, and the club operates under exactly the resource constraints that make the second question worth asking.

The **aim** is to develop and evaluate a system that identifies multiple known sponsor logos in sports-broadcast footage and measures the quality and duration of their visibility.

The study has three objectives:

1. Develop and evaluate a multi-logo detection capability on footage from matches the system has not previously encountered.
2. Examine how the conditions of appearance - size, screen coverage, camera distance, lighting and occlusion - affect both automated detection and human readability.
3. Estimate the duration of sponsor visibility and combine transparent, frame-level evidence into an interpretable Logo Visibility Score.

The corresponding research questions are:

- **RQ1:** How accurately and efficiently can the system identify multiple known sponsor logos in unseen sports footage?
- **RQ2:** How do logo size, screen coverage, camera distance, lighting and occlusion affect detection performance and human readability?
- **RQ3:** How accurately can frame-level detections estimate visibility duration and support an interpretable Logo Visibility Score?

| Research question | Evidence required | Where it is reported |
| --- | --- | --- |
| RQ1 | Held-out detection metrics on unseen matches, per-class support, comparison against an alternative architecture under one protocol, inference benchmark | Sections 5.2 to 5.4 |
| RQ2 | Input-geometry analysis, condition-stratified held-out results, qualitative error cases, human readability ratings | Sections 5.1, 5.5, 5.6; readability outstanding |
| RQ3 | Implemented temporal algorithm, manual start/end timing under alternative sampling and gap settings, score sensitivity | Section 5.7; validation outstanding |

*Table 1. Research questions and the evidence each requires. Two evidence packages remain incomplete and are identified as such rather than substituted with implementation output.*

Answering these questions is intended to contribute on three fronts. The first is evidence on feasibility: whether automated sponsor-visibility measurement can be achieved outside a commercial vendor relationship, with resources available to a small technical team. The second is a visibility measure designed to be interpretable by a commercial audience, in the sense established above - every summary figure resolvable to the footage behind it, and every assumption stated rather than embedded. The third is a candid account of the limits, so that a club adopting this approach knows what the resulting numbers will and will not support in a negotiation.

Those limits define the scope. The system recognises a defined roster of sponsors it has been taught and cannot reliably name a brand it has never encountered. It measures visibility rather than the commercial effect of visibility; where monetary valuation appears, it is an optional downstream illustration rather than a validated output. The analysis does not attribute exposure to individual players, and the commercial priority weights supplied by the club are treated as statements of preference rather than as ground truth about what an audience saw. The remainder of the dissertation follows the same movement as this chapter: Chapter 2 reviews what is known about sponsorship measurement and about the vision techniques capable of supporting it, and identifies the gap between them; Chapter 3 sets out the research design; Chapter 4 describes the system built; Chapter 5 reports what it achieved; and Chapter 6 returns to the commercial question with which this chapter began.

---

# Chapter 2: Literature Review

## 2.1 Sponsorship measurement and the business problem

Sponsorship is better understood as a linked marketing relationship than as a simple purchase of advertising space. Cornwell (2019) argues for attention to authentic engagement, while Cornwell and Kwon (2020) identify both a substantial research base and continuing gaps in explaining how sponsorship works. Broadcast visibility is one input to the relationship. It documents an opportunity for the mark to be seen, but it does not establish that a viewer looked at it, remembered it or changed behaviour.

Traditional measurement ranges from expert judgement and manual content analysis to audience research and media monitoring. A reviewer may record the start and end of each appearance, placement, size and quality. Eye-tracking and psychophysiological methods can address attention more directly. For example, Rumpf et al. (2020) modelled gaze towards sponsorship stimuli, while Breuer and Rumpf (2012) examined how viewers receive and process sponsorship information. Such methods answer questions that logo detection cannot, but controlled attention studies are expensive to apply to every minute of every broadcast. Automated exposure measurement and human attention research should therefore be treated as complementary layers.

Industry platforms combine several layers. Nielsen publicly states that its sponsorship reporting uses AI and expert analysts to track content and combines brand exposure with audience and media-rate information (Nielsen, n.d.-a). Its description of the acquired vBrand platform explicitly mentions frame-level logo recognition and quality factors such as duration, size and image clarity (Nielsen, 2017). This supports the conceptual choice to measure more than detection count. It does not disclose enough data to reproduce the proprietary quality index or to compare mAP directly. Vendor statements are consequently evidence of existing functionality, not proof that a particular algorithm is accurate on this dataset.

Equivalent Media Value converts exposure into an advertising-equivalent amount. The conversion is attractive because it produces a familiar monetary unit, but it can hide large assumptions about audience, CPM, platform, creative quality and the reference advertisement length. An observed exposure is not a sale, an invoice or a contract price. In this dissertation, quality-weighted seconds are the primary output. If a scenario calculation is required, the code uses a 30-second advertising equivalent:

\[
\text{Illustrative EMV} = \left(\frac{Q}{30}\right) \times \left(\frac{\text{CPM}}{1000}\right) \times \text{Audience} \times M,
\]

where \(Q\) is quality-weighted exposure in seconds and \(M\) represents explicitly declared scenario multipliers. Omitting the division by 30 would inflate the result by a factor of 30. No CPM or multiplier is presented as a market benchmark without an external source, and the result is not used as a model target.

The accessibility gap must also be stated carefully. Public vendor pages show capable systems, but they rarely publish prices, hardware costs or evaluation samples. It would therefore be speculative to claim that all smaller clubs are excluded or that LogoLens is universally cheaper. Within the evidence available, the defensible gap is transparency and local reproducibility: a club-specific, inspectable pipeline whose predictions, thresholds and errors can be examined without claiming to replace a commercial service.

## 2.2 Computer vision for logo detection and visibility measurement

Logo detection localises and labels a logo in an image. Logo recognition assigns its identity, while retrieval searches a gallery for similar examples. Early benchmarks such as FlickrLogos-32 and OpenLogo showed the difficulty of clutter, limited examples and large brand vocabularies (Romberg et al., 2011; Su et al., 2018). Liao et al. (2017) focused specifically on multiple logos in sports video and described variation in layout, deformation, motion blur and partial occlusion. These challenges remain directly relevant when logos are printed on moving fabric.

A closed-set detector is appropriate when the system needs to report a known seasonal sponsor list. In plain language, the model is taught the logos that the club currently needs to measure. This supports specialist accuracy and simple reporting, but a new sponsor requires annotated examples and retraining. Open-set or retrieval methods could reduce that onboarding burden, although they introduce gallery design, unknown-class handling and verification problems. The present work treats open-set recognition as future research rather than suggesting that a specialist checkpoint can recognise any logo.

Modern object detection is dominated by convolutional one-stage detectors and transformer-based detectors. YOLO framed detection as a fast, single-pass prediction problem (Redmon et al., 2016), and current implementations remain attractive for deployment. DETR replaced anchors and non-maximum suppression with set prediction and bipartite matching (Carion et al., 2020). Later work improved convergence and real-time performance. RT-DETR introduced an efficient hybrid encoder and flexible decoder depth, reporting a competitive speed-accuracy trade-off on standard benchmarks (Zhao et al., 2024). RF-DETR is a specialist real-time detection transformer with a DINOv2-based visual backbone and model variants intended to occupy different points on the accuracy-latency curve (Robinson et al., 2025; Oquab et al., 2023).

The comparative literature does not settle which family suits this task. Published rankings are established on general benchmarks whose objects, scales and scene statistics differ from a sponsor mark printed on moving fabric, and a comparison that changes the dataset, the augmentation recipe and the scoring code at the same time cannot attribute a difference to architecture. Section 5.4 therefore reports a local comparison in which the data, the split, the input resolution and the scoring code are held fixed, and states explicitly which variables could not be equalised.

Small objects are the central technical constraint. The marks in this dataset have median dimensions of 70 × 48 pixels in the source broadcast frame. Because a detection transformer resizes its input to a square, the geometry of that resize determines what survives: at a 512-pixel input the median mark measures roughly 19 × 23 pixels, and the DINOv2-style backbone used here divides the image into 16 × 16 tokens, so such a mark spans little more than one token in each direction. Information lost during resizing cannot be recovered by a better confidence threshold. Letterboxing can make this worse: preserving aspect ratio inside a square canvas adds unused pixels, so fewer model pixels represent the logo. Multi-scale features, high input resolution, native-frame preprocessing and diverse close, medium and wide shots are therefore substantive design choices rather than cosmetic tuning, and Section 5.1 quantifies each.

Evaluation uses precision, recall and Average Precision. A prediction is usually matched to a ground-truth box when class labels agree and IoU exceeds a threshold. AP@0.50 tolerates more localisation error than AP@0.75, while COCO-style mAP@[0.50:0.95] averages across increasingly strict thresholds (Lin et al., 2014). For a box only 33 pixels wide, a few pixels of displacement can change IoU substantially. Reporting both AP@0.50 and stricter metrics is essential because a broad box may be adequate for presence detection but weak for screen-coverage measurement.

Two evaluation hazards are less often discussed and both bear directly on this study. The first is temporal leakage. Frames sampled a second apart from one broadcast are near-duplicates, so a split made at the level of images allows a model to be tested on scenes it has effectively memorised; work on large sports-video benchmarks makes the same point about correlated frames (Deliège et al., 2021). The second is sparse class support. A per-class AP computed over one or two ground-truth boxes is a mechanical artefact of how the precision-recall curve is constructed rather than a measurement of capability, yet it enters the class-averaged mAP with the same weight as a class supported by thirty boxes. Section 3.3 states the rule this dissertation adopts in response, and Section 5.3 measures how much the rule changes the reported result.

Visibility is not represented fully by confidence. Size can be measured as box area divided by frame area. Position can be represented by distance from the screen centre if centrality is considered a useful proxy. Sharpness may be approximated with edge measures, and contrast with foreground-background intensity differences, but both are sensitive to crop size and background. Occlusion is especially difficult with ordinary horizontal boxes because the detector does not provide a visible mask or an oriented logo shape. A score must distinguish direct measurements, proxies and currently unsupported components.

Duration adds a temporal problem. Sampling at \(f_s\) frames per second means each analysed frame represents approximately \(1/f_s\) seconds, but positive frames can be interrupted by model misses. Tracking methods such as ByteTrack associate detections across frames and can support segments (Zhang et al., 2022). A gap tolerance prevents a single miss from splitting one appearance; a minimum duration suppresses isolated false hits. Each rule trades recall against over-counting and must be validated against manually timed sequences.

## 2.3 Research gap and study framework

The literature was reviewed through combinations of terms including *sports sponsorship measurement*, *logo detection*, *logo recognition*, *small-object detection*, *DETR*, *RF-DETR*, *broadcast video*, *visibility duration*, *occlusion* and *human readability*. Priority was given to peer-reviewed work from 2020 onwards, with older foundational detection, logo and sponsorship studies retained where necessary. Technical claims were checked against papers or official repositories. Vendor sources were included only to describe publicly documented products and were not treated as independent accuracy evidence.

| Literature area | What is established | Limitation relevant to LogoLens |
| --- | --- | --- |
| Sponsorship-linked marketing | Exposure can support awareness, but response depends on context and processing | Visibility cannot be equated with attention, sales or ROI |
| Commercial media valuation | Logo tracking and quality-weighted reporting exist in practice | Algorithms, prices and matched public benchmarks are generally unavailable |
| Logo detection in sports video | Multiple, deformed, blurred and occluded logos are recognised challenges | Many datasets do not reflect a smaller rugby club's sponsor roster |
| YOLO and DETR families | Both offer useful speed-accuracy trade-offs | General benchmark results do not resolve small-jersey-logo performance |
| Small-object detection | Resolution and multi-scale representation are critical | Broadcast resizing and temporal leakage are often underreported |
| Evaluation practice | Class-averaged mAP is the standard summary | Sparse classes enter the mean unweighted, and few studies report support |
| Temporal aggregation | Tracking and gap rules can form exposure segments | Duration estimates need manual timing validation |
| Composite visibility scores | Size, quality and duration are plausible components | Weights can appear objective without human or sensitivity validation |

*Table 2. Synthesis of selected literature and its relevance to the study.*

Within the literature reviewed, no study was identified that documents the same combination of a match-disjoint, club-specific multi-logo detector; transparent small-logo preprocessing analysis; frame-traceable visibility measurement; manual duration validation; and an explicit smaller-club accessibility focus. This wording does not claim that no commercial or academic system performs these functions. It states the narrower gap found in the reviewed evidence.

The study uses design science because it builds and evaluates an artefact intended to address a practical problem (Hevner et al., 2004). The evaluation is a quantitative case study because the artefact is tested in one real club context. Figure 1 presents the research logic: a sponsorship evidence need motivates a computer-vision pipeline, which produces traceable visibility information for local review. Figure 2 narrows that logic into the technical workflow. Technology acceptance is not used because no adoption survey or staff-interview dataset was collected.

![Figure 1. Research framework](LogoLens_MSc_Dissertation_v16_media/figure_01_research_framework.png)

*Figure 1. Conceptual research framework: sponsorship need, broadcast computer vision and transparent evidence outputs for a smaller-club context. The graphic is conceptual and contains no measured values.*

![Figure 2. Technical workflow](LogoLens_MSc_Dissertation_v16_media/figure_02_technical_workflow.png)

*Figure 2. Leakage-aware data and model-development workflow. Match separation and validation-only model selection are part of the design rather than post-hoc corrections.*

---

# Chapter 3: Research Methodology

## 3.1 Research design and case study

The research combines design science with a quantitative case-study evaluation. Design science is appropriate because the principal output is an artefact: a working pipeline that transforms broadcast video into detection and visibility records. The process was iterative. Data problems were observed, alternative preprocessing and resolutions were tested, the split was redesigned around matches, and the resulting checkpoint was evaluated on material excluded from development. The case-study element keeps the artefact connected to a real sponsor roster and real broadcast conditions instead of an artificial collection of isolated logo images.

Bradford Bulls provides a useful case because the club has multiple sponsors on one kit and a mixture of close-up, medium and wide broadcast shots. The case is not treated as representative of every sport. Rugby contact creates particular occlusion and deformation patterns; highlight editing changes the distribution of shots; and the white home kit differs from darker or patterned kits. The value of the case is analytical depth and operational realism, not statistical representativeness.

The unit of independence is the match. This decision changed the evaluation materially. The original 30 apparent "clips" were drawn from one approximately 11.5-minute source video: their timestamps rise steadily from 00:10 to 11:27. Twenty-one of 22 clips occurred in both training and validation, 15 of 16 occurred in both training and test, and 51 of 56 validation frames had a training frame from the same clip within two seconds. At a sampling rate of about two frames per second, frames two seconds apart are near-identical, so a random image split measured recognition of familiar scenes more than generalisation. The final design assigns complete matches to one split only, and Section 5.3 measures what that decision costs in reported accuracy.

## 3.2 Data preparation and model-development strategy

The final dataset contains 15 disjoint match groups: 14 named groups and one legacy source group whose frames remain together in training. Shot-aware sampling was used to reduce near-duplicate material. Candidate shots were represented with DINOv2 embeddings, clustered, and reduced to a representative frame per shot. This process aimed to add different camera views rather than more adjacent frames.

Two selection heuristics were tested and rejected on measurement rather than intuition, and both rejections are informative. A flat-region ratio was proposed to detect broadcast graphics; a frame 80% covered by a graphic wipe measured 0.208 while genuine training frames reached 0.350, so the distributions overlapped completely and the metric was discarded in favour of counting home-team players, which separated the two cases cleanly. A brightness-only lighting heuristic was also rejected: a visually confirmed daytime match measured a tenth-percentile value of 46 and a confirmed floodlit match measured 42, because stands and advertising boards are dark even at midday. Lighting metadata was therefore assigned manually. A related defect was found and fixed in the process: the white-kit colour preset had been calibrated for daylight (V ≥ 180, S ≤ 55), but under floodlights the same jersey measured V ≈ 138 and S ≈ 121, so the filter excluded the home team and returned two usable frames from a floodlit match; relaxing both channels returned fifteen.

Annotations use horizontal bounding boxes around visible sponsor marks. The category table contains a placeholder plus 16 sponsor classes used by the final home-kit checkpoint. The split script identifies nine training, three validation and three test match groups, with no group shared across splits. The label `OLD` represents the legacy source group rather than an additional named match identifier. No frame from a test match was used to choose the checkpoint.

| Split | Match groups | Images | Annotated boxes | Role |
| --- | ---: | ---: | ---: | --- |
| Train | 9 | 460 | 1,611 | Weight optimisation and augmentation |
| Validation | 3 | 63 | 127 | Checkpoint selection and stopping |
| Test | 3 | 61 | 165 | Final held-out evaluation only |
| **Total** | **15 disjoint match groups** | **584** | **1,903** | **16 sponsor classes** |

*Table 3. Final match-disjoint dataset. One class (CCH) has no box in the test split, so test mAP is calculated over the 15 represented classes.*

Because the held-out result carries the weight of RQ1, the composition of the test split is reported in its own right rather than left implicit. Table 4 shows that the test material is not drawn from a single condition: it spans three matches, both source resolutions used by the broadcaster, daylight and floodlit lighting, and all three camera distances.

| Property | Composition of the 61 test images |
| --- | --- |
| Matches | M_CAS 24 images / 106 boxes; M_HFC 28 / 41; M_HKR 9 / 18 |
| Camera distance | 40 close-up, 13 medium, 8 wide |
| Lighting | 37 daylight, 24 floodlit |
| Source resolution | 52 frames at 1920 × 1080, 9 at 2560 × 1440 |
| Kit | White home kit only |

*Table 4. Composition of the held-out test set. Lighting is confounded with match: every floodlit test image comes from M_CAS.*

Source frames retain their native 1920 × 1080 or 2560 × 1440 geometry rather than being pre-letterboxed into a mostly square canvas. Measured across all 1,903 annotated boxes, the median mark is 70 × 48 pixels, giving a median area of 3,272 square pixels. In source-frame terms that is not a small object by the COCO convention - only 7.5% of boxes fall below the 32 × 32 threshold - but the relevant space is the model input, and there the picture reverses: at a 512-pixel input the median mark shrinks to approximately 19 × 23 pixels and the great majority of boxes fall into the COCO small category. This distinction between source geometry and input geometry is the reason resolution dominates the optimisation record in Section 5.1.

RF-DETR Small was chosen for the final optimisation. The model uses a DINOv2-based windowed backbone, detection-transformer queries and set-based prediction. Training used AdamW, automatic mixed precision, exponential moving averages, a three-epoch warm-up, cosine learning-rate decay and early stopping. Augmentation included horizontal flips, small rotations, brightness and gamma variation, blur, motion blur and coarse dropout. These augmentations increase robustness but do not substitute for a condition-specific test, and Section 5.5 reports the condition-specific test separately.

One configuration defect deserves recording because it was invisible in the loss curves and was found only by reading the logged learning rate. The library defaults set the learning-rate drop to epoch 100 in a 100-epoch run with no warm-up, so the schedule never fired and every epoch trained at 1.0 × 10⁻⁴. The symptom was a run that peaked at epoch 68 and then drifted downward for thirty epochs, which is the classic signature of a step that never decays. RF-DETR does optimise the learning rate across parameter groups - a separate encoder rate, a vision-transformer layer decay and a component decay - but not across epochs. After warm-up and cosine decay were added, the final run peaked at epoch 36 and stopped at epoch 52 of a planned 60 under a patience of 15, taking approximately 2.5 hours on the target GPU.

Model development proceeded through five recorded runs. Runs 1 to 4 were useful diagnostics but used leaky image-level validation and cannot be compared as independent generalisation estimates with Run 5, which used match-disjoint data at resolution 896.

## 3.3 Evaluation protocol

Precision is the proportion of accepted predictions that match ground truth; recall is the proportion of ground-truth boxes detected. F1 balances the two. AP integrates precision and recall across confidence thresholds, while mAP averages over represented classes. The final evaluation retains predictions down to a confidence of 0.01 so that the precision-recall integration has material to work with - 5,820 candidate boxes across 61 images - matches predictions to ground truth at IoU 0.50 for the threshold sweep, and reports the threshold with the highest F1. AP@0.50, AP@0.75 and COCO-style mAP@[0.50:0.95] are all reported because they answer different localisation questions.

Three procedural decisions in this protocol are worth stating explicitly, because each affects how the numbers in Chapter 5 should be read.

**Evaluation is repeated along more than one path.** Version 15 of this work reported mAP@0.50 from an independent script and mAP@[0.50:0.95] from the training framework's own evaluator, because the independent script had been configured with a maximum-detections list that caused the library to return an invalid value for the stricter metric. That configuration has been corrected, so a single independent run now yields all four headline numbers. The earlier paths were not discarded: Section 5.2 reports all three side by side, and their agreement is treated as evidence about measurement stability rather than as an embarrassment to be resolved silently.

**Per-class results are reported with their support, and the mean is reported twice.** A class with one ground-truth box in the test split cannot produce a meaningful average precision. If the single box is matched by the highest-ranked prediction for that class, the interpolated AP is exactly 1.000; if it is not, the AP is 0.000. No intermediate value is reachable, and no confidence interval worth reporting can be attached: the exact binomial (Clopper-Pearson) 95% interval around one success in one trial runs from 0.025 to 1.000, so a perfect score on one box is statistically consistent with a true detection rate of two and a half per cent. Yet class-averaged mAP gives that class the same weight as one supported by thirty-one boxes. This dissertation therefore reports, for every held-out result: the per-class AP with its box count; the conventional mean over all represented classes; and the mean restricted to classes with at least five ground-truth boxes. The restricted figure is treated as the honest reading of detector capability, and the difference between the two is reported as a quantity rather than described as a caveat. Five is a pragmatic cut-off, not a statistical threshold, so Section 5.3 reports the mean at several cut-offs to show that the conclusion does not depend on the particular choice.

**The operating threshold was characterised on test predictions, not selected on validation.** The confidence sweep in Section 5.2 was run over the same predictions used to compute AP. Under a strict protocol the threshold would be fixed on validation data and then applied once to an untouched test set, and the threshold-specific F1 reported here is consequently an operating-point characterisation rather than an independent estimate. The threshold-free AP measures are unaffected. Section 5.2 also reports how much F1 varies across the plausible threshold band, which bounds the size of the problem.

Inference efficiency was benchmarked after three warm-up images over all 61 test images, with CUDA synchronisation around each prediction. The result includes model prediction but excludes video decoding, disk output, tracking, frontend rendering and process start-up. Peak GPU memory is PyTorch's allocated memory during the timed loop, not total system VRAM. These boundaries are necessary for a meaningful accessibility claim.

The timing benchmark and the accuracy evaluation were run on different inference paths, and the distinction is recorded because it accounts for part of the spread in Table 8. The timing figures come from the library's traced, inference-optimised model, which is what a deployment would use. The accuracy re-measurement reported in this version was run without that tracing step, because the trace requires a memory headroom the shared development machine could not reliably provide; predictions are equivalent but not bit-identical. Together with the maximum-detections correction, this accounts for the 0.0017 difference between the two independent rows of Table 8. Accuracy is therefore reported from the untraced path and latency from the traced one, and neither number is quoted as if it came from the other.

Qualitative examples were also selected reproducibly. At confidence 0.35 and IoU 0.50, the "clear success" is the perfect frame with the strongest maximum confidence; the multi-logo panel is the remaining frame with the best matched-object count; the difficult miss is the frame containing the smallest missed ground-truth box; and the false-positive panel contains the highest-confidence unmatched prediction. This prevents visually attractive examples from being presented as if they were random evidence.

For the architecture comparison in Section 5.4, three YOLO26 variants were trained on the same images, the same match-disjoint split and the same 896-pixel input, and scored with the same pycocotools code and the same greedy IoU-0.50 sweep rather than with the training framework's internal validation metric. Two variables could not be equalised and are stated wherever the comparison is used: the two families apply different augmentation recipes, and they differ in parameter count and in pre-training corpus.

## 3.4 Ethics and reproducibility

The footage is used for model research and contains visible trademarks and players. The study does not identify individuals or infer sensitive personal attributes. Frames are reproduced only where required to show detector behaviour. Sponsor names can be shown because the task is class recognition, but contractual amounts, sponsor charges and club comparisons are not disclosed. The "Human %" column in legacy spreadsheets is treated as commercially supplied weighting rather than participant data or model truth.

Reproducibility records include the dataset manifest, checkpoint, training configuration, random seed, package environment and result files. The final run uses RF-DETR 1.9.1, PyTorch 2.11 with CUDA 12.8 and an RTX 5060 Ti 16 GB. Evaluations reported in this version were executed from `.venv-rfdetr`; the older Conda environments remain relevant to the application but are not the authority for the final checkpoint. The measurements behind every chart in Chapter 5 are stored as JSON in `dissertation/v16_data/` and the charts are regenerated from those files by `dissertation/make_figures_v16.py`, so a reader can check any plotted value against the recorded run.

The dataset was annotated and corrected principally by one researcher. Model-assisted pre-annotation was used on 304 of 584 images before manual correction, which can introduce annotation-style bias. A second independent annotation audit would strengthen the evidence and is listed in Appendix B.

![Figure 3. Split and leakage](LogoLens_MSc_Dissertation_v16_media/figure_03_split_and_leakage.png)

*Figure 3. Dataset design and the effect of temporal leakage. The familiar-material result is deliberately shown as an inflation diagnostic, not as a second test score.*

---

# Chapter 4: Model and System Development

## 4.1 System architecture and logo detection

LogoLens separates model inference from reporting. The backend ingests video, reads frame metadata, samples frames, runs the selected detector and stores a common detection record. The Logo Analytics frontend presents processed videos, brand summaries and exports. This separation allows the detector to change without rewriting the reporting interface, provided every backend returns the same core fields: class, confidence, bounding box, frame index and timestamp.

![Figure 4. System architecture](LogoLens_MSc_Dissertation_v16_media/figure_04_system_architecture.png)

*Figure 4. System architecture and evidence flow. Optional player, team and body-analysis components found elsewhere in the codebase are outside the dissertation scope.*

The current checkpoint is RF-DETR Small at resolution 896. Native-aspect frames are supplied to the model, which performs the configured internal resizing. The output is a set of predicted class identifiers, confidences and horizontal boxes. Because DETR uses set prediction, it does not rely on the same non-maximum-suppression stage as a conventional YOLO detector. Several sponsor marks can be returned from one frame, including repeated instances of one class; the held-out evidence in Section 5.6 includes a frame in which twelve marks are detected simultaneously.

The confidence threshold is 0.35 for the final test operating point, identified by the recorded sweep. As Section 3.3 sets out, a strict deployment protocol would select this value on validation data and lock it before the final test; the sweep here characterises a completed checkpoint, so the threshold-free AP measures remain the stronger final metrics.

Class mapping is a critical engineering detail. The training COCO file contains a placeholder category followed by home-kit sponsor classes, and the standalone detector reads that category table directly. The older backend configuration contains a different 17-brand order, including an away-kit sponsor and a spelling difference in ASC Group, and it defaults to an RF-DETR Large path. Running the optimised Small checkpoint through that configuration without correction could shift brand labels even when boxes are visually correct. This is why the June full-video exports are not presented as final RF-DETR results. The model service must be pinned to the final checkpoint, variant, resolution and category mapping before batch analysis is repeated.

| Item | Final value | Reproducibility note |
| --- | --- | --- |
| Model | RF-DETR Small | Fine-tuned specialist detector, 31.8M parameters |
| Backbone | DINOv2 windowed small | Patch size 16 |
| Input resolution | 896 | Native-aspect source frames |
| Classes | 16 sponsor classes | CCH absent from test ground truth |
| Optimiser | AdamW | Base LR 0.0001; encoder LR 0.00015 |
| Effective batch | 16 | Batch 2 × gradient accumulation 8 |
| Schedule | 3-epoch warm-up + cosine decay | Early stopping patience 15 |
| Augmentation | flip, rotate, brightness/gamma, blur, motion blur, dropout | CPU augmentation backend |
| Model-selection epoch | 36, on EMA weights | Stopped at epoch 52 of 60 |
| Training time | approximately 2.5 hours | RTX 5060 Ti 16 GB |
| Hardware and stack | RTX 5060 Ti 16 GB | RF-DETR 1.9.1, PyTorch 2.11 + CUDA 12.8 |
| Checkpoint | `runs/rfdetr_matchsplit_r896/checkpoint_best_total.pth` | Repository-relative path |

*Table 5. Final model configuration and reproducibility details.*

## 4.2 Visibility quality and duration measurement

Each detection is converted into explicit frame-level measures. Let \(A_i\) be the predicted box area for detection \(i\), \(A_f\) the frame area, \(d_i\) the Euclidean distance between the box centre and the frame centre, \(W\) the frame width, and \(c_i\) the detector confidence. The implemented visibility proxy is

\[
V_i = \sqrt{\frac{A_i}{A_f}} \times \exp\left[-\frac{d_i^2}{(0.3W)^2}\right] \times c_i \times P_{OBB}.
\]

The square-root size term prevents a very large box from dominating linearly. The Gaussian position term assigns the highest value at the centre and reduces it towards the edges. Confidence is used as a clarity proxy. \(P_{OBB}\) is currently fixed at 1.0 because the detector predicts ordinary horizontal boxes; it does not presently measure rotation or perspective distortion. Values are clipped to [0, 1].

This formula is transparent but not yet a validated human-perception model. Size and box centre are direct geometric measurements. Confidence is a model output, not an independent sharpness measurement. The position term is a design assumption, and the OBB penalty is inactive. Blur, contrast and occlusion are named in RQ2 because they matter theoretically, but the current score does not yet contain validated components for them. Adding unvalidated factors would make the score look richer while making its meaning less defensible.

Temporal aggregation groups detections by brand and track. At sampling rate \(f_s\), one sample represents \(\Delta t = 1/f_s\) seconds. Detections below a visibility floor of 0.02 are excluded. A gap larger than 2.5 sampling intervals splits the run into two segments. Segment end is extended by one interval because a sampled frame represents an interval rather than an instant. Runs shorter than 0.5 seconds are removed as flicker. The current duration weight is 0.5 below one second, 1.0 from one to five seconds and 1.2 above five seconds. Quality-weighted exposure for a brand is

\[
Q = \sum_{s=1}^{S} \bar{V}_s \times w_s \times T_s,
\]

where \(\bar{V}_s\) is mean frame visibility in segment \(s\), \(w_s\) its duration weight and \(T_s\) its estimated duration. Raw on-screen seconds must be reported alongside \(Q\), because the weighted number is otherwise difficult to interpret.

![Figure 5. Visibility aggregation](LogoLens_MSc_Dissertation_v16_media/figure_05_visibility_aggregation.png)

*Figure 5. Frame-level visibility and temporal aggregation. The diagram describes the implemented algorithm; it is not evidence that the score agrees with human judgement.*

## 4.3 Logo Visibility Score and system outputs

The term **Logo Visibility Score** is used for a normalised reporting layer over measured exposure, not as a price. A defensible report contains four linked outputs: frame-level detections, continuous exposure segments, raw visible time and quality-weighted time. A video-level normalisation can express one brand's quality-weighted seconds as a share of total measured quality exposure, but the denominator must be stated. A score of 20% may mean 20% of detected quality exposure in one video; it does not mean that a sponsor delivered 20% of contract value.

The existing code also supports an illustrative EMV conversion. It is kept outside the core score for three reasons. First, audience and advertising-rate inputs are external to computer vision. Second, placement multipliers require market or expert justification. Third, sponsorship includes benefits not captured by broadcast equivalence. If the optional calculation is shown, every scenario input should be printed next to the output and the 30-second conversion must be applied. The result should be labelled "illustrative media-value estimate", never "revenue", "charge" or "ground truth".

Outputs are traceable. Each brand record links to segments, and every segment derives from detections with timestamps and source frames. A reviewer can therefore inspect why a logo received exposure rather than accepting a dashboard percentage as an unexplained score. This is the system's most defensible practical advantage: transparency can be evaluated even before a full economic valuation is attempted.

Deployment evidence is promising but bounded. The timed RF-DETR pass averaged 50.5 ms per image, a median of 48.1 ms and a 95th-percentile time of 67.7 ms, corresponding to 19.8 prediction frames per second on the target GPU. PyTorch peak allocated memory during the loop was 0.37 GiB after the model had been loaded and optimised; this is not total application VRAM. At an analytics rate of 2 sampled frames per second, detector inference alone has substantial headroom. Full pipeline speed will be lower once decoding, tracking, persistence and report generation are included.

Current system limits are explicit: a fixed class roster, home-kit training, horizontal boxes, a confidence-based clarity proxy, unvalidated duration weights and a backend configuration that must be aligned with the final checkpoint. These are constraints to test, not details to hide behind the frontend.

---

# Chapter 5: Experiments and Results

## 5.1 What makes this dataset hard, and what the optimisation actually changed

The final experiment is the first run in this project evaluated on complete unseen matches. Its 584 images contain 1,903 annotated boxes across 16 sponsor classes; training uses 460 images and 1,611 boxes, and the held-out test contains 61 images and 165 boxes from three matches the model has never encountered.

The central difficulty is geometric and can be stated exactly. Measured over all 1,903 boxes, the median sponsor mark occupies 70 × 48 pixels of the source frame. Because the detector resizes its input to a square, what matters is not that figure but its image after resizing, and the resize is where the original pipeline lost most of the signal. Figure 6 sets out the arithmetic. Under the original export - a "fit with black edges" canvas of 1208 × 1280, of which 47% is black padding - a 640-pixel input represented the median logo with roughly 23 × 15 pixels, or 351 square pixels in total. Training on native 16:9 frames at 896 pixels represents the same mark with 33 × 40 pixels, or 1,295 square pixels: **3.7 times the effective area, for no additional annotation effort**.

![Figure 6. Input geometry](LogoLens_MSc_Dissertation_v16_media/figure_06_input_geometry.png)

*Figure 6. The median sponsor logo as the model receives it, under five preprocessing and resolution configurations. Panel A shows why enlarging the intermediate canvas is close to useless; panel B shows the effect on effective area.*

Panel A of Figure 6 makes a point that was counter-intuitive when the optimisation began, and that saved a wasted experiment. The intuition was that a larger intermediate canvas would preserve more detail. It does not. For a 16:9 frame placed inside a square input of side R through a width-binding canvas, the content fills the canvas horizontally in both the "fit" and the "stretch" case, so both produce the identical horizontal scale factor R/1920. Preprocessing can change only the vertical scale. This is why raising the canvas from 1208 × 1280 to 1920 × 1920 buys about 6% of height and nothing else, while removing the black padding raises area by 88% at no computational cost. RF-DETR stretches rather than pads, which is often assumed to destroy information; it does not. Letterboxing preserves aspect ratio by sacrificing vertical resolution and filling the remainder with black, whereas stretching keeps the horizontal scale and increases the vertical one. The stretched image contains everything the letterboxed image contains and more, the distortion is consistent between training and inference, and the library's own pre-trained checkpoint was produced through the same transform.

The second consequence of small marks is a ceiling on the stricter metric, and it too can be derived rather than asserted. For a translation error of d pixels on a box of width w, IoU is (w − d)/(w + d), so the tolerance at threshold t is d/w = (1 − t)/(1 + t). For a 33-pixel box at input 896, IoU 0.50 tolerates ±11.0 pixels, IoU 0.75 tolerates ±4.7 pixels, and IoU 0.90 tolerates ±1.7 pixels. Since mAP@[0.50:0.95] averages ten thresholds, its upper half demands sub-two-pixel accuracy in the input space. This explains both why mAP@0.50 sits far above mAP@[0.50:0.95] and why raising resolution moved the stricter metric more than adding data did: across three runs on the same underlying material, changing only input geometry moved mAP@[0.50:0.95] from 0.429 to 0.491 to 0.603.

Table 6 records the full optimisation path. It is tempting to describe the increase from 0.816 to 0.933 as a single controlled improvement, but the evaluation protocol changed part-way: Runs 1 to 4 used image-level splits with temporal leakage, and Run 5 used unseen matches. The table is evidence about engineering decisions, not a fair leaderboard.

| Stage | Data and geometry | Evaluation protocol | mAP@0.50 | mAP@[.50:.95] | Best F1 |
| --- | --- | --- | ---: | ---: | ---: |
| Hosted baseline | Letterbox; input 640 | Leaky image split | 0.906 | not recorded | 0.858 |
| Run 1 | 196 images; letterbox; 512 | Leaky image split | 0.816 | 0.429 | 0.734 |
| Run 2 | 196 images; letterbox; 640 | Leaky image split | 0.886 | 0.491 | 0.838 |
| Run 3 | 230 images; native; 896 | Leaky image split | 0.918 | 0.603 | 0.858 |
| Run 4 | 196 images; native; 896 | Leaky image split | 0.929 | 0.612 | 0.890 |
| **Run 5 final** | **460 training images from 9 matches; native; 896** | **3 held-out test matches** | **0.933** | **0.747** | **0.898** |

*Table 6. Optimisation stages. Values in rows with different splits are not a controlled model comparison; only Run 5 measures generalisation.*

The cleanest sub-experiment in the sequence holds one checkpoint fixed and varies only the resolution used at inference. Raising the input from 512 to 768 pixels lifted mAP@0.50 from 0.776 to 0.880 without retraining a single step - a gain of 10.4 points obtained purely from input geometry. At 896 the result was 0.878 and the best F1 fell from 0.827 to 0.802, showing that resolution has diminishing and eventually negative returns when the training resolution is held fixed. Figure 7 plots both the trajectory and this controlled sweep.

![Figure 7. Optimisation and resolution](LogoLens_MSc_Dissertation_v16_media/figure_07_optimisation_and_resolution.png)

*Figure 7. Optimisation trajectory and a controlled inference-resolution experiment. The left panel crosses evaluation protocols and is therefore diagnostic; the right panel holds the checkpoint fixed.*

A third finding concerns where collection effort should go, and it contradicted the working assumption of the project. Comparing the number of training boxes per class against that class's held-out AP@0.50 produces a Pearson correlation of −0.262 (p = 0.35) and a Spearman correlation of −0.270 (p = 0.33) across the fifteen measurable classes, with an r² of 0.069. The relationship is statistically indistinguishable from none, and if anything it points the wrong way. KLG, with 279 training boxes, reaches 0.947; ATM, with 113, reaches 0.832; Ellgren, with 77, reaches 0.947. Within a fixed set of matches, a weak class is not the class with less data.

![Figure 8. Support against accuracy](LogoLens_MSc_Dissertation_v16_media/figure_08_support_vs_ap.png)

*Figure 8. Training support against held-out AP@0.50. The absence of a relationship is the result: additional frames of the same match add examples that are highly correlated with those already held.*

This is the finding that redirected data collection from adding frames to adding matches, and the redirection is what produced the largest jump in the stricter metric, from 0.612 to 0.747. One incorrect prediction is worth recording alongside it: before Run 5 the expectation was that a match-disjoint figure would fall to somewhere between 0.70 and 0.82 mAP@0.50. It reached 0.933, because the training set moved from one match to nine at the same time as the evaluation became honest. An estimate calibrated on the old data regime did not survive a change in both terms at once.

## 5.2 Held-out detection accuracy

The final evaluation loaded `checkpoint_best_total.pth`, processed the 61 test images, retained 5,820 candidate predictions above a confidence floor of 0.01, and scored them with pycocotools. Table 7 reports the result together with the inference benchmark.

| Metric | Result | Evaluation detail |
| --- | ---: | --- |
| mAP@0.50 | 0.933 | 15 represented classes |
| mAP@0.75 | 0.917 | Same run |
| mAP@[0.50:0.95] | 0.747 | Same run |
| mAP@0.50, classes with n ≥ 5 only | 0.917 | 11 classes, 158 of 165 boxes |
| Best threshold-specific F1 | 0.898 | Confidence 0.35; IoU 0.50 |
| Precision at best F1 | 0.912 | 146 true positives, 14 false positives |
| Recall at best F1 | 0.885 | 146 true positives, 19 missed |
| Mean prediction time | 50.5 ms/image | 61 images after three warm-up images |
| Median / 95th-percentile time | 48.1 / 67.7 ms | CUDA synchronised |
| Prediction throughput | 19.8 FPS | Excludes decoding and reporting |
| Peak PyTorch allocated GPU memory | 0.37 GiB | Not total process VRAM |

*Table 7. Final held-out test and inference results on an RTX 5060 Ti 16 GB. Timing figures come from the optimised inference path described in Section 3.3.*

Two features of this table matter more than the headline. The first is that mAP@0.75 (0.917) sits very close to mAP@0.50 (0.933). For an object this small that is a strong result rather than an incidental one: it says that when the detector finds a mark, it usually places the box tightly enough to survive a much stricter overlap requirement, which is what any downstream measurement of screen coverage depends on. The drop to 0.747 at mAP@[0.50:0.95] comes from the upper half of the threshold range, where, as Section 5.1 showed, the geometry allows less than two pixels of error.

The second is the shape of the confidence sweep, shown in Figure 9. Between thresholds of 0.20 and 0.50 the F1 score varies by only 0.048, so the reported operating point is not perched on a narrow peak; a deployment that chose 0.30 or 0.40 instead of 0.35 would obtain materially the same behaviour. This bounds the concern raised in Section 3.3 about the threshold having been read from test predictions. At the chosen point the detector returns 146 correct boxes, 14 false positives and 19 misses out of 165.

![Figure 9. Confidence sweep](LogoLens_MSc_Dissertation_v16_media/figure_09_confidence_sweep.png)

*Figure 9. Precision, recall and F1 across the confidence sweep, and the same sweep counted in boxes. The shaded band marks the range within which the operating point is insensitive.*

## 5.3 How much of that number is real

An accuracy figure is only as good as the checks applied to it. Three checks are reported here: agreement between evaluation paths, the effect of sparse classes, and the size of the leakage the split design avoids.

**Agreement between evaluation paths.** The same checkpoint and the same test images were scored three ways: by the training framework's own evaluator during Run 5, by the repository's independent script as configured for version 15, and by the corrected independent run reported above. Table 8 shows the results. The three paths span 0.0065 mAP@0.50 - less than seven tenths of one point - and the differences are explained by the maximum-detections setting and by whether the traced, inference-optimised model was used, which alters numerics slightly. Independently, the corrected run's mAP@[0.50:0.95] of 0.7471 agrees with the training evaluator's 0.7441 to within 0.003, despite the two being computed by different code on different paths. A conservative reader may take the lowest value in each column; the conclusion does not change.

| Evaluation path | mAP@0.50 | mAP@0.75 | mAP@[.50:.95] | Best F1 |
| --- | ---: | ---: | ---: | ---: |
| Run 5 training evaluator | 0.9383 | not reported | 0.7441 | not reported |
| Independent script, version 15 configuration | 0.9318 | 0.9149 | invalid under that configuration | 0.895 |
| Independent script, corrected configuration | 0.9335 | 0.9166 | 0.7471 | 0.898 |
| **Spread across paths** | **0.0065** | **0.0017** | **0.0030** | **0.003** |

*Table 8. Agreement between three evaluation paths on the same checkpoint and the same 61 test images.*

**The effect of sparse classes.** Of the fifteen classes represented in the test split, four carry fewer than five ground-truth boxes: Chadlaw and MNA Support Services have one each, MNA Cladding has two, and Fairway has three. Together they account for seven of the 165 test boxes - 4.2% of the evidence - yet they contribute 26.7% of the class-averaged mean, and three of them score exactly 1.000. Figure 10 shows both the per-class picture and what happens to the mean as a minimum-support rule is tightened.

![Figure 10. Per-class AP and support](LogoLens_MSc_Dissertation_v16_media/figure_10_per_class_and_support.png)

*Figure 10. Per-class AP@0.50 with ground-truth support, and the effect of requiring a minimum support before a class enters the mean.*

| Minimum support | Classes retained | Test boxes covered | mAP@0.50 |
| --- | ---: | ---: | ---: |
| n ≥ 1 (conventional) | 15 | 165 | 0.9335 |
| n ≥ 2 | 13 | 163 | 0.9232 |
| n ≥ 3 | 12 | 161 | 0.9169 |
| **n ≥ 5 (reported alongside)** | **11** | **158** | **0.9169** |
| n ≥ 10 | 7 | 134 | 0.9378 |
| Support-weighted mean over all 15 | 15 | 165 | 0.9293 |

*Table 9. Effect of a minimum-support rule on the reported mean. The conventional figure is 1.7 points above the figure obtained once classes with fewer than five boxes are excluded.*

The scale of the distortion is therefore modest but real: 1.7 points of mAP@0.50. It is worth being precise about why those three values of 1.000 carry so little information. With a single ground-truth box, the interpolated average precision can only be 1.000 or 0.000, so the value reports a coin-flip outcome rather than a rate. The exact binomial 95% interval around one success in one trial runs from 0.025 to 1.000; around two successes in two trials, from 0.158 to 1.000; around three in three, from 0.292 to 1.000. Even five consecutive successes leave a lower bound of 0.478. A second symptom appears in the stricter metrics: Chadlaw and MNA Support Services both score AP@0.50 of 1.000 and AP@[0.50:0.95] of exactly 0.600, a value reachable only because a single box either matches or does not at each of the ten IoU thresholds. A quantity that jumps between 1.000 and 0.600 according to which threshold band is quoted is not measuring detector capability.

This is why Section 3.3 requires the restricted mean to be reported alongside the conventional one, and why the sparse classes are neither deleted nor promoted. Deleting them would conceal a genuine dataset limitation - CCH, the shorts sponsor, has only eight boxes in the entire 584-image dataset and none at all in the test split - and an examiner would rightly ask where those sponsors went. Quoting them without their support would overstate what the system can promise a paying sponsor. Reporting both, with the difference quantified, is the only presentation that survives scrutiny in either direction. Section 6.3 returns to what this means commercially, and Appendix B lists the targeted frame selection needed to fix it.

**The size of the leakage avoided.** Running the same final checkpoint over material from matches that appear in training produces mAP@0.50 of 0.998 and F1 of 0.988, against 0.933 and 0.898 on unseen matches. The familiar-material figures inflate mAP@0.50 by approximately 6.5 points and F1 by 9.0 points. These differences are not model gains; they are the measured size of the evaluation bias that the match-disjoint design avoids. Stated commercially, a report built on the leaky protocol would have promised a sponsor that virtually every appearance was captured, when the honest figure at the same operating point misses roughly one mark in nine.

Finally, the aggregate is not carried by one easy match. Scored separately, the three held-out matches give mAP@0.50 of 0.973 (M_CAS, 106 boxes), 0.934 (M_HFC, 41 boxes) and 0.976 (M_HKR, 18 boxes). The spread of 0.042 across three independent matches is a more informative stability check than any single interval computed from 165 correlated boxes.

## 5.4 Does the architecture choice matter?

Version 14 of this project treated YOLO as the operational detector and RF-DETR as a secondary experiment; the August optimisation reversed that. A reader is entitled to ask whether the reversal reflects the architecture or merely the preprocessing and split work that accompanied it. To answer that, three YOLO26 variants were trained on the same images, the same match-disjoint split and the same 896-pixel input, then scored with the same pycocotools code and the same greedy sweep used for RF-DETR. Table 10 and Figure 11 report the outcome.

| Model | Parameters | GFLOPs | mAP@0.50 | mAP@0.75 | mAP@[.50:.95] | Best F1 (threshold) |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
| YOLO26-n | 2.5M | 5.9 | 0.551 | 0.485 | 0.389 | 0.691 (0.30) |
| YOLO26-s | 10.0M | 22.8 | 0.772 | 0.673 | 0.552 | 0.810 (0.20) |
| YOLO26-m | 21.8M | 75.1 | 0.747 | 0.618 | 0.529 | 0.822 (0.30) |
| **RF-DETR Small** | **31.8M** | — | **0.933** | **0.917** | **0.747** | **0.898 (0.35)** |

*Table 10. Detector families under one evaluation protocol, on the same three held-out matches. Augmentation recipes and pre-training corpora differ between families and are not controlled.*

![Figure 11. Architecture comparison](LogoLens_MSc_Dissertation_v16_media/figure_11_architecture_comparison.png)

*Figure 11. Detector families scored under one protocol. Panel B plots accuracy against parameter count, showing that the gap is not closed by adding capacity within the YOLO26 family.*

Three observations follow. First, the margin is large at every threshold and grows as the localisation requirement tightens: RF-DETR leads the best YOLO26 variant by 16.1 points at mAP@0.50 and by 24.4 points at mAP@0.75. Given the geometry established in Section 5.1, this is the expected signature of an architecture that places tighter boxes on very small objects rather than one that merely finds more of them. Second, capacity within the YOLO26 family does not explain the gap: the medium variant, with more than twice the parameters and three times the compute of the small variant, scores slightly lower on mAP while scoring slightly higher on F1, which is the pattern of a model with enough capacity to fit 460 training images and not enough data to benefit from more. Third, the ordering by F1 is much closer than the ordering by mAP - 0.822 against 0.898 - which is a reminder that a threshold-specific score compresses differences that AP exposes.

The comparison should not be over-read, and two limits are stated wherever it is used. The augmentation recipes could not be equalised: Ultralytics applies mosaic, mixup and copy-paste augmentation by default, while RF-DETR uses its own pipeline, and no configuration makes them identical. Nor is pre-training equalised: RF-DETR's backbone is initialised from DINOv2 self-supervised features (Oquab et al., 2023), which is plausibly part of why it transfers well to a small specialist dataset, and that advantage belongs to the system as delivered rather than to the detection head alone. The defensible conclusion is therefore about systems as an implementer would obtain them: for this data, at this scale, with each library's default training recipe, the transformer detector is substantially more accurate, and the preference for it is not merely a by-product of the preprocessing work.

## 5.5 Conditions of appearance

RQ2 asks how the conditions under which a mark appears affect whether it is detected. Version 15 of this dissertation could not answer that question with held-out evidence. It can now be answered in part, by scoring the same test predictions separately within each condition. Table 11 and Figure 12 report the result.

| Cut | Group | Images | Boxes | mAP@0.50 | Recall at 0.35 | Precision at 0.35 |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| Camera distance | Close-up | 40 | 126 | 0.927 | 0.897 | 0.897 |
| | Medium | 13 | 33 | 1.000 | 0.909 | 0.968 |
| | **Wide** | **8** | **6** | **0.624** | **0.500** | **1.000** |
| Lighting | Daylight | 37 | 59 | 0.903 | 0.831 | 0.860 |
| | Floodlit | 24 | 106 | 0.973 | 0.915 | 0.942 |
| Source resolution | 1920 × 1080 | 52 | 147 | 0.941 | 0.884 | 0.922 |
| | 2560 × 1440 | 9 | 18 | 0.976 | 0.889 | 0.842 |
| Match | M_CAS | 24 | 106 | 0.973 | 0.915 | 0.942 |
| | M_HFC | 28 | 41 | 0.934 | 0.805 | 0.868 |
| | M_HKR | 9 | 18 | 0.976 | 0.889 | 0.842 |

*Table 11. Held-out results by condition of appearance. Lighting is confounded with match: all floodlit test images come from M_CAS, so the lighting rows are not an independent lighting effect.*

![Figure 12. Conditions](LogoLens_MSc_Dissertation_v16_media/figure_12_conditions.png)

*Figure 12. Held-out performance by camera distance, lighting and ground-truth logo size. Panel C reports recall at the operating threshold within size bands.*

**Camera distance is the dominant measured effect.** Close-up and medium shots behave similarly, at 0.897 and 0.909 recall. Wide tactical shots collapse to 0.500 recall and 0.624 mAP@0.50. The pattern of errors is as informative as the level: precision on wide shots is 1.000, so the detector is not producing confident nonsense at distance - it is silently failing to fire. From a reporting standpoint that is the better of the two failure modes, but it means exposure in wide play will be systematically under-counted rather than randomly mis-counted, and any duration figure computed from full-match footage will be biased downward. The wide-shot subset is small, at 8 images and 6 boxes, so the effect size is uncertain even though its direction is consistent with the geometry in Section 5.1 and with the qualitative miss in Figure 13.

**Lighting cannot be separated from match here.** Floodlit material scores higher than daylight material, at 0.973 against 0.903, which inverts the usual expectation. The explanation is structural rather than photometric: every floodlit test image comes from M_CAS, the match that also has the densest annotation - 106 boxes in 24 images, against 59 boxes in 37 daylight images from two other matches - and denser boxes mean more close-up material. This row is reported because omitting it would be selective, but it should be read as a match effect wearing lighting's clothing. What can be said is narrower and still useful: the detector does not fail under floodlights, despite no training image carrying a floodlit lighting label. Separating the two factors requires floodlit and daylight material from the same match, which Appendix B lists.

**Size has the expected effect at the small end and is noisy elsewhere.** Recall by ground-truth box size, measured as the square root of area in source pixels, runs 0.667 below 30 pixels (n = 6), then 0.898, 0.894 and 0.966 through the 30-to-80 pixel range, before dropping to 0.762 in the 80-to-120 band (n = 21) and returning to 0.923 above 120 (n = 13). The smallest band is the worst, as predicted, but the dip in the 80-to-120 band shows that size is not the only factor operating: the largest marks in this dataset are chest sponsors in close-up, which are also the marks most often deformed by fabric folds, rotated by body angle or partly occluded in contact. This is precisely the interaction that the inactive OBB term in Section 4.2 cannot currently measure, and it is a more useful finding than a clean monotonic curve would have been.

Taken together these cuts answer part of RQ2 with held-out evidence and leave part of it open. Effective size and camera distance have measurable effects, and their direction is consistent with the input-geometry analysis. Blur, contrast and occlusion are still not isolated as independent factors, because the test material was not stratified along them at collection time, and no human readability data has been gathered against which detector confidence could be validated. The training augmentation deliberately simulates brightness, gamma, blur, motion blur and local dropout, but simulating a condition during training is not evidence of robustness to it at test time. Earlier occlusion figures in version 14 were collected under a different detector and data pipeline and are not carried forward as RF-DETR results.

One further boundary belongs here. All frames in the final dataset show the white home kit. Comparing the two kit specifications shows that home and away swap exactly one chest sponsor: Top Notch on the home shirt, Floor Tonic on the away shirt. Floor Tonic - a paying sponsor in the most valuable position on the garment - is therefore not measurable at all, not because of a technical limitation but because no annotated data exists. The remaining fifteen brands appear on both kits but with colours inverted for contrast against black. Because the detector has no way to refuse an input, it will return confident and wrong boxes on away-kit footage; Section 6.2 argues that this makes a domain gate a prerequisite for deployment rather than a refinement.

## 5.6 Qualitative evidence

Figure 13 shows four held-out cases selected by the rules specified in Section 3.3 rather than by appearance. Panel A contains seven ground-truth logos, all matched without a false positive. Panel B is a close-up with twelve logos and twelve matches, demonstrating that simultaneous multi-logo detection is routine rather than exceptional - the practical significance being that a single frame can supply evidence for a dozen sponsors at once. Panel C is a wide floodlit shot with two small ground-truth marks, both missed; this is the qualitative face of the 0.500 wide-shot recall in Table 11. Panel D contains ten correct matches and two false positives, both localised on visually plausible kit regions, illustrating that strong context can produce an incorrect sponsor class even when most marks in the frame are correct.

![Figure 13. Held-out detection evidence](LogoLens_MSc_Dissertation_v16_media/figure_13_detection_evidence.png)

*Figure 13. Held-out evidence at confidence 0.35. Maroon boxes are matched predictions, orange boxes are false positives and red boxes are missed ground truth. Images were selected by predefined rules rather than appearance.*

## 5.7 Duration, Logo Visibility Score and full-video results

The temporal and scoring pipeline is implemented, but it has not been revalidated end to end with the final checkpoint, and this distinction changes what can be reported. The project contains eight June 2026 workbooks in `dissertation/result_full_run`, covering M02 to M08 and M11. They include location assignment, "Human %", AI-adjusted location shares and visibility outputs. They were generated before the August RF-DETR optimisation and depend on model and class mappings outside the revised scope. The directory therefore contains eight completed workbooks, and none is treated as a final Run 5 full-video result.

Reusing those sheets would create three validity problems. First, the home-only RF-DETR checkpoint cannot support the away-kit M03, M04, M06 and M11 claims, for the reason given at the end of Section 5.5. Second, the backend's default RF-DETR variant and class order do not match the final Small checkpoint. Third, location percentages are commercial priority weights, not observed visibility or ground truth. Appendix D records the files for provenance, but the main table of full-video outcomes is deferred until the correct pipeline is run.

The manual reference needed for RQ3 should contain, for each selected brand appearance, a human start time, end time, interruption decision and readability rating. The automatic result should then be compared using absolute duration error, relative error and limits by sampling rate. Gap tolerance should be varied around the current 2.5-interval rule, and the score should be recalculated without each component and under alternative weights. At least one additional rater is desirable for a subset, with agreement reported before consensus.

Until that experiment is complete, raw duration and Logo Visibility Score accuracy are not claimed. The correct result statement is narrower: the system can transform detections into traceable segments and quality-weighted seconds, but the accuracy of those quantities against human timing and visibility judgement remains to be established. No EMV total is presented because it would compound unvalidated duration, score weights, audience and rate assumptions. Section 5.5 adds one concrete reason to expect a bias rather than merely noise: because recall halves on wide shots, an unadjusted duration estimate over full-match footage will under-count exposure in exactly the passages where wide camera work dominates.

| Research question | Main result in version 16 | Main limitation |
| --- | --- | --- |
| RQ1 | mAP@0.50 0.933 (0.917 restricted to classes with n ≥ 5), mAP@0.75 0.917, mAP@[.50:.95] 0.747, best F1 0.898 on three unseen matches at 19.8 prediction FPS; ahead of the best YOLO26 baseline by 16.1 points under one protocol | Three-match test with 165 boxes; four classes have fewer than five boxes and one has none; architecture comparison does not control augmentation or pre-training |
| RQ2 | Camera distance measured: recall 0.897 close, 0.909 medium, 0.500 wide; native 896 input raises effective logo area 3.7×; smallest size band recalls 0.667 | Blur, contrast and occlusion not isolated; lighting confounded with match; no human readability study |
| RQ3 | Transparent temporal segmentation and quality-weighted exposure implemented and inspectable | Final videos not rerun or manually timed with the new checkpoint; wide-shot recall implies a downward duration bias |

*Table 12. Research-question conclusions and evidence limits.*

---

# Chapter 6: Discussion

## 6.1 Answers to the research questions and comparison with prior work

**RQ1 is answered positively within the case boundary.** A specialist RF-DETR detector identifies multiple known sponsors in unseen Bradford Bulls home-kit footage with mAP@0.50 of 0.933, and - more importantly for any downstream measurement of screen coverage - mAP@0.75 of 0.917. The best operating point combines precision of 0.912 with recall of 0.885, and the model processes nearly twenty images per second in isolation on the target GPU, an order of magnitude above the 2 FPS analytics sampling rate. Three evaluation paths agree to within 0.007, and the three held-out matches agree to within 0.042, so the figure is stable under both measurement and sampling variation.

Two qualifications belong in the same breath as the headline. The restricted mean of 0.917 is the figure a club should plan against, because it excludes four classes whose apparent perfection rests on seven boxes. And the result is bounded to the home kit: the system has no measurement at all for Floor Tonic, an away-kit chest sponsor.

The result should not be compared directly with commercial vendor accuracy, because vendor datasets, class rosters and matching rules are unavailable; nor casually with COCO model-card results, since standard benchmarks contain different objects, scales and scene distributions. The meaningful comparisons are internal, and this version supplies two that version 15 lacked. The first is the leakage diagnostic: the same checkpoint scores 0.998 on familiar match material against 0.933 on unseen matches, which confirms the warning from sports-video benchmarks that correlated frames make evaluation optimistic (Deliège et al., 2021) and puts a number on it. The second is the architecture comparison in Section 5.4, which places the transformer detector 16.1 points ahead of the strongest YOLO26 baseline at mAP@0.50 and 24.4 points ahead at mAP@0.75 under one protocol.

That second comparison deserves a careful reading, because the tempting conclusion is stronger than the evidence. What is controlled is the data, the split, the input resolution and the scoring code - the variables that made earlier comparisons in this project uninterpretable. What is not controlled is the augmentation recipe or the pre-training corpus, and the latter may matter a great deal: the DINOv2 backbone brings self-supervised representations learned at a scale no club could reproduce (Oquab et al., 2023), and small-data specialist fine-tuning is exactly the regime in which such initialisation pays. The claim supported by Table 10 is therefore that RF-DETR Small, as an implementer would obtain and train it, substantially outperforms YOLO26 as an implementer would obtain and train it, on this task at this data scale. It is not the claim that transformer detection heads beat convolutional ones in general. For the club's purposes the weaker claim is the useful one, since it is a claim about a decision they actually face.

**RQ2 is answered in part, and with more evidence than before.** Effective logo size clearly affects feasibility, and the mechanism is now traced end to end: the geometric analysis in Section 5.1 predicts that resolution and preprocessing dominate; the controlled resolution sweep confirms a 10.4-point gain from input geometry alone; and the condition-stratified results in Section 5.5 show recall halving on the wide shots where marks are smallest. This aligns with the sports-logo challenges reported by Liao et al. (2017) and with the general importance of multi-scale representation. The finding that wide-shot failures are silent - precision 1.000, recall 0.500 - is operationally the most consequential result in Chapter 5, because it converts a technical limit into a predictable reporting bias.

What remains unanswered is the part of RQ2 concerning blur, contrast, occlusion and human readability. The augmentation recipe simulates several of these conditions during training, but simulation is not evidence of robustness, and the non-monotonic recall in the 80-to-120-pixel band suggests that deformation and occlusion are already interfering with the size effect in ways the current annotation scheme cannot separate. Nor does confidence establish readability: no human ratings have been collected, so the clarity proxy in the visibility formula remains an assumption.

**RQ3 is not yet answered empirically.** The temporal formula is coherent and inspectable, and the 30-second correction fixes the earlier EMV scaling issue. Yet correctness of code is not accuracy of measurement. A gap rule that appears reasonable can over-count or split exposure, and a confidence-based clarity proxy can disagree with a person. The most defensible conclusion is that the framework exists and produces auditable intermediate values, but its agreement with manual timing and human visibility scores remains an open result - and Section 5.5 now gives a specific, testable prediction about the direction of the error.

## 6.2 Practical meaning and accessibility for smaller clubs

The detector performance is strong enough to support a practical review workflow for in-scope footage. At 2 sampled frames per second, the isolated model's throughput provides roughly tenfold inference headroom. A staff member could receive a brand summary and inspect the frames behind it rather than watching a complete highlight video manually. This is useful even without a monetary value, because it documents delivered screen time, identifies weak views and supports evidence-based conversations.

Accessibility should be framed by measured requirements. Training completed in approximately 2.5 hours on a 16 GB consumer GPU. Inference ran at 19.8 FPS under the stated benchmark, with peak allocated memory of 0.37 GiB. These observations suggest that a local technical deployment is feasible without data-centre hardware. They do not include staff time for annotation, maintenance, video rights, hardware purchase or retraining when sponsors and kits change, and they do not prove that local ownership is cheaper than a managed service once total cost is counted. The honest accessibility claim is about capability and transparency, not about price.

Transparency is the more certain practical contribution. Every aggregate can be traced from report to segment, detection, timestamp and source frame. A commercial judgement can therefore use the measurement without confusing it with the judgement itself. The club may choose to apply expert priority weights, but those weights should be displayed as external inputs. The "Human %" column from the legacy workbook is appropriate only as an anonymised commercial priority or package-allocation variable; it should not be inserted into the model target, used to grade the detector, or described as the correct visibility share.

The reporting conventions this dissertation adopts for its own results translate directly into reporting conventions for the club. A sponsor summary should carry the number of detections behind each figure, in the same way Table 11 carries box counts, because a brand appearing three times in a match cannot be characterised by a percentage. It should distinguish measured from unmeasured: a sponsor absent from a report because it did not appear and a sponsor absent because it is out of the measured domain are different facts that look identical on a dashboard. And it should state the operating threshold and model version, since Figure 9 shows recall moving from 0.885 to 0.806 between thresholds of 0.35 and 0.50 - a difference large enough to matter in a negotiation and invisible in an unlabelled chart.

The system is not yet ready for routine use with every club video. The final class mapping must be fixed in the backend, away-kit data must be collected, and full videos must be rerun. A domain gate should refuse or flag footage whose kit and lighting fall outside the measured training domain. Without that gate, a confident output is operationally more dangerous than a visible failure, because a user will reasonably assume the dashboard has been validated on the footage in front of them.

## 6.3 Limitations and threats to validity

**Internal validity.** Model-assisted pre-annotation may produce consistent but model-shaped boxes, and a primarily single-annotator process can introduce systematic boundary choices; since mAP@0.75 is one of the headline claims, annotation-boundary bias is a live concern and a second independent audit is warranted. The threshold-specific F1 was characterised on test predictions after training; a cleaner final protocol would lock the threshold on validation, although the flatness of the sweep between 0.20 and 0.50 bounds how much this could matter. The three evaluation paths in Table 8 have been reconciled and their residual spread of 0.0065 documented rather than resolved by choosing a favourite.

**Construct validity.** Bounding-box area is a direct measure of screen coverage but not of visible logo area under occlusion. Confidence is a detector score, not clarity or readability. Screen centrality is an assumption about prominence. The inactive OBB penalty means perspective and rotation are not measured, and Section 5.5 gives evidence that this omission is already interfering with the size analysis. Quality-weighted seconds therefore operationalise selected proxies; they are not a psychological visibility scale until compared with human ratings.

**External validity.** The test contains three unseen matches from one club, one sport and one white home kit, with 165 boxes in total. Highlight videos over-represent close shots: even after deliberate diversification the test split holds 40 close-up images against 8 wide ones, which is the inverse of a full broadcast's composition, so the aggregate figure flatters performance relative to full-match footage. Results cannot be generalised to the away kit, a new season, another broadcaster, perimeter boards or unknown logos without new evidence.

**Conclusion validity.** Per-class AP of 1.000 on one or two boxes is not evidence of capability, and Section 5.3 quantifies both the distortion it causes (1.7 points) and the uncertainty it hides (a 95% interval from 0.025 to 1.000 on a single box). The study reports support and restricted means rather than confidence intervals for sparse categories, because an interval computed from one observation is not informative; a larger test set is the only real remedy. The difference between familiar and unseen material demonstrates leakage risk, but it does not estimate performance across all future matches. Similarly, the resolution experiment shows a checkpoint-specific pattern rather than a universal optimum at 768 or 896, and the architecture comparison is bounded by the two uncontrolled variables named in Section 5.4.

**Operational validity.** The backend and final checkpoint are not yet aligned, and the June workbooks belong to an earlier pipeline; presenting them as final outputs would mix model versions and class semantics. The versioned Markdown workflow exists partly to prevent this: version 16 preserves the corrected evidence boundary, and a later version can replace the incomplete sections after a controlled full-video run.

---

# Chapter 7: Conclusion and Future Work

## 7.1 Conclusion and contributions

This dissertation set out to develop and evaluate a computer-vision framework for detecting known sponsor logos and measuring visibility quality in sports broadcasts. The detector component achieved the strongest and most credible result in the project to date. RF-DETR Small, trained at resolution 896 on match-separated native frames, reached mAP@0.50 of 0.933, mAP@0.75 of 0.917, mAP@[0.50:0.95] of 0.747 and a best F1 of 0.898 on three unseen matches, and processed test images at 19.8 FPS on a consumer GPU. Restricted to the eleven classes with at least five ground-truth boxes, mAP@0.50 is 0.917. Under one evaluation protocol on the same data, the strongest of three YOLO26 baselines reached 0.772. A leakage diagnostic showed why the match-level design matters: familiar material raised mAP@0.50 to 0.998 and F1 to 0.988.

The technical contribution is a modular, multi-logo detector and reporting pipeline with traceable frame records. The methodological contribution is a package of evaluation discipline that the numbers themselves justify: match-disjoint splitting, explicit per-class support with a restricted mean reported alongside the conventional one, cross-checking between independent evaluators, condition-stratified reporting, and example selection driven by error rules rather than by appearance. The practical contribution is an inspectable route from broadcast frames to sponsor-level evidence on consumer hardware, together with a specific account of where that route is not yet safe to use.

The aim is only partly completed. The visibility and temporal framework is implemented, including corrected quality-weighted seconds and the 30-second media-value conversion, but the final checkpoint has not been rerun across all highlight videos and has not been compared with manual timing or human readability ratings. Those quantities are not claimed as validated findings. This limitation is preferable to retaining obsolete outputs, because it tells the reader exactly what the research currently demonstrates.

## 7.2 Priority future work

The first priority is evidence completion, not a more complex model. The backend should be pinned to RF-DETR Small, resolution 896, checkpoint `rfdetr_matchsplit_r896` and the COCO category table. The thirteen currently available highlight videos should then be screened by kit domain: home-kit videos can be analysed, and away-kit videos withheld until annotated away-kit data supports them. Every report should carry model version, category hash, sampling rate and threshold.

Second, the test set needs to be large enough to answer the questions now being asked of it. Two targets follow directly from Chapter 5: the four classes with fewer than five test boxes, plus CCH with none, need deliberate frame selection - marks on the shoulder and shorts are readable only from particular angles, which the current shot-based sampler does not seek out - and wide tactical shots need over-sampling, because eight images and six boxes cannot support the operational conclusion that wide-shot recall halves.

Third, RQ2 requires a stratified human study. A sample should balance size, camera distance, blur, contrast, occlusion and correct or incorrect detections, and should include floodlit and daylight material from the same match so that lighting can be separated from the match effect identified in Section 5.5. Two raters should judge whether the brand is readable and how visible it is under a short rubric, with agreement reported using weighted kappa or an appropriate intraclass correlation. Automated features should then be evaluated against those ratings rather than assigned weights by intuition.

Fourth, RQ3 requires manual timing. Continuous appearances should be timed at native frame rate and compared with automatic estimates at 1, 2, 5 and native frames per second. Gap tolerance, minimum segment length and duration weight should be varied, and the Logo Visibility Score should report sensitivity to component removal and to alternative weights. The wide-shot recall deficit gives this work a specific hypothesis to test: automatic duration should under-estimate human timing, and the size of the gap should scale with the proportion of wide camera work in the footage. EMV should remain a separate scenario layer using sourced audience and media-rate inputs.

Further work should expand match and class support, add away-kit and additional broadcaster domains, and audit a subset of annotations independently. Oriented boxes or segmentation could improve visible-area measurement under rotation and occlusion, and Section 5.5 gives a reason to expect real gains there, but they should be adopted only after the simpler score has been validated. Open-set retrieval can be explored later for new sponsors. Adoption research through interviews or surveys with club staff should be a later study, not inferred from technical feasibility.

## 7.3 Final takeaway

Transparent computer vision can give a smaller sports club credible, frame-level evidence of sponsor-logo visibility. In this case, accurate detection on unseen home-kit matches is feasible on consumer hardware, it is measurably better than the obvious alternative architecture, and its weaknesses are specific enough to plan around. The same level of confidence cannot yet be attached to duration, human readability or monetary value. The value of LogoLens therefore lies not in presenting one authoritative percentage, but in making the measurement process, its assumptions and its remaining uncertainty visible - including where those assumptions weaken its own headline number.

---

# References

Blinkfire (n.d.) *Sponsorship data platform*. Available at: https://www.blinkfire.com/d/landing/mediaanalytics (Accessed: 11 August 2026).

Breuer, C. and Rumpf, C. (2012) 'The viewer's reception and processing of sponsorship information in sport telecasts', *Journal of Sport Management*, 26(6), pp. 521-531. https://doi.org/10.1123/jsm.26.6.521

Carion, N., Massa, F., Synnaeve, G., Usunier, N., Kirillov, A. and Zagoruyko, S. (2020) 'End-to-end object detection with transformers', in *European Conference on Computer Vision*, pp. 213-229. https://arxiv.org/abs/2005.12872

Cornwell, T.B. (2019) 'Less "sponsorship as advertising" and more sponsorship-linked marketing as authentic engagement', *Journal of Advertising*, 48(1), pp. 49-60. https://doi.org/10.1080/00913367.2019.1588809

Cornwell, T.B. and Kwon, Y. (2020) 'Sponsorship-linked marketing: research surpluses and shortages', *Journal of the Academy of Marketing Science*, 48, pp. 607-629. https://doi.org/10.1007/s11747-019-00654-w

Davenport, T., Guha, A., Grewal, D. and Bressgott, T. (2020) 'How artificial intelligence will change the future of marketing', *Journal of the Academy of Marketing Science*, 48, pp. 24-42. https://doi.org/10.1007/s11747-019-00696-0

Deliège, A., Cioppa, A., Giancola, S. et al. (2021) 'SoccerNet-v2: a dataset and benchmarks for holistic understanding of broadcast soccer videos', in *CVPR Workshops*, pp. 4508-4519. https://arxiv.org/abs/2011.13367

Department for Culture, Media and Sport (2023) *Still ill? Assessing the financial sustainability of football*. Available at: https://www.gov.uk/government/publications/reforming-club-football-governance-consultation-response/research-report-still-ill-assessing-the-financial-sustainability-of-football-2023 (Accessed: 11 August 2026).

Hevner, A.R., March, S.T., Park, J. and Ram, S. (2004) 'Design science in information systems research', *MIS Quarterly*, 28(1), pp. 75-105. https://doi.org/10.2307/25148625

Huang, M.-H. and Rust, R.T. (2021) 'A strategic framework for artificial intelligence in marketing', *Journal of the Academy of Marketing Science*, 49, pp. 30-50. https://doi.org/10.1007/s11747-020-00749-9

Liao, Y., Lu, X., Zhang, C., Wang, Y. and Tang, Z. (2017) 'Mutual enhancement for detection of multiple logos in sports videos', in *Proceedings of the IEEE International Conference on Computer Vision*, pp. 4846-4855. https://openaccess.thecvf.com/content_ICCV_2017/papers/Liao_Mutual_Enhancement_for_ICCV_2017_paper.pdf

Lin, T.-Y., Maire, M., Belongie, S. et al. (2014) 'Microsoft COCO: common objects in context', in *European Conference on Computer Vision*, pp. 740-755. https://arxiv.org/abs/1405.0312

Nielsen (2017) *Nielsen acquires artificial intelligence-powered sports marketing startup vBrand*. Available at: https://www.nielsen.com/news-center/2017/nielsen-acquires-artificial-intelligence-powered-sports-marketing-startup-vbrand/ (Accessed: 11 August 2026).

Nielsen (n.d.-a) *Sports reports: Sponsorship Media Value Benchmarking Report*. Available at: https://www.nielsen.com/marketplace/sports-reports/ (Accessed: 11 August 2026).

Nielsen (n.d.-b) *Nielsen Sports - Media Valuation*. Available at: https://content.nielsen.com/l/881703/2022-11-18/42b9x (Accessed: 11 August 2026).

Oquab, M., Darcet, T., Moutakanni, T. et al. (2023) 'DINOv2: learning robust visual features without supervision', *arXiv*. https://arxiv.org/abs/2304.07193

Redmon, J., Divvala, S., Girshick, R. and Farhadi, A. (2016) 'You only look once: unified, real-time object detection', in *Proceedings of the IEEE Conference on Computer Vision and Pattern Recognition*, pp. 779-788. https://arxiv.org/abs/1506.02640

Relo Metrics (n.d.) *Sponsorship measurement platform overview*. Available at: https://relometrics.com/sponsorship-measurement-platform (Accessed: 11 August 2026).

Robinson, I., Robicheaux, P., Popov, M., Ramanan, D. and Peri, N. (2025) 'RF-DETR: neural architecture search for real-time detection transformers', *arXiv:2511.09554*. https://arxiv.org/abs/2511.09554

Romberg, S., Pueyo, L.G., Lienhart, R. and van Zwol, R. (2011) 'Scalable logo recognition in real-world images', in *ACM International Conference on Multimedia Retrieval*, pp. 1-8. https://doi.org/10.1145/1991996.1992021

Rumpf, C., Boronczyk, F. and Breuer, C. (2020) 'Predicting consumer gaze behavior toward sponsorship stimuli in sport broadcasts', *European Sport Management Quarterly*, 20(4), pp. 461-479. https://doi.org/10.1080/16184742.2019.1620838

Su, H., Zhu, X. and Gong, S. (2018) 'Open logo detection challenge', in *British Machine Vision Conference*. https://arxiv.org/abs/1807.01964

Two Circles (2025) *Sports IP Revenue League: methodology and references*. Available at: https://twocircles.com/gb/articles/sports-ip-revenue-league-methodology-and-references/ (Accessed: 12 August 2026).

Zhang, Y., Sun, P., Jiang, Y. et al. (2022) 'ByteTrack: multi-object tracking by associating every detection box', in *European Conference on Computer Vision*, pp. 1-21. https://arxiv.org/abs/2110.06864

Zhao, Y., Lv, W., Xu, S. et al. (2024) 'DETRs beat YOLOs on real-time object detection', in *Proceedings of the IEEE/CVF Conference on Computer Vision and Pattern Recognition*, pp. 16965-16974. https://openaccess.thecvf.com/content/CVPR2024/html/Zhao_DETRs_Beat_YOLOs_on_Real-time_Object_Detection_CVPR_2024_paper.html

---

# Appendices

## Appendix A: Per-class held-out results

All values come from the corrected independent evaluation described in Section 3.3, on the 61 held-out test images. Classes are ordered by ground-truth support, because support is the column that determines how much weight each row can carry. Rows with fewer than five boxes are marked; their AP values are reported for completeness and are excluded from the restricted mean of 0.917.

| Sponsor class | Test boxes | Train boxes | AP@0.50 | AP@0.75 | AP@[.50:.95] |
| --- | ---: | ---: | ---: | ---: | ---: |
| KLG | 31 | 279 | 0.947 | 0.947 | 0.816 |
| MCP | 27 | 187 | 0.891 | 0.891 | 0.758 |
| Aon | 18 | 128 | 0.984 | 0.937 | 0.800 |
| Paints & Lacquers | 18 | 129 | 0.941 | 0.941 | 0.786 |
| Top Notch | 16 | 144 | 0.935 | 0.923 | 0.819 |
| Romantica | 13 | 109 | 0.927 | 0.927 | 0.775 |
| ASC Group | 11 | 136 | 0.941 | 0.941 | 0.725 |
| Ellgren | 7 | 77 | 0.947 | 0.947 | 0.771 |
| ATM | 6 | 113 | 0.832 | 0.832 | 0.718 |
| EM Workwear | 6 | 61 | 0.857 | 0.661 | 0.664 |
| Bartercard | 5 | 104 | 0.886 | 0.886 | 0.750 |
| *Fairway* | *3* | 65 | *0.916* | *0.916* | *0.824* |
| *MNA Cladding* | *2* | 31 | *1.000* | *1.000* | *0.800* |
| *Chadlaw* | *1* | 13 | *1.000* | *1.000* | *0.600* |
| *MNA Support Services* | *1* | 27 | *1.000* | *1.000* | *0.600* |
| *CCH* | *0* | 8 | *not measurable* | — | — |
| **Mean, all 15 represented classes** | **165** | | **0.9335** | **0.9166** | **0.7471** |
| **Mean, 11 classes with n ≥ 5** | **158** | | **0.9169** | | |

The three classes scoring AP@0.50 of 1.000 illustrate the mechanism described in Section 5.3. Chadlaw and MNA Support Services each rest on a single box, and their AP@[0.50:0.95] of exactly 0.600 is the arithmetic of one box matching at six of ten IoU thresholds rather than a measure of localisation quality.

Two housekeeping notes belong with this table. First, per-class values differ from those printed in version 15 by at most 0.026, and for eleven of the fifteen classes they are identical to three decimal places; the differences arise from the corrected maximum-detections setting and from the inference-optimisation path, as recorded in Table 8. Bartercard moves from 0.860 to 0.886 and is the largest single change. Second, the train-box column is included because Section 5.1 uses it: read down the two rightmost columns together and the absence of a relationship between training volume and held-out accuracy is visible without the scatter plot.

## Appendix B: Required experiments before submission

1. Pin the backend to RF-DETR Small, resolution 896, confidence 0.35, the final checkpoint and the COCO category mapping.
2. Select the operating threshold on validation data and repeat one untouched test evaluation, so that a threshold-specific F1 can be reported as an estimate rather than a characterisation.
3. Collect away-kit training data and implement a domain gate that flags out-of-domain footage before analysing away matches.
4. Add targeted frames for CCH, Chadlaw, MNA Support Services and MNA Cladding, selected for shoulder and shorts visibility rather than by generic shot sampling.
5. Over-sample wide tactical camera work, so that the wide-shot recall deficit rests on more than six boxes.
6. Rerun all in-domain highlight videos and create one video-level summary table.
7. Manually time a stratified sample at native frame rate; test sampling rates and gap rules against it.
8. Collect two-rater readability scores across size, blur, contrast and occlusion groups, including floodlit and daylight material from the same match.
9. Perform component-removal and weight-sensitivity tests for the Logo Visibility Score.
10. Audit a random subset of annotations independently, since annotation-boundary bias bears directly on the mAP@0.75 claim.

## Appendix C: Architecture comparison protocol

The comparison in Section 5.4 was run as follows. YOLO26 nano, small and medium checkpoints were trained by `scripts/train_yolo26.py` on `datasets/yolo_matchsplit`, which is generated from the same COCO dataset used by RF-DETR through `scripts/coco_to_yolo.py`, preserving the match-disjoint assignment exactly. All runs used an input size of 896 rather than the YOLO default of 640, so that input geometry - the dominant variable identified in Section 5.1 - was equal across families. Early stopping used a patience of 30 over a maximum of 150 epochs.

Scoring did not use either framework's internal validation metric. All four models were re-run over the same 61 test images at a confidence floor of 0.01, and the resulting detections were scored by one pycocotools configuration and one greedy IoU-0.50 confidence sweep. Class indices were mapped back from the YOLO ordering to the COCO category identifiers so that both families were compared against identical ground truth.

Held constant: images, split, input resolution, evaluation code, IoU matching rule, confidence floor, hardware. Not held constant, and stated wherever the result is used: augmentation recipe (Ultralytics applies mosaic, mixup, HSV jitter and copy-paste by default) and pre-training corpus and parameter count.

## Appendix D: Legacy full-run file register

These workbooks are retained for provenance and must not be cited as final RF-DETR outputs.

| File | Kit label | Analysed at | Status |
| --- | --- | --- | --- |
| M02_white_1440p_full_highlight_locations.xlsx | Home white | 24 June 2026 07:01 UTC | Legacy pipeline |
| M03_black_1080p_full_highlight_locations.xlsx | Away black | 24 June 2026 07:40 UTC | Legacy; outside final home-kit domain |
| M04_black_1080p_full_highlight_locations.xlsx | Away black | 24 June 2026 07:57 UTC | Legacy; outside final home-kit domain |
| M05_white_1080p_full_highlight_locations.xlsx | Home white | 24 June 2026 08:09 UTC | Legacy pipeline |
| M06_black_1080p_full_highlight_locations.xlsx | Away black | 24 June 2026 08:22 UTC | Legacy; outside final home-kit domain |
| M07_white_1080p_full_highlight_locations.xlsx | Home white | 24 June 2026 08:35 UTC | Legacy pipeline |
| M08_white_1080p_full_highlight_locations.xlsx | Home white | 24 June 2026 08:46 UTC | Legacy pipeline |
| M11_black_1080p_full_highlight_locations.xlsx | Away black | 24 June 2026 09:00 UTC | Legacy; outside final home-kit domain |

## Appendix E: Figure provenance and AI disclosure

Figure 1 was generated as a conceptual infographic with OpenAI ImageGen and then revised to remove text, values and promotional claims. Final edit prompt:

> Edit this academic infographic into a cleaner conceptual figure. Preserve the left-to-right story and the maroon/charcoal/gold vector style, but remove every word, number, percentage, timestamp, brand-like mark, and unsupported claim. Remove the entire bottom promotional banner. Simplify the right-hand analytics panels to unlabeled visual symbols only: a neutral timeline with dots, a gauge without a number, and small neutral bar-chart/report icons without numeric values. Simplify the centre lower pipeline into four unlabeled icon boxes connected by arrows: video frames, detection boxes, visibility measurement, report. Keep the generic rugby stadium, generic jersey and match frame, but no real team identity and no real sponsor logos. Make the composition wide 16:9, clean, balanced, spacious, and suitable as a figure in a Master's dissertation. Absolutely no text or digits anywhere.

Figures 2 to 5 and 7 are diagrams and charts generated deterministically from the recorded design and experiment values, and are carried forward unchanged from version 15. Figures 6, 8, 9, 10, 11 and 12 were produced for this version by `dissertation/make_figures_v16.py` from the JSON measurement files in `dissertation/v16_data/`; every plotted value can be traced to a recorded evaluation run. Figure 13 was produced by running the final checkpoint over the held-out test images and applying the selection rules documented in Section 3.3.

## Appendix F: Repository evidence used for version 16

- Final checkpoint: `runs/rfdetr_matchsplit_r896/checkpoint_best_total.pth`
- Training configuration: `runs/rfdetr_matchsplit_r896/training_config.json`
- Training metrics: `runs/rfdetr_matchsplit_r896/metrics.csv`
- Dataset: `datasets/auto_label_white_matchsplit`
- YOLO26 baselines: `runs/yolo26/matchsplit_896`, `matchsplit_896_s`, `matchsplit_896_m`, with training and scoring logs in `runs/yolo26{n,s,m}_matchsplit.log`
- Independent evaluator: `scripts/eval_rfdetr_coco.py`
- Per-class diagnostic: `scripts/explain_class_metrics.py`
- Measurement files behind every chart: `dissertation/v16_data/*.json`
- Figure generator: `dissertation/make_figures_v16.py`
- Optimisation record: `docs/11-map-optimisation.md`
- RF-DETR pipeline record: `docs/10-rfdetr-pipeline.md`

<!-- End of LogoLens MSc Dissertation version 16 -->
