"""PoC — SAM 3 "exemplar → video" auto-labeling cho sponsor logo.

Ý tưởng #1 trong frontier_solutions.md: thay vì annotate hàng nghìn frame, ta cấp
~1 ảnh exemplar / logo (đã có sẵn trong thư mục `Sponsor Logo/`), để SAM 3
Promptable Concept Segmentation (PCS) tự segment + track mọi instance "giống vậy"
xuyên suốt video, rồi xuất nhãn YOLO + crop gallery cho Tầng 2.

Pipeline trong file này (phần "data engine", chạy được ngay end-to-end):

    Sponsor Logo/*.png   ──►  Roster (class_id ↔ brand) + exemplar bank
    video.mp4            ──►  lấy mẫu frame (mỗi N frame)
                              │
                              ▼  Sam3Labeler.label_frame(frame, exemplars)
                         RawDet[]  (xyxy, brand, conf, track_id)
                              │  roster prior + ngưỡng conf + lọc kích thước
                              ▼
       data/auto_label/labels/*.txt   (YOLO format, nhãn tự sinh)
       data/auto_label/images/*.jpg
       data/auto_label/gallery/<brand>/*.jpg   (crop cho Tầng 2 / fingerprint)
       data/auto_label/data.yaml

Backend SAM 3 được tách sau lớp `Sam3Labeler` (adapter). Khi chưa cài SAM 3 có thể
chạy `--backend mock` để kiểm thử toàn bộ orchestration (export YOLO, gallery,
data.yaml, roster filter) mà không cần GPU/model nặng — đúng tinh thần PoC.

Chạy thử:
    conda activate bradford_bulls_logo
    python auto_label/sam3_exemplar_autolabel.py \
        --video short-clips/sample.mp4 \
        --logos "Sponsor Logo" \
        --backend mock --every 15 --out data/auto_label
"""
from __future__ import annotations

import argparse
import json
import re
from dataclasses import dataclass
from pathlib import Path

import cv2
import numpy as np

# --------------------------------------------------------------------------- #
# Roster: brand ↔ class_id, build từ thư mục exemplar
# --------------------------------------------------------------------------- #

# bỏ tiền tố số thứ tự ("1 - aon_logo...") + hậu tố mô tả ("_white_rgb") để gom
# các biến thể (trắng/đỏ) của cùng một brand về một key.
_NUM_PREFIX = re.compile(r"^\s*\d+\s*-\s*")
_NOISE = re.compile(r"(logo|signature|master|final|transparent|rgb|white|black|"
                    r"red|away|home|new|font|digital|a3|ltd|group)", re.I)


def brand_key_from_filename(name: str) -> str:
    """`'1 - aon_logo_white_rgb (3).png'` -> `'aon'` (gom biến thể cùng brand)."""
    stem = Path(name).stem
    stem = _NUM_PREFIX.sub("", stem)
    stem = re.sub(r"\(.*?\)", "", stem)          # bỏ "(3)"
    stem = re.sub(r"[^a-zA-Z]+", " ", stem)       # giữ chữ cái
    stem = _NOISE.sub(" ", stem)
    tokens = [t for t in stem.split() if len(t) > 1]
    return "_".join(tokens[:2]).lower() or stem.strip().lower() or "unknown"


@dataclass
class Exemplar:
    brand: str
    path: Path
    image: np.ndarray  # BGRA hoặc BGR


class Roster:
    """Danh sách tài trợ của trận = closed-set prior (frontier_solutions §0,§2)."""

    def __init__(self, exemplars: list[Exemplar]):
        self.exemplars = exemplars
        self.brands = sorted({e.brand for e in exemplars})
        self.brand_to_id = {b: i for i, b in enumerate(self.brands)}

    @classmethod
    def from_dir(cls, logos_dir: Path, allow: set[str] | None = None) -> "Roster":
        exs: list[Exemplar] = []
        for p in sorted(logos_dir.iterdir()):
            if p.suffix.lower() not in {".png", ".jpg", ".jpeg"}:
                continue
            brand = brand_key_from_filename(p.name)
            if allow is not None and brand not in allow:
                continue
            img = cv2.imread(str(p), cv2.IMREAD_UNCHANGED)
            if img is None:
                continue
            exs.append(Exemplar(brand=brand, path=p, image=img))
        if not exs:
            raise SystemExit(f"Không tìm thấy exemplar logo trong {logos_dir}")
        return cls(exs)

    def exemplars_for(self, brand: str) -> list[Exemplar]:
        return [e for e in self.exemplars if e.brand == brand]


# --------------------------------------------------------------------------- #
# Detection chuẩn hoá
# --------------------------------------------------------------------------- #

@dataclass
class RawDet:
    brand: str
    xyxy: tuple[float, float, float, float]
    conf: float
    track_id: int = -1
    poly: tuple | None = None  # 4 điểm OBB (pixel) từ mask SAM 3, nếu có


# --------------------------------------------------------------------------- #
# SAM 3 labeler (adapter) — thay phần lõi ở `_run_sam3`
# --------------------------------------------------------------------------- #

class Sam3Labeler:
    """Bọc SAM 3 PCS. `backend='sam3'` gọi model thật; `'mock'` sinh box giả
    deterministic để kiểm thử toàn bộ pipeline không cần GPU."""

    def __init__(self, backend: str = "sam3", weights: str = "sam3.pt",
                 conf: float = 0.35, device: str | None = None):
        self.backend = backend
        self.conf = conf
        self.device = device
        self.model = None
        self._strategy = None  # tên chiến lược prompt đã dò được (cache)
        if backend == "sam3":
            try:
                from ultralytics import SAM  # type: ignore
                self.model = SAM(weights)
                if device:
                    self.model.to(device)
            except Exception as e:  # pragma: no cover - phụ thuộc môi trường
                raise SystemExit(
                    f"Không nạp được SAM 3 ({e}). Cài `ultralytics>=8.3` + weights "
                    f"`{weights}`, hoặc dùng --backend mock để thử pipeline."
                )

    # --- API công khai ---------------------------------------------------- #
    def label_frame(self, frame: np.ndarray, roster: Roster) -> list[RawDet]:
        if self.backend == "mock":
            return self._run_mock(frame, roster)
        return self._run_sam3(frame, roster)

    # --- backend thật ----------------------------------------------------- #
    # API prompt của SAM 3 (PCS) còn xê dịch giữa các bản ultralytics. Ta thử
    # lần lượt vài chữ ký phổ biến, nhớ lại cái nào chạy, rồi tái dùng. Mỗi
    # strategy nhận (model, frame_rgb, exemplar_paths, text_phrase).
    _STRATEGIES: dict = {
        "prompts_imgs":   lambda m, f, ex, ph: m(f, prompts=ex, verbose=False),
        "visual_prompts": lambda m, f, ex, ph: m(f, visual_prompts=ex, verbose=False),
        "refer_image":    lambda m, f, ex, ph: m(f, refer_image=ex[0], verbose=False),
        "texts":          lambda m, f, ex, ph: m(f, texts=[ph], verbose=False),
        "labels":         lambda m, f, ex, ph: m(f, labels=[ph], verbose=False),
    }

    def _predict(self, frame, exemplars: list[str], phrase: str):
        """Gọi model với chiến lược prompt dò được; trả `results` hoặc None."""
        order = ([self._strategy] if self._strategy
                 else list(self._STRATEGIES.keys()))
        for name in order:
            try:
                res = self._STRATEGIES[name](self.model, frame, exemplars, phrase)
                self._strategy = name  # nhớ chiến lược thắng
                return res
            except TypeError:
                continue  # chữ ký không khớp bản ultralytics này → thử cái khác
            except Exception:
                if self._strategy:  # đã chốt strategy mà vẫn lỗi → trả rỗng frame
                    return None
                continue
        raise SystemExit(
            "Không chữ ký prompt SAM 3 nào khớp bản ultralytics đang cài. "
            "Kiểm tra `ultralytics.SAM` API rồi bổ sung vào `_STRATEGIES`, "
            "hoặc dùng --backend mock."
        )

    @staticmethod
    def _scalar(x, default=None):
        """Lấy giá trị vô hướng từ tensor/ndarray/list của ultralytics."""
        if x is None:
            return default
        try:
            return x.item() if hasattr(x, "item") else (x[0] if len(x) else default)
        except Exception:
            return default

    def _run_sam3(self, frame: np.ndarray, roster: Roster) -> list[RawDet]:
        """SAM 3 PCS: mỗi brand prompt bằng exemplar (hoặc text fallback) → box
        + track id của mọi instance "giống vậy" trên frame, gắn nhãn brand.

        Lưu ý: chưa kiểm thử với weights SAM 3 thật trong môi trường này; adapter
        bám API `ultralytics.SAM` và tự dò chữ ký prompt. Frame không có logo trả
        list rỗng (hợp lệ) — không coi là lỗi.
        """
        # ultralytics nhận BGR ndarray, nhưng truyền RGB an toàn hơn cho prompt ảnh
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        dets: list[RawDet] = []
        for brand in roster.brands:
            exemplars = [e.path.as_posix() for e in roster.exemplars_for(brand)]
            phrase = brand.replace("_", " ")
            results = self._predict(rgb, exemplars, phrase)
            if not results:
                continue
            boxes = getattr(results[0], "boxes", None)
            if boxes is None:
                continue
            # masks SAM 3 (PCS) → OBB sát viền (minAreaRect). masks.xy[i] là
            # polygon pixel của instance i, khớp thứ tự với boxes.
            masks = getattr(results[0], "masks", None)
            mask_xy = getattr(masks, "xy", None) if masks is not None else None
            for i, b in enumerate(boxes):
                conf = self._scalar(getattr(b, "conf", None), 1.0)
                if conf < self.conf:
                    continue
                xyxy = b.xyxy[0].tolist() if hasattr(b.xyxy, "__getitem__") else list(b.xyxy)
                poly = None
                if mask_xy is not None and i < len(mask_xy):
                    poly = mask_to_obb_poly(mask_xy[i])
                tid = self._scalar(getattr(b, "id", None), -1)
                dets.append(RawDet(brand, tuple(float(v) for v in xyxy),
                                   float(conf), int(tid) if tid is not None else -1,
                                   poly=poly))
        return dets

    # --- mock backend ----------------------------------------------------- #
    def _run_mock(self, frame: np.ndarray, roster: Roster) -> list[RawDet]:
        """Sinh 1–2 box giả deterministic theo hash frame → cho phép kiểm thử
        export YOLO / gallery / roster filter mà không cần model."""
        h, w = frame.shape[:2]
        seed = int(frame[:: max(h // 8, 1), :: max(w // 8, 1)].sum()) % 997
        rng = np.random.default_rng(seed)
        dets: list[RawDet] = []
        for k in range(1 + seed % 2):
            brand = roster.brands[(seed + k) % len(roster.brands)]
            bw, bh = rng.integers(w // 12, w // 5), rng.integers(h // 14, h // 6)
            x0 = rng.integers(0, max(w - bw, 1)); y0 = rng.integers(0, max(h - bh, 1))
            conf = float(0.5 + 0.5 * rng.random())
            xyxy = (float(x0), float(y0), float(x0 + bw), float(y0 + bh))
            dets.append(RawDet(brand, xyxy, conf, track_id=(seed + k) % 50,
                               poly=obb_poly_from_xyxy(xyxy)))
        return [d for d in dets if d.conf >= self.conf]


# --------------------------------------------------------------------------- #
# Text-grounding / OCR labeler — kênh "text" của Logo Fingerprint (frontier §4)
# --------------------------------------------------------------------------- #

class TextGroundingLabeler:
    """Đọc chữ trong crop logo (Aon, Bartercard, MCP...) → kênh text cho
    fingerprint + một weak labeler trong Label Model (frontier_solutions §2,§4).

    backends:
      - 'locateanything' : NVIDIA LocateAnything-3B (scene-text/OCR mạnh, NHANH)
                           ⚠ license NON-COMMERCIAL → chỉ nghiên cứu/paper.
      - 'dinox'          : DINO-X (open-world, có text grounding) qua API.
      - 'mock'           : trả token brand (kiểm thử pipeline, không cần model).
      - 'none'           : tắt kênh text.
    """

    def __init__(self, backend: str = "none", weights: str = "locateanything-3b"):
        self.backend = backend
        self.model = None
        if backend in {"locateanything", "dinox"}:
            try:
                # ── ĐIỂM CẮM TEXT-GROUNDING ─────────────────────────────────
                # LocateAnything (non-commercial): nạp VLM, prompt "read the text"
                #   from transformers import AutoModelForCausalLM, AutoProcessor
                #   self.model = AutoModelForCausalLM.from_pretrained(weights, ...)
                # DINO-X: gọi client API text-grounding.
                # ────────────────────────────────────────────────────────────
                raise ImportError("adapter chưa nối")
            except Exception as e:  # pragma: no cover - phụ thuộc môi trường
                raise SystemExit(
                    f"Text backend '{backend}' chưa sẵn ({e}). "
                    f"Nối adapter ở 'ĐIỂM CẮM TEXT-GROUNDING' hoặc dùng "
                    f"--text-backend mock|none."
                )

    def read_text(self, crop: np.ndarray, brand_hint: str = "") -> str:
        if crop.size == 0 or self.backend == "none":
            return ""
        if self.backend == "mock":
            # giả lập OCR: token đầu của brand (đủ để test kênh text fingerprint)
            return brand_hint.split("_")[0]
        # ── ĐIỂM CẮM TEXT-GROUNDING (đọc chữ thật trong crop) ──────────────
        # out = self.model.generate(crop, prompt="Read all text in the image.")
        # return normalize(out)
        return ""


def color_signature(crop: np.ndarray) -> dict:
    """Kênh 'color' của Logo Fingerprint: BGR trung bình + hue trội."""
    if crop.size == 0:
        return {"mean_bgr": [0, 0, 0], "dominant_hue": -1}
    mean_bgr = [int(v) for v in crop.reshape(-1, 3).mean(0)]
    hsv = cv2.cvtColor(crop, cv2.COLOR_BGR2HSV)
    hist = cv2.calcHist([hsv], [0], None, [18], [0, 180]).flatten()
    return {"mean_bgr": mean_bgr, "dominant_hue": int(hist.argmax() * 10)}


# --------------------------------------------------------------------------- #
# Label Model lite — roster prior + lọc hình học (frontier_solutions §2)
# --------------------------------------------------------------------------- #

def filter_dets(dets: list[RawDet], roster: Roster, frame_shape,
                min_area_frac: float = 0.0008,
                max_area_frac: float = 0.25) -> list[RawDet]:
    """Roster prior (loại brand ngoài danh sách) + lọc box quá nhỏ/quá to."""
    h, w = frame_shape[:2]
    area = float(h * w)
    out: list[RawDet] = []
    for d in dets:
        if d.brand not in roster.brand_to_id:
            continue  # roster prior
        x0, y0, x1, y1 = d.xyxy
        a = max(x1 - x0, 0) * max(y1 - y0, 0)
        if not (min_area_frac * area <= a <= max_area_frac * area):
            continue
        out.append(d)
    return out


# --------------------------------------------------------------------------- #
# Xuất YOLO + gallery
# --------------------------------------------------------------------------- #

def obb_poly_from_xyxy(xyxy) -> list[tuple[float, float]]:
    """Quad axis-aligned từ xyxy (fallback khi không có mask)."""
    x0, y0, x1, y1 = xyxy
    return [(x0, y0), (x1, y0), (x1, y1), (x0, y1)]


def mask_to_obb_poly(points_xy) -> list[tuple[float, float]] | None:
    """polygon mask (pixel) → 4 điểm OBB sát viền qua cv2.minAreaRect."""
    pts = np.asarray(points_xy, dtype=np.float32)
    if pts.ndim != 2 or len(pts) < 3:
        return None
    rect = cv2.minAreaRect(pts)            # ((cx,cy),(w,h),angle)
    box = cv2.boxPoints(rect)              # 4x2
    return [(float(x), float(y)) for x, y in box]


def to_yolo_line(d: RawDet, class_id: int, w: int, h: int) -> str:
    """YOLO HBB: cls cx cy w h (normalized)."""
    x0, y0, x1, y1 = d.xyxy
    cx, cy = (x0 + x1) / 2 / w, (y0 + y1) / 2 / h
    bw, bh = (x1 - x0) / w, (y1 - y0) / h
    return f"{class_id} {cx:.6f} {cy:.6f} {bw:.6f} {bh:.6f}"


def to_yolo_obb_line(d: RawDet, class_id: int, w: int, h: int) -> str:
    """YOLO OBB: cls x1 y1 x2 y2 x3 y3 x4 y4 (normalized). Dùng poly từ mask,
    fallback quad axis-aligned từ xyxy."""
    poly = d.poly or obb_poly_from_xyxy(d.xyxy)
    coords = " ".join(f"{x / w:.6f} {y / h:.6f}" for x, y in poly)
    return f"{class_id} {coords}"


def save_gallery_crop(frame: np.ndarray, d: RawDet, gallery: Path,
                      text_labeler: "TextGroundingLabeler", stem: str) -> dict | None:
    """Lưu crop + trả về fingerprint record (visual path ⊕ text ⊕ color)."""
    x0, y0, x1, y1 = (int(v) for v in d.xyxy)
    crop = frame[max(y0, 0):y1, max(x0, 0):x1]
    if crop.size == 0:
        return None
    out = gallery / d.brand
    out.mkdir(parents=True, exist_ok=True)
    rel = f"{d.brand}/{d.brand}_{len(list(out.glob('*.jpg'))):05d}.jpg"
    cv2.imwrite(str(gallery / rel), crop)
    return {
        "brand": d.brand,
        "crop": rel,                                   # kênh visual (cho embedding)
        "text": text_labeler.read_text(crop, d.brand),  # kênh text (OCR)
        **color_signature(crop),                        # kênh color
        "bbox": [int(v) for v in d.xyxy],
        "conf": round(d.conf, 4),
        "track_id": d.track_id,
        "frame": stem,
    }


def write_data_yaml(out: Path, roster: Roster, class_agnostic: bool = False) -> None:
    # path tuyệt đối: Ultralytics phân giải 'path' tương đối theo datasets_dir
    # (không theo vị trí data.yaml) → dùng absolute cho chắc.
    lines = ["# auto-generated by sam3_exemplar_autolabel.py",
             f"path: {out.resolve()}", "train: images", "val: images"]
    if class_agnostic:
        # Tầng 1 = localizer 1 lớp `logo` (xem autolabel.md §3)
        lines += ["nc: 1", "names:", "  0: logo"]
    else:
        lines += [f"nc: {len(roster.brands)}", "names:"]
        lines += [f"  {i}: {b}" for b, i in roster.brand_to_id.items()]
    (out / "data.yaml").write_text("\n".join(lines) + "\n")


# --------------------------------------------------------------------------- #
# Vòng chính
# --------------------------------------------------------------------------- #

def run(video: Path, logos: Path, out: Path, backend: str, weights: str,
        every: int, conf: float, gallery_max: int, allow: set[str] | None,
        text_backend: str, text_weights: str, device: str | None = None,
        obb: bool = False, class_agnostic: bool = False) -> None:
    roster = Roster.from_dir(logos, allow=allow)
    print(f"[roster] {len(roster.brands)} brand: {', '.join(roster.brands)}")
    print(f"[mode]   {'OBB' if obb else 'HBB'} | "
          f"{'class-agnostic (Tầng 1)' if class_agnostic else 'per-brand'}")

    labeler = Sam3Labeler(backend=backend, weights=weights, conf=conf, device=device)
    text_labeler = TextGroundingLabeler(backend=text_backend, weights=text_weights)
    print(f"[text]   fingerprint text channel: {text_backend}")

    img_dir = out / "images"; lbl_dir = out / "labels"; gal_dir = out / "gallery"
    for d in (img_dir, lbl_dir, gal_dir):
        d.mkdir(parents=True, exist_ok=True)
    fp_file = (out / "fingerprint.jsonl").open("w")

    cap = cv2.VideoCapture(str(video))
    if not cap.isOpened():
        raise SystemExit(f"Không mở được video: {video}")

    fi = kept = n_dets = 0
    gallery_count: dict[str, int] = {}
    while True:
        ok, frame = cap.read()
        if not ok:
            break
        if fi % every != 0:
            fi += 1
            continue

        h, w = frame.shape[:2]
        dets = filter_dets(labeler.label_frame(frame, roster), roster, frame.shape)

        stem = f"frame_{fi:06d}"
        cv2.imwrite(str(img_dir / f"{stem}.jpg"), frame)
        writer = to_yolo_obb_line if obb else to_yolo_line
        (lbl_dir / f"{stem}.txt").write_text("\n".join(
            writer(d, 0 if class_agnostic else roster.brand_to_id[d.brand], w, h)
            for d in dets))

        for d in dets:
            if gallery_count.get(d.brand, 0) < gallery_max:
                rec = save_gallery_crop(frame, d, gal_dir, text_labeler, stem)
                if rec is not None:
                    fp_file.write(json.dumps(rec, ensure_ascii=False) + "\n")
                    gallery_count[d.brand] = gallery_count.get(d.brand, 0) + 1

        kept += 1; n_dets += len(dets); fi += 1

    cap.release()
    fp_file.close()
    write_data_yaml(out, roster, class_agnostic=class_agnostic)
    print(f"[done] {kept} frame gán nhãn, {n_dets} box, "
          f"gallery: {dict(gallery_count)}")
    print(f"[out]  {out}/  (images/ labels/ gallery/ data.yaml fingerprint.jsonl)")


def parse_args() -> argparse.Namespace:
    ap = argparse.ArgumentParser(description="SAM 3 exemplar auto-labeler (PoC)")
    ap.add_argument("--video", required=True, type=Path)
    ap.add_argument("--logos", default=Path("Sponsor Logo"), type=Path,
                    help="thư mục exemplar logo")
    ap.add_argument("--out", default=Path("data/auto_label"), type=Path)
    ap.add_argument("--backend", choices=["sam3", "mock"], default="sam3")
    ap.add_argument("--weights", default="sam3.pt")
    ap.add_argument("--every", type=int, default=15, help="lấy 1 frame mỗi N frame")
    ap.add_argument("--conf", type=float, default=0.35)
    ap.add_argument("--gallery-max", type=int, default=40,
                    help="số crop tối đa / brand cho Tầng 2")
    ap.add_argument("--roster", default=None,
                    help="lọc brand: chuỗi key cách nhau dấu phẩy (closed-set/trận)")
    ap.add_argument("--text-backend",
                    choices=["none", "mock", "locateanything", "dinox"],
                    default="none",
                    help="kênh text/OCR cho fingerprint (locateanything: non-commercial)")
    ap.add_argument("--text-weights", default="locateanything-3b")
    ap.add_argument("--device", default=None,
                    help="thiết bị suy luận SAM 3 (vd. cuda:0, mps, cpu)")
    ap.add_argument("--obb", action="store_true",
                    help="xuất OBB (oriented) từ mask SAM 3 thay vì HBB — Phase 1")
    ap.add_argument("--class-agnostic", dest="class_agnostic",
                    action="store_true",
                    help="gộp mọi brand về 1 lớp `logo` cho Tầng 1 (localizer)")
    return ap.parse_args()


def main() -> None:
    a = parse_args()
    allow = set(s.strip() for s in a.roster.split(",")) if a.roster else None
    run(a.video, a.logos, a.out, a.backend, a.weights,
        a.every, a.conf, a.gallery_max, allow,
        a.text_backend, a.text_weights, a.device,
        obb=a.obb, class_agnostic=a.class_agnostic)


if __name__ == "__main__":
    main()
