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

> **Adapter SAM 3 đã nối** (`Sam3Labeler._run_sam3`): adapter tự dò chữ ký prompt
> của `ultralytics.SAM` (`_STRATEGIES`: prompts ảnh exemplar / visual_prompts /
> refer_image / texts / labels), nhớ lại cái chạy được rồi tái dùng. Frame không
> có logo trả list rỗng (hợp lệ). ⚠ Chưa kiểm thử với weights SAM 3 thật trong
> môi trường này — nếu bản `ultralytics` của bạn dùng chữ ký khác, bổ sung vào
> `_STRATEGIES`. `--text-backend locateanything` là **non-commercial** (chỉ
> nghiên cứu) — xem `../frontier_solutions.md` §1·B.

## Chạy

**Kiểm thử toàn bộ pipeline không cần GPU/model** (sinh box giả deterministic):
```bash
python auto_label/sam3_exemplar_autolabel.py \
    --video short-clips/clip_007_01-48.mp4 \
    --logos "Sponsor Logo" \
    --backend mock --every 20 --out data/auto_label
```

**Chạy thật với SAM 3**:
```bash
python auto_label/sam3_exemplar_autolabel.py \
    --video videos/M02_white_1440p.mp4 \
    --logos "Sponsor Logo" \
    --backend sam3 --weights sam3.pt --device mps --every 10 \
    --text-backend none \
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
| `--text-backend` | kênh OCR fingerprint: `none`/`mock`/`locateanything`/`dinox` | `none` |
| `--device` | thiết bị SAM 3: `cuda:0`/`mps`/`cpu` | tự |

## Đầu ra dùng cho gì

- `images/` + `labels/` + `data.yaml` → **train YOLO nhẹ (Tầng 1)** distill từ teacher SAM 3.
- `gallery/<brand>/` → dựng **gallery embedding / Logo Fingerprint (Tầng 2)**, thêm
  brand mới = thêm thư mục, **zero training**.
- `fingerprint.jsonl` → mỗi crop một bản ghi `visual ⊕ text(OCR) ⊕ color` cho Tầng 2.

## Đo mAP trên gold set (`eval_map.py`)

Lấy **số thật** cho paper (thay các `\TODOnum` placeholder): so nhãn auto của
teacher hoặc dự đoán của student với một **gold test set** annotate tay (chỉ để
eval, không train — xem `../paper_cyberworlds.md` §7.1).

```bash
# gold/ gồm images/ + labels/ (GT YOLO); pred/ gồm labels/ (YOLO + cột conf)
python auto_label/eval_map.py \
    --gold data/gold --pred data/auto_label \
    --names data/auto_label/data.yaml --json eval_runs/teacher.json
```

Báo cáo **mAP@0.5** + **mAP@0.5:0.95** (AP all-point kiểu VOC2010, exact 1.0 khi
pred trùng GT) + AP per-class. Cần ảnh trong `gold/images/` để IoU tính theo
pixel-space (thiếu ảnh → fallback normalized, có cảnh báo).

> ⚠ `labels/` của auto-labeler hiện **chưa ghi cột conf** → khi dùng làm `--pred`,
> mọi box coi như conf=1.0 (đủ để chấm teacher). Student/detector nên xuất YOLO
> kèm conf để PR-curve có ý nghĩa.

## Hạn chế (PoC)

- Adapter SAM 3 cần nối với bản `ultralytics` thực tế (xem `_run_sam3`).
- `brand_key_from_filename` parse tên file theo heuristic — kiểm tra lại roster in ra
  lúc chạy; chỉnh `_NOISE` nếu gom nhầm biến thể.
- Chưa có Label Model đầy đủ (mới có roster prior + lọc hình học); ensemble nhiều
  labeler (GDINO/OCR/temporal) là bước kế — xem `frontier_solutions.md` §2,§5.
