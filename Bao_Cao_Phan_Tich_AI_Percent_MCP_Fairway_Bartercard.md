# Báo cáo phân tích: Sai lệch % AI-detected Exposure theo Brand
**Dự án:** LogoLens — Sponsor Logo Analytics (Bradford Bulls)
**Phạm vi:** So sánh Human (đếm tay) vs AI (model detect) cho các brand MCP, Fairway, Bartercard, KLG
**Ngày:** 02/07/2026

---

## 1. Bối cảnh & câu hỏi đặt ra

Sau khi train model detect logo (RF-DETR, notebook `train_colab_rfdetr.ipynb`, 17 class brand) và chạy inference trên video trận đấu, kết quả cho thấy hai bất thường:

1. **MCP và Fairway có % AI gần như bằng nhau (3.5% ≈ 3.5%)**, dù quan sát bằng mắt thường MCP xuất hiện rõ và nhiều hơn Fairway rõ rệt.
2. **Bartercard có % AI cao bất thường (19.4%)**, gấp gần 5 lần so với số Human đếm tay (4.0%).

Bảng số liệu gốc (Human = đếm tay, AI = model output, Visibility = điểm visibility trung bình):

| Brand | Human | AI | Visibility |
|---|---|---|---|
| TOPNOTCH/Floor Tonic | 34.0 | 13.5 | 8.1 |
| MNA Building | 7.0 | 2.2 | 2.3 |
| MNA Support Services | 7.0 | 2.2 | 2.3 |
| Romantica | 7.0 | 3.6 | 3.7 |
| Chadwick Lrenceaw (left sleeve) | 4.0 | 5.9 | 3.8 |
| **Bartercard (right sleeve lower)** | **4.0** | **19.4** | **11.6** |
| Hospitality (right sleeve upper) | 4.0 | 2.5 | 2.4 |
| **MCP** | **7.0** | **3.5** | **4.7** |
| **Fairway Roofing** | **3.0** | **3.5** | **4.7** |
| ACS Group | 7.0 | 8.1 | 5.0 |
| **KLG Europe** | **5.0** | **17.0** | **9.3** |
| Cedar Court Hotels | 3.0 | 5.9 | 6.7 |
| AON | 3.0 | 3.7 | 4.0 |
| Paint & Lacquers | 3.0 | 4.0 | 4.2 |
| Ellgren | 1.5 | 2.4 | 3.7 |
| EM | 1.5 | 2.5 | 4.0 |

---

## 2. Dữ liệu nền dùng để phân tích

Đối chiếu với các artifact sinh ra trong quá trình training model:

**Bảng đầy đủ: tổng số annotation (instance) của toàn bộ class trong dữ liệu training** — trích xuất trực tiếp từ Roboflow (Class Balance report của đúng version dataset dùng để train), kèm breakdown train/valid/test:

| Class Name | Total | Training | Validation | Test |
|---|---|---|---|---|
| klg_home | 1024 | 704 | 228 | 92 |
| klg_away | 984 | 708 | 188 | 88 |
| paints_lacquers_away | 900 | 643 | 175 | 82 |
| mcp_home | 755 | 515 | 165 | 75 |
| top_notch_home | 720 | 519 | 145 | 56 |
| mcp_away | 669 | 487 | 120 | 62 |
| romantica_home | 593 | 435 | 111 | 47 |
| romantica_away | 519 | 374 | 82 | 63 |
| floor_tonic_away | 517 | 371 | 90 | 56 |
| bartercard_away | 500 | 350 | 99 | 51 |
| ellgren_home | 496 | 357 | 101 | 38 |
| paints_lacquers_home | 488 | 325 | 114 | 49 |
| acs_group_home | 452 | 302 | 106 | 44 |
| aon_away | 443 | 327 | 74 | 42 |
| aon_home | 408 | 296 | 77 | 35 |
| acs_group_away | 402 | 292 | 76 | 34 |
| ellgren_away | 383 | 275 | 63 | 45 |
| atm_away | 277 | 195 | 54 | 28 |
| em_workwear_away | 276 | 178 | 65 | 33 |
| bartercard_home | 271 | 179 | 66 | 26 |
| atm_home | 262 | 173 | 66 | 23 |
| fairway_away | 243 | 185 | 35 | 23 |
| mna_support_service_away | 194 | 136 | 40 | 18 |
| mna_cladding_away | 192 | 147 | 29 | 16 |
| em_workwear_home | 173 | 123 | 37 | 13 |
| chadlaw_away | 171 | 133 | 27 | 11 |
| cch_away | 161 | 122 | 28 | 11 |
| fairway_home | 156 | 101 | 32 | 23 |
| mna_support_service_home | 105 | 77 | 19 | 9 |
| mna_cladding_home | 92 | 64 | 18 | 10 |
| chadlaw_home | 72 | 44 | 17 | 11 |
| cch_home | 62 | 39 | 16 | 7 |
| **Tổng cộng** | **12,960** | — | — | — |

**Gộp home + away theo brand** (cách model thực tế nhóm để tính exposure), sắp xếp giảm dần:

| # | Brand | Home | Away | Tổng | Tỷ trọng |
|---|---|---|---|---|---|
| 1 | KLG | 1024 | 984 | **2008** | 15.5% |
| 2 | **MCP** | 755 | 669 | **1424** | 11.0% |
| 3 | Paints & Lacquers | 488 | 900 | 1388 | 10.7% |
| 4 | Romantica | 593 | 519 | 1112 | 8.6% |
| 5 | Ellgren | 496 | 383 | 879 | 6.8% |
| 6 | ACS Group | 452 | 402 | 854 | 6.6% |
| 7 | AON | 408 | 443 | 851 | 6.6% |
| 8 | **Bartercard** | 271 | 500 | **771** | 5.9% |
| 9 | Top Notch | 720 | — | 720 | 5.6% |
| 10 | ATM | 262 | 277 | 539 | 4.2% |
| 11 | Floor Tonic | — | 517 | 517 | 4.0% |
| 12 | EM Workwear | 173 | 276 | 449 | 3.5% |
| 13 | **Fairway** | 156 | 243 | **399** | 3.1% |
| 14 | MNA Support Service | 105 | 194 | 299 | 2.3% |
| 15 | MNA Cladding | 92 | 192 | 284 | 2.2% |
| 16 | Chadlaw | 72 | 171 | 243 | 1.9% |
| 17 | CCH | 62 | 161 | 223 | 1.7% |
| — | **Tổng cộng (17 brand)** | | | **12,960** | **100%** |

**Đính chính so với bản báo cáo trước:** bảng annotation trong bản trước (tổng 944 instance, lấy từ một lần train YOLO26 cũ trỏ tới dữ liệu không còn tồn tại trên máy) là **sai/lệch dataset**. Số liệu ở trên mới là số thật, lấy trực tiếp từ Roboflow, khớp với quy mô >4000 ảnh / ~13.000 instance mà nhóm đang dùng để train RF-DETR. Toàn bộ phân tích bên dưới đã được cập nhật lại theo số liệu này. Ngoài ra, đính chính thêm: dataset **có đầy đủ cả hai biến thể home và away** cho hầu hết brand (trước đó tôi nhận định sai là chỉ có kit home) — riêng Top Notch chỉ có home, Floor Tonic chỉ có away.

**Average Precision (AP) per class**, epoch cuối cùng của quá trình train RF-DETR (epoch 59, từ `metrics.csv` trong thư mục kết quả training):

| Class | AP |
|---|---|
| klg | 0.580 |
| **mcp** | **0.557** |
| **bartercard** | **0.490** |
| romantica | 0.508 |
| top_notch | 0.515 |
| floor_tonic | 0.474 |
| paints_lacquers | 0.437 |
| aon | 0.385 |
| cch | 0.422 |
| chadlaw | 0.426 |
| ellgren | 0.374 |
| em_workwear | 0.379 |
| mna_cladding | 0.355 |
| mna_support_service | 0.358 |
| acs_group | 0.446 |
| atm | 0.374 |
| **fairway** | **0.301 (thấp nhất trong 17 class)** |

**Confusion matrix (validation set, model YOLO26m — cùng dataset gốc):**
- `bartercard_home`: 4/6 dự đoán đúng trên đường chéo, 2 lần model dự đoán "bartercard" trên nền không có logo (background → false positive).
- `mcp_home`: 16 đúng, 2 bị bỏ sót (rơi vào background).
- `fairway_home`: không đủ mẫu trong tập validation của run này để đánh giá riêng.
- Không có trường hợp nào bị nhầm chéo giữa bartercard và một brand cụ thể khác (không có off-diagonal confusion rõ rệt).

---

## 3. Phân tích câu hỏi 1: MCP vs Fairway — vì sao AI cho ra % gần bằng nhau?

**Kết luận:** AI không "đánh giá Fairway ngang MCP" theo nghĩa tích cực — thực chất là **hai lỗi ngược chiều cộng lại vô tình trùng nhau ở mức 3.5%**:

- **MCP bị model đếm THIẾU:** Human = 7.0 → AI = 3.5, đúng bằng một nửa. MCP và Fairway đều thuộc **vùng lưng áo (back)** — vị trí nhỏ, lệch tâm khung hình, camera broadcast hiếm khi quay lưng cầu thủ. Công thức visibility (kết hợp diện tích box, vị trí so với tâm màn hình, confidence) vốn cho điểm thấp với logo ở vùng này, khiến nhiều detection hợp lệ bị loại khỏi phép tính exposure (dưới ngưỡng visibility hoặc thời lượng segment quá ngắn). Cột Visibility = 4.7 của MCP (thấp trong bảng) xác nhận điều này. AP của MCP (0.557) thực ra khá tốt và MCP có lượng annotation khá dồi dào (**1424 instance gộp home+away, xếp hạng 2/17**) — vấn đề không nằm ở chất lượng/số lượng data mà ở khâu tổng hợp exposure theo vị trí.
- **Fairway bị model ĐOÁN NHIỄU:** chỉ có **399 instance gộp home+away — bằng ~28% của MCP (1424)**, xếp gần cuối bảng (13/17), và AP thấp nhất toàn bộ 17 class (0.301). Với lượng dữ liệu ít (chưa bằng 1/3 MCP) và AP thấp như vậy, đáng lẽ Fairway phải bị đếm thiếu nặng hơn MCP. Nhưng AI lại ra 3.5 — ngang bằng, thậm chí nhỉnh hơn Human (3.0). Đây là dấu hiệu điển hình của model thiếu data: không học đủ đặc trưng thật của logo nên dễ bắt nhầm các chi tiết tương tự (màu áo, vệt mờ do chuyển động, viền chữ) thành "fairway" — tức phần % này nhiều khả năng lẫn false positive, tình cờ bù đắp cho phần recall bị thiếu.

→ MCP: model "trung thực nhưng bị luật visibility/segment cắt bớt do vị trí lưng". Fairway: model "thiếu dữ liệu nên đoán nhiễu, bù ngẫu nhiên vào chỗ thiếu". Hai cơ chế khác nhau, tình cờ hội tụ về cùng một con số — không phản ánh đúng chênh lệch thực tế mà mắt thường quan sát được (Human 7.0 vs 3.0).

---

## 4. Phân tích câu hỏi 2: Bartercard — vì sao % AI cao bất thường?

**Kết luận:** Không phải do có nhiều dữ liệu annotate vượt trội — Bartercard có **771 instance gộp home+away, xếp hạng 8/17, gần như đúng bằng mức trung bình dataset (762)**, và không có dấu hiệu bị nhầm nhãn sang brand khác trong confusion matrix. Nguyên nhân nhiều khả năng nhất là **model quá tự tin (over-confident) + đếm lặp**, được khuếch đại bởi vị trí đặt logo dễ thấy.

Bằng chứng cho thấy đây là pattern hệ thống, không phải ngẫu nhiên:

- **KLG có hiện tượng giống hệt:** Human 5.0 → AI 17.0 (gấp 3.4 lần). KLG là class có **nhiều annotation nhất toàn dataset (2008 instance, gấp 2.6 lần Bartercard)** và AP cao nhất (0.580). Bartercard đứng thứ 3 về AP (0.490) dù lượng data chỉ ở mức trung bình. → **Hai class được train "tự tin" nhất (AP cao nhất) chính là hai class bị AI đếm vọt cao nhất so với Human — không phụ thuộc vào việc chúng có nhiều data nhất hay không (Bartercard chỉ trung bình).** Đây không phải trùng hợp ngẫu nhiên mà là dấu hiệu overconfidence/đếm lặp của model ở các class detect "dễ" (AP cao).
- **Cơ chế nghi ngờ:**
  1. Ngưỡng confidence khi inference khá thấp (0.25) — model tự tin cao dễ bắt cả những khoảnh khắc mờ/một phần/thoáng qua mà người đếm tay sẽ bỏ qua vì không coi là "xuất hiện thật sự".
  2. Cơ chế tracking (nối các detection cùng một logo vật lý qua nhiều frame thành 1 lần xuất hiện) có thể bị đứt gãy khi logo bị che khuất hoặc góc quay đổi đột ngột — khiến MỘT lần xuất hiện thực tế bị tách thành NHIỀU lần đếm riêng biệt trong khi Human chỉ đếm 1 lần.
  3. Từ confusion matrix: bartercard có 2/6 mẫu validation bị model dự đoán nhầm trên nền không có logo (background → bartercard) — tỷ lệ false-positive-trên-nền không nhỏ so với cỡ mẫu, dù không nhầm cụ thể với brand nào khác.
- **Vị trí logo cũng góp phần:** Bartercard nằm ở vùng ngực — slot lớn, ở giữa, hướng thẳng về camera nhiều hơn — nên visibility tự nhiên cao hơn hẳn (cột Visibility = 11.6, cao nhất bảng). Một phần % cao là **thật** (logo to, dễ thấy hơn logo vùng lưng/tay), nhưng biên độ lệch gần 5 lần so với Human vượt xa mức chênh lệch hợp lý do vị trí đơn thuần — nên phần lớn khả năng vẫn đến từ việc model đếm lặp/bắt nhiễu.

→ Không phải "pattern mới" (không có gì bất thường về nội dung logo) và không phải model nhầm sang brand khác — mà là hệ quả của việc model có recall cao/tự tin cao cho đúng những class được train tốt nhất, kết hợp với cách tính exposure theo segment dễ bị đếm lặp.

---

## 5. Bảng tổng hợp nguyên nhân

| Brand | Vấn đề | Nguyên nhân chính | Loại lỗi |
|---|---|---|---|
| MCP | AI thấp hơn Human (3.5 vs 7.0) | Vị trí lưng → visibility score thấp → bị lọc khỏi exposure dù detect đúng | Đếm thiếu (false negative do ngưỡng lọc) |
| Fairway | AI ngang/hơn Human dù ít data | Chỉ 399 instance (~28% của MCP), AP thấp nhất (0.301) → model đoán nhiễu | Đếm nhiễu (false positive do thiếu data) |
| Bartercard | AI cao gấp 4.9 lần Human | Model AP khá cao (0.490) dù lượng data chỉ ở mức trung bình (771 instance) + confidence threshold thấp + khả năng đếm lặp qua tracking + vị trí ngực dễ thấy | Đếm lặp / quá nhạy (false positive do overconfidence) |
| KLG (đối chứng) | AI cao gấp 3.4 lần Human | Cùng cơ chế như Bartercard — class nhiều data nhất (2008 instance), AP cao nhất (0.580) | Đếm lặp / quá nhạy |

---

## 6. Đề xuất hành động

1. **Với MCP/Fairway (vùng lưng):** xem xét giảm mức phạt của visibility score cho các logo ở vị trí lưng, hoặc hạ ngưỡng thời lượng tối thiểu tính vào exposure — hiện tại đang phạt quá nặng các logo nhỏ/lệch tâm bất kể detect đúng hay sai. Song song, bổ sung thêm ảnh annotate cho Fairway (đặc biệt góc lưng, ảnh mờ do chuyển động, bị che một phần) để kéo AP lên ngang MCP.
2. **Với Bartercard/KLG (đếm lặp):** lọc lại các detection có confidence thấp (< 0.5) trên video đã inference để xem có phải phần lớn là box nhỏ/mờ/thoáng qua hay không. Kiểm tra số lượng track riêng biệt trên cùng một pha bóng — nếu một lần xuất hiện thực tế bị tách thành nhiều track do đứt gãy tracking, cần cải thiện logic nối track (tăng độ chịu occlusion) hoặc gộp lại các segment quá gần nhau về thời gian trước khi tính exposure.
3. **Kiểm tra chéo:** chạy lại đúng đoạn video đã dùng để tính bảng Human/AI này, in ra danh sách toàn bộ detection của Bartercard và Fairway kèm confidence + timestamp, đối chiếu trực tiếp với video gốc để xác nhận tỷ lệ thật/giả trong từng trường hợp — đây là cách kiểm chứng nhanh và chắc chắn nhất trước khi điều chỉnh tham số model.
4. **Chuẩn hoá lại việc đếm Human vs AI:** đảm bảo cả hai phương pháp đang đếm trên cùng một định nghĩa "một lần xuất hiện" (theo segment liên tục hay theo tổng thời lượng cộng dồn) — nếu định nghĩa lệch nhau, một phần chênh lệch quan sát được có thể chỉ là do cách đếm khác nhau chứ không phải lỗi model.
