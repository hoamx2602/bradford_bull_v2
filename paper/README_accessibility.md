# Paper — Accessibility-framing draft (LaTeX source)

First full draft of *"LogoLens: A Vision AI Tool to Measure Kit Sponsor
Visibility and Value"* (IEEEtran conference; formerly titled "Sponsor Exposure
Analytics for the Rest of Us").
This is a **separate paper** from the CyberWorlds/Inventory draft (`main.tex`,
`refs.bib`) already in this folder — different framing (accessibility/systems, not
digital-twin/annotation-free), different files, kept side by side intentionally.

## Files

| File | Content |
|---|---|
| `main_accessibility.tex` | Full paper (abstract → conclusion), IEEEtran 2-column |
| `refs_accessibility.bib` | References — **several entries have `Author(s) TBD` and a verification note; do not submit without fixing these** |
| `fig_pipeline.tex` | Fig. 1 — end-to-end pipeline (TikZ, `figure*`) |

## Provenance

Built from `paper_outline_for_advisor.md` (project root), after two rounds of review:
(1) a self-critique pass checking related-work gaps, EMV-formula attribution, and
statistical rigor of planned experiments; (2) an advisor comment requesting related work
on existing pricing models (manual and AI-based), now in
\S\ref{sec:related-pricing}/`main_accessibility.tex` §2.5.

## Compiling

No LaTeX available in this environment. Two options:

**Overleaf (recommended):** create a project, upload this folder, set
`main_accessibility.tex` as the main file, Recompile.

**Local:**
```bash
cd paper && latexmk -pdf main_accessibility.tex
```

## Before submitting — do not skip this list

- Every `\TODOnum{...}` (red text) is a placeholder for a real measurement. The
  Experiments section is currently mostly placeholders — see
  `paper_outline_for_advisor.md` §5 for the prioritized list of what to measure first
  (hardware/latency benchmark and annotation-time cost are the highest priority for the
  accessibility claim).
- `refs_accessibility.bib`: every entry marked `Author(s) TBD` or "VERIFY" needs its
  real bibliographic details filled in — several were located via web search with only
  title/year/source confirmed, not full author/venue detail.
- Confirm target venue and page budget with your advisor (see
  `paper_outline_for_advisor.md`) — this affects how much space the accessibility
  framing (C4) should get relative to the two technical contributions (C1, C3).
- Fill in the club's actual data-use/ethics statement in §Discussion (currently a
  `\TODOnum` placeholder) — the club's name itself must stay withheld throughout per
  client confidentiality, but the rights/permission statement still needs real content.
- Decide, with your advisor, which of the five contributions are headline vs.
  supporting (a scope note is already in the Introduction — resolve it before final
  submission).
