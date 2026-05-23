# Logo Exposure Measurement — Production System Design

> Phân tích sâu về việc xây dựng một production system đo lường logo/sponsor exposure
> trong video thể thao (rugby league), từ góc nhìn industry thực tế.
>
> Context: Bradford Bulls — bài toán đo sponsor exposure trên broadcast video.

---

## Mục lục

1. [Hiểu đúng "production system" là gì](#1-hiểu-đúng-production-system-là-gì)
2. [Cách các công ty thực sự làm](#2-cách-các-công-ty-thực-sự-làm)
3. [Tách bạch Training data vs Production inference](#3-tách-bạch-training-data-vs-production-inference)
4. [Architecture đầy đủ](#4-architecture-đầy-đủ-của-production-system)
5. [Edge cases production-grade](#5-edge-cases-production-grade)
6. [Critical design decisions](#6-critical-design-decisions)
7. [Differentiation strategy](#7-differentiation-strategy)
8. [Phased roadmap](#8-phased-roadmap-12-18-tháng)
9. [Honest assessment](#9-honest-assessment)
10. [Recommendation cuối](#10-recommendation-cuối)

---

## 1. Hiểu đúng "production system" là gì

Production ≠ "model + API". Đó là **4 components cân bằng**, và 90% engineer chỉ
tập trung vào #1, để bài toán chết ở #2–#4:

| Component | Vai trò | Khó ở đâu |
|---|---|---|
| **Detection** | ML pipeline detect sponsor | Đã quen, có sẵn tools |
| **Aggregation** | Convert detection → business metric | Logic phức tạp, đầy edge case |
| **Delivery** | Dashboard / API / Report | UX/UI thường bị underbuilt |
| **Operations** | Continuous improvement, monitoring | Cần MLOps, drift detection |

> **Cảnh báo:** Nếu chỉ build #1 (detection model), bạn sẽ có 1 prototype hay nhưng
> không bán được. GumGum/Nielsen có detection chỉ 80–90% accurate — họ thắng vì #2–#4.

---

## 2. Cách các công ty thực sự làm

Big players: **Nielsen Sports, GumGum Sports, Relo Metrics, Blinkfire, Hawk-Eye**.

**Quan niệm sai lầm phổ biến:** "Trích xuất frame chất lượng cao → annotate → train model".
Đây **không** phải cách họ làm.

**Cách họ thực sự làm:**

1. **Inference chạy trên TẤT CẢ frame** (hoặc 1–2fps), không phân biệt "tốt/xấu":
   - Frame "khó" (motion blur, wide shot) là **lúc sponsor xuất hiện nhiều nhất** (action moments)
   - Train chỉ trên frame đẹp → model fail trên production
   - Sampling bias giết generalization

2. **Multi-stage pipeline** thay vì 1 model end-to-end:
   ```
   Scene classifier (play/replay/crowd/interview) →
   Region detector (player/board/scoreboard) →
   Logo detector (within region) →
   Logo recognizer (which brand) →
   Tracker (link across frames) →
   Aggregator (duration × area × position)
   ```

3. **Annotation = REVIEW, không phải DRAW:**
   - Pretrained model + OCR đưa ra prediction
   - Human chỉ confirm/correct
   - Active learning: case khó nhất được ưu tiên cho human
   - Platforms: Roboflow, Labelbox, V7 Labs, Scale AI

4. **Dataset build dần dần:**
   - Bootstrap với pretrained model (FlickrLogos, OpenLogos)
   - Fine-tune từng season khi sponsor đổi
   - Sponsor mới chỉ cần vài chục ví dụ

---

## 3. Tách bạch Training data vs Production inference

Đây là điểm dễ lẫn lộn nhất:

| | Training data | Production inference |
|---|---|---|
| **Mục tiêu** | Diverse samples (cả khó lẫn dễ) | Đo exposure trên video thực |
| **Frame extraction** | Sampling đa dạng + human review | Mọi frame (1–2fps) |
| **Quality filter** | KHÔNG filter quá tay | KHÔNG filter |
| **Vai trò pipeline frame selection hiện tại** | Helpful nhưng KHÔNG sufficient | KHÔNG dùng |

> Pipeline frame selection (đang xây) có ích cho việc **tạo training data**, nhưng nếu chỉ
> train trên frame nét đẹp, model sẽ fail trên ~70% video thực tế (frame mờ, xa, action).
>
> **Production sẽ xử lý mọi frame**, kể cả mờ — model học cách bỏ qua frame mờ thông qua
> score thấp, không phải qua pre-filter.

---

## 4. Architecture đầy đủ của production system

```
[1. Ingestion]
    ↓ S3 trigger / RTMP capture / file watcher
    ↓ Video metadata extraction (match ID, teams, date, broadcast feed)

[2. Frame extraction]
    ↓ Sample at 1-2fps (uniform, NOT quality-filtered)
    ↓ Persist frames to object store (S3/MinIO)
    ↓ Frame metadata to PostgreSQL

[3. Scene segmentation]  ← thường bị bỏ qua
    ↓ Classify: PLAY / REPLAY / ADBREAK / CROWD / INTERVIEW / GRAPHICS
    ↓ Replays counted differently from live play
    ↓ Ad breaks excluded entirely

[4. Multi-detector ensemble]
    ↓ Person detector → torso ROI
    ↓ YOLO logo detector (symbols)
    ↓ OCR text detector
    ↓ Scoreboard/board detector (LED ads change every 30s)

[5. Recognition + Tracking]
    ↓ Fuzzy match → canonical sponsor ID
    ↓ ByteTrack/DeepSORT link detections across frames
    ↓ De-duplicate: same exposure event tracked across N frames

[6. Aggregation engine]
    ↓ Per-sponsor: total_seconds, avg_area_pct, peak_area, position
    ↓ Quality weighting: sharp frames score full, blurry frames discounted
    ↓ Industry metric: AVE (Ad Value Equivalent), MII (Media Impact Index)

[7. Delivery]
    ↓ Database: PostgreSQL + time-series for trends
    ↓ Dashboard: React + Plotly/D3
    ↓ API: REST/GraphQL for integrations
    ↓ Reports: PDF/Excel auto-generated per match

[8. Quality loop]
    ↓ Confidence scoring per detection
    ↓ Low-confidence cases → human review queue
    ↓ Corrections → training dataset → model retrain
    ↓ A/B test new models before deploy
```

---

## 5. Edge cases production-grade

Chỗ nhiều startup chết vì không lường:

1. **LED board cycling**: Board LED quanh sân đổi quảng cáo mỗi 30 giây. Phải track
   per-board, không phải per-frame.
2. **Replay frames**: Cùng moment được phát 3 lần (live + slow-mo + post-match analysis).
   Tính 1 exposure hay 3?
3. **Graphic overlays che sponsor**: Lower-third graphic, scoreboard mở rộng → tạm thời
   che sponsor. Cần detect overlay và pause tracking.
4. **Camera cuts**: Broadcast cắt giữa ~15 camera angles. Tracker phải re-identify sponsor
   sau cut.
5. **Kit changes giữa season**: Đổi away kit → model phải retrain hoặc dùng few-shot.
6. **New sponsor mid-season**: Sponsor mới ký giữa season → cần add vào dictionary +
   retrain trong 24h.
7. **Weather/lighting**: Trận tối khác trận ngày, áo bùn khác áo sạch.
8. **Broadcast quality variations**: BBC vs Sky vs streaming TV → bitrate, color grading khác.
9. **Multi-language OCR**: Trận quốc tế có sponsor ngôn ngữ khác.
10. **Ghost detection**: Sponsor xuất hiện 1 frame rồi mất → noise hay real?

---

## 6. Critical design decisions

### Decision 1: Batch vs Real-time
- **Batch** (process xong xuôi 1 trận): dễ build, cost thấp, latency 1–24h
- **Real-time** (during match): khó hơn ~5x, value cao hơn (live sponsorship intelligence)

> **Recommendation:** Bắt đầu batch, không quyết định real-time vội. GumGum mất ~5 năm
> để real-time hóa.

### Decision 2: Per-team vs Multi-tenant
- **Single-tenant** (chỉ Bradford): đơn giản, không scale
- **Multi-tenant** (mỗi team 1 instance): scale tốt nhưng phức tạp về data isolation,
  sponsor namespace

> **Recommendation:** Build single-tenant trước, **architect cho multi-tenant từ ngày 1**
> (schema, namespacing). Mỗi team = 1 `tenant_id`, sponsor dictionary per-tenant.

### Decision 3: Model deployment
- **Cloud GPU on-demand**: pay-per-use, dễ scale, ~$0.50–2/match
- **Owned hardware**: cheap nếu volume lớn, complex ops
- **Hybrid**: model serving cloud, training on-prem

> **Recommendation:** AWS/GCP với spot GPU + autoscaling. Mỗi trận 2h × 1fps = 7,200 frames
> × ~50ms inference = ~6 phút wall-clock trên T4 GPU = ~$1.

### Decision 4: Annotation strategy
- **In-house team**: control cao, cost cao (~$15–30/hour)
- **Outsourced (Scale AI, Surge)**: cheap (~$2–5/hour) nhưng quality issues
- **Roboflow Annotate**: hybrid, có quality control workflow
- **Active learning + crowdsourcing**: best long-term

> **Recommendation:** Active learning từ ngày 1. Mỗi tháng human review N case khó,
> feedback vào training.

### Decision 5: Data ownership
- **Bạn host video**: nặng storage cost (1 trận = 5–10GB)
- **Client upload, bạn process, xóa**: rẻ nhưng không train được trên historical
- **Index thay vì store**: chỉ lưu frame metadata + detection, không lưu video

> **Recommendation:** Lưu **detection embeddings + thumbnail**, không full video.
> Frame thumbnail 96×54px là đủ để debug.

---

## 7. Differentiation strategy

Detection logo là **commodity**. GumGum/Nielsen có ~99% accuracy với 10 năm data.
Đừng cố compete trên accuracy — bạn sẽ thua.

**Moat phải đến từ chỗ khác:**

1. **Vertical depth**: rugby league specifically. Hiểu rules, hiểu broadcast convention
   rugby (replay, sin bin, conversion), tính metric **rugby-specific** (kicking ground time,
   scrum side coverage).
2. **Integration depth**: tích hợp sâu với team's CRM, sales pipeline. Sponsor gói có ROI
   thực, có thể renew. Đây là JOB của data, không phải dashboard.
3. **Lower price point**: rugby league budget < football ~10x. Nếu giá bạn = GumGum, không
   ai mua. Phải build leaner, sell cheaper.
4. **Speed to insight**: real-time during match cho commentator/social media team là feature
   có giá thật.
5. **Open data flywheel**: published Bradford league dataset → community contributes →
   model improves → bạn còn lại là biz logic.

---

## 8. Phased roadmap (12–18 tháng)

**Tháng 1–3 — MVP:**
- Single match end-to-end
- OCR-first detection, fuzzy sponsor match
- CSV output: sponsor × duration × area
- Run trên 5–10 trận Bradford, validate accuracy

**Tháng 3–6 — Alpha:**
- YOLO cho symbol logos (Bull's head, crest)
- Tracking + de-duplication
- Web dashboard cơ bản
- Aggregation: AVE-style metric
- Bradford full season

**Tháng 6–9 — Beta:**
- Multi-tenant architecture
- Onboard 2–3 team rugby league khác
- API cho integration
- Active learning loop

**Tháng 9–12 — Production:**
- Real-time inference (during-match)
- Mobile-friendly dashboard
- Custom report builder
- PDF/Excel export

**Tháng 12–18 — Scale:**
- Expand vertical: NRL, Super League
- White-label option
- Marketplace plugins

---

## 9. Honest assessment

**Tin tốt:**
- Bài toán có market thật, không phải thị trường ảo
- Tech stack hiện tại (YOLO + OCR + cloud GPU) đủ chín
- Rugby league = niche, ít cạnh tranh hơn football
- Bradford = good design partner, có brand recognition

**Tin xấu:**
- Production system này là **3–5 năm work** cho team 2–3 người
- Detection model chỉ là ~20% effort
- Sales/customer success quan trọng hơn engineering
- Cash flow: pricing $20–50k/year/client × 10 clients = $200–500k ARR — không huge

**Câu hỏi quan trọng hơn:**
- Bạn có domain expert rugby trong team không? (cực kỳ quan trọng)
- Bạn có sales person không? (engineering tốt thôi không đủ)
- Founder bạn có funding cho 18 tháng runway không?

---

## 10. Recommendation cuối

Nếu serious build production system, **không khuyên bắt đầu bằng detection**. Khuyên:

1. **Tháng 1**: build script đơn giản (OCR + dictionary) chạy trên 5 trận Bradford.
   Output CSV. **Mang lên đứng trước Bradford sales team** — họ trả lời câu "có thông tin
   gì useful không?".

2. **Bước này quyết định tất cả.** Nếu họ không thấy value, build model tốt cũng vô nghĩa.
   Nếu họ thấy value → bạn biết feature gì cần build trước.

3. **Đừng build dashboard trước khi có 3 trận data và 1 stakeholder confirm value.**

---

## Phụ lục: Tech stack tham khảo

| Layer | Lựa chọn |
|---|---|
| Person/logo detection | Ultralytics YOLOv8/v11, SAHI (small object) |
| OCR | PaddleOCR (PP-OCRv5), EasyOCR |
| Fuzzy matching | rapidfuzz |
| Tracking | ByteTrack, BoT-SORT, DeepSORT |
| Scene classification | TimeSformer, VideoMAE, hoặc CNN nhẹ |
| Zero-shot logo | CLIP, GroundingDINO |
| Annotation | Roboflow, Labelbox, V7 |
| Experiment tracking | Weights & Biases, MLflow |
| Serving | Docker + FastAPI, Triton Inference Server |
| Orchestration | Kubernetes, hoặc serverless (AWS Batch) |
| Object storage | S3 / MinIO |
| Metadata DB | PostgreSQL (+ TimescaleDB cho time-series) |
| Dashboard | React + Plotly/D3 |
| GPU | AWS spot (T4/A10G), GCP preemptible |

---

*Tài liệu này là phân tích chiến lược, không phải spec kỹ thuật chi tiết. Mỗi mục
(architecture, aggregation logic, tracking) có thể đào sâu thành tài liệu riêng khi cần.*
