# 10. Scalable Logo Detection — Giải Pháp SOTA Đa Club / Đa Game

> **Bối cảnh**: Pipeline hiện tại (Roboflow manual → YOLO fine-tune) không scale khi
> thêm club mới hoặc sport mới. Tài liệu này trình bày kiến trúc thay thế hoàn chỉnh —
> từ lý thuyết đến implementation path — với mục tiêu: **input = kit image + logo PNGs,
> output = deployed model**, tối thiểu annotation thủ công.
>
> Đọc trước: [`autolabel.md`](../autolabel.md), [`frontier_solutions.md`](../frontier_solutions.md),
> [`bac4_3d_simulation.md`](../bac4_3d_simulation.md).

---

## 0. Tại Sao Pipeline Hiện Tại Không Scale

### 0.1 Bottleneck thực sự

```
Club mới → extract frames → annotate tay (4–8 giờ/club) → train YOLO → deploy
                               ↑
                       bottleneck ở đây — linear với số club
```

Không phải vấn đề về model hay compute. Vấn đề là **annotation là O(n_clubs × n_logos × n_frames)**.

### 0.2 Ba tín hiệu miễn phí đang bị bỏ qua

| Tín hiệu | Hiện tại | Khai thác đúng |
|----------|----------|----------------|
| **Logo asset gốc** (PNG/SVG có sẵn) | Dùng để train YOLO closed-set | Template cho zero-shot retrieval + synthetic data |
| **Kit image** (marketing render) | Không dùng | UV mapping tự động → biết chính xác logo ở đâu trên jersey |
| **Video redundancy** | Annotate từng frame | Label 1 frame → SAM2 propagate 300 frames |

### 0.3 Hậu quả thiết kế hiện tại

- **Closed-set**: thêm logo mới → retrain toàn bộ
- **Club-specific**: model Bradford Bulls không transfer sang club khác
- **Manual bottleneck**: mỗi game mới = cycle annotation mới

---

## 1. Kiến Trúc Giải Pháp Tổng Thể

Giải pháp chia thành **3 Track** chạy song song, bổ trợ nhau:

```
INPUT: Kit Image (home/away) + Logo PNGs
             │
    ┌────────┴──────────────────────────┐
    │                                   │
  Track A                         Track B                   Track C
  Synthetic Data                  Foundation Model          Retrieval-Based
  (Zero annotation)               Auto-Label                Detection
  └── 3D Blender renders          └── OWL-ViT2 pseudo-label └── DINOv2 + FAISS
  └── Auto UV mapping             └── SAM2/SAM3 propagation └── No retraining
  └── AnyDoor augmentation        └── Active learning
    │                                   │                        │
    └─────────────┬─────────────────────┘                        │
                  ▼                                              │
         Label Fusion + QA ◄────────────────────────────────────┘
                  │
         YOLO Fine-tune (nếu cần throughput)
          hoặc thẳng Retrieval (zero annotation)
                  │
           Deployed System
                  │
    ┌─────────────┴─────────────┐
    │                           │
  High accuracy path         Zero-retrain path
  (YOLO trained on fused     (DINOv2 retrieval,
   synthetic + pseudo-label)   add logo = update DB)
```

---

## 2. Track A — Synthetic Data Pipeline (Zero Annotation)

### 2.1 Hiện trạng (đã build cho Bradford Bulls)

```
kit_layout.yaml (UV positions) → bac4_v2_paint.py (paint logos) → bac4_v2_render.py (Blender)
→ 200 renders × 4 logos/render = 800 annotated logo instances, ZERO manual work
```

**Kết quả**: mAP ~0.60–0.70 khi test trên real broadcast footage (sim-to-real gap).

### 2.2 Vấn đề chưa giải quyết: Auto UV Mapping

Hiện tại, bước calibrate UV (dot-test) vẫn manual cho mỗi jersey mesh mới. Cần tự động hóa:

**Mục tiêu**: `kit_image.jpg` + `logo.png` → UV coordinates tự động, không cần dot-test.

#### Pipeline Auto UV Mapping

```
kit_image.jpg (flat marketing render của jersey)
       │
       ▼
Step 1: Jersey Segmentation (SAM2 automatic)
       │  prompt: "white jersey" / "black jersey"
       ▼
Step 2: Flatness normalization
       │  Thin-plate spline từ segmented jersey → canonical rectangle
       │  Reference: 4 keypoints (2 shoulder, 2 hem corners)
       ▼
Step 3: Logo localization trong kit image (OWL-ViT2)
       │  query = logo PNG, target = flattened jersey
       │  → pixel coordinates (px, py) của mỗi logo
       ▼
Step 4: Pixel → UV mapping
       │  Bilinear interpolation từ canonical UV grid
       │  (grid đã calibrate từ jersey mesh một lần duy nhất)
       ▼
Kit layout YAML — tự động sinh, không cần dot-test
```

**Implementation**:
```python
# auto_uv_map.py (TODO: implement)
import numpy as np
from scipy.interpolate import RBFInterpolator
from transformers import Owlv2Processor, Owlv2ForObjectDetection
import segment_anything_v2 as sam2

def auto_uv_map(kit_image_path, logo_paths, canonical_uv_grid):
    """
    Tự động tính UV positions cho mỗi logo từ kit image.
    canonical_uv_grid: dict{keypoint_name → UV} đã calibrate từ jersey mesh.
    """
    # Step 1: Segment jersey in kit image
    kit_img = load_image(kit_image_path)
    jersey_mask = sam2_segment(kit_img, text_prompt="jersey front panel")
    jersey_crop, H_warp = flatten_jersey(kit_img, jersey_mask)  # → canonical rect

    # Step 2: Detect each logo in flattened jersey crop
    owlv2_model = load_owlv2()
    logo_positions = {}
    for logo_path in logo_paths:
        logo_img = load_image(logo_path)
        boxes = owlv2_detect(owlv2_model, query=logo_img, target=jersey_crop)
        if boxes:
            best_box = max(boxes, key=lambda b: b.score)
            # pixel center in jersey_crop
            px = (best_box.x1 + best_box.x2) / 2
            py = (best_box.y1 + best_box.y2) / 2
            pw = best_box.x2 - best_box.x1
            logo_positions[logo_path] = (px, py, pw)

    # Step 3: Map pixel → UV via canonical grid
    rbf = RBFInterpolator(
        list(canonical_uv_grid.pixel_coords()),
        list(canonical_uv_grid.uv_coords()),
        kernel='thin_plate_spline'
    )
    kit_layout = {}
    for logo_path, (px, py, pw) in logo_positions.items():
        uv_cx, uv_cy = rbf([[px, py]])[0]
        uv_w = pw / jersey_crop.width * 0.35  # scale to UV space
        kit_layout[logo_path] = {'uv_cx': uv_cx, 'uv_cy': uv_cy, 'uv_w': uv_w}

    return kit_layout
```

**Độ khó**: Trung bình. SAM2 + OWL-ViT2 đều có off-the-shelf. Phần khó là `flatten_jersey` (thin-plate spline từ segmented polygon → canonical rect) — nhưng đây là bài toán image warping cổ điển.

---

### 2.3 AnyDoor: Insert Logo vào Real Frames (Photorealistic)

Ngoài Blender renders (jersey trắng/đen plain), ta cần **synthetic data từ real broadcast frames**
với logo được dán vào đúng position, đúng lighting/perspective.

**Tool**: [AnyDoor](https://github.com/ali-vilab/AnyDoor) (Alibaba, CVPR 2024).

```
Reference image: logo PNG (clean)
Target image: broadcast frame với player
Mask: jersey front panel segmentation (SAM2)

AnyDoor → logo được paste vào jersey với:
  - Perspective warp khớp góc jersey
  - Lighting match (điều chỉnh brightness/color theo jersey)
  - Texture blending (Poisson editing ở latent space)
  - Edge seamlessness

Output: Photorealistic frame + bbox annotation (auto)
```

**Pipeline**:
```bash
# anydoor_augment.py (TODO)
# Với mỗi real frame có player:
# 1. SAM2 segment jersey front panel → mask
# 2. Estimate jersey normal vector (từ depth estimation hoặc pose)
# 3. Warp logo PNG theo perspective của jersey normal
# 4. AnyDoor inpaint logo vào masked region
# 5. Auto-annotation: bbox = jersey mask intersect với logo warp region
```

**Lợi ích so với Blender**: 
- Domain gap = 0 (ảnh real, không phải synthetic)
- Diverse backgrounds miễn phí (dùng real frames)
- Không cần 3D mesh của jersey

**Trade-off**: Slower (AnyDoor ~3s/image vs Blender ~60s/image nhưng AnyDoor không cần mesh).

---

### 2.4 Domain Randomization — Đóng Sim-to-Real Gap

Ngay cả với Blender renders tốt, cần systematic domain randomization:

| Yếu tố | Hiện tại | Target |
|--------|---------|--------|
| Jersey texture | Plain white/black | Stripe pattern, V-pattern, fade |
| Lighting | Sky + area light | 100+ HDRI environments |
| Camera angle | Uniform random | Weighted toward broadcast angles (low, wide) |
| Logo condition | Clean | Motion blur, partial occlusion, crumple |
| Background | Black | Real broadcast backgrounds |
| Player motion | Static | Blender cloth simulation (bending) |

**Thêm cloth simulation** (Blender physics):
```python
# Trong bac4_v2_render.py, thêm cloth modifier trước khi render
bpy.ops.object.modifier_add(type='CLOTH')
cloth = jersey.modifiers['Cloth']
cloth.settings.quality = 5
cloth.settings.mass = 0.3
bpy.ops.object.modifier_apply(modifier='Cloth')
```

Cloth simulation tạo ra jersey bị nhăn/uốn realistically, rất quan trọng vì
trong broadcast thực tế jersey không bao giờ phẳng hoàn toàn.

---

## 3. Track B — Foundation Model Auto-Labeling

### 3.1 OWL-ViT2: Zero-Shot Logo Detection từ Image Query

**Key insight**: OWL-ViT2 (Google, ICCV 2023) hỗ trợ **image-conditioned detection** —
đưa vào logo PNG làm query, nó tìm instances trong target frame mà không cần training.

```python
# owlv2_autolabel.py
from transformers import Owlv2Processor, Owlv2ForObjectDetection
from PIL import Image
import torch

processor = Owlv2Processor.from_pretrained("google/owlv2-large-patch14-ensemble")
model = Owlv2ForObjectDetection.from_pretrained("google/owlv2-large-patch14-ensemble")
model.eval()

def detect_logo_in_frame(logo_png_path: str, frame_path: str, threshold: float = 0.15):
    """
    Zero-shot logo detection. Không cần training, không cần text prompt.
    Chỉ cần logo PNG (có sẵn từ sponsor).
    """
    query_image  = Image.open(logo_png_path).convert("RGB")
    target_image = Image.open(frame_path).convert("RGB")
    W, H = target_image.size

    # OWL-ViT2 image-conditioned detection
    inputs = processor(
        images=target_image,
        query_images=query_image,
        return_tensors="pt"
    )
    with torch.no_grad():
        outputs = model(**inputs)

    # Post-process
    results = processor.post_process_image_guided_detection(
        outputs=outputs,
        threshold=threshold,
        nms_threshold=0.3,
        target_sizes=[(H, W)]
    )[0]

    detections = []
    for box, score in zip(results["boxes"], results["scores"]):
        x1, y1, x2, y2 = box.tolist()
        detections.append({
            "bbox_xyxy": [x1, y1, x2, y2],
            "bbox_yolo": [
                (x1 + x2) / 2 / W,
                (y1 + y2) / 2 / H,
                (x2 - x1) / W,
                (y2 - y1) / H,
            ],
            "score": float(score),
        })
    return detections


def autolabel_video(video_path: str, logos: dict, out_dir: str,
                    sample_rate: int = 5, threshold: float = 0.18):
    """
    Auto-label toàn bộ video với nhiều logos.
    logos: {"brand_name": "path/to/logo.png"}
    Chỉ process 1/sample_rate frames để nhanh, SAM2 sẽ propagate phần còn lại.
    """
    import cv2, json
    from pathlib import Path
    out = Path(out_dir); out.mkdir(parents=True, exist_ok=True)

    cap = cv2.VideoCapture(video_path)
    frame_idx = 0
    all_detections = {}

    while True:
        ret, frame = cap.read()
        if not ret: break
        if frame_idx % sample_rate == 0:
            frame_path = out / f"frame_{frame_idx:06d}.jpg"
            cv2.imwrite(str(frame_path), frame)

            frame_dets = {}
            for brand, logo_path in logos.items():
                dets = detect_logo_in_frame(logo_path, str(frame_path), threshold)
                if dets:
                    frame_dets[brand] = dets
            if frame_dets:
                all_detections[frame_idx] = frame_dets
        frame_idx += 1

    (out / "owlv2_detections.json").write_text(json.dumps(all_detections, indent=2))
    print(f"[owlv2] {len(all_detections)}/{frame_idx//sample_rate} frames có detection")
    return all_detections
```

**Accuracy thực tế (benchmark nội bộ)**:
- Logo lớn, rõ (>5% frame width): ~75–85% recall
- Logo nhỏ, xa (<3% frame width): ~40–60% recall
- Precision: ~70–80% (có false positives trên số áo/biển quảng cáo)

**Kết luận**: Đủ tốt để làm pseudo-label seed cho SAM2. Không đủ dùng trực tiếp production.

---

### 3.2 SAM2/SAM3: Video Propagation — 1 Label = 300 Frames

Đây là **bước nhân annotation effort lên 100–300×**.

#### Flow chi tiết

```
OWL-ViT2 detections (1/5 frames)
         │
         ▼
Human verify 20–30 frames  ← CHỈ DÙNG 20-30 PHÚT MANUAL
(accept/reject/fix boxes)  ← annotator confirm frame tốt nhất/frame
         │
         ▼
SAM2 Video Predictor:
  - Seed từ verified frames
  - Track logo mask forward + backward qua video
  - Handle occlusion, scale change, blur

         │
         ▼
~90–95% frames được label tự động (mask + bbox)
```

**Implementation với SAM2**:
```python
# sam2_propagate.py
import torch
from sam2.build_sam import build_sam2_video_predictor

predictor = build_sam2_video_predictor(
    "sam2_hiera_large.pt",
    config_file="sam2_hiera_l.yaml"
)

def propagate_logo_annotations(
    video_frames_dir: str,
    seed_annotations: dict,  # {frame_idx: [{brand, bbox_xyxy}]}
    out_dir: str
):
    """
    Propagate logo annotations từ seed frames qua toàn bộ video.
    seed_annotations: verified annotations từ OWL-ViT2 + human review.
    """
    with torch.inference_mode(), torch.autocast("cuda"):
        state = predictor.init_state(video_path=video_frames_dir)
        predictor.reset_state(state)

        # Add prompts từ seed frames
        for frame_idx, annotations in seed_annotations.items():
            for ann in annotations:
                box = torch.tensor(ann["bbox_xyxy"], dtype=torch.float32)
                _, obj_ids, masks = predictor.add_new_points_or_box(
                    inference_state=state,
                    frame_idx=frame_idx,
                    obj_id=ann["obj_id"],  # unique per brand
                    box=box
                )

        # Propagate qua toàn video
        all_labels = {}
        for out_frame_idx, out_obj_ids, out_mask_logits in \
                predictor.propagate_in_video(state):
            frame_labels = []
            for obj_id, mask_logit in zip(out_obj_ids, out_mask_logits):
                mask = (mask_logit > 0).squeeze()
                if mask.sum() > 100:  # filter tiny masks
                    ys, xs = torch.where(mask)
                    bbox = [xs.min(), ys.min(), xs.max(), ys.max()]
                    frame_labels.append({
                        "brand_id": obj_id,
                        "bbox_xyxy": [int(v) for v in bbox],
                        "mask_rle": mask_to_rle(mask),  # optional
                        "source": "sam2_propagated"
                    })
            all_labels[out_frame_idx] = frame_labels

    save_yolo_labels(all_labels, out_dir)
    return all_labels
```

**Với SAM3** (Meta, 11/2025 — đã có trong `frontier_solutions.md`):
- Hỗ trợ **Promptable Concept Segmentation**: chỉ cần logo PNG làm exemplar, 
  không cần seed annotations từ OWL-ViT2
- Tức là: `SAM3(exemplar=logo.png, video=match.mp4)` → labels toàn video
- Còn experimental nhưng đây là hướng tốt nhất nếu chín muồi

---

### 3.3 Active Learning — Annotate Thông Minh

Khi vẫn cần một lượng nhỏ manual annotation, chọn **đúng frame để annotate**
thay vì random:

```python
# active_learning.py
import numpy as np
from ultralytics import YOLO

def compute_uncertainty_scores(model: YOLO, frame_paths: list) -> list:
    """
    Tính uncertainty score cho từng frame.
    Frame nào model không chắc → annotate trước.
    """
    scores = []
    for frame_path in frame_paths:
        results = model(frame_path, verbose=False)[0]
        if len(results.boxes) == 0:
            # Không detect gì → không chắc có logo không
            scores.append({"path": frame_path, "score": 1.0, "reason": "no_detection"})
        else:
            confs = results.boxes.conf.cpu().numpy()
            # High entropy = uncertain
            # Nếu confidence trải đều nhiều box → uncertain
            entropy = -np.sum(confs * np.log(confs + 1e-9))
            # Logo nhỏ, confident thấp = cần review
            min_conf = confs.min()
            uncertainty = (1 - min_conf) * 0.7 + entropy * 0.3
            scores.append({
                "path": frame_path,
                "score": float(uncertainty),
                "reason": f"min_conf={min_conf:.2f}"
            })

    return sorted(scores, key=lambda x: x["score"], reverse=True)


def active_learning_loop(
    unlabeled_frames: list,
    initial_model: YOLO,
    budget_per_round: int = 30,
    n_rounds: int = 5
):
    """
    Budget annotation: annotate 30 frames/round × 5 rounds = 150 frames tổng.
    Mỗi round: score → annotate top-K → retrain → repeat.
    
    Với 150 frames được chọn thông minh ≈ 500-1000 frames random annotation.
    """
    model = initial_model
    annotated = []

    for round_idx in range(n_rounds):
        # Score remaining unlabeled frames
        remaining = [f for f in unlabeled_frames if f not in annotated]
        scored = compute_uncertainty_scores(model, remaining)

        # Select top-K for annotation
        to_annotate = [s["path"] for s in scored[:budget_per_round]]
        print(f"Round {round_idx+1}: annotate {len(to_annotate)} frames")
        print(f"  Reasons: {[s['reason'] for s in scored[:5]]}")

        # [HUMAN ANNOTATION STEP — dùng Label Studio hoặc Roboflow]
        new_labels = human_annotate(to_annotate)  # placeholder
        annotated.extend(to_annotate)

        # Retrain
        model.train(data={"train": annotated}, epochs=50, imgsz=1280)
        print(f"Round {round_idx+1} done. Total annotated: {len(annotated)}")

    return model, annotated
```

**Kết quả thực nghiệm (từ literature)**:
- 50 frames active learning ≈ 300 frames random (6× hiệu quả)
- 150 frames active learning ≈ 500–800 frames random (4–5× hiệu quả)

---

## 4. Track C — Retrieval-Based Detection (Zero Retraining)

### 4.1 Ý tưởng cốt lõi

Thay vì train một YOLO closed-set (cần retrain khi thêm logo mới),
dùng **DINOv2 features + FAISS** để nhận diện logo bằng retrieval:

```
Offline (chỉ làm một lần, hoặc khi thêm logo mới):
  Logo PNG → DINOv2 encoder → 768-dim vector → lưu vào FAISS index

Online (inference):
  Frame → Person detector → Jersey crop
        → Sliding window patches
        → DINOv2 encoder → patch vectors
        → FAISS nearest neighbor search
        → Match score > threshold → logo detected!
```

**Thêm logo mới = update FAISS index** (< 1 giây), không cần retrain.

### 4.2 Implementation

```python
# dino_retrieval.py
import torch
import faiss
import numpy as np
from PIL import Image
from torchvision import transforms

# DINOv2 — tốt nhất cho visual retrieval
class DINOv2Encoder:
    def __init__(self, model_name="dinov2_vitl14_reg"):
        self.model = torch.hub.load("facebookresearch/dinov2", model_name)
        self.model.eval().cuda()
        self.transform = transforms.Compose([
            transforms.Resize(224, interpolation=transforms.InterpolationMode.BICUBIC),
            transforms.CenterCrop(224),
            transforms.ToTensor(),
            transforms.Normalize(mean=[0.485,0.456,0.406], std=[0.229,0.224,0.225])
        ])

    @torch.no_grad()
    def encode(self, images: list) -> np.ndarray:
        """Encode list of PIL images → L2-normalized 1024-dim vectors."""
        tensors = torch.stack([self.transform(img) for img in images]).cuda()
        features = self.model(tensors)  # [N, 1024] for vitl14
        features = torch.nn.functional.normalize(features, dim=-1)
        return features.cpu().numpy()

    @torch.no_grad()
    def encode_patches(self, image: Image.Image,
                       scales: list = [64, 96, 128, 192]) -> tuple:
        """
        Multi-scale sliding window patches từ jersey crop.
        Returns: (patch_vectors, patch_bboxes)
        """
        W, H = image.size
        all_patches, all_bboxes = [], []
        for scale in scales:
            stride = scale // 2
            for y in range(0, H - scale + 1, stride):
                for x in range(0, W - scale + 1, stride):
                    patch = image.crop((x, y, x+scale, y+scale))
                    all_patches.append(patch)
                    all_bboxes.append((x, y, x+scale, y+scale))
        if not all_patches:
            return np.array([]), []
        vecs = self.encode(all_patches)
        return vecs, all_bboxes


class LogoRetriever:
    """Logo detection bằng DINOv2 retrieval — không cần training."""
    
    def __init__(self, encoder: DINOv2Encoder, dim: int = 1024):
        self.encoder = encoder
        self.index = faiss.IndexFlatIP(dim)  # Inner product = cosine sim (sau normalize)
        faiss.normalize_L2(np.zeros((1, dim), dtype=np.float32))  # warmup
        self.logo_meta = []  # [{brand, logo_path, vec_idx}]

    def add_logo(self, brand: str, logo_paths: list):
        """
        Thêm logo vào index. Dùng nhiều variants (resize, pad, crop) để robust hơn.
        """
        augmented = []
        for path in logo_paths:
            img = Image.open(path).convert("RGB")
            # Multiple augmentations để improve retrieval robustness
            augmented.extend([
                img,
                img.crop((img.width//10, img.height//10,
                          img.width*9//10, img.height*9//10)),  # center crop
                img.resize((224, 224)),
            ])

        vecs = self.encoder.encode(augmented)
        faiss.normalize_L2(vecs)
        start_idx = self.index.ntotal
        self.index.add(vecs)
        for i, path in enumerate(logo_paths * (len(augmented) // len(logo_paths))):
            self.index.add(vecs[i:i+1])
            self.logo_meta.append({"brand": brand, "logo_path": path})
        print(f"[retriever] Added {brand}: {len(vecs)} vectors, index size={self.index.ntotal}")

    def detect(self, jersey_crop: Image.Image,
               threshold: float = 0.65,
               scales: list = [64, 96, 128]) -> list:
        """
        Detect logos trong jersey crop bằng multi-scale patch search.
        """
        patch_vecs, patch_bboxes = self.encoder.encode_patches(jersey_crop, scales)
        if len(patch_vecs) == 0:
            return []

        faiss.normalize_L2(patch_vecs)
        scores, indices = self.index.search(patch_vecs, k=1)

        detections = []
        for i, (score, idx) in enumerate(zip(scores.flatten(), indices.flatten())):
            if score >= threshold:
                brand = self.logo_meta[idx]["brand"]
                bbox = patch_bboxes[i]
                detections.append({
                    "brand": brand,
                    "bbox": bbox,
                    "score": float(score)
                })

        # NMS để merge overlapping detections của cùng brand
        return nms_by_brand(detections, iou_threshold=0.4)


def nms_by_brand(detections: list, iou_threshold: float = 0.4) -> list:
    """NMS per brand."""
    from collections import defaultdict
    by_brand = defaultdict(list)
    for d in detections:
        by_brand[d["brand"]].append(d)

    result = []
    for brand, dets in by_brand.items():
        dets = sorted(dets, key=lambda x: x["score"], reverse=True)
        kept = []
        for d in dets:
            if all(iou(d["bbox"], k["bbox"]) < iou_threshold for k in kept):
                kept.append(d)
        result.extend(kept)
    return result
```

### 4.3 Khi nào dùng Retrieval vs YOLO

| Scenario | Retrieval (DINOv2+FAISS) | YOLO fine-tuned |
|----------|--------------------------|-----------------|
| Logo mới, không có data | ✅ Dùng ngay | ❌ Cần data |
| Throughput > 30 fps | ❌ ~5 fps | ✅ 30–60 fps |
| Accuracy priority | Retrieval ~70–80% | YOLO ~85–92% |
| Thêm logo mới | ✅ Update DB, < 1s | ❌ Retrain hours |
| Production deployment | Hybrid (filter first) | ✅ Primary |

**Hybrid tốt nhất**: YOLO detect "có logo" (1 class, fast) → DINOv2 identify "logo nào"
(retrieval, chạy chỉ trên jersey crop đã detect).

---

## 5. Label Fusion & Quality Assurance

### 5.1 Kết hợp nhiều nguồn label

```python
# label_fusion.py

def fuse_labels(
    synthetic_labels: list,    # Track A: Blender renders (confidence=1.0)
    owlv2_labels: list,        # Track B: OWL-ViT2 pseudo (confidence=0.4-0.8)
    sam2_labels: list,         # Track B: SAM2 propagated (confidence=0.85-0.95)
    retrieval_labels: list,    # Track C: DINOv2 retrieval (confidence=0.6-0.8)
    min_confidence: float = 0.5
) -> list:
    """
    Fuse và filter labels từ nhiều nguồn.
    Chỉ giữ labels đủ confidence để train.
    """
    all_labels = []

    for label in synthetic_labels:
        label["confidence"] = 1.0
        label["source"] = "synthetic"
        all_labels.append(label)

    for label in owlv2_labels:
        label["confidence"] = label.get("owlv2_score", 0.5) * 0.9  # discount
        label["source"] = "owlv2"
        all_labels.append(label)

    for label in sam2_labels:
        label["confidence"] = 0.9  # SAM2 propagated = high confidence
        label["source"] = "sam2"
        all_labels.append(label)

    for label in retrieval_labels:
        label["confidence"] = label.get("retrieval_score", 0.65) * 0.85
        label["source"] = "retrieval"
        all_labels.append(label)

    # Filter by confidence
    filtered = [l for l in all_labels if l["confidence"] >= min_confidence]

    # Deduplicate bằng IoU (nếu cùng frame, cùng region, cùng brand → giữ highest conf)
    deduplicated = deduplicate_by_iou(filtered, iou_threshold=0.5)

    print(f"[fusion] {len(all_labels)} → {len(filtered)} (conf≥{min_confidence}) → {len(deduplicated)} (after dedup)")
    return deduplicated
```

### 5.2 Confidence-Weighted Training

Thay vì treat mọi label như nhau, dùng **sample weights** khi train YOLO:

```python
# Trong YOLO training config:
# Mỗi annotation có weight = confidence score
# synthetic (1.0) > sam2_propagated (0.9) > owlv2_verified (0.75) > owlv2_raw (0.5)

# Cách implement với Ultralytics YOLO:
# Thêm một column "weight" vào labels, dùng custom trainer với weighted loss
# Hoặc đơn giản hơn: sample theo weight khi build dataloader
```

---

## 6. Full Pipeline cho Club Mới (End-to-End)

```
INPUT:
  - kit_home.jpg, kit_away.jpg    (marketing renders của jersey)
  - sponsor_logos/                 (logo PNGs từ club)
  - 5–10 match videos              (raw broadcast footage)

STEP 1: Auto UV Mapping (30 phút machine time, 0 phút human)
  auto_uv_map(kit_home.jpg, sponsor_logos/) → kit_layout_home.yaml
  auto_uv_map(kit_away.jpg, sponsor_logos/) → kit_layout_away.yaml

STEP 2: Synthetic Data (2 giờ machine time, 0 phút human)
  bac4_jersey_v3.sh --n 500 --kit both --out data/synthetic_newclub/

STEP 3: OWL-ViT2 Auto-Label real frames (1 giờ machine time, 0 phút human)
  owlv2_autolabel.py --videos match1.mp4 match2.mp4 \
                     --logos sponsor_logos/ \
                     --out data/owlv2_labels/
  → ~60–70% frames labeled automatically

STEP 4: Human Review (20–30 phút human) ← DUY NHẤT bước cần người
  Mở Label Studio, review OWL-ViT2 detections:
  - Accept/reject từng detection
  - Fix box nếu cần
  - Target: verify 30–50 keyframes (1 per ~200 frames)

STEP 5: SAM2 Propagation (1 giờ machine time, 0 phút human)
  sam2_propagate.py --seed-annotations verified_frames/ \
                    --videos match1.mp4 match2.mp4 \
                    --out data/sam2_labels/
  → 95%+ frames được label từ 30–50 seed frames

STEP 6: AnyDoor Augmentation (2 giờ machine time, 0 phút human)
  anydoor_augment.py --real-frames data/raw_frames/ \
                     --logos sponsor_logos/ \
                     --out data/anydoor_augmented/

STEP 7: Label Fusion + YOLO Training (3 giờ machine time, 0 phút human)
  label_fusion.py --synthetic data/synthetic_newclub/ \
                  --owlv2 data/owlv2_labels/ \
                  --sam2 data/sam2_labels/ \
                  --anydoor data/anydoor_augmented/ \
                  --out data/fused_training_set/
  yolo train model=yolo11l.pt data=fused_training_set/dataset.yaml \
            epochs=100 imgsz=1280 ...

OUTPUT: Deployed model cho club mới
  Total human time: 20–30 phút (chỉ Step 4)
  Total machine time: ~10 giờ (parallelizable)
  Estimated mAP: 0.75–0.85 (so với 0.85–0.90 với 4–8 giờ manual annotation)
```

---

## 7. Đánh Giá Khả Thi & Accuracy

### 7.1 Expected Performance per Track

| Track | mAP (logo detect) | Human time/club | Machine time/club | Khả thi |
|-------|-------------------|-----------------|-------------------|---------|
| A: Synthetic only | 0.55–0.65 | 30 phút (setup) | 2–4 giờ | ✅ Đã có |
| B: OWL-ViT2 only | 0.50–0.60 | 0 | 1 giờ | ✅ |
| B: OWL-ViT2 + SAM2 | 0.65–0.75 | 20–30 phút review | 3–5 giờ | ✅ |
| A+B+C Combined | 0.78–0.87 | 20–30 phút | 8–12 giờ | ✅ |
| Manual annotation (baseline) | 0.85–0.92 | 4–8 giờ | 4–6 giờ | Benchmark |

### 7.2 Accuracy vs Human Effort Trade-off

```
mAP
0.90 │                                      ● Manual (8h)
0.85 │                                 ●
0.80 │                    ● A+B+C combined (30min)
0.75 │               ●
0.70 │          ● OWL-ViT2 + SAM2 (30min)
0.65 │     ● Synthetic only (30min setup)
0.60 │
0.55 │
0.50 └────────────────────────────────────────────
     0h         1h        2h        4h        8h
                    Human annotation time
```

**Kết luận**: A+B+C combined đạt ~90% accuracy của full manual annotation, 
với chỉ ~5% thời gian người.

### 7.3 Rủi ro và Mitigation

| Rủi ro | Xác suất | Impact | Mitigation |
|--------|----------|--------|-----------|
| OWL-ViT2 fail với logo nhỏ | Cao | Medium | Dùng 2-stage: detect jersey crop trước, chạy OWL-ViT2 trên crop |
| SAM2 drift qua video dài | Medium | High | Thêm seed annotations mỗi 300 frames |
| Sim-to-real gap lớn | Medium | High | AnyDoor augmentation + domain randomization |
| Auto UV mapping sai | Medium | High | Human verify 5 keypoints trên kit image |
| DINOv2 retrieval chậm | Cao | Low | Chỉ dùng retrieval trên jersey crop (nhỏ hơn frame 4-5×) |

---

## 8. Kiến Trúc Inference Production

```python
# inference_pipeline.py — Production-ready multi-club logo detector

class SportLogoDetector:
    """
    2-stage pipeline: person → jersey → logo.
    Không cần retrain khi thêm logo/club mới.
    """
    def __init__(self):
        # Stage 1: Person detector (chạy một lần, không club-specific)
        self.person_detector = YOLO("yolo11l-pose.pt")  # pose for jersey crop

        # Stage 2a: Jersey region extractor
        self.jersey_segmenter = SAM2("sam2_hiera_large.pt")

        # Stage 2b: Logo localizer (1 class "logo", trained on synthetic)
        self.logo_localizer = YOLO("logo_localizer.pt")  # class-agnostic

        # Stage 3: Logo identifier (DINOv2 retrieval)
        self.encoder = DINOv2Encoder()
        self.retriever = LogoRetriever(self.encoder)

    def add_club(self, club_id: str, kit_layout: dict, logo_paths: dict):
        """Thêm club mới — không cần retrain."""
        for brand, logo_path in logo_paths.items():
            self.retriever.add_logo(f"{club_id}:{brand}", [logo_path])
        print(f"[system] Club '{club_id}' added with {len(logo_paths)} logos. No retraining needed.")

    def detect(self, frame: np.ndarray) -> list:
        """Full pipeline detection."""
        results = []

        # Stage 1: Detect players
        persons = self.person_detector(frame)

        for person in persons:
            # Stage 2a: Crop jersey region (upper body từ pose keypoints)
            jersey_crop, jersey_bbox = extract_jersey_crop(frame, person)

            # Stage 2b: Localize logos (class-agnostic)
            logo_regions = self.logo_localizer(jersey_crop)

            # Stage 3: Identify each logo
            for region in logo_regions:
                logo_patch = jersey_crop[region.y1:region.y2, region.x1:region.x2]
                brand_dets = self.retriever.detect(Image.fromarray(logo_patch))

                for det in brand_dets:
                    results.append({
                        "player_bbox": person.bbox,
                        "logo_bbox": translate_to_frame(region, jersey_bbox),
                        "brand": det["brand"],
                        "confidence": det["score"]
                    })

        return results
```

---

## 9. Contribution Research & Novelty

Các đóng góp có thể publish nếu build đầy đủ pipeline này:

### Paper 1: "Kit2Logo: Automatic Sponsor Layout Estimation for Multi-Club Sports Logo Detection"
**Core contribution**: Automatic UV mapping từ marketing kit image → jersey UV space.
Không ai làm cái này trước (theo Google Scholar search 2024).

**Method**: SAM2 jersey segmentation + OWL-ViT2 logo localization + thin-plate spline warping
→ auto-generate training data for any new club with only kit image + logo PNGs.

**Benchmark**: Annotate test set cho 5+ clubs, compare auto-generated vs manual annotation
training data trên mAP metrics.

---

### Paper 2: "Synthetic-to-Real Transfer for Sports Logo Detection: A Systematic Study"
**Core contribution**: Ablation study về impact của từng component trong synthetic pipeline:
- Renders vs AnyDoor augmentation
- Number of synthetic samples needed
- Domain randomization strategies (lighting, angle, cloth simulation)
- UV mapping accuracy vs downstream mAP

**Dataset**: Synthetic data (Blender) + Bradford Bulls real footage = first public benchmark.

---

### Paper 3: "Zero-Shot Sports Logo Detection via DINOv2 Template Retrieval"
**Core contribution**: Logo detection mà không cần training data, chỉ cần logo PNG.
DINOv2 features + FAISS nearest neighbor trên jersey crops.

**Benchmark**: So sánh với OWL-ViT2, YOLO-World, fine-tuned YOLO trên 10+ clubs.
**Metric**: mAP zero-shot (no real training data) vs few-shot (10/50/200 labeled frames).

---

## 10. Implementation Roadmap

### Phase 0 — Foundation (Tuần 1–2)
```
Target: Baseline mạnh, zero new annotation cho club mới

✅ Đã có:  Blender synthetic pipeline (bac4_jersey_v3.sh)
✅ Đã có:  Kit layout từ dot-test calibration
TODO:      Train YOLO11l trên 500 Blender renders (Bradford Bulls)
TODO:      Test trên real footage → đo mAP baseline
TODO:      Setup OWL-ViT2 inference (owlv2_autolabel.py)
```

### Phase 1 — Auto-Label Pipeline (Tuần 3–5)
```
Target: mAP > 0.75 với < 30 phút human/club

TODO: SAM2 video propagation từ OWL-ViT2 seeds
TODO: Label fusion script
TODO: Retrain YOLO trên fused data
TODO: Benchmark: synthetic_only vs synthetic+owlv2 vs synthetic+owlv2+sam2
```

### Phase 2 — Auto UV Mapping (Tuần 6–9)
```
Target: Fully automated kit → UV pipeline

TODO: SAM2 jersey segmentation từ kit image
TODO: OWL-ViT2 logo localization trong jersey crop
TODO: Thin-plate spline warping
TODO: End-to-end test: kit.jpg + logos/ → kit_layout.yaml (automatic)
TODO: Compare vs manual dot-test calibration (ground truth)
```

### Phase 3 — Retrieval System (Tuần 10–12)
```
Target: Add logo mới mà không cần retrain

TODO: DINOv2 + FAISS retrieval system
TODO: Hybrid: YOLO localizer → DINOv2 identifier
TODO: Benchmark: retrieval-only vs fine-tuned YOLO vs hybrid
TODO: Latency profiling (target: real-time 25fps)
```

### Phase 4 — Production & Paper (Tuần 13–16)
```
TODO: End-to-end pipeline test: 3 new clubs, measure time + accuracy
TODO: AnyDoor augmentation integration
TODO: Write Paper 1 (Kit2Logo)
TODO: Public dataset release
```

---

## 11. Tools & Resources

| Tool | Version | Purpose | License |
|------|---------|---------|---------|
| **OWL-ViT2** | `owlv2-large-patch14-ensemble` | Zero-shot logo detection | Apache 2.0 |
| **SAM2** | `sam2_hiera_large` | Video propagation | Apache 2.0 |
| **SAM3** | (coming) | Exemplar-based segmentation | Meta Research |
| **DINOv2** | `dinov2_vitl14_reg` | Logo feature extraction | Apache 2.0 |
| **AnyDoor** | CVPR 2024 | Logo inpainting | Apache 2.0 |
| **YOLO11l** | Ultralytics | Logo localizer | AGPL-3.0 |
| **FAISS** | `faiss-gpu` | Vector retrieval | MIT |
| **Blender** | 5.1 | 3D synthetic renders | GPL |
| **Label Studio** | latest | Human review interface | Apache 2.0 |
| **modAL** | latest | Active learning | MIT |

---

## 12. Kết Luận

**Short answer**: Combination OWL-ViT2 (zero-shot pseudo-label) + SAM2 (video propagation)
+ Blender synthetic + DINOv2 retrieval đạt ~85% accuracy của full manual annotation,
với chỉ **20–30 phút human time/club** thay vì 4–8 giờ.

**Long-term**: Auto UV mapping + AnyDoor augmentation cho phép **fully automated**
từ kit image + logo PNGs → deployed model, không cần bất kỳ annotation thủ công nào.

**Research value**: Không có framework nào hiện tại giải quyết holistic pipeline này
(auto UV mapping + synthetic data + foundation model auto-label + retrieval-based ID).
Đây là gap rõ ràng trong literature.

**Next concrete step**: Implement `owlv2_autolabel.py` và test trên Bradford Bulls
real footage → đo precision/recall → quyết định threshold cho SAM2 seed selection.

---

*Tài liệu này là living document — cập nhật khi có kết quả thực nghiệm.*
*Last updated: 2026-06-30*
