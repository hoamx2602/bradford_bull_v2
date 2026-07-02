# 11. Master Plan — Annotation-Free Logo Detection (thực thi theo stage, có gate đo được)

> **Mục tiêu tối thượng**: thêm club/môn mới = thả logo PNG + ảnh kit vào hệ thống,
> KHÔNG annotate tay. Nhãn tay duy nhất trong toàn kế hoạch = 0 (gold set hiện có
> chỉ dùng để ĐO, không train).
>
> Kế thừa: [`frontier_solutions.md`](../frontier_solutions.md),
> [`docs/10-scalable-logo-detection.md`](./10-scalable-logo-detection.md).
> Bằng chứng thực nghiệm: Stage 0 (`data/stage0/stage0_report.json`).

---

## 0. Nguyên lý thiết kế (rút từ dữ liệu, không phải lý thuyết)

1. **Phân rã xác suất**: `P(brand, loc | frame) = P(loc | frame) × P(brand | crop)`
   — tầng WHERE học 1 lần dùng mọi môn; tầng WHAT là retrieval zero-training.
2. **Tái phân bổ độ phân giải**: logo 30-60px trong frame 720p chỉ phủ 3-4 ViT patch
   → mọi xử lý jersey phải chạy trên torso crop upscale, không phải full frame.
   *Bằng chứng: miss rate 67.5% ở bin 30-60px (Stage 0).*
3. **Hai track theo loại bề mặt** *(phát hiện Stage 0: 25% GT là biển tĩnh)*:
   - **Track J (jersey)**: biến dạng, nhỏ, blur — cần pipeline đầy đủ.
   - **Track S (signage)**: phẳng, cứng, tĩnh hàng trăm frame — dễ, ăn ngay 25% bài toán.
4. **Verification thay vì search**: kit layout cho biết logo PHẢI ở đâu trên torso
   → bài toán trở thành xác minh tại vị trí kỳ vọng (dễ) thay vì tìm tự do (khó).
5. **Mỗi stage một giả thuyết khả kiểm + gate go/no-go** — sai thì biết sớm, có fallback.

## Kiến trúc đích

```
Frame ──► YOLOv8 person+pose ──► torso crop (upscale 640)
              │                        │
              │              [J1 WHERE] proposer class-agnostic (YOLO-n, train 1 lần)
              │              [J2 STRUCTURE] chiếu kit_layout qua torso quad → slot kỳ vọng
              │                        │  khớp proposal ↔ slot
              │              [J3 WHAT] verify crop: DINOv2/SigLIP vs gallery template
              │                        │  + roster prior (~20 brand/trận)
              │                        ▼
              │                  (bbox, brand, conf) per player
              │
              └─► [Track S] signage: template retrieval full-frame
                             + temporal stability filter (biển đứng yên)
                                       │
                        ┌──────────────┴──────────────┐
                        ▼                             ▼
              [T TEMPORAL] track 2 chiều,      nhãn hợp nhất sạch
              lan nhãn, lọc track chập chờn          │
                                                     ▼
                              [D DISTILL] YOLO student realtime
                              ca low-conf (~5%) → human review (tùy chọn)
```

**Thêm club mới**: logo PNG → gallery (copy file) · ảnh kit → kit_layout (auto-UV, Stage 6) ·
không train lại WHERE (khái niệm "logo trên vải" bất biến giữa môn).

---

## Trạng thái đo lường (cập nhật sau mỗi stage)

Gold: 40 frames, 403 GT (tự tách bằng person box: **303 jersey / 100 signage** — không cần annotate thêm).

| Mốc | P | R | F1 | Ghi chú |
|---|---|---|---|---|
| Baseline OWL-ViT2 full-frame (raw, toàn GT) | 0.031 | 0.608 | 0.059 | thr=0.05 |
| + person-ROI oracle (toàn GT) | 0.056 | 0.372 | 0.098 | mất signage |
| **Jersey-track baseline** (person-filter vs 303 jersey GT) | **0.056** | **0.495** | **0.101** | ← Stage 1 phải vượt |
| Stage 1a: OWL-ViT2 trên torso crop (fp16) | — | 0.508 | — | **H1 BÁC BỎ** — gate 0.70 fail |
| Stage 1 target (proposal recall, class-agnostic) | — | ≥0.85 | — | ≤10 proposal/người |
| Stage 2 target (P sau verify) | ≥0.60 | ≥0.45 | ≥0.5 | trên jersey subset |
| Stage 4 target (sau temporal) | ≥0.70 | ≥0.65 | ≥0.67 | |

---

## Stage 0 — Phân rã lỗi + oracle ✅ HOÀN THÀNH (2026-07-02)

**Kết quả**: FP 67.1% ngoài person (ROI loại được) + 2516 FP trên người (cần verify).
25% GT là signage. FN tập trung bin 30-60px (miss 67.5%). Person detector chỉ sót 5 GT.
**Quyết định**: ROI = GO · verification = bắt buộc · torso-upscale = justified · thêm Track S.
Artifacts: `auto_label/stage0_error_analysis.py`, `data/stage0/`.

---

## Stage 1 — Track J tầng WHERE: proposer trên torso crop

**Giả thuyết H1**: phần lớn FN 30-60px là do scale; đưa về torso crop 640px thì
detector (kể cả zero-shot) tìm lại được.

### 1a. Thí nghiệm chẩn đoán ✅ HOÀN THÀNH (2026-07-02) — **H1 BÁC BỎ**
OWL-ViT2 fp16 trên torso crop (129 crop, query embeds cached 1 lần):
- R_jersey = **0.508** @ thr 0.05 (baseline full-frame 0.495, gate 0.70 → **FAIL**)
- Bin 30-60px: R=0.345 — không cải thiện dù upscale 2-5×
- Bin medium/large: R=0.78/0.83 — như full-frame
- prop/person = 41 @ 0.05 — FP per crop vẫn rất cao

**Kết luận**: nguyên nhân miss KHÔNG phải scale mà là **appearance gap** —
logo broadcast bị motion blur + biến dạng vải + nén, còn query là template sạch.
Embedding template-matching zero-shot không bắc được cầu này.
**Hệ quả** (theo fallback đã định): (i) Stage 1b train proposer với augmentation
degradation-heavy (blur/downscale/nén) để học "logo-ness" ở low-res thay vì dựa
zero-shot; (ii) gallery Stage 2 phải augment cùng loại degradation;
(iii) copy-paste lên torso THẬT ưu tiên hơn render Blender thuần.
Artifacts: `auto_label/stage1a_torso_owlv2.py`, `data/stage1a/`.

### 1b. Train proposer class-agnostic (thiết kế cập nhật sau 1a)
- Data — 2 nguồn, ưu tiên (A):
  (A) **Copy-paste-on-real**: torso crop thật (person boxes trên frame KHÔNG thuộc
  gold, trích từ video nguồn) + paste logo template với TPS/perspective warp,
  scale thực tế (15-45% bề rộng torso), **motion blur + downscale-upscale + JPEG**
  → bbox chính xác miễn phí, appearance gap tối thiểu.
  (B) Synthetic bậc-4 (relabel mọi logo → 1 lớp `logo`), crop torso, cùng
  degradation trên. Trộn A:B ≈ 70:30.
- Model: YOLOv8n, 1 lớp, imgsz=640, train trên torso crops.
- **Đo**: proposal recall trên 303 jersey GT @ IoU 0.5.
- **Gate GO**: recall ≥ 0.85 với ≤10 proposal/người → Stage 2.
- **Gate NO-GO**: recall < 0.70 → sim-gap lớn hơn dự tính → kích hoạt fallback:
  render-to-photo (img2img strength ~0.55 trên render, label giữ nguyên) rồi train lại.

Deliverables: `auto_label/stage1_torso_proposer.py`, model `runs/stage1/`,
số liệu vào bảng trạng thái.

---

## Stage 2 — Track J tầng WHAT: verification bằng retrieval

**Giả thuyết H2**: với crop đủ nét (≥40px), embedding retrieval trên gallery
template-augmented phân biệt được brand ≥90% và từ chối được FP.

- Gallery: mỗi logo PNG → ~50 biến thể augment tự động (perspective warp, cloth-warp
  thin-plate-spline, motion blur, JPEG nén, đổi nền theo màu jersey) → embedding
  DINOv2-S/SigLIP → FAISS. **Zero annotation.**
- Verify: crop từ proposer Stage 1 → embedding → top-1 similarity;
  chấp nhận nếu sim ≥ τ VÀ brand ∈ roster; ngược lại reject.
- Chọn τ bằng sweep trên... KHÔNG dùng gold (tránh overfit thước đo) — dùng
  synthetic val set; gold chỉ đo 1 lần cuối.
- **Đo** (phân tầng theo size bin): accuracy trên TP crop, FPR trên FP crop, P/R/F1
  end-to-end jersey track.
- **Gate GO**: P ≥ 0.60 giữ R ≥ 0.45 → Stage 3. Bin nào dưới chuẩn → ghi nhận là
  "ngoài phạm vi claim" (crop quá nhỏ thì người cũng không đọc được).

Deliverables: `auto_label/stage2_verify_retrieval.py`, gallery `data/gallery/`.

---

## Stage 3 — Track J tầng STRUCTURE: kit-layout làm prior hình học

**Giả thuyết H3**: chiếu slot kit layout qua torso quad (4 keypoint vai/hông từ
YOLOv8-pose) vá được FN do occlusion một phần / blur, không tăng FP đáng kể.

- Torso quad → homography đơn giản → vị trí kỳ vọng từng slot → slot chưa có
  proposal khớp → cắt vùng kỳ vọng, hỏi thẳng tầng WHAT (targeted verification).
- Sản phẩm phụ: trạng thái `visible / occluded / off-screen` per slot per frame
  = **sponsor visibility metric** (giá trị thương mại trực tiếp).
- **Đo**: recall phục hồi trên FN của Stage 2; điều kiện FP tăng ≤ 2 điểm.
- **Gate**: nếu pose quá nhiễu ở tackle/ruck → Stage 3 chỉ áp cho player đứng/chạy
  (pose conf cao), vẫn giữ giá trị; không chặn đường đi tiếp.

Deliverables: `auto_label/stage3_kit_prior.py`.

---

## Stage 4 — TEMPORAL: track → lan nhãn → lọc

**Giả thuyết H4**: temporal consistency nhân số nhãn ×10+ và nâng cả P lẫn R
mà không cần người.

- Cần video gốc (frame liên tiếp, không phải mỗi 25 frame). Trích thêm frame
  quanh 40 gold frame (±12 frame) từ video nguồn.
- ByteTrack/BoT-SORT trên person; logo gắn theo player track; verify chắc ở
  frame t → lan sang t±k qua optical flow/track; track logo chập chờn (<N frame) → loại.
- **Đo**: (a) số nhãn sinh ra so với số verify gốc; (b) precision nhãn lan
  (kiểm trên gold frame nằm giữa đoạn lan); (c) P/R end-to-end sau temporal.
- **Gate GO**: P ≥ 0.70, R ≥ 0.65 trên jersey subset.

Deliverables: `auto_label/stage4_temporal.py`.

---

## Stage 5 — Track S: biển quảng cáo tĩnh (chạy song song, độc lập J)

**Giả thuyết H5**: bề mặt phẳng + đứng yên → template retrieval + ổn định
temporal giải được ≥80% signage GT với FP thấp.

- Vùng ngoài person box → proposal bằng chính OWL-ViT2/edge-based (biển có khung
  chữ nhật, tương phản cao) → verify bằng gallery Stage 2 (dùng chung!) →
  filter: box phải ổn định vị trí qua ≥K frame (biển không chạy).
- **Đo**: P/R trên 100 signage GT.
- **Gate GO**: R ≥ 0.80, P ≥ 0.70 (kỳ vọng dễ đạt vì bề mặt sạch).

---

## Stage 6 — DISTILL + bài test mở rộng (chứng minh luận điểm scale)

1. Hợp nhất nhãn J + S + temporal → train YOLOv8s student đa lớp (lớp = brand).
   - **Đo**: mAP@0.5 trên gold (cả 2 subset), so với teacher pipeline.
   - **Gate**: student ≥ 90% chất lượng teacher, tốc độ realtime (>30fps).
2. **Bài test tối thượng**: lấy 1 trận môn khác / club khác (vd bóng đá) →
   chỉ cung cấp logo PNG + ảnh kit → chạy toàn pipeline → đo trên ~20 frame
   gold mới (annotate 30 phút, CHỈ để đo).
   - **Gate thành công của toàn dự án**: số liệu môn mới đạt ≥80% số liệu rugby
     mà không sửa code, không train lại WHERE.
3. Auto-UV từ ảnh kit (xóa nốt bước manual cuối): SAM segment áo → detect logo
   trên ảnh kit phẳng (điều kiện dễ) → nội suy UV (§2.2 doc 10).

---

## Rủi ro & fallback (tổng hợp)

| Rủi ro | Phát hiện ở | Fallback |
|---|---|---|
| Sim-gap synthetic quá lớn | Stage 1b gate | render-to-photo img2img, label giữ nguyên |
| Crop nhỏ/mờ không verify được | Stage 2 size-bin | loại khỏi phạm vi claim + để temporal vá |
| Pose fail khi tackle | Stage 3 | chỉ áp cho pose conf cao |
| Không có video gốc đủ dài | Stage 4 | dùng clip có sẵn; giảm claim temporal |
| SAM 3 tốt hơn toàn bộ Track J | benchmark riêng | nếu PCS exemplar→video đạt hơn → thay J1-J3 bằng SAM3, giữ WHAT làm verifier |

---

## Nhật ký thực thi

- **2026-07-02**: Stage 0 hoàn thành. Quyết định kiến trúc 2 track. Kế hoạch này được viết.
