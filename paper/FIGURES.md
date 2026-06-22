# Figure art-direction — *PhD-thesis figure style · research-poster infographic · publication-ready*

Hai cách dùng tài liệu này:
1. **Đã có bản vector render được ngay**: mỗi hình đã có file TikZ (`fig_*.tex`) —
   biên dịch `main.tex` ra PDF là có hình vector publication-ready, không cần ảnh ngoài.
2. **Muốn bản infographic đẹp hơn** (poster/slide/thesis): dùng các mô tả dưới đây
   làm *art-direction brief* cho designer hoặc image-generation tool.

## Bảng phong cách chung (giữ nhất quán mọi hình)
- **Aesthetic**: flat vector, isometric-lite, generous whitespace, thin rounded
  strokes (~1.2pt), subtle drop shadows; *no 3D bevels, no clipart*.
- **Palette** (đồng bộ với TikZ): teacher = amber `#E8A33D`, student = green
  `#3FA64D`, data/IO = neutral gray `#8A8F98`, twin/3DGS = violet `#7A5AC2`,
  prior/accent = blue `#3D6FE8`, alert/active-learning = red `#D9534F`.
- **Typography**: sans-serif (Inter/Helvetica Neue), title 12–14pt bold, labels
  8–9pt; mọi mũi tên có hướng rõ; chú thích đặt sát node.
- **Định dạng**: vector SVG/PDF, 300+ dpi nếu raster, an toàn khi in trắng-đen
  (phân biệt bằng pattern, không chỉ bằng màu).

---

## Fig. 1 — `fig_architecture.tex` · System / flywheel (figure*, 2 cột)
**Vai trò**: hình "anchor" của bài. **Brief infographic**: dải trái→phải.
- Trái: hai IO node *Sponsor roster + assets* và *Broadcast video* (gray).
- Giữa-trên: khối **TEACHER** viền amber đứt nét gồm *Exemplar PCS (SAM 3)*,
  *OCR/box labellers*, *Label model + temporal refine*.
- Giữa-dưới: node violet **Gaussian-splatting venue twin** rót vào label model.
- Phải: *Clean labels* → **Student (distilled YOLO)** (green) → **Exposure/
  visibility analytics**.
- **Flywheel**: cung đứt nét xanh lá từ Student vòng lại Gallery, nhãn
  *"gallery + student grow per event"*.
- Phong cách thesis: đánh số bước ①–⑥ khớp claim C1–C6.

## Fig. 2 — `fig_funnel.tex` · Roster prior (C1)
**Brief**: phễu 3 tầng dọc: `B (thousands)` xanh nhạt → `Roster R_e (10–30)`
amber → `Accepted detections` green. Mũi tên bên phải chú "rejects b∉R_e at zero
cost". Ẩn dụ phễu = thu hẹp không gian giả thuyết.

## Fig. 3 — `fig_labelmodel.tex` · Weak-supervision voting (C3)
**Brief**: 6 labeler (5 amber + *Roster prior* xanh) → hội tụ vào hộp xám *Label
model (denoise + vote)* → ra *Clean label + confidence* (green); nhánh đỏ xuống
*active learning* khi đồng thuận thấp. Gợi ý poster: vẽ "phiếu bầu" nhỏ trên mỗi
mũi tên vào label model.

## Fig. 4 — `fig_twin.tex` · 3DGS digital twin (C4)
**Brief**: pipeline 5 bước ngang: *Footage* → *3DGS reconstruction* (violet) →
*Real-logo insertion (lighting-aware)* → *6-DoF + domain randomisation* →
*Photoreal frames + pixel-perfect labels* (green). Caption nhấn "background is the
real scene; only logos synthetic". Poster: thêm thumbnail thật→twin→inserted.

## Fig. 5 — `fig_efficiency.tex` · Annotation efficiency (kết quả chính)
**Brief**: trục x log = số nhãn tay, trục y = mAP@.5. Đường *Supervised* (xanh)
leo chậm tới plateau; đường *Ours* (đỏ) đạt gần plateau với rất ít nhãn; đường
gạch ngang = supervised plateau. ⚠ **Số hiện là placeholder** — thay bằng số đo.

## Fig. 6 — `fig_ablation.tex` · Ablation (C1/C3/C4/C5)
**Brief**: bar chart mAP@.5: *Full* vs bỏ từng thành phần (−Roster, −LabelModel,
−Twin, −Text/Col). Cột *Full* xanh đậm nhất. ⚠ **Placeholder** — thay bằng delta đo.

---

## Hình NÊN bổ sung (chưa có TikZ — để designer dựng)
- **Fig. 7 — Qualitative grid**: lưới ảnh thật broadcast với box+nhãn brand của
  *Ours* vs baseline (ô xanh = đúng, đỏ = sai/sót). Rất thuyết phục reviewer.
- **Fig. 8 — Logo Fingerprint**: một crop logo tách 3 kênh (visual embedding chấm
  t-SNE · chuỗi OCR · ô màu trội) hợp thành vector; minh hoạ "add brand = +1 row".
- **Fig. 9 — Exposure timeline**: dải thời gian trận, mỗi brand một lane, ô tô đậm
  = đang hiển thị; gắn với analytics đầu ra (LOGOS_Exposure_Pricing_Algorithm).
