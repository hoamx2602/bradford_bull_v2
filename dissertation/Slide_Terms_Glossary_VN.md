# Giải thích thuật ngữ / đơn vị trong từng slide — LogoLens WP1 Summary
### (Tiếng Việt — để đọc kèm khi trình bày, phòng giáo sư hỏi bất kỳ con số/khái niệm nào trên slide)

---

## Slide 4 — Dataset & leakage-aware split

- **584 images / 61 test images**: số lượng khung hình (frame) được trích từ video, đã gán nhãn. "Test images" là 61 ảnh **chưa từng xuất hiện trong lúc huấn luyện** — dùng để đánh giá cuối cùng.
- **1,903 annotated boxes**: tổng số bounding box (khung chữ nhật bao quanh 1 logo) đã được người gán nhãn vẽ tay/chỉnh sửa trên toàn bộ 584 ảnh. Một ảnh có thể chứa nhiều box.
- **16 sponsor classes**: 16 nhãn hiệu tài trợ khác nhau mà hệ thống được huấn luyện để nhận diện (đây là bài toán "closed-set" — chỉ nhận diện được đúng 16 nhãn này, không tự nhận ra nhãn mới).
- **15 disjoint match groups**: 15 trận đấu, mỗi trận là một "nhóm" độc lập — không có ảnh nào của cùng 1 trận vừa nằm ở tập train vừa nằm ở tập test.
- **Match-disjoint split / leakage**: "leakage" (rò rỉ dữ liệu) xảy ra khi mô hình vô tình "nhìn thấy" thông tin của tập test ngay trong lúc huấn luyện (ví dụ 2 khung hình cách nhau 2 giây của cùng 1 pha bóng, một cái ở tập train, một cái ở tập test — gần như giống hệt nhau). "Match-disjoint" là cách chia dữ liệu theo **cả trận đấu**, không theo từng khung hình lẻ, để tránh việc đó.
- **mAP@0.50 = 0.998 (familiar) vs 0.933 (unseen)**: xem giải thích mAP ở Slide 6 bên dưới. Điểm quan trọng ở đây: 0.998 là điểm khi đo trên footage **quen thuộc** (mô hình từng thấy trận đó lúc train), còn 0.933 là điểm khi đo trên **trận hoàn toàn mới**. Chênh lệch 6.5 điểm chứng minh việc chia theo trận là cần thiết.

---

## Slide 5 — RF-DETR vs. YOLO26

- **YOLO26-n / s / m**: ba phiên bản của cùng một họ mô hình YOLO26, khác nhau về **kích cỡ** — n (nano, nhỏ nhất), s (small), m (medium, lớn nhất). Mô hình càng lớn thì càng nhiều tham số, tính toán càng nặng, nhưng không chắc chính xác hơn (thấy rõ ở bảng: "m" thua "s" về mAP dù nặng hơn nhiều).
- **RF-DETR Small**: mô hình chính được luận văn chọn dùng — thuộc họ kiến trúc khác (transformer-based, không phải YOLO).
- **Params (2.5M, 10.0M, 21.8M, 31.8M)**: số lượng **tham số** (parameter) của mạng neural — con số càng lớn thì mô hình càng "nặng", càng tốn bộ nhớ/tính toán. Đơn vị M = triệu (million).
- **mAP@0.50 / mAP@0.75 / mAP[.50:.95]**: xem giải thích chi tiết ở Slide 6.
- **F1**: chỉ số kết hợp giữa Precision và Recall (xem Slide 7) thành 1 con số duy nhất — càng gần 1.0 càng tốt.
- **"Same images, match-disjoint split, 896px input"**: nghĩa là cả 4 mô hình được huấn luyện/đánh giá trên **cùng một bộ dữ liệu, cùng cách chia, cùng độ phân giải đầu vào 896×896 pixel** — để so sánh công bằng, không mô hình nào được lợi thế về dữ liệu.
- **"+16.1 points at mAP@0.50"**: nghĩa là RF-DETR Small đạt điểm mAP@0.50 cao hơn YOLO26-s (mô hình YOLO tốt nhất) **16.1 điểm phần trăm** (0.933 − 0.772 = 0.161 → 16.1 điểm).

---

## Slide 6 — Headline result (đúng hình bạn gửi)

### 5 ô số liệu trên cùng

- **mAP@0.50 = 0.933**: "mAP" = mean Average Precision — chỉ số chuẩn trong lĩnh vực object detection, đo mức độ chính xác **tổng thể** của mô hình khi phát hiện + định vị logo, tính trung bình qua toàn bộ 15 lớp sponsor có mặt trong tập test. "@0.50" nghĩa là một dự đoán chỉ được tính là "đúng" nếu box dự đoán **chồng lấp ít nhất 50%** (theo chỉ số IoU — xem Slide 8) với box thật (ground truth). Đây là ngưỡng "dễ" — hay dùng làm chuẩn so sánh chung trong ngành.
- **mAP@0.75 = 0.917**: giống hệt mAP@0.50 nhưng ngưỡng chồng lấp **khắt khe hơn — phải trùng ít nhất 75%**. Điểm này cao gần bằng mAP@0.50 (0.917 so với 0.933) chứng tỏ box dự đoán không chỉ "đúng logo" mà còn **định vị rất chính xác vị trí**, không bị lệch nhiều.
- **mAP[.50:.95] = 0.747**: đây là chuẩn đánh giá của bộ dữ liệu COCO (chuẩn phổ biến nhất ngành) — thay vì chỉ đo ở 1 ngưỡng, nó lấy **trung bình mAP ở 10 ngưỡng chồng lấp khác nhau, từ 0.50 đến 0.95**, nên đây là con số "khắt khe" và toàn diện nhất trong 3 số mAP.
- **F1 = 0.898 @ CONF 0.35**: F1-score đo tại một **ngưỡng tin cậy (confidence) cụ thể = 0.35** — nghĩa là mô hình chỉ "chấp nhận" một dự đoán nếu độ tự tin của nó ≥ 0.35, thấp hơn thì bỏ qua. F1 là trung bình điều hoà giữa Precision (độ chính xác) và Recall (độ đầy đủ) — 0.898 nghĩa là cân bằng rất tốt giữa hai điều này tại ngưỡng đó.
- **19.8 Pred. FPS**: "FPS" = Frames Per Second — tốc độ xử lý, ở đây là **19.8 khung hình mỗi giây** mà mô hình có thể chạy dự đoán (prediction) trên GPU thử nghiệm (RTX 5060 Ti). Con số này **chưa** tính thời gian giải mã video hay hiển thị kết quả — chỉ riêng phần mô hình suy luận (inference).

### Ảnh minh hoạ bên trái

- **Các nhãn trên box (vd "MCP 0.87", "ASC Group 0.88", "KLG 0.90"...)**: mỗi nhãn gồm **tên nhãn hiệu sponsor** (class) + **độ tin cậy (confidence)** mà mô hình gán cho dự đoán đó — số càng gần 1.0 thì mô hình càng "chắc chắn" đây đúng là logo của nhãn hiệu đó. Đây **không phải** là Logo Visibility Score (V_i) ở Slide 8 — chỉ là confidence thô của detector.
- **Bảng tỉ số góc dưới trái ("CAS 40-16 BRA", "1st 6m", "58:21")**: đây là **overlay đồ hoạ gốc của đài truyền hình** (tỉ số trận đấu, thời gian trận) — **không liên quan gì đến hệ thống LogoLens**, chỉ là một phần của khung hình gốc, giữ nguyên để minh hoạ đây là footage thật, chưa qua chỉnh sửa/dàn dựng.
- **Caption "12 of 12 matched logos across 6 sponsor classes, no false positive"**: trong khung hình này có 12 logo thật (ground truth), mô hình phát hiện đúng cả 12 (matched), thuộc 6 nhãn hiệu khác nhau trong số 16 lớp, và **không có false positive** (không đoán bừa ra logo nào không tồn tại).

### Ba ô "check" bên phải

- **Leakage check** ("0.998 familiar → 0.933 unseen, 6.5-point drop"): xem giải thích "leakage" ở Slide 4. "Naive split" = cách chia dữ liệu ngây thơ theo từng ảnh lẻ (không theo trận) — cách này sẽ làm điểm số bị "ảo" cao hơn thực tế.
- **Support check** ("4 of 15 classes carry 7 of 165 test boxes"): "support" = số lượng box thật (ground truth) có trong tập test cho mỗi lớp — đây là để đo xem một lớp có **đủ dữ liệu để tin cậy con số AP của nó hay không**. 4 trong 15 lớp chỉ có tổng cộng 7 box (rất ít) — nên nếu tính điểm trung bình theo kiểu thông thường (0.9335) thì 4 lớp hiếm này vẫn được tính "nặng" ngang các lớp có hàng chục box, làm sai lệch. **"Restricted mean (n≥5)"** = tính lại điểm trung bình mAP nhưng **chỉ giữ các lớp có từ 5 box thật trở lên** — cho ra 0.917, đáng tin hơn.
- **Stability check** ("Per-match mAP@0.50: 0.973/0.934/0.976"): điểm mAP@0.50 tính **riêng cho từng trận** trong 3 trận test — mục đích là chứng minh điểm tổng (0.933) không phải do "ăn may" ở 1 trận dễ rồi kéo điểm trung bình lên, mà cả 3 trận đều cho điểm tương đương nhau.

---

## Slide 7 — Where detection breaks down

- **Recall (0.897 / 0.909 / 0.500)**: "Recall" (độ đầy đủ) = trong số tất cả logo **thật sự có mặt** trong nhóm ảnh đó, mô hình phát hiện được **bao nhiêu phần trăm**. Ví dụ Recall = 0.500 ở nhóm "Wide" nghĩa là mô hình chỉ tìm ra được **một nửa** số logo thật có trong các khung hình quay xa.
- **"Close-up (126 boxes)" / "Medium (33 boxes)" / "Wide (6 boxes)"**: đây là 3 nhóm khung hình được phân loại theo **khoảng cách camera** (cận cảnh / trung cảnh / toàn cảnh), và số trong ngoặc là **tổng số box thật (ground truth)** có trong nhóm đó — dùng để biết mẫu đủ lớn hay không (nhóm "Wide" chỉ có 6 box, rất ít, nên số Recall = 0.500 cần được đọc cẩn thận).
- **Precision**: khác với Recall — Precision đo trong số **tất cả những gì mô hình đã đoán là logo**, có bao nhiêu phần trăm đoán đúng thật. Precision cao mà Recall thấp (như ở nhóm Wide) nghĩa là: mô hình **không đoán bừa**, nhưng lại **bỏ sót** nhiều logo thật.

---

## Slide 8 — Logo Visibility Score, ví dụ tính tay

Công thức: **Vᵢ = clip₍₀,₁₎( √(Aᵢ/A_f) × exp[−dᵢ²/(0.3W)²] × cᵢ )**

- **Aᵢ**: diện tích (tính bằng pixel²) của **box dự đoán** cho logo đó — chiều rộng × chiều cao của box.
- **A_f**: diện tích của **cả khung hình** (frame) — chiều rộng × chiều cao của toàn bộ ảnh.
- **Aᵢ / A_f**: tỉ lệ logo chiếm **bao nhiêu phần trăm diện tích màn hình** — logo càng lớn trên màn hình thì tỉ lệ này càng cao.
- **√ (căn bậc hai)**: được áp lên tỉ lệ diện tích để **"nén" bớt** ảnh hưởng của kích thước — tránh việc một logo cực lớn (do máy quay áp sát) làm điểm số tăng vọt một cách không cân xứng.
- **dᵢ**: khoảng cách (tính bằng pixel) từ **tâm của box dự đoán** đến **tâm của khung hình** — đo logo nằm gần trung tâm màn hình hay lệch ra rìa.
- **W**: chiều rộng của khung hình (pixel).
- **0.3W**: một hằng số thiết kế, quy định **"độ rộng vùng khoan dung"** quanh tâm màn hình — logo càng ra xa khỏi phạm vi 0.3×chiều-rộng-khung-hình thì điểm vị trí càng giảm nhanh.
- **exp[−dᵢ²/(0.3W)²]**: đây là công thức của một **đường cong hình chuông (Gaussian)** — cho điểm gần 1.0 nếu logo ở giữa khung hình, và giảm dần (mượt, không đột ngột) khi logo dịch ra xa tâm.
- **cᵢ**: độ tin cậy (confidence) mà detector gán cho dự đoán đó — giống khái niệm đã giải thích ở Slide 6.
- **Phép nhân (×) giữa 3 thành phần**: đây là lựa chọn thiết kế có chủ đích — nghĩa là nếu **bất kỳ một** trong 3 thành phần thấp (logo nhỏ, hoặc lệch tâm, hoặc confidence thấp) thì **toàn bộ điểm số bị kéo xuống thấp** — không có chuyện 1 yếu tố tốt "bù" được cho yếu tố kém.
- **clip₍₀,₁₎**: giới hạn kết quả cuối cùng nằm trong khoảng từ 0 đến 1 (không cho phép âm hoặc lớn hơn 1).
- **Vᵢ**: kết quả cuối cùng — "Logo Visibility" của **một detection**, một con số duy nhất từ 0 đến 1, càng gần 1 thì logo đó càng "hiển thị tốt" (to, ở giữa khung hình, mô hình tự tin).
- **IoU (Intersection over Union) = 0.85** *(trong caption ví dụ)*: chỉ số đo **mức độ chồng lấp** giữa box dự đoán và box thật (ground truth) — bằng diện tích phần giao nhau chia cho diện tích phần hợp nhất của 2 box. IoU = 0.85 nghĩa là 2 box gần như trùng khít nhau.
- **t = 21.000s**: mốc thời gian (giây) trong video mà khung hình này xuất hiện.

---

## Slide 9 — Formula provenance & evaluation status

- **"Literature-informed, not literature-derived"**: nghĩa là **các thành phần đầu vào** của công thức (kích thước, vị trí, confidence) được **gợi ý/tham khảo** từ các nguồn tài liệu đã có, nhưng **công thức kết hợp cụ thể** (căn bậc hai, đường cong Gaussian, phép nhân...) là **do người nghiên cứu tự thiết kế**, không sao chép từ bất kỳ nguồn nào — vì chưa có nguồn nào công bố công thức đó.
- **Measured geometry (hình học đo được)**: những con số lấy **trực tiếp** từ box dự đoán, không qua suy diễn — ví dụ diện tích box, khoảng cách tâm. Đây là loại bằng chứng **đáng tin cậy nhất**.
- **Model-derived proxy (proxy suy ra từ mô hình)**: những con số do **mô hình AI tự tính ra**, không phải đo trực tiếp từ ảnh — ví dụ confidence. Nó phản ánh "mô hình tự tin đến đâu", **không phải** "con người có đọc được logo hay không".
- **Researcher-defined transformation (biến đổi do người nghiên cứu tự định nghĩa)**: các phép biến đổi toán học được **chọn có chủ đích** (căn bậc hai, Gaussian, hằng số 0.3W, phép nhân) — hợp lý về mặt thiết kế nhưng **chưa được đo lường/kiểm chứng bằng dữ liệu thật** (chưa fit theo số liệu, chưa so sánh với đánh giá của con người).
- **"Component-removal analysis"**: một phương pháp kiểm chứng trong tương lai — thử **bỏ từng thành phần** ra khỏi công thức xem điểm số thay đổi ra sao, để biết thành phần nào thực sự có ý nghĩa.
- **"Two-rater human readability judgements"**: một nghiên cứu tương lai — cho **2 người đánh giá độc lập** chấm điểm "logo này có dễ đọc/dễ thấy không" bằng mắt thường, rồi so sánh với điểm Vᵢ mà công thức tính ra, để kiểm tra công thức có phản ánh đúng cảm nhận con người hay không.

---

*Tài liệu này dùng kèm `LogoLens_WP1_Summary.pptx` — mỗi mục ứng với đúng số thứ tự slide.*
