# 1. Tổng quan hệ thống

## Bài toán

Bradford Bulls bán vị trí quảng cáo (sponsor slot) trên kit thi đấu. Câu hỏi
khách hàng cần trả lời: **logo của tôi xuất hiện bao nhiêu, rõ đến mức nào,
và đáng giá bao nhiêu tiền media?**

Hệ thống nhận video broadcast → tự động:

1. **Phát hiện logo** trên áo cầu thủ (YOLO26 fine-tuned, 16 sponsor classes)
2. **Chỉ đếm logo trên cầu thủ Bradford** — loại logo trùng trên áo đối thủ,
   trọng tài, biển LED (xem [Team filter](04-team-filter.md))
3. **Chấm điểm visibility** từng lần xuất hiện (kích thước, vị trí, độ tin cậy)
4. **Quy ra EMV** (USD) theo công thức ngành (xem [Exposure & EMV](05-exposure-emv.md))
5. **Gán logo vào vị trí trên cơ thể** (18 kit slot: ngực giữa, lưng trên, shorts sau...)
   → làm cơ sở pricing model theo vị trí đặt logo

## Kiến trúc

```
┌──────────────┐   upload    ┌─────────────────────────────┐
│  Frontend    │ ──────────► │  Backend (FastAPI)          │
│  Next.js     │   poll job  │  - Job queue (in-process)   │
│  :3000       │ ◄────────── │  - Pipeline orchestrator    │
└──────────────┘   results   │  - SQLite (→Postgres later) │
                             │  - Local storage (→S3 later)│
                             └──────────┬──────────────────┘
                                        │
                     ┌──────────────────┼──────────────────┐
                     ▼                  ▼                  ▼
              YOLO26 logo        YOLO11 person       YOLO11-pose
              (fine-tuned)       + BoT-SORT          (body zones)
                                 + SigLIP team       YOLO11-seg /
                                 classifier          DensePose (overlay)
```

- **Backend**: `backend/` — FastAPI + pipeline. Mọi infra (DB/storage/queue) nằm
  sau interface, đổi production stack chỉ bằng env var.
- **Frontend**: `logo-analytics/` — Next.js dashboard 5 tab, chart SVG tự viết
  (không dependency chart lib).
- **Model logo**: `logo_detection/runs/*/weights/best.pt` — tự pick bản mới nhất.

## Cấu trúc repo (các thư mục chính)

| Thư mục | Vai trò |
|---|---|
| `backend/` | API + pipeline xử lý (production code) |
| `logo-analytics/` | Frontend dashboard Next.js |
| `logo_detection/` | Training model logo (dataset, runs, weights) |
| `team_detection/` | Prototype nghiên cứu team classification (đã port vào `backend/app/pipeline/teamid/`) |
| `KIT/` | Ảnh kit chính thức Home/Away — nguồn sinh kit anchors |
| `docs/` | Tài liệu này |
| `videos/`, `short-clips/` | Video test |

## Luồng người dùng

1. Mở dashboard → **New Analysis** → upload video, nhập event/audience/CPM,
   chọn **kit** (Away đen / Home trắng)
2. Màn processing hiển thị 5 bước realtime (frame → team → detect → exposure → EMV)
3. Tự chuyển về **Match Videos** xem kết quả: video preview có box + audio,
   timeline per-brand, bảng brand breakdown
4. Các tab **Overview / Brand Insights / Analytics Report** tổng hợp đa trận,
   filter, export PDF/CSV
