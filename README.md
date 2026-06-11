# Bradford Bulls — Sponsor Logo Analytics

Đo lường sponsor logo exposure trên video broadcast và tính EMV (Equivalent
Media Value) per brand, kèm dashboard phân tích.

**📚 Tài liệu: [`docs/`](docs/README.md)** — bắt đầu từ
[Tổng quan](docs/01-overview.md) → [Cài đặt](docs/02-setup.md).

## Chạy nhanh

```bash
# Backend (cần weights tại logo_detection/runs/*/weights/best.pt)
cd backend
pip install -e . -e ".[team]"
python scripts/make_kit_anchors.py        # một lần
uvicorn app.main:create_app --factory --port 8000

# Frontend
cd logo-analytics
npm install && npm run dev                # http://localhost:3000
```

| Thành phần | Đường dẫn | Docs |
|---|---|---|
| Backend pipeline (FastAPI) | `backend/` | [Pipeline](docs/03-pipeline.md) · [API](docs/07-api.md) |
| Dashboard (Next.js) | `logo-analytics/` | [Dashboard](docs/06-dashboard.md) |
| Training model logo | `logo_detection/` | [Annotation & Training](docs/08-annotation-training.md) |
| Team filter | `backend/app/pipeline/teamid/` | [Team filter](docs/04-team-filter.md) |

> ⚠️ ultralytics pin **8.3.40** — bản mới hơn không load được weights hiện tại.
