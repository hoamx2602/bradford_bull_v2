# Tài liệu hệ thống — Bradford Bulls Logo Analytics

Hệ thống đo lường **sponsor logo exposure** trên video broadcast (rugby league),
tính **EMV (Equivalent Media Value)** cho từng brand và trực quan hóa trên dashboard.

## Đọc theo thứ tự

| # | Tài liệu | Dành cho ai / khi nào |
|---|---|---|
| 1 | [Tổng quan hệ thống](01-overview.md) | Bắt đầu ở đây — bài toán, kiến trúc, cấu trúc repo |
| 2 | [Cài đặt & chạy](02-setup.md) | Setup máy mới: macOS (M-series) và Windows (CUDA) |
| 3 | [Pipeline xử lý](03-pipeline.md) | Hiểu các stage chạy khi upload một video |
| 4 | [Team filter](04-team-filter.md) | Cách hệ thống chỉ đếm logo trên cầu thủ Bradford |
| 5 | [Exposure & EMV](05-exposure-emv.md) | Phương pháp tính điểm và định giá |
| 6 | [Dashboard](06-dashboard.md) | Hướng dẫn dùng frontend (5 tab) |
| 7 | [API reference](07-api.md) | Endpoint backend cho tích hợp |
| 8 | [Annotation & Training](08-annotation-training.md) | Quy trình data Roboflow + train model logo |
| 9 | [Vận hành & Troubleshooting](09-operations.md) | Tuning knobs, lỗi thường gặp, scaling |

## Tài liệu deep-dive (giữ ở repo root)

Các tài liệu nghiên cứu/thiết kế gốc — chi tiết hơn docs ở trên, đọc khi cần đào sâu:

- [`LOGOS_Exposure_Pricing_Algorithm.md`](../LOGOS_Exposure_Pricing_Algorithm.md) — đặc tả đầy đủ thuật toán 3 tầng Visibility → Exposure → EMV
- [`Production-System-Design.MD`](../Production-System-Design.MD) — phân tích thiết kế production system, roadmap 12–18 tháng
- [`Motion-blur.MD`](../Motion-blur.MD) — nghiên cứu xử lý motion blur trong detection
- [`TESTING_GUIDE.md`](../TESTING_GUIDE.md) — hướng dẫn test thủ công
- [`backend/README.md`](../backend/README.md) — README kỹ thuật của backend (setup chi tiết, env vars)

## Sơ đồ nhanh

```
Upload video (+ kit away/home)
        │
        ▼
┌─ Backend pipeline ────────────────────────────────────┐
│ frames → team identify → logo detect (filtered)       │
│        → pose/body-zones → exposure → EMV             │
│        → preview video (+audio) → bodyseg overlay     │
└────────────────────────┬──────────────────────────────┘
                         ▼
              Dashboard (Next.js)
   Overview · Match Videos · Brand Insights
   Analytics Report (PDF) · Body Segmentation (3D)
```
