"""Test deterministic cho bộ eval Phase 0 — không cần GPU/model/ảnh thật.

Chạy:  pytest auto_label/tests/test_eval.py -q
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

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


def test_aggregate_coverage_clamped_and_summed():
    # 2 instance cùng frame cùng brand → coverage cộng, clamp 100
    fps, sfps = 25.0, 2.5
    dets = [{"frame": f, "brand": "x", "conf": 0.9, "area_pct": 70.0}
            for f in (0, 10)] + \
           [{"frame": f, "brand": "x", "conf": 0.9, "area_pct": 70.0}
            for f in (0, 10)]
    r = aggregate.aggregate(dets, fps, sfps, min_seg=0.3)
    assert abs(r["brands"]["x"]["visibility_pct"] - 100.0) < 1e-6   # 140→clamp 100
