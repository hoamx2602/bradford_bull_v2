# Kết quả rà soát dissertation LogoLens

Ngày hoàn tất: 05/08/2026  
Giới hạn áp dụng: 12.000 từ cho Chapters 1–7

## Kết luận

Bản dissertation hiện phù hợp với định hướng MSc Applied AI and Data Analytics: có artefact end-to-end, câu hỏi có thể kiểm chứng, đánh giá leakage-controlled, human audit và phân tích sensitivity/data efficiency. Bản mới có **11.851 từ**, **15 hình** và **10 bảng**.

## Research questions

RQ5 cũ về “AI in advertising” đã được bỏ khỏi nhóm research questions vì không có phương pháp hay dữ liệu riêng để kiểm nghiệm. Nội dung này vẫn được giữ như một discussion lens và objective. Bốn RQ còn lại tạo thành chuỗi bằng chứng rõ hơn:

1. Độ chính xác detection và team attribution dưới protocol chống leakage.
2. Các thuộc tính thực nghiệm của logo exposure và hệ quả đo lường.
3. Cách tổng hợp exposure thành EMV và độ nhạy với tham số/sampling.
4. Mối liên hệ giữa số annotation mỗi sponsor và held-out AP, dùng để đưa ra ngân sách onboarding có tính chỉ dẫn.

RQ4 nên được đọc như một association trong case study, không phải quan hệ nhân quả; luận văn đã nêu confound do độ khó từng logo và kích thước validation set.

## EMV

Công thức đã được sửa thành:

`EMV = (quality-exposure seconds / 30) × (CPM / 1,000) × audience × scenario multiplier`

Việc chia cho 30 quy đổi thời lượng về số spot quảng cáo 30 giây tương đương. CPM và audience là scenario inputs, không phải hằng số thị trường do hệ thống suy ra. Ví dụ 120 quality-weighted seconds, CPM US$22 và audience 40.000 cho EMV **US$3.520**, không phải US$105.600.

Nguồn phương pháp chính:

- Google Ads: CPM là chi phí cho 1.000 impressions.
- U.S. Patent 12,124,509 của GumGum Sports: định giá theo commercial-cost equivalent, audience và attribution quality bao gồm duration/prominence.
- Nielsen Sponsorship Media Value Benchmarking: exposure metrics được kết hợp với Quality Index, audience và advertising rates.

Database đã được migrate có backup. Tổng của 23 analysis records giảm từ **US$3.490.388,01** xuống **US$116.346,29**. Đây là tổng các record đang lưu, có thể gồm nhiều lần chạy/fixture trùng nhau, nên không được trình bày như giá trị của một experimental sample độc lập.

## Hình ảnh

Số hình trong main dissertation đã giảm từ 31 xuống **15**. Các screenshot giao diện, training curves và hình minh họa trùng chức năng đã được bỏ. Ba hình detection cũ được thay bằng một plate hai panel từ validation export, có confidence labels, legend chung và làm mờ broadcast overlays. Hình này là qualitative evidence, không được dùng để tính accuracy.

## Runtime

Không có Conda environment tên `rfdetr`. Environment backend đúng là `bradford_bulls`, có RF-DETR 1.8.3, CUDA và checkpoint `checkpoint_best_ema.pth`. Backend health check và một inference RF-DETR trực tiếp đều chạy thành công; inference thử trả 14 detections ở threshold 0,20. Environment `bradford_bulls_logo` phù hợp với các script YOLO/figure nhưng không chứa RF-DETR/FastAPI.

## Kiểm tra cuối

- Pricing tests: 4/4 pass.
- Backend `/api/health`: HTTP 200, backend `rfdetr`, GPU device `0`.
- Backend `/api/analyses`: HTTP 200, 23 records.
- Frontend production build: pass.
- DOCX: 15/15 hình được nhúng, 371 paragraphs, 9 tables, TOC field và 7 chapter headings đầy đủ.
- Chưa thể render toàn bộ DOCX thành ảnh trang trên máy này vì LibreOffice/soffice không được cài; cần mở trong Microsoft Word, update TOC và kiểm tra page breaks lần cuối trước khi nộp.
