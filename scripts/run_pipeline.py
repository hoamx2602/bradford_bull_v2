"""
Run the full frame-selection pipeline on one or more videos.

Usage:
    python scripts/run_pipeline.py --video videos/M06_black_1080p.mp4
    python scripts/run_pipeline.py                          # all *.mp4 in videos/
    python scripts/run_pipeline.py --fps 10 --max-output 600
"""
import argparse
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from frame_selector.color_filter import COLOR_PRESETS
from frame_selector.pipeline import Config, run_pipeline


def parse_color(filename: str) -> str:
    name = Path(filename).stem.lower()
    m = re.match(r'^m\d+_([a-z]+)_', name)
    if m and m.group(1) in COLOR_PRESETS:
        return m.group(1)
    for c in COLOR_PRESETS:
        if c in name:
            return c
    raise ValueError(
        f'Cannot parse color from "{filename}". '
        f'Rename as M01_white_1080p.mp4 or pass --color explicitly.'
    )


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument('--video', type=Path, default=None,
                    help='Single video (default: all videos/*.mp4)')
    ap.add_argument('--color', default=None,
                    help='Target jersey color (auto-parsed from filename)')
    ap.add_argument('--out-dir', type=Path, default=Path('pipeline_output'),
                    help='Root output directory (default: pipeline_output/)')
    ap.add_argument('--cache-dir', type=Path, default=Path('pipeline_cache'),
                    help='Cache dir for candidate JSONs (default: pipeline_cache/)')
    ap.add_argument('--fps', type=float, default=None,
                    help='Override sample FPS (default: adaptive by duration)')
    ap.add_argument('--fps-per-min', type=float, default=10.0,
                    help='Frames-per-minute target for annotation (default: 10)')
    ap.add_argument('--max-output', type=int, default=500,
                    help='Hard cap on frames selected per video (default: 500)')
    ap.add_argument('--scale', type=float, default=0.5,
                    help='Save images at this scale (default: 0.5 = 960px wide for 1080p)')
    ap.add_argument('--no-cache', action='store_true',
                    help='Ignore existing candidate cache')
    ap.add_argument('--debug-frames', type=int, default=None,
                    help='Only scan first N sampled frames (debug)')
    args = ap.parse_args()

    video_dir = Path('videos')
    if args.video:
        videos = [args.video]
    else:
        videos = sorted(video_dir.glob('*.mp4'))

    if not videos:
        print('No videos found.')
        return

    cfg = Config(
        sample_fps_override=args.fps,
        frames_per_minute=args.fps_per_min,
        max_output=args.max_output,
        max_frames_debug=args.debug_frames,
    )

    cache_dir = None if args.no_cache else args.cache_dir

    for vpath in videos:
        color = args.color or parse_color(vpath.name)
        run_pipeline(
            video_paths=[vpath],
            target_color=color,
            cfg=cfg,
            out_dir=args.out_dir,
            cache_dir=cache_dir,
            save_frames=True,
            display_scale=args.scale,
        )

    print(f'\nAll done. Output → {args.out_dir}/')


if __name__ == '__main__':
    main()
