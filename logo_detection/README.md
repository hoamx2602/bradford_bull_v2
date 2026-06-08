# logo_detection

Train a **yolo26** detector for the Bradford sponsor logos, from the Roboflow
COCO export in `../logo-dataset/`.

## Pipeline

```
conda activate bradford_bulls          # has ultralytics + ffmpeg + cv2
cd logo_detection

python prepare_data.py                 # COCO -> YOLO, clip-aware split -> data/
python train.py                        # yolo26m @ imgsz 1280
```

On Windows you can use `train.bat ...` instead of `python train.py ...`.

## prepare_data.py

Converts `../logo-dataset/train/_annotations.coco.json` (COCO) into YOLO format
under `data/{train,val}/{images,labels}` and writes `data/data.yaml`.

- **Clip-aware split**: whole clips go to train or val (never split a clip), so
  near-duplicate frames don't leak across the split and inflate val mAP.
- **Seed search**: with ~30 tiny, imbalanced clips, it tries many splits and
  picks the one that keeps each logo's instances mostly on the train side, so
  every class is actually learnable. Override with `--seed`.
- Keeps `category_id == YOLO class index` (Roboflow's class 0 `Bradford-Bulls`
  is an unused placeholder; 17 real logo classes follow).

## train.py

yolo26m @ imgsz 1280 with small-object/small-dataset friendly settings
(cos_lr, close_mosaic, no vertical flip). Outputs to `runs/<name>/weights/best.pt`.

## Caveats for this dataset (281 imgs / 1099 boxes / 17 classes)

- **Severe class imbalance**: `klg_home` ~197 boxes down to `aon_away`/`cch_home`
  ~4. The 3 rarest logos (`aon_away`, `cch_home`, `chadlaw_home`, <10 train
  instances) will not learn reliably — collect more crops for them. The
  track-propagation trick (annotate a logo once, propagate across the tracked
  player) is the cheapest way to grow these.
- Judge the model on the **common logos** + **false-positive rate**, not the
  rare-class AP.
- Validation has no instances of the rarest classes by design (too few to both
  train and validate).
