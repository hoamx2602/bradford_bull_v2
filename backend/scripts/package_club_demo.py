"""Verify the six exports and build a portable review gallery and ZIP."""
from pathlib import Path
import json,zipfile,html,cv2,subprocess,sys
ROOT=Path(__file__).resolve().parents[2]; OUT=ROOT/'artifacts/bradford_review'
sys.path.insert(0,str(ROOT/'backend'))
from app.pipeline.av import _ffmpeg_exe,_probe
m=json.loads((OUT/'manifest.json').read_text())
checks=[]; blocks=[]
for c in m['clips']:
    name=c['name']
    cards=[]
    for kind,label in [('no_split','Logo detection — không team split'),('team_split','Logo detection + team split'),('body','Body segmentation')]:
        f=OUT/f'{name}_{kind}.mp4'; probe=_probe(f,_ffmpeg_exe()); assert 'Video: h264' in probe
        cap=cv2.VideoCapture(str(f)); n=0
        while True:
            ok,frame=cap.read()
            if not ok:break
            n+=1
        fps=cap.get(5);cap.release(); assert n==c['frames'],(f,n,c['frames'])
        checks.append({'file':f.name,'decoded_frames':n,'fps':fps,'codec':'H.264'})
        cards.append(f'<article><h3>{label}</h3><video controls preload="metadata" src="{f.name}"></video><p><a download href="{f.name}">Tải MP4</a></p></article>')
    blocks.append(f'<section><h2>{name.title()} · {c["start"]}–{c["start"]+c["duration"]} giây nguồn</h2><p>{c["all_logo_detections"]} lượt detection; giữ {c["retained_logo_detections"]} sau lọc đội. Các lượt lặp lại theo frame, không phải logo duy nhất.</p><div class="grid">'+''.join(cards)+f'</div><details><summary>Heatmap và dữ liệu kiểm tra</summary><img src="{name}_heatmap.jpg"><p><a href="{name}_detections.json">Detection theo frame</a> · <a href="{name}_persons.json">Nhãn người theo frame</a></p></details></section>')
page='''<!doctype html><html lang="vi"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Bradford Bulls · Bộ demo</title><style>body{font:17px/1.6 system-ui;margin:0;background:#f5f6f8;color:#19202a}main{max-width:1450px;margin:auto;padding:45px}h1{font-size:44px;line-height:1.15}h2{margin-top:42px}h3{font-size:19px}a{color:#bd1832}.grid{display:grid;grid-template-columns:repeat(3,1fr);gap:22px}article{background:white;padding:18px}video,img{width:100%;height:auto}details img{max-width:900px}small{color:#626a77}section{margin:40px 0}header{max-width:1000px}.notice{background:#fff;padding:22px;border-radius:8px}@media(max-width:900px){.grid{grid-template-columns:1fr}main{padding:20px}}</style><main><header><h1>Bradford Bulls<br>Logo detection, team split & body segmentation</h1><p>Hình ảnh và video được xuất bằng code từ footage thật. Các bản có và không team split dùng cùng detection gốc để so sánh.</p><p><a href="presentation/Bradford_Bulls_Findings_Final.pptx">Presentation tiếng Anh · 16 slides</a> · <a href="manifest.json">Thông tin lần chạy</a> · <a href="HANDOVER.md">Ghi chú bàn giao</a></p></header><div class="notice"><strong>Phạm vi:</strong> hai đoạn demo tổng 22 giây, không phải phân tích lại toàn trận. Trạng thái chưa đủ bằng chứng và vùng segmentation màu xám được giữ rõ ràng. Vẫn có thể sai trong pha tackle hoặc che khuất. Các biểu đồ Match 1/2 trong slide dùng kết quả lịch sử, không phải kết quả chạy lại sau sửa.</div>'''+''.join(blocks)+'''<section><h2>Ảnh minh họa vị trí tài trợ</h2><div class="grid">'''+''.join(f'<article><h3>{x.title()}</h3><img src="{x}_evidence.jpg"></article>' for x in ['chest','back','sleeves','shorts'])+'''</div></section><p><small>Heatmap ở tọa độ màn hình, không phải tọa độ sân. Confidence là proxy cho độ rõ. Điểm Human trong slide là trọng số cấu hình, chưa phải bảng giá hợp đồng đã xác minh.</small></p></main></html>'''
(OUT/'index.html').write_text(page,encoding='utf-8')
(OUT/'video_validation.json').write_text(json.dumps(checks,indent=2))
selected=[OUT/'index.html',OUT/'HANDOVER.md',OUT/'manifest.json',OUT/'slide_data.json',OUT/'stored_evidence.json',OUT/'video_validation.json',OUT/'presentation/Bradford_Bulls_Findings_Final.pptx']
selected+=list(OUT.glob('*_evidence.jpg'))+list(OUT.glob('*_heatmap.jpg'))
for c in m['clips']:
    name=c['name'];selected+=[OUT/f'{name}_{k}.mp4' for k in ['no_split','team_split','body']]
    selected+=[OUT/f'{name}_{k}.json' for k in ['detections','persons']]
    selected+=list(OUT.glob(f'{name}_[0-9]*.jpg'))
with zipfile.ZipFile(OUT/'Bradford_Bulls_Media_Pack.zip','w',zipfile.ZIP_DEFLATED) as z:
    for f in selected:z.write(f,f.relative_to(OUT))
print(json.dumps(checks,indent=2))
