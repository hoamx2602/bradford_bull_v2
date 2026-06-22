# Bậc 3 — Diffusion Inpainting / Harmonization (logo thật + context sinh)

> Tài liệu triển khai sâu cho **Bậc 3** trong thang synthetic data
> (xem tổng quan ở [`autolabel.md`](./autolabel.md) §8).
>
> **Mục tiêu:** sinh ảnh training photorealistic, đa dạng, trong đó **logo luôn
> là asset thật được khóa pixel-perfect**, diffusion chỉ sinh/hòa phần context
> xung quanh (vải, nếp gấp, ánh sáng, bóng, nền). Giữ trọn **label fidelity**.

---

## 1. Vì sao chọn Bậc 3

| Tiêu chí | Bậc 1 (copy-paste) | **Bậc 3 (diffusion)** | Bậc 4 (3D) |
|---|---|---|---|
| Realism | Thấp (trông "dán") | **Cao (photorealistic)** | Rất cao |
| Label fidelity | Tuyệt đối | **Tuyệt đối (logo khóa)** | Tuyệt đối |
| Chi phí dựng | Rất thấp | **Trung bình (1 GPU)** | Cao |
| Đa dạng appearance cho Tầng 2 | Thấp | **Rất cao** | Cao |
| Thời gian/ảnh | ms | **giây** | giây–phút |

Bậc 3 là **điểm ngọt ROI**: dùng được ngay với 1 GPU, code mã nguồn mở sẵn,
và đặc biệt mạnh ở việc sinh **nhiều biến thể của CÙNG một logo** → nuôi
Recognizer (Tầng 2) cực tốt.

---

## 2. Nguyên tắc bất biến: KHÓA logo

```
        ┌──────────────────────────────────────────────┐
        │  Vùng logo (mask)  →  KHÓA, không cho denoise │
        │  Vùng còn lại       →  diffusion tự do sinh   │
        └──────────────────────────────────────────────┘
```

Mọi kỹ thuật dưới đây đều phải đảm bảo: **các pixel bên trong mask logo KHÔNG
bị mô hình sinh lại**. Ta chỉ cho diffusion đụng vào viền/bóng/vải xung quanh,
hoặc dùng ControlNet để *ép* viền logo khớp đúng layout.

---

## 3. Ba biến thể kỹ thuật (từ đơn giản → mạnh)

### 3.1. Biến thể A — img2img harmonization (đơn giản nhất)

Quy trình:
1. Copy-paste logo thật lên ảnh nền thật (như Bậc 1) → ảnh "dán giả".
2. Chạy **img2img strength thấp (0.2–0.35)** trên **toàn ảnh** để hòa ánh sáng,
   tông màu, hạt nhiễu → mất cảm giác "dán".
3. **Composite lại logo gốc qua mask** sau khi sinh (an toàn tuyệt đối): vùng
   logo lấy lại từ ảnh paste gốc, chỉ giữ phần context đã hòa.

Ưu: cực dễ. Nhược: strength thấp nên thay đổi context hạn chế.

### 3.2. Biến thể B — Inpainting (sinh lại context quanh logo)

1. Paste logo thật lên nền.
2. Tạo **mask = "mọi nơi TRỪ logo"** (inverted) → cho mô hình inpaint vùng này.
3. Inpainting model (SDXL-inpaint) sinh lại vải/nền/cơ thể quanh logo theo prompt
   ("rugby jersey fabric, stadium floodlight, motion blur, wet from rain").
4. Logo nằm trong vùng khóa → bất biến.

Ưu: context đa dạng hơn A. Nhược: phải canh để inpaint không "ăn lẹm" viền logo.

### 3.3. Biến thể C — ControlNet + IP-Adapter (mạnh nhất, "Diffusion Copy-Paste")

Đây là kỹ thuật trong các paper 2025 (Gen2Det, Object-Centric Data Synthesis).

```
   Logo thật ──► Canny/HED edge ──┐
                                  ├──► ControlNet  (ÉP viền logo + layout)
   Layout box  ─────────────────► ┘
   Ảnh sân thật ──► IP-Adapter ─────► (ÉP phong cách nền giống sân thật)
   Prompt text ──────────────────────► "rugby player, jersey, floodlight"
                                  │
                                  ▼
                       SDXL  →  ảnh photorealistic, viền logo khớp edge map
```

- **ControlNet (Canny/HED/depth)**: trích edge map của logo → ép diffusion sinh
  ảnh có viền logo đúng vị trí & hình dạng. Logo "mọc ra" đúng chỗ, đúng dáng.
- **IP-Adapter**: nạp 1 ảnh sân/áo thật làm tham chiếu style → ảnh sinh mang
  đúng "chất" sân vận động.
- **An toàn label**: sau sinh, **vẫn composite logo gốc qua mask** để đảm bảo
  pixel-perfect (ControlNet ép hình dạng đúng nhưng có thể lệch màu/chữ nhỏ).

---

## 4. Pipeline tham khảo (code skeleton)

> Pseudo-code minh hoạ luồng; thư viện: `diffusers`, `controlnet_aux`,
> `opencv`, `numpy`. Chạy trên 1 GPU (>=12GB cho SDXL).

```python
# bac3_generate.py  — skeleton, KHÔNG phải code production
import cv2, numpy as np, random
from diffusers import StableDiffusionXLControlNetInpaintPipeline, ControlNetModel
from controlnet_aux import CannyDetector
from PIL import Image

canny = CannyDetector()
controlnet = ControlNetModel.from_pretrained("diffusers/controlnet-canny-sdxl-1.0")
pipe = StableDiffusionXLControlNetInpaintPipeline.from_pretrained(
    "stabilityai/stable-diffusion-xl-base-1.0", controlnet=controlnet
).to("cuda")

PROMPTS = [
    "rugby player wearing team jersey, stadium floodlights, photorealistic",
    "close-up sports jersey fabric with sponsor logo, motion blur, rain",
    "athlete running on rugby pitch, dynamic pose, broadcast camera",
]

def domain_randomize(logo_rgba):
    # scale, xoay nhẹ, perspective warp, color jitter trên LOGO THẬT
    ...
    return warped_logo_rgba, warp_matrix

def make_sample(bg_img, logo_rgba, brand_name):
    logo, M = domain_randomize(logo_rgba)
    x, y = random.randint(0, bg_img.shape[1]-logo.shape[1]), ...
    pasted, logo_mask = paste_rgba(bg_img.copy(), logo, x, y)   # logo thật

    # mask = mọi nơi TRỪ logo  → cho diffusion sinh context
    inpaint_mask = 255 - logo_mask
    edge = canny(Image.fromarray(pasted))                      # ép viền logo

    gen = pipe(
        prompt=random.choice(PROMPTS),
        image=Image.fromarray(pasted),
        mask_image=Image.fromarray(inpaint_mask),
        control_image=edge,
        strength=0.85, controlnet_conditioning_scale=0.7,
        num_inference_steps=30,
    ).images[0]
    gen = np.array(gen)

    # AN TOÀN LABEL: composite logo gốc trở lại qua mask (pixel-perfect)
    gen = composite_back(gen, pasted, logo_mask)

    bbox = mask_to_yolo_bbox(logo_mask, brand=brand_name)      # nhãn tự sinh
    return gen, bbox
```

**Điểm mấu chốt code:**
- `domain_randomize` chỉ biến đổi **hình học/màu nhẹ của logo thật**, không sinh mới.
- `inpaint_mask = 255 - logo_mask` → diffusion **không đụng** pixel logo.
- `composite_back` → bước bảo hiểm cuối: trả lại logo gốc, đảm bảo Tầng 2 đúng.
- `bbox`/mask xuất **tự động** từ `logo_mask` → zero annotate.

---

## 5. Phục vụ Tầng 2 (Recognizer) — giá trị riêng của Bậc 3

Bậc 3 sinh được **hàng trăm biến thể của cùng một logo**: cong theo vai, mờ,
ngược sáng, ướt mưa, nhăn vải, nén video. Đây chính là tập **positive đa dạng**
lý tưởng cho:
- **Triplet loss encoder** — anchor (logo gốc) / positive (các biến thể sinh ra) /
  negative (logo hãng khác).
- **Template DB augmentation** — mỗi hãng có nhiều vector ở các điều kiện khác
  nhau → so khớp robust hơn nhiều so với 1 template tĩnh.

---

## 6. Kiểm soát chất lượng (QC) — bắt buộc

Diffusion thỉnh thoảng vẫn hỏng. Lọc tự động trước khi đưa vào train:

1. **Logo-IoU check**: chạy lại detector/template-match trên ảnh sinh, xác nhận
   logo còn ở đúng bbox đã ghi. Lệch → loại.
2. **Embedding-distance check**: embedding crop logo sinh ra phải gần embedding
   logo gốc (cosine > ngưỡng). Xa → diffusion đã bóp méo → loại.
3. **Realism filter (tuỳ chọn)**: dùng một discriminator/aesthetic scorer loại
   ảnh "trông giả".
4. **Human spot-check**: duyệt ngẫu nhiên 1–2% bằng mắt.

---

## 7. Checklist triển khai

- [ ] Thu thập **logo gốc vector/PNG nền trong suốt** của mọi nhà tài trợ.
- [ ] Thu thập **ảnh nền/sân/áo thật** làm bối cảnh & tham chiếu IP-Adapter.
- [ ] Dựng `domain_randomize` cho logo (scale/warp/color/blur).
- [ ] Pipeline SDXL-inpaint + ControlNet-canny (Biến thể C).
- [ ] Bước `composite_back` (bảo hiểm label fidelity).
- [ ] Bộ lọc QC (Logo-IoU + embedding-distance).
- [ ] Xuất YOLO format cho Tầng 1 + crop biến thể cho Tầng 2.
- [ ] Trộn với real auto-labeled (Grounded-SAM) theo tỉ lệ ~70/30.

---

## 8. Nguồn tham khảo

- [Gen2Det — Generate to Detect](https://arxiv.org/pdf/2312.04566)
- [Object-Centric Data Synthesis (Diffusion Copy-Paste, 2025)](https://arxiv.org/pdf/2511.23450)
- [ControlNet — Complete Guide](https://stable-diffusion-art.com/controlnet/)
- [Heeding the Inner Voice: Aligning ControlNet Training](https://arxiv.org/pdf/2507.02321)
- [Diffusers — Stable Diffusion XL Inpainting / ControlNet docs](https://huggingface.co/docs/diffusers)
