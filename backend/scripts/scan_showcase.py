"""Scan actual footage for clear multi-player logo demonstrations."""
from build_club_demo import ROOT, DEVICE  # DEVICE toggle: auto|cuda|0|mps|cpu
import cv2,json,numpy as np
from ultralytics import YOLO
from PIL import Image,ImageDraw
from app.pipeline.teamid.jersey import get_jersey_region,bradford_home_evidence
OUT=ROOT/'artifacts/bradford_showcase';OUT.mkdir(parents=True,exist_ok=True)
SRC=ROOT/'backend/data/uploads/c775d9975e3047a19eca8268a5825f3f.mp4'
logo=YOLO(str(ROOT/'runs/yolo26/matchsplit_896_m/weights/best.pt'))
person=YOLO(str(ROOT/'yolo11m.pt'))
cap=cv2.VideoCapture(str(SRC)); duration=cap.get(7)/cap.get(5); rows=[]
for t in np.arange(12,duration-2,2):
    cap.set(cv2.CAP_PROP_POS_MSEC,float(t)*1000);ok,im=cap.read()
    if not ok:continue
    lr=logo.predict(im,imgsz=1280,conf=.35,device=DEVICE,verbose=False)[0]
    pr=person.predict(im,imgsz=960,conf=.4,classes=[0],device=DEVICE,verbose=False)[0]
    people=[]
    for b in pr.boxes.xyxy.cpu().numpy():
        crop,_=get_jersey_region(im,b);people.append({'box':b.tolist(),'team':bradford_home_evidence(crop)})
    dets=[]; owners=set()
    for b,conf,cls in zip(lr.boxes.xyxy.cpu().numpy(),lr.boxes.conf.cpu().numpy(),lr.boxes.cls.cpu().numpy()):
        cx,cy=(b[0]+b[2])/2,(b[1]+b[3])/2
        inside=[(i,p) for i,p in enumerate(people) if p['box'][0]<=cx<=p['box'][2] and p['box'][1]<=cy<=p['box'][3]]
        owner=min(inside,key=lambda ip:(ip[1]['box'][2]-ip[1]['box'][0])*(ip[1]['box'][3]-ip[1]['box'][1])) if inside else None
        target=owner is not None and owner[1]['team']=='target'
        if target:owners.add(owner[0])
        x1,y1,x2,y2=map(int,b);crop=im[max(y1,0):y2,max(x1,0):x2]
        sharp=float(cv2.Laplacian(cv2.cvtColor(crop,cv2.COLOR_BGR2GRAY),cv2.CV_64F).var()) if crop.size else 0
        dets.append({'box':b.tolist(),'conf':float(conf),'class':int(cls),'name':logo.names[int(cls)],'target':target,'sharpness':sharp})
    score=sum(d['conf']*min(2,((d['box'][2]-d['box'][0])*(d['box'][3]-d['box'][1]))/1200) for d in dets if d['target'])+len(owners)*1.5
    row={'t':float(t),'score':score,'target_players_with_logos':len(owners),'detections':dets,'people':people};rows.append(row)
    if len(dets)>=3:cv2.imwrite(str(OUT/f'scan_{int(t):04d}.jpg'),im)
    if len(rows)%40==0:print('scan',int(t),'seconds',flush=True)
cap.release();(OUT/'scan.json').write_text(json.dumps(rows,indent=2))
ranked=sorted(rows,key=lambda r:r['score'],reverse=True)[:72]
for start in range(0,len(ranked),24):
    sheet=Image.new('RGB',(1440,4*228),'#151920');dr=ImageDraw.Draw(sheet)
    for j,r in enumerate(ranked[start:start+24]):
        im=cv2.imread(str(OUT/f"scan_{int(r['t']):04d}.jpg"))
        if im is None:continue
        for d in r['detections']:
            x1,y1,x2,y2=map(int,d['box']);cv2.rectangle(im,(x1,y1),(x2,y2),(0,255,255) if d['target'] else (140,140,140),2)
        thumb=Image.fromarray(cv2.cvtColor(im,cv2.COLOR_BGR2RGB));thumb.thumbnail((360,202))
        x=j%4*360;y=j//4*152
        thumb.thumbnail((360,125));sheet.paste(thumb,(x,y));dr.text((x+8,y+127),f"t={r['t']:.0f}s  score={r['score']:.1f}  players={r['target_players_with_logos']}  logos={len(r['detections'])}",fill='white')
    sheet.save(OUT/f'contact_{start//24}.jpg')
windows=[]
for t in range(12,int(duration)-60,2):
    rr=[r for r in rows if t<=r['t']<t+60]
    windows.append((sum(r['score'] for r in rr),t))
print('BEST WINDOWS',sorted(windows,reverse=True)[:10])
