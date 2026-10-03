"""Gom các file KHÔNG nằm trong git (dữ liệu, weights, media) vào một thư mục
để upload lên Google Drive, giữ nguyên đường dẫn tương đối so với repo.

    python scripts/collect_backup.py --dry-run                 # chỉ xem dung lượng
    python scripts/collect_backup.py --dest D:/bradford_backup # copy tier "required"
    python scripts/collect_backup.py --dest D:/bradford_backup --tier recommended

Trên Mac: tải thư mục backup từ Drive về rồi copy đè vào thư mục repo
(cấu trúc thư mục đã khớp sẵn). Xem docs/14-mac-migration.md.
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

# Tier 1 — đủ để sửa slide, mở dashboard với dữ liệu đã phân tích và chạy lại demo/showcase.
REQUIRED = [
    "LogoLens_Bradford_Bulls_Findings_v5.pptx",
    ".env",                                   # secrets (HF/W&B tokens)
    "backend/.env",
    "backend/data/app.db",
    "backend/data/app.before-emv-v2.20260805T074503Z.db",
    "backend/data/team_refs.pkl",
    "backend/data/auto_refs",
    "backend/data/kit_anchors",
    "backend/data/output",
    "backend/data/uploads/*.pkl",
    "backend/data/uploads/c775d9975e3047a19eca8268a5825f3f.mp4",  # M08 — nguồn của demo/showcase
    "runs/yolo26/matchsplit_896_m/weights/best.pt",                # YOLO dùng cho video demo
    "runs/rfdetr_matchsplit_r896/checkpoint_best_ema.pth",         # MODEL TỐT NHẤT (RF-DETR Small 896)
    "runs/rfdetr_matchsplit_r896/training_config.json",            # bắt buộc đi kèm: variant/res/class names
    "yolo11m.pt", "yolo11x-pose.pt", "yolo11n-seg.pt", "backend/yolo11x-seg.pt",
    "artifacts/deck_media",
    "artifacts/bradford_review",
    "artifacts/bradford_showcase",
]

# Tier 2 — thêm nếu muốn xem/chạy lại toàn bộ các trận cũ và giữ đủ model của app.
RECOMMENDED = REQUIRED + [
    "backend/data/uploads",                           # toàn bộ video đã upload (~8.8 GB)
    "logo_detection/runs/*/weights/best.pt",          # weights YOLO mà app tự chọn
    "logo_detection/runs/rfdetr_large/weights/checkpoint_best_ema.pth",  # LOGO_BACKEND=rfdetr
    "runs/yolo26/*/weights/best.pt",
    "runs/rfdetr_matchsplit_r896/checkpoint_best_ema.pth",
    "dissertation",                                   # docx/hình/media của luận văn
    "demo_logolense.mp4", "demo_logolense_audio.mp4",
    "logolense_full.mp4", "logolense_full_v2.mp4", "logolense_remotion.mp4",
]

SKIP_PARTS = {"node_modules", ".chart-data", "__pycache__"}


def walk_files(top: Path):
    """os.walk with pruning: never descends into node_modules (a Windows
    junction there is unreadable from some tools) or other skipped dirs."""
    for dirpath, dirnames, filenames in os.walk(top):
        dirnames[:] = [d for d in dirnames if d not in SKIP_PARTS and not d.startswith(".chart-data")]
        for name in filenames:
            if name in SKIP_PARTS:
                continue
            f = Path(dirpath) / name
            try:
                if f.is_file():
                    yield f
            except OSError:
                print(f"  [bỏ qua, không đọc được] {f.relative_to(ROOT)}")


def expand(patterns):
    out = {}
    for pat in patterns:
        hits = sorted(ROOT.glob(pat)) if any(c in pat for c in "*?[") else [ROOT / pat]
        for h in hits:
            if not h.exists() and not h.is_symlink():
                print(f"  [thiếu] {pat}")
                continue
            files = [h] if h.is_file() else list(walk_files(h))
            for f in files:
                rel = f.relative_to(ROOT)
                if any(p in SKIP_PARTS or p.startswith(".chart-data") or p.endswith(":Zone.Identifier") for p in rel.parts):
                    continue
                out[rel.as_posix()] = f.stat().st_size
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--tier", choices=["required", "recommended"], default="required")
    ap.add_argument("--dest", type=Path)
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()
    files = expand(REQUIRED if a.tier == "required" else RECOMMENDED)
    total = sum(files.values())
    print(f"Tier {a.tier}: {len(files)} file, {total/1e9:.2f} GB")
    if a.dry_run or not a.dest:
        if not a.dest and not a.dry_run:
            print("Thêm --dest <thư mục> để copy.")
        return
    for i, (rel, size) in enumerate(sorted(files.items()), 1):
        dst = a.dest / rel
        if dst.exists() and dst.stat().st_size == size:
            continue  # chạy lại an toàn: bỏ qua file đã copy
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(ROOT / rel, dst)
        if i % 50 == 0:
            print(f"  {i}/{len(files)}")
    (a.dest / "BACKUP_MANIFEST.json").write_text(
        json.dumps({"tier": a.tier, "files": files, "total_bytes": total}, indent=1), encoding="utf-8")
    print(f"Xong -> {a.dest}")


if __name__ == "__main__":
    main()
