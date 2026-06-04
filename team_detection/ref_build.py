#!/usr/bin/env python3
"""
Interactive reference builder — SigLIP + UMAP + K-Means.

Workflow
--------
1. Extract isolated player shirt crops from a short video clip.
2. Encode crops with SigLIP  →  768-dim semantic embeddings.
3. Fit UMAP (3-D)  +  K-Means to auto-cluster teams.
4. Open an interactive window — crops are PRE-COLOURED by the auto-cluster.
   Verify, fix any wrong crops, then press SAVE.
5. Saves mean SigLIP embeddings per team  →  output/refs/team_refs.pkl

Usage
-----
    python ref_build.py --video clip.mp4
    python ref_build.py --video clip.mp4 --n_clusters 3 --n_frames 30

Controls (in the window)
------------------------
    Click team button     set active team
    Left-click crop       assign crop to active team  (click again = unassign)
    Right-click crop      unassign
    Swap A↔B button       flip Team A and Team B assignments
    ← Prev / Next →       browse pages
    S / Enter             save and exit
    Q / Esc               quit without saving
"""
import argparse
import math
import pickle
import sys
from collections import Counter
from pathlib import Path

import cv2
import matplotlib.pyplot as plt
from matplotlib.widgets import Button
import numpy as np
from sklearn.cluster import KMeans
from tqdm import tqdm
from ultralytics import YOLO

try:
    import umap as umap_lib
except ImportError:
    print("ERROR: umap-learn not installed.  Run:  pip install umap-learn")
    sys.exit(1)

from src.embedder    import load_siglip, encode_crops
from src.shirt_color import get_shirt_crop_bgr, lab_to_rgb, SHIRT_TOP, SHIRT_BOTTOM, get_shirt_color

# ── Colours matching visualizer.py ───────────────────────────────────────────
TEAM_HEX = {'Team A': '#5050FF', 'Team B': '#FF5050', 'Other': '#00BBBB'}
TEAM_HEX_DIM  = {'Team A': '#1a2255', 'Team B': '#551a1a', 'Other': '#0d3333'}
BORDER_NONE   = '#2e2e2e'
THUMB_PX      = 120


# ── IoU helper ────────────────────────────────────────────────────────────────

def _iou(a, b):
    ax1, ay1, ax2, ay2 = a;  bx1, by1, bx2, by2 = b
    ix1, iy1 = max(ax1, bx1), max(ay1, by1)
    ix2, iy2 = min(ax2, bx2), min(ay2, by2)
    inter = max(0, ix2 - ix1) * max(0, iy2 - iy1)
    if inter == 0: return 0.0
    return inter / ((ax2-ax1)*(ay2-ay1) + (bx2-bx1)*(by2-by1) - inter)


def _isolated(boxes, max_iou=0.25):
    return [
        i for i, bi in enumerate(boxes)
        if all(_iou(bi, boxes[j]) <= max_iou for j in range(len(boxes)) if j != i)
    ]


def _letterbox(img_bgr, size=THUMB_PX, bg=35):
    ih, iw = img_bgr.shape[:2]
    s  = min(size / iw, size / ih)
    nw, nh = max(1, int(iw * s)), max(1, int(ih * s))
    r  = cv2.resize(img_bgr, (nw, nh))
    out = np.full((size, size, 3), bg, np.uint8)
    out[(size-nh)//2:(size-nh)//2+nh, (size-nw)//2:(size-nw)//2+nw] = r
    return out


# ── Crop extraction ───────────────────────────────────────────────────────────

def extract_crops(video, n_frames, conf, min_height, max_iou):
    cap     = cv2.VideoCapture(video)
    total   = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    fps     = cap.get(cv2.CAP_PROP_FPS) or 30.0
    h_vid   = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    cap.release()

    min_h_px = int(min_height * h_vid)
    indices  = np.linspace(0, total - 1, min(n_frames, total), dtype=int)
    print(f"Video    : {video}")
    print(f"Duration : {total/fps:.1f}s  ({total} frames @ {fps:.0f} fps)")
    print(f"Sampling : {len(indices)} frames  (min player height: {min_h_px}px)")

    model = YOLO('yolo26n.pt')
    crops = []   # list of {'thumb_rgb', 'crop_bgr'}

    cap = cv2.VideoCapture(video)
    for fidx in tqdm(indices, desc='Extracting crops'):
        cap.set(cv2.CAP_PROP_POS_FRAMES, int(fidx))
        ok, frame = cap.read()
        if not ok:
            continue
        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        result    = model(frame, verbose=False, conf=conf, classes=[0])[0]
        if len(result.boxes) == 0:
            continue

        boxes = [list(map(int, b.xyxy[0].tolist())) for b in result.boxes]
        boxes = [b for b in boxes if (b[3] - b[1]) >= min_h_px]
        if not boxes:
            continue

        for li in _isolated(boxes, max_iou):
            x1, y1, x2, y2 = boxes[li]
            crop_bgr = get_shirt_crop_bgr(frame, (x1, y1, x2, y2))
            if crop_bgr is None:
                continue
            thumb = cv2.cvtColor(_letterbox(crop_bgr), cv2.COLOR_BGR2RGB)
            crops.append({'thumb_rgb': thumb, 'crop_bgr': crop_bgr})

    cap.release()
    return crops


# ── SigLIP encode + UMAP + K-Means ───────────────────────────────────────────

def auto_cluster(crops, n_clusters, siglip_proc, siglip_model):
    """
    Encode crops → UMAP(3-D) → K-Means.
    Returns (embeddings_full, labels) where labels ∈ [0, n_clusters).
    """
    print(f"\nEncoding {len(crops)} crops with SigLIP...")
    crops_bgr  = [c['crop_bgr'] for c in crops]
    embeddings = encode_crops(crops_bgr, siglip_proc, siglip_model)  # (N, D)

    print(f"Fitting UMAP (n_components=3) on {len(embeddings)} embeddings...")
    reducer  = umap_lib.UMAP(n_components=3, n_neighbors=min(15, len(embeddings)-1),
                              min_dist=0.1, random_state=42, verbose=False)
    emb_3d   = reducer.fit_transform(embeddings)

    print(f"Fitting K-Means (k={n_clusters})...")
    kmeans = KMeans(n_clusters=n_clusters, random_state=42, n_init=20)
    kmeans.fit(emb_3d)
    labels = kmeans.labels_

    # Sort: largest cluster → Team A, second → Team B, rest → Other
    counts        = Counter(labels.tolist())
    sorted_clust  = [c for c, _ in counts.most_common()]
    team_names    = ['Team A', 'Team B', 'Other']
    clust_to_team = {c: team_names[min(i, 2)] for i, c in enumerate(sorted_clust)}

    assignments = [clust_to_team[lb] for lb in labels]
    return embeddings, assignments


# ── Interactive selector ──────────────────────────────────────────────────────

class RefSelector:
    N_COLS     = 8
    N_ROWS     = 5
    N_PER_PAGE = 40
    FIG_W      = 15.0
    FIG_H      =  9.0
    GRID_L, GRID_R = 0.01, 0.99
    GRID_B, GRID_T = 0.01, 0.82
    BTN_B, BTN_H   = 0.88, 0.09

    def __init__(self, crops, initial_assignments, label_a, label_b, label_other):
        self.crops       = crops
        self.n           = len(crops)
        self.labels      = {'Team A': label_a, 'Team B': label_b, 'Other': label_other}
        self.assignments = list(initial_assignments)   # mutable copy
        self.active      = 'Team A'
        self.saved       = False
        self.page        = 0
        self.n_pages     = max(1, math.ceil(self.n / self.N_PER_PAGE))
        self._team_btns  = {}
        self._img_arts   = []

    # ── Build figure ──────────────────────────────────────────────────────────

    def run(self):
        self.fig = plt.figure(figsize=(self.FIG_W, self.FIG_H), facecolor='#1a1a1a')
        self._build_buttons()
        self._build_grid()
        self._refresh()
        self.fig.canvas.mpl_connect('button_press_event', self._on_click)
        self.fig.canvas.mpl_connect('key_press_event',    self._on_key)
        plt.show(block=True)
        return self.saved

    def _build_buttons(self):
        by, bh = self.BTN_B, self.BTN_H

        # Team buttons
        for team, bx, bw in [
            ('Team A', 0.01, 0.13),
            ('Team B', 0.15, 0.13),
            ('Other',  0.29, 0.09),
        ]:
            ax  = self.fig.add_axes([bx, by, bw, bh])
            btn = Button(ax, self.labels[team],
                         color=TEAM_HEX[team], hovercolor=TEAM_HEX[team])
            btn.label.set_color('white')
            btn.label.set_fontsize(9)
            btn.label.set_fontweight('bold')
            btn.on_clicked(lambda _, t=team: self._set_active(t))
            self._team_btns[team] = (ax, btn)

        # Swap A↔B
        ax_swap = self.fig.add_axes([0.39, by, 0.08, bh])
        self._btn_swap = Button(ax_swap, 'Swap A↔B', color='#444400', hovercolor='#666600')
        self._btn_swap.label.set_color('white')
        self._btn_swap.label.set_fontsize(8)
        self._btn_swap.on_clicked(lambda _: self._swap_ab())

        # Page navigation
        ax_prev = self.fig.add_axes([0.49, by, 0.07, bh])
        ax_next = self.fig.add_axes([0.57, by, 0.07, bh])
        self._btn_prev = Button(ax_prev, '← Prev', color='#383838', hovercolor='#505050')
        self._btn_next = Button(ax_next, 'Next →', color='#383838', hovercolor='#505050')
        for b in (self._btn_prev, self._btn_next):
            b.label.set_color('white'); b.label.set_fontsize(9)
        self._btn_prev.on_clicked(lambda _: self._go_page(-1))
        self._btn_next.on_clicked(lambda _: self._go_page(+1))
        self._page_txt = self.fig.text(
            0.655, by + bh * 0.5, '', ha='center', va='center',
            fontsize=9, color='#cccccc')

        # Save / Quit
        ax_save = self.fig.add_axes([0.74, by, 0.12, bh])
        ax_quit = self.fig.add_axes([0.87, by, 0.12, bh])
        self._btn_save = Button(ax_save, 'SAVE  (S)', color='#245c24', hovercolor='#2e7a2e')
        self._btn_quit = Button(ax_quit, 'QUIT  (Q)', color='#4a3820', hovercolor='#6a5030')
        for b in (self._btn_save, self._btn_quit):
            b.label.set_color('white'); b.label.set_fontsize(10); b.label.set_fontweight('bold')
        self._btn_save.on_clicked(lambda _: self._do_save())
        self._btn_quit.on_clicked(lambda _: self._do_quit())

        self._status = self.fig.text(
            0.5, self.BTN_B - 0.022, '', ha='center', va='top',
            fontsize=8, color='#aaaaaa', fontfamily='monospace')

    def _build_grid(self):
        self.fig.subplots_adjust(
            left=self.GRID_L, right=self.GRID_R,
            bottom=self.GRID_B, top=self.GRID_T,
            hspace=0.40, wspace=0.04)
        blank = np.full((THUMB_PX, THUMB_PX, 3), 30, np.uint8)
        self.axes, self._img_arts = [], []
        for i in range(self.N_PER_PAGE):
            ax = self.fig.add_subplot(self.N_ROWS, self.N_COLS, i + 1)
            im = ax.imshow(blank, aspect='auto', interpolation='bilinear')
            ax.set_title('', fontsize=6, color='#bbbbbb', pad=2, fontweight='bold')
            ax.set_facecolor('#222222')
            for sp in ax.spines.values():
                sp.set_visible(True); sp.set_linewidth(0.4); sp.set_edgecolor(BORDER_NONE)
            ax.tick_params(left=False, bottom=False, labelleft=False, labelbottom=False)
            self.axes.append(ax); self._img_arts.append(im)

    # ── Refresh ───────────────────────────────────────────────────────────────

    def _refresh(self):
        # Button highlights
        for team, (ax_b, btn) in self._team_btns.items():
            col = TEAM_HEX[team] if team == self.active else TEAM_HEX_DIM[team]
            ax_b.set_facecolor(col); btn.color = col; btn.hovercolor = col

        self._page_txt.set_text(f'Page {self.page+1} / {self.n_pages}')

        counts = {t: sum(1 for v in self.assignments if v == t)
                  for t in ['Team A', 'Team B', 'Other']}
        self._status.set_text(
            '   '.join(f"{self.labels[t]}: {counts[t]}" for t in ['Team A', 'Team B', 'Other'])
            + '   |   Left-click=assign   Right-click=clear   1/A  2/B  3/O')

        blank = np.full((THUMB_PX, THUMB_PX, 3), 30, np.uint8)
        start = self.page * self.N_PER_PAGE
        for i, (ax, im) in enumerate(zip(self.axes, self._img_arts)):
            gidx = start + i
            if gidx < self.n:
                im.set_data(self.crops[gidx]['thumb_rgb'])
                ax.set_title(f'{gidx:03d}', fontsize=6, color='#bbbbbb', pad=2, fontweight='bold')
                ax.set_visible(True)
                team = self.assignments[gidx]
                col  = TEAM_HEX.get(team, BORDER_NONE)
                lw   = 4.0 if team else 0.4
                for sp in ax.spines.values():
                    sp.set_edgecolor(col); sp.set_linewidth(lw)
            else:
                im.set_data(blank); ax.set_title(''); ax.set_visible(False)
        self.fig.canvas.draw_idle()

    # ── Actions ───────────────────────────────────────────────────────────────

    def _set_active(self, team): self.active = team; self._refresh()

    def _swap_ab(self):
        swap = {'Team A': 'Team B', 'Team B': 'Team A'}
        self.assignments = [swap.get(v, v) for v in self.assignments]
        self._refresh()

    def _go_page(self, d):
        new = max(0, min(self.n_pages - 1, self.page + d))
        if new != self.page: self.page = new; self._refresh()

    def _do_save(self): self.saved = True; plt.close(self.fig)
    def _do_quit(self): plt.close(self.fig)

    # ── Events ────────────────────────────────────────────────────────────────

    def _on_click(self, event):
        if event.inaxes is None: return
        start = self.page * self.N_PER_PAGE
        for i, ax in enumerate(self.axes):
            if ax is event.inaxes:
                gidx = start + i
                if gidx >= self.n: break
                if event.button == 1:
                    self.assignments[gidx] = (
                        None if self.assignments[gidx] == self.active else self.active)
                elif event.button == 3:
                    self.assignments[gidx] = None
                self._refresh(); break

    def _on_key(self, event):
        k = event.key
        if   k in ('1','a'): self._set_active('Team A')
        elif k in ('2','b'): self._set_active('Team B')
        elif k in ('3','o'): self._set_active('Other')
        elif k == 'left':    self._go_page(-1)
        elif k == 'right':   self._go_page(+1)
        elif k in ('enter','s'): self._do_save()
        elif k in ('q','escape'): self._do_quit()

    # ── Build refs ────────────────────────────────────────────────────────────

    def get_refs(self, embeddings):
        refs = {}
        selections = {}
        for team in ['Team A', 'Team B', 'Other']:
            idxs = [i for i, v in enumerate(self.assignments) if v == team]
            if not idxs: continue
            embs = embeddings[idxs]   # (k, D)
            mean_emb = embs.mean(axis=0)
            mean_emb = mean_emb / (np.linalg.norm(mean_emb) + 1e-8)   # re-normalise
            refs[team]       = {'embedding': mean_emb, 'label': self.labels[team]}
            selections[team] = idxs
        return refs, selections


# ── Save helpers ──────────────────────────────────────────────────────────────

def save_refs(refs, selections, crops, output_dir):
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)

    refs_path = out / 'team_refs.pkl'
    with open(refs_path, 'wb') as f:
        pickle.dump(refs, f)

    print(f"\nSaved → {refs_path}")
    for team, data in refs.items():
        print(f"  {data['label']:14s}: {len(selections[team])} crops used")

    _save_confirmation(refs, selections, crops, out)
    print(f"\nRun detection with:")
    print(f"  bash run.sh --video /path/to/video.mp4 --refs {refs_path}")


def _save_confirmation(refs, selections, crops, out_dir, n_samples=6):
    teams  = list(refs.keys())
    n_cols = n_samples + 1
    COLORS = ['#3355FF', '#FF4444', '#00CCCC', '#FFAA00']

    fig, axes = plt.subplots(len(teams), n_cols,
                             figsize=(2.4 * n_cols, 3.0 * len(teams)))
    if len(teams) == 1: axes = [axes]

    for ti, team in enumerate(teams):
        label = refs[team]['label']
        col   = COLORS[ti % len(COLORS)]
        axes[ti][0].set_facecolor('#333333')
        axes[ti][0].set_title(f'{label}\n{len(selections[team])} crops',
                              fontsize=9, fontweight='bold', color=col)
        axes[ti][0].axis('off')
        for j, idx in enumerate(selections[team][:n_samples]):
            axes[ti][j+1].imshow(crops[idx]['thumb_rgb'])
            axes[ti][j+1].set_title(f'#{idx}', fontsize=7, pad=2)
            axes[ti][j+1].axis('off')
        for j in range(len(selections[team]), n_samples):
            axes[ti][j+1].axis('off')

    plt.suptitle('Reference embeddings confirmed', fontsize=10, fontweight='bold')
    plt.tight_layout()
    path = out_dir / 'refs_confirm.png'
    plt.savefig(path, dpi=130, bbox_inches='tight')
    plt.close(fig)
    print(f"Confirmation image → {path}")


# ── Main ──────────────────────────────────────────────────────────────────────

def main(args):
    # 1. Extract crops
    crops = extract_crops(
        args.video, args.n_frames, args.conf, args.min_height, args.max_iou)
    if not crops:
        print("ERROR: No valid crops found. Try --conf 0.35 or --min_height 0.05")
        return

    # 2. SigLIP encode + UMAP + K-Means
    proc, model = load_siglip(args.siglip_model)
    embeddings, initial_assignments = auto_cluster(crops, args.n_clusters, proc, model)

    counts = Counter(initial_assignments)
    print(f"\nAuto-cluster result:")
    for team in ['Team A', 'Team B', 'Other']:
        if counts[team]: print(f"  {team}: {counts[team]} crops")

    print(f"\n{len(crops)} crops ready. Opening selector window...")
    print("Crops are PRE-COLOURED by auto-cluster — just verify and fix errors.")

    # 3. Interactive confirmation
    selector = RefSelector(
        crops, initial_assignments,
        args.team_a_label, args.team_b_label, args.other_label)
    saved = selector.run()

    if not saved:
        print("Quit without saving.")
        return

    refs, selections = selector.get_refs(embeddings)
    if len(refs) < 2:
        print("ERROR: Need at least Team A and Team B selected (≥1 crop each).")
        return

    # 4. Save
    save_refs(refs, selections, crops, args.output_dir)


if __name__ == '__main__':
    p = argparse.ArgumentParser(description='Interactive SigLIP-based reference builder')
    p.add_argument('--video',          required=True)
    p.add_argument('--output_dir',     default='output/refs')
    p.add_argument('--n_clusters',     type=int,   default=2,    help='K-Means clusters (default 2)')
    p.add_argument('--n_frames',       type=int,   default=25,   help='Frames to sample (default 25)')
    p.add_argument('--conf',           type=float, default=0.50)
    p.add_argument('--min_height',     type=float, default=0.07)
    p.add_argument('--max_iou',        type=float, default=0.25)
    p.add_argument('--siglip_model',   default='google/siglip-base-patch16-224')
    p.add_argument('--team_a_label',   default='Bradford')
    p.add_argument('--team_b_label',   default='Opponent')
    p.add_argument('--other_label',    default='Other')
    main(p.parse_args())
