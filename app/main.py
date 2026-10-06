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


# Yerel test sunucusunda tarayıcı eski JS/CSS'i önbellekten göstermesin diye 'no-cache' başlığı
# ekleyen statik dosya sunucusu.
class NoCacheStatic(StaticFiles):
    """Local test server: never serve stale JS/CSS while students are editing."""

    async def get_response(self, path, scope):
        response = await super().get_response(path, scope)
        response.headers["Cache-Control"] = "no-cache"
        return response


# Bakım turu: her modülün on_tick fonksiyonunu çağırır (süresi dolan ilan ve rezervasyonları
# kapatma). Test sırasında bu fonksiyon doğrudan çağrılır.
def run_maintenance(app: FastAPI) -> None:
    """One maintenance pass: every module's on_tick hook (expiry of foods and reservations)."""
    for spec in app.state.modules:
        if spec.on_tick is None:
            continue
        with app.state.db.session() as session:
            spec.on_tick(session, utcnow())


# Arka planda periyodik çalışan döngü. Hata olursa döngü ölmez, bir sonraki turda yeniden dener.
async def _maintenance_loop(app: FastAPI, interval: int) -> None:
    while True:
        # Asenkron bekleme: bu sırada sunucu diğer istekleri işlemeye devam eder.
        await asyncio.sleep(interval)
        try:
            # Veritabanı işi senkron olduğu için ayrı thread'de çalıştırılır; böylece olay döngüsü
            # (event loop) bloke olmaz.
            await run_in_threadpool(run_maintenance, app)
        # Beklenmeyen hata döngüyü öldürmesin; logla ve devam et.
        except Exception:  # keep the loop alive; a failed pass is retried on the next tick
            logger.exception("maintenance pass failed")


# Uygulama fabrikası: her çağrıda sıfırdan, bağımsız bir uygulama üretir. Testler bellek içi
# veritabanlı kendi uygulamasını, sunucu ise kalıcı dosyalı olanı kurar.
def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or load_settings()
    # 1) Paylaşılan nesneleri (olay yolu, sınırlayıcılar) kur.
    ctx = build_context(settings)
    # 2) Veritabanı bağlantısını kur.
    db = Database(settings.database_url, ctx)
    # 3) Ayarlarda açık olan modülleri yükle.
    modules: list[ModuleSpec] = load_modules(settings.enabled_modules)
    for spec in modules:
        # 4) Önce olay dinleyicilerini kaydet: ilk olay yayınlanmadan abonelikler hazır olmalı.
        if spec.subscribe:
            spec.subscribe(ctx.bus)
    # 5) Tabloları kur. Modellerin hepsi bu noktada import edilmiştir (router ve servis import'ları
    # sayesinde).
    db.create_all()  # every module's models are imported by now (through routers/services)
    settings.upload_dir.mkdir(parents=True, exist_ok=True)

    # lifespan: sunucu açılırken ve kapanırken çalışan kod. yield'den önce açılış, sonra kapanış.
    @asynccontextmanager
    async def lifespan(app: FastAPI):
        # Bakım döngüsü ayarda sıfır verilirse hiç başlamaz (testler böyle kapatır).
        task = None
        if settings.maintenance_interval_seconds > 0:
            task = asyncio.create_task(_maintenance_loop(app, settings.maintenance_interval_seconds))
        # Sunucu burada çalışır durumdadır.
        yield
        if task:
            task.cancel()

    # docs_url yalnızca yerelde açıktır: üretimde API belgesi sızdırılmaz.
    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        docs_url="/docs" if settings.is_local else None,
        redoc_url=None,
        lifespan=lifespan,
    )
    # app.state: uygulamaya iliştirilmiş paylaşılan nesneler. Endpoint'ler request.app.state
    # üzerinden ulaşır.
    app.state.ctx = ctx
    app.state.db = db
    app.state.modules = modules
    # AppError -> JSON dönüşümünü etkinleştir.
    install_error_handlers(app)

    # CORS yalnızca izin verilen adresler tanımlıysa açılır. Varsayılan kapalı: ön yüz aynı adresten
    # sunulduğu için gerek yok.
    if settings.cors_origins:
        app.add_middleware(
            CORSMiddleware, allow_origins=list(settings.cors_origins), allow_methods=["*"], allow_headers=["*"]
        )

    # Sağlık kontrolü: uygulama ayakta mı, hangi modüller yüklü? İzleme araçları ve paylaşım betiği
    # bunu kullanır.
    @app.get("/api/v1/health", tags=["system"])
    def health():
        return {"status": "ok", "version": settings.app_version, "modules": [m.name for m in modules]}

    for spec in modules:
        # Her modülün router'ını uygulamaya bağlar; modül kendi yollarını kendisi tanımlar.
        for router in spec.routers:
            app.include_router(router)

    # Yüklenen fotoğrafları sunar.
    app.mount("/uploads", StaticFiles(directory=settings.upload_dir), name="uploads")
    if settings.web_dir.exists():
        # '/' EN SONA bağlanır: önce API yolları eşleşsin, geriye kalan her istek statik ön yüz
        # dosyasına gitsin. Sırayı tersine çevirirseniz API'ye hiç ulaşılamaz.
        app.mount("/", NoCacheStatic(directory=settings.web_dir, html=True), name="web")
    return app
