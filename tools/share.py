"""Share the local test server with other people through a Cloudflare quick tunnel.

    python tools/share.py              # fresh demo data, random private admin password
    python tools/share.py --keep-data  # keep the current local database
    python tools/share.py --port 8010

What it does: starts `run.py`, opens a temporary https://<random>.trycloudflare.com address that forwards
to it, prints the link and the admin login, and saves them to data/share_info.txt (git-ignored).
Stop with Ctrl+C: both the server and the tunnel are closed and the link stops working.

Ders notu (güvenlik): bu komut yerel sunucunuzu İNTERNETE açar. Bu yüzden yönetici parolası her
çalıştırmada rastgele üretilir (bilinen demo parolası kullanılmaz). Link tahmin edilemez ama gizli
değildir: kimle paylaştıysanız o kullanabilir. Bitince kapatın. Gerçek kişisel veri girmeyin.
Gereken: cloudflared (https://developers.cloudflare.com/cloudflare-one/connections/connect-networks/downloads/).
"""
from __future__ import annotations

import argparse
import re
import secrets
import shutil
import subprocess
import sys
import threading
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
INFO_FILE = ROOT / "data" / "share_info.txt"
CLOUDFLARED_DEFAULT = Path(r"C:\Program Files (x86)\cloudflared\cloudflared.exe")
URL_PATTERN = re.compile(r"https://[a-zA-Z0-9-]+\.trycloudflare\.com")
ADMIN_EMAIL = "admin@foodrescue.local"
DEMO_PASSWORD = "Demo12345"
DEMO_ACCOUNTS = [
    ("Bağışçı (onaylı)", "restoran@foodrescue.local"),
    ("Yararlanıcı", "ogrenci@foodrescue.local"),
    ("Barınak", "barinak@foodrescue.local"),
    ("Bağışçı (onay bekleyen)", "yeni.isletme@foodrescue.local"),
]


def find_cloudflared() -> str:
    if CLOUDFLARED_DEFAULT.exists():
        return str(CLOUDFLARED_DEFAULT)
    found = shutil.which("cloudflared")
    if not found:
        sys.exit("cloudflared bulunamadı. Kurulum: https://developers.cloudflare.com/cloudflare-one/connections/connect-networks/downloads/")
    return found


def wait_for_health(port: int, timeout: float = 40) -> None:
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            with urllib.request.urlopen(f"http://127.0.0.1:{port}/api/v1/health", timeout=2):
                return
        except OSError:
            time.sleep(0.5)
    raise RuntimeError("sunucu zamanında başlamadı")


def read_tunnel_url(process: subprocess.Popen, timeout: float = 60) -> str:
    found: list[str] = []
    ready = threading.Event()

    def pump() -> None:  # keeps draining output so cloudflared never blocks on a full pipe
        for line in process.stderr:
            match = URL_PATTERN.search(line)
            if match and not found:
                found.append(match.group(0))
                ready.set()

    threading.Thread(target=pump, daemon=True).start()
    if not ready.wait(timeout):
        raise RuntimeError("tünel adresi alınamadı (internet bağlantısını kontrol edin)")
    return found[0]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument("--keep-data", action="store_true", help="do not reset the local database")
    args = parser.parse_args()
    sys.stdout.reconfigure(encoding="utf-8")

    admin_password = secrets.token_urlsafe(12)
    server_cmd = [sys.executable, str(ROOT / "run.py"), "--port", str(args.port), "--admin-password", admin_password]
    if not args.keep_data:
        server_cmd.append("--reset")

    server = subprocess.Popen(server_cmd, cwd=ROOT, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    tunnel = None
    try:
        wait_for_health(args.port)
        tunnel = subprocess.Popen(
            [find_cloudflared(), "tunnel", "--no-autoupdate", "--url", f"http://127.0.0.1:{args.port}"],
            stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, text=True, encoding="utf-8", errors="replace",
        )
        url = read_tunnel_url(tunnel)

        lines = [
            f"Paylaşım linki : {url}",
            f"API belgeleri  : {url}/docs",
            "",
            "YÖNETİCİ (yalnızca sizde kalsın)",
            f"  e-posta : {ADMIN_EMAIL}",
            f"  parola  : {admin_password}",
            "",
            f"TEST HESAPLARI (parola hepsinde: {DEMO_PASSWORD})",
            *[f"  {label:<26} {email}" for label, email in DEMO_ACCOUNTS],
            "",
            "Kapatmak için bu pencerede Ctrl+C. Kapanınca link çalışmaz.",
        ]
        text = "\n".join(lines)
        INFO_FILE.parent.mkdir(exist_ok=True)
        INFO_FILE.write_text(text + "\n", encoding="utf-8")
        print("\n" + text + f"\n\n(Bilgiler ayrıca kaydedildi: {INFO_FILE})\n", flush=True)

        while server.poll() is None and tunnel.poll() is None:
            time.sleep(1)
        print("Süreçlerden biri kapandı, paylaşım sonlandırılıyor.")
        return 1
    except KeyboardInterrupt:
        print("\nKapatılıyor...")
        return 0
    finally:
        for process in (tunnel, server):
            if process and process.poll() is None:
                process.terminate()
        INFO_FILE.unlink(missing_ok=True)  # the saved admin password is only valid while sharing


if __name__ == "__main__":
    sys.exit(main())
