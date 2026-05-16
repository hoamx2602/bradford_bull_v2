# v5 Deep Dive — Technical clarifications

> **Phụ lục cho** `SOLUTION_ARCHITECTURE_V5.md`
> **Ngày:** 2026-05-16
> **Phạm vi:** Giải thích sâu (1) DINOv2 embedding nearest-neighbor cho brand classification (Stage 3B), (2) SAM 2 propagation cho auto-annotation (Stage 2B). Bao gồm pseudocode, limitations, spot-check protocol, fallback strategy.

---

## 📑 Mục lục

- [Phần 1: DINOv2 Nearest-Neighbor cho brand classification](#phần-1-dinov2-nearest-neighbor-cho-brand-classification)
- [Phần 2: SAM 2 propagation cho auto-annotation](#phần-2-sam-2-propagation-cho-auto-annotation)
- [Phần 3: Decision tree — khi nào dùng cái gì](#phần-3-decision-tree--khi-nào-dùng-cái-gì)

---

## Phần 1: DINOv2 Nearest-Neighbor cho brand classification

### 1.1 Vấn đề và intuition

**Vấn đề:** Trong v5, Stage 3A detector chỉ output "có logo ở vị trí này" (binary, không biết brand nào). Stage 3B phải classify: logo này là MCP hay AON hay KLG?

**Cách truyền thống (v4):** Train một YOLO multi-class với 21 head — model học classify trực tiếp. Vấn đề: thêm sponsor mới = thêm 1 head → retrain toàn bộ.

**Cách mới (v5):** Tách classify thành 2 bước:
1. **Build reference bank:** Convert mỗi logo file trong `/Sponsor Logo/` thành 1 "embedding vector" — 1 dãy số 768 hoặc 1024 chiều đặc trưng cho visual identity của logo đó
2. **Runtime:** Lấy 1 crop logo từ frame thực tế → convert thành embedding cùng cách → so sánh với tất cả embeddings trong bank → trả về brand gần nhất

**Intuition:** Hai logo trông giống nhau → embeddings gần nhau trong không gian vector. Hai logo khác nhau → embeddings xa nhau. **DINOv2** (Meta, 2023) đã được pretrained trên 142M images để học cách "trông giống" → out-of-the-box dùng được cho tasks như logo, không cần fine-tune cho v1.

### 1.2 Pseudocode đầy đủ

#### A. Build reference bank (offline, 1 lần, ~30 giây compute)

```python
"""
File: src/embedding/build_reference_bank.py

Tạo reference bank từ tất cả logo files trong /Sponsor Logo/.
Mỗi brand có thể có nhiều variants (color, orientation) → nhiều references.
"""

import torch
import numpy as np
from PIL import Image
from torchvision import transforms
from pathlib import Path

# Load DINOv2 — chỉ làm 1 lần, cache vào memory
# Choice: "dinov2_vitb14" (Base, 88M params, 768-dim) — balance speed/accuracy
# Alternative: "dinov2_vitl14" (Large, 300M, 1024-dim) — slower but more accurate
model = torch.hub.load("facebookresearch/dinov2", "dinov2_vitb14")
model.eval().cuda()

# DINOv2 expects 224×224, ImageNet-normalized
preprocess = transforms.Compose([
    transforms.Resize(256),
    transforms.CenterCrop(224),
    transforms.ToTensor(),
    transforms.Normalize(
        mean=[0.485, 0.456, 0.406],
        std=[0.229, 0.224, 0.225]
    ),
])

def compute_embedding(image_path: Path) -> np.ndarray:
    """Embed 1 image → 768-dim vector (L2-normalized)."""
    img = Image.open(image_path).convert("RGB")
    x = preprocess(img).unsqueeze(0).cuda()  # (1, 3, 224, 224)
    with torch.no_grad():
        feat = model(x)                       # (1, 768)
    feat = feat.cpu().numpy()[0]              # (768,)
    feat = feat / np.linalg.norm(feat)        # L2 normalize → cosine sim = dot product
    return feat

# Build bank
sponsor_logo_dir = Path("/Users/hoamai/Bradford/bradford_bulls_v2/Sponsor Logo")
bank = {}  # {brand_key: [(variant_name, embedding), ...]}

for logo_file in sorted(sponsor_logo_dir.glob("*")):
    if logo_file.suffix.lower() not in {".jpg", ".jpeg", ".png"}:
        continue
    if logo_file.stat().st_size == 0:  # Skip romantica_black.jpg (0-byte)
        continue
    
    # Map filename → brand class_code (per v5 §6 taxonomy)
    brand_key = map_filename_to_brand_key(logo_file.name)
    # e.g., "1 - aon_logo_signature_red_rgb.png" → "aon_red"
    
    emb = compute_embedding(logo_file)
    
    bank.setdefault(brand_key, []).append({
        "variant_name": logo_file.name,
        "embedding": emb,
        "source": "official_logo",
    })

# Save
np.savez_compressed("reference_bank.npz", **{
    f"{k}__{i}": v["embedding"]
    for k, vs in bank.items()
    for i, v in enumerate(vs)
})
```

#### B. Runtime: classify a detected crop

```python
"""
File: src/embedding/classify_brand.py

Runtime: cho 1 logo crop từ Stage 3A detector, trả về brand prediction.
"""

import numpy as np

class BrandClassifier:
    def __init__(self, bank_path: str, conf_threshold: float = 0.6):
        # Load reference bank
        data = np.load(bank_path)
        self.embeddings = []   # (N, 768)
        self.labels = []       # (N,) — brand_key per entry
        
        for key in data.files:
            brand_key = key.rsplit("__", 1)[0]  # strip "__0", "__1"
            self.embeddings.append(data[key])
            self.labels.append(brand_key)
        
        self.embeddings = np.stack(self.embeddings)  # (N, 768)
        self.labels = np.array(self.labels)
        self.conf_threshold = conf_threshold
    
    def classify(self, crop_embedding: np.ndarray) -> dict:
        """
        Input: crop_embedding (768,) L2-normalized
        Output: {"brand": str, "confidence": float, "top_5": [...]}
        """
        # Cosine similarities (vì đã L2-normalized, cosine = dot product)
        sims = self.embeddings @ crop_embedding  # (N,)
        
        # Aggregate per-brand (max similarity across variants)
        brand_to_max_sim = {}
        for label, sim in zip(self.labels, sims):
            brand_to_max_sim[label] = max(
                brand_to_max_sim.get(label, -1.0), 
                sim
            )
        
        # Sort
        ranked = sorted(brand_to_max_sim.items(), key=lambda x: -x[1])
        top_brand, top_sim = ranked[0]
        second_brand, second_sim = ranked[1] if len(ranked) > 1 else (None, 0.0)
        
        # Confidence: margin between top-1 and top-2
        # High margin = confident; low margin = ambiguous
        margin = top_sim - second_sim
        
        # Decide
        if top_sim < self.conf_threshold:
            brand = "unknown"  # Below abs threshold → no match
        elif margin < 0.05:
            brand = "ambiguous"  # Top-1 and top-2 too close
        else:
            brand = top_brand
        
        return {
            "brand": brand,
            "top_1_brand": top_brand,
            "top_1_similarity": float(top_sim),
            "top_2_brand": second_brand,
            "top_2_similarity": float(second_sim),
            "margin": float(margin),
            "top_5": ranked[:5],
        }

# Usage in inference engine
classifier = BrandClassifier("reference_bank.npz", conf_threshold=0.6)

# For each detected logo OBB from Stage 3A:
crop = extract_obb_region(frame, bbox)  # extract rotated crop
crop_emb = compute_embedding_from_array(crop)  # DINOv2 forward
result = classifier.classify(crop_emb)

# Result:
# {
#   "brand": "mcp_home",          # or "unknown" / "ambiguous"
#   "top_1_brand": "mcp_home",
#   "top_1_similarity": 0.847,
#   "top_2_brand": "mcp_away",
#   "top_2_similarity": 0.620,
#   "margin": 0.227,
#   "top_5": [...]
# }
```

#### C. Adding a new sponsor (mid-season scenario)

```python
"""
Sponsor mới X ký với Bradford. Workflow:
"""

# Step 1: Add file to /Sponsor Logo/
new_logo_path = Path("/Users/hoamai/Bradford/bradford_bulls_v2/Sponsor Logo/22 - NewBrand.png")
# (user upload file vào folder)

# Step 2: Compute embedding
new_embedding = compute_embedding(new_logo_path)

# Step 3: Append to existing bank
existing = dict(np.load("reference_bank.npz"))
existing["newbrand__0"] = new_embedding
np.savez_compressed("reference_bank.npz", **existing)

# Step 4: Restart inference service (or hot-reload bank in service)
# Done. Model giờ detect được brand X.
# 0 retrain Stage 3A detection model.
# Total time: ~30 giây.
```

### 1.3 Tại sao approach này hoạt động

**Lý thuyết:** DINOv2 được train với "self-distillation" — không có labels, chỉ học representations sao cho 2 augmentations của cùng 1 image có embedding gần nhau, 2 images khác nhau xa nhau. Kết quả: embedding space rất tốt cho retrieval tasks.

**Bằng chứng từ paper:**
- DINOv2 k-NN classification trên ImageNet: 83.5% top-1 (DINOv2-Large)
- Out-of-domain transfer (logos, medical, satellite): vẫn cao mà không cần fine-tune

**Áp dụng cho logo:**
- Logo đặc thù visual (text + symbol cụ thể) → embedding sẽ discriminative
- Multiple variants (color, scale) → multiple references per brand → robust

### 1.4 Limitations và mitigation

| Limitation | Lý do | Mitigation |
|------------|-------|------------|
| Similar logos confuse | 2 brand cùng dùng text trắng-đen → embeddings gần nhau | (a) Contrastive fine-tuning, (b) ensemble với CLIP, (c) ngưỡng margin cao hơn |
| Heavily occluded crops | DINOv2 expect full object | Filter detector output: skip OBB nếu visible ratio < 60% |
| Very small crops (<32px) | DINOv2 input 224×224, upscale từ <32px lose info | Skip classification cho crops < threshold; tag as "small_logo" |
| New sponsor không cùng style với references | Reference từ official PNG, video có version stylized | Add multiple references per brand: official + crop từ video |
| Lighting/color shift gross | Embedding sensitive với color | Photometric augmentation in detector training; fine-tune classifier với augmented references |

### 1.5 Optional: Contrastive fine-tuning (Phase 2 enhancement)

Nếu accuracy < 90% với plain DINOv2, fine-tune:

```python
"""
Contrastive fine-tuning để improve discrimination cho domain-specific logos.
Lấy positive pairs (same brand) và hard negatives (different brand but similar visually).
Loss: InfoNCE / Triplet
"""

# Pseudocode
for batch in dataloader:
    anchor_crops = batch["anchor"]      # 1 reference per brand
    positive_crops = batch["positive"]  # crop từ video cùng brand
    negative_crops = batch["negative"]  # crop từ video brand khác (hard mined)
    
    anchor_emb = model(anchor_crops)
    positive_emb = model(positive_crops)
    negative_emb = model(negative_crops)
    
    # Triplet loss: pull positive close, push negative far
    loss = max(0, cos(anchor, negative) - cos(anchor, positive) + margin)
    
    loss.backward()
    optimizer.step()
```

Effort: ~1-2 ngày code + train, ~500 manually verified positive/negative pairs.

### 1.6 Spot-check protocol

**Trước khi deploy production, validate brand classification accuracy:**

```python
"""
Spot-check protocol cho Stage 3B (Brand classifier):

1. Tạo test set: 200 logo crops (chosen từ Stage 3A outputs trên held-out match)
   - 10 crops per brand (cố gắng cover all 22 classes)
   - Mix sharp + blur + occluded
2. Human label ground truth (gồm "unknown" cho crops không phải bất kỳ brand nào)
3. Run classifier, compute:
   - Top-1 accuracy per brand
   - Confusion matrix
   - Pass rate cho "unknown" detection (correctly identify out-of-distribution)
4. Pass criteria:
   - Overall top-1 ≥ 0.90
   - No brand below 0.70 (flag for re-train references hoặc data augmentation)
   - "unknown" precision ≥ 0.80 (không reject brand đã có trong bank)
"""

# Implementation
import json
from collections import defaultdict

test_set = load_test_set("validation/brand_test_200.jsonl")
classifier = BrandClassifier("reference_bank.npz")

results = []
confusion = defaultdict(lambda: defaultdict(int))

for sample in test_set:
    crop_emb = compute_embedding_from_array(sample["crop_image"])
    pred = classifier.classify(crop_emb)
    
    truth = sample["ground_truth_brand"]
    predicted = pred["brand"]
    
    confusion[truth][predicted] += 1
    results.append({
        "truth": truth,
        "predicted": predicted,
        "confidence": pred["top_1_similarity"],
        "margin": pred["margin"],
    })

# Compute per-brand top-1
per_brand_acc = {}
for brand in set(r["truth"] for r in results):
    brand_results = [r for r in results if r["truth"] == brand]
    correct = sum(1 for r in brand_results if r["predicted"] == brand)
    per_brand_acc[brand] = correct / len(brand_results)

# Report
print(f"Overall top-1: {sum(per_brand_acc.values())/len(per_brand_acc):.3f}")
print(f"Weakest brand: {min(per_brand_acc, key=per_brand_acc.get)}: {min(per_brand_acc.values()):.3f}")
print(f"Confusion matrix:")
for truth in confusion:
    for pred, count in confusion[truth].items():
        if truth != pred:
            print(f"  {truth} → {pred}: {count}")
```

### 1.7 Fallback strategy nếu DINOv2 approach không đủ tốt

Nếu spot-check accuracy < 0.85, fallback theo thứ tự ưu tiên:

**Fallback A: Contrastive fine-tuning (effort: 2 ngày)**
- Như §1.5
- Expect: tăng 5-10 percentage points

**Fallback B: Dual model (DINOv2 + CLIP)**
- Embed crop bằng cả DINOv2 (visual structure) + CLIP (semantic)
- Concatenate hoặc weighted-sum embeddings
- Source: [CLIP-DINOv2 fusion paper](https://www.mdpi.com/2079-9292/14/24/4785)

**Fallback C: Supervised classifier (full retreat)**
- Train một ResNet-50 classifier với 22 heads trên annotated crops
- Mất khả năng "thêm sponsor mới không retrain"
- Chỉ dùng nếu A và B đều fail

---

## Phần 2: SAM 2 propagation cho auto-annotation

### 2.1 Vấn đề và intuition

**Vấn đề:** Manual annotate frame là bottleneck. 1 frame có ~5-8 logos × 30 giây mỗi bbox = 3-4 phút/frame. 400 frames = 20-30 giờ human effort. Quá tốn.

**Insight:** Trong video, 1 logo trên áo cầu thủ A xuất hiện liên tục qua nhiều frames (mỗi giây = 30 frames). Nếu chúng ta annotate frame 100 → frames 95-105 đều có logo đó CÙNG vị trí (player chỉ di chuyển nhẹ). Có cách nào tự động transfer annotation?

**SAM 2** (Meta, August 2024) là model promptable segmentation với **memory bank**:
- Cho 1 prompt (point hoặc box) trên 1 keyframe → model output mask
- Memory bank lưu features của object → propagate mask sang frames kế tiếp/trước
- Handle occlusion: nếu object bị che 1-2 frames, vẫn track được khi xuất hiện lại

### 2.2 Pseudocode workflow

```python
"""
File: src/annotation/sam2_propagate.py

Propagate OBB annotation từ keyframe qua các neighbor frames.
"""

import torch
import numpy as np
from sam2.build_sam import build_sam2_video_predictor
from PIL import Image
import cv2

# Load SAM 2 video predictor
sam2_checkpoint = "checkpoints/sam2.1_hiera_large.pt"
model_cfg = "configs/sam2.1_hiera_l.yaml"
predictor = build_sam2_video_predictor(model_cfg, sam2_checkpoint)
predictor.eval().cuda()

def propagate_one_keyframe(
    video_dir: str,
    keyframe_idx: int,
    obb_annotations: list,  # [{class: "mcp_home", obb: [x1,y1,x2,y2,x3,y3,x4,y4]}, ...]
    radius: int = 15,
) -> dict:
    """
    Cho 1 keyframe với N OBB annotations, propagate qua ±radius frames.
    Returns: {frame_idx: [{class, obb_propagated}, ...]}
    """
    # Initialize predictor state với toàn bộ video frames trong window
    start_idx = max(0, keyframe_idx - radius)
    end_idx = keyframe_idx + radius + 1
    
    inference_state = predictor.init_state(
        video_path=video_dir,
        offload_video_to_cpu=True,
    )
    
    # Convert mỗi OBB → bounding box hình chữ nhật bao OBB → prompt SAM 2
    # SAM 2 accept box prompts; OBB convert thành axis-aligned bbox (lose rotation)
    # Sau khi propagate, chúng ta sẽ re-fit OBB từ mask
    
    propagated = {}
    
    for obj_id, ann in enumerate(obb_annotations):
        obb = np.array(ann["obb"]).reshape(4, 2)  # 4 corners
        x_min, y_min = obb.min(axis=0)
        x_max, y_max = obb.max(axis=0)
        bbox = np.array([x_min, y_min, x_max, y_max])
        
        # Add prompt to SAM 2
        _, out_obj_ids, out_mask_logits = predictor.add_new_points_or_box(
            inference_state=inference_state,
            frame_idx=keyframe_idx - start_idx,  # relative idx
            obj_id=obj_id,
            box=bbox,
        )
        
        # Store class metadata
        propagated[obj_id] = {"class": ann["class"], "frames": {}}
    
    # Run propagation forward + backward
    for out_frame_idx, out_obj_ids, out_mask_logits in predictor.propagate_in_video(
        inference_state
    ):
        actual_frame = out_frame_idx + start_idx
        
        for obj_id, mask_logits in zip(out_obj_ids, out_mask_logits):
            mask = (mask_logits > 0).cpu().numpy()[0]  # (H, W) bool
            
            # Convert mask back to OBB
            obb = mask_to_obb(mask)
            
            if obb is None or mask_area(mask) < 50:
                continue  # Mask too small / lost
            
            propagated[obj_id]["frames"][actual_frame] = obb
    
    # Reshape output
    out = {}
    for obj_id, data in propagated.items():
        for frame_idx, obb in data["frames"].items():
            out.setdefault(frame_idx, []).append({
                "class": data["class"],
                "obb": obb,
                "source": "sam2_propagated",
                "keyframe_origin": keyframe_idx,
            })
    
    return out

def mask_to_obb(mask: np.ndarray) -> list:
    """Convert binary mask → rotated rectangle (OBB)."""
    ys, xs = np.where(mask)
    if len(xs) < 5:
        return None
    points = np.column_stack([xs, ys]).astype(np.float32)
    rect = cv2.minAreaRect(points)        # ((cx, cy), (w, h), angle)
    box = cv2.boxPoints(rect)             # 4 corners (4, 2)
    return box.flatten().tolist()         # [x1,y1,x2,y2,x3,y3,x4,y4]
```

**Workflow cho 50 keyframes:**

```python
for keyframe_idx in range(0, 5400, 108):  # ~50 keyframes total từ 5400 frame extraction output
    obb_anns = load_manual_annotations(keyframe_idx)  # human labeled
    propagated = propagate_one_keyframe(
        video_dir="frames/M01/",
        keyframe_idx=keyframe_idx,
        obb_annotations=obb_anns,
        radius=15,  # ±15 frames = ±0.5s ở 30fps
    )
    save_pseudo_labels(propagated)
    # Expected: ~25-30 frames per keyframe successfully labeled
    # Total: ~1250-1500 pseudo-labels
```

### 2.3 Cách SAM 2 hoạt động dưới hood (đơn giản hóa)

```
1. Frame 100 (keyframe): Human → box prompt → SAM 2 → mask
2. SAM 2 lưu vào memory bank: 
   {object_id: feature_vector từ mask region}
3. Frame 101: SAM 2 propagate
   - Extract features từ frame 101
   - Attention với memory bank → "object 5 ở đâu trong frame này?"
   - Output: new mask cho frame 101
   - Update memory bank với features mới
4. Frame 102: Repeat với updated memory
5. ...
6. Khi confidence drop quá thấp (object bị che hoàn toàn): SAM 2 stop tracking
7. Backward: Tương tự cho frame 99, 98, 97...
```

**Memory bank** là innovation chính của SAM 2 (vs SAM 1) — cho phép propagation lâu mà không drift.

### 2.4 Limitations cụ thể

| Limitation | Mô tả | Khi nào xảy ra |
|------------|------|----------------|
| **Full occlusion >5 frames** | Object bị che hoàn toàn quá lâu, memory bank lose track | Player bị che bởi player khác trong ruck > 1s |
| **Drastic appearance change** | Logo bị deform mạnh (cầu thủ xoay 90°+) | Quick player rotation |
| **Multiple similar objects** | 2 logo MCP trên 2 cầu thủ gần nhau → SAM 2 confuse | Close-up nhiều Bradford players |
| **Tiny objects** | Logo < 20px → mask noisy | Wide shot |
| **Heavy motion blur** | Mask boundary uncertain | Fast camera pan |
| **Mask → OBB conversion lossy** | `minAreaRect` không capture rotation chính xác khi mask irregular | Always present, small error |

### 2.5 Spot-check protocol

```python
"""
Spot-check protocol cho SAM 2 outputs:

1. Random sample 100 SAM 2 propagated labels (across all keyframes)
2. Human review each:
   - Pass: OBB tight around logo, class correct, no major leak
   - Soft pass: OBB slightly loose nhưng usable
   - Fail: OBB wrong location, wrong size, leaked to background
3. Pass rate target: ≥ 85%
4. If pass rate < 85%:
   - Analyze failure types:
     - Tracking lost early? → reduce radius
     - Mask too noisy? → smooth before OBB conversion
     - Class confusion (2 nearby logos)? → manual review those cases
   - Re-run với adjusted parameters
"""

# Implementation
import json

sample_size = 100
all_propagated = load_all_propagated_labels()
sample = random.sample(all_propagated, sample_size)

# Export sample to a review UI (Roboflow accepts this)
export_for_human_review(sample, output_path="sam2_spotcheck.json")

# ... Human reviews ...

# Aggregate results
review_results = load_human_review("sam2_spotcheck_reviewed.json")
pass_count = sum(1 for r in review_results if r["verdict"] == "pass")
soft_pass_count = sum(1 for r in review_results if r["verdict"] == "soft_pass")
fail_count = sum(1 for r in review_results if r["verdict"] == "fail")

print(f"Pass: {pass_count/100*100:.0f}%")
print(f"Soft pass: {soft_pass_count/100*100:.0f}%")
print(f"Fail: {fail_count/100*100:.0f}%")

# Analyze failure types
failure_types = defaultdict(int)
for r in review_results:
    if r["verdict"] == "fail":
        failure_types[r["failure_type"]] += 1
print(f"Failure breakdown: {dict(failure_types)}")
```

### 2.6 Fallback strategy nếu SAM 2 không đủ tốt

**Nếu spot-check pass rate < 70%:**

**Fallback A: Reduce propagation radius**
- Thử radius=5 thay vì 15 → fewer propagated frames nhưng higher accuracy
- Cost: ít pseudo-labels hơn → cần thêm manual

**Fallback B: Optical flow + template matching (per v4 plan)**
- Đây là approach v4 đã đề xuất nhưng yếu hơn SAM 2
- Per frame, dùng `cv2.matchTemplate` để track each OBB region
- Threshold NCC > 0.5 để accept
- Less accurate hơn SAM 2 nhưng deterministic

**Fallback C: Pure Soft Teacher pseudo-labeling**
- Skip SAM 2 entirely
- Manual annotate 100 frames (thay vì 50)
- Train weak teacher → predict on unlabeled → keep high-confidence
- Iterate

**Fallback D: Hybrid SAM 2 + manual review of low-confidence**
- Keep SAM 2 outputs với high mask confidence
- Flag low-confidence outputs cho human review
- Reduces total manual time ~50% vẫn maintain quality

### 2.7 Realistic expectations

Dựa trên SAM 2 paper benchmarks và experience cộng đồng:
- **Static or slow-moving objects:** propagation pass rate 90%+
- **Fast-moving sports:** pass rate 70-85% (range tùy sport)
- **Rugby league specifically:** chưa có benchmark public; ước tính **75-85%** với radius=15

→ Plan: bootstrap với SAM 2 radius=15, spot-check, adjust dynamically.

---

## Phần 3: Decision tree — khi nào dùng cái gì

```
                    Frame mới cần annotation/inference
                              │
                              ▼
                  ┌──────────────────────────┐
                  │  Frame đã được manually  │
                  │  annotated (keyframe)?    │
                  └──────────┬───────────────┘
                             │
                  ┌──────────┴────────────┐
                 YES                     NO
                  │                       │
                  ▼                       ▼
        Use manual labels    ┌──────────────────────────┐
                             │  Trong ±15 frames của     │
                             │  một keyframe đã annotate?│
                             └──────────┬───────────────┘
                                        │
                             ┌──────────┴────────────┐
                            YES                     NO
                             │                       │
                             ▼                       ▼
                  Use SAM 2 propagation   ┌──────────────────────┐
                                          │  Có high-confidence   │
                                          │  pseudo-label từ teacher?│
                                          └──────────┬───────────┘
                                                     │
                                          ┌──────────┴────────────┐
                                         YES                     NO
                                          │                       │
                                          ▼                       ▼
                              Use pseudo-label    ┌─────────────────────┐
                                                  │  Active learning queue?│
                                                  └──────────┬──────────┘
                                                             │
                                                  ┌──────────┴──────────┐
                                                 YES                   NO
                                                  │                     │
                                                  ▼                     ▼
                                          Add to human queue  Skip (insufficient signal)
```

### Runtime inference decision tree

```
                    Logo OBB detected by Stage 3A
                              │
                              ▼
                  ┌──────────────────────────┐
                  │  Crop size > 32×32?       │
                  └──────────┬───────────────┘
                             │
                  ┌──────────┴────────────┐
                 YES                     NO
                  │                       │
                  ▼                       ▼
        Compute DINOv2 embedding    Tag as "small_logo",
                  │                  skip classification
                  ▼
        Cosine similarity với reference bank
                  │
                  ▼
        ┌──────────────────────────────┐
        │  Top-1 similarity ≥ 0.6?     │
        └──────────────┬───────────────┘
                       │
            ┌──────────┴────────────┐
           YES                    NO
            │                      │
            ▼                      ▼
   ┌─────────────────┐    Tag "unknown_logo"
   │ Margin ≥ 0.05?  │
   └────────┬────────┘
            │
   ┌────────┴────────┐
  YES               NO
   │                 │
   ▼                 ▼
Return brand   Tag "ambiguous"
              (top_2 candidates)
```

---

## Kết luận

**DINOv2 embedding (Stage 3B):**
- Pros: Future-proof, sponsor mới = 0 retrain, modular
- Cons: Cần validate accuracy, có risk với similar visual brands
- Mitigation rõ ràng (contrastive fine-tune, CLIP fusion, supervised fallback)

**SAM 2 propagation (Stage 2B):**
- Pros: 6-7× giảm annotation effort, mature library (Apache 2.0)
- Cons: Fail trên full occlusion + fast motion + similar nearby objects
- Mitigation rõ ràng (reduce radius, hybrid với template matching, manual fallback)

Cả 2 đều có **fallback path clear** → nếu một technique không work, không block project.

---

## Tài liệu tham khảo bổ sung

- DINOv2 GitHub: https://github.com/facebookresearch/dinov2
- DINOv2 paper: https://arxiv.org/html/2304.07193v2
- SAM 2 GitHub: https://github.com/facebookresearch/sam2
- SAM 2 paper: https://arxiv.org/abs/2408.00714
- SAM 2 Roboflow blog: https://blog.roboflow.com/sam-2-video-segmentation/
- DINOv2 + CLIP fusion: https://www.mdpi.com/2079-9292/14/24/4785
- DINOSim (zero-shot OD): https://www.biorxiv.org/content/10.1101/2025.03.09.642092v2.full
