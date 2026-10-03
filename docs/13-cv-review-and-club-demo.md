# CV review and Bradford Bulls presentation

## Changes

- Uploads with automatic references enabled now build references from the current video. An old global away-kit pickle no longer silently overrides a home match. Explicit upload references still take priority; disable automatic references to use the global file.
- Team tracking advances on every sampled frame, including frames without detected logos. New trackers reset the cached person model's tracking state.
- Tracks without evidence have an explicit `unknown` label. The configured unknown policy applies to both tentative TARGET and OTHER labels.
- Colour-distribution and pixel-change checks reset tracks and votes at broadcast cuts. Votes decay to reduce historical inertia after identity changes; cut detection remains heuristic.
- Logo ownership outside a person box uses a small edge tolerance instead of a 1.2-diagonal search that could include advertising boards.
- Kit anchors are already torso crops and are no longer cropped a second time. Saturated red/yellow fabric is preserved by the skin filter. Saturation joins luminance and hue in new colour references; legacy 20-element references remain readable.
- Reference clustering uses colour, a kit-lightness prior, and reduced semantic influence. For the currently configured white/red/yellow Bradford home kit, central-shirt chromatic evidence takes precedence over generic clustering: cyan/purple or green observations vote OTHER, supported neutral/warm observations vote TARGET, ambiguous observations abstain. This is kit-specific and must be reviewed when the kit changes; it is not a universal team model. Existing explicit references without kit metadata use the general classifier.
- Body masks match pose skeletons one-to-one. Missing hips no longer produce a made-up vertical torso during tackles. Missing/unsupported regions are grey (`Unassigned`), and overlapping masks do not double-count pixels.
- Fixed missing model/device initialisation and tracker reset in the YOLO logo adapter.

## Reproduction

From the repository root, using the CUDA environment:

```powershell
& .venv-rfdetr/Scripts/python.exe backend/scripts/build_club_demo.py
& .venv-rfdetr/Scripts/python.exe backend/scripts/refresh_team_demo.py
& .venv-app/Scripts/python.exe backend/scripts/export_club_evidence.py
& .venv-rfdetr/Scripts/python.exe backend/scripts/prepare_club_slides.py
$env:PYTHONPATH = 'D:/bradford_bull_v2/backend'
& .venv-rfdetr/Scripts/python.exe -m pytest backend/tests/test_teamid.py backend/tests/test_cv_regressions.py backend/tests/test_bodyzones.py backend/tests/test_visibility.py -q
```

The demo runs native-frame inference on two excerpts (18–28 s and 84–96 s) of the existing `M08_white_1080p.mp4` upload. Output is 1280×720, 25 fps, H.264. Both filtered/unfiltered videos reuse identical logo detections. The export uses the explicit matchsplit YOLO26m checkpoint and YOLO11x segmentation/pose models; it does not change global model settings or overwrite the database.

`artifacts/bradford_review/manifest.json` and `*_detections.json` contain source offsets, model identity, per-frame detections and counts. `stored_evidence.json` is a read-only snapshot of historical analyses. The presentation builder is `artifacts/bradford_review/build/build_deck.mjs` and uses the bundled Node artifact runtime.

## Interpretation

Detection-instance counts are not unique sponsor counts or accuracy. Body-region pixel coverage is not sponsor exposure. The heatmap is camera/screen space, not player positions on the pitch. Confidence is a clarity proxy; the scoring pipeline has no independent occlusion measurement.

The deck compares historical Match 1/2 AI shares with configured human weights, normalised from a total of 95. Those weights are not verified contract prices or manually labelled truth. Full matches have not been reprocessed after these changes. Validation precision/recall/mAP in the deck come from the existing training log, not a new team/segmentation evaluation.

Rugby contact, overlapping people, cropped bodies, colour changes and camera cuts still need review. No quantified accuracy improvement is claimed without a labelled evaluation set. Body boundaries are pose-guided estimates, not a trained fine-grained rugby body parser. Manual overrides remain useful where the kit or opponent invalidates the colour assumptions.
