from pathlib import Path
import cv2,json,csv
ROOT=Path(__file__).resolve().parents[2]; OUT=ROOT/'artifacts/bradford_review'
e=json.loads((OUT/'stored_evidence.json').read_text())
logs=list(csv.DictReader((ROOT/'runs/yolo26/matchsplit_896_m/results.csv').open()))
best=max(logs,key=lambda r:float(r['metrics/mAP50-95(B)']))
e['validation_log']=best
e['manual_total']=sum(l['human_percentage'] for l in e['locations'])
categories={'chest':['top_notch'],'back':['mcp','asc_group','fairway'], 'sleeves':['bartercard','atm','chadlaw'],'shorts':['klg','aon','paints_lacquers']}
allrows=[]
for clip in ['wide','tackle']:
    for row in json.loads((OUT/f'{clip}_detections.json').read_text()):
        row['clip']=clip; allrows.append(row)
e['crop_sources']={}
for key,brands in categories.items():
    choices=[r for r in allrows if r['brand_key'] in brands]
    if not choices: continue
    clear=[r for r in choices if r['conf'] >= .65 and r['xyxy'][0] > 20 and r['xyxy'][2] < 1260]
    if clear: choices=clear
    row=max(choices,key=lambda r:(r['xyxy'][2]-r['xyxy'][0])*(r['xyxy'][3]-r['xyxy'][1])*r['conf'])
    cap=cv2.VideoCapture(str(OUT/f"{row['clip']}_source.mp4")); cap.set(cv2.CAP_PROP_POS_FRAMES,row['frame']); ok,img=cap.read(); cap.release()
    img=cv2.resize(img,(1280,720)); x1,y1,x2,y2=map(int,row['xyxy'])
    cv2.rectangle(img,(x1,y1),(x2,y2),(20,230,255),3)
    # Preserve the surrounding player for visual placement verification.
    cx=(x1+x2)//2; cy=(y1+y2)//2; halfw=max(180,x2-x1); halfh=max(190,y2-y1)
    crop=img[max(0,cy-halfh):min(720,cy+halfh),max(0,cx-halfw):min(1280,cx+halfw)]
    cv2.rectangle(crop,(0,0),(crop.shape[1],34),(24,24,24),-1)
    cv2.putText(crop,f"{row['brand_name']} {row['conf']:.2f}",(8,24),cv2.FONT_HERSHEY_SIMPLEX,.55,(20,230,255),1,cv2.LINE_AA)
    cv2.imwrite(str(OUT/f'{key}_evidence.jpg'),crop)
    e['crop_sources'][key]=row
(OUT/'slide_data.json').write_text(json.dumps(e,indent=2),encoding='utf-8')
print('manual total',e['manual_total'],'best validation',best)
