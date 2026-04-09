from __future__ import annotations

from contextlib import asynccontextmanager
import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes.admin import router as admin_router
from app.api.routes.brief import router as brief_router
from app.api.routes.classify import router as classify_router
from app.api.routes.compress import router as compress_router
from app.api.routes.diff import router as diff_router
from app.api.routes.internal import router as internal_router
from app.api.routes.logs import router as logs_router
from app.api.routes.report import router as report_router
from app.api.routes.runs import router as runs_router
from app.core import bootstrap_runtime, get_settings
from app.routes.dispatch import router as dispatch_router
from app.routes.health import router as health_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    runtime = bootstrap_runtime(settings)
    app.state.settings = settings
    app.state.runtime = runtime
    yield


logging.basicConfig(level=logging.INFO)
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
app.include_router(runs_router)
app.include_router(admin_router)
app.include_router(internal_router)
