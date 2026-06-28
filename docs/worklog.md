# Work Log

> Nhật ký triển khai: đã làm gì + **mục tiêu** + cách kiểm chứng. Quản lý bởi skill
> `/log-work` (newest-on-top — chèn entry mới ngay dưới marker).

<!-- new entries below -->

## 2026-06-28 — Glue end-to-end: video → dets.jsonl → exposure
**Mục tiêu (vì sao làm):** nối trọn Tầng1 + Tầng2 + aggregation thành **1 lệnh chạy 1 video → exposure**; mảnh data-independent cuối trước khi cần SAM3 + gold thật.
**Đã làm:** `auto_label/run_pipeline.py` — sample frame → YOLOv11-OBB localizer → crop+mask(OBB) → recognizer (brand+score) + clarity(Laplacian) + area_pct(shoelace) → `dets.jsonl` → `aggregate` → `result.json` (+ tự eval nếu có `--gold`). Cờ: `--tau` open-set, `--w-color/--w-text/--score`, `--bridge/--min-seg/--rate/--every`.
**Kiểm chứng / kết quả:** smoke thật GPU (localizer Phase1 + DB Phase2 + video AON tổng hợp): **14/14 present-frame được localize, conf ~0.98**; aggregate ra segment + exposure. **NHƯNG recognizer gán nhầm AON→mna_cladding** (rec_score ~0.39); với `--tau 0.55` → reject hết (0 false-attribution nhưng miss AON). Artifacts `data/demo_e2e/`.
**Caveat / hạn chế:** phát hiện THẬT — Tầng 2 zero-shot **yếu trên logo cách điệu** (AON) ở render held-out; DB chỉ dựng từ logo PNG sạch. Fix: build DB kèm **gallery crop từ render thật** (auto-label gallery / `--gallery`) và/hoặc fine-tune; calibrate τ trên validation. Localizer thì khỏe. Mọi thứ vẫn synthetic.
**Bước tiếp:** cần SAM3 + video thật để (1) auto-label sinh gallery thật cho Tầng 2 DB, (2) gold set calibrate τ + đo thật. Bottleneck = dữ liệu, không phải code.

## 2026-06-28 — Phase 3: aggregation engine (detections → exposure/visibility/EMV)
**Mục tiêu (vì sao làm):** chuyển detection per-frame (Tầng1+Tầng2) thành **metric sản phẩm** (exposure-seconds, visibility%, EMV) với xử lý edge case — phần data-independent, nơi giá trị sản phẩm nằm (Production-System-Design: "startup chết ở aggregation, không phải detection").
**Đã làm:** `auto_label/aggregate.py` — temporal smoothing (bắc cầu flicker), drop ghost (min_seg), lọc conf, loại scene (replay/adbreak), coverage cộng+clamp 100, clarity-weighted `quality_exposure_sec`, EMV (placeholder), segments. Output **khớp `eval_exposure.py`**. +5 tests.
**Kiểm chứng / kết quả:** 32/32 pytest; demo end-to-end `data/demo_phase3/`: aggregate → aon 8.4s (liên tục), bartercard 4.4s (**flicker bắc cầu + ghost frame-500 bị bỏ**), klg(replay)/mcp(low-conf) bị loại → eval_exposure MAE 1.2s (do floor_tonic bị miss), temporal IoU 0.94.
**Caveat / hạn chế:** edge case CHƯA xử lý (cần detector riêng): LED board cycling per-board, graphic-overlay occlusion. Scene-exclude cần nhãn scene từ upstream (engine nhận, không tự phân loại). EMV là placeholder (pricing thật ở `LOGOS_Exposure_Pricing_Algorithm.md`). Tracking hiện **presence-based** (đủ cho exposure-seconds); box-level ByteTrack là refinement để đếm instance / re-id sau camera-cut.
**Bước tiếp:** glue chạy localizer+recognizer trên video thật → sinh `dets.jsonl`; (tùy chọn) scene classifier; calibrate trên gold thật.

## 2026-06-28 — Phase 2: bật OCR thật (easyocr) cho kênh text fingerprint
**Mục tiêu (vì sao làm):** kiểm chứng OCR text có "cứu" được open-set rejection của Tầng 2 không (color thắng ở demo bị nghi là artifact).
**Đã làm:** `pip install easyocr`; build DB có OCR + query fuse text (kênh đã wire sẵn). So các cấu hình color/text.
**Kiểm chứng / kết quả (demo synthetic):** OCR đọc tốt logo nhiều chữ (mna/cedar court/chadwick/bartercard/romantica), **fail logo cách điệu** (aon='', atm garbled). AUROC: visual 0.69 → +color0.3 0.86 → +text0.5 0.86 → **color+text 0.89 (best)**; text=1.0 làm top-1 sập 0.65. Best (mask+color0.3+text0.5): AUROC 0.89, τ=0.6 → known-acc 0.89 & reject 70% unknown; muốn reject 100% (Youden) thì known-acc tụt 0.69. Artifacts: `data/demo_phase2/{templates_txt.npz,pred_best.jsonl,eval_recognition_best.json}`.
**Caveat / hạn chế:** OCR giúp **MODEST, không phải silver bullet**; logo-dependent (vô dụng với icon logo như AON); over-weight text hỏng closed-set; vẫn KHÔNG tách sạch unknown. Mọi số synthetic → chỉ minh hoạ cơ chế.
**Bước tiếp:** cần crop THẬT để kết luận open-set; nếu cần reject cao hơn → fine-tune/ArcFace metric head.

## 2026-06-28 — Phase 2 tiếp: open-set scoring (margin) + calibrate τ
**Mục tiêu (vì sao làm):** cho Tầng 2 một **ngưỡng vận hành** dùng được (thay vì hardcode τ) và thử tín hiệu open-set scale-free tốt hơn cosine thô — để khi có data thật là chọn được điểm vận hành.
**Đã làm:** `auto_label/recognizer.py` thêm `score_mode='margin'` (top1−top2 theo brand) + gom template theo brand; `auto_label/eval_recognition.py` thêm `calibrate()` (τ theo target known-acc + điểm Youden) + CLI `--calibrate`; +tests.
**Kiểm chứng / kết quả:** 28/28 pytest. Demo (synthetic, illustrative): calibrate trên cosine (AUROC 0.86) → τ*=0.784 giữ known-acc 0.91 & reject 40% unknown; Youden τ=0.866 reject 100% unknown nhưng known-acc tụt 73%. **Margin LÀM TỆ HƠN: AUROC 0.86→0.47.**
**Caveat / hạn chế:** margin tệ vì DB có brand gần-trùng (romantica vs romantica_beds) → known cũng margin nhỏ → tín hiệu hỏng ⇒ margin là **data-dependent, KHÔNG mặc định tốt**. Mọi số trên synthetic → chỉ minh hoạ cơ chế, không phải chất lượng thật; τ chỉ đáng tin khi calibrate trên **validation THẬT**.
**Bước tiếp:** cần crop thật để calibrate có nghĩa; OCR text cho reject robust; rồi mới chốt score_mode + τ.

## 2026-06-28 — Phase 2 vá open-set: mask nền + logo fingerprint
**Mục tiêu (vì sao làm):** raw DINOv2 đạt closed-set tốt nhưng open-set AUROC chỉ ~0.61 (không từ chối nổi logo lạ — rủi ro gán nhầm/thổi EMV). Cần tăng khả năng reject unknown của Tầng 2.
**Đã làm:** thêm vào `auto_label/recognizer.py`: #1 `--mask` (crop sát + xoá nền theo alpha/mask SAM 3 trước embed), #2 fingerprint fuse visual⊕color(hue-hist)⊕OCR text (`--w-color`, `--w-text`, `--text-backend easyocr|tesseract`). Cập nhật DB lưu color+text; +tests.
**Kiểm chứng / kết quả:** demo dinov2-base 16 brand: top-1 0.93→**0.99** (mask), AUROC 0.68→**0.86** (mask+color0.3)→0.93 (color0.8). 25/25 pytest pass.
**Caveat / hạn chế:** dải điểm known/unknown vẫn chồng → τ phải calibrate trên validation; color thắng đậm do brand demo khác màu (data thật cần OCR); OCR chưa chạy được ở đây (cần `pip install easyocr`). Closed-set lạc quan (query là augment của template).
**Bước tiếp:** hàm calibrate τ trên validation; bật OCR text channel; hoặc sang Phase 3.

## 2026-06-28 — Phase 2: Tầng 2 Recognizer (embedding + retrieval)
**Mục tiêu (vì sao làm):** định danh brand theo cách "thêm logo = thêm vector, KHÔNG train lại" → cốt lõi để scale đa club/đa môn.
**Đã làm:** `auto_label/recognizer.py` (build Template DB + query), encoder DINOv2/v3/SigLIP2 qua transformers, store numpy cosine; xuất JSONL cho `eval_recognition.py`.
**Kiểm chứng / kết quả:** chạy thật dinov2-base; selftest + pytest pass; demo artifacts `data/demo_phase2/`.
**Caveat / hạn chế:** faiss/qdrant chưa cài (numpy đủ cho hàng nghìn template); open-set yếu (xem entry vá phía trên).
**Bước tiếp:** vá open-set (đã làm).

## 2026-06-28 — Phase 1: SAM 3 → YOLOv11-OBB localizer (Tầng 1)
**Mục tiêu (vì sao làm):** dựng localizer class-agnostic (1 lớp `logo`) distill từ teacher SAM 3, xuất OBB sát viền (visibility%→EMV) — nền tảng tổng quát giữa club/môn.
**Đã làm:** nâng cấp `auto_label/sam3_exemplar_autolabel.py` (`--obb` từ mask SAM3 minAreaRect, `--class-agnostic`); thêm `auto_label/train_localizer.py` (train + predict→eval_obb); data.yaml ghi path tuyệt đối.
**Kiểm chứng / kết quả:** smoke end-to-end trên GPU (RTX 5060 Ti): train YOLOv11n-OBB → predict → eval_obb chạy thông; demo học-được (copy-paste logo thật) gold mAP50=1.0, mAP50-95≈0.96, ảnh viz đúng box nghiêng. pytest pass.
**Caveat / hạn chế:** số demo bão hòa (task quá dễ) → vô nghĩa về chất lượng; chạy thật cần SAM 3 weights + video + gold set; adapter SAM 3 cần khớp API ultralytics thực tế.
**Bước tiếp:** chạy thật, vượt cổng OBB mAP@0.5 ≥ baseline YOLO26 trên gold set khó.

## 2026-06-28 — Phase 0: bộ eval + khung gold set
**Mục tiêu (vì sao làm):** "đo trước, xây sau" — có thước đo khách quan (gold set) trước khi triển khai, làm cổng go/no-go cho các phase.
**Đã làm:** `auto_label/eval_obb.py` (OBB mAP, polygon IoU), `eval_recognition.py` (top-1 + open-set AUROC), `eval_exposure.py` (exposure-sec/visibility% MAE), `gold_set.py` (scaffold/validate/stats + stratify), `tests/test_eval.py`.
**Kiểm chứng / kết quả:** mỗi module có `--selftest`; 20→25 pytest pass; smoke CLI end-to-end.
**Caveat / hạn chế:** cần người dựng gold set thật + annotate tay (~300–500 frame, phủ stratum khó).
**Bước tiếp:** Phase 1.
