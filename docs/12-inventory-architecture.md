# 12. Kiến trúc Inventory — thiết kế lại từ gốc (2026-07-04)

> Thay thế cách tiếp cận "phân loại từng crop" (docs/11 Stage 1-2, đã chứng minh
> fail nhiều đường). Kế thừa toàn bộ bằng chứng thực nghiệm trong docs/11.

## Insight trung tâm

**Kit Regulation ⇒ cả đội mặc MỘT bộ kit giống hệt, suốt mùa.** Logo ngực của mọi
cầu thủ, mọi phút, mọi trận (cùng kit) = CÙNG MỘT sponsor. Biển quảng cáo = tập
hữu hạn bề mặt vật lý cố định mỗi sân.

⇒ Bài toán KHÔNG phải "phân loại N triệu crop mờ" mà là **KIỂM KÊ**:
định danh **mỗi bề mặt vật lý MỘT LẦN** (≈6 slot/kit × 2-3 kit + ~20 biển/sân),
tại **khoảnh khắc tốt nhất cả mùa** (pha cận cảnh, logo 200px+, nét). Mọi crop
sau đó chỉ cần **gán về bề mặt nào** (hình học — dễ) rồi thừa hưởng nhãn.

Crop 20px mờ không cần nhận diện — chỉ cần biết nó là "slot ngực Bradford".

## Pipeline

```
video ─► WHERE  : SAM3 concept "logo" + person detect (sample frame)
     ─► SPINE  : tracking — cầu thủ (ByteTrack, logo→torso-slot theo vị trí);
                  biển (bù camera-motion bằng homography → tĩnh trong toạ độ sân)
     ─► INVENTORY: gom track về bề mặt vật lý — hình học + cluster REAL↔REAL
                  (DINOv2 dùng ở đây: real↔real tốt; real↔template mới fail)
     ─► ANCHOR : định danh mỗi bề mặt 1 lần tại top-K frame nét nhất, fuse:
                  OCR-lexicon ⊕ template-verify-trong-roster ⊕ ảnh kit (nếu có)
                  ⊕ màu. → CONFIRMED / UNKNOWN (đối thủ/giải = unknown ĐÚNG)
     ─► AGGREGATE: exposure = tổng thời lượng track (× chất lượng hiển thị)
     ─► BOOTSTRAP: crop thật + nhãn inventory → train YOLO student đa lớp
                  → realtime + thay teacher đi mine vòng sau
```

## Vai trò cố định của từng mảnh đã build (không mảnh nào bỏ)

| Mảnh | Vai trò duy nhất |
|---|---|
| SAM3 (`sam3_concept_label/sam3_masked_crops`) | WHERE class-agnostic |
| OCR-lexicon (`signage_ocr.py`) | ANCHOR (định danh inventory 1 lần) |
| DINOv2 + template aug (`gallery_augment`, `templates_dinov2s.npz`) | cluster real↔real + verify phụ ở frame nét |
| `exposure_ocr.py` | tầng AGGREGATE |
| YOLO train infra (từ stage1b) | STUDENT học crop thật |
| `team_detection/` | gán đội (màu áo) trước khi gom slot |

## Vì sao lấp được các hố đã gặp (bằng chứng docs/11)

1. **Logo thuần hình / cold-start**: cụm chỉ cần 1 anchor bất kỳ trong mùa
   (cận cảnh / ảnh kit / template khớp ở 200px) → cả cụm có nhãn.
2. **Hố template-sạch↔broadcast-mờ** (giết Stage 1a/1b/2): student không bao giờ
   nhìn template — học từ crop thật. Hố biến mất vì không bắc cầu qua nữa.
3. **"Chỉ là keyword"**: sau bootstrap, nhận diện là thị giác thuần (student);
   OCR chỉ là cách hệ tự dạy mình lúc đầu.
4. **Generic club mới**: thả logo PNG → auto-lexicon + template → mine video họ
   (YouTube sẵn) → bootstrap qua đêm. Slot map chung toàn giải.
5. **Realtime (overlay)**: = student, sản phẩm phụ của M3.

## Lỗ hổng của chính kiến trúc này + đối sách

| # | Lỗ hổng | Mức | Đối sách |
|---|---|---|---|
| 1 | Nhãn nhiễu khuếch đại (anchor sai → cụm sai → student sai) | 🔴 | bootstrap chỉ từ cụm ≥2 tín hiệu đồng thuận; audit 30' mẫu phân tầng trước train |
| 2 | Kit variant home/away/cúp (MCP vs "MCP Away" có thật trong gallery) | 🟠 | cluster kit theo màu trước; inventory riêng từng kit |
| 3 | Gán đội (slot Bradford ≠ đối thủ) | 🟠 | màu áo (`team_detection/`); loại trọng tài |
| 4 | Camera pan làm biển trôi trong ảnh | 🟡 | homography ORB/ECC frame-to-frame |
| 5 | Đo đạc: không có nhãn người → lặp bẫy "gold=SAM3" | 🔴 | ~30' click-audit cho báo cáo đầu; sau khi student validated thì thôi |
| 6 | SAM3 mine chậm ~7s/frame | 🟡 | teacher offline; vòng 2 student realtime tự mine |

## Milestones + gate

- **M1** Spine+Inventory trên 1 trận 88' (`data/real/yt/`): tracking, bù camera,
  cụm slot/biển + top-5 frame nét nhất mỗi cụm.
  *Gate: cụm "ngực Bradford" thuần ≥90% (soi mắt).*
- **M2** Anchor + exposure v2 (track-time, không đếm frame lẻ).
  *Gate: audit 30' → precision CONFIRMED ≥95%.*
- **M3** Bootstrap student YOLO đa lớp, đo trên tập audit M2.
  *Gate: ≥90% chất lượng teacher, realtime >30fps.*
- **M4** Club thứ 2: chỉ logo pack + video YouTube, zero code change.
  *Gate: báo cáo exposure + audit precision tương đương.*

## Kết quả M1 ✅ (2026-07-04) — jersey logo detection END-TO-END đạt

Trận `bradford_home.mp4` (10', 1080p): 2900 track (ByteTrack@12.5fps) → rule màu
few-shot → 511 track Bradford (precision ~80%, đủ cho mining) → SAM3 mine 7410
logo-crop torso → DINOv2 real↔real leader-cluster (τ=0.65) → 189 cụm; cụm brand
thuần ≥90% (C61 KLG 11/12, C146 mcp, C67 VARLEY-đối-thủ tự tách) → **GATE PASS**.

**Anchor thắng cuộc = OCR full-frame chiếu vào bbox track** (`anchor_slots.py`):
brand đọc được ở khoảnh khắc nét (1080p) rơi vào (u,v) trên person bbox → slot.

| Brand | Slot | Status | Reads (target-team) |
|---|---|---|---|
| **mcp** | chest | **CONFIRMED** | 9 (9) |
| **klg** | abdomen | **CONFIRMED** | 17 (12) |
| **klg** | shorts | **CONFIRMED** | 4 (2) |
| chadlaw | chest-trên | SUSPECT_PLAYER_NAME | 3 — "LAWRENCE" ở vùng tên áo = họ cầu thủ |

Bài học quan trọng:
- **OCR-anchor per-cluster trên crop mined KHÔNG đủ** (đọc méo 'Kic/Kig', mcp
  vàng-trên-vàng đọc 0) và **template-verify closed-set mean-embedding CŨNG sai**
  (C61=KLG nhưng mcp xếp trên) → real↔template chết hẳn, kể cả sau khử nhiễu.
  Anchor đúng = full-frame OCR ở khoảnh khắc nét + chiếu hình học.
- **Bẫy tên cầu thủ**: "LAWRENCE 13" = họ cầu thủ, KHÔNG phải sponsor Chadwick
  Lawrence → claim chadlaw 6s trong exposure report cũ PHẢI RÚT. Rule: brand có
  token trùng họ người + đọc 1-token + nằm vùng tên áo (v<0.24 lưng trên) → SUSPECT.
- Anchor sửa ngược được nhãn đội (4 track "opponent" có KLG@abdomen ⇒ thật ra Bradford).
- Artifacts: `inventory/*.py`, `data/inventory/` (tracks, jersey crops, clusters,
  bradford_inventory.json).

## Kết quả M2 ✅ (2026-07-04) — nhãn bootstrap sạch, gate audit PASS

Quét anchor dày (OCR full-frame every-10 → **168 reads**: klg 103, mcp 47).
Ba lần lặp gán nhãn, audit bằng mắt mỗi lần (đúng rủi ro #1):
- **v1 (cầu ngoại hình anchor→cluster)**: FAIL kỹ thuật — anchor embed kèm nền thật
  vs cluster embed đã mask → lệch không gian; C61 (KLG thuần) bị bỏ, cụm rác dính mcp.
- **v2 (hình học tid×slot + cluster majority)**: 1275 nhãn nhưng audit ~40-60% purity —
  **ByteTrack ID-switch** trong tackle làm track anchored đổi chủ (VARLEY lọt vào mcp)
  + SAM3 fire nếp vải.
- **v3 (3 cổng: temporal ±6s quanh anchor ∧ quality [≥22px, Laplacian var≥40, mask
  fill≥25%] ∧ giao hình-học∩cluster-consensus-85%)**: **107 nhãn, purity ≈94%** →
  **GATE PASS**. Ít nhưng đúng — bootstrap vòng 1 chỉ cần thế.

Bài học: nhãn bootstrap phải đi qua temporal-locality (chống ID-switch) và
quality-filter (chống fabric-fire); mở rộng số lượng = THÊM VIDEO, không phải nới cổng.
Artifacts: `data/inventory/crop_labels_v3.jsonl`, `label_audit_v3.png`,
`data/exposure_dense/`, `inventory/label_clusters.py`.

## M3 smoke-test ✅ (2026-07-04) — vòng teacher→label→student KHÉP KÍN
Dataset 97 person-crop imgs (85/12), 2 lớp, từ nhãn v3. yolo26n early-stop@47
(best ep22): **mAP50 all 0.920 (mcp 0.995 / klg 0.846)** trên val 14 instance.
Val quá nhỏ → CHỈ là bằng chứng chu trình chạy, không phải claim chất lượng.
Weights: `runs/detect/runs/student_v1/weights/best.pt`.
**Ý nghĩa**: detector thị giác thuần (5.2 GFLOPs, realtime) giờ detect mcp/klg
trên áo — inference không còn phụ thuộc OCR; OCR chỉ là teacher.

### Đánh giá TRUNG THỰC v2 (2026-07-05) — track-disjoint split + FP test
Phát hiện leakage v1: 9/12 ảnh val trùng track với train, cách 16 frame (0.64s)
→ 0.92 là số ảo. Rebuild split theo TRACK (76/21, val 11 track disjoint), retrain:
- **all mAP50 0.558** (0.92→0.56 sau khi bỏ leak — đúng kỳ vọng)
- **klg: mAP50 0.867, R 0.80** trên 20 instance track-chưa-thấy → **tín hiệu thật**
- **mcp: mAP50 0.248, R 0** — fail vì đói data (23 crop train, ~7 track) → cần scale
- **FP test** (150 opponent + 150 steward person-crop): ≤3% ảnh có FP @conf 0.5;
  FP "nặng nhất" (0.93) soi ra là **KLG THẬT trên quần cầu thủ Bradford lẫn trong
  pha tackle** → FP thật ~1-2%. Model KHÔNG bịa brand lên áo đối thủ/steward.
Kết luận: pipeline validated trung thực; thiếu hụt duy nhất = SỐ LƯỢNG DATA.
Weights: `runs/detect/runs/student_v2/weights/best.pt`.

### Nâng cấp KIT-MAP ✅ (2026-07-05) — anchor từ ảnh kit, phủ TOÀN BỘ slot regulation
User chỉ ra hệ mới phủ 3/~10 slot (regulation có cả socks). Đọc `KIT/`:
- `Kit Regulations 2025 SPONSORS SIZINGS.pdf`: 4 trang FRONT/REVERSE/SHORTS/SOCKS
  (socks: "singular sponsor patch on the rear").
- **`Home Kit.jpg` 300dpi = mỏ vàng anchor**: mọi slot đọc được. `inventory/kit_map.py`
  (OCR sheet + template-match; trên kit sheet template là CLEAN↔CLEAN nên hoạt động,
  khác real↔template đã fail) + xác nhận mắt 1 lần/kit (few-shot đã thoả thuận) →
  **`data/inventory/kitmap_home_final.json`: 23 slot / 13 brand gallery** (top_notch
  ngực, mna×2 patch, romantica vạt, chadlaw+atm+bartercard tay, fairway cổ sau, mcp
  lưng trên, acs lưng dưới, cch quần trước, klg+aon+paints quần sau, em_workwear socks).
- Phát hiện kèm: cụm "legs" M1 = **đồ hoạ broadcast** (crest 2 CLB, scorebug) lọt vào
  bbox — cần filter vị-trí-cố-định-trên-màn-hình. Logo socks 2024 quá nhỏ (~10px).
- **Caveat kit-mùa**: video 2024 = kit vàng-đen ≠ kit file 25/26 (trắng) → mining
  chuyển sang trận mùa 25/26 (đã tìm thấy trên YouTube: Bradford ở Super League 2026).
- Gate mới M3: **độ phủ slot theo regulation checklist**, không chỉ mAP.

### Video mùa 25/26 — kiểm chứng kit-map bước 1 (2026-07-05)
Tải `data/real/yt/bradford_sthelens26.mp4` (Bradford (H) vs St Helens 2026, 10',
720p) — **kit trắng khớp Home Kit 25/26** ✓. Track: 1569 tracks. OCR anchor
(every-15): **8/13 brand kit-map đọc được** (klg 35s, mcp 19.5s/129 dets,
bartercard, aon, mna_cladding, acs, top_notch, romantica) — nhảy vọt so với 3
brand ở video 2024; xác nhận kit 25/26 nhiều wordmark đọc được và **kit-map đúng
về tập brand**.
- **Kiểm chứng brand→slot bằng chiếu OCR vào bbox: CHƯA KẾT LUẬN ĐƯỢC** — chỉ
  35/266 read nằm trong bbox cầu thủ sau lọc; phân bố slot nhoè do (i) read của
  BIỂN (acs/bartercard board) sau lưng cầu thủ lọt vào bbox, (ii) tư thế cúi/ngã
  làm v-normalized nhoè, (iii) n quá nhỏ. KHÔNG phải bằng chứng kit-map sai.
- **Cách kiểm chứng đúng (bước tiếp)**: mine SAM3 crop trên cầu thủ Bradford
  (kit trắng — cần rule màu mới: trắng+chevron vàng-đỏ vs teal StHelens) → match
  crop ↔ **patch cắt từ kit sheet** (render-thực, gần broadcast hơn logo phẳng)
  trong closed-set slot của zone đó + tách front/back bằng có/không tên+số.

### Bước 1 (theo yêu cầu user) — WHERE 1-lớp "logo trên NGƯỜI bất kỳ" (2026-07-05)
Scope user chốt: detect mọi logo đúng vị trí trên người (cầu thủ 2 đội + trọng
tài), KHÔNG cần đội/brand. Làm: mine SAM3 all-person video 2026 (**13.053 crop**,
1632 frame, 1569 track) + tái dùng 7410 crop 2024 → `build_where_ds.py` (lọc
sam_conf≥0.4, ≥12px, vùng đồ hoạ scorebug/watermark) → dataset 1 lớp:
train=1244 img/1985 box (2024, kit vàng, 1080p) · val=1609 img/7852 box (2026,
kit trắng, 720p, all-person) — **val cross-video/cross-kit**.
- yolo26n best@ep17: **P 0.373 / R 0.371 / mAP50 0.263** (agreement với teacher
  SAM3 trên video khác hẳn). Diễn giải TRUNG THỰC: (i) "GT" val = pseudo-label
  SAM3 gồm cả nhiễu → số bị đè xuống; (ii) train hẹp (1 trận, 1 kit, Bradford-only)
  vs val rộng (all-person) → domain gap đúng dự kiến; (iii) tốt hơn hẳn Stage 1b
  synthetic (R 0.063) — pseudo-label THẬT hoạt động, cần SCALE đa dạng.
- Viz: `data/inventory/where_v1_valpreds.png`. Weights: `runs/detect/runs/where_v1/`.
- Thuốc: thêm video/kit vào train (mỗi trận ~1-2h mine tự động); val giữ 1 trận
  tách riêng; cân nhắc distill trực tiếp SAM3-teacher trên chính video val-domain.
- Bẫy env mới ghi nhận: launch 2 process CUDA cùng lúc trên Windows có thể dính
  `cudaErrorDevicesUnavailable` thoáng qua → launch tuần tự, verify alive 45s.

### Temporal voting cho WHERE (thiết kế 2026-07-06, từ nhận xét user)
User: student bắt vệt vải thành logo; hỏi "detect theo đoạn thay vì theo frame?".
ĐO trên 13k box mined 2026: **49% box là ONE-OFF** (không lặp vị trí (u,v) trong
track, R=0.09, track≥3 mẫu) = nghi nếp vải/blur → NỬA nhãn train là nhiễu.
Giải pháp 4 tầng (ưu tiên rẻ→đắt):
1. **Temporal voting per-track trên pseudo-label** (lọc meta.jsonl: chỉ giữ box có
   ≥2 support cùng vị trí khác frame) → rebuild where_ds → retrain. RẺ NHẤT.
2. **Cross-player voting**: heatmap (u,v) toàn đội — slot thật là peak chung nhiều
   cầu thủ; nếp vải không align. (= inventory cho WHERE.)
3. **Inference-time min-persistence**: chỉ emit detection sống ≥K frame trong track.
4. Model đa-frame (video input) — đắt, CHỈ làm nếu 1-3 chưa đủ.
Kèm: one-off crops → hard negatives cho vòng self-training sau.

### M3 full (kế tiếp): SCALE
1. Mine thêm 3-5 trận YouTube Bradford (pipeline y nguyên) → mục tiêu 2-5k nhãn
   sạch qua 3 cổng v3 → train lại student, val tách theo TRẬN (không leak).
2. Human audit 30' trên mẫu nhãn + val → metric đáng tin đầu tiên.
3. M4: club thứ 2 (logo pack + video họ) → zero code change.

## Quyết định đã chốt (đổi được nếu user muốn)

- Deliverable chính: **bảng exposure/trận** (aggregate). Overlay realtime = hệ quả M3.
- Ảnh kit: **tuỳ chọn** — có thì anchor mạnh hơn; không có vẫn chạy nhờ cận cảnh.
- "Annotation-free" hiểu đúng: **0 nhãn cho TRAIN**; vẫn cần ~30' xác nhận người
  cho ĐO để con số đáng tin (bài học "gold=SAM3").
