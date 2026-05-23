# Motion Blur — Toàn Cảnh Kỹ Thuật & Nghiên Cứu

> Tổng hợp toàn bộ kỹ thuật, bài báo, hệ thống thương mại, và dataset liên quan đến xử lý motion blur — với trọng tâm ứng dụng vào **phân tích video thể thao** (logo/jersey detection, player tracking, logo exposure measurement).
>
> *Nghiên cứu: tháng 5/2026.*

---

## Mục lục

1. [Bức tranh tổng quan — Nguyên nhân & phân loại blur](#1-bức-tranh-tổng-quan)
2. [Classical / Traditional methods](#2-classical--traditional-methods)
3. [Deep Learning — Single Image Deblurring](#3-deep-learning--single-image-deblurring)
4. [Video Deblurring (temporal methods)](#4-video-deblurring)
5. [Frame Interpolation](#5-frame-interpolation)
6. [Optical Flow (nền tảng)](#6-optical-flow)
7. [Lucky Imaging / Temporal Frame Selection](#7-lucky-imaging--temporal-frame-selection)
8. [Papers Sports-Specific](#8-papers-sports-specific)
9. [Hệ thống thương mại](#9-hệ-thống-thương-mại)
10. [Logo Detection trong sports broadcast](#10-logo-detection-trong-sports-broadcast)
11. [Benchmark Datasets](#11-benchmark-datasets)
12. [Performance Comparison Table](#12-performance-comparison-table)
13. [Synthesis — Áp dụng vào Bradford Bulls / Sports Video](#13-synthesis--áp-dụng-vào-bradford-bulls--sports-video)

---

## 1. Bức tranh tổng quan

### Nguồn gốc của motion blur trong sports video

Motion blur trong video thể thao có **hai nguồn riêng biệt**, cần xử lý khác nhau:

| Nguồn | Mô tả | Đặc điểm blur | Phương pháp phù hợp |
|---|---|---|---|
| **Camera pan/tilt** | Camera quay theo bóng/cầu thủ | Global — toàn frame | Classical methods, Single-image DL (Wiener, NAFNet, FFTformer) |
| **Player motion** | Cầu thủ di chuyển nhanh | Local — chỉ trong bbox player | Video DL (BSSTNet, STFAN), local deblurring, frame selection |

Tại sao video *nhìn có vẻ rõ* nhưng frame đơn lẻ lại blur?
- Mắt người "integrate" thông tin theo thời gian — nhìn video liên tục não tự dựng lại chuyển động mượt.
- Một frame đơn lẻ được chụp trong thời gian = 1/fps (ví dụ 1/25s ở 25fps). Trong khoảng thời gian đó, cầu thủ di chuyển → blur trail. Thông tin về vị trí thật của logo/jersey **tồn tại nhưng bị phân tán** ra nhiều frame xung quanh.

### Phân loại kỹ thuật xử lý

```
Motion Blur Handling
├── Frame Selection (Tier 1)
│   └── Lucky Imaging — chọn frame sắc nhất
├── Single Image Deblurring (Tier 2)
│   ├── Classical: Wiener, Richardson-Lucy, Blind Deconvolution
│   └── DL: NAFNet, Restormer, FFTformer, DeblurGAN-v2, ...
├── Video Deblurring (Tier 3)
│   ├── CNN-based: DVD, STFAN, EDVR, BasicVSR++
│   └── Transformer-based: VRT, RVRT, Shift-Net, BSSTNet, VD-Diff
└── Frame Interpolation (Tier 4)
    └── RIFE, DAIN, FILM — tăng frame rate giảm apparent blur
```

---

## 2. Classical / Traditional Methods

### Wiener Filter

- **Paper gốc**: Wiener (1949) — statistical signal theory; image deblurring via frequency domain.
- **Ý tưởng**: Minimize MSE giữa ảnh ước lượng và ảnh thật. Tính trong frequency domain:
  ```
  Ĥ(u,v) = H*(u,v) / (|H(u,v)|² + NSR)
  ```
  Trong đó NSR = noise-to-signal power ratio. Cần biết PSF (Point Spread Function).
- **Ưu điểm**: Cực nhanh (FFT-based), closed-form, không cần huấn luyện.
- **Nhược điểm**: Yêu cầu biết PSF trước (non-blind); giả định blur spatially invariant (sai cho player motion blur); ring/Gibbs artifacts; khuếch đại noise ở tần số thấp của blur kernel.
- **PSNR điển hình**: 25–30 dB (tùy chất lượng PSF estimate).
- **Relevance**: Chỉ dùng được khi biết motion của camera (IMU data, optical flow estimate). Fallback hữu ích khi không có GPU/model. Đang dùng trong `deblur_single.py` làm Wiener fallback.
- **Code**: `scipy.signal.wiener`, `skimage.restoration.wiener`

### Richardson-Lucy Deconvolution

- **Paper**: Richardson (1972, JOSA) + Lucy (1974, Astronomical Journal).
- **Ý tưởng**: Iterative EM algorithm, giả định Poisson noise:
  ```
  f̂ ← f̂ × (g / (h ⊗ f̂)) ⊗ h̃
  ```
- **Ưu điểm**: Xử lý Poisson noise tốt (low-light/astronomical imaging); đảm bảo non-negativity.
- **Nhược điểm**: Chậm (50–1000+ iterations); nhạy với noise ở iteration cao; cần PSF; "checkerboard" artifacts.
- **Relevance**: Hạn chế cho sports video. Có thể hữu ích cho indoor sports ánh sáng yếu (boxing, ice hockey).
- **Code**: `skimage.restoration.richardson_lucy`

### Blind Deconvolution — Dark Channel Prior

- **Paper**: Pan et al., "Deblurring Images via Dark Channel Prior" — TPAMI 2018 (CVPR 2016).
- **Ý tưởng**: Ảnh sắc nét có dark channel (minimum of R,G,B trong local patch) rất sparse; ảnh blur làm mất sparse này. Dùng sự khác biệt này để estimate blur kernel trong MAP framework.
- **Ưu điểm**: Blind deblurring (không cần PSF); hoạt động tốt cho nhiều loại scene.
- **Nhược điểm**: Rất chậm (minutes per frame); thất bại khi dark channel prior bị vi phạm (snow, ice, áo trắng, cỏ xanh sáng) — chính xác là môi trường sports!
- **PSNR**: 28–30 dB trên synthetic benchmarks.
- **Relevance**: Ít áp dụng cho sports vì bright green grass và white jerseys vi phạm dark channel assumption.

### L0 Gradient Minimization

- **Paper**: Xu, Zheng, Jia — "Unnatural L0 Sparse Representation for Natural Image Deblurring", CVPR 2013.
- **Ý tưởng**: Ảnh sắc nét có gradient rất sparse (L0 — đếm số pixel có gradient ≠ 0). Minimize L0 gradient norm + data fidelity.
- **Ưu điểm**: Tạo kết quả sharp rõ ràng, không cần PSF.
- **Nhược điểm**: Rất chậm; chỉ xử lý global blur (camera shake); player motion blur là non-uniform → phương pháp này không áp dụng được.
- **PSNR**: 27–29 dB.

### Total Variation (TV) Deblurring — ROF Model

- **Paper**: Rudin, Osher, Fatemi — "Nonlinear total variation based noise removal algorithms", Physica D, 1992.
- **Ý tưởng**: Minimize tổng TV (sum of gradient magnitudes) subject to data fidelity: `min_u TV(u) + λ/2 ||u - f||²`.
- **Ưu điểm**: Edge-preserving (không blur cạnh như Wiener); convex problem → global optimum.
- **Nhược điểm**: "Staircase effect" tạo vùng flat nhân tạo; chỉ spatially uniform blur; chậm; khó tune λ.
- **Relevance**: Đôi khi dùng làm post-processing sau optical flow alignment. Staircase effect rõ trên cỏ phẳng.

---

## 3. Deep Learning — Single Image Deblurring

### Tiến trình SOTA (2017–2024)

```
2017: DeepDeblur (29.08 dB) → DeblurGAN (28.70 dB)
2018: SRN-Deblur (30.26 dB) → DeblurGAN
2019: DMPHN (32.20 dB) → DeblurGAN-v2 (29.55 dB)
2021: MPRNet (32.66 dB) → MIMO-UNet+ (32.45 dB)
2022: NAFNet (33.69 dB) → Restormer (32.92 dB) → Uformer (33.06 dB) → FFTformer (34.21 dB)
2023: FFTformer (34.21 dB) → Stripformer
2024: AdaRevD (34.60 dB) → ID-Blau augmentation
```

### DeepDeblur / Deep Multi-scale CNN

- **Paper**: Nah, Kim, Lee — "Deep Multi-scale Convolutional Neural Network for Dynamic Scene Deblurring", CVPR 2017.
- **GitHub**: https://github.com/SeungjunNah/DeepDeblur-PyTorch
- **Kiến trúc**: Multi-scale coarse-to-fine CNN; 3 scales; residual learning tại mỗi scale; không estimate kernel.
- **PSNR GoPro**: 29.08 dB / 0.914 SSIM.
- **Đóng góp**: Phương pháp DL end-to-end đầu tiên; giới thiệu **GoPro dataset** như benchmark chuẩn.
- **Relevance**: Foundational — kiến trúc multi-scale encoder-decoder được dùng trong tất cả methods sau.

### DeblurGAN

- **Paper**: Kupyn et al. — "DeblurGAN: Blind Motion Deblurring Using Conditional Adversarial Networks", CVPR 2018.
- **GitHub**: https://github.com/KupynOrest/DeblurGAN
- **Kiến trúc**: ResNet generator (9 ResBlocks) + PatchGAN discriminator; Wasserstein GAN + perceptual loss.
- **PSNR GoPro**: 28.70 dB / 0.858 SSIM.
- **Đặc điểm**: GAN tạo kết quả perceptually sharp ngay cả khi PSNR không cao nhất — quan trọng cho jersey/logo readability hơn là pixel accuracy.
- **Nhược điểm**: GAN instability; hallucination artifacts; có thể tạo texture không tồn tại trong original.

### DeblurGAN-v2

- **Paper**: Kupyn et al. — "DeblurGAN-v2: Deblurring (Orders-of-Magnitude) Faster and Better", ICCV 2019.
- **GitHub**: https://github.com/VITA-Group/DeblurGANv2
- **Kiến trúc**: FPN (Feature Pyramid Network) generator; relativistic conditional GAN; hỗ trợ nhiều backbone (MobileNetV2, InceptionResNetV2, MobileNet).
- **PSNR GoPro**: 29.55 dB / 0.934 SSIM (Inception); MobileNet version: ~28.37 dB nhưng **near real-time**.
- **Đặc điểm**: **10–100x nhanh hơn** DeblurGAN v1; FPN phù hợp multi-scale logo + jersey analysis.
- **Relevance**: **CAO** — MobileNet version có thể deploy trong live broadcast pipeline; FPN architecture lý tưởng cho sports analysis.

### SRN-Deblur (Scale-Recurrent Network)

- **Paper**: Tao, Gao, Shen, Wang, Jia — "Scale-recurrent Network for Deep Image Deblurring", CVPR 2018.
- **GitHub**: https://github.com/jiangsutx/SRN-Deblur
- **Kiến trúc**: Shared encoder-decoder + ConvLSTM kết nối giữa các scale; một mạng duy nhất cho 3 scales.
- **PSNR GoPro**: 30.26 dB / 0.934 SSIM — SOTA tại CVPR 2018.
- **Ưu điểm so với DeepDeblur**: Parameter-efficient hơn (dùng shared weights); ConvLSTM mang thông tin từ coarse → fine.
- **Relevance**: Efficient — xử lý player gần (large blur) và xa (fine detail) trong cùng pass.

### DMPHN (Deep Multi-Patch Hierarchical Network)

- **Paper**: Zhang, Dai, Li, Koniusz — CVPR 2019.
- **GitHub**: https://github.com/HongguangZhang/DMPHN-cvpr19-master
- **Kiến trúc**: Chia image thành patches nhiều level; process hierarchically; residual từ fine → coarse.
- **PSNR GoPro**: 32.20 dB / 0.976 SSIM.
- **Đặc điểm**: Patch-based scalable lên 4K frames; phù hợp broadcast video high-res.

### MPRNet (Multi-Stage Progressive Restoration Network)

- **Paper**: Zamir et al. — "Multi-Stage Progressive Image Restoration", CVPR 2021.
- **GitHub**: https://github.com/swz30/MPRNet
- **Kiến trúc**: 3 stages cascade U-Net; Supervised Attention Module (SAM) tại mỗi stage; Channel Attention.
- **PSNR**: GoPro 32.66 dB / 0.959 SSIM; **HIDE 30.96 dB / 0.939 SSIM**; RealBlur-J 28.70 dB.
- **Đặc điểm**: SAM dùng loss của stage trước để reweight features; đặc biệt mạnh trên HIDE (human-centric).
- **Relevance**: Multi-stage robust với diverse blur types (camera shake + player motion); supervised attention focus vào jersey/logo regions.

### MIMO-UNet (Multi-Input Multi-Output U-Net)

- **Paper**: Cho et al. — "Rethinking Coarse-to-Fine Approach in Single Image Deblurring", ICCV 2021.
- **GitHub**: https://github.com/chosj95/MIMO-UNet
- **Kiến trúc**: Single U-Net nhận multi-scale input VÀ output multi-scale results; Asymmetric Feature Fusion (AFF).
- **PSNR GoPro**: 32.45 dB / 0.957 SSIM (MIMO-UNet+).
- **Đặc điểm**: Capability của cascaded multi-stage trong single-pass → nhanh hơn nhiều.
- **Relevance**: Single-pass efficiency quan trọng cho live broadcast.

### NAFNet (Nonlinear Activation Free Network) ⭐ *Đang dùng trong Tier 2*

- **Paper**: Chen, Chu, Zhang, Sun — "Simple Baselines for Image Restoration", ECCV 2022.
- **GitHub**: https://github.com/megvii-research/NAFNet
- **Kiến trúc**: U-Net backbone; NAFBlock thay thế residual blocks; **SimpleGate** (element-wise multiplication) thay sigmoid/gating; Simplified Channel Attention; LayerNorm.
- **PSNR GoPro**: **33.69 dB** — SOTA tại ECCV 2022.
- **Phát hiện chính**: Loại bỏ TOÀN BỘ nonlinear activations (ReLU, GELU, Sigmoid, Softmax) và thay bằng multiplicative gates → đạt SOTA với **8.4% FLOPs** của previous SOTA. Simplicity = extreme efficiency.
- **Nhược điểm**: Single image only; không dùng temporal info; có thể không generalize tốt cho highly non-uniform blur.
- **Relevance**: **RẤT CAO** — NAFNet phù hợp nhất cho sports video vì FLOPs thấp nhất trong nhóm SOTA. Weights (GoPro-width64, 67MB) sẵn sàng tải về. Đây là model được implement trong `tier2/single-image-deblur`.

### Restormer (Efficient Transformer for Image Restoration)

- **Paper**: Zamir et al. — "Restormer: Efficient Transformer for High-Resolution Image Restoration", CVPR 2022 (Oral).
- **GitHub**: https://github.com/swz30/Restormer
- **Kiến trúc**: Multi-Dconv Head Transposed Attention (MDTA) — attention across CHANNELS (không phải spatial); Gated-Dconv FFN; encoder-decoder transformer multi-scale.
- **Đột phá**: Transposed attention giảm complexity từ O(H²W²) → O(C²HW) → scalable lên high-res images.
- **PSNR**: GoPro 32.92 dB / 0.961; **HIDE 31.22 dB / 0.942**; RealBlur-J 28.96 dB; RealBlur-R 35.94 dB.
- **Nhược điểm**: Nặng hơn NAFNet; cần GPU memory đáng kể; không real-time.
- **Relevance**: Strong general deblurring model; đặc biệt hiệu quả với defocus deblurring (players ở edge của depth of field).

### Uformer (U-shaped Transformer)

- **Paper**: Wang et al. — "Uformer: A General U-Shaped Transformer for Image Restoration", CVPR 2022.
- **GitHub**: https://github.com/ZhendongWang6/Uformer
- **Kiến trúc**: 4-level U-Net encoder-decoder với LeWin Transformer blocks (window attention 8×8 + depth-wise conv); learnable modulator.
- **PSNR**: GoPro 33.06 dB / 0.967; **RealBlur-J 29.06 dB / 0.884** (đứng đầu RealBlur); RealBlur-R 36.22 dB / 0.957.
- **Relevance**: Strong RealBlur performance quan trọng vì broadcast video là real-world blur, không phải synthetic. Window attention phù hợp batch processing sports frames.

### MAXIM (Multi-Axis MLP) — Google Research

- **Paper**: Tu et al. — "MAXIM: Multi-Axis MLP for Image Processing", CVPR 2022 (Oral).
- **GitHub**: https://github.com/google-research/maxim
- **Kiến trúc**: U-Net backbone; Multi-Axis Gated MLP blocks (mixing H và W axes riêng biệt); Cross-Gating Block cho skip connections.
- **PSNR GoPro**: 32.86 dB.
- **Đặc biệt**: Multi-task — xử lý denoising + deblurring + deraining + dehazing với một kiến trúc.
- **Relevance**: Multi-task capability quan trọng cho indoor sports (noise + blur cùng lúc).

### FFTformer

- **Paper**: Kong et al. — "Efficient Frequency Domain-based Transformer for High-Quality Image Deblurring", CVPR 2023.
- **GitHub**: https://github.com/kkkls/FFTformer
- **Kiến trúc**: FSAS (Frequency-domain Self-Attention) dùng FFT → element-wise product thay matrix multiplication; DFFN (Discriminative Frequency-domain FFN) với JPEG-inspired frequency gating.
- **Đột phá**: FFT biến attention từ O(N²) → O(N log N); convolution theorem: correlation trong spatial domain = element-wise product trong frequency domain.
- **PSNR GoPro**: **34.21 dB / 0.969 SSIM** — SOTA tại CVPR 2023. HIDE: 31.62 / 0.945.
- **Relevance**: **RẤT CAO** — frequency-domain approach tự nhiên cho camera motion blur (global/semi-global); mạnh trên HIDE (human-aware, gần giống sports players).

### Stripformer

- **Paper**: Tsai et al. — "Stripformer: Strip Transformer for Fast Image Deblurring", ECCV 2022 (Oral).
- **GitHub**: https://github.com/pp00704831/Stripformer-ECCV-2022-
- **Kiến trúc**: Intra-strip tokens (trong row/column) + inter-strip tokens (giữa rows/columns); mô hình blur theo chiều horizontal và vertical riêng biệt.
- **Đặc điểm**: Strip attention tự nhiên aligned với motion blur directions — **horizontal blur từ camera pan, vertical blur từ camera tilt** — chính xác là dạng blur phổ biến nhất trong sports broadcast!
- **Relevance**: **CAO** — strip attention là ideal match cho sports video: camera pan theo action chủ yếu tạo horizontal blur.

### AdaRevD — CVPR 2024 SOTA

- **Paper**: Mao et al. — "AdaRevD: Adaptive Patch Exiting Reversible Decoder", CVPR 2024.
- **Kiến trúc**: Reversible decoder (có thể recompute activations → tiết kiệm GPU memory); Adaptive patch exiting — patches "easy" exit sớm, patches "hard" dùng full depth.
- **PSNR GoPro**: **34.60 dB** — SOTA tại CVPR 2024.
- **Relevance**: Adaptive exit đặc biệt phù hợp sports video — background pitch là "easy" (ít blur hơn), jersey/logo region là "hard" (cần full computation). Hiệu quả cả về quality lẫn computation.

### ID-Blau (Diffusion-based Augmentation)

- **Paper**: Wu, Tsai et al. — "ID-Blau: Image Deblurring by Implicit Diffusion-based reBLurring AUgmentation", CVPR 2024.
- **GitHub**: https://github.com/plusgood-steven/ID-Blau
- **Ý tưởng**: Dùng diffusion model KHÔNG phải để deblur, mà để **data augmentation** — generate synthetic blurry images với continuous blur condition maps (orientation + magnitude fields).
- **Kết quả**: Cải thiện existing models (MPRNet, Restormer...) thêm 0.2–0.5 dB PSNR khi dùng làm augmentation.
- **Relevance**: **CAO** — có thể generate sports-specific synthetic blur data (player motion direction blur) để train models tốt hơn trên sports-specific test cases mà không cần ground truth thật.

### KPN (Kernel Prediction Network)

- **Paper**: Mildenhall, Barron et al. — "Burst Denoising with Kernel Prediction Networks", CVPR 2018.
- **Ý tưởng**: Với mỗi output pixel, predict weighted average kernel trên N input frames; network học optimal per-pixel blending weights mà không cần explicit motion estimation.
- **Đặc điểm**: Implicit alignment via learned per-pixel kernels; đây là nguyên lý đằng sau **Google Pixel Night Sight**.
- **Relevance**: Burst mode cameras phổ biến trong sports photography; KPN-style approach dùng trong smartphone burst processing.

---

## 4. Video Deblurring

### DVD — Deep Video Deblurring (Baseline)

- **Paper**: Su, Delbracio, Wang, Sapiro, Heidrich, Wang — CVPR 2017.
- **Kiến trúc**: Concatenate 5 consecutive blurry frames theo channel dimension; encoder-decoder CNN cho sharp middle frame; pre-alignment via homography.
- **PSNR**: ~30–31 dB trên DVD dataset.
- **Nhược điểm**: Fixed 5-frame window; homography chỉ xử lý global camera motion — thất bại với player motion trong sports.
- **Relevance**: Foundational baseline; không đủ tốt cho sports vì player motion không handle được bằng homography.

### STFAN (Spatio-Temporal Filter Adaptive Network)

- **Paper**: Zhou et al. — "Spatio-Temporal Filter Adaptive Network for Video Deblurring", ICCV 2019.
- **GitHub**: https://github.com/sczhou/STFAN
- **Kiến trúc**: Recurrent; FAC (Filter Adaptive Convolutional) layer dự đoán spatially-adaptive kernels cho mỗi pixel; thực hiện cả alignment VÀ deblurring đồng thời.
- **Đột phá**: Một FAC layer thực hiện cả temporal alignment + blur removal mà **không cần explicit optical flow**.
- **Relevance**: **CAO** — unified alignment+deblurring không cần optical flow là robust với irregular motions của sports players; flow thường fail trên blurry frames.

### EDVR (Enhanced Deformable Video Restoration)

- **Paper**: Wang, Chan, Yu, Dong, Loy — "EDVR: Video Restoration with Enhanced Deformable Convolutional Networks", CVPR Workshops 2019 (NTIRE challenge winner).
- **GitHub**: https://github.com/xinntao/EDVR (merged into BasicSR)
- **Kiến trúc**: PCD module (Pyramid Cascading Deformable) align neighboring frames via deformable convolutions; TSA module (Temporal and Spatial Attention) fuse aligned features.
- **Đột phá**: Deformable convolutions cho phép per-pixel dynamic offsets → xử lý non-rigid motions tốt hơn homography/flow warping.
- **Kết quả**: Win ALL 4 tracks tại NTIRE19 challenge.
- **Relevance**: **RẤT CAO** — deformable convolutions tự nhiên handle non-rigid player motions, jersey deformation, partial occlusion; widely used làm backbone cho sports video analysis.

### CDVD-TSP (Cascaded Deep Video Deblurring với Temporal Sharpness Prior)

- **Paper**: Pan, Bai, Tang — CVPR 2020.
- **GitHub**: https://github.com/csbhr/CDVD-TSP
- **Kiến trúc**: 2-stage cascade — (1) estimate optical flow từ partially deblurred frames; (2) warp previous deblurred frame → temporal sharpness prior → guide current frame deblurring.
- **Đặc điểm**: Dùng frame đã deblurred để estimate better optical flow (sharp → better flow hơn blurry → flow).
- **PSNR GoPro video**: ~31.97 dB / 0.956 SSIM — SOTA tại CVPR 2020.
- **Relevance**: Temporal sharpness prior quan trọng cho sports — sharp frames cung cấp player position reference tốt hơn.

### VRT (Video Restoration Transformer)

- **Paper**: Liang et al. — "VRT: A Video Restoration Transformer", IEEE TIP 2024 (arXiv 2022).
- **GitHub**: https://github.com/JingyunLiang/VRT
- **Kiến trúc**: TMSA (Temporal Mutual Self-Attention) — attention joint trên 2-frame clips cho simultaneous motion estimation, alignment, và fusion; parallel warping cho cross-clip info.
- **PSNR**: Video deblurring DVD: 34.81 dB; **GoPro video: 38.83 dB** — vượt xa previous SOTA trên 14 benchmarks.
- **Nhược điểm**: Rất chậm (10+ seconds/frame); không phù hợp real-time.
- **Relevance**: Best cho post-production highlight processing; quá chậm cho live broadcast nhưng xuất sắc cho archival footage enhancement.

### RVRT (Recurrent Video Restoration Transformer)

- **Paper**: Liang et al. — "Recurrent Video Restoration Transformer with Guided Deformable Attention", NeurIPS 2022.
- **GitHub**: https://github.com/JingyunLiang/RVRT
- **Kiến trúc**: Recurrent clip processing; guided deformable attention cho inter-clip alignment; bidirectional recurrent.
- **Đặc điểm**: Cân bằng tốt giữa VRT (parallel = large memory) và sequential methods; guided deformable attention chính xác hơn standard deformable conv.
- **Relevance**: Candidate thực tế hơn VRT cho sports footage processing; bidirectional processing tốt cho offline tactical analysis.

### BasicVSR++

- **Paper**: Chan et al. — "BasicVSR++: Improving Video Super-Resolution with Enhanced Propagation and Alignment", CVPR 2022.
- **GitHub**: https://github.com/ckkelvinchan/BasicVSR_PlusPlus
- **Kiến trúc**: Bidirectional recurrent network; second-order grid propagation (dùng cả frame trước VÀ "grandparent" frame); FlowNet-based flow + deformable alignment.
- **Đặc điểm**: Win 3 championships tại NTIRE 2021 video restoration challenge.
- **Relevance**: Flow-guided alignment handle camera movements trong sports broadcasts; NTIRE challenge bao gồm sports-like sequences.

### Shift-Net

- **Paper**: Li et al. — "A Simple Baseline for Video Restoration with Grouped Spatial-temporal Shift", CVPR 2023.
- **GitHub**: https://github.com/dasongli1/Shift-Net
- **Kiến trúc**: Thay optical flow/deformable conv bằng simple spatial-temporal SHIFT operations — shift feature maps theo fixed offsets across time và space.
- **Đột phá**: Grouped shift = implicit inter-frame feature fusion không cần alignment; outperforms VRT/RVRT với <25% compute.
- **PSNR GoPro video**: >38 dB range với fraction of compute.
- **Relevance**: **CAO** — lightweight đủ cho near-real-time processing; simpler deployment (không có optical flow dependencies); competitive PSNR cho sports footage post-processing.

### BSSTNet (Blur-aware Spatio-temporal Sparse Transformer) ⭐ *Best cho sports video*

- **Paper**: Zhang, Xie, Yao — "Blur-aware Spatio-temporal Sparse Transformer for Video Deblurring", CVPR 2024.
- **GitHub**: https://github.com/huicongzhang/BSSTNet
- **Kiến trúc**: Blur map → sparse attention — chỉ attend vào sharp regions từ neighboring frames; blur-guided bidirectional propagation tránh error propagation từ blurry frames.
- **Đột phá**: Blur maps là masks focus attention vào sharp pixels trong neighboring frames (tránh propagate errors từ blurry pixels); sparse attention cho phép temporal window dài hơn dense attention.
- **Relevance**: **RẤT QUAN TRỌNG cho sports** — trong sports sequences, một số frames sharp (player tạm thời đứng yên) và một số blurry; blur-aware attention correctly leverage sharp frames làm reference. Đây là version learned của Lucky Imaging principle.

### VD-Diff (Wavelet-Aware Dynamic Transformer + Diffusion)

- **Paper**: Chen et al. — "Rethinking Video Deblurring with Wavelet-Aware Dynamic Transformer and Diffusion Model", ECCV 2024.
- **GitHub**: https://github.com/Chen-Rao/VD-Diff
- **Kiến trúc**: WADT (Wavelet-Aware Dynamic Transformer) bảo tồn low-freq; diffusion model generate high-freq priors trong compact latent space.
- **PSNR**: Outperforms SOTA trên GoPro, DVD, BSD, real-world video — **best performing video deblurring method tính đến ECCV 2024**.
- **Relevance**: Excellent cho recovering fine jersey texture, logo details, sharp edges trong sports broadcast; diffusion's generative power phục hồi details mà pure regression losses bỏ qua.

---

## 5. Frame Interpolation

Frame interpolation (tăng frame rate) giảm apparent motion blur vì exposure time ngắn hơn tại frame rate cao hơn.

### RIFE (Real-Time Intermediate Flow Estimation) ⭐ *Real-time*

- **Paper**: Huang et al. — "Real-Time Intermediate Flow Estimation for Video Frame Interpolation", ECCV 2022.
- **GitHub**: https://github.com/hzwer/ECCV2022-RIFE
- **Kiến trúc**: IFNet estimate intermediate optical flow directly từ image pairs (không cần bi-directional flows); FusionNet cho final synthesis; **~35ms/frame tại 720p** (2080Ti).
- **Đặc điểm**: Arbitrary-timestep interpolation; **30+ FPS** tại 720p → real-time capable.
- **Relevance**: **CAO** — RIFE tăng apparent frame rate từ 25/30fps → 60/120fps; giảm apparent motion blur; suitable cho live broadcast.

### DAIN (Depth-Aware Video Frame Interpolation)

- **Paper**: Bao et al. — "Depth-Aware Video Frame Interpolation", CVPR 2019.
- **GitHub**: https://github.com/baowenbo/DAIN
- **Kiến trúc**: PWC-Net optical flow + MonoDepth monocular depth; depth-aware flow projection.
- **Đặc điểm**: Depth awareness giúp xử lý player/crowd occlusion. Nhưng monocular depth unreliable trong sports arenas (flat pitch, white jerseys).
- **Nhược điểm**: Chậm hơn RIFE; depth network có thể fail trong sports.

### FILM (Frame Interpolation for Large Motion) — Google Research

- **Paper**: Reda et al. — "FILM: Frame Interpolation for Large Motion", ECCV 2022.
- **GitHub**: https://github.com/google-research/frame-interpolation
- **Kiến trúc**: Scale-agnostic feature extractor (shared weights across scales); multi-scale optical flow pyramid; Gram Matrix loss để preserve high-frequency details.
- **Đặc điểm**: Xử lý **LARGE interframe motion** (player sprinting, ball trajectory) mà các methods khác fail.
- **Relevance**: **CAO** — use case "near-duplicate photos" (burst photography) map trực tiếp vào sports photography; creating super slow-motion replays từ standard broadcast footage.

### CAIN (Channel Attention Is All You Need)

- **Paper**: Choi et al. — AAAI 2020.
- **GitHub**: https://github.com/myungsub/CAIN
- **Ý tưởng**: Thay optical flow hoàn toàn bằng PixelShuffle + channel attention; không compute flow.
- **Relevance**: Flow-free interpolation robust hơn khi player di chuyển nhanh (optical flow fail trên blurry frames).

### IFRNet

- **Paper**: Kong et al. — "IFRNet: Intermediate Feature Refine Network for Efficient Frame Interpolation", CVPR 2022.
- **GitHub**: https://github.com/ltkong218/IFRNet
- **Ý tưởng**: Jointly refine intermediate optical flow VÀ intermediate feature — feature compensates cho context details mà flow bỏ qua. Task-oriented flow distillation từ RAFT teacher.
- **Relevance**: Efficient interpolation cho broadcast; distillation từ RAFT cho good motion understanding.

---

## 6. Optical Flow

Optical flow là nền tảng của hầu hết video deblurring và frame interpolation methods.

### RAFT (Recurrent All-Pairs Field Transforms) ⭐ *Đang dùng trong Tier 3*

- **Paper**: Teed, Deng — "RAFT: Recurrent All-Pairs Field Transforms for Optical Flow", ECCV 2020 (Best Paper Award).
- **GitHub**: https://github.com/princeton-vl/RAFT, có sẵn trong `torchvision >= 0.13`.
- **Kiến trúc**: All-pairs 4D correlation volume (mọi pixel frame1 vs mọi pixel frame2); GRU-based iterative update operator (32 iterations); convex upsampling.
- **PSNR**: 5.10% F1-all trên KITTI (16% better than prior SOTA); 2.855 EPE trên Sintel final.
- **Nhược điểm**: Chậm (32 iterations); 4D correlation volume memory-intensive cho high-res.
- **Relevance**: **Standard backbone** cho tất cả video restoration work sau này; used trong EDVR, BasicVSR++, CDVD-TSP; provides accurate motion estimation trong challenging sports scenes.

### FlowFormer

- **Paper**: Huang et al. — "FlowFormer: A Transformer Architecture for Optical Flow", ECCV 2022.
- **GitHub**: https://github.com/drinkingcoder/FlowFormer-Official
- **Kiến trúc**: Cost volume tokenization + AGT encoder (alternates spatial/channel attention) + recurrent transformer decoder.
- **PSNR**: Sintel clean 1.144 AEPE (17.6% improvement over RAFT); #1 trên Sintel benchmark.
- **Relevance**: Better flow quality cho complex player motions; hữu ích trong offline sports analysis.

### PWC-Net

- **Paper**: Sun, Yang, Liu, Kautz — "PWC-Net: CNNs for Optical Flow", CVPR 2018.
- **GitHub**: https://github.com/NVlabs/PWC-Net
- **Ý tưởng**: Feature pyramid + warping + cost volume; coarse-to-fine flow estimation; 35 FPS.
- **Relevance**: Standard backbone trong EDVR, DAIN, CDVD-TSP; balance accuracy và speed.

### SpyNet

- **Paper**: Ranjan, Black — "Optical Flow Estimation Using a Spatial Pyramid Network", CVPR 2017.
- **Đặc điểm**: Cực lightweight (1.2M params); dùng trong BasicVSR, CAIN cho efficiency.
- **Nhược điểm**: Ít chính xác hơn PWC-Net/RAFT; fail trên large motions.

---

## 7. Lucky Imaging / Temporal Frame Selection

### Nguồn gốc Thiên văn học

- **Tên gọi**: "Lucky Imaging" — từ thiên văn học (Fried 1978; Tubbs 2003; Law et al. 2006).
- **Ý tưởng gốc**: Ground-based telescopes bị blur bởi atmospheric turbulence. Chụp hàng nghìn short-exposure frames; chọn top 1–10% sharp nhất; align và stack lại → resolution gần diffraction-limited.
- **Transfer sang sports video**: Sports video có sharp frames xen kẽ blurry frames (player tạm thời đứng yên, camera pan tạm dừng). Principle giống hệt: **select sharpest frames làm reference/keyframes**.

### Sharpness Metrics cho Frame Selection

| Metric | Công thức | Đặc điểm | Độ nhanh |
|---|---|---|---|
| **Laplacian Variance** | `var(Laplacian(I))` | Reliable, widely used | Rất nhanh |
| **Tenengrad** | `sum(Sobel_x² + Sobel_y²)` | Tốt nhất cho natural images | Nhanh |
| **FFT High-freq ratio** | `HF_energy / total_energy` | Bổ sung Tenengrad | Trung bình |
| **Brenner focus** | `sum((I(x+2) - I(x))²)` | Simple, fast | Rất nhanh |

*Tenengrad đang được dùng trong `src/frame_selector/sharpness.py` làm metric chính.*

### Lucky Imaging trong Sports Applications

1. **Logo Exposure**: Chỉ count frames có logo đủ sharp để đọc được (Nielsen's "image clarity" score là implementation này).
2. **Jersey Number Recognition**: "Jersey Number Recognition using Keyframe Identification from Low-Resolution Broadcast Videos" (ACM MM 2023) — frame selection trước OCR.
3. **Pipeline Tier 1 của chúng ta**: `burst.py` → tìm sharpest frame trong ±N frame window quanh candidate.

### Temporal Sharpness Weighting

Thay vì binary select/reject, assign weights based on sharpness → weighted temporal average:
```python
weights = softmax(tenengrad_scores / temperature)
result = sum(weights * aligned_frames)
```
*Đây chính xác là điều đang làm trong `tier3/optical-flow-fusion/flow_fusion.py`.*

---

## 8. Papers Sports-Specific

### MoSA-Det: Motion State Adaptive Object Detection

- **Paper**: "MoSA-Det: motion state adaptive object detection for sports videos" — Scientific Reports, April 2026.
- **URL**: https://www.nature.com/articles/s41598-026-43231-2
- **Ý tưởng**: Dùng motion states làm regulatory signals cho detection strategy; hai thách thức: (1) motion blur-induced feature degradation; (2) temporal aggregation failure khi inter-frame displacement quá lớn.
- **Kiến trúc**: Motion state estimator + adaptive detection branch selection.
- **Kết quả**: mAP@0.5 = 80.5%; +1.7% over baseline; sports: basketball, soccer (+1.7), volleyball (+1.4).
- **Relevance**: **TRỰC TIẾP** — paper đầu tiên explicitly address motion blur trong multi-sport object detection.

### TeamTrack Dataset

- **Paper**: Scott et al. — "TeamTrack: A Dataset for Multi-Sport Multi-Object Tracking", CVPR Workshops 2024.
- **GitHub**: https://github.com/AtomScott/TeamTrack
- **Data**: 279,900+ frames; 4,374,900+ bounding boxes; 4K–8K resolution; soccer, basketball, handball.
- **Relevance**: Training/evaluation data cho motion blur handling trong sports MOT; 4K resolution làm motion blur visible và cần explicit handling.

### SoccerSynth-Detection

- **Paper**: "SoccerSynth-Detection: A Synthetic Dataset for Soccer Player Detection", 2025.
- **URL**: https://arxiv.org/abs/2501.09281
- **Key finding**: "SoccerSynth-Detection significantly outperformed real datasets in images with motion blur" — synthetic motion blur augmentation RẤT hiệu quả cho blur-robust detection.
- **Relevance**: Validates synthetic blur augmentation approach; ID-Blau + SoccerSynth-Detection style augmentation → blur-robust jersey/logo detectors.

### Jersey Number Recognition — Keyframe

- **Paper**: "Jersey Number Recognition using Keyframe Identification from Low-Resolution Broadcast Videos" — ACM MM Workshop on Multimedia Content Analysis in Sports, 2023.
- **URL**: https://dl.acm.org/doi/abs/10.1145/3606038.3616162
- **Ý tưởng**: Trong broadcast video, hầu hết frames không readable (blur, angle, occlusion). Keyframe selection identify few readable frames; OCR chỉ apply trên keyframes.
- **Challenges được nêu**: Motion blur, low resolution, partial occlusion.
- **Relevance**: Direct application — extends lucky imaging principle sang jersey number reading; applicable cho logo exposure measurement.

### HIDE Dataset — Human-Aware Deblurring

- **Paper**: Shen et al. — "Human-Aware Motion Deblurring", ICCV 2019.
- **GitHub**: https://github.com/joanshen0508/HA_deblur
- **Data**: 8,422 blurry/sharp pairs; human-centric scenes; 65,784 foreground human bboxes annotated.
- **Kiến trúc model**: Human parsing network guide deblurring CNN; body part segmentation focus vào human regions.
- **Relevance**: **TRỰC TIẾP** — athletes là human subjects trong motion, rất giống HIDE's pedestrian focus; models trained/evaluated trên HIDE generalize tốt sang players trên sports pitches.

### ExposureEngine — Logo Detection & Sponsor Analytics

- **Paper**: "ExposureEngine: Oriented Logo Detection and Sponsor Visibility Analytics in Sports Broadcasts" — SimulaMet-HOST; arXiv:2510.04739, October 2025.
- **URL**: https://arxiv.org/abs/2510.04739
- **Dataset**: 1,103 frames, Swedish elite soccer, 670 unique sponsor logos, OBB annotations.
- **Kiến trúc**: YOLOv11-Medium (OBB) + temporal smoothing + LLM analytics agent.
- **Kết quả**: mAP@0.5 = 0.859; precision = 0.96; recall = 0.87.
- **Blur mitigation**: OBB vs HBB — axis-aligned bboxes underestimate logo coverage cho tilted logos; **temporal smoothing** across frames handle motion blur frames.
- **Relevance**: **TRỰC TIẾP với Bradford Bulls v3** — OBB detection cho jersey/field logos; temporal smoothing cho blur-affected frames; visibility metric calculation.

### Blur-Aware Reconstruction via Gaussian Splatting

- **Paper**: "BARD-GS: Blur-Aware Reconstruction of Dynamic Scenes via Gaussian Splatting", arXiv 2025.
- **Ý tưởng**: Extends neural radiance fields + Gaussian Splatting với explicit blur modeling; separate camera motion blur và object motion blur.
- **Relevance**: 3D reconstruction của sports scenes từ blurry broadcast footage.

### Player Target Tracking với Edge Computing

- **Paper**: "Player target tracking and detection in football game video using edge computing and deep learning", 2022.
- **Key findings**: Motion blur during rapid movements là major challenge; 3-stage matching để xử lý motion blur và body overlap.

---

## 9. Hệ thống Thương mại

### Hawk-Eye Innovations (Sony)

- **Website**: https://www.hawkeyeinnovations.com
- **Technology**: 12+ high-res, high-frame-rate cameras per venue.
- **Blur approach**: Kinematics refinement — bone-length constraints, joint-limited inverse kinematics, temporal smoothing, symmetry constraints. Đây là **model-based blur correction**: fit physical motion model vào noisy/blurry detections.
- **Sports**: Tennis (ball tracking), Cricket, Soccer (offside VAR tại 2022 World Cup), NBA (SkeleTRACK — 29 skeletal points).
- **Key insight**: Dùng HIGH frame rate cameras để giảm per-frame blur → không cần image-level deblurring.

### TRACAB / ChyronHego

- **Technology**: Wide-angle cameras + optical tracking; 8–9 cm error margin.
- **Blur approach**: Temporal Kalman filtering của player position tracks; velocity-based smoothing trên blurry frames; IMU data supplement optical tracking.
- **Sports**: Soccer (Bundesliga, Premier League, MLS), NFL, NBA, Rugby.
- **Key insight**: Tracking degradation do motion blur được handle bằng **predictive Kalman filtering**, không phải image-level deblurring.

### Second Spectrum (Genius Sports)

- **Technology**: Player tracking qua broadcast video + dedicated cameras; deep learning detection.
- **Sports**: NBA (official tracking partner), MLS, LA Rams (NFL).
- **Blur approach**: Multi-frame temporal fusion cho player position; models trained on diverse blurry frames; temporal consistency constraints.

### Nielsen Sports (formerly vBrand)

- **Technology**: Frame-by-frame logo detection; AI + deep learning.
- **Blur mitigation**: **"Image clarity" weighting** — blurry logo exposures được down-weighted trong ROI calculation. Weighs: duration + SIZE + **IMAGE CLARITY**.
- **Key insight**: Image clarity scoring = essentially sharpness/blur score per frame — commercially implements Lucky Imaging selection.
- **Relevance**: Commercial validation rằng frame quality weighting quan trọng cho logo exposure measurement.

### Kantar Media

- **History**: First company mang image recognition vào sports market, 2004.
- **Technology**: Image recognition + audience data fusion; 25+ years of sports data.
- **Blur approach**: Temporal aggregation qua multiple frames; quality scoring cho partial/blurry logo frames.

### Pixellot

- **Scale**: 30,000+ installations globally; 19 sports.
- **Technology**: Fixed multi-array panoramic cameras; AI auto-tracking.
- **Blur approach**: Fixed cameras **giảm motion blur** (không có pan/tilt movements); AI tracking ở scene level không phải pixel level.

### Stats Perform (Opta)

- **Data**: 3,900+ competitions; 501,000 matches/year.
- **Technology**: Camera networks + wearables + manual notation.
- **Blur relevance**: "Off-tube" video analysis từ broadcast video inherits all blur limitations.

---

## 10. Logo Detection trong Sports Broadcast

### Landscape tổng quan

| Approach | Accuracy | Speed | Blur Robustness |
|---|---|---|---|
| YOLOv8/v11-HBB | High | Real-time | Low (fixed bbox misses tilted logos) |
| YOLOv11-OBB (ExposureEngine) | Higher | Real-time | Medium (temporal smoothing) |
| EDVR + detection | Highest | Slow | High (deblur first) |
| Frame selection + detection | Medium-High | Fast | High (only process sharp frames) |

### Temporal Smoothing — approach phổ biến nhất

Từ [API4AI blog]: *"When a logo detection solution only looks at 1 or 5 frames per second, it is likely the chosen frame may contain a blurry image as a result of motion blur from a camera pan."*

Commercial systems dùng sliding window temporal smoothing:
- Low-confidence (blurry) frames → interpolate từ neighboring sharp frames.
- Logo tracks: detect tại high-confidence frames, interpolate/extrapolate tại low-confidence frames.

### ExposureEngine Pipeline (OBB-based)

```
Input video → YOLOv11-Medium OBB → Confidence score per frame
→ Temporal smoothing (blur frames filled in) → Visibility metrics
→ LLM analytics agent → NL report
```

Temporal smoothing là blur mitigation chính — không cần image-level deblurring.

### Logo Deformation Problem

Logos trên curved surfaces (jersey numbers, inflatable boards) cần OBB (Oriented Bounding Box) hoặc quad-fit, không đủ với axis-aligned HBB. Motion blur làm vấn đề này tệ hơn vì edges của curved logo bị smear.

---

## 11. Benchmark Datasets

### GoPro Dataset — Image Deblurring Standard

- **Paper**: Nah, Kim, Lee — CVPR 2017.
- **URL**: https://seungjunnah.github.io/Datasets/gopro
- **Method**: GoPro camera tại 240fps; average 7–13 consecutive frames → synthetic blur của varying strength.
- **Size**: 3,214 blurry/sharp pairs (2,103 train, 1,111 test).
- **Resolution**: 720×1280.
- **Current SOTA**: ~34.6 dB PSNR (AdaRevD, CVPR 2024).
- **Note**: Synthetic blur từ averaging — không hoàn toàn representative của real sports video blur.

### HIDE Dataset — Human-Aware

- **Paper**: Shen et al. — ICCV 2019.
- **URL**: https://github.com/joanshen0508/HA_deblur
- **Method**: High-speed camera; human-centric scenes; 65,784 foreground human bboxes.
- **Size**: 8,422 blurry/sharp pairs.
- **Current SOTA**: ~31.6 dB PSNR (FFTformer, MRLPFNet).
- **Sports relevance**: Human motion blur (foreground + background combined) → closest proxy cho sports player blur.

### RealBlur Dataset

- **Paper**: Rim et al. — ECCV 2020.
- **URL**: https://github.com/rimchang/RealBlur
- **Method**: Beam-splitting optical system — cùng scene, hai camera: một long exposure (blurry), một short exposure (sharp). Hai variants: RealBlur-J (JPEG) và RealBlur-R (RAW).
- **Size**: 4,738 pairs (3,758 train, 980 test).
- **Sports relevance**: Real-world camera motion blur → representative hơn cho broadcast camera conditions.
- **SOTA (RealBlur-J)**: ~29 dB (Uformer: 29.06, Restormer: 28.96).

### DVD Dataset — Video Deblurring

- **Paper**: Su et al. — CVPR 2017.
- **Method**: DSLR tại low shutter speed (intentional blur); paired với sharp từ tripod.
- **Size**: 71 video clips; 1080p.
- **SOTA**: ~36+ dB (VRT, Shift-Net, VD-Diff range).

### REDS Dataset

- **Paper**: NTIRE19 Challenge; Nah et al.
- **URL**: https://seungjunnah.github.io/Datasets/reds.html
- **Method**: 120fps footage downsampled; 720×1280; larger và phức tạp hơn GoPro.
- **Size**: 240 video clips (100 frames mỗi clip).
- **Use**: Video deblurring + super-resolution + denoising; EDVR, BasicVSR, VRT evaluation.

### BSD Dataset (Blur-Static-Dynamic) — Real Video

- **Paper**: 2021 — "Real-world Video Deblurring: A Benchmark Dataset".
- **Method**: Co-axis beam splitter — hai cameras aligned, different exposures → same scene.
- **Key property**: FIRST real-world video deblurring dataset; 3 blur intensity levels.
- **Note**: Models trained trên BSD transfer tốt hơn sang các real-world datasets khác.

### ReLoBlur Dataset — LOCAL Motion Blur ⭐ *Most relevant to sports*

- **Paper**: Li et al. — AAAI 2023.
- **GitHub**: https://github.com/LeiaLi/ReLoBlur
- **Method**: Synchronized beam-splitting photographing; 2,405 pairs; 2,152×1,436 resolution.
- **Blur type**: **LOCAL** — chỉ một phần image blurry (foreground object moving against sharp background).
- **Relevance**: **RẤT QUAN TRỌNG** — LOCAL blur (player/ball moving against relatively static stadium background) chính xác là blur type chính trong sports video. Đây là dataset phù hợp nhất để train model cho sports application.

### Khoảng trống dataset

> Không có sports-specific deblurring dataset (rugby, soccer, basketball) với paired sharp/blurry ground truth tính đến 2025. HIDE là proxy gần nhất. **Đây là gap nghiên cứu có thể khai thác.**

---

## 12. Performance Comparison Table

### Single Image Deblurring (GoPro Benchmark)

| Method | Venue | PSNR (GoPro) | SSIM | Type | Speed |
|---|---|---|---|---|---|
| **AdaRevD** | CVPR 2024 | **34.60** | — | Transformer (reversible) | Medium |
| **FFTformer** | CVPR 2023 | **34.21** | 0.969 | Transformer (FFT) | Medium |
| **NAFNet** | ECCV 2022 | **33.69** | — | CNN (activation-free) | **Fast** |
| Uformer | CVPR 2022 | 33.06 | 0.967 | Transformer (window) | Medium |
| Restormer | CVPR 2022 | 32.92 | 0.961 | Transformer (channel attn) | Slow |
| MAXIM | CVPR 2022 | 32.86 | — | MLP | Medium |
| MPRNet | CVPR 2021 | 32.66 | 0.959 | CNN (3-stage) | Slow |
| MIMO-UNet+ | ICCV 2021 | 32.45 | 0.957 | CNN | Fast |
| DMPHN (4-level) | CVPR 2019 | 32.20 | 0.976 | CNN (patch) | Medium |
| SRN | CVPR 2018 | 30.26 | 0.934 | CNN+RNN | Medium |
| DeepDeblur | CVPR 2017 | 29.08 | 0.914 | CNN (multi-scale) | Slow |
| DeblurGAN-v2 (Inception) | ICCV 2019 | 29.55 | 0.934 | GAN | Medium |
| DeblurGAN-v2 (MobileNet) | ICCV 2019 | ~28.37 | — | GAN | **Real-time** |
| DeblurGAN | CVPR 2018 | 28.70 | 0.858 | GAN | Medium |

### HIDE Benchmark (Human-Aware — Most Sports-Relevant)

| Method | PSNR (HIDE) | SSIM |
|---|---|---|
| FFTformer | 31.62 | 0.945 |
| Restormer | 31.22 | 0.942 |
| MPRNet | 30.96 | 0.939 |
| NAFNet | ~30.5 | — |

### RealBlur-J Benchmark (Real-world)

| Method | PSNR (RealBlur-J) | SSIM |
|---|---|---|
| Uformer | 29.06 | 0.884 |
| Restormer | 28.96 | 0.879 |
| MPRNet | 28.70 | 0.873 |

### Video Deblurring (GoPro Video Benchmark)

| Method | Venue | PSNR | Type | Real-time |
|---|---|---|---|---|
| VD-Diff | ECCV 2024 | SOTA | Diffusion+Transformer | No |
| BSSTNet | CVPR 2024 | SOTA | Sparse Transformer | No |
| Shift-Net | CVPR 2023 | >38 dB | Shift (no flow) | Near |
| VRT | TIP 2024 | 38.83 | Transformer | No (10s/frame) |
| RVRT | NeurIPS 2022 | Competitive | Recurrent Transformer | No |
| BasicVSR++ | CVPR 2022 | Strong | Recurrent+Deformable | No |
| EDVR | CVPR 2019 | ~31 dB | Deformable CNN | No |
| CDVD-TSP | CVPR 2020 | 31.97 | CNN+Flow | No |

---

## 13. Synthesis — Áp dụng vào Bradford Bulls / Sports Video

### Hai nguồn blur và cách xử lý

```
Camera pan blur (global)          →  Classical, Single-image DL
                                      Wiener (nếu PSF biết), NAFNet, FFTformer
                                      ─────────────────────────────
Player motion blur (local)        →  Video DL với temporal context
                                      BSSTNet, STFAN, EDVR
                                      Hoặc: Frame selection (lucky imaging)
                                      + local deblurring (AdaRevD adaptive exit)
```

### Tiến trình 3 tiers trong project

| Tier | Approach | Method | Tradeoff |
|---|---|---|---|
| **Tier 1** | Temporal burst selection | Lucky Imaging | Không artifact, chỉ work nếu có frame sharp gần đó |
| **Tier 2** | Single image deblurring | NAFNet (GoPro-width64) | Cải thiện blind, có thể artifact; CPU chậm hơn |
| **Tier 3** | Optical flow + temporal fusion | RAFT + sharpness-weighted fuse | Tốt nhất về chất lượng, chậm nhất, có ghost risk |

### 10 Phương pháp Quan trọng nhất cho Sports Logo Detection

1. **NAFNet** — Best FLOPs-to-PSNR ratio; practical nhất cho batch processing sports broadcast.
2. **FFTformer** — Highest PSNR cho single-image; frequency domain tự nhiên cho camera motion blur.
3. **Restormer** — Strong general model; đặc biệt tốt cho defocus blur (players ở depth boundaries).
4. **BSSTNet (CVPR 2024)** — Best video deblurring cho sports: blur-aware sparse attention handle mixed sharp/blurry sequences; directly leverage sharp frames làm reference.
5. **VD-Diff (ECCV 2024)** — Best quality video deblurring cho post-production sports highlights.
6. **DeblurGAN-v2 (MobileNet)** — ONLY truly real-time option cho live broadcast; tradeoff: lower PSNR nhưng 30+ FPS.
7. **RIFE** — Frame rate upsampling (25fps → 60fps); giảm apparent motion blur; real-time.
8. **ExposureEngine approach** — YOLOv11-OBB + temporal smoothing; directly applicable cho Bradford Bulls jersey/logo analysis.
9. **Frame selection / Lucky Imaging** — Simple Laplacian variance filter làm pre-step; cải thiện precision đáng kể.
10. **ReLoBlur-style training** — Train deblurring models trên LOCAL motion blur (player-against-background) thay vì global camera blur; generalizes tốt hơn cho sports.

### Key Insight cho Logo/Jersey Detection trong Sports

- **Logo trên advertising boards**: Chủ yếu camera pan blur (source 1). Temporal smoothing 3–5 frames thường đủ (Nielsen approach). Classical methods + single-image DL work tốt.
- **Logo trên jerseys**: Chủ yếu player motion blur (source 2). Cần LOCAL deblurring hoặc video methods với temporal context. Keyframe selection + local deblurring reliable nhất.
- **Approach kết hợp (recommended)**:
  ```
  Frame selection (Tier 1) → identify best candidate
  → NAFNet deblur (Tier 2) → further improve sharpness
  → Detection on deblurred frame
  → Temporal smoothing across shot → final visibility metric
  ```

### Gap nghiên cứu có thể khai thác

1. **Chưa có sports-specific deblurring dataset** — rugby, soccer với paired ground truth.
2. **Chưa có model trained đặc biệt cho jersey/logo blur** — ReLoBlur + sports data augmentation là hướng đi.
3. **Blur-aware logo detection** chưa được address systematically — blur map integration vào YOLO detector.

### Roadmap phát triển tiếp

```
Hiện tại (v3):
  Lucky Imaging (Tier 1) → NAFNet (Tier 2) → RAFT Fusion (Tier 3)

Tương lai (v4):
  ├── BSSTNet video deblurring (thay Tier 3)
  ├── DeblurGAN-v2 MobileNet cho real-time mode
  ├── YOLOv11-OBB integration (ExposureEngine approach)
  └── ReLoBlur-style training với sports-specific data augmentation

Post-production (v5):
  └── VD-Diff (ECCV 2024) cho highest-quality highlight processing
```

---

## Tài nguyên

### GitHub Repositories chính

- **Awesome-Deblurring** (comprehensive list): https://github.com/subeeshvasu/Awesome-Deblurring
- **NAFNet** (Tier 2 của chúng ta): https://github.com/megvii-research/NAFNet
- **Restormer**: https://github.com/swz30/Restormer
- **FFTformer**: https://github.com/kkkls/FFTformer
- **RAFT** (Tier 3 của chúng ta): https://github.com/princeton-vl/RAFT (torchvision)
- **BSSTNet**: https://github.com/huicongzhang/BSSTNet
- **VD-Diff**: https://github.com/Chen-Rao/VD-Diff
- **DeblurGAN-v2**: https://github.com/VITA-Group/DeblurGANv2
- **RIFE**: https://github.com/hzwer/ECCV2022-RIFE
- **FILM**: https://github.com/google-research/frame-interpolation
- **ExposureEngine dataset**: https://huggingface.co/datasets/SimulaMet-HOST/ExposureEngine
- **TeamTrack**: https://github.com/AtomScott/TeamTrack
- **ReLoBlur**: https://github.com/LeiaLi/ReLoBlur
- **Blind-Motion-Deblurring-Survey 2024**: https://github.com/VisionVerse/Blind-Motion-Deblurring-Survey
