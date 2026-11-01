"""Demo seed data: consistent customers + entries for recording."""
from __future__ import annotations

import sqlite3
from datetime import date, timedelta

from . import db

DEMO = [
    ("Ramesh", "rice 5kg", 320, "credit", 20),
    ("Ramesh", "dal 2kg", 240, "credit", 12),
    ("Ramesh", "payment", 200, "payment", 5),
    ("Suresh", "oil 1L", 150, "credit", 25),
    ("Suresh", "sugar 2kg", 110, "credit", 9),
    ("Anita", "atta 10kg", 450, "credit", 30),
    ("Anita", "payment", 450, "payment", 2),
    ("Vikram", "tea 500g", 180, "credit", 15),
    ("Vikram", "biscuits", 60, "credit", 3),
]


def seed(conn: sqlite3.Connection | None = None) -> dict:
    own = conn is None
    conn = conn or db.get_conn()
    try:
        for name, desc, amt, kind, days_ago in DEMO:
            conn.execute("INSERT OR IGNORE INTO customers (name, created_at) VALUES (?,?)",
                         (name, db.now_iso()))
            cid = conn.execute("SELECT id FROM customers WHERE name=?", (name,)).fetchone()["id"]
            d = (date.today() - timedelta(days=days_ago)).isoformat()
            conn.execute(
                "INSERT INTO entries (customer_id, date, description, amount, kind, confirmed_at)"
                " VALUES (?,?,?,?,?,?)",
                (cid, d, desc, amt, kind, db.now_iso()),
            )
        db.audit(conn, "user", "seed_demo", {"entries": len(DEMO)})
        conn.commit()
    finally:
        if own:
            conn.close()
    return {"customers": len({r[0] for r in DEMO}), "entries": len(DEMO)}


if __name__ == "__main__":
    db.init_db()
    print(seed())
