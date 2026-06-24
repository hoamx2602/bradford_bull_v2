# Location Breakdown — Bảng vị trí logo & các thông số %

Bảng **Location Breakdown** xuất hiện cho **mỗi video** ở dashboard (mục _Location
Breakdown_ trong tab Videos) và xuất ra **file Excel** 2 sheet. Nó trả lời câu hỏi
của khách hàng: *mỗi vị trí đặt logo trên áo đấu đáng giá / hiển thị bao nhiêu %?*

```
Location | Logo | Human % | AI % | AI Adjusted % | Visibility % | Human AI %
```

Mỗi dòng là một **vị trí trên kit** (taxonomy của khách: Main Sponsor, Collar Bone,
Sleeve 1/2/3, Top Back, …) — cấu hình ở trang **Settings**, dùng chung cho mọi video,
cho phép override theo từng video.

---

## 1. Ý nghĩa từng cột

| Cột | Nguồn | Tổng = 100%? | Tóm tắt |
|---|---|---|---|
| **Location** | Cấu hình (Settings) | — | Tên vị trí đặt logo trên áo |
| **Logo** | Cấu hình, **theo kit** | — | Thương hiệu gán cho vị trí đó |
| **Human %** | Khách nhập (hợp đồng) | Không* | Giá trị hợp đồng theo vị trí |
| **AI %** | Hệ thống đo | **Có (100.00)** | Tỉ trọng exposure đo được, chuẩn hoá |
| **AI Adjusted %** | Trộn AI + người | **Có (100.00)** | Trung hoà AI với tham chiếu người |
| **Visibility %** | Hệ thống đo | Không | Thời gian logo trên màn hình / thời lượng video |
| **Human AI %** | Bạn nhập tay | Không | Đánh giá thủ công khi xem video |

\* Human % là số khách tự đặt nên tổng có thể khác 100% (vd sheet gốc tổng ~194%).

> **Vị trí không có logo** (vd Collar Back): các cột AI %, AI Adjusted %, Visibility %
> để trống ("—"). Vị trí đó cũng **không** nhận phần exposure của zone — xem §6.

---

## 2. Logo theo kit (home/away)

Bố cục tài trợ hai kit giống nhau, **chỉ khác logo ngực chính**:

| | Home (áo trắng) | Away (áo đen) |
|---|---|---|
| **Main Sponsor** | Top Notch | Floor Tonic |

- Mỗi location có `brand_key` (logo home/mặc định) và `brand_key_away` (chỉ đặt khi
  khác — null = giống home).
- Logo hiển thị chọn theo **kit của video** (lấy từ job lúc upload): away & có
  `brand_key_away` → dùng logo away; ngược lại dùng logo home.
- **Lưu ý vận hành:** kit phải chọn đúng lúc upload (trắng = home, đen = away),
  nếu không logo ngực chính sẽ sai.

---

## 3. AI % — cách tính (cốt lõi)

AI % = **tỉ trọng "quality exposure" đo được tại vị trí đó**, trên tổng các vị trí
có logo, chuẩn hoá đúng 100%. Tính lại tức thì khi đổi tiêu chí (criteria) — **không
cần chạy lại detection** — nhờ lưu sẵn các thành phần factor của từng detection.

### 3.1 Dữ liệu gốc — "exposure facts"

Khi phân tích, mỗi detection (lấy mẫu 2 fps) lưu một fact:

```
{ t, zone, brandKey, size, pos, clarity, obb, durSec }
```

- `zone` = vùng cơ thể (anchor) mà detection được gán (từ pose keypoints).
- `durSec = 1 / SAMPLE_FPS` (mặc định 2 fps → 0.5s mỗi frame mẫu).
- `size, pos, clarity, obb` = 4 thành phần **Tier-1 visibility** (xem §3.2).

### 3.2 Tier-1 — Factor mỗi detection (`visibility.py`)

| Factor | Công thức | Ý nghĩa |
|---|---|---|
| **Size** | `sqrt(box_area / frame_area)` | Logo lớn → cao hơn (sqrt để logo cực lớn không áp đảo) |
| **Position** | `exp( −dist_tâm² / (0.3·W)² )` | Gaussian: giữa khung = 1.0, góc ≈ 0.1 |
| **Clarity** | confidence của detector | Logo rõ/nét → cao hơn |
| **OBB** | `area_HBB / area_OBB` | Phạt logo nghiêng; = 1.0 với model HBB hiện tại |

### 3.3 Frame weight (theo criteria đang bật)

```
frame_weight = tích các factor ĐANG BẬT     (factor tắt = 1.0)
```

Bật/tắt factor ở Settings → đổi `frame_weight` → đổi AI %. Mặc định bật:
`size, position, clarity, obb, durationWeight`.

### 3.4 Gom segment + Tier-2 (theo zone)

Với mỗi **zone**, sắp facts theo thời gian rồi cắt thành **segment** (khoảng cách
> 2.5·durSec coi như logo biến mất rồi xuất hiện lại):

```
duration  = (t_cuối − t_đầu) + durSec            (tối thiểu durSec)
mean_w    = trung bình frame_weight trong segment
dw        = duration_weight(duration)  nếu bật "Duration Weight", ngược lại 1.0
quality_segment = mean_w × dw × duration
quality_zone    = Σ quality_segment
```

**Duration weight** (độ dài segment): `< 1s → 0.5 · 1–5s → 1.0 · > 5s → 1.2`.

### 3.5 Từ zone → location → AI %

```
zone_share      = quality_zone / Σ quality(mọi zone có logo) × 100
AI%(location)   = zone_share(anchor) / n          (n = số location-có-logo dùng chung anchor)
```

Sau đó **chuẩn hoá đúng 100.00%** trên các location có logo bằng phương pháp
**phần dư lớn nhất** (largest-remainder) để tránh lệch 100.01% do làm tròn.

> AI % gán theo **vùng (zone)**, không theo tên brand. Nếu nhiều logo cùng rơi vào
> một vùng, exposure cộng chung cho vùng đó.

---

## 4. Tiêu chí AI % (tick được ở Settings)

| Key | Nhãn | Phạm vi | Ảnh hưởng AI %? |
|---|---|---|---|
| `size` | Size Score | mỗi frame | Có |
| `position` | Position Score | mỗi frame | Có |
| `clarity` | Clarity (Confidence) | mỗi frame | Có |
| `obb` | OBB Penalty | mỗi frame | Có (=1.0 với model HBB) |
| `durationWeight` | Duration Weight | mỗi segment | Có |
| `placement` | Placement Multiplier | mỗi video | **Không** — áp đều mọi logo nên triệt tiêu trong tỉ trọng |
| `category` | Category (Share of Voice) | mỗi brand | Không (chưa có category map; để dành) |
| `primeTime` | Prime-time | mỗi segment | Không (cần đồng hồ trận; để dành) |

Tick → lưu vào setting `ai_criteria`, áp cho mọi video. Có thể xem trước nhanh qua
query `?criteria=size,clarity` ở API mà không lưu.

---

## 5. Visibility % — thời gian hiển thị

```
Visibility%(location) = on_screen_seconds(zone) / video_duration_seconds × 100
```

- `on_screen_seconds` = tổng `duration` các segment của zone (thời gian thực logo
  trên màn hình tại vị trí đó).
- Là **chỉ số hiện diện thô** — KHÔNG nhân trọng số criteria, KHÔNG chuẩn hoá → tổng
  không bằng 100%.
- Khác AI % ở chỗ: AI % là *tỉ trọng so với các vị trí khác*; Visibility là *phần
  trăm thời lượng video*.

---

## 6. AI Adjusted % — trung hoà AI với con người

**Vì sao cần:** AI % là exposure thô nên thiên về các vị trí **luôn nhìn thấy**
(tay áo nhìn được cả mặt trước/sau) và bị **detector over-detect** (vd Bartercard
xuất hiện ở hầu hết cảnh) → đảo ngược kỳ vọng hợp đồng. AI Adjusted kéo AI về gần
đánh giá con người.

```
reference(location) = Human-AI %  nếu bạn đã nhập tay cho dòng đó
                      = Human %     nếu chưa (giá trị hợp đồng)

AI_adjusted = (1 − β)·AI_norm  +  β·reference_norm
```

- `AI_norm`, `reference_norm` đều chuẩn hoá về tổng 100 trên các location có logo →
  kết quả tự động tổng 100 (tổ hợp lồi), rồi làm tròn đúng 100.00%.
- **β** = trọng số kéo về phía con người, chỉnh bằng thanh trượt ở Settings
  (mặc định 0.5). `β=0` → bằng AI %. `β=1` → bằng tham chiếu người.

**Ví dụ thực (video M01, β=0.5):**

| Location | Human % | AI % | AI Adjusted % |
|---|---|---|---|
| Main Sponsor (Top Notch) | 26 | 10.81 | **20.35** ↑ |
| Sleeve 3 (Bartercard) | 4 | 24.26 | **14.43** ↓ |
| Sleeve 2 (ATM) | 11 | 1.29 | 6.97 ↑ |

---

## 7. Human % và Human AI %

- **Human %** — giá trị hợp đồng theo vị trí, cấu hình ở Settings (mặc định seed
  theo sheet khách hàng), cho phép override theo từng video.
- **Human AI %** — bạn **nhập tay** trực tiếp ở bảng dashboard sau khi xem video;
  lưu theo từng video (override). Đây là "ground truth" chủ quan, đồng thời là
  tham chiếu ưu tiên cho AI Adjusted (§6).

---

## 8. Sheet Excel "AI % Detail" — thông số tạo ra AI %

Mỗi location-có-logo một dòng, phơi bày các số sau (location không logo để trống):

| Cột | Nguồn | Ý nghĩa |
|---|---|---|
| **Anchor zone** | cấu hình | Vùng pose mà location map tới |
| **AI %** | §3.5 | Kết quả cuối |
| **Quality exposure** | `quality_zone` (§3.4) | Tổng giây quality-weighted của vùng |
| **Detections** | đếm | Số detection rơi vào vùng (2 fps) |
| **Segments** | đếm | Số lần xuất hiện liên tục |
| **On-screen (s)** | `on_screen_seconds` | Tổng thời gian hiện trên màn hình |
| **Mean Size** | TB `size` | Trung bình factor Size của vùng |
| **Mean Position** | TB `pos` | Trung bình factor Position |
| **Mean Clarity** | TB `clarity` | Trung bình confidence |
| **Mean OBB** | TB `obb` | Trung bình OBB (=1.0 model HBB) |
| **Mean frame weight** | TB `frame_weight` | Trung bình trọng số mỗi frame (theo criteria bật) |

Header file Excel cũng ghi: Event, Video, **Kit**, Analysed at, **AI criteria enabled**.

---

## 9. Quy tắc tổng hợp (cheat sheet)

- Tổng **AI %** và **AI Adjusted %** = **đúng 100.00%** trên các location có logo
  (largest-remainder rounding).
- **Visibility %**, **Human %**, **Human AI %**: KHÔNG chuẩn hoá về 100%.
- Location **không logo** → AI/AIadj/Visibility trống; không "ăn" phần của vùng;
  vùng chia exposure cho các location-có-logo dùng chung anchor.
- Nhiều location chung 1 anchor (Collar Back/Top Back/Nape Neck cùng `back-top`)
  → exposure của anchor chia **đều** cho các location-có-logo đó.
- AI % gán theo **vùng**, không theo brand được detect (xem giới hạn §10).

---

## 10. Giới hạn đã biết

1. **Detector bias** — một số class (vd Bartercard) bị over-detect → bơm exposure
   cho vùng tương ứng. AI Adjusted trung hoà ở *tầng báo cáo*; chữa *gốc* cần
   tuning detector (per-class confidence, lọc false positive) — việc riêng.
2. **Vùng cổ/gáy sát nhau** (Collar Back, Nape Neck, Top Back) COCO-17 không tách
   được nên chia sẻ anchor `back-top` → AI % của chúng phụ thuộc cách chia đều.
3. **Exposure rơi ngoài taxonomy** (abdomen, shoulder-r, …) bị loại khỏi tỉ trọng
   để AI % tổng đúng 100% trên các vị trí khách đã cấu hình.
4. **Overlay video** (annotated preview ~60s, body-seg/team-detect ~30s) chỉ phủ
   đoạn đầu video dài; nhưng AI/exposure/Visibility phủ **toàn bộ** video.

---

## 11. Cấu hình & API liên quan

**Settings (trang `/settings`):**
- Locations: Location · Anchor · Logo (home) · Logo (away) · Human %.
- AI Criteria: tick các factor.
- AI Adjusted: thanh trượt β.

**API (backend):**
- `GET /api/analyses/{id}/location-breakdown[?criteria=...]` — bảng (kèm `kit`,
  `enabledCriteria`, `adjustWeight`).
- `PUT /api/analyses/{id}/location-overrides` — lưu override + Human AI %.
- `GET /api/analyses/{id}/location-export.xlsx` — file Excel 2 sheet.
- `GET/PUT /api/settings/locations` · `/api/settings/ai-criteria[/options]` ·
  `/api/settings/ai-adjust` · `/api/settings/anchors` · `/api/settings/brands`.

**Mã nguồn chính:**
- `backend/app/pipeline/location_breakdown.py` — toàn bộ công thức AI %/Adjusted.
- `backend/app/pipeline/visibility.py` — factor Tier-1.
- `backend/app/pipeline/bodyzones.py` — gán detection vào vùng pose.
- `backend/app/api/routes_analyses.py` — dựng bảng, kit-aware, export.
- `backend/app/api/xlsx_export.py` — sinh file Excel.
