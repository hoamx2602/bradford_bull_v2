# Bradford Bulls — AI Sponsorship Exposure Valuation

## Mục tiêu

Đo lường mức độ hiện diện (exposure) của từng logo sponsor trên áo cầu thủ Bradford Bulls trong video trận đấu, từ đó đưa ra định giá khách quan cho từng vị trí sponsor.

---

## Phase 1: Training Data (ĐANG LÀM)

### Pipeline
```
Video trận đấu (YouTube, 1080p, ~90 phút)
    → Sample 1 FPS (~5,400 frames)
    → Filter: có cầu thủ (YOLOv8) + frame nét (sharpness score)
    → De-duplicate (pHash)
    → Top N selection (time diversity)
    → 300-400 full frames chất lượng cao
    → Upload Roboflow (không annotation)
    → Manual annotate trên Roboflow (vẽ bbox + gán class)
    → Train YOLOv8 trên Roboflow (hoặc export YOLO format)
```

### 21 Logo Classes
| ID | Code | Logo | ID | Code | Logo |
|----|------|------|----|------|------|
| 0 | aon_red | Aon (Red) | 11 | mna_cladding | MNA Cladding |
| 1 | aon_white | Aon (White) | 12 | mna_support | MNA Support |
| 2 | atm_hospitality | ATM Hospitality | 13 | paints_lacquers_yellow | Paints & Lacquers (yellow) |
| 3 | cch_black | CCH (Black) | 14 | top_notch | Top Notch |
| 4 | cch_white | CCH (White) | 15 | bartercard | Bartercard |
| 5 | chadlaw | ChadLaw | 16 | floor_tonic | Floor Tonic |
| 6 | em_workwear | EM Workwear | 17 | paints_lacquers_red | Paints & Lacquers (red) |
| 7 | fairway_flooring | Fairway Flooring | 18 | romantica_white | Romantica (White) |
| 8 | klg | KLG | 19 | romantica_black | Romantica (Black) |
| 9 | mcp_away | MCP (Away) | 20 | acs_group | ACS Group |
| 10 | mcp_home | MCP (Home) | | | |

### Annotation Guidelines (CẦN ĐỊNH NGHĨA TRƯỚC KHI BẮT ĐẦU)
- [ ] Logo bị che bao nhiêu % thì bỏ? (đề xuất: >50% → bỏ)
- [ ] Kích thước tối thiểu bao nhiêu pixel để annotate? (đề xuất: >15px width)
- [ ] Logo mờ nhưng đoán được → có annotate không?
- [ ] Cùng sponsor ở 2 vị trí trên 1 cầu thủ → 2 bbox riêng
- [ ] Có annotate logo đội đối thủ không? (đề xuất: không, chỉ Bradford)
- [ ] Replay frame → có annotate không? (đề xuất: có, nhưng tag riêng nếu được)

### Notebooks
- `colab_03_frame_extraction.ipynb` — Pipeline lấy frame + upload Roboflow (DÙNG CÁI NÀY)
- `colab_02_smart_crop_pipeline.ipynb` — Crop cầu thủ + auto-annotate (ĐÃ BỎ — Grounding DINO không phù hợp)

### Bài học rút ra
- Grounding DINO không phân biệt được 21 loại logo cụ thể — chỉ detect "có gì đó" chứ không classify được
- Auto-annotate tạo quá nhiều box sai, tốn thời gian sửa hơn là annotate từ đầu
- Full frame tốt hơn crop: giữ context, cả 2 đội, annotator thấy toàn cảnh

---

## Phase 2: Train Logo Detection Model

### Trên Roboflow
1. Annotate đủ ~300-400 frames
2. Generate dataset version (preprocessing + augmentation)
3. Train YOLOv8 trực tiếp trên Roboflow
4. Evaluate mAP, per-class AP

### Hoặc export + train local/Colab
```
Export YOLO format → Train YOLOv8 trên Colab GPU
Ưu điểm: kiểm soát hyperparameters, custom augmentation
```

### Đánh giá model
- [ ] Benchmark: chọn 5-10 phút video, đếm logo bằng tay → so với model → tính sai số
- [ ] Per-class accuracy: class nào model yếu → cần thêm training data
- [ ] Cross-match test: train từ trận A, test trên trận B → generalize không?

---

## Phase 3: Exposure Measurement Engine

### Phương pháp đo

Chạy model trên **toàn bộ video ở 30 FPS** (không chỉ frame nét):
```
Mỗi frame → detect logos → ghi nhận: logo_class, confidence, bbox_size, position_on_screen
```

### Metrics chính

**1. Exposure Time (giây)**
```
exposure_time[logo] = count(frames với detection) / FPS
```

**2. Weighted Exposure (tính cả mức độ rõ ràng)**
```
weighted_exposure[logo] = Σ (confidence × 1/FPS)
```
→ Frame nét (conf 0.9) đóng góp nhiều hơn frame mờ (conf 0.4), nhưng frame mờ vẫn được tính vì người xem vẫn nhận biết logo.

**3. Continuous Segments**
```
Thay vì đếm frame rời rạc, nhóm thành exposure events:
    Logo A xuất hiện liên tục giây 12.3 → 14.8 = 1 event (2.5s)
```
Nghiên cứu quảng cáo: cần tối thiểu 0.5-1s liên tục để não ghi nhận brand.

**4. Quality Index (QI)**
```
QI = size_on_screen × clarity × (1 / clutter) × position_weight
```
- `size_on_screen`: bbox area / frame area
- `clarity`: confidence score
- `clutter`: bao nhiêu logo khác cùng xuất hiện (cạnh tranh attention)
- `position_weight`: trung tâm màn hình > rìa

---

## Vấn đề tiềm tàn và rủi ro

### 1. "Hiện diện" ≠ "Được nhìn thấy" ≠ "Được nhận biết"

| Mức | Ý nghĩa | Model đo được? |
|-----|---------|----------------|
| Presence | Logo trong khung hình | Có |
| Visibility | Đủ lớn, đủ rõ để mắt thấy | Phần nào (qua confidence + size) |
| Recognition | Não nhận biết brand | Không — cần eye-tracking study |

**Rủi ro**: Báo cáo logo xuất hiện 12 phút, nhưng người xem chỉ thực sự nhận biết 3 phút.
**Giải pháp**: Dùng weighted exposure + minimum duration threshold (0.5s). Trình bày kèm confidence interval.

### 2. Camera Bias

- Camera theo bóng, không theo cầu thủ → cầu thủ xa bóng ít xuất hiện
- Close-up thiên lệch: đội ghi bàn, ngôi sao, HLV
- Replay: cùng 1 pha phát lại 2-3 lần → logo nhân đôi
- Overlay/graphics: scoreboard, tên cầu thủ che logo
- Bảng LED sân: model có thể detect nhầm logo trên LED

**Rủi ro**: Kết quả exposure phụ thuộc vào đạo diễn hình, không phải bản thân vị trí logo.
**Giải pháp**: 
- Detect và loại bỏ replay segments (scene change detection, overlay detection)
- Filter logo trên LED vs trên áo (dựa vào position: LED thường ở rìa frame)
- Đo nhiều trận để trung bình hóa camera bias

### 3. Vị trí logo vs thực tế nhìn thấy

- Logo trước ngực chỉ thấy khi cầu thủ hướng mặt về camera
- Logo sau lưng chỉ thấy khi quay lưng
- Logo quần/tất gần như không nhìn thấy trừ close-up
- Thủ môn: áo khác, ít di chuyển → exposure pattern khác hoàn toàn

**Rủi ro**: Kết quả có thể xung đột với bảng giá hiện tại (Main Sponsor 26% có thể exposure thấp hơn Sleeve).
**Giải pháp**: Đây chính là giá trị của sản phẩm — dữ liệu thực thay thế phỏng đoán. Trình bày transparent.

### 4. Generalization

- Áo sân nhà vs sân khách: khác màu, khác kích thước logo
- Mùa giải mới: sponsor thay đổi → model cũ không dùng được
- Chất lượng video: TV broadcast vs 1 camera YouTube
- Sân khác nhau: ánh sáng, thời tiết → domain shift

**Giải pháp**: 
- Train riêng cho từng bộ áo (home/away)
- Retrain mỗi mùa giải khi áo mới
- Test cross-match trước khi deploy

### 5. So sánh với Industry Standard

Các công ty chuyên (Nielsen Sports, Hookit, GumGum Sports) dùng:
- AI detection + eye-tracking study thực tế
- Quality Index weight theo size, clarity, clutter, screen position
- Media value equivalence (so với giá quảng cáo TV)
- Hàng triệu frame training data

**Lợi thế của approach này**: Cost-effective, specific cho Bradford Bulls, có thể customize.
**Hạn chế**: Không có eye-tracking, ít training data, chưa benchmark với industry standard.

---

## Phase 4: Pricing Model

### Input
- Exposure data từ Phase 3 (per logo, per match)
- Current pricing (bảng giá hiện tại)
- Match context: đối thủ, giải đấu, viewership

### Output
- **Relative comparison**: Logo A exposure gấp 3x logo B (dễ chấp nhận, ít tranh cãi)
- **Pricing recommendation**: Dựa trên actual exposure thay vì fixed percentages
- **Confidence interval**: Không chỉ 1 con số

### Cách trình bày
Nên dùng relative comparison trước (logo A vs logo B) thay vì absolute value ($X per giây). Lý do:
- Ít tranh cãi về methodology
- Sponsor dễ hiểu: "bạn được gấp 2x exposure so với vị trí bên cạnh nhưng trả gấp 5x"
- Không cần justify absolute media value

---

## Phase 5: Reporting & Scale

### Per-match report
- Timeline: logo nào xuất hiện khi nào, bao lâu
- Heatmap: vị trí logo trên màn hình theo thời gian
- Per-sponsor scorecard: exposure time, QI, relative ranking
- So sánh với trận trước: trend theo mùa giải

### SaaS potential
- Mỗi CLB upload video → tự động phân tích
- Cần: retrain per-club (khác áo, khác sponsor), API inference, dashboard
- Pricing model: per-match hoặc subscription

---

## Tech Stack

| Component | Tool | Ghi chú |
|-----------|------|---------|
| Video download | yt-dlp + ffmpeg | |
| Frame sampling | OpenCV + custom | 1 FPS + quality filter |
| Person detection | YOLOv8 (ultralytics) | Pre-trained, GPU batch |
| Annotation | Roboflow | Manual annotate + train |
| Logo detection | YOLOv8 custom trained | Train trên Roboflow hoặc Colab |
| Compute | Google Colab (GPU) | T4/A100 |
| Storage | Google Drive | All data in/out |
| Local dev | MacBook (Apple Silicon MPS) | Cho code, không cho training nặng |

---

## Timeline

| Phase | Trạng thái | Ghi chú |
|-------|-----------|---------|
| 1. Training data | **ĐANG LÀM** | Frame extraction done, cần annotate trên Roboflow |
| 2. Train model | Chưa bắt đầu | Sau khi annotate xong |
| 3. Exposure engine | Chưa bắt đầu | Sau khi model accuracy OK |
| 4. Pricing model | Chưa bắt đầu | |
| 5. Reporting | Chưa bắt đầu | |
