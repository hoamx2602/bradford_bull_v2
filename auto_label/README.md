# auto_label — SAM 3 Exemplar Auto-Labeling (PoC)

PoC cho **Ý tưởng #1** trong [`../frontier_solutions.md`](../frontier_solutions.md):
biến *~1 ảnh exemplar / logo* (có sẵn trong `Sponsor Logo/`) thành nhãn YOLO cho
cả video — **không annotate tay** — bằng SAM 3 Promptable Concept Segmentation.

## Pipeline

```
Sponsor Logo/*.png  ──►  Roster (brand ↔ class_id) + exemplar bank
video.mp4           ──►  lấy mẫu frame mỗi N frame
                         │
                         ▼  Sam3Labeler (exemplar prompt → segment + track)
                    RawDet[]  →  Label-Model-lite (roster prior + lọc hình học)
                         │
   data/auto_label/images/*.jpg
   data/auto_label/labels/*.txt        ← nhãn YOLO tự sinh
   data/auto_label/gallery/<brand>/    ← crop cho Tầng 2 (fingerprint/embedding)
   data/auto_label/data.yaml
```

## Cài đặt

```bash
conda activate bradford_bulls_logo      # env backend (xem memory)
pip install ultralytics opencv-python numpy   # SAM 3 qua ultralytics
```

> SAM 3 rất mới — API prompt-bằng-exemplar còn thay đổi giữa các bản `ultralytics`.
> Điểm nối model nằm ở `Sam3Labeler._run_sam3` (đánh dấu `ĐIỂM CẮM SAM 3`).

## Chạy

**Kiểm thử toàn bộ pipeline không cần GPU/model** (sinh box giả deterministic):
```bash
python auto_label/sam3_exemplar_autolabel.py \
    --video short-clips/clip_007_01-48.mp4 \
    --logos "Sponsor Logo" \
    --backend mock --every 20 --out data/auto_label
```

**Chạy thật với SAM 3** (sau khi nối adapter):
```bash
python auto_label/sam3_exemplar_autolabel.py \
    --video videos/M02_white_1440p.mp4 \
    --logos "Sponsor Logo" \
    --backend sam3 --weights sam3.pt --every 10 \
    --roster aon,mcp,klg,cch          # closed-set của riêng trận (roster prior)
```

## Tham số chính

| Cờ | Ý nghĩa | Mặc định |
|---|---|---|
| `--video` | video đầu vào | (bắt buộc) |
| `--logos` | thư mục exemplar | `Sponsor Logo` |
| `--backend` | `sam3` (thật) / `mock` (thử) | `sam3` |
| `--every` | lấy 1 frame mỗi N frame | 15 |
| `--conf` | ngưỡng confidence | 0.35 |
| `--roster` | giới hạn brand theo trận (closed-set prior) | tất cả |
| `--gallery-max` | số crop tối đa / brand | 40 |

## Đầu ra dùng cho gì

- `images/` + `labels/` + `data.yaml` → **train YOLO nhẹ (Tầng 1)** distill từ teacher SAM 3.
- `gallery/<brand>/` → dựng **gallery embedding / Logo Fingerprint (Tầng 2)**, thêm
  brand mới = thêm thư mục, **zero training**.

## Hạn chế (PoC)

- Adapter SAM 3 cần nối với bản `ultralytics` thực tế (xem `_run_sam3`).
- `brand_key_from_filename` parse tên file theo heuristic — kiểm tra lại roster in ra
  lúc chạy; chỉnh `_NOISE` nếu gom nhầm biến thể.
- Chưa có Label Model đầy đủ (mới có roster prior + lọc hình học); ensemble nhiều
  labeler (GDINO/OCR/temporal) là bước kế — xem `frontier_solutions.md` §2,§5.
