# 8. Annotation & Training — model logo

Workflow data trên **Roboflow** (workspace `hoamxit`), train YOLO26 local.

## Nguyên tắc annotate (rút từ review dataset M06)

| Trường hợp | Quyết định |
|---|---|
| Logo rõ, ≥50% diện tích hiện | Annotate |
| Bị che một phần nhưng nhận ra được | Annotate (model cần học occlusion) |
| Motion blur nhưng vẫn nhận ra | Annotate (video thể thao luôn blur) |
| Logo < ~15px cạnh nhỏ / che >70% / chỉ vài pixel ở xa | **Không** annotate |
| Logo trong màn hình replay lồng nhau (Video Ref) | **Không** — context sai |
| Logo BullsTV overlay góc màn hình | **Không** — không phải sponsor trên áo |

Lỗi hay gặp đã từng dính: bỏ sót frame có logo (model học "không có logo" sai),
annotate cả player trong khung Video-Ref-Replay, box quá nhỏ trên cầu thủ xa.
Box bao sát logo, dư ≤5px mỗi cạnh.

## Quy mô dữ liệu

- Mục tiêu ≥ **300–500 instance/class**; class < 30 instance gần như không học được
- Cân bằng class: ưu tiên thêm ảnh cho class hiếm trước khi thêm ảnh class phổ biến

## Model-Assisted Labeling (đã áp dụng — nhanh hơn 5–10×)

```
1. Annotate tay 50–80 ảnh "sạch" (close-up, rõ, đủ mỗi class ≥5–8 lần)
2. Train model v1 nhanh (vài chục epoch)
3. Bật Roboflow Label Assist → model gợi ý box trên ảnh mới
4. Người chỉ accept/sửa/thêm → nhanh hơn vẽ tay ~80%
5. Gộp tất cả → train model thật
```

## Cấu hình Roboflow version

- **Split 70/20/10** (train/valid/test) — đừng để 100% train
- **Resize: Fit/Letterbox 1280×1280** — KHÔNG dùng Stretch (méo logo);
  1280 vì logo nhỏ (~3–5% bề ngang frame) cần đủ pixel
- Augmentation (multiplier ~3×):
  - ✓ Flip ngang · Rotation ±15° · Brightness ±30% · Exposure ±15% ·
    Blur 0–3px · Noise nhẹ · Crop 0–20% · Cutout **≤5%, count ≤3** · Mosaic
  - ✗ Flip dọc · Shear mạnh · Saturation mạnh (đổi màu logo)

## Train local

Dataset YOLO format trong `logo_detection/`; train ra `runs/<name>/weights/best.pt`
— backend tự pick bản mới nhất (`MODEL_PATH` để pin cụ thể).

> ⚠️ **ultralytics 8.3.40 bắt buộc** — weights hiện tại không detect trên 8.4.x.

## Lựa chọn kiến trúc

- **YOLO26 @1280**: lựa chọn hiện tại — tốt với dataset nhỏ, inference nhanh
- **RF-DETR**: chỉ đáng benchmark khi dataset ≥ ~3000 ảnh; khi đó train song
  song và so mAP-small + FPS trên validation thật, đừng đoán trước
- Chất lượng annotation quan trọng hơn kiến trúc model

## Đánh giá

So sánh các bản train bằng mAP@0.5 per-class + confusion matrix (xem class nào
nhầm nhau), và quan trọng nhất: chạy thử trên clip thật qua pipeline
(`TESTING_GUIDE.md`) xem detection/EMV có hợp lý.
