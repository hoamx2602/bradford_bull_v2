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

> **⚠ Provenance của "gold" (xác minh 2026-07-03)**: `data/real/auto/labels` **CHÍNH LÀ
> output SAM3 concept raw** (`sam3_concept_label.py`, text="logo", conf 0.5, every 25),
> KHÔNG phải nhãn người. Bằng chứng: chạy lại SAM3 concept trên đúng 40 frame tái tạo
> gần như y hệt — **403 gold vs 401 re-run**, 30/40 frame trùng số box, 133 box trùng
> khít từng ký tự (chênh nhỏ = SAM3 non-determinism + imgsz stride 640→644). Nhất quán
> với nguyên tắc "nhãn tay = 0" của plan, NHƯNG hệ quả: mọi **R trong bảng dưới = "tỷ lệ
> khớp với logo SAM3 tìm được", không phải recall so với sự thật**. SAM3 concept vì thế
> là teacher/gold de-facto (R=1.0 by construction). Để đo ĐỘ ĐÚNG THẬT của chính SAM3
> cần một gold người nhỏ (chưa có) — xem "Việc cần làm tiếp".

| Mốc | P | R | F1 | Ghi chú |
|---|---|---|---|---|
| Baseline OWL-ViT2 full-frame (raw, toàn GT) | 0.031 | 0.608 | 0.059 | thr=0.05 |
| + person-ROI oracle (toàn GT) | 0.056 | 0.372 | 0.098 | mất signage |
| **Jersey-track baseline** (person-filter vs 303 jersey GT) | **0.056** | **0.495** | **0.101** | ← Stage 1 phải vượt |
| Stage 1a: OWL-ViT2 trên torso crop (fp16) | — | 0.508 | — | **H1 BÁC BỎ** — gate 0.70 fail |
| Stage 1b: copy-paste proposer (YOLO26n, best@ep44) | — | 0.063 | — | **NO-GO** @2.5 prop/person — sim-gap toàn phần |
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

#### Kết quả 1b ✅ HOÀN THÀNH (2026-07-03) — **NO-GO (hard fail)**
Train YOLO26n 1-lớp trên `data/stage1b_ds` (2005 crop copy-paste-on-real, 4128
logo instance), 59 epoch (early-stop patience=15, **best @ epoch 44**).
- **In-domain (synthetic val)**: mAP50 **0.874**, P 0.942, R 0.782 → model học tốt
  chính phân phối train.
- **Trên gold thật (303 jersey GT, protocol y hệt 1a)**: R_jersey = **0.007** @conf 0.05.
  Hạ predict xuống conf 0.001 (prop/person mới 2.5, còn thừa ngân sách ≤10):
  R_jersey chỉ lên **0.063** — 269 box conf-thấp KHÔNG trúng logo, fire vào sọc
  áo/số/nếp vải. Không phải lỗi calibration.
- **Chẩn đoán** (3 góc: sanity in-domain fire OK, sweep conf thấp, ảnh viz): logo
  copy-paste vẫn **sắc nét/tương phản cao** hơn hẳn logo broadcast thật (mờ do
  motion blur, nén, biến dạng vải) dù đã augment. Proposer học "logo = overlay chữ
  sạch" → câm trước logo thật. Kém hơn cả zero-shot 1a (0.508) và baseline (0.495).
- **Quyết định**: gate NO-GO (< 0.70) → copy-paste-on-real **không đủ** thu hẹp
  sim-gap. Kích hoạt nhánh fallback (xem bảng rủi ro). Ứng viên kế tiếp cần đánh giá:
  (a) render-to-photo img2img theo kế hoạch gốc; (b) tăng độ chân thực copy-paste
  (khớp blur/tương phản/hòa sắc mép — rẻ, nhắm đúng nguyên nhân); (c) SAM3
  exemplar→video (branch hiện tại `feat/sam3-autolabel-eval`, xem dòng rủi ro SAM3).
- Artifacts: `auto_label/run_stage1b_train.py`, `auto_label/stage1b_eval.py`,
  weights `runs/detect/runs/stage1b_proposer/weights/best.pt`, `data/stage1b_eval/`.

Deliverables: `auto_label/stage1_torso_proposer.py`, model `runs/stage1/`,
số liệu vào bảng trạng thái.

### 1c. WHERE = SAM3 concept (thay proposer) — ràng buộc độ phân giải ✅ (2026-07-03)
Sau NO-GO 1b, tầng WHERE dùng **SAM3 concept** (`text="logo"`). Đo thực tế trên
RTX 5060 Ti 16GB (6 frame, conf 0.35):

| Config | #box | ms/frame | peak VRAM |
|---|---|---|---|
| imgsz 644 full | 45 | 4191 | 3.97 GB |
| imgsz 1036 full (+`expandable_segments`) | 46 | 4504 | 6.00 GB |
| imgsz 1288 full | **OOM** | — | — |
| **imgsz 644 × 2-tile ngang** | **61 (+36%)** | 3498 | 3.97 GB |

- SAM3 dùng `LetterBox(scale_fill=True)` → **kéo méo** 1280×720 về vuông (ngang bị bóp
  ~0.5× ở 644). Grounding encoder self-attention **O(N²)** theo token → imgsz>1036 OOM
  trên 16GB; 1036 chạy được nhờ chống phân mảnh nhưng **hầu như không thêm box** (vẫn
  stretch cả frame).
- **Lời giải cho logo nhỏ (65% <60px) = TILING**, không phải tăng imgsz: 2 tile ngang
  @644 (~720px/tile → gần-native) cho **+36% box, cùng VRAM**.
- **Cấu hình WHERE chốt**: SAM3 concept, **2-tile ngang, imgsz 644, conf 0.35, overlap
  15%, cross-seam NMS IoU 0.5**. (Latency ~7s/frame — chấp nhận cho auto-label offline.)
- Artifacts đo: `runs/sam3_imgsz_sweep.log`, `runs/sam3_hires_test.log`.

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

#### Kết quả 2 — build + điều tra retrieval ✅ (2026-07-03) — encoder OK, **eval set sai**

Encoder DINOv2-small (384-d) + template DB augment degradation-heavy (1008 biến thể
/18 brand, `gallery_augment.py`) + score margin. Review bởi agent chuyên gia CV.

- **Ràng buộc môi trường (đo thực)**: input frame **720p, KHÔNG phải 1080p**; logo p50
  longest 42px (65% <60px); **không có encoder ảnh offline** (mobileclip_blt.ts chỉ có
  text-tower; DINOv2/SigLIP2 tải 1 lần khi có net — đã tải).
- **Synthetic val** (query = augment held-out của chính 18 logo): top1 **0.913** — NHƯNG
  là "near-duplicate leak" (aug↔aug cùng file gốc), chỉ là upper-bound, không nói gì về
  crop thật.
- **Crop SAM3 thật**: margin p50 0.026 vs synthetic 0.094 (~3.6× thấp), hub-collapse về
  cch. Chẩn đoán loại trừ: corr(size,margin)≈−0.05 (KHÔNG phải sàn logo nhỏ); mask nền
  cho crop thật KHÔNG giúp (0.018) → KHÔNG phải mismatch tiền xử lý.
- **Nguyên nhân thật (soi ảnh crop + frame)**: **gold set 40 frame gần như không chứa
  logo Bradford in-roster**. Video là Bradford **vs St Helens**: gallery = sponsor
  Bradford (aon, cch, chadlaw, klg, fairway, mcp, bartercard...), còn phần lớn crop là
  áo St Helens (BrewDog/CBS/EFT/RWL/B&M), Betfred/Super League, huy hiệu CLB, đồ hoạ
  broadcast — **đều out-of-roster**. Margin thấp phần lớn là **từ-chối-unknown ĐÚNG**,
  không phải encoder hỏng.
- **Bằng chứng dương**: biển **bartercard** (in-roster, xuất hiện nhiều frame) → retrieval
  ID **ĐÚNG** logo "b" (f000200_0, margin 0.048). Xác nhận retrieval chạy được trên
  crop in-roster THẬT. (Chưa nhất quán: crop chữ "Bartercard" bị nhầm mna_cladding.)
- **Quyết định scope (tự quyết, mặc định)**: target = **chỉ sponsor Bradford** (gallery
  hiện tại); đối thủ/giải/đồ hoạ = unknown (từ chối đúng). Khớp luận điểm "thêm club =
  thả logo PNG".
- **Housekeeping**: merge brand key trùng — `yellow`==`paints_laquers` (cùng Paints &
  Lacquers), lưu ý `romantica`/`romantica_beds`, `mna_cladding`/`mna_support`. Bỏ
  `romantica black.jpg` (0-byte), `Bartercard.jpg` CMYK→RGB khi load.
#### Kết quả 2b — Track S boards ⇒ **DINOv2 yếu với wordmark** (2026-07-03)
Trích 100 frame trải toàn clip (video chỉ 90s/4500fr), SAM3 single-tile@644 → 1406
crop, lọc 202 board-candidate (aspect≥1.8, ≥60px), retrieval DINOv2-small. Soi ảnh
top board (đọc được chữ):
- Biển **IN-ROSTER to & rõ vẫn SAI**: "KLG" → aon(sai)/klg(đúng) không nhất quán;
  "acs group" → chadlaw (SAI). Đây KHÔNG phải confound out-of-roster — là biển
  in-roster rõ ràng mà encoder vẫn nhầm.
- Out-of-roster misID: "Stainforth"(ngoài gallery, rất nhiều)→romantica; "BETFRED"→
  atm_hospitality.
- **Kết luận mới**: logo ở đây chủ yếu là **WORDMARK** (chữ). DINOv2-small (self-sup,
  shape-based) đọc chữ kém → sai cả trên biển in-roster lớn. Cần **OCR-lexicon**
  (đọc chữ → khớp tên brand) hoặc **SigLIP2 image→brand-name-text** (đã tải sẵn).
- **OCR-lexicon test (easyocr + fuzzy)**: đọc text 53% board-candidate; fuzzy-match tên
  18 brand → **6/202 khớp roster, TẤT CẢ đúng** (acs×2, aon, bartercard, klg, mna) và
  **DINOv2 sai 5/6 ca đó**. OCR đọc méo do motion blur ("Daitercard"↔bartercard,
  "ACON"↔aon, "klc"↔klg) + tự reject out-of-roster ("stainforth"/"bargains"/"betfred").
  → **OCR-lexicon là WHAT ĐÚNG cho signage** (thắng embedding). Recall/frame thấp do blur.
- **Đòn bẩy tiếp = TEMPORAL**: biển TĨNH, xuất hiện qua nhiều frame, mỗi frame đọc méo
  khác nhau → **gộp consensus cross-frame** khôi phục brand sạch + tăng recall. Hợp
  Track S + đúng lever #1 của chuyên gia. Sản phẩm phụ = "brand nào xuất hiện + tần suất"
  = sponsor-exposure metric.
- **SigLIP2 image→brand-name-text (A2, đã test)**: chỉ đúng **1/6** biển đã xác nhận
  (bartercard), thua OCR (6/6). Sim đồng loạt thấp (~0.1) — crop nhỏ/mờ + brand là DN
  UK ít tên tuổi nên model vision-language không biết zero-shot. → **Embedding (cả
  image-template DINOv2 lẫn image-text SigLIP2) đều THUA OCR trên wordmark mờ.**
  Chốt: **OCR-lexicon = kênh WHAT chính cho signage**, embedding chỉ phụ cho logo-hình.
- Artifacts: `data/real/trackS/`, `data/trackS_pred.jsonl`, `data/trackS_boards_top.png`,
  `data/trackS_ocr.jsonl`, `data/trackS_siglip.jsonl`, `auto_label/siglip_textmatch.py`,
  `auto_label/gallery_augment.py`, `auto_label/sam3_masked_crops.py`.
- **Bottleneck dữ liệu**: clip chỉ 90s → rất ít instance in-roster (mỗi brand 1-2 lần).
  Temporal consensus (A1) và metric nghiêm túc cần **video trận đầy đủ** (A3).

#### Kết quả 2c — PIPELINE GENERIC OCR-lexicon + sponsor-exposure ✅ (2026-07-03)
Chốt kiến trúc WHAT cho signage = **OCR-lexicon TỰ SINH TỪ GALLERY** (drop-in per team,
KHÔNG hard-code):
- `signage_ocr.py build-lex`: OCR mỗi logo SẠCH (nét cao → đọc chuẩn) + token tên file →
  tập token/brand → `lexicon.json`. Lọc STOP (đuôi file, màu, từ generic tài trợ như
  "support/proud/official" — nếu không sẽ false-match "proud supporters of Halifax").
- `exposure_ocr.py`: OCR full-frame 1080p → fuzzy-match token vào lexicon → temporal
  gộp qua frame → bảng exposure (brand, #frame, giây, text). Out-of-roster (đối thủ/giải)
  tự thành 'unknown' vì không khớp token đội nào.
- **Validate trên video THẬT**: tải `yt-dlp` đoạn 10 phút trận **sân nhà Bradford**
  (`Bradford Bulls (H)`, 1920×1080), sample mỗi 2s (301 frame). Kết quả (sau khi lọc FP):
  **KLG (quần short), MCP (áo+biển), Chadwick Lawrence (sau lưng áo)** — ID ĐÚNG, có
  giây phơi sáng. FP "mna_support" từ biển "Proud supporters of Halifax RLFC" đã sửa
  bằng STOP-list generic.
- **Ý nghĩa**: pipeline **annotation-free + generic** chạy end-to-end trên trận Full HD,
  ra sponsor-exposure metric đúng. Đổi đội = thả gallery mới → auto-lexicon → chạy.
- **Giới hạn hiện tại**: recall phụ thuộc OCR đọc được chữ (biển to/áo rõ OK; logo hình
  thuần không chữ + jersey <40px vẫn khó → cần embedding phụ / temporal / frame nét nhất).
- Artifacts: `auto_label/signage_ocr.py`, `auto_label/exposure_ocr.py`, `data/lexicon.json`,
  `data/exposure/`, `data/real/yt/bradford_home.mp4`, `data/exposure_verify.png`.

- **Việc tiếp (blocker)**: gold 40-frame KHÔNG đủ instance Bradford in-roster để đo WHAT
  jersey. Hai hướng: (a) **Track S** — retrieval trên biển tĩnh (bartercard đã chạy,
  logo to/rõ, in-roster) → ăn ngay phần signage; (b) trích thêm frame có player/biển
  Bradford để dựng known-present seed đủ lớn (đo rank + AUROC theo protocol chuyên gia).
- Artifacts: `auto_label/gallery_augment.py`, `auto_label/sam3_masked_crops.py`,
  `data/templates_dinov2s.npz`, `data/gallery_aug|gallery_val/`, `data/gallery_reference.png`,
  `data/stage2_*_pred.jsonl`, `data/stage2_perbrand_top.png`.

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
- **2026-07-03**: Di cư WSL→Windows native (D:\, RTX 5060 Ti). Stage 1b train xong
  (YOLO26n copy-paste, best@ep44, synthetic mAP50 0.874) nhưng **NO-GO trên gold**
  (R_jersey 0.063 @2.5 prop/person). Sim-gap toàn phần: proposer câm trước logo
  broadcast thật. Copy-paste-on-real bị loại.
- **2026-07-04**: Thiết kế lại từ gốc → **kiến trúc INVENTORY** (docs/12): Kit
  Regulation ⇒ định danh mỗi bề mặt vật lý (slot kit / biển) MỘT LẦN ở khoảnh khắc
  nét nhất, mọi crop thừa hưởng nhãn theo hình học; bootstrap student từ crop thật.
  Thay cách "phân loại từng crop" đã fail nhiều đường. Stage 3-6 cũ được hấp thụ
  vào M1-M4 của docs/12.
- **2026-07-03 (tiếp)**: Xác minh **gold = SAM3 concept raw output** (re-run 401 vs
  403, 30/40 frame khớp). **Quyết định (tự quyết theo chỉ đạo): chọn nhánh SAM3** làm
  tầng WHERE — bỏ tiền đề train-synthetic đã fail; SAM3 concept đã là teacher de-facto
  và tìm được logo thật (viz: bắt "IDEAL" ngực + huy hiệu scorebug mà proposer trượt).
  Kiến trúc cập nhật: **thay J1-J3 (proposer/structure) bằng SAM3 concept, giữ tầng
  WHAT (retrieval) làm verifier** (đúng dòng rủi ro SAM3 trong bảng).
  **Việc cần làm tiếp**: (1) một gold NGƯỜI nhỏ (~10-15 frame) để đo độ đúng thật của
  SAM3 concept — hiện framework không đo được vì gold chính là SAM3; (2) làm rõ SAM3
  có nên gồm đồ hoạ scorebug (huy hiệu CLB) hay lọc ra; (3) Stage 2 verification:
  crop SAM3 → retrieval brand trên gallery.
