# Dukaan Saathi — दुकान साथी

An AI assistant that turns a small shopkeeper's handwritten ledger photos and
spoken questions into reliable records and actions. Built for the Meta Global
AI Developer Hackathon (Build for Your World, Indie track). Everything in this
repo was built during the hackathon.

## What it does

- **Photo → rows:** snap a bahi-khaata page, review extracted rows, confirm —
  nothing saves before confirmation.
- **Voice/text Q&A in Hindi, Telugu, Hinglish or English:**
  "sabse zyada udhaar kiska hai?" / "ఎవరికి ఎక్కువ అప్పు ఉంది?" —
  auto-detected per message, answered with SQL-computed numbers,
  never model arithmetic.
- **Agent actions:** finds overdue customers, drafts Hindi/Telugu reminders,
  suggests restocks. Drafts need approval; nothing is ever auto-sent.
- **Audit log:** every tool call and user action is recorded.

## Meta tooling

- Muse Spark (vision extraction + agent reasoning) via `https://api.meta.ai/v1`
- Muse Voice Transcribe for spoken questions
- Built with Muse Code

## Quick start

```
python -m venv .venv
.venv\Scripts\activate        # Windows
pip install -r requirements.txt
copy .env.example .env        # add META_API_KEY (or leave empty for offline mock mode)
python -m app.seed            # demo customers + entries
python -m app.main            # open http://127.0.0.1:8000 in a browser
```

No key? The app runs in deterministic mock mode so the full flow
(photo → confirm → voice → approval) works offline for development.

## Extraction accuracy

| Sample set | customer | description | amount | kind | date |
| --- | --- | --- | --- | --- | --- |
| 20 synthetic pages, 248 rows (te/hi/en/mixed; clean/normal/hard), 30 Oct 2026 | 0.996 | 0.986 | 1.0 | 1.0 | 1.0 |

## Layout

```
app/   main.py, meta_client.py, extract.py, voice.py, agent.py, tools.py, db.py, seed.py
web/   index.html, app.js
samples/  ledger photos + expected JSON
tests/    pytest suite + eval_extract.py
```

## API

| Endpoint | Purpose |
| --- | --- |
| POST /api/ledger/extract | Photo in, draft rows out (not saved) |
| POST /api/ledger/commit | Confirmed rows saved to SQLite |
| POST /api/voice/ask | Audio in, transcript + agent answer out |
| POST /api/chat | Text question to agent answer |
| GET /api/customers | Customers with balances |
| GET /api/reminders | Drafts waiting for approval |
| POST /api/reminders/{id}/approve | Approve a drafted reminder |
| GET /api/report/weekly | Weekly summary |
```
