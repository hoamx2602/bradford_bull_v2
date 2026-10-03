# Chạy full match → report Location Breakdown (CLI)

Tài liệu này mô tả cách lấy file Excel **Location Breakdown** (giống `BB1_locations.xlsx`)
cho một trận **full match** mà không cần upload qua trình duyệt và không cần chạy
frontend Next.js.

> Nội dung của report — ý nghĩa từng cột, công thức AI % — xem
> [10-location-breakdown.md](10-location-breakdown.md) và
> [11-ai-percentage-calculation.md](11-ai-percentage-calculation.md).
> Tài liệu này chỉ nói về **cách chạy**.

---

## 1. Vì sao có CLI riêng

Luồng web (upload → `/processing` → dashboard → nút *Export .xlsx*) phải đẩy toàn bộ
file qua HTTP upload và cần cả backend + frontend chạy. Với một trận ~100 phút
(1–3 GB) việc đó vừa chậm vừa dễ đứt.

`backend/scripts/run_match_report.py` trỏ **đúng pipeline đó** vào một thư mục video,
ghi kết quả vào cùng SQLite DB (nên trận vẫn hiện trên dashboard), rồi xuất một
file `.xlsx` cho mỗi video.

Runner chỉ chạy nhánh **analytics**. Ba video overlay (annotated preview, body-part
segmentation, team-detection) là render full-fps bị chặn ở ~30–60 giây đầu, tốn
nhiều phút và **không** ảnh hưởng số liệu report → mặc định tắt (`--with-overlays`
để bật lại).

---

## 2. Quy trình

```bash
# 1. Thả video vào thư mục input (tạo sẵn ở repo root)
#    D:\bradford_bull_v2\match_input\

# 2. Chạy
conda activate bradford_bulls
python backend/scripts/run_match_report.py --kit home

# 3. Lấy report
#    D:\bradford_bull_v2\match_reports\<tên video>_locations.xlsx
```

Mọi video trong `match_input/` được xử lý lần lượt. Video đã có analysis (cùng tên
file + cùng kit) sẽ được **export lại luôn** thay vì chạy detection lần nữa; dùng
`--force` để buộc chạy lại.

### Các tuỳ chọn hay dùng

| Flag | Ý nghĩa |
|---|---|
| `--kit home\|away` | Kit Bradford mặc trong trận. Quyết định Main Sponsor = Top Notch (home) hay Floor Tonic (away), và cụm kit nào là đội nhà. **Bắt buộc đúng.** |
| `--fps 2` | Số frame phân tích mỗi giây video (mặc định 2). |
| `--video <path>` | Chạy đúng 1 file, bỏ qua `--input-dir`. Lặp lại được. |
| `--event "BB2"` | Tên event ghi vào report và vào tên file xuất ra. |
| `--detector yolo\|rfdetr` | Ghi đè backend detector của `backend/.env`. |
| `--no-team-filter` | Đếm logo trên **mọi** cầu thủ (khi team filter chọn nhầm đội). |
| `--team-refs <file.pkl>` | Dùng reference đội đã biết là đúng thay vì tự bootstrap. |
| `--export-only <analysis_id>` | Không chạy detection, chỉ xuất lại Excel từ analysis đã có. |
| `--criteria size,position,...` | Xuất thử với một bộ tiêu chí AI khác mà không đổi Settings. |

---

## 3. Tốc độ

Chi phí gần như tuyến tính theo **số frame lấy mẫu** = `thời lượng × --fps`.

- `--fps 2` trên trận 104 phút ≈ **12.500 frame**.
- Mỗi frame chạy: logo detector + YOLO11x-pose (body zone) + person detector và
  SigLIP của team filter.

Giảm `--fps` xuống 1.0 sẽ giảm gần một nửa thời gian. Với report theo **vị trí**
(chia tỉ lệ giữa các zone) thì 1–2 fps đã đủ ổn định; đừng lấy hết frame.

Frame sampling dùng `cap.grab()` cho các frame **không** lấy mẫu và chỉ
`retrieve()` frame thật sự cần — ở 2fps trên video 30fps điều này bỏ qua ~93 %
công decode.

---

## 4. Team reference — chỗ dễ sai nhất

Team filter quyết định cầu thủ nào là Bradford. Nếu nó chọn nhầm đội thì **toàn bộ
logo Bradford bị loại** và report vô nghĩa.

- File toàn cục `backend/data/team_refs.pkl` được build cho **một kit** (hiện tại
  là `away`/đen). Luồng web chỉ dùng lại file này khi nó tồn tại → chạy một trận
  **home** sẽ âm thầm dùng reference của kit away.
- Vì vậy runner **luôn bootstrap reference từ chính video**, theo từng
  `(video, kit)`, và cache ở `backend/data/auto_refs/<tên video>-<kit>.pkl`.

Bootstrap chọn đúng đội bằng cách so cụm jersey với **kit anchor** — ảnh áo đấu cắt
từ artwork trong `KIT/`:

```bash
python backend/scripts/make_kit_anchors.py
# -> backend/data/kit_anchors/{home,away}/{front,back}.jpg
```

Không có anchor, bootstrap phải đoán bằng độ sáng áo và sẽ bỏ cuộc khi hai kit
sáng gần bằng nhau (`kits not separable by luminance`).

Sau mỗi lần chạy, runner in ra:

```
team filter: kept 8421 / dropped 5133 logo detections (drop rate 0.379)
17 brand(s) detected: Top Notch, MCP, KLG, ...
```

Drop rate gần 1.0 ⇒ nhiều khả năng chọn nhầm đội → chạy lại với `--no-team-filter`
hoặc `--team-refs`.

---

## 5. Ô trống trong report

Report **không** điền `0.00` cho ô không có số liệu. Một Location để trống
`AI % / AI Adjusted % / Visibility %` khi:

- chưa map logo nào vào Location đó (ví dụ *Collar Back*), hoặc
- anchor zone của nó chưa từng được detect trong video.

`0.00` sẽ đọc thành "đo được và bằng 0", khác hẳn với "không đo được". `AI Adjusted %`
cũng chỉ được tính trên các Location **có** số liệu, nên nó vẫn tổng đúng 100 %.

Sheet **AI % Detail** có thêm cột `Locations on anchor` và `Quality (this location)`
vs `Quality (whole zone)`: khi nhiều Location dùng chung một anchor (COCO-17 không
tách được các slot cổ/lưng sát nhau, ví dụ *Top Back* và *Nape Neck* cùng
`back-top`), quality của zone được chia đều — cột `AI %` khớp với
`Quality (this location)`, không khớp với quality của cả zone.
