from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Iterator

from fastapi import Request
from sqlalchemy import DateTime, Enum as SAEnum, create_engine, event
from sqlalchemy.engine import Engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker
from sqlalchemy.pool import StaticPool
from sqlalchemy.types import TypeDecorator

from app.core.clock import ensure_utc
from app.core.context import AppContext


# Tüm model sınıflarının atası. `Base.metadata` tabloların listesini tutar; create_all bunu
# kullanarak tabloları kurar.
class Base(DeclarativeBase):
    pass


# SQLite tarihi saat dilimsiz saklar. Bu özel tür yazarken UTC'ye çevirip dilimi atar, okurken UTC
# dilimini geri ekler: uygulama içinde her zaman 'aware' tarih görürüz.
class UTCDateTime(TypeDecorator):
    """Stores naive UTC, always returns timezone-aware UTC."""

    impl = DateTime
    cache_ok = True

    # Veritabanına YAZARKEN çalışır.
    def process_bind_param(self, value: datetime | None, dialect) -> datetime | None:
        if value is None:
            return None
        return ensure_utc(value).replace(tzinfo=None)

    # Veritabanından OKURKEN çalışır.
    def process_result_value(self, value: datetime | None, dialect) -> datetime | None:
        if value is None:
            return None
        return value.replace(tzinfo=timezone.utc)


# native_enum=False: değer veritabanında VARCHAR olarak saklanır (SQLite'ta ENUM tipi yok,
# taşınabilirlik). validate_strings=True: geçersiz değer yazılmasını engeller.
def enum_column(enum_cls: type):
    return SAEnum(enum_cls, native_enum=False, length=24, validate_strings=True)


# Motor (engine) ve oturum fabrikasını (session factory) sarar. Uygulama başına bir tane kurulur.
class Database:
    def __init__(self, url: str, ctx: AppContext) -> None:
        self._ctx = ctx
        # SQLite'a özel ayarlar bu sözlükte toplanır.
        kwargs: dict[str, Any] = {}
        if url.startswith("sqlite"):
            # check_same_thread=False: FastAPI istekleri farklı thread'lerde çalışır, SQLite
            # varsayılanı buna izin vermez.
            kwargs["connect_args"] = {"check_same_thread": False}
            if url in ("sqlite://", "sqlite:///:memory:"):
                # Bellek içi veritabanı bağlantı kapanınca silinir; StaticPool tek bağlantıyı
                # paylaştırır. Yalnızca testler için.
                kwargs["poolclass"] = StaticPool
        # Engine = veritabanına bağlantı havuzu.
        self.engine: Engine = create_engine(url, **kwargs)
        if url.startswith("sqlite"):
            # Her yeni bağlantıda yabancı anahtarları açan fonksiyonu bağlar (aşağıya bakın).
            event.listen(self.engine, "connect", _enable_sqlite_foreign_keys)
        # expire_on_commit=False: commit sonrası nesnenin alanları yeniden sorgulanmaz; yanıt
        # oluştururken fazladan SELECT olmaz.
        self._factory = sessionmaker(bind=self.engine, expire_on_commit=False)

    # Modellerden tabloları kurar. Var olan tabloların şemasını DEĞİŞTİRMEZ (bunun için Alembic gibi
    # migration aracı gerekir).
    def create_all(self) -> None:
        Base.metadata.create_all(self.engine)

    # Session = bir 'iş birimi' (unit of work): değişiklikleri biriktirir, commit ile tek işlemde
    # yazar.
    def session(self) -> Session:
        session = self._factory()
        # Bağlamı session'a iliştiririz; servisler ctx_of(db) ile ulaşır.
        session.info["ctx"] = self._ctx
        return session


# SQLite'ta yabancı anahtar (FOREIGN KEY) denetimi varsayılan olarak KAPALIDIR. PRAGMA ile her
# bağlantıda açmazsak var olmayan kullanıcıya bağlı kayıt eklenebilir.
def _enable_sqlite_foreign_keys(dbapi_connection, _record) -> None:
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()


# FastAPI bağımlılığı: her istek için bir session açar, iş bitince (yield sonrası finally) kapatır.
# Endpoint'ler `Depends(get_db)` ile alır.
def get_db(request: Request) -> Iterator[Session]:
    session = request.app.state.db.session()
    try:
        yield session
    finally:
        session.close()
