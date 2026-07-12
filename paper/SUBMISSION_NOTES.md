# LogoLens — submission notes (NOT part of the paper; do not submit this file)

## Camera-ready author block (paste into main_accessibility.tex AFTER acceptance)

For double-blind review the paper ships with an anonymous author block. After
acceptance, replace the anonymous `\author{...}` block with:

```latex
\author{\IEEEauthorblockN{Xuan Hoa Mai, Ezichi Abel, Jason Akhuemokhan,
Rashmi Yatawara, Simranjit Kaur, Tabby Mungai, Tillal Eldabi, and Irfan Mehmood}
\IEEEauthorblockA{University of Bradford, Bradford, United Kingdom\\
\texttt{x.mai@bradford.ac.uk}}}
```

- Corresponding author email: `x.mai@bradford.ac.uk`.
- To match the IEEE template more fully, department + per-author ORCID can be
  added at camera-ready (authors span School of Management and Faculty of
  Engineering & Digital Technologies — supply the split if you want it formatted).

## Submission checklist (CW26 = double-blind, A4, ≤8 pages incl. references)

- [x] Anonymous author block; PDF metadata author cleared; A4 (MediaBox 595×842).
- [x] 8 pages including references.
- [x] No placeholders / TODO / red text / template phrases / broken refs in the PDF.
- [x] Body has no Bradford / funding / acknowledgment / self-citation.
- [x] Figures: club NAME/crest/scoreboards/watermarks withheld; Fig. 4 sponsors
      numbered; Fig. 3 keeps a few visible logo crops (user decision).
- [ ] **SUBMIT THE PDF, not the .tex** (source safety already maximized, but PDF
      is the review artifact).
- [ ] Confirm with advisor: ethics/consent wording matches the club's actual
      agreement; whether University of Bradford requires an ethics-approval ref
      (add only at camera-ready, not in the blind version).
- [ ] Confirm club (BullsTV footage) permits publishing the figure frames.

## Verified numbers (provenance, for your records)

- Detection mAP (logo_detection/runs/*/results.csv): random-frame 0.862;
  clip-disjoint 0.702; extended 0.745 (P .65, R .74). RF-DETR run
  (training-result/, 0.778) used a RANDOM split → not citable.
- Deployment conf floor was **0.20** (facts_json min clarity = 0.200).
- 41% attribution drop; 91.8% track-label audit (paper/track_label_audit.csv);
  ≈1.0× throughput (job log); +63% sampling bias; visibility-floor sensitivity
  sweep; confusion-matrix finding (clipsplit run). Nothing fabricated.
- Not yet measured (stated as open items in the paper, not as results): exposure
  MAE vs manual timing; held-out clip-disjoint TEST split per-class AP;
  per-sponsor counterfactual; per-class annotation wall-clock time.

## Data source

Footage is the club's own BullsTV match video, obtained from public YouTube and
provided by the club. Framing in the paper says "the club's own match video /
no enterprise broadcast integration" (accurate) — NOT "self-shot amateur video".
