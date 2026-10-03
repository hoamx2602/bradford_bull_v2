# 14 — Chuyển dự án sang MacBook Pro M4 (Apple Silicon)

## 1. Cái gì nằm ở đâu

| Nơi lưu | Nội dung |
|---|---|
| **Git** (`hoamx2602/bradford_bull_v2`) | Code backend/frontend, script, docs, **các file presentation** (`LogoLens_Bradford_Bulls_Findings*.pptx` v1–v5, `artifacts/bradford_review/presentation/Bradford_Bulls_Findings_Final.pptx`, `dissertation/LogoLens_WP1_Summary.pptx`), json/md bằng chứng của demo, markdown + script của luận văn |
| **Google Drive** | Dữ liệu, weights, video, secrets — gom bằng `scripts/collect_backup.py` |
| **Không mang** | `.venv-app`, `.venv-rfdetr`, `node_modules`, `.next` (cài lại trên Mac) |

## 2. Backup lên Drive

```bash
python scripts/collect_backup.py --dry-run                                  # xem dung lượng
python scripts/collect_backup.py --dest D:/bradford_backup                  # tier required  (~1.5 GB)
python scripts/collect_backup.py --dest D:/bradford_backup --tier recommended  # (~12 GB)
```

Upload cả thư mục `D:/bradford_backup` lên Drive. Script giữ nguyên đường dẫn tương đối, chạy lại an toàn (bỏ qua file đã copy).

**required (~1.5 GB)** — đủ để sửa slide, mở dashboard với các phân tích đã lưu, chạy lại demo/showcase:
- `LogoLens_Bradford_Bulls_Findings_v5.pptx` (đã có trong git — giữ trong backup cho chắc)
- `.env`, `backend/.env` (token HF / W&B — bí mật, đừng chia sẻ thư mục Drive này)
- `backend/data/` trừ video: `app.db` (+ bản backup), `team_refs.pkl`, `auto_refs/`, `kit_anchors/`, `output/`, `uploads/*.pkl`
- `backend/data/uploads/c775d9975e3047a19eca8268a5825f3f.mp4` — trận M08, nguồn của demo/showcase
- `runs/rfdetr_matchsplit_r896/checkpoint_best_ema.pth` + `training_config.json` — **model tốt nhất** (RF-DETR Small 896, slide 13)
- `runs/yolo26/matchsplit_896_m/weights/best.pt` — YOLO dùng để render các video demo trong deck
- `yolo11m.pt`, `yolo11x-pose.pt`, `yolo11n-seg.pt`, `backend/yolo11x-seg.pt`
- `artifacts/deck_media`, `artifacts/bradford_review`, `artifacts/bradford_showcase` (ảnh/video của deck)

**recommended (~12 GB)** — thêm: toàn bộ `backend/data/uploads` (~8.8 GB video các trận), weights trong `logo_detection/runs/*/weights/best.pt` + `rfdetr_large`, các checkpoint `runs/yolo26/*`, `runs/rfdetr_matchsplit_r896` (ema), file docx/hình của `dissertation/`, các video demo ở thư mục gốc.

**Không cần nếu không train lại:** `datasets/` (5.8 GB), `training-result/` (3.2 GB), `logo_detection/data`, phần còn lại của `runs/` (checkpoint regular/total, rfdetr_small…), `logo_detection/meshes`.

## 3. Cài trên Mac

```bash
git clone git@github.com:hoamx2602/bradford_bull_v2.git && cd bradford_bull_v2
git checkout feat/full-match-report
# copy nội dung thư mục backup từ Drive đè vào repo (cấu trúc đã khớp)

python3.11 -m venv .venv && source .venv/bin/activate
pip install -e "./backend[dev,team,rfdetr]" python-pptx
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

## 5. Model tốt nhất trên Mac

Model tốt nhất là **RF-DETR Small 896** — `runs/rfdetr_matchsplit_r896/checkpoint_best_ema.pth`
(mAP@0.50 = 0.933 trên 3 trận chưa thấy, slide 13). `rfdetr` ≥ 1.9 chạy được trên Apple MPS,
nên Mac dùng **đúng model này**, không phải lùi về YOLO.

`backend/.env` (giống nhau trên Windows và Mac — chỉ khác máy tự chọn GPU):

```ini
DEVICE=auto                      # Windows -> CUDA, Mac -> MPS
LOGO_BACKEND=rfdetr
RFDETR_MODEL_PATH=runs/rfdetr_matchsplit_r896/checkpoint_best_ema.pth
RFDETR_VARIANT=auto              # đọc 'small' từ training_config.json
RFDETR_RESOLUTION=0              # = 896 từ training_config.json
RFDETR_CLASS_NAMES_SOURCE=auto   # tên nhãn hiệu từ training_config.json
```

Vì sao phải ghim như trên (đã kiểm chứng bằng cách chạy model thật):
- Không ghim đường dẫn -> app tự chọn `logo_detection/runs/rfdetr_large` (bản tháng 6), không phải model tốt nhất.
- Chạy ở resolution mặc định 512 thay vì 896 -> bỏ sót logo (frame 272/284 mất 1–2 nhãn hiệu).
- Thứ tự class của model này khác danh sách cũ trong `config.py` -> nếu dùng `RFDETR_CLASS_NAMES_SOURCE=config`
  thì MCP bị gắn tên "floor_tonic", Paints & Lacquers thành "mna_support_service", Aon thành "acs_group".
- `training_config.json` **phải nằm cạnh checkpoint**.

Kiểm tra sau khi khởi động backend: log phải có
`loading RF-DETR logo model (small, res=896, device=mps)` và `RF-DETR class names from …training_config.json`.

## 6. Lưu ý khác cho Mac

- `BODYSEG_ENGINE=densepose` không chạy được trên MPS (CPU-only, phải build detectron2). Trên Mac đặt
  `BODYSEG_ENGINE=yolo` — đây cũng là engine đã dùng cho các video demo trong deck.
- `scripts/merge_home_away.py`, `scripts/resplit_data.py`: đặt `LOGO_DATA_DIR` nếu dữ liệu train không nằm ở `logo_detection/data`.
- Train lại model: nên dùng máy CUDA hoặc Colab; MPS train được nhưng chậm.
- Muốn nhanh hơn nữa: rfdetr có thể export sang CoreML (`model.export(format="coreml")`) — chưa tích hợp vào pipeline.
