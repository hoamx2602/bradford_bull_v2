"""FastAPI application entry point."""
from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import (
    routes_analyses,
    routes_health,
    routes_jobs,
    routes_settings,
    routes_teamrefs,
)
from app.config import get_settings
from app.db.base import init_db

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(title=settings.app_name, version="0.1.0", lifespan=lifespan)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_list,
        # Accept ANY localhost port too — the Next dev server hops to 3001/3002
        # when 3000 is busy, and a missing origin there silently falls back to
        # demo data in the dashboard.
        allow_origin_regex=r"https?://(localhost|127\.0\.0\.1)(:\d+)?",
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(routes_health.router)
    app.include_router(routes_jobs.router)
    app.include_router(routes_analyses.router)
    app.include_router(routes_teamrefs.router)
    app.include_router(routes_settings.router)
    return app


app = create_app()
