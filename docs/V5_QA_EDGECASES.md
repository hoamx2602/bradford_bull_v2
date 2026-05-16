# v5 Q&A — 25 câu hỏi technical edge cases

> **Phụ lục cho** `SOLUTION_ARCHITECTURE_V5.md`
> **Ngày:** 2026-05-16
> **Mục đích:** Stress-test kiến trúc v5 bằng cách brainstorm và trả lời 25 câu hỏi technical mà sẽ thực sự gặp phải khi build hệ thống. Mỗi câu hỏi đi kèm: cơ chế vấn đề, giải pháp v5 cụ thể (kỹ thuật + reference), risk + mitigation, open question (nếu có).
> **Mục tiêu:** Định hình rõ ràng các vấn đề trước khi code → kiến trúc robust hơn.

---

## 📑 Mục lục theo nhóm

- **Nhóm A: Data & Annotation** (5 câu)
- **Nhóm B: Model & Detection** (5 câu)
- **Nhóm C: Tracking & Attribution** (4 câu)
- **Nhóm D: Inference & Performance** (3 câu)
- **Nhóm E: Broadcast Edge Cases** (4 câu)
- **Nhóm F: Reporting & Methodology** (3 câu)
- **Nhóm G: Multi-club / Multi-sport scaling** (1 câu tổng)

---

## NHÓM A — Data & Annotation

### Q1. Logo same position 2 players, 1 sharp 1 blur — auto-annotate blur?
(User đã hỏi, đã trả lời trong v5 §3.1. Tóm tắt: kết hợp 4 cơ chế = SAM 2 propagation + DINOv2 ReID cross-instance + Teacher-Student distillation + tracker temporal propagation.)

### Q2. Logo xoay 45° vs xoay 0° (đứng hoặc nghiêng) — model handle cả 2?

**Vấn đề:**
Cầu thủ chạy, nhảy, ngã → logo có thể xoay từ 0° đến 90°. Một logo "MCP" thẳng đứng trên ngực vs cầu thủ nằm ngửa → logo xoay 90°.

**Cơ chế xảy ra:**
- Logo `aon_red` thường horizontal, nhưng nếu cầu thủ ngã ngửa, logo có thể xoay 90°
- Augmentation rotation thường ±15° trong training → model chỉ học các xoay nhỏ
- Logo xoay lớn (>30°) trong inference → confidence drop nhiều

**Giải pháp v5:**

1. **OBB (Oriented Bounding Box) is the answer.** v5 chọn OBB từ đầu (Stage 3A) chính xác vì lý do này. OBB capture được rotation:
   ```
   Regular bbox: [x, y, w, h] — luôn axis-aligned, không hiểu rotation
   OBB: [x1,y1, x2,y2, x3,y3, x4,y4] — 4 góc của rotated rectangle, capture rotation
   ```

2. **Augmentation mạnh hơn cho rotation:**
   ```python
   # YOLOv11-OBB hyperparameters
   degrees: 45.0     # ±45° rotation (vs default 10°)
   perspective: 0.001  # Mild perspective distortion
   shear: 5.0          # Mild shear
   ```

3. **Stage 3B (DINOv2 embedding) cũng cần handle rotation:**
   - DINOv2 KHÔNG inherently rotation-invariant
   - Mitigation: trong reference bank, generate **8 rotated versions** of mỗi logo (0°, 45°, 90°, 135°, 180°, 225°, 270°, 315°) → 8 references per brand → nearest-neighbor sẽ match được logo xoay
   - Hoặc: rotation-equivariant model (RotEqNet, scarce in production) → defer

**Risk:** Logo OBB detector có thể predict OBB sai orientation (off by 90°) → ExposureEngine paper note "OBB-aware tracking" là future work.

**Mitigation:** Validate OBB orientation accuracy trên 100 test samples. Pass: angle error < 15°.

**Open question:** Có nên train rotation-equivariant variant của YOLOv11-OBB? (effort ~1-2 weeks, gain ~3-5% AP on rotated samples)

### Q3. Logo bị che một phần bởi player khác — annotate hay skip?

**Vấn đề:**
Trong scrum/ruck, logo trên ngực Bradford bị che bởi cánh tay đối thủ. Visible 30%, 50%, 70%? Annotate ngưỡng bao nhiêu?

**Cơ chế xảy ra:**
- Rugby league có nhiều physical contact → frequent partial occlusion
- Spec v4 nói: "Logo bị che <50% → annotate; ≥50% → bỏ" — arbitrary

**Giải pháp v5:**

1. **Annotation guideline cụ thể:**
   ```
   Visibility levels (annotator quyết định):
   - "full"     (>80% visible): annotate, normal label
   - "partial"  (40-80% visible): annotate, tag with attribute "partial"
   - "barely"   (15-40% visible): annotate, tag "barely_visible"
   - "occluded" (<15% visible): SKIP
   ```

2. **Use visibility attribute in QI scoring:**
   ```
   QI penalty cho partial visibility:
   - full: QI multiplier 1.0
   - partial: 0.7
   - barely: 0.4
   ```
   → Logo bị che một phần vẫn được tính exposure nhưng QI thấp hơn

3. **Model training:** Train với `partial` và `barely` samples (không filter) để model học detect cả partial logos. KHÔNG train với `occluded`.

**Risk:** Annotator inconsistent về phân loại visibility level (subjective).

**Mitigation:** Reference guide với example images cho từng level. Inter-annotator agreement check trên 50 samples (Cohen's κ > 0.7).

**Open question:** Có cần auto-classify visibility level bằng model thay vì rely annotator? (Có nhưng adds complexity → defer to v6)

### Q4. Logo trong REPLAY footage — count exposure or duplicate?

**Vấn đề:**
Broadcast thường replay cùng pha 2-3 lần (slow-motion, multiple angles). Cùng 1 cú try → logo MCP xuất hiện 3 lần. Có phải đó là 3× exposure không?

**Đây là MAJOR methodology question** — affect bottom-line numbers.

**Cách tiếp cận trong industry:**
- Nielsen MIV: thường **count replay** (vì sponsor thực sự được view 3×)
- Một số agency: **discount replay** (gọi là "fresh exposure" vs "replay exposure", split metrics)

**Giải pháp v5:**

1. **Detect replay segments:**
   ```
   Heuristics:
   a) Broadcast graphic insertion: nhiều broadcast có "replay" banner/wipe transition
      → template-match transition graphic ở begin + end của replay
   b) Scoreboard freeze: scoreboard typically pause during replay
      → detect scoreboard region (đã có từ Stage 0 overlay mask) → check if same content for >2s
   c) Slow-motion: replay thường có frame rate khác → check inter-frame motion ratio drops sharply
   d) Visual similarity: replay = đoạn video similar với <5s recently
      → compute pHash sequence, detect repeating subsequences
   ```

2. **Report BOTH counted and discounted versions:**
   ```yaml
   per_brand_report:
     mcp_home:
       total_raw_seconds: 145.3
       total_main_action_seconds: 92.1   # excluded replays
       total_replay_seconds: 53.2
       replay_event_count: 8
   ```

3. **Default presentation:** Show "main action seconds" làm primary number (more conservative, defensible).

**Risk:** Replay detection có thể fail (false positive nếu trận có camera angle đặc biệt; false negative nếu broadcast không có chuẩn replay graphic).

**Mitigation:** Validate trên 5 min footage với manually flagged replays. Precision ≥ 0.85.

**Open question:** Sponsor có muốn replay được count hay không? → Cần CLB confirm methodology before commercial report.

### Q5. Sponsor changes logo design mid-season (rebrand) — handle?

**Vấn đề:**
Sponsor X rebrands giữa mùa, logo mới hoàn toàn khác visual. Reference bank chứa logo cũ → confidence drop, miss detections.

**Giải pháp v5:**

1. **Multi-version reference per brand:**
   ```python
   bank["sponsor_x"] = [
       {"variant": "v1_old", "embedding": old_emb, "valid_until": "2026-09-30"},
       {"variant": "v2_new", "embedding": new_emb, "valid_from": "2026-10-01"},
   ]
   ```

2. **Runtime: time-aware lookup:**
   ```python
   match_date = video_metadata["match_date"]
   active_refs = [r for r in bank if r.valid_from <= match_date <= r.valid_until]
   sims = cosine(crop_emb, [r.embedding for r in active_refs])
   ```

3. **For matches BEFORE rebrand:** model uses old reference.
   **For matches AFTER rebrand:** model uses new reference.
   **No retraining needed** — purely reference bank update.

**Risk:** Trong match khi transition (chính ngày rebrand), kit có thể có logo cũ trên một số jerseys, mới trên số khác.

**Mitigation:** Manual review per-match transition; allow both variants for that match.

**Open question:** Có cần auto-detect rebrand từ kit photos? (Probably not — manual update is rare event)

---

## NHÓM B — Model & Detection

### Q6. Match ban đêm low-light — model fails?

**Vấn đề:**
M01 video là match ban đêm với stadium lights. Lighting không đều, shadows, sources khác nhau (overhead, side). Logo có thể có shadow lệch, contrast giảm.

**Cơ chế xảy ra:**
- COCO-trained YOLO weights học từ daylight images
- Night broadcast color shift toward yellow/warm
- Shadows tạo false edges → false detections

**Giải pháp v5:**

1. **Photometric augmentation trong training:**
   ```python
   # Albumentations
   A.ColorJitter(brightness=0.4, contrast=0.4, saturation=0.3, hue=0.1)
   A.RandomGamma(gamma_limit=(60, 140))    # simulate low/high gamma
   A.RandomShadow(num_shadows_lower=1, num_shadows_upper=3)  # cast shadows
   A.RandomFog(fog_coef_lower=0.1, fog_coef_upper=0.3)       # haze
   ```

2. **CLAHE preprocessing:**
   - Apply Contrast Limited Adaptive Histogram Equalization trước khi detection
   - Improves contrast in dark regions

3. **Test-time augmentation (TTA):**
   - Run inference trên original + brightened version
   - Merge predictions via WBF (Weighted Box Fusion)

4. **Validate explicitly:**
   - Cross-quality validation: train M01 (night) → test M06 (day) and vice versa
   - If AP drops > 15% night→day → add more night training data

**Risk:** Stadium lights vary (LED vs halogen, color temperature 3000K-6500K) → broad lighting domain.

**Mitigation:** Domain randomization với color temperature shift in augmentation pipeline.

### Q7. Pitch logos (BETFRED, ABK Beer painted on grass) false-detected as jersey logos?

**Vấn đề:**
Frame M01_t1200 và M01_t3600 cho thấy huge logos painted on grass (BETFRED, BulldogTV, Super League logo). Model có thể nhầm chúng là jersey logos.

**Cơ chế xảy ra:**
- Logo trên cỏ có visual giống logo trên áo (same brand)
- BetFred logo huge trên sân + small trên áo → cùng "BetFred" embedding match

**Giải pháp v5 (kiến trúc giải quyết VỀ MẶT THIẾT KẾ):**

1. **Crop-and-Detect kiến trúc inherently solve:**
   ```
   Pipeline:
   1. YOLOv11l detect person bbox
   2. Filter: only Bradford players (team classifier)
   3. Crop player (pad 20%)
   4. Stage 3A logo detection CHỈ trên crop player (not full frame)
   → Pitch logos KHÔNG NẰM TRONG crop của bất kỳ player nào → KHÔNG được inference
   ```

2. **Edge case: Pitch logo chồng lên player bbox** (khi player đứng trên logo):
   - Pitch logo bị crop một phần vào player bbox
   - Stage 3A may detect → Stage 3B classify as brand
   - Mitigation: position check — nếu logo OBB lies BELOW player feet level (y > 95% bbox), discard as "pitch contamination"
   - Heuristic accuracy estimated 85%

3. **Hard-negative mining in training:**
   - Annotate 20% frames chứa pitch logos visible nhưng NO jersey logo
   - Train model với empty labels for those frames → teach "không detect logo on grass"

**Risk:** Player đeo logo ngay vị trí bottom của crop (e.g., shorts) — confused with pitch.

**Mitigation:** Combine height check với context check (logo size relative to player → pitch logo usually larger).

### Q8. Logo bị deform khi player crouch/scrum — bbox méo

**Vấn đề:**
Player cúi xuống, logo trên ngực bị stretched/compressed theo direction người gấp. OBB detector trained on standing players → fail on deformed.

**Giải pháp v5:**

1. **Augmentation: perspective + shear:**
   ```python
   degrees: 45.0
   perspective: 0.001  # adds perspective transformation
   shear: 10.0          # ±10° shear
   ```

2. **Training data diversity:**
   - In Stage 1, quota selection ĐÃ include scrum/ruck frames (mixed category)
   - Frames có deformed logos sẽ flow into training

3. **DINOv2 embedding tolerance:**
   - DINOv2 trained on natural images với various poses → có inherent robustness
   - Validate: spot-check embeddings of deformed crops vs straight crops, cosine sim > 0.7?

**Risk:** Logo deformed beyond recognition → no method recovers it.

**Mitigation:** Accept inherent limitation; report drop in detection rate for "ruck/scrum" segments separately.

### Q9. Multiple logos very close (collar bone area có 3 small logos) — NMS suppress chúng?

**Vấn đề:**
Collar bone có thể chứa 3 logos: Domantica + Bull badge + Ellgren manufacturer, mỗi cái 20×40px, packed close together. Standard NMS với IoU 0.5 sẽ suppress.

**Cơ chế xảy ra:**
- YOLO predicts multiple OBBs nearby
- NMS suppresses any OBB pair with IoU > threshold
- Default threshold 0.5 → adjacent small logos suppressed

**Giải pháp v5:**

1. **Lower NMS threshold for small objects:**
   ```python
   # SAHI hỗ trợ class-aware NMS với different thresholds
   sahi_config = {
       'nms_iou_threshold': 0.3,  # Lower for small (vs 0.5 default)
   }
   ```

2. **Class-aware NMS:**
   - NMS chỉ suppress nếu cả 2 OBB cùng class
   - 3 different brand logos close → all kept

3. **Soft-NMS thay vì hard NMS:**
   - Decay confidence của overlap predictions thay vì suppress hoàn toàn
   - Preserve more candidates

**Risk:** Lower NMS → more duplicate detections → false positive increase.

**Mitigation:** Post-processing dedup based on DINOv2 embedding similarity (if 2 OBBs same class same location, keep higher confidence).

### Q10. Brand X có logo giống brand Y (e.g., 2 brand đều dùng text trắng-đen) — disambiguate?

**Vấn đề:**
Bradford có ~20 sponsors. Statistics: 2-3 cặp sponsors likely có visual similar (same color scheme, similar font). DINOv2 embedding có thể confuse.

**Giải pháp v5:**

1. **Margin-based decision (đã có trong Stage 3B):**
   ```python
   if top_1_similarity - top_2_similarity < 0.05:
       return "ambiguous"  # Don't commit to a brand
   ```

2. **Contrastive fine-tuning với hard negatives:**
   ```python
   # Mining: cặp brand confused thường xuyên trong validation
   hard_negative_pairs = [
       ("mcp_home", "mcp_away"),     # cùng MCP logo, khác color background
       ("aon_red", "aon_white"),     # similar
       ("cch_black", "cch_white"),
   ]
   # Train DINOv2 với triplet loss to push these apart
   ```

3. **Context-aware classification:**
   - Use position metadata as additional signal
   - "Logo on shorts" + "rectangular text" → bias toward `aon` (vì AON ở shorts)
   - "Logo on upper back center" + similar visual → bias toward `mcp`
   - This is a soft prior, not hard rule

4. **Multi-modal: kit color context:**
   - Nếu jersey màu trắng (HOME) → bias toward `mcp_home` vs `mcp_away`
   - Nếu jersey màu đen (AWAY) → bias toward `mcp_away`

**Risk:** Heuristic priors có thể fail trên kit change.

**Mitigation:** Per-kit calibration; explicit "kit_color" feature into classification head.

**Open question:** Có nên có "human-in-the-loop confirmation" cho ambiguous detections trong production? (Yes, optional flag for low-margin cases)

---

## NHÓM C — Tracking & Attribution

### Q11. Track ID swap giữa Bradford player và opponent player (similar build) — exposure attribute sai?

**Vấn đề:**
2 players close together (Bradford white #5 vs Castleford yellow #10). BoT-SORT có thể swap IDs do appearance similarity in motion blur.

**Hậu quả:** Bradford logos exposure bị attributed cho opponent track_id → lost from report.

**Giải pháp v5:**

1. **Team filter là first defense:**
   - Sau tracking, classify mỗi track_id theo dominant team color (vote across all frames)
   - Filter: chỉ keep Bradford track_ids
   - Even if 2 IDs swap, total Bradford exposure count vẫn đúng (vì cả 2 đều count if both Bradford)

2. **Sliding-window team classification:**
   - Mỗi track_id classified team mỗi 30 frames (1s)
   - Nếu team flips mid-track → flag as "swap candidate"
   - Manual review (or automated split into 2 tracks)

3. **Appearance ReID feature in BoT-SORT:**
   - BoT-SORT có appearance descriptor (ReID embedding)
   - Increase weight of appearance vs motion → better at handling occlusion
   - Tradeoff: slightly slower

**Risk:** Bradford home (white) vs Hull FC (white with stripes) trong M06 → team classifier confused.

**Mitigation:** Train team classifier với specific kit photos for each opponent. Or rely on jersey pattern (stripes vs solid) via additional CNN.

**Open question:** Có nên fine-tune ReID model on specific Bradford players? (Yes if accuracy < 85% → add jersey-number recognition as additional feature)

### Q12. Player off-screen 10s rồi quay lại — recover track ID?

**Vấn đề:**
Player Bradford rời camera frame 10s (camera focus on opposite side), sau đó quay lại. Tracker mất track → assign new track_id → considered new player → logo binding starts fresh.

**Hậu quả:** Exposure cho cùng player bị split thành 2 tracks → 2 binding processes → underestimate continuous exposure events.

**Giải pháp v5:**

1. **Extend lost_track_buffer:**
   ```python
   # BoT-SORT config
   lost_track_buffer = 300  # 10 seconds at 30fps (vs default 90 = 3s)
   ```

2. **Re-identification by appearance:**
   - Khi new track xuất hiện, compute appearance descriptor
   - Compare with descriptors of recently-lost tracks
   - If match > threshold → reuse old track_id (track merge)

3. **Logo binding stability across re-id:**
   - Logo tracker stores binding per player_identity (not just track_id)
   - When tracks merge, logo bindings merge too

**Risk:** False merge (2 different Bradford players similar appearance merged into 1).

**Mitigation:** Conservative threshold; require multiple frames of match before merging.

### Q13. Players in ruck/scrum — can't tell which body belongs to whom — attribution?

**Vấn đề:**
6-8 players pile in ruck. Tracker outputs may swap IDs. Logo detections in pile attributed wrongly.

**Giải pháp v5:**

1. **Ruck event detection:**
   ```python
   def is_ruck(player_bboxes, iou_thresh=0.3, min_players=4):
       overlap_count = 0
       for i, j in combinations(range(len(bboxes)), 2):
           if iou(bboxes[i], bboxes[j]) > iou_thresh:
               overlap_count += 1
       return overlap_count >= min_players
   ```

2. **Freeze logo binding updates during ruck:**
   - Trong ruck event, không update logo bindings (preserve pre-ruck state)
   - Resume normal binding after ruck disperses
   - Detections during ruck → flagged but not bound

3. **Aggregate exposure at TEAM level (not per-player) for ruck duration:**
   - "5 Bradford players visible in ruck" + "logo MCP detected 3 times" → count as 3 separate brand impressions, attribute to "ruck event" not individual player

**Risk:** Long ruck (>5s) → significant exposure missed if completely frozen.

**Mitigation:** Smart approach — during ruck, still count detection but mark `track_id = "ruck_aggregated"` instead of trying per-player.

### Q14. Camera zoom out: player area shrinks, tracker drop track?

**Vấn đề:**
Wide shot → players become 30-50px tall → person detection confidence drops → tracker may lose them.

**Giải pháp v5:**

1. **Lower person detection threshold during wide shots:**
   - Detect shot type (close-up / medium / wide) via average player bbox size
   - In wide shots, lower YOLO conf threshold from 0.35 → 0.25
   - Tradeoff: more FP person detections (mitigated by team filter)

2. **Use upscaled imgsz for wide shots:**
   - Default inference imgsz=1280
   - For wide shot frames, increase to 1920 (slower but better small-person detection)

3. **Accept tracker dropouts as inevitable:**
   - Document in report: "wide shot segments have lower attribution confidence"
   - QI naturally lower for wide shots (small size_score) → impact on final number minimal

---

## NHÓM D — Inference & Performance

### Q15. Inference takes too long (90-min video × 5 stages = hours) — optimize?

**Vấn đề:**
Pipeline 5-stage with multiple model inferences (person detector + logo detector + DINOv2 + tracker + SAHI + SAM2 for annotation) → each match could take 2-3 hours on T4.

**Giải pháp v5 — optimization ladder:**

1. **GPU batching:**
   - Batch person detection 32 frames at a time
   - Batch logo detection 16 crops at a time
   - DINOv2 embedding batch 32 crops

2. **Selective keyframe processing:**
   - KHÔNG run logo detection on every frame
   - New tracks: every frame for first 1s (establish binding)
   - Unstable bindings: every 5 frames
   - Stable bindings: every 15 frames (just confirmation)
   - Saves ~5× compute

3. **TensorRT optimization:**
   - Export YOLOv11-OBB to TensorRT FP16
   - 2-3× speedup vs PyTorch native
   - Same for DINOv2

4. **Half-precision inference (FP16):**
   - All models support AMP (Automatic Mixed Precision)
   - 1.5-2× speedup, negligible accuracy loss

5. **Pipeline parallelism:**
   - GPU does logo detection while CPU prepares next batch of crops
   - Use `torch.utils.data.DataLoader` with workers

**Estimated time after optimization:**
- T4 (free Colab): 60-90 min per 90-min match
- A100 (Colab Pro+): 20-30 min per match
- Multi-GPU: linear speedup

### Q16. Real-time inference (< 5s latency live broadcast) — possible?

**Vấn đề:**
Production v2 may need real-time exposure reporting (live during broadcast for sponsor activation).

**Giải pháp v5 (NOT v1, defer to v3 SaaS):**

Real-time approach (post-v1):
1. **Tiered architecture:**
   - Fast path (real-time): YOLOv11n-OBB (tiny) + lightweight ReID + simple QI
   - Slow path (offline): full v5 pipeline with audit reconciliation

2. **Streaming inference:**
   - Process video in 1-sec chunks
   - Maintain tracker state across chunks
   - Output exposure updates per chunk

3. **Latency budget:**
   - Person detect: 30ms
   - Tracking: 10ms
   - Logo detect on crops: 20-50ms (depending on # players)
   - DINOv2 embedding: 30ms per logo
   - Total: 100-200ms per frame → 5x real-time on A100

**v1 explicit scope:** Offline post-broadcast processing. Real-time deferred to v3.

### Q17. Same video re-processed (re-runs, debug) — cache?

**Vấn đề:**
During development, re-run inference 10× on same video → wasteful.

**Giải pháp v5:**

1. **Cache layers:**
   ```
   cache/
   ├── {video_id}_person_detections.parquet
   ├── {video_id}_tracks.parquet
   ├── {video_id}_logo_detections.parquet
   ├── {video_id}_dinov2_embeddings.npy
   ```

2. **Invalidation by model version:**
   - Cache key includes model version hash
   - Re-compute only if model changes

3. **Resume from checkpoint:**
   - Long inference can resume from where it stopped (per-frame checkpoint)

---

## NHÓM E — Broadcast Edge Cases

### Q18. Camera shake (handheld, drone footage) — model fail?

**Vấn đề:**
Rugby league sometimes have drone footage or handheld sideline cameras. Adds blur + perspective distortion not present in main broadcast feed.

**Giải pháp v5:**

1. **Stage 1 frame extraction filter:**
   - Compute optical flow magnitude per frame
   - Filter out frames with global motion > threshold
   - Drone/handheld auto-filtered

2. **If still useful (e.g., drone overhead view):**
   - Train separate model variant on drone-specific data (Phase 2)
   - For v1, accept inability to process drone segments

### Q19. Lens flare from stadium lights — distorts logo?

**Vấn đề:**
Strong stadium light hits logo at certain angles → lens flare/saturation → logo washed out.

**Giải pháp v5:**

1. **Augmentation: overexposure simulation:**
   ```python
   A.RandomBrightnessContrast(brightness_limit=0.5, p=0.3)
   A.HueSaturationValue(val_shift_limit=50, p=0.3)
   ```

2. **Confidence threshold dynamic per frame quality:**
   - Detect overexposed frames (mean brightness > 240)
   - Lower logo detection threshold for those (more permissive)
   - But mark detections with `quality: "overexposed"` → lower QI

### Q20. Player jersey wet (rain, sweat) — color/contrast shift?

**Vấn đề:**
Wet jersey color changes (darker, more saturated). Logo edges may bleed (white logo on now-darker jersey).

**Giải pháp v5:**

1. **Augmentation in training:**
   ```python
   A.RandomGamma(gamma_limit=(70, 130))  # darker simulation
   A.OpticalDistortion(p=0.2)             # slight warp
   ```

2. **Use both wet + dry frames in training (assuming we have rainy matches):**
   - Domain randomization via real samples
   - Tag training frames with `weather` attribute → check per-attribute AP

### Q21. Jersey torn / ripped (rugby is physical) — partial logo visible?

**Vấn đề:**
Rugby jerseys regularly get torn. Logo might be split or missing chunks.

**Giải pháp v5:**

1. **CoarseDropout augmentation:**
   ```python
   A.CoarseDropout(max_holes=3, max_height=0.2, max_width=0.3, p=0.2)
   ```
   Simulates random cutouts in training crops.

2. **Partial visibility handling (như Q3):**
   - Detect as `partial` → QI penalty 0.7×

---

## NHÓM F — Reporting & Methodology

### Q22. Sponsor disputes report numbers — audit/explain?

**Vấn đề:**
Sponsor says "We tracked our own brand exposure separately, we got 250s but you report 180s. Why?"

**Giải pháp v5:**

1. **Audit trail per-detection:**
   ```
   For every reported second of exposure:
   - frame_id, timestamp
   - player track_id
   - OBB coords
   - detection confidence
   - DINOv2 similarity (top-1, top-2, margin)
   - QI breakdown (size, position, clarity, clutter, exclusivity)
   - source: "detected" or "inferred from tracking"
   ```

2. **Per-report config disclosure:**
   ```yaml
   report_config:
     impact_threshold_seconds: 2.0  # MRC standard
     qi_weights: {size: 0.35, position: 0.20, clarity: 0.20, clutter: 0.15, exclusivity: 0.10}
     replay_handling: "report_separately"
     model_version: "v5.1.0_yolov11m_dinov2_base"
   ```

3. **Replay-ability:**
   - Snapshot all model weights + bank + config per report
   - Sponsor can request "show me the 30 frames where you detected MCP at 32:15-32:18"

**This is the #1 defensibility feature.** Without audit trail, no sponsor will trust numbers.

### Q23. 0 detections for a brand — was it absent, or model failed?

**Vấn đề:**
Report says "Romantica: 0 seconds." Did Romantica logo not appear, or did model miss?

**Giải pháp v5:**

1. **Coverage check per brand:**
   ```
   For each "0 detection" brand, run diagnostic:
   - Count frames where ANY Bradford player visible
   - Count crops where logo detector predicted ANYTHING
   - If 0 cases where logo detector predicted but brand was Argmax → likely true absence
   - If logo detector predicted but DINOv2 returned "unknown" frequently → model uncertainty, possibly present but unclassified
   ```

2. **Reporting:**
   ```
   Romantica: 0 detections
     Status: low_confidence (logo detector predicted 12 unknown brands; recommend manual review)
   
   ACS Group: 145 seconds
     Status: high_confidence (consistent detections, low ambiguity)
   ```

3. **Place "needs review" cases on manual queue for human label-then-retrain.**

### Q24. Per-position aggregation — how exactly compute "chest vs sleeve vs shorts"?

**Vấn đề:**
Report wants "exposure per kit position" but v5 detects per brand, not per position.

**Giải pháp v5:**

1. **Compute position metadata per detection:**
   ```python
   def infer_position(logo_obb, player_crop):
       """Infer position from OBB center within player crop."""
       h, w = player_crop.shape[:2]
       cx, cy = obb_center(logo_obb)
       rx, ry = cx / w, cy / h
       
       if ry < 0.10:
           return "head_collar"
       elif ry < 0.30 and 0.3 < rx < 0.7:
           return "front_chest_main"
       elif ry < 0.30:
           return "front_chest_side"
       elif ry < 0.50 and (rx < 0.2 or rx > 0.8):
           return "sleeve"
       elif ry < 0.55:
           return "front_chest_lower"
       elif ry < 0.70:
           return "shorts_front"
       elif ry < 0.90:
           return "shorts_back"
       else:
           return "socks"
   ```

2. **Aggregate report:**
   ```
   Position aggregation (across all brands):
     front_chest_main: 1247s (TopNotch 870s + Floor Tonic 377s)
     shorts_front: 892s (AON 510s + KLG 382s)
     sleeve: 567s (Chad 145s + Bartercard 122s + ATM 300s)
     socks: 234s (EM Workwear 234s)
   ```

3. **Validate position inference accuracy:**
   - 100 detections, human verify position
   - Pass: position correct ≥ 90%

**Open question:** Cầu thủ back-to-camera, logo back-top vs back-bottom — position inference reverses? Need pose detection?

---

## NHÓM G — Multi-club / Multi-sport scaling

### Q25. Mở rộng sang club mới (e.g., Wakefield Trinity) — phải làm gì?

**Vấn đề:**
v5 architecture future-proof, nhưng concretely khi nào extend?

**Giải pháp v5 — đã design ngay từ đầu:**

1. **Per-club assets:**
   ```
   clubs/
   ├── bradford_bulls/
   │   ├── sponsor_logos/
   │   ├── kit_photos/
   │   ├── team_palette.json   (HSV palettes)
   │   ├── reference_bank.npz  (DINOv2 embeddings)
   │   └── pricing.csv
   ├── wakefield_trinity/
   │   └── ... (same structure)
   ```

2. **Per-club config:**
   ```yaml
   clubs:
     wakefield_trinity:
       primary_color: "purple"
       secondary_color: "white"
       sport: "rugby_league"
       sponsor_count: 18
       reference_bank_path: "clubs/wakefield_trinity/reference_bank.npz"
   ```

3. **Workflow for adding new club:**
   - User uploads sponsor logo files
   - User runs `python scripts/build_club.py wakefield_trinity`
     - Auto-build reference bank from logos
     - Auto-extract kit colors from kit photos
     - Setup config
   - Done — pipeline ready for that club's matches

4. **Detection model is SHARED across clubs:**
   - Same YOLOv11-OBB model (trained on Bradford data) works for other clubs because:
     - Stage 3A is class-agnostic (just "logo / not logo")
     - Stage 3B uses per-club embedding bank
   - **Optional:** Per-club fine-tuning if accuracy < threshold

5. **For new sport** (e.g., soccer):
   - Same architecture
   - May need different person detector tuning (soccer players run faster, more open field)
   - QI weights different (per YAML config from v5 §4.3)
   - 2-3 weeks effort for sport-specific adaptation

---

## 🎯 Kết luận

25 câu hỏi này stress-tested v5 architecture. Kết quả:

| Nhóm | Issues found | All addressable? |
|------|---------------|-------------------|
| A. Data & Annotation | 5 | ✅ All have concrete solutions |
| B. Model & Detection | 5 | ✅ Strong on Q7, Q9, Q10; some open questions on Q6 (low-light data quantity) |
| C. Tracking & Attribution | 4 | ⚠️ Q11 team-classifier robustness needs validation; Q13 ruck handling pragmatic |
| D. Inference & Performance | 3 | ✅ Optimization ladder clear; Q16 real-time deferred |
| E. Broadcast Edge Cases | 4 | ✅ Mostly augmentation strategies; accept some inherent limitations |
| F. Reporting & Methodology | 3 | ✅ Audit trail is critical; Q24 needs pose detection for back-to-camera |
| G. Multi-club / Multi-sport | 1 | ✅ Architecture designed from day 1 for this |

**Critical open questions to validate empirically:**
1. **DINOv2 brand discrimination accuracy** (Q10) — spot-check protocol mandatory
2. **SAM 2 propagation pass rate trong rugby league specifically** — first time tested at scale
3. **Team classifier accuracy giữa Bradford white vs Hull FC white** (Q11) — needs jersey-pattern recognition
4. **Position inference accuracy với back-to-camera** (Q24) — may need pose detection

**Risk concentration:** Stage 3B (DINOv2) là single point của brand recognition. Nếu fail, full system fails. Mitigation: spot-check early in development; fallback supervised classifier ready.

**No question discovered an unsolvable problem.** v5 architecture remains valid.
