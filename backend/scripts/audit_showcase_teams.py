"""Replay team inference on the same 90 seconds, preserving logo predictions."""
from build_club_demo import ROOT
import cv2, json, pickle
from collections import Counter, defaultdict
from dataclasses import asdict
from app.pipeline.teamid.tracker import TeamTracker, assign_owner
from app.pipeline.teamdet_video import _draw
from app.pipeline.datatypes import Detection
OUT=ROOT/'artifacts/bradford_showcase';AUDIT=OUT/'team_audit';AUDIT.mkdir(exist_ok=True)
meta=json.loads((OUT/'showcase_manifest.json').read_text());rows=json.loads((OUT/'showcase_detections.json').read_text())
if not (AUDIT/'before_detections.json').exists():(AUDIT/'before_detections.json').write_text(json.dumps(rows))
indexed=defaultdict(list)
for r in rows:indexed[r['output_frame']].append(r)
refs=pickle.load((ROOT/'backend/data/auto_refs/c775d9975e3047a19eca8268a5825f3f-home.pkl').open('rb'))
cap=cv2.VideoCapture(meta['source']); idx=0; before=Counter();after=Counter();person_before=Counter();person_after=Counter();snapshots=[];changes=0
for ci,(start,end) in enumerate(meta['segments']):
    tr=TeamTracker(refs=refs);cap.set(1,round(start*meta['fps']))
    for j in range(round((end-start)*meta['fps'])):
        ok,frame=cap.read();assert ok
        people=tr.process(frame)
        for p in people:
            old='uncertain' if p.vote_mass<tr.settings.team_min_votes else tr.voter.label(p.track_id)
            new='uncertain' if p.vote_mass<tr.settings.team_min_votes or p.team=='unknown' else p.team
            person_before[old]+=1;person_after[new]+=1
        for r in indexed[idx]:
            d=Detection(**{k:v for k,v in r.items() if k in Detection.__dataclass_fields__})
            owner=assign_owner(d,people)
            state='unassigned' if owner is None else ('uncertain' if owner.vote_mass<tr.settings.team_min_votes or owner.team=='unknown' else owner.team)
            before[r['team_state']]+=1;after[state]+=1;changes+=int(r['team_state']!=state)
            tr.annotate([d],people);r.update(team_state=state,on_target_team=d.on_target_team)
        if idx in [100,175,350,575,1000,1250,1300,1350,1400,1600,1775,2125]:
            im=frame.copy();_draw(im,people,1,1,tr.settings.team_min_votes);cv2.imwrite(str(AUDIT/f'frame_{idx:04d}.jpg'),im)
            snapshots.append({'output_frame':idx,'source_time':start+j/meta['fps'],'people':[asdict(p) for p in people]})
        idx+=1
    print('Team audit segment',ci+1,flush=True)
cap.release()
report={'scope':'90-second selected footage; no human ground truth; counts are repeated frame instances, NOT accuracy.',
        'logo_states_before':dict(before),'logo_states_after':dict(after),'changed_logo_states':changes,
        'person_states_without_margin_gate':dict(person_before),'person_states_with_margin_gate':dict(person_after),
        'settings':{k:getattr(tr.settings,k) for k in ['team_person_conf','team_person_imgsz','team_siglip_every','team_hysteresis','team_min_votes','team_vote_decay','team_min_vote_margin','team_keep_unknown','team_keep_unassigned']},
        'kit':tr.kit,'snapshots':snapshots}
(AUDIT/'audit.json').write_text(json.dumps(report,indent=2));(OUT/'showcase_detections.json').write_text(json.dumps(rows))
meta.update(confirmed_target_instances=after['target'],uncertain_instances=after['uncertain'],team_audit='team_audit/audit.json',team_settings=report['settings'],team_status_labels='BRA = predicted Bradford; ? = uncertain; colour = sponsor')
(OUT/'showcase_manifest.json').write_text(json.dumps(meta,indent=2));print(json.dumps({k:v for k,v in report.items() if k!='snapshots'}),flush=True)
