import json,cv2
from PIL import Image,ImageDraw
from pathlib import Path
out=Path(__file__).resolve().parents[2]/'artifacts/bradford_showcase'
r=json.loads((out/'scan.json').read_text());cases=[]
for t in [282,284,286,348,496,552]:
    row=next(x for x in r if x['t']==t);im=cv2.imread(str(out/f'scan_{t:04d}.jpg'))
    for di,d in enumerate(row['detections']):
        if (t==282 and di in [1,3,4,8,9,11,12]) or (t==284 and di in [3,4,10]) or (t==286 and di in [1,2]) or t in [348,496] or (t==552 and di in [3,4,6,8]):
            x1,y1,x2,y2=map(int,d['box']);crop=im[max(0,y1-65):min(1080,y2+65),max(0,x1-100):min(1920,x2+100)].copy();cases.append((t,di,d,crop))
for st in range(0,len(cases),12):
    sheet=Image.new('RGB',(1440,1000),'#151920');dr=ImageDraw.Draw(sheet)
    for j,(t,di,d,crop) in enumerate(cases[st:st+12]):
        p=Image.fromarray(cv2.cvtColor(crop,cv2.COLOR_BGR2RGB));p.thumbnail((350,270));x=(j%4)*360;y=(j//4)*330;sheet.paste(p,(x,y+30));dr.text((x+5,y+5),f'{t}s idx{di} {d["name"]} {d["conf"]:.2f}',fill='white')
    sheet.save(out/f'challenges_{st//12}.jpg')
