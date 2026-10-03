# LogoLens — Kịch bản Thuyết trình & Bảo vệ Đầy đủ
### ~10 phút họp với giảng viên hướng dẫn: ~7–8 phút trình bày + câu trả lời chuẩn bị sẵn cho phần thảo luận sau đó

Đi kèm với `LogoLens_WP1_Summary.pptx` (10 slide). Mỗi phần slide dưới đây bao gồm: thời lượng mục tiêu, kịch bản nói, và — khi slide có số liệu hoặc công thức — giải thích ý nghĩa và nguồn gốc, kèm các liên kết thực tế đến nguồn tham khảo được trích dẫn trong luận văn.

---

## Tổng quan thời lượng

| Slide | Nội dung | Thời lượng mục tiêu |
|---|---|---:|
| 1 | Trang bìa | 15 giây |
| 2 | Khoảng trống đo lường | 40 giây |
| 3 | Mục tiêu & câu hỏi nghiên cứu | 35 giây |
| 4 | Bộ dữ liệu & phân chia chống rò rỉ | 55 giây |
| 5 | RF-DETR so với YOLO26 | 55 giây |
| 6 | Kết quả chính & kiểm tra độ tin cậy | 65 giây |
| 7 | Khi nào phát hiện thất bại | 55 giây |
| 8 | Điểm Khả năng Hiển thị Logo — ví dụ minh họa | 100 giây |
| 9 | Nguồn gốc công thức & trạng thái đánh giá | 100 giây |
| 10 | Cảm ơn | 10 giây |
| **Tổng thời lượng trình bày** | | **~8 phút** |
| Thảo luận / bảo vệ | sử dụng các câu trả lời chuẩn bị sẵn bên dưới | ~2 phút trở lên |

---

## SLIDE 1 — Trang bìa (15 giây)

> "Xin chào [buổi sáng/buổi chiều]. Đây là LogoLens, đề tài luận văn của tôi trong Gói Công việc 1: phát hiện logo và phân tích khả năng hiển thị. Tôi sẽ trình bày hệ thống, các kết quả chính, và trạng thái hiện tại của phần chấm điểm khả năng hiển thị — khoảng tám phút, sau đó sẵn sàng nhận câu hỏi."

---

## SLIDE 2 — Khoảng trống đo lường (40 giây)

> "Vấn đề khởi đầu: mỗi trận đấu phát sóng bản thân nó đã là một bản ghi hình ảnh hoàn chỉnh về những logo nhà tài trợ nào đã xuất hiện — nhưng việc định giá tài trợ vẫn dựa trên tiền lệ, chứ không dựa trên bằng chứng đó. Các nền tảng thương mại — Nielsen, Relo Metrics, Blinkfire — chứng minh rằng theo dõi tự động là khả thi, nhưng phương pháp và dữ liệu của họ là độc quyền, nên một câu lạc bộ không thể đối chiếu con số với hình ảnh gốc.
>
> Con số thúc đẩy toàn bộ luận văn nằm ở bên phải: cùng một bộ phát hiện đạt độ thu hồi 90% ở cảnh gần và trung bình, nhưng chỉ 50% ở cảnh rộng chiến thuật. Cùng vị trí trên áo, kết quả rất khác — sự bất đối xứng đó là điều mà phần còn lại của bài trình bày sẽ giải thích."

**Nguồn tham khảo cho slide này** (trích dẫn đầy đủ trong danh mục tài liệu tham khảo của luận văn):
- Nielsen vBrand — [nielsen.com/news-center/2017/…vbrand](https://www.nielsen.com/news-center/2017/nielsen-acquires-artificial-intelligence-powered-sports-marketing-startup-vbrand/)
- Nielsen Sports Reports — [nielsen.com/marketplace/sports-reports](https://www.nielsen.com/marketplace/sports-reports/)
- Relo Metrics — [relometrics.com/sponsorship-measurement-platform](https://relometrics.com/sponsorship-measurement-platform)
- Blinkfire — [blinkfire.com/d/landing/mediaanalytics](https://www.blinkfire.com/d/landing/mediaanalytics)
- Two Circles, ước tính doanh thu IP thể thao — [twocircles.com/…sports-ip-revenue-league](https://twocircles.com/gb/articles/sports-ip-revenue-league-methodology-and-references/)

---

## SLIDE 3 — Mục tiêu & câu hỏi nghiên cứu (35 giây)

> "Hai câu hỏi, rồi câu hỏi thứ ba về cách xử lý câu trả lời. RQ1: hệ thống có thể phát hiện chính xác nhiều logo nhà tài trợ trên các trận đấu chưa từng thấy không? RQ2: độ chính xác đó sụp đổ ở đâu — kích thước, khoảng cách camera, ánh sáng, độ phân giải? RQ3: làm thế nào biến những phát hiện đó thành một thước đo khả năng hiển thị trung thực về những gì nó chưa chứng minh được? Bảng trên màn hình ánh xạ trực tiếp từng RQ vào các hoạt động của Gói Công việc 1 — phát hiện và nhận diện đa logo thuộc RQ1, kích thước/che khuất/chất lượng thuộc RQ2, thời lượng và Điểm Khả năng Hiển thị Logo thuộc RQ3."

---

## SLIDE 4 — Bộ dữ liệu & phân chia chống rò rỉ (55 giây)

> "584 ảnh, 1.903 khung bao, 16 lớp nhà tài trợ, 15 trận đấu riêng biệt. Quyết định phương pháp quan trọng nhất ở đây: đơn vị phân chia là **trận đấu**, không phải khung hình. Tôi phát hiện điều này một cách khó khăn — một lần phân chia theo khung hình trước đó đã để 51 trong 56 khung hình xác thực chia sẻ một khung hình huấn luyện từ cùng một đoạn clip trong vòng hai giây. Đó không phải là kiểm tra khả năng tổng quát hóa, đó là kiểm tra trí nhớ.
>
> Vì vậy thiết kế cuối cùng gán toàn bộ trận đấu vào tập huấn luyện, xác thực hoặc kiểm tra — không bao giờ chia trong cùng một trận. Và con số ở cuối chứng minh tại sao điều đó quan trọng: chạy cùng một checkpoint trên dữ liệu *quen thuộc* và nó đạt 0,998 mAP. Chạy trên các trận đấu thực sự chưa từng thấy và nó giảm xuống 0,933. Khoảng cách 6,5 điểm đó chính là sự lạc quan trong đánh giá mà một phép phân chia ngây thơ sẽ che giấu hoàn toàn."

---

## SLIDE 5 — RF-DETR so với YOLO26 (55 giây)

> "Sau khi cố định phép phân chia, tôi thực hiện so sánh có kiểm soát: RF-DETR Small so với ba phiên bản YOLO26 cơ sở — nano, small, medium — tất cả trên cùng bộ ảnh, cùng đầu vào 896 pixel, cùng mã chấm điểm. RF-DETR Small thắng 16,1 điểm ở mAP@0.50 và, đáng chú ý hơn, 24,4 điểm ở ngưỡng nghiêm ngặt hơn mAP@0.75 — khoảng cách mở rộng khi yêu cầu trùng lặp tăng lên, điều này chỉ ra khả năng định vị tốt hơn, không chỉ phân loại tốt hơn.
>
> Một lưu ý tôi muốn tự nêu trước khi ai đó đặt ra: tiền huấn luyện, số lượng tham số và công thức tăng cường dữ liệu không tương đương giữa hai họ mô hình — RF-DETR mang theo tiền huấn luyện DINOv2 mà YOLO26 không có. Vì vậy đây là kết quả ở *cấp hệ thống* — 'RF-DETR Small hoạt động tốt hơn ở đây, với các công thức này' — không phải một tuyên bố chung rằng transformer đánh bại bộ phát hiện tích chập."

**Nguồn tham khảo:**
- RF-DETR — Robinson et al., 2025 — [arxiv.org/abs/2511.09554](https://arxiv.org/abs/2511.09554)
- YOLO26 — Jocher et al., 2026 — [arxiv.org/abs/2606.03748](https://arxiv.org/abs/2606.03748)
- Backbone DINOv2 — Oquab et al., 2023 — [arxiv.org/abs/2304.07193](https://arxiv.org/abs/2304.07193)

---

## SLIDE 6 — Kết quả chính & kiểm tra độ tin cậy (65 giây)

> "Vậy kết quả chính: 0,933 mAP@0.50, 0,917 ở ngưỡng nghiêm ngặt hơn, F1 đạt 0,898, và suy luận ở tốc độ 19,8 khung hình mỗi giây trên GPU tiêu dùng. Hình ảnh bên trái là một khung hình thực từ tập kiểm tra — không phải ảnh chọn lọc, mà là ảnh kiểm tra thực sự — với tất cả 12 logo trên 6 thương hiệu nhà tài trợ khác nhau được nhận diện chính xác, không có dương tính giả. Đó là hình ảnh thực tế của 'nhận diện đồng thời nhiều logo'.
>
> Nhưng tôi không muốn để bất kỳ con số nào mà không có ngữ cảnh, nên ba bước kiểm tra đi kèm. Kiểm tra rò rỉ mà bạn đã thấy — từ 0,998 xuống 0,933. Kiểm tra mẫu: bốn trong mười lăm lớp có ít hơn năm khung bao kiểm tra, nên tôi báo cáo trung bình giới hạn trên mười một lớp có đủ mẫu — 0,917 — ngay bên cạnh con số thông thường 0,9335. Và kiểm tra ổn định: điểm theo trận lần lượt là 0,973, 0,934 và 0,976, nên kết quả không bị chi phối bởi một trận đấu may mắn."

---

## SLIDE 7 — Khi nào phát hiện thất bại (55 giây)

> "RQ2: nó thất bại ở đâu? Khoảng cách camera là câu trả lời rõ ràng nhất. Độ thu hồi khoảng 0,90 ở cảnh gần và trung bình, và giảm xuống 0,500 ở cảnh rộng chiến thuật. Điều quan trọng là *cách* nó thất bại — độ chính xác ở cảnh rộng vẫn đạt 1,000. Bộ phát hiện không ảo giác logo, nó đơn giản là không nhìn thấy những logo nhỏ, xa. Đó là một thiên lệch dự đoán được, một chiều: bất kỳ ước tính thời lượng nào dựa trên bộ phát hiện này sẽ đếm thiếu mức độ xuất hiện cụ thể trong các đoạn chủ yếu là cảnh rộng — điều này quan trọng vì các bản phát sóng trận đấu đầy đủ chứa nhiều cảnh rộng hơn rất nhiều so với các clip highlight mà bộ dữ liệu này được lấy từ."

---

## SLIDE 8 — Điểm Khả năng Hiển thị Logo: ví dụ minh họa (100 giây)

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

## SLIDE 9 — Nguồn gốc công thức & trạng thái đánh giá (100 giây)

> "Hai câu hỏi nảy sinh ngay lập tức từ ví dụ minh họa đó: công thức này đến từ đâu, và nên tin tưởng nó đến mức nào? Slide này trả lời trực tiếp cả hai, vì tôi muốn tự nêu vấn đề thay vì để người khác nêu.
>
> **Nguồn gốc.** Ba nguồn trong tài liệu nêu cùng các thành phần chung. ExposureEngine, một bài báo năm 2025, tính toán độ phủ trên màn hình và thời lượng xuất hiện trực tiếp từ hình học bộ phát hiện — cùng điểm xuất phát tôi sử dụng. Một bằng sáng chế định giá tài trợ của GumGum nêu kích thước, độ rõ nét, thời lượng và vị trí là các yếu tố chất lượng ứng viên. Và bản mô tả công khai của Nielsen về sản phẩm vBrand nêu cùng ba yếu tố: thời lượng, kích thước, độ rõ hình ảnh.
>
> Điều mà không nguồn nào trong ba nguồn đó làm là công bố quy tắc kết hợp thực tế — dạng hàm. Không ai cho bạn biết *cách* biến kích thước, vị trí và độ tin cậy thành một con số. Vì vậy phương trình này **được thông tin bởi tài liệu, không phải được dẫn xuất từ tài liệu**: việc chọn đầu vào đến từ tài liệu, nhưng căn bậc hai, hàm Gaussian, tỷ lệ 0,3W, và quyết định nhân thay vì cộng — đó là của tôi, được thiết kế và công khai, không phải sao chép từ nguồn đã được xác thực, vì chưa có nguồn xác thực nào công bố điều này.
>
> **Cách tôi đánh giá.** Tôi phân loại mỗi thành phần thành ba mức theo mức độ bằng chứng thực sự hỗ trợ. Diện tích khung bao và khoảng cách tâm là **hình học đo lường được** — đọc trực tiếp từ dự đoán, phần đáng tin cậy nhất của toàn bộ điểm số. Độ tin cậy là **đại diện từ mô hình** — nó cho biết mức độ chắc chắn của bộ phát hiện, không phải liệu con người có thực sự đọc được logo hay không; đó là hai điều khác nhau. Và bản thân các phép biến đổi — căn bậc hai, Gaussian, hằng số 0,3W, phép nhân — là **lựa chọn thiết kế của nhà nghiên cứu**: hợp lý, được ghi nhận, nhưng chưa được khớp với bất kỳ dữ liệu nào và chưa được kiểm chứng so với đánh giá của con người.
>
> Vậy trạng thái trung thực, trong một câu: **minh bạch và hoàn toàn tái tạo được, nhưng chưa phải là thước đo đã được xác thực về chất lượng khả năng hiển thị.** Ba điều cần làm trước khi đạt được trạng thái đó — phân tích loại bỏ thành phần, để kiểm tra xem mỗi thành phần có thực sự đóng góp hay không; so sánh với hình ảnh được tính giờ thủ công, ở nhiều tốc độ lấy mẫu; và một nghiên cứu đọc hiểu của con người với hai người đánh giá đúng chuẩn. Đó không phải là nói suông — đó là mục ưu tiên hàng đầu trong danh sách công việc tương lai ở Chương 6, chính xác vì đó là khoảng trống bằng chứng lớn nhất còn lại trong toàn bộ luận văn."

**Nguồn tham khảo — đọc trước buổi họp nếu có thời gian:**
- ExposureEngine (độ phủ trên màn hình & thời lượng từ hình học) — Sarkhoosh et al., 2025 — [arxiv.org/abs/2510.04739](https://arxiv.org/abs/2510.04739)
- Bằng sáng chế định giá tài trợ tự động GumGum Sports — Katz, Carter & Kim, 2024, US 12,124,509 B2 — [patents.google.com/patent/US12124509B2](https://patents.google.com/patent/US12124509B2/en)
- Mua lại / mô tả sản phẩm Nielsen vBrand — [nielsen.com/news-center/2017/…vbrand](https://www.nielsen.com/news-center/2017/nielsen-acquires-artificial-intelligence-powered-sports-marketing-startup-vbrand/)

**Điểm Khả năng Hiển thị Logo phát triển theo thời gian như thế nào (phòng khi được hỏi, không có trên slide):** các giá trị V_i riêng lẻ được nhóm thành các đoạn liên tục theo thương hiệu; mỗi đoạn nhận trọng số thời lượng (0,5× dưới 1 giây, 1,0× từ 1–5 giây, 1,2× trên 5 giây) và đóng góp `Q = Σ (khả năng hiển thị trung bình đoạn) × (trọng số thời lượng) × (độ dài đoạn)`. Q được báo cáo cùng với số giây xuất hiện trên màn hình thô, không bao giờ đứng một mình — cùng lưu ý "nguyên mẫu, chưa xác thực" áp dụng cho các trọng số và quy tắc dung sai khoảng cách dùng để xây dựng các đoạn.

---

## SLIDE 10 — Cảm ơn (10 giây)

> "Đó là toàn bộ bài trình bày — phát hiện mạnh mẽ và được giới hạn trung thực, lớp khả năng hiển thị đã được triển khai và truy nguyên được nhưng rõ ràng chưa được xác thực. Sẵn sàng nhận câu hỏi."

---

## Chuẩn bị Hỏi đáp mở rộng / bảo vệ

Được nhóm theo chủ đề để bạn có thể tìm câu trả lời phù hợp nhanh chóng nếu cuộc thảo luận chuyển hướng.

### Phương pháp luận & kết quả rò rỉ

**H: "Bạn tự tin đến mức nào rằng phân chia theo trận đấu là đủ — liệu vẫn có thể rò rỉ không?"**
> "Nó loại bỏ chế độ lỗi mà tôi thực sự có thể đo được — 51 trong 56 khung hình xác thực chia sẻ một khung hình huấn luyện trong vòng hai giây. Tôi không thể loại trừ rò rỉ tinh vi hơn, như các bộ camera lặp lại hoặc đồ họa phát sóng giữa các trận, nhưng khoảng cách 6,5 điểm giữa dữ liệu quen thuộc và chưa từng thấy là bằng chứng trực tiếp rằng rò rỉ tôi đã loại bỏ là thực và lớn."

**H: "Tại sao chỉ có ba trận kiểm tra?"**
> "Hạn chế về dữ liệu và chi phí gán nhãn — một nhà nghiên cứu, gán nhãn chủ yếu thủ công. Điều này được nêu rõ ràng là mối đe dọa hiệu lực bên ngoài trong Chương 6, và 'thêm các trận đấu độc lập' là ưu tiên số 2 trong danh sách công việc tương lai, cụ thể là để mở rộng tập con sáu khung bao cảnh rộng, vốn là phần mỏng nhất của bằng chứng hiện tại."

### So sánh bộ phát hiện

**H: "RF-DETR có phải chỉ tốt hơn vì tiền huấn luyện DINOv2, không phải kiến trúc?"**
> "Có thể, và tôi nói thẳng điều đó — tiền huấn luyện, dung lượng và tăng cường dữ liệu không được kiểm soát, chỉ ảnh, phép phân chia, độ phân giải và mã chấm điểm là giống nhau. Điều kết quả hỗ trợ là *lựa chọn thực tế của người triển khai* cho nhiệm vụ này; nó không hỗ trợ một tuyên bố kiến trúc chung. Một benchmark hiệu suất so sánh tương đương — độ trễ, bộ nhớ, trên cùng phần cứng — là ưu tiên số 3 trong công việc tương lai, vì hiện tại chỉ có thời gian chạy của RF-DETR được đo thực tế."

**H: "Tại sao đầu vào 896px thay vì mặc định 640 của YOLO?"**
> "Để giữ so sánh công bằng cho cả hai hệ thống thay vì chỉ công bằng với mặc định riêng của YOLO — các logo nhà tài trợ nhỏ mất nhiều độ phân giải nhất ở 640. Phụ lục B trong luận văn cho thấy bài kiểm tra quét độ phân giải có kiểm soát (512→768→896) đã thúc đẩy quyết định này."

### Điểm Khả năng Hiển thị Logo

**H: "Một công thức chưa được xác thực có làm suy yếu toàn bộ đóng góp về khả năng hiển thị không?"**
> "Chỉ nếu tôi tuyên bố nó đã được xác thực. Tôi không — đóng góp là *chuỗi đo lường truy nguyên được*, không phải tuyên bố rằng 0,016 là đúng khách quan. Mọi con số trong chuỗi đó — diện tích khung bao, khoảng cách, độ tin cậy — đều có thể kiểm tra ngược lại khung hình nguồn. Nghiên cứu xác thực được nêu là bước tiếp theo cần thiết, không phải bỏ qua."

**H: "Điều gì sẽ thay đổi nếu bạn thêm độ mờ hoặc che khuất vào điểm số?"**
> "Chưa có gì — một cách có chủ đích. Chương 2 liệt kê chúng là liên quan nhưng là *cấu trúc chưa được hỗ trợ*: tôi không có cách đã được xác thực để ước tính tổn thất diện tích nhìn thấy do che khuất hoặc độ mờ mà con người nhận thức chỉ từ một khung bao ngang. Thêm chúng mà không xác thực sẽ làm điểm số trông tinh vi hơn mà không làm nó đúng hơn — nên chúng là công việc tương lai, không phải đầu vào hiện tại."

**H: "Có đầu ra EMV / tiền tệ nào không?"**
> "Chỉ như một lớp kịch bản tùy chọn, được gắn nhãn rõ ràng — không bao giờ là đầu ra đã xác thực. Chương 2 trình bày phép tính EMV minh họa và nêu rõ độ tin cậy của nó không bao giờ có thể vượt quá độ tin cậy của thời lượng, trọng số chất lượng, ước tính khán giả và tỷ lệ truyền thông bên dưới. LogoLens báo cáo mức độ xuất hiện truy nguyên được là đầu ra chính; tiền tệ hóa được giữ riêng biệt có mục đích."

### Tổng quát hóa & công việc tương lai

**H: "Điều này có hoạt động cho bóng đá, hoặc câu lạc bộ khác không?"**
> "Như một giả thuyết, có khả năng — hạn chế đối tượng nhỏ và vấn đề thu hồi cảnh rộng đều xuất phát từ tài trợ trên áo và khoảng cách camera nói chung, không đặc thù cho bóng bầu dục liên minh. Nhưng chưa được kiểm chứng; mở rộng sang câu lạc bộ mới hiện tại có nghĩa là gán nhãn thủ công mới, đó chính xác là lý do tại sao ý tưởng gán nhãn tự động dựa trên quy định nằm trong công việc tương lai — quy định trang phục cùng giải đấu cố định vị trí logo nhà tài trợ so với đường may và tấm vải, nên các nhãn từ bộ trang phục tham chiếu có thể tạo khung bao ứng viên cho bộ trang phục của câu lạc bộ mới, giảm chi phí gán nhãn để kiểm chứng giả thuyết đó."

**H: "Bước tiếp theo quan trọng nhất là gì?"**
> "Xác thực tính giờ thủ công và khả năng đọc của lớp khả năng hiển thị — mọi thứ khác trong công việc tương lai hoặc là tăng cường bằng chứng đã vững (thêm trận kiểm tra, benchmark độ trễ tương đương) hoặc là hạ nguồn của bước này. Cho đến khi thời lượng và điểm số được kiểm chứng so với tham chiếu con người, kết quả phát hiện đứng vững một mình nhưng khung khả năng hiển thị vẫn là nguyên mẫu theo thiết kế."

---

*Chuẩn bị cho: Buổi họp giảng viên hướng dẫn LogoLens WP1. Tài liệu đi kèm `LogoLens_WP1_Summary.pptx`.*
