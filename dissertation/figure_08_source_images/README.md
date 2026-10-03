# Figure 8 source-image components

This folder contains the four independent image sets used to assemble Figure 8.

## File variants

- `*_source_full.jpg`: untouched full-resolution frame copied from the held-out dataset.
- `*_source_boxed.png`: full-resolution frame with only the target ground-truth box.
- `*_logo_crop_clean.png`: clean contextual crop around the target logo, without a box or label.
- `*_panel_complete.png`: exact A, B, C or D panel cropped from the final composite, including its header and magnified inset.

## Cases

| Panel | Condition | Brand | Detector outcome | Confidence | Ground-truth box `[x, y, width, height]` |
| --- | --- | --- | --- | ---: | --- |
| A | Clear | Top Notch | Detected | 0.915 | `[975.16, 246.59, 97.16, 56.20]` |
| B | Partially occluded | Aon | Detected | 0.780 | `[1322.26, 1050.06, 63.13, 55.31]` |
| C | Partially occluded | Aon | Missed | — | `[1133.15, 914.07, 58.44, 57.47]` |
| D | Heavily occluded | Fairway | Detected | 0.351 | `[1416.31, 609.46, 67.80, 50.06]` |

The solid boxes in A, B and D identify matched ground truth. The dashed box in C identifies missed ground truth. The source frames preserve their original dimensions: A and D are 1920 × 1080; B and C are 2560 × 1440.

The export can be reproduced with `dissertation/export_figure08_source_images_v17.py`.
