# Bậc 4 — Tool 3D synthetic data (khảo sát internet, 2026)

> Cho `auto_label/synth_3d_blenderproc.py` và `../bac4_3d_simulation.md`. Mục tiêu:
> sinh ảnh cầu thủ rugby với **logo thật UV-map lên áo** + nhãn hoàn hảo tự động
> (bbox/OBB, mask, **% visibility kể cả khi bị che**) — thứ auto-label video không có.

## 1. Engine render + xuất nhãn

| Tool | Vai trò | Ưu | Nhược | Khi nào |
|---|---|---|---|---|
| **BlenderProc** (DLR-RM) ⭐ | Pipeline Blender scriptable | Xuất **COCO/BOP/bbox/seg/depth/normal** sẵn; cộng đồng synthetic mạnh; Cycles PBR | Render chậm hơn game engine | **Mặc định khuyến nghị** — research cho thấy mạng train trên Cycles vượt game engine |
| **bpycv** | Utils CV cho Blender | Instance mask + depth + 6D pose "one-line" | Ít chuẩn hoá hơn BlenderProc | Khi cần nhanh, scene tự dựng |
| **NVIDIA Omniverse Replicator / Isaac Sim** | SDG công nghiệp | Randomizers/Annotators/Writers chuẩn; real-time; scale hàng triệu frame | Hệ sinh thái NVIDIA nặng | Team có hạ tầng NVIDIA, cần scale lớn |
| **Kubric** (Google/DeepMind) | Sinh video synthetic + nhãn | Tốt cho video/optical-flow | Không sports-specific | Khi cần chuỗi video + flow |
| **Infinigen** | Sinh môi trường procedural | Nền/thiên nhiên vô hạn; tích hợp được Replicator | Không phải người/áo | Đa dạng hoá nền (kết hợp Replicator) |

## 2. Logo lên áo 3D (UV texture — trái tim label fidelity)

| Tool | Vai trò | Ghi chú |
|---|---|---|
| **Cloth2Tex** (2023) | Sinh texture map cho áo từ ảnh 2D ref | Neural rendering, bỏ chọn control point tay; blueprint đặt logo lên UV |
| **TexGarment** (CVPR 2025) ⭐ | UV texture nhất quán, **< 4s/texture** | Mới + nhanh; tốt cho scale nhiều kit |
| **FabricDiffusion** (2024) | Transfer texture từ ảnh áo "in-the-wild" → 3D garment | Hợp khi chỉ có ảnh áo thật, không có file vector |
| **CLOTH3D++** | 2M+ frame vải mô phỏng (Cycles) | Nguồn asset/blueprint cloth sim |

> Nguyên tắc: logo **UV-map từ ảnh THẬT** vào ô áo (ngực/vai/tay). Khi cloth sim làm
> áo biến dạng, logo biến dạng theo vật lý nhưng vẫn là chính logo thật → engine biết
> mọi pixel render thuộc texel logo nào → **mask + % visibility hoàn hảo**.

## 3. Nền sân — đóng sim2real gap bằng 3DGS (khuyến nghị lai)

Thay vì dựng sân từ con số 0 (sim2real gap lớn): **reconstruct sân thật bằng 3D
Gaussian Splatting** từ chính footage broadcast → nền gần như thật, chỉ composite cầu
thủ 3D (UV-map logo) vào. Tool: **FastGS** (CVPR 2026, train ~100s), Nerfstudio/gsplat,
Material-informed GS (mesh + material cho simulator). → giảm mạnh sim2real của nền so
với authoring Blender đầy đủ. Xem `expert_review_and_plan.md` (đường 3DGS-hybrid).

## 4. Asset người + pose

- **SMPL / SMPL-X** — body tham số hoá (vóc dáng). Cần đăng ký license.
- **AMASS** — mocap, NHƯNG **thiếu động tác rugby** (scrum/tackle/pass) → nguồn pose
  rugby là gap thật, cần mocap riêng hoặc tổng hợp.
- **Mixamo** — rig + animation nhanh (không rugby-specific nhưng có chạy/ngã).

## 5. Khuyến nghị triển khai (ROI)

```
P0 (1–2 tuần+): BlenderProc + 1 áo có UV + UV-map 1 logo + render tĩnh → bbox/mask
P1: + cloth sim (Blender cloth) + pose (AMASS/Mixamo) + domain randomization (§5 bac4)
P2: + đa cầu thủ/occlusion + scene sân + EXPORT % visibility
P3: scale + logo/môn mới (biên ≈ 0); cân nhắc 3DGS-hybrid cho nền
```

**Lưu ý trung thực (xem `analysis-log` critique Bậc 4):** effort thực ~nhiều tháng;
cloth sim giòn (vải xuyên body); ngưỡng sim2real cho **recognition** cao hơn detection
(SoccerSynth chứng minh cho player-detection, không phải logo-recognition). Bậc 4 là
**đầu tư R&D trung-dài hạn**, KHÔNG block sản phẩm — chỉ theo đuổi cho **% visibility/
occlusion GT** và scale đa môn biên-≈-0.

## Nguồn
- [BlenderProc (DLR-RM)](https://dlr-rm.github.io/BlenderProc/) · [bpycv](https://github.com/DIYer22/bpycv)
- [NVIDIA Omniverse Replicator](https://developer.nvidia.com/blog/build-custom-synthetic-data-generation-pipelines-with-omniverse-replicator/) · [Infinigen + Replicator (Isaac Sim)](https://docs.isaacsim.omniverse.nvidia.com/4.5.0/replicator_tutorials/tutorial_replicator_infinigen_sdg.html)
- [Cloth2Tex (arXiv 2308.04288)](https://arxiv.org/abs/2308.04288) · [TexGarment (CVPR 2025)](https://openaccess.thecvf.com/content/CVPR2025/papers/Liu_TexGarment_Consistent_Garment_UV_Texture_Generation_via_Efficient_3D_Structure-Guided_CVPR_2025_paper.pdf) · [FabricDiffusion (arXiv 2410.01801)](https://arxiv.org/html/2410.01801)
- [FastGS (CVPR 2026)](https://github.com/fastgs/FastGS)
