<!--
Version 15: restructured from the supervisor-aligned outline and updated for the
match-disjoint RF-DETR optimisation completed in August 2026. The Word and
Markdown sources for version 14 remain unchanged.

Evidence rule used in this draft:
- figures reported as results must be reproducible from the current repository;
- legacy June 2026 full-video spreadsheets are not treated as RF-DETR results;
- incomplete readability and duration-validation studies are stated explicitly;
- team attribution, body segmentation and kit-location pricing are outside scope.
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

I declare that this dissertation is my own work and has not been submitted, in whole or in part, for another degree or qualification. All external sources are acknowledged. Third-party models, libraries and services are identified where they are discussed. Artificial-intelligence assistance used to produce the conceptual infographic in Figure 1 is disclosed in Appendix D; all quantitative charts were generated from project data and were checked against the recorded experiment outputs.

## Abstract

Sports clubs need credible evidence that sponsor logos were visible in broadcast and highlight footage, but exposure is difficult to measure when marks are small, distorted by fabric, partly hidden and present in several locations at once. Commercial sponsorship-analytics services demonstrate that automated logo tracking is already feasible, including for marks on players. Their methods, costs and evaluation data are not normally transparent, however, which limits what a smaller club can reproduce locally. This dissertation develops and evaluates LogoLens, a computer-vision framework for detecting a known roster of Bradford Bulls sponsor logos and converting detections into traceable measures of visibility quality and duration. The contribution is measurement rather than pricing: visibility is kept separate from audience attention, return on investment and sponsorship revenue.

The study follows a design-science approach with a quantitative single-club case evaluation. The final dataset contains 584 images and 1,903 annotated boxes across 16 sponsor classes drawn from 15 disjoint match groups (14 named groups plus one legacy source group). Matches, rather than neighbouring frames, form the units of the train, validation and test split. RF-DETR Small was fine-tuned on native-aspect broadcast frames at an input resolution of 896 pixels. On 61 images and 165 boxes from three unseen held-out matches, an independently repeated evaluation produced mAP@0.50 of 0.932 and mAP@0.75 of 0.915. The training evaluator reported mAP@[0.50:0.95] of 0.744. A confidence sweep produced a best F1 of 0.895 at a threshold of 0.35 (precision 0.912; recall 0.879). Inference over the same images averaged 50.5 ms per image, or 19.8 frames per second, on an RTX 5060 Ti 16 GB GPU, excluding file-system and video-decoding costs.

The experiments show that input geometry and match diversity matter strongly. Letterboxing a 1208 × 1280 frame made approximately 47% of the input black, while native-frame training at 896 increased the effective median logo area by about 3.7 times relative to the original pipeline. Evaluation on familiar match material gave mAP@0.50 of 0.998 and F1 of 0.988, illustrating why frame-level leakage would overstate generalisation. Performance was high across the measured classes, but rare-class estimates with one to three test boxes were too unstable for strong claims. The implemented visibility framework combines size, screen position, detector confidence and temporal segments into quality-weighted seconds. Nevertheless, the new detector has not yet been re-run and manually timed across the complete highlight-video set, and a planned human-readability study remains incomplete. The dissertation therefore supports the feasibility of accurate closed-set logo detection on consumer hardware, while treating duration accuracy and the final Logo Visibility Score as implemented but not yet fully validated outcomes.

**Keywords:** computer vision; logo detection; RF-DETR; small-object detection; sports sponsorship; visibility measurement; design science.

## Acknowledgements

I thank my supervisor for guidance on narrowing the dissertation towards the computer-vision and model-development work package. I am grateful to Bradford Bulls for the applied case context and to the open-source communities supporting RF-DETR, PyTorch, DINOv2 and the associated evaluation tools. I also thank my family for their support throughout the project.

## List of Abbreviations

| Abbreviation | Meaning |
| --- | --- |
| AP / mAP | Average Precision / mean Average Precision |
| COCO | Common Objects in Context evaluation convention |
| CPM | Cost per thousand impressions |
| DETR | Detection Transformer |
| EMV | Equivalent Media Value |
| F1 | Harmonic mean of precision and recall |
| FPS | Frames per second |
| GPU | Graphics Processing Unit |
| IoU | Intersection over Union |
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
6. Optimisation trajectory and inference-resolution experiment.
7. Per-class AP@50 with test support.
8. Held-out success and error examples selected by predefined rules.

## List of Tables

1. Research questions and evidence required.
2. Selected literature and its relevance to this study.
3. Final match-disjoint dataset.
4. Final RF-DETR configuration and reproducibility details.
5. Optimisation stages and their evaluation protocols.
6. Final held-out test results.
7. Research-question conclusions and evidence limits.

---

---

# Chapter 1: Introduction

## 1.1 Sponsorship, association and the record it leaves behind

**Sponsorship is a commercial agreement in which an organisation pays a rights holder - a club, a competition, an event or an individual - for the right to associate itself with that property and to receive an agreed package of promotional benefits.** What separates it from advertising is not the size of the cheque but the nature of what is bought. An advertiser buys space and controls the message; a sponsor buys association, and accepts that the message will be carried by someone else's activity, audience and reputation. Cornwell (2019) argues that the field is better understood as sponsorship-linked marketing, in which value arises from authentic engagement with an audience rather than from the repetition of a claim.

That is precisely what makes sponsorship attractive, and precisely what makes it difficult to account for. The association reaches people inside content they have chosen to watch rather than in an interruption they may avoid, and it borrows an emotional attachment the audience already holds. But an association is diffuse in a way that a purchased advertising slot is not, and the agreements reflect this: naming rights, branding on kit and venue signage, exposure during broadcast and highlights coverage, hospitality, digital content and community programmes are bundled together and priced as a whole. For the rights holder the same agreement is not a marketing activity at all but a revenue stream, and commercial income of this kind is a material component of financial sustainability rather than a discretionary extra (Department for Culture, Media and Sport, 2023).

The sums exchanged on this basis are considerable. Two Circles (2025) estimates that organisations owning sports intellectual property generated approximately US$174 billion in annualised revenue in 2025, with sponsorship rights among the principal routes by which that value is realised. `[TODO: bo sung mot so lieu ve rieng chi tieu sponsorship toan cau + nguon da kiem chung]` Sport commands a disproportionate share of such spending for structural reasons: sporting events are consumed live and at scale, they generate repeated rather than one-off contact, and they attach a brand to a relationship that is emotional, habitual and geographically identifiable.

Sport also has one further property, less often remarked upon, that matters more to this dissertation than any of the others. It leaves a complete visual record of itself. Every match that is broadcast, streamed or cut into highlights is a permanent account of which sponsor marks appeared, when, for how long and how clearly. The evidence that would settle what a sponsorship actually delivered is therefore produced automatically, as a by-product of the sport being watched.

## 1.2 The measurement gap

That evidence is almost never used. Sponsorship continues to be priced on precedent and professional judgement: what a comparable property charged last season, adjusted by negotiation, relationship history and the commercial confidence of the parties. Inventory is described in terms of what is offered - a shirt position, a number of perimeter rotations, a package of hospitality - rather than in terms of what an audience demonstrably saw. Post-season reporting is typically a presentation assembled from selected examples, aggregate audience figures and the experience of the people who produced it.

The gap this leaves is specific rather than general. What is invoiced is a position on a shirt; what is delivered is visibility, and the two are not the same thing. The same nominal position yields a mark that is large and legible when a player is the subject of a close-up, and a few indistinct pixels when play moves to the far touchline; it disappears in a tackle, blurs when the camera pans, and appears far more often for a player who happens to be involved in the passages that broadcasters choose to show. Two clubs charging the same price for the same position may therefore deliver materially different value, and under current practice neither they nor their sponsors have any independent means of telling. Cornwell and Kwon (2020), reviewing sponsorship-linked marketing research, identify persistent shortages in precisely this area of measurement and accountability.

Being exact about the target matters here, because the claim is narrower than it may first appear. Visibility is not attention, recall, brand attitude or sales; research on how viewers process sponsorship stimuli in broadcast sport shows that response depends on the conditions of exposure and on the viewer's involvement, not merely on whether a mark was present (Breuer and Rumpf, 2012; Rumpf et al., 2020). What can be said is firmer for being narrower: visibility is the first link in that chain and the only one that can be observed directly rather than inferred, so everything inferred from it inherits whatever error it contains.

Where the money is largest, the market has already responded. Nielsen describes a valuation process combining automated detection, human analysts, quality-weighted exposure and media rates (Nielsen, n.d.-a; Nielsen, 2017), and Relo Metrics and Blinkfire offer comparable platforms (Relo Metrics, n.d.; Blinkfire, n.d.). Their existence confirms both that the problem is real and that it is tractable. It does not make it solved for most rights holders. These services are specified and priced for major properties, and their methods are proprietary: the club receiving the report cannot see how a figure was produced or check it against the footage. The organisations least able to absorb a mispriced sponsorship are thus the ones still negotiating on assertion.

## 1.3 From judgement to evidence

The obstacle, then, has never been the absence of evidence. As the previous sections have set out, the footage already contains a complete account of what appeared on screen; what has been missing is an affordable way to examine it. That work has traditionally meant a person watching a match in real time, producing judgements that differ between reviewers and cannot be re-checked without repeating the effort from the beginning.

Automation changes that cost, and this is where artificial intelligence enters the argument - though not in its most discussed form. Work on AI in marketing has concentrated on prediction, personalisation and content generation (Davenport et al., 2020; Huang and Rust, 2021). The application here is more modest and more immediately tractable: not deciding what a customer will do, but observing reliably what has already happened. Computer vision suits the task because the record is visual and highly repetitive, and because once the examination is automated the same footage can be re-examined indefinitely at negligible additional cost.

The commercial consequence is not primarily speed. It is that a claim about visibility can be traced back to the moments of footage that produced it, which is what turns a number into an argument a sponsor is able to check. That, in turn, sets a condition on any system built for this purpose: accuracy alone is insufficient if the resulting figure cannot be inspected, because an unverifiable number simply reproduces the limitation of the proprietary platforms it was meant to replace. The same discipline applies in the other direction, since a measure that quietly overstates its own reach is no more useful than one that cannot be checked at all.

## 1.4 Aim, research questions and contribution

Two questions follow from the preceding argument. Can sponsor visibility be measured automatically and accurately enough to be commercially useful? And can it be measured transparently and cheaply enough to be usable by an organisation that has neither a specialist technical team nor an enterprise contract?

This dissertation addresses both, using a professional rugby league club, Bradford Bulls, as its case study. Rugby league is a demanding but representative setting: sponsor marks appear on moving players as well as on static signage, several sponsors compete for attention within a single frame, and the club operates under exactly the resource constraints that make the second question worth asking.

The **aim** is to develop and evaluate a system that identifies multiple known sponsor logos in sports-broadcast footage and measures the quality and duration of their visibility.

The study has three objectives:

1. Develop and evaluate a multi-logo detection capability on footage from matches the system has not previously encountered.
2. Examine how the conditions of appearance - size, screen coverage, blur, contrast and occlusion - affect both automated detection and human readability.
3. Estimate the duration of sponsor visibility and combine transparent, frame-level evidence into an interpretable Logo Visibility Score.

The corresponding research questions are:

- **RQ1:** How accurately and efficiently can the system identify multiple known sponsor logos in unseen sports footage?
- **RQ2:** How do logo size, screen coverage, blur, contrast and occlusion affect detection performance and human readability?
- **RQ3:** How accurately can frame-level detections estimate visibility duration and support an interpretable Logo Visibility Score?

Answering them is intended to contribute on three fronts. The first is evidence on feasibility: whether automated sponsor-visibility measurement can be achieved outside a commercial vendor relationship, with resources available to a small technical team. The second is a visibility measure designed to be interpretable by a commercial audience, in the sense established above - every summary figure resolvable to the footage behind it, and every assumption stated rather than embedded. The third is a candid account of the limits, so that a club adopting this approach knows what the resulting numbers will and will not support in a negotiation.

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

Modern object detection is dominated by convolutional one-stage detectors and transformer-based detectors. YOLO framed detection as a fast, single-pass prediction problem (Redmon et al., 2016), and current implementations remain attractive for deployment. DETR replaced anchors and non-maximum suppression with set prediction and bipartite matching (Carion et al., 2020). Later work improved convergence and real-time performance. RT-DETR introduced an efficient hybrid encoder and flexible decoder depth, reporting a competitive speed-accuracy trade-off on standard benchmarks (Zhao et al., 2024). RF-DETR is a specialist real-time detection transformer with a DINOv2-based visual backbone and model variants intended to occupy different points on the accuracy-latency curve (Robinson et al., 2025). Standard-benchmark rankings cannot determine the best model for jersey logos; local data, resolution and evaluation design remain decisive.

Small objects are the central technical constraint. A mark with median dimensions 71 × 50 pixels in the original broadcast becomes approximately 16 pixels across one dimension after aggressive resizing. The DINOv2-style patch size used by the final RF-DETR configuration is 16 × 16 pixels, so a very small mark may occupy approximately one token row. Information lost during resizing cannot be recovered by a better confidence threshold. Letterboxing can make this worse: preserving aspect ratio inside a square canvas adds unused pixels, so fewer model pixels represent the logo. Multi-scale features, high input resolution, native-frame preprocessing and diverse close, medium and wide shots are therefore substantive design choices rather than cosmetic tuning.

Evaluation uses precision, recall and Average Precision. A prediction is usually matched to a ground-truth box when class labels agree and IoU exceeds a threshold. AP@0.50 tolerates more localisation error than AP@0.75, while COCO-style mAP@[0.50:0.95] averages across increasingly strict thresholds (Lin et al., 2014). For a box only 33 pixels wide, a few pixels of displacement can change IoU substantially. Reporting both AP@0.50 and stricter metrics is essential because a broad box may be adequate for presence detection but weak for screen-coverage measurement.

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
| Temporal aggregation | Tracking and gap rules can form exposure segments | Duration estimates need manual timing validation |
| Composite visibility scores | Size, quality and duration are plausible components | Weights can appear objective without human or sensitivity validation |

*Table 2. Synthesis of selected literature and its relevance to the study.*

Within the literature reviewed, no study was identified that documents the same combination of a match-disjoint, club-specific multi-logo detector; transparent small-logo preprocessing analysis; frame-traceable visibility measurement; manual duration validation; and an explicit smaller-club accessibility focus. This wording does not claim that no commercial or academic system performs these functions. It states the narrower gap found in the reviewed evidence.

The study uses design science because it builds and evaluates an artefact intended to address a practical problem (Hevner et al., 2004). The evaluation is a quantitative case study because the artefact is tested in one real club context. Figure 1 presents the research logic: a sponsorship evidence need motivates a computer-vision pipeline, which produces traceable visibility information for local review. Figure 2 narrows that logic into the technical workflow. Technology acceptance is not used because no adoption survey or staff-interview dataset was collected.

![Figure 1. Research framework](LogoLens_MSc_Dissertation_v15_media/figure_01_research_framework.png)

*Figure 1. Conceptual research framework: sponsorship need, broadcast computer vision and transparent evidence outputs for a smaller-club context. The graphic is conceptual and contains no measured values.*

![Figure 2. Technical workflow](LogoLens_MSc_Dissertation_v15_media/figure_02_technical_workflow.png)

*Figure 2. Leakage-aware data and model-development workflow. Match separation and validation-only model selection are part of the design rather than post-hoc corrections.*

---

# Chapter 3: Research Methodology

## 3.1 Research design and case study

The research combines design science with a quantitative case-study evaluation. Design science is appropriate because the principal output is an artefact: a working pipeline that transforms broadcast video into detection and visibility records. The process was iterative. Data problems were observed, alternative preprocessing and resolutions were tested, the split was redesigned around matches, and the resulting checkpoint was evaluated on material excluded from development. The case-study element keeps the artefact connected to a real sponsor roster and real broadcast conditions instead of an artificial collection of isolated logo images.

Bradford Bulls provides a useful case because the club has multiple sponsors on one kit and a mixture of close-up, medium and wide broadcast shots. The case is not treated as representative of every sport. Rugby contact creates particular occlusion and deformation patterns; highlight editing changes the distribution of shots; and the white home kit differs from darker or patterned kits. The value of the case is analytical depth and operational realism, not statistical representativeness.

The unit of independence is the match. This decision changed the evaluation materially. The original 30 apparent “clips” were drawn from one approximately 11.5-minute source video. Twenty-one of 22 clips occurred in both training and validation, 15 of 16 occurred in both training and test, and 51 of 56 validation frames had a training frame from the same clip within two seconds. A random image split therefore measured recognition of familiar scenes more than generalisation. The final design assigns complete matches to one split only.

The evidence plan follows the research questions. RQ1 uses held-out detection metrics, class support, resolution experiments, a familiar-versus-unseen comparison and an inference benchmark. RQ2 uses object-size analysis, camera-condition examples and, in the complete design, stratified blur, contrast and occlusion groups plus human readability ratings. RQ3 uses the implemented temporal algorithm and, in the complete design, manual start/end timing under alternative sampling and gap settings. Version 15 reports the completed evidence and identifies the two incomplete validation packages rather than replacing them with implementation output.

## 3.2 Data preparation and model-development strategy

The final dataset contains 15 disjoint match groups: 14 named groups and one legacy source group whose frames remain together in training. Shot-aware sampling was used to reduce near-duplicate material. Candidate shots were represented with DINOv2 embeddings, clustered, and reduced to a representative frame per shot. This process aimed to add different camera views rather than more adjacent frames. A flat-region heuristic was tested but discarded because broadcast graphics also contain flat regions. A brightness-only lighting heuristic was also rejected: the floodlit white jersey differed in both value and saturation from the daytime preset, and manual lighting metadata was more reliable.

Annotations use horizontal bounding boxes around visible sponsor marks. The category table contains a placeholder plus 16 sponsor classes used by the final home-kit checkpoint. The train, validation and test totals are shown in Table 3. The split script identifies nine training, three validation and three test match groups, with no group shared across splits. The label `OLD` represents the legacy source group rather than an additional named match identifier. No frame from a test match was used to choose the checkpoint.

| Split | Match assignments | Images | Annotated boxes | Role |
| --- | ---: | ---: | ---: | --- |
| Train | 9 | 460 | 1,611 | Weight optimisation and augmentation |
| Validation | 3 | 63 | 127 | Checkpoint selection and stopping |
| Test | 3 | 61 | 165 | Final held-out evaluation only |
| **Total** | **15 disjoint match groups** | **584** | **1,903** | **16 measured sponsor classes** |

*Table 3. Final match-disjoint dataset. One test class (CCH) has no boxes, so test mAP is calculated over 15 represented classes.*

The source frames retain their native 1920 × 1080 or 2560 × 1440 geometry rather than being pre-letterboxed into a mostly square image. Median logo dimensions in the original material are approximately 71 × 50 pixels. At a 512-pixel model input the median mark is approximately 16 pixels in one dimension, and between 86% and 95% of boxes fall into a COCO-small category depending on the precise export. Approximately half fall below 16 pixels. These distributions motivated higher-resolution training.

RF-DETR Small was chosen for the final optimisation. The model uses a DINOv2-based windowed backbone, detection-transformer queries and set-based prediction. Training used AdamW, automatic mixed precision, exponential moving averages, a three-epoch warm-up, cosine learning-rate decay and early stopping. Augmentation included horizontal flips, small rotations, brightness/gamma variation, blur, motion blur and coarse dropout. These augmentations increase robustness but do not substitute for a condition-specific test.

Model development proceeded through five recorded runs. Runs 1–4 were useful diagnostics but used leaky image-level validation and cannot be compared as independent generalisation estimates with Run 5. The final run used match-disjoint data and resolution 896. The model reached its best validation point at epoch 36 and stopped after epoch 51 of a planned 60 because the early-stopping criterion was met. Training took approximately 2.5 hours on the target GPU.

## 3.3 Evaluation, ethics and reproducibility

Precision is the proportion of accepted predictions that match ground truth; recall is the proportion of ground-truth boxes detected. F1 balances the two. AP integrates precision and recall across confidence thresholds, while mAP averages over represented classes. The independent final evaluation retains predictions at a low confidence to build a precision-recall sweep, matches predictions at IoU 0.50 and reports the threshold with the highest F1. AP@0.50, AP@0.75 and COCO-style mAP@[0.50:0.95] are all reported because they answer different localisation questions.

Per-class AP is accompanied by ground-truth support. An AP of 1.000 based on one box is not evidence of general reliability. The test set contains no CCH box, and three other classes have one or two boxes. Those classes remain in the trained roster but cannot support a stable test conclusion. The overall test set is also modest: 61 images and 165 boxes from three matches. The dissertation uses three decimal places to reproduce experiment outputs, not to imply population-level precision.

Inference efficiency was benchmarked after three warm-up images over all 61 test images. CUDA synchronisation was applied around each prediction. The result includes model prediction but excludes video decoding, disk output, tracking, frontend rendering and process start-up. Peak GPU memory is PyTorch's allocated memory during the timed loop, not total system VRAM. These boundaries are necessary for a meaningful accessibility claim.

Qualitative examples were also selected reproducibly. At confidence 0.35 and IoU 0.50, the “clear success” is the perfect frame with the strongest maximum confidence; the multi-logo panel is the remaining frame with the best matched-object count; the difficult miss is the frame containing the smallest missed ground-truth box; and the false-positive panel contains the highest-confidence unmatched prediction. This prevents visually attractive examples from being presented as if they were random evidence.

The footage is used for model research and contains visible trademarks and players. The study does not identify individuals or infer sensitive personal attributes. Frames are reproduced only where required to show detector behaviour. Sponsor names can be shown because the task is class recognition, but contractual amounts, sponsor charges and club comparisons are not disclosed. The “Human %” column in legacy spreadsheets is treated as commercially supplied weighting rather than participant data or model truth.

Reproducibility records include the dataset manifest, checkpoint, training configuration, random seed, package environment and result files. The final run uses RF-DETR 1.9.1, PyTorch 2.11 with CUDA 12.8 and an RTX 5060 Ti 16 GB. The independent evaluation in this revision was executed from `.venv-rfdetr`; the older Conda environments remain relevant to the application but are not the authority for the final checkpoint. The dataset was annotated and corrected principally by one researcher. Model-assisted pre-annotation was used on 304 of 584 images before manual correction, which can introduce annotation-style bias. A second independent annotation audit would strengthen the evidence.

![Figure 3. Split and leakage](LogoLens_MSc_Dissertation_v15_media/figure_03_split_and_leakage.png)

*Figure 3. Dataset design and the effect of temporal leakage. The familiar-material result is deliberately shown as an inflation diagnostic, not as a second test score.*

---

# Chapter 4: Model and System Development

## 4.1 System architecture and logo detection

LogoLens separates model inference from reporting. The backend ingests video, reads frame metadata, samples frames, runs the selected detector and stores a common detection record. The Logo Analytics frontend presents processed videos, brand summaries and exports. This separation allows the detector to change without rewriting the reporting interface, provided every backend returns the same core fields: class, confidence, bounding box, frame index and timestamp.

![Figure 4. System architecture](LogoLens_MSc_Dissertation_v15_media/figure_04_system_architecture.png)

*Figure 4. System architecture and evidence flow. Optional player, team and body-analysis components found elsewhere in the codebase are outside the dissertation scope.*

The current checkpoint is RF-DETR Small with resolution 896. Native-aspect frames are supplied to the model, which performs the configured internal resizing. The output is a set of predicted class identifiers, confidences and horizontal boxes. Because DETR uses set prediction, it does not rely on the same non-maximum-suppression stage as a conventional YOLO detector. Several sponsor marks can be returned from one frame, including repeated instances of one class.

The confidence threshold is 0.35 for the final test operating point. This value was identified by the recorded sweep and balances precision and recall on the evaluation output. In a strict deployment, the threshold should be selected using validation data and then locked before the final test. Because the repository's independent sweep was run on the test predictions to characterise the completed checkpoint, the threshold-specific F1 is best viewed as a post-hoc operating-point estimate; the threshold-free AP measures remain the stronger final metrics. A future rerun should select 0.35 on validation and report one untouched test F1.

Class mapping is a critical engineering detail. The training COCO file contains a placeholder category followed by home-kit sponsor classes. The standalone detector reads the category table directly. The older backend configuration contains a different 17-brand order, including an away-kit sponsor and a spelling difference in ASC Group. It also defaults to an RF-DETR Large path. Running the optimised Small checkpoint through that configuration without correction could shift brand labels even when boxes are visually correct. For this reason, the June full-video exports are not presented as final RF-DETR results. The model service must be pinned to the final checkpoint, variant, resolution and category mapping before batch analysis is repeated.

| Item | Final value | Reproducibility note |
| --- | --- | --- |
| Model | RF-DETR Small | Fine-tuned specialist detector |
| Backbone | DINOv2 windowed small | Patch size 16 |
| Input resolution | 896 | Native-aspect source frames |
| Classes | 16 sponsor classes | CCH absent from test ground truth |
| Optimiser | AdamW | Base LR 0.0001; encoder LR 0.00015 |
| Effective batch | 16 | Batch 2 × gradient accumulation 8 |
| Schedule | 3-epoch warm-up + cosine decay | Early stopping patience 15 |
| Augmentation | flip, rotate, brightness/gamma, blur, motion blur, dropout | CPU augmentation backend |
| Model-selection epoch | 36 | Stopped at epoch 51 |
| Hardware | RTX 5060 Ti 16 GB | PyTorch 2.11 + CUDA 12.8 |
| Checkpoint | `runs/rfdetr_matchsplit_r896/checkpoint_best_total.pth` | Repository-relative path |

*Table 4. Final model configuration and reproducibility details.*

## 4.2 Visibility quality and duration measurement

Each detection is converted into explicit frame-level measures. Let \(A_i\) be the predicted box area for detection \(i\), \(A_f\) the frame area, \(d_i\) the Euclidean distance between the box centre and the frame centre, \(W\) the frame width, and \(c_i\) the detector confidence. The implemented visibility proxy is

\[
V_i = \sqrt{\frac{A_i}{A_f}} \times \exp\left[-\frac{d_i^2}{(0.3W)^2}\right] \times c_i \times P_{OBB}.
\]

The square-root size term prevents a very large box from dominating linearly. The Gaussian position term assigns the highest value at the centre and reduces it towards the edges. Confidence is used as a clarity proxy. \(P_{OBB}\) is currently fixed at 1.0 because the detector predicts ordinary horizontal boxes; it does not presently measure rotation or perspective distortion. Values are clipped to [0, 1].

This formula is transparent but not yet a validated human-perception model. Size and box centre are direct geometric measurements. Confidence is a model output, not an independent sharpness measurement. The position term is a design assumption, and OBB penalty is inactive. Blur, contrast and occlusion are named in RQ2 because they matter theoretically, but the current score does not yet contain validated components for them. Adding unvalidated factors would make the score look richer while making its meaning less defensible.

Temporal aggregation groups detections by brand and track. At sampling rate \(f_s\), one sample represents \(\Delta t=1/f_s\) seconds. Detections below a visibility floor of 0.02 are excluded. A gap larger than 2.5 sampling intervals splits the run into two segments. Segment end is extended by one interval because a sampled frame represents an interval rather than an instant. Runs shorter than 0.5 seconds are removed as flicker. The current duration weight is 0.5 below one second, 1.0 from one to five seconds and 1.2 above five seconds. Quality-weighted exposure for a brand is

\[
Q = \sum_{s=1}^{S} \bar{V}_s \times w_s \times T_s,
\]

where \(\bar{V}_s\) is mean frame visibility in segment \(s\), \(w_s\) its duration weight and \(T_s\) its estimated duration. Raw on-screen seconds must be reported alongside \(Q\), because the weighted number is otherwise difficult to interpret.

![Figure 5. Visibility aggregation](LogoLens_MSc_Dissertation_v15_media/figure_05_visibility_aggregation.png)

*Figure 5. Frame-level visibility and temporal aggregation. The diagram describes the implemented algorithm; it is not evidence that the score agrees with human judgement.*

## 4.3 Logo Visibility Score and system outputs

The term **Logo Visibility Score** is used for a normalised reporting layer over measured exposure, not as a price. A defensible report contains four linked outputs: frame-level detections, continuous exposure segments, raw visible time and quality-weighted time. A video-level normalisation can express one brand's quality-weighted seconds as a share of total measured quality exposure, but the denominator must be stated. A score of 20% may mean 20% of detected quality exposure in one video; it does not mean that a sponsor delivered 20% of contract value.

The existing code also supports an illustrative EMV conversion. It is kept outside the core score for three reasons. First, audience and advertising-rate inputs are external to computer vision. Second, placement multipliers require market or expert justification. Third, sponsorship includes benefits not captured by broadcast equivalence. If the optional calculation is shown, every scenario input should be printed next to the output and the 30-second conversion must be applied. The result should be labelled “illustrative media-value estimate”, never “revenue”, “charge” or “ground truth”.

Outputs are traceable. Each brand record links to segments, and every segment derives from detections with timestamps and source frames. A reviewer can therefore inspect why a logo received exposure rather than accepting a dashboard percentage as an unexplained score. This is the system's most defensible practical advantage: transparency can be evaluated even before a full economic valuation is attempted.

Deployment evidence is promising but bounded. The timed RF-DETR pass averaged 50.5 ms per image, a median of 48.1 ms and a 95th-percentile time of 67.7 ms, corresponding to 19.8 prediction FPS on the target GPU. PyTorch peak allocated memory during the loop was 0.37 GiB after the model had been loaded and optimised; this is not total application VRAM. At an analytics rate of 2 sampled frames per second, detector inference alone has substantial headroom. Full pipeline speed will be lower once decoding, tracking, persistence and report generation are included.

Current system limits are explicit: a fixed class roster, home-kit training, horizontal boxes, a confidence-based clarity proxy, unvalidated duration weights and a backend configuration that must be aligned with the final checkpoint. These are constraints to test, not details to hide behind the frontend.

---

# Chapter 5: Experiments and Results

## 5.1 Dataset summary and model performance

The final experiment is the first run in this project evaluated on complete unseen matches. Its 584 images contain 1,903 annotated boxes across 16 sponsor classes. The training set contains 460 images and 1,611 boxes, while the held-out test contains 61 images and 165 boxes. Median source-logo size is approximately 71 × 50 pixels. When the earlier pipeline reduced images to 512, roughly half of the marks fell below 16 pixels and most met the COCO-small definition. The model therefore had to solve recognition and precise localisation from a small visual signal.

Table 5 records the optimisation path. It is tempting to describe the increase from 0.816 to 0.932 as a single controlled improvement, but the evaluation protocol changed. Runs 1–4 used image-level splits with temporal leakage; Run 5 used unseen matches. The table is evidence about engineering decisions, not a fair leaderboard. The most informative controlled sub-experiment is the resolution sweep with one fixed checkpoint: raising inference resolution from 512 to 768 increased mAP@0.50 from 0.776 to 0.880. At 896 the result remained 0.878 and F1 fell from 0.827 to 0.802, showing that resolution has diminishing returns when the training resolution is fixed.

| Stage | Data and geometry | Evaluation protocol | mAP@0.50 | mAP@[.50:.95] | Best F1 |
| --- | --- | --- | ---: | ---: | ---: |
| Hosted baseline | Letterbox; input 640 | Leaky image split | 0.906 | not recorded | 0.858 |
| Run 1 | 196 images; letterbox; 512 | Leaky image split | 0.816 | 0.429 | 0.734 |
| Run 2 | 196 images; letterbox; 640 | Leaky image split | 0.886 | 0.491 | 0.838 |
| Run 3 | 230 images; native; 896 | Leaky image split | 0.918 | 0.603 | 0.858 |
| Run 4 | 196 images; native; 896 | Leaky image split | 0.929 | 0.612 | 0.890 |
| **Run 5 final** | **460 training images from 9 matches; native; 896** | **3 held-out test matches** | **0.932** | **0.744** | **0.895** |

*Table 5. Optimisation stages. Values in rows with different splits should not be interpreted as a controlled model comparison.*

The final independent evaluation loaded `checkpoint_best_total.pth`, processed the 61 test images and produced 5,842 low-threshold candidate predictions for AP integration. It returned mAP@0.50 of 0.9318 and mAP@0.75 of 0.9149. The run's training evaluator reported COCO mAP@[0.50:0.95] of 0.7441. The training log also contains mAP@0.50 of 0.9383; the difference of 0.0065 reflects evaluator configuration and maximum-detection handling. The independently repeated 0.9318 is used as the headline AP@0.50 because it is directly reproducible with the repository script.

| Metric | Result | Evaluation detail |
| --- | ---: | --- |
| mAP@0.50 | 0.932 | Independent repeat; 15 represented classes |
| mAP@0.75 | 0.915 | Independent repeat |
| mAP@[0.50:0.95] | 0.744 | Final run evaluator |
| Best threshold-specific F1 | 0.895 | Confidence 0.35; IoU 0.50 |
| Precision at best F1 | 0.912 | 145 TP, 14 FP |
| Recall at best F1 | 0.879 | 145 TP, 20 FN |
| Mean prediction time | 50.5 ms/image | 61 images after three warm-up images |
| Median / p95 prediction time | 48.1 / 67.7 ms | CUDA synchronised |
| Prediction throughput | 19.8 FPS | Excludes decoding and reporting |
| Peak PyTorch allocated GPU memory | 0.37 GiB | Not total process VRAM |

*Table 6. Final held-out test and inference results on an RTX 5060 Ti 16 GB.*

Per-class AP@0.50 ranges from 0.832 for ATM to 0.984 for Aon among classes with at least five test boxes. MCP, KLG, Aon, Paints & Lacquers and Top Notch have the largest test support. Chadlaw and MNA Support Services each have one box, and MNA Cladding has two; their AP of 1.000 is descriptive of those few boxes only. CCH has no test box and is excluded from mAP. Figure 7 makes the support visible so that a rare class cannot appear more certain than a common one.

![Figure 6. Optimisation and resolution](LogoLens_MSc_Dissertation_v15_media/figure_06_optimisation_and_resolution.png)

*Figure 6. Optimisation trajectory and a controlled inference-resolution experiment. The left panel crosses evaluation protocols and is therefore diagnostic; the right panel holds the checkpoint fixed.*

![Figure 7. Per-class AP](LogoLens_MSc_Dissertation_v15_media/figure_07_per_class_ap50.png)

*Figure 7. Per-class AP@0.50 on held-out matches with ground-truth support. Gold bars have fewer than five boxes and should not be used for stable brand comparisons.*

The familiar-versus-unseen comparison confirms the importance of match separation. The same final checkpoint produced mAP@0.50 of 0.998 and F1 of 0.988 on training-match material, compared with 0.932 and 0.895 on unseen matches. Familiar scenes inflate mAP by approximately 6.6 percentage points and F1 by approximately 9.3 points. These differences are not model gains; they are the size of the evaluation bias avoided by the final design.

## 5.2 Visibility conditions, multi-logo cases and model errors

Preprocessing analysis explains much of the improvement. The original 1208 × 1280 letterboxed export contained approximately 47% black canvas. At a 640 input, a median logo was represented by roughly 24 × 16 pixels under that export, compared with approximately 24 × 30 pixels under native stretching. Native input at 896 represented the median logo at approximately 33 × 42 pixels, giving about 1,374 effective pixels, around 3.7 times the original pipeline's median effective area. This is especially important for a patch-based backbone: the mark spans more tokens and provides more local structure.

Localisation remains sensitive. For an approximately 33-pixel-wide box, a one-dimensional displacement of around 11 pixels can reduce overlap to IoU 0.50, about 4.7 pixels to IoU 0.75, and about 1.7 pixels to IoU 0.90 under a simplified equal-box calculation. The gap between mAP@0.50 and mAP@[0.50:0.95] is therefore expected even when class identity is correct. The stricter metric is the more relevant one for any downstream calculation based on box area.

Figure 8 shows four held-out cases selected by the rules specified in Section 3.3. Panel A contains seven ground-truth logos, all matched without a false positive. Panel B is a close-up with 12 logos and 12 matches, demonstrating simultaneous multi-logo detection. Panel C is a wide floodlit shot with two small ground-truth marks; both are missed. This example matches the quantitative small-object argument: recognition fails when camera distance removes the available visual detail. Panel D contains ten correct matches and two false positives. Both false boxes are localised on visually plausible kit regions, illustrating that strong context can produce an incorrect sponsor class even when most marks in the frame are correct.

![Figure 8. Held-out detection evidence](LogoLens_MSc_Dissertation_v15_media/figure_08_detection_evidence.png)

*Figure 8. Held-out evidence at confidence 0.35. Maroon boxes are matched predictions, orange boxes are false positives and red boxes are missed ground truth. Images were selected by predefined rules rather than appearance.*

The final test includes a floodlit match, but lighting is not balanced systematically. Of 304 newly selected frames, the recorded camera distribution was 87 close, 19 medium and only five wide frames; the remaining frames lacked one of these manual labels. Highlights therefore over-represent the views in which logos are largest. All frames in the final dataset show the white home kit. The model's behaviour on the black away kit, including the Floor Tonic chest sponsor, is not measured and should not be inferred from home-kit AP.

RQ2 also asks about blur, contrast, occlusion and human readability. The training augmentation deliberately simulates brightness, gamma, blur, motion blur and local dropout, and Figure 8 provides examples under varied camera distances. However, version 15 does not contain a held-out condition table or a human-readability dataset produced after the final optimisation. Earlier occlusion figures in version 14 were collected under a different detector/data pipeline and are not carried forward as RF-DETR results. Consequently, the current evidence supports a strong effect of effective logo size and a qualitative account of wide-shot failure, but it does not yet estimate independent effects for blur, contrast and occlusion or agreement with human readability.

## 5.3 Duration, Logo Visibility Score and full-video results

The temporal and scoring pipeline is implemented, but it has not been revalidated end-to-end with the final checkpoint. This distinction changes what can be reported. The project contains eight June 2026 workbooks in `dissertation/result_full_run`, covering M02, M03, M04, M05, M06, M07, M08 and M11. They include location assignment, “Human %”, AI-adjusted location shares and visibility outputs. They were generated before the August RF-DETR optimisation and depend on model/class mappings and kit-location logic outside the revised scope. The directory therefore contains eight, not approximately ten, completed workbooks, and none is treated as a final Run 5 full-video result.

Reusing those sheets would create three validity problems. First, the home-only RF-DETR checkpoint cannot support the away-kit M03, M04, M06 and M11 claims. Second, the backend's default RF-DETR variant and class order do not match the final Small checkpoint. Third, location percentages are commercial priority weights, not observed visibility or ground truth. Appendix C records the files for provenance but the main table of full-video outcomes is deferred until the correct pipeline is run.

The manual reference needed for RQ3 should contain, for each selected brand appearance, a human start time, end time, interruption decision and readability rating. The automatic result should then be compared using absolute duration error, relative error and limits by sampling rate. Gap tolerance should be varied around the current 2.5-interval rule, and the score should be recalculated without each component and under alternative weights. At least one additional rater is desirable for a subset, with agreement reported before consensus.

Until that experiment is complete, raw duration and Logo Visibility Score accuracy are not claimed. The correct result statement is narrower: the system can transform detections into traceable segments and quality-weighted seconds, but the accuracy of those quantities against human timing and visibility judgement remains to be established. No EMV total is presented because it would compound unvalidated duration, score weights, audience and rate assumptions.

| Research question | Main result in version 15 | Main limitation |
| --- | --- | --- |
| RQ1 | RF-DETR reaches mAP@0.50 0.932, mAP@[.50:.95] 0.744 and best F1 0.895 on unseen matches; 19.8 prediction FPS | Small three-match test; rare classes have little or no support |
| RQ2 | Native 896 input increases effective small-logo information; wide-shot misses remain; 12-logo held-out success demonstrated | No final condition-stratified or human-readability study |
| RQ3 | Transparent temporal segmentation and quality-weighted exposure are implemented | Final videos have not been rerun or manually timed with the new checkpoint |

*Table 7. Research-question conclusions and evidence limits.*

---

# Chapter 6: Discussion

## 6.1 Answers to the research questions and comparison with prior work

**RQ1 is answered positively within the case boundary.** A specialist RF-DETR detector can identify multiple known sponsors in unseen Bradford Bulls home-kit footage with high AP@0.50 and useful stricter localisation performance. The best threshold-specific operating point combines precision above 0.91 with recall close to 0.88. The model can also process nearly 20 images per second in isolation on the target GPU, well above a 2 FPS analytics sampling rate. The 12-logo success case shows that simultaneous detections are not an exceptional edge case for the model.

The result should not be compared directly with commercial vendor accuracy because the vendor datasets, class rosters and matching rules are unavailable. It also should not be compared casually with COCO model-card results. Standard benchmarks contain different objects, scales and scene distributions. The more meaningful comparison is internal: the final split removes temporal familiarity, and the unseen score is materially lower than the training-match score. This confirms the warning from sports-video benchmarks that correlated frames can make evaluation optimistic (Deliège et al., 2021).

The final checkpoint also changes the earlier architectural story. Version 14 centred on YOLO as the operational detector and treated an earlier RF-DETR experiment as secondary. The August optimisation shows that a small transformer detector, when given appropriate geometry and diverse matches, can outperform the previous project baselines. The important lesson is not that transformers always beat YOLO. Run protocols are not sufficiently matched for that universal statement. The result supports RF-DETR for this data and shows that preprocessing and split design can matter as much as the family name.

**RQ2 is answered only in part.** Effective logo size clearly affects feasibility. Native frames and higher resolution produce more useful pixels and improve AP in the controlled resolution experiment. The wide-shot miss supplies concrete held-out evidence of the limit. This aligns with the sports-logo challenges reported by Liao et al. (2017) and with the general importance of multi-scale representation. However, the augmentation recipe does not prove robustness to blur, contrast or occlusion. Nor does confidence establish readability. The planned human and condition-based analysis is needed before the dissertation can rank those factors.

**RQ3 is not yet answered empirically.** The temporal formula is coherent and inspectable, and the 30-second correction fixes the earlier EMV scaling issue. Yet correctness of code is not accuracy of measurement. A gap rule that appears reasonable can over-count or split exposure, and a confidence-based clarity proxy can disagree with a person. The most academically defensible conclusion is that the framework exists and produces auditable intermediate values, but its agreement with manual timing and human visibility scores remains an open result.

## 6.2 Practical meaning and accessibility for smaller clubs

The detector performance is strong enough to support a practical review workflow for in-scope footage. At 2 sampled FPS, the isolated model's throughput provides roughly tenfold inference headroom. A staff member could receive a brand summary and inspect the frames behind it rather than watching a complete highlight video manually. This is useful even without a monetary value because it documents delivered screen time, identifies weak views and supports evidence-based conversations.

Accessibility should be framed by measured requirements. Training completed in approximately 2.5 hours on a 16 GB consumer GPU. Inference ran at 19.8 FPS under the stated benchmark. These observations suggest that a local technical deployment is feasible without data-centre hardware. They do not include staff time for annotation, maintenance, video rights, hardware purchase or retraining when sponsors and kits change. They also do not prove that local ownership is cheaper than a managed service once total cost is counted.

Transparency is the more certain practical contribution. Every aggregate can be traced from report to segment, detection, timestamp and source frame. A commercial judgement can therefore use the measurement without confusing it with the judgement itself. The club may choose to apply expert priority weights, but those weights should be displayed as external inputs. The red-circled “Human %” from the legacy workbook is appropriate only as an anonymised commercial priority or package-allocation variable. It should not be inserted into the model target, used to grade the detector or described as the correct visibility share.

The system is not yet ready for routine use with every club video. The final class mapping must be fixed in the backend, away-kit data must be collected, and full videos must be rerun. A domain gate should refuse or flag footage whose kit and lighting are outside the measured training domain. Without that gate, a confident output can be operationally more dangerous than a visible failure because users may assume the dashboard has been validated on the footage.

## 6.3 Limitations and threats to validity

**Internal validity.** Model-assisted pre-annotation may produce consistent but model-shaped boxes. A primarily single-annotator process can also introduce systematic boundary choices. The threshold-specific F1 was characterised on test predictions after training; a cleaner final protocol would lock the threshold on validation. Two evaluator paths produce mAP@0.50 values differing by 0.006, which must be resolved or documented before journal submission. The independent script's mAP@[.50:.95] output was invalid under its current maximum-detection configuration, so that metric is taken from the run evaluator rather than silently reported as a failed value.

**Construct validity.** Bounding-box area is a direct measure of screen coverage but not visible logo area under occlusion. Confidence is a detector score, not clarity or readability. Screen centrality is an assumption about prominence. The inactive OBB penalty means perspective and rotation are not measured. Quality-weighted seconds therefore operationalise selected proxies; they are not a psychological visibility scale until compared with human ratings.

**External validity.** The test contains three unseen matches from one club, one sport and one white home kit. Highlight videos over-represent close shots and under-represent wide tactical views. The test set has 165 boxes, and several brands have insufficient support. Results cannot be generalised to the away kit, a new season, another broadcaster, perimeter boards or unknown logos without new evidence.

**Conclusion validity.** Per-class AP of 1.000 with one or two boxes is highly uncertain. The study reports support instead of confidence intervals for these sparse categories, but a larger test is required. The difference between familiar and unseen material demonstrates leakage risk; it does not estimate performance across all future matches. Similarly, the resolution experiment shows a checkpoint-specific pattern rather than a universal optimum at 768 or 896.

**Operational validity.** The backend and final checkpoint are not yet aligned, and the June workbooks belong to an earlier pipeline. Presenting them as final outputs would mix model versions and class semantics. The versioned Markdown workflow is used partly to prevent this: version 15 preserves the corrected evidence boundary, while a later version can replace incomplete sections after a controlled full-video run.

---

# Chapter 7: Conclusion and Future Work

## 7.1 Conclusion and contributions

This dissertation set out to develop and evaluate a computer-vision framework for detecting known sponsor logos and measuring visibility quality in sports broadcasts. The detector component achieved the strongest and most credible result in the project to date. RF-DETR Small, trained at resolution 896 on match-separated native frames, reached mAP@0.50 of 0.932, mAP@[0.50:0.95] of 0.744 and a best F1 of 0.895 on three unseen matches. It processed test images at 19.8 FPS on an RTX 5060 Ti. A leakage diagnostic showed why the match-level design matters: familiar material increased mAP@0.50 to 0.998 and F1 to 0.988.

The technical contribution is a modular, multi-logo detector and reporting pipeline with traceable frame records. The methodological contribution is a match-disjoint evaluation, explicit class support, evaluator cross-checking and example selection based on error rules. The practical contribution is an inspectable route from broadcast frames to sponsor-level evidence on consumer hardware.

The aim is only partly completed. The visibility and temporal framework is implemented, including corrected quality-seconds and 30-second media-value conversion, but the final RF-DETR checkpoint has not been rerun across all highlight videos and has not been compared with manual timing or human readability ratings. Those quantities are not claimed as validated findings. This limitation is preferable to retaining obsolete outputs because it tells the reader exactly what the research currently demonstrates.

## 7.2 Priority future work

The first priority is evidence completion, not a more complex model. The backend should be pinned to RF-DETR Small, resolution 896, checkpoint `rfdetr_matchsplit_r896` and the COCO category table. The 13 currently available highlight videos should then be screened by kit domain. Home-kit videos can be analysed; away-kit videos should be withheld until annotated away-kit data support them. The output set should include model version, category hash, sampling rate and threshold in every report.

Second, RQ2 requires a stratified human study. A sample should balance size, camera distance, blur, contrast, occlusion and correct/incorrect detections. Two raters should judge whether the brand is readable and how visible it is under a short rubric. Agreement can be reported with weighted kappa or an intraclass correlation appropriate to the scale. Automated features should then be evaluated against those ratings rather than assigned weights by intuition.

Third, RQ3 requires manual timing. Continuous appearances should be timed at native frame rate, then compared with automatic estimates at 1, 2, 5 and native FPS. Gap tolerance, minimum segment length and duration weight should be varied. The final Logo Visibility Score should report sensitivity to component removal and alternative weights. EMV should remain a separate scenario layer using sourced audience and media-rate inputs.

Further work should expand match and class support, especially for CCH and the one-to-three-box test classes; add away-kit and additional broadcaster domains; oversample wide shots; and audit a subset of annotations independently. Oriented boxes or segmentation could improve visible-area measurement under rotation and occlusion, but should be adopted only after the simpler score has been validated. Open-set retrieval can be explored later for new sponsors. Adoption research through interviews or surveys with club staff should also be a later study, not inferred from technical feasibility.

## 7.3 Final takeaway

Transparent computer vision can give a smaller sports club credible, frame-level evidence of sponsor-logo visibility. In this case, accurate detection on unseen home-kit matches is feasible on consumer hardware. The same level of confidence cannot yet be attached to duration, human readability or monetary value. The value of LogoLens therefore lies not in presenting one authoritative percentage, but in making the measurement process, its assumptions and its remaining uncertainty visible.

---

# References

Blinkfire (n.d.) *Sponsorship data platform*. Available at: https://www.blinkfire.com/d/landing/mediaanalytics (Accessed: 11 August 2026).

Breuer, C. and Rumpf, C. (2012) ‘The viewer’s reception and processing of sponsorship information in sport telecasts’, *Journal of Sport Management*, 26(6), pp. 521–531. https://doi.org/10.1123/jsm.26.6.521

Carion, N., Massa, F., Synnaeve, G., Usunier, N., Kirillov, A. and Zagoruyko, S. (2020) ‘End-to-end object detection with transformers’, in *European Conference on Computer Vision*, pp. 213–229. https://arxiv.org/abs/2005.12872

Cornwell, T.B. (2019) ‘Less “sponsorship as advertising” and more sponsorship-linked marketing as authentic engagement’, *Journal of Advertising*, 48(1), pp. 49–60. https://doi.org/10.1080/00913367.2019.1588809

Cornwell, T.B. and Kwon, Y. (2020) ‘Sponsorship-linked marketing: research surpluses and shortages’, *Journal of the Academy of Marketing Science*, 48, pp. 607–629. https://doi.org/10.1007/s11747-019-00654-w

Davenport, T., Guha, A., Grewal, D. and Bressgott, T. (2020) ‘How artificial intelligence will change the future of marketing’, *Journal of the Academy of Marketing Science*, 48, pp. 24–42. https://doi.org/10.1007/s11747-019-00696-0

Deliège, A., Cioppa, A., Giancola, S. et al. (2021) ‘SoccerNet-v2: a dataset and benchmarks for holistic understanding of broadcast soccer videos’, in *CVPR Workshops*, pp. 4508–4519. https://arxiv.org/abs/2011.13367

Department for Culture, Media and Sport (2023) *Still ill? Assessing the financial sustainability of football*. Available at: https://www.gov.uk/government/publications/reforming-club-football-governance-consultation-response/research-report-still-ill-assessing-the-financial-sustainability-of-football-2023 (Accessed: 11 August 2026).

Hevner, A.R., March, S.T., Park, J. and Ram, S. (2004) ‘Design science in information systems research’, *MIS Quarterly*, 28(1), pp. 75–105. https://doi.org/10.2307/25148625

Huang, M.-H. and Rust, R.T. (2021) ‘A strategic framework for artificial intelligence in marketing’, *Journal of the Academy of Marketing Science*, 49, pp. 30–50. https://doi.org/10.1007/s11747-020-00749-9

Liao, Y., Lu, X., Zhang, C., Wang, Y. and Tang, Z. (2017) ‘Mutual enhancement for detection of multiple logos in sports videos’, in *Proceedings of the IEEE International Conference on Computer Vision*, pp. 4846–4855. https://openaccess.thecvf.com/content_ICCV_2017/papers/Liao_Mutual_Enhancement_for_ICCV_2017_paper.pdf

Lin, T.-Y., Maire, M., Belongie, S. et al. (2014) ‘Microsoft COCO: common objects in context’, in *European Conference on Computer Vision*, pp. 740–755. https://arxiv.org/abs/1405.0312

Nielsen (2017) *Nielsen acquires artificial intelligence-powered sports marketing startup vBrand*. Available at: https://www.nielsen.com/news-center/2017/nielsen-acquires-artificial-intelligence-powered-sports-marketing-startup-vbrand/ (Accessed: 11 August 2026).

Nielsen (n.d.-a) *Sports reports: Sponsorship Media Value Benchmarking Report*. Available at: https://www.nielsen.com/marketplace/sports-reports/ (Accessed: 11 August 2026).

Nielsen (n.d.-b) *Nielsen Sports—Media Valuation*. Available at: https://content.nielsen.com/l/881703/2022-11-18/42b9x (Accessed: 11 August 2026).

Oquab, M., Darcet, T., Moutakanni, T. et al. (2023) ‘DINOv2: learning robust visual features without supervision’, *arXiv*. https://arxiv.org/abs/2304.07193

Redmon, J., Divvala, S., Girshick, R. and Farhadi, A. (2016) ‘You only look once: unified, real-time object detection’, in *Proceedings of the IEEE Conference on Computer Vision and Pattern Recognition*, pp. 779–788. https://arxiv.org/abs/1506.02640

Relo Metrics (n.d.) *Sponsorship measurement platform overview*. Available at: https://relometrics.com/sponsorship-measurement-platform (Accessed: 11 August 2026).

Robinson, I., Robicheaux, P., Popov, M., Ramanan, D. and Peri, N. (2025) ‘RF-DETR: neural architecture search for real-time detection transformers’, *arXiv:2511.09554*. https://arxiv.org/abs/2511.09554

Romberg, S., Pueyo, L.G., Lienhart, R. and van Zwol, R. (2011) ‘Scalable logo recognition in real-world images’, in *ACM International Conference on Multimedia Retrieval*, pp. 1–8. https://doi.org/10.1145/1991996.1992021

Rumpf, C., Boronczyk, F. and Breuer, C. (2020) ‘Predicting consumer gaze behavior toward sponsorship stimuli in sport broadcasts’, *European Sport Management Quarterly*, 20(4), pp. 461–479. https://doi.org/10.1080/16184742.2019.1620838

Su, H., Zhu, X. and Gong, S. (2018) ‘Open logo detection challenge’, in *British Machine Vision Conference*. https://arxiv.org/abs/1807.01964
Two Circles (2025) *Sports IP Revenue League: methodology and references*. Available at: https://twocircles.com/gb/articles/sports-ip-revenue-league-methodology-and-references/ (Accessed: 12 August 2026).

Zhang, Y., Sun, P., Jiang, Y. et al. (2022) ‘ByteTrack: multi-object tracking by associating every detection box’, in *European Conference on Computer Vision*, pp. 1–21. https://arxiv.org/abs/2110.06864

Zhao, Y., Lv, W., Xu, S. et al. (2024) ‘DETRs beat YOLOs on real-time object detection’, in *Proceedings of the IEEE/CVF Conference on Computer Vision and Pattern Recognition*, pp. 16965–16974. https://openaccess.thecvf.com/content/CVPR2024/html/Zhao_DETRs_Beat_YOLOs_on_Real-time_Object_Detection_CVPR_2024_paper.html

---

# Appendices

## Appendix A: Per-class held-out AP@0.50

| Sponsor class | Test boxes | AP@0.50 |
| --- | ---: | ---: |
| ATM | 6 | 0.832 |
| EM Workwear | 6 | 0.857 |
| Bartercard | 5 | 0.860 |
| MCP | 27 | 0.891 |
| Fairway | 3 | 0.916 |
| Romantica | 13 | 0.927 |
| Top Notch | 16 | 0.935 |
| Paints & Lacquers | 18 | 0.941 |
| ASC Group | 11 | 0.941 |
| Ellgren | 7 | 0.947 |
| KLG | 31 | 0.948 |
| Aon | 18 | 0.984 |
| Chadlaw | 1 | 1.000 |
| MNA Support Services | 1 | 1.000 |
| MNA Cladding | 2 | 1.000 |
| CCH | 0 | Not measurable |

## Appendix B: Required experiments before submission

1. Pin backend to RF-DETR Small, resolution 896, confidence 0.35, final checkpoint and COCO category mapping.
2. Select validation-based threshold and repeat one untouched test evaluation.
3. Resolve the 0.932 versus 0.938 evaluator difference and make maximum detections consistent.
4. Add away-kit training and a domain gate before analysing away footage.
5. Rerun all in-domain highlight videos and create one video-level summary table.
6. Manually time a stratified sample at native frame rate; test sampling and gap rules.
7. Collect two-rater readability scores across size, blur, contrast and occlusion groups.
8. Perform component-removal and weight-sensitivity tests for the Logo Visibility Score.

## Appendix C: Legacy full-run file register

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

## Appendix D: Figure provenance and AI disclosure

Figure 1 was generated as a conceptual infographic with OpenAI ImageGen and then revised to remove text, values and promotional claims. Final edit prompt:

> Edit this academic infographic into a cleaner conceptual figure. Preserve the left-to-right story and the maroon/charcoal/gold vector style, but remove every word, number, percentage, timestamp, brand-like mark, and unsupported claim. Remove the entire bottom promotional banner. Simplify the right-hand analytics panels to unlabeled visual symbols only: a neutral timeline with dots, a gauge without a number, and small neutral bar-chart/report icons without numeric values. Simplify the centre lower pipeline into four unlabeled icon boxes connected by arrows: video frames, detection boxes, visibility measurement, report. Keep the generic rugby stadium, generic jersey and match frame, but no real team identity and no real sponsor logos. Make the composition wide 16:9, clean, balanced, spacious, and suitable as a figure in a Master's dissertation. Absolutely no text or digits anywhere.

Figures 2–7 were generated deterministically from the recorded design and experiment values. Figure 8 was produced by running the final checkpoint over the held-out test images and applying the selection rules documented in Section 3.3.

## Appendix E: Repository evidence used for version 15

- Final checkpoint: `runs/rfdetr_matchsplit_r896/checkpoint_best_total.pth`
- Training configuration: `runs/rfdetr_matchsplit_r896/training_config.json`
- Training metrics: `runs/rfdetr_matchsplit_r896/metrics.csv`
- Dataset: `datasets/auto_label_white_matchsplit`
- Independent evaluator: `scripts/eval_rfdetr_coco.py`
- Optimisation record: `docs/11-map-optimisation.md`
- RF-DETR pipeline record: `docs/10-rfdetr-pipeline.md`

<!-- End of LogoLens MSc Dissertation version 15 -->
