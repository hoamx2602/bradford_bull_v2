# LogoLens — Full Presentation & Defense Script | Kịch bản Thuyết trình & Bảo vệ Đầy đủ
### ~10-minute supervisor meeting: ~7–8 min walkthrough + prepared answers for the discussion that follows
### ~10 phút họp với giảng viên hướng dẫn: ~7–8 phút trình bày + câu trả lời chuẩn bị sẵn cho phần thảo luận sau đó

Pairs with `LogoLens_WP1_Summary.pptx` (10 slides). Each slide section below gives: a target time, the spoken script, and — where a slide carries a number or a formula — what it means and where it came from, with real links to the sources cited in the dissertation.

*Đi kèm với `LogoLens_WP1_Summary.pptx` (10 slide). Mỗi phần slide dưới đây bao gồm: thời lượng mục tiêu, kịch bản nói, và — khi slide có số liệu hoặc công thức — giải thích ý nghĩa và nguồn gốc, kèm các liên kết thực tế đến nguồn tham khảo được trích dẫn trong luận văn.*

---

## Timing overview | Tổng quan thời lượng

| Slide | Content / Nội dung | Target time / Thời lượng |
|---|---|---:|
| 1 | Title / Trang bìa | 15 s |
| 2 | The measurement gap / Khoảng trống đo lường | 40 s |
| 3 | Aim & research questions / Mục tiêu & câu hỏi nghiên cứu | 35 s |
| 4 | Dataset & leakage-aware split / Bộ dữ liệu & phân chia chống rò rỉ | 55 s |
| 5 | RF-DETR vs. YOLO26 / RF-DETR so với YOLO26 | 55 s |
| 6 | Headline result & reliability checks / Kết quả chính & kiểm tra độ tin cậy | 65 s |
| 7 | Where detection breaks down / Khi nào phát hiện thất bại | 55 s |
| 8 | Logo Visibility Score — worked example / Điểm Khả năng Hiển thị Logo — ví dụ minh họa | 100 s |
| 9 | Formula provenance & evaluation status / Nguồn gốc công thức & trạng thái đánh giá | 100 s |
| 10 | Thank you / Cảm ơn | 10 s |
| **Total / Tổng** | | **~8 min** |
| Discussion / defense | using the prepared answers below / sử dụng câu trả lời chuẩn bị sẵn bên dưới | ~2 min+ |

---

## SLIDE 1 — Title / Trang bìa (15 s)

🇬🇧 **English:**

> "Good [morning/afternoon]. This is LogoLens, my dissertation work on Work Package 1: logo detection and visibility intelligence. I'll walk through the system, the headline results, and where the visibility-scoring side of it currently stands — about eight minutes, then happy to take questions."

🇻🇳 **Tiếng Việt:**

> "Xin chào [buổi sáng/buổi chiều]. Đây là LogoLens, đề tài luận văn của tôi trong Gói Công việc 1: phát hiện logo và phân tích khả năng hiển thị. Tôi sẽ trình bày hệ thống, các kết quả chính, và trạng thái hiện tại của phần chấm điểm khả năng hiển thị — khoảng tám phút, sau đó sẵn sàng nhận câu hỏi."

---

## SLIDE 2 — The measurement gap / Khoảng trống đo lường (40 s)

🇬🇧 **English:**

> "The starting problem: every broadcast is already a complete visual record of which sponsor logos appeared — but sponsorship is still priced on precedent, not on that evidence. Commercial platforms — Nielsen, Relo Metrics, Blinkfire — prove automated tracking is feasible, but their methods and data are proprietary, so a club can't check a number against the footage.
>
> The number that motivates the whole dissertation is on the right: the same detector recovers 90% of marks in close and medium shots, but only 50% in wide tactical shots. Same shirt position, very different outcome — that asymmetry is what the rest of the talk explains."

🇻🇳 **Tiếng Việt:**

> "Vấn đề khởi đầu: mỗi trận đấu phát sóng bản thân nó đã là một bản ghi hình ảnh hoàn chỉnh về những logo nhà tài trợ nào đã xuất hiện — nhưng việc định giá tài trợ vẫn dựa trên tiền lệ, chứ không dựa trên bằng chứng đó. Các nền tảng thương mại — Nielsen, Relo Metrics, Blinkfire — chứng minh rằng theo dõi tự động là khả thi, nhưng phương pháp và dữ liệu của họ là độc quyền, nên một câu lạc bộ không thể đối chiếu con số với hình ảnh gốc.
>
> Con số thúc đẩy toàn bộ luận văn nằm ở bên phải: cùng một bộ phát hiện đạt độ thu hồi 90% ở cảnh gần và trung bình, nhưng chỉ 50% ở cảnh rộng chiến thuật. Cùng vị trí trên áo, kết quả rất khác — sự bất đối xứng đó là điều mà phần còn lại của bài trình bày sẽ giải thích."

**Sources behind this slide / Nguồn tham khảo** (full citations in the dissertation's reference list / trích dẫn đầy đủ trong danh mục tài liệu tham khảo):
- Nielsen vBrand — [nielsen.com/news-center/2017/…vbrand](https://www.nielsen.com/news-center/2017/nielsen-acquires-artificial-intelligence-powered-sports-marketing-startup-vbrand/)
- Nielsen Sports Reports — [nielsen.com/marketplace/sports-reports](https://www.nielsen.com/marketplace/sports-reports/)
- Relo Metrics — [relometrics.com/sponsorship-measurement-platform](https://relometrics.com/sponsorship-measurement-platform)
- Blinkfire — [blinkfire.com/d/landing/mediaanalytics](https://www.blinkfire.com/d/landing/mediaanalytics)
- Two Circles, sports IP revenue estimate / ước tính doanh thu IP thể thao — [twocircles.com/…sports-ip-revenue-league](https://twocircles.com/gb/articles/sports-ip-revenue-league-methodology-and-references/)

---

## SLIDE 3 — Aim & research questions / Mục tiêu & câu hỏi nghiên cứu (35 s)

🇬🇧 **English:**

> "Two questions, then a third about what to do with the answer. RQ1: can the system detect multiple sponsor logos accurately on matches it has never seen? RQ2: where does that accuracy break down — size, camera distance, lighting, resolution? RQ3: how do you turn those detections into a visibility measure that's honest about what it hasn't proven yet? The table on screen maps each RQ straight onto the Work Package 1 activities — detection and multi-logo work under RQ1, size/occlusion/quality under RQ2, duration and the Logo Visibility Score under RQ3."

🇻🇳 **Tiếng Việt:**

> "Hai câu hỏi, rồi câu hỏi thứ ba về cách xử lý câu trả lời. RQ1: hệ thống có thể phát hiện chính xác nhiều logo nhà tài trợ trên các trận đấu chưa từng thấy không? RQ2: độ chính xác đó sụp đổ ở đâu — kích thước, khoảng cách camera, ánh sáng, độ phân giải? RQ3: làm thế nào biến những phát hiện đó thành một thước đo khả năng hiển thị trung thực về những gì nó chưa chứng minh được? Bảng trên màn hình ánh xạ trực tiếp từng RQ vào các hoạt động của Gói Công việc 1 — phát hiện và nhận diện đa logo thuộc RQ1, kích thước/che khuất/chất lượng thuộc RQ2, thời lượng và Điểm Khả năng Hiển thị Logo thuộc RQ3."

---

## SLIDE 4 — Dataset & leakage-aware split / Bộ dữ liệu & phân chia chống rò rỉ (55 s)

🇬🇧 **English:**

> "584 images, 1,903 boxes, 16 sponsor classes, 15 separate matches. The methodological decision that matters most here: the unit of split is the **match**, not the frame. I found this the hard way — an earlier frame-level split let 51 of 56 validation frames share a training frame from the same clip within two seconds. That's not testing generalisation, that's testing memory.
>
> So the final design assigns whole matches to train, validation or test — never split within a match. And the number at the bottom proves why that mattered: run the same checkpoint on *familiar* footage and it scores 0.998 mAP. Run it on genuinely unseen matches and it drops to 0.933. That 6.5-point gap is evaluation optimism a naive split would have hidden completely."

🇻🇳 **Tiếng Việt:**

> "584 ảnh, 1.903 khung bao, 16 lớp nhà tài trợ, 15 trận đấu riêng biệt. Quyết định phương pháp quan trọng nhất ở đây: đơn vị phân chia là **trận đấu**, không phải khung hình. Tôi phát hiện điều này một cách khó khăn — một lần phân chia theo khung hình trước đó đã để 51 trong 56 khung hình xác thực chia sẻ một khung hình huấn luyện từ cùng một đoạn clip trong vòng hai giây. Đó không phải là kiểm tra khả năng tổng quát hóa, đó là kiểm tra trí nhớ.
>
> Vì vậy thiết kế cuối cùng gán toàn bộ trận đấu vào tập huấn luyện, xác thực hoặc kiểm tra — không bao giờ chia trong cùng một trận. Và con số ở cuối chứng minh tại sao điều đó quan trọng: chạy cùng một checkpoint trên dữ liệu *quen thuộc* và nó đạt 0,998 mAP. Chạy trên các trận đấu thực sự chưa từng thấy và nó giảm xuống 0,933. Khoảng cách 6,5 điểm đó chính là sự lạc quan trong đánh giá mà một phép phân chia ngây thơ sẽ che giấu hoàn toàn."

---

## SLIDE 5 — RF-DETR vs. YOLO26 / RF-DETR so với YOLO26 (55 s)

🇬🇧 **English:**

> "With the split fixed, I ran a controlled comparison: RF-DETR Small against three YOLO26 baselines — nano, small, medium — all on the same images, same 896-pixel input, same scoring code. RF-DETR Small wins by 16.1 points at mAP@0.50 and, more tellingly, by 24.4 points at the stricter mAP@0.75 — the gap widens as the overlap requirement gets stricter, which points to better localisation, not just better classification.
>
> One caveat I want to state myself before anyone else raises it: pre-training, parameter count and the augmentation recipe are not equal between the two families — RF-DETR carries DINOv2 pre-training that YOLO26 doesn't get. So this is a *system-level* result — 'RF-DETR Small worked better here, under these recipes' — not a general claim that transformers beat convolutional detectors."

🇻🇳 **Tiếng Việt:**

> "Sau khi cố định phép phân chia, tôi thực hiện so sánh có kiểm soát: RF-DETR Small so với ba phiên bản YOLO26 cơ sở — nano, small, medium — tất cả trên cùng bộ ảnh, cùng đầu vào 896 pixel, cùng mã chấm điểm. RF-DETR Small thắng 16,1 điểm ở mAP@0.50 và, đáng chú ý hơn, 24,4 điểm ở ngưỡng nghiêm ngặt hơn mAP@0.75 — khoảng cách mở rộng khi yêu cầu trùng lặp tăng lên, điều này chỉ ra khả năng định vị tốt hơn, không chỉ phân loại tốt hơn.
>
> Một lưu ý tôi muốn tự nêu trước khi ai đó đặt ra: tiền huấn luyện, số lượng tham số và công thức tăng cường dữ liệu không tương đương giữa hai họ mô hình — RF-DETR mang theo tiền huấn luyện DINOv2 mà YOLO26 không có. Vì vậy đây là kết quả ở *cấp hệ thống* — 'RF-DETR Small hoạt động tốt hơn ở đây, với các công thức này' — không phải một tuyên bố chung rằng transformer đánh bại bộ phát hiện tích chập."

**Sources / Nguồn tham khảo:**
- RF-DETR — Robinson et al., 2025 — [arxiv.org/abs/2511.09554](https://arxiv.org/abs/2511.09554)
- YOLO26 — Jocher et al., 2026 — [arxiv.org/abs/2606.03748](https://arxiv.org/abs/2606.03748)
- DINOv2 backbone — Oquab et al., 2023 — [arxiv.org/abs/2304.07193](https://arxiv.org/abs/2304.07193)

---

## SLIDE 6 — Headline result & reliability checks / Kết quả chính & kiểm tra độ tin cậy (65 s)

🇬🇧 **English:**

> "So the headline: 0.933 mAP@0.50, 0.917 at the stricter threshold, F1 of 0.898, and inference at 19.8 frames per second on a consumer GPU. The image on the left is a real held-out frame — not a cherry-picked demo, an actual test image — with all 12 logos across 6 different sponsor brands correctly matched, zero false positives. That's what 'multiple logos simultaneously' looks like in practice.
>
> But I don't want to leave a single number unqualified, so three checks sit alongside it. The leakage check you've already seen — 0.998 to 0.933. The support check: four of fifteen classes have fewer than five test boxes between them, so I report a restricted mean over the eleven better-supported classes — 0.917 — right alongside the conventional 0.9335. And the stability check: per-match scores of 0.973, 0.934 and 0.976, so the result isn't being carried by one lucky match."

🇻🇳 **Tiếng Việt:**

> "Vậy kết quả chính: 0,933 mAP@0.50, 0,917 ở ngưỡng nghiêm ngặt hơn, F1 đạt 0,898, và suy luận ở tốc độ 19,8 khung hình mỗi giây trên GPU tiêu dùng. Hình ảnh bên trái là một khung hình thực từ tập kiểm tra — không phải ảnh chọn lọc, mà là ảnh kiểm tra thực sự — với tất cả 12 logo trên 6 thương hiệu nhà tài trợ khác nhau được nhận diện chính xác, không có dương tính giả. Đó là hình ảnh thực tế của 'nhận diện đồng thời nhiều logo'.
>
> Nhưng tôi không muốn để bất kỳ con số nào mà không có ngữ cảnh, nên ba bước kiểm tra đi kèm. Kiểm tra rò rỉ mà bạn đã thấy — từ 0,998 xuống 0,933. Kiểm tra mẫu: bốn trong mười lăm lớp có ít hơn năm khung bao kiểm tra, nên tôi báo cáo trung bình giới hạn trên mười một lớp có đủ mẫu — 0,917 — ngay bên cạnh con số thông thường 0,9335. Và kiểm tra ổn định: điểm theo trận lần lượt là 0,973, 0,934 và 0,976, nên kết quả không bị chi phối bởi một trận đấu may mắn."

---

## SLIDE 7 — Where detection breaks down / Khi nào phát hiện thất bại (55 s)

🇬🇧 **English:**

> "RQ2: where does it fail? Camera distance is the clearest answer. Recall is around 0.90 in close and medium shots, and falls to 0.500 in wide tactical shots. What's important is *how* it fails — precision on wide shots stays at 1.000. The detector isn't hallucinating logos, it's simply not seeing the small, distant ones. That's a predictable, one-directional bias: any duration estimate built on this detector will under-count exposure specifically in passages dominated by wide camera work — which matters because full match broadcasts contain a lot more wide play than the highlight clips this dataset draws from."

🇻🇳 **Tiếng Việt:**

> "RQ2: nó thất bại ở đâu? Khoảng cách camera là câu trả lời rõ ràng nhất. Độ thu hồi khoảng 0,90 ở cảnh gần và trung bình, và giảm xuống 0,500 ở cảnh rộng chiến thuật. Điều quan trọng là *cách* nó thất bại — độ chính xác ở cảnh rộng vẫn đạt 1,000. Bộ phát hiện không ảo giác logo, nó đơn giản là không nhìn thấy những logo nhỏ, xa. Đó là một thiên lệch dự đoán được, một chiều: bất kỳ ước tính thời lượng nào dựa trên bộ phát hiện này sẽ đếm thiếu mức độ xuất hiện cụ thể trong các đoạn chủ yếu là cảnh rộng — điều này quan trọng vì các bản phát sóng trận đấu đầy đủ chứa nhiều cảnh rộng hơn rất nhiều so với các clip highlight mà bộ dữ liệu này được lấy từ."

---

## SLIDE 8 — Logo Visibility Score: a worked example / Điểm Khả năng Hiển thị Logo: ví dụ minh họa (100 s)

🇬🇧 **English:**

> "This is where detections stop being just boxes and start becoming a visibility number. The formula on screen —
>
> **V_i = clip₍₀,₁₎( √(A_i / A_f) × exp[ −d_i² / (0.3W)² ] × c_i )**
>
> — has three multiplied terms, and I want to be precise about what each one is:
>
> - **√(A_i / A_f) — the size term.** A_i is the predicted box's area in pixels, A_f is the whole frame's area. So this fraction is literally 'what share of the screen does the logo occupy' — and the square root is there deliberately, to compress that share so one very large, close-up mark doesn't completely dominate the score on its own.
> - **exp[ −d_i² / (0.3W)² ] — the position term.** d_i is the straight-line distance, in pixels, from the box's centre to the frame's centre; W is the frame width. This is a Gaussian — a bell curve centred on the middle of the screen — so a logo dead-centre scores close to 1, and the score falls off smoothly the further it drifts toward the edge. The 0.3W is the width of that bell curve: how forgiving it is before position starts really hurting the score.
> - **c_i — the confidence term.** This is just the detector's own output confidence for that box — how sure the model is that this is really a KLG mark and not something else.
>
> Multiplying all three, rather than adding them, is itself a choice: it means a low score on *any one* term drags the whole thing down — a large, dead-centre, low-confidence detection still scores badly.
>
> Now the worked example, using a real detection from the held-out test set: a KLG logo, match M_CAS, 21 seconds into the clip. The model was confident — 0.925 — and accurate — IoU 0.85 against the ground-truth box, a genuine true positive. But because the box sits 578 pixels off-centre in a 1920-pixel-wide medium shot, the position term collapses to 0.365, and the size term — because the box is only 0.2% of the frame — caps out around 0.046 before you even multiply anything else in. The final score: **V_i = 0.016**. Low, even though the detection itself was excellent.
>
> That's the point of showing this example rather than just the formula: a low visibility score does not mean the detector failed. It means the *appearance* was small and off-centre — which is exactly the kind of distinction a club needs, and exactly why every term stays traceable back to the source frame instead of being collapsed into one opaque number."

🇻🇳 **Tiếng Việt:**

> "Đây là nơi các phát hiện không còn chỉ là khung bao mà bắt đầu trở thành một con số khả năng hiển thị. Công thức trên màn hình —
>
> **V_i = clip₍₀,₁₎( √(A_i / A_f) × exp[ −d_i² / (0.3W)² ] × c_i )**
>
> — có ba thành phần nhân với nhau, và tôi muốn giải thích chính xác từng thành phần:
>
> - **√(A_i / A_f) — thành phần kích thước.** A_i là diện tích khung bao dự đoán tính bằng pixel, A_f là diện tích toàn bộ khung hình. Vậy phân số này nghĩa đen là 'logo chiếm bao nhiêu phần trăm màn hình' — và căn bậc hai ở đây là có chủ đích, để nén tỷ lệ đó sao cho một logo rất lớn, cận cảnh không hoàn toàn chi phối điểm số.
> - **exp[ −d_i² / (0.3W)² ] — thành phần vị trí.** d_i là khoảng cách đường thẳng, tính bằng pixel, từ tâm khung bao đến tâm khung hình; W là chiều rộng khung hình. Đây là một hàm Gaussian — đường cong hình chuông tâm ở giữa màn hình — nên logo ở chính giữa đạt điểm gần 1, và điểm giảm dần mượt mà khi nó dịch xa về phía rìa. 0,3W là độ rộng của đường cong hình chuông đó: mức độ khoan dung trước khi vị trí bắt đầu thực sự ảnh hưởng đến điểm.
> - **c_i — thành phần độ tin cậy.** Đây đơn giản là độ tin cậy đầu ra của bộ phát hiện cho khung bao đó — mô hình chắc chắn đến mức nào rằng đây thực sự là logo KLG chứ không phải thứ khác.
>
> Nhân tất cả ba thành phần, thay vì cộng, bản thân nó là một lựa chọn: nghĩa là điểm thấp ở *bất kỳ thành phần nào* kéo toàn bộ điểm xuống — một phát hiện lớn, ở chính giữa, nhưng độ tin cậy thấp vẫn đạt điểm kém.
>
> Bây giờ là ví dụ minh họa, sử dụng một phát hiện thực từ tập kiểm tra: một logo KLG, trận M_CAS, giây thứ 21 trong clip. Mô hình khá tin cậy — 0,925 — và chính xác — IoU 0,85 so với khung bao gốc, một dương tính thật chính hiệu. Nhưng vì khung bao nằm cách tâm 578 pixel trong cảnh trung bình 1920 pixel chiều rộng, thành phần vị trí sụp xuống 0,365, và thành phần kích thước — vì khung bao chỉ chiếm 0,2% khung hình — đạt tối đa khoảng 0,046 trước khi bạn nhân bất kỳ thứ gì khác vào. Điểm cuối cùng: **V_i = 0,016**. Thấp, mặc dù bản thân phát hiện rất xuất sắc.
>
> Đó là lý do tôi cho thấy ví dụ này thay vì chỉ công thức: điểm khả năng hiển thị thấp không có nghĩa là bộ phát hiện đã thất bại. Nó có nghĩa là *sự xuất hiện* nhỏ và lệch tâm — đó chính xác là loại phân biệt mà một câu lạc bộ cần, và chính xác là lý do tại sao mỗi thành phần vẫn truy nguyên được về khung hình nguồn thay vì bị gộp thành một con số mờ đục."

---

## SLIDE 9 — Formula provenance & evaluation status / Nguồn gốc công thức & trạng thái đánh giá (100 s)

🇬🇧 **English:**

> "Two questions follow immediately from that worked example: where did this formula come from, and how much should anyone trust it? This slide answers both directly, because I'd rather raise it myself than have it raised for me.
>
> **Where it comes from.** Three sources in the literature name the same broad ingredients. ExposureEngine, a 2025 paper, derives on-screen coverage and exposure duration directly from detector geometry — the same starting point I use. A GumGum sponsor-valuation patent names size, clarity, duration and position as candidate quality factors. And Nielsen's own public description of their vBrand product names the same three: duration, size, image clarity.
>
> What none of those three sources does is publish the actual combination rule — the functional form. Nobody tells you *how* to turn size, position and confidence into one number. So this equation is **literature-informed, not literature-derived**: the choice of inputs comes from the literature, but the square root, the Gaussian, the 0.3W scale, and the decision to multiply rather than add — those are mine, designed and disclosed, not copied from a validated source, because no validated source publishing this exists yet.
>
> **How I evaluate it.** I split every component into three categories by how much evidence actually backs it. Box area and centre distance are **measured geometry** — read directly off the prediction, the most reliable part of the whole score. Confidence is a **model-derived proxy** — it tells you the detector's certainty, not whether a human being could actually read the logo; those are not the same thing. And the transformations themselves — square root, Gaussian, the 0.3W constant, multiplication — are **researcher-defined design choices**: reasonable, documented, but not fitted to any data and not yet checked against a human judgement.
>
> So the honest status, in one line: **transparent and fully reproducible, but not yet a validated measure of visibility quality.** Three things stand between it and that status — component-removal analysis, to check whether each term is actually pulling its weight; comparison against manually timed footage, at several sampling rates; and a proper two-rater human readability study. That's not a hand-wave — it's the top item on the future-work priority list in Chapter 6, precisely because it's the biggest evidentiary gap left in the whole dissertation."

🇻🇳 **Tiếng Việt:**

> "Hai câu hỏi nảy sinh ngay lập tức từ ví dụ minh họa đó: công thức này đến từ đâu, và nên tin tưởng nó đến mức nào? Slide này trả lời trực tiếp cả hai, vì tôi muốn tự nêu vấn đề thay vì để người khác nêu.
>
> **Nguồn gốc.** Ba nguồn trong tài liệu nêu cùng các thành phần chung. ExposureEngine, một bài báo năm 2025, tính toán độ phủ trên màn hình và thời lượng xuất hiện trực tiếp từ hình học bộ phát hiện — cùng điểm xuất phát tôi sử dụng. Một bằng sáng chế định giá tài trợ của GumGum nêu kích thước, độ rõ nét, thời lượng và vị trí là các yếu tố chất lượng ứng viên. Và bản mô tả công khai của Nielsen về sản phẩm vBrand nêu cùng ba yếu tố: thời lượng, kích thước, độ rõ hình ảnh.
>
> Điều mà không nguồn nào trong ba nguồn đó làm là công bố quy tắc kết hợp thực tế — dạng hàm. Không ai cho bạn biết *cách* biến kích thước, vị trí và độ tin cậy thành một con số. Vì vậy phương trình này **được thông tin bởi tài liệu, không phải được dẫn xuất từ tài liệu**: việc chọn đầu vào đến từ tài liệu, nhưng căn bậc hai, hàm Gaussian, tỷ lệ 0,3W, và quyết định nhân thay vì cộng — đó là của tôi, được thiết kế và công khai, không phải sao chép từ nguồn đã được xác thực, vì chưa có nguồn xác thực nào công bố điều này.
>
> **Cách tôi đánh giá.** Tôi phân loại mỗi thành phần thành ba mức theo mức độ bằng chứng thực sự hỗ trợ. Diện tích khung bao và khoảng cách tâm là **hình học đo lường được** — đọc trực tiếp từ dự đoán, phần đáng tin cậy nhất của toàn bộ điểm số. Độ tin cậy là **đại diện từ mô hình** — nó cho biết mức độ chắc chắn của bộ phát hiện, không phải liệu con người có thực sự đọc được logo hay không; đó là hai điều khác nhau. Và bản thân các phép biến đổi — căn bậc hai, Gaussian, hằng số 0,3W, phép nhân — là **lựa chọn thiết kế của nhà nghiên cứu**: hợp lý, được ghi nhận, nhưng chưa được khớp với bất kỳ dữ liệu nào và chưa được kiểm chứng so với đánh giá của con người.
>
> Vậy trạng thái trung thực, trong một câu: **minh bạch và hoàn toàn tái tạo được, nhưng chưa phải là thước đo đã được xác thực về chất lượng khả năng hiển thị.** Ba điều cần làm trước khi đạt được trạng thái đó — phân tích loại bỏ thành phần, để kiểm tra xem mỗi thành phần có thực sự đóng góp hay không; so sánh với hình ảnh được tính giờ thủ công, ở nhiều tốc độ lấy mẫu; và một nghiên cứu đọc hiểu của con người với hai người đánh giá đúng chuẩn. Đó không phải là nói suông — đó là mục ưu tiên hàng đầu trong danh sách công việc tương lai ở Chương 6, chính xác vì đó là khoảng trống bằng chứng lớn nhất còn lại trong toàn bộ luận văn."

**Sources — read these before the meeting if there's time / Nguồn tham khảo — đọc trước buổi họp nếu có thời gian:**
- ExposureEngine (on-screen coverage & duration from geometry / độ phủ trên màn hình & thời lượng từ hình học) — Sarkhoosh et al., 2025 — [arxiv.org/abs/2510.04739](https://arxiv.org/abs/2510.04739)
- GumGum Sports automated sponsor-valuation patent / Bằng sáng chế định giá tài trợ tự động GumGum Sports — Katz, Carter & Kim, 2024, US 12,124,509 B2 — [patents.google.com/patent/US12124509B2](https://patents.google.com/patent/US12124509B2/en)
- Nielsen vBrand acquisition / product description / Mua lại / mô tả sản phẩm Nielsen vBrand — [nielsen.com/news-center/2017/…vbrand](https://www.nielsen.com/news-center/2017/nielsen-acquires-artificial-intelligence-powered-sports-marketing-startup-vbrand/)

**What the Logo Visibility Score becomes over time (in case it's asked, not on the slide):**

🇬🇧 Individual V_i values are grouped into continuous segments per brand; each segment gets a duration weight (0.5× under 1 s, 1.0× from 1–5 s, 1.2× above 5 s) and contributes `Q = Σ (mean segment visibility) × (duration weight) × (segment length)`. Q is reported alongside raw on-screen seconds, never alone — same "prototype, not validated" caveat applies to the weights and the gap-tolerance rule used to build segments.

🇻🇳 *Các giá trị V_i riêng lẻ được nhóm thành các đoạn liên tục theo thương hiệu; mỗi đoạn nhận trọng số thời lượng (0,5× dưới 1 giây, 1,0× từ 1–5 giây, 1,2× trên 5 giây) và đóng góp `Q = Σ (khả năng hiển thị trung bình đoạn) × (trọng số thời lượng) × (độ dài đoạn)`. Q được báo cáo cùng với số giây xuất hiện trên màn hình thô, không bao giờ đứng một mình — cùng lưu ý "nguyên mẫu, chưa xác thực" áp dụng cho các trọng số và quy tắc dung sai khoảng cách dùng để xây dựng các đoạn.*

---

## SLIDE 10 — Thank you / Cảm ơn (10 s)

🇬🇧 **English:**

> "That's the walkthrough — detection is strong and honestly bounded, the visibility layer is implemented and traceable but explicitly not yet validated. Happy to take questions."

🇻🇳 **Tiếng Việt:**

> "Đó là toàn bộ bài trình bày — phát hiện mạnh mẽ và được giới hạn trung thực, lớp khả năng hiển thị đã được triển khai và truy nguyên được nhưng rõ ràng chưa được xác thực. Sẵn sàng nhận câu hỏi."

---

## Extended Q&A / defense preparation | Chuẩn bị Hỏi đáp mở rộng / bảo vệ

Grouped by theme so you can find the right answer fast if the discussion jumps around.

*Được nhóm theo chủ đề để bạn có thể tìm câu trả lời phù hợp nhanh chóng nếu cuộc thảo luận chuyển hướng.*

---

### Methodology & the leakage result | Phương pháp luận & kết quả rò rỉ

**Q: "How confident are you that match-disjoint splitting is enough — could there still be leakage?"**
**H: "Bạn tự tin đến mức nào rằng phân chia theo trận đấu là đủ — liệu vẫn có thể rò rỉ không?"**

🇬🇧
> "It removes the failure mode I could actually measure — 51 of 56 validation frames sharing a training frame within two seconds. I can't rule out subtler leakage, like recurring camera rigs or broadcast graphics across matches, but the 6.5-point drop between familiar and unseen material is the direct evidence that the leakage I removed was real and large."

🇻🇳
> "Nó loại bỏ chế độ lỗi mà tôi thực sự có thể đo được — 51 trong 56 khung hình xác thực chia sẻ một khung hình huấn luyện trong vòng hai giây. Tôi không thể loại trừ rò rỉ tinh vi hơn, như các bộ camera lặp lại hoặc đồ họa phát sóng giữa các trận, nhưng khoảng cách 6,5 điểm giữa dữ liệu quen thuộc và chưa từng thấy là bằng chứng trực tiếp rằng rò rỉ tôi đã loại bỏ là thực và lớn."

---

**Q: "Why only three test matches?"**
**H: "Tại sao chỉ có ba trận kiểm tra?"**

🇬🇧
> "Data availability and annotation cost — one researcher, mostly manual annotation. It's flagged explicitly as external validity threat in Chapter 6, and 'add independent matches' is priority #2 in the future-work list, specifically to grow the six-box wide-shot subset, which is the thinnest part of the evidence right now."

🇻🇳
> "Hạn chế về dữ liệu và chi phí gán nhãn — một nhà nghiên cứu, gán nhãn chủ yếu thủ công. Điều này được nêu rõ ràng là mối đe dọa hiệu lực bên ngoài trong Chương 6, và 'thêm các trận đấu độc lập' là ưu tiên số 2 trong danh sách công việc tương lai, cụ thể là để mở rộng tập con sáu khung bao cảnh rộng, vốn là phần mỏng nhất của bằng chứng hiện tại."

---

### Detector comparison | So sánh bộ phát hiện

**Q: "Is RF-DETR just better because of DINOv2 pre-training, not the architecture?"**
**H: "RF-DETR có phải chỉ tốt hơn vì tiền huấn luyện DINOv2, không phải kiến trúc?"**

🇬🇧
> "Possibly, and I say so directly — pre-training, capacity and augmentation are not controlled, only images, split, resolution and scoring code are. What the result does support is a *practical implementer's choice* for this task; it doesn't support a general architectural claim. A matched efficiency benchmark — latency, memory, on the same hardware — is priority #3 in future work, because right now only RF-DETR's runtime is actually measured."

🇻🇳
> "Có thể, và tôi nói thẳng điều đó — tiền huấn luyện, dung lượng và tăng cường dữ liệu không được kiểm soát, chỉ ảnh, phép phân chia, độ phân giải và mã chấm điểm là giống nhau. Điều kết quả hỗ trợ là *lựa chọn thực tế của người triển khai* cho nhiệm vụ này; nó không hỗ trợ một tuyên bố kiến trúc chung. Một benchmark hiệu suất so sánh tương đương — độ trễ, bộ nhớ, trên cùng phần cứng — là ưu tiên số 3 trong công việc tương lai, vì hiện tại chỉ có thời gian chạy của RF-DETR được đo thực tế."

---

**Q: "Why 896px input instead of YOLO's default 640?"**
**H: "Tại sao đầu vào 896px thay vì mặc định 640 của YOLO?"**

🇬🇧
> "To keep the comparison fair to both systems rather than fair to YOLO's own default — small sponsor marks lose the most resolution at 640. Appendix B in the dissertation shows the controlled resolution sweep (512→768→896) that motivated this."

🇻🇳
> "Để giữ so sánh công bằng cho cả hai hệ thống thay vì chỉ công bằng với mặc định riêng của YOLO — các logo nhà tài trợ nhỏ mất nhiều độ phân giải nhất ở 640. Phụ lục B trong luận văn cho thấy bài kiểm tra quét độ phân giải có kiểm soát (512→768→896) đã thúc đẩy quyết định này."

---

### The Logo Visibility Score | Điểm Khả năng Hiển thị Logo

**Q: "Doesn't an unvalidated formula undermine the whole visibility contribution?"**
**H: "Một công thức chưa được xác thực có làm suy yếu toàn bộ đóng góp về khả năng hiển thị không?"**

🇬🇧
> "Only if I claimed it was validated. I don't — the contribution is the *traceable measurement chain*, not a claim that 0.016 is objectively correct. Every number in that chain — box area, distance, confidence — remains inspectable back to the source frame. The validation study is named as the next required step, not assumed away."

🇻🇳
> "Chỉ nếu tôi tuyên bố nó đã được xác thực. Tôi không — đóng góp là *chuỗi đo lường truy nguyên được*, không phải tuyên bố rằng 0,016 là đúng khách quan. Mọi con số trong chuỗi đó — diện tích khung bao, khoảng cách, độ tin cậy — đều có thể kiểm tra ngược lại khung hình nguồn. Nghiên cứu xác thực được nêu là bước tiếp theo cần thiết, không phải bỏ qua."

---

**Q: "What would change if you added blur or occlusion to the score?"**
**H: "Điều gì sẽ thay đổi nếu bạn thêm độ mờ hoặc che khuất vào điểm số?"**

🇬🇧
> "Nothing yet — deliberately. Chapter 2 lists them as relevant but *unsupported constructs*: I don't have a validated way to estimate visible-area loss under occlusion or human-perceived blur from a horizontal box alone. Adding them without validation would make the score look more sophisticated without making it more true — so they're future work, not current inputs."

🇻🇳
> "Chưa có gì — một cách có chủ đích. Chương 2 liệt kê chúng là liên quan nhưng là *cấu trúc chưa được hỗ trợ*: tôi không có cách đã được xác thực để ước tính tổn thất diện tích nhìn thấy do che khuất hoặc độ mờ mà con người nhận thức chỉ từ một khung bao ngang. Thêm chúng mà không xác thực sẽ làm điểm số trông tinh vi hơn mà không làm nó đúng hơn — nên chúng là công việc tương lai, không phải đầu vào hiện tại."

---

**Q: "Is there any EMV / monetary output?"**
**H: "Có đầu ra EMV / tiền tệ nào không?"**

🇬🇧
> "Only as an explicitly optional, clearly-labelled scenario layer — never a validated output. Chapter 2 shows the illustrative EMV calculation and states its reliability can never exceed the reliability of the duration, quality weights, audience estimate and media rate underneath it. LogoLens reports traceable exposure as the primary output; monetisation is kept separate on purpose."

🇻🇳
> "Chỉ như một lớp kịch bản tùy chọn, được gắn nhãn rõ ràng — không bao giờ là đầu ra đã xác thực. Chương 2 trình bày phép tính EMV minh họa và nêu rõ độ tin cậy của nó không bao giờ có thể vượt quá độ tin cậy của thời lượng, trọng số chất lượng, ước tính khán giả và tỷ lệ truyền thông bên dưới. LogoLens báo cáo mức độ xuất hiện truy nguyên được là đầu ra chính; tiền tệ hóa được giữ riêng biệt có mục đích."

---

### Generalisation & future work | Tổng quát hóa & công việc tương lai

**Q: "Would this work for football, or a different club?"**
**H: "Điều này có hoạt động cho bóng đá, hoặc câu lạc bộ khác không?"**

🇬🇧
> "As a hypothesis, plausibly — the small-object constraint and the wide-shot recall problem both follow from shirt-mounted sponsorship and camera distance generally, not from rugby league specifically. But it's untested; extending to a new club currently means new manual annotation, which is exactly why the regulation-guided auto-annotation idea is in future work — same-league kit regulations fix where a sponsor mark sits relative to seams and panels, so a reference kit's annotations could seed candidate boxes for a new club's kit, cutting the annotation cost of testing that hypothesis."

🇻🇳
> "Như một giả thuyết, có khả năng — hạn chế đối tượng nhỏ và vấn đề thu hồi cảnh rộng đều xuất phát từ tài trợ trên áo và khoảng cách camera nói chung, không đặc thù cho bóng bầu dục liên minh. Nhưng chưa được kiểm chứng; mở rộng sang câu lạc bộ mới hiện tại có nghĩa là gán nhãn thủ công mới, đó chính xác là lý do tại sao ý tưởng gán nhãn tự động dựa trên quy định nằm trong công việc tương lai — quy định trang phục cùng giải đấu cố định vị trí logo nhà tài trợ so với đường may và tấm vải, nên các nhãn từ bộ trang phục tham chiếu có thể tạo khung bao ứng viên cho bộ trang phục của câu lạc bộ mới, giảm chi phí gán nhãn để kiểm chứng giả thuyết đó."

---

**Q: "What's the single most important next step?"**
**H: "Bước tiếp theo quan trọng nhất là gì?"**

🇬🇧
> "Manual-timing and readability validation of the visibility layer — everything else in future work is either strengthening evidence that's already solid (more test matches, a matched latency benchmark) or is downstream of this one. Until duration and the score are checked against a human reference, the detection result stands on its own but the visibility framework stays a prototype by design."

🇻🇳
> "Xác thực tính giờ thủ công và khả năng đọc của lớp khả năng hiển thị — mọi thứ khác trong công việc tương lai hoặc là tăng cường bằng chứng đã vững (thêm trận kiểm tra, benchmark độ trễ tương đương) hoặc là hạ nguồn của bước này. Cho đến khi thời lượng và điểm số được kiểm chứng so với tham chiếu con người, kết quả phát hiện đứng vững một mình nhưng khung khả năng hiển thị vẫn là nguyên mẫu theo thiết kế."

---

*Prepared for: LogoLens WP1 supervisor meeting. Companion to `LogoLens_WP1_Summary.pptx`.*
*Chuẩn bị cho: Buổi họp giảng viên hướng dẫn LogoLens WP1. Tài liệu đi kèm `LogoLens_WP1_Summary.pptx`.*
