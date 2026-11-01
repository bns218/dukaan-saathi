"""Agent offline path: same tools, keyword routing, approval-safe replies."""
from app import agent, db, tools


def test_balance_question_matches_sql():
    db.init_db()
    conn = db.get_conn()
    try:
        tools.add_entry(conn, "Ramesh", 500, "credit", "rice")
        tools.add_entry(conn, "Suresh", 100, "credit", "oil")
        out = agent.run_agent(conn, "who owes me the most?")
        assert "Ramesh" in out["answer"] and "500" in out["answer"]
        assert out["tool_calls"][0]["tool"] == "get_balances"
    finally:
        conn.close()


def test_reminder_command_creates_drafts_only():
    db.init_db()
    conn = db.get_conn()
    try:
        tools.add_entry(conn, "Ramesh", 600, "credit", "rice", "2020-01-01")
        out = agent.run_agent(conn, "sabko reminder banao")
        assert "approval" in out["answer"].lower()
        rows = conn.execute("SELECT status FROM reminders").fetchall()
        assert rows and all(r["status"] == "draft" for r in rows)
    finally:
        conn.close()


def test_live_loop_sends_function_call_output(monkeypatch):
    """Live loop: tool results go back as function_call_output items,
    chained with previous_response_id (Responses API shape)."""
    db.init_db()
    conn = db.get_conn()
    try:
        tools.add_entry(conn, "Ramesh", 500, "credit", "rice")
        calls = []

        def fake_turn(messages, tool_defs, prev=None):
            calls.append((messages, prev))
            if len(calls) == 1:
                return {"text": "", "response_id": "r1", "tool_calls": [
                    {"call_id": "c1", "name": "get_balances", "arguments": "{}"}]}
            return {"text": "Ramesh owes the most: Rs 500.",
                    "tool_calls": [], "response_id": "r2"}

        monkeypatch.setattr(agent.meta_client, "mock_mode", lambda: False)
        monkeypatch.setattr(agent.meta_client, "agent_turn", fake_turn)
        out = agent.run_agent(conn, "who owes me the most?")
        assert "Ramesh" in out["answer"]
        second, prev = calls[1]
        assert prev == "r1"
        assert second[0]["type"] == "function_call_output"
        assert second[0]["call_id"] == "c1"
    finally:
        conn.close()


def test_restock_question():
    db.init_db()
    conn = db.get_conn()
    try:
        tools.add_entry(conn, "A", 50, "credit", "tea 500g")
        tools.add_entry(conn, "B", 50, "credit", "tea 500g")
        out = agent.run_agent(conn, "what stock should I order?")
        assert "tea" in out["answer"].lower()
    finally:
        conn.close()
