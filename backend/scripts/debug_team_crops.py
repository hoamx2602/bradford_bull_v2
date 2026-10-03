import sys,os,pickle
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT/'backend'))
os.environ['TEAM_PERSON_MODEL']=str(ROOT/'yolo11m.pt')
import cv2,numpy as np
from app.pipeline.teamid.bootstrap import _collect_crops,_kmeans,_luminance
from app.pipeline.teamid.features import color_feature
from PIL import Image,ImageDraw
r,m=_collect_crops(ROOT/'backend/data/uploads/c775d9975e3047a19eca8268a5825f3f.mp4',48,'0')
f=np.stack([color_feature(a,b) for a,b in zip(r,m)]); labels,centers=_kmeans(f,3)
for c in range(3):
    ix=np.where(labels==c)[0]; out=Image.new('RGB',(1000,100*((len(ix)+9)//10)), '#222222'); dr=ImageDraw.Draw(out)
    for n,i in enumerate(ix):
        im=Image.fromarray(cv2.cvtColor(r[i],cv2.COLOR_BGR2RGB));im.thumbnail((98,75));x=n%10*100;y=n//10*100;out.paste(im,(x,y));dr.text((x,y+76),str(i),fill='white')
    out.save(ROOT/f'artifacts/bradford_review/cluster{c}.jpg')
    print(c,len(ix),_luminance(centers[c]),centers[c].round(2),flush=True)
