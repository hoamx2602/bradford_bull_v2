"""Build a portable gallery and validate the actual rendered showcase videos."""
from pathlib import Path
import json, html, zipfile
import cv2
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'artifacts/bradford_showcase'
evidence = json.loads((OUT / 'image_evidence.json').read_text(encoding='utf-8'))
cards = []
for item in evidence:
    links = ' · '.join(f'<a href="{item[k]}" download>{label}</a>' for k, label in [('file','Ảnh cho slide'),('frame','Toàn cảnh'),('crop','Crop gốc')] if k in item)
    t = item['source_time']
    cards.append(f'<article><a href="{item["file"]}"><img loading="lazy" src="{item["file"]}" alt="{html.escape(item["title"])}"></a><h3>{html.escape(item["title"])}</h3><p>{html.escape(item["description_vi"])}</p><small>Nguồn {t//60:02d}:{t%60:02d}</small><p>{links}</p></article>')
page = '''<!doctype html><html lang="vi"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Bradford Bulls · Detection under difficult conditions</title><style>body{margin:0;background:#111720;color:#edf1f5;font:17px/1.6 system-ui}main{max-width:1500px;margin:auto;padding:40px}h1{font-size:44px;line-height:1.15}h2{margin-top:48px}h3{font-size:20px}a{color:#ffe14d}header{max-width:1080px}.grid{display:grid;grid-template-columns:1fr 1fr;gap:24px}article{background:#1b2430;padding:20px;border-radius:12px}video,img{width:100%;height:auto}small{color:#b5c0cc}.note{border-left:4px solid #ffe14d;padding:16px 24px;background:#1b2430}button{background:#ffe14d;color:#111;padding:10px 18px;border:0;border-radius:5px;cursor:pointer;font-weight:bold}@media(max-width:850px){.grid{grid-template-columns:1fr}main{padding:20px}h1{font-size:32px}}</style><main><header><p>BRADFORD BULLS · REAL FOOTAGE / REAL INFERENCE</p><h1>Logo detection khi bị che khuất, nhòe và biến dạng</h1><p>9 ví dụ chọn lọc từ video trận đấu, kèm ảnh toàn cảnh và crop để sử dụng trong presentation. Các khung detection xuất phát từ model chạy trên footage thật; không tạo logo, che khuất hay làm mờ bằng AI.</p><p><a href="Bradford_Bulls_Challenge_Examples.zip" download>Tải trọn bộ ảnh + video</a> · <a href="README.md">Hướng dẫn và nguồn dữ liệu</a></p></header><h2>Video tuyển chọn · 90 giây · Full HD</h2><p>7 đoạn ghép theo thứ tự thời gian, 1920 × 1080, 25 fps, không âm thanh. Có cả cảnh chuyển tiếp và cảnh rộng của footage. Đoạn đông cầu thủ, nhiều logo nằm khoảng giây 40–60; cảnh nguồn 04:42 tương ứng giây 52.</p><div class="grid"><article><h3>Logo detection · Không team split</h3><video id="plain" controls preload="metadata" poster="images/09_multiple_players.png" src="logo_showcase_90s.mp4"></video><p><button onclick="document.getElementById('plain').currentTime=48;document.getElementById('plain').play()">Xem cảnh nhiều logo</button></p><a href="logo_showcase_90s.mp4" download>Tải MP4</a></article><article><h3>Logo detection · Có team split</h3><video id="team" controls preload="metadata" poster="team_preview.jpg" src="team_showcase_90s.mp4"></video><p>Xanh: model xác định Bradford. Vàng: chưa đủ bằng chứng phân đội.</p><a href="team_showcase_90s.mp4" download>Tải MP4</a></article></div><h2>Ảnh minh họa để đưa vào slide</h2><div class="grid">''' + ''.join(cards) + '''</div><h2>Cách diễn giải kết quả</h2><div class="note">Đây là các ví dụ định tính được chọn sau khi xem ảnh. Confidence là độ tin cậy của dự đoán, không phải độ chính xác đo trên tập kiểm thử hoặc tỷ lệ logo bị che. Ảnh số 09 chọn 10 detection và loại một dự đoán sai rõ ràng; video giữ các dự đoán theo ngưỡng model. Bộ ảnh quét dùng ngưỡng 0.35; video dùng 0.40. Trường hợp ASC Group bị cánh tay che có confidence khoảng 0.40.</div><p><a href="image_evidence.json">Nguồn từng ảnh</a> · <a href="showcase_manifest.json">Cấu hình video</a> · <a href="showcase_detections.json">Detection theo frame</a> · <a href="scan.json">Toàn bộ kết quả quét ảnh</a></p></main></html>'''
page=page.replace('Xanh: model xác định Bradford. Vàng: chưa đủ bằng chứng phân đội.', 'Màu khung cố định theo thương hiệu logo. Nhãn BRA: model xác định Bradford; ?: chưa đủ bằng chứng phân đội.')
page=page.replace('<h2>Cách diễn giải kết quả</h2>', '<h2>Kiểm tra team split</h2><p><a href="team_audit/REVIEW.md">Đánh giá kỹ thuật, tham số và hạn chế</a> · <a href="team_audit/audit.json">Kết quả chạy kiểm tra</a></p><h2>Cách diễn giải kết quả</h2>')
page=page.replace('<h2>Cách diễn giải kết quả</h2>', '<details><summary>Ảnh chẩn đoán đội: cảnh tách người và cảnh chồng lấn</summary><p>Trong ảnh chẩn đoán người: vàng = Target; xám = Other; xanh = chưa chắc chắn. Trong video logo, màu thể hiện sponsor.</p><div class="grid"><img src="team_audit/frame_0175.jpg" alt="Cảnh người tách nhau"><img src="team_audit/frame_1300.jpg" alt="Cảnh người chồng lấn"></div></details><h2>Cách diễn giải kết quả</h2>')
(OUT/'index.html').write_text(page, encoding='utf-8')
(OUT/'README.md').write_text('''# Bradford Bulls — difficult-condition examples

Deliverables: nine curated examples (eight presentation panels with separate annotated frames and raw crops, plus one multi-player frame), and two silent 90-second 1080p/25fps H.264 videos with/without team split.

Source: M08_white_1080p.mp4, local upload c775d9975e3047a19eca8268a5825f3f.mp4. Videos concatenate source intervals 00:12–00:20, 02:12–02:20, 03:38–03:58, 04:26–04:50, 05:44–05:54, 07:10–07:20 and 09:08–09:18. Source timestamps are burned into the videos. These are edited highlights, not 90 consecutive seconds of a match. Output 00:52 corresponds to source 04:42 (dense multi-player view).

All boxes originate from code-run inference with runs/yolo26/matchsplit_896_m/weights/best.pt, inference size 1280. Still scan confidence threshold 0.35; video threshold 0.40. No synthetic blur, restored lettering, or AI-generated analytical images. Crops are enlarged for viewing. Green in team video means predicted Bradford; amber means uncertain. Errors and missed detections can remain.

Image selections illustrate partial occlusion by players/arms/a foreground head, source blur, fabric folds and oblique chest views. They are qualitative examples, not independent ground truth or a robustness benchmark. Confidence is not measured accuracy or percent occlusion. The multi-player still includes ten selected predictions; an obvious false positive over a player name was excluded. scan.json preserves all original scan predictions. Static scan's detection.target is a rough shirt-color heuristic, not a verified team label; use the video team_state for temporal pipeline output.

Reproduction from repository root (python = .venv-rfdetr/Scripts/python.exe on Windows/CUDA, .venv/bin/python on macOS). Compute device toggle: DEVICE=auto|cuda|0|mps|cpu (default auto = CUDA > Apple MPS > CPU):
1. python backend/scripts/scan_showcase.py
2. python backend/scripts/build_showcase_images.py
3. python backend/scripts/render_showcase.py
4. python backend/scripts/audit_showcase_teams.py
5. python backend/scripts/repaint_showcase.py
6. python backend/scripts/package_showcase.py

Open index.html to browse. Evidence and manifests retain exact source times, coordinates and confidence. Video counts are repeated detections across frames, not unique logos.
''', encoding='utf-8')
readme=(OUT/'README.md').read_text(encoding='utf-8').replace('Green in team video means predicted Bradford; amber means uncertain.', 'Box colour identifies the sponsor. BRA means predicted Bradford; ? means uncertain. The current team output was replayed with a vote consensus margin gate; see team_audit/REVIEW.md.')
(OUT/'README.md').write_text(readme,encoding='utf-8')
qa = {}
for name in ['logo_showcase_90s', 'team_showcase_90s']:
    cap = cv2.VideoCapture(str(OUT/f'{name}.mp4'))
    fps = cap.get(cv2.CAP_PROP_FPS); frames = 0
    while True:
        ok, frame = cap.read()
        if not ok: break
        assert frame.shape[:2] == (1080,1920)
        if frames == 1300:
            cv2.imwrite(str(OUT/('team_preview.jpg' if name.startswith('team') else 'logo_preview.jpg')),frame)
        frames += 1
    cap.release()
    assert frames == 2250 and fps == 25, (name, frames, fps)
    qa[name] = {'decoded_frames':frames, 'fps':fps,'size':[1920,1080],'duration':frames/fps}
(OUT/'validation.json').write_text(json.dumps(qa,indent=2))
sheet = Image.new('RGB',(1440,810),'#111720')
for i,item in enumerate(evidence):
    im = Image.open(OUT/item['file']); im.thumbnail((480,270));sheet.paste(im,((i%3)*480,(i//3)*270))
sheet.save(OUT/'image_review.jpg')
old = ROOT/'artifacts/bradford_review/index.html'
content = old.read_text(encoding='utf-8')
if '../bradford_showcase/index.html' not in content:
    content = content.replace('</header>','<p><a href="../bradford_showcase/index.html"><strong>MỚI: 9 ví dụ che khuất / nhòe + hai video 90 giây Full HD</strong></a></p></header>',1)
    old.write_text(content,encoding='utf-8')
files = list((OUT/'images').glob('*.png')) + [OUT/n for n in ['index.html','README.md','image_evidence.json','scan.json','showcase_manifest.json','showcase_detections.json','validation.json','logo_preview.jpg','team_preview.jpg','logo_showcase_90s.mp4','team_showcase_90s.mp4']]
files += [p for p in (OUT/'team_audit').glob('*') if p.suffix in ['.md','.json','.jpg']]
with zipfile.ZipFile(OUT/'Bradford_Bulls_Challenge_Examples.zip','w',zipfile.ZIP_DEFLATED,compresslevel=1) as z:
    for p in files:z.write(p,p.relative_to(OUT))
print(json.dumps(qa));print('Packaged',len(files),'files')
