# Từ Sáng tạo đến Định giá: Một Hệ thống Thị giác Máy tính Tự cải thiện cho việc Đo lường và Định giá Tài trợ Quảng cáo trong Kỷ nguyên Trí tuệ Nhân tạo

### Nghiên cứu điển hình hệ thống LogoLens trên môi trường phát sóng bóng bầu dục Bradford Bulls

---

**Luận văn tốt nghiệp (Dissertation)**
Chương trình: Thạc sĩ Khoa học Dữ liệu / Trí tuệ Nhân tạo *(giả định — điều chỉnh theo chương trình thực tế)*
Cơ sở đào tạo: University of Bradford *(giả định theo bối cảnh dự án — cần xác nhận)*
Tác giả: *[Điền họ tên]*
Người hướng dẫn: *[Điền tên giảng viên hướng dẫn]*
Năm học: 2025–2026

> **Ghi chú của tác giả về tính minh bạch số liệu.** Mọi con số định lượng trong luận văn được trích từ nhật ký thực nghiệm của dự án (`docs/`, `paper/`, các bản ghi `results.csv` và audit thủ công). Những số liệu chưa được đo trực tiếp, hoặc suy diễn từ tên run/cấu hình, đều được đánh dấu rõ bằng cụm *[cần kiểm chứng]*. Các tài liệu tham khảo cần xác minh nguồn được đánh dấu tương tự trong phần References. Cách làm này tuân thủ chuẩn liêm chính học thuật: không báo cáo con số chưa đo.

---

## Tóm tắt (Abstract)

Trí tuệ nhân tạo tạo sinh (generative AI) đang công nghiệp hoá khâu *sản xuất* nội dung quảng cáo: soạn lời, dựng hình, tạo ra hàng nghìn biến thể thông điệp trong vài phút. Khi nguồn cung sáng tạo trở nên gần như vô hạn, nút thắt của ngành quảng cáo dịch chuyển từ *tạo ra* sang *đánh giá và định giá* — làm thế nào để biết một vị trí đặt logo, một khoảnh khắc hiển thị, hay một placement cụ thể đáng giá bao nhiêu tiền media. Luận văn này giải quyết đúng mặt còn thiếu đó thông qua **LogoLens**, một hệ thống thị giác máy tính đầu-cuối đo lường mức độ hiển thị (exposure) của logo nhà tài trợ trên video phát sóng thể thao và quy đổi thành Giá trị Media Tương đương (Equivalent Media Value — EMV). Hệ thống gồm một backend xử lý (FastAPI) điều phối một pipeline tám giai đoạn — phát hiện logo bằng YOLO26 fine-tuned, lọc theo đội bằng phân loại áo đấu tham chiếu, gán logo vào mười tám "slot" tài trợ trên kit qua ước lượng tư thế, chấm điểm visibility ba tầng, và tổng hợp EMV — kết nối với một frontend dashboard (Next.js) trực quan hoá kết quả đa trận. Trên tập broadcast bóng bầu dục, mô-đun phát hiện đạt **mAP@0.5 = 0,745** ở giao thức tách theo clip (P 0,65 / R 0,74), trong khi một audit thủ công phân tầng cho thấy độ chính xác gán-đội đạt **91,8% (169/184)**; bộ lọc đội loại **44%** số phát hiện lẽ ra bị tính nhầm, bảo vệ tính đúng đắn của con số doanh thu. Ngoài kiến trúc production, luận văn trình bày một nhánh phương pháp thế hệ sau — *cỗ máy dữ liệu tự cải thiện, không cần gán nhãn thủ công* (annotation-free self-improving data engine) — khai thác ba tín hiệu bị bỏ phí (tài sản logo có sẵn, danh sách nhà tài trợ biết trước, tính dư thừa thời gian của video) để tự sinh nhãn và chưng cất một detector realtime. Đóng góp của luận văn có ba tầng: (i) một hệ thống định giá tài trợ vận hành được, chi phí thấp, tái lập được; (ii) một tái định khung lý thuyết coi định giá bằng AI là *đối trọng tất yếu* của sáng tạo bằng AI trong tương lai của quảng cáo; và (iii) bằng chứng thực nghiệm về việc *dân chủ hoá* năng lực đo lường vốn trước đây chỉ các câu lạc bộ lớn mới tiếp cận được. Từ khoá: định giá quảng cáo, đo lường tài trợ, EMV, phát hiện logo, thị giác máy tính, foundation models, AI và sáng tạo quảng cáo.

*(~320 từ)*

---

## Lời cảm ơn (Acknowledgements)

Tôi xin trân trọng cảm ơn người hướng dẫn khoa học đã định hướng chủ đề, đặc biệt là gợi ý gắn kết công trình kỹ thuật này với khung lý thuyết của số đặc biệt *"AI and the Future of Advertising Creativity"* — một kết nối đã nâng dự án từ một sản phẩm kỹ thuật thành một câu hỏi nghiên cứu có ý nghĩa học thuật. Tôi cảm ơn câu lạc bộ Bradford Bulls và các bên liên quan đã cung cấp bối cảnh nghiệp vụ thực tế cùng tư liệu kit chính thức. Tôi cũng biết ơn cộng đồng mã nguồn mở — các nhóm phát triển Ultralytics, Segment Anything, DINOv2 và hệ sinh thái Python khoa học dữ liệu — những công cụ đã làm cho một nghiên cứu quy mô cá nhân trở nên khả thi. Cuối cùng, tôi cảm ơn gia đình và bạn bè đã kiên nhẫn đồng hành trong suốt quá trình thực hiện.

*(~150 từ)*

---

## Mục lục (Table of Contents)

1. **Giới thiệu**
   1.1. Bối cảnh: từ khan hiếm sáng tạo đến khan hiếm định giá
   1.2. Phát biểu vấn đề
   1.3. Câu hỏi và mục tiêu nghiên cứu
   1.4. Phạm vi và giới hạn phạm vi
   1.5. Đóng góp của luận văn
   1.6. Cấu trúc luận văn
2. **Tổng quan tài liệu**
   2.1. Trí tuệ nhân tạo và tương lai của sáng tạo quảng cáo
   2.2. Kinh tế học của tài trợ thể thao và bài toán định giá
   2.3. Đo lường giá trị media: từ thủ công đến tự động
   2.4. Phát hiện và nhận dạng logo trong thị giác máy tính
   2.5. Foundation models, weak supervision và dữ liệu tổng hợp
   2.6. Khoảng trống nghiên cứu
3. **Phương pháp luận**
   3.1. Triết lý thiết kế và lập trường nhận thức luận
   3.2. Kiến trúc hệ thống: backend ↔ frontend
   3.3. Pipeline xử lý tám giai đoạn
   3.4. Mô hình định giá ba tầng
   3.5. Bộ lọc đội và vấn đề quy gán doanh thu
   3.6. Mô hình mười tám slot tài trợ
   3.7. Nhánh thế hệ sau: cỗ máy dữ liệu tự cải thiện không cần gán nhãn
4. **Triển khai dự án và Nghiên cứu điển hình**
   4.1. Bối cảnh Bradford Bulls
   4.2. Dữ liệu và quy trình huấn luyện
   4.3. Hiện thực backend
   4.4. Hiện thực frontend
   4.5. Bản sao số (digital twin) và dữ liệu tổng hợp
   4.6. Kỹ thuật triển khai và các bẫy kỹ thuật
5. **Kết quả và Đánh giá**
6. **Thảo luận**
7. **Giới hạn của nghiên cứu**
8. **Kết luận và Hướng phát triển**
- Tài liệu tham khảo
- Phụ lục

---

# Chương 1. Giới thiệu

## 1.1. Bối cảnh: từ khan hiếm sáng tạo đến khan hiếm định giá

Trong gần một thế kỷ, kinh tế học của ngành quảng cáo được định hình bởi một sự khan hiếm căn bản: khan hiếm *sáng tạo*. Ý tưởng lớn, bản vẽ storyboard, đoạn phim quảng cáo — tất cả đều tốn kém, chậm và phụ thuộc vào tài năng con người hiếm hoi. Toàn bộ cấu trúc của các agency, quy trình pitch, và cách định giá dịch vụ sáng tạo được xây dựng quanh giả định rằng nội dung quảng cáo tốt là thứ đắt đỏ và khó tạo ra. Làn sóng trí tuệ nhân tạo tạo sinh (generative AI) đang phá vỡ chính giả định nền tảng đó. Các công cụ hiện đại có thể soạn hàng chục phiên bản lời quảng cáo, dựng hình ảnh và video, và sản xuất hàng nghìn biến thể thông điệp được cá nhân hoá chỉ trong vài phút (Davenport et al., 2020; số đặc biệt *AI and the Future of Advertising Creativity*, Journal of Advertising Research, 2025). Khi chi phí biên của việc tạo ra một đơn vị nội dung sáng tạo tiệm cận không, sự khan hiếm cũ tan biến — và một sự khan hiếm mới lộ diện.

Sự khan hiếm mới là *khan hiếm định giá* (valuation scarcity). Nếu một hệ thống có thể sinh ra mười nghìn biến thể một chiến dịch, câu hỏi khẩn thiết không còn là "làm sao tạo ra nội dung?" mà là "biến thể nào, vị trí nào, khoảnh khắc hiển thị nào thực sự có giá trị, và giá trị đó là bao nhiêu?". Chính lời kêu gọi bài của số đặc biệt đã diễn đạt điều này khi khẳng định generative AI đang tái sắp xếp cách nội dung quảng cáo được *hình dung, tạo ra, đánh giá và định giá* (imagined, made, evaluated, and valued). Phần lớn sự chú ý học thuật và thương mại dồn vào hai động từ đầu — *hình dung* và *tạo ra*. Luận văn này lập luận rằng hai động từ sau — *đánh giá* và *định giá* — mới là nơi giá trị kinh tế thực sự được chốt lại, và là nơi mà một hệ thống AI đo lường trở thành đối trọng tất yếu của một hệ thống AI sáng tạo. Không có định giá đáng tin cậy, sự bùng nổ nguồn cung sáng tạo chỉ tạo ra nhiễu; có định giá, nó trở thành một thị trường vận hành được.

Bối cảnh cụ thể mà luận văn khảo sát là **tài trợ thể thao** (sports sponsorship) — một trong những hình thức quảng cáo lâu đời và có giá trị nhất, nơi thương hiệu trả tiền để logo của mình xuất hiện trên áo đấu cầu thủ, biển quảng cáo quanh sân và các bề mặt phát sóng. Không giống quảng cáo TV truyền thống có thời lượng và giá niêm yết rõ ràng, giá trị của tài trợ là *ẩn* và *phân tán*: một logo ngực áo có thể xuất hiện ba giây trong một pha cận cảnh rồi biến mất trong đám đông tranh chấp, kích thước và độ rõ thay đổi liên tục theo góc máy. Việc quy đổi dòng hiển thị hỗn độn này thành một con số tiền tệ — cái mà ngành gọi là Sponsorship Media Value (SMV) hay Equivalent Media Value (EMV) — từ lâu là đặc quyền của các nhà cung cấp đắt đỏ (Nielsen Sports, Relo Metrics, GumGum Sports) mà chỉ các giải đấu và câu lạc bộ hàng đầu đủ khả năng chi trả. Các câu lạc bộ hạng trung như Bradford Bulls — chủ thể của nghiên cứu điển hình này — nằm ngoài tầm với của công cụ đo lường, và do đó không thể chứng minh giá trị cho nhà tài trợ bằng dữ liệu.

## 1.2. Phát biểu vấn đề

Vấn đề nghiên cứu có thể phát biểu ở hai cấp độ đan xen. Ở cấp độ *kỹ thuật*, đo lường tài trợ tự động vấp phải một chuỗi thách thức thị giác máy tính khó: logo nhỏ, biến dạng, thường xuyên bị che khuất; cùng một logo xuất hiện trên áo cả hai đội, trên biển LED và đồ hoạ phát sóng, khiến việc *quy gán* (attribution) đúng cho bên trả tiền trở nên mấu chốt; và mỗi giải đấu, mỗi mùa lại có tập nhà tài trợ khác nhau, khiến các detector đóng (closed-set) truyền thống phải gán nhãn lại hàng nghìn khung hình và huấn luyện lại mỗi khi có nhà tài trợ mới. Ở cấp độ *kinh tế học tổ chức*, chi phí gán nhãn tăng tuyến tính theo mỗi giải đấu mới làm cho các giải pháp hiện có không thể mở rộng xuống phân khúc câu lạc bộ nhỏ — đúng phân khúc cần được dân chủ hoá năng lực định giá nhất.

Hệ quả là một khoảng trống kép: các câu lạc bộ nhỏ vừa thiếu công cụ *kỹ thuật* để đo, vừa thiếu công cụ *lý thuyết* để đặt việc đo lường bằng AI vào bức tranh lớn hơn về tương lai của quảng cáo. Luận văn này lấp cả hai: nó xây dựng và đánh giá một hệ thống vận hành được, đồng thời định vị hệ thống đó trong cuộc thảo luận học thuật về AI và sáng tạo quảng cáo.

## 1.3. Câu hỏi và mục tiêu nghiên cứu

Luận văn được dẫn dắt bởi một câu hỏi nghiên cứu tổng quát:

> **CHNC:** Làm thế nào một hệ thống thị giác máy tính có thể đo lường và định giá mức độ hiển thị của logo tài trợ trong phát sóng thể thao một cách chính xác, tái lập được và có chi phí đủ thấp để dân chủ hoá năng lực định giá vốn trước đây chỉ dành cho các tổ chức lớn?

Câu hỏi này được phân rã thành bốn câu hỏi con:

1. **CHC1 (Phát hiện & quy gán):** Một detector logo fine-tuned kết hợp với bộ lọc đội tham chiếu có thể đạt độ chính xác phát hiện và độ chính xác quy-gán-doanh-thu nào trên broadcast thực tế, và các con số này thay đổi thế nào giữa các giao thức đánh giá?
2. **CHC2 (Định giá):** Làm thế nào để chuyển đổi dòng phát hiện theo từng khung hình thành một con số EMV có cơ sở phương pháp luận, và mô hình định giá theo *vị trí đặt logo* (kit slot) đóng góp gì cho quyết định thương mại?
3. **CHC3 (Khả mở rộng & tự cải thiện):** Có thể loại bỏ nút thắt gán nhãn thủ công bằng một cỗ máy dữ liệu tự cải thiện khai thác các tín hiệu sẵn có (tài sản logo, danh sách nhà tài trợ, dư thừa thời gian) hay không, và giới hạn thực nghiệm của cách tiếp cận này là gì?
4. **CHC4 (Ý nghĩa lý thuyết):** Việc tự động hoá *đánh giá và định giá* bằng AI định vị ra sao trong khung lý thuyết về tương lai của sáng tạo quảng cáo, và nó gợi mở hình thức *đồng sáng tạo người–AI* (human–AI co-creation) nào?

Tương ứng, các **mục tiêu** là: thiết kế và hiện thực hoá pipeline đầu-cuối (backend ↔ frontend); xây dựng và biện minh mô hình định giá ba tầng; thử nghiệm nhánh không-gán-nhãn và đánh giá trung thực cả thành công lẫn thất bại của nó; và tổng hợp một luận điểm lý thuyết gắn công trình vào diễn ngôn AI–quảng cáo.

## 1.4. Phạm vi và giới hạn phạm vi

Luận văn tập trung vào *đo lường và định giá* mức độ hiển thị của logo trên **cầu thủ** (jersey sponsorship) trong môn bóng bầu dục league, với Bradford Bulls làm nghiên cứu điển hình. Các bề mặt khác (biển LED quanh sân, đồ hoạ phát sóng) được xử lý ở mức lọc/loại trừ chứ không phải là đối tượng định giá chính trong phiên bản hiện tại. Luận văn *không* tuyên bố xây dựng một mô hình kinh tế lượng dự báo doanh thu tài trợ; EMV ở đây là một *proxy* chuẩn ngành cho giá trị hiển thị, không phải giá bán thực tế. Luận văn cũng không thực hiện nhận dạng danh tính cá nhân cầu thủ hay khán giả — một lựa chọn có chủ đích vì lý do đạo đức (xem Chương 7). Cuối cùng, các con số hiệu năng được báo cáo trên quy mô dữ liệu của một dự án nghiên cứu cá nhân (hàng chục trận, một môn thể thao, một câu lạc bộ chính); khả năng khái quát hoá liên môn được thảo luận nhưng chưa được chứng minh ở quy mô lớn.

## 1.5. Đóng góp của luận văn

Luận văn đưa ra ba đóng góp, trải trên trục kỹ thuật–lý thuyết:

- **Đóng góp 1 (Hệ thống).** Một hệ thống định giá tài trợ đầu-cuối, tái lập được, chi phí thấp: pipeline tám giai đoạn ghép YOLO26, phân loại đội tham chiếu, ước lượng tư thế và mô hình định giá ba tầng, kết nối với một dashboard phân tích đa trận. Toàn bộ vận hành được trên phần cứng cấp tiêu dùng ở tốc độ xấp xỉ thời gian thực.
- **Đóng góp 2 (Phương pháp không-gán-nhãn).** Một *cỗ máy dữ liệu tự cải thiện* tái định khung bài toán từ "gán nhãn" sang "khai thác thông tin bị bỏ phí", cùng một đánh giá trung thực (bao gồm cả các thất bại do đói dữ liệu) về tính khả thi của nó.
- **Đóng góp 3 (Lý thuyết).** Một luận điểm định vị *định giá bằng AI* như đối trọng tất yếu của *sáng tạo bằng AI*, và một khung *đồng sáng tạo người–AI trong đo lường* trong đó vai trò con người dịch từ "người gán nhãn" sang "người kiểm định", cùng bằng chứng về việc dân chủ hoá năng lực định giá cho tổ chức nhỏ.

## 1.6. Cấu trúc luận văn

Chương 2 tổng quan bốn dòng tài liệu giao nhau tại đề tài này. Chương 3 trình bày phương pháp luận và kiến trúc hệ thống chi tiết. Chương 4 mô tả việc hiện thực hoá và nghiên cứu điển hình Bradford Bulls. Chương 5 báo cáo và đánh giá kết quả thực nghiệm. Chương 6 thảo luận ý nghĩa lý thuyết và thực tiễn. Chương 7 nêu các giới hạn. Chương 8 kết luận và đề xuất hướng phát triển.

*(~1.520 từ cho Chương 1)*

---

# Chương 2. Tổng quan tài liệu

Đề tài này nằm ở giao điểm của bốn dòng nghiên cứu ít khi được đọc cùng nhau: (i) diễn ngôn về AI và sáng tạo quảng cáo trong khoa học marketing; (ii) kinh tế học và đo lường tài trợ thể thao; (iii) phát hiện — nhận dạng logo trong thị giác máy tính; và (iv) foundation models cùng học giám sát yếu (weak supervision). Chương này tổng quan từng dòng một cách phản biện, rồi tổng hợp thành một khoảng trống nghiên cứu mà luận văn nhắm tới.

## 2.1. Trí tuệ nhân tạo và tương lai của sáng tạo quảng cáo

Nghiên cứu về AI trong marketing đã chuyển từ giai đoạn dự báo tổng quát (Davenport et al., 2020; Huang & Rust, 2021) sang giai đoạn khảo sát cụ thể tác động của generative AI lên *quá trình sáng tạo*. Số đặc biệt của Journal of Advertising Research mà luận văn lấy làm khung — *AI and the Future of Advertising Creativity* — đóng khung generative AI như một lực làm sụp đổ các ràng buộc vốn giới hạn sáng tạo quảng cáo, và mời gọi khảo sát cách nội dung được *hình dung, tạo ra, đánh giá và định giá*. Song song, lời kêu gọi bài *Generative AI and Advertising: Building New Theoretical Frontiers* của Journal of Advertising nhấn mạnh nhu cầu về khung lý thuyết mới cho hiện tượng này (ISPR, 2025).

Một chủ đề nổi bật trong dòng này là *đồng sáng tạo giá trị người–AI* (human–AI value co-creation). Các nghiên cứu gần đây khảo sát cách các chuyên gia quảng cáo cảm nhận vai trò của mình khi AI tham gia vào workflow, cho thấy giá trị được tạo ra không phải bởi AI *thay thế* con người mà bởi sự phân công lại lao động nhận thức (International Journal of Advertising, 2026 [cần kiểm chứng chi tiết trích dẫn]). Một hướng phản biện khác — tiếp cận *maieutic* (đặt câu hỏi) với quảng cáo AI (Journal of Advertising, 2022) — cảnh báo rằng việc tự động hoá không trung lập về giá trị và cần được chất vấn liên tục.

Điểm mù của dòng tài liệu này, đối với mục đích của luận văn, là nó hầu như chỉ nói về *phía cung sáng tạo*: AI tạo ra gì, con người cảm thấy thế nào về việc đó. Rất ít công trình xử lý *phía đánh giá và định giá* — dù chính lời kêu gọi bài liệt kê "đánh giá và định giá" ngang hàng với "hình dung và tạo ra". Luận văn này lập luận rằng đó không phải là một chi tiết phụ: khi generative AI làm nguồn cung sáng tạo bùng nổ, năng lực *phân biệt cái gì đáng giá* trở thành ràng buộc mới. Do đó, một hệ thống AI đo lường giá trị hiển thị không nằm ngoài diễn ngôn sáng tạo quảng cáo — nó là mặt còn thiếu của chính diễn ngôn đó.

## 2.2. Kinh tế học của tài trợ thể thao và bài toán định giá

Tài trợ thể thao là một kênh truyền thông marketing khác biệt về bản chất so với quảng cáo mua chỗ (paid media): giá trị của nó gián tiếp, gắn với cảm xúc và bối cảnh, và khó tách bạch khỏi hiệu ứng của chính sự kiện (Cornwell, 2019; Cornwell & Kwon, 2020). Nền tảng tâm lý học của hiệu quả biển hiệu tài trợ đã được nghiên cứu kỹ: Breuer và Rumpf (2012) cùng Rumpf, Boronczyk và Breuer (2020) chỉ ra rằng *đặc điểm hiển thị* — kích thước, thời lượng, vị trí, sự chuyển động và độ tương phản — dự báo mạnh khả năng ghi nhớ thương hiệu của người xem. Đây là cơ sở lý thuyết trực tiếp cho việc một hệ thống đo lường phải *trọng số hoá theo chất lượng hiển thị* chứ không chỉ đếm thời lượng thô — nguyên lý mà mô hình visibility ba tầng trong luận văn này hiện thực hoá.

Về phía đo lường giá trị tiền tệ, ngành đã hội tụ quanh khái niệm SMV/EMV: quy đổi thời lượng hiển thị đã hiệu chỉnh chất lượng thành "chi phí tương đương nếu phải mua quảng cáo cùng lượng chú ý đó" (Nielsen Sports, 2019; Relo Metrics, 2022 [cần kiểm chứng]). Cách tiếp cận EMV bị phê phán chính đáng là ước lượng thô của *chú ý* chứ không phải *tác động kinh doanh*, và dễ bị thổi phồng nếu đếm cả những hiển thị không tạo ghi nhớ. Tuy vậy nó vẫn là ngôn ngữ chung mà các bên thương lượng, và do đó là đầu ra thực dụng đúng đắn cho một hệ thống hướng tới ứng dụng thực tế. Luận văn tiếp nhận EMV như một *proxy chuẩn ngành*, đồng thời thừa nhận rõ giới hạn nhận thức luận của nó (Chương 6–7).

## 2.3. Đo lường giá trị media: từ thủ công đến tự động

Về mặt lịch sử, đo lường tài trợ được thực hiện thủ công: nhân viên xem lại băng ghi hình và bấm giờ từng lần logo xuất hiện — một quy trình chậm, đắt và thiếu nhất quán giữa người quan sát. Thế hệ tự động hoá đầu tiên dùng thị giác máy tính để phát hiện logo theo khung hình, được thương mại hoá bởi các nhà cung cấp như GumGum Sports, Hive và Relo Metrics. Gần đây, công trình học thuật *ExposureEngine* (arXiv 2510.04739 [cần kiểm chứng]) báo cáo mAP 0,859 với bounding box định hướng (oriented bounding box — OBB) trên dữ liệu bóng đá, và đề xuất một pipeline định giá gắn với phát hiện. Luận văn này kế thừa nhiều nguyên lý từ dòng đó — đặc biệt là ý tưởng dùng OBB để hiệu chỉnh diện tích logo bị nghiêng do góc máy — nhưng bổ sung ba yếu tố mà tài liệu thương mại thường không công khai: (i) một *bộ lọc đội* tường minh để chỉ tính hiển thị thuộc về bên trả tiền; (ii) một mô hình *định giá theo vị trí* trên kit; và (iii) một cam kết *tái lập được và chi phí thấp* nhằm phục vụ phân khúc bị bỏ quên.

Một khoảng cách quan trọng trong tài liệu đo lường là *thiếu ground-truth công khai có nhãn quyền-sở-hữu-tài-trợ*. Các benchmark thể thao lớn như SoccerNet-v2 (Deliège et al., 2021) cung cấp nhãn cầu thủ, bóng và sự kiện, nhưng không có nhãn "logo này thuộc nhà tài trợ nào và của đội nào". Sự thiếu vắng này buộc mọi hệ thống định giá phải tự tạo cơ chế đánh giá riêng — và, như luận văn sẽ lập luận, khiến việc *audit thủ công có kiểm soát* trở thành một thành phần phương pháp luận bắt buộc chứ không phải tuỳ chọn.

## 2.4. Phát hiện và nhận dạng logo trong thị giác máy tính

Phát hiện logo là một nhánh chuyên biệt của phát hiện đối tượng với những khó khăn riêng: đối tượng nhỏ, biến dạng phi cứng (trên vải áo), số lớp lớn và mất cân bằng, và yêu cầu *mở* (open-set) — hệ thống phải xử lý các thương hiệu chưa từng thấy khi huấn luyện. Các detector đóng dựa trên CNN/transformer (họ YOLO — Redmon et al., 2016; Jocher et al., 2023; họ DETR) đạt độ chính xác cao trên tập lớp cố định nhưng không khái quát sang thương hiệu mới nếu không huấn luyện lại. Để giải quyết tính mở, dòng *truy hồi logo open-set* (open-set logo retrieval) đối sánh vùng phát hiện với một thư viện mẫu (gallery): OSLD và SeeTek (Tüzkö et al.; Xu et al.) là các đại diện, trong đó SeeTek hợp nhất embedding thị giác với văn bản trong ảnh (scene text) để mở rộng sang quy mô lớn. Luận văn kế thừa ý tưởng gallery mở rộng được, và mở rộng nó bằng ba kênh — thị giác ⊕ văn bản ⊕ màu — cùng một *tiên nghiệm danh sách* (roster prior) đặc thù cho thể thao.

Điểm mấu chốt mà tài liệu logo detection thường bỏ qua nhưng lại quyết định trong bối cảnh tài trợ là *quy gán chủ sở hữu*. Một logo được phát hiện đúng vẫn có thể bị tính sai tiền nếu nó nằm trên áo đối thủ hoặc biển LED. Vấn đề này thực chất là bài toán *phân loại đội* (team assignment), gần với thử thách SoccerNet Game State Reconstruction, nơi các giải pháp hàng đầu dùng phân cụm màu/embedding cộng bỏ phiếu theo tracklet thay vì huấn luyện một mô hình riêng cho mỗi trận (vì kit đối thủ đổi liên tục). Luận văn áp dụng đúng họ kỹ thuật tham chiếu này cho bộ lọc đội.

## 2.5. Foundation models, weak supervision và dữ liệu tổng hợp

Bước ngoặt gần đây cho phép tái định khung bài toán gán nhãn là sự trưởng thành của các *foundation model* thị giác. Các detector open-vocabulary (Grounding DINO — Liu et al., 2023; DINO-X) và các segmenter promptable (Segment Anything — Kirillov et al., 2023; SAM 2 — Ravi et al., 2024; SAM 3 [cần kiểm chứng]) cho phép tạo *pseudo-label* zero-shot. Đặc biệt, khả năng phân đoạn theo *khái niệm được prompt bằng mẫu* (exemplar-prompted concept segmentation) và *bám theo* (track) đối tượng qua video mở ra khả năng gán nhãn cả một broadcast từ một mẫu logo duy nhất cho mỗi thương hiệu. Embedding tự giám sát DINOv2 (Oquab et al., 2023) cung cấp biểu diễn thị giác mạnh để phân cụm các crop *thực-với-thực* — một chi tiết mà luận văn phát hiện là mấu chốt: DINOv2 phân cụm thực↔thực tốt nhưng đối sánh thực↔mẫu-sạch (template) lại thất bại, một bài học thực nghiệm sẽ được trình bày ở Chương 3 và 5.

Để hợp nhất nhiều nguồn nhãn nhiễu thành tín hiệu huấn luyện sạch, dòng *học giám sát yếu theo lập trình* (programmatic weak supervision) — tiêu biểu là Snorkel (Ratner et al., 2017) — cung cấp khung *label model* gộp các *labelling function* mâu thuẫn. Bổ trợ cho nó, *tinh chỉnh theo thời gian* (temporal track refinement) dùng tính liên tục của track để phục hồi các phát hiện bị bỏ sót và loại các track chớp nháy nhiễu. Cuối cùng, để phủ các điều kiện hiếm (góc gắt, loá đèn, mưa), dữ liệu tổng hợp — từ copy-paste, diffusion compositing, đến *bản sao số* dựng bằng 3D Gaussian Splatting (Kerbl et al., 2023) với chèn logo có nhận biết ánh sáng — cho phép sinh khung hình quang-thực với nhãn chính xác pixel. Luận văn tích hợp cả bốn ý tưởng này trong nhánh phương pháp thế hệ sau (Mục 3.7).

## 2.6. Khoảng trống nghiên cứu

Tổng hợp bốn dòng trên làm lộ ra một khoảng trống có cấu trúc. Dòng (i) bàn nhiều về AI *sáng tạo* nhưng bỏ ngỏ AI *định giá*; dòng (ii) có lý thuyết định giá vững nhưng phương pháp đo phần lớn thủ công hoặc bị khoá trong sản phẩm thương mại không tái lập được; dòng (iii) có kỹ thuật phát hiện mạnh nhưng ít xử lý *quy gán doanh thu* và *định giá theo vị trí*; dòng (iv) cung cấp công cụ để phá nút thắt gán nhãn nhưng chưa được kiểm nghiệm trong bối cảnh định giá tài trợ chi phí thấp. Chưa có công trình nào *đồng thời* (a) xây dựng hệ thống định giá tài trợ đầu-cuối tái lập được, (b) đánh giá trung thực nó bằng audit có kiểm soát trên nhiều giao thức, và (c) định vị nó trong khung lý thuyết về tương lai của sáng tạo quảng cáo như một hành vi *đồng đánh giá người–AI*. Luận văn này nhắm vào đúng giao điểm đó.

*(~1.700 từ cho Chương 2)*

---

# Chương 3. Phương pháp luận

## 3.1. Triết lý thiết kế và lập trường nhận thức luận

Phương pháp luận của luận văn kết hợp *khoa học thiết kế* (design science) — trong đó tri thức được tạo ra thông qua việc xây dựng và đánh giá một hiện vật (artifact) — với *nghiên cứu điển hình* (case study) làm bối cảnh kiểm nghiệm. Ba nguyên lý thiết kế xuyên suốt định hình mọi quyết định kỹ thuật.

Thứ nhất, **tính tổng quát (generality)**: hệ thống phải để một câu lạc bộ khác "thả logo của họ vào là chạy" mà không phải sửa mã. Nguyên lý này loại bỏ các giải pháp hard-code theo Bradford Bulls và ưu tiên các cơ chế tham chiếu, cấu hình bằng biến môi trường.

Thứ hai, **an toàn cho doanh thu (revenue-safety)**: khi hệ thống không chắc chắn, nó phải sai *về phía không trừ tiền khách hàng* thay vì thổi phồng. Nguyên lý này chi phối chính sách giữ/bỏ của bộ lọc đội (giữ lại các track chưa đủ bằng chứng thay vì loại bừa).

Thứ ba, **liêm chính đo lường (measurement integrity)**: vì không có ground-truth công khai, mọi con số báo cáo phải truy nguyên được về một quy trình đánh giá minh bạch, và các số chưa đo phải được đánh dấu là chưa đo. Bài học nền tảng ở đây — được rút ra một cách đau đớn trong quá trình phát triển — là *"không được lấy đầu ra của mô hình giáo viên (teacher) làm chân lý (gold) để tự chấm điểm chính mình"*, vì làm vậy sẽ tạo ra những con số ảo tự khẳng định.

Về nhận thức luận, luận văn phân biệt rạch ròi ba loại phát biểu: (a) *phát biểu vận hành* — hệ thống làm được gì, đo bằng chính đầu ra của nó; (b) *phát biểu chính xác* — hệ thống đúng đến đâu, chỉ được khẳng định khi đối chiếu với đánh giá độc lập của con người; và (c) *phát biểu giá trị* — con số EMV có ý nghĩa kinh tế gì, luôn kèm điều kiện về giả định. Sự phân biệt này được duy trì trong toàn bộ phần kết quả.

## 3.2. Kiến trúc hệ thống: backend ↔ frontend

Hệ thống chia thành hai nửa ghép lỏng qua một API HTTP, cho phép phát triển và mở rộng độc lập.

```
Frontend (Next.js :3000)  ──upload video──►  Backend (FastAPI)
   dashboard 5 tab        ◄──poll job JSON──   - hàng đợi job (in-process)
                          ◄──kết quả + video──  - orchestrator pipeline
                                                - SQLite (→ Postgres)
                                                - local storage (→ S3)
                                                        │
                          YOLO26 logo · YOLO11 person + BoT-SORT ·
                          phân loại áo (color ⊕ SigLIP) · YOLO11-pose ·
                          YOLO11-seg / DensePose (overlay)
```

**Backend** (`backend/`) là nơi chứa "phần xử lý chính": một ứng dụng FastAPI phơi bày các endpoint tạo job, poll tiến độ, và truy xuất kết quả (`/api/jobs`, `/api/analyses`). Điểm thiết kế then chốt là *mọi hạ tầng nằm sau interface*: cơ sở dữ liệu (SQLite trong phát triển, có thể đổi sang Postgres), lưu trữ (local, có thể đổi sang S3) và hàng đợi job (in-process, có thể đổi sang hàng đợi phân tán) đều được trừu tượng hoá, nên việc nâng cấp lên production stack chỉ cần đổi biến môi trường chứ không sửa logic pipeline. Đây là hiện thân của nguyên lý tổng quát ở tầng hạ tầng.

**Frontend** (`logo-analytics/`) là một dashboard Next.js gồm năm tab phân tích (Overview, Match Videos, Brand Insights, Analytics Report, Body Segmentation). Một chi tiết thiết kế đáng chú ý: toàn bộ biểu đồ (donut, trend, heatmap, radar, scatter) được *tự viết bằng SVG* trong `components/dashboard/charts.tsx`, không phụ thuộc thư viện chart bên ngoài. Lựa chọn này đánh đổi công sức phát triển lấy quyền kiểm soát hoàn toàn về trực quan và tính tương tác, đồng thời giảm bề mặt phụ thuộc — phù hợp với một sản phẩm hướng tới triển khai bền vững.

## 3.3. Pipeline xử lý tám giai đoạn

Trái tim của backend là *orchestrator* (`app/pipeline/orchestrator.py`), chạy tuần tự tám giai đoạn cho mỗi job và liên tục cập nhật trường `stage`/`progress` để frontend hiển thị tiến độ thời gian thực. Một nguyên tắc kỹ thuật quan trọng: mọi giai đoạn tuỳ chọn đều *suy giảm nhẹ nhàng* (degrade gracefully) — lỗi chỉ ghi cảnh báo, job vẫn hoàn tất với kết quả một phần thay vì sụp đổ toàn bộ.

| Giai đoạn | Tiến độ | Nội dung |
|---|---|---|
| `frames` | 5% | Đọc metadata video (thời lượng, fps, kích thước) |
| `team` | 8% | Nếu chưa có tham chiếu: bootstrap kit references từ chính video |
| `detect` | 10→80% | Vòng lặp chính (lấy mẫu 2 fps): YOLO26 phát hiện logo (imgsz 1280) → chấm visibility → lọc đội → gán logo vào slot qua pose |
| `exposure` | 92% | Gộp phát hiện thành segment liên tục theo từng brand |
| `pricing` | 98% | Quy đổi EMV theo brand |
| `preview` | 98% | Video chú thích full-fps (hộp + nhãn), ghép **audio gốc** |
| `bodyseg` | 98% | Video overlay body-part (YOLO-seg hoặc DensePose) |
| `done` | 100% | Lưu bản ghi Analysis vào DB + storage |

Một quyết định thiết kế tinh tế là **hai lượt phát hiện tách biệt**. Lượt *analytics* lấy mẫu thưa (SAMPLE_FPS = 2/giây) — đủ chính xác để ước lượng *thời lượng* mà rẻ về tính toán, và là nguồn của mọi con số EMV. Lượt *preview* chạy full-fps (giới hạn bởi PREVIEW_MAX_FRAMES) để tạo video xem lại mượt với hộp bám sát logo từng khung hình. Việc tách này thừa nhận rằng *đo lường* và *trình diễn* có yêu cầu tần suất khác nhau, và tối ưu riêng cho từng mục tiêu. (Một hệ quả cần lưu ý về mặt phương pháp: lượt preview hiện không chạy bộ lọc đội, nên hộp hiển thị mọi logo; con số EMV thì luôn đã lọc — sự bất đối xứng này được ghi nhận minh bạch. Như Chương 5 sẽ cho thấy, tần suất lấy mẫu *có* ảnh hưởng hệ thống lên con số cuối, nên lựa chọn 2 fps không phải là trung tính.)

Đầu ra của pipeline là một bản ghi JSON đầy đủ (`aggregate.build_analysis_result`) gồm: mảng `logos[]` (segment, giây exposure, quality exposure, avg visibility, EMV theo brand); `bodyZones[]` (18 kit slot với % exposure); `teamFilter` (kept/dropped/dropRate); và `detectionTimeline[]` (khoảng thời gian on-screen mỗi brand, dùng để vẽ timeline trên player).

## 3.4. Mô hình định giá ba tầng

Cốt lõi *học thuật* của hệ thống — và là câu trả lời cho CHC2 — là một mô hình định giá ba tầng chuyển dòng phát hiện thô thành một con số tiền tệ có cơ sở. Mô hình được xây trên nền tài liệu hiệu quả biển hiệu tài trợ (Mục 2.2) và chuẩn EMV ngành.

**Tầng 1 — Điểm khả kiến (Visibility Score), tính cho mỗi phát hiện mỗi khung hình.** Bốn thành phần được nhân với nhau:

```
Visibility = Size × Position × Clarity × OBB_penalty
```

- `Size = sqrt(box_area / frame_area)` — dùng căn bậc hai để tránh một logo cực lớn (pha cận cảnh) chi phối toàn bộ, phản ánh quy luật tâm lý rằng khả kiến không tăng tuyến tính theo diện tích.
- `Position = exp(−dist_from_center² / (0.3·W)²)` — một Gaussian đặt trọng số cao cho vùng trung tâm màn hình (nơi mắt người xem tập trung) và giảm dần về góc.
- `Clarity` = điểm tin cậy (confidence) của YOLO, đại diện độ rõ/độ chắc chắn của logo.
- `OBB_penalty = area_HBB / area_OBB` — hệ số hiệu chỉnh khi logo bị nghiêng do góc máy: hộp bao thẳng (HBB) phóng đại diện tích của một logo nghiêng, nên tỉ số với hộp định hướng (OBB) kéo diện tích về giá trị thực. Nguyên lý này kế thừa từ ExposureEngine (mAP 0,859 với OBB trên bóng đá [cần kiểm chứng]).

Một ngưỡng sàn `VISIBILITY_FLOOR = 0,02` loại các phát hiện quá nhỏ/lệch tâm khỏi việc tạo segment. Ngưỡng này thấp hơn nhiều so với đề xuất 0,1 trong một số tài liệu, và lựa chọn đó *có chủ đích và được kiểm nghiệm*: logo tài trợ thực tế thường có visibility ~0,03–0,08 vì nhỏ và lệch tâm, nên ngưỡng 0,1 sẽ vứt gần hết tín hiệu thật. Phân tích độ nhạy (Chương 5) định lượng đánh đổi này.

**Tầng 2 — Điểm hiển thị (Exposure Score), tổng hợp theo thời gian cho mỗi brand.** Các phát hiện *đã qua lọc đội* được nối thành *segment* liên tục (nhờ track-id từ BoT-SORT), rồi:

```
Quality Exposure (giây) = Σ_segment [ duration × mean(visibility) × duration_weight ]
```

Segment ngắn hơn `MIN_SEGMENT_SECONDS = 0,5` bị loại (chớp nháy, nhiễu). *Duration weight* mã hoá quy luật ghi nhớ: segment < 1s được trọng số 0,5 (quá ngắn để nhớ), 1–5s là 1,0 (chuẩn), > 5s là 1,2 (hiển thị bền vững, giá trị cao hơn). Đầu ra tầng này gồm `total_exposure_seconds`, `quality_exposure_seconds`, `avg_visibility_score`, `segment_count` và `longest_segment_seconds` cho mỗi brand.

**Tầng 3 — Giá trị Media Tương đương (EMV), quy ra USD.** Công thức lõi hiện triển khai:

```
EMV = QualityExposure(s) × (CPM / 1000) × AudienceSize × PlacementMultiplier
```

trong đó `CPM` (chi phí trên một nghìn lượt hiển thị) và `AudienceSize` nhập khi upload; `PlacementMultiplier` phản ánh loại phát sóng (Live TV = 1,0; Highlight = 1,4 vì được xem lại nhiều; Stream = 0,85; Social = 0,7). Đặc tả đầy đủ (`LOGOS_Exposure_Pricing_Algorithm.md`) còn định nghĩa hai hệ số nhân bổ sung — *Category Multiplier* (share of voice: độc quyền ngành 1,25; có đối thủ cùng khung 0,80) và *Prime-Time Multiplier* (15 phút đầu/cuối trận 1,30) — để mở rộng khi có dữ liệu ngữ cảnh. Bảng CPM tham chiếu theo loại sự kiện (thể thao đại chúng 15–25 USD, cao cấp 35–60 USD, esports 8–15 USD) cung cấp giá trị mặc định hợp lý khi người dùng chưa có số riêng.

Giá trị phương pháp luận của mô hình ba tầng, so với cách tiếp cận ngây thơ (đếm số khung hình × CPM), nằm ở chỗ mỗi tầng đưa vào một hiệu chỉnh có cơ sở lý thuyết: tầng 1 hiệu chỉnh *chất lượng hiển thị không gian*, tầng 2 hiệu chỉnh *cấu trúc thời gian và ghi nhớ*, tầng 3 hiệu chỉnh *bối cảnh phát sóng và cạnh tranh*. Chuỗi hiệu chỉnh này biến một phép đếm thô thành một ước lượng chú ý có thể biện minh.

## 3.5. Bộ lọc đội và vấn đề quy gán doanh thu

Nếu mô hình định giá là "cái gì đáng giá bao nhiêu", thì bộ lọc đội trả lời "đáng giá đó thuộc về ai". Vấn đề: nhiều nhà tài trợ xuất hiện trên áo *cả hai đội*, trên biển LED và áo trọng tài; một detector chỉ được train trên kit Bradford vẫn khớp nhầm các logo giống nhau ở nơi khác, làm EMV bị thổi phồng. Khách hàng mua slot trên áo Bradford chỉ được tính đúng những lần logo nằm trên cầu thủ Bradford.

Thiết kế (port từ prototype `team_detection/` vào `backend/app/pipeline/teamid/`) theo đúng họ kỹ thuật của các giải pháp SoccerNet hàng đầu — phân cụm màu/embedding cộng bỏ phiếu theo tracklet — và *không train mô hình riêng*, vì kit đối thủ đổi mỗi trận nên cách tham chiếu tự thích nghi từng trận là bền vững hơn. Luồng xử lý mỗi khung hình được lấy mẫu:

```
YOLO11 person + BoT-SORT → track_id ổn định cho từng cầu thủ
   → cắt dải áo (15–45% chiều cao bbox, bỏ pixel cỏ + da)
   → classify = fuse(color histogram, SigLIP embedding)
        (trọng số học từ chính refs: kit đen/trắng → color thắng)
   → VoteTracker: cộng dồn phiếu theo track + hysteresis 1,25×
   → gán logo → người (bbox nhỏ nhất chứa tâm logo, else gần nhất)
   → owner == TARGET ? giữ : bỏ
```

Kit references được thiết lập theo ba nấc *không có bước thủ công bắt buộc*: (1) file refs tay nếu tồn tại (chỉ để override); (2) auto-bootstrap + kit anchors — phân cụm cầu thủ trong 32 khung đầu, chọn cụm giống ảnh kit chính thức (`KIT/*.jpg`) nhất; (3) auto-bootstrap + luminance — kit away tối thì chọn cụm tối nhất. Nấc 2 là mặc định thực tế.

Chính sách giữ/bỏ hiện thân trực tiếp nguyên lý *an toàn doanh thu*: owner là TARGET thì giữ; owner là OTHER nhưng track *chưa đủ phiếu* (`TEAM_KEEP_UNKNOWN = true`) thì vẫn giữ (thiếu bằng chứng thì không trừ tiền khách); owner là OTHER và đủ phiếu thì bỏ; không gắn được với người nào (biển LED, khán đài) thì bỏ. Sự bất đối xứng có chủ đích này — giữ khi nghi ngờ, bỏ khi chắc chắn — biến một quyết định kỹ thuật thành một quyết định *đạo đức thương mại*.

## 3.6. Mô hình mười tám slot tài trợ

Đóng góp thứ hai cho CHC2 là *định giá theo vị trí*. Thay vì coi "một logo trên áo" là đồng nhất, hệ thống gán mỗi phát hiện — qua keypoint từ YOLO11-pose (`bodyzones.py`) — vào một trong *mười tám slot bán được trên kit*, chứ không phải vào vùng giải phẫu. Các nhóm slot gồm: ngực (chest-center/l/r), vai–tay (shoulder-l/r, sleeve-l/r), lưng (back-top/center/lower), bụng (abdomen), quần (shorts-front-l/r, shorts-back, shorts-leg-l/r) và tất (sock-l/r). Vùng da (đầu, tay trần, đùi, giày) *không có slot* — logo không bao giờ bị gán nhầm vào đó.

Ý nghĩa thương mại: phần trăm exposure theo từng slot trở thành cơ sở định giá vi mô — slot nào hiển thị nhiều thì đáng giá cao hơn, cho phép câu lạc bộ định giá *khác nhau* cho từng vị trí đặt logo thay vì một mức chung. Đây chính là điểm mà công trình đo lường chạm vào *phía sáng tạo* của quảng cáo: nó biến "chỗ nào trên áo" thành một biến thiết kế có giá, thông tin ngược lại cho quyết định *đặt logo ở đâu*. Frontend hiện thực hoá điều này bằng một mô hình 3D xoay được, tô màu 18 slot và xếp hạng theo % exposure — một công cụ trực quan để thuyết trình pricing theo vị trí.

## 3.7. Nhánh thế hệ sau: cỗ máy dữ liệu tự cải thiện không cần gán nhãn

Kiến trúc production ở trên vẫn phụ thuộc một detector fine-tuned trên nhãn thủ công. Để trả lời CHC3 — liệu có thể phá nút thắt gán nhãn — luận văn phát triển và thử nghiệm một nhánh phương pháp thế hệ sau, gọi là *cỗ máy dữ liệu tự cải thiện* (self-improving data engine), tái định khung bài toán từ "gán nhãn" sang "khai thác thông tin bị bỏ phí". Ba tín hiệu miễn phí thường bị bỏ qua:

1. **Tài sản có sẵn.** File logo vector/PNG của mọi nhà tài trợ đã tồn tại — là *mẫu* (exemplar) thị giác tự nhiên.
2. **Danh sách biết trước.** Một trận chỉ có ~10–30 thương hiệu khả dĩ; *tiên nghiệm danh sách* (roster prior) này biến nhận dạng thế-giới-mở thành *đóng-theo-từng-sự-kiện* (closed-set-per-event), loại bỏ dương tính giả ngoài danh sách với chi phí bằng không.
3. **Video dư thừa.** Một logo vật lý tồn tại qua hàng trăm khung hình liên tiếp; một quyết định có thể gán nhãn cả một track.

Xây trên ba tín hiệu này, pipeline giáo viên–học trò (teacher–student) hoạt động như sau. Một *teacher* nặng — phân đoạn khái niệm được prompt bằng mẫu (SAM 3 [cần kiểm chứng]) kết hợp OCR đọc tên thương hiệu, phân cụm embedding DINOv2 *thực↔thực*, và tiên nghiệm danh sách — tự gán nhãn cả broadcast từ một mẫu mỗi brand; một *label model* kiểu Snorkel hợp nhất các nguồn nhãn nhiễu thành nhãn sạch kèm độ tin cậy; *tinh chỉnh theo thời gian* back-propagate các track dài ổn định để phục hồi khung bị bỏ sót và loại track chớp nháy. Danh tính được giải bằng một *dấu vân tay logo đa phương thức* — thị giác ⊕ văn bản ⊕ màu — cho phép mở rộng gallery *không cần train*. Để phủ điều kiện hiếm, một *bản sao số* dựng bằng 3D Gaussian Splatting chèn logo thật với compositing nhận biết ánh sáng, tạo khung quang-thực với nhãn chính xác pixel. Cuối cùng, nhãn của teacher (thực + tổng hợp) *chưng cất* một *student* YOLO realtime; mỗi sự kiện mở rộng gallery và student — một *bánh đà tự cải thiện* (self-improving flywheel).

Một biến thể *kiểm kê* (inventory) của ý tưởng này — thích hợp cho tài trợ trên kit — khai thác *Kit Regulation*: cả đội mặc một bộ kit giống hệt suốt mùa, nên logo ngực của mọi cầu thủ, mọi phút, mọi trận (cùng kit) là *cùng một* nhà tài trợ. Bài toán do đó không phải "phân loại N triệu crop mờ" mà là *kiểm kê*: định danh mỗi bề mặt vật lý *một lần* tại khoảnh khắc nét nhất cả mùa (pha cận cảnh, logo 200px+), rồi mọi crop mờ sau đó chỉ cần *gán về bề mặt nào* (bài toán hình học dễ) và thừa hưởng nhãn. Insight này biến một bài toán nhận dạng khó thành một bài toán kế toán dễ hơn nhiều — và là đóng góp phương pháp luận riêng của luận văn cho tài trợ trên kit.

Cần nhấn mạnh về mặt liêm chính: nhánh này được trình bày *cùng với các thất bại của nó* (Chương 5). "Annotation-free" ở đây hiểu đúng là *không cần nhãn để train*; hệ vẫn cần khoảng 30 phút xác nhận của con người cho khâu *đo* để con số đáng tin — đúng theo nguyên lý liêm chính đo lường ở Mục 3.1.

*(~2.550 từ cho Chương 3)*

---

# Chương 4. Triển khai dự án và Nghiên cứu điển hình

Chương này chuyển từ *thiết kế* sang *hiện thực*: nó mô tả việc dựng hệ thống trên một câu lạc bộ thật, các lựa chọn kỹ thuật cụ thể, và những bài học triển khai mà chỉ việc "chạm tay vào dữ liệu thật" mới bộc lộ. Xuyên suốt, chương duy trì một giọng phản biện: mỗi thành công được kể cùng chi phí và điều kiện của nó.

## 4.1. Bối cảnh Bradford Bulls

Bradford Bulls là một câu lạc bộ bóng bầu dục league có bề dày lịch sử nhưng hiện thi đấu ngoài nhóm tinh hoa tài chính của môn thể thao này — đúng phân khúc "hạng trung" mà luận văn muốn phục vụ. Câu lạc bộ bán nhiều slot tài trợ trên kit thi đấu cho các doanh nghiệp địa phương và khu vực (trong dữ liệu dự án xuất hiện các thương hiệu như KLG, MCP, Floor Tonic, ACS Group, MNA Cladding, Bartercard, AON, Romantica và nhiều tên khác). Câu hỏi nghiệp vụ mà mỗi nhà tài trợ đặt ra rất cụ thể: *"Logo của tôi xuất hiện bao nhiêu, rõ đến mức nào, và đáng giá bao nhiêu tiền media?"*. Trước dự án này, câu lạc bộ không có công cụ định lượng để trả lời — chính khoảng trống đó là động lực thực tế.

Bối cảnh Bradford cũng cung cấp các *điều kiện khó* lý tưởng để kiểm nghiệm tính bền vững: nhiều trận được phát trên các kênh stream chất lượng thấp, quay ban đêm dưới đèn pha, với các cặp đấu "kit tối gặp kit tối" (ví dụ trận gặp Toulouse, cả hai đội áo sẫm) — những tình huống đẩy bộ phân loại đội đến giới hạn. Dữ liệu video nguồn được thu từ các trận đầy đủ đăng công khai trên YouTube (tải bằng `yt-dlp`), trải nhiều mùa và điều kiện ánh sáng.

Một chi tiết bối cảnh có ý nghĩa phương pháp luận là *sự thay đổi kit theo mùa*: kit 2024 của Bradford là vàng-đen, trong khi tài liệu quy chuẩn kit 2025/26 (`Kit Regulations 2025 SPONSORS SIZINGS.pdf`) mô tả kit trắng. Điều này buộc quy trình khai thác dữ liệu phải chuyển sang các trận mùa 2025/26 để kit khớp với ảnh anchor — một minh hoạ cụ thể cho việc *tính hợp lệ của tham chiếu* quan trọng đến mức nào trong một hệ thống tham chiếu.

## 4.2. Dữ liệu và quy trình huấn luyện

Mô hình phát hiện logo production là một YOLO26 fine-tuned trên khoảng *1.100 hộp thủ công phủ 17 lớp thương hiệu* — quy mô nhỏ có chủ đích, phản ánh ràng buộc chi phí thực tế của một câu lạc bộ hạng trung. Chính sự nhỏ bé này làm cho câu hỏi *khả mở rộng không cần gán nhãn* (Mục 3.7) trở nên cấp thiết chứ không hàn lâm.

Một đóng góp phương pháp luận quan trọng của giai đoạn thực nghiệm là nhận thức về *giao thức tách dữ liệu* (data split protocol). Cùng một mô hình cho ra các con số rất khác nhau tuỳ cách tách train/test:

- **Tách khung ngẫu nhiên (random-frame):** mAP@0.5 = 0,862 — nhưng con số này *bị thổi phồng do rò rỉ* (leakage): các khung liền kề trong cùng một pha bóng lọt vào cả train lẫn test, khiến mô hình "đã thấy" gần như chính cảnh đó.
- **Tách rời theo clip (clip-disjoint):** mAP@0.5 = 0,702 — trung thực hơn vì không clip nào xuất hiện ở cả hai phía.
- **Tập mở rộng, nhận biết clip (extended clip-aware v2):** mAP@0.5 = 0,745 (P 0,65 / R 0,74) — con số headline hiện tại, cân bằng giữa quy mô dữ liệu và tính trung thực.

Bài học — mà luận văn coi là một đóng góp *về liêm chính đánh giá* — là con số 0,862 dễ gây ấn tượng nhưng *không được trích dẫn như hiệu năng thật*; con số 0,745 kém hấp dẫn hơn nhưng trung thực hơn. Việc chủ động báo cáo con số thấp hơn, kèm giải thích cơ chế rò rỉ, là một lựa chọn đạo đức nghiên cứu.

Về hạ tầng huấn luyện: fine-tuning được thực hiện trên GPU đám mây thuê (Google Colab, lớp A100/H100) vì thử nghiệm cho thấy tập mở rộng cần hơn một tuần trên phần cứng cấp tiêu dùng (một lần chạy 20/300 epoch mất 14,2 giờ ≈ 42 phút/epoch), trong khi *suy luận* (inference) chạy tốt trên máy local. Mô hình vận hành do đó là *"thuê để huấn luyện, sở hữu để suy luận"* — một cấu trúc chi phí đặc biệt phù hợp với tổ chức nhỏ.

## 4.3. Hiện thực backend

Backend được tổ chức theo module rõ ràng dưới `backend/app/`: `api/` (các route FastAPI cho jobs, analyses, teamrefs, health), `pipeline/` (toàn bộ logic xử lý), `db/` (mô hình và repository), `jobs/` (hàng đợi in-process), `storage/` (trừu tượng lưu trữ) và `models_zoo/` (đăng ký và nạp detector). Sự phân tách này hiện thực hoá nguyên lý "hạ tầng sau interface" ở cấp mã nguồn.

Trong `pipeline/`, mỗi giai đoạn là một module riêng: `detect_track.py` (phát hiện + tracking logo), `visibility.py` (tầng 1), `teamid/` (bộ lọc đội, gồm `jersey.py`, `features.py`, `classifier.py`, `tracker.py`, `bootstrap.py`), `pose.py` + `bodyzones.py` (gán slot), `exposure.py` (tầng 2), `pricing.py` (tầng 3), `annotate.py` + `av.py` (preview + ghép audio), và `bodyseg_yolo.py` + `bodyseg.py` (overlay). Kiến trúc module này khiến việc kiểm thử đơn vị khả thi — thư mục `tests/` chứa các test cho exposure, pricing, bodyzones, teamid và av, một dấu hiệu của kỷ luật kỹ thuật hiếm thấy ở prototype nghiên cứu.

API phơi bày một hợp đồng gọn: `POST /api/jobs` (multipart: video + eventName + audienceSize + placementType + cpmBase + kit) trả về `jobId`; `GET /api/jobs/{id}` để poll `status`/`progress`/`stage`/`stageDetail`; và khi xong, `GET /api/analyses/{id}` trả `AnalysisResult` đầy đủ cùng các endpoint media (`/video`, `/bodyseg-video`, `/export.csv`). Thiết kế này cho phép frontend là một client mỏng, thuần trình bày.

## 4.4. Hiện thực frontend

Frontend `logo-analytics/` biến dòng JSON khô khan thành công cụ ra quyết định. Năm tab phục vụ năm câu hỏi nghiệp vụ khác nhau:

- **Overview** — bức tranh danh mục đa trận: bốn KPI (Total EMV, Brands Tracked, Quality Exposure, Avg Visibility), biểu đồ xu hướng EMV theo thời gian, donut *share of voice* phân bố EMV theo brand, và bảng xếp hạng EMV theo trận.
- **Match Videos** — thư viện và chi tiết từng trận: tìm kiếm/lọc/sắp xếp, và khi mở một trận: KPI trận, *badge thống kê bộ lọc đội* (kept/dropped), video preview có audio với hộp phát hiện, và timeline per-brand có thể click để tua.
- **Brand Insights** — phân tích một thương hiệu xuyên hệ thống: sáu KPI (gồm EMV/giây và quality ratio), xu hướng EMV theo trận so với "brand trung bình", và một *radar 5 trục* so sánh brand với trung bình danh mục.
- **Analytics Report** — báo cáo có bộ lọc và xuất file: heatmap Brand × Match, *Appearance Quality Map* (scatter thời lượng × visibility, góc trên phải là "inventory cao cấp"), và xuất PDF/CSV.
- **Body Segmentation** — mô hình 3D xoay được với 18 slot tô màu, hover hiện %, xếp hạng zone — công cụ trực quan cho định giá theo vị trí (Mục 3.6).

Toàn bộ biểu đồ là SVG tự viết và tương tác; màu brand ổn định xuyên tab (đánh chỉ số theo xếp hạng EMV) để người dùng nhận diện thương hiệu nhất quán. Khi không có backend, frontend tự hiển thị dữ liệu mô phỏng gắn nhãn "demo" — một chi tiết nhỏ nhưng thể hiện tư duy sản phẩm.

## 4.5. Bản sao số (digital twin) và dữ liệu tổng hợp

Để phủ các điều kiện hiếm mà dữ liệu thật ít có (góc gắt, loá đèn, mưa), dự án thử nghiệm ba nguồn dữ liệu tổng hợp theo thứ tự tăng dần độ chân thực: (i) *copy-paste* logo lên nền thật; (ii) *diffusion inpainting* chèn logo theo ngữ cảnh; và (iii) một *bản sao số* của sân dựng bằng 3D Gaussian Splatting, sau đó chèn texture logo thật với compositing nhận biết ánh sáng và ngẫu nhiên hoá 6 bậc tự do. Logic then chốt của bản sao số là: *vì nền là cảnh thật và chỉ logo được chèn, nhãn chính xác đến pixel trong khi khoảng cách miền (domain gap) vẫn nhỏ*. Đây là một hướng đầy hứa hẹn nhưng, trung thực mà nói, ở giai đoạn nghiên cứu chứ chưa phải thành phần production đã kiểm chứng đầy đủ — nó được trình bày như một *đóng góp phương pháp và hướng tương lai* (Chương 8) hơn là một kết quả đã đo.

## 4.6. Kỹ thuật triển khai và các bẫy kỹ thuật

Một phần giá trị của nghiên cứu điển hình nằm ở những bài học kỹ thuật cụ thể mà chỉ việc triển khai thật mới lộ ra — chúng minh hoạ khoảng cách giữa "thuật toán trên giấy" và "hệ thống chạy được".

**Bẫy môi trường Windows.** Huấn luyện Ultralytics trên Windows đòi `workers=0` (nếu không sẽ gặp lỗi pagefile WinError 1455); mọi lệnh Python in tiếng Việt cần `PYTHONUTF8=1` để tránh crash mã hoá cp1252; và ffmpeg phải trỏ qua `imageio_ffmpeg.get_ffmpeg_exe()`. Những chi tiết này tầm thường về mặt lý thuyết nhưng quyết định việc hệ có chạy được hay không.

**Ràng buộc bộ nhớ và độ phân giải.** Mô hình phân đoạn nền tảng gặp tràn bộ nhớ (OOM) ở độ phân giải > 1036px trên GPU 16GB do cơ chế attention có độ phức tạp O(N²); giải pháp là *chia ô* (tiling) — hai ô ngang ở 644px cho thêm 36% số hộp phát hiện với cùng lượng VRAM. Đây là ví dụ điển hình của việc *ràng buộc phần cứng định hình thuật toán*, đúng theo tinh thần "đánh giá kỹ ràng buộc kỹ thuật ở mỗi bước".

**Bẫy phương pháp trong chính quá trình tự-gán-nhãn.** Nhánh không-gán-nhãn (Mục 3.7) bộc lộ nhiều bẫy tinh vi: *ID-switch* của tracker trong pha tranh chấp làm một track đã được gán nhãn "đổi chủ" (một cầu thủ đối phương lọt vào cụm mang nhãn nhà tài trợ Bradford); phân đoạn nền tảng đôi khi "kích hoạt" trên nếp gấp vải và tưởng đó là logo; và một bẫy ngữ nghĩa thú vị — họ cầu thủ "LAWRENCE" in trên lưng áo bị nhầm thành nhà tài trợ có tên tương tự, buộc phải rút một tuyên bố exposure sai trong báo cáo cũ. Mỗi bẫy này được xử lý bằng một *cổng kiểm soát* (temporal locality chống ID-switch, quality filter chống "cháy" nếp vải, luật ngữ nghĩa chống nhầm tên người) — và việc phải thêm các cổng đó là bằng chứng thực nghiệm cho luận điểm rằng *tự động hoá đo lường không loại bỏ con người mà tái phân bổ vai trò con người sang thiết kế các ràng buộc kiểm soát*.

*(~1.750 từ cho Chương 4)*

---

# Chương 5. Kết quả và Đánh giá

Chương này báo cáo bằng chứng thực nghiệm, được tổ chức theo bốn câu hỏi con. Nguyên tắc xuyên suốt (Mục 3.1): phân biệt phát biểu *vận hành* với phát biểu *chính xác*, và chỉ khẳng định độ chính xác khi có đánh giá độc lập của con người.

## 5.1. Độ chính xác phát hiện và quy gán (CHC1)

**Phát hiện logo.** Như đã nêu ở Mục 4.2, hiệu năng phụ thuộc mạnh vào giao thức tách. Bảng dưới tổng hợp:

| Giao thức tách | Run | mAP@0.5 | Ghi chú |
|---|---|---|---|
| Random-frame | `logo_yolo26m` | 0,862 | *Thổi phồng* do rò rỉ khung liền kề |
| Clip-disjoint | `logo_yolo26m_clipsplit` | 0,702 | Trung thực |
| Extended clip-aware v2 | `logo_yolo26m_v2_full-2` | **0,745** (P 0,65 / R 0,74) | **Headline** |

Phân tích ma trận nhầm lẫn trên split clip-disjoint cho thấy một tính chất đáng khích lệ: ma trận gần như thuần đường chéo *trừ hàng background* — nghĩa là detector *không nhầm thương hiệu này với thương hiệu khác*, mà chỉ *bỏ sót* các logo hiếm vào background. Với bài toán định giá, kiểu lỗi "bỏ sót" (làm EMV thấp đi) an toàn hơn nhiều so với kiểu lỗi "nhầm thương hiệu" (gán tiền cho sai nhà tài trợ). Đây là một kết quả *chất lượng lỗi* quan trọng ngang với con số mAP.

**Quy gán đội — audit thủ công phân tầng.** Vì không có ground-truth công khai, độ chính xác quy gán được đo bằng một audit người có kiểm soát: ba khung hình (ở mốc 55%, 75%, 95% thời lượng) mỗi trận × chín trận = 184 quan sát, mỗi nhãn được đối chiếu thủ công với màu áo. Kết quả: **91,8% đúng (169/184)** — chia thành nhóm TARGET (cầu thủ Bradford) 78/86 = 90,7% và OTHER 91/98 = 92,9%. Phân tích lỗi bộc lộ nguyên nhân có cấu trúc: 4/8 lỗi TARGET là *trọng tài/nhân viên sân mặc đồ nổi* (gợi ý cần một lớp "officials" thứ ba), phần còn lại là kit đối thủ; toàn bộ 7 lỗi OTHER dồn vào *giây đầu sau kickoff* (khi phiếu vote chưa ổn định) và trận "kit tối gặp kit tối". Những lỗi này *có hệ thống và giải thích được*, không phải nhiễu ngẫu nhiên — điều quan trọng vì lỗi có cấu trúc thì sửa được.

**Hiệu lực của bộ lọc đội.** Trên chín trận, bộ lọc loại **44% số phát hiện** (11.161/25.153, dao động 21–78% tuỳ trận) — tức nếu *không* lọc, EMV sẽ bị thổi phồng gần gấp đôi ở nhiều trận. Đây là bằng chứng định lượng trực tiếp cho tầm quan trọng của quy gán trong định giá tài trợ, một khía cạnh mà tài liệu logo detection thuần tuý thường bỏ qua.

## 5.2. Định giá và đóng góp của mô hình theo vị trí (CHC2)

Vì không tồn tại "giá đúng" khách quan cho EMV, đánh giá tầng định giá tập trung vào *tính hợp lý cấu trúc* và *độ nhạy tham số* thay vì so với một chân lý.

**Phân bố exposure theo thương hiệu và vị trí.** Trên tám trận, nhà tài trợ dẫn đầu gánh khoảng **41% tổng exposure đã trọng số** (9.383/22.863), cho thấy một phân bố lệch mạnh điển hình của tài trợ (logo ngực chính chi phối). Ở chiều vị trí, khoảng cách giữa slot cao nhất và thấp nhất lên tới **27×** về thời lượng hiển thị (ví dụ 110 giây so với 4 giây) — một biên độ đủ lớn để *biện minh cho việc định giá khác nhau theo vị trí* thay vì một mức chung. Đây chính là giá trị thực tiễn của mô hình 18-slot: nó biến trực giác "logo ngực đáng giá hơn logo tất" thành một tỉ số có thể đưa vào hợp đồng.

**Đóng góp của chất lượng-trọng-số.** Phân tích cho thấy các phát hiện có độ tin cậy thấp (conf < 0,4) chiếm *29% số lượng* nhưng chỉ *9,5% exposure đã trọng số chất lượng*; ngược lại, các phát hiện conf ≥ 0,8 đóng góp *64% exposure*. Điều này xác nhận rằng cơ chế trọng số chất lượng ba tầng *thực sự* dịch trọng lượng về phía các hiển thị rõ và đáng nhớ, đúng như thiết kế — chứ không chỉ đếm thô.

## 5.3. Phân tích độ nhạy và các thiên lệch đo lường

Một hệ thống định giá chỉ đáng tin nếu ta hiểu con số của nó nhạy thế nào với lựa chọn tham số. Ba phân tích được thực hiện.

**Độ nhạy ngưỡng.** Quét ngưỡng trên 13.439 phát hiện: nâng visibility floor từ 0,02 lên 0,05 *xoá 71%* exposure chất lượng, lên 0,1 *xoá tới 98%*; trong khi nâng confidence floor từ 0,25 lên 0,6 chỉ mất *dưới 5%*. Kết quả này biện minh mạnh cho lựa chọn visibility floor thấp (0,02) ở Mục 3.4: ngưỡng 0,1 mà một số tài liệu đề xuất sẽ *phá huỷ gần như toàn bộ tín hiệu tài trợ thật* vì logo tài trợ vốn nhỏ và lệch tâm. Nó cũng cho thấy con số EMV *nhạy với visibility floor hơn nhiều so với confidence floor* — một thông tin quan trọng để hiệu chỉnh có trách nhiệm.

**Thiên lệch tần suất lấy mẫu.** So sánh lấy mẫu 2 fps với xử lý native 50 fps trên một đoạn ba phút cho thấy 2 fps *đo dư +63%* tổng exposure so với native, do cơ chế "lượng tử hoá" 0,5 giây mỗi mẫu đơn cộng với việc nối khoảng trống (gap-bridge). Đây là một phát hiện quan trọng về *tính trung thực*: sai số này *lệch về phía có lợi cho nhà tài trợ*, nên phải được công bố minh bạch khi báo cáo cho khách hàng thay vì che giấu. Việc chủ động đo và tiết lộ một thiên lệch bất lợi cho lập luận bán hàng là một hành vi liêm chính nghiên cứu.

**Thông lượng (throughput).** Trên máy RTX 5060 Ti 16GB + i5-13400F + 16GB RAM, hệ đạt *xấp xỉ thời gian thực* (87,7 phút video / 88,4 phút xử lý ≈ 1,0×, dải 0,81–1,12×). Con số này chứng minh phát biểu *khả thi trên phần cứng cấp tiêu dùng* — điều kiện cần để dân chủ hoá công cụ cho câu lạc bộ nhỏ.

## 5.4. Đánh giá nhánh không-gán-nhãn (CHC3) — cả thành công và thất bại

Nhánh cỗ máy dữ liệu tự cải thiện được đánh giá *trung thực*, bao gồm các thất bại — vì che giấu chúng sẽ vi phạm nguyên lý liêm chính.

**Chuỗi kiểm kê (Bradford, một trận).** Từ 2.900 track (ByteTrack) → luật màu few-shot lọc còn 511 track Bradford → SAM3 khai thác 7.410 crop logo trên thân → phân cụm DINOv2 *thực↔thực* (τ = 0,65) → 189 cụm, trong đó các cụm thương hiệu đạt độ thuần ≥ 90% (ví dụ cụm KLG 11/12). Ba nhà tài trợ chủ chốt được *xác nhận* đúng slot: MCP ở ngực, KLG ở bụng và quần.

**Nhãn bootstrap và các cổng kiểm soát.** Ba lần lặp gán nhãn, mỗi lần audit bằng mắt: phiên bản 1 và 2 *thất bại* (v2 cho 1.275 nhãn nhưng độ thuần chỉ ~40–60% do ID-switch của tracker và "cháy" nếp vải); chỉ phiên bản 3 — qua *ba cổng đồng thời* (định vị thời gian ±6s quanh anchor ∧ lọc chất lượng ∧ giao của đồng thuận hình học và cụm) — cho **107 nhãn với độ thuần ~94%**, đạt cổng chất lượng. Bài học: *ít nhưng đúng*; mở rộng số lượng phải bằng *thêm video* chứ không phải nới lỏng cổng.

**Student chưng cất — đánh giá trung thực có kiểm soát rò rỉ.** Một smoke-test ban đầu cho mAP@0.5 = 0,92, nhưng khi phát hiện 9/12 ảnh val trùng track với train (cách nhau 0,64s), việc *tách lại theo track* kéo con số về **0,558** — một sự sụt giảm *đúng như kỳ vọng* khi loại rò rỉ. Trên track chưa từng thấy, KLG đạt mAP 0,867 (R 0,80) — *tín hiệu thật*; nhưng MCP thất bại (mAP 0,248, R 0) vì *đói dữ liệu* (chỉ ~23 crop, 7 track). Một FP-test trên 300 crop đối thủ/nhân viên cho thấy ≤ 3% ảnh có dương tính giả, và FP "nặng" nhất soi ra lại là *KLG thật* trên quần cầu thủ Bradford — nghĩa là mô hình *không bịa* thương hiệu lên áo đối thủ.

Kết luận trung thực của nhánh này: *pipeline được kiểm chứng là hoạt động về nguyên lý, nhưng thiếu hụt duy nhất và quyết định là SỐ LƯỢNG dữ liệu*. Đây là một kết quả có giá trị chính vì nó trung thực: nó cho biết chính xác cần đầu tư vào đâu (mở rộng khai thác video) thay vì tuyên bố thành công sớm.

## 5.5. Tổng hợp đánh giá

Đặt cạnh nhau, bằng chứng ủng hộ ba phát biểu có mức độ chắc chắn khác nhau. *Chắc chắn cao:* hệ thống production đo được exposure và EMV ở thời gian thực trên phần cứng rẻ, với quy gán đội chính xác ~92% theo audit người, và bộ lọc đội tạo khác biệt định lượng lớn (44%). *Chắc chắn vừa:* mô hình định giá cho ra phân bố hợp lý và nhạy có kiểm soát với tham số, dù thiếu một ground-truth EMV để đo sai số tuyệt đối. *Còn mở:* nhánh không-gán-nhãn đúng về nguyên lý nhưng chưa chứng minh ở quy mô — đây là công việc còn lại rõ ràng nhất.

*(~1.700 từ cho Chương 5)*

---

# Chương 6. Thảo luận

## 6.1. Định giá bằng AI như đối trọng tất yếu của sáng tạo bằng AI

Trở lại luận điểm trung tâm (CHC4). Số đặc biệt *AI and the Future of Advertising Creativity* đóng khung generative AI như lực tái sắp xếp cách quảng cáo được *hình dung, tạo ra, đánh giá và định giá*. Kết quả của luận văn cho phép một khẳng định lý thuyết cụ thể: khi AI làm sụp đổ chi phí *sản xuất* sáng tạo, giá trị kinh tế dịch chuyển sang khả năng *phân biệt cái gì đáng giá* — và đó là địa hạt của AI đo lường. Hai loại AI này không cạnh tranh mà *bổ sung*: generative AI mở rộng không gian khả năng sáng tạo (nghìn biến thể, nghìn vị trí đặt logo khả dĩ), trong khi valuation AI thu hẹp không gian đó về các lựa chọn thực sự có giá trị. Nếu không có đối trọng đo lường, sự bùng nổ nguồn cung sáng tạo chỉ tạo ra một biển nhiễu không định giá được; có nó, mỗi biến thể trở thành một giả thuyết có thể kiểm nghiệm về giá trị.

Mô hình 18-slot minh hoạ sự bổ sung này một cách cụ thể. Bằng cách biến "vị trí đặt logo trên kit" thành một biến có *giá đo được* (chênh 27× giữa slot cao và thấp), hệ thống đo lường *thông tin ngược* cho quyết định sáng tạo: một câu lạc bộ giờ có thể trả lời "nên bán slot nào với giá bao nhiêu" và một thương hiệu có thể trả lời "nên mua vị trí nào". Vòng phản hồi đo-lường → thiết-kế này chính là hình thức mà "tương lai của sáng tạo quảng cáo" mang lấy ở phía tài trợ: sáng tạo được *dẫn dắt bởi dữ liệu định giá*.

## 6.2. Đồng sáng tạo người–AI trong đo lường

Dòng tài liệu AI-quảng cáo nhấn mạnh *đồng sáng tạo giá trị người–AI* ở phía sản xuất. Luận văn mở rộng khái niệm này sang phía *đo lường*. Kinh nghiệm triển khai (Mục 4.6, 5.4) cho thấy tự động hoá không loại bỏ con người mà *tái phân bổ* vai trò của họ: người vận hành không còn *gán nhãn hàng nghìn khung hình* mà chuyển sang *kiểm định* (khoảng 30 phút audit phân tầng mỗi báo cáo) và *thiết kế các cổng kiểm soát* (temporal locality, quality filter, luật ngữ nghĩa chống nhầm tên người). Đây là một dạng đồng sáng tạo: AI đảm nhận khối lượng tri giác, con người đảm nhận phán đoán về tính hợp lệ và ý nghĩa.

Quan trọng hơn, chính *cấu trúc của lỗi* cho thấy vì sao con người vẫn cần thiết: các lỗi có hệ thống (trọng tài đồ nổi bị nhầm là cầu thủ, họ "LAWRENCE" bị nhầm là nhà tài trợ) là những lỗi mà chỉ *hiểu biết ngữ cảnh của con người* mới phát hiện và mã hoá thành ràng buộc được. Nói cách khác, con người không phải là "khâu còn sót lại chờ được tự động hoá nốt" mà là *nguồn của các tiên nghiệm ngữ nghĩa* mà hệ thống cần để đo đúng.

## 6.3. Dân chủ hoá năng lực định giá

Phát hiện có ý nghĩa thực tiễn lớn nhất là *tính khả thi chi phí thấp*: toàn hệ chạy xấp xỉ thời gian thực trên một GPU cấp tiêu dùng, với mô hình "thuê để huấn luyện, sở hữu để suy luận". Điều này hạ rào cản để một câu lạc bộ hạng trung như Bradford Bulls — vốn không đủ khả năng thuê Nielsen Sports hay Relo Metrics — tự đo và *chứng minh giá trị bằng dữ liệu* cho nhà tài trợ. Xét về hàm ý ngành, đây là một sự dịch chuyển quyền lực đo lường từ số ít nhà cung cấp đắt đỏ sang số đông tổ chức nhỏ — song song với cách generative AI hạ rào cản *sản xuất* sáng tạo cho các agency nhỏ. Cùng một logic dân chủ hoá vận hành ở cả hai phía cung và cầu của sáng tạo quảng cáo.

## 6.4. Hàm ý lý thuyết và thực tiễn

Về *lý thuyết*, luận văn đề xuất bổ sung một trục còn thiếu vào khung "tương lai của sáng tạo quảng cáo": trục *đo lường–định giá bằng AI*, với luận điểm rằng nó là điều kiện cần để sự bùng nổ sáng tạo do genAI tạo ra trở thành giá trị kinh tế chứ không phải nhiễu. Về *phương pháp*, luận văn đóng góp nguyên lý *liêm chính đo lường* (không lấy đầu ra teacher làm gold; báo cáo giao thức tách trung thực; công bố cả thiên lệch bất lợi) như một chuẩn mực cho nghiên cứu đo lường quảng cáo bằng AI. Về *thực tiễn*, mô hình định giá theo vị trí và bộ lọc đội an-toàn-doanh-thu cung cấp các mẫu thiết kế tái sử dụng được cho bất kỳ tổ chức nào muốn tự đo giá trị tài trợ.

*(~1.100 từ cho Chương 6)*

---

# Chương 7. Giới hạn của nghiên cứu

Tính chính đáng của một luận văn khoa học thiết kế phụ thuộc vào việc nêu rõ giới hạn của chính nó. Luận văn nhận diện năm giới hạn chính.

**Thiếu ground-truth EMV tuyệt đối.** Vì không tồn tại "giá đúng" khách quan cho giá trị hiển thị, luận văn không thể báo cáo *sai số tuyệt đối trung bình* (MAE) của EMV so với một chân lý. Đây là giới hạn quan trọng nhất và cũng là *phép đo còn thiếu quan trọng nhất*: một hướng đo tương lai là so exposure hệ thống với thời lượng bấm giờ thủ công của con người trên một mẫu, để lượng hoá sai số. Hiện tại, đánh giá tầng định giá chỉ đạt mức *tính hợp lý cấu trúc và độ nhạy*, không phải *độ đúng*.

**Quy mô và tính khái quát.** Kết quả được đo trên một môn thể thao (bóng bầu dục league), một câu lạc bộ chính (Bradford Bulls) và hàng chục trận. Tuyên bố "sport-agnostic" và "generic" (đội khác thả logo vào là chạy) là *mục tiêu thiết kế đã được kiến trúc hoá* nhưng *chưa được chứng minh thực nghiệm ở quy mô* — cột mốc club thứ hai với zero code change vẫn là công việc còn lại. Con số hiệu năng có thể khác đáng kể ở môn thể thao có động lực học thị giác khác (ví dụ bóng đá sân rộng, góc máy xa).

**Khoảng cách miền của dữ liệu tổng hợp.** Bản sao số Gaussian-splatting và các nguồn tổng hợp khác là hướng hứa hẹn nhưng ở giai đoạn nghiên cứu; nếu trộn không cẩn thận với dữ liệu thật, chúng có thể gây *trôi sim-to-real* (mô hình học đặc trưng của ảnh tổng hợp thay vì logo thật). Đóng góp digital-twin do đó được trình bày như *phương pháp và hướng tương lai* chứ không phải kết quả đã kiểm chứng.

**Phụ thuộc giả định danh sách biết trước.** Tiên nghiệm danh sách (roster prior) — nền tảng của hiệu quả nhánh không-gán-nhãn — chỉ đúng cho các giải chuyên nghiệp có danh sách nhà tài trợ công bố; nó không áp dụng cho video tuỳ ý. Ngoài ra, một số thành phần nghiên cứu (ví dụ một số detector text-only) có giấy phép chỉ dùng cho nghiên cứu; một triển khai thương mại phải thay bằng thành phần có giấy phép phù hợp.

**Giới hạn đạo đức và riêng tư.** Hệ thống chủ đích *không* thực hiện nhận dạng danh tính cá nhân cầu thủ hay khán giả — nó phân tích *phơi bày thương hiệu*, không phân tích con người. Đây vừa là lựa chọn đạo đức đúng đắn vừa là giới hạn phạm vi có chủ đích. Tuy vậy, việc xử lý video có mặt người vẫn đặt ra nghĩa vụ về đồng thuận và bảo mật dữ liệu; các tuyên bố đạo đức trong báo cáo cần được đối chiếu với thoả thuận thực tế với câu lạc bộ trước khi công bố, và những khung hình thô lộ danh tính câu lạc bộ (biển điểm, huy hiệu, watermark kênh) cần được che (redact) khi dùng làm minh hoạ.

*(~640 từ cho Chương 7)*

---

# Chương 8. Kết luận và Hướng phát triển

## 8.1. Kết luận

Luận văn xuất phát từ một quan sát về sự dịch chuyển của khan hiếm trong ngành quảng cáo: khi generative AI công nghiệp hoá khâu *sản xuất* sáng tạo, nút thắt giá trị dời sang khâu *đánh giá và định giá*. Trả lời câu hỏi nghiên cứu tổng quát, luận văn đã thiết kế, hiện thực và đánh giá **LogoLens** — một hệ thống thị giác máy tính đầu-cuối đo lường và định giá mức độ hiển thị của logo tài trợ trên phát sóng thể thao, gồm một backend pipeline tám giai đoạn kết nối với một dashboard phân tích đa trận.

Về CHC1, hệ đạt mAP@0.5 = 0,745 ở giao thức tách trung thực và độ chính xác quy gán đội ~91,8% theo audit người có kiểm soát, với bộ lọc đội loại 44% phát hiện lẽ ra làm thổi phồng EMV. Về CHC2, mô hình định giá ba tầng và mô hình 18-slot biến dòng phát hiện thô thành EMV có cơ sở và bộc lộ chênh lệch 27× giữa các vị trí đặt logo, cung cấp nền tảng định lượng cho định giá vi mô. Về CHC3, nhánh cỗ máy dữ liệu tự cải thiện được chứng minh đúng về nguyên lý (tín hiệu học thật trên track chưa thấy) nhưng bị giới hạn bởi số lượng dữ liệu — một kết luận trung thực chỉ rõ hướng đầu tư tiếp theo. Về CHC4, luận văn đề xuất định vị *định giá bằng AI* như đối trọng tất yếu của *sáng tạo bằng AI*, và tái khái niệm hoá vai trò con người từ "người gán nhãn" thành "người kiểm định và người thiết kế ràng buộc" — một hình thức đồng sáng tạo người–AI ở phía đo lường.

Đóng góp bao trùm, xét theo tinh thần của số đặc biệt, là bằng chứng rằng *dân chủ hoá năng lực định giá* cho các tổ chức nhỏ là khả thi về mặt kỹ thuật và có ý nghĩa về mặt lý thuyết — và rằng tương lai của sáng tạo quảng cáo sẽ không chỉ được viết ở phía những gì AI *tạo ra*, mà còn ở phía những gì AI giúp con người *định giá*.

## 8.2. Hướng phát triển

Sáu hướng phát triển tự nhiên nối tiếp các giới hạn ở Chương 7:

1. **Đo sai số EMV tuyệt đối.** So exposure hệ thống với thời lượng bấm giờ thủ công trên một mẫu phân tầng để báo cáo MAE — phép đo còn thiếu quan trọng nhất.
2. **Chứng minh tính khái quát liên môn/liên CLB.** Thực thi cột mốc "club thứ hai với zero code change" và mở rộng sang môn thể thao khác để kiểm nghiệm tuyên bố generic.
3. **Mở rộng khai thác video cho nhánh không-gán-nhãn.** Khai thác 3–5 trận YouTube nữa để đạt 2–5k nhãn sạch, huấn luyện lại student với val tách theo trận — giải quyết trực tiếp nút thắt "đói dữ liệu".
4. **Hoàn thiện và kiểm chứng bản sao số.** Xác thực dữ liệu Gaussian-splatting với logo insertion nhận biết ánh sáng cho các điều kiện hiếm, với quy trình trộn thật/tổng hợp có kiểm soát chống trôi sim-to-real.
5. **Định giá phản thực (counterfactual) theo từng nhà tài trợ.** Mô hình hoá hiện tượng "đếm dư" khi nhiều logo xuất hiện cùng khung, để phân bổ giá trị công bằng hơn giữa các nhà tài trợ cùng ngành.
6. **Thích ứng trực tiếp theo sự kiện và tự-giám-sát render-and-verify.** Cho hệ tự cập nhật gallery và student ngay trong lúc xử lý một sự kiện mới, hướng tới bánh đà tự cải thiện vận hành liên tục.

Nhìn xa hơn, hướng phát triển tham vọng nhất là khép kín vòng phản hồi giữa *đo lường* và *sáng tạo*: dùng đầu ra định giá theo vị trí để *đề xuất* thiết kế kit và chiến lược đặt logo tối ưu — đưa hệ thống từ một công cụ *đo giá trị* thành một công cụ *đồng thiết kế giá trị*, đúng vào trung tâm của câu hỏi về tương lai của sáng tạo quảng cáo trong kỷ nguyên AI.

*(~740 từ cho Chương 8)*

---

# Tài liệu tham khảo (References — APA 7th)

> **Lưu ý xác minh.** Các mục đánh dấu **[cần kiểm chứng]** là đề xuất trích dẫn dựa trên nội dung dự án hoặc kết quả tìm kiếm; cần xác minh tác giả, năm, số trang/DOI chính xác trước khi nộp. Các mục còn lại là công trình đã được thiết lập trong tài liệu nhưng vẫn nên đối chiếu định dạng APA 7th với nguồn gốc.

Aharon, N., Orfaig, R., & Bobrovsky, B.-Z. (2022). *BoT-SORT: Robust associations multi-pedestrian tracking*. arXiv. https://arxiv.org/abs/2206.14651

Breuer, C., & Rumpf, C. (2012). The viewer's reception and processing of sponsorship information in sport telecasts. *Journal of Sport Management, 26*(6), 521–531. https://doi.org/10.1123/jsm.26.6.521

Cornwell, T. B. (2019). Less "sponsorship as advertising" and more sponsorship-linked marketing as authentic engagement. *Journal of Advertising, 48*(1), 49–60. https://doi.org/10.1080/00913367.2019.1588809

Cornwell, T. B., & Kwon, Y. (2020). Sponsorship-linked marketing: Research surpluses and shortages. *Journal of the Academy of Marketing Science, 48*(4), 607–629. https://doi.org/10.1007/s11747-019-00654-w

Davenport, T., Guha, A., Grewal, D., & Bressgott, T. (2020). How artificial intelligence will change the future of marketing. *Journal of the Academy of Marketing Science, 48*(1), 24–42. https://doi.org/10.1007/s11747-019-00696-0

Deliège, A., Cioppa, A., Giancola, S., Seikavandi, M. J., Dueholm, J. V., Nasrollahi, K., Ghanem, B., Moeslund, T. B., & Van Droogenbroeck, M. (2021). SoccerNet-v2: A dataset and benchmarks for holistic understanding of broadcast soccer videos. In *Proceedings of the IEEE/CVF Conference on Computer Vision and Pattern Recognition Workshops (CVPRW)* (pp. 4508–4519). https://arxiv.org/abs/2011.13367

Huang, M.-H., & Rust, R. T. (2021). A strategic framework for artificial intelligence in marketing. *Journal of the Academy of Marketing Science, 49*(1), 30–50. https://doi.org/10.1007/s11747-020-00749-9

Jocher, G., Chaurasia, A., & Qiu, J. (2023). *Ultralytics YOLO* (Version 8.x) [Computer software]. https://github.com/ultralytics/ultralytics **[cần kiểm chứng phiên bản/định dạng]**

Journal of Advertising Research. (2025). *AI and the future of advertising creativity* [Call for papers, special issue]. Taylor & Francis. https://think.taylorandfrancis.com/special_issues/ai-and-the-future-of-advertising-creativity/ **[cần kiểm chứng năm/biên tập viên khách mời]**

Journal of Advertising. (2025). *Generative AI and advertising: Building new theoretical frontiers* [Call for papers]. https://ispr.info/2025/09/15/call-generative-ai-and-advertising-building-new-theoretical-frontiers-issue-of-journal-of-advertising/ **[cần kiểm chứng]**

Kerbl, B., Kopanas, G., Leimkühler, T., & Drettakis, G. (2023). 3D Gaussian splatting for real-time radiance field rendering. *ACM Transactions on Graphics, 42*(4), 1–14. https://doi.org/10.1145/3592433

Kirillov, A., Mintun, E., Ravi, N., Mao, H., Rolland, C., Gustafson, L., Xiao, T., Whitehead, S., Berg, A. C., Lo, W.-Y., Dollár, P., & Girshick, R. (2023). Segment anything. In *Proceedings of the IEEE/CVF International Conference on Computer Vision (ICCV)* (pp. 4015–4026). https://arxiv.org/abs/2304.02643

Liu, S., Zeng, Z., Ren, T., Li, F., Zhang, H., Yang, J., Li, C., Yang, J., Su, H., Zhu, J., & Zhang, L. (2023). *Grounding DINO: Marrying DINO with grounded pre-training for open-set object detection*. arXiv. https://arxiv.org/abs/2303.05499

Nielsen Sports. (2019). *The changing value of sponsorship: Measuring media value in sports* [Industry report]. Nielsen. **[cần kiểm chứng tiêu đề/năm]**

Oquab, M., Darcet, T., Moutakanni, T., Vo, H., Szafraniec, M., Khalidov, V., Fernandez, P., Haziza, D., Massa, F., El-Nouby, A., Assran, M., Ballas, N., Galuba, W., Howes, R., Huang, P.-Y., Li, S.-W., Misra, I., Rabbat, M., Sharma, V., … Bojanowski, P. (2023). *DINOv2: Learning robust visual features without supervision*. arXiv. https://arxiv.org/abs/2304.07193

Radford, A., Kim, J. W., Hallacy, C., Ramesh, A., Goh, G., Agarwal, S., Sastry, G., Askell, A., Mishkin, P., Clark, J., Krueger, G., & Sutskever, I. (2021). Learning transferable visual models from natural language supervision. In *Proceedings of the 38th International Conference on Machine Learning (ICML)* (pp. 8748–8763). https://arxiv.org/abs/2103.00020

Ratner, A., Bach, S. H., Ehrenberg, H., Fries, J., Wu, S., & Ré, C. (2017). Snorkel: Rapid training data creation with weak supervision. *Proceedings of the VLDB Endowment, 11*(3), 269–282. https://doi.org/10.14778/3157794.3157797

Ravi, N., Gabeur, V., Hu, Y.-T., Hu, R., Ryali, C., Ma, T., Khedr, H., Rädle, R., Rolland, C., Gustafson, L., Mintun, E., Pan, J., Alwala, K. V., Carion, N., Wu, C.-Y., Girshick, R., Dollár, P., & Feichtenhofer, C. (2024). *SAM 2: Segment anything in images and videos*. arXiv. https://arxiv.org/abs/2408.00714

Redmon, J., Divvala, S., Girshick, R., & Farhadi, A. (2016). You only look once: Unified, real-time object detection. In *Proceedings of the IEEE Conference on Computer Vision and Pattern Recognition (CVPR)* (pp. 779–788). https://arxiv.org/abs/1506.02640

Relo Metrics. (2022). *The benefits of sponsor media value and how it is calculated* [Blog post]. https://blog.relometrics.com/the-benefits-of-sponsor-media-value-and-how-it-is-calculated **[cần kiểm chứng năm]**

Rumpf, C., Boronczyk, F., & Breuer, C. (2020). Predicting consumer gaze behavior toward sponsorship stimuli in sport broadcasts. *European Sport Management Quarterly, 20*(4), 461–479. https://doi.org/10.1080/16184742.2019.1620838 **[cần kiểm chứng số trang]**

*[Tác giả ExposureEngine]*. (2025). *ExposureEngine: [tiêu đề đầy đủ]*. arXiv. https://arxiv.org/abs/2510.04739 **[cần kiểm chứng tác giả/tiêu đề/năm]**

*[Nhóm SAM 3]*. (2025). *SAM 3: [tiêu đề đầy đủ]*. **[cần kiểm chứng — công bố gần đây]**

Xu, C., Zhu, G., & Shu, J. (2021). SeeTek: Very large-scale open-set logo recognition with text-aware metric learning. In *Proceedings of the IEEE/CVF Winter Conference on Applications of Computer Vision (WACV)*. **[cần kiểm chứng]**

Zhai, X., Mustafa, B., Kolesnikov, A., & Beyer, L. (2023). Sigmoid loss for language image pre-training (SigLIP). In *Proceedings of the IEEE/CVF International Conference on Computer Vision (ICCV)*. https://arxiv.org/abs/2303.15343

Zhang, Y., Sun, P., Jiang, Y., Yu, D., Weng, F., Yuan, Z., Luo, P., Liu, W., & Wang, X. (2022). ByteTrack: Multi-object tracking by associating every detection box. In *Proceedings of the European Conference on Computer Vision (ECCV)* (pp. 1–21). https://arxiv.org/abs/2110.06864

---

# Phụ lục (Appendices)

## Phụ lục A — Bảng cấu hình hệ thống chính

| Tham số | Giá trị mặc định | Ý nghĩa |
|---|---|---|
| `SAMPLE_FPS` | 2 | Tần suất lấy mẫu khung cho lượt analytics |
| Logo detect `imgsz` | 1280 | Độ phân giải đầu vào YOLO26 |
| `VISIBILITY_FLOOR` | 0,02 | Sàn visibility để tạo segment |
| `MIN_SEGMENT_SECONDS` | 0,5 | Ngưỡng độ dài segment tối thiểu |
| Duration weight | 0,5 / 1,0 / 1,2 | <1s / 1–5s / >5s |
| `CPM` mặc định | 22,0 USD | Đầu vào EMV |
| Placement multiplier | 1,0 / 1,4 / 0,85 / 0,7 | Live TV / Highlight / Stream / Social |
| `TEAM_KEEP_UNKNOWN` | true | An toàn doanh thu: giữ khi thiếu bằng chứng |
| `TEAM_MIN_VOTES` | 2,0 | Khối lượng phiếu trước khi tin nhãn OTHER |
| `TEAM_HYSTERESIS` | 1,25 | Độ lì của nhãn vote |
| `TEAM_BOOTSTRAP_FRAMES` | 32 | Số khung sample khi bootstrap refs |

## Phụ lục B — Tổng hợp số liệu thực nghiệm

| Chỉ số | Giá trị | Nguồn/Điều kiện |
|---|---|---|
| mAP@0.5 (random-frame) | 0,862 | Thổi phồng do rò rỉ — không trích dẫn như hiệu năng thật |
| mAP@0.5 (clip-disjoint) | 0,702 | Trung thực |
| mAP@0.5 (extended clip-aware) | 0,745 (P 0,65 / R 0,74) | Headline |
| Độ chính xác quy gán đội | 91,8% (169/184) | Audit người, 3 khung × 9 trận |
| Bộ lọc đội loại bỏ | 44% (11.161/25.153) | 9 trận, dải 21–78% |
| conf < 0,4 | 29% số lượng / 9,5% exposure trọng số | 8 trận |
| conf ≥ 0,8 | 64% exposure | 8 trận |
| Nhạy floor 0,02→0,1 | xoá tới 98% exposure | 13.439 phát hiện |
| Nhạy conf 0,25→0,6 | mất <5% | 13.439 phát hiện |
| Thiên lệch lấy mẫu 2fps vs 50fps | +63% đo dư | Đoạn 3 phút |
| Thông lượng | ~1,0× realtime (0,81–1,12×) | RTX 5060 Ti 16GB |
| Chênh lệch slot cao/thấp | tới 27× | Ví dụ 110s vs 4s |
| Exposure nhà tài trợ dẫn đầu | ~41% (9.383/22.863) | 8 trận |

## Phụ lục C — Sơ đồ luồng người dùng

```
Mở dashboard → New Analysis → upload video + nhập event/audience/CPM + chọn kit
     ↓
Màn processing (5 bước realtime: frames → team → detect → exposure → EMV)
     ↓
Match Analysis: video preview (box + audio) + timeline per-brand + brand breakdown
     ↓
Overview / Brand Insights / Analytics Report: tổng hợp đa trận, filter, export PDF/CSV
     ↓
Body Segmentation: mô hình 3D 18 slot → thuyết trình pricing theo vị trí
```

## Phụ lục D — Ghi chú về giả định và tính minh bạch

Các giả định chính đã nêu trong luận văn: (i) cơ sở đào tạo và chương trình học được giả định theo bối cảnh dự án (University of Bradford) — cần thay bằng thông tin thực tế; (ii) một số trích dẫn học thuật được đề xuất và đánh dấu *[cần kiểm chứng]*; (iii) mô hình EMV được coi là *proxy chuẩn ngành* cho chú ý, không phải giá bán thực; (iv) các con số định lượng trích từ nhật ký thực nghiệm dự án và có thể thay đổi khi mở rộng dữ liệu. Người đọc/hội đồng nên đối chiếu Phụ lục B với các bản ghi gốc (`results.csv`, `track_label_audit.csv`) trước khi sử dụng cho mục đích chính thức.

---

*Hết luận văn.*
