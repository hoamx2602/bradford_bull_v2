# Testing Guide — Motion Blur Tiers

Mục tiêu: kiểm tra 3 chiến lược xử lý blur trên frame thực từ 3 video mẫu,
xác định tier nào cải thiện sharpness nhiều nhất cho mục đích annotation logo.

---

## Môi trường & setup một lần

```bash
# Clone / vào thư mục project
cd bradford_bulls_v2_copy_v3

# Cài dependencies cơ bản (nếu chưa có)
pip install -e ".[dev]"

# Kiểm tra tất cả tests trên main pass
python -m pytest tests/ -q
# Expected: 32 passed
```

---

## Frame cần test

Từ kết quả `sample_for_eval.py` chạy trước, những frame này đã **pass pipeline nhưng blurry nhất**:

| Video | Frame idx | Thời điểm | Sharp | Ghi chú |
|---|---|---|---|---|
| `M06_black_1080p.mp4` | **5450** | 5:01 | 12.5 | Blur nhất, close-up |
| `M06_black_1080p.mp4` | **16947** | 9:24 | 14.1 | Blur, 3 players |
| `M06_black_1080p.mp4` | **15372** | 8:32 | 14.7 | Blur, 3 players |
| `M01_white_1080p.mp4` | **77149** | 42:51 | 33.7 | Borderline, close-up |

> **Bắt đầu với M06 frame 5450** — đây là worst case rõ ràng nhất.

---

## Bước 0 — Baseline (main branch)

```bash
git checkout main
python -m pytest tests/ -q   # 32 passed

python scripts/compare_tiers.py \
    --video videos/M06_black_1080p.mp4 \
    --frame 5450 \
    --color black \
    --save compare_output/baseline
```

**Kết quả mong đợi:**
- Hai ô giống nhau (original = processed, vì main không có tier nào)
- `Original sharp: 12.5`
- Thư mục `compare_output/baseline/` có 3 file JPG

**Việc cần làm:** nhìn vào ảnh và ghi nhận: logo có nhìn thấy không? Jersey có rõ không?

---

## Bước 1 — Tier 1: Temporal Burst Selection

**Ý tưởng:** tìm frame sắc nét nhất trong cửa sổ ±15 frame quanh frame 5450.
Không thay đổi pixel — chỉ chọn frame tốt hơn từ video gốc.

```bash
git checkout tier1/burst-selection
python -m pytest tests/test_burst.py -v   # 9 passed
```

### Test với 3 kích thước cửa sổ khác nhau

```bash
# Window nhỏ: ±5 frames (~0.17s)
python scripts/compare_tiers.py \
    --video videos/M06_black_1080p.mp4 \
    --frame 5450 --color black \
    --window 5 \
    --save compare_output/tier1_w5

# Window trung bình: ±15 frames (~0.5s)  ← default
python scripts/compare_tiers.py \
    --video videos/M06_black_1080p.mp4 \
    --frame 5450 --color black \
    --window 15 \
    --save compare_output/tier1_w15

# Window lớn: ±30 frames (~1s)
python scripts/compare_tiers.py \
    --video videos/M06_black_1080p.mp4 \
    --frame 5450 --color black \
    --window 30 \
    --save compare_output/tier1_w30
```

### Câu hỏi cần trả lời khi nhìn kết quả

- [ ] Sharp score tăng lên bao nhiêu %?
- [ ] Frame index có thay đổi không? (in ra "Best frame idx: XXXX, was 5450")
- [ ] Khi tăng window từ 5 → 15 → 30, điểm sharp còn tăng nữa không?
- [ ] Logo jersey có nhìn rõ hơn không?

### Chạy thêm trên 2 video còn lại

```bash
python scripts/compare_tiers.py \
    --video videos/M01_white_1080p.mp4 \
    --frame 77149 --color white \
    --window 15 \
    --save compare_output/tier1_M01

python scripts/compare_tiers.py \
    --video videos/M06_black_1080p.mp4 \
    --frame 16947 --color black \
    --window 15 \
    --save compare_output/tier1_f16947
```

---

## Bước 2 — Tier 2: NAFNet Single-Frame Deblurring

**Ý tưởng:** reconstruct pixel từ blur trail bằng deep learning. Không cần frame lân cận.

### Cài đặt (chỉ cần làm 1 lần)

```bash
git checkout tier2/single-image-deblur
pip install basicsr gdown
python -m pytest tests/test_deblur_single.py -v   # 10 passed
```

### Tải weights NAFNet (~67 MB)

```bash
gdown --id 1Fr2QadtDCEXg6iwWX8OzeZLgFm955Yb9 \
      -O ~/.cache/nafnet/NAFNet-GoPro-width64.pth
```

> Nếu `gdown` bị block bởi Google Drive: tải thủ công từ
> https://github.com/megvii-research/NAFNet rồi đặt vào `~/.cache/nafnet/`.
> Nếu không tải được, script tự dùng **Wiener fallback** — chất lượng thấp hơn
> nhưng vẫn chạy được để test flow.

### Chạy deblur

```bash
python scripts/compare_tiers.py \
    --video videos/M06_black_1080p.mp4 \
    --frame 5450 --color black \
    --deblur \
    --save compare_output/tier2_nafnet

# Frame blur nhẹ hơn để so sánh
python scripts/compare_tiers.py \
    --video videos/M01_white_1080p.mp4 \
    --frame 77149 --color white \
    --deblur \
    --save compare_output/tier2_M01
```

### Terminal sẽ in

```
[DeblurSingle] NAFNet loaded on cpu.   ← hoặc 'cuda'
─────────────────────────────────────────────────
Tier            : Tier 2 — NAFNet / Wiener deblur
Original  sharp : 12.5
Processed sharp : XX.X  (+XX%)
─────────────────────────────────────────────────
```

### Câu hỏi cần trả lời

- [ ] NAFNet có load được không hay dùng Wiener fallback?
- [ ] Sharp score tăng bao nhiêu %?
- [ ] Nhìn vào ảnh: logo jersey có edge rõ hơn không?
- [ ] Có artifact (vệt lạ, màu sai) trên jersey không? — quan trọng vì ảnh hưởng annotation

---

## Bước 3 — Tier 3: RAFT Optical Flow Fusion

**Ý tưởng:** căn chỉnh ±5 frames lân cận vào frame trung tâm bằng RAFT,
fuse bằng trọng số sharpness — "lucky imaging" cho thể thao.

```bash
git checkout tier3/optical-flow-fusion
python -m pytest tests/test_flow_fusion.py -v   # 10 passed
```

> Không cần cài thêm gì — RAFT có sẵn trong `torchvision >= 0.13`.
> Lần đầu chạy tự download RAFT weights (~20 MB).

### Chạy fusion

```bash
# Window mặc định ±5 frames
python scripts/compare_tiers.py \
    --video videos/M06_black_1080p.mp4 \
    --frame 5450 --color black \
    --fuse \
    --save compare_output/tier3_w5

# Window rộng hơn ±10 frames (chậm hơn ~2×)
python scripts/compare_tiers.py \
    --video videos/M06_black_1080p.mp4 \
    --frame 5450 --color black \
    --fuse --window 10 \
    --save compare_output/tier3_w10
```

> **Lưu ý thời gian:** RAFT trên CPU với 1080p frame tốn ~30-60s/frame.
> Nếu chạy trên GPU (Colab T4), chỉ tốn ~2-5s/frame.

### Câu hỏi cần trả lời

- [ ] Sharp score tăng bao nhiêu %?
- [ ] Có ghost artifact (bóng mờ của player ở sai vị trí) không?
- [ ] Biên của cầu thủ có bị nhòe do alignment không khớp không?
- [ ] So với Tier 1 và 2, cái nào logo rõ hơn?

---

## Bước 4 — So sánh tổng hợp

### Gom tất cả frame đã xử lý vào 1 thư mục

```bash
mkdir -p compare_final
# Copy comparison images từ mỗi tier
cp compare_output/baseline/*_comparison.jpg    compare_final/
cp compare_output/tier1_w15/*_comparison.jpg   compare_final/
cp compare_output/tier2_nafnet/*_comparison.jpg compare_final/
cp compare_output/tier3_w5/*_comparison.jpg    compare_final/
```

### Label thủ công để đo bằng số

```bash
# Label: g = tốt (logo nhìn thấy rõ), b = không tốt
python eval/label_frames.py \
    --frames-dir compare_final/ \
    --output compare_labels.csv

# Đo AUC và best threshold
python eval/eval_sharpness.py \
    --labels compare_labels.csv \
    --plot
```

### Ghi kết quả vào bảng này

| Tier | Frame | Sharp gốc | Sharp sau | % tăng | Artifact? | Logo rõ? |
|---|---|---|---|---|---|---|
| Baseline | M06-5450 | 12.5 | 12.5 | — | Không | ? |
| Tier 1 w=5 | M06-5450 | 12.5 | ? | ? | Không | ? |
| Tier 1 w=15 | M06-5450 | 12.5 | ? | ? | Không | ? |
| Tier 1 w=30 | M06-5450 | 12.5 | ? | ? | Không | ? |
| Tier 2 NAFNet | M06-5450 | 12.5 | ? | ? | ? | ? |
| Tier 3 w=5 | M06-5450 | 12.5 | ? | ? | ? | ? |
| Tier 3 w=10 | M06-5450 | 12.5 | ? | ? | ? | ? |

---

## Điều cần đặc biệt chú ý khi nhìn ảnh

### Tier 1 — tìm gì
- Nhìn góc trên: "Best frame idx: XXXX, was 5450" → nếu idx khác nghĩa là burst tìm được frame tốt hơn
- Logo có sắc nét hơn mà không có artifact nào không?
- Nếu sharp score KHÔNG tăng: đoạn video này mọi frame đều blur → cần tier 2 hoặc 3

### Tier 2 — tìm gì
- Nhìn sát jersey: edge của số áo, text logo có sharper không?
- Màu sắc có bị shift không (NAFNet đôi khi làm đậm màu hơn một chút)?
- Nhìn biên giữa player và background: có halo (viền sáng) không?

### Tier 3 — tìm gì
- Ghost: nếu player di chuyển nhanh, alignment RAFT sai → thấy "bóng" mờ của player ở vị trí cũ
- Nhìn tay/chân: nếu có ghosting → alignment quality thấp → cần giảm window hoặc dùng tier 2

---

## Quyết định cuối cùng

Sau khi test, chọn 1 trong 3 kết quả:

**Nếu Tier 1 đủ tốt (sharp tăng rõ, không artifact):**
```bash
git checkout tier1/burst-selection
# Đây là production branch — không cần model nào thêm
```

**Nếu Tier 1 không đủ (frame vẫn blur sau burst):**
```bash
git checkout tier2/single-image-deblur
# Cần: basicsr + NAFNet weights
```

**Nếu Tier 2 tạo artifact trên logo:**
```bash
git checkout tier3/optical-flow-fusion
# Cần: torchvision (có sẵn), GPU nếu muốn nhanh
```

**Nếu muốn kết hợp tốt nhất:** merge tier1 + tier2/tier3 —
Tier 1 chọn frame tốt nhất trước, sau đó tier 2/3 deblur frame đó.
Trao đổi với team trước khi merge.
