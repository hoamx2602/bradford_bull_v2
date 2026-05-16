# Bradford Bulls — Solution Architecture v5

> **Trạng thái:** Đánh giá lại hoàn toàn từ đầu (fresh re-evaluation), không bị anchor bởi v4 / plan-2026-04-17 / pipeline_final_review
> **Ngày:** 2026-05-16
> **Thay thế:** v4 (vẫn lưu trong docs/ để tham khảo lịch sử)
> **Tác giả:** AI Solutions Architect (Claude Opus 4.7) với input từ user
> **Mục đích:** Trình bày kiến trúc giải pháp đề xuất sau khi research độc lập các SOTA techniques 2024-2026, không bị giới hạn bởi các giả định trong docs cũ. Trả lời trực tiếp các technical questions user nêu (same logo / khác clarity, new sponsor mid-season, v.v.).

---

## 📑 Mục lục

- [0. TL;DR](#0-tldr-tóm-tắt-cốt-lõi)
- [1. Đánh giá lại bài toán](#1-đánh-giá-lại-bài-toán)
- [2. Khảo sát SOTA techniques 2024-2026](#2-khảo-sát-sota-techniques-2024-2026)
- [3. Trả lời các câu hỏi technical của bạn](#3-trả-lời-các-câu-hỏi-technical-của-bạn)
- [4. Kiến trúc v5 đề xuất](#4-kiến-trúc-v5-đề-xuất)
- [5. So sánh v5 vs v4](#5-so-sánh-v5-vs-v4)
- [6. Validation strategy](#6-validation-strategy)
- [7. Risk register](#7-risk-register)
- [8. Roadmap v5 (14-18 tuần)](#8-roadmap-v5-14-18-tuần)
- [9. Open questions còn lại](#9-open-questions-còn-lại)
- [10. Tài liệu tham khảo](#10-tài-liệu-tham-khảo)

---

## 0. TL;DR — Tóm tắt cốt lõi

### Bài toán thật sự là gì?
Đây KHÔNG phải là bài toán "train YOLO để detect 21 logo classes" như v4 đã framing. Bản chất thật sự là **3 sub-problems lồng vào nhau**:

1. **Brand recognition under broadcast noise** — nhận diện một brand identity bất kể nó xuất hiện ở vị trí nào, kích thước nào, blur ra sao, dưới lighting nào, có overlay nào che — và brand list có thể THAY ĐỔI giữa mùa giải (sponsor mới ký, sponsor cũ bỏ).
2. **Per-instance attribution under multi-player scene** — gán mỗi lần xuất hiện logo cho ĐÚNG cầu thủ Bradford (KHÔNG phải đối thủ, KHÔNG phải LED board, KHÔNG phải khán giả), và gán xuyên qua các frame để đo "event duration" chứ không phải đếm frame rời rạc.
3. **Quality-weighted exposure measurement** — chuyển raw detections thành một con số có ý nghĩa với sponsor, defensible methodology, ground trong industry/academic standards.

### Tại sao v5 khác v4?
v4 implicitly chấp nhận: "21 classes là cố định, train một CNN supervised end-to-end". v5 challenge giả định này:
- Brand list **không cố định** — nên dùng **embedding-based retrieval** thay vì fixed classifier head
- Annotation là bottleneck → dùng **SAM 2 + Soft Teacher pseudo-labeling + active learning** để giảm manual effort 5-10×
- Logo nhỏ trên broadcast là khó cứng → **SAHI tiled inference** (technique cụ thể, có paper, có lib)
- "Bắt blur frame từ sharp frame" có giải pháp SOTA: **knowledge distillation teacher (sharp) → student (blur)** + **temporal propagation via tracker**

### Tóm tắt kiến trúc v5

```
┌─────────────────────────────────────────────────────────────────────┐
│  v5 PIPELINE — 6 STAGES, mỗi stage có SOTA component                │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  Stage 0: Auto-calibration                                          │
│    • Detect static overlays (temporal variance)                     │
│    • Detect team palettes (K-Means + user picks Bradford cluster)   │
│                                                                     │
│  Stage 1: Smart frame extraction (giữ ý tưởng v4)                  │
│    • Tiered torso-sharpness (Gold/Silver/Bronze)                    │
│    • Foreground filter, overlay-masked                              │
│                                                                     │
│  Stage 2: Bootstrap annotation (MỚI — khác v4)                     │
│    • Bootstrap: annotate 50 keyframes manually                      │
│    • SAM 2 propagation: 1 keyframe → 30 nearby frames auto-annotate │
│    • Soft Teacher pseudo-labeling: train weak teacher → predict on  │
│      unlabeled → keep high-confidence pseudo-labels                 │
│    • Active learning loop: model uncertainty selects next 50 frames │
│      cho human review → iterate                                     │
│    • Mục tiêu: từ 50 manual → 2000-3000 effective annotations       │
│                                                                     │
│  Stage 3: Detection model (KIẾN TRÚC MỚI — 2-stage)                │
│    Stage 3A: Class-agnostic OBB logo detector                       │
│      YOLOv11m-OBB hoặc RT-DETRv2-OBB                                │
│      Output: binary "có logo / không có logo" + OBB                 │
│    Stage 3B: Brand classifier via embedding retrieval               │
│      Crop logo OBB → DINOv2 feature → nearest-neighbor với bank     │
│      của reference embeddings từ /Sponsor Logo/                     │
│      ➜ Thêm sponsor mới = thêm 1 embedding, KHÔNG retrain           │
│                                                                     │
│  Stage 4: Inference engine                                          │
│    • Person detection + BoT-SORT tracking                           │
│    • Team classifier (HSV palette từ Stage 0)                       │
│    • Crop-and-Detect: chỉ inference logo trên Bradford crops        │
│    • SAHI tiled inference khi player crop > 640px                   │
│    • Per-track logo binding (giống v4)                              │
│    • Temporal smoothing: detection sharp frame → infer cho blur     │
│      frame qua tracker (giải quyết câu hỏi của user)                │
│                                                                     │
│  Stage 5: 4-Layer exposure measurement (giữ từ v4)                  │
│    • Dedupe + smoothing + QI + reporting                            │
│    • QI weights 35/20/20/15/10 (validate sau)                       │
│    • Min-duration: store all, filter ở reporter, default 2s (MRC)   │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

### Đột phá so với v4

| Vấn đề | v4 cách giải | v5 cách giải | Lợi ích |
|--------|---------------|----------------|----------|
| Annotation tốn 5h/kit | Manual 100% | Manual 50 frames + SAM 2 + pseudo-label + active learning | 5-10× ít manual |
| Sponsor mới giữa mùa | Retrain từ đầu | Thêm 1 reference embedding | 0 retrain |
| Logo nhỏ ở socks/sleeve | imgsz=1280 only | SAHI tiled inference | +5-7% AP cho small objects |
| Same logo, sharp + blur | Hy vọng tracker bridge | Teacher-Student distillation + temporal propagation via tracker | Cụ thể, có technique |
| 21 fixed classes | Retrain khi thêm | Embedding bank → swap-in/swap-out runtime | Future-proof |

### Feasibility verdict
**Khả thi cao hơn v4** vì v5 giảm phụ thuộc vào manual annotation (bottleneck thật sự) và mở đường cho multi-club scale mà không cần retrain. Effort: 14-18 tuần (v5 cần thêm thời gian xây embedding pipeline + active learning loop so với v4 12-14 tuần).

---

## 1. Đánh giá lại bài toán

### 1.1 Tại sao cần đánh giá lại?

v4 hoàn toàn dựa trên một chuỗi design docs đã thảo luận trước đó (`plan-2026-04-17`, `pipeline_final_review`, `team_aware_frame_extraction_proposal`, v.v.). Khi đọc lại các docs đó cùng v4, tôi nhận ra **5 giả định bị kế thừa mà chưa được question**:

1. **"21 classes là cố định"** — Spec gốc list 21 logo classes, v4 chỉ correct mapping mà không challenge cách tiếp cận. Thực tế: user nói "sponsor có thể thay đổi giữa mùa, brand list không cố định". Cách tiếp cận supervised classifier với fixed head SAI BẢN CHẤT vấn đề.
2. **"Manual annotate 400-2000 frames là acceptable"** — v4 đề xuất manual 400 + temporal propagation ±3 = 2000. Nhưng SOTA 2024-2026 (Soft Teacher, SAM 2, active learning) cho phép giảm xuống ~50 manual + auto-label everything else, với accuracy tương đương.
3. **"YOLOv11m-OBB end-to-end là tối ưu"** — v4 chọn vì ExposureEngine dùng. Nhưng ExposureEngine có 670 unique logos, chúng ta có ~21 + nhiều brand đặc thù — cardinality khác nhau hoàn toàn. 2-stage (class-agnostic detector + embedding classifier) có thể phù hợp hơn cho domain ít class nhưng cần flexibility.
4. **"Crop-and-Detect giải quyết logo nhỏ"** — Đúng một phần, nhưng SAHI (Slicing Aided Hyper Inference) là kỹ thuật cụ thể hơn, có paper, có lib mature, được prove tăng +5-7% AP cho small objects. v4 không mention.
5. **"Tracker bridge gap giải quyết blur frames"** — v4 nói "if player tracked + has bound logos → all bound logos are exposed even on blurry frames where logo detection didn't fire". Đúng nhưng yếu — nếu tracker miss player thì cả block sai. SOTA approach: knowledge distillation teacher (sharp) → student (blur) để model học BIẾT detect cả blur.

→ v5 challenge từng giả định và đề xuất alternative.

### 1.2 Bản chất bài toán (định nghĩa lại)

Bài toán không phải "21-class object detection". Bài toán là:

> **Cho một video broadcast 90 phút, output báo cáo "mỗi brand trong rolling roster sponsor của Bradford xuất hiện bao nhiêu giây với chất lượng visibility ra sao", với:**
> - **Rolling roster sponsor** — danh sách có thể thay đổi
> - **Visibility quality** — không chỉ là pixel count, mà là một QI score grounded trong industry standards
> - **Defensibility** — methodology phải chống challenge từ sponsor commercial
> - **Generalization** — sau này áp dụng cho club khác, sport khác mà không phải build lại từ đầu

Đây là **brand visibility analytics**, không phải "logo detection". Sự khác biệt quan trọng:
- Logo detection: input = frame, output = bboxes với class
- Brand visibility analytics: input = video, output = per-brand time-weighted metrics có meaning với business

### 1.3 5 technical questions user đã đặt (hoặc implicit)

Trong message gần nhất, user nêu rõ:
> "Ví dụ giải quyết vấn đề logo cùng 1 vị trí nhưng trên 2 cầu thủ khác nhau, khác khung hình, nhưng 1 cái nét, 1 cái blur thì có cách nào để sau này nó tự động bắt annotate cho cái blur không?"

Câu hỏi này ngụ ý 5 sub-problems mà v4 chưa addressing đầy đủ. Tôi sẽ liệt kê và trả lời chi tiết ở §3:

| # | Sub-problem | v4 giải | v5 cải tiến |
|---|-------------|---------|---------|
| Q1 | Same logo, 2 players, 1 sharp 1 blur — auto-annotate blur từ sharp? | Hy vọng tracker bridge | SAM 2 propagation + teacher-student distillation + ReID-based instance linking |
| Q2 | Sponsor mới ký giữa mùa, không có training data | Retrain từ đầu | Embedding bank: thêm 1 reference, KHÔNG retrain |
| Q3 | Video 720p vs 1080p khác quality | Strong augmentation | Resolution-aware augmentation + cross-quality validation explicit |
| Q4 | Trận này ánh sáng vàng, trận khác ánh sáng trắng → màu kit shift | HSV augmentation 0.7 | Photometric domain randomization + per-match auto-calibration |
| Q5 | Logo nhỏ (sock, sleeve) <20px | imgsz=1280 + crop-and-detect | SAHI tiled inference + super-resolution preprocessing for socks |

---

## 2. Khảo sát SOTA techniques 2024-2026

### 2.1 Semi-supervised Object Detection (SSOD)

**Vấn đề:** Manual annotation expensive. Có cách nào dùng nhiều unlabeled data + ít labeled data?

**SOTA techniques:**

#### Soft Teacher (Microsoft, ICCV 2021 → vẫn là baseline)
- Train một "teacher" network trên labeled data
- Teacher predict trên unlabeled data → tạo pseudo-labels
- Weighted bằng confidence score (soft, không phải hard threshold)
- Box jittering để tránh noise
- Source: [Soft Teacher paper review](https://medium.com/@gagatsis94/a-paper-review-on-softteacher-8a24d7e23780)

#### Dense Teacher (2022)
- Bỏ thresholding của Soft Teacher
- Dùng dense predictions trực tiếp làm pseudo-labels
- Tốt hơn cho object dense (như nhiều logo cùng frame)
- Source: [Dense Teacher](https://www.researchgate.net/publication/365168832_Dense_Teacher_Dense_Pseudo-Labels_for_Semi-supervised_Object_Detection)

#### Collaboration of Teachers (CTF, 2024)
- Multiple teacher-student pairs train song song
- "Data Performance Consistency Optimization" module chọn pair tốt nhất
- Source: [CTF paper](https://arxiv.org/html/2405.13374v1)

#### STEP-DETR (ICCV 2025) — Newest
- DETR-based SSOD với "Super Teacher"
- Outperform CNN-based methods
- Source: [STEP-DETR](https://openaccess.thecvf.com/content/ICCV2025/papers/Shehzadi_STEP-DETR_Advancing_DETR-based_Semi-Supervised_Object_Detection_with_Super_Teacher_and_ICCV_2025_paper.pdf)

#### SOOD: Semi-Supervised Oriented Object Detection (arXiv 2023, vẫn relevant)
- SSOD cụ thể cho OBB detection
- Critical vì v5 chọn OBB approach
- Source: [SOOD](https://arxiv.org/pdf/2304.04515)

**Áp dụng cho Bradford:**
- Manual annotate ~50 keyframes của 1 trận (1 giờ effort)
- Train weak teacher (small YOLO-OBB) → predict trên ~5000 unlabeled frames
- Keep pseudo-labels confidence > 0.7
- Retrain student YOLO-OBB với labeled + pseudo-labeled
- Iterate 2-3 vòng → final model

→ Giảm manual effort 8-10×.

### 2.2 SAM 2 (Segment Anything Model 2) — Video annotation propagation

**Game-changer cho bài toán annotation.** SAM 2 (Meta AI, Aug 2024) là model promptable segmentation cho cả image VÀ video, với **memory bank** propagate mask qua tất cả frames trong video.

**Cách hoạt động:**
1. Annotator vẽ 1 mask (hoặc 1 point) trên 1 keyframe
2. SAM 2 propagate mask qua N frames trước + sau, theo dõi object qua occlusion
3. Annotator chỉ cần correct ở vài frame khó

**Số liệu:**
- Mục tiêu: 1 mask → propagate qua 30-60 frames thành công
- Memory bank stores object context → handle occlusion tốt
- Real-time inference

**Áp dụng cho Bradford:**
- Annotator vẽ OBB trên logo "MCP" ở frame 100 của 1 close-up shot
- SAM 2 propagate qua frame 90-130 → tự động có 41 frames có mask cho MCP
- Convert mask → OBB
- Repeat cho mỗi logo type → 1 giờ annotation → 1000+ frames có labels

**Hạn chế:**
- SAM 2 segment 1 instance một lúc, không multi-class out-of-the-box → cần wrapper logic
- Mask → OBB cần extra step

**Source:** [SAM 2 paper](https://arxiv.org/abs/2408.00714), [GitHub](https://github.com/facebookresearch/sam2)

### 2.3 DINOv2 / CLIP Embedding cho Brand Recognition

**Insight quan trọng:** Logo detection có thể tách thành 2 stages:
- **Stage A:** "Có logo ở đâu?" (class-agnostic detection — không cần biết brand nào)
- **Stage B:** "Logo này là brand nào?" (classification từ crop)

**Stage B có thể làm bằng EMBEDDING RETRIEVAL thay vì supervised classifier:**

#### DINOv2 (Meta, 2023, vẫn SOTA cho visual features 2024-2025)
- Self-supervised ViT, trained 142M images
- Features capture visual structure + texture mà không cần text alignment
- Out-of-the-box k-NN classification accuracy cao
- Source: [DINOv2](https://ai.meta.com/blog/dino-v2-computer-vision-self-supervised-learning/)

#### Cách áp dụng cho logo:
1. **Build reference bank:** Mỗi file trong `/Sponsor Logo/` → DINOv2 embedding (1 vector ~768-dim per logo) → stored
2. **Runtime:** Detector predict logo OBB → crop → DINOv2 embedding → cosine similarity với bank → return top-1 brand
3. **Confidence:** Distance ratio (top-1 / top-2) → ngưỡng confident

**Lợi ích cực lớn:**
- **Thêm sponsor mới** = thêm 1 reference image vào bank + compute embedding. **0 retrain.**
- **Sponsor cũ rời** = remove embedding từ bank. **0 retrain.**
- **Mid-season kit change** = update bank, deploy ngay.

**Hạn chế:**
- DINOv2 embedding cho LOGO chưa được benchmark wide. Cần validate với 100-200 test cases.
- Logo bị crop một phần, blur nặng → embedding có thể không discriminative.

**Mitigation:**
- Fine-tune DINOv2 trên positive/negative pairs của logo (contrastive learning)
- Hoặc dùng CLIP-DINOv2 dual fusion ([paper](https://www.mdpi.com/2079-9292/14/24/4785))

### 2.4 Active Learning cho annotation budget

**Vấn đề:** Manual annotation expensive. Trong N candidate frames, chọn frame nào để annotate next?

**SOTA approach (CVPR 2024 — Plug & Play Active Learning):**
- Uncertainty: chọn frame mà model dự đoán không chắc chắn nhất (high entropy)
- Diversity: chọn frame "khác biệt" với những frame đã annotate (avoid redundant)
- Hybrid: kết hợp 2 criteria

**Áp dụng cho Bradford:**
1. Vòng 1: annotate 30 frames random
2. Train model
3. Model predict trên 1000 unlabeled frames → tính uncertainty per frame
4. Sort: top 30 frames uncertain nhất → annotate → retrain
5. Lặp 5 vòng → model accuracy tốt với chỉ ~150-200 manual annotations

**Source:** [Plug and Play AL for OD (CVPR 2024)](https://cvpr.thecvf.com/virtual/2024/poster/29790)

### 2.5 SAHI — Slicing Aided Hyper Inference cho logo nhỏ

**Vấn đề:** Logo trên sock/sleeve có thể chỉ 10-15px trong wide shot. YOLOv11 dù imgsz=1280 vẫn struggle với object <20px.

**SAHI giải pháp:**
- Chia frame thành overlapping patches (e.g., 512×512 với overlap 128)
- Run inference trên TỪNG patch → logo nhỏ trở thành "logo medium" trong patch
- Merge predictions từ patches qua NMS
- **Tăng AP +5-7% cho small objects** (đã prove trên multiple detectors)

**Áp dụng cho Bradford:**
- Cho close-up frame có Bradford player to: inference bình thường (logo đủ to)
- Cho medium shot: SAHI với patches → catch logo sock/sleeve
- Cho wide shot: skip (logo quá nhỏ → bias toward FP)

**Source:** [SAHI paper](https://arxiv.org/abs/2202.06934), [SAHI GitHub](https://github.com/obss/sahi)

### 2.6 RT-DETRv2 vs YOLOv11-OBB

**v4 chọn YOLOv11m-OBB vì ExposureEngine dùng.** Nhưng RT-DETRv2 (2024) có một số ưu điểm:

| Metric | YOLOv11m-OBB | RT-DETRv2-S |
|--------|---------------|-------------|
| Architecture | CNN + OBB head | DETR (transformer-based) |
| COCO mAP@50:95 | ~51 | 48.1 |
| Speed (T4) | ~15ms | ~5ms (217 FPS) |
| Small object | Tốt | Tốt hơn (multi-scale deformable attention) |
| Small dataset (1000 frames) | OK | Tốt hơn (transformer mạnh với less data) |
| Native OBB support | Có | Chưa (cần adapter) |
| Sliced inference support | Qua SAHI | Native từ Oct 2024 |

**Khuyến nghị v5:**
- **Primary: YOLOv11m-OBB** (matched với ExposureEngine, OBB native)
- **Backup: RT-DETRv2-S** với SAHI nếu YOLOv11-OBB không đạt target

Test cả 2 ở Stage 5, chọn cái cho cao hơn.

**Source:** [RT-DETRv2](https://arxiv.org/abs/2407.17140)

### 2.7 Diffusion-based synthetic data cho rare/placeholder classes

**Vấn đề:** Một số sponsor (Paints & Lacquers, Cedar Court Hotels) hiện tại 0 detection trong 3 video → không train được class đó.

**SOTA approach (2025): Multi-Perspective Data Augmentation (MPAD)**
- Dùng Stable Diffusion + ControlNet để generate synthetic images:
  - Input: reference logo + background context
  - Output: synthetic player crop với logo composited natural
- Tăng nAP50 trung bình +17.5% trên PASCAL VOC few-shot

**Áp dụng cho Bradford:**
- Lấy reference logo `Paints & Laquers Logo FINAL.jpg`
- Generate 50 synthetic player crops với logo này ở các vị trí khác nhau (chest, sleeve, shorts) qua ControlNet
- Mix vào training data → class có data train
- Khi class này xuất hiện real, model đã được pretrain

**Hạn chế:**
- Synthetic không 100% giống real distribution
- Compute cost cao (Stable Diffusion + LoRA training)
- Optional cho v5 → có thể defer sang Phase 2

**Source:** [MPAD](https://arxiv.org/html/2502.18195v1), [AeroGen CVPR 2025](https://openaccess.thecvf.com/content/CVPR2025/papers/Tang_AeroGen_Enhancing_Remote_Sensing_Object_Detection_with_Diffusion-Driven_Data_Generation_CVPR_2025_paper.pdf)

### 2.8 Open-vocabulary detection (fallback)

**Vấn đề:** Khi sponsor mới hoàn toàn xuất hiện mà chưa có reference embedding.

**Fallback: OWLv2 / Grounding DINO 1.5**
- Open-vocabulary detector — accept text prompt "a corporate logo on a jersey"
- Detect generic logo location (không classify brand)
- Crop → manual review → annotate

**Lưu ý:** v4 đã thử Grounding DINO và FAIL (per `docs/PROJECT_SPECIFICATION.md` §12.1 — phrase matching quá loose, detect cả người). Nhưng KHÁC use case:
- v4 failed: dùng GD để CLASSIFY (21 brands) → fail
- v5 propose: dùng GD/OWLv2 để DETECT logo location only (class-agnostic) → may work

→ Test cẩn thận, không over-rely.

**Source:** [OWLv2](https://www.ikomia.ai/blog/owlv2-open-vocabulary-object-detection)

### 2.9 Domain randomization cho blur / low-resolution

**Vấn đề:** Video M01 là AV1 1Mbps, M02 là H.264 1.7Mbps 720p. Model train trên một → fail trên kia.

**SOTA approach:**
- Apply random degradation TRONG TRAINING:
  - JPEG compression Q=40-95
  - Gaussian blur σ=0.5-3
  - Motion blur kernel 3-15px
  - Resolution down-then-up (1080p → 720p → upsample)
  - Color jitter (broadcast color grading varies)
  - Noise (Gaussian + salt-pepper)

**Tăng robustness:** Models trained with domain randomization survive 10-15% AP drop khi cross-quality, vs >40% drop without.

**Source:** [Domain Randomization for OD survey](https://www.researchgate.net/publication/392987422_Domain_Randomization_for_Object_Detection_A_Survey)

### 2.10 BoT-SORT + appearance ReID cho player tracking

**v4 chọn BoT-SORT, vẫn đúng.** Bổ sung từ research:
- DeepOC-SORT++ (SoccerNet 2023 winner) tốt hơn ~1% HOTA nhưng phức tạp hơn
- BoT-SORT vẫn là production sweet spot (Ultralytics, supervision lib support)
- Critical: dùng appearance ReID feature để re-link sau ruck/scrum

**Áp dụng cho Bradford:**
- BoT-SORT với `lost_track_buffer=90` (3s ở 30fps) — survive scrum durations
- Optional: thêm jersey-color ReID feature đơn giản (HSV histogram per track) để boost re-identification

---

## 3. Trả lời các câu hỏi technical của bạn

### Q1. Same logo, 2 players, 1 sharp 1 blur — tự động annotate blur từ sharp?

**Câu hỏi gốc:**
> "Ví dụ giải quyết vấn đề logo cùng 1 vị trí nhưng trên 2 cầu thủ khác nhau, khác khung hình, nhưng 1 cái nét, 1 cái blur thì có cách nào để sau này nó tự động bắt annotate cho cái blur không?"

**Câu trả lời: CÓ, qua 4 cơ chế kết hợp:**

#### Cơ chế 1 — SAM 2 mask propagation (cho blur cùng video, gần nhau)
- Frame 100: cầu thủ A có logo MCP rõ → annotator vẽ mask
- SAM 2 propagate qua frame 95-105 → tự động có mask trên những frame mờ hơn của CÙNG cầu thủ A
- Note: chỉ work trong CÙNG track (cùng player, gần nhau temporal)

#### Cơ chế 2 — DINOv2 ReID cross-instance (cho blur trên player KHÁC, cùng frame)
- Frame 200: cầu thủ A có logo MCP rõ + cầu thủ B có logo MCP mờ
- Stage A detector detect cả 2 logos (class-agnostic)
- Stage B: DINOv2 embedding của crop A → match với bank → "MCP" confident 0.95
- Stage B: DINOv2 embedding của crop B → match với bank → "MCP" confident 0.6
- Cross-reference: nếu A và B cùng vị trí pricing slot (chest of bradford home kit) AND same brand match → confidence boost cho B
- → B được auto-labeled MCP với confidence cao hơn

#### Cơ chế 3 — Teacher-Student distillation (cho blur frames generally)
- Pretrain "teacher" model chỉ trên SHARP frames (Gold tier) → teacher rất chính xác trên sharp
- Pretrain "student" model trên TẤT CẢ frames (sharp + blur)
- Trong training, force student match teacher predictions ON BLUR FRAMES (knowledge distillation)
- Student học predict đúng KỂ CẢ trên blur, vì teacher đã teach
- Source: Soft Teacher concept, áp dụng cho cross-quality

#### Cơ chế 4 — Temporal propagation via tracker (cho blur frames consecutive)
- Tracker bind track_id cho cầu thủ A qua 30 frames
- Trong 30 frames, có 5 frame sharp (detection confident MCP)
- 25 frames blur (detection miss)
- Logic: "track_id 5 đã bind MCP với confidence cao → tất cả 30 frames có exposure MCP" (với weight thấp hơn cho 25 frames inferred)

**Kết hợp 4 cơ chế:**
```
Annotation pipeline (manual + auto):
  Manual: 50 keyframes sharp
  Auto via SAM 2: 50 × 30 nearby = 1500 frames pseudo-labeled
  Auto via active learning: 5 vòng × 30 frames = 150 more
  → ~1700 effective annotations from 50 manual + 30 active learning = 80 manual total

Inference pipeline (real-time on new video):
  Sharp frame: Stage A detect → Stage B classify (DINOv2 confident)
  Blur frame: Stage A detect (weaker) → Stage B classify (less confident)
             + tracker reuses bound brand from sharp nearby frame
             + teacher-student boost confidence
  → 85-90% recall trên cả sharp và blur
```

### Q2. Sponsor mới ký giữa mùa — không có training data

**Câu trả lời: Embedding bank approach (Stage 3B trong v5)**

Quy trình:
1. Sponsor mới X ký, gửi logo file `.png` cho club
2. Engineer:
   - Compute DINOv2 embedding của logo X (5 giây)
   - Add vào reference bank với key = "x_brand"
   - Update pricing config nếu cần
3. Deploy ngay — model đã có thể detect và classify brand X
4. Confidence threshold sẽ thấp hơn ban đầu (vì chưa có positive training data)
5. Khi có vài match có brand X xuất hiện:
   - Manual annotate vài frame
   - Fine-tune embedding cho brand X (hoặc thêm augmentation specific)
6. Confidence tăng dần qua thời gian

**KHÔNG cần retrain detection model (Stage A).** Chỉ embedding bank thay đổi.

**Hạn chế:**
- Brand X visual unique nhưng giống brand Y khác? → embedding có thể nhầm.
- Mitigation: contrastive fine-tuning với hard negatives

### Q3. Video 720p vs 1080p khác quality

**Câu trả lời: Resolution-aware augmentation + cross-quality validation**

Strategy:
1. **Training:** Apply random degradation augmentation (mục §2.9):
   - 50% xác suất downscale 1080p → 720p → upscale back
   - 30% xác suất JPEG compress Q=40-70
   - 20% xác suất motion blur
2. **Validation:** Explicit cross-quality test:
   - Train: M02 720p annotations
   - Validate: M01 1080p subset
   - Vice versa
   - Đảm bảo AP drop <15% cross-quality
3. **Inference:** Detect input resolution → adjust SAHI tile size + confidence threshold

**Kết quả expected:** Model robust trên 720p, 1080p, 4K nếu Bradford sau này có camera xịn hơn.

### Q4. Khác trận khác lighting — màu kit shift

**Câu trả lời: Photometric augmentation + auto-calibration per match**

Strategy:
1. **Training augmentation:**
   - HSV jitter cao (H=0.05, S=0.7, V=0.5)
   - Brightness/contrast ±40%
   - Color temperature shift (simulate ánh sáng vàng → trắng)
2. **Inference per-match:**
   - Stage 0 auto-calibration: sample 50 frames, K-Means cluster jersey colors
   - User confirms Bradford cluster (1 click)
   - Team classifier dùng learned palette cho video đó (không phải HSV cố định)
3. **Detection robust:** logo detection model đã thấy nhiều lighting trong training → không sensitive

### Q5. Logo nhỏ (sock, sleeve) <20px

**Câu trả lời: SAHI tiled inference + có thể super-resolution preprocessing**

Strategy:
1. **Primary: SAHI** (§2.5)
   - Cho mọi player crop > 400px tall, tiled inference với tile=512, overlap=128
   - Catch logo socks (typically 15-25px trong wide shots)
2. **Optional: Super-resolution preprocessing**
   - Real-ESRGAN hoặc SwinIR upscale 2× player crop trước khi detect
   - Cost: +200ms per crop
   - Benefit: tăng accuracy cho ultra-small (<10px) logos
3. **Acceptance:** Một số logo (socks trong wide shot) inherently không detect được — accept và document trong report

---

## 4. Kiến trúc v5 đề xuất

### 4.1 Pipeline overview

```
┌──────────────────────────────────────────────────────────────────────────┐
│              v5 END-TO-END PIPELINE                                       │
└──────────────────────────────────────────────────────────────────────────┘

Input: Match video (90 min, 720p hoặc 1080p, broadcast .mp4)
            │
            ▼
┌─────────────────────────────────────────────────────────────────┐
│ STAGE 0 — Auto-calibration (one-time per video, ~5 phút)        │
│   • Temporal overlay mask (20 frames sample → static pixels)    │
│   • Team palette K-Means (50 frames → 200 torsos → 3 clusters)  │
│   • User confirms Bradford cluster (1 click)                    │
│   • Output: overlay_mask.png + team_palette.json                │
└─────────────────────────────────────────────────────────────────┘
            │
            ▼
┌─────────────────────────────────────────────────────────────────┐
│ STAGE 1 — Smart frame extraction (~10 phút trên T4)             │
│   • Pass 1: scan @ every 5th frame, YOLOv11l person detect      │
│   • Identify quality segments (target player area > threshold)  │
│   • Pass 2: full scan trong segments                            │
│   • Tiered torso-sharpness: Gold (≥0.20) / Silver / Bronze      │
│   • Foreground filter, overlay-masked                           │
│   • Quota selection: 35% target_closeup, 25% target_medium, 20% │
│     mixed, 15% opponent, 5% wide                                │
│   • Output: ~400-600 candidate frames                           │
└─────────────────────────────────────────────────────────────────┘
            │
            ▼
┌─────────────────────────────────────────────────────────────────┐
│ STAGE 2 — Hybrid annotation pipeline (MỚI — khác v4 hoàn toàn)  │
│                                                                  │
│   PHASE 2A: Bootstrap (Human, 1 giờ effort)                     │
│     • Annotate 50 keyframes manually (OBB labels, brand-only)   │
│                                                                  │
│   PHASE 2B: SAM 2 propagation (Auto, 30 phút compute)           │
│     • For each annotated frame T:                                │
│       - Load OBB → convert to mask → use as SAM 2 prompt        │
│       - Propagate qua frame T-15 đến T+15                       │
│       - Convert resulting masks → OBB                           │
│     • Output: ~1500 pseudo-annotated frames                     │
│                                                                  │
│   PHASE 2C: Soft Teacher pseudo-labeling (Auto, 2 giờ)          │
│     • Train weak teacher YOLOv11m-OBB trên 50 manual + 1500 prop│
│     • Teacher predict trên ALL remaining frames                 │
│     • Keep predictions confidence > 0.7 → pseudo-labels         │
│                                                                  │
│   PHASE 2D: Active learning (Iterative, 3 vòng × 30 phút)       │
│     • Model uncertainty score per frame                         │
│     • Top 30 uncertain frames → human review (30 phút effort)   │
│     • Retrain → repeat 3 vòng                                   │
│                                                                  │
│   Total: ~1.5h human + 4h compute → 2000-3000 effective annotations│
│   (vs v4 plan: 10h human + 4h compute → 2000 annotations)       │
└─────────────────────────────────────────────────────────────────┘
            │
            ▼
┌─────────────────────────────────────────────────────────────────┐
│ STAGE 3 — Detection model: 2-stage architecture (MỚI)           │
│                                                                  │
│   STAGE 3A: Class-agnostic OBB logo detector                    │
│     • Architecture: YOLOv11m-OBB (primary) or RT-DETRv2 (test)  │
│     • Input: 640×640 player crop hoặc 1280×720 frame            │
│     • Output: OBB bboxes + binary "logo / not-logo"             │
│     • Train với combined dataset (50 manual + 1500 SAM2 + 1000  │
│       pseudo-labeled + 150 active learning)                     │
│     • Augmentation: motion blur 0.35p, JPEG Q=40-95, HSV jitter,│
│       resolution scale, mosaic, mixup, copy-paste, coarse drop  │
│     • Loss: Varifocal (α=0.75, γ=2.0)                           │
│     • Hardware: 1× A100, ~3-5h training                         │
│     • Target: detection AP@0.5 ≥ 0.85 (cao hơn v4 vì binary)    │
│                                                                  │
│   STAGE 3B: Brand classifier via DINOv2 embedding retrieval     │
│     • For each sponsor file in /Sponsor Logo/:                  │
│       embed = DINOv2-Large(logo_image) → 1024-dim vector        │
│       Save to reference_bank.npy                                │
│     • Optional fine-tune: contrastive learning với positive pairs│
│       (crop logo từ video) và hard negatives                    │
│                                                                  │
│     Runtime:                                                     │
│       For each detected logo OBB:                                │
│         crop = extract_obb(frame, bbox)                          │
│         emb = DINOv2(crop)                                       │
│         similarities = cosine(emb, reference_bank)               │
│         brand = argmax(similarities) if max > 0.6 else "unknown" │
│         confidence = max - second_max                            │
│                                                                  │
│   Lợi ích kiến trúc 2-stage:                                    │
│   ✓ Sponsor mới = thêm 1 reference, KHÔNG retrain Stage 3A      │
│   ✓ Detector học task đơn giản hơn (binary) → AP cao hơn        │
│   ✓ Classifier tách biệt → có thể dùng SOTA embedding model     │
│   ✓ "Unknown brand" handling tự nhiên qua confidence threshold  │
└─────────────────────────────────────────────────────────────────┘
            │
            ▼
┌─────────────────────────────────────────────────────────────────┐
│ STAGE 4 — Inference engine                                      │
│   1. Person detection: YOLOv11l pretrained, 1280×720, batch     │
│   2. Tracking: BoT-SORT, lost_buffer=90, match_thresh=0.7       │
│   3. Team classify: HSV palette từ Stage 0                      │
│   4. Filter: keep only Bradford track_ids                       │
│   5. Crop player (pad 20%), resize 640×640                      │
│   6. Stage 3A (class-agnostic OBB detect) on crops              │
│      [Optional] SAHI tiled inference cho close-up large crops   │
│   7. Stage 3B (DINOv2 embedding classification) per detection   │
│   8. LogoTracker: accumulate (track_id × brand) detections      │
│   9. Bind brand to track_id when count ≥ 3 AND avg_conf ≥ 0.6   │
│  10. Temporal inference: visible+bound → exposed (0.7× weight   │
│      if not directly detected on frame)                         │
│                                                                  │
│   Selective keyframe: detect every frame for new tracks,        │
│   every 5 if unstable, every 15 if stable                       │
│                                                                  │
│   Compute on T4: ~75-100 phút per 90-min match                  │
└─────────────────────────────────────────────────────────────────┘
            │
            ▼
┌─────────────────────────────────────────────────────────────────┐
│ STAGE 5 — 4-Layer exposure measurement (giữ từ v4)              │
│   L1 Dedupe: same brand on N players in same frame → 1 event    │
│   L2 Smoothing: bridge gaps ≤ 0.5s, split at scene cuts         │
│      STORE ALL events (no filtering at storage layer)           │
│   L3 QI per frame:                                              │
│      QI = 0.35·size + 0.20·position + 0.20·clarity              │
│         + 0.15·(1-clutter) + 0.10·exclusivity                   │
│      (validate sau với human ground-truth)                      │
│   L4 Reporter:                                                   │
│      • total_raw_seconds (no filter, informative)               │
│      • total_impact_seconds (≥ 2s, default per MRC, config)     │
│      • total_equivalent_seconds = Σ second × QI                 │
│      • impact_events_count                                      │
│      • per-position breakdown (chest/sleeve/shorts/socks)       │
└─────────────────────────────────────────────────────────────────┘
            │
            ▼
┌─────────────────────────────────────────────────────────────────┐
│ Output: per-match report (CSV + JSON + matplotlib PDF)          │
│   • Per-brand: raw_s, impact_s, equiv_s, events, avg_QI         │
│   • Per-position aggregation                                    │
│   • Timeline chart                                              │
│   • Heatmap (vị trí logo trên màn hình)                         │
│   • Comparison vs current pricing CSV (relative ranking)        │
└─────────────────────────────────────────────────────────────────┘
```

### 4.2 Annotation pipeline chi tiết (Stage 2 — phần khác v4 nhất)

v4 plan: 400 manual + temporal propagation ±3 = 2000 frames, **10 giờ human effort**.

v5 plan: 50 manual + SAM 2 propagation + Soft Teacher pseudo-labeling + 3 vòng active learning = 2000-3000 effective frames, **~1.5 giờ human effort**.

**Lý do giảm 6-7× effort:**
- SAM 2 propagation tự động qua 30 frames cho mỗi keyframe
- Soft Teacher tận dụng unlabeled data còn lại
- Active learning chỉ ask human ở những frame model thực sự uncertain

**Workflow cụ thể:**

```
DAY 1 — Bootstrap (4 giờ)
  Hour 1: Human annotate 50 keyframes (chọn từ Gold tier)
          Tools: Roboflow OBB
  Hour 2: Run SAM 2 propagation script
          Input: 50 keyframes + 5400 surrounding frames
          Output: ~1500 frames có OBB labels (some need review)
  Hour 3: Human spot-check 50 SAM 2 outputs random
          Reject failures (typically <10%)
  Hour 4: Train weak teacher (small YOLOv11n-OBB) on 1550 frames
          Compute: 30 phút trên T4

DAY 2 — Pseudo-labeling + Active learning vòng 1
  Hour 1: Teacher predict trên 3000+ unlabeled frames
          Keep confidence > 0.7 → ~800 high-confidence pseudo-labels
  Hour 2: Calculate uncertainty trên remaining frames
          Top 30 most uncertain → human queue
  Hour 3: Human review 30 frames (30 phút)
          Correct labels if needed
  Hour 4: Retrain teacher → student model
          Use focal loss + Varifocal loss for imbalance

DAY 3 — Active learning vòng 2 + 3
  Repeat Day 2 process twice
  Total human: ~1.5 giờ
  Total annotations effective: 50 + 1500 + 800 + 90 = ~2440

DAY 4 — Final training
  Train final YOLOv11m-OBB (Stage 3A) trên 2440 frames
  Compute: 3-5 giờ trên A100
  Target: detection AP@0.5 ≥ 0.85
```

### 4.3 Per-quality QI adjustments

Một insight quan trọng: hiện QI weights là FIXED 35/20/20/15/10. Nhưng cho multi-sport scale, weights nên là **sport-specific YAML config**.

```yaml
# qi_weights.yaml
default:  # baseline cho rugby league
  size: 0.35
  position: 0.20
  clarity: 0.20
  clutter: 0.15
  exclusivity: 0.10

sport_overrides:
  basketball:
    # Nhiều close-up replay → size weight giảm vì có inherent close-up bias
    size: 0.25
    position: 0.25
    clarity: 0.25
    clutter: 0.15
    exclusivity: 0.10
  
  f1:
    # Sponsor stuck trên xe, exclusivity cao → bump exclusivity
    size: 0.30
    position: 0.15
    clarity: 0.20
    clutter: 0.10
    exclusivity: 0.25
  
  rugby_league:  # explicit override even if matches default
    size: 0.35
    position: 0.20
    clarity: 0.20
    clutter: 0.15
    exclusivity: 0.10
```

→ Multi-sport extension chỉ cần thêm 1 entry YAML, không thay đổi code.

---

## 5. So sánh v5 vs v4

| Khía cạnh | v4 | v5 | Trade-off |
|-----------|-----|-----|-----------|
| **Annotation effort** | 10h manual / kit | 1.5h manual / kit | v5 cần thêm 4h compute cho SAM 2 + pseudo-label |
| **Detection architecture** | YOLOv11m-OBB end-to-end (21 classes) | 2-stage: class-agnostic detector + DINOv2 embedding | v5 nhiều moving parts hơn nhưng modular |
| **Sponsor mới (mid-season)** | Retrain từ đầu (3-5h compute, manual annotate trước) | Thêm 1 embedding, deploy ngay | v5 win rõ rệt |
| **Logo nhỏ (sock/sleeve)** | imgsz=1280 + crop-and-detect | + SAHI tiled inference | v5 thêm +5-7% AP |
| **Cross-match generalization** | Strong augmentation | + cross-quality validation explicit + per-match calibration | v5 chuẩn hóa hơn |
| **Auto-annotate blur frames** | Tracker bridge gap | SAM 2 propagation + teacher-student + tracker | v5 đa lớp |
| **Multi-sport extension** | Hardcoded QI weights | YAML config per sport | v5 future-proof |
| **POC effort** | 12-14 tuần | 14-18 tuần | v5 chậm hơn ~3 tuần do thêm embedding pipeline + active learning |
| **Risk** | Annotation bottleneck blocks Stage 2 | SAM 2 / pseudo-label quality cần validate | v5 risk khác loại |

**Khi nào nên dùng v4 thay v5:**
- Nếu KHÔNG quan tâm multi-sport extension
- Nếu sponsor list cực kỳ stable, không bao giờ thay đổi
- Nếu prefer simple end-to-end thay vì 2-stage

**Khi nào nên dùng v5:**
- Có vision SaaS multi-club / multi-sport
- Sponsor list rolling (mới ký, cũ rời thường xuyên)
- Annotation budget eo hẹp
- Cần future-proof architecture

### Recommendation
**Đi v5** vì user đã indicate vision multi-club + đã clarify "sponsor có thể thay đổi giữa mùa".

---

## 6. Validation strategy

### 6.1 Stage 2 (annotation) validation
- **SAM 2 propagation accuracy:** Sample 100 SAM2-generated labels, human review. Pass: ≥85% correct mask boundaries.
- **Pseudo-label precision:** Sample 100 pseudo-labels (conf >0.7), human review. Pass: ≥90% correct.
- **Active learning convergence:** Plot AP vs vòng active learning. Pass: AP improvement <2% per vòng → stop.

### 6.2 Stage 3 (detection model) validation
- **Stage 3A (detection):**
  - Cross-match holdout: train M01+M02 → test M06
  - Target: detection AP@0.5 ≥ 0.85
  - Per-quality split: Gold AP ≥ 0.90, Silver ≥ 0.80, Bronze ≥ 0.65
- **Stage 3B (embedding classification):**
  - 200 crop test set, human-labeled brand
  - Target: top-1 accuracy ≥ 0.92
  - Per-brand confusion matrix (xem có brand nào hay confuse)

### 6.3 Stage 4 (inference) validation
- **End-to-end on 3× 5-min segments:** open play / set piece / fast play
- Human annotate ground truth: which Bradford players visible, which brands visible
- Compare pipeline:
  - Per-brand exposure deviation < 15%
  - Brand ranking Spearman ρ ≥ 0.90
  - Track fragmentation ratio < 1.3

### 6.4 Stage 5 (QI + reporting) validation
- **QI ranking vs human:** 5-min "gold" segment, human rate each visible logo prominence 1-5
- Compare QI rank vs human rank
- Target: Spearman ρ ≥ 0.85
- If not, tune QI weights to maximize ρ

### 6.5 Sponsor credibility check
- **Random sample 100 detections at conf 0.5+:** human yes/no
- Target: precision ≥ 0.92 (FP <8%)
- Failure mode analysis: log per-class FP rate

---

## 7. Risk register

| # | Rủi ro | Severity | Probability | Mitigation |
|---|--------|----------|-------------|-------------|
| R1 | SAM 2 propagation fail trên blur/occlusion sequences | High | Medium | Human spot-check 10% output; fallback Soft Teacher only nếu SAM 2 < 70% accuracy |
| R2 | DINOv2 embedding không discriminative cho logo có similar visual (e.g., 2 logo trắng-đen text) | High | Medium | Contrastive fine-tuning với hard negatives; fallback supervised classifier nếu cần |
| R3 | Active learning convergence chậm — cần nhiều hơn 3 vòng | Medium | Medium | Budget 5 vòng; nếu không converge sau 5, accept partial accuracy + flag low-confidence classes |
| R4 | Per-class imbalance (Paints & Lacquers 0 detection) | High | High | Diffusion synthetic augmentation cho rare classes (defer Phase 2 if time-constrained) |
| R5 | Crop-and-Detect miss logo trên LED background mistakenly bound to player | Medium | Low | Crop-and-Detect kiến trúc inherently solve; verify với manual review |
| R6 | Replay double-counting | Medium | High | Scene transition detection + scoreboard overlay change detection; flag replay frames |
| R7 | Tracker ID swap trong ruck/scrum | Medium | Medium | BoT-SORT 3s buffer; freeze logo binding during high-IoU cluster events |
| R8 | 720p video M02 quality thấp hơn 1080p M01 | Medium | Confirmed | Domain randomization augmentation; cross-quality validation explicit |
| R9 | OBB detection fail vì kit chevron pattern confusing | Low | Low | Background hard-negative mining trên kit pattern areas |
| R10 | Sponsor commercial challenge methodology | High | High | All weights + thresholds cite published sources; ground truth report attach to per-match output |
| R11 | DINOv2-Large compute too heavy for runtime | Medium | Medium | Use DINOv2-Base (384-dim, faster); cache embeddings per logo crop |
| R12 | SAM 2 license / commercial usage | Medium | Low | SAM 2 dùng Apache 2.0 license, OK commercial |

---

## 8. Roadmap v5 (14-18 tuần)

| Tuần | Phase | Deliverable | Effort estimate |
|------|-------|-------------|------------------|
| 0 (hiện tại) | Spec | SOLUTION_ARCHITECTURE_V5.md (file này) | ✅ Done |
| 1 | Setup | Project skeleton: `src/`, `requirements.txt`, `config.py` với 22 classes, Colab + local MPS setup | 1 tuần |
| 2 | Stage 0 + 1A | Auto-overlay mask + team calibration + person detection + frame I/O | 1 tuần |
| 3 | Stage 1B | Tiered torso-sharpness + foreground filter + quota selection + frame export. Run extraction trên M01/M02/M06 | 1 tuần |
| 4 | Stage 2A + 2B | Manual annotate 50 keyframes. Build SAM 2 propagation script. Propagate to ~1500 frames | 1 tuần (human 1h) |
| 5 | Stage 2C + 2D | Train weak teacher, Soft Teacher pseudo-labeling, 3 vòng active learning | 1 tuần |
| 6 | Stage 3A | Build + train final YOLOv11m-OBB class-agnostic detector. Cross-match validation. Iterate. | 1 tuần |
| 7 | Stage 3B | Build DINOv2 embedding bank. Optional contrastive fine-tuning. Validate on 200 test crops. | 1 tuần |
| 8-9 | Stage 4 | Build inference engine: person detect + BoT-SORT + team classify + crop-and-detect + LogoTracker + temporal inference | 2 tuần |
| 10 | SAHI integration | Add SAHI tiled inference. Benchmark improvement. | 0.5 tuần |
| 10-11 | Stage 5 | Build 4-layer measurement engine + QI computation + reporter (CSV/JSON/matplotlib) | 1.5 tuần |
| 12 | Validation | End-to-end validation on 3× 5-min ground truth segments. Tune QI weights. | 1 tuần |
| 13 | Per-match reports | Generate reports for M01, M02, M06. User review. | 1 tuần |
| 14-16 | Iteration | Refine based on user feedback. Document handover. | 2-3 tuần |
| 17-18 | Optional | Diffusion synthetic data cho rare classes. Web dashboard MVP. | 2 tuần |

**Effort breakdown:**
- Compute time (Colab Pro A100): ~30-40 hours
- Human time (annotation): ~1.5-3 hours (vs v4 plan ~10h)
- Engineering time: 14-16 weeks 1 engineer (vs v4 12-14 weeks)

---

## 9. Open questions còn lại

### 9.1 Cần quyết định trước khi code Stage 1

1. **Primary detector:** YOLOv11m-OBB (an toàn, có precedent) hay test cả RT-DETRv2 song song? → đề xuất: YOLOv11m primary, RT-DETRv2 dual-test ở Stage 6 nếu YOLOv11m < target.
2. **DINOv2 size:** Base (~88M params, faster) hay Large (~300M, accurate)? → đề xuất: Base cho v1, upgrade Large nếu top-1 acc < 90%.
3. **Reference bank build:** Sử dụng full logo files in `/Sponsor Logo/` hay crop logo từ kit photos? → đề xuất: cả 2 (multiple references per brand cho robustness).

### 9.2 Validation methodology

4. **Ground truth segments:** 3× 5-min = 15 min total. User OK budget này hay muốn ít/nhiều hơn?
5. **Human annotator availability:** Ai sẽ annotate? Bạn? Team? Cần training annotators về OBB labeling guidelines.

### 9.3 Operational

6. **Compute environment:** Colab Pro+ (~$50/month) OK hay cần dedicated GPU server?
7. **Storage:** Google Drive (free 15GB) đủ hay cần upgrade?
8. **Report format:** PDF Standard hay HTML interactive? Phase 1 ai consume reports?

### 9.4 Strategic

9. **Multi-sport timeline:** v5 design future-proof, nhưng khi nào thực sự extend? Ảnh hưởng prioritization của embedding-based vs supervised approach.
10. **£-MAV (v2):** Khi nào thêm? Cần CPM benchmark Super League rugby — bạn có nguồn?

---

## 10. Tài liệu tham khảo

### Industry & academic
1. **ExposureEngine** — Yerlikaya et al., arXiv 2510.04739 (Oct 2025). Closest published analogue. https://arxiv.org/abs/2510.04739
2. **SAM 2** — Meta, arXiv 2408.00714. Video segmentation + memory propagation. https://arxiv.org/abs/2408.00714
3. **DINOv2** — Meta, arXiv 2304.07193. Self-supervised ViT features. https://arxiv.org/html/2304.07193v2
4. **SAHI** — arXiv 2202.06934. Tiled inference cho small objects. https://arxiv.org/abs/2202.06934
5. **RT-DETRv2** — arXiv 2407.17140. Real-time DETR baseline. https://arxiv.org/abs/2407.17140
6. **Soft Teacher** — ICCV 2021. Semi-supervised OD pseudo-labeling.
7. **STEP-DETR** — ICCV 2025. DETR-based SSOD. https://openaccess.thecvf.com/content/ICCV2025/papers/Shehzadi_STEP-DETR_Advancing_DETR-based_Semi-Supervised_Object_Detection_with_Super_Teacher_and_ICCV_2025_paper.pdf
8. **SOOD** — arXiv 2304.04515. Semi-supervised OBB detection.
9. **Plug and Play Active Learning** — CVPR 2024. https://arxiv.org/abs/2211.11612
10. **MPAD** — Multi-Perspective Data Augmentation, ICLR 2025. Diffusion-based synthetic data for FSOD. https://arxiv.org/html/2502.18195v1
11. **SoccerNet 2023 Tracking** — arXiv 2308.16651. Player tracking SOTA reference.
12. **BoT-SORT** — Aharon et al. https://github.com/NirAharon/BoT-SORT
13. **MRC Viewable Ad Impression Guidelines v2.0** — 50% pixels × 2 continuous seconds. https://mediaratingcouncil.org/sites/default/files/Standards/081815%20Viewable%20Ad%20Impression%20Guideline_v2.0_Final.pdf
14. **Nielsen Sports Media Valuation** — QI Score concept. https://nielsensports.com/media-valuation/
15. **OWLv2** — Open-vocabulary detection. https://www.ikomia.ai/blog/owlv2-open-vocabulary-object-detection
16. **Domain Randomization for OD Survey** — https://www.researchgate.net/publication/392987422_Domain_Randomization_for_Object_Detection_A_Survey

### Tools / libs
- **Ultralytics YOLO11/12** — https://docs.ultralytics.com
- **SAHI** — https://github.com/obss/sahi
- **SAM 2** — https://github.com/facebookresearch/sam2
- **supervision (sv)** — https://github.com/roboflow/supervision (BoT-SORT wrapper)
- **Roboflow** — annotation platform
- **albumentations** — augmentation library

---

## 11. Summary cho non-technical reader

**Vấn đề:** Bradford Bulls muốn biết mỗi sponsor logo trên áo cầu thủ xuất hiện bao nhiêu thời gian trên TV, với chất lượng visibility ra sao, để định giá lại các vị trí sponsor.

**Giải pháp v5:**
1. **Tự động lấy frames chất lượng** từ video trận đấu (Stage 1)
2. **Human chỉ annotate 50 frames**, sau đó AI tự label thêm 2000-3000 frames qua các kỹ thuật SOTA (Stage 2)
3. **2-stage detection:** trước phát hiện "có logo ở đâu" (model 1), rồi xác định "logo nào" (model 2 dùng embedding nearest-neighbor — cho phép thêm sponsor mới không cần retrain) (Stage 3)
4. **Theo dõi cầu thủ qua trận**: phát hiện mỗi cầu thủ → crop → detect logos → bind logo với cầu thủ. Tổng hợp exposure per logo per match (Stage 4)
5. **Báo cáo industry-grade**: 4 lớp đo (dedupe → smoothing → Quality Index → reporting) với metrics defensible cho sponsor (Stage 5)

**Khác v4 như thế nào:**
- Giảm manual annotation 6-7×
- Future-proof: thêm sponsor mới không cần retrain
- SOTA techniques 2024-2026 (SAM 2, DINOv2, Soft Teacher, SAHI, RT-DETRv2)
- Multi-sport extension chỉ cần config YAML

**Effort:** 14-18 tuần engineering, ~3 giờ human annotation total.

**Khi nào sẵn sàng:** Hết tuần 13 sẽ có per-match report đầu tiên.
