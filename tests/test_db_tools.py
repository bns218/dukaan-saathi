"""Balances in SQL, tools, audit log."""
from app import db, tools


def test_balances_credit_minus_payment():
    db.init_db()
    conn = db.get_conn()
    try:
        tools.add_entry(conn, "Ramesh", 320, "credit", "rice 5kg")
        tools.add_entry(conn, "Ramesh", 240, "credit", "dal 2kg")
        tools.add_entry(conn, "Ramesh", 200, "payment", "payment")
        bals = {b["customer"]: b["balance"] for b in tools.get_balances(conn)}
        assert bals["Ramesh"] == 360  # 320+240-200, computed by SQL
    finally:
        conn.close()


def test_list_overdue_and_search():
    db.init_db()
    conn = db.get_conn()
    try:
        tools.add_entry(conn, "Old", 100, "credit", "atta", "2020-01-01")
        over = tools.list_overdue(conn, 7)
        assert any(o["customer"] == "Old" for o in over)
        hits = tools.search_entries(conn, "atta")
        assert hits and hits[0]["customer"] == "Old"
    finally:
        conn.close()


def test_draft_reminder_never_sends():
    db.init_db()
    conn = db.get_conn()
    try:
        tools.add_entry(conn, "Suresh", 150, "credit", "oil")
        d = tools.draft_reminder(conn, "Suresh", "hi")
        assert d["status"] == "draft"
        row = conn.execute("SELECT status FROM reminders WHERE id=?", (d["id"],)).fetchone()
        assert row["status"] == "draft"
    finally:
        conn.close()


def test_audit_log_records_tool_calls():
    db.init_db()
    conn = db.get_conn()
    try:
        tools.get_balances(conn)
        n = conn.execute("SELECT COUNT(*) c FROM audit_log WHERE action='get_balances'").fetchone()["c"]
        assert n >= 1
    finally:
        conn.close()
