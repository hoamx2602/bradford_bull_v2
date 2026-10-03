# LogoLens — Literature Review Summary, mapped to WP1
### (Tóm tắt Literature Review của LogoLens, đối chiếu theo WP1)

**Prepared for a supervisor meeting. Bilingual: English first, Vietnamese in parentheses.**
**(Chuẩn bị cho buổi gặp giáo sư. Song ngữ: tiếng Anh trước, tiếng Việt trong ngoặc đơn ngay sau.)**

---

## The dissertation in one paragraph
### (Tóm tắt luận văn trong một đoạn)

LogoLens is a closed-set multi-logo detection system for sponsor marks in rugby broadcast footage, paired with a transparent prototype framework that turns detections into visibility evidence — screen size, position, duration and a composite Logo Visibility Score. (LogoLens là một hệ thống phát hiện đa logo dạng closed-set cho các nhãn hiệu tài trợ trong video phát sóng bóng bầu dục, đi kèm một khung prototype minh bạch để biến các detection thành bằng chứng về độ hiển thị — kích thước trên màn hình, vị trí, thời lượng và một điểm số tổng hợp Logo Visibility Score.) The literature review (Chapter 2) exists to justify every one of these pieces before they are built and tested. (Chương Literature Review — Chương 2 — tồn tại để biện minh cho từng thành phần này trước khi chúng được xây dựng và kiểm chứng.)

---

## WP1 Aim & Rationale — where they come from in the literature
### (WP1 Aim & Rationale — bắt nguồn từ đâu trong literature review)

**Aim:** develop the core computer-vision system that detects sponsor logos *and* measures their visibility quality. (**Aim:** xây dựng hệ thống thị giác máy tính cốt lõi vừa phát hiện logo tài trợ, vừa đo chất lượng hiển thị của chúng.)

Section 2.1 of the literature review draws the line the whole dissertation is built on: broadcast visibility is only the **exposure** layer — it proves a mark *could* be seen, not that it *was* attended to, remembered, or that it changed a viewer's attitude. (Mục 2.1 của literature review vạch ra ranh giới mà cả luận văn dựa vào: độ hiển thị trên sóng chỉ là lớp **exposure** — nó chứng minh logo *có thể* được nhìn thấy, chứ không chứng minh nó *đã được* chú ý, ghi nhớ, hay làm thay đổi thái độ người xem.) That is exactly why the WP1 rationale says detection is "only the first step" — the literature is what draws that boundary and justifies going further, into size, duration and quality. (Đó chính xác là lý do rationale của WP1 nói phát hiện logo "chỉ là bước đầu tiên" — literature review là nơi vạch ra ranh giới đó và biện minh cho việc đi xa hơn, vào kích thước, thời lượng và chất lượng.)

---

## Activity-by-activity: what the literature review says
### (Từng activity: literature review nói gì)

### 1. Train and evaluate logo detection models
### (Huấn luyện và đánh giá các mô hình phát hiện logo)

Section 2.2 frames logo detection as a **closed-set** problem — the sponsor roster is known and fixed for a season — which permits specialist fine-tuning but creates a hard domain boundary: a new sponsor or kit needs new data. (Mục 2.2 định hình phát hiện logo là bài toán **closed-set** — danh sách sponsor đã biết và cố định trong một mùa giải — điều này cho phép fine-tune chuyên biệt nhưng tạo ra ranh giới domain cứng: sponsor hay kit mới cần dữ liệu mới.) Section 2.3 then reviews the two candidate detector families in depth: YOLO's single-pass, deployment-oriented lineage versus DETR's transformer-based set-prediction lineage, ending at RF-DETR (DINOv2 backbone + neural architecture search) and YOLO26 (small-target-aware label assignment). (Mục 2.3 sau đó xem xét kỹ hai họ detector ứng viên: dòng YOLO một-lượt hướng triển khai thực tế, so với dòng DETR dựa trên transformer dự đoán theo tập hợp — kết ở RF-DETR (backbone DINOv2 + neural architecture search) và YOLO26 (label assignment nhận biết vật thể nhỏ).) Neither architecture's general reputation is trusted on its own — the review explicitly states that general COCO benchmark rankings cannot substitute for a local, task-specific comparison. (Không có kiến trúc nào được tin dùng chỉ dựa trên danh tiếng chung — review nói rõ rằng thứ hạng benchmark COCO tổng quát không thể thay thế cho một so sánh cục bộ, đặc thù cho tác vụ.)

### 2. Detect multiple logos simultaneously
### (Phát hiện nhiều logo cùng lúc)

Liao et al. (2017) is the key source here: their study of multiple logos in sports video identifies layout variation, deformation, motion blur and partial occlusion as the specific difficulties of this exact setting — logos on moving fabric, not static boards. (Liao et al. (2017) là nguồn quan trọng nhất ở đây: nghiên cứu của họ về nhiều logo trong video thể thao chỉ ra biến thiên bố cục, biến dạng, mờ do chuyển động và che khuất một phần là những khó khăn đặc thù của chính bối cảnh này — logo trên vải chuyển động, không phải trên biển quảng cáo tĩnh.) This is why a horizontal-box, multi-instance detector — rather than a single-logo classifier — was the necessary design choice. (Đây là lý do vì sao một detector đa-instance với box ngang — chứ không phải bộ phân loại một-logo — là lựa chọn thiết kế bắt buộc.)

### 3. Analyse logo size and screen coverage
### (Phân tích kích thước logo và diện tích chiếm trên màn hình)

Section 2.2 makes small-object geometry the central visual constraint of the whole project: the median annotated mark is only 70×48 pixels in the source broadcast, and shrinks further — to roughly 19×23 pixels — once resized to the model's input resolution. (Mục 2.2 biến hình học vật thể nhỏ thành ràng buộc thị giác trung tâm của cả dự án: logo trung vị chỉ 70×48 pixel trong ảnh gốc, và co lại còn khoảng 19×23 pixel sau khi resize về độ phân giải đầu vào của model.) The review explains why this matters technically: at that scale, a few pixels of box displacement changes IoU substantially, so mAP@0.50 and the stricter mAP@0.75 measure meaningfully different capabilities — which is precisely the justification for reporting both. (Review giải thích vì sao điều này quan trọng về mặt kỹ thuật: ở quy mô đó, lệch vài pixel làm IoU thay đổi đáng kể, nên mAP@0.50 và mAP@0.75 khắt khe hơn đo hai năng lực khác nhau có ý nghĩa — đây chính là lý do báo cáo cả hai.)

### 4. Measure visibility duration
### (Đo thời lượng hiển thị)

Section 2.4 identifies duration as a **temporal aggregation problem**, not a simple counting problem: sampling at a fixed rate means true appearances can be fragmented by single detector misses. (Mục 2.4 xác định thời lượng là một **bài toán tổng hợp theo thời gian**, không phải bài toán đếm đơn giản: lấy mẫu ở tốc độ cố định khiến các lần xuất hiện thật có thể bị gãy vụn bởi những lần miss đơn lẻ của detector.) The review cites ByteTrack (Zhang et al., 2022) for associating detections across frames, and explains that gap-tolerance and minimum-duration rules are needed to stop one miss from fragmenting a real segment — while warning that every such rule trades under-counting against over-counting and needs comparison against manually timed footage before being trusted. (Review dẫn ByteTrack (Zhang et al., 2022) để liên kết detection qua các khung hình, và giải thích rằng cần có gap-tolerance và ngưỡng thời lượng tối thiểu để một lần miss không làm gãy một đoạn xuất hiện thật — đồng thời cảnh báo rằng mỗi quy tắc như vậy đánh đổi giữa đếm thiếu và đếm thừa, và cần đối chiếu với thời gian đo thủ công trước khi được tin dùng.)

### 5. Measure occlusion levels
### (Đo mức độ bị che khuất)

Occlusion appears twice in the review: as one of Liao et al.'s (2017) four core difficulties of sports-video logo detection, and again in Section 2.4 as an **unsupported construct** — a horizontal bounding box contains no explicit estimate of how much of a rotated or folded logo remains visible. (Occlusion xuất hiện hai lần trong review: là một trong bốn khó khăn cốt lõi của phát hiện logo trong video thể thao theo Liao et al. (2017), và một lần nữa ở Mục 2.4 như một **cấu trúc chưa được hỗ trợ** — một box ngang không chứa ước lượng tường minh nào về việc bao nhiêu phần của một logo bị xoay hoặc gấp vẫn còn nhìn thấy được.) This honesty in the review is what later justifies treating occlusion qualitatively (a three-level scale, illustrative examples) rather than claiming a quantified, validated occlusion metric. (Sự thẳng thắn này trong review chính là cơ sở sau này để xử lý occlusion theo hướng định tính (thang 3 mức, ví dụ minh hoạ) thay vì tuyên bố một chỉ số occlusion đã được định lượng và kiểm chứng.)

### 6. Assess image quality and readability
### (Đánh giá chất lượng hình ảnh và khả năng đọc được)

Section 2.4 draws a sharp, deliberate line: detector confidence expresses **model certainty under the trained classifier**, not human readability — the two are not interchangeable, even though confidence is the only quality-adjacent signal directly available from the detector. (Mục 2.4 vạch một ranh giới rõ ràng, có chủ đích: confidence của detector thể hiện **độ chắc chắn của mô hình theo bộ phân loại đã huấn luyện**, không phải khả năng đọc được của con người — hai thứ này không thể thay thế cho nhau, dù confidence là tín hiệu duy nhất liên quan đến chất lượng có sẵn trực tiếp từ detector.) The review also reports that blur and contrast were considered as measurable proxies but are sensitive to crop size and background, which is why they are named as relevant-but-unmeasured rather than built into the current score. (Review cũng ghi nhận rằng độ mờ và độ tương phản từng được cân nhắc làm proxy đo được, nhưng nhạy với kích thước crop và nền ảnh, đây là lý do chúng được xem là liên quan-nhưng-chưa-đo-được thay vì được đưa thẳng vào điểm số hiện tại.)

### 7. Develop a Logo Visibility Score
### (Xây dựng Logo Visibility Score)

This is the activity the literature review supports most explicitly. Section 2.4 reviews three real sources that name plausible quality components — ExposureEngine (Sarkhoosh et al., 2025), a GumGum sponsor-valuation patent (Katz et al., 2024), and Nielsen's public vBrand description — all naming size, position, duration and clarity as relevant factors. (Đây là activity được literature review hỗ trợ tường minh nhất. Mục 2.4 xem xét ba nguồn thực tế nêu ra các thành phần chất lượng khả dĩ — ExposureEngine (Sarkhoosh et al., 2025), một bằng sáng chế định giá sponsor của GumGum (Katz et al., 2024), và mô tả công khai vBrand của Nielsen — tất cả đều nêu kích thước, vị trí, thời lượng và độ rõ là các yếu tố liên quan.) But the review is explicit that **none of these sources specifies or validates the actual functional form** — so the review does not hand LogoLens a formula, it hands it a justified *list of inputs* and a warning that the combination rule must be built and disclosed as a heuristic, not presented as an adopted standard. (Nhưng review nói rõ **không nguồn nào trong số đó quy định hay kiểm chứng công thức thực tế** — vậy nên review không trao sẵn công thức cho LogoLens, mà trao một *danh sách đầu vào* có căn cứ, cùng lời cảnh báo rằng quy tắc kết hợp phải được xây dựng và công bố như một heuristic, chứ không được trình bày như một chuẩn đã được công nhận.) Section 2.4 also introduces Equivalent Media Value and states plainly that its reliability can never exceed the reliability of the duration, quality weights, audience estimate and media rate beneath it — which is why monetary value is kept as an optional, clearly-separate layer, never the main output. (Mục 2.4 cũng giới thiệu Equivalent Media Value và nói thẳng rằng độ tin cậy của nó không bao giờ vượt quá độ tin cậy của thời lượng, trọng số chất lượng, ước lượng khán giả và đơn giá truyền thông bên dưới nó — đây là lý do giá trị tiền tệ được giữ như một lớp tuỳ chọn, tách biệt rõ ràng, không bao giờ là output chính.)

---

## The research gap the review lands on (Section 2.5)
### (Khoảng trống nghiên cứu mà review chỉ ra — Mục 2.5)

The literature establishes that exposure is commercially relevant but distinct from attention and value; that sports-logo detection is affected by scale, motion and deformation; that YOLO and DETR offer different transfer strategies; and that temporal aggregation needs manual validation. (Literature review xác lập rằng exposure có liên quan về mặt thương mại nhưng khác với attention và giá trị; rằng phát hiện logo thể thao bị ảnh hưởng bởi tỉ lệ, chuyển động và biến dạng; rằng YOLO và DETR mang lại các chiến lược transfer khác nhau; và rằng tổng hợp theo thời gian cần được kiểm chứng thủ công.) What it does **not** find is a reproducible, club-specific study that combines match-disjoint multi-logo evaluation, a current YOLO26-vs-RF-DETR comparison, condition-specific failure analysis, and traceable visibility aggregation on smaller-club footage — that gap is exactly what all seven WP1 activities, taken together, were designed to fill. (Điều nó **không** tìm thấy là một nghiên cứu có thể tái lập, đặc thù cho một club, kết hợp đánh giá đa logo theo trận-tách-biệt, một so sánh YOLO26-với-RF-DETR hiện đại, phân tích lỗi theo điều kiện cụ thể, và tổng hợp độ hiển thị có thể truy vết trên footage của một club nhỏ hơn — khoảng trống đó chính là điều mà cả bảy activity của WP1, gộp lại, được thiết kế để lấp đầy.)

---

## WP1 Outputs — how the review supports each one
### (WP1 Outputs — literature review hỗ trợ từng cái ra sao)

- **Logo detection engine** — justified by the closed-set framing and the YOLO26/RF-DETR architecture review (§2.2–2.3). (**Logo detection engine** — được biện minh bởi khung closed-set và phần review kiến trúc YOLO26/RF-DETR — Mục 2.2–2.3.)
- **Visibility scoring framework** — justified by the three quality-factor sources and the explicit measured/proxy/researcher-defined evidence categories (§2.4). (**Visibility scoring framework** — được biện minh bởi ba nguồn về yếu tố chất lượng và các phạm trù bằng chứng đo được/proxy/do người nghiên cứu định nghĩa được nêu tường minh — Mục 2.4.)
- **Performance evaluation reports** — justified by the leakage warning for sports video (Deliège et al., 2021, cited in §2.2) that motivates match-disjoint, condition-stratified reporting rather than a single aggregate number. (**Performance evaluation reports** — được biện minh bởi cảnh báo về leakage trong video thể thao (Deliège et al., 2021, trích trong Mục 2.2) — lý do cho việc báo cáo theo trận-tách-biệt, phân tầng theo điều kiện, thay vì chỉ một con số tổng hợp.)

---

*Prepared for a supervisor meeting on the LogoLens dissertation, Work Package 1.*
*(Chuẩn bị cho buổi gặp giáo sư về luận văn LogoLens, Work Package 1.)*
