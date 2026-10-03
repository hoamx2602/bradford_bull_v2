"""Presentation-ready evidence panels from real, inspected model detections."""
from pathlib import Path
import json,cv2,sys
from PIL import Image,ImageDraw,ImageFont
ROOT=Path(__file__).resolve().parents[2];OUT=ROOT/'artifacts/bradford_showcase';IMG=OUT/'images';IMG.mkdir(exist_ok=True)
sys.path.insert(0,str(ROOT/'backend'))
from app.pipeline.colors import brand_hex
rows=json.loads((OUT/'scan.json').read_text());evidence=[]
FONT='C:/Windows/Fonts/arial.ttf';BOLD='C:/Windows/Fonts/arialbd.ttf'
def font(n,b=False):return ImageFont.truetype(BOLD if b else FONT,n)
def fit(canvas,im,box):
    im=im.copy();im.thumbnail((box[2],box[3]),Image.Resampling.LANCZOS)
    pos=(box[0]+(box[2]-im.width)//2,box[1]+(box[3]-im.height)//2);canvas.paste(im,pos);return pos,im.size
cases=[
('01_player_occlusion',282,9,'KLG detected behind another player','Only part of the mark is visible beside the foreground player.','Che bởi cầu thủ khác; logo KLG còn nhìn thấy một phần.'),
('02_foreground_head',282,8,'KLG detected behind a foreground head','The left side of the logo is partly covered by the official.','Đầu trọng tài ở tiền cảnh che một phần logo KLG.'),
('03_crossing_arm',282,11,'MCP detected beneath a crossing arm','A hand and forearm cover part of the upper-back mark.','Bàn tay và cánh tay che một phần logo MCP trên lưng áo.'),
('04_forearm_occlusion',284,10,'ASC Group detected with partial arm occlusion','A foreground forearm crosses the lower-back logo. Lower-confidence example.','Cẳng tay che logo ASC Group; ví dụ confidence thấp, cần kiểm tra.'),
('05_blurred_fairway',348,1,'Fairway detected in a blurred frame','Fine lettering is soft in the source frame. No artificial blur was applied.','Logo Fairway bị mờ trong footage gốc; không làm mờ nhân tạo.'),
('06_moving_player_blur',496,2,'ASC Group detected on a moving player','The small lower-back mark appears soft during movement.','Logo ASC Group nhỏ và mờ khi cầu thủ di chuyển.'),
('07_fabric_folds',282,1,'ASC Group detected across fabric folds','Shirt creases compress and distort the printed mark.','Nếp gấp áo làm biến dạng logo ASC Group nhưng detector vẫn trả box.'),
('08_oblique_chest',552,4,'Top Notch detected on a bent torso','The chest mark is tilted and distorted by the player\'s posture.','Logo ngực Top Notch nghiêng, biến dạng theo tư thế cúi người.'),
]
for stem,t,di,title,description,vi in cases:
    row=next(r for r in rows if r['t']==t);det=row['detections'][di]
    source=Image.open(OUT/f'scan_{t:04d}.jpg').convert('RGB');box=list(map(int,det['box']));x1,y1,x2,y2=box
    # Context and native crop remain unaltered apart from model-box overlays.
    color=brand_hex(det['name'])
    annotated=source.copy();dr=ImageDraw.Draw(annotated);dr.rectangle(box,outline=color,width=5)
    clean=source.crop((max(0,x1-100),max(0,y1-70),min(1920,x2+100),min(1080,y2+70)))
    clean.save(IMG/f'{stem}_crop.png');annotated.save(IMG/f'{stem}_frame.png')
    canvas=Image.new('RGB',(1920,1080),'#151A21');d=ImageDraw.Draw(canvas)
    d.text((64,46),title,font=font(46,True),fill='white')
    d.text((64,119),description,font=font(27),fill='#C5CBD3')
    fit(canvas,annotated,(55,200,1210,700));fit(canvas,clean,(1300,210,555,575))
    label=det['name'].replace('_home','').replace('_',' ').upper()
    d.text((1300,815),label,font=font(30,True),fill=color)
    d.text((1300,865),f"Model confidence: {det['conf']:.2f}",font=font(27),fill='white')
    d.text((64,956),f'Source M08_white_1080p.mp4   |   {t//60:02d}:{t%60:02d}.00   |   Actual model output',font=font(24),fill='#CED4DD')
    d.text((64,1005),'Selected qualitative example. Confidence is not a measured occlusion percentage or proof of general accuracy.',font=font(22),fill='#A5AFBB')
    canvas.save(IMG/f'{stem}.png')
    evidence.append({'file':f'images/{stem}.png','frame':f'images/{stem}_frame.png','crop':f'images/{stem}_crop.png','title':title,'description_vi':vi,'source_time':t,'detection':det,'selection':'Visually inspected illustrative model prediction; not independent ground-truth annotation.'})
# Multiple logos on multiple Bradford players, excluding an obviously incorrect
# model prediction over a player name. Keep the original scan JSON for audit.
row=next(r for r in rows if r['t']==282);chosen=[0,1,3,4,5,6,7,8,9,11]
im=Image.open(OUT/'scan_0282.jpg').convert('RGB');d=ImageDraw.Draw(im);used_labels=[]
for i in chosen:
    det=row['detections'][i];color=brand_hex(det['name']);box=list(map(int,det['box']));d.rectangle(box,outline=color,width=3)
    label=det['name'].replace('_home','').replace('_',' ')+' '+f"{det['conf']:.2f}"
    x=min(box[0],1920-320);y=max(4,box[1]-30)
    for attempt in range(20):
        bb=d.textbbox((x,y),label,font=font(21))
        if not any(bb[0]<b[2] and bb[2]>b[0] and bb[1]<b[3] and bb[3]>b[1] for b in used_labels):break
        y=max(4,y-28)
    used_labels.append(bb);d.rectangle(bb,fill='#151A21');d.text((x,y),label,font=font(21),fill=color)
im.save(IMG/'09_multiple_players.png')
evidence.append({'file':'images/09_multiple_players.png','title':'Ten selected detections across Bradford players','description_vi':'10 detection được chọn để minh họa nhiều logo trên nhiều cầu thủ Bradford; bỏ một dự đoán sai rõ ràng trên tên cầu thủ.','source_time':282,'selected_detection_indices':chosen,'all_predictions_source':'scan.json'})
(OUT/'image_evidence.json').write_text(json.dumps(evidence,indent=2),encoding='utf-8')
print('Wrote',len(evidence),'examples')
