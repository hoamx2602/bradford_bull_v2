"""Native-resolution, actual-inference 90-second presentation highlights."""
from build_club_demo import ROOT, DEVICE  # DEVICE toggle: auto|cuda|0|mps|cpu
import cv2,json,numpy as np,pickle,subprocess
from dataclasses import asdict
from ultralytics import YOLO
from app.pipeline.teamid.tracker import TeamTracker,assign_owner
from app.pipeline.datatypes import Detection
from app.config import normalize_class,display_name
from app.pipeline.av import _ffmpeg_exe
from app.pipeline.colors import brand_bgr
OUT=ROOT/'artifacts/bradford_showcase'
SRC=ROOT/'backend/data/uploads/c775d9975e3047a19eca8268a5825f3f.mp4'
SEGMENTS=[(12,20),(132,140),(218,238),(266,290),(344,354),(430,440),(548,558)]
refs=pickle.load((ROOT/'backend/data/auto_refs/c775d9975e3047a19eca8268a5825f3f-home.pkl').open('rb'))
model=YOLO(str(ROOT/'runs/yolo26/matchsplit_896_m/weights/best.pt'))
cap=cv2.VideoCapture(str(SRC));fps=cap.get(5);w,h=int(cap.get(3)),int(cap.get(4))
writers={k:cv2.VideoWriter(str(OUT/f'{k}_working.mp4'),cv2.VideoWriter_fourcc(*'mp4v'),fps,(w,h)) for k in ['logo_showcase_90s','team_showcase_90s']}
records=[];output_frame=0;manifest={'source':str(SRC),'source_name':'M08_white_1080p.mp4','segments':SEGMENTS,'fps':fps,'size':[w,h],'imgsz':1280,'confidence_threshold':.4,'model':str(ROOT/'runs/yolo26/matchsplit_896_m/weights/best.pt'),'description':'Edited highlight reel in chronological order; source timestamps shown. Silent for presentation use. No artificial blur, restoration, generated logos or bounding boxes.'}
def iou(a,b):
    inter=max(0,min(a[2],b[2])-max(a[0],b[0]))*max(0,min(a[3],b[3])-max(a[1],b[1]));return inter/((a[2]-a[0])*(a[3]-a[1])+(b[2]-b[0])*(b[3]-b[1])-inter+1e-8)
def draw(im,d,col,suffix=''):
    col=brand_bgr(d.brand_key)
    x1,y1,x2,y2=map(int,d.xyxy);cv2.rectangle(im,(x1,y1),(x2,y2),col,2)
    label=f'{d.brand_name} {d.conf:.2f}{suffix}';(tw,th),_=cv2.getTextSize(label,cv2.FONT_HERSHEY_SIMPLEX,.55,1)
    xx=max(2,min(x1,w-tw-10));yy=max(th+7,y1-5)
    cv2.rectangle(im,(xx-2,yy-th-4),(xx+tw+5,yy+4),(15,19,23),-1)
    cv2.putText(im,label,(xx,yy),cv2.FONT_HERSHEY_SIMPLEX,.55,col,1,cv2.LINE_AA)
for ci,(start,end) in enumerate(SEGMENTS):
    tracker=TeamTracker(refs=refs);cap.set(cv2.CAP_PROP_POS_FRAMES,round(start*fps))
    for j in range(round((end-start)*fps)):
        ok,frame=cap.read()
        if not ok:raise RuntimeError('Unexpected EOF')
        source_t=start+j/fps
        result=model.predict(frame,imgsz=1280,conf=.4,device=DEVICE,verbose=False)[0]
        dets=[]
        for box,cf,cls in zip(result.boxes.xyxy.cpu().numpy(),result.boxes.conf.cpu().numpy(),result.boxes.cls.cpu().numpy()):
            raw=model.names[int(cls)]
            if any(d.class_id==int(cls) and iou(d.xyxy,box)>.6 for d in dets):continue
            dets.append(Detection(t=source_t,class_id=int(cls),raw_name=raw,brand_key=normalize_class(raw),brand_name=display_name(raw),conf=float(cf),xyxy=tuple(map(float,box)),track_id=-1,frame_w=w,frame_h=h))
        people=tracker.process(frame);tracker.annotate(dets,people)
        plain=frame.copy();team=frame.copy();kept=0;uncertain=0
        for d in dets:
            owner=assign_owner(d,people);state='unassigned' if owner is None else ('uncertain' if owner.team=='unknown' or owner.vote_mass<tracker.settings.team_min_votes else owner.team)
            draw(plain,d,(70,255,210))
            if state=='target':draw(team,d,(70,255,210),' [BRA]');kept+=1
            elif state=='uncertain':draw(team,d,(0,190,255),' [?]');uncertain+=1
            records.append({'output_frame':output_frame,'segment':ci,'source_time':source_t,'team_state':state,**asdict(d)})
        for key,img in [('logo_showcase_90s',plain),('team_showcase_90s',team)]:
            cv2.rectangle(img,(0,h-43),(w,h),(18,22,28),-1)
            caption=(f'LOGO DETECTION | {len(dets)} detections | Colour = brand' if key.startswith('logo') else f'TEAM VIEW | BRA: Bradford ({kept}) | ?: uncertain ({uncertain}) | Colour = brand')
            caption+=f'   |   Selected sequence {ci+1}/{len(SEGMENTS)}   |   Source {int(source_t)//60:02d}:{source_t%60:05.2f}'
            cv2.putText(img,caption,(24,h-15),cv2.FONT_HERSHEY_SIMPLEX,.65,(255,255,255),1,cv2.LINE_AA)
            writers[key].write(img)
        output_frame+=1
        if j%125==0:print('segment',ci+1,'frame',j,'logos',len(dets),'confirmed',kept,flush=True)
    (OUT/'showcase_detections.json').write_text(json.dumps(records))
for wr in writers.values():wr.release()
cap.release()
for key in writers:
    tmp=OUT/f'{key}_working.mp4';dest=OUT/f'{key}.mp4'
    subprocess.run([_ffmpeg_exe(),'-y','-loglevel','error','-i',str(tmp),'-c:v','libx264','-preset','fast','-crf','17','-pix_fmt','yuv420p','-movflags','+faststart',str(dest)],check=True)
    tmp.unlink()
manifest.update(frames=output_frame,duration=output_frame/fps,detection_instances=len(records),confirmed_target_instances=sum(r['team_state']=='target' for r in records),uncertain_instances=sum(r['team_state']=='uncertain' for r in records))
(OUT/'showcase_manifest.json').write_text(json.dumps(manifest,indent=2))
print('DONE',manifest,flush=True)
