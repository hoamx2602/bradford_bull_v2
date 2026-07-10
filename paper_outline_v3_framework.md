# Paper Outline v3 — Framework/hệ thống tính Sponsor Logo Exposure (nhánh `main`)

> Đổi hướng theo yêu cầu: bài báo kể câu chuyện **hệ thống/framework đã triển khai thật**
> ở nhánh `main` (detection từ manual-annotation, YOLO26, đã production hoá đủ 3 tầng
> Visibility→Exposure→EMV + team-filter + body-zone pricing + dashboard) — **không phải**
> một thuật toán AI mới. Nhánh `autolabel` (SAM3/Inventory — xem
> `paper_ideation_v2_inventory.md`) chuyển xuống **Future Work** như một hướng mở rộng
> chưa chắc chắn, đúng như bạn đề xuất.

---

## 0. Đã tra related work — trả lời câu hỏi "có ai viết cái này chưa"

Tôi tra trực tiếp (không đoán). Kết luận: **có, nhưng rất ít, và hệ thống của bạn rộng
hơn** phần lớn tài liệu học thuật đang có.

| Nguồn | Loại | Phạm vi | Khác gì với bạn |
|---|---|---|---|
| **ExposureEngine** (arXiv 2510.04739, nộp IEEE 10/2025) | Bài báo học thuật gần nhất, đã được chính bạn trích trong `LOGOS_Exposure_Pricing_Algorithm.md` | Soccer, OBB logo detection (mAP@0.5 **0.859**, P 0.96 / R 0.87) + tầng phân tích visibility/exposure + lớp "agentic" hỏi-đáp ngôn ngữ tự nhiên. Dataset riêng 1.103 frame/670 logo, giải VĐQG Thuỵ Điển | **Không thấy** xử lý logo trùng giữa 2 đội/trọng tài (team-attribution); **không** có pricing theo vị trí trên áo (body-zone); không phải rugby; không mô tả kiến trúc production (job queue, 2-pass detect, dashboard đa trận) |
| Nielsen "Sponsorship Media Value Benchmarking" | Industry report, không peer-review | Định nghĩa/benchmark EMV ở mức ngành | Không công bố phương pháp CV/kiến trúc kỹ thuật |
| GumGum/Zoomph, Relo Metrics, Shikenso, VISUA | Whitepaper/blog thương mại | Sponsorship ROI, "AI đo logo" | Không phải paper học thuật, không method chi tiết, không mở |
| Patents (vd US11748785, US12141842 — "quantify screen time of displayed brands") | Bằng sáng chế | Đo screen-time bằng deep neural net | Patent, không phải publication; văn phong claim pháp lý, không thực nghiệm tái lập được |
| "Deep Learning for Logo Detection: A Survey" | Survey CV | Tổng quan detection, không riêng sports/EMV | Nền tảng cho Related Work, không cạnh tranh trực tiếp |
| "A Survey of Deep Learning in Sports Applications" (arXiv 2307.03353) | Survey CV thể thao | Perception/comprehension/decision nói chung | Không đề cập sponsor/EMV cụ thể |

**Kết luận cho bạn:** khoảng trống thật tồn tại — **chưa có bài học thuật nào mô tả một
framework production đầy đủ** (job pipeline + team/opponent-safe attribution + 3-tầng
Visibility→Exposure→EMV + pricing theo vị trí trên kit + dashboard đa trận) cho sponsor
exposure. ExposureEngine là bài gần nhất nhưng hẹp hơn (chỉ detection + visibility cơ
bản, không giải quyết bài toán "logo ai" khi 2 đội cùng sponsor — đúng vấn đề mà
`docs/04-team-filter.md` của bạn giải quyết). Đây là **góc bán hàng chính** cho bài báo
framework: "hệ thống production-grade đầu tiên công bố công khai giải bài toán sponsor
exposure end-to-end, kể cả phần khó nhất trong triển khai thật — không phải chỉ
detection".

---

## 1. Định vị bài báo

**Không** bán "chúng tôi có detector tốt hơn" (mAP của bạn thực ra **thấp hơn**
ExposureEngine — xem §5, nên đừng so sánh trực diện ở trục này, sẽ thua). **Bán:**
"đây là kiến trúc hệ thống end-to-end đầu tiên xử lý toàn bộ chuỗi giá trị từ video thô
đến hoá đơn media value — bao gồm những phần literature hiện tại bỏ qua: quy đúng chủ sở
hữu logo khi 2 đội trùng sponsor, định giá theo vị trí trên trang phục, và vận hành
production thật (graceful degradation, 2-pass cost/quality trade-off, báo cáo đa trận)".
Đây là bài **systems/applications paper**, đúng tinh thần bạn muốn — không phải bài
thuật toán.

## 2. Tên bài (ứng viên)

1. **"Beyond Detection: An End-to-End Production Framework for Sponsor Logo Exposure
   and Media Valuation in Sports Broadcasts."**
2. "Who Owns This Logo? Team-Attribution and Slot-Level Pricing for Automated Sponsor
   Exposure Analytics."
3. "From Pixels to Invoice: A Deployed Pipeline for Visibility-, Exposure-, and
   EMV-Based Sponsor Analytics in Rugby League Broadcasts."

> Gợi ý cá nhân: #2 nhấn đúng điểm khác biệt với ExposureEngine (team-attribution +
> slot pricing), dễ giải thích "cái mới" cho reviewer trong 1 câu.

## 3. Abstract (nháp — số thật ở đâu có, còn lại đánh dấu cần đo thêm)

> Automated sponsor-logo exposure measurement is gaining academic attention (e.g.
> ExposureEngine's oriented-box detector for Swedish soccer broadcasts), but published
> work still treats the problem as detection-plus-basic-visibility. Two practical
> obstacles are left largely unaddressed: (i) the same sponsor frequently appears on
> *both* competing teams' kits (or on advertising boards, or referees), so raw detection
> systematically over-counts exposure unless ownership is resolved per-instance; and
> (ii) media buyers price sponsorship by *placement* (chest-centre vs. sock), not just
> aggregate screen time, yet no published system attributes exposure to garment-level
> slots. We present a deployed, end-to-end framework that closes this gap: a fine-tuned
> logo detector (YOLO26, 16 sponsor classes, manually annotated with a model-assisted
> labelling loop) feeds a reference-based, training-free **team-attribution** stage that
> fuses colour-histogram and vision-embedding features with track-level vote hysteresis
> and a three-tier zero-manual-setup bootstrap (kit-anchor images → auto-clustered
> references → luminance heuristic); a three-tier **Visibility \(\to\) Exposure \(\to\)
> EMV** pricing pipeline converts filtered detections into industry-standard media value
> using CPM, audience size and placement multipliers; and an 18-slot **body-zone**
> assignment (via pose keypoints) enables placement-aware pricing absent from prior
> systems. The framework is deployed end-to-end (job orchestration, graceful
> degradation, two-tier sampled/full-fps detection, multi-match analytics dashboard) and
> validated on real rugby-league broadcasts. On a held-out, clip-disjoint test split the
> detector reaches mAP@0.5 = \TODOnum{0.65} (vs.\ an optimistic, leakage-prone
> frame-level split at 0.84 — a methodological cautionary result we report in full); the
> team-attribution stage keeps the correct-team logo in \TODOnum{2/2} validated clips
> while correctly dropping opponent overlap. We report the design decisions, failure
> modes, and calibration lessons (e.g. why literature-default visibility thresholds
> discard real broadcast logos) needed to take a sponsor-analytics system from paper to
> production, and outline an annotation-free extension path as future work.

*(Đánh dấu rõ: mAP 0.65 lấy từ `logo_detection/runs/logo_yolo26m_clipsplit` — split
đúng theo clip, không leak. Số "2/2 clip" hiện quá ít để là claim khoa học — xem §6 việc
cần làm thêm.)*

## 4. Đóng góp (systems/framework contributions — không phải thuật toán mới)

- **C1. Bài toán team-attribution cho sponsor trùng 2 đội** — hình thức hoá + giải bằng
  pipeline reference-based **không cần train riêng** (kit đối thủ đổi mỗi trận): color +
  SigLIP embedding fusion, VoteTracker với hysteresis chống lật nhãn do 1 frame mờ, và
  chính sách **an toàn doanh thu** tường minh (thiếu bằng chứng → giữ, không trừ tiền
  khách hàng sai) — một quy tắc thiết kế đáng công bố vì ảnh hưởng trực tiếp độ tin cậy
  số liệu thương mại.
- **C2. Bootstrap 3 nấc, zero-manual-setup** cho reference đội bóng (kit-anchor ảnh chính
  thức → auto-cluster từ chính video → luminance heuristic) — cho phép hệ chạy ngay trên
  trận/kit mới không cần người set up tay.
- **C3. Body-zone/slot-level pricing (18 slot)** qua pose keypoints — chuyển từ "brand
  X xuất hiện bao lâu" sang "brand X xuất hiện bao lâu **ở vị trí nào**", nền tảng định
  giá theo vị trí (chest-centre giá khác sock) — điểm khác biệt rõ nhất với ExposureEngine
  và toàn bộ industry report đã tra được.
- **C4. Kiến trúc production 2-pass + graceful degradation** — tách pass phân tích
  (sampled, rẻ, đủ chính xác cho EMV) khỏi pass preview (full-fps, mượt cho người xem);
  mọi stage tuỳ chọn lỗi không sập job — một mẫu thiết kế hệ thống đáng chia sẻ cho
  người làm sản phẩm CV thực tế, ít khi xuất hiện trong paper CV thuần.
- **C5. Bài học hiệu chỉnh từ triển khai thật** (đáng giá dù không phải "thuật toán
  mới"): (a) ngưỡng visibility mặc định trong literature (paper gốc ~0.1) vứt gần hết
  logo sponsor thật nhỏ/lệch tâm — phải hạ xuống 0.02 mới dùng được; (b) tách train/test
  theo **clip** thay vì theo frame làm mAP tụt từ 0.84 xuống 0.65 — con số "thật" thấp
  hơn con số "lạc quan do rò rỉ dữ liệu" đáng kể, một cảnh báo phương pháp luận hữu ích
  cho cộng đồng.

## 5. Định vị so với related work (bảng dùng luôn cho §Related Work)

| | ExposureEngine (2510.04739) | Industry (Nielsen/GumGum/Relo/Shikenso) | **Hệ thống này** |
|---|---|---|---|
| Detection | OBB YOLO, mAP 0.859 (soccer) | Không công bố | HBB YOLO26, mAP 0.65 clip-split thật (rugby) — thấp hơn, **không giấu** |
| Team/opponent-overlap | Không đề cập | Không công bố | **Có** — C1/C2, giải đúng vấn đề "2 đội cùng sponsor" |
| Pricing theo vị trí trên kit | Không | Không công bố | **Có** — 18 slot, C3 |
| Kiến trúc production công bố | Một phần (pipeline tổng quát) | Không (bí mật thương mại) | **Đầy đủ**, mở — C4 |
| Bài học hiệu chỉnh/thất bại | Không | Không | **Có**, tường minh — C5 |
| Peer-reviewed | Có (nộp IEEE) | Không | *(mục tiêu của bài này)* |

> Cách viết Related Work: mở đầu bằng ExposureEngine (closest, credit đầy đủ), chỉ ra 2
> khoảng trống nó để lại (team-attribution, slot-pricing) chính là nơi bài này đóng góp;
> đưa industry vào như "thực hành công nghiệp không công bố phương pháp" để lập luận
> đóng góp mở/tái lập được của bạn có giá trị riêng.

## 6. Kiến trúc hệ thống (Figure 1)

```
Video upload ──► Job Orchestrator (FastAPI, stage/progress realtime)
                        │
   ┌────────────────────┼─────────────────────────────────────────┐
   ▼                    ▼                                         ▼
 frames            team (bootstrap refs nếu chưa có)         [degrade gracefully
 (ffprobe)          nấc 1: manual refs                        nếu thiếu model/refs]
                    nấc 2: kit-anchor auto-cluster
                    nấc 3: luminance heuristic
                        │
                        ▼
   detect (sample 2fps): YOLO26 logo ──► visibility score (size×position×conf×OBB)
                        │
                        ▼
   team filter: YOLO11 person + BoT-SORT track ──► jersey crop ──►
   fuse(color, SigLIP) ──► VoteTracker(hysteresis) ──► owner==target? giữ : bỏ
                        │
                        ▼
   pose (YOLO11-pose) ──► gán 18 body-zone/kit-slot
                        │
                        ▼
   exposure (Tầng 2): gộp segment liên tục, per brand, quality-weighted
                        │
                        ▼
   pricing (Tầng 3): EMV = QualityExposure × (CPM/1000) × Audience × PlacementMult.
                        │
        ┌───────────────┼────────────────────┐
        ▼                                     ▼
  preview (full-fps, box+audio)      dashboard (Next.js): Overview / Brand Insights /
        + bodyseg overlay 3D          Analytics Report / export PDF-CSV
```

Figure 2 (mạnh cho Method): **timeline "leakage lesson"** — mAP 0.84 (split theo frame,
lạc quan giả) → 0.65 (split theo clip, thật) → giải thích tại sao (frame liền kề trong
cùng clip rất giống nhau, leak vào val). Cùng tinh thần "kể thất bại rồi sửa" đã dùng
trong outline Inventory — reviewer thích kiểu này.

## 7. Thực nghiệm — đã có gì, còn thiếu gì

**Đã có (thật):**

| Hạng mục | Số liệu | Nguồn |
|---|---|---|
| Detector, split theo frame (lạc quan, có rủi ro leak) | mAP50 0.84, P 0.78, R 0.78–0.83 (16 lớp) | `logo_detection/runs/logo_yolo26m/results.csv` |
| Detector, split theo **clip** (đúng, dùng số này cho paper) | mAP50 0.65 | `logo_detection/runs/logo_yolo26m_clipsplit/results.csv` |
| Detector, 17 lớp (thêm sponsor) | mAP50 0.62–0.63 | `logo_detection/runs/logo_yolo26m_17cls/results.csv` |
| Team-filter, case study | Clip 00-28 (6.6s): kept 6/dropped 0, đúng zone; Clip 01-46 (9.4s): kept 15/dropped 1, đúng zone dù Bradford chỉ 8/39 crop bootstrap | `docs/04-team-filter.md` |
| Exposure/EMV thật trên trận | `exposure_output/M05_white_1080p/exposure_report.csv` (TOPNOTCH 23s/9 lần, BARTERCARD 26s/9 lần, KLG 38s/15 lần...) | production run thật |
| Pipeline tests | 27 pytest (teamid/av/bodyzones...) | `docs/09-operations.md` |

**Cần đo thêm trước khi viết Experiments cho paper (khoảng trống thật, đừng giấu
reviewer):**

1. **Test set giữ lại đúng nghĩa (held-out theo trận)**: hiện các số mAP theo class,
   chưa thấy per-brand breakdown + confusion matrix trên test set trận chưa từng thấy —
   cần chạy 1 lần rõ ràng, report per-class AP.
2. **Định lượng team-filter trên nhiều hơn 2 clip**: cần precision/recall trên vài chục
   clip có nhãn tay "logo này thuộc đội nào" — hiện chỉ có 2 case study định tính.
3. **Validate EMV**: chưa thấy so sánh EMV hệ thống tính vs ước lượng thủ công/chuyên
   gia media-value cho cùng 1 trận — đây là claim "đúng tiền" quan trọng nhất với khách
   hàng thật, nên là bảng số liệu trung tâm của Experiments.
4. **Ablation ngưỡng visibility/segment**: đo Δ exposure khi đổi `VISIBILITY_FLOOR`
   (0.02 vs 0.1 mặc định paper gốc) và `MIN_SEGMENT_SECONDS` — biến bài học định tính ở
   C5 thành số liệu.
5. **Chi phí/latency thật**: đã có 2-pass design (C4) nhưng chưa thấy đo FPS/giờ xử lý
   mỗi phút video — con số vận hành này thuyết phục reviewer "systems" rất nhiều.
6. **So sánh gián tiếp với ExposureEngine**: không cần chạy trên data của họ (khác môn),
   nhưng nên trình bày rõ bảng §5 để reviewer thấy phạm vi rộng hơn dù mAP thấp hơn —
   tránh reviewer nghĩ bạn "thua" ExposureEngine.

## 8. Discussion / Limitations

- Team-attribution giả định kit ổn định trong trận (đổi áo giữa hiệp/giữa mùa cần refresh
  bootstrap).
- Color+embedding fusion nhạy ánh sáng sân/đêm — chưa đo robustness theo điều kiện sáng.
- `SAMPLE_FPS=2` là đánh đổi tốc độ/độ mịn — cần nói rõ sai số exposure tối đa do
  sampling (worst-case 0.5s/detection).
- Body-zone gán qua pose keypoints — lỗi pose (che khuất, va chạm) lan sang sai zone;
  chưa có số đo riêng cho bước này.
- Model 16 lớp cần annotate tay mỗi sponsor mới (~300–500 instance/class,
  `docs/08-annotation-training.md`) — đây **chính là** động lực cho hướng future-work bên
  dưới.

## 9. Future Work — đúng như bạn muốn, đưa nhánh autolabel/Inventory vào đây

> Viết ngắn gọn (nửa cột), không đi sâu — chỉ nêu **vấn đề annotation là bottleneck** của
> hệ thống hiện tại rồi giới thiệu hướng đang thử nghiệm, có cảnh báo "chưa chắc chắn":

- Annotate tay 300–500 instance/class mỗi sponsor mới (`docs/08`) là **chi phí biến đổi
  chính** khi mở rộng sang club/mùa giải mới — không scale tuyến tính với số sponsor.
- Đang thử nghiệm (nhánh `autolabel`, chưa production-ready) một hướng annotation-free
  dựa trên **kit-invariance**: vì một đội mặc đúng 1 kit suốt mùa, mỗi bề mặt vật lý
  (jersey slot/biển quảng cáo) chỉ cần định danh **một lần** ở khung hình nét nhất, rồi
  gán hình học cho mọi lần xuất hiện khác — bước đầu cho kết quả nội bộ đáng khích lệ
  (cụm thuần ≥90%, bootstrap student mAP50 0.92 trên tập rất nhỏ) nhưng **chưa đủ chứng
  cứ để khẳng định** (mới 1 trận, chưa qua audit thống kê nghiêm ngặt). Nếu hướng này
  chín muồi, nó có thể thay thế bước annotate tay ở C1 mà không đổi phần còn lại của
  framework (team-filter, pricing, dashboard giữ nguyên).
- Các hướng mở khác: 3D Gaussian-Splatting digital twin cho dữ liệu điều kiện hiếm
  (rain/glare); mô hình kinh tế lượng phi tuyến cho EMV (bão hoà chú ý, đồng xuất hiện
  nhiều logo); continual/online flywheel cập nhật model theo từng trận mới trong mùa.

*(Chi tiết đầy đủ của hướng annotation-free: xem `paper_ideation_v2_inventory.md` — tài
liệu đó có thể trở thành Phần 2/bài báo thứ hai một khi có đủ số liệu, chứ không nên
gộp vào bài framework này.)*

## 10. Cấu trúc bài (IEEE 2 cột, ~8 trang)

1. **Introduction** (1 tr): pain điểm thật (2 đội cùng sponsor, pricing theo vị trí,
   vận hành production) → contributions C1–C5.
2. **Related Work** (0.75 tr): bảng §5.
3. **System Architecture** (1 tr): Figure 1, mô tả orchestrator + graceful degradation.
4. **Method** (2–2.5 tr): detection+annotation workflow · team-attribution (C1/C2) ·
   Visibility→Exposure→EMV (3 tầng) · body-zone pricing (C3).
5. **Experiments** (2 tr): bảng §7 (đã có), + phần "cần đo thêm" phải làm xong trước khi
   viết mục này thật.
6. **Discussion/Limitations** (0.5 tr): §8.
7. **Future Work** (0.3–0.5 tr): §9 — annotation-free là 1 hướng trong nhiều hướng, nêu
   ngắn, không hứa hẹn quá.
8. **Conclusion** (0.25 tr).

## 11. Venue — gợi ý

- **IEEE CyberWorlds**: vẫn hợp nếu đóng khung phần dashboard 3D/body-zone như "cyber-
  physical visualization of sponsorship data" — nhưng câu chuyện chính (team-attribution,
  pricing) là ứng dụng/systems hơn là "cyberworlds" thuần.
- **ACM MMSports** (workshop tại ACM Multimedia) hoặc **CV4Sports/CVsports** (workshop
  CVPR/WACV): khớp hơn — đúng cộng đồng đang đọc ExposureEngine, quen văn phong
  "applied system + case study thật", chấp nhận mAP không SOTA nếu đóng góp hệ thống rõ.
- Cân nhắc **track "Applications"/"Industry"** nếu venue có, vì bài thiên hệ thống hơn
  thuật toán.

## 12. Checklist trước khi viết bản đầy đủ

- [ ] Chốt bảng §7 mục "cần đo thêm" — ít nhất mục 1–3 (test set giữ trận, team-filter
      định lượng ≥10 clip, EMV validate) trước khi viết Experiments thật.
- [ ] Report rõ ràng cả 2 số mAP (0.84 leak vs 0.65 clip-split) — biến điểm yếu thành bài
      học phương pháp luận (C5), đừng chỉ report số đẹp.
- [ ] Viết bảng so sánh §5 cẩn thận, trung thực về việc mAP thấp hơn ExposureEngine —
      định vị đúng "khác phạm vi" chứ không "cạnh tranh cùng trục".
- [ ] Vẽ Figure 1 (kiến trúc) + Figure 2 (leakage timeline).
- [ ] Future Work: chỉ 1 đoạn ngắn cho autolabel — không kể chi tiết kỹ thuật (đã có bài
      riêng), tránh loãng trọng tâm bài framework.
- [ ] Chọn venue cụ thể theo §11, khớp trang/deadline/format trước khi format IEEEtran.

---

## Tài liệu nền đã đọc thêm cho outline này

`docs/01-overview.md` · `docs/03-pipeline.md` · `docs/04-team-filter.md` ·
`docs/05-exposure-emv.md` · `docs/06-dashboard.md` · `docs/08-annotation-training.md` ·
`docs/09-operations.md` · `LOGOS_Exposure_Pricing_Algorithm.md` ·
`logo_detection/runs/logo_yolo26m*/results.csv` · web search: ExposureEngine
(arXiv 2510.04739), Nielsen/GumGum/Relo Metrics/Shikenso whitepapers, patents liên quan,
"Deep Learning for Logo Detection: A Survey", arXiv 2307.03353.
