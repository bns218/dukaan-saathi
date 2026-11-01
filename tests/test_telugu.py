"""Telugu (+ Hindi/English) language support, end to end."""
from fastapi.testclient import TestClient

from app import agent, db, lang, tools
from app.main import app


def test_detect():
    assert lang.detect("ఎవరికి ఎక్కువ అప్పు ఉంది?") == "te"
    assert lang.detect("सबसे ज़्यादा उधार किसका है?") == "hi"
    assert lang.detect("sabse zyada udhaar kiska hai") == "hinglish"
    assert lang.detect("remind in telugu") == "te"
    assert lang.detect("anything", hint="te") == "te"


def test_telugu_balance_answer():
    db.init_db()
    conn = db.get_conn()
    try:
        tools.add_entry(conn, "Ramesh", 500, "credit", "rice")
        out = agent.run_agent(conn, "అందరికంటే ఎక్కువ అప్పు ఎవరిది?")
        assert out["language"] == "te"
        assert "Ramesh" in out["answer"] and "500" in out["answer"]
        assert "అప్పు" in out["answer"]
    finally:
        conn.close()


def test_telugu_reminder_command_makes_telugu_drafts():
    db.init_db()
    conn = db.get_conn()
    try:
        tools.add_entry(conn, "Ramesh", 600, "credit", "rice", "2020-01-01")
        out = agent.run_agent(conn, "అందరికీ రిమైండర్ చేయండి")
        assert out["language"] == "te"
        rows = conn.execute("SELECT language, draft_text, status FROM reminders").fetchall()
        assert rows
        assert all(r["language"] == "te" and r["status"] == "draft" for r in rows)
        assert "బకాయి" in rows[0]["draft_text"]
    finally:
        conn.close()


def test_hindi_and_english_replies():
    db.init_db()
    conn = db.get_conn()
    try:
        tools.add_entry(conn, "Ramesh", 500, "credit", "rice")
        hi = agent.run_agent(conn, "सबसे ज़्यादा उधार किसका है?")
        assert hi["language"] == "hi" and "उधार" in hi["answer"]
        en = agent.run_agent(conn, "hello", language="en")
        assert en["language"] == "en" and "owes the most" in en["answer"]
    finally:
        conn.close()


def test_chat_api_language_param():
    db.init_db()
    client = TestClient(app)
    client.post("/api/ledger/commit", json={"rows": [
        {"customer": "Ramesh", "description": "rice", "amount": 600,
         "kind": "credit", "date": "2020-01-01"}]})
    r = client.post("/api/chat",
                    json={"message": "ఎవరికి ఎక్కువ అప్పు ఉంది?", "language": "auto"})
    assert r.json()["language"] == "te" and "అప్పు" in r.json()["answer"]
