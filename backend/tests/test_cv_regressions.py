import numpy as np
from types import SimpleNamespace

from app.pipeline.bodyseg_yolo import _bones, _match_poses, _segment_frame
from app.pipeline.teamid.classifier import VoteTracker, TARGET, OTHER, UNKNOWN
from app.pipeline.teamid.tracker import TeamTracker
from test_teamid import _det, _person


def test_no_evidence_is_unknown():
    assert VoteTracker([TARGET, OTHER]).label(99) == UNKNOWN


def test_unknown_policy_applies_to_both_teams():
    tracker = object.__new__(TeamTracker)
    tracker.settings = SimpleNamespace(team_keep_unknown=False, team_keep_unassigned=False, team_min_votes=2)
    for team in (TARGET, OTHER, UNKNOWN):
        det = _det(150, 150)
        tracker.annotate([det], [_person(100, 100, 200, 250, team=team, mass=0)])
        assert det.on_target_team is False


def test_advertising_board_outside_player_is_unassigned():
    from app.pipeline.teamid.tracker import assign_owner
    assert assign_owner(_det(230, 160), [_person(100, 100, 160, 220)]) is None


def test_pose_is_never_reused_for_overlapping_players():
    matches = _match_poses([[0, 0, 100, 200], [5, 5, 105, 205]], [[0, 0, 100, 200]])
    assert matches == {0: 0}


def test_missing_hips_do_not_invent_vertical_torso():
    kp = np.zeros((17, 3))
    kp[5], kp[6] = (10, 20, .9), (30, 20, .9)
    assert not any(g == 'torso' for _, _, g in _bones(kp))


def test_unmatched_silhouette_is_unknown_not_torso():
    class Tensor:
        def __init__(self, a): self.a = np.array(a)
        def cpu(self): return self
        def numpy(self): return self.a
    seg = SimpleNamespace(predict=lambda *a, **kw: [SimpleNamespace(
        masks=SimpleNamespace(data=Tensor(np.ones((1, 8, 8)))),
        boxes=SimpleNamespace(xyxy=Tensor([[0, 0, 8, 8]]), conf=Tensor([.9])))])
    pose = SimpleNamespace(predict=lambda *a, **kw: [])
    counts = {}
    overlay = _segment_frame(np.zeros((8, 8, 3), dtype=np.uint8), seg, pose, 'cpu', 32, .3, counts)
    assert counts == {'unknown': 64}
    assert (overlay == 128).all()


def test_yolo_adapter_initializes_model_and_resets_state(monkeypatch):
    from app.pipeline.detect_track import _YoloBackend
    from app.models_zoo import registry
    reset = []
    model = SimpleNamespace(predictor=SimpleNamespace(trackers=[SimpleNamespace(reset=lambda: reset.append(True))]))
    backend = SimpleNamespace(model=model, names={0: 'logo'}, reset=lambda: None)
    monkeypatch.setattr(registry, 'get_logo_backend', lambda: backend)
    monkeypatch.setattr(registry, 'device', lambda: 'cpu')
    adapter = _YoloBackend()
    assert adapter.model is model and adapter.device == 'cpu' and reset == [True]


def test_kit_anchor_is_not_cropped_as_a_full_body(monkeypatch, tmp_path):
    import cv2
    from app.pipeline.teamid import bootstrap
    folder = tmp_path / 'data' / 'kit_anchors' / 'home'
    folder.mkdir(parents=True)
    cv2.imwrite(str(folder / 'front.jpg'), np.full((100, 60, 3), 240, dtype=np.uint8))
    seen = []
    monkeypatch.setattr(bootstrap, 'BACKEND_DIR', tmp_path)
    def encode(regions, masks, device):
        seen.extend(r.shape for r in regions)
        return None
    monkeypatch.setattr(bootstrap, 'encode_crops_masked', encode)
    bootstrap._anchor_features('home', 'cpu')
    assert seen == [(100, 60, 3)]


def test_identical_reference_crops_do_not_crash_kmeans():
    from app.pipeline.teamid.bootstrap import _kmeans
    labels, centers = _kmeans(np.ones((30, 20)), 3)
    assert (labels == 0).all() and np.isfinite(centers).all()


def test_home_kit_keeps_shaded_white_and_excludes_coloured_kit():
    from app.pipeline.teamid.jersey import bradford_home_evidence, _skin_mask
    white = np.full((50, 50, 3), 150, dtype=np.uint8)
    white[:5] = (0, 0, 230)
    assert bradford_home_evidence(white) == TARGET
    assert bradford_home_evidence(np.full((50, 50, 3), (180, 70, 100), dtype=np.uint8)) == OTHER
    assert bradford_home_evidence(np.full((50, 50, 3), (50, 210, 70), dtype=np.uint8)) == OTHER
    assert not _skin_mask(np.full((20, 20, 3), (0, 0, 230), dtype=np.uint8)).any()
    assert bradford_home_evidence(np.full((50, 50, 3), 20, dtype=np.uint8)) is None


def test_broadcast_cut_is_detected_without_resetting_identical_frames():
    tr = object.__new__(TeamTracker)
    tr._previous_scene = None
    a = np.full((80, 100, 3), (30, 170, 30), dtype=np.uint8)
    b = np.full((80, 100, 3), (150, 30, 160), dtype=np.uint8)
    assert not tr._scene_changed(a)
    assert not tr._scene_changed(a)
    assert tr._scene_changed(b)
