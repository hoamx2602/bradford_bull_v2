# 14 — Chuyển dự án sang MacBook Pro M4 (Apple Silicon)

## 1. Cái gì nằm ở đâu

| Nơi lưu | Nội dung |
|---|---|
| **Git** (`hoamx2602/bradford_bull_v2`) | Code backend/frontend, script, docs, json/md bằng chứng của demo, markdown + script của luận văn |
| **Google Drive** | Dữ liệu, weights, video, file pptx, secrets — gom bằng `scripts/collect_backup.py` |
| **Không mang** | `.venv-app`, `.venv-rfdetr`, `node_modules`, `.next` (cài lại trên Mac) |

## 2. Backup lên Drive

```bash
python scripts/collect_backup.py --dry-run                                  # xem dung lượng
python scripts/collect_backup.py --dest D:/bradford_backup                  # tier required  (~1.5 GB)
python scripts/collect_backup.py --dest D:/bradford_backup --tier recommended  # (~12 GB)
```

Upload cả thư mục `D:/bradford_backup` lên Drive. Script giữ nguyên đường dẫn tương đối, chạy lại an toàn (bỏ qua file đã copy).

**required (~1.5 GB)** — đủ để sửa slide, mở dashboard với các phân tích đã lưu, chạy lại demo/showcase:
- `LogoLens_Bradford_Bulls_Findings_v5.pptx`
- `.env`, `backend/.env` (token HF / W&B — bí mật, đừng chia sẻ thư mục Drive này)
- `backend/data/` trừ video: `app.db` (+ bản backup), `team_refs.pkl`, `auto_refs/`, `kit_anchors/`, `output/`, `uploads/*.pkl`
- `backend/data/uploads/c775d9975e3047a19eca8268a5825f3f.mp4` — trận M08, nguồn của demo/showcase
- `runs/yolo26/matchsplit_896_m/weights/best.pt` — model dùng trong deck
- `yolo11m.pt`, `yolo11x-pose.pt`, `yolo11n-seg.pt`, `backend/yolo11x-seg.pt`
- `artifacts/deck_media`, `artifacts/bradford_review`, `artifacts/bradford_showcase` (ảnh/video của deck)

**recommended (~12 GB)** — thêm: toàn bộ `backend/data/uploads` (~8.8 GB video các trận), weights trong `logo_detection/runs/*/weights/best.pt` + `rfdetr_large`, các checkpoint `runs/yolo26/*`, `runs/rfdetr_matchsplit_r896` (ema), file docx/hình của `dissertation/`, các video demo ở thư mục gốc, deck v1–v4.

**Không cần nếu không train lại:** `datasets/` (5.8 GB), `training-result/` (3.2 GB), `logo_detection/data`, phần còn lại của `runs/` (checkpoint regular/total, rfdetr_small…), `logo_detection/meshes`.

## 3. Cài trên Mac

```bash
git clone git@github.com:hoamx2602/bradford_bull_v2.git && cd bradford_bull_v2
git checkout feat/full-match-report
# copy nội dung thư mục backup từ Drive đè vào repo (cấu trúc đã khớp)

python3.11 -m venv .venv && source .venv/bin/activate
pip install -e "./backend[dev,team]" python-pptx
# tuỳ chọn RF-DETR (chỉ chạy CPU trên Mac): pip install -e "./backend[rfdetr]"
cd logo-analytics && npm install && cd ..
```

## 4. Toggle thiết bị tính toán (CUDA ↔ Apple ↔ CPU)

Không có chỗ nào phải sửa code khi đổi máy — dùng biến môi trường `DEVICE`:

| `DEVICE` | Ý nghĩa |
|---|---|
| `auto` (mặc định) | CUDA nếu có → Apple MPS → CPU |
| `cuda` / `gpu` / `0` | GPU NVIDIA đầu tiên |
| `mps` | GPU Apple Silicon |
| `cpu` | CPU |

Áp dụng cho backend (`app/config.py` → `registry.resolve_device`) và các script demo (`build_club_demo.py`, `scan_showcase.py`, `render_showcase.py`, `refresh_team_demo.py`…). Ví dụ:

```bash
DEVICE=mps python backend/scripts/render_showcase.py     # Mac
DEVICE=cuda python backend/scripts/render_showcase.py    # máy Windows CUDA (giống hành vi cũ)
```

## 5. Lưu ý riêng cho Mac

- **`backend/.env` đang đặt `LOGO_BACKEND=rfdetr`.** RF-DETR không có đường MPS → chạy CPU, rất chậm. Trên Mac nên đặt `LOGO_BACKEND=yolo` (và `DETECTOR_BACKEND=yolo`).
- **Ghim model:** app tự chọn `best.pt` *mới nhất theo ngày sửa* trong `logo_detection/runs/*`. Copy qua Drive có thể làm đổi ngày → đổi model. Đặt rõ:
  `MODEL_PATH=runs/yolo26/matchsplit_896_m/weights/best.pt` (đường dẫn tuyệt đối trên Mac).
- `scripts/merge_home_away.py`, `scripts/resplit_data.py`: đặt `LOGO_DATA_DIR` nếu dữ liệu train không nằm ở `logo_detection/data`.
- Train lại model: nên dùng máy CUDA hoặc Colab; MPS train được nhưng chậm.
- DensePose/detectron2 khó build trên Mac — pipeline đã dùng `bodyseg_yolo` thay thế.
