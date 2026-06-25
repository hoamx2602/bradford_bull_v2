# AI % — How the parameters are calculated (English)

This document explains, step by step, **how every parameter is computed to produce
the `AI %` value** shown in the Location Breakdown table and the **"AI % Detail"**
Excel sheet. It is the English, calculation-focused companion to the broader
[`10-location-breakdown.md`](10-location-breakdown.md) (Vietnamese).

> **In one sentence:** `AI %` for a location is that location's share of the total
> *quality-weighted on-screen exposure*, measured by the AI, normalised to exactly
> 100 % across the locations the customer has configured.

The pipeline never stores a single baked number. It stores the **factor components
of every detection**, so the AI % can be **recomputed instantly** when the user
ticks/unticks criteria in Settings — without re-running detection.

Source of truth in code:
- `backend/app/pipeline/visibility.py` — the per-frame Tier-1 factors.
- `backend/app/pipeline/location_breakdown.py` — frame weight, segmentation,
  zone quality, zone→location share, normalisation, AI Adjusted.
- `backend/app/api/xlsx_export.py` — the "AI % Detail" sheet layout.

---

## 0. The calculation at a glance

```
 detection (every sampled frame, 2 fps)
        │   factors: size · position · clarity · obb        (Tier-1, visibility.py)
        ▼
 frame_weight = product of the ENABLED factors             (disabled factor = 1.0)
        │
        ▼   group a zone's detections into time SEGMENTS
 quality_segment = mean(frame_weight) × duration_weight × duration
        │
        ▼   sum over a zone's segments
 quality_zone  = Σ quality_segment
        │
        ▼   share of all zones, then map zone → location
 AI %(location) = quality(anchor) / (#locations sharing anchor)
        │        then normalise to EXACTLY 100 % over configured locations
        ▼
 AI %   (the column)            AI % Detail sheet exposes every number above
```

---

## 1. The raw input: "exposure facts"

During analysis the video is sampled at `SAMPLE_FPS` (default **2 fps**). Each logo
detection in each sampled frame is persisted as one **fact**:

```json
{ "t": 12.5, "zone": "chest-center", "brandKey": "top_notch",
  "size": 0.18, "pos": 0.72, "clarity": 0.66, "obb": 1.0, "durSec": 0.5 }
```

| Field | Meaning |
|---|---|
| `t` | timestamp (seconds) of the sampled frame |
| `zone` | the body **anchor** the detection was assigned to (from pose keypoints) |
| `brandKey` | which brand was detected |
| `size`, `pos`, `clarity`, `obb` | the four Tier-1 factors (§2) |
| `durSec` | seconds represented by one sample = `1 / SAMPLE_FPS` (0.5 s at 2 fps) |

Persisting the **factors** (not just their product) is what makes the AI %
re-tickable in Settings. The facts are written once per analysis and reused.

---

## 2. Tier-1 — the four per-frame factors (`visibility.py`)

Each factor is in `[0, 1]`. `Detection.area = box_w × box_h`,
`frame_area = frame_w × frame_h`, `(cx, cy)` is the box centre.

### 2.1 Size
```
size = sqrt( min(1, box_area / frame_area) )
```
Bigger logos score higher. The `sqrt` is deliberate: it compresses the top end so a
single very large logo cannot completely dominate the share.

### 2.2 Position
```
sigma    = 0.3 × frame_w
dist²    = (cx − frame_w/2)² + (cy − frame_h/2)²
position = exp( −dist² / sigma² )
```
A Gaussian centred on the frame: **centre ≈ 1.0**, far corners ≈ 0.1. Logos near the
middle of the broadcast frame are worth more than logos at the edge.

### 2.3 Clarity
```
clarity = detector confidence (YOLO conf)
```
A proxy for how clear/sharp the logo is. Blurry or ambiguous detections come with a
lower confidence and therefore count less.

### 2.4 OBB penalty
```
obb = 1.0          # horizontal-box (HBB) model today
```
Reserved for an oriented-box model: it would become `area_HBB / area_OBB` to discount
logos stretched by camera angle. With the current HBB model it is always `1.0`, so it
never changes the result — but it is kept in the chain (and the sheet) for transparency.

### 2.5 The clamped product (the classic "visibility")
```
visibility = clamp( size × position × clarity × obb , 0, 1 )
```
This is the standard Tier-1 visibility score. The AI % uses the **same factors**, but
multiplies only the ones currently enabled (next section).

---

## 3. Frame weight — applying the enabled criteria

The Location Breakdown lets the user **toggle which factors count**, in Settings →
*AI Criteria*. For one detection:

```
frame_weight = product of the ENABLED per-frame factors      (a disabled factor = 1.0)
```

So with all four on, `frame_weight == visibility`. With, say, only `size` and
`clarity` enabled, `frame_weight = size × clarity`.

| Key | Label | Scope | Changes AI %? |
|---|---|---|---|
| `size` | Size Score | per-frame | **Yes** |
| `position` | Position Score | per-frame | **Yes** |
| `clarity` | Clarity (Confidence) | per-frame | **Yes** |
| `obb` | OBB Penalty | per-frame | Yes in principle (= 1.0 on the HBB model, so no effect now) |
| `durationWeight` | Duration Weight | per-segment | **Yes** (see §4) |
| `placement` | Placement Multiplier | per-video | **No** — applied to every logo equally, cancels out of a *share* |
| `category` | Category / Share of Voice | per-brand | No — needs a category map (reserved) |
| `primeTime` | Prime-time Multiplier | per-segment | No — needs a match clock (reserved) |

Default enabled: `size, position, clarity, obb, durationWeight`.

> Why placement does not move the AI %: it multiplies *all* locations by the same
> constant, and AI % is a ratio — the constant divides out. It still matters for EMV
> ($), just not for this share.

---

## 4. Tier-2 — segments, duration weight, zone quality

The factors are per-frame; exposure value is per *appearance*. For each **zone**, its
facts are sorted by time and cut into **segments** (a continuous on-screen run):

```
dt        = durSec of the zone's first fact (fallback 0.5)
gap_limit = max(dt × 2.5, dt + 0.05)
→ start a NEW segment whenever the time gap to the previous fact > gap_limit
```
(At 2 fps, `dt = 0.5` and `gap_limit = 1.25 s`: a gap longer than ~2–3 missed samples
means the logo left the screen and came back as a separate appearance.)

For each segment (run of facts):
```
duration = max( t_last − t_first + dt , dt )      # at least one sample long
mean_w   = mean( frame_weight )  over the run
dw       = duration_weight(duration)   if "durationWeight" enabled, else 1.0
quality_segment = mean_w × dw × duration
```

**Duration weight** rewards sustained exposure:

| Segment length | `duration_weight` |
|---|---|
| < 1 s | 0.5 |
| 1 – 5 s | 1.0 |
| > 5 s | 1.2 |

The zone total:
```
quality_zone     = Σ quality_segment          (over the zone's segments)
on_screen_zone   = Σ duration                 (raw seconds the zone was visible)
```

`quality_zone` is the single number that ultimately drives the AI %.

---

## 5. From zone quality to AI %

### 5.1 Zone share
```
zone_share(z) = quality_zone(z) / Σ_all_zones quality_zone × 100
```
This sums to ~100 % across **all** anatomical zones, mapped or not.

### 5.2 Zone → Location, with even split
Locations are a customer taxonomy (Main Sponsor, Sleeve 1/2/3, Collar Bone, …); each
maps to one pose **anchor**. The AI % the customer sees is computed over **configured
locations only**:

```
raw(location) = quality( location's anchor ) / n
                where n = number of logo-bearing locations sharing that anchor
```
- Exposure on **unmapped** zones (abdomen, opposite shoulder, …) is excluded, so the
  column totals 100 % over the locations the customer actually set up.
- When several locations map to one anchor (e.g. Collar Back / Nape Neck / Top Back
  all map to `back-top`, which COCO-17 keypoints can't separate), that anchor's
  quality is split **evenly** between them.
- A location with **no logo** is attributed nothing (its AI %, AI Adjusted, Visibility
  cells are left blank), and does not draw any of the anchor's share.

### 5.3 Normalise to exactly 100.00 %
The raw values are rounded with the **largest-remainder method** so the printed numbers
sum to **exactly 100.00 %** (no "100.01 %" rounding drift): floor every value to whole
cents, then hand the few leftover cents to the entries with the biggest fractional
remainder.

That rounded, normalised number is the **`AI %`** column.

---

## 6. The "AI % Detail" sheet — every parameter, column by column

Excel sheet 2 (`xlsx_export.py`). **One row per location** (the parameter cells are
left **blank** when the location has no logo, because no exposure is attributed to it).
The sheet header also records the **Enabled criteria** string, so any row is fully
reproducible. The 13 columns are explained one by one below; each entry says *what it
is*, *where it comes from*, *its typical range*, and *what pushes it up or down*.

### 6.1 `Location`
- **What:** the customer's kit-slot name for this row (e.g. *Main Sponsor*, *Sleeve 3*).
- **Source:** Settings → Locations (`anchor_by_location` config). Pure label, not measured.
- **Note:** the row exists even with no logo; in that case every measured column is blank.

### 6.2 `Anchor zone`
- **What:** the pose **anchor** id this location maps to, e.g. `chest-center`, `back-top`.
- **Source:** Settings (the Location→Anchor mapping). All measurement happens per *anchor*,
  then is handed to the location — so two locations on the **same** anchor read the same
  raw parameters and split the share (see §5.2).
- **Why it matters:** the anchor is the key the facts were bucketed under (`fact["zone"]`).
  If the mapping is wrong, every number on the row describes the wrong body area.

### 6.3 `Logo`
- **What:** the brand shown at this location, **for this video's kit** (home vs away).
- **Source:** Settings, kit-aware — `brand_key` (home/default) or `brand_key_away`.
- **Note:** the AI never used this brand name to compute the share — attribution is by
  **zone**, not by detected class (see limit §9.1). The column is for human reading only.

### 6.4 `AI %`
- **What:** the final headline number — this location's normalised share of quality exposure.
- **Source:** §5 (`compute_location_ai_percentages`).
- **Range:** 0–100; the column **sums to exactly 100.00 %** across logo-bearing locations.
- **Up/down:** rises with this anchor's **Quality exposure** relative to the others; falls
  if it shares its anchor with other locations (even split) or if other zones get more
  exposure. Changing enabled criteria in Settings recomputes it instantly.

### 6.5 `Quality exposure`
- **What:** `quality_zone` — the engine's core measure of *how much valuable screen time*
  this zone got. **This is the number AI % is the share of.**
- **Source / formula (§4):** `Σ_segments ( mean(frame_weight) × duration_weight × duration )`.
- **Unit:** quality-weighted seconds (a segment of 2 s at frame_weight 0.1 and dw 1.0 → 0.2).
- **Up/down:** more on-screen time, higher per-frame weight (big/central/clear logo), and
  longer segments (duration_weight 1.2) all raise it. It is **not** a percentage and does
  not sum to 100 — it is the raw fuel that §5 turns into the percentage.

### 6.6 `Detections`
- **What:** how many sampled frames contained a logo in this zone.
- **Source:** count of facts for the anchor.
- **Unit:** frames at the sample rate (2 fps → 100 detections ≈ 50 s of *frames*, but not
  necessarily 50 continuous seconds).
- **Use:** a confidence/sample-size cue. A big AI % built on very few detections is fragile;
  many detections means the measurement is well-supported.

### 6.7 `Segments`
- **What:** number of **separate** on-screen appearances (continuous runs, §4).
- **Source:** count of runs after the `gap_limit` split.
- **Up/down:** a logo that flickers in and out many times has many short segments (each may
  hit the < 1 s duration_weight 0.5 penalty); one long steady appearance is a single segment
  (and can earn the > 5 s bonus 1.2). So **Segments vs On-screen** together tell you whether
  the exposure was steady or fragmented.

### 6.8 `On-screen (s)`
- **What:** `on_screen_zone` — total **raw** seconds the zone was visible.
- **Source / formula (§4):** `Σ duration` over the zone's segments.
- **Range:** 0 … video length. **Not** weighted by criteria, **not** normalised.
- **Relation:** this is the numerator of **Visibility %** (§7). Compare it with *Quality
  exposure*: if On-screen is high but Quality is low, the logo was visible but small / off-centre
  / low-confidence.

### 6.9 `Mean Size`
- **What:** average **Size** factor over the zone's detections — `mean(sqrt(box_area/frame_area))`.
- **Range:** 0–1; in practice logos are small, so values are typically low (e.g. 0.1–0.3).
- **Up/down:** larger logo boxes (close-up shots) raise it; distant/tiny logos lower it.
  Explains part of why *Mean frame weight* (and thus Quality) is high or low.

### 6.10 `Mean Position`
- **What:** average **Position** factor — `mean(exp(−dist²/(0.3·W)²))`.
- **Range:** 0–1; **1.0 = always dead-centre**, ~0.1 = always near a corner.
- **Up/down:** zones that tend to appear in the middle of the broadcast frame score high;
  zones often caught at the frame edge score low.

### 6.11 `Mean Clarity`
- **What:** average detector **confidence** for the zone's detections.
- **Range:** 0–1 (bounded below by the detection threshold used in the pipeline).
- **Up/down:** sharp, unambiguous, well-lit logos → high; motion-blurred / occluded / odd-angle
  logos → low. A persistently low value can also flag a weak/under-trained class.

### 6.12 `Mean OBB`
- **What:** average **OBB penalty**.
- **Value today:** **always 1.0** — the current model uses horizontal boxes (HBB), so this
  factor never discounts anything. It is shown for transparency and forward-compatibility:
  with an oriented-box model it would drop below 1.0 for tilted logos.

### 6.13 `Mean frame weight`
- **What:** average **`frame_weight`** over the zone's detections — the product of the
  **enabled** per-frame factors (§3), averaged.
- **Source:** `mean(frame_weight)` under the current criteria. With all four on, this equals
  `Mean Size × Mean Position × Mean Clarity × Mean OBB` *only approximately* (the mean of a
  product ≠ product of the means).
- **Use:** the single "how valuable is one frame here" number. It changes when you toggle
  criteria, which is exactly why the AI % is re-tickable without re-detection.

> **How to read a row.** Start at **Quality exposure** — it ranks the locations and AI %
> is just its normalised share. To see *why* it is high or low, read **On-screen (s)** (how
> long) and **Mean frame weight** (how valuable each frame), then drill into the four `Mean *`
> factors (big? central? clear?). **Detections / Segments** tell you how trustworthy and how
> steady the measurement is. Caveat: `Quality ≈ Mean frame weight × On-screen`, but **not
> exactly** — the mean frame weight is taken **per segment** and each segment is multiplied by
> its own duration_weight (0.5 / 1.0 / 1.2) before summing, so steady long appearances beat
> the same seconds split into flickers.

---

## 7. Related columns (context)

These are not part of the AI % chain but appear next to it; see
[`10-location-breakdown.md`](10-location-breakdown.md) §5–6 for detail.

- **Visibility %** = `on_screen_zone / video_duration × 100`. Raw presence, **not**
  weighted by criteria and **not** normalised to 100 %.
- **AI Adjusted %** = convex blend of the AI distribution with a human reference
  (manual *Human AI %* if entered, else contractual *Human %*), both normalised to
  100 % over the same locations:
  ```
  AI_adjusted = (1 − β)·AI_norm + β·reference_norm        # β = Settings slider, default 0.5
  ```
  β = 0 → pure AI; β = 1 → pure human reference. Also rounded to exactly 100.00 %.

---

## 8. Worked example

Take a zone `chest-center` with three sampled detections (2 fps, `durSec = 0.5`) and
all four per-frame factors enabled.

| t (s) | size | pos | clarity | obb | frame_weight |
|---|---|---|---|---|---|
| 10.0 | 0.20 | 0.80 | 0.70 | 1.0 | 0.112 |
| 10.5 | 0.22 | 0.78 | 0.65 | 1.0 | 0.1115 |
| 11.0 | 0.18 | 0.82 | 0.60 | 1.0 | 0.0886 |

Gaps are 0.5 s ≤ `gap_limit` (1.25 s) → **one segment**.
```
duration = (11.0 − 10.0) + 0.5 = 1.5 s
mean_w   = (0.112 + 0.1115 + 0.0886) / 3 = 0.1040
dw       = duration_weight(1.5 s) = 1.0        # 1–5 s band
quality_zone = 0.1040 × 1.0 × 1.5 = 0.1560
```
"AI % Detail" for this row would read: Detections 3, Segments 1, On-screen 1.50 s,
Mean Size 0.200, Mean Position 0.800, Mean Clarity 0.650, Mean OBB 1.000, Mean frame
weight 0.1040, Quality exposure 0.1560. If every other configured location summed to a
quality of, say, 0.624, then `AI % = 0.156 / (0.156 + 0.624) × 100 = 20.00 %` (before
even-split / largest-remainder rounding).

---

## 9. Known limits (that affect the numbers)

1. **Detector bias** — an over-detected class inflates the quality of its zone. AI
   Adjusted reconciles this at the *reporting* layer; fixing the *root* needs detector
   tuning (per-class confidence, false-positive filtering).
2. **Close neck/back slots** share one anchor (`back-top`); their split is the even
   division of §5.2, not a true per-slot measurement.
3. **Exposure outside the taxonomy** (abdomen, opposite shoulder, …) is dropped from
   the share so the column totals 100 % over configured locations only.
4. AI %, Visibility and exposure cover the **whole** video, even though the annotated
   preview / overlay clips only cover the first ~30–60 s.
```
