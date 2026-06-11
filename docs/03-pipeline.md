# 3. Pipeline xử lý

Một upload = một **job**. Orchestrator (`backend/app/pipeline/orchestrator.py`)
chạy tuần tự các stage, cập nhật `stage`/`progress` để màn processing hiển thị
realtime. Mọi stage tùy chọn đều **degrade gracefully** — lỗi chỉ log warning,
job vẫn hoàn thành.

## Các stage

```
 stage      progress   việc làm
─────────────────────────────────────────────────────────────────────
 frames        5%      ffprobe metadata (duration/fps/size)
 team          8%      [nếu chưa có refs] bootstrap kit references
                       từ chính video — xem docs/04-team-filter.md
 detect     10→80%     vòng lặp frame chính (sample SAMPLE_FPS=2/s):
                         1. YOLO26 logo detect (imgsz 1280)
                         2. visibility score từng detection
                         3. team filter: track person (BoT-SORT) →
                            classify áo → vote → DROP logo không thuộc
                            cầu thủ Bradford
                         4. YOLO11-pose → gán logo vào 18 kit slot
 exposure      92%     gộp detections → segments per brand (Tier 2)
 pricing       98%     EMV per brand (Tier 3)
 preview       98%     annotated video full-fps (box + nhãn), capped
                       PREVIEW_MAX_FRAMES; mux AUDIO GỐC vào output
 bodyseg       98%     overlay video body-part (YOLO-seg hoặc DensePose),
                       cũng mux audio
 done         100%     persist Analysis vào DB + storage
```

## Hai pass detection — vì sao

| Pass | Mục đích | Tần suất |
|---|---|---|
| **Analytics** (sampled) | EMV/exposure — rẻ, đủ chính xác về thời lượng | `SAMPLE_FPS` (2 fps) |
| **Preview** (full-fps) | Video mượt để xem lại, box dính sát logo | mọi frame, cap `PREVIEW_MAX_FRAMES` |

Timeline per-brand trên player lấy từ pass preview để khớp box từng frame.

> Lưu ý: pass preview hiện **không** chạy team filter — box hiển thị mọi logo
> detect được. Con số EMV/exposure thì luôn đã filter.

## Dữ liệu đầu ra (Analysis)

Một bản ghi JSON đầy đủ (xem `aggregate.build_analysis_result`):

- `logos[]` — per brand: segments, exposure giây, quality exposure, avg
  visibility, EMV
- `bodyZones[]` — 18 kit slot với % exposure (xem [Exposure & EMV](05-exposure-emv.md))
- `teamFilter` — `{enabled, kept, dropped, dropRate}`
- `detectionTimeline[]` — interval on-screen per brand (drive player timeline)
- `previewAvailable` / `bodysegAvailable` / `bodysegGroups`

## File liên quan

| Stage | File |
|---|---|
| Orchestrator | `app/pipeline/orchestrator.py` |
| Frame sampling | `app/pipeline/frames.py`, `ingest.py` |
| Logo detect | `app/pipeline/detect_track.py` |
| Visibility | `app/pipeline/visibility.py` |
| Team filter | `app/pipeline/teamid/` |
| Body zones | `app/pipeline/pose.py`, `bodyzones.py` |
| Exposure/EMV | `app/pipeline/exposure.py`, `pricing.py` |
| Preview + audio | `app/pipeline/annotate.py`, `av.py` |
| Bodyseg overlay | `app/pipeline/bodyseg_yolo.py`, `bodyseg.py` |
