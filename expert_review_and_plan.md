# Đánh giá chuyên gia & Kế hoạch triển khai — Annotation-Free Logo Detection

> Tài liệu hợp nhất: (0) **lưu lại toàn bộ phân tích** đã thảo luận, (1) **đánh giá
> của chuyên gia CV/logo-detection** đối chiếu SOTA 2026, (2) **kế hoạch triển khai**
> theo phase, (3) **kế hoạch test & evaluation**.
>
> Bối cảnh: nhánh `feat/sam3-autolabel-eval`. Liên quan: [`autolabel.md`](./autolabel.md),
> [`bac3_diffusion_inpainting.md`](./bac3_diffusion_inpainting.md),
> [`bac4_3d_simulation.md`](./bac4_3d_simulation.md),
> [`frontier_solutions.md`](./frontier_solutions.md),
> [`Motion-blur.MD`](./Motion-blur.MD),
> [`Production-System-Design.MD`](./Production-System-Design.MD).
>
> *Soạn: 2026-06.*

---

## PHẦN 0 — Nhật ký phân tích (lưu lại toàn bộ, theo yêu cầu)

### 0.1. Vòng 1 — Vấn đề cốt lõi & kiến trúc decoupled

**Chẩn đoán:** quy trình hiện tại (annotate trên RoboFlow → fine-tune YOLO26/RF-DETR
cho từng club) **không scale** vì nó *couple* hai việc vào một model: vừa "logo ở
đâu" vừa "logo của club nào". Danh tính club bị nướng cứng vào trọng số → club mới =
class mới = annotate lại + train lại.

**Giải pháp (đã trùng khớp với `autolabel.md` hiện có):** tách 2 tầng.
- **Tầng 1 — Localizer (class-agnostic):** "có một logo, ở đây" — train một lần, dùng
  cho mọi club/môn.
- **Tầng 2 — Recognizer (retrieval):** crop → embedding → so khớp Template DB → gán
  brand. Thêm club/logo mới = **thêm vector vào DB, zero retraining**.

Input của khách (logo images, kit jersey, video trận) map thẳng vào: logo → template +
visual prompt; kit → synthetic data + reference crop; video → auto-label + embedding
thực chiến.

### 0.2. Vòng 2 — Critique tài liệu Motion-blur (Tier 3/4)

- **Câu hỏi chiến lược:** không hệ thương mại nào (Nielsen, GumGum, ExposureEngine)
  deblur ở mức pixel. Họ dùng **temporal smoothing mức track + image-clarity weighting**.
  Deblur là *means*, mục tiêu là *đo exposure*.
- **Tier 3 (RAFT + temporal fusion):** chicken-and-egg (flow kém nhất đúng trên frame
  mờ → ghost); ghost = độc với logo detection (cạnh giả); tối ưu PSNR ≠ tối ưu mAP/EMV.
  → Chuyển sang **BSSTNet** (bản học được của chính Tier 3); nếu giữ RAFT thì chỉ chạy
  local ROI; **validate bằng mAP/EMV, không PSNR**.
- **Tier 4 (frame interpolation):** lỗi khái niệm — interpolation **không** giảm blur
  của frame đã quay (chỉ giảm judder). Giá trị thật: trợ giúp **tracker** + slow-mo
  presentation. **Không đếm frame nội suy như exposure thật.**
- **Mâu thuẫn với Production-System-Design:** đừng train trên frame đã deblur → tạo
  train/serve mismatch. Hướng đúng: **blur-robust detection bằng synthetic blur
  augmentation** (ID-Blau, ReLoBlur, SoccerSynth), không phải deblur lúc inference.
- **Giữ:** Tier 1 (lucky imaging, rẻ, không artifact). **Dùng chọn lọc:** Tier 2
  (NAFNet) chỉ cho keyframe OCR. **Hạ ưu tiên:** Tier 3/4.

### 0.3. Vòng 3 — Critique thang synthetic (Bậc 3/4)

Nguyên tắc VÀNG (logo luôn ghép từ asset thật, generative chỉ sinh context) là **đúng**.

- **Bậc 3 (diffusion inpainting) — khả thi CAO, nhưng 3 lỗ hổng:**
  1. **Mâu thuẫn `composite_back` ⊥ giá trị Tầng 2:** dán logo phẳng gốc trở lại →
     vứt bỏ đúng biến thể (cong/mờ/ướt) mà Bậc 3 hứa cho Recognizer. → **Tách luồng:**
     Tầng 1 dùng composite_back; **Tầng 2 KHÔNG composite_back**, giữ biến thể và
     **gate bằng embedding-distance QC**.
  2. **Seam ở biên mask** → detector học shortcut "logo = discontinuity sắc nét". →
     feather/Poisson-blend hoặc img2img strength 0.1–0.15 trên vành quanh logo.
  3. **SDXL cho "đẹp artstation", không "giống broadcast".** → IP-Adapter reference từ
     frame broadcast thật + degrade hậu kỳ (H.264 recompress, broadcast LUT).
- **Bậc 4 (3D simulation) — khả thi TRUNG BÌNH, R&D bet:**
  - Justification *sống sót*: **nhãn occlusion-aware + % visibility** (auto-label video
    thật không bao giờ có) — mà visibility% chính là input EMV.
  - Rủi ro bị đánh giá thấp: effort thực là **nhiều tháng** (không phải 1–2 tuần); gap
    **mocap rugby** (AMASS thiếu scrum/tackle); **cloth sim giòn** (vải xuyên body);
    **ngưỡng sim2real cho Tầng 2 cao hơn** precedent SoccerSynth (detect người ≫ dễ hơn
    nhận dạng logo).
  - **Giải pháp:** đường **lai 3DGS** — reconstruct sân thật bằng Gaussian Splatting →
    gap sim2real của nền ≈ 0, chỉ composite cầu thủ 3D (UV-map logo thật).
- **Cảnh báo over-engineering:** nhánh đã có Bậc 1–4 + frontier (SAM3, label-model,
  3DGS twin, logo fingerprint, render-verify, teacher-student). Quá nhiều bề mặt cho
  team nhỏ. Chốt đường tối thiểu → ship → để gap đo được kéo Bậc 3/4 vào.

---

## PHẦN 1 — Đánh giá chuyên gia đối chiếu SOTA 2026

> Góc nhìn: kỹ sư đã triển khai hệ thống logo/brand detection quy mô lớn.

### 1.1. Phán quyết tổng thể

**Kiến trúc 2 tầng của bạn ĐÚNG và khớp hướng hội tụ của SOTA 2026.** Decoupling
"localize class-agnostic" + "recognize bằng retrieval" chính là cách industry/research
đang làm. Rủi ro lớn nhất **không phải kiến trúc** mà là **phạm vi quá rộng + thiếu
thước đo**. Khuyến nghị xuyên suốt: **đo trước, xây sau** (eval-driven), và **nâng cấp
công cụ lên SOTA mới** thay vì tự dựng lại.

### 1.2. Bảng nâng cấp công cụ theo SOTA

| Thành phần | Thiết kế hiện tại | SOTA 2026 nên dùng | Lý do |
|---|---|---|---|
| **Auto-label Tầng 1** | Grounding DINO + SAM 2 | **SAM 3** (text + **exemplar** prompt, + video tracking native) | Một model làm cả detect+segment+**track**; prompt bằng *chính ảnh logo*. Ra 11/2025, SAM 3.1 03/2026, **gấp đôi accuracy** hệ cũ. Nhánh đã có `sam3_exemplar_autolabel.py`. |
| **Distill → production** | YOLOv8/v11 | **YOLOv11-OBB** (oriented) | SAM3→YOLOv8m đạt **mAP 79.4% zero human-label, nhanh 200×** (arXiv 2605.25860). **OBB** vì HBB thổi phồng visibility% (ExposureEngine). |
| **Open-vocab realtime (tùy chọn)** | YOLOE / YOLO-World | **YOLOE** | ICCV 2025; vượt T-Rex2 **+3.3 APr** với **6.3× ít params**; hỗ trợ visual prompt (ảnh logo). |
| **Visual-prompt accuracy cao nhất** | — | **DINO-X** (API) | LVIS 59.8 AP; **rare-class 63.3** (>Grounding DINO 1.6 Pro +5.8). Dùng làm teacher chất lượng cao khi cần. |
| **Encoder Tầng 2** | CLIP/SigLIP | **DINOv3** (hoặc DINOv2) | Fine-grained: DINOv2 **70%** vs CLIP **15%** (10k lớp). Logo là fine-grained → DINO > CLIP. SigLIP2 mạnh hơn ở text-image retrieval (dùng khi fuse text). |
| **Vector DB** | (chưa chốt) | **Qdrant / FAISS (HNSW)** | Chuẩn công nghiệp; thêm brand = upsert vector. |
| **Đo exposure** | exposure.py (Tier 2/3) | **OBB + temporal smoothing mức track + clarity-weight** | Đúng cách ExposureEngine/Nielsen; mAP@0.5 0.859, P 0.96, R 0.87. |
| **Synthetic Bậc 3** | SDXL inpaint + ControlNet | OK, + xét **Object-Centric Data Synthesis (Diffusion Copy-Paste, 2025)** | Lift diffusion thường **nhỏ** (Gen2Det: low-data +2.27 box AP; general +0.45). Validate trước. |
| **Synthetic Bậc 4** | Blender authoring | **3DGS-hybrid** (FastGS train 100s) | Nền thật từ GS → sim2real nền ≈ 0. |

### 1.3. Ba điều SOTA làm thay đổi ưu tiên của bạn

1. **SAM 3 hợp nhất pipeline auto-label.** Trước cần Grounding DINO (detect) → SAM 2
   (mask) → ByteTrack (track) là 3 mảnh. Nay **SAM 3** làm cả ba với **exemplar = ảnh
   logo**, và **track xuyên frame native**. Đây là **đòn bẩy lớn nhất** và bạn đã bắt
   đầu đúng (file `sam3_exemplar_autolabel.py`).

2. **Temporal self-training giờ gần như miễn phí.** Vì SAM 3 track trong video: exemplar
   1 logo → propagate mask toàn shot → **dữ liệu train đúng domain, sim2real = 0**. Đây
   nên là **ưu tiên #1**, *trên cả* synthetic (frontier §5). Synthetic chỉ lấp phần
   đuôi (logo hiếm, occlusion, club mới khi *chưa* có video).

3. **OBB không phải HBB.** Vì sản phẩm cuối là **visibility% → EMV**, axis-aligned box
   thổi phồng diện tích logo nghiêng/cong. ExposureEngine chứng minh OBB là điều kiện
   cần cho con số đo chính xác. Localizer nên xuất **oriented box ngay từ đầu**.

### 1.4. Đánh giá tính khả thi (tóm tắt)

| Hạng mục | Khả thi | Đề xuất |
|---|---|---|
| Kiến trúc 2 tầng | ✅ Cao | Giữ nguyên, nâng công cụ lên SAM 3 / DINOv3 / OBB |
| Auto-label (SAM 3) | ✅ Cao | Ưu tiên #1; teacher SAM 3 → student YOLOv11-OBB |
| Temporal self-training | ✅ Cao | Ưu tiên #1 (cùng auto-label) |
| Tầng 2 retrieval (DINOv3) | ✅ Cao | Zero-shot + few templates; fuse OCR ("logo fingerprint") |
| Bậc 1 copy-paste | ✅ Cao | Coverage logo hiếm; rẻ |
| Bậc 3 diffusion | 🟡 Trung bình | Chỉ cho Tầng 2 (bỏ composite_back, embedding-gate); validate lift |
| Bậc 4 3D | 🟠 R&D | Chỉ cho visibility%/occlusion GT; đường 3DGS-hybrid; track song song |
| Deblur Tier 3/4 | 🔴 Hạ ưu tiên | Thay bằng blur-robust augmentation + temporal smoothing |

---

## PHẦN 2 — Kế hoạch triển khai (theo phase, có cổng go/no-go)

> Nguyên tắc: **mỗi phase phải vượt cổng eval trên gold set mới đi tiếp.** Không xây
> phase sau trên niềm tin.

### Phase 0 — Thước đo trước tiên (Tuần 1–2) ⭐ bắt buộc

- **Gold test set:** annotate tay **một lần** ~300–500 frame Bradford thật, **OBB +
  brand**, phân tầng theo điều kiện: sharp / motion-blur / occlusion / replay / wide-shot
  / lighting. Đây là thước đo duy nhất, không dùng để train.
- **Mở rộng `eval_map.py`:** OBB mAP@0.5/0.75; per-brand top-1; open-set AUROC (từ chối
  unknown); **exposure-seconds MAE** & **visibility% MAE** vs ground truth.
- **Baseline:** chạy model YOLO26 fine-tuned hiện tại trên gold set → có số để so.

**Cổng:** harness chạy được, có baseline number.

### Phase 1 — Tầng 1 v1 (Tuần 2–4)

- **SAM 3 auto-label** (exemplar = ảnh logo + text "sponsor logo / advertising board")
  trên video Bradford → pseudo-label OBB.
- **+ Bậc 1 copy-paste** cho coverage logo hiếm + blur augmentation (ID-Blau-style).
- **Distill → YOLOv11-OBB** (class-agnostic `logo`).
- Trộn real auto-label : synthetic ≈ **70:30**.

**Cổng:** localizer OBB mAP@0.5 ≥ baseline; recall trên tầng "blur" ≥ ngưỡng đặt ra.

### Phase 2 — Tầng 2 v1 (Tuần 4–6)

- **Template DB:** embed logo PNG/SVG + crop từ kit jersey bằng **DINOv3** → **Qdrant**.
- **Open-set threshold** (cosine < τ → "unknown"; an toàn doanh thu: thiếu bằng chứng
  thì không gán nhầm).
- **Tùy chọn "logo fingerprint":** fuse DINOv3 (visual) ⊕ OCR wordmark ⊕ tỉ lệ hình học.
- Nuôi Tầng 2 bằng biến thể Bậc 3 (KHÔNG composite_back, embedding-gate).

**Cổng:** brand top-1 acc + unknown-rejection AUROC trên gold set ≥ ngưỡng.

### Phase 3 — Self-training + Aggregation (Tuần 6–8)

- **Temporal self-training:** SAM 3 track → propagate → mine frame confidence thấp →
  human review **chỉ edge case** → retrain (active learning loop).
- **Aggregation:** ByteTrack/BoT-SORT link detection + **temporal smoothing** + de-dup
  + **clarity-weight** → exposure-seconds, visibility%, EMV.

**Cổng:** exposure-seconds MAE ≤ X% so với ground truth thủ công trên trận held-out.

### Phase 4 — Bậc 3 diffusion (Tháng 2–3, *có điều kiện*)

- Chỉ làm nếu Phase 1–3 còn gap mà copy-paste không lấp được.
- Theo skeleton đã tách luồng Tầng 1/Tầng 2. **Đo lift** trên gold set; giữ nếu
  ≥ +1–2 mAP / +Δ recognition, bỏ nếu không.

### Phase 5 — Bậc 4 / 3DGS-hybrid (Tháng 3+, track R&D song song)

- Mục tiêu hẹp: **visibility%/occlusion GT** + onboard môn mới biên ≈ 0.
- Bắt đầu bằng 3DGS reconstruct 1 sân + 1 cầu thủ UV-map; đo sim2real trên gold set.
- **Không block sản phẩm.**

### Onboarding test (KPI scale — xuyên suốt)

Lấy **một club mới / một môn khác**, chỉ cung cấp **logo + kit** (không video, hoặc ít
video). Đo **time-to-first-result** và accuracy khi **chỉ nạp template Tầng 2** (Tầng 1
giữ nguyên). Đây là KPI thật cho mục tiêu "đa club/đa môn".

---

## PHẦN 3 — Kế hoạch Test & Evaluation

### 3.1. Unit / fidelity

- **Label fidelity synthetic:** sau `composite_back`, logo-IoU với bbox ghi = 1.0;
  embedding(crop sinh) vs embedding(logo gốc) cosine > τ. Lệch → loại (Bậc 3 §6).
- **QC filters:** kiểm Bậc 4 mask khớp material logo; loại frame "vải xuyên body".

### 3.2. Component

- **Tầng 1:** OBB mAP@0.5/0.75; **per-stratum recall** (sharp/blur/occlusion/replay).
- **Tầng 2:** top-1 brand acc; open-set AUROC; confusion giữa logo *giống nhau*
  (cùng nhà tài trợ trên 2 đội — bài toán team-filter cũ).
- **Ablation synthetic mix:** real-only vs +30% vs +50% vs +70% synthetic → xác định tỉ
  lệ tối ưu; ablation Bậc 1 vs Bậc 1+3.

### 3.3. System (end-to-end)

- **Exposure-seconds MAE** & **visibility% MAE** vs ground truth thủ công, trên ≥ 3 trận
  held-out.
- So **2-tier mới vs YOLO26 fine-tuned cũ** trên cùng gold set → định lượng đánh đổi
  (chấp nhận giảm nhẹ accuracy để đổi lấy scalability).

### 3.4. Generalization (cốt lõi — đo đúng lời hứa scale)

- **Leave-one-club-out:** train Tầng 1 trên Bradford, test localization trên **club
  khác** *không retrain*; chỉ swap template Tầng 2. Báo cáo sụt giảm mAP/acc.
- **Leave-one-sport-out:** tương tự với **môn khác** (rổ/chuyền) nếu có clip.
- **Cold-start brand:** thêm 1 brand chỉ bằng 1 ảnh logo → đo recognition ngay.

### 3.5. Robustness & vận hành

- Stratified report theo blur/occlusion/replay/lighting/broadcast-source.
- **Blur-robustness:** so model train có/không synthetic-blur augmentation trên tầng
  "blur" (kỳ vọng augmentation > deblur-at-inference).
- **A/B test** model mới trước khi deploy (Production-System-Design §4 quality loop).
- **Drift monitoring:** theo dõi tỉ lệ "unknown" tăng bất thường (sponsor mới/đổi kit).

### 3.6. Bảng metric mục tiêu (điền ngưỡng khi có baseline)

| Tầng | Metric | Mục tiêu |
|---|---|---|
| Tầng 1 | OBB mAP@0.5 | ≥ baseline YOLO26 |
| Tầng 1 | Recall @ blur stratum | ≥ ____ |
| Tầng 2 | Brand top-1 | ≥ ____ |
| Tầng 2 | Unknown-rejection AUROC | ≥ ____ |
| System | Exposure-sec MAE | ≤ ____ % |
| System | Visibility% MAE | ≤ ____ |
| Scale | Leave-one-club mAP drop | ≤ ____ |
| Scale | Time-to-first-result (club mới) | ≤ ____ |

---

## Nguồn tham khảo (SOTA 2026)

- [SAM 3: Segment Anything with Concepts — arXiv 2511.16719](https://arxiv.org/abs/2511.16719) · [Meta blog (SAM 3 / 3.1)](https://ai.meta.com/blog/segment-anything-model-3/) · [facebookresearch/sam3](https://github.com/facebookresearch/sam3)
- [SAM3-Assisted Training of Lightweight YOLO — arXiv 2605.25860](https://arxiv.org/abs/2605.25860)
- [DINO-X: Unified Open-World Detection — arXiv 2411.14347](https://arxiv.org/pdf/2411.14347)
- [YOLOE: Real-Time Seeing Anything — ICCV 2025, arXiv 2503.07465](https://arxiv.org/pdf/2503.07465)
- [DINOv3 — arXiv 2508.10104](https://arxiv.org/abs/2508.10104) · [Meta research](https://ai.meta.com/research/dinov3/)
- [SigLIP 2 — arXiv 2502.14786](https://arxiv.org/html/2502.14786v1) · [SigLIP 2 vs DINOv2 (Underfitted)](https://underfitted.dev/2026/03/01/siglip-2-vs-dinov2-battle-of-the-embeddings-titans/)
- [Gen2Det: Generate to Detect — arXiv 2312.04566](https://arxiv.org/abs/2312.04566)
- [Object-Centric Data Synthesis (Diffusion Copy-Paste, 2025) — arXiv 2511.23450](https://arxiv.org/pdf/2511.23450)
- [ExposureEngine: Oriented Logo Detection & Sponsor Visibility — arXiv 2510.04739](https://arxiv.org/html/2510.04739v1)
- [FastGS: 3D Gaussian Splatting in 100 Seconds — CVPR 2026](https://github.com/fastgs/FastGS)
- [SoccerSynth-Detection — arXiv 2501.09281](https://arxiv.org/pdf/2501.09281)
