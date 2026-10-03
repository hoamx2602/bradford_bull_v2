# Bradford Bulls — bàn giao CV và presentation

Mở `index.html` để xem 6 video; mở `presentation/Bradford_Bulls_Findings_Final.pptx` để trình bày. Các biểu đồ trong PowerPoint có thể chỉnh sửa. Video được bàn giao riêng để chèn vào slide hoặc phát từ gallery.

## Bộ dữ liệu mới chạy

- Footage thật: `M08_white_1080p.mp4`, Bradford áo trắng, Hull áo tím/xanh.
- Hai đoạn: 18–28 giây và 84–96 giây của file nguồn (khác đồng hồ thi đấu trên màn hình).
- 550 frame, 25 fps, đầu ra 1280×720 H.264.
- Mỗi đoạn có `no_split.mp4`, `team_split.mp4`, `body.mp4`.
- 583 lượt detection trước lọc; 407 lượt được giữ sau lọc ở lần chạy cuối. Đây là lượt detection theo frame, không phải số logo riêng biệt hoặc phép đo accuracy.
- `*_detections.json` và `*_persons.json` lưu đầu ra để kiểm tra; `manifest.json` ghi nguồn và cấu hình; `video_validation.json` ghi kiểm tra giải mã.
- Ảnh theo timestamp, bốn ảnh vị trí tài trợ và heatmap đều lấy từ kết quả code. Không dùng ảnh AI giả làm output hệ thống.

## Đã sửa trong code

Tham chiếu team theo video hiện tại; không cắt lại ảnh kit vốn đã cắt torso; bảo toàn đỏ/vàng khỏi bộ lọc da; thêm đặc trưng saturation; dùng bằng chứng màu riêng cho home kit Bradford hiện tại; bỏ phiếu có suy giảm; reset nhãn ở chuyển cảnh; trạng thái unknown; thu hẹp khoảng gán logo cho người; sửa khởi tạo model YOLO.

Body segmentation ghép mask–pose một-một, không suy diễn torso khi thiếu hông, tô xám vùng không đủ bằng chứng, không cộng trùng pixel chồng lấp. Demo dùng YOLO11x-seg/pose. Các chỉnh sửa mã không tự thay thế cấu hình model đang chạy trong app; khởi động lại backend để nạp code mới.

## Cách đọc slide

- So sánh Match 1/2 dùng phân tích lịch sử trong database, **chưa chạy lại toàn trận sau bản sửa này**.
- Human là trọng số cấu hình, tổng 95; biểu đồ chuẩn hóa thành 100%. Chưa có rate card/hợp đồng chính thức hoặc nhãn manual từng frame để xác minh.
- Chỉ số 85.2% mAP@50 là log validation của detector ở epoch 22, không phải accuracy của team split/body segmentation, và không phải benchmark mới chạy.
- Heatmap là mật độ bounding box logo theo màn hình; không phải tọa độ sân hoặc thống kê chạy của cầu thủ.
- Torso/arm/leg là ước lượng giải phẫu từ pose. Phân vùng slot tài trợ chest/back/sleeve là bước riêng; không được đồng nhất hai loại vùng.

## Giới hạn còn lại

Pha tackle, người nằm ngang, cơ thể bị cắt, áo nằm trong bóng râm và người chồng lấp vẫn có thể sai hoặc chưa xác định. Cấu hình demo loại các track chưa đủ bằng chứng (`team_keep_unknown=false`); số lượt bị loại không đồng nghĩa tất cả là false positive. Nhận dạng home kit dựa trên trắng/đỏ/vàng hiện tại và cần rà lại nếu đổi kit hoặc đối thủ có màu tương tự. Heuristic chuyển cảnh có thể reset khi camera thay đổi mạnh.

Đã chạy toàn bộ 36 test backend ở vòng tích hợp; sau các sửa màu/chuyển cảnh cuối, 25 test liên quan team, CV, body zone và visibility đều qua. Đây là kiểm thử logic, không thay thế bộ nhãn rugby để đo accuracy. Xem `docs/13-cv-review-and-club-demo.md` và các script `backend/scripts/*club*`, `refresh_team_demo.py` để tái chạy.

Đề xuất trước khi thay đổi giá: club xác nhận mapping logo/slot và bảng giá, gán nhãn một mẫu đa dạng góc quay, đo precision/recall team và chất lượng body mask, rồi chạy lại toàn trận.
