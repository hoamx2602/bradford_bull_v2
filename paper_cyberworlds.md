# Paper Ideation — CyberWorlds (IEEE International Conference on Cyberworlds)

> Đề cương viết dưới góc nhìn một giáo sư đã publish: định vị bài toán, đóng góp
> khoa học, thiết kế thực nghiệm để **đạt độ chính xác cao + thuyết phục reviewer**.
> Gắn với hệ thống mô tả ở [`autolabel.md`](./autolabel.md),
> [`frontier_solutions.md`](./frontier_solutions.md) và PoC [`auto_label/`](./auto_label/).

---

## 1. Vì sao hợp CyberWorlds (định vị venue)

CyberWorlds đề cao **digital twins, cyber-physical systems, AI/computer vision,
multimedia, visual analytics, virtual worlds**. Bài toán của bạn chạm trúng nếu
khung hoá đúng:

- **Digital twin** sân vận động bằng 3D Gaussian Splatting → đúng trung tâm chủ đề.
- **Cyber-physical / virtual-real loop**: synthetic ↔ real flywheel.
- **Visual analytics**: phân tích sponsor exposure/visibility từ broadcast.

> Mẹo định vị: đừng bán đây là "thêm một logo detector". Bán là **"một khung
> dữ liệu cyber-physical tự cải thiện (self-improving data engine) nối thế giới
> ảo (synthetic/digital-twin) với broadcast thật để phân tích tài trợ thể thao"**.
> Đó là câu chuyện CyberWorlds muốn nghe.

---

## 2. Tên bài (ứng viên)

1. **"A Self-Improving Cyber-Physical Data Engine for Annotation-Free Sponsor
   Logo Analytics in Sports Broadcasts."**
2. "Exemplar-to-Video: Foundation-Model Auto-Labeling and Gaussian-Splatting
   Digital Twins for Open-Set Logo Detection in Sports."
3. "From One Exemplar to a Trained Detector: A Roster-Prior Teacher–Student
   Flywheel for Sponsor Visibility Estimation."

> #1 nhấn "cyber-physical data engine" (hợp venue); #2 nhấn kỹ thuật; #3 nhấn pipeline.

---

## 3. Abstract (bản nháp, ~180 từ)

> Sponsor logo analytics in sports broadcasts traditionally requires annotating
> thousands of frames per event and re-training a closed-set detector whenever a
> new sponsor or sport is introduced — costly and inflexible. We present a
> *self-improving cyber-physical data engine* that produces a deployable logo
> detector **without manual frame annotation**. Our key insight is to exploit
> three free signals: (i) brand logo assets already exist; (ii) the sponsor
> *roster* of a given match is known a-priori, turning an open-world problem into
> a closed-set-per-event prior; and (iii) videos are temporally redundant. We
> couple a Promptable Concept Segmentation foundation model (exemplar-prompted)
> with a weak-supervision label model and temporal track refinement to auto-label
> entire broadcasts from a single exemplar per brand, then distill a real-time
> student detector. To close the sim-to-real gap and cover rare conditions, we
> build a *Gaussian-Splatting digital twin* of the venue and insert real logos
> with lighting-aware compositing. Identity is resolved by a multimodal "logo
> fingerprint" (visual + scene-text + color), making the gallery expandable with
> zero training. Experiments on rugby-league broadcasts show [X] mAP with [Y]%
> less manual labeling and seamless addition of new sponsors/sports.

*(điền X/Y sau khi có số.)*

---

## 4. Đóng góp khoa học (claims — phải đo được)

C1. **Roster-prior closed-set-per-event formulation**: hình thức hoá việc dùng
    danh sách tài trợ làm prior, biến open-set logo detection thành bài toán dễ
    hơn nhiều; chứng minh tăng precision Δ so với không dùng prior.

C2. **Exemplar-to-Video auto-labeling**: pipeline gán nhãn cả broadcast từ 1
    exemplar/brand, đạt chất lượng đủ train student ≈ supervised, với chi phí
    annotate ↓ ~95%.

C3. **Weak-supervision label model + temporal track-refine** cho logo: hợp nhất
    nhiều labeler nhiễu (PCS, OCR, template, track) → nhãn sạch; đo lợi ích từng
    thành phần (ablation).

C4. **Gaussian-Splatting venue digital twin** như data generator cho sponsor
    analytics: lighting-aware logo insertion thu hẹp sim2real; đo Δ accuracy khi
    thêm dữ liệu twin so với synthetic thuần / không synthetic.

C5. **Multimodal Logo Fingerprint (visual ⊕ text ⊕ color)** mở rộng gallery open-set
    zero-training; đo accuracy nhận diện + khả năng thêm brand "unseen".

C6. **Self-improving flywheel** (teacher→student per-event): chứng minh hệ mạnh
    dần qua nhiều trận (accuracy tăng theo số sự kiện đã xử lý).

> Một paper CyberWorlds ~8 trang nên **chốt 3–4 claim mạnh** (gợi ý: C1, C2, C4, C5)
> và để phần còn lại là "system + ablation", tránh dàn trải.

---

## 5. Kiến trúc hệ thống (hình chủ đạo — Figure 1)

```
   Sponsor roster + logo assets ──► ROSTER PRIOR (closed-set/event)
                │                          │
   Broadcast ───┤                          ▼
                │     TEACHER (offline): SAM3 exemplar PCS  ┐
                │                          OCR scene-text   ├─► LABEL MODEL ─► nhãn sạch
                │                          template match   ┘        │
                │                          temporal track-refine ◄────┘
                ▼                                                    │
   GS DIGITAL TWIN (venue) ──► lighting-aware logo insertion ──► synthetic + labels
                │                                                    │
                └──────────────► trộn real+synthetic ────────────────┤
                                                                     ▼
                                        STUDENT realtime (YOLO distilled)
                                                     │
                                LOGO FINGERPRINT gallery (Tầng 2, open-set)
                                                     │
                                  Sponsor exposure / visibility analytics
```

---

## 6. Định vị so với related work (để reviewer thấy "mới")

| Hướng cũ | Hạn chế | Ta khác chỗ nào |
|---|---|---|
| Closed-set logo detector (YOLO fine-tune) | Annotate nặng; thêm brand = retrain | Annotation-free; gallery zero-training |
| Open-set logo retrieval (SeeTek, OSLD) | Cần detector + gallery riêng; không khai thác video/roster | Roster prior + temporal + fingerprint hợp nhất |
| Synthetic-data logo (copy-paste, GAN) | Sim2real gap; nền giả | GS **digital twin của chính venue** |
| FM auto-label (Grounded-SAM) | Nhãn nhiễu, không định danh brand | Label model + exemplar PCS + OCR |
| Sponsor visibility (ExposureEngine…) | Supervised, một môn | Self-improving, đa môn/đa sự kiện |

---

## 7. Thiết kế thực nghiệm (phần quyết định accept/reject)

### 7.1. Dữ liệu
- **Real**: broadcast rugby-league (M02…), nhiều trận/điều kiện ánh sáng. Một
  **test set vàng có annotate tay** (chỉ để *đánh giá*, không train) — bắt buộc để
  số liệu đáng tin.
- **Synthetic**: GS digital twin của ≥1 venh + logo insertion.
- **Open-set split**: giữ lại vài brand "unseen" để test khả năng thêm zero-training.

### 7.2. Baselines (so sánh công bằng)
1. Closed-set YOLO train trên N frame annotate tay (đường nền supervised, *upper-cost*).
2. Grounded-SAM auto-label (FM thuần, không roster/label-model).
3. Template matching / open-set retrieval thuần.
4. **Ours** (full) + các biến thể ablation.

### 7.3. Metrics
- Detection: **mAP@0.5, mAP@0.5:0.95**, precision/recall per-brand.
- Open-set: accuracy trên brand unseen; FPR trên "non-sponsor".
- **Annotation efficiency**: mAP vs số nhãn tay (đường cong) — *điểm bán hàng chính*.
- Analytics-level: sai số **exposure time / visibility %** so ground truth
  (gắn với `LOGOS_Exposure_Pricing_Algorithm.md`) — rất thuyết phục cho ứng dụng.
- Realtime: FPS của student.

### 7.4. Ablations (chứng minh từng claim)
- − roster prior (C1) · − label model (chỉ PCS) (C3) · − temporal refine (C3) ·
  − GS twin / − synthetic (C4) · fingerprint: visual-only vs +text vs +color (C5) ·
  flywheel: accuracy theo số trận đã xử lý 1→K (C6).

### 7.5. Bảng kết quả (khung điền)
| Method | Manual labels | mAP@.5 | mAP@.5:.95 | Open-set acc | Exposure err | FPS |
|---|---|---|---|---|---|---|
| Supervised YOLO | thousands | – | – | n/a | – | – |
| Grounded-SAM auto | 0 | – | – | – | – | – |
| **Ours (full)** | **~0** | – | – | – | – | – |

---

## 8. Cấu trúc bài (IEEE 2 cột, ~8 trang)

1. **Introduction** (1 tr): pain → 3 free signals → contributions (C1–C5).
2. **Related Work** (0.75 tr): logo detection, open-set/retrieval, FM auto-label,
   synthetic/GS, sports analytics.
3. **Method** (2.5–3 tr): roster prior · exemplar-to-video · label model + temporal ·
   GS digital twin · logo fingerprint · flywheel (Figure 1 + 1–2 hình phụ).
4. **Experiments** (2–2.5 tr): setup, baselines, kết quả, ablations, qualitative.
5. **Discussion / Limitations / Ethics** (0.5 tr).
6. **Conclusion** (0.25 tr).

---

## 9. Reproducibility & artifact
- Công khai: code data-engine (PoC `auto_label/`), config GS twin, test set vàng
  (nếu bản quyền cho phép — nếu không, mô tả + một subset).
- Seeds, phiên bản model (SAM 3, ultralytics), pin như memory backend.
- Bảng compute (GPU-giờ teacher vs student).

---

## 10. Rủi ro reviewer & phòng thủ trước
- *"FM auto-label không mới."* → Đóng góp là **roster-prior + label model + GS twin
  + flywheel cho sponsor analytics**, không phải bản thân FM. Nhấn ablation C1/C4.
- *"GS twin tốn công, có cần?"* → Ablation C4 cho thấy Δ accuracy ở điều kiện hiếm;
  định vị là *optional booster*, hệ vẫn chạy không cần nó.
- *"Test set nhỏ."* → Bổ sung đa trận/đa điều kiện + cross-sport demo (dù nhỏ) để
  chứng minh tính tổng quát (đúng claim linh hoạt).
- *"Đạo đức?"* → Bàn quyền riêng tư cầu thủ/khán giả, dùng đúng mục đích analytics,
  không nhận diện người.

---

## 11. Việc cần làm để có paper (checklist)
- [ ] Chốt 3–4 claim chính (gợi ý C1, C2, C4, C5).
- [ ] Annotate **test set vàng** (chỉ để eval) — đầu tư bắt buộc.
- [ ] Nối adapter SAM 3 thật trong PoC, chạy auto-label vài trận.
- [ ] Dựng 1 GS digital twin venue + logo insertion → đo C4.
- [ ] Triển khai logo fingerprint (visual+OCR+color) → đo C5.
- [ ] Chạy đủ baseline + ablation, điền bảng §7.5.
- [ ] Vẽ Figure 1 + đường cong "mAP vs manual labels".
- [ ] Viết theo cấu trúc §8; kiểm deadline & format IEEE CyberWorlds năm nay.

---

## 12. Nguồn nền (trích trong related work)
- SAM 3 (PCS) · 3DGS data generator + D3DR lighting-aware insertion · SeeTek
  text-aware logo metric learning · Snorkel weak supervision · Track-Refine-Retrain
  temporal self-training · ExposureEngine sponsor visibility. (Link đầy đủ ở
  `frontier_solutions.md` §10 và `autolabel.md` §9.)
