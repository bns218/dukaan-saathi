"""FastAPI backend. Serves API + the web/ single-page UI."""
from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

load_dotenv()

from . import agent, db, extract, tools, voice  # noqa: E402

app = FastAPI(title="Dukaan Saathi")
db.init_db()

WEB_DIR = Path(__file__).resolve().parent.parent / "web"
if WEB_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(WEB_DIR)), name="static")


@app.get("/")
def index():
    return FileResponse(str(WEB_DIR / "index.html"))


class CommitRow(BaseModel):
    customer: str
    description: str = ""
    amount: float
    kind: str
    date: str = ""
    confidence: float = 0.0


class CommitRequest(BaseModel):
    rows: list[CommitRow]
    source_image: str = ""


class ChatRequest(BaseModel):
    message: str
    history: list[dict] = []
    language: str = "auto"


@app.post("/api/ledger/extract")
async def ledger_extract(photo: UploadFile = File(...)):
    data = await photo.read()
    if not data:
        raise HTTPException(400, "empty photo")
    try:
        draft = extract.extract_draft(data)
    except ValueError as e:
        raise HTTPException(502, str(e)) from e
    conn = db.get_conn()
    try:
        db.audit(conn, "user", "ledger_extract",
                 {"filename": photo.filename, "rows": len(draft.rows)})
        conn.commit()
    finally:
        conn.close()
    return {"rows": [r.model_dump() for r in draft.rows]}


@app.post("/api/ledger/commit")
def ledger_commit(req: CommitRequest):
    conn = db.get_conn()
    try:
        saved = []
        for r in req.rows:
            if r.kind not in ("credit", "payment"):
                raise HTTPException(400, f"bad kind: {r.kind}")
            saved.append(tools.add_entry(conn, r.customer, r.amount, r.kind,
                                         r.description, r.date))
        db.audit(conn, "user", "ledger_commit", {"rows": len(saved)})
        conn.commit()
        return {"saved": saved}
    finally:
        conn.close()


@app.post("/api/voice/ask")
async def voice_ask(audio: UploadFile = File(...), language: str = Form("hi")):
    data = await audio.read()
    if not data:
        raise HTTPException(400, "empty audio")
    suffix = Path(audio.filename or "audio.webm").suffix or ".webm"
    hint = language if language in ("hi", "te", "en") else "hi"
    try:
        transcript = voice.transcribe_audio(data, language=hint, suffix=suffix)
    except Exception as e:  # noqa: BLE001
        raise HTTPException(502, f"transcription failed: {e}") from e
    conn = db.get_conn()
    try:
        out = agent.run_agent(conn, transcript, language=language)
        return {"transcript": transcript, **out}
    finally:
        conn.close()


@app.post("/api/chat")
def chat(req: ChatRequest):
    if not req.message.strip():
        raise HTTPException(400, "empty message")
    conn = db.get_conn()
    try:
        return agent.run_agent(conn, req.message, req.history, req.language)
    finally:
        conn.close()


@app.get("/api/customers")
def customers():
    conn = db.get_conn()
    try:
        return {"customers": tools.get_balances(conn)}
    finally:
        conn.close()


@app.get("/api/reminders")
def reminders():
    conn = db.get_conn()
    try:
        rows = conn.execute(
            """SELECT r.id, c.name AS customer, r.draft_text, r.language,
                      r.status, r.created_at FROM reminders r
               JOIN customers c ON c.id=r.customer_id
               ORDER BY r.id DESC LIMIT 50""").fetchall()
        return {"reminders": [dict(r) for r in rows]}
    finally:
        conn.close()


@app.post("/api/reminders/{rid}/approve")
def approve_reminder(rid: int):
    conn = db.get_conn()
    try:
        cur = conn.execute("UPDATE reminders SET status='approved' WHERE id=? AND status='draft'",
                           (rid,))
        if cur.rowcount == 0:
            raise HTTPException(404, "draft not found")
        db.audit(conn, "user", "reminder_approve", {"id": rid})
        conn.commit()
        return {"id": rid, "status": "approved"}
    finally:
        conn.close()


@app.get("/api/report/weekly")
def weekly():
    conn = db.get_conn()
    try:
        bals = tools.get_balances(conn)
        total = round(sum(b["balance"] for b in bals), 2)
        top = conn.execute(
            """SELECT description AS item, COUNT(*) AS times FROM entries
               WHERE kind='credit' AND description != ''
               GROUP BY description ORDER BY times DESC LIMIT 5""").fetchall()
        return {"total_outstanding": total, "balances": bals,
                "top_items": [dict(r) for r in top]}
    finally:
        conn.close()


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=int(os.environ.get("PORT", "8000")))
