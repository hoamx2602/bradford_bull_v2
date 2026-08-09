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

### Công thức time-normalised

```
EMV = (Quality_Exposure_Seconds / Reference_Spot_Seconds)
    × (CPM_base / 1000) × Audience_Size
    × Placement_Multiplier
    × Category_Multiplier
    × Prime_Time_Multiplier
```

`Reference_Spot_Seconds = 30` trong implementation hiện tại. CPM là chi phí cho
1.000 impressions, không phải chi phí cho mỗi giây. Vì vậy quality-exposure
seconds phải được quy đổi thành số 30-second equivalent spots trước khi nhân
với CPM và audience. US Patent 12,124,509 mô tả media-cost equivalent dựa trên
giá commercial 30 giây, audience và phần trăm attribution theo duration,
prominence, size, clarity và position; Nielsen cũng mô tả QI Media Value là sự
kết hợp giữa quality-weighted exposure, audience data và advertising rates.

Ví dụ: 120 quality-exposure seconds, CPM US$22, audience 40.000 và multiplier
1,0 cho kết quả `(120/30) × (22/1000) × 40.000 = US$3.520`, không phải
US$105.600.

### Placement Multiplier

Các giá trị dưới đây là **scenario assumptions của project**, không phải một
rate card phổ quát. Nếu có CPM riêng cho từng broadcaster/channel thì nên dùng
CPM đó và đặt multiplier bằng 1,0.

| Loại phát sóng | Multiplier |
|---------------|------------|
| Live broadcast TV | 1.00 |
| Live stream online | 0.85 |
| Highlight / clip (xem nhiều lần) | 1.40 |
| Social media clip | tuỳ engagement rate |

### Category Multiplier (Share of Voice)

Các multiplier này hiện là extension points và chưa được bật trong backend;
giá trị mặc định là 1,0.

| Tình huống | Multiplier |
|-----------|------------|
| Logo duy nhất trong ngành (exclusivity) | 1.25 |
| Có 2–3 thương hiệu cùng ngành | 1.00 |
| Có competitor cùng frame | 0.80 |

### Prime Time Multiplier

Các multiplier này hiện là extension points và chưa được bật trong backend;
giá trị mặc định là 1,0.

| Thời điểm trong sự kiện | Multiplier |
|------------------------|------------|
| 15 phút đầu / cuối trận | 1.30 |
| Giữa trận | 1.00 |
| Ngoài giờ chính (pre/post match) | 0.70 |

### CPM input

Không có một CPM đúng cho mọi sự kiện. CPM phải lấy từ broadcaster, media buyer
hoặc rate card của event/channel và lưu cùng analysis. Giá trị US$22 trong dữ
liệu hiện tại được xem là scenario input của project, không phải market benchmark
được luận văn chứng minh.

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
| CPM × giây | Quy về 30-second equivalent rồi mới nhân CPM và các scenario multipliers |
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

- [Google Ads — Cost-per-thousand impressions (CPM): Definition](https://support.google.com/google-ads/answer/6310?hl=en)
- [Nielsen — Sponsorship Media Value Benchmarking Report and QI methodology](https://www.nielsen.com/report/sponsorship-media-value-benchmarking-report/)
- Katz, J. B., Carter, C. N., & Kim, B. J. (2024). *Automated media analysis for sponsor valuation*. U.S. Patent No. 12,124,509. [USPTO PDF](https://image-ppubs.uspto.gov/dirsearch-public/print/downloadPdf/12124509)
- [ExposureEngine — arXiv:2510.04739](https://arxiv.org/abs/2510.04739) (visibility measurement only; it does not publish an EMV formula)
