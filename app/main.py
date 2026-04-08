from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.routes.brief import router as brief_router
from app.routes.classify import router as classify_router
from app.routes.compress import router as compress_router
from app.routes.diff import router as diff_router
from app.routes.dispatch import router as dispatch_router
from app.routes.health import router as health_router
from app.routes.logs import router as logs_router
from app.routes.report import router as report_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    settings.ensure_runtime_dirs()
    app.state.settings = settings
    yield


settings = get_settings()
app = FastAPI(title=settings.app_name, version="0.1.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_allow_origins_raw,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(health_router)
app.include_router(classify_router)
app.include_router(logs_router)
app.include_router(diff_router)
app.include_router(compress_router)
app.include_router(brief_router)
app.include_router(report_router)
app.include_router(dispatch_router)
