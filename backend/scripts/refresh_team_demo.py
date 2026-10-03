"""Re-evaluate team attribution on cached, identical logo detections."""
from build_club_demo import *
from app.pipeline.teamdet_video import _draw
from app.pipeline.datatypes import Detection
import pickle
manifest=json.loads((OUT/'manifest.json').read_text())
refs=pickle.load((ROOT/'backend/data/auto_refs/c775d9975e3047a19eca8268a5825f3f-home.pkl').open('rb'))
manifest['team_reference_meta']=refs['meta']
manifest['team_method']='Kit-specific home colour evidence, temporal votes, broadcast-cut reset'
for stat in manifest['clips']:
    name=stat['name']; rows=json.loads((OUT/f'{name}_detections.json').read_text()); by={}
    for row in rows: by.setdefault(row['frame'],[]).append(row)
    raw=OUT/f'{name}_source.mp4'; cap=cv2.VideoCapture(str(raw)); fps=cap.get(5)
    tracker=TeamTracker(refs=refs); tmp=OUT/f'{name}_refresh_working.mp4'
    wr=cv2.VideoWriter(str(tmp),cv2.VideoWriter_fourcc(*'mp4v'),fps,(1280,720))
    heat=np.zeros((720,1280),np.float32); idx=0;best=-1; records=[]
    stat.update(retained_logo_detections=0,confirmed_target=0,uncertain_retained=0)
    person_records=[]
    while True:
        ok,img=cap.read()
        if not ok:break
        img=cv2.resize(img,(1280,720)); persons=tracker.process(img)
        ds=[Detection(**{k:v for k,v in row.items() if k in Detection.__dataclass_fields__}) for row in by.get(idx,[])]
        tracker.annotate(ds,persons);_draw(img,persons,1,1,tracker.settings.team_min_votes)
        for p in persons: person_records.append({'frame':idx,**asdict(p)})
        for row,det in zip(by.get(idx,[]),ds):
            owner=assign_owner(det,persons)
            state='unassigned' if owner is None else ('uncertain' if owner.team=='unknown' or owner.vote_mass<tracker.settings.team_min_votes else owner.team)
            row.update(on_target_team=det.on_target_team,owner_state=state);records.append(row)
            if det.on_target_team:
                x1,y1,x2,y2=map(int,det.xyxy); color=(0,210,255) if state=='uncertain' else (70,230,70)
                cv2.rectangle(img,(x1,y1),(x2,y2),color,2)
                cv2.putText(img,f'{det.brand_name} {det.conf:.2f}',(x1,max(45,y1-5)),cv2.FONT_HERSHEY_SIMPLEX,.43,color,1,cv2.LINE_AA)
                heat[max(0,y1):min(720,y2),max(0,x1):min(1280,x2)]+=1/fps
                stat['retained_logo_detections']+=1;stat['confirmed_target']+=int(state=='target');stat['uncertain_retained']+=int(state=='uncertain')
        title(img,'Logo + team split | green: retained | amber ?: uncertain | grey: other players')
        wr.write(img)
        if idx%25==0:cv2.imwrite(str(OUT/f'{name}_{idx:04d}_team_split.jpg'),img)
        if len(ds)>best:best=len(ds);cv2.imwrite(str(OUT/f'{name}_best_team_split.jpg'),img)
        idx+=1
    cap.release();wr.release()
    final=OUT/f'{name}_team_split.mp4'
    result=mux_audio(tmp,raw,final)
    if result!=final:raise RuntimeError('video finalisation failed')
    tmp.unlink()
    blur=cv2.GaussianBlur(heat,(0,0),25)
    colored=cv2.applyColorMap((255*blur/max(float(blur.max()),1e-6)).astype(np.uint8),cv2.COLORMAP_TURBO)
    title(colored,'Screen-space logo occupancy | retained detections | relative intensity, not pitch coordinates')
    cv2.imwrite(str(OUT/f'{name}_heatmap.jpg'),colored)
    (OUT/f'{name}_detections.json').write_text(json.dumps(records,indent=2))
    (OUT/f'{name}_persons.json').write_text(json.dumps(person_records))
    print(name,stat,flush=True)
manifest['team_keep_unknown']=tracker.settings.team_keep_unknown
manifest['team_min_votes']=tracker.settings.team_min_votes
(OUT/'manifest.json').write_text(json.dumps(manifest,indent=2))
