"""Central runtime settings. Every tunable value lives here; modules never read os.environ."""
from __future__ import annotations

import os
import secrets
from dataclasses import dataclass, replace
from pathlib import Path

# Proje kök klasörü: bu dosyanın iki üst dizini. Tüm yollar buradan türetilir, böylece proje nereye
# kopyalanırsa kopyalansın çalışır.
ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = ROOT / "data"
WEB_DIR = ROOT / "web"

# Varsayılan olarak yüklenen modüller. Sıra önemlidir: önce bağımlı olunan modüller.
ALL_MODULES = ("identity", "inventory", "reservation", "notification", "impact")


# Ayarlar değişmez bir veri sınıfıdır. Çalışma sırasında kimse bir ayarı sessizce değiştiremez.
@dataclass(frozen=True)
# Uygulamanın tüm ayarları. Kodun başka hiçbir yerinde sihirli sayı (örn. 90 dakika, 5 deneme)
# bulunmaz; hepsi buradan okunur.
class Settings:
    app_env: str = "local"
    app_name: str = "FoodRescue"
    app_version: str = "2.0.0"
    # SQLite yerelde sıfır kurulumla çalışır. Üretimde DATABASE_URL ortam değişkeniyle PostgreSQL
    # adresi verilir.
    database_url: str = f"sqlite:///{(DATA_DIR / 'foodrescue.db').as_posix()}"
    secret_key: str = ""
    upload_dir: Path = DATA_DIR / "uploads"
    web_dir: Path = WEB_DIR
    cors_origins: tuple[str, ...] = ()
    enabled_modules: tuple[str, ...] = ALL_MODULES

    # Giriş bileti (JWT) ömrü: 720 dakika = 12 saat.
    token_ttl_minutes: int = 720
    login_max_failures: int = 8
    login_window_seconds: int = 300

    # Bir rezervasyonun teslim alınması için tanınan süre; dolunca porsiyonlar stoğa döner.
    reservation_ttl_minutes: int = 90
    max_active_reservations: int = 2
    # Teslim masasında işletme başına izin verilen hatalı PIN denemesi; aşılırsa
    # verify_window_seconds kadar kilitlenir. 6 haneli PIN'in kaba kuvvetle bulunmasını engeller.
    verify_max_failures: int = 5
    verify_window_seconds: int = 300

    # Bir işletmeyi askıya almak için gereken FARKLI kişiden açık şikâyet sayısı.
    complaint_suspend_threshold: int = 3
    # Fotoğraf yükleme üst sınırı (2 MB). Sınırsız yükleme, diski doldurma saldırısına kapı açar.
    max_upload_bytes: int = 2 * 1024 * 1024
    max_pickup_window_hours: int = 24
    maintenance_interval_seconds: int = 30

    # Varsayılan harita merkezi (Sivas).
    default_lat: float = 39.7477
    default_lon: float = 37.0179
    default_radius_km: float = 15.0

    # Hesaplanan özellik: `settings.is_local` parantezsiz çağrılır.
    @property
    def is_local(self) -> bool:
        return self.app_env == "local"


# `.env` dosyasını (ANAHTAR=değer satırları) okur. Gizli ayarlar koda değil ortama yazılır; .env
# dosyası git'e girmez.
def _load_dotenv(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    if not path.exists():
        return values
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        values[key.strip()] = value.strip().strip('"').strip("'")
    return values


# Yerelde makineye özel rastgele bir anahtarı bir kez üretip data/.dev_secret dosyasına yazarız.
# Anahtar koda gömülseydi herkes aynı anahtarla sahte giriş bileti üretebilirdi.
def _dev_secret() -> str:
    """Persisted per-machine key so local tokens survive restarts. Never used outside local."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    path = DATA_DIR / ".dev_secret"
    if not path.exists():
        path.write_text(secrets.token_urlsafe(48), encoding="utf-8")
    return path.read_text(encoding="utf-8").strip()


# Ayarları kurar. Kaynak önceliği: gerçek ortam değişkeni > .env dosyası > koddaki varsayılan.
def load_settings(**overrides) -> Settings:
    # İki sözlüğü birleştirir; sağdaki (os.environ) soldakini ezer.
    env = {**_load_dotenv(ROOT / ".env"), **os.environ}
    base = Settings(
        app_env=env.get("APP_ENV", "local"),
        database_url=env.get("DATABASE_URL", Settings.database_url),
        secret_key=env.get("SECRET_KEY", ""),
        cors_origins=tuple(o for o in env.get("CORS_ORIGINS", "").split(",") if o),
    )
    # dataclasses.replace: değişmez nesnenin değiştirilmiş KOPYASINI üretir. Testler ayarları böyle
    # ezer.
    settings = replace(base, **overrides)
    # Anahtar verilmediyse: yerelde otomatik üret, değilse uygulamayı hiç başlatma.
    if not settings.secret_key:
        if not settings.is_local:
            # 'Güvenli varsayılan': üretimde anahtar yoksa uygulama açılmaz. Zayıf bir anahtarla
            # sessizce çalışmasından iyidir.
            raise RuntimeError("SECRET_KEY must be set when APP_ENV is not 'local'.")
        settings = replace(settings, secret_key=_dev_secret())
    return settings
