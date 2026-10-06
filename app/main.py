"""Application factory.

Ders notu: `create_app()` bir "factory"dir. Her çağrıda sıfırdan, bağımsız bir uygulama üretir;
testler bellek içi veritabanıyla kendi uygulamasını kurabilir, sunucu ise kalıcı dosya kullanır.
"""
from __future__ import annotations

import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from starlette.concurrency import run_in_threadpool

from app.config.settings import Settings, load_settings
from app.core.clock import utcnow
from app.core.context import build_context
from app.core.db import Database
from app.core.errors import install_error_handlers
from app.core.registry import ModuleSpec, load_modules

logger = logging.getLogger("foodrescue")


class NoCacheStatic(StaticFiles):
    """Local test server: never serve stale JS/CSS while students are editing."""

    async def get_response(self, path, scope):
        response = await super().get_response(path, scope)
        response.headers["Cache-Control"] = "no-cache"
        return response


def run_maintenance(app: FastAPI) -> None:
    """One maintenance pass: every module's on_tick hook (expiry of foods and reservations)."""
    for spec in app.state.modules:
        if spec.on_tick is None:
            continue
        with app.state.db.session() as session:
            spec.on_tick(session, utcnow())


async def _maintenance_loop(app: FastAPI, interval: int) -> None:
    while True:
        await asyncio.sleep(interval)
        try:
            await run_in_threadpool(run_maintenance, app)
        except Exception:  # keep the loop alive; a failed pass is retried on the next tick
            logger.exception("maintenance pass failed")


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or load_settings()
    ctx = build_context(settings)
    db = Database(settings.database_url, ctx)
    modules: list[ModuleSpec] = load_modules(settings.enabled_modules)
    for spec in modules:
        if spec.subscribe:
            spec.subscribe(ctx.bus)
    db.create_all()  # every module's models are imported by now (through routers/services)
    settings.upload_dir.mkdir(parents=True, exist_ok=True)

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        task = None
        if settings.maintenance_interval_seconds > 0:
            task = asyncio.create_task(_maintenance_loop(app, settings.maintenance_interval_seconds))
        yield
        if task:
            task.cancel()

    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        docs_url="/docs" if settings.is_local else None,
        redoc_url=None,
        lifespan=lifespan,
    )
    app.state.ctx = ctx
    app.state.db = db
    app.state.modules = modules
    install_error_handlers(app)

    if settings.cors_origins:
        app.add_middleware(
            CORSMiddleware, allow_origins=list(settings.cors_origins), allow_methods=["*"], allow_headers=["*"]
        )

    @app.get("/api/v1/health", tags=["system"])
    def health():
        return {"status": "ok", "version": settings.app_version, "modules": [m.name for m in modules]}

    for spec in modules:
        for router in spec.routers:
            app.include_router(router)

    app.mount("/uploads", StaticFiles(directory=settings.upload_dir), name="uploads")
    if settings.web_dir.exists():
        app.mount("/", NoCacheStatic(directory=settings.web_dir, html=True), name="web")
    return app
