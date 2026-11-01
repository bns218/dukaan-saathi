"""API end-to-end over the mock backend."""
from fastapi.testclient import TestClient

from app import db
from app.main import app

client = TestClient(app)


def test_extract_commit_flow():
    db.init_db()
    r = client.post("/api/ledger/extract", files={"photo": ("page.jpg", b"fake-bytes", "image/jpeg")})
    assert r.status_code == 200
    rows = r.json()["rows"]
    assert rows and rows[0]["customer"] == "Ramesh"  # mock extraction
    # nothing saved yet: draft-only
    assert client.get("/api/customers").json()["customers"] == []
    r2 = client.post("/api/ledger/commit", json={"rows": rows})
    assert r2.status_code == 200 and len(r2.json()["saved"]) == len(rows)
    bals = client.get("/api/customers").json()["customers"]
    assert bals[0]["balance"] == 320


def test_chat_and_voice_and_approvals():
    db.init_db()
    client.post("/api/ledger/commit", json={"rows": [
        {"customer": "Ramesh", "description": "rice", "amount": 600, "kind": "credit", "date": "2020-01-01"}]})
    r = client.post("/api/chat", json={"message": "remind everyone"})
    assert r.status_code == 200 and "approval" in r.json()["answer"].lower()
    drafts = client.get("/api/reminders").json()["reminders"]
    assert drafts and drafts[0]["status"] == "draft"
    rid = drafts[0]["id"]
    assert client.post(f"/api/reminders/{rid}/approve").json()["status"] == "approved"
    rv = client.post("/api/voice/ask", files={"audio": ("q.webm", b"fake-audio", "audio/webm")},
                     data={"language": "hi"})
    assert rv.status_code == 200 and rv.json()["transcript"]
    w = client.get("/api/report/weekly").json()
    assert w["total_outstanding"] == 600
