# Paper Ideation v2 — "Inventory" là câu chuyện khoa học mạnh nhất bạn đang có

> Vai: đọc lại **toàn bộ** dự án (README, `paper_cyberworlds.md`, `paper/main.tex`,
> `frontier_solutions.md`, `expert_review_and_plan.md`, `docs/worklog.md`,
> `docs/analysis-log.md`, `docs/10-scalable-logo-detection.md`,
> `docs/12-inventory-architecture.md`, số liệu thật trong `runs/`, `exposure_output/`)
> rồi đóng vai một nghiên cứu sinh tiến sĩ đọc kỹ log thí nghiệm của chính mình để
> chốt xem **bài báo nên kể câu chuyện gì**. Tài liệu này bổ sung/điều chỉnh
> `paper_cyberworlds.md` và `paper/main.tex`, không xoá — vì có phát hiện quan trọng
> làm thay đổi trọng tâm.

---

## 1. Đọc lại toàn bộ dự án: đây thực ra là 3 thế hệ kiến trúc, không phải 1

Trước khi bàn bài báo, cần nói thẳng điều tôi thấy rõ nhất sau khi đọc hết log: **dự án
đã tự thí nghiệm qua 3 kiến trúc**, mỗi cái để lại bằng chứng số liệu thật, và **kiến
trúc mới nhất (04/07) mạnh hơn hẳn** cái đang được viết thành bài báo LaTeX
(`paper/main.tex`, soạn 02/07). Đây không phải phê bình — đây là tin tốt: bạn có một
**diễn tiến khoa học thật** (giả thuyết → thất bại đo được → giả thuyết tốt hơn), đúng
thứ một reviewer giỏi muốn thấy nếu kể đúng cách.

| # | Kiến trúc | Ý tưởng lõi | Bằng chứng thật | Số phận |
|---|---|---|---|---|
| G1 | 2-tầng Localizer/Recognizer (`autolabel.md`, `docs/10`) | Tách "logo ở đâu" (class-agnostic) khỏi "logo của ai" (retrieval, zero-train) | Recognizer trên COCO-gold thật (280 ảnh, 1095 ann, 16 brand): **top-1 0.823, open-set AUROC 0.986**; sau mask+fingerprint: **top-1 0.99, AUROC 0.93** | Đúng hướng, vẫn là nền, nhưng... |
| G2 | Cyber-physical data engine: SAM3 exemplar-to-video + label-model + 3DGS twin + logo fingerprint (`paper_cyberworlds.md`, `paper/main.tex`) | Auto-label bằng ensemble foundation-model, đóng sim2real bằng digital twin | **SAM 3 zero-shot dùng trực tiếp làm localizer chấm mAP: mAP@0.5 = 0.013** (over-detect 12× + box vụn/lệch granularity so với người gán nhãn) — xem `docs/analysis-log.md` 28/06 | **Bị chính dữ liệu của bạn bác bỏ** ở vai trò "localizer trực tiếp". SAM3 vẫn dùng được nhưng **chỉ làm labeler/miner**, không phải detector chấm điểm. |
| G3 | **Kit-Regulation Inventory** (`docs/12-inventory-architecture.md`, 04/07) | Cả đội mặc 1 kit y hệt cả mùa ⇒ định danh **mỗi bề mặt vật lý (jersey slot / biển quảng cáo) một lần** tại khung hình nét nhất, mọi crop khác chỉ cần **gán hình học** về bề mặt đó | **M1 PASS**: 2900 track → lọc màu 511 track Bradford (P≈80%) → SAM3 mine 7410 crop → DINOv2 real↔real cluster (τ=0.65) → 189 cụm, cụm thuần ≥90%. **M2 PASS**: sau 3 vòng lặp (v1 fail kỹ thuật, v2 fail vì ID-switch, v3 = temporal-lock+quality-gate+geometric-consensus) → 107 nhãn, **purity ≈94%**. **M3 PASS**: bootstrap YOLO26n (97 ảnh) → **mAP50 0.920 (mcp 0.995 / klg 0.846)** ep22 — xác nhận vòng lặp khép kín | **Đây là kiến trúc thắng cuộc hiện tại — có gate PASS thật, có ablation tự nhiên (v1/v2/v3), có bài học thất bại đã ghi lại.** |

**Nhận định của tôi (advisor voice):** `paper/main.tex` hiện tại kể câu chuyện của **G2**
— hợp lý về mặt "câu chuyện hay cho venue CyberWorlds" (digital twin, cyber-physical),
nhưng **hai claim trung tâm của nó (C2 exemplar-to-video tự động nhãn cả trận; C5
logo-fingerprint mở gallery zero-training) đã bị chính log 28/06–04/07 của bạn cho thấy
yếu hơn dự kiến**: SAM3 zero-shot không đạt mAP dùng được ở vai trò localizer, và
"real↔template" (so logo crop thật với ảnh logo gốc/PNG) — nền tảng của "logo
fingerprint" — **chết hẳn** ("real↔template mới fail", `docs/12` dòng 27). Cái thực
sự work là **real↔real clustering** + **anchor bằng OCR full-frame chiếu hình học**,
tức G3. Nộp `main.tex` như hiện trạng có rủi ro: khi reviewer hỏi "số liệu đâu", bạn sẽ
phải điền các ô `\TODOnum` bằng số thật — mà số thật bạn đang có lại **không ủng hộ**
đúng những gì abstract/main.tex đang tuyên bố.

**Khuyến nghị:** đừng cố nhét G3 vào làm "thêm 1 ablation" của bài G2. **G3 xứng đáng là
bài báo riêng, với framing riêng, mạnh hơn.** Phần còn lại của tài liệu này viết outline
cho bài đó.

---

## 2. Bài báo đề xuất: "Inventory, not Recognition" — sponsor exposure như bài toán kiểm kê bề mặt vật lý

### 2.1. Vì sao đây là góc nhìn mới, không phải "thêm một auto-labeler"

Toàn bộ literature logo detection (đóng khung trong `paper_cyberworlds.md` §6, `docs/10`)
coi bài toán là **classification/retrieval trên từng crop độc lập**: mỗi ảnh logo phải
được nhận diện bằng thị giác (embedding, OCR, template match) — đây là lý do open-set
logo recognition luôn khó (logo nhỏ, mờ, cách điệu, đối thủ giống nhau).

Insight của bạn trong `docs/12` **loại bỏ tiền đề đó**: nhờ **luật kit** (regulation thể
thao: một đội mặc đúng 1 bộ kit suốt mùa, mọi vị trí ngực/tay/quần) và **biển quảng cáo
là vật thể tĩnh cố định trên sân**, số **bề mặt vật lý riêng biệt** trong cả một trận/mùa
là hữu hạn và nhỏ (~6 slot kit × 2–3 bộ kit + ~20 biển ≈ vài chục "identity" — không phải
hàng nghìn crop). Vậy bài toán thật không phải "nhận diện hàng triệu crop mờ" mà là:

> **Kiểm kê (inventory):** định danh mỗi bề mặt vật lý **đúng một lần**, tại khoảnh khắc
> chất lượng cao nhất nó từng xuất hiện trong toàn bộ dữ liệu; mọi lần xuất hiện khác chỉ
> cần **gán về đúng bề mặt đó** — một bài toán tracking/hình học, dễ hơn nhận diện thị
> giác rất nhiều.

Đây là một **structural prior mạnh hơn "roster prior"** (ý tưởng ở G2/`paper_cyberworlds.md`
C1): roster prior thu hẹp "brand nào có thể" (đóng open-world thành closed-set); **kit
prior** đi xa hơn — biến "nhận diện mọi lúc" thành **"nhận diện một lần, ghi nhớ mãi mãi"**.
Đây chính là góc để bán cho reviewer: không phải một auto-labeler tốt hơn, mà là **một
sự đổi khung bài toán** (problem reformulation), loại renders bài toán logo recognition
thành bài toán **re-identification theo track + one-shot anchor**, gần với instance-level
tracking/SLAM hơn là closed/open-set classification truyền thống.

### 2.2. Tên bài (ứng viên)

1. **"Identify Once, Inherit Forever: Kit-Invariance as a Structural Prior for
   Annotation-Free Sponsor Exposure Analytics."** *(nhấn mạnh đúng đóng góp lõi)*
2. "From Recognition to Inventory: Physical-Surface Identity Tracking for Sports
   Sponsorship Analytics."
3. "One Frame Is Enough: Anchor-and-Propagate Labeling for Kit-Constrained Logo
   Exposure Measurement."

### 2.3. Abstract (bản nháp — số liệu THẬT lấy từ log, không phải placeholder)

> Measuring sponsor exposure in sports broadcasts is usually framed as a *recognition*
> problem: every logo crop, however small or blurred, must be independently classified
> against a brand gallery. We argue this framing is unnecessarily hard, and wasteful of
> a domain constraint that sports regulation gives for free: **a team wears one fixed kit
> for an entire season**, and advertising boards are physically static per venue — so the
> number of *distinct physical surfaces* bearing a logo is small (tens, not millions of
> crops). We reformulate sponsor-logo exposure as an **inventory problem**: identify each
> physical surface exactly once, at its highest-quality occurrence, and propagate that
> label to every other occurrence via tracking and geometry rather than repeated visual
> classification. Our pipeline (WHERE → SPINE → INVENTORY → ANCHOR → AGGREGATE →
> BOOTSTRAP) tracks players and boards, clusters raw detections into physical-surface
> groups by real-to-real visual similarity (avoiding the brittle real-to-template
> matching that we show fails empirically), anchors each cluster's identity via
> full-frame OCR projected geometrically onto the clearest frame, and bootstraps a
> lightweight real-time student detector from the resulting labels. On an 88-minute
> rugby-league broadcast, the pipeline tracks 2,900 raw player detections into 511
> team-filtered tracks (~80% team precision), mines 7,410 jersey-logo crops via a
> promptable segmentation teacher, and clusters them into 189 physical-surface groups
> with brand purity above 90%. A three-gate anchor procedure (temporal locality, image
> quality, geometric-cluster consensus) — arrived at only after two simpler variants
> failed under audit — yields 107 confirmed labels at ~94% purity from zero manual
> annotation, sufficient to bootstrap a multi-class real-time detector (mAP@0.5 = 0.92
> on an early validation slice). We report the full failure trajectory (why direct
> zero-shot foundation-model detection, and why gallery-template matching, both fail on
> this data) as evidence for why the inventory reformulation is necessary, not
> incidental.

*(Số liệu trên là thật nhưng **quy mô nhỏ** — 1 trận, val 14 instance. Trước khi nộp
paper thật, cần chạy thêm 3–5 trận để số liệu đủ sức thuyết phục — xem §5.)*

### 2.4. Đóng góp khoa học (claims — đã có bằng chứng sơ bộ thật, không phải giả định)

- **C1. Kit-invariance reformulation.** Hình thức hoá "closed-set-per-surface-per-season"
  thay vì "open-set-per-crop": định nghĩa toán học của physical surface, chứng minh số
  surface ≪ số crop, và đo lợi ích (giảm số quyết định nhận diện cần thiết từ O(#crop)
  xuống O(#surface)).
- **C2. Real↔real clustering thắng real↔template.** Bằng chứng thực nghiệm trực tiếp
  (không phải giả định): DINOv2 template-verify (crop thật vs PNG logo gốc) thất bại,
  trong khi crop-thật↔crop-thật (cùng track/cùng mùa) cluster tốt (189 cụm, purity ≥90%).
  Đây là một **negative result có giá trị** — nhiều hệ thống công nghiệp (gallery
  matching, "logo fingerprint" kiểu SeeTek) ngầm định real↔template hoạt động; dữ liệu
  của bạn cho thấy khoảng cách miền (clean PNG vs broadcast blur/kit-wrinkle/lighting) đủ
  lớn để phá vỡ giả định đó.
- **C3. Anchor-and-propagate labeling với 3 cổng (temporal-locality ∧ quality ∧
  geometric-consensus).** Không chỉ đề xuất — có **ablation tự nhiên đã chạy** (v1→v2→v3,
  xem §2.6) cho thấy vì sao cần cả 3 điều kiện: thiếu temporal-lock → id-switch nhiễm
  nhãn; thiếu quality-gate → vải nhăn/fabric-fire giả logo; thiếu geometric-consensus →
  anchor chiếu sai bề mặt.
- **C4. Negative result: SAM3 zero-shot không dùng được làm localizer chấm mAP.**
  mAP@0.5 = 0.013 khi so với box người gán, dù recall@0.3 = 0.72 — bài học phương pháp
  luận: **đo foundation-model auto-labeler bằng mAP so với box người gán là sai công cụ**
  khi granularity không khớp; cần đo bằng vai trò đúng của nó (region proposal/mining),
  không phải vai trò detector cuối.
  đo lường đúng vai trò cho tuyên bố này, nếu chưa có, coi là "insight, cần thêm 1 thí
  nghiệm nhỏ để khẳng định" (xem §5).
- **C5. Bootstrap flywheel khép kín, không nhãn tay cho train.** Annotation-free thật sự
  ở khâu train (0 nhãn tay để train); vẫn cần ~30 phút audit người **cho việc đo**, không
  phải cho train — phân biệt rạch ròi 2 vai trò này là một đóng góp phương pháp luận nhỏ
  nhưng quan trọng để reviewer không bắt bẻ "sao vẫn có người".

> Gợi ý: một bài CyberWorlds/MMSports ~8 trang nên chốt **C1–C3** làm claim chính (kèm
> C4 như "lesson learned" trong Method/Discussion), để C5 là phần hệ thống hỗ trợ.

### 2.5. Định vị so với related work

| Hướng cũ | Hạn chế | Bạn khác chỗ nào |
|---|---|---|
| Closed-set logo detector (YOLO fine-tune per club) | Club mới = retrain; annotate nặng | Không train nhận diện lại — chỉ cần track+cluster+anchor |
| Open-set logo retrieval (SeeTek, OSLD, "logo fingerprint" kiểu G2) | Giả định real↔template hoạt động | Bạn **đo và chỉ ra** giả định đó vỡ trên broadcast thật; thay bằng real↔real |
| Weak-supervision / ensemble teacher (Grounded-SAM, label model kiểu G2) | Vẫn coi mỗi crop là 1 quyết định cần nhãn | Bạn giảm số quyết định cần thiết xuống O(#surface vật lý), không phải O(#crop) |
| Sports player/ball re-ID, tracking | Không gắn với bài toán sponsor/brand identity | Bạn dùng đúng track identity + fixed-surface geometry làm *nhãn brand miễn phí* — cầu nối tracking↔brand analytics chưa ai làm |
| Sponsor visibility (ExposureEngine, Nielsen-style) | Supervised, cần nhãn tay mỗi giải | Zero-label train nhờ kit-invariance; vẫn xuất đúng metric ngành (exposure-seconds, visibility%, EMV) |

### 2.6. Kiến trúc & hình chủ đạo (Figure 1)

```
video ──► WHERE (SAM3 concept "logo" + person detect, sample frame)
      ──► SPINE (ByteTrack cầu thủ; homography bù camera-motion cho biển tĩnh)
      ──► INVENTORY (gom track→bề mặt vật lý: hình học + cluster REAL↔REAL, τ=0.65)
      ──► ANCHOR (định danh MỖI bề mặt 1 LẦN tại top-K frame nét nhất:
                    OCR-lexicon ⊕ roster ⊕ màu; 3 cổng: temporal-lock ∧ quality ∧
                    geometric-cluster-consensus 85%)
      ──► AGGREGATE (exposure = tổng thời lượng track × chất lượng hiển thị → EMV)
      ──► BOOTSTRAP (crop thật + nhãn inventory → student YOLO đa lớp, realtime,
                       tự thay teacher đi mine vòng sau — flywheel)
```

Figure 2 (rất mạnh cho reviewer): **timeline thất bại→thành công của Anchor** — v1 (fail:
lệch không gian embedding anchor-có-nền vs cluster-đã-mask) → v2 (fail: ID-switch khi
tackle làm anchor đổi chủ, purity 40–60%) → v3 (PASS: purity 94%). Đây là ablation thật,
kể câu chuyện "chúng tôi thử điều hiển nhiên trước, nó vỡ, đây là lý do và cách sửa" —
đúng khẩu vị reviewer thực nghiệm.

### 2.7. Thiết kế thực nghiệm

**Đã có (dùng làm preliminary results / pilot trong bài):**

| Giai đoạn | Số liệu thật đã đo | Nguồn |
|---|---|---|
| Tracking + team-filter | 2900 track → 511 track Bradford, precision ~80% | `docs/12` M1 |
| Mining + inventory cluster | 7410 crop torso → 189 cụm, purity ≥90% (vd C61 KLG 11/12) | `docs/12` M1 |
| Anchor (3 phiên bản) | v1 fail kỹ thuật; v2: 1275 nhãn, purity ~40–60%; v3: 107 nhãn, purity ≈94% | `docs/12` M2 |
| Bootstrap student | YOLO26n, 97 ảnh (85/12), mAP50=0.920 (mcp 0.995/klg 0.846) tại ep22, val 14 instance | `docs/12` M3; xác nhận trong `runs/detect/runs/student_v1/results.csv` dòng epoch 22 |
| Recognizer Tầng 2 (nền, G1) | top-1 0.823→0.99, AUROC 0.986→0.93 (mask+fingerprint), trên COCO-gold 280 ảnh/16 brand | `docs/worklog.md` 28/06 |
| SAM3 as direct localizer (negative) | mAP@0.5=0.013, recall@0.3=0.72, pred area ≈0.2× gt | `docs/analysis-log.md` 28/06 |
| Sản phẩm cuối (baseline pipeline khác, để so sánh) | exposure_report.csv thật trận M05 (TOPNOTCH 23s/9 lần, KLG 38s/15 lần...) | `exposure_output/M05_white_1080p/` |

**Cần làm thêm trước khi nộp (gap thật, đừng giấu reviewer):**

1. **Mở rộng dữ liệu**: hiện mới **1 trận** cho pipeline Inventory (M1–M3) — cần 3–5 trận
   YouTube Bradford khác (docs/12 đã note "M3 full" làm đúng việc này) để có val theo
   TRẬN (no leakage) và số liệu đáng tin thay vì val 14 instance.
2. **Audit người có kiểm soát thống kê**: 30 phút audit hiện tại là "đủ để tự tin nội bộ",
   chưa đủ chặt cho bài báo — cần khung lấy mẫu (stratified theo brand/điều kiện) + báo
   cáo cỡ mẫu/khoảng tin cậy cho precision CONFIRMED, tránh bẫy "gold=SAM3" mà chính bạn
   đã cảnh báo (`docs/12` rủi ro #5).
3. **So sánh với baseline thật**: cột "Manual annotation" trong bảng kết quả hiện là số
   ước lượng từ literature (`docs/10` §7.1: mAP 0.85–0.92, 4–8h/club) — nếu có thể, chạy
   thật 1 baseline supervised nhỏ trên chính data Bradford để con số so sánh không phải
   suy đoán.
4. **Đo đúng vai trò SAM3** (C4): thêm 1 thí nghiệm đo SAM3 ở vai trò "region
   proposal/mining recall" (không phải mAP so box người) để C4 có số liệu thay vì chỉ
   lập luận định tính.
5. **Leave-one-club-out / cold-start**: `docs/12` đã thiết kế M4 (club thứ 2, zero code
   change) nhưng chưa chạy — đây là bằng chứng mạnh nhất cho "scale" claim, nên ưu tiên
   chạy trước khi viết Experiments.
6. **Kit-variant risk (rủi ro #2 trong docs/12)**: chưa có số đo — nên thêm 1 thử nghiệm
   nhỏ (home vs away kit) để chứng minh đối sách "cluster theo màu trước" hoạt động, nếu
   không sẽ là lỗ hổng reviewer dễ bắt.

### 2.8. Ablation (đã có 1 cái tự nhiên, cần thêm 2–3 cái nhỏ)

- **Anchor v1 vs v2 vs v3** (đã có số liệu thật, xem trên) — ablation chính, rất mạnh vì
  là "chúng tôi thử và thất bại thật", không phải ablation giả lập.
- **Real↔real vs real↔template clustering** (C2) — nên đo lại có kiểm soát (hiện là quan
  sát định tính "real↔template mới fail"; nếu đo được số (vd AUROC/purity 2 cách) sẽ mạnh
  hơn nhiều).
- **Có/không homography compensation cho biển quảng cáo** (rủi ro #4) — biển đang là phần
  chưa đo trong M1–M3 (M1–M3 tập trung jersey slot); nên bổ sung nếu kịp.
- **Số trận mine (1 → 3 → 5)**: purity/coverage tăng theo số trận — đúng câu chuyện
  "flywheel" mà không cần tuyên bố suông.

### 2.9. Discussion / Limitations / Ethics

Thẳng thắn dùng lại đúng bảng rủi ro bạn đã tự liệt kê trong `docs/12` (nó rất tốt, giữ
nguyên tinh thần, chỉ dịch sang văn phong paper):

- Giả định roster/kit-list biết trước — đúng cho giải chuyên nghiệp, không đúng cho giải
  nghiệp dư/không kiểm soát trang phục.
- Khuếch đại nhiễu nhãn nếu anchor sai lan sang cả cụm — đối sách: chỉ bootstrap từ cụm
  ≥2 tín hiệu đồng thuận, audit trước train.
- ID-switch khi tackle/va chạm làm track đổi chủ — đối sách: temporal-locality gate (đã
  đo, đã sửa).
- Không có nhãn người độc lập ⇒ nguy cơ "gold tự đo bằng chính hệ" — cam kết audit người
  cho MỌI số liệu báo cáo trong bài, không dùng SAM3 làm gold.
- Đạo đức: hệ đo hiển thị thương hiệu, không định danh người xem/khán giả; cầu thủ chỉ
  được track ở mức instance (không liên kết danh tính cá nhân ngoài mục đích gán kit-slot).

### 2.10. Cấu trúc bài (IEEE 2 cột, ~8 trang) — tái dùng khung `paper/main.tex` đã có

1. Introduction (1 tr): đổi mở bài — pain điểm là "logo recognition khó vì coi mỗi crop
   độc lập"; insight kit-invariance; contributions C1–C4.
2. Related Work (0.75 tr): logo detection/retrieval, weak-sup auto-label, sports
   tracking/re-ID (bảng §2.5).
3. Method (2.5–3 tr): WHERE→SPINE→INVENTORY→ANCHOR→AGGREGATE→BOOTSTRAP + Figure
   1 (kiến trúc) + Figure 2 (anchor v1→v2→v3 timeline thất bại/thành công).
4. Experiments (2–2.5 tr): setup 1 trận (+3–5 nếu kịp), bảng M1–M3, ablation §2.8, so
   sánh sơ bộ với `exposure_output/` pipeline cũ.
5. Discussion/Limitations/Ethics (0.5 tr).
6. Conclusion + Future Work (0.5 tr, xem §3).

---

## 3. Việc bạn có thể làm với bản CyberWorlds cũ (G2) — 2 lựa chọn, không nên bỏ hẳn

**Lựa chọn A — Sáp nhập có kiểm soát (khuyến nghị nếu chỉ muốn 1 bài):** giữ khung
"self-improving cyber-physical data engine" của `main.tex` làm **vỏ hệ thống**, nhưng đổi
**lõi Tầng "label model"** từ (SAM3 exemplar trực tiếp + logo fingerprint real↔template)
sang **Inventory (real↔real cluster + anchor 3-cổng)** — vì đó là phần thật sự work. 3DGS
digital twin lùi xuống "optional future booster cho điều kiện hiếm" (đúng vị trí nó đã có
trong `frontier_solutions.md` §3: 🟡, không phải core). Ưu điểm: 1 bài, không tốn thêm
review-cycle. Nhược điểm: phải viết lại Method + Abstract + Contributions khá nhiều, gần
như bài mới.

**Lựa chọn B — Hai bài riêng (khuyến nghị nếu có thời gian/muốn 2 publication):**
- **Bài 1 (nộp trước, mạnh hơn, đã có số thật):** bài Inventory ở §2 — venue CyberWorlds
  hoặc **MMSports (ACM Multimedia workshop)** / **CV4Sports (CVPR/WACV workshop)** đều
  hợp vì đây là ứng dụng sports-analytics + systems, không chỉ CV thuần.
- **Bài 2 (sau, khi có số thật cho GS twin + weak-supervision ensemble):** giữ nguyên
  tinh thần `main.tex` làm bài về **synthetic data / sim2real cho sponsor logo** — chỉ nộp
  khi đã đo được Δ mAP thật khi thêm 3DGS twin (hiện `docs/analysis-log.md` liệt kê đây
  vẫn là 🟡/🔴, "R&D bet", chưa chạy).

> Cảnh báo của "chuyên gia phản biện" trong chính `expert_review_and_plan.md` của bạn
> (§0.3, "cảnh báo over-engineering") vẫn đúng và tôi nhắc lại: nhánh này đã có **quá
> nhiều bề mặt** (2-tier, SAM3 ensemble, label-model, 3DGS twin, logo fingerprint, Kit2Logo,
> Inventory...) cho một bài báo hay một team nhỏ. Chọn **một câu chuyện chính** (khuyến
> nghị: Inventory) và để phần còn lại làm rõ ràng future-work — đừng cố kể hết trong 8
> trang.

---

## 4. Hướng đi mới / mở rộng nghiên cứu (future work — như bạn yêu cầu)

Ngoài future-work "hiển nhiên" (thêm trận, thêm club, GS-twin), đây là các hướng tôi
nghĩ **thật sự mới và chưa ai làm**, đứng trên vai insight kit-invariance bạn đã có:

1. **"Identify-Once-Inherit-Many" như một paradigm CV tổng quát, không chỉ logo.** Cùng
   nguyên lý áp dụng được cho: số áo cầu thủ (jersey number re-ID — số áo cố định cả mùa),
   nhận diện trọng tài/đội (kit cố định), thậm chí quảng cáo LED động (chuỗi nội dung lặp
   theo chu kỳ đã biết trước). Một bài báo "hệ thống hoá" nguyên lý này như một class bài
   toán (không riêng sponsor logo) sẽ có tầm ảnh hưởng rộng hơn 1 bài ứng dụng.
2. **Lý thuyết lấy mẫu tối ưu cho audit.** Bạn đang audit ~30 phút "cho có" — có thể hình
   thức hoá thành bài toán **thống kê lấy mẫu phân tầng (stratified sampling)**: audit tối
   thiểu bao nhiêu cluster/brand để đạt khoảng tin cậy precision cho trước? Đây là đóng
   góp phương pháp luận nhỏ nhưng làm cho toàn bộ hệ "annotation-free" có nền thống kê
   chặt thay vì "audit cho yên tâm".
3. **Mô hình kinh tế lượng cho EMV**, đi xa hơn `LOGOS_Exposure_Pricing_Algorithm.md`
   hiện tại: exposure-seconds/visibility% → giá trị truyền thông không tuyến tính (độ
   bão hoà chú ý, vị trí trên màn hình, đồng xuất hiện nhiều logo). Kết hợp dữ liệu inventory
   sạch của bạn với mô hình causal/hồi quy từ media-economics là một bài báo riêng, khác
   hẳn hướng CV, nhắm venue kinh tế truyền thông/thể thao thay vì CyberWorlds.
4. **Graph-based correction cho ID-switch**, thay vì chỉ gate temporal-locality: coi toàn
   bộ track+cluster là một đồ thị, dùng **community detection / spectral clustering** để tự
   phát hiện và sửa các track bị "lai" giữa 2 identity sau va chạm — mạnh hơn heuristic ±6s
   hiện tại và có thể đo bằng chính audit purity đã có.
5. **Continual/online flywheel trong mùa giải thật** (không chỉ offline): mỗi trận mới tự
   động chạy inventory, merge vào gallery cụm hiện có, phát hiện kit mới (đổi áo giữa mùa)
   tự động thay vì giả định cố định — biến hệ thống production hiện tại (`backend/`) thành
   nơi triển khai thật cho câu chuyện "self-improving" mà `main.tex` đang mô tả trên giấy.
6. **3DGS digital twin, đúng vị trí của nó**: giữ làm booster có mục tiêu hẹp — sinh dữ
   liệu occlusion/góc hiếm cho riêng bước ANCHOR (không phải cho toàn pipeline), đo Δ
   purity khi thêm, thay vì tuyên bố chung chung "đóng sim2real gap".

---

## 5. Checklist trước khi bắt tay viết bản nộp thật

- [ ] Chốt chiến lược §3 (A: sáp nhập vào `main.tex`, hay B: bài Inventory riêng — khuyến
      nghị B).
- [ ] Chạy thêm 3–5 trận (M3-full theo `docs/12`) → val theo trận, không leak.
- [ ] Audit người có thiết kế lấy mẫu (không chỉ 30 phút tuỳ ý) → precision CONFIRMED có
      khoảng tin cậy.
- [ ] Chạy M4 (club thứ 2, zero code change) — bằng chứng "scale" mạnh nhất còn thiếu.
- [ ] Đo lại C2 (real↔real vs real↔template) có số liệu định lượng, không chỉ định tính.
- [ ] Đo vai trò đúng của SAM3 (region-proposal recall) cho C4.
- [ ] Vẽ Figure 1 (kiến trúc) + Figure 2 (anchor v1→v2→v3 timeline) — đây là 2 hình bán
      được câu chuyện nhất.
- [ ] Viết Method/Abstract theo outline §2, điền số thật đã có, đánh dấu rõ phần nào còn
      "1 trận" (pilot) để reviewer không hiểu nhầm là kết quả cuối.
- [ ] Chọn venue cụ thể (CyberWorlds / MMSports / CVsports) và khớp trang/deadline/format.

---

## 6. Tài liệu nền đã đọc (tham chiếu)

`README.md` · `paper_cyberworlds.md` · `paper/main.tex` · `paper/README.md` ·
`frontier_solutions.md` · `expert_review_and_plan.md` · `docs/worklog.md` ·
`docs/analysis-log.md` · `docs/10-scalable-logo-detection.md` ·
`docs/12-inventory-architecture.md` · `exposure_output/M05_white_1080p/*.csv` ·
`runs/detect/runs/student_v1/results.csv` · `data/inventory/*`.
