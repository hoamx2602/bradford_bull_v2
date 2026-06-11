# 4. Team filter — chỉ đếm logo trên cầu thủ Bradford

## Vấn đề

Nhiều sponsor xuất hiện trên áo **cả hai đội** (hoặc trên biển LED, áo trọng
tài). Model logo chỉ được train trên kit Bradford nhưng vẫn match nhầm các
logo giống nhau ở nơi khác → EMV bị thổi phồng. Khách hàng mua slot trên áo
Bradford thì chỉ được đếm đúng những lần logo nằm trên cầu thủ Bradford.

## Thiết kế (port từ prototype `team_detection/`, production hóa)

Cùng họ kỹ thuật với top SoccerNet GSR Challenge (color/embedding clustering +
tracklet voting) — **không train model riêng**, vì kit đối thủ đổi mỗi trận;
reference-based tự thích nghi từng trận.

```
mỗi sampled frame:
  YOLO11 person + BoT-SORT  ──►  track_id ổn định cho từng cầu thủ
        │
  jersey crop (band 15–45% bbox, bỏ pixel cỏ + da)
        │
  classify = fuse( color histogram , SigLIP embedding )
        │            └ trọng số học từ chính refs (đen/trắng → color thắng)
  VoteTracker: vote tích lũy theo track + hysteresis 1.25×
        │            └ một frame mờ không lật được nhãn
  logo → owner person (bbox nhỏ nhất chứa tâm logo, else gần nhất)
        │
  owner == TARGET ? giữ : DROP
```

Code: `backend/app/pipeline/teamid/` — `jersey.py`, `features.py`,
`classifier.py`, `tracker.py`, `bootstrap.py`.

## Kit references — 3 nấc, không có bước manual

| Ưu tiên | Cách | Setup |
|---|---|---|
| 1 | **File refs thủ công** `data/team_refs.pkl` (nếu tồn tại) | CLI `scripts/build_team_refs.py` — chỉ khi muốn override |
| 2 | **Auto-bootstrap + kit anchors** — cluster cầu thủ trong 32 frame đầu của chính video, chọn cluster giống ảnh kit chính thức nhất | `scripts/make_kit_anchors.py` một lần |
| 3 | **Auto-bootstrap + luminance** — kit away (đen) → cluster tối nhất | Zero |

Nấc 2 là mặc định thực tế: anchors được cắt tự động từ `KIT/*.jpg`.
Mỗi lần bootstrap, refs debug lưu tại `data/auto_refs/<video>-<kit>.pkl`.

## Chính sách giữ/bỏ (an toàn cho doanh thu)

- Owner là TARGET → **giữ**
- Owner là OTHER nhưng track chưa đủ phiếu (`TEAM_MIN_VOTES`) → **giữ**
  (`TEAM_KEEP_UNKNOWN=true` — thiếu bằng chứng thì không trừ tiền khách)
- Owner là OTHER, đủ phiếu → **bỏ**
- Không gắn được với người nào (LED board, khán đài) → **bỏ**
  (`TEAM_KEEP_UNASSIGNED=false`)

## Config

| Env var | Default | Ý nghĩa |
|---|---|---|
| `TEAM_FILTER_ENABLED` | `true` | bật/tắt stage |
| `TEAM_AUTO_REFS` | `true` | bootstrap khi không có refs file |
| `TEAM_PERSON_MODEL` | `yolo11m.pt` | Mac dùng `yolo11n.pt` |
| `TEAM_PERSON_IMGSZ` | `960` | Mac dùng 640 |
| `TEAM_SIGLIP_EVERY` | `5` | re-embed mỗi track sau N frame (cache) |
| `TEAM_BOOTSTRAP_FRAMES` | `32` | số frame sample khi bootstrap |
| `TEAM_HYSTERESIS` | `1.25` | độ lì của nhãn vote |
| `TEAM_MIN_VOTES` | `2.0` | khối lượng phiếu trước khi tin nhãn OTHER |
| `TEAM_DARK_KITS` | `away` | kit nào được coi là tối (luminance rule) |
| `TEAM_REFS_PATH` | `data/team_refs.pkl` | refs override |

## Chẩn đoán

- **Dashboard**: badge "Target-team filter: kept X · dropped Y (Z%)" trong
  Match Analysis. Với trận 2 đội chung sponsor, dropRate hợp lý ~5–60% tùy clip.
  **Gần 0% hoặc >90% bất thường** → nghi bootstrap chọn nhầm cluster.
- Mở `data/auto_refs/<video>-<kit>.pkl` xem `meta.bootstrap` (anchors/luminance)
  và log `team bootstrap: N crops, k=3, target=cluster i (...)`.
- Khắc phục: đảm bảo `data/kit_anchors/<kit>/` tồn tại, hoặc build refs tay
  bằng CLI rồi đặt `TEAM_REFS_PATH`.

## Kết quả test thực tế (clip Bradford vs Hull FC, M4/MPS)

| Clip | Bootstrap | Kết quả |
|---|---|---|
| 00-28 (6.6s) | 31 crops, chọn đúng cluster đen (by anchors) | kept 6 / dropped 0 — KLG đúng zone Shorts Back |
| 01-46 (9.4s) | 39 crops, Bradford chỉ 8 crops, vẫn chọn đúng | kept 15 / dropped 1 — Floor Tonic đúng zone Chest Centre |
