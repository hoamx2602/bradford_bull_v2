from build_club_demo import *
from app.pipeline.teamid.features import color_feature,color_sim
from app.pipeline.teamid.jersey import get_jersey_region
from app.pipeline.teamid.classifier import TeamClassifier
refs=build_refs_from_video(ROOT/'backend/data/uploads/c775d9975e3047a19eca8268a5825f3f.mp4','home')
cl=TeamClassifier.from_refs(refs)
c=cv2.VideoCapture(str(OUT/'wide_source.mp4'));c.set(1,100);ok,f=c.read();f=cv2.resize(f,(1280,720))
for name,b in [('white',(660,221,829,576)),('purple',(887,237,1044,668)),('ref',(15,251,220,700))]:
    crop,mask=get_jersey_region(f,b);cf=color_feature(crop,mask)
    print(name,cl.classify(None,cf),{t:color_sim(cf,x['color']) for t,x in refs['teams'].items()},flush=True)
