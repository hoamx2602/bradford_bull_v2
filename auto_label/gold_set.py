"""Dựng & kiểm tra GOLD SET — thước đo của toàn dự án (Phase 0).

Gold set = tập nhỏ frame thật gán tay MỘT LẦN, CHỈ để eval (không train). Mọi
phase sau phải vượt cổng trên gold set mới đi tiếp. Stratify theo điều kiện để
biết model yếu ở đâu (blur/occlusion/replay/...), không chỉ một con số trung bình.

Lệnh con:
  scaffold  — tạo cây thư mục + manifest mẫu + README
  validate  — kiểm nhãn (HBB/OBB) hợp lệ, toạ độ ∈ [0,1], ảnh tồn tại, class hợp lệ
  stats     — thống kê phân tầng theo tag trong manifest + phân bố box/class

Bố cục:
    gold/
      images/<stem>.jpg
      labels/<stem>.txt          # HBB "cls cx cy w h" hoặc OBB "cls x1..y4"
      manifest.csv               # stem,tags   (tags: ';'-phân tách)
      recognition/crops.jsonl    # (tùy chọn) cho eval_recognition.py
      exposure/<video>.gt.json   # (tùy chọn) cho eval_exposure.py
      README.md

Chạy:
    python auto_label/gold_set.py scaffold --gold data/gold
    python auto_label/gold_set.py validate --gold data/gold --names data/auto_label/data.yaml
    python auto_label/gold_set.py stats    --gold data/gold
"""
from __future__ import annotations

import argparse
import csv
from collections import Counter
from pathlib import Path

# Các stratum khuyến nghị — phủ đúng các ca khó nêu trong Motion-blur.MD /
# Production-System-Design.MD (edge cases production-grade).
RECOMMENDED_TAGS = [
    "sharp", "motion_blur", "occlusion", "replay", "wide_shot",
    "close_up", "low_light", "led_board", "two_teams_same_sponsor",
]

README = """# Gold set — thước đo eval (KHÔNG dùng để train)

~300–500 frame thật gán tay, phủ đa dạng điều kiện. Chỉ để chấm Tầng 1 / Tầng 2 /
hệ end-to-end. Xem `../../expert_review_and_plan.md` Phần 3.

## Cấu trúc
- `images/<stem>.jpg`        — frame
- `labels/<stem>.txt`        — GT box: HBB `cls cx cy w h` hoặc OBB `cls x1 y1 ... x4 y4`
                               (normalized [0,1]). Tầng 1 class-agnostic → cls=0 (`logo`).
- `manifest.csv`             — `stem,tags`; tags phân tách bằng `;`
- `recognition/crops.jsonl`  — (tùy chọn) `{"id","gt","pred","score"}` cho Tầng 2
- `exposure/<video>.gt.json` — (tùy chọn) ground-truth exposure cho cả trận

## Tags khuyến nghị (stratify)
""" + "\n".join(f"- `{t}`" for t in RECOMMENDED_TAGS) + """

## Quy ước annotate
- Annotate MỌI logo nhìn thấy đủ để mắt người nhận ra (cả mờ) → đo recall thật.
- Logo bị che một phần: vẽ phần nhìn thấy; gắn tag `occlusion`.
- Dùng OBB nếu logo nghiêng/cong (khuyến nghị, vì visibility% feed EMV).
"""


def load_names(names_path: Path | None) -> dict[int, str]:
    if not names_path or not names_path.is_file():
        return {}
    out: dict[int, str] = {}
    in_names = False
    for line in names_path.read_text().splitlines():
        s = line.strip()
        if s.startswith("names:"):
            in_names = True; continue
        if in_names and ":" in s:
            k, v = s.split(":", 1)
            try:
                out[int(k.strip())] = v.strip()
            except ValueError:
                in_names = False
    return out


def scaffold(gold: Path) -> None:
    for sub in ("images", "labels", "recognition", "exposure"):
        (gold / sub).mkdir(parents=True, exist_ok=True)
    man = gold / "manifest.csv"
    if not man.exists():
        with man.open("w", newline="") as f:
            w = csv.writer(f)
            w.writerow(["stem", "tags"])
            w.writerow(["example_0001", "sharp;close_up"])
            w.writerow(["example_0002", "motion_blur;wide_shot"])
    (gold / "README.md").write_text(README)
    print(f"  scaffold xong tại {gold}")
    print(f"  → bỏ ảnh vào {gold/'images'}, nhãn vào {gold/'labels'}, "
          f"điền {man}")


def _parse_label_line(parts: list[str]) -> tuple[int, list[float], str | None]:
    """Trả (cls, coords, err). err=None nếu hợp lệ."""
    if len(parts) < 5:
        return -1, [], "ít hơn 5 token"
    try:
        cls = int(float(parts[0]))
        coords = [float(v) for v in parts[1:]]
    except ValueError:
        return -1, [], "token không phải số"
    ncoord = len(coords)
    if ncoord not in (4, 8):  # HBB 4, OBB 8 (bỏ qua conf nếu lỡ có ở GT)
        if ncoord in (5, 9):
            coords = coords[:ncoord - 1]  # cho phép GT lỡ kèm conf
        else:
            return cls, coords, f"số toạ độ lạ: {ncoord} (cần 4 hoặc 8)"
    if any(c < -0.01 or c > 1.01 for c in coords):
        return cls, coords, "toạ độ ngoài [0,1] (chưa normalize?)"
    return cls, coords, None


def validate(gold: Path, names: dict[int, str]) -> int:
    lab_dir, img_dir = gold / "labels", gold / "images"
    if not lab_dir.is_dir():
        raise SystemExit(f"Không thấy {lab_dir} — chạy 'scaffold' trước")
    label_files = sorted(lab_dir.glob("*.txt"))
    if not label_files:
        raise SystemExit(f"Chưa có nhãn trong {lab_dir}")

    valid_cls = set(names) if names else None
    n_err = 0
    n_box = 0
    for lf in label_files:
        stem = lf.stem
        if not any((img_dir / f"{stem}{e}").exists()
                   for e in (".jpg", ".jpeg", ".png")):
            print(f"  ✗ {stem}: thiếu ảnh trong images/")
            n_err += 1
        for i, line in enumerate(lf.read_text().splitlines(), 1):
            if not line.strip():
                continue
            cls, _coords, err = _parse_label_line(line.split())
            if err:
                print(f"  ✗ {stem}:{i}: {err}")
                n_err += 1
                continue
            if valid_cls is not None and cls not in valid_cls:
                print(f"  ✗ {stem}:{i}: class {cls} không có trong names")
                n_err += 1
            n_box += 1
    print("  " + "-" * 50)
    if n_err == 0:
        print(f"  ✅ hợp lệ: {len(label_files)} file, {n_box} box, 0 lỗi")
    else:
        print(f"  ⚠ {n_err} lỗi / {len(label_files)} file ({n_box} box hợp lệ)")
    return n_err


def stats(gold: Path) -> None:
    lab_dir = gold / "labels"
    label_files = sorted(lab_dir.glob("*.txt"))
    cls_counter: Counter = Counter()
    obb = hbb = 0
    boxes_per_img = []
    for lf in label_files:
        n = 0
        for line in lf.read_text().splitlines():
            p = line.split()
            if len(p) < 5:
                continue
            cls_counter[int(float(p[0]))] += 1
            if len(p) >= 8:
                obb += 1
            else:
                hbb += 1
            n += 1
        boxes_per_img.append(n)

    print(f"\n  [Gold stats]  images: {len(label_files)}  "
          f"boxes: {sum(boxes_per_img)}  (OBB {obb} / HBB {hbb})")
    if boxes_per_img:
        print(f"  boxes/ảnh: min {min(boxes_per_img)}  "
              f"max {max(boxes_per_img)}  "
              f"trung bình {sum(boxes_per_img)/len(boxes_per_img):.1f}")
    print("  class dist:", dict(sorted(cls_counter.items())))

    man = gold / "manifest.csv"
    if man.exists():
        tag_counter: Counter = Counter()
        rows = 0
        with man.open() as f:
            for r in csv.DictReader(f):
                rows += 1
                for t in (r.get("tags") or "").split(";"):
                    t = t.strip()
                    if t:
                        tag_counter[t] += 1
        print(f"\n  [Stratify]  manifest rows: {rows}")
        for t in RECOMMENDED_TAGS:
            c = tag_counter.get(t, 0)
            flag = "" if c else "   ⚠ chưa phủ"
            print(f"    {t:<26}{c:>4}{flag}")
        extra = set(tag_counter) - set(RECOMMENDED_TAGS)
        for t in sorted(extra):
            print(f"    {t:<26}{tag_counter[t]:>4}   (tag thêm)")
    else:
        print("  (chưa có manifest.csv — chạy scaffold để tạo mẫu)")
    print()


def main() -> None:
    ap = argparse.ArgumentParser(description="Gold set: scaffold/validate/stats")
    sub = ap.add_subparsers(dest="cmd", required=True)
    for name in ("scaffold", "validate", "stats"):
        sp = sub.add_parser(name)
        sp.add_argument("--gold", required=True, type=Path)
        if name == "validate":
            sp.add_argument("--names", type=Path, default=None)
    a = ap.parse_args()

    if a.cmd == "scaffold":
        scaffold(a.gold)
    elif a.cmd == "validate":
        n = validate(a.gold, load_names(getattr(a, "names", None)))
        raise SystemExit(1 if n else 0)
    elif a.cmd == "stats":
        stats(a.gold)


if __name__ == "__main__":
    main()
