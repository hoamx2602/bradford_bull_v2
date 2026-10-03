"""Render saved inference with collision-aware labels; no model predictions change."""
from pathlib import Path
from collections import defaultdict
import json, cv2, subprocess, imageio_ffmpeg, sys
ROOT=Path(__file__).resolve().parents[2]; OUT=ROOT/'artifacts/bradford_showcase'
sys.path.insert(0,str(ROOT/'backend'))
from app.pipeline.colors import brand_bgr
meta=json.loads((OUT/'showcase_manifest.json').read_text()); rows=defaultdict(list)
for r in json.loads((OUT/'showcase_detections.json').read_text()):rows[r['output_frame']].append(r)
cap=cv2.VideoCapture(meta['source']); fps=meta['fps']; w,h=meta['size']; count=0
writers={k:cv2.VideoWriter(str(OUT/f'{k}_labels.mp4'),cv2.VideoWriter_fourcc(*'mp4v'),fps,(w,h)) for k in ['logo_showcase_90s','team_showcase_90s']}
def draw(im,ds,team):
    used=[]
    for d in ds:
        state=d['team_state']
        if team and state not in ['target','uncertain']:continue
        col=brand_bgr(d['brand_key'])
        x1,y1,x2,y2=map(int,d['xyxy']);cv2.rectangle(im,(x1,y1),(x2,y2),col,2)
        suffix=(' [BRA]' if state=='target' else ' [?]') if team else ''
        label=f"{d['brand_name']} {d['conf']:.2f}{suffix}"; (tw,th),_=cv2.getTextSize(label,cv2.FONT_HERSHEY_SIMPLEX,.55,1)
        xx=max(2,min(x1,w-tw-10)); yy=max(th+7,y1-5)
        for attempt in range(30):
            rect=(xx-2,yy-th-4,xx+tw+5,yy+4)
            if not any(rect[0]<b[2] and rect[2]>b[0] and rect[1]<b[3] and rect[3]>b[1] for b in used):break
            yy=yy-(th+11) if yy>th*2+22 else min(h-55,y2+th+12+attempt*(th+11))
        used.append(rect)
        if abs(yy-(y1-5))>10:cv2.line(im,(xx,yy+4),(x1,y1),col,1)
        cv2.rectangle(im,rect[:2],rect[2:],(15,19,23),-1);cv2.putText(im,label,(xx,yy),cv2.FONT_HERSHEY_SIMPLEX,.55,col,1,cv2.LINE_AA)
for ci,(start,end) in enumerate(meta['segments']):
    cap.set(cv2.CAP_PROP_POS_FRAMES,round(start*fps))
    for j in range(round((end-start)*fps)):
        ok,frame=cap.read();assert ok
        ds=rows[count];t=start+j/fps
        for key,wr in writers.items():
            team=key.startswith('team');im=frame.copy();draw(im,ds,team)
            cv2.rectangle(im,(0,h-43),(w,h),(18,22,28),-1)
            caption=f"TEAM VIEW | BRA: Bradford ({sum(d['team_state']=='target' for d in ds)}) | ?: uncertain ({sum(d['team_state']=='uncertain' for d in ds)}) | Colour = brand" if team else f'LOGO DETECTION | {len(ds)} detections | Colour = brand'
            caption+=f' | Selected sequence {ci+1}/7 | Source {int(t)//60:02d}:{t%60:05.2f}'
            cv2.putText(im,caption,(24,h-15),cv2.FONT_HERSHEY_SIMPLEX,.65,(255,255,255),1,cv2.LINE_AA);wr.write(im)
        count+=1
    print('Rendered segment',ci+1,flush=True)
cap.release()
for wr in writers.values():wr.release()
for key in writers:
    tmp=OUT/f'{key}_labels.mp4'
    subprocess.run([imageio_ffmpeg.get_ffmpeg_exe(),'-y','-loglevel','error','-i',str(tmp),'-c:v','libx264','-preset','fast','-crf','17','-pix_fmt','yuv420p','-movflags','+faststart',str(OUT/f'{key}.mp4')],check=True)
    tmp.unlink()
print('DONE',count,flush=True)
