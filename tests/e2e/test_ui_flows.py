"""Browser end-to-end tests (Playwright). Skipped automatically when Playwright is not installed.

    pip install playwright && playwright install chromium
    python -m pytest tests/e2e -q
    SCREENSHOT_DIR=shots python -m pytest tests/e2e -q      # also saves screenshots

Ders notu: uçtan uca (E2E) testler gerçek tarayıcıyı sürer; birim testlerin göremediği
"düğme yerinde mi, sayfa açılıyor mu" türü hataları yakalar. Yavaştırlar, bu yüzden sayıları az tutulur.
"""
from __future__ import annotations

import os
import re
import socket
import threading
import time
from dataclasses import replace
from pathlib import Path

import pytest

playwright_sync = pytest.importorskip("playwright.sync_api")
import uvicorn  # noqa: E402

from app.config.settings import load_settings  # noqa: E402
from app.main import create_app  # noqa: E402
from app.seed import DEMO_ACCOUNTS, DEMO_PASSWORD, seed_demo  # noqa: E402

# SCREENSHOT_DIR ortam değişkeni verilirse testler ekran görüntüsü de kaydeder.
SHOTS = Path(os.environ["SCREENSHOT_DIR"]) if os.environ.get("SCREENSHOT_DIR") else None
# External tile/CDN failures are environment noise, not application errors.
# Dış kaynaklardan (harita karoları, CDN) gelen ağ hataları uygulama hatası sayılmaz.
IGNORED_ERRORS = ("tile.openstreetmap.org", "unpkg.com", "ERR_INTERNET_DISCONNECTED", "ERR_NAME_NOT_RESOLVED", "Failed to load resource")


# İşletim sisteminden boş bir port ister: sabit port çakışmasını önler.
def _free_port() -> int:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


@pytest.fixture(scope="module")
# Testler için gerçek bir sunucu (uvicorn) arka plan thread'inde başlatılır, bitince kapatılır.
# scope='module': dosyadaki tüm testler aynı sunucuyu paylaşır (hız).
def base_url(tmp_path_factory):
    tmp = tmp_path_factory.mktemp("e2e")
    settings = replace(
        load_settings(secret_key="e2e-secret-key-with-at-least-32-bytes!!"),
        database_url=f"sqlite:///{(tmp / 'e2e.db').as_posix()}",
        upload_dir=tmp / "uploads",
        maintenance_interval_seconds=0,
    )
    app = create_app(settings)
    with app.state.db.session() as session:
        seed_demo(session)
    port = _free_port()
    server = uvicorn.Server(uvicorn.Config(app, host="127.0.0.1", port=port, log_level="warning"))
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()
    for _ in range(100):
        if server.started:
            break
        time.sleep(0.1)
    yield f"http://127.0.0.1:{port}"
    server.should_exit = True
    thread.join(timeout=5)


@pytest.fixture(scope="module")
# Playwright ile gerçek Chromium. Kurulu değilse testler atlanır (skip), hata vermez.
def browser():
    with playwright_sync.sync_playwright() as p:
        try:
            instance = p.chromium.launch()
        except Exception as exc:  # browser binary missing
            pytest.skip(f"Chromium not available: {exc}")
        yield instance
        instance.close()


# Bir kullanıcıyı (tarayıcı bağlamı) temsil eder: kendi çerezleri ve depolaması vardır. Konsol
# hatalarını kaydeder.
class Session:
    """One browser context (= one user) that records console errors."""

    def __init__(self, browser, base_url: str, viewport=(1280, 900)) -> None:
        self.base = base_url
        self.context = browser.new_context(viewport={"width": viewport[0], "height": viewport[1]})
        self.page = self.context.new_page()
        self.errors: list[str] = []
        self.page.on("pageerror", lambda exc: self.errors.append(str(exc)))
        self.page.on("console", lambda msg: msg.type == "error" and self.errors.append(msg.text))

    # Sayfayı açar ve ağ boşalana kadar bekler.
    def open(self, hash_: str = "/") -> None:
        self.page.goto(f"{self.base}/#{hash_}")
        self.page.wait_for_load_state("networkidle")

    # Gerçek giriş formunu doldurur: arayüz akışının kendisini de sınar.
    def login(self, role: str) -> None:
        self.open("/login")
        self.page.fill("input[name=email]", DEMO_ACCOUNTS[role])
        self.page.fill("input[name=password]", DEMO_PASSWORD)
        self.page.click("button[type=submit]")
        self.page.wait_for_function("() => !location.hash.startsWith('#/login')")
        self.page.wait_for_load_state("networkidle")

    def shot(self, name: str) -> None:
        if SHOTS:
            SHOTS.mkdir(parents=True, exist_ok=True)
            self.page.screenshot(path=str(SHOTS / f"{name}.png"), full_page=True)

    def app_errors(self) -> list[str]:
        return [e for e in self.errors if not any(noise in e for noise in IGNORED_ERRORS)]

    def close(self) -> None:
        self.context.close()


@pytest.fixture()
# Her test kendi oturumlarını açar; test bitince hepsi kapatılır (yield sonrası temizlik).
def make_session(browser, base_url):
    sessions: list[Session] = []

    def _make(**kwargs) -> Session:
        s = Session(browser, base_url, **kwargs)
        sessions.append(s)
        return s

    yield _make
    for s in sessions:
        s.close()


# Ziyaretçi akışı: sayaçlar, ilan listesi ve filtreler. wait_for_function: sonucun GELMESİNİ bekler
# (asenkron arayüzde sabit bekleme yerine koşul beklemek testi hem hızlı hem kararlı yapar).
def test_home_and_feed_filters(make_session):
    s = make_session()
    s.open("/")
    page = s.page
    assert "Çöpe gidecek yemek" in page.inner_text("h1")
    assert page.locator(".stat-value").first.inner_text() == "1"
    s.open("/foods")
    page.wait_for_function("() => document.querySelectorAll('a.food-card').length === 6")
    s.shot("01_feed")
    page.click(".chip[data-cat=ANIMAL]")
    page.wait_for_function("() => document.querySelectorAll('a.food-card').length === 2")
    page.click(".chip[data-cat='']")
    page.fill(".search input", "çorba")
    page.wait_for_function("() => document.querySelectorAll('a.food-card').length === 1")
    assert not s.app_errors(), s.app_errors()


# İKİ kullanıcılı gerçek senaryo: yararlanıcı rezerve eder, bağışçı PIN ile teslimi onaylar,
# yararlanıcı şikâyet eder. İlk deneme yanlış PIN ile yapılır. Ekranda 'null' veya '[object' metni
# olmaması da denetlenir (eskiden yaşanmış bir hatanın regresyon testi).
def test_beneficiary_reserves_and_donor_verifies_with_pin(make_session):
    student, donor = make_session(), make_session()
    student.login("beneficiary")
    page = student.page
    student.open("/foods")
    page.locator("a.food-card", has_text="Pilav ve tavuk").click()
    page.wait_for_selector("text=Rezerve et")
    student.shot("02_detail")
    page.click("button:has-text('Rezerve et')")
    page.wait_for_selector(".ticket img")
    assert page.url.endswith("#/wallet")
    pin = re.sub(r"\s", "", page.inner_text(".pin"))
    assert re.fullmatch(r"\d{6}", pin)
    student.shot("03_wallet_ticket")
    assert "null" not in page.inner_text(".view") and "[object" not in page.inner_text(".view")  # regression: replaceChildren(null)

    donor.login("donor")
    donor.open("/donor/desk")
    donor.page.fill("input[name=code]", "000000")
    donor.page.click("button:has-text('Teslimi onayla')")
    donor.page.wait_for_selector(".notice-error")
    donor.page.fill("input[name=code]", pin)
    donor.page.click("button:has-text('Teslimi onayla')")
    donor.page.wait_for_selector(".verified")
    donor.shot("04_desk_verified")
    assert "null" not in donor.page.inner_text(".view") and "[object" not in donor.page.inner_text(".view")

    student.open("/wallet")
    page.wait_for_selector("text=Teslim edildi")
    page.click("button:has-text('Sorun bildir')")
    page.fill("textarea", "Yemek soğumuştu ve eksik geldi.")
    page.click("dialog button:has-text('Gönder')")
    page.wait_for_selector(".toast-success")
    assert not student.app_errors(), student.app_errors()
    assert not donor.app_errors(), donor.app_errors()


# Yönetici akışı: onay bekleyeni onaylar, denetim kaydında olayı görür.
def test_admin_approves_pending_donor(make_session):
    admin = make_session()
    admin.login("admin")
    admin.open("/admin/accounts")
    page = admin.page
    page.wait_for_selector("text=Yeni Bistro")
    admin.shot("05_admin_accounts")
    page.click("button:has-text('Onayla')")
    page.fill("dialog textarea", "Belgeler uygun.")
    page.click("dialog button:has-text('Onayla')")
    page.wait_for_selector("text=Bu durumda hesap yok.")
    admin.open("/admin/audit")
    page.wait_for_selector("code:has-text('account.reviewed')")
    admin.shot("06_admin_audit")
    assert not admin.app_errors(), admin.app_errors()


# Bağışçı formu doldurup ilan yayınlar.
def test_donor_creates_listing(make_session):
    donor = make_session()
    donor.login("donor")
    donor.open("/donor/new")
    page = donor.page
    page.fill("input[name=title]", "Akşam yemeği paketi")
    page.fill("input[name=portions]", "6")
    page.check("input[name=hygiene]")
    page.click("button:has-text('Yayınla')")
    page.wait_for_selector("text=Akşam yemeği paketi")
    assert page.url.endswith("#/donor")
    donor.shot("07_donor_dashboard")
    assert not donor.app_errors(), donor.app_errors()


# Erişim koruması (girişsiz ve yetkisiz) ile mobil düzen: yatay taşma olmamalı ve menü açılabilmeli.
def test_guards_and_mobile_layout(make_session):
    anonymous = make_session()
    anonymous.open("/wallet")
    assert "#/login" in anonymous.page.url

    student = make_session()
    student.login("beneficiary")
    student.open("/admin/overview")
    student.page.wait_for_selector("text=yetkiniz yok")

    phone = make_session(viewport=(390, 800))
    phone.open("/")
    assert phone.page.is_visible(".menu-toggle")
    phone.page.click(".menu-toggle")
    assert phone.page.is_visible("#main-nav.is-open")
    overflow = phone.page.evaluate("document.documentElement.scrollWidth - document.documentElement.clientWidth")
    assert overflow <= 1, f"horizontal overflow of {overflow}px on a phone"
    phone.shot("08_mobile_home")
