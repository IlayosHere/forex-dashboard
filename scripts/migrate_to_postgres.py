"""
Migrate local SQLite data to remote PostgreSQL via Cloud SQL Proxy.

Reads whatever columns exist in the local SQLite and inserts them into
Postgres (which has the full schema via create_all). Missing columns
get NULL/defaults.

Usage:
    python scripts/migrate_to_postgres.py
"""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import sqlite3

import psycopg2
import psycopg2.extras

PROJECT_ROOT = Path(__file__).resolve().parent.parent
SQLITE_PATH = str(PROJECT_ROOT / "signals.db")

PG_HOST = "127.0.0.1"
PG_PORT = 5433
PG_USER = "forex"
PG_DB = "forex"
GCP_PROJECT = "project-2f1c7228-98f9-4373-a13"

# Tables to migrate in dependency order
TABLES = ["signals", "accounts", "trades"]

# Defaults for NOT NULL columns that may be missing in older SQLite schemas
COLUMN_DEFAULTS = {
    "accounts": {"owner": "admin"},
    "trades": {"owner": "admin"},
}


def get_password() -> str:
    pw = os.environ.get("DB_PASSWORD")
    if pw:
        return pw.strip()
    print("Fetching password from GCP Secret Manager ...")
    result = subprocess.run(
        ["gcloud.cmd", "secrets", "versions", "access", "latest",
         "--secret=db_password", f"--project={GCP_PROJECT}"],
        capture_output=True, text=True, check=True,
    )
    return result.stdout.strip()


def get_sqlite_tables(conn: sqlite3.Connection) -> list[str]:
    cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
    return [row[0] for row in cursor.fetchall()]


def get_sqlite_columns(conn: sqlite3.Connection, table: str) -> list[str]:
    cursor = conn.execute(f"PRAGMA table_info(\"{table}\")")
    return [row[1] for row in cursor.fetchall()]


def ensure_pg_tables(pg_conn) -> None:
    """Create tables in Postgres using SQLAlchemy models."""
    from sqlalchemy import create_engine
    from api.db import Base
    from api.models import AccountModel, SignalModel, TradeModel, UserModel  # noqa: F401
    engine = create_engine(
        "postgresql://",
        connect_args={
            "host": PG_HOST, "port": PG_PORT,
            "user": PG_USER, "password": get_password(),
            "dbname": PG_DB,
        },
    )
    Base.metadata.create_all(engine)
    engine.dispose()


def migrate_table(
    src: sqlite3.Connection,
    dst,
    table: str,
) -> int:
    columns = get_sqlite_columns(src, table)
    rows = src.execute(f"SELECT {','.join(columns)} FROM \"{table}\"").fetchall()
    if not rows:
        return 0

    # Add missing NOT NULL columns with defaults
    defaults = COLUMN_DEFAULTS.get(table, {})
    for col, default_val in defaults.items():
        if col not in columns:
            columns.append(col)
            rows = [row + (default_val,) for row in rows]

    # Build upsert: INSERT ... ON CONFLICT (id) DO UPDATE
    cols_str = ", ".join(columns)
    placeholders = ", ".join(["%s"] * len(columns))
    update_set = ", ".join(
        f"{c} = EXCLUDED.{c}" for c in columns if c != "id"
    )

    sql = f"""
        INSERT INTO "{table}" ({cols_str})
        VALUES ({placeholders})
        ON CONFLICT (id) DO UPDATE SET {update_set}
    """

    cursor = dst.cursor()
    cursor.executemany(sql, rows)
    return len(rows)


def main() -> None:
    password = get_password()
    print(f"Password OK ({len(password)} chars)\n")

    src = sqlite3.connect(SQLITE_PATH)
    existing_tables = get_sqlite_tables(src)

    pg_conn = psycopg2.connect(
        host=PG_HOST, port=PG_PORT,
        user=PG_USER, password=password,
        dbname=PG_DB,
    )
    pg_conn.autocommit = False

    # Create Postgres schema
    ensure_pg_tables(pg_conn)

    try:
        for table in TABLES:
            if table not in existing_tables:
                print(f"  {table}: skipped (not in local SQLite)")
                continue
            count = migrate_table(src, pg_conn, table)
            print(f"  {table}: {count} rows migrated")

        pg_conn.commit()
        print("\nDone. All data migrated successfully.")
    except Exception:
        pg_conn.rollback()
        raise
    finally:
        src.close()
        pg_conn.close()


if __name__ == "__main__":
    main()
