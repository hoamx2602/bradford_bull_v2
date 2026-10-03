**UNIVERSITY OF BRADFORD**

**FACULTY OF ENGINEERING AND DIGITAL TECHNOLOGIES**

**MSc Dissertation**

**MAI XUAN HOA**

# COMPUTER-VISION FRAMEWORK FOR SPONSOR-LOGO DETECTION AND VISIBILITY-QUALITY ASSESSMENT IN SPORTS

A dissertation submitted in partial fulfilment of the requirements for the degree of

**MSc Applied Artificial Intelligence and Data Analytics**

Student ID: *[insert student ID]*  
Supervisor: *[insert supervisor name]*  
Submission date: *[insert date]*

---

## Declaration

I declare that this dissertation is my own work and has not been submitted, in whole or in part, for another degree or qualification. All external sources are acknowledged. Third-party models, libraries and services are identified where they are discussed. Artificial-intelligence assistance used to produce the conceptual and system-flow diagrams in Figures 1, 2, 3, 5 and 6 is disclosed in Appendix E. Every quantitative chart was generated from recorded project measurements and checked against its source experiment output, as described in that appendix.

## Abstract

Sports clubs need credible evidence that sponsor logos appeared in broadcast and highlight footage, yet exposure is difficult to measure when marks are small, deformed by fabric, partly hidden and repeated across several locations in one frame. Commercial platforms demonstrate that automated tracking is feasible, but their methods and evaluation data are generally not transparent. This dissertation develops LogoLens: a closed-set multi-logo detection system and a transparent prototype framework for transforming detections into auditable measures of visibility duration and quality. Visibility is treated as an observable exposure condition, not as evidence of attention, return on investment or sponsorship revenue.

The study follows a design-science approach with a quantitative single-club case evaluation. The dataset contains 584 images and 1,903 annotated boxes across 16 sponsor classes from 15 match groups. Complete matches, rather than neighbouring frames, form the units of the train, validation and test split. RF-DETR Small and three YOLO26 baselines were trained at the same 896-pixel input resolution and evaluated on the same 61 images and 165 boxes from three unseen matches using one scoring protocol.

RF-DETR Small achieved mAP@0.50 of 0.933, mAP@0.75 of 0.917 and mAP@[0.50:0.95] of 0.747, with F1 of 0.898 at the characterised operating threshold. The strongest YOLO26 baseline reached 0.772 mAP@0.50 and 0.673 mAP@0.75. A support-restricted mean of 0.917 is reported alongside the conventional RF-DETR mAP@0.50 because four sparse classes contribute only seven test boxes. Match-disjoint evaluation reduced the apparent score from 0.998 on familiar material to 0.933 on unseen matches, demonstrating the practical effect of temporal leakage. Performance was stable across the three test matches but recall fell to 0.500 on wide tactical shots, identifying a predictable downward bias for exposure-duration estimates. RF-DETR inference averaged 50.5 ms per image on an RTX 5060 Ti 16 GB GPU, excluding video decoding and reporting.

The results establish accurate in-domain sponsor-logo detection on consumer hardware and show why match separation, camera distance and per-class support must be reported. The temporal and Logo Visibility Score components are implemented and traceable to source frames, but have not yet been validated against manual timing or human readability judgements. They are therefore presented as a transparent prototype and validation agenda rather than as confirmed measures of sponsor value.

**Keywords:** computer vision; logo detection; YOLO26; RF-DETR; small-object detection; sports sponsorship; visibility measurement; design science.

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

1. Conceptual comparison of the YOLO26 and RF-DETR detection routes.
2. Research framework: from sponsorship accountability to auditable visibility evidence.
3. Leakage-aware research design and case boundary.
4. Dataset design and the effect of temporal leakage.
5. LogoLens processing pipeline and detector-adapter detail.
6. From detection records to prototype visibility evidence.
7. RF-DETR training trajectory and held-out class-level evidence.
8. Qualitative held-out occlusion examples.
9. Held-out success and error examples selected by predefined rules.
10. Prototype brand-level visibility timeline.

## List of Tables

1. Research questions and evidence required.
2. Conceptual and experimental comparison of YOLO26 and RF-DETR.
3. Final match-disjoint dataset.
4. Composition of the held-out test set.
5. Detector systems under one accuracy-evaluation protocol.
6. Research-question conclusions and evidence limits.
7. Term-by-term computation of frame-level visibility for one held-out detection.

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

Two questions follow from the preceding argument. Can multiple sponsor logos be detected accurately on matches that the model has not seen? If they can, how should those detections be converted into evidence that remains traceable to the footage and honest about its uncertainty?

This dissertation addresses both questions through a case study with Bradford Bulls, a professional rugby league club. Rugby league is a demanding applied setting: sponsor marks appear on moving and deformable clothing, several sponsors can occur in one frame, and camera distance changes rapidly between close, medium and wide play. The club context also makes transparency important, because a measurement that cannot be checked is of limited value in a commercial conversation.

The **aim** is to develop and evaluate an accurate multi-logo detection system for unseen sports footage and to implement a transparent prototype framework that converts frame-level detections into auditable visibility evidence.

The study has three objectives:

1. Develop and evaluate a multi-logo detector on footage from matches excluded from model development, including a controlled local comparison between YOLO26 and RF-DETR systems.
2. Examine how held-out detection performance varies across logo size, camera distance, lighting and source resolution.
3. Implement a traceable transformation from detections to temporal segments and quality-weighted exposure, while defining the validation required before the Logo Visibility Score can be treated as an accurate operational measure.

The corresponding research questions are:

- **RQ1:** How accurately and efficiently can the system identify multiple known sponsor logos in unseen sports footage?
- **RQ2:** How does held-out detection performance vary across logo size, camera distance, lighting and source resolution?
- **RQ3:** How can frame-level detections be transformed into a transparent and auditable prototype measure of visibility duration and quality, and what validation is required before operational use?

| Research question | Evidence required | Where it is reported |
| --- | --- | --- |
| RQ1 | Match-disjoint detection metrics, per-class support, YOLO26-RF-DETR comparison under one accuracy protocol, and RF-DETR inference benchmark | Sections 5.1 to 5.3 |
| RQ2 | Condition-stratified held-out results and predefined qualitative error cases | Sections 5.4 and 5.5 |
| RQ3 | Implemented temporal algorithm, traceability of intermediate outputs, and an explicit validation boundary | Section 5.6 |

*Table 1. Research questions and the evidence used to answer them. RQ3 is intentionally framed as a design-and-validation-boundary question because manual timing and human-readability validation are not yet complete.*

Answering these questions contributes on three fronts. The first is evidence on the feasibility of specialist sponsor-logo detection using resources available to a small technical team. The second is a controlled, task-specific comparison between a current YOLO system and a detection-transformer system rather than a comparison borrowed from a general benchmark. The third is an auditable visibility framework in which every aggregate remains resolvable to temporal segments, detections, timestamps and source frames, with unvalidated assumptions kept visible.

Those limits define the scope. The system recognises a fixed seasonal roster and cannot reliably name a brand it has never encountered. It measures observable screen exposure rather than attention, recall, sales or sponsorship value. Monetary valuation is therefore kept as an optional scenario layer, not a validated model output. Player attribution, team attribution, body segmentation and kit-location pricing are outside scope. The dissertation now follows one continuous movement: Chapter 2 defines the measurement construct and the model choices; Chapter 3 establishes how they are tested without temporal leakage; Chapter 4 describes the implemented system; Chapter 5 reports the results in research-question order; and Chapter 6 explains what those results mean and where their use must stop.

---

# Chapter 2: Literature Review

## 2.1 From sponsorship value to an observable measurement construct

Sponsorship is better understood as a linked marketing relationship than as a purchase of controlled advertising space. Cornwell (2019) emphasises authentic engagement, while Cornwell and Kwon (2020) show that sponsorship outcomes arise from several interacting mechanisms rather than exposure alone. Broadcast visibility is therefore an input to sponsorship effectiveness, not a complete measure of it. It establishes an opportunity for a mark to be seen; it does not establish that a viewer attended to it, remembered it, changed attitude or purchased a product.

This distinction separates three layers that are often collapsed in commercial reporting. **Exposure** is an observable property of the media: whether a logo appeared, how large it was, where it appeared and for how long. **Attention and cognition** concern whether a viewer processed the stimulus. Eye-tracking research addresses this second layer more directly; Breuer and Rumpf (2012) and Rumpf et al. (2020), for example, show that processing depends on both exposure conditions and viewer involvement. **Commercial effect** concerns outcomes such as brand lift, sales or contract value and requires additional behavioural and financial evidence. LogoLens operates at the first layer.

Manual content analysis can measure that layer, but it scales poorly. A reviewer must locate each appearance, assign a brand, judge interruptions and record quality. Commercial platforms automate parts of this work. Nielsen describes AI-assisted tracking combined with analysts, audience data and media rates, and its vBrand description explicitly names duration, size and image clarity as quality factors (Nielsen, 2017; Nielsen, n.d.-a). Relo Metrics and Blinkfire describe comparable capabilities. These sources establish that automated exposure analysis exists in practice, but their private datasets and scoring rules prevent direct replication or accuracy comparison.

Equivalent Media Value illustrates why the measurement layers must remain separate. Converting quality-weighted exposure into a 30-second advertising equivalent can be useful as a declared scenario:

\[
\text{Illustrative EMV} = \left(\frac{Q}{30}\right) \times \left(\frac{\text{CPM}}{1000}\right) \times \text{Audience} \times M,
\]

where \(Q\) is quality-weighted exposure in seconds and \(M\) contains explicit scenario multipliers. The calculation is not a model target and does not convert visibility into revenue. Its reliability cannot exceed the reliability of the detected duration, quality weights, audience estimate or media rate beneath it. LogoLens therefore treats traceable exposure as the primary output and any monetary expression as a separate, optional layer.

The gap relevant to a smaller club is consequently not established by an unsupported claim that every commercial service is unaffordable. It is established by transparency and reproducibility: a club-specific system whose detections, thresholds, errors and aggregation rules can be inspected locally.

## 2.2 The technical task: closed-set multi-logo detection in broadcast video

Logo detection localises and assigns an identity to a mark in an image. Logo recognition without localisation and image retrieval are related but different tasks. Early benchmarks such as FlickrLogos-32 and OpenLogo demonstrated the effects of clutter, limited examples and large brand vocabularies (Romberg et al., 2011; Su et al., 2018). Liao et al. (2017) examined multiple logos in sports video and identified layout variation, deformation, motion blur and partial occlusion. Those difficulties intensify when marks are printed on moving fabric rather than placed on static boards.

A closed-set detector fits the operational problem examined here. The seasonal sponsor roster is known, and the required output is a class-labelled box for every visible instance of those sponsors. Closed-set training permits specialist fine-tuning and simple reporting, but it creates a clear domain boundary: a new sponsor, new kit design or substantially different broadcaster requires new evidence and potentially retraining. Open-set and retrieval methods may reduce that onboarding cost, but introduce unknown-class handling and verification questions beyond the present study.

Broadcast video adds two dependencies that ordinary image benchmarks can hide. First, adjacent frames are highly correlated. If frames from one match are divided randomly between training and test sets, the test material can reproduce the same players, camera position, lighting and phase of play as training. Sports-video benchmark work has highlighted this dependence (Deliège et al., 2021). Second, the distribution of camera shots matters. Highlight footage favours close views, while a complete broadcast contains more wide tactical play. An aggregate result can therefore be accurate for the sampled highlight distribution yet optimistic for full-match duration measurement.

Small-object geometry is the central visual constraint. The median annotated mark in this study is 70 × 48 pixels in the source broadcast, but the detector does not receive the source image at full resolution. At a 512-pixel square input, the median mark is approximately 19 × 23 pixels. A few pixels of displacement then change IoU substantially, so AP@0.50 and AP@0.75 describe meaningfully different localisation capability. Input resolution, aspect transformation and multi-scale representation are therefore experimental variables rather than implementation details.

## 2.3 YOLO26 and RF-DETR as candidate detector systems

YOLO introduced object detection as a single-pass prediction problem and became influential because of its speed and deployment simplicity (Redmon et al., 2016). The YOLO26 system evaluated in this dissertation differs materially from early YOLO versions. It uses a convolutional backbone and multi-scale feature-fusion neck, but its default one-to-one detection head supports end-to-end inference without non-maximum suppression. Its training design also includes Progressive Loss and Small-Target-Aware Label Assignment, intended to maintain positive supervision for small objects (Jocher et al., 2026). It should therefore not be described merely as a traditional NMS-based detector.

DETR reframed detection as direct set prediction. A transformer encoder-decoder processes learned object queries, and bipartite matching assigns predictions uniquely to ground-truth objects (Carion et al., 2020). This removes anchors and NMS from the original DETR formulation and allows the model to reason about the set of objects in an image. Subsequent systems improved convergence and real-time performance. RT-DETR uses an efficient hybrid encoder and adjustable decoder depth (Zhao et al., 2024). RF-DETR combines a DINOv2-based visual backbone with a specialist detection-transformer design and uses weight-sharing neural architecture search to identify accuracy-latency configurations (Robinson et al., 2025; Oquab et al., 2023).

The two systems are credible candidates for different reasons. YOLO26 provides a compact, deployment-oriented family with explicit small-target training mechanisms. RF-DETR provides foundation-model features, global context and set-based prediction that may transfer well to a small specialist dataset. Neither architectural description determines the outcome on rugby-shirt logos, and general COCO rankings cannot substitute for a local comparison because the object scales and scene statistics differ.

Figure 1 narrows the comparison to the architectural ideas relevant to this study. YOLO26 builds and fuses convolutional features across scales before its one-to-one detection head. RF-DETR projects DINOv2 features and uses object queries in a transformer decoder to predict an object set. Both routes are normalised to the same class, confidence and box schema so that the evaluation protocol can be shared.

![Figure 1. YOLO26 and RF-DETR conceptual architecture comparison](LogoLens_MSc_Dissertation_v17_media/figure_01_yolo26_rfdetr_architecture.png)

*Figure 1. Conceptual comparison of the evaluated YOLO26 and RF-DETR detection routes. The figure shows the task-relevant prediction pathways and their common output schema; it is not a layer-complete network specification and does not imply equivalent accuracy or efficiency.*

| Comparison dimension | YOLO26 system | RF-DETR Small system | Relevance to LogoLens |
| --- | --- | --- | --- |
| Core representation | Convolutional backbone with multi-scale feature fusion | DINOv2-based visual backbone with transformer queries | Small marks require retained local detail and useful context |
| Prediction design | Dual-head training; default one-to-one end-to-end inference | Set prediction with bipartite matching | Both can produce final predictions without a conventional NMS stage |
| Small-target support | Small-Target-Aware Label Assignment and scale augmentation | Foundation pre-training and multi-scale transformer features | Provides two plausible transfer strategies for limited specialist data |
| Compared variants | Nano, small and medium | Small | Capacity and compute are not identical |
| Local training recipe | Mosaic, HSV and geometric augmentation in the recorded runs; mixup and copy-paste disabled | RF-DETR augmentation pipeline including photometric, blur and dropout transforms | Training recipe remains a confounding system-level difference |
| Fair controls in this study | Same images, match split, input size and scoring code | Same images, match split, input size and scoring code | Supports a task-specific accuracy comparison, not a pure architecture ablation |
| Deployment evidence | Accuracy measured; matched latency benchmark not yet recorded | 50.5 ms per image and 19.8 prediction FPS on the target GPU | Efficiency cannot yet be compared symmetrically |

*Table 2. Conceptual and experimental comparison of the two detector systems. The local experiment compares systems as configured, not isolated architectural components.*

## 2.4 From detections to visibility evidence

A detection count is not a visibility measure. Screen coverage can be measured directly as box area divided by frame area, and box-centre position can be measured geometrically. Detector confidence is also directly available, but its interpretation is narrower: it expresses model certainty under the trained classifier, not human readability. Blur and contrast can be estimated from image features, yet both are sensitive to crop size and background. Occlusion is still more difficult because a horizontal box contains no explicit estimate of the visible proportion of a rotated or folded logo.

This distinction motivates three categories. **Direct measurements** include timestamp, box coordinates, area and screen position. **Model-derived proxies** include detector confidence. **Unsupported constructs** currently include human readability and visible-area loss under occlusion. A transparent composite score should preserve these categories instead of presenting all components as equally validated observations.

Duration introduces a temporal aggregation problem. Sampling at \(f_s\) frames per second means each analysed frame represents approximately \(1/f_s\) seconds, but true appearances may be interrupted by detector misses. Tracking methods such as ByteTrack associate detections across frames (Zhang et al., 2022), while gap tolerances can prevent a single miss from fragmenting one exposure segment. Minimum-duration rules can remove isolated false detections. Each rule trades under-counting against over-counting and requires comparison with manually timed sequences before the result can be described as accurate duration.

The same requirement applies to a Logo Visibility Score. Size, position, confidence and duration are plausible components, but plausible components do not create a validated psychological scale. Component-removal analysis, alternative weights, manual timing and human judgements are required before quality-weighted seconds can be interpreted as more than an auditable prototype.

## 2.5 Research gap and study framework

The literature was reviewed through combinations of terms including *sports sponsorship measurement*, *logo detection*, *small-object detection*, *YOLO26*, *DETR*, *RF-DETR*, *broadcast video*, *visibility duration*, *occlusion* and *human readability*. Peer-reviewed papers and official technical publications were prioritised for model claims; vendor sources were used only to describe publicly documented services.

The reviewed evidence establishes that exposure is commercially relevant but distinct from attention and value; that sports-logo detection is affected by small scale, motion and deformation; that YOLO and DETR systems offer different transfer and deployment strategies; and that temporal aggregation needs manual validation. It does not provide a reproducible, club-specific study combining match-disjoint multi-logo evaluation, a current YOLO26-RF-DETR comparison, condition-specific failure analysis and traceable visibility aggregation on smaller-club footage.

Figure 2 summarises the resulting research logic. A need for sponsorship accountability is narrowed to an observable exposure construct, tested through leakage-aware computer vision and converted into traceable evidence. The study uses design science because it builds and evaluates that artefact (Hevner et al., 2004), and a quantitative case study because its claims are bounded to one club context. Adoption theory is not used because no staff-interview or survey dataset was collected.

![Figure 2. Research framework](LogoLens_MSc_Dissertation_v17_media/figure_02_research_framework.png)

*Figure 2. LogoLens study framework. The sponsorship-accountability need is operationalised as observable exposure, evaluated through a match-disjoint YOLO26 and RF-DETR study, and converted into auditable visibility evidence. The study is bounded to one club, the white home kit, broadcast and highlight footage, and three unseen test matches; temporal aggregation requires separate validation. The figure is conceptual and contains no measured results.*

---

# Chapter 3: Research Methodology

## 3.1 Research design and case boundary

The research combines design science with a quantitative case-study evaluation. Design science is appropriate because the main output is an artefact: a pipeline that converts sports-broadcast video into detections, temporal segments and sponsor-level evidence. The case-study design keeps that artefact tied to a real sponsor roster and real broadcast conditions rather than to isolated logo images.

Bradford Bulls provides the applied context. The club's kit contains many simultaneous sponsor marks, and the footage includes close, medium and wide camera shots. The case is not statistically representative of every sport or club. Rugby contact creates distinctive deformation and occlusion, highlight editing changes the shot distribution, and the final training domain is the white home kit. The intended contribution is analytical depth and operational realism within a clearly stated boundary.

The unit of independence is the match. Earlier image-level splits placed near-identical neighbouring frames in both training and evaluation data: 51 of 56 validation frames had a training frame from the same source clip within two seconds. Such a split tests familiarity with scenes more than generalisation to new matches. The final design assigns every match group to one split only and reserves three complete matches for final evaluation.

Figure 3 shows the methodological sequence and the boundary around the claims. The research questions determine the evidence required; matches, rather than frames, form the independent units; and complete match groups are assigned separately to training, validation and held-out test roles. Only training matches fit the two detector systems, validation matches guide checkpoint selection and stopping, and held-out matches enter final evaluation directly. Evaluated detections may then feed the visibility prototype, but the dashed boundary separates those prototype outputs from the validated detection study.

![Figure 3. Research design and case boundary](LogoLens_MSc_Dissertation_v17_media/figure_03_research_design_case_boundary.png)

*Figure 3. Leakage-aware research design and case boundary. Train, validation and held-out matches have non-overlapping roles. The evaluated detection study is bounded to one club, the white home kit, broadcast and highlight footage, and three unseen test matches. Visibility aggregation consumes evaluated detections but remains beyond the prototype boundary and requires separate validation.*

## 3.2 Dataset construction, annotation and split

The final dataset contains 15 disjoint match groups: 14 named groups and one legacy source group retained wholly in training. Shot-aware sampling reduced temporal redundancy. Candidate frames were represented with DINOv2 embeddings, clustered and reduced to representative views so that annotation effort added camera diversity rather than adjacent copies of the same scene.

Frames were screened for the white home kit, usable broadcast content and sponsor visibility. Lighting labels were assigned manually because a global brightness statistic could not separate daylight from floodlit matches: stands and advertising boards remained dark in both conditions. This manual assignment is used for stratified reporting, not for model training. Annotations use horizontal bounding boxes around visible sponsor marks and 16 sponsor classes. Model-assisted pre-annotation was used on 304 of 584 images before manual correction.

| Split | Match groups | Images | Annotated boxes | Role |
| --- | ---: | ---: | ---: | --- |
| Train | 9 | 460 | 1,611 | Weight optimisation and augmentation |
| Validation | 3 | 63 | 127 | Checkpoint selection and stopping |
| Test | 3 | 61 | 165 | Final held-out evaluation only |
| **Total** | **15 disjoint match groups** | **584** | **1,903** | **16 sponsor classes** |

*Table 3. Final match-disjoint dataset. CCH has no box in the test split, so test mAP is calculated over the 15 represented classes.*

The held-out set spans all three camera-distance labels, both source resolutions and both lighting labels used in the dataset. Lighting is not independently balanced: every floodlit test image comes from M_CAS, so lighting and match are confounded.

| Property | Composition of the 61 test images |
| --- | --- |
| Matches | M_CAS: 24 images / 106 boxes; M_HFC: 28 / 41; M_HKR: 9 / 18 |
| Camera distance | 40 close-up, 13 medium, 8 wide |
| Lighting | 37 daylight, 24 floodlit |
| Source resolution | 52 frames at 1920 × 1080; 9 at 2560 × 1440 |
| Kit domain | White home kit only |

*Table 4. Composition of the held-out test set. Lighting rows cannot be interpreted as an independent causal lighting effect.*

Source frames retain their native 1920 × 1080 or 2560 × 1440 geometry rather than being exported to a padded intermediate canvas. Across 1,903 boxes, the median source mark is 70 × 48 pixels with median area 3,272 square pixels. The relevant scale is the resized model input: at 512 pixels, the median mark is approximately 19 × 23 pixels. This calculation is retained as implementation context, while the controlled resolution diagnostic is reported separately in Appendix B rather than treated as a principal result.

![Figure 4. Split and leakage](LogoLens_MSc_Dissertation_v17_media/figure_04_split_and_leakage.png)

*Figure 4. Match-disjoint dataset design and measured inflation on familiar match material. The familiar-material score is a leakage diagnostic, not a second test result.*

## 3.3 Detector systems and training protocol

RF-DETR Small was fine-tuned at input resolution 896. Training used AdamW, automatic mixed precision, exponential moving averages, a three-epoch warm-up, cosine learning-rate decay and early stopping. Augmentation included horizontal flips, small rotations, brightness and gamma variation, blur, motion blur and coarse dropout. The final EMA checkpoint was selected on validation data at epoch 36; training stopped at epoch 52 of a planned 60.

YOLO26 nano, small and medium checkpoints were trained on a YOLO-format conversion of the same annotations while preserving the same match assignments. All used input size 896 and early stopping with patience 30 over a maximum of 150 epochs. Recorded defaults included mosaic, HSV variation, scale and translation augmentation and horizontal flipping. In the actual runs, `mixup=0.0` and `copy_paste=0.0`; neither augmentation is claimed as an uncontrolled difference.

The comparison is a system-level accuracy comparison, not a pure architecture ablation. Held constant are the images, match split, input resolution, confidence floor, IoU rules and scoring code. Not held constant are parameter count, pre-training, optimiser and the full augmentation recipe. These differences are disclosed because they may contribute to the result. A matched YOLO latency benchmark was not recorded, so the model-family table does not claim a comparative efficiency result.

## 3.4 Evaluation design by research question

### 3.4.1 RQ1: detection accuracy, reliability and efficiency

Precision is the proportion of accepted predictions that match ground truth; recall is the proportion of ground-truth boxes detected; and F1 is their harmonic mean. Average Precision integrates precision and recall across confidence thresholds. The final evaluator retains predictions to confidence 0.01, producing 5,820 candidate boxes across 61 test images. It reports mAP@0.50, mAP@0.75 and COCO-style mAP@[0.50:0.95] because the stricter metrics are important for downstream box-area measurement.

The operating threshold of 0.35 is characterised from the completed test predictions rather than fixed from validation. Threshold-specific F1 is consequently descriptive, while threshold-free AP measures carry the stronger inferential weight. The sweep is retained in Appendix A so the sensitivity of the operating point remains visible.

Sparse support is handled explicitly. For every represented class, AP is reported with the number of ground-truth boxes. The conventional class mean is accompanied by a second mean restricted to classes with at least five boxes. Five is a pragmatic reporting rule, not a statistical threshold, so Appendix A also shows alternative cut-offs. CCH, with no held-out box, is reported as not measurable rather than assigned zero.

Three evaluation paths are compared as a reproducibility check: the RF-DETR training-framework evaluator, the earlier independent configuration and the corrected independent evaluator used for the headline. The spread across paths is reported rather than resolved by choosing the highest value. Familiar-match inference is analysed only to quantify leakage inflation.

RF-DETR efficiency was benchmarked after three warm-up images over all 61 test images, with CUDA synchronisation around prediction. Timing excludes decoding, file writing, tracking, persistence, frontend rendering and process start-up. Accuracy was measured on the untraced path; latency was measured on the traced, deployment-oriented path. Peak memory refers to PyTorch allocation during the timed loop, not total system VRAM.

### 3.4.2 RQ2: conditions of appearance and error selection

The final test predictions are stratified by camera distance, lighting, source resolution, match and ground-truth logo size. mAP@0.50, precision and recall are recalculated within each group. These are descriptive cuts of one held-out sample, not independent experiments. Lighting is interpreted particularly cautiously because it is confounded with match. Occlusion is not available as an instance-level test annotation, so it is represented only through purposively selected qualitative cases using the retained three-level scale: clear, partially covered and heavily covered. The cases include both detected and missed instances and are not used to estimate condition-level recall.

Qualitative examples are selected by reproducible error rules at confidence 0.35 and IoU 0.50. The clear-success frame is the perfect frame with the strongest maximum confidence, and the multi-logo frame has the largest matched-object count among the remaining perfect cases. Evaluator-level errors are audited at source resolution before qualitative selection. All 19 missed ground-truth boxes are reviewed to exclude annotations on scoreboards, broadcaster graphics and background regions; the miss panel contains the smallest visually verified in-scope kit-logo miss from a frame without an invalid missed annotation. All 14 unmatched predictions are also reviewed; the false-positive panel contains the highest-confidence visually verified model error, excluding plausible annotation omissions and indeterminate crops. Review decisions and crops are retained with the figure evidence. This procedure prevents visually attractive examples and reference-label gaps from being presented as model failures.

### 3.4.3 RQ3: prototype visibility transformation and validation boundary

RQ3 is evaluated as a design-and-auditability question. The analysis verifies that every quality-weighted aggregate can be traced through segments and detections to timestamps and source frames, and that direct measurements, model proxies and external scenario inputs remain distinguishable. It does not claim duration accuracy or human readability agreement because no manual timing reference or two-rater readability dataset has yet been completed.

The required future validation is specified in advance: manually time continuous appearances at native frame rate; compare automatic estimates at 1, 2, 5 and native frames per second; vary gap tolerance and minimum duration; test score sensitivity to component removal and alternative weights; and collect independent readability ratings balanced across size, blur, contrast and occlusion. This converts an evidence gap into a testable protocol without substituting implementation output for validation.

## 3.5 Ethics and reproducibility

The footage contains visible players and trademarks. The study does not identify individuals or infer sensitive attributes. Frames are reproduced only to demonstrate detector behaviour. Sponsor names are retained because class recognition is the task, but contractual amounts, sponsor charges and comparisons between clubs are not disclosed. Legacy commercial priority percentages are treated as external preferences, not participant data or model truth.

Reproducibility records include the dataset manifest, checkpoint, training configuration, package environment, random seed and result files, retained by the author and available on request. The final RF-DETR run uses RF-DETR 1.9.1, PyTorch 2.11 with CUDA 12.8 and an RTX 5060 Ti 16 GB.

Annotation was principally completed by one researcher, and model-assisted pre-annotation may create consistent but model-shaped boundaries. This is a direct threat to the mAP@0.75 claim. An independent annotation audit is therefore listed as future validation rather than assumed.

---

# Chapter 4: Model and System Development

## 4.1 System architecture and logo detection

LogoLens separates model inference from reporting. The backend ingests video, reads frame metadata, samples frames, runs the selected detector and stores a common detection record. The Logo Analytics frontend presents processed videos, brand summaries and exports. This separation allows the detector to change without rewriting the reporting interface, provided every backend returns the same core fields: class, confidence, bounding box, frame index and timestamp.

![Figure 5. System architecture](LogoLens_MSc_Dissertation_v17_media/figure_05_system_architecture.png)

*Figure 5. LogoLens processing pipeline. The stage-3 inset shows RF-DETR Small and YOLO26 as alternative backends behind one adapter; both return the same record schema, and final reports remain traceable to source frames.*

The current checkpoint is RF-DETR Small at resolution 896. Native-aspect frames are supplied to the model, which performs the configured internal resizing. The output is a set of predicted class identifiers, confidences and horizontal boxes. RF-DETR uses set prediction and returns final predictions without a conventional non-maximum-suppression stage. The YOLO26 baseline also uses its default end-to-end head, so both systems are integrated through the same detector-adapter interface rather than distinguished by an assumed NMS requirement. Several sponsor marks can be returned from one frame, including repeated instances of one class; the held-out evidence in Section 5.5 includes a frame in which twelve marks are detected simultaneously.

The confidence threshold is 0.35 for the characterised test operating point. As Section 3.4.1 explains, a strict deployment protocol would select this value on validation data and lock it before the final test; threshold-free AP measures therefore remain the stronger final metrics.

Class mapping is a critical engineering detail: the standalone detector reads its category table directly from the training COCO file, and an older backend configuration used a different, non-matching class order that could silently shift brand labels even when boxes are visually correct (Appendix D gives the configuration difference in full). This is why the June full-video exports are not presented as final RF-DETR results. The model service must be pinned to the final checkpoint, variant, resolution and category mapping before batch analysis is repeated.

## 4.2 Visibility quality and duration measurement

Each detection supplies directly observed geometry and a model output. Let \(A_i\) be the predicted box area for detection \(i\), \(A_f\) the frame area, \(d_i\) the Euclidean distance between the box centre and frame centre, \(W\) the frame width, and \(c_i\) the detector confidence.

The choice of broad inputs is literature-informed, but the exact score is not taken from a published formula. ExposureEngine derives on-screen coverage and exposure duration from detector geometry (Sarkhoosh et al., 2025). An automated sponsor-valuation patent identifies size, clarity, duration and position as possible quality factors (Katz et al., 2024), while Nielsen's public vBrand description similarly names duration, size and image clarity (Nielsen, 2017). None of these sources specifies or validates the functional form implemented in LogoLens. The following equation is therefore a **researcher-defined heuristic**:

\[
V_i = \operatorname{clip}_{[0,1]}\!\left(
\sqrt{\frac{A_i}{A_f}}
\times \exp\left[-\frac{d_i^2}{(0.3W)^2}\right]
\times c_i
\right).
\]

The square root compresses the influence of area, and the Gaussian term gives the frame centre the largest weight. Both transformations, including the width scale of \(0.3W\), are project design choices. Multiplication is also a design choice: it makes a low value in any component reduce the whole score. Confidence is model certainty rather than an independent measurement of sharpness or human readability. The implementation contains a dormant oriented-box factor fixed at 1.0; because both evaluated detectors produce horizontal boxes, it has no effect and is omitted from the equation.

The score therefore mixes the three categories defined in Section 2.4 - measured geometry, a model-derived proxy and researcher-defined transformations - and is transparent and reproducible but not a validated human-perception measure.

Temporal aggregation groups detections by brand and track. At sampling rate \(f_s\), one sample represents \(\Delta t = 1/f_s\) seconds. Detections below a visibility floor of 0.02 are excluded. A gap larger than 2.5 sampling intervals splits the run into two segments. Segment end is extended by one interval because a sampled frame represents an interval rather than an instant. Runs shorter than 0.5 seconds are removed as flicker. The current duration weight is 0.5 below one second, 1.0 from one to five seconds and 1.2 above five seconds. These thresholds and weights are also researcher-defined engineering settings, not published perceptual constants. Quality-weighted exposure for a brand is

\[
Q = \sum_{s=1}^{S} \bar{V}_s \times w_s \times T_s,
\]

where \(\bar{V}_s\) is mean frame visibility in segment \(s\), \(w_s\) its duration weight and \(T_s\) its estimated duration. Raw on-screen seconds must be reported alongside \(Q\), because the weighted number is otherwise difficult to interpret.

![Figure 6. Visibility aggregation](LogoLens_MSc_Dissertation_v17_media/figure_06_visibility_aggregation.png)

*Figure 6. From detection records to prototype visibility evidence. The inset distinguishes measured geometry, model-derived confidence and researcher-defined transformations; the final outputs still require manual timing and readability validation.*

## 4.3 Reporting and interpretation

The reporting layer presents two principal sponsor-level outputs: **raw visible time** and **quality-weighted exposure**. Raw visible time estimates how long a detected logo remains on screen. Quality-weighted exposure adjusts that duration using the frame-level heuristic defined in Section 4.2. The two should be reported together because the weighted value is less directly interpretable and depends on researcher-defined assumptions.

The term **Logo Visibility Score** refers to a normalised summary of quality-weighted exposure within a stated video or collection. Any percentage must identify its denominator; for example, a sponsor may account for a share of the total detected exposure in one video. It must not be interpreted as viewer attention, sponsorship return or contract value.

The interface also presents a brand-level visibility timeline. Each sponsor occupies one row, while coloured bars show the start and end of retained visibility segments along the video time axis. Hover labels expose the exact interval and the playhead supports navigation back to the relevant moment. The timeline therefore makes visible time inspectable before it is reduced to a sponsor-level total.

Every summary remains traceable to its contributing temporal segments, timestamps and source frames, so a reviewer can inspect the evidence behind an aggregate rather than accept an unexplained score. As Section 2.4 sets out, that traceability does not yet extend to validation against human judgement or manual timing.

## 4.4 A worked example: from detection to score

To make Section 4.2 concrete, this section traces one real detection through the full transformation. The example is the highest-confidence prediction behind the clear-success case in Figure 9 Panel A: a KLG mark detected in a 1920 × 1080 medium-shot frame from match M_CAS, 21.000 s into the clip. The predicted box is [1487.1, 417.1, 85.9, 51.5] pixels at confidence \(c_i = 0.925\), matched to its ground-truth box at IoU 0.85 - one of the 146 operating-point true positives reported in Section 5.1.

| Term | Value | Source |
| --- | ---: | --- |
| \(A_i\) (predicted box area) | 4,422 px² | 85.9 × 51.5 px |
| \(A_f\) (frame area) | 2,073,600 px² | 1920 × 1080 |
| \(\sqrt{A_i/A_f}\) | 0.046 | size term |
| \(d_i\) (centre distance) | 578 px | box centre (1530, 443) vs frame centre (960, 540) |
| \(\exp[-d_i^2/(0.3W)^2]\) | 0.365 | position term, \(W = 1920\) |
| \(c_i\) (detector confidence) | 0.925 | model output |
| \(V_i\) | **0.016** | product of the three terms |

*Table 7. Term-by-term computation of frame-level visibility for one held-out detection.*

The result is instructive precisely because it is unremarkable: a confident, accurately localised detection still produces a low score. Box area is 0.21% of the frame, consistent with the median annotated mark occupying well under 1% of a broadcast frame (Section 3.2), so the size term alone caps \(V_i\) near 0.05 regardless of how central or confident the detection is. The position term then roughly halves that ceiling again, because the mark sits 578 pixels from frame centre in a 1920-pixel-wide image - a routine distance for a shirt logo that is not the subject of the shot. Confidence, at 0.925, is the least influential factor of the three.

This is the practical meaning of the multiplicative design choice explained in Section 4.2: a reviewer reading \(V_i = 0.016\) in isolation cannot tell whether the mark was small, off-centre, uncertain, or all three, without retrieving the intermediate terms in Table 7. That retrieval is what Section 4.3 means by traceability - the score is auditable because \(A_i\), \(d_i\) and \(c_i\) remain attached to the record that produced it, not because 0.016 is self-explanatory on its own.

The same detection illustrates temporal aggregation. If neighbouring sampled frames continue to match the same box within the 2.5-interval gap tolerance, this 0.016 becomes one sample contributing to a segment mean \(\bar{V}_s\); the duration weight \(w_s\) and segment length \(T_s\) from Section 4.2 are applied to that mean, not to any single frame. A brief, off-centre appearance like this one therefore has limited influence on the resulting \(Q\) unless it recurs across many consecutive frames - a claim about persistence that has not yet been checked against manually timed footage (Section 3.4.3).

---

# Chapter 5: Experiments and Results

## 5.1 Training trajectory and held-out detection evidence

The training trajectory in Figure 7 provides the context for the final result. Across epochs 0–51, composite training loss fell from 35.835 to 3.072 and validation loss from 12.231 to 3.739. Because this is the framework's weighted composite objective rather than a directly comparable risk estimate, the two curves are interpreted by their trajectories rather than by their absolute gap. Most improvement occurred in the first ten epochs; thereafter validation loss fluctuated within a narrower range while EMA validation mAP@[0.50:0.95] continued to improve more gradually. The selected checkpoint is epoch 36, where the EMA validation metric reached its maximum of 0.741. Later epochs did not improve that selection criterion. This is why the held-out result is attached to the selected checkpoint rather than to the final training epoch.

![Figure 7. RF-DETR training and held-out evidence](LogoLens_MSc_Dissertation_v17_media/figure_07_training_and_heldout_evidence.png)

*Figure 7. RF-DETR Small training and held-out evidence. (a) Composite training and validation loss across the two retained runs joined at the resume boundary. (b) Regular and EMA validation mAP@[0.50:0.95], with epoch 36 selected by the maximum EMA value. (c) Operating-point confusion matrix at confidence 0.35 and IoU 0.50; colour is normalised by ground-truth row, labels show raw counts, and orange cells identify misses or unmatched predictions. “No object” denotes misses and unmatched predictions. (d) Per-brand AP@0.50 with held-out support in parentheses; grey identifies classes with fewer than five boxes. CCH is omitted from panels (c) and (d) because the held-out set contains no CCH ground truth and its AP is not estimable.*

On the three unseen matches, the selected checkpoint achieved mAP@0.50 of 0.933, mAP@0.75 of 0.917 and mAP@[0.50:0.95] of 0.747. The small gap between the first two metrics indicates that most accepted boxes remain well localised at the stricter overlap requirement, which is important because screen coverage is calculated from box geometry.

The confusion matrix in panel (c) contains 146 correct detections, 19 misses and 14 false positives, with no matched brand-to-brand confusion. The observed operating-point errors therefore arise from missing a logo or adding an unmatched detection rather than assigning an overlapping logo to the wrong sponsor.

The per-brand result prevents the aggregate mean from hiding uneven evidence. Among the eleven brands with at least five test boxes, AP@0.50 ranges from 0.832 for ATM to 0.984 for Aon. The three values of 1.000 belong to brands represented by only one or two boxes and must not be interpreted as stable perfect performance; CCH has no test ground truth and is not estimable. Appendix A retains the complete class table, evaluator agreement and threshold sensitivity. The separately measured prediction path averaged 50.5 ms per image, or 19.8 FPS, on the stated GPU; Section 3.4.1 defines the timing boundary.

## 5.2 Reliability of the headline result

Three checks determine how much weight the headline can carry: agreement between evaluators, support behind each class and the effect of temporal leakage.

The same checkpoint and test images were scored by the RF-DETR training-framework evaluator, the earlier independent configuration and the corrected independent evaluator. Their mAP@0.50 values span 0.0065, while the two valid mAP@[0.50:0.95] values differ by 0.0030. The residual differences arise from the maximum-detections configuration and traced versus untraced inference paths. Appendix A reports the rows in full. Taking the lowest value from each valid column does not change the conclusion.

The conventional class mean needs a support qualification. Four of the fifteen represented classes contain fewer than five held-out boxes: one box each for Chadlaw and MNA Support Services, two for MNA Cladding and three for Fairway. These seven boxes form 4.2% of the test evidence but 26.7% of the class-averaged mean. Three sparse classes score AP@0.50 of 1.000; with one ground-truth box, that value can only be 1.000 or 0.000 and is not a stable capability estimate. Removing classes below five boxes reduces mAP@0.50 from 0.9335 to 0.9169. The 1.7-point difference is modest but reported alongside the headline because it is systematic.

Temporal leakage creates a larger distortion. Applying the final checkpoint to familiar match material gives mAP@0.50 of 0.998 and F1 of 0.988, compared with 0.933 and 0.898 on unseen matches. The difference represents evaluation optimism rather than model improvement. A frame-level split would therefore have supported a much stronger operational promise than the unseen-match evidence allows.

The aggregate is not carried by one test match. Separate match scores are 0.973 for M_CAS, 0.934 for M_HFC and 0.976 for M_HKR. The 0.042 spread is reassuring but remains descriptive because the test contains only three independent matches.

## 5.3 YOLO26 and RF-DETR accuracy comparison

The local comparison tests whether the selected RF-DETR result is simply a consequence of the improved data split and input resolution. YOLO26 nano, small and medium models were trained on the same match-disjoint images at input 896 and rescored using the same evaluator and confidence floor.

| Model | Parameters | GFLOPs | mAP@0.50 | mAP@0.75 | mAP@[.50:.95] | Characterised F1 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| YOLO26-n | 2.5M | 5.9 | 0.551 | 0.485 | 0.389 | 0.691 |
| YOLO26-s | 10.0M | 22.8 | 0.772 | 0.673 | 0.552 | 0.810 |
| YOLO26-m | 21.8M | 75.1 | 0.747 | 0.618 | 0.529 | 0.822 |
| **RF-DETR Small** | **31.8M** | **not recorded** | **0.933** | **0.917** | **0.747** | **0.898** |

*Table 5. Detector systems under one accuracy-evaluation protocol on the same three held-out matches. This is not a matched efficiency comparison.*

RF-DETR leads the strongest YOLO26 result by 16.1 points at mAP@0.50 and 24.4 points at mAP@0.75. The widening gap at stricter IoU is consistent with better localisation on this test set, but it does not by itself identify which component caused the difference. It may reflect backbone pre-training, optimisation, augmentation, capacity, set-based prediction or interactions among them.

Capacity alone does not order the YOLO results: the medium model has more than twice the parameters and over three times the reported GFLOPs of the small model, yet its mAP is lower while its characterised F1 is slightly higher. This is evidence that selecting the largest YOLO variant would not have closed the local accuracy gap. It is not evidence that the medium model overfit, because no controlled capacity ablation or training-gap analysis was conducted.

The defensible conclusion is system-level: under the recorded fine-tuning recipes, RF-DETR Small is substantially more accurate for these small sponsor marks. The comparison does not isolate architecture because pre-training, parameter count and augmentation are not equal. The YOLO logs record mosaic, HSV, scale, translation and flipping, with mixup and copy-paste both disabled; the discussion therefore refers to different recipes without claiming augmentations that did not occur. Matched latency, memory and energy measurements are still required before one system can be called more efficient than the other.

## 5.4 Performance across held-out broadcast conditions

RQ2 concerns variation in detection performance under the conditions present in unseen footage. The held-out set supports quantitative comparisons by camera distance and logo size, while lighting and source resolution are retained only as confounded descriptive checks. Occlusion is illustrated qualitatively because it was not independently annotated across the complete test set. None of these conditions is treated as a balanced experimental intervention.

Camera distance produces the clearest operational result. Close-up images contain 126 boxes and achieve mAP@0.50 of 0.927 with recall of 0.897. Medium shots contain 33 boxes and achieve mAP@0.50 of 1.000 with recall of 0.909. In contrast, the eight wide images contain only six boxes and achieve mAP@0.50 of 0.624 with recall of 0.500. Wide-shot precision is 1.000, indicating that the detector primarily fails through missed logos rather than additional false detections. This creates a predictable downward bias when estimating exposure during wide play.

Logo-size results support the same failure pattern at the smallest scale, although the relationship is not monotonic. Recall is 0.667 for the six boxes below 30 pixels, ranges from 0.894 to 0.966 across the 30-to-80-pixel groups, falls to 0.762 for 21 boxes between 80 and 120 pixels, and returns to 0.923 above 120 pixels. Size alone therefore does not explain every error; deformation, rotation and occlusion may contribute, but were not independently annotated.

Figure 8 makes that limitation visible through four held-out instances rather than presenting occlusion as a measured subgroup. Panel A is an unobstructed Top Notch mark detected at confidence 0.915. Panel B is a partially covered Aon mark detected at 0.780, whereas the partially covered Aon mark in Panel C is missed. Panel D shows a heavily covered Fairway mark detected only just above the operating threshold, at 0.351. The contrast demonstrates that occlusion can coexist with both detection and failure; four purposive examples cannot establish an occlusion effect or a monotonic confidence relationship.

![Figure 8. Held-out occlusion examples](LogoLens_MSc_Dissertation_v17_media/figure_08_occlusion_examples_v2.png)

*Figure 8. Qualitative held-out examples using the three-level occlusion scale. Solid boxes denote matched ground truth, the dashed box denotes a missed ground-truth instance, and box colour identifies the sponsor class. These cases illustrate appearance conditions and model outcomes; they are not an aggregate clear-versus-occluded benchmark.*

The lighting and source-resolution comparisons do not support independent effects. Floodlit footage reaches mAP@0.50 of 0.973 compared with 0.903 in daylight, but all floodlit images come from one match. Similarly, the 2560 × 1440 subset reaches 0.976 compared with 0.941 for 1920 × 1080, but it contains only 18 boxes from the single M_HKR match. These differences cannot be separated from match composition.

The measured domain is also restricted to the white home kit. Away-kit footage changes both sponsor composition and foreground-background contrast and is therefore outside the evidence reported here. Overall, the condition analysis supports one firm conclusion: wide tactical views are the principal observed weakness. The other condition differences remain provisional because their groups are small or confounded.

## 5.5 Representative successes and failure modes

Figure 9 connects the aggregate results to visible detector behaviour using the selection and audit rules in Section 3.4.2. Panel A contains seven ground-truth logos, all matched without a false positive. Panel B, captured eight minutes and twenty-one seconds into a close-up sequence in match M_CAS, contains twelve logos across six of the fifteen represented sponsor classes - Aon, ASC Group, EM Workwear, KLG, MCP and Paints & Lacquers - all twelve matched without a false positive. A single frame carrying more than a third of the sponsor roster is a direct illustration of why closed-set multi-logo detection, rather than single-brand tracking, is the right unit of analysis for this kit. Panel C contains one visually verified KLG mark on a player's shorts; the small mark is missed without any false positive. Panel D is a verified negative-frame failure: it contains no annotated in-scope logo, yet two opponent-kit marks are predicted as Top Notch. Together, the error panels show sensitivity to small kit logos and confusion caused by logo-like marks on the opposing team.

![Figure 9. Held-out detection evidence](LogoLens_MSc_Dissertation_v17_media/figure_09_detection_evidence.png)

*Figure 9. Representative held-out outcomes from the selected RF-DETR Small EMA checkpoint (epoch 36), regenerated at confidence 0.35 and IoU 0.50. Box colour identifies the sponsor class; solid boxes are correct predictions, short-dashed boxes labelled FP are false positives, and long-dashed boxes labelled Missed are missed ground truth. Source frames retain their natural colour, and cases were selected by the predefined rules in Section 3.4.2.*

These examples perform different evidential roles. Panels A and B show that the model can resolve repeated and simultaneous sponsor instances. Panels C and D reveal the two downstream risks: silent misses reduce estimated duration, while opponent-kit confusion can assign exposure to the wrong sponsor. Neither risk is captured by a headline mAP alone.

The annotation audit qualifies both raw error counts. Of 19 missed ground-truth boxes, 12 are visually verified in-scope kit logos, three are plausible but not sufficiently legible for firm confirmation, and four are invalid non-kit annotations on broadcast graphics or background regions. Of 14 unmatched predictions, three are visually verified wrong-brand or opponent-kit errors, one is a duplicate detection, eight are plausible annotation-omission candidates and two remain indeterminate at the available image quality. The reported precision and recall remain results against the frozen held-out annotations and are not retrospectively adjusted, but the raw FP and FN counts should not be interpreted as fully verified visual errors.

## 5.6 Prototype visibility and duration outputs

The temporal layer answers RQ3 as a transparent implementation, not as a validated accuracy result. A detection record can be followed from class, confidence, box and timestamp into a brand track, a continuous segment, raw estimated seconds and quality-weighted seconds. The reporting layer retains those intermediate records, allowing a reviewer to inspect the source frames behind an aggregate.

Figure 10 shows the implemented visibility-time view. Rows separate sponsor classes and the horizontal axis represents elapsed video time. Each coloured bar is a retained interval between a segment start and end, rather than an individual frame detection; repeated bars therefore reveal when a brand disappears and later returns. The interactive tooltip reports the selected brand and time interval, while the vertical playhead links the overview to a specific moment in the video. This representation adds temporal structure that a single total-duration value would hide.

![Figure 10. Prototype visibility timeline](LogoLens_MSc_Dissertation_v17_media/figure_10_visibility_timeline.png)

*Figure 10. Prototype brand-level visibility timeline in the LogoLens reporting interface. Colour distinguishes sponsor classes, horizontal position encodes video time, and each bar represents a continuous detected segment. The interface demonstrates traceability and temporal reporting; the displayed intervals are not treated as validated duration ground truth.*

The existing June workbooks are not treated as final results. They were produced before the final RF-DETR checkpoint and use backend model and class configurations that do not match the revised home-kit system. Four also concern away-kit footage outside the training domain. Reusing them would mix model versions, category semantics and unsupported input, so Appendix D retains them only as provenance.

As in Section 4.2, the 2.5-interval gap tolerance, 0.5-second minimum segment and duration weights are design choices, not validated against manual duration or readability - so no EMV total is reported.

One result predicts the likely direction of duration error: recall falls to 0.500 on wide shots. A full-match analysis using the present detector should therefore under-estimate exposure in passages dominated by wide camera work. Manual timing across sampling rates and gap settings can test that prediction directly.

## 5.7 Research-question synthesis

| Research question | Supported conclusion | Evidence boundary |
| --- | --- | --- |
| RQ1 | RF-DETR reaches 0.933 mAP@0.50, 0.917 mAP@0.75 and 0.747 mAP@[.50:.95] on three unseen matches; the support-restricted mAP@0.50 is 0.917. It exceeds the strongest YOLO26 baseline by 16.1 points at mAP@0.50 under one accuracy protocol and runs at 19.8 prediction FPS. | Three matches and 165 boxes; four sparse classes and one absent class; no matched YOLO latency benchmark; augmentation and pre-training differ. |
| RQ2 | Camera distance is the clearest measured condition: recall is approximately 0.90 in close and medium views but falls to 0.500 in wide shots. The detector therefore risks under-counting exposure during wide play. | Wide subset has six boxes; lighting and source resolution are confounded with match; deformation and occlusion are not independently annotated. |
| RQ3 | Detections are transformed into auditable segments, raw seconds and quality-weighted seconds with traceable intermediate records and explicit assumptions. | Duration, readability and score weights are not validated against human reference data; operational accuracy is not claimed. |

*Table 6. Research-question conclusions and the evidence boundary attached to each.*

---

# Chapter 6: Discussion

## 6.1 Detection performance and model choice

RQ1 is answered positively within the measured home-kit domain. RF-DETR Small identifies repeated and simultaneous sponsors on unseen matches with strong presence and localisation accuracy, and its isolated throughput is sufficient for the intended 2 FPS analytics rate. The support-restricted mAP@0.50 of 0.917 is the most useful planning figure because it removes four classes whose apparent accuracy rests on seven boxes while retaining 158 of 165 test instances.

The leakage result explains why the evaluation design is part of the contribution rather than an administrative detail. A score of 0.998 on familiar match material would suggest nearly complete capture, whereas the unseen-match operating point misses 19 of 165 marks. This agrees with the broader sports-video concern that adjacent frames cannot be treated as independent examples (Deliège et al., 2021). For a commercial report, the difference is not cosmetic: it separates evidence of future-match generalisation from evidence of scene familiarity.

The YOLO26-RF-DETR comparison supports a practical system choice but not a universal architecture claim. Data, split, input resolution and scoring are controlled, so the 16.1-point mAP@0.50 advantage is relevant to an implementer choosing between these trained systems. Pre-training, optimisation, capacity and augmentation remain different. DINOv2 initialisation may be particularly valuable in a small specialist dataset, while the YOLO26 small-target mechanisms may require a different tuning regime to realise their potential. The result should therefore be read as “RF-DETR Small worked better here under the recorded recipes”, not “transformers always outperform convolutional detectors”.

Efficiency remains asymmetric. RF-DETR inference is measured, but equivalent YOLO latency, memory and energy figures are not. YOLO26 may offer a more attractive deployment trade-off even while producing lower accuracy. The next comparison should therefore plot accuracy against latency on the same hardware rather than treat parameter count or GFLOPs as a substitute for measured runtime.

## 6.2 From detection error to visibility bias

RQ2 reveals the mechanism that connects object detection to sponsor reporting. Input preprocessing changes how many model pixels represent a mark, and camera distance changes whether those pixels exist in the first place. The 10.4-point controlled resolution gain and the fall to 0.500 recall on wide shots are two observations of the same small-object constraint described in the literature (Liao et al., 2017).

The wide-shot error pattern matters more than its aggregate size. Precision is 1.000 while recall is 0.500, so the detector usually does not invent remote logos; it fails to record them. A temporal report will therefore be biased downward in passages with wide camera work. Because highlight clips favour close views, the current test distribution may understate that operational problem for full broadcasts.

The non-monotonic size result also limits interpretation. Large source boxes can be folded, rotated or occluded chest marks, while small boxes can be clean static views. Horizontal boxes and confidence alone cannot separate these factors. A future human-readability study should therefore stratify by size, camera distance, blur, contrast, deformation and occlusion rather than assume size is a sufficient proxy.

RQ3 is deliberately narrower than an accuracy claim: the implemented transformation is transparent, but transparency does not validate the weights. The distinction between “code produces a score” and “the score agrees with human judgement” is essential to construct validity.

## 6.3 Practical meaning for a smaller club

The measured throughput supports a practical review workflow for in-domain highlight footage. At 2 sampled frames per second, RF-DETR prediction has roughly tenfold headroom before decoding, tracking and reporting are added. A staff member could inspect sponsor summaries and jump to supporting frames instead of watching every video manually.

Accessibility should be framed as demonstrated capability, not demonstrated cost advantage. Training took approximately 2.5 hours on a 16 GB consumer GPU, and isolated inference reached 19.8 FPS. These measurements exclude annotation labour, maintenance, video rights, hardware purchase and seasonal retraining. They show that local operation is technically feasible; they do not show that it is cheaper than a managed service.

The more certain practical benefit is auditability. A sponsor summary should show the model version, category mapping, threshold, sample rate and number of supporting detections. It should distinguish “no appearance detected” from “brand outside the measured domain”. Commercial priority weights may be added as external inputs, but should never be presented as observed visibility or detector ground truth.

Routine deployment still requires three safeguards: the backend must be pinned to the evaluated checkpoint and category table; away-kit footage must be withheld until supporting data exists; and a domain gate should flag unsupported kit or broadcast conditions before producing a report. A confident result on out-of-domain footage is more dangerous than an explicit refusal.

## 6.4 Generalisability beyond rugby league

The evidence in this dissertation is bounded to one sport, one club and one kit, so any extension beyond rugby league is a hypothesis rather than a tested claim. Three properties of the present result plausibly transfer. First, the small-object constraint identified in Sections 2.2 and 6.2 - a median mark of 70 × 48 source pixels shrinking further under model resizing - is a property of shirt-mounted sponsorship generally, not of rugby specifically; football, rugby union and other kit-sponsored team sports share the same geometry and would be expected to show a comparable size-driven recall pattern. Second, the wide-shot recall failure documented in Section 5.4 follows from camera distance rather than from the sport's rules, so any broadcast that alternates between close and wide coverage - which describes most televised team sport - should show the same asymmetry in some form. Third, the closed-set architecture (Section 2.2) transfers mechanically to any fixed sponsor roster: retraining on a new sport's kit and sponsor set requires new annotated data and a new category mapping, but not a different detection paradigm.

Two properties are less likely to transfer without adjustment. Rugby league's high-contact play produces occlusion and fabric deformation at a rate that lower-contact sports such as cricket or athletics would not reproduce, so the occlusion-related failure modes illustrated in Figure 8 may be less prominent - and reasoning about confidence near the operating threshold correspondingly less urgent - in a non-contact setting. Static perimeter and pitch-side signage, which this dissertation does not evaluate, would remove the deformation problem entirely but reintroduce the wide-shot distance problem at a larger and more consistent scale, since board text does not move with a player. Testing either hypothesis would require the same match-disjoint evaluation design used here, applied to new footage; no claim beyond that design's applicability is made.

## 6.5 Limitations and threats to validity

**Internal validity.** Model-assisted pre-annotation and a primarily single-annotator process may create systematic box boundaries. This matters directly to mAP@0.75 and requires an independent annotation audit. The operating threshold was characterised on test predictions rather than fixed on validation; the flat sweep limits but does not remove this concern.

**Construct validity.** Box area measures rectangular screen coverage, not visible logo area under occlusion. Confidence is model certainty, not clarity or human readability. Screen centrality and duration weights are design assumptions. Quality-weighted seconds are consequently prototype outputs rather than a validated perception scale.

**External validity.** The test contains three unseen matches, one sport, one club and one white home kit. It includes 165 boxes and only six boxes in wide-shot images. Results cannot be generalised to the away kit, another season, another broadcaster, static perimeter boards or unknown sponsors without new evidence.

**Conclusion validity.** Sparse classes can produce AP of 1.000 from one or two boxes. Reporting support and a restricted mean limits overstatement but does not replace a larger test set. The architecture comparison remains a system comparison with uncontrolled pre-training, capacity and training recipe. Condition cuts are descriptive and lighting is confounded with match.

**Operational validity.** Full-video workbooks from the earlier pipeline do not use the evaluated checkpoint and class mapping. They are excluded from the findings. Until manual duration and readability studies are complete, the system can support detection review and prototype aggregation but not a validated sponsor-value claim.

---

# Chapter 7: Conclusion and Future Work

## 7.1 Conclusion and contributions

This dissertation developed and evaluated a closed-set sponsor-logo detector and connected it to a transparent prototype for visibility measurement. On three held-out matches, RF-DETR Small achieved mAP@0.50 of 0.933, mAP@0.75 of 0.917, mAP@[0.50:0.95] of 0.747 and best F1 of 0.898, with isolated inference at 19.8 FPS. The result is strong for this dataset, but its meaning depends on the accompanying evidence: only 11 classes have at least five test boxes, wide-shot support is small, and a leakage diagnostic showed that familiar match material can inflate mAP@0.50 from 0.933 to 0.998.

The technical contribution is a modular route from video to traceable frame records, detections, temporal segments and sponsor summaries. That separation, demonstrated concretely in Section 4.4, is what allows the detector to be retrained or replaced as seasons and sponsors change without rebuilding the reporting layer a club would actually use. The methodological contribution is the evaluation design: match-disjoint splitting, support-aware reporting, independent evaluator checks, condition cuts and error-rule-based qualitative evidence. Together these choices are what let the headline mAP@0.50 of 0.933 be read as a claim about unseen matches rather than about familiar footage - a distinction Section 5.2 shows to be worth 6.5 points. The comparative contribution is a controlled system-level accuracy benchmark in which RF-DETR outperformed three YOLO26 baselines on the same split, input size and scoring code. This comparison supports the selected implementation for the present small-data task; it does not establish a universal architectural ranking.

The visibility framework is an implemented and auditable design contribution rather than a validated perception or valuation model, answering RQ3 without turning unvalidated prototype output into an empirical claim. Its practical value is what a proprietary vendor report cannot offer: a number that can be taken apart into the frames, detections and design choices that produced it.

## 7.2 Priority future work

Future work should follow the evidential bottlenecks identified in the study, in this order:

1. **Control the operational domain.** Pin the evaluated checkpoint and category mapping, record the threshold and sampling rate in every report, and reject or flag away-kit and unsupported broadcaster footage, so that any report inherits the accuracy characterised here rather than accuracy from an unpinned configuration.
2. **Strengthen the held-out test.** Add independent matches, deliberately sample wide tactical views, increase support for the four classes with fewer than five test boxes, and include CCH, which is absent from the current test - the single largest source of uncertainty behind Table 6.
3. **Complete a matched deployment benchmark.** Measure YOLO26 and RF-DETR latency, memory use and end-to-end video throughput on the same hardware and decoding pipeline, since the efficiency comparison in Section 6.1 is currently one-sided and supports accuracy selection only.
4. **Validate temporal and perceptual measures.** Compare automatic duration with native-frame-rate manual timing at several sampling rates and gap settings. Collect two-rater readability judgements and test whether the proposed proxies predict them; this is the step that would let a duration figure be reported as fact rather than as implementation output.
5. **Audit sensitivity and annotation quality.** Report inter-annotator agreement on a stratified subset and vary the components and weights of the Logo Visibility Score. Closing this gap is a precondition for trusting the mAP@0.75 result specifically (Section 3.5), not only the Logo Visibility Score; segmentation, oriented boxes and open-set retrieval should be considered only after this simpler measurement chain is validated.
6. **Explore regulation-guided automatic pre-annotation across clubs.** The present dataset covers one club because annotation was manual and mostly single-researcher work (Section 3.5). Within one league, kit regulations fix where a sponsor mark may sit relative to a shirt's seams and panels, so clubs differ mainly in colourway and brand imagery rather than in mark placement. This has not been tested, but it suggests a concrete way to reduce annotation cost when extending to a second club: a reference kit's annotated mark regions could seed a geometric prior for a new kit in the same league, producing draft boxes for correction rather than boxes drawn from nothing. The risk is the same one already identified in Section 4.1's class-mapping error - a template mismatch would produce confidently placed boxes in the wrong location rather than an obvious gap - so any such pipeline would need the audit discipline used for Figure 9 applied to its own output before it could be trusted, not before.

## 7.3 Final takeaway

LogoLens demonstrates that accurate in-domain sponsor-logo detection is feasible on consumer hardware and that its evidence can be made traceable to individual frames. Its central contribution is not one authoritative visibility number - the duration and quality summaries still require human validation before operational or commercial use - but a measurement chain whose evidence, assumptions and failure boundaries are visible to the reader.

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

Jocher, G., Qiu, J., Liu, M., Lyu, S., Akyon, F.C. and Kalfaoglu, M.E. (2026) 'Ultralytics YOLO26: unified real-time end-to-end vision models', *arXiv:2606.03748*. https://arxiv.org/abs/2606.03748

Katz, J.B., Carter, C.N. and Kim, B.J. (2024) *Automated media analysis for sponsor valuation*. US Patent 12,124,509 B2, assigned to GumGum Sports Inc. https://patents.google.com/patent/US12124509B2/en

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

Sarkhoosh, M.H., Øye, F., Sørlie, H.N. et al. (2025) 'ExposureEngine: oriented logo detection and sponsor visibility analytics in sports broadcasts', *arXiv:2510.04739*. https://arxiv.org/abs/2510.04739

Su, H., Zhu, X. and Gong, S. (2018) 'Open logo detection challenge', in *British Machine Vision Conference*. https://arxiv.org/abs/1807.01964

Two Circles (2025) *Sports IP Revenue League: methodology and references*. Available at: https://twocircles.com/gb/articles/sports-ip-revenue-league-methodology-and-references/ (Accessed: 12 August 2026).

Zhang, Y., Sun, P., Jiang, Y. et al. (2022) 'ByteTrack: multi-object tracking by associating every detection box', in *European Conference on Computer Vision*, pp. 1-21. https://arxiv.org/abs/2110.06864

Zhao, Y., Lv, W., Xu, S. et al. (2024) 'DETRs beat YOLOs on real-time object detection', in *Proceedings of the IEEE/CVF Conference on Computer Vision and Pattern Recognition*, pp. 16965-16974. https://openaccess.thecvf.com/content/CVPR2024/html/Zhao_DETRs_Beat_YOLOs_on_Real-time_Object_Detection_CVPR_2024_paper.html

---

# Appendices

## Appendix A: Per-class held-out results

All values come from the corrected independent evaluation described in Section 3.4.1, on the 61 held-out test images. Classes are ordered by ground-truth support because support determines how much weight each row can carry. Rows with fewer than five boxes are marked; their AP values are reported for completeness and excluded from the restricted mean of 0.917.

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

The single-box classes demonstrate why support must accompany AP. Chadlaw and MNA Support Services each score AP@0.50 of 1.000 but AP@[0.50:0.95] of 0.600: the change records whether one box matches at each IoU threshold, not a stable class capability.

### A.1 Evaluator agreement

| Evaluation path | mAP@0.50 | mAP@0.75 | mAP@[.50:.95] | Best F1 |
| --- | ---: | ---: | ---: | ---: |
| RF-DETR training-framework evaluator | 0.9383 | not reported | 0.7441 | not reported |
| Independent script, earlier configuration | 0.9318 | 0.9149 | invalid under that configuration | 0.895 |
| Independent script, corrected configuration | 0.9335 | 0.9166 | 0.7471 | 0.898 |
| **Spread across valid paths** | **0.0065** | **0.0017** | **0.0030** | **0.003** |

*Appendix Table A1. Agreement between three evaluation paths on the same checkpoint and held-out images.*

### A.2 Threshold and support sensitivity

| Confidence | TP | FP | FN | Precision | Recall | F1 |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 0.20 | 148 | 35 | 17 | 0.809 | 0.897 | 0.851 |
| **0.35** | **146** | **14** | **19** | **0.913** | **0.885** | **0.898** |
| 0.50 | 133 | 9 | 32 | 0.937 | 0.806 | 0.866 |

*Appendix Table A2. Three representative points from the full confidence sweep. The selected value of 0.35 is a characterised operating point, not an independently estimated deployment threshold.*

| Minimum support | Classes retained | Test boxes covered | mAP@0.50 |
| --- | ---: | ---: | ---: |
| n ≥ 1 (conventional) | 15 | 165 | 0.9335 |
| n ≥ 2 | 13 | 163 | 0.9232 |
| n ≥ 3 | 12 | 161 | 0.9169 |
| **n ≥ 5 (reported alongside)** | **11** | **158** | **0.9169** |
| n ≥ 10 | 7 | 134 | 0.9378 |
| Support-weighted mean, all represented classes | 15 | 165 | 0.9293 |

*Appendix Table A3. Sensitivity of the reported mean to minimum test support.*

## Appendix B: Supporting optimisation diagnostic

| Fixed checkpoint inference input | mAP@0.50 |
| ---: | ---: |
| 512 | 0.776 |
| 768 | 0.880 |
| 896 | 0.878 |

*Appendix Table B1. Controlled inference-resolution sweep with one checkpoint held fixed. The improvement from 512 to 768 is retained as an implementation diagnostic; the plateau at 896 shows why it is not presented as a principal held-out result.*

## Appendix C: Architecture comparison protocol

The comparison in Section 5.3 was run as follows. YOLO26 nano, small and medium checkpoints were trained on a YOLO-format conversion of the same COCO dataset used by RF-DETR, produced by a category-preserving conversion utility that retained the match-disjoint assignment. All runs used input size 896 rather than the YOLO default of 640, and early stopping used patience 30 over a maximum of 150 epochs.

Scoring did not use either framework's internal validation metric. All four models were re-run over the same 61 test images at a confidence floor of 0.01, and the resulting detections were scored by one pycocotools configuration and one greedy IoU-0.50 confidence sweep. Class indices were mapped back from the YOLO ordering to the COCO category identifiers so that both families were compared against identical ground truth.

Held constant were the images, split, input resolution, evaluation code, IoU matching rule, confidence floor and evaluation hardware. The recorded YOLO recipe used mosaic, HSV jitter, scale, translation and horizontal flipping; both mixup and copy-paste were disabled. Pre-training, parameter count, backbone, optimisation and the complete augmentation recipes were not equal across model families. The experiment is consequently a system-level accuracy comparison, not a causal architecture ablation. A matched end-to-end latency and resource benchmark was not completed, so no relative efficiency claim is made.

## Appendix D: Legacy full-run file register

Eight full-match export workbooks from an earlier pipeline run are retained for provenance and must not be cited as final RF-DETR outputs. All eight were produced in June, before the final checkpoint and category mapping were fixed, under an older backend configuration whose category table used a different 17-brand order than the final training COCO file, including an away-kit sponsor and a spelling difference in ASC Group, and which defaulted to an RF-DETR Large path rather than the evaluated Small checkpoint. Four cover the white home kit and four cover away-kit footage that falls outside the training domain evaluated in this dissertation. Reusing any of them would risk silently shifted brand labels in addition to the model-version and kit-domain mismatches already noted.

## Appendix E: Figure provenance and AI disclosure

Figures 1, 2, 3, 5 and 6 are conceptual diagrams generated with OpenAI ImageGen. They organise concepts and system components; they do not contain measured values or constitute empirical evidence. Each image was visually inspected after generation. Figure 1 received a targeted edit to replace generic football thumbnails with neutral rugby scenes, and Figure 2 received a second edit to remove an incidental jersey number. Figures 2 and 3 shared this visual instruction:

> Clean academic layered system architecture diagram; PhD thesis figure style; research poster infographic; publication-ready; wide 16:9; white background; rounded modules; minimal flat vector icons; clear data-flow arrows; generous whitespace; deep maroon, charcoal, muted gold and pale grey palette; no real logos, club identity, unsupported metrics, decorative text, gradients, 3D elements or watermark.

The figure-specific final content instructions were:

- **Figure 1:** one input splits into `YOLO26 — convolutional route` and `RF-DETR — transformer route`, then converges on `Common output — class • confidence • box`. The YOLO26 lane contains a convolutional backbone, multi-scale feature fusion and a one-to-one detection head. The RF-DETR lane contains a DINOv2 visual backbone, projected feature maps and object queries with a decoder. The prompt excluded performance metrics, winner badges, layer-complete specifications and claims of architectural superiority.
- **Figure 2:** four modules, `Sponsorship accountability → Observable exposure → Leakage-aware computer vision → Auditable visibility evidence`; generic document/handshake, broadcast frame, detection and evidence-report icons; no numbers or icon text.
- **Figure 3:** eight stages from `Research questions` through match-separated data, a three-way leakage-safe split, parallel RF-DETR/YOLO26 training, validation-only selection, held-out evaluation and detection evidence. A dashed `PROTOTYPE BOUNDARY` separates visibility aggregation, marked `requires separate validation`, from the evaluated detection study. The lower case-boundary strip states `One club`, `White home kit`, `Broadcast & highlight footage` and `Three unseen test matches`. Rugby-specific icons replace football imagery.
- **Figure 5:** generated using a supplied pipeline diagram as a style-and-layout reference only. The prompt requested a white-background academic infographic with dark navy typography, six pale-tinted cards, thin multicolour outlines, numbered circular badges, simple line icons and navy arrows. Its six stages are `Video input → Frame sampling → Logo detection → Detection records → Temporal aggregation → Evidence report`. A dashed stage-3 inset shows `Common adapter` branching to the parallel alternatives `RF-DETR Small — selected system` and `YOLO26 — comparison baseline`, then merging into `Common output — class • score • box`. Percentages, EMV, team filtering, pose estimation and body segmentation were explicitly excluded.
- **Figure 6:** generated using Figure 5 as its design-system reference. Five numbered stages show `Detection record → Direct geometry → Frame-level proxy → Temporal segments → Exposure outputs`. A dashed stage-3 inset shows three parallel inputs — `Size term — measured geometry`, `Position term — design assumption` and `Confidence term — model-derived proxy` — converging on `Combined score — multiplicative heuristic`. The legend separates measured, model-derived, researcher-defined and validation-required elements. Equations, numerical constants, OBB penalties, pricing and commercial-value claims were excluded.

Figure 4 was generated deterministically from recorded measurement files, so its plotted values can be traced to recorded evaluation output. Figure 7 retained the loss and validation trajectory from the two training logs spanning epochs 0–51, the corrected per-brand AP values, and the confusion records reconstructed from the final checkpoint over the 61 held-out images at confidence 0.35 and IoU 0.50. Figure 8 retained the four held-out source frames, crops and RF-DETR matching records used to build the occlusion plate; the evidence explicitly marks the cases as qualitative rather than an aggregate occlusion benchmark. Figure 9 was produced from a fresh inference pass with the selected RF-DETR Small checkpoint over all 61 held-out images, applying the selection rules in Section 3.4.2; every unmatched prediction and missed ground-truth box behind it was reviewed at source resolution, using tight crops, before the final panels were fixed. Figure 10 is a direct capture of the implemented LogoLens reporting interface rather than a generated diagram; it demonstrates the temporal representation and is not used as manual duration ground truth.
