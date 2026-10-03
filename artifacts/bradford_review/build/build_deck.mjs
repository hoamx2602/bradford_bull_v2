import fs from 'node:fs/promises';
import path from 'node:path';
import {pathToFileURL} from 'node:url';
import {Presentation,PresentationFile} from '@oai/artifact-tool';
const root='D:/bradford_bull_v2/artifacts/bradford_review';
const skill='C:/Users/nguye/.codex/plugins/cache/openai-primary-runtime/presentations/26.909.12148/skills/presentations';
const {applyPresentationChartFont,finalizePresentation}=await import(pathToFileURL(skill+'/container_tools/artifact_tool_utils.mjs'));
const d=JSON.parse(await fs.readFile(root+'/slide_data.json','utf8'));
const m=JSON.parse(await fs.readFile(root+'/manifest.json','utf8'));
const p=Presentation.create({slideSize:{width:1280,height:720}});
const RED='#C51D32',DARK='#161A20',GRAY='#626974',GOLD='#D6A83F';
function text(s,t,x,y,w,h,size=26,color=DARK,bold=false){const q=s.shapes.add({geometry:'textbox',position:{left:x,top:y,width:w,height:h},fill:'none',line:{fill:'none',width:0}});q.text=t;q.text.style={typeface:'Arial',fontSize:size,color,bold,autoFit:'none'};return q;}
function slide(title,note='',dark=false){let s=p.slides.add();s.background.fill=dark?DARK:'#FFFFFF';text(s,title,60,42,1160,96,40,dark?'#FFFFFF':DARK,true);if(note)text(s,note,60,648,1160,44,17,dark?'#D4D7DC':GRAY);return s;}
async function img(s,file,x,y,w,h){s.images.add({blob:new Uint8Array(await fs.readFile(root+'/'+file)),contentType:'image/jpeg',fit:'contain',position:{left:x,top:y,width:w,height:h}});}
function notes(s,t){s.speakerNotes.textFrame.setText(t);}
function chart(s,cats,series,x=70,y=165,w=1120,h=420){const c=s.charts.add('bar',{position:{left:x,top:y,width:w,height:h},categories:cats,series,barOptions:{direction:'column',grouping:'clustered',gapWidth:90},hasLegend:true,legend:{position:'bottom',textStyle:{fontSize:17}},dataLabels:{showValue:true,position:'outEnd',textStyle:{fontSize:17}},chartFill:'#FFFFFF',xAxis:{textStyle:{fontSize:17}},yAxis:{numberFormatCode:'0.0',textStyle:{fontSize:16}}});applyPresentationChartFont(c,{fontFamily:'Arial'});return c;}
const analyses=d.analyses.slice(0,2);
function vals(ids,a){return ids.map(id=>a.location_ai[id]||0);}
function baseline(ids){return ids.map(id=>+(100*d.locations.find(l=>l.id===id).human_percentage/d.manual_total).toFixed(2));}
const historical='Historical saved analyses, before this revision. Human weights normalised from a total of 95.';
{
let s=slide('Bradford Bulls\nSponsor visibility in match footage','Findings, practical demos and sponsorship decisions',true);
await img(s,'tackle_best_source.jpg',470,160,750,420);text(s,'LogoLens',60,255,380,70,60,'#FFFFFF',true);text(s,'Evidence from the kit\nto the sponsor conversation',60,357,395,130,30,'#FFFFFF');notes(s,'Prepared from local code execution and stored analyses. All match screenshots are extracted from real footage. Demo source: M08_white_1080p.mp4. No synthetic detection images.');
}
{
let s=slide('Shorts exposure exceeds its configured weight',historical);
chart(s,['Main sponsor','Top back shorts'],[{name:'Human weight (normalised %)',values:baseline(['main-sponsor','top-back-shorts']),fill:GRAY},{name:'Match 1 AI share (%)',values:vals(['main-sponsor','top-back-shorts'],analyses[1]),fill:RED},{name:'Match 2 AI share (%)',values:vals(['main-sponsor','top-back-shorts'],analyses[0]),fill:GOLD}]);
notes(s,'Sources: stored_evidence.json; backend/data/app.db, analyses 7451009139ba and 26d98363c4bd. AI shares recomputed using current location mapping and criteria size, position, confidence, OBB, durationWeight. These are exposure shares, not price recommendations. Stored matches were not rerun after the CV fixes.');
}
{
let s=slide('The comparison measures exposure, not contract value','No verified rate card or frame-level manual audit is available in the repository.');
text(s,'Human reference',70,180,510,55,32,DARK,true);text(s,'Configured location weights\nMain sponsor: 26\nTop back shorts: 5',70,250,500,175,29);
text(s,'AI measurement',690,180,510,55,32,RED,true);text(s,'Share of weighted visible exposure\nMatch 2 main sponsor: 12.71%\nMatch 2 top back shorts: 21.82%',690,250,515,180,29);
text(s,'Use the difference to review placement value and supporting footage.',70,505,1100,95,34,DARK,true);
notes(s,'Human values are user-configured weights in location_configs, not verified club prices or manual logo ground truth. Raw weights sum to 95 and are normalised in charts. Never interpret the difference as an accuracy error or a direct price multiplier.');
}
for(const spec of [
 ['Chest: the main sponsor leads the human weighting','chest',['main-sponsor','collar-bone','chest-opp-badge'],['Main sponsor','Collar bone','Chest badge']],
 ['Back: nearby slots share one pose anchor','back',['collar-back','top-back','nape-neck','bottom-back'],['Collar back','Top back','Nape neck','Bottom back']],
 ['Sleeves: exposure differs between placements','sleeves',['sleeve-1','sleeve-2','sleeve-3'],['Sleeve 1','Sleeve 2','Sleeve 3']],
 ['Shorts: both matches show substantial exposure','shorts',['top-back-shorts','shorts-front','shorts-back-1','shorts-back-2'],['Top back','Front','Side 1','Side 2']]
]){
let [title,key,ids,labels]=spec;let s=slide(title,'Historical Match 2 shares; image is a fresh detection example from the separate demo footage.');
await img(s,key+'_evidence.jpg',60,175,410,420);
chart(s,labels,[{name:'Human normalised %',values:baseline(ids),fill:GRAY},{name:'AI share %',values:vals(ids,analyses[0]),fill:RED}],500,170,720,430);
notes(s,JSON.stringify({source:'stored_evidence.json and slide_data.json',imageDetection:d.crop_sources[key],locationIds:ids,limitation:key==='back'?'Collar back, top back and nape neck map to back-top and share its measurement equally; these are not independently resolved slots.':'Placement labels and brand mapping need club verification. Detection crop illustrates the named sponsor, not a manual validation label.'}));
}
{
let s=slide('Team attribution changes what enters the analysis','Identical frames and logo detections; only the ownership and team-filter decision changes.');
await img(s,'wide_0175_no_split.jpg',60,170,565,318);await img(s,'wide_0175_team_split.jpg',655,170,565,318);
text(s,'Without team split',60,510,550,50,30,DARK,true);text(s,'With team split',655,510,550,50,30,RED,true);
notes(s,'Fresh CUDA run: build_club_demo.py. Images at demo frame 175, source offset 18 + 175/25 = 25 seconds. Video files wide_no_split.mp4 and wide_team_split.mp4. Boxes represent predictions, not verified truth.');
}
{
let s=slide(`${m.clips.reduce((a,c)=>a+c.retained_logo_detections,0)} of 583 detection instances pass the team filter`,'22 seconds at 25 fps. Counts are repeated frame detections, not unique logos or accuracy.');
chart(s,['Opening sequence (10 s)','Tackle sequence (12 s)'],[{name:'All detected logos',values:m.clips.map(c=>c.all_logo_detections),fill:GRAY},{name:'Retained by team filter',values:m.clips.map(c=>c.retained_logo_detections),fill:RED}]);
notes(s,'Source manifest.json and per-frame *_detections.json. Home-kit colour evidence with temporal votes and broadcast-cut resets. Rejected detections include opponents, unassigned logos and tracks without sufficient evidence under the current policy. No claim that all rejections are correct.');
}
{
let s=slide('Body regions follow each player’s visible silhouette','Grey pixels remain unassigned when pose evidence is missing. Colours are anatomical estimates.');
await img(s,'tackle_0150_body.jpg',60,175,850,440);
text(s,'Changes',980,185,245,50,30,DARK,true);text(s,'One pose per mask\n\nNo invented torso\n\nNo duplicate pixel counts',980,257,240,290,24);
notes(s,'Source tackle_body.mp4, generated with YOLO11x-seg and YOLO11x-pose, imgsz896, confidence0.35. Baseline dashboard defaults may use smaller models. Anatomical colour regions are not pixel-labelled ground truth and do not distinguish chest from back. Sponsor slot attribution is a separate pipeline stage.');
}
{
let s=slide('The heatmap shows where retained logos appear','Screen-space occupancy from the 12-second tackle demo; bright areas receive more repeated coverage.');
await img(s,'tackle_heatmap.jpg',60,175,850,440);text(s,'Relative\nintensity',1020,230,190,80,29,DARK,true);text(s,'Camera framing\naffects this view.\n\nThis is not a\npitch-position map.',1020,345,200,180,25);
notes(s,'Source tackle_detections.json. For every retained bounding box, add 1/fps to covered screen pixels; Gaussian smoothing sigma25px; normalise to maximum for display. All-team anatomical pixel coverage is different from sponsor visibility. No homography or pitch coordinates are estimated.');
}
{
let s=slide('Each exposure combines time, size and confidence','Confidence is a clarity proxy. Occlusion is not independently measured in the current score.');
const items=[['Duration','Time visible in sampled footage'],['Logo size','Bounding-box area relative to frame'],['Position','Weight relative to the frame centre'],['Clarity','Detector confidence, not legibility truth'],['Frequency','Repeated exposure events and tracks'],['Occlusion','Reflected indirectly in detection loss']];
items.forEach((a,i)=>{let x=70+(i%2)*610,y=170+Math.floor(i/2)*145;text(s,a[0],x,y,550,44,31,RED,true);text(s,a[1],x,y+54,530,65,24);});
notes(s,'Source backend/app/pipeline/visibility.py, exposure.py and location_breakdown.py. HBB models use OBB factor1. Duration segments depend on sampling and tracking. Confidence cannot establish human readability; no calibrated standalone occlusion metric is present.');
}
{
let s=slide('Logged detector validation: 85.2% mAP@50','Best logged mAP@50–95 epoch (22). These scores do not validate team identity or body parts.');
let vals=[['Precision',82.6],['Recall',73.1],['mAP@50',85.2],['mAP@50–95',63.9]];
vals.forEach((a,i)=>{let x=65+i*305;text(s,a[1]+'%',x,230,285,100,64,i===2?RED:DARK,true);text(s,a[0],x,355,280,65,27);});
text(s,'Next validation: label teams and body parts across tackles, cuts and distant shots.',70,510,1130,100,30,DARK,true);
notes(s,'Source runs/yolo26/matchsplit_896_m/results.csv, epoch22: precision .82631, recall .73073, mAP50 .85239, mAP50-95 .63865. args.yaml points to datasets/yolo_matchsplit/data.yaml. These are historical training validation logs; selected weights were used in demos but benchmark was not rerun in this session. No manual body-part or team ground truth was available.');
}
{
let s=slide('The system keeps a traceable path back to footage','Every exported screenshot and video comes from code execution on the source match.');
const stages=[['Match footage','Source + timestamp'],['Logo detection','Box + confidence'],['Team / body','Ownership + pose'],['Exposure','Duration + weight']];
stages.forEach((a,i)=>{let x=60+i*305;s.shapes.add({geometry:'rect',position:{left:x,top:240,width:265,height:180},fill:i===2?'#F8E8EB':'#EEF0F2',line:{fill:'none',width:0}});text(s,String(i+1),x+18,255,230,45,28,RED,true);text(s,a[0],x+18,310,230,40,27,DARK,true);text(s,a[1],x+18,365,230,46,21);});
text(s,'Per-frame JSON and a run manifest make each demo reproducible.',60,515,1160,80,32,DARK,true);notes(s,'Editable conceptual flow diagram. Evidence files: manifest.json, wide_detections.json, tackle_detections.json, stored_evidence.json; runner backend/scripts/build_club_demo.py. Diagram is explanatory, not a generated match scene.');
}
{
let s=slide('Tackles, camera cuts and small logos remain difficult','Unknown labels and reviewable evidence are necessary parts of the output.');
await img(s,'wide_best_body.jpg',60,165,715,402);text(s,'Visible limitations',815,165,390,50,31,RED,true);text(s,'Overlapping players mix kit colours\n\nMissing joints leave uncertain regions\n\nDistant logos lose readable detail\n\nClose kit slots share pose anchors',815,240,390,350,25);
notes(s,'No claim of perfect segmentation or production accuracy uplift. This revision fixes identified logic errors and passes regression tests, but a labelled rugby evaluation set is needed to quantify improvement. Cut detection is heuristic; calibrated pose-based ownership remains further work.');
}
{
let s=slide('Bradford Bulls can use the evidence in sponsor reviews','Exposure supports commercial judgement; audience, rights and contracts also determine price.',true);
text(s,'Review high-exposure\nplacements',65,195,520,120,42,'#FFFFFF',true);text(s,'Use shorts and chest comparisons to question assumptions in the current weighting.',65,340,515,140,28,'#D4D7DC');
text(s,'Show the sponsor\nthe footage',690,195,520,120,42,'#FFFFFF',true);text(s,'Pair every placement claim with a dated clip, a visibility measure and its limitations.',690,340,515,140,28,'#D4D7DC');
notes(s,'Recommended next commercial step: verify the club rate card and placement map, agree a manually labelled evaluation sample, then rerun complete matches with the reviewed pipeline before changing sponsorship prices.');
}
await fs.mkdir(root+'/build/renders',{recursive:true});
await(await PresentationFile.exportPptx(p)).save(root+'/build/candidate.pptx');
for(let i=0;i<p.slides.items.length;i++){let b=await p.export({slide:p.slides.items[i],format:'png',scale:1});await fs.writeFile(root+`/build/renders/slide-${String(i+1).padStart(2,'0')}.png`,new Uint8Array(await b.arrayBuffer()));}
const result=await finalizePresentation({workspaceDir:root,candidatePath:root+'/build/candidate.pptx',finalPath:root+'/presentation/Bradford_Bulls_Findings_Final.pptx',pythonExecutable:'C:/Users/nguye/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe',integrityValidatorPath:skill+'/container_tools/inspect_presentation_package_integrity.py',layoutValidatorPath:skill+'/container_tools/inspect_presentation_layout_geometry.py',layoutArgs:['--expected-slide-size-emu','12192000,6858000','--validate-heading-fit'],fontPolicy:{basis:'design',families:['Arial']},verifyArtifactToolImport:true,materializeLiteralChartWorkbooks:true,receiptPath:root+'/build/validation_final.json'});
console.log(result);




