# Logo Exposure & Pricing Model Algorithm

> Dựa trên: ExposureEngine (arxiv 2510.04739), Relo Metrics, Shikenso, USPTO Patents  
> Áp dụng cho: YOLO26 logo detection tại sự kiện thể thao

---

## Tổng quan kiến trúc — 3 tầng

```
Video / Livestream
        ↓
[Tầng 1] Visibility Score   ← YOLO26 output (mỗi frame)
        ↓
[Tầng 2] Exposure Score     ← Tổng hợp theo thời gian (per logo)
        ↓
[Tầng 3] Media Value ($)    ← Quy đổi ra tiền (per logo per event)
```

---

## Tầng 1 — Visibility Score (per frame)

Tính cho từng detection trong từng frame.

### Các thành phần

| Factor | Công thức | Ghi chú |
|--------|-----------|---------|
| **Size Score** | `sqrt(box_area / frame_area)` | sqrt tránh logo cực lớn dominate |
| **Position Score** | `exp(-dist_from_center² / (0.3×W)²)` | Gaussian: tâm = 1.0, góc ≈ 0.1 |
| **Clarity Score** | confidence score từ YOLO | 0–1, thể hiện độ rõ của logo |
| **OBB Penalty** | `box_area_HBB / box_area_OBB` | = 1.0 nếu thẳng, < 1.0 nếu nghiêng |

> **Tại sao cần OBB Penalty?**  
> Bounding box thẳng (HBB) phóng đại diện tích khi logo bị nghiêng do góc camera.  
> OBB Penalty hiệu chỉnh lại diện tích thực theo hình dạng logo.  
> *(Nguồn: ExposureEngine paper — mAP 0.859 với OBB trên dataset soccer)*

### Công thức tổng hợp

```
Visibility_Score(frame) = Size_Score
                        × Position_Score
                        × Clarity_Score
                        × OBB_Penalty
```

Kết quả: số từ 0.0 → 1.0 cho từng logo trong từng frame.

---

## Tầng 2 — Exposure Score (per logo, toàn video)

### Bước 1 — Gom frame thành Segment

```
Segment = chuỗi frame liên tiếp có Visibility_Score > 0.1
```

- Bỏ segment có độ dài < 0.5 giây (flicker, nhiễu — không tính)
- Mỗi segment lưu: `[start_time, end_time, [visibility_scores]]`

### Bước 2 — Duration Weight theo độ dài segment

| Độ dài segment | Duration Weight | Lý do |
|---------------|-----------------|-------|
| < 1 giây | 0.5 | Quá ngắn, người xem khó nhớ |
| 1 – 5 giây | 1.0 | Standard |
| > 5 giây | 1.2 | Sustained exposure, giá trị cao hơn |

### Bước 3 — Tổng hợp

```
Exposure_Score = Σ [ mean(Visibility_Scores) × Duration_Weight × segment_duration ]
                 trên mọi segment của logo đó
```

Kết quả: **tổng giây exposure đã được quality-weighted** cho mỗi logo.

### Output Tầng 2

| Metric | Ý nghĩa |
|--------|---------|
| `total_exposure_seconds` | Tổng giây xuất hiện thô |
| `quality_exposure_seconds` | Exposure_Score (đã điều chỉnh quality) |
| `avg_visibility_score` | Chất lượng trung bình |
| `segment_count` | Số lần xuất hiện riêng lẻ |
| `longest_segment_seconds` | Lần xuất hiện liên tục dài nhất |

---

## Tầng 3 — Media Value / EMV (per logo per event)

### Công thức gốc (chuẩn industry — Relo Metrics, USPTO Patent)

```
EMV = Exposure_Score × (CPM_base / 1000) × Audience_Size
    × Placement_Multiplier
    × Category_Multiplier
    × Prime_Time_Multiplier
```

### Placement Multiplier

| Loại phát sóng | Multiplier |
|---------------|------------|
| Live broadcast TV | 1.00 |
| Live stream online | 0.85 |
| Highlight / clip (xem nhiều lần) | 1.40 |
| Social media clip | tuỳ engagement rate |

### Category Multiplier (Share of Voice)

| Tình huống | Multiplier |
|-----------|------------|
| Logo duy nhất trong ngành (exclusivity) | 1.25 |
| Có 2–3 thương hiệu cùng ngành | 1.00 |
| Có competitor cùng frame | 0.80 |

### Prime Time Multiplier

| Thời điểm trong sự kiện | Multiplier |
|------------------------|------------|
| 15 phút đầu / cuối trận | 1.30 |
| Giữa trận | 1.00 |
| Ngoài giờ chính (pre/post match) | 0.70 |

### CPM Benchmark tham khảo

| Loại sự kiện | CPM_base gợi ý |
|-------------|----------------|
| Thể thao đại chúng (bóng đá, bóng bầu dục) | $15 – $25 |
| Thể thao cao cấp (golf, tennis, F1) | $35 – $60 |
| Esports / Gaming event | $8 – $15 |
| Local / regional event | $5 – $12 |

> Điều chỉnh CPM_base theo dữ liệu thực tế của broadcaster/event organizer.

---

## Output cuối cùng — Report per logo per event

| Field | Ý nghĩa |
|-------|---------|
| `logo_name` | Tên thương hiệu |
| `total_exposure_seconds` | Tổng giây thô |
| `quality_exposure_seconds` | Giây đã quality-weighted |
| `avg_visibility_score` | Chất lượng trung bình (0–1) |
| `segment_count` | Số lần xuất hiện |
| `longest_segment_seconds` | Lần xuất hiện dài nhất |
| `emv_usd` | Equivalent Media Value ($) |
| `placement_type` | Live / Highlight / Social |
| `audience_size` | Số người xem |
| `event_name` | Tên sự kiện |

---

## So sánh với approach ngây thơ

| Approach đơn giản | Approach này |
|-------------------|-------------|
| Đếm số frame xuất hiện | Quality-weighted exposure seconds |
| Diện tích HBB thẳng | OBB Penalty hiệu chỉnh logo nghiêng |
| Duration đơn giản | Phân segment + Duration Weight |
| CPM × giây | EMV × 3 multipliers (Placement, Category, Prime Time) |
| Không phân biệt vị trí | Gaussian Position Score (tâm > góc) |

---

## Câu hỏi cần xác nhận trước khi code

1. **OBB hay HBB?** — Logo trong dataset có hay bị nghiêng góc camera không? Nếu có → re-annotate OBB và train lại YOLO26 ở mode OBB.
2. **Input** — File video tĩnh hay livestream real-time?
3. **Viewership data** — Nhập tay theo event hay kết nối API từ broadcaster?
4. **CPM_base** — Đã có số tham chiếu thị trường chưa?
5. **Output format** — JSON, CSV, hay dashboard web?

---

## Nguồn tham khảo

- [ExposureEngine — arxiv 2510.04739](https://arxiv.org/abs/2510.04739)
- [Sponsorship ROI with Logo Tracking — API4AI](https://medium.com/@API4AI/sponsorship-roi-from-live-sports-feeds-bd9b686038f9)
- [The Benefits of Sponsor Media Value — Relo Metrics](https://blog.relometrics.com/the-benefits-of-sponsor-media-value-and-how-it-is-calculated)
- [What is Media Value — Shikenso](https://shikenso.com/blog/understanding-media-value-the-key-to-sponsorship-success)
- [Automated media analysis for sponsor valuation — USPTO Patent 12124509](https://image-ppubs.uspto.gov/dirsearch-public/print/downloadPdf/12124509)
