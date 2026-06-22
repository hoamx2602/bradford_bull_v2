# Paper — CyberWorlds submission (LaTeX source)

Full draft of *"A Self-Improving Cyber-Physical Data Engine for Annotation-Free
Sponsor-Logo Analytics in Sports Broadcasts"* (IEEEtran conference).

## Files
| File | Nội dung |
|---|---|
| `main.tex` | Bài báo đầy đủ (abstract → conclusion), IEEEtran 2 cột |
| `refs.bib` | Tài liệu tham khảo (kiểm tra lại year/venue trước khi nộp) |
| `fig_architecture.tex` | Fig.1 — data engine / flywheel (TikZ, figure*) |
| `fig_funnel.tex` | Fig.2 — roster prior (C1) |
| `fig_labelmodel.tex` | Fig.3 — weak-supervision voting (C3) |
| `fig_twin.tex` | Fig.4 — 3DGS venue twin (C4) |
| `fig_efficiency.tex` | Fig.5 — mAP vs #labels (pgfplots, **placeholder**) |
| `fig_ablation.tex` | Fig.6 — ablation bars (pgfplots, **placeholder**) |
| `FIGURES.md` | Art-direction cho hình (thesis/poster style) + hình nên bổ sung |

## Biên dịch
Máy này chưa có LaTeX. Hai cách:

**Overleaf (khuyến nghị, nhanh nhất):** tạo project, upload toàn bộ thư mục
`paper/`, đặt `main.tex` làm main → Recompile. Hình TikZ render thành vector
publication-ready, không cần ảnh ngoài.

**Local:**
```bash
brew install --cask mactex-no-gui      # hoặc: tlmgr cần IEEEtran, pgfplots, tikz
cd paper && latexmk -pdf main.tex
```

## ⚠ Trước khi nộp
- Mọi số `\TODOnum{...}` (đỏ) là **placeholder** — thay bằng số đo thật. Tuyệt
  đối không nộp số chưa đo.
- Điền tác giả/affiliation.
- Kiểm tra `refs.bib` (tên tác giả/venue/năm một số mục để trống/ước lượng).
- Cân nhắc thêm Fig.7–9 (qualitative, fingerprint, exposure timeline) — xem
  `FIGURES.md`; đây là các hình tăng sức thuyết phục mạnh nhất.
- Khớp deadline & template chính thức của IEEE CyberWorlds năm nay (số trang,
  copyright block).

## Liên hệ tài liệu nền
Method ↔ `../frontier_solutions.md`; ablation/claims ↔ `../paper_cyberworlds.md`;
data engine code ↔ `../auto_label/`.
