"""Local test server launcher.

    python run.py                 start on http://127.0.0.1:8000 (seeds demo data on first run)
    python run.py --reset         delete the local database and start fresh
    python run.py --port 8010
"""
from __future__ import annotations

import argparse
import logging

import uvicorn

from app.config.settings import DATA_DIR, load_settings
from app.main import create_app
from app.seed import DEMO_ACCOUNTS, DEMO_PASSWORD, seed_demo


def main() -> None:
    parser = argparse.ArgumentParser(description="FoodRescue local test server")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument("--reset", action="store_true", help="delete the local SQLite database first")
    parser.add_argument("--no-seed", action="store_true", help="do not insert demo data")
    parser.add_argument("--admin-password", help="private admin password (use when the server is shared publicly)")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    settings = load_settings()
    if args.reset:
        # Only the known database file, never a wider folder.
        for suffix in ("", "-wal", "-shm"):
            (DATA_DIR / f"foodrescue.db{suffix}").unlink(missing_ok=True)

    app = create_app(settings)
    if not args.no_seed:
        with app.state.db.session() as session:
            if seed_demo(session, admin_password=args.admin_password):
                print("Demo data created.")

    base = f"http://{args.host}:{args.port}"
    print(f"\nFoodRescue test server: {base}   (API docs: {base}/docs)")
    print(f"Demo password for all accounts{' except admin' if args.admin_password else ''}: {DEMO_PASSWORD}")
    for role, email in DEMO_ACCOUNTS.items():
        print(f"  {role:<14} {email}")
    print()
    uvicorn.run(app, host=args.host, port=args.port, log_level="info")


if __name__ == "__main__":
    main()
