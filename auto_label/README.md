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
| `--obb` | xuất OBB (oriented) từ mask SAM 3 thay vì HBB — **Phase 1** | off |
| `--class-agnostic` | gộp mọi brand về 1 lớp `logo` (Tầng 1 localizer) | off |

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

## Phase 1 — SAM 3 → YOLOv11-OBB localizer (Tầng 1)

Distill teacher SAM 3 thành student YOLOv11-OBB nhẹ, **1 lớp `logo`** (class-agnostic
→ tổng quát club/môn; định danh brand để Tầng 2 lo). OBB lấy từ **mask SAM 3**
(`cv2.minAreaRect`) nên sát viền logo nghiêng/cong → visibility% chính xác.

```bash
# 1) auto-label OBB class-agnostic từ video thật (teacher SAM 3)
python auto_label/sam3_exemplar_autolabel.py --video V.mp4 --logos "Sponsor Logo" \
    --backend sam3 --weights sam3.pt --device cuda:0 --obb --class-agnostic \
    --out data/auto_label          # vẫn xuất gallery/ + fingerprint cho Tầng 2

# 2) train student (yolo11{n,s,m}-obb.pt; logo nhỏ → imgsz lớn)
python auto_label/train_localizer.py train --data data/auto_label/data.yaml \
    --model yolo11s-obb.pt --epochs 100 --imgsz 1280 --device 0

# 3) chấm trên gold set → mAP OBB
python auto_label/train_localizer.py predict --weights runs/obb/train/weights/best.pt \
    --images data/gold/images --out data/pred --imgsz 1280 --conf 0.25 --device 0
python auto_label/eval_obb.py --gold data/gold --pred data/pred
```

> ✅ Đã smoke-test end-to-end trên GPU (mock teacher → train 2 epoch YOLOv11n-OBB →
> predict → eval_obb): mọi mắt xích nối đúng, nhãn OBB chảy tới eval. Chạy thật cần
> SAM 3 weights + video + gold set. `data.yaml` ghi `path:` **tuyệt đối** (Ultralytics
> phân giải path tương đối theo datasets_dir, không theo vị trí file).
>
> Smoke không cần GPU/weights: `train_localizer.py selftest-predict --out /tmp/p`.
>
> **Cổng Phase 1:** OBB mAP@0.5 trên gold ≥ baseline YOLO26 (xem
> `../expert_review_and_plan.md` Phần 2/3).

## Phase 2 — Tầng 2 Recognizer (DINO embedding + retrieval)

`recognizer.py`: crop logo → embedding (DINOv2/DINOv3/SigLIP2 qua `transformers`) →
cosine với Template DB → brand gần nhất; score < τ → `unknown`. **Thêm brand =
thêm vector, KHÔNG train lại.** Store mặc định numpy brute-force (đủ hàng nghìn
template); đổi `--model` sang DINOv3/SigLIP2 khi có quyền.

Cải tiến open-set: **#1 mask nền** (`--mask`, crop sát + xoá nền theo alpha/mask
SAM 3) + **#2 fingerprint** fuse visual ⊕ color (`--w-color`) ⊕ OCR text
(`--w-text`, cần `--text-backend easyocr|tesseract`).

```bash
python auto_label/recognizer.py build --logos "Sponsor Logo" \
    --gallery data/auto_label/gallery --out data/templates.npz --device cuda
python auto_label/recognizer.py query --db data/templates.npz \
    --crops data/gold/recognition/crops --out pred.jsonl \
    --mask --w-color 0.3 --device cuda          # bật mask + color fusion
python auto_label/eval_recognition.py --pred pred.jsonl --tau 0.6
# chọn ngưỡng vận hành τ trên validation (cần cả known + unknown):
python auto_label/eval_recognition.py --pred pred.jsonl --calibrate --target-known-acc 0.95
python auto_label/recognizer.py selftest        # logic + fusion, không cần model
```

Open-set scoring: `--score cosine` (mặc định) hoặc `--score margin` (top1−top2).
⚠ margin **không mặc định tốt**: demo có brand gần-trùng → margin tụt AUROC 0.86→0.47.
`--calibrate` đổi AUROC thành điểm vận hành: vd cosine AUROC 0.86 → τ*=0.78 giữ
known-acc 0.91 & reject 40% unknown (số demo, chỉ minh hoạ — τ thật cần validation thật).

> ✅ Đã chạy thật `facebook/dinov2-base` (16 brand, 85 crop demo) — tiến trình vá open-set:
>
> | cấu hình | top-1 | open-set AUROC |
> |---|---|---|
> | raw (no mask) | 0.93 | 0.68 |
> | **+ mask nền (#1)** | **0.99** | 0.69 |
> | + mask + color 0.3 (#2) | 0.92 | **0.86** |
> | + mask + color 0.8 | 0.92 | 0.93 |
>
> **#1 mask** kéo closed-set top-1 lên 0.99 (bỏ nhiễu nền khỏi CLS). **#2 color**
> tăng AUROC mạnh. **Caveat trung thực:** phân bố điểm vẫn chồng (unknown 0.77–0.86
> nằm trong dải known) → **một τ cố định chưa reject sạch**; τ phải **calibrate trên
> validation split**, và **kênh OCR text** mới là tín hiệu reject robust (token khớp
> ≈1/0, không phụ thuộc thang visual) — đã wire sẵn (`pip install easyocr`).
>
> **Đã thử OCR thật:** AUROC visual 0.69 → +color0.3 0.86 → **+color0.3+text0.5 0.89
> (best)**; nhưng OCR **modest, không silver bullet** — đọc tốt logo nhiều chữ, fail
> logo cách điệu (AON=''); over-weight text (1.0) làm top-1 sập 0.65; vẫn chưa tách
> sạch unknown. Mọi số synthetic. Xem `docs/worklog.md` + `../expert_review_and_plan.md`.

## End-to-end glue — video → exposure (1 lệnh)

`run_pipeline.py`: video → sample frame → Tầng1 (YOLOv11-OBB) → crop+mask(OBB) →
Tầng2 (recognizer: brand+score, +clarity Laplacian, +area_pct) → `dets.jsonl` →
`aggregate` → `result.json`. `score<τ → unknown` (mặc định bỏ).

```bash
python auto_label/run_pipeline.py --video V.mp4 \
    --weights runs/obb/train/weights/best.pt --db data/templates.npz \
    --out-dir data/run1 --every 10 --device cuda \
    --mask --w-color 0.3 --tau 0.55 [--gold gold.json]
```

> ✅ Smoke thật GPU (localizer Phase1 + DB Phase2 + video AON): **14/14 frame localize,
> conf ~0.98** → aggregate ra exposure. ⚠ Recognizer **gán nhầm AON→mna_cladding**
> (rec_score ~0.39, logo cách điệu + DB chỉ có logo PNG sạch); τ=0.55 → reject hết
> (0 false-attribution nhưng miss AON). **Fix: build DB kèm `--gallery` (crop render
> thật) hoặc fine-tune.** Localizer khỏe; bottleneck là Tầng 2 + dữ liệu thật.

## Phase 3 — Aggregation engine (detections → metric sản phẩm)

`aggregate.py`: detection per-frame (Tầng1+Tầng2) → exposure-seconds, visibility%,
EMV, segments. Xử lý edge case (data-independent, test được ngay): temporal
smoothing (bắc cầu flicker), drop ghost (`--min-seg`), lọc conf, loại scene
(`--exclude-scenes replay,adbreak`), coverage cộng+clamp, clarity-weighting.
Output **khớp `eval_exposure.py`**.

```bash
python auto_label/aggregate.py --dets dets.jsonl --fps 25 --sample-fps 2.5 \
    --bridge 0.8 --min-seg 0.5 --conf 0.3 --exclude-scenes replay --out result.json
python auto_label/eval_exposure.py --pred result.json --gt gold.json
python auto_label/aggregate.py --selftest      # không cần model/GPU
```

> ✅ Demo `data/demo_phase3/`: aon 8.4s, bartercard 4.4s (flicker bắc cầu + ghost bỏ),
> replay/low-conf loại → eval_exposure MAE 1.2s, temporal IoU 0.94.
> **Chưa xử lý** (cần detector riêng): LED board cycling, graphic-overlay occlusion;
> scene-exclude cần nhãn scene upstream; EMV là placeholder; tracking presence-based
> (ByteTrack box-level là refinement cho re-id sau camera-cut).

## Bộ eval Phase 0 — thước đo trước khi xây (xem `../expert_review_and_plan.md`)

Ngoài `eval_map.py` (HBB mAP), Phase 0 bổ sung 4 module **self-contained** (numpy,
+ opencv cho OBB ảnh). Mỗi module có `--selftest` (không cần dữ liệu/model/GPU):

| Module | Đo gì | Lệnh |
|---|---|---|
| `eval_obb.py` | **OBB mAP** (polygon IoU) — vì visibility% feed EMV, HBB thổi phồng | `eval_obb.py --gold data/gold --pred data/auto_label` |
| `eval_recognition.py` | Tầng 2: top-1 acc, **open-set AUROC**, unknown-rejection, confusion | `eval_recognition.py --pred crops.jsonl --tau 0.6` |
| `eval_exposure.py` | End-to-end: **exposure-sec MAE/MAPE**, visibility% MAE, temporal IoU | `eval_exposure.py --pred pred.json --gt gt.json` |
| `gold_set.py` | Dựng/kiểm/thống kê **gold set** + stratify theo tag | `gold_set.py scaffold\|validate\|stats --gold data/gold` |

```bash
# 0) dựng khung gold set + đọc quy ước annotate
python auto_label/gold_set.py scaffold --gold data/gold
# 1) sau khi bỏ ảnh + nhãn tay + điền manifest.csv:
python auto_label/gold_set.py validate --gold data/gold --names data/auto_label/data.yaml
python auto_label/gold_set.py stats    --gold data/gold      # xem stratum nào chưa phủ
# 2) chấm teacher/student
python auto_label/eval_obb.py --gold data/gold --pred data/auto_label --json eval_runs/obb.json
```

Test: `pytest auto_label/tests/test_eval.py -q` (16 test, gồm IoU OBB xoay 45°,
AUROC, MAE, validate gold). `eval_obb` đọc được cả nhãn HBB (4 toạ độ) lẫn OBB (8
toạ độ) nên dùng chung gold set với `eval_map.py`.

## Hạn chế (PoC)

- Adapter SAM 3 cần nối với bản `ultralytics` thực tế (xem `_run_sam3`).
- `brand_key_from_filename` parse tên file theo heuristic — kiểm tra lại roster in ra
  lúc chạy; chỉnh `_NOISE` nếu gom nhầm biến thể.
- Chưa có Label Model đầy đủ (mới có roster prior + lọc hình học); ensemble nhiều
  labeler (GDINO/OCR/temporal) là bước kế — xem `frontier_solutions.md` §2,§5.
