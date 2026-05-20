"""
Interactive frame labeling tool. Label frames as good/bad for ground-truth evaluation.

Usage:
    python eval/label_frames.py --frames-dir extracted_frames/ --output labels.csv

Keys:
    g      = good (logo visible and sharp)
    b      = bad  (blur, occluded, player too small)
    space  = skip
    q      = quit and save
"""
import argparse
import csv
from pathlib import Path

import cv2


def label_frames(frames_dir: Path, output_csv: Path, scale: float = 0.5) -> None:
    existing: dict[str, str] = {}
    if output_csv.exists():
        with open(output_csv) as f:
            for row in csv.DictReader(f):
                existing[row['filename']] = row['label']

    frames = sorted(frames_dir.rglob('*.jpg'))
    unlabeled = [f for f in frames if f.name not in existing]
    print(f'{len(frames)} total | {len(existing)} already labeled | {len(unlabeled)} remaining')
    print('Keys: g=good | b=bad | space=skip | q=quit\n')

    results = dict(existing)
    with open(output_csv, 'w', newline='') as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(['filename', 'path', 'label'])
        for name, label in existing.items():
            writer.writerow([name, '', label])

        for i, frame_path in enumerate(unlabeled):
            img = cv2.imread(str(frame_path))
            if img is None:
                continue
            h, w = img.shape[:2]
            small = cv2.resize(img, (int(w * scale), int(h * scale)))

            # burn filename into preview
            cv2.putText(small, f'{i+1}/{len(unlabeled)}  {frame_path.name}',
                        (10, 25), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (0, 255, 255), 1)
            cv2.imshow('[g]ood | [b]ad | [space]skip | [q]uit', small)
            key = cv2.waitKey(0) & 0xFF

            if key == ord('q'):
                break
            elif key == ord('g'):
                label = 'good'
            elif key == ord('b'):
                label = 'bad'
            else:
                continue  # skip

            writer.writerow([frame_path.name, str(frame_path), label])
            csvfile.flush()
            results[frame_path.name] = label
            print(f'  [{label:>4}] {frame_path.name}')

    cv2.destroyAllWindows()
    goods = sum(1 for v in results.values() if v == 'good')
    bads  = sum(1 for v in results.values() if v == 'bad')
    print(f'\nSaved → {output_csv}  ({goods} good, {bads} bad)')


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--frames-dir', type=Path, required=True,
                    help='Directory containing .jpg frames (searched recursively)')
    ap.add_argument('--output', type=Path, default=Path('labels.csv'))
    ap.add_argument('--scale', type=float, default=0.5,
                    help='Display scale factor (default 0.5 = half resolution)')
    args = ap.parse_args()
    label_frames(args.frames_dir, args.output, args.scale)
