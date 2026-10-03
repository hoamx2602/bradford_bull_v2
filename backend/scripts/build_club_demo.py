"""Reproducible paired exports from identical per-frame detections.

Run:  python backend/scripts/build_club_demo.py
  Windows/CUDA:  .venv-rfdetr/Scripts/python.exe backend/scripts/build_club_demo.py
  macOS (M-series):  .venv/bin/python backend/scripts/build_club_demo.py

Compute device is a toggle, not hard-coded: set DEVICE=auto|cuda|0|mps|cpu
(default auto = CUDA > Apple MPS > CPU). Every showcase/demo script that
imports from this module uses the same DEVICE value.
"""
from pathlib import Path
import os, sys, json, csv, logging, sqlite3
from dataclasses import asdict
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'backend'))
os.environ.setdefault('DEVICE', 'auto')  # toggle: auto | cuda | 0 | mps | cpu
os.environ.update(LOGO_BACKEND='yolo', DETECTOR_BACKEND='yolo',
    MODEL_PATH=str(ROOT/'runs/yolo26/matchsplit_896_m/weights/best.pt'),
    TEAM_PERSON_MODEL=str(ROOT/'yolo11m.pt'), POSE_MODEL=str(ROOT/'yolo11x-pose.pt'),
    IMGSZ='896', CONF='0.25', TEAM_BOOTSTRAP_FRAMES='48')
import cv2
import numpy as np
from ultralytics import YOLO
from app.pipeline.teamid.bootstrap import build_refs_from_video
from app.pipeline.teamid.tracker import TeamTracker, assign_owner
from app.pipeline.detect_track import LogoDetector
from app.pipeline.bodyseg_yolo import _segment_frame
from app.pipeline.teamdet_video import _draw
from app.pipeline.av import mux_audio, _ffmpeg_exe
from app.pipeline import visibility
import subprocess
from app.models_zoo.registry import resolve_device

DEVICE = resolve_device(os.environ['DEVICE'])
os.environ['DEVICE'] = DEVICE  # pipeline settings read the resolved value
DEVICE_LABEL = {'mps': 'Apple MPS', 'cpu': 'CPU'}.get(DEVICE, f'CUDA:{DEVICE}')
print(f'[build_club_demo] compute device: {DEVICE_LABEL}', flush=True)

OUT=ROOT/'artifacts/bradford_review'
OUT.mkdir(parents=True, exist_ok=True)
logging.basicConfig(level=logging.INFO)

def title(img, text):
    cv2.rectangle(img,(0,0),(img.shape[1],34),(22,22,28),-1)
    cv2.putText(img,text,(12,24),cv2.FONT_HERSHEY_SIMPLEX,.58,(255,255,255),1,cv2.LINE_AA)

def main():
    source=ROOT/'backend/data/uploads/c775d9975e3047a19eca8268a5825f3f.mp4'
    ffmpeg=_ffmpeg_exe()
    if not ffmpeg: raise RuntimeError('ffmpeg required for H.264 deliverables')
    seg=YOLO(str(ROOT/'backend/yolo11x-seg.pt'))
    pose=YOLO(str(ROOT/'yolo11x-pose.pt'))
    refs=build_refs_from_video(source,'home')
    if refs is None: raise RuntimeError('Cannot establish team references')
    manifest={'source':str(source),'source_name':'M08_white_1080p.mp4',
        'kit':'home','model':os.environ['MODEL_PATH'],'device':DEVICE_LABEL,
        'team_reference_meta':refs['meta'], 'clips':[],
        'scope':'Demonstration clips; not full-match measurement or a labelled accuracy benchmark.'}
    for name,start,duration in [('wide',18,10),('tackle',84,12)]:
        raw=OUT/f'{name}_source.mp4'
        subprocess.run([ffmpeg,'-y','-loglevel','error','-ss',str(start),'-i',str(source),
            '-t',str(duration),'-c:v','libx264','-crf','18','-an',str(raw)],check=True)
        cap=cv2.VideoCapture(str(raw)); fps=cap.get(cv2.CAP_PROP_FPS)
        tracker=TeamTracker(refs=refs); detector=LogoDetector()
        size=(1280,720)
        paths={k:OUT/f'{name}_{k}_working.mp4' for k in ['no_split','team_split','body']}
        writers={k:cv2.VideoWriter(str(p),cv2.VideoWriter_fourcc(*'mp4v'),fps,size) for k,p in paths.items()}
        heat=np.zeros((720,1280),np.float32); counts={}; rows=[]; idx=0; best=-1
        stats={'name':name,'start':start,'duration':duration,'frames':0,'all_logo_detections':0,
               'retained_logo_detections':0,'confirmed_target':0,'uncertain_retained':0}
        try:
            while True:
                ok,frame=cap.read()
                if not ok: break
                img=cv2.resize(frame,size); t=idx/fps
                dets=detector.infer(img,t); visibility.annotate(dets)
                persons=tracker.process(img); tracker.annotate(dets,persons)
                plain=img.copy(); split=img.copy(); _draw(split,persons,1,1,tracker.settings.team_min_votes)
                for d in dets:
                    p=assign_owner(d,persons)
                    state='unassigned' if p is None else ('uncertain' if p.team=='unknown' or p.vote_mass < tracker.settings.team_min_votes else p.team)
                    row=asdict(d); row.update(frame=idx,source_time=start+t,owner_state=state)
                    rows.append(row)
                    x1,y1,x2,y2=map(int,d.xyxy)
                    label=f'{d.brand_name} {d.conf:.2f}'
                    cv2.rectangle(plain,(x1,y1),(x2,y2),(70,230,70),2)
                    cv2.putText(plain,label,(x1,max(45,y1-5)),cv2.FONT_HERSHEY_SIMPLEX,.43,(70,255,70),1,cv2.LINE_AA)
                    if d.on_target_team:
                        color=(0,210,255) if state=='uncertain' else (70,230,70)
                        cv2.rectangle(split,(x1,y1),(x2,y2),color,2)
                        cv2.putText(split,label+(' ?' if state=='uncertain' else ''),(x1,max(45,y1-5)),cv2.FONT_HERSHEY_SIMPLEX,.43,color,1,cv2.LINE_AA)
                        heat[max(0,y1):min(720,y2),max(0,x1):min(1280,x2)]+=1/fps
                        stats['retained_logo_detections']+=1
                        stats['confirmed_target']+=int(state=='target')
                        stats['uncertain_retained']+=int(state=='uncertain')
                overlay=_segment_frame(img,seg,pose,'0',896,.35,counts)
                body=np.where(overlay.any(2,keepdims=True),(img*.5+overlay*.5).astype(np.uint8),img)
                title(plain,'Logo detections | team filter OFF')
                title(split,'Logo + team split | green: retained | amber ?: uncertain | grey: other players')
                title(body,'Pose-guided body regions | grey: unassigned | anatomical estimates, not ground truth')
                for k,im in [('no_split',plain),('team_split',split),('body',body)]: writers[k].write(im)
                if idx%25==0:
                    for k,im in [('no_split',plain),('team_split',split),('body',body)]: cv2.imwrite(str(OUT/f'{name}_{idx:04d}_{k}.jpg'),im)
                if len(dets)>best:
                    best=len(dets)
                    for k,im in [('no_split',plain),('team_split',split),('body',body),('source',img)]: cv2.imwrite(str(OUT/f'{name}_best_{k}.jpg'),im)
                idx+=1; stats['all_logo_detections']+=len(dets)
                if idx%50==0: print(name,idx,stats,flush=True)
        finally:
            cap.release()
            for wr in writers.values(): wr.release()
        for k,path in paths.items():
            final=OUT/f'{name}_{k}.mp4'
            result=mux_audio(path,raw,final)
            if result!=final: raise RuntimeError('H.264 finalisation failed')
            path.unlink()
        blur=cv2.GaussianBlur(heat,(0,0),25)
        colored=cv2.applyColorMap((255*blur/max(float(blur.max()),1e-6)).astype(np.uint8),cv2.COLORMAP_TURBO)
        title(colored,'Screen-space logo occupancy | retained detections | relative intensity, not pitch coordinates')
        cv2.imwrite(str(OUT/f'{name}_heatmap.jpg'),colored)
        (OUT/f'{name}_detections.json').write_text(json.dumps(rows,indent=2))
        stats.update(frames=idx,body_pixel_counts=counts)
        manifest['clips'].append(stats)
        (OUT/'manifest.json').write_text(json.dumps(manifest,indent=2))
    c=sqlite3.connect(f'file:{ROOT / "backend/data/app.db"}?mode=ro',uri=True)
    tables=[r[0] for r in c.execute("select name from sqlite_master where type='table'")]
    print('DB tables',tables)
    print(json.dumps(manifest,indent=2))

if __name__=='__main__': main()
