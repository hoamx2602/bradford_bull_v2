# Kiểm tra team split và màu logo — 16/09/2026

**Kết luận: chưa đủ bằng chứng để gọi team split là đã tối ưu.** Các cảnh người tách nhau cho kết quả dễ kiểm tra; cảnh đông người vẫn có nhiều trường hợp chưa xác định. Chưa có bộ nhãn chuẩn độc lập để đo precision/recall theo đội, lỗi gán chủ logo hoặc chọn tham số tối ưu.

## Kết quả chạy thật trên 90 giây

Chạy lại TeamTracker trên cùng 2.250 frame, giữ nguyên 6.639 dự đoán logo. Đây là số lượt theo frame, không phải số logo/cầu thủ duy nhất và không phải accuracy.

| Trạng thái chủ logo | Trước | Sau kiểm tra đồng thuận |
|---|---:|---:|
| Dự đoán Bradford | 4.579 | 4.574 |
| Chưa chắc chắn | 1.766 | 1.792 |
| Đội khác/trọng tài | 219 | 198 |
| Không gán được người | 75 | 75 |

26 lượt logo chuyển từ nhãn đội sang chưa chắc chắn: 5 từ Bradford, 21 từ Other. Đây là tránh quyết định khi phiếu mâu thuẫn, không phải 26 lỗi đã chứng minh được sửa. Ở cấp người, 176 lượt người/frame chuyển sang chưa chắc chắn. Sau thay đổi, 27,0% lượt logo thuộc nhóm chưa chắc chắn; không được diễn giải thành tỷ lệ sai 27%.

Ảnh kiểm tra: `frame_0175.jpg` (nguồn 00:19: ba cầu thủ Bradford và một cầu thủ Hull nổi bật được tách đúng qua quan sát), `frame_1300.jpg` (nguồn 04:42: nhiều khung người chồng nhau, một số người chưa chắc chắn). Đây là quan sát định tính, không phải tập kiểm thử đại diện.

## Các kỹ thuật thực sự đang chạy

- YOLO11m phát hiện người, BoT-SORT theo dõi ID; crop áo ở 15–45% chiều cao bounding box.
- Màu áo, chất lượng crop, loại phiếu từ người chồng lấn mạnh; tích lũy phiếu theo track, hysteresis và reset khi chuyển cảnh.
- Riêng kit `home`: bỏ qua SigLIP và dùng quy tắc trắng/đỏ/vàng, đối chiếu xanh/tím/xanh lá. Margin phân loại cho quy tắc là hằng số 0.75, không phải xác suất đã hiệu chỉnh. Vì vậy không nên mô tả demo home là kết quả tối ưu fusion màu + SigLIP.
- Gán logo cho bounding box người nhỏ nhất chứa tâm logo; fallback theo khoảng cách gần mép. Chưa dùng instance mask/depth để xác định chủ logo.

## Tham số thực tế và nhận xét

| Tham số | Giá trị | Nhận xét |
|---|---:|---|
| Person confidence | 0.35 | Chưa có sweep với nhãn chuẩn để chứng minh tốt nhất |
| Person image size | 960 | Cần đánh giá recall người nhỏ và tốc độ trên cảnh rộng |
| Hysteresis | 1.25 | Giảm đổi nhãn, nhưng có thể giữ nhãn cũ khi track đổi người |
| Vote mass tối thiểu | 2.0 | Tổng phiếu không thể thay thế độ đồng thuận |
| Vote decay | 0.95 | Đã đưa thành cấu hình; tính theo lần cập nhật có bằng chứng, chưa theo giây |
| Vote margin tối thiểu | 0.20 | Mới thêm; với hai đội đòi hỏi ít nhất 60/40 phiếu cho nhãn đang hiển thị; chưa được tối ưu trên tập giữ riêng |
| SigLIP refresh | 5 frame | Không có tác dụng trong nhánh home hiện tại |
| Keep unknown | false trong lần chạy này | Mặc định code là true; cần phân biệt cấu hình mặc định với cấu hình có hiệu lực |
| Keep unassigned | false | Loại logo không gán được người khỏi kết quả lọc |

Video team là bản chẩn đoán: vẫn vẽ `[?]` để người xem thấy dự đoán logo chưa chắc đội. Những trường hợp này có `on_target_team=false` theo cấu hình có hiệu lực, không phải Bradford được xác nhận. `[BRA]` là nhãn model, không phải xác nhận thủ công.

Các thông số thời gian chưa được chuẩn hóa: decay 0.95 có nửa đời khoảng 13,5 **lần cập nhật có phiếu**; nếu mỗi frame đều có phiếu thì khoảng 0,54 giây ở 25 fps nhưng 6,76 giây ở 2 fps. Khi crop bị loại không có decay, nhãn cũ có thể giữ lâu. Vì vậy video demo 25 fps không chứng minh hành vi tương đương analytics mặc định 2 fps.

## Những hạn chế còn lại

1. Crop hình chữ nhật và gán chủ theo box dễ lẫn áo khi tackle/chen chúc. Body segmentation hiện chưa cấp instance mask cho bước gán chủ logo.
2. Quy tắc áo home phụ thuộc bộ áo và màu đối thủ; chưa chứng minh dùng tốt cho mọi trận/kit/điều kiện ánh sáng.
3. Khóa phiếu cho box quá chồng lấn hoặc bị cắt làm tăng Unknown. ID switch và chuyển cảnh vẫn cần đánh giá riêng.
4. Hàm học trọng số fusion đánh giá trên chính các crop tạo centroid, chưa phải đánh giá độc lập.
5. Preview logo trong luồng upload gọi `detector.detect_boxes` trực tiếp. Không nên dùng preview thuần logo để suy ra team filter trong analytics không hoạt động; video chẩn đoán đội là một đầu ra riêng.

Để gọi là tối ưu, cần tập nhãn có chủ logo + đội theo track, chia theo shot/match; đo precision/recall Bradford, tỷ lệ abstain, độ chính xác gán chủ và tốc độ. Tune trên tập phát triển, báo cáo tập giữ riêng; so sánh cả 2 fps và native fps. Không nên chỉ hạ ngưỡng để giảm số Unknown.

## Thay đổi đã thực hiện

- Thêm kiểm tra signed vote margin: tổng phiếu lớn nhưng hai đội xung đột sẽ trả Unknown. Hysteresis vẫn giữ lịch sử nội bộ để phục hồi khi bằng chứng đủ rõ.
- Đưa vote decay và vote margin thành cấu hình có kiểm tra miền giá trị.
- Sửa overlay người để Unknown luôn hiển thị `?`, kể cả vote mass lớn.
- Màu riêng cố định cho mỗi sponsor trong video và ảnh; dùng chung hàm màu của ứng dụng. Chuẩn hóa suffix home/away và alias tên để màu cùng thương hiệu không đổi. Nhãn `[BRA]`/`[?]` thể hiện đội, không dùng màu sponsor làm mã đội.
- Xuất lại hai video 90 giây và ảnh từ dự đoán thật. Giữ dự đoán trước thay đổi trong `before_detections.json`.

Kiểm thử: 42 tests backend passed. Các kiểm thử bao gồm phiếu mâu thuẫn, nhãn hysteresis cũ, Unknown nhiều phiếu và màu sponsor. Đây là kiểm thử phần mềm, không phải chứng minh accuracy CV. OpenCV H.264 có cảnh báo codec trong test; video bàn giao được encode riêng bằng FFmpeg libx264 và kiểm tra giải mã toàn bộ.
