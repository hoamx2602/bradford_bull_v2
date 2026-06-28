# Analysis Log

> Nhật ký phân tích / đánh giá / quyết định thiết kế. Mỗi entry ngắn gọn; chi tiết
> ở `../expert_review_and_plan.md` và các doc chuyên sâu. Quản lý bởi skill
> `/log-analysis` (newest-on-top — chèn entry mới ngay dưới marker).

<!-- new entries below -->

## 2026-06-28 — Quyết định: dừng tinh chỉnh Tầng 2 lúc này, ưu tiên aggregation engine (Phase 3)
**Bối cảnh / câu hỏi:** tiếp tục Tầng 2 có khả thi & cho kết quả tốt không, hay sang Phase 3?
**Phương án xem xét:** (a) tiếp Phase 2 (calibrate τ, bật OCR, chỉnh trọng số fusion); (b) sang Phase 3.
**Kết luận / khuyến nghị:** Tầng 2 khả thi — closed-set mạnh (top-1 0.99), open-set cải thiện được bằng OCR — NHƯNG **không tinh chỉnh thêm bây giờ**: mọi số đang trên data synthetic → calibrate/tune sẽ overfit artifact (false confidence). Code Phase 2 đã đủ. Chạy song song: (1) user lo data thật (SAM 3 + gold set) để validate Phase 1+2; (2) tôi xây **aggregation engine** (detections→ByteTrack→temporal smoothing→exposure-sec/visibility%/EMV) — data-independent, cắm vào `eval_exposure.py`.
**Lý do:** bottleneck thật là thiếu data in-domain, không phải thiếu code Tầng 2; temporal self-training cũng cần SAM3+video nên hoãn cùng; aggregation là nơi giá trị sản phẩm + edge case (Production-System-Design) và test được ngay.
**Đổi ý nếu:** có dù chỉ ít crop THẬT (+ vài logo lạ) → lúc đó OCR + calibrate τ đáng làm ngay.
**Tham chiếu:** `../expert_review_and_plan.md` Phần 2/3; `../auto_label/eval_exposure.py`; `data/demo_phase2/`.

## 2026-06-28 — Khảo SOTA 2026 + đánh giá chuyên gia toàn hệ
**Bối cảnh / câu hỏi:** cần đối chiếu thiết kế hiện có với công cụ SOTA mới nhất rồi ra kế hoạch triển khai + test.
**Phương án xem xét:** SAM 3 vs Grounding DINO+SAM2 (auto-label); YOLOv11-OBB vs HBB; DINOv3/SigLIP2 vs CLIP (Tầng 2); Gen2Det/diffusion; 3DGS vs Blender (Bậc 4).
**Kết luận / khuyến nghị:** kiến trúc 2 tầng đúng & khớp SOTA; nâng auto-label lên **SAM 3** (exemplar+track), distill **YOLOv11-OBB**, encoder Tầng 2 **DINOv3**, temporal self-training là ưu tiên #1, deblur Tier 3/4 hạ ưu tiên; rủi ro lớn nhất là over-engineering + thiếu thước đo.
**Lý do:** OBB cần cho visibility%→EMV; DINO fine-grained > CLIP; diffusion lift nhỏ (Gen2Det ~+2 mAP) → validate trước.
**Tham chiếu:** `../expert_review_and_plan.md` (toàn bộ); nguồn SOTA liệt kê ở Phần "Nguồn tham khảo".

## 2026-06-27 — Critique thang synthetic (Bậc 3 diffusion, Bậc 4 3D)
**Bối cảnh / câu hỏi:** đánh giá tính khả thi Bậc 3/4 trong nhánh autolabel.
**Phương án xem xét:** Bậc 1 copy-paste / Bậc 3 diffusion inpainting / Bậc 4 3D sim (Blender vs 3DGS).
**Kết luận / khuyến nghị:** Bậc 3 khả thi CAO nhưng tách luồng Tầng1(composite_back)/Tầng2(giữ biến thể+embedding-gate); Bậc 4 R&D bet, chỉ cho visibility%/occlusion, ưu tiên 3DGS-hybrid; coi chừng over-engineering.
**Lý do:** `composite_back` mâu thuẫn giá trị Tầng 2; effort 3D bị ước lượng thấp; ngưỡng sim2real cho recognition cao hơn SoccerSynth.
**Tham chiếu:** `../expert_review_and_plan.md` §0.3; `../bac3_diffusion_inpainting.md`, `../bac4_3d_simulation.md`.

## 2026-06-27 — Critique tài liệu Motion-blur (Tier 3/4)
**Bối cảnh / câu hỏi:** đánh giá Tier 3 (RAFT fusion) & Tier 4 (frame interpolation).
**Kết luận / khuyến nghị:** hạ ưu tiên deblur pixel; Tier 3 → BSSTNet/local ROI, đo bằng mAP/EMV không PSNR; Tier 4 KHÔNG phải deblur (đừng đếm frame nội suy là exposure); thay bằng blur-robust augmentation + temporal smoothing mức track.
**Lý do:** không hệ thương mại nào deblur pixel; train trên frame deblur gây train/serve mismatch.
**Tham chiếu:** `../expert_review_and_plan.md` §0.2; `../Motion-blur.MD`.

## 2026-06-27 — Kiến trúc decoupled 2 tầng (bỏ manual annotate, scale đa club/môn)
**Bối cảnh / câu hỏi:** vì sao fine-tune YOLO per-club không scale; làm sao bỏ manual annotate.
**Kết luận / khuyến nghị:** tách Tầng 1 Localizer class-agnostic (train 1 lần) + Tầng 2 Recognizer bằng embedding retrieval (thêm logo = thêm vector, zero retrain); input logo/kit/video map vào template+synthetic+auto-label.
**Lý do:** danh tính club bị nướng vào trọng số → club mới = retrain; retrieval tách định danh ra khỏi train.
**Tham chiếu:** `../expert_review_and_plan.md` §0.1; `../autolabel.md`.
