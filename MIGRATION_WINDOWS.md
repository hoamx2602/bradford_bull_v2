# Di cư từ WSL sang Windows native

> Lý do: WSL bị giới hạn 7GB RAM trên máy 16GB → OOM killer giết training liên tục.
> Windows native thấy toàn bộ RAM + GPU CUDA trực tiếp.

## Bước 1 — Dữ liệu (đang được copy tự động)

Toàn bộ repo được rsync sang `D:\bradford_bull_v2` (loại `node_modules`,
`__pycache__`). Sau khi hoàn tất, mọi thao tác làm trên bản D:, bản WSL
giữ nguyên làm backup cho tới khi xác nhận mọi thứ chạy — rồi mới
`wsl --unregister <distro>` để lấy lại tài nguyên.

## Bước 2 — Cài môi trường Python trên Windows

1. Cài [Miniconda for Windows](https://docs.conda.io/en/latest/miniconda.html)
2. Mở **Anaconda Prompt** (hoặc PowerShell sau `conda init powershell`):

```powershell
conda create -n bradford_bulls python=3.12 -y
conda activate bradford_bulls

# PyTorch CUDA (RTX 5060 Ti = Blackwell, cần CUDA 12.8+)
pip install torch torchvision --index-url https://download.pytorch.org/whl/cu130

pip install ultralytics==8.4.86 transformers==4.57.6 opencv-python numpy pillow pyyaml
```

Phiên bản đối chiếu từ WSL (đã chạy tốt):
python 3.12.13 · torch 2.12.0+cu130 · ultralytics 8.4.86 · transformers 4.57.6
· opencv 4.13.0 · numpy 2.4.6 · pillow 12.2.0

3. Kiểm tra GPU: `python -c "import torch; print(torch.cuda.get_device_name(0))"`

⚠ `backend/` (logo-analytics-backend) pin `ultralytics==8.3.40` — cũ hơn bản cần
cho YOLO26. Nếu cần chạy backend, tạo env riêng cho nó thay vì hạ version env chính.

## Bước 3 — ffmpeg + git

```powershell
winget install Gyan.FFmpeg Git.Git
```

## Bước 4 — Claude Code trên Windows

Cài đặt bản desktop/CLI Windows, mở thư mục `D:\bradford_bull_v2`.
Bộ nhớ phiên làm việc (memory) của Claude nằm phía WSL sẽ không tự chuyển —
nói Claude đọc `docs/11-annotation-free-master-plan.md` là đủ ngữ cảnh tiếp tục.

## Bước 5 — Những khác biệt code cần biết khi chạy trên Windows

| Chỗ | WSL | Windows |
|---|---|---|
| Đường dẫn tạm | `/tmp/...` | dùng `%TEMP%` hoặc thư mục trong repo |
| Symlink (`ln -s`) | tự do | cần Developer Mode; thay bằng copy file |
| `nohup ... &` | có | dùng `Start-Process -WindowStyle Hidden` |
| `conda run -n bradford_bulls python ...` | giữ nguyên cú pháp | giữ nguyên |

Các script chính (`auto_label/stage*.py`, `logo_detection/synthetic/*.py`)
dùng `pathlib` — chạy được trên Windows không sửa. Chỉ các lệnh shell trong
tài liệu là cần đổi cú pháp.

### ⚠ Train YOLO/ultralytics trên Windows — 3 cái bẫy đã gặp (2026-07-03)

1. **`data.yaml` giữ path tuyệt đối kiểu WSL** (`/home/baonguyen/...`) → sửa thành
   path Windows (`D:/bradford_bull_v2/...`). Đồng thời **xóa `labels/*.cache`** cũ
   (train.cache/val.cache nhúng path WSL, không tự tái tạo nếu còn tồn tại).
2. **`WinError 1455 — paging file too small`** khi load `cublas64_13.dll`:
   mỗi DataLoader worker (multiprocessing 'spawn') import lại torch → nạp DLL CUDA
   → commit virtual memory bùng nổ, máy 16GB hết pagefile. **Fix: `workers=0`**
   (crop nhỏ nên không nghẽn). Muốn dùng workers>0 thì phải tăng pagefile thủ công.
3. **Không chạy train qua `conda run ... | tail`**: pipe + spawn worker gây treo
   (process sống nhưng 0% CPU, không tạo save_dir). **Cách chạy đúng**: viết script
   có `if __name__ == "__main__":` guard rồi gọi thẳng
   `C:/Users/<user>/miniconda3/envs/bradford_bulls/python.exe auto_label/run_*.py`,
   redirect log ra file (`> runs/x.log 2>&1`) để xem tiến độ streaming.
   Xem `auto_label/run_stage1b_train.py` làm mẫu.
4. **`UnicodeEncodeError: 'charmap'`** khi script `print()` tiếng Việt/ký tự lạ: stdout
   Windows mặc định cp1252. **Fix: đặt `PYTHONUTF8=1`** trước mọi lệnh python
   (`export PYTHONUTF8=1`), hoặc `PYTHONIOENCODING=utf-8`.
5. **ffmpeg/yt-dlp**: không có ffmpeg trên PATH → `pip install imageio-ffmpeg`, lấy binary
   bằng `python -c "import imageio_ffmpeg;print(imageio_ffmpeg.get_ffmpeg_exe())"` rồi
   truyền `yt-dlp --ffmpeg-location <path>` (cần cho `--download-sections` + merge).

## Bước 6 — Xác nhận rồi mới xóa WSL

```powershell
# sau khi mọi thứ chạy tốt trên Windows:
wsl --shutdown
wsl --unregister Ubuntu   # (tên distro xem bằng: wsl -l -v)
```

## Trạng thái tại thời điểm di cư (2026-07-03)

- Master plan: `docs/11-annotation-free-master-plan.md`
- Stage 0 + 1a xong (kết quả trong data/stage0, data/stage1a)
- Stage 1b: YOLO26n proposer — train trên `data/stage1b_ds` (2005 crop),
  weights tại `runs/stage1b_proposer/weights/best.pt`,
  eval bằng `auto_label/stage1b_eval.py` (xem lệnh trong docstring)
- Stage 2-6: chưa bắt đầu, thiết kế trong master plan
