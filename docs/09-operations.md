# 9. Vận hành & Troubleshooting

## Tuning knobs chính (env vars — đầy đủ trong `backend/app/config.py`)

| Var | Default | Khi nào chỉnh |
|---|---|---|
| `DEVICE` | `auto` | `0` (CUDA) · `mps` · `cpu` |
| `SAMPLE_FPS` | `2.0` | giảm để chạy nhanh hơn (đánh đổi độ mịn exposure) |
| `IMGSZ` | `1280` | model train ở 1280; hạ 960 đổi tốc độ lấy accuracy |
| `CONF` | `0.25` | ngưỡng detect |
| `VISIBILITY_FLOOR` | `0.02` | dưới ngưỡng không tính segment |
| `MIN_SEGMENT_SECONDS` | `0.5` | flash ngắn hơn bị bỏ |
| `PREVIEW_MAX_FRAMES` | `1800` | cap render preview full-fps (~60–72s đầu) |
| `ENABLE_POSE` | `true` | tắt để bỏ body zones (nhanh hơn) |
| `ENABLE_BODYSEG` | `true` | overlay video body-part |
| `TEAM_*` | — | xem [Team filter](04-team-filter.md) |

## Lỗi thường gặp

| Triệu chứng | Nguyên nhân / xử lý |
|---|---|
| Model không detect gì dù video có logo | **ultralytics ≠ 8.3.40** — `pip install ultralytics==8.3.40` |
| `SigLIP unavailable ... sentencepiece` | Đã fix bằng vision-only (`SiglipVisionModel`). Nếu còn gặp: code cũ — pull bản mới |
| Team filter `dropRate` ≈ 0% hoặc > 90% bất thường | Bootstrap chọn nhầm cluster — kiểm tra `data/kit_anchors/<kit>/` tồn tại; xem `data/auto_refs/*.pkl`; cuối cùng build refs tay (`scripts/build_team_refs.py`) |
| `team filter disabled: ...` trong log | Stage tự tắt (thiếu refs/model/video không có người) — job vẫn chạy, kết quả KHÔNG filter |
| Preview không play trên browser | Build OpenCV thiếu H.264 (`avc1`) → fallback `mp4v`. Cài `opencv-python-headless` bản chuẩn |
| Video output mất tiếng | Thiếu ffmpeg — `pip install -e .` để có `imageio-ffmpeg`, hoặc cài ffmpeg vào PATH |
| Warning "Apple MPS known Pose bug" | Vô hại trên M-series — keypoints vẫn đúng; muốn sạch log thì pose riêng chạy CPU |
| DensePose không chạy trên Mac | Dùng engine mặc định `BODYSEG_ENGINE=yolo`; DensePose cần detectron2 (build riêng, xem backend/README) |
| Job treo ở `detect` lâu | Bình thường với video dài (2fps × duration); xem `stageDetail` đếm frame |

## Kiểm thử

```bash
cd backend && pytest -q                  # 27 tests
pytest tests/test_teamid.py -q           # logic team filter (không load model)
pytest tests/test_av.py -q               # audio mux (cần ffmpeg)
pytest tests/test_bodyzones.py -q        # gán 18 kit slot
```

Smoke test full luồng bằng clip thật: xem [`TESTING_GUIDE.md`](../TESTING_GUIDE.md)
hoặc upload `team_detection/short-clips/clip_003_00-28.mp4` qua UI.

## Dữ liệu trên đĩa (backend/data/)

| Đường dẫn | Nội dung |
|---|---|
| `data/app.db` | SQLite (jobs + analyses) |
| `data/uploads/` | video gốc + preview/bodyseg đã render |
| `data/kit_anchors/{home,away}/` | anchor crops từ ảnh kit |
| `data/auto_refs/` | refs bootstrap từng video (debug) |
| `data/team_refs.pkl` | refs thủ công (override, nếu có) |

## Scaling lên production (tóm tắt — chi tiết trong Production-System-Design.MD)

Mọi infra nằm sau interface, promote bằng env:

- **DB**: `DB_URL=postgresql+psycopg://...`
- **Storage**: `STORAGE_BACKEND=s3` (+ viết `storage/s3.py`)
- **Queue**: `QUEUE_BACKEND=celery` (+ `jobs/celery_app.py`) — tách worker GPU
- Thêm auth cho API trước khi public.

## Quy ước khi sửa code

- Đổi danh sách body zone: sửa đồng bộ 3 nơi (`bodyzones.py`, `assignZoneId`,
  `ZONE_GLSL`) — xem [Exposure & EMV](05-exposure-emv.md)
- Brand mới: thêm `BRAND_DISPLAY` trong `config.py` (không bắt buộc — có fallback)
- Stage pipeline mới: cập nhật `STAGE_TO_STEP` trong
  `logo-analytics/app/processing/page.tsx` để màn processing map đúng bước
