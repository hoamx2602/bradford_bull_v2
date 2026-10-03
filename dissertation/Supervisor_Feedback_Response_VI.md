# Phản hồi feedback của giáo sư — LogoLens Dissertation

**File đã sửa:** `dissertation/Dissertation_Draft_MXH_rev1.docx` (bản gốc `Dissertation_Draft_MXH.docx` giữ nguyên)

---

## 1. Đánh giá tổng thể feedback

12 ý của giáo sư chia làm **ba nhóm**, và nhóm nào cũng đáng điểm:

| Nhóm | Ý số | Bản chất | Ảnh hưởng điểm |
|---|---|---|---|
| **A. Định vị học thuật** (aim, objectives, RQ mapping, trả lời RQ ở Ch.6) | 1, 2, 3, 11 | Nội dung đúng nhưng *không được trình bày như một lập luận khép kín*. Giám khảo phải tự nối objective ↔ RQ ↔ kết quả. | Cao nhất. Đây là tiêu chí "aims & objectives" và "conclusions" trong rubric. |
| **B. Minh bạch bằng chứng** (Table 2 dài, gap table, bảng measurement-status, bảng mAP, bảng annotation audit) | 4, 5, 6, 9, 10 | Bài **đã có** các phân biệt tinh tế nhất (đo được / model-derived / giả định; mAP thường vs support-restricted; audit annotation) nhưng chôn trong văn xuôi. | Cao. Đây chính là điểm mạnh nhất của bài — không trình bày nổi bật là mất điểm oan. |
| **C. Trình bày** (figure quá dày, Figure 16 đa thông điệp, sai cross-reference, caption provenance) | 7, 8, 12 | Lỗi kỹ thuật trình bày. Giáo sư nói thẳng: *"technical quality is stronger than some aspects of the current formatting"*. | Trung bình nhưng **rẻ nhất để sửa** — bỏ qua thì rất phí. |

**Điểm quan trọng cần hiểu:** giáo sư **không** phản đối nội dung hay số liệu nào. Không có ý nào yêu cầu chạy lại thí nghiệm. Toàn bộ là *tái cấu trúc cách trình bày* + **hạ giọng (soften) 2 chỗ** (aim và Objective 3). Đây là feedback của một người đang đẩy bài lên distinction, không phải cảnh báo.

**Rủi ro duy nhất phải cẩn thận:** ý 1 và ý 3 yêu cầu bỏ chữ "accurate". Nhưng bài **vẫn** phải khẳng định độ chính xác ở Chương 5–6 (đó là RQ1). Cách xử lý đúng: bỏ "accurate" khỏi *aim* (câu bao trùm cả LVS), giữ nguyên khẳng định accuracy ở chỗ nó thực sự được đo (detector, trong domain home-kit). Bản rev1 làm đúng như vậy.

---

## 2. Đối chiếu từng ý → đã làm gì

### ✅ Ý 1 — Aim quá chủ quan ("accurate")
**§1.4.** Thay bằng đúng công thức giáo sư đề xuất, cộng một câu ràng buộc phạm vi:

> The aim of this dissertation is to develop and evaluate a **closed-set** multi-logo detection system for unseen sports footage and to implement a **transparent prototype for transforming those detections into auditable visibility evidence**. The scope of the word closed-set is exact: the system recognises a fixed seasonal sponsor roster, and accuracy is established only within the Bradford Bulls home-kit domain defined in Section 3.1.

Câu thứ hai là phần thêm — nó biến việc "bỏ chữ accurate" thành một *hành động có chủ đích* chứ không phải rút lui.

### ✅ Ý 2 — Đánh số O1–O3 + bảng alignment
**§1.4.** Ba bullet → **O1, O2, O3**. Thêm **Table 2. Alignment of objectives, research questions, methods and main outputs** (4 cột: Objective | RQ | Method and analysis | Main output), có câu dẫn.

Cột "Main output" trỏ thẳng tới Table 6/7, Table 8, Table 5 và Figures 14a–19 → giám khảo thấy ngay **mọi objective đều có sản phẩm cụ thể**.

### ✅ Ý 3 — Hạ giọng Objective 3
Trước: *"...while defining the validation required before the LVS can be treated as an accurate operational measure."*
Sau:

> **O3.** Implement a transformation from detections to temporal segments and quality-weighted exposure, **evaluate whether every reported aggregate remains traceable** to the segments, detections, timestamps and source frames that produced it, and **specify the validation** the Logo Visibility Score would have to pass before it could be used as an operational measure.

Trọng tâm chuyển từ *accuracy* → *traceability* + *validation requirements*, đúng yêu cầu.

### ✅ Ý 4 — Table 2 quá dài, trùng lặp §2.1–2.4
Giáo sư viết *"reducing Table 2 to the most important studies **or** moving the full version to an appendix"* — chữ **"or"**, làm một trong hai là đủ. Đã chọn phương án rút gọn, **không tạo appendix**.

- Bảng chính rút **13 → 7 nghiên cứu** (giữ Cornwell & Kwon 2020, Su 2018, Liao 2017, Deliège 2021, Sarkhoosh 2025, Robinson 2025, Jocher 2026), đổi số thành **Table 3**, và **giãn dòng đơn** trong ô bảng (trước là giãn đôi — đây mới là lý do chính khiến bảng tràn nhiều trang).
- Sáu nghiên cứu bị cắt (Breuer & Rumpf 2012, Romberg 2011, Redmon 2016, Carion 2020, Zhao 2024, Zhang 2022) **vẫn được thảo luận đầy đủ trong §2.1–2.4 và vẫn nằm trong References** — không mất bằng chứng nào. Câu dẫn vào bảng nay nói rõ điều đó.
- Đoạn "The table is intended as a reference map…" thay bằng **đoạn synthesis 3 chủ đề** đúng như giáo sư yêu cầu:
  *what is already known → what remains technically unresolved → what no reviewed source supplies*.

### ✅ Ý 5 — Làm research gap hiện rõ bằng hình/bảng
**§2.5.** Thêm **Table 4. Bridge from the reviewed limitations to the response made in this study and the research question that addresses it** — 3 cột `Limitation in the reviewed literature | Response in this study | RQ`, 5 dòng, có trích dẫn ở mỗi limitation. Đoạn dẫn vào Chương 3 viết lại quanh bảng này.

Giáo sư cho phép *"a concise **figure or table**"*, và đã chọn phương án **bảng**: nó đáp ứng đầy đủ yêu cầu mà không phải đánh số lại 12 hình và 4 bảng. Một bản **hình TikZ** cùng nội dung đã được dựng sẵn và compile được tại `latex_figures/fig_11_research_gap_bridge.tex` (render: `pdflatex render_fig_11.tex`) nếu sau này muốn đổi.

### ✅ Ý 6 — Bảng 3 cột phân biệt đo được / proxy / giả định
**§4.2.** Thêm **Table 5. Measurement status of each component of the LogoLens visibility calculation** — 11 dòng, cột `Component | Measurement status | Basis and consequence`. Phân loại từng thành phần: timestamp, A_i, A_f/d_i, size term √(A_i/A_f), confidence c_i, position term, phép nhân, gap tolerance, T_min, T_raw, Q.

Đây là bảng tôi cho là **có giá trị điểm cao nhất trong toàn bộ danh sách** — nó biến điểm mạnh trừu tượng nhất của bài thành một trang giám khảo có thể chỉ tay vào.

### ✅ Ý 7 — Figure 14 và 15 quá dày
- **Figure 14** (6 panel × 3 cột) → tách thành **Figure 14a** (panel a–c, marks gần tâm) và **Figure 14b** (panel d–f, marks lệch tâm/rìa), **và bố cục lại thành lưới 2 cột**. Mỗi panel nay rộng ~3 inch thay vì ~2 inch → chữ và giá trị V_i lớn hơn khoảng **1,5 lần**. Header công thức và footnote giữ trên cả hai hình.
- **Figure 15**: hai ảnh vốn đã là hai file riêng nhưng dùng chung một caption → tách thành **Figure 15a** (12 frame + V_i) và **Figure 15b** (segment formation + aggregation), mỗi hình một caption riêng.
- Văn bản §4.2 viết lại để tham chiếu 14a/14b/15a/15b.

### ✅ Ý 8 — Figure 16 đa thông điệp
Tách đúng như giáo sư gợi ý:
- **Figure 16a. RF-DETR Small training and checkpoint selection** — panel (a) loss, (b) validation/EMA mAP + epoch 36.
- **Figure 16b. RF-DETR Small held-out performance on the three unseen matches** — panel (c) confusion matrix, (d) per-brand AP@0.50.

Tham chiếu trong §5.1 sửa theo ("The confusion matrix in **Figure 16b** contains 146…").

### ✅ Ý 9 — Phân biệt mAP thường vs support-restricted
**§5.2.** Thêm **Table 6. Headline and support-qualified held-out results** — 4 cột `Reported quantity | Value | Classes | Held-out boxes`, 7 dòng:

| Quantity | Value | Classes | Boxes |
|---|---|---|---|
| mAP@0.50, conventional class mean (headline) | 0.9335 | 15 | 165 |
| mAP@0.50, support-qualified (n ≥ 5) | 0.9169 | 11 | 158 |
| mAP@0.50, support-weighted | 0.9293 | 15 | 165 |
| mAP@0.75 | 0.9166 | 15 | 165 |
| mAP@[0.50:0.95] | 0.7471 | 15 | 165 |
| F1 @ 0.35 | 0.898 | 15 | 165 |
| Familiar-match mAP@0.50 (leakage diagnostic) | 0.998 | 15 | not comparable |

**Một lỗi thật đã được sửa nhân tiện:** abstract và §6.1 viết cả `mAP@0.75 = 0.917` lẫn `support-restricted mean = 0.917` — hai đại lượng khác nhau, trùng số khi làm tròn 3 chữ số. Nay dùng 4 chữ số (0.9166 vs 0.9169) và nêu rõ quy ước: *4 chữ số ở §5.2 và Appendix A nơi so sánh chênh lệch < 0.01; 3 chữ số ở chỗ khác*.

### ✅ Ý 10 — Bảng annotation audit
**§5.5.** Thêm **Table 8. Manual audit of the 179 operating-point evaluator outcomes** — `Evaluator outcome | n | Manual-audit interpretation`:
- Matched detection (TP) — 146
- Missed ground truth (FN) — 19 → 12 verified / 3 plausible / **4 invalid non-kit annotations**
- Unmatched prediction (FP) — 14 → 3 verified errors / 1 duplicate / **8 plausible annotation omissions** / 2 indeterminate
- Total — 179

### ✅ Ý 11 — Trả lời RQ1/RQ2/RQ3 tường minh ở Chương 6
Thêm ba đoạn kết:
- Cuối **§6.1**: *"In response to RQ1, …"* (0.9335 / 0.9169 / 0.9166 / F1 0.898 / 50.5 ms / 19.8 FPS; YOLO26 thấp hơn 16.1 và 24.4 điểm; giới hạn 3 trận, 165 box, 1 kit).
- Cuối **§6.2**: *"In response to RQ2, …"* (camera distance là hiệu ứng duy nhất chắc chắn; recall 0.500 wide shot; lighting/resolution confounded).
- Viết lại đoạn RQ3 thành *"In response to RQ3, …"* (traceability chứ không phải accuracy; trỏ về Table 5; liệt kê validation agenda).

### ✅ Ý 12 — Rà soát trình bày và nhất quán
| Lỗi phát hiện | Xử lý |
|---|---|
| §5.1 gọi training trajectory là **"Figure 7"** (thực tế là Figure 16) | → **Figure 16a** |
| **Abstract mất nửa câu**: *"RF-DETR inference on an RTX 5060 Ti…"* (thiếu con số) | → *"averaged 50.5 ms per image, or 19.8 frames per second, on an RTX 5060 Ti…"* |
| **§2.4 lặp nguyên một đoạn** ("The same requirement applies to a Logo Visibility Score…") xuất hiện 2 lần, trước và sau Figure 7 | Xoá bản trùng |
| Appendix A trỏ tới **"Section 3.4.1"** — section không tồn tại | → Section 3.4 |
| Bảng per-class ở Appendix A **không có caption**; A1–A3 đánh số lệch | Thêm **Appendix Table A1**, dồn A1–A3 → **A2–A4** |
| Bảng Appendix B **không có caption** | Thêm **Appendix Table B1** |
| Heading **"Chapter 5: …"** dùng dấu hai chấm, các chương khác dùng dấu chấm | → "Chapter 5. Experiments and Results" |
| Caption **Figure 6(a)/6(b)** khác quy ước với 14a/14b/15a/15b | → Figure 6a / 6b |
| Caption thiếu nhãn provenance ở **Figures 1, 8, 11, 13, 17, 18, 19** | Thêm *Illustrative diagram* / *Empirical data* / *Prototype output* theo đúng quy ước bài đã dùng ở các hình khác |
| **fps** vs **FPS** dùng lẫn lộn | Chuẩn hoá thành **FPS** (khớp List of Abbreviations) |
| **NMS, HSV, GFLOPs, DINOv2** dùng trong bài nhưng không có trong List of Abbreviations | Đã thêm |
| Số bảng bị dồn do thêm bảng mới | Đánh lại toàn bộ: Table 1 (RQ) → 2 (alignment) → 3 (literature) → 4 (gap) → 5 (measurement status) → 6 (headline) → 7 (detector comparison) → 8 (audit). Mọi tham chiếu trong bài đã sửa theo. |

---

## 3. Việc bạn **phải tự làm** trước khi nộp

1. **Cập nhật Table of Contents** — mở file trong Word, Ctrl+A → F9 (hoặc chuột phải vào TOC → *Update Field* → *Update entire table*). Số trang và tiêu đề đã thay đổi.
2. **Kiểm tra word count so với giới hạn.** Đây là điểm cần quyết:
   - Bản gốc: **12,635 từ** (Ch.1–7, kể cả bảng) — trang bìa ghi 12,680.
   - Bản rev1: **14,389 từ** (+1,056 từ văn xuôi, +698 từ trong bảng). Trang bìa đã cập nhật thành 14,389.
   - Nếu giới hạn là **15,000** → an toàn.
   - Nếu giới hạn là **12,000–13,000** → cần cắt. Cắt ở đâu (theo thứ tự ưu tiên, ít mất điểm nhất trước): (a) rút Table 5 từ 11 dòng xuống 7 dòng bằng cách gộp `A_f/d_i` vào dòng `A_i`, gộp gap tolerance + T_min thành một dòng; (b) rút Table 6 bỏ dòng support-weighted và dòng F1; (c) rút Table 3 từ 7 xuống 5 nghiên cứu. **Không** cắt Table 4 hay Table 8 — đó là hai bảng giáo sư yêu cầu trực tiếp.
3. **Xem lại ngắt trang** quanh các bảng/hình mới. Bảng mới đã bật thuộc tính *lặp dòng tiêu đề* khi tràn trang, nhưng Figure 14a/14b nay cao khoảng 5,2 inch nên có thể cần đẩy xuống trang mới.
4. **Đọc lại 3 đoạn "In response to RQ…"** — tôi viết bám sát số liệu đã có trong bài, nhưng giọng văn của bạn nên là người quyết định cuối cùng.
5. *(Tuỳ chọn)* Trong ảnh Figure 15a có dòng chữ in sẵn *"Romantica example from Figure 14(a)"*. Nó vẫn đọc đúng (Figure 14a, panel a), nhưng nếu muốn tuyệt đối sạch thì chạy lại script sinh hình và đổi thành "Figure 14a".

---

## 4. Nhận định về khả năng đạt ≥ 80%

Sau bản rev1, bài đã có đủ những thứ mà một examiner tìm khi cho distinction:

- Aim đo được, objectives đánh số, **bảng alignment chứng minh mọi objective đều được trả lời**.
- **Research gap hiện thành bảng** với trích dẫn, không phải khẳng định suông.
- Kết quả headline **được trình bày kèm giới hạn của chính nó** (support-qualified mean, leakage diagnostic, per-class support) — đây là dấu hiệu rõ nhất của tư duy phê phán.
- **Annotation audit** — rất ít MSc dissertation tự kiểm tra ground truth của mình rồi báo cáo là 4/19 FN là annotation sai.
- **Table 5** phân biệt đo được / proxy / giả định — trả lời trước câu hỏi khó nhất mà viva có thể hỏi về LVS.
- Ba đoạn "In response to RQ…" khiến giám khảo không phải đi tìm.

Điều còn thiếu về mặt *bằng chứng* (validation LVS bằng manual timing và human readability) là giới hạn thật của phạm vi, và bài **đã xử lý đúng cách**: khai báo thẳng, biến thành validation agenda có thể kiểm chứng. Giáo sư đã xác nhận điều này là *"one of the strongest aspects"* — nên đừng cố lấp nó bằng số liệu mới.


---

## 5. Về hình ảnh — có cần generate thêm gì không?

**Câu trả lời ngắn: không.** Rà lại cả 12 ý:

| Ý | Giáo sư yêu cầu gì | Cần hình mới? |
|---|---|---|
| 2, 6, 9, 10 | nói rõ chữ **"table"** | Không — đã làm bảng |
| 5 | *"a concise **figure or table**"* | Không bắt buộc. Đã chọn bảng (Table 4). Bản hình TikZ có sẵn ở `latex_figures/fig_11_research_gap_bridge.tex` nếu đổi ý |
| 7 | Figure 14/15 — chia nhỏ, phóng chữ | Không — đã tách và bố cục lại từ ảnh gốc, **giữ nguyên pixel gốc (~382 DPI ở khổ 6 inch)** |
| 8 | Figure 16 — tách 16a/16b | Không — đã tách (~332 DPI). Xem ghi chú bên dưới nếu muốn render native |
| 1, 3, 4, 11, 12 | chữ nghĩa, cấu trúc, cross-reference | Không liên quan hình |

### Nếu vẫn muốn render lại native (tuỳ chọn, không bắt buộc)

Máy đã cài **MiKTeX** và repo đã có pipeline LaTeX ở `dissertation/latex_figures/` với style dùng chung `logolens_style.tex`. Không cần dùng công cụ sinh ảnh bên ngoài — và **không nên**, vì:
- ảnh do image-gen sinh ra sẽ lệch style với 10 hình LaTeX/TikZ còn lại;
- và sẽ phải khai báo trong **Appendix E (AI disclosure)**, hiện đang ghi rõ *"No empirical metric or reported result was generated by an image-generation model"* — một sơ đồ mang nội dung nghiên cứu do image-gen vẽ sẽ làm câu đó khó bảo vệ.

| Hình | Nguồn native có sẵn | Ghi chú |
|---|---|---|
| Figure 16a / 16b | `latex_figures/fig_07_training_evidence.tex` (PGFPlots), và các panel rời `LogoLens_MSc_Dissertation_v17_media/figure_06a_training_trajectory.png`, `figure_06b_heldout_confusion_matrix.png`, `figure_06c_per_brand_ap50.png` | Nếu dùng panel rời, **phải verify số liệu trước** (epoch 36 / 0.741, và 146–19–14) vì các file đó cũ hơn hình đang nằm trong bài |
| Figure 14a / 14b | **không tìm thấy script nguồn trong repo** | Bản hiện tại là re-composite từ PNG gốc, sắc nét, dùng được. Muốn vẽ lại phải dựng script mới |
| Figure 15a / 15b | không tìm thấy script nguồn | Ảnh gốc đã đủ rõ, chỉ cần tách caption (đã làm) |

Lệnh render một hình TikZ bất kỳ trong thư mục đó:

```
cd dissertation/latex_figures
pdflatex -output-directory=build render_fig_11.tex
pdftoppm -r 300 -png build/render_fig_11.pdf build/fig11
```
