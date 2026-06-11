# 6. Dashboard — hướng dẫn sử dụng

Frontend Next.js tại `logo-analytics/`, chạy `npm run dev` → http://localhost:3000.
Nav: **Dashboard** (tổng hợp) · **New Analysis** (upload). Không có backend →
tự hiển thị mock data (gắn nhãn "demo data").

## Upload (New Analysis — `/`)

Drop video (MP4/MOV/AVI/MKV ≤ 2GB) + nhập:

- **Event Name**, **Audience Size**, **CPM Base** — đầu vào công thức EMV
- **Placement Type** — hệ số nhân EMV
- **Bradford Kit** (Away đen / Home trắng) — cho team filter chọn đúng kit

Màn processing hiển thị 5 bước realtime; xong tự chuyển vào tab Match Videos
của video vừa phân tích.

## Tab Overview — dashboard tổng hợp toàn bộ dữ liệu

- 4 KPI portfolio: Total EMV, Brands Tracked, Quality Exposure, Avg Visibility
- **EMV Trend** — line chart Total + top 3 brand qua các trận (theo thời gian)
- **Share of Voice** — donut phân bố EMV theo brand
- **EMV by Match** / **Top Brands** — bar ranking, click → mở chi tiết trận

## Tab Match Videos — thư viện + chi tiết từng trận

- **Search** theo tên, **filter ngày** (from/to), **sort** (newest/EMV/duration)
- Click card → **Match Analysis**: KPI trận, badge **team-filter stats**
  (kept/dropped), **video preview có audio** với box detection + timeline
  per-brand bên dưới (click timeline để seek), bảng Brand Breakdown

## Tab Brand Insights — phân tích 1 brand xuyên hệ thống

- Chọn brand bằng chip màu
- 6 KPI: EMV + SoV, Exposure, Coverage (x/y trận), Avg Visibility, **EMV/s**,
  Quality Ratio
- **EMV per Match** — trend brand vs "brand trung bình trong trận"
- **Radar profile 5 trục** (EMV/Exposure/Visibility/EMV-s/Consistency) vs
  trung bình portfolio
- Highlights (best match, most efficient) + bảng per-match — click row mở trận

## Tab Analytics Report — báo cáo có filter + export

- **Filter**: Match scope (All/từng trận) · Brand · khoảng ngày (scope All)
- Scope **All matches**: SoV donut, EMV Trend by Brand, **Brand × Match
  heatmap** (click cell mở trận), Match Comparison
- Scope **1 trận**: Exposure Over Time (line), Distribution (pie),
  **Appearance Quality Map** (scatter duration × visibility — góc trên phải là
  premium inventory), Exposure Quality bars (quality/raw per brand)
- Bảng **Brand Performance**: EMV, SoV, Quality Ratio, Avg Vis, EMV/s, Segments
- **Export PDF** — in vùng report (print CSS, chart giữ nguyên); **Export CSV**
  trên nav

## Tab Body Segmentation

- Video overlay body-part (DensePose/YOLO-seg) nếu backend bật bodyseg
- **Model 3D xoay được** (drag xoay, scroll zoom): 18 kit slot tô màu riêng,
  vùng da xám; hover hiện %, label leader-line tự cull mặt sau; sidebar ranking
  zone — cơ sở thuyết trình pricing theo vị trí

## Ghi chú kỹ thuật

- Chart đều là SVG tự viết trong `components/dashboard/charts.tsx`
  (Donut/Trend/Heatmap/Radar/Scatter) — interactive, không dependency
- Màu brand ổn định xuyên tab (index theo ranking EMV)
- Model 3D: `public/male_model.glb` + zone classify trong fragment shader
