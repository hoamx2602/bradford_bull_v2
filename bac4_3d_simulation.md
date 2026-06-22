# Bậc 4 — 3D Simulation (UV-map logo thật + cloth sim + pose + render)

> Tài liệu triển khai sâu cho **Bậc 4** trong thang synthetic data
> (xem tổng quan ở [`autolabel.md`](./autolabel.md) §8).
>
> **Mục tiêu:** dựng một "data factory" 3D sinh **vô hạn** ảnh cầu thủ rugby với
> logo thật UV-map lên áo, mô phỏng tư thế/vải/ánh sáng/nhiễu — và xuất **nhãn
> hoàn hảo tự động** (bbox, mask, keypoint, cờ occlusion) cho cả Tầng 1 & 2.

---

## 1. Vì sao Bậc 4 là "chén thánh"

Đây là nguồn duy nhất cho thứ mà auto-label video thật **không bao giờ** có:

- **Nhãn pixel-perfect kể cả khi logo bị che**: engine biết chính xác mỗi pixel
  thuộc logo nào, ngay cả khi tay cầu thủ che 70% — ground truth từ render buffer.
- **Mọi modality miễn phí**: bbox, instance mask, semantic mask, depth, normal,
  keypoint khớp, **% visibility của logo** (rất quý cho phân tích tài trợ).
- **Control tuyệt đối**: ép sinh đúng các ca khó & hiếm (góc gập, ngược sáng, va
  chạm, bùn) mà video thật ít có.
- **Biên chi phí mỗi logo/môn mới ≈ 0**: thêm áo/logo/môn = thêm asset, không
  annotate. → đúng mục tiêu "linh hoạt đa môn".

> Đã được chứng minh trong thể thao thật: **SoccerSynth-Detection** (Unreal) và
> **Jersey Number Detection** (synthetic 3D) đạt kết quả production cho phát hiện
> cầu thủ / số áo.

---

## 2. Chọn engine

| Engine | Ưu | Nhược | Khi nào |
|---|---|---|---|
| **Blender + Cycles (PBR)** | Photorealism cao nhất; **BlenderProc** tự xuất nhãn; Python script hoá toàn bộ; miễn phí | Render chậm hơn | **Khuyến nghị mặc định** — nghiên cứu cho thấy mạng train trên Cycles vượt game engine |
| Unreal Engine | Render real-time, scale lớn; plugin bbox sẵn | Setup nặng, license | Khi cần hàng triệu frame nhanh (như SoccerSynth) |
| NVIDIA Omniverse Replicator | Pipeline synthetic + DR chuẩn công nghiệp | Hệ sinh thái NVIDIA | Team có hạ tầng NVIDIA |

**Khuyến nghị:** bắt đầu với **BlenderProc** (Blender Cycles) — scriptable, xuất
COCO/bbox/mask tự động, cộng đồng synthetic data mạnh.

---

## 3. Kiến trúc pipeline 3D

```
 1. BODY      SMPL / SMPL-X  → tham số hoá vóc dáng cầu thủ (cao/gầy/cơ bắp)
                 │
 2. POSE      AMASS / mocap rugby (chạy, tắc bóng, ngã, ôm bóng)  → rig body
                 │
 3. GARMENT   mesh áo đấu rugby khoác lên body  (mua asset / dựng / Cloth2Tex)
                 │
 4. LOGO      UV-map ảnh logo THẬT lên đúng toạ độ UV của áo  ◀── label fidelity
                 │     (giữ nguyên hình học pixel-perfect — KHÔNG sinh logo)
 5. CLOTH SIM mô phỏng vải: nếp gấp, co giãn khi vận động (Blender cloth / PhysX)
                 │
 6. SCENE     sân cỏ, khung thành, khán đài, nhiều cầu thủ (occlusion thật)
                 │
 7. RENDER    Cycles PBR  →  ảnh + các buffer (mask/depth/normal)
                 │
 8. DR        domain randomization (xem §5)
                 │
 9. LABELS    BlenderProc xuất TỰ ĐỘNG: bbox + mask + keypoint + logo-visibility
```

### Bước 4 — UV-map: trái tim của label fidelity

```
Áo 3D có sẵn "UV layout" (bản đồ trải phẳng bề mặt áo).
Logo thật (PNG/SVG) được đặt vào đúng ô UV (ngực, vai, tay).
→ Khi áo biến dạng (cloth sim), logo biến dạng THEO vải một cách vật lý đúng,
   nhưng vẫn là CHÍNH cái logo thật — không phải logo "vẽ lại".
→ Engine biết mọi pixel render ra thuộc texel nào của logo → mask hoàn hảo.
```

Tham chiếu kỹ thuật: **Cloth2Tex** (sinh/đặt texture lên vải 3D) và **CLOTH3D++**
(2M+ frame vải mô phỏng, render Cycles) là blueprint sẵn cho bước 3–4.

---

## 4. Xuất nhãn tự động (BlenderProc)

Render xong, engine cho ta **ground truth không cần annotate**:

| Nhãn | Cách lấy | Dùng cho |
|---|---|---|
| **2D bbox** logo | bounding của các pixel mang material logo | Tầng 1 |
| **Instance mask** logo | segmentation buffer theo material id | Tầng 1 (mask) |
| **Crop logo sạch** | cắt theo mask | Tầng 2 (template/triplet) |
| **% visibility** | (pixel logo hiện) / (pixel logo nếu không bị che) | Phân tích tài trợ + lọc sample |
| **Keypoint cầu thủ** | từ rig SMPL | (mở rộng) pose/player detection |
| **Depth / normal** | render pass | (mở rộng) huấn luyện đa nhiệm |

```python
# bac4_render.py  — skeleton BlenderProc, KHÔNG phải production
import blenderproc as bproc, random
bproc.init()

body    = bproc.loader.load_obj("assets/rugby_body_smpl.obj")[0]
jersey  = bproc.loader.load_obj("assets/rugby_jersey.obj")[0]
logo_tex = bproc.material.create_material_from_texture(
              "assets/logos/pepsi.png", "logo_pepsi")   # LOGO THẬT
jersey.set_material(slot="chest_uv", material=logo_tex) # UV-map đúng ô

for i in range(N_FRAMES):
    apply_random_pose(body, amass_clip=random.choice(POSES))  # tư thế rugby
    simulate_cloth(jersey, body)                              # nếp gấp vật lý
    domain_randomize_scene(...)                               # §5
    bproc.camera.add_camera_pose(random_broadcast_view())

    data = bproc.renderer.render()                # ảnh + buffers
    seg  = bproc.renderer.render_segmap(map_by=["instance", "material"])

    bbox = material_to_bbox(seg, material="logo_pepsi")       # nhãn tự sinh
    vis  = visibility_ratio(seg, material="logo_pepsi")
    write_yolo(data["colors"], bbox, brand="pepsi", visibility=vis)
```

---

## 5. Domain Randomization (đóng sim2real gap)

Randomize **mọi thứ TRỪ logo** để model học bản chất, không học "vẻ giả":

- **Ánh sáng**: floodlight sân, mặt trời gradient, trong nhà/ngoài trời, HDRI.
- **Sân & nền**: màu/texture cỏ, vạch kẻ, khán đài, biển quảng cáo, thời tiết.
- **Camera**: góc broadcast, tiêu cự, **rung tay → motion blur**, độ cao.
- **Cầu thủ**: vóc dáng, da, tóc, số áo, **nhiều cầu thủ chồng lấn (occlusion)**.
- **Vải/áo**: màu áo nền, độ bóng, độ nhăn, bùn/ướt mưa.
- **Hậu kỳ ảnh**: nhiễu cảm biến, **nén video (JPEG/H.264 artifact)**, đổi gamma.

> SoccerSynth làm đúng các mục này: motion blur bằng rung camera, gradient
> sunlight, thư viện tóc/áo/quần/giày, randomize màu/texture cỏ.

---

## 6. Sim2Real — không bao giờ dùng 3D đơn độc

3D dù đẹp vẫn có "mùi render". Bắt buộc kết hợp:

1. **Photoreal PBR** (Cycles) + **HDRI** ánh sáng thật.
2. **Domain randomization** rộng (§5).
3. **Trộn real-in-the-loop**: 70–90% synthetic 3D + 10–30% frame thật
   **auto-label Grounded-SAM** → fine-tune kéo model về domain thật.
4. **Domain adaptation** (tuỳ chọn): style-transfer ảnh 3D → trông giống broadcast,
   hoặc adversarial feature alignment.

---

## 7. Lộ trình & chi phí

| Giai đoạn | Việc | Thời gian ước tính |
|---|---|---|
| P0 | 1 áo rugby + 1 body SMPL + UV-map 1 logo, render tĩnh, xuất bbox | 1–2 tuần |
| P1 | Thêm cloth sim + pose từ AMASS + DR cơ bản | 2–3 tuần |
| P2 | Đa cầu thủ/occlusion + scene sân đầy đủ + visibility export | 2–4 tuần |
| P3 | Scale hàng trăm nghìn frame + bộ logo/môn mới (biên ≈ 0) | liên tục |

**Chi phí:** cao ở P0–P1 (asset, rigging, script). Sau đó **biên gần 0** — đây là
khoản đầu tư hạ tầng, không phải chi phí lặp lại như annotate tay.

---

## 8. Khi nào KHÔNG nên dùng Bậc 4

- Cần kết quả trong vài ngày → dùng Bậc 1+3 + auto-label trước.
- Chỉ vài logo, ít thay đổi → ROI 3D chưa bõ.
- Không có nhân lực quen Blender/3D pipeline.

→ Bậc 4 dành cho **đầu tư trung–dài hạn** khi mục tiêu là **đa môn thể thao +
nhiều nhà tài trợ + cần nhãn occlusion/visibility chính xác**.

---

## 9. Checklist triển khai

- [ ] Cài **BlenderProc** (Blender Cycles) hoặc Unreal + plugin bbox.
- [ ] Asset: body SMPL/SMPL-X, mesh áo rugby có UV layout chuẩn.
- [ ] Thư viện pose rugby (AMASS / mocap).
- [ ] UV-map **logo thật** vào đúng ô áo (ngực/vai/tay).
- [ ] Cloth simulation + collision với body.
- [ ] Module domain randomization (§5).
- [ ] Auto-export: bbox + mask + crop + visibility (§4).
- [ ] Bộ trộn real-in-the-loop (Grounded-SAM) ~70/30.
- [ ] QC: kiểm tra mask khớp logo, lọc frame lỗi sim (vải xuyên body...).

---

## 10. Nguồn tham khảo

- [SoccerSynth-Detection — Synthetic Dataset for Soccer Player Detection (Unreal)](https://arxiv.org/pdf/2501.09281)
- [Jersey Number Detection Using Synthetic Data in a Low-Data Regime](https://www.ncbi.nlm.nih.gov/pmc/articles/PMC9583843/)
- [Cloth2Tex — Customized Cloth Texture Generation for 3D Virtual Try-On](https://tomguluson92.github.io/projects/cloth2tex/static/document/cloth2tex.pdf)
- [CLOTH3D++ / 3D+Texture Garment Reconstruction (Cycles render)](https://chalearnlap.cvc.uab.cat/dataset/38/description/)
- [Synthetic Data Generation for Bridging Sim2Real Gap in Production](https://arxiv.org/html/2311.11039v2)
- [Synthetic Data from Unreal Game Engine for Object Detection](https://www.mdpi.com/2076-3417/12/17/8534)
- [BlenderProc — procedural Blender pipeline for synthetic data](https://github.com/DLR-RM/BlenderProc)
