# 2. Cài đặt & chạy

Hai môi trường đã được test: **macOS Apple Silicon (M4, MPS)** và
**Windows + NVIDIA RTX (CUDA 12.8)**. Code chung — chỉ khác `.env`.

## Yêu cầu chung

- Python 3.11+ (khuyến nghị conda env — trên Mac đang dùng env `bradford_bulls_logo`)
- Node 18+ (frontend)
- Weights logo model tại `logo_detection/runs/*/weights/best.pt`

> ⚠️ **ultralytics phải đúng 8.3.40** — bản 8.4.x load `best.pt` này
> không detect được gì. Đã pin trong `backend/pyproject.toml`, đừng nâng cấp tay.

## Windows + NVIDIA (RTX 4500 Ada, CUDA 12.8)

```bat
:: 1. PyTorch CUDA 12.8
pip install torch torchvision --index-url https://download.pytorch.org/whl/cu128

:: 2. Backend + team-filter extras
cd backend
pip install -e . -e ".[team]"

:: 3. Kiểm tra GPU
python -c "import torch; print(torch.cuda.get_device_name(0))"
```

`.env` (tạo file `backend/.env`):

```ini
DEVICE=0
TEAM_FILTER_ENABLED=true
TEAM_PERSON_MODEL=yolo11m.pt
TEAM_PERSON_IMGSZ=960
```

## macOS Apple Silicon (M-series)

```bash
cd backend
pip install -e . -e ".[team]"
```

`.env` — preset nhẹ cho M4:

```ini
DEVICE=auto                 # tự resolve sang mps
TEAM_FILTER_ENABLED=true
TEAM_PERSON_MODEL=yolo11n.pt
TEAM_PERSON_IMGSZ=640
TEAM_SIGLIP_EVERY=8
TEAM_BOOTSTRAP_FRAMES=24
```

Ghi chú MPS: SigLIP chạy fp32 (fp16 chỉ bật trên CUDA); ultralytics sẽ in
cảnh báo "MPS known Pose bug" — vô hại, body zones vẫn ra đúng.

## Sinh kit anchors (một lần, cả 2 nền tảng)

```bash
python scripts/make_kit_anchors.py
```

Cắt áo từ `KIT/Home Kit.jpg` + `KIT/Away Kit.jpg` → `data/kit_anchors/{home,away}/`.
Bước team-identify sẽ chọn đúng cluster Bradford theo ảnh kit thật.
Chỉ chạy lại khi đổi thiết kế kit.

## Chạy backend

```bash
cd backend
uvicorn app.main:create_app --factory --reload --port 8000
```

## Chạy frontend

```bash
cd logo-analytics
npm install
npm run dev          # http://localhost:3000
```

Frontend trỏ backend qua `NEXT_PUBLIC_API_URL` (mặc định `http://localhost:8000`).
Không có backend → dashboard tự fallback mock data để demo UI.

## Âm thanh video output

Preview/bodyseg video giữ audio gốc nhờ ffmpeg — tự tìm trong PATH, nếu không
có thì dùng binary bundled trong package `imageio-ffmpeg` (đã nằm trong deps).
Không cần cài gì thêm trên Windows.

## Kiểm tra cài đặt

```bash
cd backend && pytest -q        # 27 tests: unit + HTTP smoke (load model thật)
```
