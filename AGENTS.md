# AGENTS.md — Dukaan Saathi

Build for the Meta Global AI Developer Hackathon (Indie track).
Due Thu 5 Nov 2026, 7:30 AM IST. Demo must show only work built during the event.

## Stack

- Backend: FastAPI + SQLite (`app/`), balances computed in SQL only.
- Frontend: vanilla `web/index.html` + `web/app.js`, mobile-first.
- Models: all Meta calls go through `app/meta_client.py` (OpenAI-compatible,
  base `https://api.meta.ai/v1`). Model ids from env, never hardcoded elsewhere.
- Set `MOCK_META=1` (or omit `META_API_KEY`) for deterministic offline mocks.

## Rules

- Extracted rows are drafts until the user confirms via `POST /api/ledger/commit`.
- Reminders are drafts until approved; the app never sends anything itself.
- Every tool call and user action writes to `audit_log`.
- Validate model output with Pydantic; retry once, then return an error.
- No secrets in code, skills, or commits. No vector DB; memory is last-N
  messages + a short shop summary in the system prompt.
- Balances: `SUM(credit) - SUM(payment)` per customer, computed in SQL.
