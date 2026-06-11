# 5. Exposure & EMV — phương pháp tính

> Đặc tả đầy đủ: [`LOGOS_Exposure_Pricing_Algorithm.md`](../LOGOS_Exposure_Pricing_Algorithm.md)
> (dựa trên ExposureEngine arxiv 2510.04739, Relo Metrics, Shikenso).
> Tài liệu này tóm tắt phần đã triển khai trong code.

## Kiến trúc 3 tầng

```
[Tầng 1] Visibility Score   — mỗi detection, mỗi frame      (visibility.py)
[Tầng 2] Exposure Score     — gộp theo thời gian, per brand  (exposure.py)
[Tầng 3] EMV                — quy ra USD                     (pricing.py)
```

### Tầng 1 — Visibility (0..1 mỗi detection)

Kết hợp: kích thước box (sqrt area ratio) · vị trí trên màn hình (Gaussian,
giữa màn hình điểm cao) · detection confidence · OBB orientation penalty.

- `VISIBILITY_FLOOR=0.02`: dưới ngưỡng này không tính vào segment (logo sponsor
  thật thường ~0.03–0.08 vì nhỏ và lệch tâm — ngưỡng 0.1 của paper sẽ vứt gần hết).

### Tầng 2 — Exposure (per brand)

Detections (đã qua **team filter**) gộp thành **segments** liên tục:

```
Quality Exposure (giây) = Σ segment: duration × avg_visibility × duration_weight
```

- `MIN_SEGMENT_SECONDS=0.5` — flash ngắn hơn không tính.
- Track-id từ ByteTrack giúp nối các detection cùng một logo instance.

### Tầng 3 — EMV

```
EMV = QualityExposure(s) × (CPM / 1000) × AudienceSize × PlacementMultiplier
```

- `CPM`, `AudienceSize` nhập khi upload; `PlacementMultiplier` theo loại
  placement (Live TV 1.0 · Highlight 1.4 · Stream 0.85 · Social 0.7).

## Body zones — 18 kit sponsor slot

Mỗi logo detection được gán (qua YOLO11-pose keypoints, `bodyzones.py`) vào
**slot bán được trên kit** — không phải vùng giải phẫu:

| Nhóm | Slot | Sponsor hiện tại (Away kit) |
|---|---|---|
| Ngực | `chest-center` · `chest-l` · `chest-r` | **Floor Tonic** (main) · Romatica/Ellgren · Bartercard |
| Vai/tay | `shoulder-l/r` · `sleeve-l/r` | MNA Cladding / MNA Support |
| Lưng | `back-top` · `back-center` · `back-lower` | MCP/Fairway · **ACS Group** |
| Bụng | `abdomen` | — |
| Shorts | `shorts-front-l/r` · `shorts-back` · `shorts-leg-l/r` | Cedar Court · **KLG** · Paints&Lacquers / AON |
| Tất | `sock-l/r` | EM Workwear |

Vùng da (đầu, tay trần, đùi, giày) **không có slot** — logo không bao giờ bị
gán vào đó. % per-zone = tỉ trọng exposure → nền tảng cho **pricing theo vị trí**
(slot nào show nhiều → giá cao).

> Ba nơi phải đồng bộ khi đổi danh sách zone: `bodyzones.py` (backend),
> `assignZoneId()` + `ZONE_GLSL` trong `body-segmentation-3d.tsx` (frontend).

## Brand name mapping

Model trả class thô (`klg_away`) → `normalize_class()` bỏ hậu tố kit →
`BRAND_DISPLAY` map sang tên đẹp ("KLG"). Brand mới chưa khai báo sẽ tự
Title-Case. Sửa tại `backend/app/config.py`.
