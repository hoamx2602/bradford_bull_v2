"""
SAM2 real-time tracker — uses segment-anything-2-real-time camera predictor.

Install:
    pip install git+https://github.com/Gy920/segment-anything-2-real-time.git
    bash download_sam2.sh large

This uses build_sam2_camera_predictor for true frame-by-frame streaming,
unlike the video predictor which requires all frames on disk upfront.
"""
import numpy as np
import torch
import supervision as sv


class SAM2Tracker:
    """
    Frame-by-frame SAM2 tracker (camera predictor API).

    Usage
    -----
    tracker = SAM2Tracker.from_size('large')
    tracker.prompt_first_frame(first_frame_bgr, sv_detections)

    for frame_bgr in frames:
        detections = tracker.track(frame_bgr)
        # detections.mask      → (N, H, W) bool
        # detections.xyxy      → (N, 4)
        # detections.tracker_id → (N,) int
    """

    CHECKPOINTS = {
        'large':  'checkpoints/sam2.1_hiera_large.pt',
        'base+':  'checkpoints/sam2.1_hiera_base_plus.pt',
        'small':  'checkpoints/sam2.1_hiera_small.pt',
        'tiny':   'checkpoints/sam2.1_hiera_tiny.pt',
    }
    CONFIGS = {
        'large':  'configs/sam2.1/sam2.1_hiera_l.yaml',
        'base+':  'configs/sam2.1/sam2.1_hiera_b+.yaml',
        'small':  'configs/sam2.1/sam2.1_hiera_s.yaml',
        'tiny':   'configs/sam2.1/sam2.1_hiera_t.yaml',
    }

    def __init__(self, checkpoint: str, config: str, device: str = None):
        if device is None:
            device = 'cuda' if torch.cuda.is_available() else 'cpu'
        self.device = device

        try:
            from sam2.build_sam import build_sam2_camera_predictor
        except ImportError:
            raise ImportError(
                "build_sam2_camera_predictor not found.\n"
                "Install the real-time fork:\n"
                "  pip install git+https://github.com/Gy920/segment-anything-2-real-time.git "
                "--no-build-isolation"
            )

        self.predictor = build_sam2_camera_predictor(config, checkpoint, device=device)
        self._api      = 'camera'
        self._prompted = False

    @classmethod
    def from_size(cls, size: str = 'large', device: str = None) -> 'SAM2Tracker':
        return cls(cls.CHECKPOINTS[size], cls.CONFIGS[size], device)

    # ── Initialisation ────────────────────────────────────────────────────────

    def prompt_first_frame(self, frame: np.ndarray,
                           detections: sv.Detections) -> None:
        """
        Initialise SAM2 with the first frame and player bounding boxes.

        Parameters
        ----------
        frame      : BGR numpy array (H, W, 3)
        detections : sv.Detections — must have .xyxy; .tracker_id optional
                     (assigned automatically as 1, 2, … if missing)
        """
        if len(detections) == 0:
            raise ValueError("Need at least one detection to initialise SAM2")

        if detections.tracker_id is None:
            detections.tracker_id = np.arange(1, len(detections) + 1)

        with torch.inference_mode(), \
             torch.autocast(self.device, dtype=torch.bfloat16):
            self.predictor.load_first_frame(frame)
            for xyxy, obj_id in zip(detections.xyxy, detections.tracker_id):
                self.predictor.add_new_prompt(
                    frame_idx=0,
                    obj_id=int(obj_id),
                    bbox=np.array([xyxy], dtype=np.float32),
                )

        self._prompted = True

    # ── Per-frame tracking ────────────────────────────────────────────────────

    def track(self, frame: np.ndarray) -> sv.Detections:
        """
        Track players in the current frame.
        Returns sv.Detections with .mask, .xyxy, .tracker_id.
        """
        if not self._prompted:
            raise RuntimeError("Call prompt_first_frame() before track()")

        with torch.inference_mode(), \
             torch.autocast(self.device, dtype=torch.bfloat16):
            tracker_ids, mask_logits = self.predictor.track(frame)

        if len(tracker_ids) == 0:
            return sv.Detections.empty()

        tracker_ids = np.asarray(tracker_ids, dtype=np.int32)
        masks = (mask_logits > 0.0).squeeze(1).cpu().numpy()
        if masks.ndim == 2:
            masks = masks[None]

        masks = np.array([
            sv.filter_segments_by_distance(m, relative_distance=0.03, mode='edge')
            for m in masks
        ])

        xyxy = sv.mask_to_xyxy(masks=masks)
        return sv.Detections(xyxy=xyxy, mask=masks, tracker_id=tracker_ids)

    # ── Utilities ─────────────────────────────────────────────────────────────

    def reset(self) -> None:
        """Reset tracker state (call before processing a new video)."""
        self._prompted = False
