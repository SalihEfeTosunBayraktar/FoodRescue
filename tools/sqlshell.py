"""Run a .sql worksheet (or a single query) against the local database and print readable tables.

    python tools/sqlshell.py app/modules/impact/sql/queries.sql
    python tools/sqlshell.py "SELECT role, COUNT(*) FROM users GROUP BY role"
    python tools/sqlshell.py --db data/foodrescue.db app/modules/inventory/sql/queries.sql

The database is opened read-only unless --write is given, so exploring cannot damage test data.
Worksheets that contain BEGIN ... ROLLBACK blocks need --write (a transaction needs a writable
connection) but still leave the data unchanged.
"""
from __future__ import annotations

import argparse
import sqlite3
import sys
from pathlib import Path

DEFAULT_DB = Path(__file__).resolve().parents[1] / "data" / "foodrescue.db"


def split_statements(sql: str) -> list[str]:
    """Split on ';' using sqlite3.complete_statement so semicolons inside strings do not break it."""
    statements, buffer = [], ""
    for line in sql.splitlines(keepends=True):
        buffer += line
        if sqlite3.complete_statement(buffer):
            statements.append(buffer.strip())
            buffer = ""
    if buffer.strip():
        statements.append(buffer.strip())
    return [s for s in statements if any(not l.strip().startswith("--") and l.strip() for l in s.splitlines())]


def render(cursor: sqlite3.Cursor) -> str:
    if cursor.description is None:
        return "(ok)"
    headers = [d[0] for d in cursor.description]
    rows = [["NULL" if v is None else str(v) for v in row] for row in cursor.fetchall()]
    widths = [max(len(h), *(len(r[i]) for r in rows)) if rows else len(h) for i, h in enumerate(headers)]
    widths = [min(w, 60) for w in widths]
    line = lambda cells: " | ".join(c[:60].ljust(widths[i]) for i, c in enumerate(cells))
    out = [line(headers), "-+-".join("-" * w for w in widths)] + [line(r) for r in rows]
    out.append(f"({len(rows)} satır)")
    return "\n".join(out)


def run(connection: sqlite3.Connection, sql: str) -> None:
    for statement in split_statements(sql):
        first = next((l for l in statement.splitlines() if l.strip()), "")
        print(f"\n>>> {first.strip()}" + (" ..." if "\n" in statement.strip() else ""))
        print(render(connection.execute(statement)))


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8")  # Windows consoles default to a legacy code page
    sys.stderr.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("target", help="path to a .sql file or a SQL string")
    parser.add_argument("--db", type=Path, default=DEFAULT_DB)
    parser.add_argument("--write", action="store_true", help="open the database writable")
    args = parser.parse_args()

    if not args.db.exists():
        print(f"Veritabanı yok: {args.db}\nÖnce sunucuyu bir kez başlatın: python run.py", file=sys.stderr)
        return 1
    sql = Path(args.target).read_text(encoding="utf-8") if Path(args.target).exists() else args.target
    uri = f"file:{args.db.as_posix()}?mode={'rw' if args.write else 'ro'}"
    connection = sqlite3.connect(uri, uri=True, isolation_level=None)  # autocommit: BEGIN/ROLLBACK are explicit
    try:
        run(connection, sql)
    except sqlite3.Error as exc:
        print(f"\nSQL hatası: {exc}", file=sys.stderr)
        return 2
    finally:
        connection.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
