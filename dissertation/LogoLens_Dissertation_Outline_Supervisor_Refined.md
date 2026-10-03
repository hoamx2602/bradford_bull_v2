<!-- Converted from LogoLens_Dissertation_Outline_Supervisor_Refined.docx. The Word source remains unchanged. -->

**DISSERTATION WRITING OUTLINE**

**Developing and Evaluating a Computer Vision Framework for Sponsor-Logo Detection and Visibility-Quality Assessment in Sports Broadcasts**

*Supervisor-refined structure | MSc Applied Artificial Intelligence and Data Analytics | 12,000-word ceiling*

# Recommended word budget

The chapter budgets total 12,000 words. Confirm whether the University counts captions, tables and appendices within the limit.

| **Chapter** | **Main focus** | **Words** |
| --- | --- | --- |
| Chapter 1 | Introduction: business problem, AI opportunity and research focus | 1,200 |
| Chapter 2 | Literature Review: sponsorship measurement and computer vision | 2,200 |
| Chapter 3 | Research Methodology | 1,800 |
| Chapter 4 | Model and System Development | 1,600 |
| Chapter 5 | Experiments and Results | 2,500 |
| Chapter 6 | Discussion | 1,900 |
| Chapter 7 | Conclusion and Future Work | 800 |

# How to use this outline

- Use the three main sections in each chapter as the formal structure. The bullets are writing prompts, not additional headings.

- Keep the story business-led in Chapters 1, 2, 5, 6 and 7. Put the deeper computer vision detail in Chapters 3 and 4.

- For each paragraph, answer: what is the point, why does it matter, what evidence supports it, and how does it lead to the next point?

# Chapter 1: Introduction

Purpose: explain what the study is about and why it matters. Approximate budget: 1,200 words.

## 1.1 Sponsorship and the sports business context

**What this section must do:** Start with sponsorship, not technology. Build the business context before mentioning AI or rugby.

- Define sponsorship and explain why brands invest in it as part of marketing.

- Use recent statistics to show the size and commercial importance of the sponsorship market.

- Narrow the discussion to sports sponsorship and identify the main stakeholders: sponsors, clubs, leagues, broadcasters and audiences.

- Explain that sponsorship decisions are often based on experience, negotiated value and expected exposure, while objective evidence can be limited.

- Keep this section about sport in general. Introduce rugby only when the study itself is presented.

## 1.2 The measurement problem and the opportunity for AI

**What this section must do:** Move from the business problem to emerging technology, then to computer vision.

- Explain the practical questions: how often, how long and how clearly does a sponsor logo appear on screen?

- Show why manual video review is slow, inconsistent and difficult to repeat across many broadcasts.

- Briefly introduce emerging technologies used for evidence-based sponsorship measurement, then explain why AI and computer vision are relevant.

- Acknowledge existing products such as Nielsen Sports, Blinkfire and Relo Metrics. Treat vendor information as product context, not independent evidence.

- Explain the accessibility problem for smaller clubs. Only describe commercial systems as expensive or unsuitable when a reliable source supports that claim.

- Present Bradford Bulls and rugby broadcasts as the case study used to develop and test the proposed system.

- State clearly that the system measures on-screen visibility. It does not directly measure audience attention, sales, return on investment or the correct price of a sponsorship package.

## 1.3 Aim, objectives, research questions and scope

**What this section must do:** Keep the commitments short, testable and closely linked to the computer vision work package.

- Aim: Develop and evaluate a computer vision system that detects multiple sponsor logos and measures their visibility quality in sports broadcasts.

- Objective 1: Train and compare selected YOLO and transformer-based models for multi-logo detection.

- Objective 2: Measure logo size, screen coverage, visual quality, occlusion and human readability.

- Objective 3: Estimate visibility duration and combine the measured features into an interpretable Logo Visibility Score.

- RQ1: How accurately and efficiently can the selected models detect multiple sponsor logos in unseen sports footage?

- RQ2: How do logo size, screen coverage, blur, contrast and occlusion affect detection performance and human readability?

- RQ3: How accurately can frame-level detections estimate visibility duration and support an interpretable Logo Visibility Score?

- Scope: known Bradford Bulls sponsor logos in selected broadcast and highlight videos. The study focuses on logo visibility and does not analyse players, teams or detailed kit-location pricing.

- Contribution: a detection engine, a transparent visibility-measurement method, a Logo Visibility Score and an evaluation report for a smaller-club case study.

# Chapter 2: Literature Review

Purpose: explain what is already known, what is still uncertain and why the proposed study is needed. Approximate budget: 2,200 words.

## 2.1 Sponsorship measurement and the business problem

**What this section must do:** Review how sponsor value and exposure are currently understood before focusing on AI.

- Discuss sponsorship as a commercial relationship involving brands, sports organisations, broadcasters and audiences.

- Review traditional ways of judging sponsor exposure, including expert judgement, media monitoring and manual content analysis.

- Include evidence-based systems that may use sensors, IoT, broadcast monitoring or other analytical tools; do not limit the review to AI systems.

- Separate on-screen exposure from attention, brand recall, sales and return on investment.

- Use commercial platforms to show that the market already contains logo-tracking and sponsorship-analytics products, including systems that track logos on players.

- Discuss the practical gap for small and medium-sized clubs: access, transparency, local control, hardware requirements and cost evidence where available.

## 2.2 Computer vision for logo detection and visibility measurement

**What this section must do:** Narrow the review from AI in marketing to the model and measurement problems addressed in this dissertation.

- Explain how AI supports measurement and decision-making in marketing, then introduce computer vision for sponsor-logo analysis.

- Distinguish logo detection, logo recognition and logo retrieval in simple terms.

- Compare easier static placements, such as banners and pitch-side boards, with moving, small and partly hidden logos on player clothing.

- Explain that the current model is trained to recognise only the club's known sponsor logos because these are the brands the system needs to report on.

- Review the small-object challenge and compare YOLO, DETR, RT-DETR and RF-DETR in terms of accuracy, speed, memory and deployment needs.

- Review the effects of size, screen coverage, blur, contrast, compression and occlusion on detection and readability.

- Review methods for estimating how long a logo is visible from sampled video frames, including missed frames and short gaps.

- Explain why detection confidence alone is not a complete measure of visibility and why a small human-readability study is useful.

- Review transparent ways to combine size, clarity, occlusion and duration into a composite visibility score. Keep EMV separate as an optional commercial illustration.

## 2.3 Research gap and study framework

**What this section must do:** Bring the literature together and show exactly how it leads to the research questions.

- Use a traditional literature review with clear databases, search terms, date range and selection rules.

- Prioritise peer-reviewed work from the last five years, while retaining older foundational studies only where they are necessary.

- Include credible reports from government, sports organisations and recognised marketing bodies; label vendor material clearly.

- Summarise the main studies in one comparison table rather than describing every paper separately.

- Use careful gap wording: within the literature reviewed, no study was identified that provides the same transparent combination of multi-logo detection, visibility-quality measurement, duration validation and smaller-club deployment focus.

- Use a research framework, such as the Research Onion and design science, to explain the study choices. Discuss technology adoption or acceptance only if it genuinely fits the evidence collected; do not force it into a model-development study.

- End with a short map linking each literature theme to one research question and one part of the methodology.

# Chapter 3: Research Methodology

Purpose: explain how the study was designed, how the evidence was collected and how each research question will be tested. Approximate budget: 1,800 words.

## 3.1 Research design and case study

**What this section must do:** Show both the wider research logic and the technical development process.

- Describe the study as design science used to build an artefact, followed by a quantitative case-study evaluation.

- Use one high-level framework diagram showing the sponsorship problem, the proposed AI system, the expected outputs and the practical accessibility goal.

- Use a second technical diagram showing data collection, frame sampling, annotation, preprocessing, training, validation, testing and reporting.

- Explain why Bradford Bulls provides a useful real-world case while acknowledging that one club cannot represent every sport or sponsorship setting.

- Map each research question to the data, metrics and evidence used to answer it.

## 3.2 Data preparation and model-development strategy

**What this section must do:** Make the data flow and model comparison clear enough for another researcher to repeat.

- Describe the videos, seasons, resolutions and inclusion rules. Separate training, validation, test and full-run videos.

- Report the number of videos, sampled frames, annotated boxes and sponsor classes in one master data table.

- Explain frame sampling, annotation rules, quality checks and class imbalance.

- Prevent leakage by keeping neighbouring frames from the same clip or match out of different dataset splits.

- Describe the selected YOLO and RF-DETR checkpoints, input resolution, training settings and model-selection rule.

- Compare models using the same sponsor data, test split and target hardware wherever possible.

- State when confidence thresholds and score settings were chosen. The test set must not be used to tune the system.

## 3.3 Evaluation, ethics and reproducibility

**What this section must do:** Define the tests before presenting any results.

- RQ1 measures: precision, recall, mAP, latency, memory and performance when several logos appear together.

- RQ2 measures: performance across size, screen coverage, blur, contrast and occlusion groups, plus agreement with human readability ratings.

- RQ3 measures: error against manually timed logo appearances, effects of sampling rate, human-score agreement and score sensitivity.

- Report sample sizes and uncertainty, especially for manually timed clips and human-rated detections.

- Protect commercial information. Sponsor names and logos may be shown for detection examples, but pricing values, club comparisons and contractual information must be anonymised or described only in general terms.

- Record code version, environment, random seeds, dataset manifests, checkpoints and the role of each researcher.

- State limitations caused by a single annotator or rater and describe any checking procedure used.

# Chapter 4: Model and System Development

Purpose: explain how the computer vision artefact works. This is the main technical chapter. Approximate budget: 1,600 words.

## 4.1 System architecture and logo detection

**What this section must do:** Describe the implemented system at component level without turning the chapter into software documentation.

- Show one architecture figure from video input to detection results and final report.

- Explain the role of the backend, model service, stored outputs and Logo Analytics frontend.

- Describe preprocessing, input resolution, confidence thresholds and the shared output format used by YOLO and RF-DETR.

- Explain how the system detects several sponsor logos in the same frame and stores class, confidence, box, frame number and timestamp.

- Explain that only sponsor logos included in the trained class list can be recognised in the current version.

- Do not include source code. Use a short algorithm or pseudocode only when it helps explain the process.

## 4.2 Visibility quality and duration measurement

**What this section must do:** Explain how each detection is converted into measurable visibility information.

- Define logo size, screen coverage, screen position, sharpness, contrast and occlusion in clear language.

- Give the formula, range and normalisation rule for each retained feature.

- Separate directly measured features, approximate indicators and human readability ratings.

- Use one worked detection example to show how the feature values are calculated.

- Explain how timestamps, sampling intervals and a stated gap rule are used to estimate visibility duration.

- Explain how missed detections can split one appearance or merge separate appearances, and how this is handled.

## 4.3 Logo Visibility Score and system outputs

**What this section must do:** Show how the measurements are combined and reported without presenting the score as commercial truth.

- Present the Logo Visibility Score equation and explain every component and weight.

- Justify the weights using literature, expert input or validation evidence, and test how much the results change when the weights change.

- Keep EMV outside the core score unless a reliable source supports the conversion used. Label it as an illustrative media-value estimate, not revenue or billing value.

- Describe video-level, brand-level and detection-level outputs and show how a result can be traced back to its source frame.

- Report target hardware, processing speed and memory so accessibility for a smaller club can be judged from evidence.

- State current limits, including the known sponsor list, sampling choices and ordinary rectangular detection boxes.

# Chapter 5: Experiments and Results

Purpose: present what was found. Keep interpretation brief here and save the wider meaning for Chapter 6. Approximate budget: 2,500 words.

## 5.1 Dataset summary and model performance

**What this section must do:** Establish the test conditions and answer the main detection part of RQ1.

- Report the final dataset size, class balance, logo-size distribution and number of logos per frame.

- List final model checkpoints, thresholds, input resolution and test hardware.

- Compare YOLO and RF-DETR using precision, recall, mAP and per-class performance on the same unseen test set.

- Compare latency and memory on the same hardware and state whether preprocessing and file input/output are included.

- Select the preferred model using both detection performance and deployment cost, not accuracy alone.

- Use one main model-comparison table and one supporting chart; move detailed training curves to an appendix.

## 5.2 Visibility conditions, multi-logo cases and model errors

**What this section must do:** Answer RQ2 and explain what the overall metrics do not show.

- Report detection performance by logo size, screen coverage, blur, contrast and occlusion group.

- Report performance when one, several or many logos appear in the same frame.

- Compare automated quality measurements with a clearly defined human-readability sample.

- Show one compact figure containing a clear success, a multi-logo success, a difficult miss and a false positive.

- For each example, explain what made the image difficult, what the model did and why the error matters.

- State how examples were selected. Do not use attractive examples as evidence of overall accuracy.

## 5.3 Duration, Logo Visibility Score and full-video results

**What this section must do:** Answer RQ3 and show how the system behaves on the complete set of analysed videos.

- Compare estimated visibility duration with manually timed logo appearances.

- Report absolute and relative error under the selected sampling rates and explain the effect of missed frames and gap rules.

- Compare the Logo Visibility Score with human visibility ratings and test component removal and weight changes.

- Summarise all full-run videos in one main table with video name, duration analysed, number of detections, detected visibility time and overall visibility measures.

- Move detailed brand-by-video rows and repeated charts to the appendix.

- If club-provided location percentages are discussed, describe them as anonymised expert or commercial priority weights. Do not show them as the correct visibility value, a sponsor charge or model ground truth.

- End with one short table linking each research question to its main result and its main limitation.

# Chapter 6: Discussion

Purpose: explain what the findings mean for research and practice. Approximate budget: 1,900 words.

## 6.1 Answers to the research questions and comparison with prior work

**What this section must do:** Interpret the evidence instead of repeating every number from Chapter 5.

- Answer RQ1 by explaining the accuracy-efficiency trade-off and whether reliable multi-logo detection is feasible on the target hardware.

- Answer RQ2 by explaining which visual conditions most affect detection and where confidence differs from human readability.

- Answer RQ3 by stating when duration estimates and the Logo Visibility Score are trustworthy and when they are not.

- Compare the findings carefully with recent logo-detection and sponsor-analytics studies.

- Do not use vendor claims as direct benchmarks because their datasets and evaluation methods are usually not public.

## 6.2 Practical meaning and accessibility for smaller clubs

**What this section must do:** Translate the technical results into a realistic business takeaway.

- Explain how the system could support sponsor reporting and evidence-based conversations without replacing commercial judgement.

- Discuss whether the measured hardware, speed and workflow are realistic for a small or medium-sized club.

- Explain the value of transparent frame-level evidence and repeatable reports.

- Avoid unsupported claims that the system is cheaper or better than Nielsen or other commercial platforms.

- Keep visibility separate from attention, brand impact, return on investment and sponsorship pricing.

## 6.3 Limitations and threats to validity

**What this section must do:** Make the boundaries of the evidence clear.

- Discuss the one-club case study, one sport, known sponsor list and selected video types.

- Discuss dataset leakage controls, class imbalance, threshold selection and limited difficult examples.

- Discuss uncertainty from manual timing, a small human-rating sample and possible single-rater bias.

- Discuss how sampling rate, score weights and approximate occlusion measures affect the results.

- State that the findings support feasibility and local evaluation, not universal claims about all sports or sponsorship markets.

# Chapter 7: Conclusion and Future Work

Purpose: give the final answer without introducing new evidence. Approximate budget: 800 words.

## 7.1 Conclusion and contributions

**What this section must do:** Answer the aim directly using only evidence already presented.

- Summarise whether the system can detect known sponsor logos and measure visibility quality and duration with useful accuracy.

- Technical contribution: a modular multi-logo detection and reporting pipeline.

- Methodological contribution: a condition-based evaluation with leakage controls, manual duration checks and human readability comparison.

- Practical contribution: a transparent Logo Visibility Score and performance report designed around a smaller-club case study.

- Keep every contribution limited to what was built, tested or observed.

## 7.2 Priority future work

**What this section must do:** Propose work that directly addresses the current limitations.

- Test more clubs, sports, seasons and broadcast styles.

- Add more manually timed samples and at least one additional human rater.

- Evaluate stronger approaches for rotated, distorted and heavily occluded logos.

- Explore recognition of previously unseen logos only after the core known-sponsor system is fully validated.

- Study user adoption or technology acceptance later through interviews or surveys with club staff; do not claim adoption findings without collecting that evidence.

## 7.3 Final takeaway

**What this section must do:** End with one short and defensible message.

- Transparent computer vision can help smaller sports clubs measure sponsor-logo visibility, provided that uncertainty, sampling choices and the difference between visibility and commercial value remain clear.

# Evidence and visual plan

## Keep the main body selective

- Aim for about 6-8 figures and 5-7 main tables. More detailed outputs can go in the appendices.

- Priority figures: research framework, technical workflow, data split, system architecture, model comparison, one detection success/failure plate, and duration/score validation.

- Priority tables: literature summary, dataset summary, model comparison, condition-based performance, full-video summary, and research-question summary.

- Use no more than one dashboard screenshot. Every figure must support a specific finding or methodological decision.

- If an image is generated with AI, state the tool and prompt and check the image carefully for errors.

## Writing boundaries

- Introduction: no detailed model settings, data split or evaluation metrics.

- Literature Review: compare and synthesise sources; do not describe papers one by one without a clear argument.

- Methodology: explain what was planned and why; do not include results.

- Model Development: explain the system and formulas; do not paste source code.

- Results: report the evidence; keep the longer comparison with literature for the Discussion.

- Discussion: explain meaning, usefulness and limitations; do not introduce new experiments.

- Conclusion: answer the aim without adding new references, results or product claims.

## Source priorities

- Use mainly peer-reviewed studies from the last five years, supported by older foundational work only when needed.

- Use credible government, sports-industry and marketing reports for market size and practice.

- Use Nielsen Sports, Blinkfire and Relo Metrics pages only to describe their publicly documented services and capabilities.

- Record exact model versions, publication status and access dates in the final reference list.
