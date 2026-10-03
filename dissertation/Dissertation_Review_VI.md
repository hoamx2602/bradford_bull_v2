# Đánh giá dissertation LogoLens (giới hạn 12.000 từ)

Ngày rà soát: 05/08/2026  
Phạm vi: bản Markdown và DOCX v12, mã nguồn `backend`, frontend `logo-analytics`, checkpoint clip-disjoint và các artefact kết quả hiện có.

## 1. Kết luận ngắn

Đề tài phù hợp với MSc Applied AI and Data Analytics và đã có một artefact kỹ thuật đáng kể: pipeline end-to-end, giao diện chạy được, detector được đánh giá trên dữ liệu broadcast thật, cùng các kiểm tra leakage, team attribution, sensitivity và annotation effort. Tuy nhiên, bản hiện tại **chưa nên nộp** vì còn bốn vấn đề ưu tiên cao:

1. Phần Chapters 1–7 đang được script trên trang bìa tính là **13.646 từ**, vượt giới hạn 12.000 từ **1.646 từ (13,7%)**. Toàn DOCX có metadata khoảng 18.630 từ và 72 trang vì còn front matter, captions, references và appendices.
2. RQ5 không phải câu hỏi được kiểm nghiệm bằng phương pháp hoặc dữ liệu riêng; RQ4 đang dùng ngôn ngữ nhân quả mạnh hơn thiết kế thí nghiệm cho phép.
3. Công thức EMV trong backend và luận văn thiếu bước quy CPM của spot 30 giây về giá mỗi giây. Ví dụ US$105.600 hiện cao hơn 30 lần so với phép tính có chuẩn hóa thời gian, trước cả sponsorship discount.
4. Luận văn, README, frontend và cấu hình runtime không hoàn toàn thống nhất về YOLO/RF-DETR, phiên bản Ultralytics và chính sách giữ/bỏ attribution “unknown”. Điều này làm yếu claim về reproducibility.

Sau khi sửa bốn điểm trên, cấu trúc nghiên cứu có thể trở thành một dissertation tốt. Trọng tâm nên là **measurement validity under constrained resources**, không phải quảng bá một sản phẩm thương mại hoàn chỉnh.

## 2. Research questions đề xuất

Nên dùng bốn RQ, mỗi RQ gắn với một loại bằng chứng rõ ràng:

**RQ1.** *To what extent can a consumer-hardware pipeline correctly detect and attribute kit-sponsor logos in unseen broadcast clips under a leakage-controlled evaluation protocol?*

- Gộp detection và team attribution vì đây là hai bước quyết định một exposure có được ghi nhận đúng hay không.
- “Consumer-hardware” chính xác hơn “low-cost” nếu luận văn chưa đo chi phí thực tế.
- Nêu rõ training dùng rented cloud GPU; claim consumer hardware chỉ áp dụng cho inference/deployment nếu đúng với thí nghiệm.

**RQ2.** *What properties of sponsor-logo exposure in broadcast footage—multiplicity, screen share, rendered resolution and occlusion—constrain automated measurement?*

- Câu hỏi mô tả, phù hợp với EDA và occlusion audit hiện có.
- Trong phần kết quả, tách “đã đo được” khỏi “hàm ý suy luận”.

**RQ3.** *How sensitive are quality-weighted exposure and EMV estimates to visibility thresholds, confidence thresholds and temporal sampling rate?*

- Tốt hơn cách hỏi “How can detections be combined... in a principled way”, vì thiết kế artefact không tự chứng minh tính “principled”.
- Sensitivity chỉ cho biết hệ thống phản ứng thế nào; nó không xác nhận threshold 0,02 là đúng nếu chưa có exposure-level ground truth.

**RQ4.** *What association is observed between per-class annotation volume and held-out AP, and what indicative onboarding budget follows within this case study?*

- Dùng “association”, không dùng “affect”, vì 17 class không phải controlled subsampling experiment và còn confound bởi độ khó của logo cùng kích thước validation set.
- Mốc khoảng 500 instances chỉ nên gọi là **indicative case-study budget**, không phải threshold nhân quả hoặc quy tắc tổng quát.

Nên bỏ RQ5 hiện tại. Mối liên hệ với AI in advertising vẫn giữ ở motivation, literature review và discussion, nhưng là **discussion lens/objective**, không phải empirical research question.

## 3. Kế hoạch đưa về dưới 12.000 từ

Nên nhắm 11.700–11.900 từ để còn khoảng an toàn. Phân bổ gợi ý:

| Chương | Hiện tại (xấp xỉ, gồm nội dung hiển thị) | Mục tiêu |
|---|---:|---:|
| 1. Introduction | 1.469 | 1.200–1.300 |
| 2. Literature review | 2.015 | 1.700–1.800 |
| 3. Methodology | 2.268 | 1.700–1.850 |
| 4. System design | 2.385 | 1.700–1.850 |
| 5. Results | 4.963 | 3.200–3.500 |
| 6. Discussion | 1.668 | 1.300–1.450 |
| 7. Conclusion/future work | 1.099 | 500–650 |

Cắt theo thứ tự hiệu quả nhất:

1. Bỏ RQ5 và các đoạn lặp lại framing AI/advertising ở Chương 1, 2, 6 và 7.
2. Thu gọn phần dashboard/data model ở Chương 4 thành một mô tả kiến trúc và một screenshot đại diện.
3. Thay ba detection figures 19–21 cùng phần diễn giải lặp bằng một figure hai panel mới.
4. Chuyển training curves, PR curves và chi tiết benchmark RF-DETR sang appendix; main text chỉ giữ kết luận so sánh.
5. Rút mạnh phần future work về weak supervision/foundation models vì đó là đề xuất chưa được thực nghiệm trong dissertation.
6. Bỏ các cụm từ lặp như “honest”, “credible”, “trustworthy”, “disclosed rather than hidden”; thay bằng ngôn ngữ trung tính như “leakage-controlled estimate” và để dữ liệu tự chứng minh.

Không nên cắt các thông tin cần cho reproducibility: sample size, split rule, metric definition, audit sampling, equations, confidence interval và limitations.

## 4. Hình ảnh và bảng

Bản DOCX hiện có 31 ảnh. Số lượng này không tự động là sai, nhưng ở đây nhiều ảnh trùng chức năng hoặc chỉ minh họa quy trình; với 12.000 từ, main body nên còn khoảng **15–18 figures**.

### Nên giữ trong main body

- Một figure về frame selection/annotation workflow.
- Một architecture hoặc pipeline figure; gộp Figures 5 và 6 nếu có thể.
- Figure 8 về valuation model, sau khi sửa công thức/đơn vị.
- Một screenshot dashboard duy nhất, ưu tiên per-match view vì thể hiện output và auditability.
- Data distribution/content profile, split protocol và confusion matrix.
- Figure detection mới hai panel thay Figures 19–21.
- Team attribution overlay và team-filter result.
- Sensitivity, sampling bias, data efficiency và occlusion.

### Nên chuyển appendix hoặc bỏ

- Roboflow screenshot, kit reference, 3D kit UI.
- Dashboard overview nếu đã giữ per-match dashboard.
- Raw EDA labels, training curves, PR curves.
- Hai RF-DETR plots: gộp thành một hoặc chuyển appendix.
- Team audit bar chart 169/184: con số đơn giản phù hợp với text/table hơn.
- Confidence-weight chart nếu nội dung đã thể hiện trong sensitivity analysis.

Tránh dùng cả table và figure cho cùng một kết quả. Hiện Table 2/Figure 15, Table 3/Figures 22–23, Table 4/Figure 30 và Table 5/Figure 31 có mức độ lặp đáng kể. Caption nên khoảng 30–60 từ: nói figure đo gì, trên dữ liệu nào và takeaway chính; không kể lại toàn bộ đoạn văn bên cạnh.

Figure detection mới đã được tạo từ checkpoint clip-disjoint trên hai held-out broadcast frames:

`figures/fig_detection_evidence_compact.png`

Caption đề xuất:

> **Qualitative output from the clip-disjoint YOLO checkpoint on two held-out broadcast frames:** (A) nine detections across six brands during close play; (B) examples spanning different viewing angles and confidence levels. Colours denote brand and labels report detector confidence.

Figure này có thể thay trực tiếp Figures 19–21. Panel A có 9 detections; panel B có 4 detections. Broadcast overlays đã được che để giảm thông tin không liên quan.

## 5. Các vấn đề phương pháp và câu chữ cần sửa

### EMV và đơn vị

Backend hiện tính:

`quality_seconds × CPM/1000 × audience × multipliers`

Nếu CPM là giá của một standard 30-second spot như luận văn đang diễn giải, công thức cần tối thiểu chia cho 30:

`quality_seconds × (CPM × audience/1000) / 30 × multipliers`

Notebook pricing cũ còn nhân sponsorship discount 0,30. Với ví dụ 120 quality-seconds, CPM US$22 và audience 40.000:

- Công thức hiện tại: US$105.600.
- Chuẩn hóa theo spot 30 giây, chưa discount: US$3.520.
- Chuẩn hóa 30 giây và discount 30%: US$1.056.

Cần chọn một định nghĩa có nguồn đáng tin cậy, sửa backend, tests, dashboard và luận văn cùng lúc, rồi chạy lại toàn bộ EMV results. Nếu không có benchmark đủ chắc, nên gọi output là **scenario-based EMV proxy**, trình bày nhiều kịch bản CPM/audience/discount thay vì một “giá trị” duy nhất.

### Những claim đang mạnh quá mức

- “The system’s operative accuracy is better than raw mAP suggests” chưa có exposure-level ground truth để chứng minh.
- “A false negative merely under-counts” xem nhẹ hậu quả định giá; under-counting vẫn làm sai sponsor valuation.
- Filter làm raw detection volume tăng khoảng 80% khi bỏ filter, nhưng không thể nói EMV “roughly doubled” nếu chưa tính lại với quality weights.
- Thí nghiệm sampling chỉ trên một đoạn 3 phút: viết “+63% in one controlled segment”, không khái quát thành bias toàn hệ thống.
- Sensitivity cho thấy threshold 0,02 giữ nhiều signal theo chính score hiện tại; nó chưa “strongly justify” threshold nếu thiếu manual exposure timing.
- Claim annotation nhanh hơn 5–10 lần/order of magnitude cần time log; nếu không có, ghi là informal observation hoặc bỏ.
- “All quantitative results are reconstructable” chưa đúng khi nhiều figure lấy số hard-coded và thiếu raw audit/sweep files.

## 6. Đối chiếu source code với luận văn

### Detector backend không thống nhất

- `backend/app/config.py` có cả `detector_backend` và `logo_backend`; detector thực tế dùng `logo_backend`.
- `backend/README.md` hướng dẫn `DETECTOR_BACKEND=rfdetr`, nhưng biến có hiệu lực là `LOGO_BACKEND`.
- Frontend hiển thị cố định “YOLO26 logo detection”, dù runtime có thể là RF-DETR.
- Cấu hình local hiện tại chọn RF-DETR, trong khi dissertation nói deployed YOLO được giữ vì throughput.

Cần quyết định rõ checkpoint nào tạo ra **mọi kết quả dissertation**, lưu một config snapshot cho experiment đó và đổi frontend label thành “Sponsor-logo detection” hoặc lấy tên backend từ API.

### Team-attribution policy không thống nhất

Default code giữ low-evidence “unknown” (`team_keep_unknown=True`), nhưng local runtime configuration đặt false. Hai chính sách có hướng sai số thương mại trái ngược nhau. Dissertation phải ghi đúng giá trị dùng để tạo kết quả, không gọi policy là conservative/under-claim nếu unknown vẫn được giữ.

### Môi trường tái lập

README nói Ultralytics 8.3.40; các environment hiện có 8.4.x. Frontend build thành công, nhưng backend tests chưa chạy được vì các environment chứa model/web dependencies khác nhau và không có `pytest` trong environment phù hợp. Nên cung cấp một lockfile hoặc environment export duy nhất, cài test dependencies và lưu command/output của một clean verification run.

### Provenance của kết quả

`make_figures.py` đọc một phần dữ liệu thật nhưng hard-code các kết quả split, audit, filter, confidence, sensitivity và sampling. Nên thêm ít nhất:

- `team_attribution_audit.csv`
- `team_filter_summary.csv`
- `sensitivity_sweep.csv`
- `sampling_rate_experiment.csv`
- `throughput.csv`

Sau đó sửa script để mọi biểu đồ đọc trực tiếp các file này. Database hiện có thể xác nhận 23 analyses và, với chín full-match records, 25.153 raw detections gồm 13.992 kept và 11.161 dropped (44,37%).

### Bảo mật

File `.env` local có một token truy cập trông như còn hoạt động. Không đưa token vào dissertation, screenshot hoặc repository; nên rotate token và dùng secret management/environment variable riêng. Giá trị token không được chép vào bản review này.

### References cần hiệu chỉnh

- Reference `ExposureEngine` đã xác minh được: M. Houshmand Sarkhoosh, F. Øye, H. N. Sørlie, N. H. Vu, D. Johansen, C. Midoglu, T. Kupka và P. Halvorsen, *ExposureEngine: Oriented Logo Detection and Sponsor Visibility Analytics in Sports Broadcasts*, arXiv:2510.04739 (2025), https://arxiv.org/abs/2510.04739.
- Call for papers *AI and the Future of Advertising Creativity* không nên ghi đơn giản là một nguồn năm 2025: trang hiện tại mang copyright 2026 và deadline manuscript là 15/10/2027. Nếu chỉ dùng để chứng minh đây là chủ đề đương thời, cần ghi đúng loại tài liệu và ngày truy cập: https://think.taylorandfrancis.com/special_issues/ai-and-the-future-of-advertising-creativity/.
- Chưa xác minh được đúng tài liệu Nielsen có tiêu đề *Measuring the value of sponsorship (2019)* như bibliography hiện tại. Có thể thay bằng report có thật và chỉ dùng cho những claim report hỗ trợ: https://www.nielsen.com/report/sponsorship-media-value-benchmarking-report/. Không dùng một industry webpage để khẳng định công thức toán học cụ thể nếu trang không công bố công thức đó.

## 7. Kiểm nghiệm đã thực hiện

- Frontend `logo-analytics`: production build thành công, gồm TypeScript/lint/static generation.
- Detector: checkpoint `logo_yolo26m_clipsplit/weights/best.pt` chạy thành công bằng GPU trên held-out frames.
- Output kiểm tra: panel A phát hiện 9 logos; panel B phát hiện 4 logos.
- DOCX v12: kiểm tra cấu trúc, media và contact sheet; 31 inline images, không có anchored/floating image gây rủi ro layout.
- Chưa thể render đầy đủ từng trang DOCX trong môi trường hiện tại vì LibreOffice không có và Word COM export bị treo; do đó cần mở bản DOCX cuối trong Word và kiểm tra thủ công page breaks, caption splits, TOC và numbering trước khi nộp.

## 8. Thứ tự sửa khuyến nghị

1. Chốt định nghĩa EMV và sửa đồng bộ code/tests/text; chạy lại monetary outputs.
2. Chốt bốn RQ và mapping RQ → method → result → discussion.
3. Khóa experiment configuration và detector checkpoint dùng trong dissertation.
4. Xuất raw audit/sensitivity/sampling/throughput records; loại hard-coded figure values.
5. Giảm còn 15–18 figures và đưa Chapters 1–7 về 11.700–11.900 từ.
6. Chạy backend tests trong một environment sạch; ghi hardware, package versions, runtime và chi phí.
7. Sửa references mới/chưa xác minh, build DOCX cuối và kiểm tra bằng Word.
