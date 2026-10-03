# Bradford Bulls — difficult-condition examples

Deliverables: nine curated examples (eight presentation panels with separate annotated frames and raw crops, plus one multi-player frame), and two silent 90-second 1080p/25fps H.264 videos with/without team split.

Source: M08_white_1080p.mp4, local upload c775d9975e3047a19eca8268a5825f3f.mp4. Videos concatenate source intervals 00:12–00:20, 02:12–02:20, 03:38–03:58, 04:26–04:50, 05:44–05:54, 07:10–07:20 and 09:08–09:18. Source timestamps are burned into the videos. These are edited highlights, not 90 consecutive seconds of a match. Output 00:52 corresponds to source 04:42 (dense multi-player view).

All boxes originate from code-run inference with runs/yolo26/matchsplit_896_m/weights/best.pt, inference size 1280. Still scan confidence threshold 0.35; video threshold 0.40. No synthetic blur, restored lettering, or AI-generated analytical images. Crops are enlarged for viewing. Box colour identifies the sponsor. BRA means predicted Bradford; ? means uncertain. The current team output was replayed with a vote consensus margin gate; see team_audit/REVIEW.md. Errors and missed detections can remain.

Image selections illustrate partial occlusion by players/arms/a foreground head, source blur, fabric folds and oblique chest views. They are qualitative examples, not independent ground truth or a robustness benchmark. Confidence is not measured accuracy or percent occlusion. The multi-player still includes ten selected predictions; an obvious false positive over a player name was excluded. scan.json preserves all original scan predictions. Static scan's detection.target is a rough shirt-color heuristic, not a verified team label; use the video team_state for temporal pipeline output.

Reproduction from repository root with the GPU environment:
1. .venv-rfdetr/Scripts/python.exe backend/scripts/scan_showcase.py
2. .venv-rfdetr/Scripts/python.exe backend/scripts/build_showcase_images.py
3. .venv-rfdetr/Scripts/python.exe backend/scripts/render_showcase.py
4. .venv-rfdetr/Scripts/python.exe backend/scripts/audit_showcase_teams.py
5. .venv-rfdetr/Scripts/python.exe backend/scripts/repaint_showcase.py
6. .venv-rfdetr/Scripts/python.exe backend/scripts/package_showcase.py

Open index.html to browse. Evidence and manifests retain exact source times, coordinates and confidence. Video counts are repeated detections across frames, not unique logos.
