"""Capture every screen of the app (all roles, desktop + mobile) into screenshots/ (git-ignored).

    python tools/screenshots.py
    python tools/screenshots.py --out my_shots

It starts its own temporary server with fresh demo data, so your local database and any shared
instance are untouched. Needs Playwright (pip install playwright && playwright install chromium).
Map tiles come from the internet; offline, maps appear without tiles.
"""
from __future__ import annotations

import argparse
import re
import shutil
import socket
import sys
import tempfile
import threading
import time
from dataclasses import replace
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import uvicorn  # noqa: E402
from playwright.sync_api import sync_playwright  # noqa: E402

from app.config.settings import load_settings  # noqa: E402
from app.main import create_app  # noqa: E402
from app.seed import DEMO_ACCOUNTS, DEMO_PASSWORD, seed_demo  # noqa: E402

DESKTOP = {"width": 1280, "height": 900}
MOBILE = {"width": 390, "height": 844}


def free_port() -> int:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


class Shooter:
    def __init__(self, browser, base: str, out: Path, viewport: dict, counter: list[int]) -> None:
        self.base, self.out, self.counter = base, out, counter
        self.context = browser.new_context(viewport=viewport, locale="tr-TR")
        self.page = self.context.new_page()
        out.mkdir(parents=True, exist_ok=True)

    def open(self, route: str, wait_map: bool = False) -> None:
        target = f"{self.base}/#{route}"
        if self.page.url == target:
            self.page.reload()  # navigating to the identical hash URL would not re-render the page
        else:
            self.page.goto(target)
        self.page.wait_for_load_state("networkidle")
        self.page.wait_for_timeout(1800 if wait_map else 350)

    def login(self, role: str) -> None:
        self.open("/login")
        self.page.fill("input[name=email]", DEMO_ACCOUNTS[role])
        self.page.fill("input[name=password]", DEMO_PASSWORD)
        self.page.click("button[type=submit]")
        self.page.wait_for_function("() => !location.hash.startsWith('#/login')")
        self.page.wait_for_load_state("networkidle")

    def shot(self, name: str) -> None:
        self.counter[0] += 1
        path = self.out / f"{self.counter[0]:02d}_{name}.png"
        self.page.screenshot(path=str(path), full_page=True)
        print(f"  {path.relative_to(ROOT) if path.is_relative_to(ROOT) else path}")

    def close(self) -> None:
        self.context.close()


def desktop_pass(browser, base: str, out: Path) -> None:
    n = [0]
    anon, student, donor, pending, shelter, admin = (Shooter(browser, base, out, DESKTOP, n) for _ in range(6))

    print("Ziyaretçi")
    anon.open("/", wait_map=True); anon.shot("ziyaretci_ana_sayfa")
    anon.open("/foods", wait_map=True); anon.shot("ziyaretci_bagis_akisi")
    anon.page.click(".chip[data-cat=ANIMAL]"); anon.page.wait_for_timeout(600); anon.shot("ziyaretci_filtre_hayvan")
    anon.open("/foods"); anon.page.locator("a.food-card", has_text="Pilav ve tavuk").click()
    anon.page.wait_for_selector("text=Rezervasyon"); anon.page.wait_for_timeout(1500); anon.shot("ziyaretci_ilan_detay")
    anon.open("/login"); anon.shot("giris")
    anon.open("/register"); anon.shot("kayit_rol_secimi")
    for role_text, name in (("Yararlanıcı", "yararlanici"), ("Bağışçı işletme", "bagisci"), ("Hayvan barınağı", "barinak")):
        anon.open("/register")
        anon.page.locator("button.role-card", has_text=role_text).click()
        anon.page.wait_for_timeout(1500 if name == "bagisci" else 300)
        anon.shot(f"kayit_formu_{name}")

    print("Yararlanıcı")
    student.login("beneficiary"); student.page.wait_for_timeout(1500); student.shot("yararlanici_bagis_akisi")
    student.open("/foods"); student.page.locator("a.food-card", has_text="Pilav ve tavuk").click()
    student.page.wait_for_selector("button:has-text('Rezerve et')"); student.page.wait_for_timeout(1500); student.shot("yararlanici_ilan_detay_rezervasyon")
    student.page.click("button:has-text('Rezerve et')")
    student.page.wait_for_selector(".ticket img"); student.page.wait_for_timeout(400); student.shot("yararlanici_cuzdan_qr_pin")
    pin = re.sub(r"\s", "", student.page.inner_text(".pin"))
    student.open("/notifications"); student.shot("yararlanici_bildirimler")

    print("Bağışçı")
    donor.login("donor"); donor.shot("bagisci_panel")
    donor.open("/donor/new"); donor.shot("bagisci_yeni_ilan")
    donor.open("/donor/desk"); donor.page.wait_for_selector("text=Teslim bekleyenler"); donor.shot("bagisci_teslim_masasi")
    donor.page.fill("input[name=code]", "000000"); donor.page.click("button:has-text('Teslimi onayla')")
    donor.page.wait_for_selector(".notice-error"); donor.shot("bagisci_hatali_pin")
    donor.page.fill("input[name=code]", pin); donor.page.click("button:has-text('Teslimi onayla')")
    donor.page.wait_for_selector(".verified"); donor.page.wait_for_timeout(400); donor.shot("bagisci_teslim_onaylandi")
    donor.open("/notifications"); donor.shot("bagisci_bildirimler")

    print("Yararlanıcı: teslim sonrası ve şikâyet")
    student.open("/wallet"); student.page.wait_for_selector("text=Teslim edildi"); student.shot("yararlanici_cuzdan_gecmis")
    student.page.locator("button:has-text('Sorun bildir')").first.click()
    student.page.fill("dialog textarea", "Yemek soğumuştu ve tarif edilenden az geldi.")
    student.page.wait_for_timeout(200); student.shot("yararlanici_sikayet_penceresi")
    student.page.click("dialog button:has-text('Gönder')"); student.page.wait_for_selector(".toast-success")

    print("Onay bekleyen bağışçı")
    pending.login("donor_pending"); pending.shot("bekleyen_bagisci_panel")

    print("Barınak")
    shelter.login("shelter"); shelter.page.wait_for_timeout(1500); shelter.shot("barinak_bagis_akisi")
    shelter.open("/foods"); shelter.page.locator("a.food-card", has_text="Kuru ekmek").click()
    shelter.page.wait_for_selector("button:has-text('Rezerve et')"); shelter.page.wait_for_timeout(1500); shelter.shot("barinak_ilan_detay")
    shelter.open("/wallet"); shelter.shot("barinak_cuzdan_bos")

    print("Yönetici")
    admin.login("admin"); admin.open("/admin/overview"); admin.shot("yonetici_genel_bakis")
    admin.open("/admin/accounts"); admin.page.wait_for_selector("text=Yeni Bistro"); admin.shot("yonetici_basvurular")
    admin.open("/admin/complaints"); admin.page.wait_for_selector("text=Sivas Lezzet"); admin.shot("yonetici_sikayetler")
    admin.open("/admin/audit"); admin.page.wait_for_selector("code"); admin.shot("yonetici_denetim_kaydi")
    admin.open("/notifications"); admin.shot("yonetici_bildirimler")

    print("Hata sayfaları")
    anon.open("/wallet"); anon.shot("yetkisiz_girise_yonlendirme")
    student.open("/admin/overview"); student.page.wait_for_selector("text=yetkiniz yok"); student.shot("yetki_yok")
    anon.open("/bulunmayan-sayfa"); anon.shot("sayfa_bulunamadi")

    for shooter in (anon, student, donor, pending, shelter, admin):
        shooter.close()


def mobile_pass(browser, base: str, out: Path) -> None:
    n = [0]
    anon, student, donor, admin = (Shooter(browser, base, out, MOBILE, n) for _ in range(4))
    print("Mobil")
    anon.open("/", wait_map=True); anon.shot("ana_sayfa")
    anon.page.click(".menu-toggle"); anon.page.wait_for_timeout(200); anon.shot("menu_acik")
    anon.open("/foods", wait_map=True); anon.shot("bagis_akisi")
    anon.open("/login"); anon.shot("giris")
    student.login("beneficiary"); student.open("/foods")
    student.page.locator("a.food-card", has_text="Yemekhane akşam menüsü").click()
    student.page.wait_for_selector("button:has-text('Rezerve et')"); student.page.wait_for_timeout(1500); student.shot("ilan_detay")
    student.page.click("button:has-text('Rezerve et')"); student.page.wait_for_selector(".ticket img"); student.page.wait_for_timeout(300); student.shot("cuzdan_qr_pin")
    donor.login("donor"); donor.shot("bagisci_panel")
    donor.open("/donor/desk"); donor.shot("bagisci_teslim_masasi")
    admin.login("admin"); admin.open("/admin/overview"); admin.shot("yonetici_genel_bakis")
    for shooter in (anon, student, donor, admin):
        shooter.close()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--out", type=Path, default=ROOT / "screenshots")
    args = parser.parse_args()
    sys.stdout.reconfigure(encoding="utf-8")

    for sub in ("masaustu", "mobil"):  # only our own output folders are cleared
        shutil.rmtree(args.out / sub, ignore_errors=True)

    work = Path(tempfile.mkdtemp(prefix="foodrescue-shots-"))
    settings = replace(
        load_settings(secret_key="screenshots-secret-key-with-32-bytes!!"),
        database_url=f"sqlite:///{(work / 'shots.db').as_posix()}",
        upload_dir=work / "uploads",
        maintenance_interval_seconds=0,
    )
    app = create_app(settings)
    with app.state.db.session() as session:
        seed_demo(session)
    port = free_port()
    server = uvicorn.Server(uvicorn.Config(app, host="127.0.0.1", port=port, log_level="warning"))
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()
    while not server.started:
        time.sleep(0.1)
    base = f"http://127.0.0.1:{port}"

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch()
            desktop_pass(browser, base, args.out / "masaustu")
            mobile_pass(browser, base, args.out / "mobil")
            browser.close()
    finally:
        server.should_exit = True
        thread.join(timeout=5)
        app.state.db.engine.dispose()
        shutil.rmtree(work, ignore_errors=True)
    print(f"\nBitti: {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
