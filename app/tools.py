"""Agent tools. Balances always computed in SQL. Every call is audited."""
from __future__ import annotations

import sqlite3
from datetime import date, timedelta

from . import db

TOOL_SPECS = [
    {"name": "get_balances", "description": "Outstanding balance per customer (credit minus payment), optionally one customer.",
     "parameters": {"type": "object", "properties": {"customer": {"type": "string"}}, "required": []}},
    {"name": "list_overdue", "description": "Customers with unpaid balance older than N days.",
     "parameters": {"type": "object", "properties": {"days": {"type": "integer", "default": 7}}, "required": []}},
    {"name": "search_entries", "description": "Find past entries by text and optional date range.",
     "parameters": {"type": "object", "properties": {
         "query": {"type": "string"}, "date_from": {"type": "string"}, "date_to": {"type": "string"}},
      "required": ["query"]}},
    {"name": "restock_suggestions", "description": "Frequently occurring items/descriptions in a period.",
     "parameters": {"type": "object", "properties": {"period_days": {"type": "integer", "default": 30}}, "required": []}},
    {"name": "draft_reminder", "description": "Save a reminder draft (never sends). Language hi/te/en.",
     "parameters": {"type": "object", "properties": {
         "customer": {"type": "string"}, "language": {"type": "string", "default": "hi"}},
      "required": ["customer"]}},
    {"name": "add_entry", "description": "Add one record. Caller must have user confirmation.",
     "parameters": {"type": "object", "properties": {
         "customer": {"type": "string"}, "description": {"type": "string"},
         "amount": {"type": "number"}, "kind": {"type": "string"},
         "date": {"type": "string"}}, "required": ["customer", "amount", "kind"]}},
]


def _balances(conn: sqlite3.Connection, customer: str | None = None) -> list[dict]:
    q = """SELECT c.name AS customer,
      COALESCE(SUM(CASE WHEN e.kind='credit' THEN e.amount ELSE -e.amount END),0) AS balance
      FROM customers c LEFT JOIN entries e ON e.customer_id=c.id"""
    args: list = []
    if customer:
        q += " WHERE c.name = ?"
        args.append(customer)
    q += " GROUP BY c.id HAVING balance != 0 OR ? IS NOT NULL ORDER BY balance DESC"
    args.append(customer)
    return [dict(r) for r in conn.execute(q, args).fetchall()]


def get_balances(conn: sqlite3.Connection, customer: str | None = None) -> list[dict]:
    out = _balances(conn, customer)
    db.audit(conn, "agent", "get_balances", {"customer": customer, "n": len(out)})
    conn.commit()
    return out


def list_overdue(conn: sqlite3.Connection, days: int = 7) -> list[dict]:
    cutoff = (date.today() - timedelta(days=days)).isoformat()
    rows = conn.execute(
        """SELECT c.name AS customer,
          COALESCE(SUM(CASE WHEN e.kind='credit' THEN e.amount ELSE -e.amount END),0) AS balance,
          MAX(CASE WHEN e.kind='credit' THEN e.date ELSE NULL END) AS last_credit
          FROM customers c JOIN entries e ON e.customer_id=c.id
          GROUP BY c.id HAVING balance > 0 AND (last_credit IS NULL OR last_credit <= ?)
          ORDER BY balance DESC""",
        (cutoff,),
    ).fetchall()
    out = [dict(r) for r in rows]
    db.audit(conn, "agent", "list_overdue", {"days": days, "n": len(out)})
    conn.commit()
    return out


def search_entries(conn: sqlite3.Connection, query: str,
                   date_from: str = "", date_to: str = "") -> list[dict]:
    q = """SELECT c.name AS customer, e.date, e.description, e.amount, e.kind
           FROM entries e JOIN customers c ON c.id=e.customer_id
           WHERE (c.name LIKE ? OR e.description LIKE ?)"""
    args: list = [f"%{query}%", f"%{query}%"]
    if date_from:
        q += " AND e.date >= ?"
        args.append(date_from)
    if date_to:
        q += " AND e.date <= ?"
        args.append(date_to)
    q += " ORDER BY e.date DESC LIMIT 50"
    out = [dict(r) for r in conn.execute(q, args).fetchall()]
    db.audit(conn, "agent", "search_entries", {"query": query, "n": len(out)})
    conn.commit()
    return out


def restock_suggestions(conn: sqlite3.Connection, period_days: int = 30) -> list[dict]:
    cutoff = (date.today() - timedelta(days=period_days)).isoformat()
    rows = conn.execute(
        """SELECT description AS item, COUNT(*) AS times,
                  SUM(CASE WHEN kind='credit' THEN amount ELSE 0 END) AS total
           FROM entries WHERE date >= ? AND kind='credit' AND description != ''
           GROUP BY description ORDER BY times DESC LIMIT 10""",
        (cutoff,),
    ).fetchall()
    out = [dict(r) for r in rows]
    db.audit(conn, "agent", "restock_suggestions", {"period_days": period_days})
    conn.commit()
    return out


_REMINDER_TMPL = {
    "hi": "नमस्ते {name} जी, आपका {amt:.0f} रुपये का उधार बाकी है। कृपया जल्द भुगतान करें। धन्यवाद!",
    "te": "నమస్తే {name} గారు, మీకు {amt:.0f} రూపాయలు బకాయి ఉంది. దయచేసి త్వరలో చెల్లించండి. ధన్యవాదాలు!",
    "en": "Hello {name}, you have an outstanding balance of Rs {amt:.0f}. Please pay at your convenience. Thank you!",
}


def draft_reminder(conn: sqlite3.Connection, customer: str, language: str = "hi") -> dict:
    row = conn.execute("SELECT id, name FROM customers WHERE name=?", (customer,)).fetchone()
    if row is None:
        raise ValueError(f"unknown customer: {customer}")
    bal = _balances(conn, customer)
    amt = bal[0]["balance"] if bal else 0
    tmpl = _REMINDER_TMPL.get(language, _REMINDER_TMPL["hi"])
    text = tmpl.format(name=row["name"], amt=amt)
    cur = conn.execute(
        "INSERT INTO reminders (customer_id, draft_text, language, status, created_at) VALUES (?,?,?,?,?)",
        (row["id"], text, language, "draft", db.now_iso()),
    )
    db.audit(conn, "agent", "draft_reminder",
             {"customer": customer, "language": language, "id": cur.lastrowid})
    conn.commit()
    return {"id": cur.lastrowid, "customer": customer, "draft_text": text,
            "language": language, "status": "draft"}


def add_entry(conn: sqlite3.Connection, customer: str, amount: float, kind: str,
              description: str = "", entry_date: str = "") -> dict:
    if kind not in ("credit", "payment"):
        raise ValueError("kind must be credit or payment")
    conn.execute("INSERT OR IGNORE INTO customers (name, created_at) VALUES (?,?)",
                 (customer, db.now_iso()))
    cid = conn.execute("SELECT id FROM customers WHERE name=?", (customer,)).fetchone()["id"]
    cur = conn.execute(
        "INSERT INTO entries (customer_id, date, description, amount, kind, confirmed_at) VALUES (?,?,?,?,?,?)",
        (cid, entry_date or date.today().isoformat(), description, amount, kind, db.now_iso()),
    )
    db.audit(conn, "agent", "add_entry",
             {"customer": customer, "amount": amount, "kind": kind, "id": cur.lastrowid})
    conn.commit()
    return {"id": cur.lastrowid, "customer": customer, "amount": amount, "kind": kind}
