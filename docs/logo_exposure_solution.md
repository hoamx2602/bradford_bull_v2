# 🏉 Bradford Bulls — AI Logo Exposure Detection System
## Solution Architecture & Implementation Plan

> **Tài liệu này được xây dựng từ quan điểm của một AI Solutions Expert với kinh nghiệm triển khai thực tế các hệ thống computer vision quy mô lớn trong ngành thể thao và media.**

---

## 1. Hiểu Bài Toán (Problem Understanding)

### 1.1. Context Kinh Doanh

Bradford Bulls là một CLB Rugby League chuyên nghiệp (Betfred Championship 2025/26). Họ có một danh mục sponsor lớn được đặt trên jersey và kit của cầu thủ. **Mục tiêu cốt lõi** của bài toán này là:

> **"Tự động đo lường và chứng minh giá trị phơi bày thương hiệu (Brand Exposure Value) của từng sponsor trên các trận đấu broadcast, thay thế hoàn toàn phương pháp thủ công."**

### 1.2. Tại Sao Bài Toán Này Quan Trọng?

Hiện tại, các CLB nhỏ hơn như Bradford Bulls thường:
- Bán sponsorship dựa trên **ước tính** chứ không phải data thực
- Không có bằng chứng ROI cụ thể để thuyết phục sponsor tái ký
- Không thể định giá chính xác từng vị trí logo trên kit
- Mất lợi thế thương lượng so với các đối thủ lớn có công cụ analytics

Hệ thống AI này sẽ biến Bradford Bulls thành **data-driven sports organization**, cho phép:
- Xuất báo cáo sponsorship ROI tự động sau mỗi trận
- Định giá chính xác từng vị trí logo (dựa vào data thực, không phải ước tính)
- Thuyết phục sponsor mới với bằng chứng cụ thể

---

## 2. Phân Tích Sponsor & Kit (Kit Mapping)

### 2.1. Home Kit (Trắng - Red/Amber/Black bands)

| # | Vị Trí | Sponsor | Kích Thước | Priority |
|---|---------|---------|------------|----------|
| 1 | Main Chest (Front) | **TOPNOTCH** | XL | ⭐⭐⭐⭐⭐ |
| 2 | Collar Left (Front) | MNA Cladding | S | ⭐⭐ |
| 3 | Collar Right (Front) | MNA Support Services | S | ⭐⭐ |
| 4 | Left Chest | Romantica | M | ⭐⭐⭐ |
| 5 | Left Chest Lower | Ellgren | S | ⭐⭐ |
| 6 | Right Chest | ATM Hospitality (at...) | M | ⭐⭐⭐ |
| 7 | Right Chest Lower | Bartercard (barte...) | M | ⭐⭐⭐ |
| 8 | Left Sleeve | Lawrence Legal People | M | ⭐⭐⭐ |
| 9 | Right Sleeve | (ATM partial) | S | ⭐⭐ |
| 10 | Top Back | Fairway | S | ⭐⭐ |
| 11 | Upper Back | MCP | M | ⭐⭐⭐ |
| 12 | Mid Back | im (identity/legibility) | M | ⭐⭐⭐ |
| 13 | Back | Bartercard (back) | M | ⭐⭐⭐ |
| 14 | Lower Back | ACS Group | L | ⭐⭐⭐⭐ |
| 15 | Right Sleeve (back) | Chadwick | S | ⭐⭐ |
| 16 | Right Sleeve Back | BETFRED CHAMPIONSHIP | S | ⭐ |
| 17 | Shorts Left (front) | Bradford Bulls crest | S | - |
| 18 | Shorts Right (front) | Cedar Court Hotels | M | ⭐⭐⭐ |
| 19 | Shorts Left (back) | KLG Europe | L | ⭐⭐⭐⭐ |
| 20 | Shorts Right (back) | AON | L | ⭐⭐⭐⭐ |
| 21 | Shorts Left (back) | Paints & Laquers | S | ⭐⭐ |

### 2.2. Away Kit (Đen - Red/Amber/White bands)

| # | Vị Trí | Sponsor | Thay Đổi So Với Home |
|---|---------|---------|----------------------|
| 1 | Main Chest (Front) | **Floor Tonic** | **KHÁC** — Sponsor khác nhau! |
| 2 | Collar/Upper | MNA Cladding, MNA Support | Giống |
| 3 | Left Chest | Romantica | Giống |
| 4 | Right Chest | ATM, Bartercard | Giống |
| ... | Hầu hết vị trí khác | Giống Home | Chỉ background màu khác |

> ⚠️ **Quan trọng:** Main chest sponsor **khác nhau** giữa Home và Away kit. Hệ thống phải phân biệt được kit type trước khi assign sponsor.

### 2.3. Mapping Giữa CSV Pricing và Visual Positions

```
CSV Column          → Visual Position         → Priority Weight
─────────────────────────────────────────────────────────────
Main Sponsor        → Chest Front Center      → 26%
Collar Back         → Collar (Back side)      → 8%
Collar Bone         → Collar (Front, each)    → 8%
Chest (opp Badge)   → Left/Right Chest area   → 7%
Sleeve 1/2/3        → Multiple sleeve logos   → 4/11/4%
Top Back            → Upper back (Fairway)    → 5%
Nape Neck           → Collar back logo        → 3%
Bottom Back         → Lower back (ACS Group)  → 3%
Top Back Shorts     → Shorts back (KLG)       → 5%
Shorts Front        → Cedar Court Hotels      → 3%
Shorts Back 1/2     → AON / Paints & Laquers  → 3/3%
Socks               → Ellgren on socks        → 1%
```

---

## 3. Kiến Trúc Giải Pháp (Solution Architecture)

### 3.1. Tổng Quan Hệ Thống

```
┌─────────────────────────────────────────────────────────────┐
│                    VIDEO INPUT LAYER                        │
│  M01_1080p / M02_720p / M06_1080p → Frame Extraction       │
└──────────────────────────┬──────────────────────────────────┘
                           │
┌──────────────────────────▼──────────────────────────────────┐
│                 PREPROCESSING MODULE                         │
│  • Scene Detection (cut/replay/commercial filter)           │
│  • Quality Assessment (blur, exposure, resolution)          │
│  • Broadcast Overlay Masking (scoreboard, clock, graphics)  │
└──────────────────────────┬──────────────────────────────────┘
                           │
┌──────────────────────────▼──────────────────────────────────┐
│              PLAYER DETECTION & TRACKING                     │
│  • YOLOv11 → Bounding Box cho mỗi player                   │
│  • ByteTrack → Duy trì player ID xuyên suốt match          │
│  • Team Classification → Phân biệt Home/Away/Referee        │
└──────────────────────────┬──────────────────────────────────┘
                           │
┌──────────────────────────▼──────────────────────────────────┐
│              POSE ESTIMATION MODULE                          │
│  • YOLO-Pose / RTMPose → 17 keypoints/player               │
│  • Body Part Segmentation → Map các vùng logo trên body    │
│  • Orientation Detection → Front/Back/Side facing           │
└──────────────────────────┬──────────────────────────────────┘
                           │
┌──────────────────────────▼──────────────────────────────────┐
│              LOGO DETECTION & RECOGNITION                    │
│  • Pose-Guided ROI Extraction → Crop từng vùng logo        │
│  • Logo Template Matching → So sánh với template library   │
│  • OBB Detection → Oriented Bounding Box cho rotated logos │
│  • Confidence Scoring → Per-logo detection confidence       │
└──────────────────────────┬──────────────────────────────────┘
                           │
┌──────────────────────────▼──────────────────────────────────┐
│              QUALITY SCORING ENGINE                          │
│  • Size Score → % of screen occupied                        │
│  • Position Score → Centrality weighting                    │
│  • Clarity Score → Sharpness/blur assessment               │
│  • Occlusion Score → Visibility percentage                  │
│  • Duration Accumulator → Rolling frame counter             │
└──────────────────────────┬──────────────────────────────────┘
                           │
┌──────────────────────────▼──────────────────────────────────┐
│              EXPOSURE VALUE CALCULATOR                       │
│  • Raw Exposure Duration (seconds)                          │
│  • Weighted Exposure (Quality Score × Duration)             │
│  • Media Value Equivalent (MVE)                             │
│  • Per-Sponsor Breakdown                                    │
│  • Per-Match / Per-Half / Per-Period Reports                │
└──────────────────────────┬──────────────────────────────────┘
                           │
┌──────────────────────────▼──────────────────────────────────┐
│              REPORTING & DASHBOARD                           │
│  • PDF Report Generator (per match)                         │
│  • Interactive Dashboard (sponsor view)                     │
│  • Video Clips (highlight reel per sponsor)                 │
│  • CSV/JSON Export for external tools                       │
└─────────────────────────────────────────────────────────────┘
```

### 3.2. Chi Tiết Từng Module

#### Module 1: Preprocessing & Scene Detection

**Vấn đề cần giải quyết:**
- Video dài 3 tiếng chứa: Warm-up, Match (2 halves), Half-time, Replays, Commercials
- Phải loại bỏ các phân đoạn không phải live play
- Phải tránh đếm replay như exposure thực

**Giải pháp:**
```python
class SceneDetector:
    # PySceneDetect để phát hiện các scene cuts
    # Classifier nhận biết: live_play / replay / commercial / studio
    # Timestamp-based filtering: chỉ xử lý live play segments
    # Replay detection: optical flow + graphic overlay detection
```

**Output:** Danh sách timestamps cho các live play segments

---

#### Module 2: Player Detection & Tracking

**Mô hình:** YOLOv11 fine-tuned trên rugby/football player detection

**Tracking:** ByteTrack (tốt nhất cho high-density occlusion scenarios)

**Team Classification:**
```
Method A (Primary): Color histogram của jersey region
  → Home kit: White dominant, Red/Amber/Black bands
  → Away kit: Black dominant, Red/Amber/White bands
  
Method B (Fallback): Pre-trained jersey classifier
  → CNN trained trên crop của từng jersey type
  → Handles partial occlusion, back-facing players
```

**Re-identification:** Khi player bị occluded trong tackle:
- Kalman Filter dự đoán vị trí
- Re-ID features maintain player ID
- Exposure timer PAUSE khi confidence < threshold, không STOP

---

#### Module 3: Pose Estimation & ROI Extraction

**Mô hình:** YOLO-Pose (17 keypoints)

**Keypoints quan trọng nhất:**
```
Shoulders (5, 6)   → Define chest region
Hips (11, 12)      → Define torso boundary  
Neck (0)           → Define collar area
Elbows (7, 8)      → Define sleeve regions
Knees (13, 14)     → Define shorts regions
```

**ROI Extraction Logic:**
```python
def extract_logo_regions(keypoints, player_bbox):
    chest_region = compute_chest_roi(
        left_shoulder=keypoints[5],
        right_shoulder=keypoints[6],
        left_hip=keypoints[11],
        right_hip=keypoints[12]
    )
    collar_region = compute_collar_roi(neck=keypoints[0], ...)
    sleeve_left = compute_sleeve_roi(shoulder=keypoints[5], elbow=keypoints[7])
    sleeve_right = compute_sleeve_roi(shoulder=keypoints[6], elbow=keypoints[8])
    shorts_region = compute_shorts_roi(hips=keypoints[11:13], knees=keypoints[13:15])
    back_region = compute_back_roi(...)  # when facing away
    
    return {
        'chest': chest_region,
        'collar': collar_region,
        'sleeve_left': sleeve_left,
        'sleeve_right': sleeve_right,
        'shorts': shorts_region,
        'back': back_region
    }
```

**Orientation Detection:**
- Front-facing: Chest logos visible
- Back-facing: Back logos visible (ACS Group, KLG, AON)
- Side-facing: Một sleeve visible + partial chest/back

---

#### Module 4: Logo Detection & Recognition

**Hai lớp phát hiện:**

**Lớp 1 — Template Matching + Feature Extraction**
```
Input: Cropped ROI từ pose-guided extraction
Method: 
  1. SIFT/ORB feature matching với logo templates
  2. Phù hợp với kích thước nhỏ, rotated, partially occluded logos
  3. Confidence score dựa trên match quality
```

**Lớp 2 — CNN Classifier (Robust Recognition)**
```
Input: ROI crop (normalized size)
Architecture: EfficientNet-B0 / MobileNetV3 (nhẹ, fast)
Output: [logo_class, confidence]
Classes: [topnotch, floor_tonic, aon, klg_europe, acs_group, 
          cedar_court, romantica, mcp, mna_cladding, ...]
```

**OBB (Oriented Bounding Box) cho accuracy cao hơn:**
- Logos trên jersey bị rotate theo angle của body
- OBB khớp chính xác hơn, giảm noise pixels
- Dùng YOLOv8-OBB làm detection head

---

#### Module 5: Quality Scoring Engine

Đây là **trái tim** của hệ thống. Mỗi logo detection instance nhận một Quality Score từ 0-100%.

**Formula:**

```
Quality Score = (Size_Score × 0.30) 
              + (Position_Score × 0.25)
              + (Clarity_Score × 0.25)
              + (Occlusion_Score × 0.20)
```

**Chi tiết từng sub-score:**

| Sub-Score | Cách Tính | Range |
|-----------|-----------|-------|
| **Size Score** | (logo_pixels / total_pixels) × scale_factor | 0-100% |
| **Position Score** | Gaussian weighting từ center | Center=100%, Edge=20% |
| **Clarity Score** | Laplacian variance (blur detection) | Sharp=100%, Blurry=0% |
| **Occlusion Score** | % of logo bounding box visible (không bị che) | Full=100%, Half=50% |

**Weighted Exposure Duration:**
```
WED = Σ (frame_duration × quality_score_i)

Ví dụ:
- Frame 1: Logo xuất hiện 0.033s (30fps), quality = 85% → 0.028s WED
- Frame 2: Logo blur/edge, quality = 40% → 0.013s WED  
- Tổng raw: 10 giây, WED: 6.5 giây
```

**Media Value Equivalent (MVE):**
```
MVE = (WED / 30) × Cost_of_30s_ad_slot

Ví dụ:
- WED = 120 giây (2 phút quality exposure)
- 30s ad slot giả sử £500 (cần input từ client)
- MVE = (120/30) × £500 = £2,000
```

---

#### Module 6: Output & Reporting

**Report per match gồm:**

**Executive Summary:**
- Total duration processed (live play only)
- Total brand exposures detected
- Total weighted exposure time per sponsor
- Estimated Media Value (cần TVR data)

**Per-Sponsor Report:**
- Sponsor Name + Logo
- Exposure on which kit position
- Raw exposure time (seconds)
- Quality score average
- Weighted exposure time
- % of match time visible
- Frame count
- Best/worst exposure clips

**Benchmark Comparison:**
- So sánh với CSV pricing percentages
- Actual vs. Expected exposure ratio
- Recommendations cho season berikutnya

---

## 4. Thách Thức Kỹ Thuật & Cách Giải Quyết

### Challenge 1: Logos nhỏ và bị biến dạng

**Problem:** Main chest logo (~200x100px trong frame 1080p), nhưng collar logos có thể chỉ 30x15px

**Solution:**
- Super-resolution cho ROI crops trước khi recognition
- Multi-scale template matching
- Train CNN trên augmented data (scale, rotation, perspective)

### Challenge 2: Occlusion trong tackle

**Problem:** Rugby League rất physical. Players stack lên nhau trong tackle, logo biến mất hoàn toàn

**Solution:**
- ByteTrack + Kalman Filter giữ player ID
- Exposure timer PAUSE (không dừng) khi occluded > 80%
- Re-ID khi player xuất hiện lại: tiếp tục track cùng ID

### Challenge 3: Home vs Away kit detection

**Problem:** Phải biết đang xử lý match nào (M01_white = Home, M06_black = Away)

**Solution (2 layers):**
1. **Filename metadata:** M01_white → Home kit, M06_black → Away kit  
2. **Auto-detection:** Color histogram của player cluster → Dominant color → Kit type
3. **Cross-validation:** Match với known sponsor positions per kit type

### Challenge 4: Replay vs. Live Play

**Problem:** Replays không nên được đếm gấp đôi

**Solution:**
- Scene detection: Replays có graphic overlay ("REPLAY"), slow-motion
- Optical flow analysis: Replay = reverse/slow motion flow patterns  
- Exclude all non-forward-chronological segments

### Challenge 5: Multiple players in frame

**Problem:** Khi nhiều player xuất hiện cùng lúc, phải tránh double-count

**Solution:**
- Track theo player ID (unique ID per player per match)
- Share of Voice (SOV): Nếu 3 players có logo visible, mỗi player nhận 1/3 SOV bonus discount hoặc tính riêng per-instance
- Frame-level deduplication: Mỗi sponsor chỉ được count 1 lần per frame (dù nhiều player đeo logo đó)

### Challenge 6: Broadcast overlay interference

**Problem:** Score graphic, clock, và lower-thirds có thể overlap với player area

**Solution:**
- Fixed mask zones (score thường góc trên trái/phải)
- Dynamic overlay detection bằng OCR (detect text regions)
- Exclude những detections nằm trong overlay zones

---

## 5. Tech Stack Đề Xuất

### Core ML/CV Stack
```
Detection:       YOLOv11 (Ultralytics) — State of art 2025
Tracking:        ByteTrack (integrated với YOLO)
Pose:            YOLOv11-Pose (17 keypoints)
Logo Detect:     YOLOv11-OBB (Oriented Bounding Box)
Classification:  EfficientNet-B0 (fine-tuned trên sponsor logos)
Blur Detection:  OpenCV Laplacian variance
```

### Infrastructure
```
Processing:      Python 3.11 + PyTorch 2.x
Video:           OpenCV + FFmpeg (frame extraction, scene detection)
Scene Detection: PySceneDetect
Storage:         Local (MVP) → Cloud Storage (Production)
GPU:             NVIDIA (CUDA) — cần ít nhất RTX 3080 hoặc A4000 cho 1080p 30fps
Database:        SQLite (MVP) → PostgreSQL (Production)
```

### Reporting Stack
```
PDF Reports:     ReportLab / WeasyPrint
Dashboard:       Streamlit (rapid MVP) → React + FastAPI (Production)
Visualization:   Plotly / Matplotlib
Export:          CSV, JSON, PDF
```

---

## 6. Phân Tích Dữ Liệu Hiện Có

### Videos:
| File | Size | Resolution | Estimated Duration | Kit |
|------|------|------------|-------------------|-----|
| M01_white_1080p.mp4 | 1.74GB | 1080p | ~2-3 hours | Home (White) |
| M02_white_720p.mp4 | 1.25GB | 720p | ~2-3 hours | Home (White) |
| M06_black_1080p.mp4 | 361MB | 1080p | ~30-45 min | Away (Black) |

### Sponsor Logos:
- **22 logo assets** đã có trong `Sponsor Logo/`
- Có cả light và dark version của một số logos (CCH white/black, AON red/white)
- Một số logos có nền trong suốt (PNG) — tốt cho template matching

### Kit Assets:
- Có full kit design reference (Home + Away)
- Có thể dùng để map chính xác vị trí logo theo % tọa độ trên jersey template

---

## 7. Roadmap Triển Khai (Phased Approach)

### Phase 0: Foundation (2-3 tuần)
- [ ] Xây dựng logo template library (resize, normalize tất cả 22 logos)
- [ ] Phân tích videos: extract sample frames từ mỗi video
- [ ] Define ground truth: label thủ công 200-300 frames (bounding boxes)
- [ ] Xác nhận tech stack, setup dev environment
- [ ] Tạo evaluation metrics framework

### Phase 1: Core Detection MVP (4-6 tuần)
- [ ] Implement player detection (YOLOv11)
- [ ] Implement team classification (Home/Away)
- [ ] Implement basic pose estimation
- [ ] Implement main chest logo detection (chỉ main sponsor trước)
- [ ] Basic exposure timer (raw, không weighted)
- [ ] Simple output: CSV với per-match exposure durations

**Milestone:** Có thể chạy M06 (ngắn nhất) end-to-end và lấy được exposure time cho Floor Tonic (main chest Away)

### Phase 2: Full Logo Coverage (4-6 tuần)
- [ ] Implement pose-guided ROI extraction cho tất cả 20+ positions
- [ ] Train/fine-tune logo classifier trên tất cả sponsors
- [ ] Implement OBB detection
- [ ] Handle Home vs Away kit logic
- [ ] Scene detection (loại replay, commercial)

**Milestone:** Full per-sponsor exposure report cho 1 complete match

### Phase 3: Quality Scoring (3-4 tuần)
- [ ] Implement size scoring
- [ ] Implement position (centrality) scoring
- [ ] Implement clarity/sharpness scoring
- [ ] Implement occlusion detection
- [ ] Implement Weighted Exposure Duration
- [ ] Validate Quality Scores với human review

### Phase 4: Valuation & Reporting (2-3 tuần)
- [ ] Implement MVE calculation (cần input: TV ad rate)
- [ ] Build PDF report generator
- [ ] Build Streamlit dashboard
- [ ] Build sponsor-view portal (per-sponsor access)
- [ ] Video clip extractor (best exposure moments per sponsor)

### Phase 5: Production & Optimization (ongoing)
- [ ] Performance optimization (batch processing)
- [ ] New season kit update workflow
- [ ] Accuracy validation & model retraining pipeline
- [ ] Integration với club's existing tools

---

## 8. Câu Hỏi Cần Clarify (Mở)

Tôi cần bạn trả lời các câu hỏi sau để hoàn thiện thiết kế:

### A. Về Business Requirements

1. **TV Ad Rate:** Để tính MVE, cần biết cost of a 30-second ad slot trong broadcast của Bradford Bulls. Bạn có con số này không, hay cần estimate?

2. **Replay counting:** Replay có được tính vào exposure không? Nhiều hệ thống enterprise loại bỏ replay hoàn toàn.

3. **Match segments:** Có cần report riêng cho từng half (1st half, 2nd half, extra time)? Hay chỉ cần tổng?

4. **Frequency:** Hệ thống sẽ chạy: (a) Real-time trong trận? (b) Post-match processing sau trận? (c) Batch processing cho nhiều trận cùng lúc?

5. **Multiple matches:** Các file M01, M02, M06 có phải 3 trận khác nhau không? Hay M01 và M02 là cùng 1 trận nhưng 2 bản ghi khác nhau?

6. **Audience data:** Bradford Bulls có data về viewership/TVR (TV Rating) không? Cần để tính Media Value chính xác hơn.

### B. Về Technical Requirements

7. **Hardware:** Bạn có GPU không? Nếu có, model gì? Nếu không, sẽ cần cloud processing (AWS/GCP/Azure).

8. **Processing time:** Acceptable processing time là bao lâu per match? 1 hour? 4 hours? Overnight OK?

9. **Storage:** Có cần lưu trữ output video clips không? Điều này ảnh hưởng lớn đến storage requirements.

10. **Integration:** Hệ thống này sẽ standalone hay integrate với tool/platform nào khác?

### C. Về Data & Accuracy

11. **Minimum accuracy:** Acceptable accuracy là bao nhiêu? 80%? 90%? 95%? Accuracy cao hơn = training data nhiều hơn.

12. **Labeling budget:** Có ngân sách/thời gian để label training data thủ công không? (MVP cần khoảng 300-500 labeled frames)

13. **Multiple seasons:** Hệ thống có cần xử lý videos từ các mùa trước không (với kit design khác)?

14. **Away matches:** Video M06 (black kit) — đây là trận sân nhà hay sân khách? Camera góc nhìn có khác nhau không?

### D. Về Output & Delivery

15. **Report format:** Sponsor muốn nhận report dưới dạng gì? PDF email? Web dashboard? Excel?

16. **Delivery timing:** Sponsor cần report sau bao lâu kể từ khi trận kết thúc? Same-day? Next-day?

17. **Sponsor access:** Mỗi sponsor có muốn xem dashboard riêng của họ không, hay chỉ club xem tổng?

---

## 9. Rủi Ro & Mitigation

| Rủi Ro | Mức Độ | Mitigation |
|--------|--------|------------|
| Logo quá nhỏ để detect | High | Super-resolution + multi-scale detection |
| Occlusion trong tackle | High | Tracking + pause logic |
| Home/Away confusion | Medium | 2-layer kit detection |
| Replay double-counting | Medium | Scene detection + timestamp filtering |
| Thiếu training data | High | Data augmentation + semi-supervised learning |
| Processing speed (3h video) | Medium | GPU optimization + batching |
| Kit thay đổi theo mùa | Low | Modular sponsor config file |
| Logo bị warped/stretched | Medium | OBB + perspective correction |

---

## 10. Đề Xuất Bước Tiếp Theo

**Ngay lập tức (tuần này):**
1. Trả lời 17 câu hỏi clarification ở Section 8
2. Extract 30 sample frames từ mỗi video (90 frames tổng)
3. Xem xét và xác nhận mapping vị trí logo (Section 2)
4. Xác nhận hardware/infrastructure

**Sau khi có clarification:**
1. Build Phase 0 foundation
2. Create labeled ground truth dataset
3. Setup development pipeline

---

*Document Version: 1.0 | Created: 2026-05-16 | Author: AI Solutions Expert*
*Status: Awaiting Client Clarification on 17 open questions*
