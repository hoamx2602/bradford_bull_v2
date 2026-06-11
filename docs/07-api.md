# 7. API reference

Base URL: `http://localhost:8000`. Tất cả JSON trừ upload (multipart) và
video/CSV. Không auth (thêm khi lên production — xem Production-System-Design).

## Jobs

### `POST /api/jobs` — upload video, tạo job phân tích

Multipart form:

| Field | Kiểu | Bắt buộc | Ghi chú |
|---|---|---|---|
| `video` | file | ✓ | mp4/mov/avi/mkv, ≤ `MAX_UPLOAD_MB` (2048) |
| `eventName` | str | ✓ | |
| `audienceSize` | int | ✓ | đầu vào EMV |
| `placementType` | str | | default "Live Broadcast TV" |
| `cpmBase` | float | | default 22.0 |
| `kit` | str | | `away` (default) \| `home` — cho team filter |

Response `201`: `{"jobId": "...", "status": "queued"}`
Lỗi: `413` quá size · `415` sai định dạng.

### `GET /api/jobs/{id}` — poll tiến độ

```json
{
  "id": "...", "status": "queued|processing|done|error",
  "progress": 0-100,
  "stage": "queued|frames|team|detect|exposure|pricing|preview|bodyseg|done",
  "stageDetail": "236/780 frames · 5 brands",
  "analysisId": "... (khi done)", "error": null
}
```

## Analyses

### `GET /api/analyses` — danh sách (shape khớp `MatchEntry` của frontend)

Mỗi phần tử: `{id, eventName, date, videoName, durationSeconds, logoCount,
totalEmv, result}` — `result` là AnalysisResult đầy đủ.

### `GET /api/analyses/{id}` — một kết quả đầy đủ

Các khóa chính của AnalysisResult:

```json
{
  "id": "...", "eventName": "...", "videoName": "...",
  "videoDurationSeconds": 4800.0, "analyzedAt": "ISO",
  "metadata": {"audienceSize":..., "placementType":"...", "cpmBase":..., "placementMultiplier":...},
  "logos": [{"id","name","class","segments":[{"startTime","endTime","avgVisibility","durationWeight"}],
             "totalExposureSeconds","qualityExposureSeconds","avgVisibilityScore",
             "segmentCount","longestSegmentSeconds","emvUsd"}],
  "totalEmvUsd":..., "totalQualityExposureSeconds":..., "avgVisibilityScore":...,
  "bodyZones": [{"id":"chest-center","name":"Chest Centre","percentage":16.4,"color":""}],
  "teamFilter": {"enabled":true,"kept":150,"dropped":23,"dropRate":0.133},
  "detectionTimeline": [{"name","class","color","intervals":[{"start","end"}]}],
  "previewAvailable": true, "bodysegAvailable": true,
  "bodysegGroups": {"Head": 4.2, "Torso": 38.1}
}
```

### Media & export

| Endpoint | Trả về |
|---|---|
| `GET /api/analyses/{id}/video` | MP4 preview có box detection + **audio gốc** |
| `GET /api/analyses/{id}/bodyseg-video` | MP4 overlay body-part + audio |
| `GET /api/analyses/{id}/export.csv` | CSV per-brand metrics |

## Health

`GET /api/health` → `{"status": "ok"}`

## Client frontend

`logo-analytics/lib/api.ts` đóng gói toàn bộ các call trên (`createJob`,
`getJob`, `listAnalyses`, `getAnalysis`, `videoUrl`, `bodysegVideoUrl`, `csvUrl`).
