Thả video full match vào ĐÂY (.mp4 / .mov / .mkv / .avi).

Chạy report:
    conda activate bradford_bulls
    python backend/scripts/run_match_report.py --kit home

  --kit home  = Bradford mặc áo trắng (Main Sponsor = Top Notch)
  --kit away  = Bradford mặc áo đen   (Main Sponsor = Floor Tonic)
  --fps 2     = số frame phân tích mỗi giây (mặc định 2; giảm 1.0 cho nhanh gấp đôi)

Mỗi video ở đây sẽ ra 1 file .xlsx trong ..\match_reports\
Video đã chạy rồi sẽ được export lại luôn; dùng --force để chạy lại detection.

Nếu 2 video khác kit nhau, chạy 2 lần với --video:
    python backend/scripts/run_match_report.py --video match_input\A.mp4 --kit home
    python backend/scripts/run_match_report.py --video match_input\B.mp4 --kit away

Chi tiết: docs\12-full-match-report.md
