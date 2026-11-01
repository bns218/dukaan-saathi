"""SQLite layer. All balances computed in SQL, never by the model."""
from __future__ import annotations

import json
import os
import sqlite3
import time
from pathlib import Path

SCHEMA = """
CREATE TABLE IF NOT EXISTS customers (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  name TEXT NOT NULL UNIQUE,
  phone TEXT DEFAULT '',
  created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS entries (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  customer_id INTEGER NOT NULL REFERENCES customers(id),
  date TEXT NOT NULL,
  description TEXT DEFAULT '',
  amount REAL NOT NULL,
  kind TEXT NOT NULL CHECK (kind IN ('credit','payment')),
  source_image TEXT DEFAULT '',
  confidence REAL DEFAULT 0,
  confirmed_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS items (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  name TEXT NOT NULL UNIQUE,
  unit TEXT DEFAULT '',
  typical_qty REAL DEFAULT 1
);
CREATE TABLE IF NOT EXISTS reminders (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  customer_id INTEGER NOT NULL REFERENCES customers(id),
  draft_text TEXT NOT NULL,
  language TEXT NOT NULL DEFAULT 'hi',
  status TEXT NOT NULL DEFAULT 'draft'
    CHECK (status IN ('draft','approved','sent')),
  created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS audit_log (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  ts TEXT NOT NULL,
  actor TEXT NOT NULL,
  action TEXT NOT NULL,
  payload_json TEXT NOT NULL DEFAULT '{}'
);
CREATE INDEX IF NOT EXISTS idx_entries_customer ON entries(customer_id);
CREATE INDEX IF NOT EXISTS idx_entries_date ON entries(date);
"""


def _db_path() -> Path:
    p = Path(os.environ.get("DB_PATH", "./data/dukaan.db"))
    p.parent.mkdir(parents=True, exist_ok=True)
    return p


def get_conn(path: str | None = None) -> sqlite3.Connection:
    db = Path(path) if path else _db_path()
    db.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(db))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db(path: str | None = None) -> str:
    db = Path(path) if path else _db_path()
    conn = get_conn(str(db))
    try:
        conn.executescript(SCHEMA)
        conn.commit()
    finally:
        conn.close()
    return str(db)


def now_iso() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%S")


def audit(conn: sqlite3.Connection, actor: str, action: str, payload: dict) -> None:
    conn.execute(
        "INSERT INTO audit_log (ts, actor, action, payload_json) VALUES (?,?,?,?)",
        (now_iso(), actor, action, json.dumps(payload, ensure_ascii=False)),
    )
