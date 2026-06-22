# Auto-Labeling & Kiến trúc Logo Detection linh hoạt đa môn thể thao

Tài liệu này mô tả giải pháp thay thế cho quy trình hiện tại
(`extract frame → annotate tay → train YOLO`) nhằm:

1. **Loại bỏ việc annotate thủ công hàng nghìn frame.**
2. **Linh hoạt đa môn thể thao** và **thêm nhà tài trợ mới mà không cần retrain.**

---

## 1. Vấn đề với quy trình hiện tại

| Điểm yếu | Hệ quả |
|----------|--------|
| Annotate tuyến tính | Mỗi môn thể thao mới = annotate lại từ đầu hàng nghìn frame |
| Closed-set (cố định lớp) | Model chỉ biết đúng các logo đã train; thêm logo mới = retrain toàn bộ |
| Phụ thuộc người gán nhãn | Tốn thời gian, dễ sai/không nhất quán, khó scale |

**Chiến lược:** tách bài toán thành 2 trục độc lập và giải riêng:

- **Trục A — Bỏ annotate tay:** sinh nhãn tự động (auto-label) + dữ liệu tổng hợp (synthetic).
- **Trục B — Linh hoạt:** tách *tìm vùng logo* khỏi *định danh thương hiệu* (kiến trúc 2 tầng / embedding).

---

## 2. Kiến trúc tổng thể: hệ thống 2 tầng

Thay vì một YOLO closed-set duy nhất, ta dùng **2 tầng tách biệt**:

```
                     ┌─────────────────────────────────────────────┐
   Video frame ─────▶│  TẦNG 1 — LOCALIZER (class-agnostic)         │
                     │  "Ở đây có MỘT logo" → bbox/mask, KHÔNG tên   │
                     └───────────────────────┬─────────────────────┘
                                             │ crop từng vùng logo
                                             ▼
                     ┌─────────────────────────────────────────────┐
                     │  TẦNG 2 — RECOGNIZER (embedding)             │
                     │  crop → vector → so với Template DB          │
                     │  → gán nhãn thương hiệu gần nhất             │
                     └─────────────────────────────────────────────┘
```

| Tầng | Nhiệm vụ | Công nghệ | Annotate cần |
|------|----------|-----------|--------------|
| **1. Localizer** | Tìm mọi vùng logo (không gán tên) | YOLO train từ **synthetic + auto-label** | ~0 (chỉ review) |
| **2. Recognizer** | Định danh thương hiệu | **Embedding** (CLIP/SigLIP/triplet) so với template DB | 1 ảnh/logo |

> **Vì sao tách 2 tầng?**
> - Việc *"có phải logo không"* mang tính chung, học một lần dùng cho mọi môn.
> - Việc *"logo của hãng nào"* thay đổi liên tục theo giải đấu/nhà tài trợ → đẩy về tra cứu vector, **không cần train lại**.

---

## 3. TẦNG 1 — Localizer (tìm vùng logo, class-agnostic)

### 3.1. Mục tiêu
Một detector chỉ trả lời **"đây là một logo"** (1 lớp duy nhất: `logo`), không quan tâm của hãng nào. Vì là class-agnostic nên nó **tổng quát giữa các môn thể thao** và là nền tảng ổn định nhất của hệ thống.

### 3.2. Lấy dữ liệu huấn luyện KHÔNG annotate tay

Kết hợp **2 nguồn dữ liệu**, cả hai đều cho nhãn tự động:

#### Nguồn (a) — Synthetic copy-paste (nhãn sạch 100%, zero annotate)

Nếu có file logo gốc (PNG/SVG nền trong suốt) của nhà tài trợ — thường có sẵn:

```
logo PNG  +  background thật (sân, áo đấu, biển quảng cáo)
        │
        ▼  domain randomization
   - scale ngẫu nhiên          - blur / motion blur
   - xoay + perspective warp   - đổi độ sáng / contrast
   - đổi màu nhẹ (color jitter)- che khuất một phần (occlusion)
   - nén JPEG / nhiễu video    - dán nhiều logo / chồng lấn
        │
        ▼
   Ảnh tổng hợp + bbox sinh tự động (vì ta tự dán → biết toạ độ chính xác)
```

- Vì **ta tự dán logo nên toạ độ box/mask sinh ra tự động, chính xác tuyệt đối, không cần vẽ tay.**
- Tham khảo: Su et al. sinh ~46K ảnh huấn luyện từ ~100 ảnh/logo theo cách này và cải thiện rõ độ chính xác.
- **Mục đích:** coverage rộng + nhãn sạch, đặc biệt cho logo hiếm gặp.

#### Nguồn (b) — Auto-label bằng foundation model (khớp domain thật)

Dùng model nền tảng zero-shot để **sinh pseudo-labels** trên frame thật, rồi distill xuống YOLO:

```
Frame thật
   │
   ▼  Grounding DINO   (prompt: "logo", "sponsor logo", "brand mark", "advertising board")
   box thô
   │
   ▼  SAM 2 / SAM 3    (tinh chỉnh thành mask/box khít viền logo)
   mask chính xác
   │
   ▼  lọc confidence + NMS + lọc theo kích thước/tỉ lệ
   │
   ▼  xuất YOLO format (.txt)
   │
   ▼  train YOLOv8 / v11 (Localizer)
```

- **Grounded-SAM** (IDEA-Research) là combo có sẵn cho đúng việc này: detect + segment + xuất nhãn tự động.
- Bạn chỉ còn **review/sửa** thay vì vẽ từ con số 0 → giảm **80–95%** công annotate.
- Các nghiên cứu 2025 (bird segmentation Grounding DINO 1.5 + SAM 2.1 → YOLOv11; pig farming SAM3 → YOLOv8) xác nhận pipeline distillation zero-shot này **đủ chất lượng cho production**.

> **Lưu ý quan trọng:** Grounding DINO giỏi tìm *"vùng có logo"* hơn là phân biệt *logo của hãng nào*.
> → Hoàn hảo cho **Tầng 1 (localization)**. Phần định danh thương hiệu để **Tầng 2** lo.

#### Công thức tốt nhất: TRỘN (a) + (b)

| Nguồn | Đóng góp |
|-------|----------|
| Synthetic (a) | Nhãn sạch, coverage rộng, logo hiếm, biến thể đa dạng |
| Auto-label (b) | Khớp domain thật: motion blur, ánh sáng sân vận động, nén video, góc quay |

### 3.3. Vòng lặp Active Learning
- Chạy Localizer → các frame **confidence thấp** đẩy cho người duyệt.
- Chỉ annotate **ca khó / biên** (edge cases), không phải hàng nghìn frame dễ.
- Bổ sung vào tập train → vòng sau tốt hơn. Công annotate giảm dần về gần 0.

### 3.4. Lựa chọn nâng cao
Có thể thay/ghép thêm **open-vocabulary detector** chạy trực tiếp:
- **YOLOE** (Tsinghua, 03/2025) — real-time, hỗ trợ cả **text prompt** và **visual prompt** (prompt bằng ảnh logo mẫu).
- **YOLO-World** — detect theo mô tả văn bản, gần như zero-shot.

---

## 4. TẦNG 2 — Recognizer (định danh thương hiệu bằng embedding)

### 4.1. Mục tiêu
Nhận crop logo từ Tầng 1 và trả lời **"logo này của hãng nào"** — nhưng theo cách **thêm hãng mới KHÔNG cần retrain.**

### 4.2. Cơ chế: embedding + template database

```
crop logo  ──▶  Encoder  ──▶  vector (vd. 512-d)
                                   │
                                   ▼  cosine similarity
                         ┌──────────────────────────┐
                         │   TEMPLATE DATABASE       │
                         │   Pepsi   → [vector]      │
                         │   Toyota  → [vector]      │
                         │   Nike    → [vector]      │
                         │   ...                     │
                         └──────────────────────────┘
                                   │
                                   ▼
                         Gán nhãn = template gần nhất
                         (nếu similarity < ngưỡng → "unknown")
```

### 4.3. Hai cách dựng Encoder

#### Cách 1 — Triplet loss (deepsense.ai, đã kiểm chứng cho tài trợ thể thao)
- Train encoder bằng bộ ba **(anchor, positive, negative)**:
  - *anchor*: logo hãng A
  - *positive*: vùng chứa logo hãng A (ảnh khác)
  - *negative*: vùng chứa logo hãng khác
- Mục tiêu: kéo gần anchor–positive, đẩy xa anchor–negative trong không gian vector.
- Kết quả: các crop cùng một thương hiệu nằm cụm gần nhau → so sánh template hoạt động.

#### Cách 2 — Foundation embedding (hiện đại, ít/không cần train)
- Dùng **CLIP / SigLIP** làm encoder sẵn → embed crop logo trực tiếp.
- Gần như **zero-shot**: chỉ cần 1 ảnh template/hãng là dùng được ngay.
- Có thể fine-tune nhẹ trên domain logo nếu cần độ chính xác cao hơn.

### 4.4. Tính linh hoạt — điểm mấu chốt

| Tình huống | Quy trình cũ (closed-set) | Kiến trúc 2 tầng |
|------------|---------------------------|------------------|
| Thêm nhà tài trợ mới | Annotate + **retrain toàn bộ** | **Thêm 1 vector vào DB** — xong ngay |
| Đổi sang môn thể thao khác | Annotate lại từ đầu | Tái dùng Tầng 1, **nạp bộ template mới** ở Tầng 2 |
| Logo bị gỡ khỏi giải | Retrain | Xoá/đổi vector trong DB |

> **Thêm logo mới = thêm/đổi 1 vector trong database, KHÔNG train lại model.**
> Đây chính là tính linh hoạt mà quy trình closed-set hiện tại không có.

---

## 5. Vòng đời dữ liệu end-to-end

```
┌─────────────┐   ┌──────────────┐   ┌──────────────┐   ┌──────────────┐
│ Logo PNG/SVG│   │ Frame thật   │   │ Active learn │   │ Template DB  │
│ (synthetic) │   │ (auto-label) │   │ (edge cases) │   │ (1 ảnh/hãng) │
└──────┬──────┘   └──────┬───────┘   └──────┬───────┘   └──────┬───────┘
       │ copy-paste      │ Grounded-SAM     │ review          │
       └────────┬────────┴──────────────────┘                 │
                ▼                                              │
        Tập train Localizer (Tầng 1)                           │
                ▼                                              │
        YOLO class-agnostic  ──────crop logo──────▶  Recognizer (Tầng 2)
                                                              ▲
                                                              │
                                              embedding so khớp template
```

---

## 6. Lợi ích trực tiếp

- **Annotate tay → gần 0**: chỉ còn review + xử lý edge cases.
- **Thêm nhà tài trợ mới**: drop 1 ảnh logo vào DB, dùng ngay, không retrain.
- **Môn thể thao mới**: tái dùng Tầng 1, chỉ nạp template Tầng 2.
- **Mở rộng tuyến tính thành gần-hằng số**: chi phí mỗi logo/môn mới giảm mạnh.

---

## 7. Bước triển khai đề xuất

1. **PoC Tầng 1 (auto-label):** dựng script Grounded-SAM trên một tập frame mẫu → xuất YOLO labels → train YOLO class-agnostic. Đo recall vùng logo.
2. **Synthetic generator:** script copy-paste logo PNG + domain randomization → sinh thêm data + nhãn sạch.
3. **Tầng 2 (embedding):** bắt đầu bằng CLIP/SigLIP zero-shot + template DB; nâng cấp lên triplet-loss encoder nếu cần độ chính xác cao hơn.
4. **Active learning loop:** đẩy frame low-confidence cho người duyệt; tự động nạp lại tập train.
5. **Tích hợp backend hiện tại** (`bradford_bulls_logo` env, `best.pt`): thay model closed-set bằng pipeline 2 tầng.

---

## 8. Synthetic data nâng cao — Thang giải pháp & Data Engine

Mục 3.2 (a) mới chỉ là **bậc thấp nhất** của synthetic data. Phần này mở rộng
thành một "thang" đầy đủ và một kiến trúc data engine phối hợp.

> Triển khai chi tiết từng bậc nằm ở file riêng:
> - **Bậc 3** → [`bac3_diffusion_inpainting.md`](./bac3_diffusion_inpainting.md)
> - **Bậc 4** → [`bac4_3d_simulation.md`](./bac4_3d_simulation.md)

### 8.1. Nguyên tắc VÀNG: Label Fidelity

> **Logo là "brand mark" — hình học phải đúng từng pixel. Mọi mô hình
> generative TỰ DO (text-to-image) đều BÓP MÉO logo.**

Nếu để Stable Diffusion / LLM ảnh tự "vẽ logo Pepsi", nó sinh ra thứ *na ná*
nhưng sai chữ, sai tỉ lệ, méo cong. Hệ quả:
- Tầng 1 vẫn học được "có vùng logo" (chấp nhận được).
- **Tầng 2 học SAI** — template thật ≠ embedding ảnh sinh → recognizer hỏng.
- Model tự tin nhận diện logo "ảo" không tồn tại.

**Nguyên tắc bắt buộc:** *Logo luôn được GHÉP từ asset thật (PNG/SVG/vector
gốc). Generative & 3D chỉ được sinh phần CONTEXT (vải, nếp gấp, ánh sáng, nền,
cơ thể) — KHÔNG được sinh ra chính cái logo.*

### 8.2. Thang giải pháp synthetic (rẻ→đắt, control→realism)

```
Bậc 4  ┌─ 3D SIMULATION (UV-map logo thật + cloth sim + pose)
       │      realism cao, nhãn HOÀN HẢO, control tuyệt đối, chi phí dựng cao
Bậc 3  ├─ DIFFUSION INPAINTING / HARMONIZATION (giữ logo thật, sinh context)
       │      ControlNet + IP-Adapter: hòa logo vào ảnh thật, photorealistic
Bậc 2  ├─ GENERATIVE BACKGROUND + paste logo thật
       │      diffusion sinh nền/cầu thủ, dán logo thật lên qua mask
Bậc 1  └─ COPY-PASTE 2D + domain randomization  (mục 3.2 a)
              rẻ nhất, kém realism nhất
```

Càng lên cao, **sim2real gap càng nhỏ** nhưng **chi phí kỹ thuật càng lớn**.
Không chọn một bậc — **trộn nhiều bậc** thành một data engine.

### 8.3. Nơi LLM/Diffusion & 3D thuộc về

| Ý tưởng | Bản chất | Phục vụ |
|---|---|---|
| LLM/diffusion sinh ảnh logo trên vải, cầu thủ nhiều tư thế | Synthetic **2D generative** (Bậc 3) | Tầng 1 (data) + Tầng 2 (đa dạng appearance cùng 1 logo → embedding khỏe) |
| Dựng 3D, gắn logo lên mesh, mô phỏng tư thế/noise/blur | Synthetic **3D simulation** (Bậc 4) | Tầng 1 (data + **nhãn hoàn hảo tự động**) + Tầng 2 |

Cả hai **không phải tầng mới** — chúng là **nguồn cấp dữ liệu** cho Tầng 1 & 2.

### 8.4. Thu hẹp Sim2Real gap

1. **Domain Randomization** — đa dạng đến mức ảnh thật chỉ là một biến thể.
2. **Domain Adaptation / fine-tune** trên ít frame thật **auto-label (Grounded-SAM)**.
3. **Real-in-the-loop** — trộn 70–90% synthetic + 10–30% real auto-labeled.
4. **Photorealism** — ưu tiên **Blender Cycles (PBR)** hơn game engine.

### 8.5. Kiến trúc "Data Engine" phối hợp (khuyến nghị cuối)

| Ưu tiên | Nguồn | Vai trò | Chi phí | Khi nào |
|---|---|---|---|---|
| 1️⃣ ngay | Auto-label Grounded-SAM trên video thật | Neo domain thật | Thấp | Tuần 1 |
| 2️⃣ ngay | Copy-paste 2D + DR (Bậc 1) | Coverage logo, nhãn sạch | Thấp | Tuần 1–2 |
| 3️⃣ kế | Diffusion inpainting (Bậc 3) | Realism + đa dạng cho Tầng 2 | Trung bình | Tháng 1 |
| 4️⃣ đầu tư | 3D simulation (Bậc 4) | Nhãn hoàn hảo, occlusion, pose, đa môn | Cao | Tháng 2+ |

Tất cả đổ vào **Tầng 1 (Localizer)** + **Tầng 2 (Recognizer)**; vòng **active
learning** lọc edge case từ video thật để vá liên tục.

---

## 9. Nguồn tham khảo

- [Voxel51 — Complete Guide to Auto-Labeling](https://voxel51.com/blog/the-complete-guide-to-auto-labeling)
- [Grounded-Segment-Anything (IDEA-Research)](https://github.com/idea-research/grounded-segment-anything)
- [Zero-Shot Bird Segmentation: Grounding DINO 1.5 + SAM 2.1 + YOLOv11](https://arxiv.org/html/2603.00184v1)
- [SAM3-Assisted Training of Lightweight YOLO Models](https://arxiv.org/html/2605.25860)
- [YOLOE Tutorial — Real-Time Open-Vocabulary Detection (LearnOpenCV)](https://learnopencv.com/yoloe-tutorial-real-time-open-vocabulary-detection/)
- [Grounding DINO on Videos (PyImageSearch)](https://pyimagesearch.com/2025/12/08/grounding-dino-open-vocabulary-object-detection-on-videos/)
- [deepsense.ai — Logo Detection in Sports Sponsorship (one-shot + triplet loss)](https://deepsense.ai/blog/logo-detection-in-sports-sponsorship/)
- [Su et al. — Deep Learning Logo Detection with Data Expansion by Synthesising Context](https://arxiv.org/pdf/1612.09322)
- [ExposureEngine — Oriented Logo Detection & Sponsor Visibility in Sports Broadcasts](https://arxiv.org/html/2510.04739)
- [SoccerSynth-Detection — Synthetic Dataset for Soccer Player Detection (Unreal)](https://arxiv.org/pdf/2501.09281)
- [Jersey Number Detection Using Synthetic Data in a Low-Data Regime](https://www.ncbi.nlm.nih.gov/pmc/articles/PMC9583843/)
- [Gen2Det — Generate to Detect (diffusion synthetic data)](https://arxiv.org/pdf/2312.04566)
- [Object-Centric Data Synthesis (Diffusion Copy-Paste, 2025)](https://arxiv.org/pdf/2511.23450)
- [ControlNet — Complete Guide](https://stable-diffusion-art.com/controlnet/)
- [Cloth2Tex — Customized Cloth Texture Generation for 3D Virtual Try-On](https://tomguluson92.github.io/projects/cloth2tex/static/document/cloth2tex.pdf)
- [CLOTH3D++ / 3D+Texture Garment Reconstruction](https://chalearnlap.cvc.uab.cat/dataset/38/description/)
- [Synthetic Data Generation for Bridging Sim2Real Gap in Production](https://arxiv.org/html/2311.11039v2)
- [Synthetic Data from Unreal Game Engine for Object Detection](https://www.mdpi.com/2076-3417/12/17/8534)
