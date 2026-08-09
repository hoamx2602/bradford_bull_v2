"""Test deterministic cho bộ eval Phase 0-3 — không cần GPU/model/ảnh thật.

Chạy:  pytest auto_label/tests/test_eval.py -q
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import cv2
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import eval_obb          # noqa: E402
import eval_recognition  # noqa: E402
import eval_exposure     # noqa: E402
import gold_set          # noqa: E402
import sam3_exemplar_autolabel as sam3  # noqa: E402
import train_localizer   # noqa: E402
import recognizer        # noqa: E402
import aggregate         # noqa: E402
import synth_copypaste   # noqa: E402
import team_filter       # noqa: E402
import synth_diffusion   # noqa: E402
import coco_ingest       # noqa: E402
import eval_map          # noqa: E402
import run_pipeline      # noqa: E402
import signage_ocr       # noqa: E402


# --------------------------- OBB --------------------------------------------- #

def test_poly_iou_identical():
    sq = [(0, 0), (1, 0), (1, 1), (0, 1)]
    assert abs(eval_obb.poly_iou(sq, sq) - 1.0) < 1e-9


def test_poly_iou_disjoint():
    sq = [(0, 0), (1, 0), (1, 1), (0, 1)]
    far = [(5, 5), (6, 5), (6, 6), (5, 6)]
    assert eval_obb.poly_iou(sq, far) == 0.0


def test_poly_iou_half_overlap():
    sq = [(0, 0), (1, 0), (1, 1), (0, 1)]
    half = [(0.5, 0), (1.5, 0), (1.5, 1), (0.5, 1)]
    assert abs(eval_obb.poly_iou(sq, half) - (0.5 / 1.5)) < 1e-9


def test_poly_iou_rotated_45():
    # ô vuông cạnh 2 tâm gốc, và bản xoay 45° cùng diện tích 4.
    # giao là bát giác đều — diện tích = 8*(sqrt2 - 1) ≈ 3.31371
    a = [(-1, -1), (1, -1), (1, 1), (-1, 1)]
    b = [(0, -np.sqrt(2)), (np.sqrt(2), 0), (0, np.sqrt(2)), (-np.sqrt(2), 0)]
    inter_expected = 8 * (np.sqrt(2) - 1)
    iou_expected = inter_expected / (4 + 4 - inter_expected)
    assert abs(eval_obb.poly_iou(a, b) - iou_expected) < 1e-6


def test_obb_ap_perfect():
    gts = {"a": [[(0, 0), (10, 0), (10, 10), (0, 10)]]}
    preds = [("a", 0.9, [(0, 0), (10, 0), (10, 10), (0, 10)])]
    ap, n = eval_obb.ap_for_class(preds, gts, 0.5)
    assert n == 1 and abs(ap - 1.0) < 1e-9


def test_obb_load_hbb_fallback():
    # 4 toạ độ kiểu HBB phải tự thành quad
    p = Path("/tmp/_obb_hbb.txt")
    p.write_text("0 0.5 0.5 0.2 0.2 0.77\n")
    rows = eval_obb.load_obb_file(p, with_conf=True)
    assert len(rows) == 1
    cls, quad, conf = rows[0]
    assert cls == 0 and len(quad) == 4 and abs(conf - 0.77) < 1e-9


# --------------------------- Recognition ------------------------------------- #

def test_recognition_perfect_separation():
    rows = [
        {"id": "1", "gt": "pepsi", "pred": "pepsi", "score": 0.9},
        {"id": "2", "gt": "toyota", "pred": "toyota", "score": 0.85},
        {"id": "3", "gt": "unknown", "pred": "pepsi", "score": 0.2},
        {"id": "4", "gt": "unknown", "pred": "toyota", "score": 0.3},
    ]
    res = eval_recognition.evaluate(rows, tau=0.6)
    assert abs(res["top1_acc"] - 1.0) < 1e-9
    assert abs(res["open_set_auroc"] - 1.0) < 1e-9
    assert abs(res["unknown_rejection@tau"] - 1.0) < 1e-9
    assert abs(res["known_acceptance@tau"] - 1.0) < 1e-9


def test_auroc_chance():
    sc = np.array([0.5, 0.5, 0.5, 0.5])
    lb = np.array([1, 0, 1, 0])
    assert abs(eval_recognition.auroc(sc, lb) - 0.5) < 1e-9


def test_recognition_threshold_rejects_low_score():
    # pred đúng brand nhưng score < τ → không được tính đúng (bị coi unknown)
    rows = [{"id": "1", "gt": "pepsi", "pred": "pepsi", "score": 0.4}]
    res = eval_recognition.evaluate(rows, tau=0.6)
    assert res["top1_acc"] == 0.0


def test_ocr_rejects_single_auxiliary_brand_word():
    lex = {"chadlaw": {"tokens": ["chadlaw", "chadwick", "lawrence"]}}
    assert signage_ocr.classify("LAWRENCE", lex) == ("unknown", 0.0)
    assert signage_ocr.classify("CHADLAW", lex)[0] == "chadlaw"
    assert signage_ocr.classify("Chadwick Lawrence", lex)[0] == "chadlaw"


# --------------------------- Exposure ---------------------------------------- #

def test_exposure_mae_and_missing_brands():
    pred = {"video": "t", "brands": {
        "pepsi": {"exposure_sec": 40.0, "visibility_pct": 3.0},
        "ghost": {"exposure_sec": 5.0, "visibility_pct": 0.5},
    }}
    gt = {"video": "t", "brands": {
        "pepsi": {"exposure_sec": 42.0, "visibility_pct": 3.1},
        "toyota": {"exposure_sec": 12.0, "visibility_pct": 1.0},
    }}
    res = eval_exposure.evaluate(pred, gt)
    assert abs(res["exposure_sec_MAE"] - (2 + 5 + 12) / 3) < 1e-9


def test_temporal_iou():
    assert abs(eval_exposure.temporal_iou([[0, 10]], [[5, 15]]) - (5 / 15)) < 1e-9
    # gộp đoạn chồng lấn
    assert abs(eval_exposure.temporal_iou([[0, 6], [4, 10]], [[0, 10]]) - 1.0) < 1e-9


# --------------------------- Gold set ---------------------------------------- #

def test_gold_label_parse_valid():
    cls, coords, err = gold_set._parse_label_line("0 0.5 0.5 0.2 0.2".split())
    assert err is None and cls == 0 and len(coords) == 4


def test_gold_label_parse_out_of_range():
    _, _, err = gold_set._parse_label_line("0 0.5 0.5 1.9 0.2".split())
    assert err is not None and "ngoài" in err


def test_gold_label_parse_obb():
    line = "0 0.1 0.1 0.2 0.1 0.2 0.2 0.1 0.2"
    cls, coords, err = gold_set._parse_label_line(line.split())
    assert err is None and len(coords) == 8


def test_scaffold_and_validate(tmp_path):
    gold = tmp_path / "gold"
    gold_set.scaffold(gold)
    assert (gold / "images").is_dir()
    assert (gold / "manifest.csv").exists()
    # tạo 1 cặp ảnh+nhãn hợp lệ (ảnh rỗng đủ để tồn tại)
    (gold / "images" / "x.jpg").write_bytes(b"\xff\xd8\xff\xd9")
    (gold / "labels" / "x.txt").write_text("0 0.5 0.5 0.2 0.2\n")
    n_err = gold_set.validate(gold, names={0: "logo"})
    assert n_err == 0


def test_validate_catches_bad_class(tmp_path):
    gold = tmp_path / "gold"
    gold_set.scaffold(gold)
    (gold / "images" / "y.jpg").write_bytes(b"\xff\xd8\xff\xd9")
    (gold / "labels" / "y.txt").write_text("5 0.5 0.5 0.2 0.2\n")
    n_err = gold_set.validate(gold, names={0: "logo"})
    assert n_err >= 1


# --------------------------- Phase 1: OBB autolabel -------------------------- #

def test_obb_poly_from_xyxy():
    poly = sam3.obb_poly_from_xyxy((10, 20, 30, 40))
    assert poly == [(10, 20), (30, 20), (30, 40), (10, 40)]


def test_mask_to_obb_poly_axis_aligned():
    # mask hình chữ nhật trục → minAreaRect trả đúng 4 góc (đủ diện tích)
    pts = [(10, 10), (50, 10), (50, 30), (10, 30)]
    poly = sam3.mask_to_obb_poly(pts)
    assert poly is not None and len(poly) == 4
    xs = [p[0] for p in poly]; ys = [p[1] for p in poly]
    assert min(xs) <= 11 and max(xs) >= 49 and min(ys) <= 11 and max(ys) >= 29


def test_to_yolo_obb_line_class_agnostic():
    d = sam3.RawDet("aon", (0, 0, 100, 50), 0.9,
                    poly=[(0, 0), (100, 0), (100, 50), (0, 50)])
    out = sam3.to_yolo_obb_line(d, class_id=0, w=200, h=100)
    toks = out.split()
    assert toks[0] == "0" and len(toks) == 9   # cls + 8 toạ độ
    assert abs(float(toks[1]) - 0.0) < 1e-9 and abs(float(toks[3]) - 0.5) < 1e-9


def test_train_localizer_obb_rows_shape():
    # dùng selftest interface giả của train_localizer (không cần ultralytics)
    import numpy as np

    class _T:
        def __init__(self, a): self.a = a
        def cpu(self): return self
        def numpy(self): return self.a

    class _OBB:
        xyxyxyxy = _T(np.array([[[10, 10], [50, 12], [48, 40], [8, 38]]], float))
        conf = _T(np.array([0.87])); cls = _T(np.array([0]))
        def __len__(self): return 1

    class _Res:
        orig_shape = (100, 200); obb = _OBB(); boxes = None

    rows = train_localizer._obb_rows_from_result(_Res(), class_agnostic=True)
    assert len(rows) == 1
    toks = rows[0].split()
    assert toks[0] == "0" and len(toks) == 10   # cls + 8 toạ độ + conf


# --------------------------- Phase 2: Recognizer ---------------------------- #

def _unit(v):
    v = np.asarray(v, np.float32)
    return v / np.linalg.norm(v)


def test_templatedb_nearest_brand():
    base = np.eye(3, dtype=np.float32)  # 3 vector trực giao
    db = recognizer.TemplateDB(base, ["aon", "toyota", "klg"], ["a", "b", "c"])
    brand, score = db.query(_unit([0.9, 0.1, 0.0]))
    assert brand == "aon" and score > 0.9


def test_templatedb_batch_matches_single():
    base = np.eye(4, dtype=np.float32)
    db = recognizer.TemplateDB(base, ["a", "b", "c", "d"], ["1", "2", "3", "4"])
    qs = np.stack([_unit([0.8, 0.2, 0, 0]), _unit([0, 0, 0.1, 0.95])])
    out = db.query_batch(qs)
    assert out[0][0] == "a" and out[1][0] == "d"


def test_templatedb_multi_template_per_brand_takes_max():
    # 2 template cho 'aon' (1 lệch), 1 cho 'klg'; query gần template aon thứ 2
    V = np.stack([_unit([1, 0, 0]), _unit([0.6, 0.8, 0]), _unit([0, 0, 1])])
    db = recognizer.TemplateDB(V, ["aon", "aon", "klg"], ["a1", "a2", "k"])
    brand, _ = db.query(_unit([0.55, 0.83, 0]))
    assert brand == "aon"


def test_templatedb_save_load(tmp_path):
    V = _unit([1, 2, 2]).reshape(1, 3)
    db = recognizer.TemplateDB(V, ["aon"], ["p"], model_id="m")
    p = tmp_path / "db.npz"; db.save(p)
    db2 = recognizer.TemplateDB.load(p)
    assert db2.brands == ["aon"] and db2.model_id == "m"
    assert np.allclose(db2.vecs, db.vecs)


def test_recognizer_margin_score():
    base = np.eye(3, dtype=np.float32)
    db = recognizer.TemplateDB(base, ["a", "b", "c"], ["1", "2", "3"])
    pa, ma = db.query(_unit([0.95, 0.05, 0]), score_mode="margin")  # rõ ràng là a
    pb, mb = db.query(_unit([0.72, 0.70, 0]), score_mode="margin")  # mơ hồ a/b
    assert pa == "a" and ma > mb            # query rõ → margin lớn hơn query mơ hồ


def test_calibrate_perfect_separation():
    rows = [{"gt": "a", "score": 0.9}, {"gt": "a", "score": 0.85},
            {"gt": "unknown", "score": 0.2}, {"gt": "unknown", "score": 0.3}]
    c = eval_recognition.calibrate(rows, target_known_acc=0.95)
    assert c["tau_target"] is not None
    assert c["tau_target"]["known_acc"] == 1.0
    assert c["tau_target"]["unknown_rej"] == 1.0


def test_calibrate_no_feasible_tau():
    # known và unknown trùng điểm hoàn toàn → không τ nào đạt target + reject
    rows = [{"gt": "a", "score": 0.5}, {"gt": "unknown", "score": 0.5}]
    c = eval_recognition.calibrate(rows, target_known_acc=0.95)
    assert c["tau_target"] is None


def test_bgra_to_rgb_alpha_blend():
    # pixel xanh dương mờ 50% alpha trên nền trắng → sáng lên
    bgra = np.zeros((1, 1, 4), np.uint8); bgra[..., 0] = 255; bgra[..., 3] = 128
    rgb = recognizer.bgra_to_rgb(bgra)
    assert rgb.shape == (1, 1, 3) and rgb[0, 0, 0] > 100  # R kéo lên do nền trắng


# --------------------------- Phase 3: Aggregation --------------------------- #

def test_merge_intervals_bridge_and_gap():
    assert aggregate.merge_intervals([0.0, 0.4], 0.4, 0.8) == [(0.0, 0.8)]
    assert aggregate.merge_intervals([0.0, 5.0], 0.4, 0.8) == [(0.0, 0.4), (5.0, 5.4)]
    assert aggregate.merge_intervals([], 0.4, 0.8) == []


def test_aggregate_exposure_and_visibility():
    fps, sfps = 25.0, 2.5            # dt = 0.4s
    dets = [{"frame": fr, "brand": "aon", "conf": 0.9, "area_pct": 2.0}
            for fr in (0, 10, 20, 30)]
    r = aggregate.aggregate(dets, fps, sfps, min_seg=0.5)
    assert abs(r["brands"]["aon"]["exposure_sec"] - 1.6) < 1e-6
    assert abs(r["brands"]["aon"]["visibility_pct"] - 2.0) < 1e-6
    assert r["brands"]["aon"]["n_segments"] == 1


def test_aggregate_drops_ghost_lowconf_and_scene():
    fps, sfps = 25.0, 2.5
    dets = [
        {"frame": 100, "brand": "ghost", "conf": 0.9, "area_pct": 1.0},   # 1 sample
        {"frame": 0, "brand": "low", "conf": 0.1, "area_pct": 5.0},        # low conf
        {"frame": 0, "brand": "rep", "conf": 0.9, "area_pct": 3.0, "scene": "replay"},
    ]
    r = aggregate.aggregate(dets, fps, sfps, conf_thr=0.3, min_seg=0.5,
                            exclude_scenes={"replay"})
    assert r["brands"] == {}


# --------------------------- Bậc 1 / 3 / team-filter ------------------------ #

def test_synth_copypaste_paste_and_lines():
    bg = np.zeros((80, 160, 3), np.uint8)
    logo = np.dstack([np.full((30, 30, 3), 255, np.uint8),
                      np.full((30, 30), 255, np.uint8)])
    out, quad = synth_copypaste.paste_logo(bg, logo)
    assert quad.shape == (4, 2) and out.sum() > 0
    q = np.array([[0, 0], [10, 0], [10, 20], [0, 20]], np.float32)
    assert len(synth_copypaste.to_obb_line(q, 0, 100, 100).split()) == 9
    assert len(synth_copypaste.to_hbb_line(q, 2, 100, 100).split()) == 5


def test_team_filter_classify_and_filter():
    refs = {"bradford": np.array([1, 0, 0], np.float32),
            "other": np.array([0, 1, 0], np.float32)}
    assert team_filter.classify(np.array([0.9, 0.1, 0], np.float32), refs)[0] == "bradford"
    persons = [[0, 0, 100, 200], [40, 40, 70, 120]]
    assert team_filter.assign_owner([50, 50, 60, 60], persons) == 1
    res = team_filter.filter_logos([[50, 50, 60, 60], [10, 10, 20, 20]],
                                   persons, ["other", "bradford"], target="bradford")
    keep = {r["idx"]: r["keep"] for r in res}
    assert keep[0] is True and keep[1] is False


def test_synth_diffusion_composite_back_restores_logo():
    bg = np.zeros((50, 50, 3), np.uint8)
    logo = np.dstack([np.full((16, 16, 3), 200, np.uint8),
                      np.full((16, 16), 255, np.uint8)])
    pasted, lmask, quad = synth_diffusion.paste_with_mask(bg, logo)
    inv = synth_diffusion.inpaint_mask_from_logo(lmask)
    assert np.all((inv == 0) == (lmask == 255))
    gen = np.full_like(pasted, 99)
    out = synth_diffusion.composite_back(gen, pasted, lmask, feather=0)
    px = lmask == 255
    assert np.array_equal(out[px], pasted[px])


def test_aggregate_coverage_clamped_and_summed():
    # 2 instance cùng frame cùng brand → coverage cộng, clamp 100
    fps, sfps = 25.0, 2.5
    dets = [{"frame": f, "brand": "x", "conf": 0.9, "area_pct": 70.0}
            for f in (0, 10)] + \
           [{"frame": f, "brand": "x", "conf": 0.9, "area_pct": 70.0}
            for f in (0, 10)]
    r = aggregate.aggregate(dets, fps, sfps, min_seg=0.3)
    assert abs(r["brands"]["x"]["visibility_pct"] - 100.0) < 1e-6   # 140→clamp 100


# --------------------------- coco_ingest ------------------------------------ #

def _make_coco_json(tmp_path: Path, n_images: int = 4) -> Path:
    """Tạo COCO JSON giả + ảnh dummy cho test."""
    tmp_path.mkdir(parents=True, exist_ok=True)
    cats = [{"id": 1, "name": "aon"}, {"id": 2, "name": "klg"}]
    images, annotations, ann_id = [], [], 1
    for i in range(n_images):
        fname = f"img_{i:03d}.jpg"
        images.append({"id": i, "file_name": fname,
                        "width": 200, "height": 100})
        img = np.zeros((100, 200, 3), np.uint8) + (i * 30)
        cv2.imwrite(str(tmp_path / fname), img)
        cat_id = 1 + (i % 2)
        annotations.append({"id": ann_id, "image_id": i,
                             "category_id": cat_id,
                             "bbox": [10, 10, 50, 30]})
        ann_id += 1
    js = {"images": images, "annotations": annotations, "categories": cats}
    p = tmp_path / "_annotations.coco.json"
    p.write_text(json.dumps(js))
    return tmp_path


def _coco_args(**kw):
    import argparse
    defaults = dict(split=0.5, pad=0.0, yolo=False, seed=42)
    defaults.update(kw)
    return argparse.Namespace(**defaults)


def test_coco_ingest_splits_at_image_level(tmp_path):
    """Split tỉ lệ 0.5 → mỗi bên nhận đúng n_images/2 ảnh (không leakage)."""
    coco_dir = _make_coco_json(tmp_path / "coco", n_images=4)
    out = tmp_path / "out"
    coco_ingest.run(_coco_args(coco=str(coco_dir), out=str(out), split=0.5))
    gal = list((out / "gallery").rglob("*.jpg"))
    tst = list((out / "test").rglob("*.jpg"))
    assert len(gal) == 2 and len(tst) == 2


def test_coco_ingest_yolo_labels(tmp_path):
    """Nhãn YOLO HBB đúng: 5 token, cx/cy/w/h ∈ (0,1), cls hợp lệ."""
    coco_dir = _make_coco_json(tmp_path / "coco", n_images=4)
    out = tmp_path / "out"
    coco_ingest.run(_coco_args(coco=str(coco_dir), out=str(out), split=1.0, yolo=True))
    lbl_files = list((out / "labels").glob("*.txt"))
    assert lbl_files, "phải có ít nhất 1 file nhãn"
    for f in lbl_files:
        for line in f.read_text().splitlines():
            toks = line.split()
            assert len(toks) == 5, f"YOLO HBB cần 5 token, got {len(toks)}"
            cx, cy, w, h = (float(t) for t in toks[1:])
            assert 0 < cx < 1 and 0 < cy < 1
            assert 0 < w <= 1 and 0 < h <= 1


def test_coco_ingest_crops_padded(tmp_path):
    """Pad > 0 → crop rộng hơn bbox gốc (không vượt biên ảnh)."""
    coco_dir = _make_coco_json(tmp_path / "coco", n_images=2)
    out_nop = tmp_path / "out_nop"
    out_pad = tmp_path / "out_pad"
    coco_ingest.run(_coco_args(coco=str(coco_dir), out=str(out_nop), split=1.0, pad=0.0))
    coco_ingest.run(_coco_args(coco=str(coco_dir), out=str(out_pad), split=1.0, pad=0.5))
    imgs_nop = list(out_nop.rglob("*.jpg"))
    imgs_pad = list(out_pad.rglob("*.jpg"))
    assert imgs_nop and imgs_pad
    sizes_nop = {p.name: cv2.imread(str(p)).shape for p in imgs_nop}
    sizes_pad = {p.name: cv2.imread(str(p)).shape for p in imgs_pad}
    any_larger = any(sizes_pad[n][0] >= sizes_nop[n][0] and
                     sizes_pad[n][1] >= sizes_nop[n][1]
                     for n in sizes_nop if n in sizes_pad)
    assert any_larger


# --------------------------- eval_map end-to-end ---------------------------- #

def _write_hbb_labels(d: Path, rows: list[str]) -> None:
    d.mkdir(parents=True, exist_ok=True)
    for i, r in enumerate(rows):
        (d / f"img_{i:03d}.txt").write_text(r + "\n")


def _write_images(d: Path, n: int) -> None:
    d.mkdir(parents=True, exist_ok=True)
    for i in range(n):
        img = np.zeros((100, 200, 3), np.uint8)
        cv2.imwrite(str(d / f"img_{i:03d}.jpg"), img)


def test_eval_map_perfect_hbb(tmp_path):
    """mAP@0.5 = 1.0 và mAP@[.5:.95] cao khi pred = gt."""
    gold = tmp_path / "gold"
    pred = tmp_path / "pred"
    labels = ["0 0.25 0.25 0.2 0.2", "0 0.75 0.75 0.2 0.2"]
    _write_images(gold / "images", 2)
    _write_hbb_labels(gold / "labels", labels)
    # pred = gt + conf
    _write_hbb_labels(pred / "labels", [l + " 0.95" for l in labels])
    res = eval_map.evaluate(gold, pred)
    assert abs(res["map50"] - 1.0) < 1e-9
    assert res["map5095"] > 0.5
    assert res["n_images"] == 2


def test_eval_map_no_pred(tmp_path):
    """Không có pred → mAP = 0.0."""
    gold = tmp_path / "gold"
    _write_images(gold / "images", 1)
    _write_hbb_labels(gold / "labels", ["0 0.5 0.5 0.2 0.2"])
    pred = tmp_path / "pred"
    (pred / "labels").mkdir(parents=True, exist_ok=True)
    # pred dir rỗng → không match GT nào
    res = eval_map.evaluate(gold, pred)
    assert res["map50"] == 0.0


def test_eval_map_iou_fallback_no_images(tmp_path):
    """Khi thiếu ảnh trong gold/images → iou_fallback = True."""
    gold = tmp_path / "gold"
    pred = tmp_path / "pred"
    _write_hbb_labels(gold / "labels", ["0 0.5 0.5 0.2 0.2"])
    _write_hbb_labels(pred / "labels", ["0 0.5 0.5 0.2 0.2 0.9"])
    (gold / "images").mkdir(parents=True, exist_ok=True)   # thư mục rỗng, không có ảnh
    res = eval_map.evaluate(gold, pred)
    assert res["iou_fallback_normalized"] is True


# --------------------------- run_pipeline utilities ------------------------- #

def test_poly_area_unit_square():
    """Diện tích ô vuông đơn vị = 1.0."""
    poly = np.array([[0, 0], [1, 0], [1, 1], [0, 1]], np.float32)
    assert abs(run_pipeline.poly_area(poly) - 1.0) < 1e-9


def test_poly_area_triangle():
    """Tam giác cạnh 2 → diện tích = 2."""
    poly = np.array([[0, 0], [2, 0], [0, 2]], np.float32)
    assert abs(run_pipeline.poly_area(poly) - 2.0) < 1e-9


def test_clarity_score_in_range():
    """Score ∈ [0, 1) trên ảnh bất kỳ."""
    img = np.random.randint(0, 256, (50, 50, 3), dtype=np.uint8)
    s = run_pipeline.clarity_score(img)
    assert 0.0 <= s < 1.0


def test_clarity_score_empty():
    """Ảnh rỗng → 0.0 (không crash)."""
    assert run_pipeline.clarity_score(np.zeros((0, 0, 3), np.uint8)) == 0.0


def test_clarity_sharp_gt_blur():
    """Ảnh sắc nét có clarity cao hơn ảnh mờ."""
    sharp = np.random.randint(0, 256, (80, 80, 3), dtype=np.uint8)
    blurred = cv2.GaussianBlur(sharp, (21, 21), 10)
    assert run_pipeline.clarity_score(sharp) > run_pipeline.clarity_score(blurred)


def test_crop_and_mask_shape():
    """crop_and_mask trả đúng kích thước và mask nhị phân."""
    frame = np.random.randint(0, 256, (100, 200, 3), dtype=np.uint8)
    poly = np.array([[10, 20], [60, 20], [60, 50], [10, 50]], np.float32)
    crop, mask = run_pipeline.crop_and_mask(frame, poly, pad=0)
    assert crop is not None and mask is not None
    assert crop.shape[:2] == mask.shape
    assert set(np.unique(mask)) <= {0, 1}


def test_crop_and_mask_degenerate():
    """Poly suy biến (0 diện tích) → trả (None, None), không crash."""
    frame = np.zeros((100, 200, 3), np.uint8)
    poly = np.array([[5, 5], [5, 5], [5, 5], [5, 5]], np.float32)
    crop, mask = run_pipeline.crop_and_mask(frame, poly, pad=0)
    assert crop is None and mask is None
