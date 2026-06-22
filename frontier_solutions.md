# Frontier Solutions — Auto-Labeling logo thể thao thế hệ mới

> Tầng tài liệu thứ 3 (frontier). Đọc sau:
> [`autolabel.md`](./autolabel.md) (nền tảng 2 tầng) →
> [`bac3_diffusion_inpainting.md`](./bac3_diffusion_inpainting.md) /
> [`bac4_3d_simulation.md`](./bac4_3d_simulation.md) (triển khai synthetic).
>
> Ký hiệu mức độ chín:
> 🟢 đã có & proven · 🟡 tổng hợp mới (ghép mảnh đã có, chưa ai làm đúng cho case này) ·
> 🔴 forward / đầu cơ (rủi ro cao, tiềm năng lớn).

---

## 0. Đổi khung tư duy: không phải "bài toán annotate" mà là "dư thừa thông tin chưa khai thác"

Ba tín hiệu **miễn phí** pipeline hiện tại đang vứt đi:

1. **Đã có logo gốc** — asset vector của mọi nhà tài trợ (thư mục `Sponsor Logo/`).
2. **Biết trước roster tài trợ mỗi trận** — *prior* cực mạnh: chỉ ~10–30 brand khả dĩ,
   không phải "mọi logo trên đời" → biến open-world thành **closed-set-per-match**.
3. **Dư thừa thời gian trong video** — 1 logo xuất hiện ở hàng trăm frame liên tiếp;
   annotate/track 1 lần đủ cho cả đoạn.

Mọi giải pháp dưới đây **khai thác triệt để 3 tín hiệu này** thay vì gán nhãn mù.

---

## 1. 🟢 Cú hích lớn nhất, làm NGAY: "Exemplar → Video" auto-label bằng **SAM 3**

SAM 3 (Meta, 11/2025) giới thiệu **Promptable Concept Segmentation (PCS)**: đưa
**một ảnh exemplar** (hoặc cụm từ) → segment + **TRACK toàn bộ instance "giống vậy"**
xuyên suốt video.

```
Logo gốc (đã có)  ──► SAM 3 exemplar prompt
                          │
Video trận đấu  ──────────┤
                          ▼
   Mask + track logo ở MỌI frame nó xuất hiện — TỰ ĐỘNG, không annotate
```

- Thay vì annotate **hàng nghìn frame** → cấp **~1 exemplar/logo**, engine gán cả trận.
- PCS chạy trên video, có tracking sẵn → đúng bài toán broadcast.
- Đầu ra (mask + box + brand) → train YOLO nhẹ realtime (distillation).
- SAM 3 đạt 75–80% mức người trên SA-CO (270K khái niệm).

> 🟢 Kỹ thuật đã có; cái mới là **dùng làm auto-label engine chuyên cho sponsor logo
> thể thao**. Riêng bước này xoá ~95% công annotate. → PoC: [`auto_label/`](./auto_label/).

---

## 1·B. Chọn model & license: SAM 3 vs DINO-X vs LocateAnything

Không có "một model thắng tất cả" — chọn theo đúng vai trò trong flywheel.

| Tiêu chí cho bài toán này | SAM 3 | NVIDIA LocateAnything-3B | DINO-X |
|---|---|---|---|
| Prompt bằng **ảnh exemplar** (đã có logo asset) | ✅ | ❌ chỉ text | ✅ visual prompt |
| **Video tracking** xuyên frame | ✅ native | ❌ ảnh tĩnh | ❌ (cần tracker ngoài) |
| Xuất **mask** (cho visibility %) | ✅ | ❌ box + point | ✅ (qua SAM) |
| **OCR / scene-text grounding** | hạn chế | ✅ rất mạnh | khá |
| Tốc độ | TB | ✅ nhanh nhất (PBD) | TB |
| **License thương mại** | ✅ | ❌ **NON-COMMERCIAL** (chỉ academic) | ✅ (API) |

**Kết luận:**
- **SAM 3 = lõi auto-label** (exemplar→video, track, mask). Không model nào khác
  làm trọn 3 việc này → giữ làm xương sống Teacher.
- **LocateAnything = labeler OCR/text** trong Label Model + **kênh text của Logo
  Fingerprint** (§4). ⚠ **Chỉ dùng cho nghiên cứu/paper** — license cấm thương mại;
  KHÔNG nhúng vào sản phẩm. Nó là VLM nặng → thuộc Teacher offline, không phải
  Student realtime.
- **DINO-X = lựa chọn detection thương mại** mạnh hơn (SOTA open-world, +5–6 AP
  LVIS long-tail, có visual prompt) khi cần thay/bù SAM 3 trong bản bán được.
- **Student realtime** luôn là **YOLO distilled** — không dùng VLM nặng cho live.

> Việc benchmark 3 foundation model dị thể (exemplar vs box vs OCR) làm Teacher là
> một **ablation đẹp cho paper** (claim C3): đo từng kênh đóng góp bao nhiêu.
>
> PoC `auto_label/` đã có sẵn `--text-backend {locateanything,dinox,mock}` để cắm
> kênh OCR/text fingerprint song song với SAM 3.

---

## 2. 🟡 "Label Model" — ensemble weak-supervision + **roster prior**

Mỗi labeler đơn lẻ đều nhiễu. Chạy **nhiều labeler yếu song song**, một **label model**
hợp nhất + khử nhiễu thành nhãn sạch + điểm tin cậy (cảm hứng Snorkel, tổ hợp chưa ai
làm cho logo):

| Weak labeler | Tín hiệu |
|---|---|
| Grounding DINO | "có vùng logo ở đây" |
| SAM 3 exemplar | mask + track theo từng brand |
| OCR / scene-text | đọc chữ trong logo |
| Template / embedding | brand gần nhất trong gallery |
| Temporal track | lan nhãn sang frame lân cận |
| **Roster prior (mới)** | **chỉ ~20 brand có thật → loại mọi phỏng đoán ngoài danh sách** |

*Roster prior* là vũ khí riêng của thể thao tài trợ — đẩy precision lên cao gần như
miễn phí. Quy tắc: ≥k labeler đồng thuận + nằm trong roster → nhãn chắc; bất đồng →
human review (active learning).

---

## 3. 🟡 **Digital Twin sân vận động** bằng 3D Gaussian Splatting — đóng sim2real gap gần tuyệt đối

Nâng cấp Bậc 4: **đừng dựng sân giả — tái dựng CHÍNH sân thật**.

```
Footage broadcast  ──► 3D Gaussian Splatting  ──► "digital twin" sân thật
                              │
Logo thật  ──► chèn billboard/áo, LIGHTING-AWARE insertion (D3DR)
                              │
Đổi vị trí/ánh sáng/góc camera  ──► render ảnh + nhãn HOÀN HẢO
```

- Nền **chính là cảnh thật** → chỉ logo là chèn → sim2real gap gần biến mất.
- D3DR (2025): chèn vật thể ăn đúng ánh sáng sân.
- RoboSplat / RoboGSim (2025): train **thuần 3DGS synthetic** sánh ngang/vượt real,
  tổng quát tốt sang góc nhìn mới; 6-DoF augmentation cho vô hạn biến thể.

> 🟡 Các mảnh đã có; **ghép thành digital-twin-per-venue cho sponsor logo là ứng dụng
> chưa thấy**. Đường tới độ chính xác cao nhất khi mở rộng.

---

## 4. 🟡 Tầng 2 đa phương thức: **"Logo Fingerprint"** (visual ⊕ text ⊕ hình học)

Mở rộng SeeTek (text-aware metric learning, WACV'22 — tên brand làm weak label,
fuse visual + scene-text).

```
Logo crop ─┬─► CLIP/SigLIP visual embedding
           ├─► OCR scene-text → tên brand
           ├─► dominant color signature
           └─► aspect ratio / shape descriptor
                     │
                     ▼  hợp nhất → "fingerprint" → so khớp gallery
```

- Nhiều sponsor logo **có chữ** → OCR cho định danh gần chắc chắn, phân biệt được
  logo *trông giống nhau* (điểm yếu kinh điển của embedding thuần).
- **Thêm brand mới = thêm 1 dòng (tên + ảnh + màu) vào gallery, zero training.**

---

## 5. 🟡 Temporal self-training: "Track → Refine → Retrain → Repeat"

Khai thác dư thừa thời gian như self-supervision:
- Detector chạy → **tracking 2 chiều** nối detection thành track.
- Track dài/ổn định = nhãn tin cậy → lan ngược **vá false-negative** (frame bỏ sót).
- Track ngắn/chập chờn = nhiễu → loại.
- Retrain trên nhãn tinh lọc → lặp. **Không cần người**, dựa tính nhất quán thời gian.

---

## 6. 🔴 (Forward) **Render-and-Verify** — analysis-by-synthesis tự kiểm tra, không nhãn

Compositing khả vi làm "trọng tài" tự giám sát: với mỗi detection, **render lại** logo
giả định theo pose/ánh sáng ước lượng rồi so pixel thật.
- Sai số tái dựng thấp → detection thật. Cao → false positive, tự loại.

Cho tín hiệu xác minh **self-supervised hoàn toàn không nhãn** + bộ lọc QC cho mọi
nguồn synthetic (§3). 🔴 Chưa có sẵn cho logo — cần R&D, để ngoài critical path.

---

## 7. Kiến trúc hợp nhất: **"Per-Event Teacher–Student Flywheel"**

```
 MỖI TRẬN / SỰ KIỆN:
   1. Nạp roster tài trợ + logo assets  → cấu hình gallery (zero training)
   2. TEACHER (nặng, offline): SAM3 + GDINO + OCR + roster prior
        → Label Model hợp nhất → nhãn sạch cho trận đó
   3. Temporal track-refine vá sót → 3DGS twin sinh ca hiếm
   4. STUDENT (nhẹ, realtime): YOLO distill từ nhãn teacher → chạy live
   5. Active learning: ca bất đồng/low-conf → human review (rất ít)
   6. Fingerprint gallery + student lớn dần qua mỗi sự kiện ──┐
        └──────────────────── flywheel ─────────────────────┘
```

- *Hiện tại*: bước 1–2 chạy trong **ngày**, xoá annotate ngay.
- *Mở rộng*: môn mới = đổi roster + exemplar; venue trọng điểm = dựng 3DGS twin;
  mỗi sự kiện làm hệ **mạnh dần** (flywheel) thay vì cào lại từ đầu.

---

## 8. Khuyến nghị thực dụng (thứ tự ROI)

| # | Hành động | Loại | Công | Khi nào |
|---|---|---|---|---|
| 1 | SAM 3 exemplar → auto-label + track video | 🟢 | Thấp | **Ngay (PoC sẵn)** |
| 2 | Roster-prior + Label Model hợp nhất | 🟡 | Thấp–TB | Tuần 2–3 |
| 3 | Fingerprint gallery (visual+OCR+màu) | 🟡 | TB | Tháng 1 |
| 4 | Temporal track-refine self-training | 🟡 | TB | Tháng 1–2 |
| 5 | 3DGS digital twin cho venue trọng điểm | 🟡 | Cao | Tháng 2+ |
| 6 | Render-and-Verify QC loop | 🔴 | R&D | Khi cần đẩy trần chính xác |

---

## 9. Trung thực về rủi ro

- **SAM 3 / 3DGS** rất mới (2025–2026) → benchmark trên footage của bạn trước khi tin
  số liệu paper; tracking SAM3 với logo nhỏ/mờ cần kiểm chứng.
- **Roster prior** giả định luôn biết danh sách tài trợ — đúng với giải chuyên nghiệp.
- **Render-and-Verify** là đầu cơ — để R&D song song, không đặt vào critical path.
- Mọi nguồn synthetic vẫn cần **trộn real auto-labeled** tránh sim2real drift.

---

## 10. Nguồn tham khảo

- [SAM 3: Segment Anything with Concepts (arXiv 2511.16719)](https://arxiv.org/html/2511.16719v1)
- [SAM 3 — Ultralytics Docs](https://docs.ultralytics.com/models/sam-3)
- [Gaussian Splatting is an Effective Data Generator for 3D Object Detection](https://arxiv.org/html/2504.16740v1)
- [D3DR — Lighting-Aware Object Insertion in Gaussian Splatting](https://arxiv.org/pdf/2503.06740)
- [3DGS Synthetic Data for Physical AI (RoboSplat / RoboGSim)](https://blog.pebblous.ai/report/isaac-sim-3dgs-vla-synthetic-data-2026-04/en/)
- [SeeTek — Open-set Logo Recognition with Text-Aware Metric Learning (WACV'22)](https://openaccess.thecvf.com/content/WACV2022/papers/Li_SeeTek_Very_Large-Scale_Open-Set_Logo_Recognition_With_Text-Aware_Metric_Learning_WACV_2022_paper.pdf)
- [Image-Text Pre-Training for Logo Recognition](https://arxiv.org/html/2309.10206v1)
- [Snorkel AI — Weak Supervision & Programmatic Labeling](https://snorkel.ai/data-centric-ai/weak-supervision/)
- [TempT — Temporal Consistency for Test-Time Adaptation](https://arxiv.org/pdf/2303.10536)
- [Automatic Adaptation of Object Detectors via Self-Training](https://arxiv.org/pdf/1904.07305)
