#!/usr/bin/env python3
"""
Process video: SAM2 tracking + SigLIP team classification.
Uses supervision library for clean video processing.

Usage:
    python process_video.py --video /path/to/video.mp4 --refs output/refs/team_refs.pkl
    python process_video.py --video clip.mp4 --refs refs.pkl --tracker byte
"""
import argparse
import pickle
import shutil
import subprocess
from pathlib import Path

import cv2
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import supervision as sv
from tqdm import tqdm
from ultralytics import YOLO

from src.embedder    import load_siglip, encode_crops_masked
from src.jersey      import get_jersey_region, jersey_quality
from src.classifier  import TeamClassifier, color_feature

# ── Constants ─────────────────────────────────────────────────────────────────

TEAM_HEX = {'Team A': '#5050FF', 'Team B': '#FF5050', 'Other': '#00BBBB'}


# ── Shared helpers ────────────────────────────────────────────────────────────

def load_refs(path: str) -> dict:
    with open(path, 'rb') as f:
        refs = pickle.load(f)
    if 'teams' not in refs:
        raise ValueError(
            "Old refs format detected. Rebuild references with the updated "
            "ref_build.py (schema 2):  bash ref_build.sh --video <clip>")
    return refs


# ── Temporal voting ───────────────────────────────────────────────────────────

class VoteTracker:
    """
    Accumulates per-frame classification votes per track id and exposes a
    stable label via majority vote + hysteresis.

    - Votes accumulate over the whole track lifetime → a single bad frame
      cannot flip the label, and a bad initial guess is out-voted over time.
    - Hysteresis: the shown label only changes when a rival leads the current
      label by `hysteresis`× → no border flicker.
    """

    def __init__(self, teams, hysteresis: float = 1.25):
        self.teams = list(teams)
        self.hyst  = hysteresis
        self.votes = {}    # tid -> np.ndarray(len(teams))
        self.shown = {}    # tid -> team name

    def update(self, tid: int, team: str | None, weight: float) -> None:
        v = self.votes.setdefault(tid, np.zeros(len(self.teams)))
        if team is not None and weight > 0:
            v[self.teams.index(team)] += weight

    def label(self, tid: int) -> str:
        v = self.votes.get(tid)
        if v is None or v.sum() == 0:
            return self.shown.get(tid, self.teams[0])
        top = int(np.argmax(v))
        cur = self.shown.get(tid)
        if cur is None:
            self.shown[tid] = self.teams[top]
        else:
            ci = self.teams.index(cur)
            if top != ci and v[top] > v[ci] * self.hyst:
                self.shown[tid] = self.teams[top]
        return self.shown[tid]


class DrawHolder:
    """
    Display-level track coasting: keep drawing a track's last box + label for a
    few frames when the detector momentarily drops it.  Removes the visible
    "nháy" (box/label blinking) caused by single-frame detection gaps — without
    touching the player counts, which stay based on real detections.
    """

    def __init__(self, hold: int = 8):
        self.hold = hold
        self.last = {}   # tid -> [xyxy(4,), team_idx, label, last_frame_idx]

    def merge(self, index, xyxy, tids, team_indices, labels):
        present = set()
        for b, t, ti, l in zip(xyxy, tids, team_indices, labels):
            self.last[int(t)] = [np.asarray(b, dtype=float), int(ti), l, index]
            present.add(int(t))

        held_b, held_ti, held_l = [], [], []
        for tid, (b, ti, l, f) in list(self.last.items()):
            if tid in present:
                continue
            if 0 < index - f <= self.hold:
                held_b.append(b); held_ti.append(ti); held_l.append(l)
            elif index - f > self.hold:
                del self.last[tid]

        xs  = [xyxy] if len(xyxy) else []
        tis = [np.asarray(team_indices)] if len(team_indices) else []
        lbl = list(labels)
        if held_b:
            xs.append(np.array(held_b)); tis.append(np.array(held_ti)); lbl += held_l

        m_xyxy = np.vstack(xs).astype(np.float32) if xs else np.zeros((0, 4), np.float32)
        m_ti   = np.concatenate(tis).astype(int)  if tis else np.zeros((0,), int)
        return m_xyxy, m_ti, lbl


def classify_and_vote(frame, detections, masks, classifier, voter,
                      siglip_proc, siglip_model, index, siglip_every, emb_cache):
    """
    Per-detection: extract jersey region → fused colour+SigLIP classify →
    weighted temporal vote.  Returns per-detection list of shown team names.

    SigLIP is computed on background-masked crops and refreshed only every
    `siglip_every` frames (or first sighting); the cheap colour feature runs
    every frame so votes accumulate continuously.
    """
    n = len(detections)
    regions, pmasks, cfeats, quals = [], [], [], []
    for i in range(n):
        m = masks[i] if masks is not None else None
        region, pmask = get_jersey_region(frame, detections.xyxy[i], m)
        regions.append(region)
        pmasks.append(pmask)
        cfeats.append(color_feature(region, pmask) if region is not None else None)
        quals.append(jersey_quality(region, pmask) if region is not None else 0.0)

    # Decide which detections need a fresh SigLIP embedding this frame.
    if classifier.w_siglip > 0:
        need = [
            i for i in range(n)
            if regions[i] is not None
            and (int(detections.tracker_id[i]) not in emb_cache
                 or index % siglip_every == 0)
        ]
        if need:
            embs = encode_crops_masked(
                [regions[i] for i in need], [pmasks[i] for i in need],
                siglip_proc, siglip_model)
            for j, i in enumerate(need):
                emb_cache[int(detections.tracker_id[i])] = embs[j]

    shown = []
    for i in range(n):
        tid = int(detections.tracker_id[i])
        team, conf, margin = classifier.classify(emb_cache.get(tid), cfeats[i])
        if team is not None:
            w = quals[i] * max(margin, 0.0)
            if margin < classifier.min_margin:
                w *= 0.2            # ambiguous frame → small influence
            voter.update(tid, team, w)
        shown.append(voter.label(tid))
    return shown


def _detect_players(yolo_model, frame: np.ndarray, args) -> sv.Detections:
    """Run YOLO and return sv.Detections filtered by min height."""
    H = frame.shape[0]
    results    = yolo_model(frame, verbose=False, conf=args.conf, iou=args.iou,
                            imgsz=args.imgsz, classes=[0])[0]
    detections = sv.Detections.from_ultralytics(results)
    if len(detections) == 0:
        return detections
    heights    = detections.xyxy[:, 3] - detections.xyxy[:, 1]
    return detections[heights >= int(args.min_height * H)]


def _build_annotators(palette: sv.ColorPalette):
    mask_ann = sv.MaskAnnotator(
        color=palette, opacity=0.40, color_lookup=sv.ColorLookup.INDEX)
    box_ann = sv.BoxAnnotator(
        color=palette, thickness=2, color_lookup=sv.ColorLookup.INDEX)
    lbl_ann = sv.LabelAnnotator(
        color=palette, text_color=sv.Color.WHITE,
        text_scale=0.45, text_padding=4,
        color_lookup=sv.ColorLookup.INDEX,
        smart_position=True)   # nudge overlapping labels apart in pile-ups
    return mask_ann, box_ann, lbl_ann


def _raw_video_path(output_dir: Path) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    return output_dir / '_team_detect_raw.mp4'


def _reencode(src: Path, dst: Path) -> None:
    try:
        subprocess.run(
            ['ffmpeg', '-y', '-i', str(src),
             '-c:v', 'libx264', '-preset', 'fast', '-crf', '20', str(dst)],
            check=True, capture_output=True, text=True)
    except FileNotFoundError:
        print('ffmpeg not found — copying raw video without re-encode')
        shutil.copy2(src, dst)
    except subprocess.CalledProcessError as e:
        err = (e.stderr or '').strip()
        raise RuntimeError(f'ffmpeg re-encode failed: {err}') from e
    finally:
        src.unlink(missing_ok=True)


# ── SAM2 path ─────────────────────────────────────────────────────────────────

def run_sam2(args, classifier, label_map, teams,
             siglip_proc, siglip_model, output_dir):
    from src.sam2_tracker import SAM2Tracker

    try:
        sam2 = SAM2Tracker.from_size(args.sam2_size)
    except Exception as e:
        print(f"SAM2 failed to load ({e}) — falling back to ByteTrack")
        return run_bytetrack(args, classifier, label_map, teams,
                             siglip_proc, siglip_model, output_dir)

    team_to_idx = {t: i for i, t in enumerate(teams)}
    hex_list    = [TEAM_HEX.get(t, '#888888') for t in teams] + ['#888888']
    palette     = sv.ColorPalette.from_hex(hex_list)
    mask_ann, box_ann, lbl_ann = _build_annotators(palette)

    video_info  = sv.VideoInfo.from_video_path(args.video)
    yolo        = YOLO(args.yolo_model)

    # ── First frame: YOLO detect → SAM2 init ─────────────────────────────────
    gen         = sv.get_video_frames_generator(args.video)
    first_frame = next(gen)

    init_det = _detect_players(yolo, first_frame, args)
    if len(init_det) == 0:
        print("WARNING: No players in first frame — trying frame 5")
        gen2 = sv.get_video_frames_generator(args.video)
        for _ in range(5): first_frame = next(gen2)
        init_det = _detect_players(yolo, first_frame, args)

    init_det.tracker_id = np.arange(1, len(init_det) + 1)
    print(f"SAM2: initialising with {len(init_det)} players")

    voter     = VoteTracker(teams, hysteresis=args.vote_hysteresis)
    emb_cache = {}
    timeline  = []
    src_fps   = video_info.fps or 30.0

    sam2.prompt_first_frame(first_frame, init_det)

    # ── Callback ─────────────────────────────────────────────────────────────
    def callback(frame: np.ndarray, index: int) -> np.ndarray:
        detections = sam2.track(frame)

        if len(detections) == 0:
            row = {'frame': index, 'sec': round(index / src_fps, 2)}
            row.update({t: 0 for t in teams})
            timeline.append(row)
            return frame

        masks = detections.mask
        shown = classify_and_vote(
            frame, detections, masks, classifier, voter,
            siglip_proc, siglip_model, index, args.siglip_every, emb_cache)

        team_indices = np.array([team_to_idx.get(s, len(teams)) for s in shown])
        labels       = [label_map.get(s, s) for s in shown]

        # ── Filter tiny masks (< 100px²) ─────────────────────────────────────
        keep         = detections.area > 100
        detections   = detections[keep]
        team_indices = team_indices[keep]
        labels       = [l for l, k in zip(labels, keep) if k]
        shown_keep   = [s for s, k in zip(shown, keep) if k]

        counts = {t: 0 for t in teams}
        for s in shown_keep:
            if s in counts:
                counts[s] += 1

        # ── Annotate ──────────────────────────────────────────────────────────
        annotated = frame.copy()
        if detections.mask is not None and len(detections) > 0:
            annotated = mask_ann.annotate(
                annotated, detections, custom_color_lookup=team_indices)
        annotated = box_ann.annotate(
            annotated, detections, custom_color_lookup=team_indices)
        annotated = lbl_ann.annotate(
            annotated, detections, labels=labels,
            custom_color_lookup=team_indices)

        row = {'frame': index, 'sec': round(index / src_fps, 2)}
        row.update(counts)
        timeline.append(row)
        return annotated

    # ── Process ───────────────────────────────────────────────────────────────
    stem      = Path(args.video).stem
    tmp_path  = _raw_video_path(output_dir)
    out_video = output_dir / f'{stem}_team_detection.mp4'

    sv.process_video(
        source_path=args.video,
        target_path=str(tmp_path),
        callback=callback,
        show_progress=True)

    _reencode(tmp_path, out_video)
    print(f"\nVideo  → {out_video}  ({out_video.stat().st_size/1e6:.1f} MB)")
    print(f"Tracks : {len(voter.votes)}")
    return pd.DataFrame(timeline), src_fps, stem


# ── ByteTrack path ────────────────────────────────────────────────────────────

def run_bytetrack(args, classifier, label_map, teams,
                  siglip_proc, siglip_model, output_dir):

    team_to_idx = {t: i for i, t in enumerate(teams)}
    hex_list    = [TEAM_HEX.get(t, '#888888') for t in teams] + ['#888888']
    palette     = sv.ColorPalette.from_hex(hex_list)
    _, box_ann, lbl_ann = _build_annotators(palette)

    video_info = sv.VideoInfo.from_video_path(args.video)
    src_fps    = video_info.fps or 30.0
    yolo       = YOLO(args.yolo_model)

    voter      = VoteTracker(teams, hysteresis=args.vote_hysteresis)
    holder     = DrawHolder(hold=args.label_hold)
    emb_cache  = {}
    timeline   = []

    def callback(frame: np.ndarray, index: int) -> np.ndarray:
        results    = yolo.track(frame, persist=True, verbose=False,
                                conf=args.conf, iou=args.iou, imgsz=args.imgsz,
                                classes=[0], tracker=args.tracker_cfg)
        detections = sv.Detections.from_ultralytics(results[0])

        if len(detections) == 0 or detections.tracker_id is None:
            row = {'frame': index, 'sec': round(index / src_fps, 2)}
            row.update({t: 0 for t in teams})
            timeline.append(row)
            return frame

        H          = frame.shape[0]
        heights    = detections.xyxy[:, 3] - detections.xyxy[:, 1]
        detections = detections[heights >= int(args.min_height * H)]

        if len(detections) == 0:
            row = {'frame': index, 'sec': round(index / src_fps, 2)}
            row.update({t: 0 for t in teams})
            timeline.append(row)
            return frame

        shown = classify_and_vote(
            frame, detections, None, classifier, voter,
            siglip_proc, siglip_model, index, args.siglip_every, emb_cache)

        team_indices = np.array([team_to_idx.get(s, len(teams)) for s in shown])
        labels       = [label_map.get(s, s) for s in shown]

        # Counts come from REAL detections only (held boxes don't inflate them).
        counts = {t: 0 for t in teams}
        for s in shown:
            if s in counts:
                counts[s] += 1

        # Coast briefly-dropped tracks so labels don't blink.
        m_xyxy, m_ti, m_labels = holder.merge(
            index, detections.xyxy, detections.tracker_id, team_indices, labels)

        annotated = frame.copy()
        if len(m_xyxy) > 0:
            draw_det  = sv.Detections(xyxy=m_xyxy)
            annotated = box_ann.annotate(
                annotated, draw_det, custom_color_lookup=m_ti)
            annotated = lbl_ann.annotate(
                annotated, draw_det, labels=m_labels, custom_color_lookup=m_ti)

        row = {'frame': index, 'sec': round(index / src_fps, 2)}
        row.update(counts)
        timeline.append(row)
        return annotated

    stem      = Path(args.video).stem
    tmp_path  = _raw_video_path(output_dir)
    out_video = output_dir / f'{stem}_team_detection.mp4'

    sv.process_video(
        source_path=args.video,
        target_path=str(tmp_path),
        callback=callback,
        show_progress=True)

    _reencode(tmp_path, out_video)
    print(f"\nVideo  → {out_video}  ({out_video.stat().st_size/1e6:.1f} MB)")
    print(f"Tracks : {len(voter.votes)}")
    return pd.DataFrame(timeline), src_fps, stem


# ── Timeline chart ────────────────────────────────────────────────────────────

def save_timeline(df, src_fps, stem, label_map, teams, output_dir):
    w = max(1, int(src_fps))
    for t in teams:
        df[f'{t}_s'] = df[t].rolling(w, min_periods=1).mean()

    fig, axes = plt.subplots(2, 1, figsize=(14, 7), sharex=True)

    for t in teams:
        col = TEAM_HEX.get(t, '#999999')
        ls  = '--' if t == 'Other' else '-'
        lw  = 1.0  if t == 'Other' else 1.5
        axes[0].plot(df['sec'], df[f'{t}_s'],
                     color=col, label=label_map.get(t, t), lw=lw, ls=ls)
    axes[0].set_ylabel('Players / frame')
    axes[0].legend(); axes[0].grid(alpha=0.3)
    axes[0].spines[['top','right']].set_visible(False)

    main = [t for t in teams if t in ('Team A','Team B')]
    if len(main) == 2:
        ta, tb = main
        tot = df[f'{ta}_s'] + df[f'{tb}_s'] + 1e-9
        axes[1].stackplot(
            df['sec'],
            df[f'{ta}_s'] / tot * 100,
            df[f'{tb}_s'] / tot * 100,
            colors=[TEAM_HEX[ta], TEAM_HEX[tb]], alpha=0.6,
            labels=[f"{label_map.get(ta,ta)} %", f"{label_map.get(tb,tb)} %"])
        axes[1].set_ylim(0, 100)
        axes[1].legend(loc='upper right')
        axes[1].set_ylabel('Relative presence (%)')
    axes[1].set_xlabel('Time (seconds)')
    axes[1].grid(alpha=0.3); axes[1].spines[['top','right']].set_visible(False)

    plt.suptitle(f'Team Presence — {stem}', fontsize=13, fontweight='bold')
    plt.tight_layout()
    chart = output_dir / f'{stem}_team_timeline.png'
    plt.savefig(chart, dpi=150, bbox_inches='tight'); plt.close()
    print(f"Chart  → {chart}")

    csv = output_dir / f'{stem}_team_timeline.csv'
    df[['frame','sec'] + list(teams)].to_csv(csv, index=False)
    print(f"CSV    → {csv}")

    print('\n── Summary ──────────────────────────────────')
    for t in teams:
        lbl = label_map.get(t, t)
        print(f"  {lbl:14s}  avg {df[t].mean():.1f}/frame  max {int(df[t].max())}/frame")


# ── Entry point ───────────────────────────────────────────────────────────────

def main(args):
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    print(f"Loading refs from {args.refs} ...")
    refs = load_refs(args.refs)

    teams_data = refs['teams']
    label_map  = {t: d['label'] for t, d in teams_data.items()}
    if args.team_a_label and 'Team A' in label_map: label_map['Team A'] = args.team_a_label
    if args.team_b_label and 'Team B' in label_map: label_map['Team B'] = args.team_b_label
    if args.other_label  and 'Other'  in label_map: label_map['Other']  = args.other_label
    # Swap Team A ↔ Team B if assignments came out reversed
    if args.swap_teams and 'Team A' in teams_data and 'Team B' in teams_data:
        teams_data['Team A'], teams_data['Team B'] = \
            teams_data['Team B'], teams_data['Team A']
        label_map['Team A'],  label_map['Team B']  = \
            label_map['Team B'], label_map['Team A']
        print("Teams swapped: A↔B")

    teams      = list(teams_data.keys())
    classifier = TeamClassifier.from_refs(refs)

    print('Teams:')
    for t in teams:
        print(f'  {label_map[t]:14s} ← {t}')
    print(f"Fusion  : colour {classifier.w_color:.2f} | SigLIP {classifier.w_siglip:.2f}")

    siglip_proc, siglip_model = load_siglip(args.siglip_model)

    run_fn = run_sam2 if args.tracker == 'sam2' else run_bytetrack
    df, src_fps, stem = run_fn(
        args, classifier, label_map, teams,
        siglip_proc, siglip_model, output_dir)

    save_timeline(df, src_fps, stem, label_map, teams, output_dir)


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('--video',          required=True)
    p.add_argument('--refs',           required=True)
    p.add_argument('--tracker',        default='sam2', choices=['sam2','byte'])
    p.add_argument('--tracker_cfg',    default='bytetrack.yaml',
                   help='YOLO tracker config. Default bytetrack.yaml; use '
                        'botsort_gmc.yaml for clips with heavy camera panning')
    p.add_argument('--swap_teams',     action='store_true',
                   help='Swap Team A and Team B if initial assignment is reversed')
    p.add_argument('--sam2_size',      default='large',
                   choices=['large','base+','small','tiny'])
    p.add_argument('--team_a_label',   default=None)
    p.add_argument('--team_b_label',   default=None)
    p.add_argument('--other_label',    default=None)
    p.add_argument('--siglip_model',   default='google/siglip-base-patch16-224')
    p.add_argument('--yolo_model',     default='yolo11x.pt',
                   help='YOLO weights. Larger models (yolo11x) recover far more '
                        'players in crowded pile-ups than yolo26n')
    p.add_argument('--output_dir',     default='output')
    p.add_argument('--conf',           type=float, default=0.25,
                   help='YOLO confidence. Lower = better recall on occluded '
                        'players in pile-ups')
    p.add_argument('--iou',            type=float, default=0.70,
                   help='NMS IoU threshold. Higher keeps overlapping player '
                        'boxes from being suppressed against each other')
    p.add_argument('--imgsz',          type=int,   default=1280,
                   help='YOLO inference resolution. Larger detects small / '
                        'partly-occluded players in crowds')
    p.add_argument('--min_height',     type=float, default=0.07)
    p.add_argument('--smoothing',      type=int,   default=20)
    p.add_argument('--vote_hysteresis', type=float, default=1.25,
                   help='Rival must lead the shown label by this factor to flip it')
    p.add_argument('--siglip_every',   type=int,   default=5,
                   help='Refresh SigLIP embedding every N frames (colour runs every frame)')
    p.add_argument('--label_hold',     type=int,   default=8,
                   help='Keep drawing a dropped track for N frames (stops label blinking)')
    main(p.parse_args())
