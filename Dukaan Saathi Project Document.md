# Dukaan Saathi: Project Document

Oct 30, 2026 · @Naga

Dukaan Saathi is an AI assistant that turns a small shopkeeper's handwritten ledger photos and spoken questions into reliable records and actions. It is our entry for the Meta Global AI Developer Hackathon (theme: Build for Your World, track: Indie), due Thu 5 Nov 2026, 7:30 AM IST.

## Overview

**Problem.** Millions of small shops in India run on handwritten ledgers and memory. Existing shop apps assume English, typing and clean data, so these shopkeepers are left out.

**What it does.**

- Reads a photo of a ledger page and extracts customers, items and amounts as draft rows.
- Shows the draft next to the photo; the shopkeeper corrects it and confirms before anything is saved.
- Answers spoken or typed questions such as "who owes me the most this month?" using SQL-backed numbers.
- Acts as an agent: finds overdue customers, drafts reminder messages in Hindi or Telugu, and suggests restocks. Nothing is sent without approval.

**Why it is more than an image analyzer.** The hackathon guide lists simple image analyzers as a generic project to avoid. The differentiator is the agent layer: multi-step workflows, a verify-before-save step, and an audit log.

## Hackathon fit

Judges score four equally weighted criteria from 0 to 10, so the project is planned to earn points on each one.

| Criterion | What judges ask | Our answer |
| --- | --- | --- |
| Impact | Real-world potential; fits a problem statement | Shopkeepers who cannot use English-first software; Build for Your World |
| Use of Meta AI tooling | Beyond a basic integration | Muse Spark (vision, agent tools), Muse Voice Transcribe, optional SAM 3.1 and Muse Image; built with Muse Code |
| Technical depth and execution | Sound engineering, real craft | Schema-validated extraction, SQL-computed balances, tool loop, audit log, accuracy measured on samples |
| Demo | Working, impressive, fun to watch | 3-minute video: photo, confirm, voice command, multi-step agent action |

**Rules to respect**

- Repository must be public; the demo may show only work built during the event, so start a new repo and commit often.
- Submit a 3-minute demo video through the Cerebral Valley platform; everyone on the project must be listed.
- Avoid banned or generic ideas: medical advice, basic RAG apps, simple image analyzers, AI education chatbots, anything political or about war.
- Claim your own $150 Meta Model API credits by Wed 4 Nov, 9:00 PM ET; a card on the account is needed to use them.

**Prizes in reach.** Indie track places pay from $25K to $150K. Bonus prizes we can plausibly target: Best Agentic Use-Case ($5K), Best Creative Build with Muse Image ($5K), Best Build on Meta Open Weight Models ($10K), and Community Vote ($10K).

## Architecture

&#91;embedded content: architecture · 4 layers\]

Photo and voice requests enter one FastAPI backend, which calls Meta models for vision, speech and reasoning and stores confirmed data in SQLite. The highlighted agent loop is the differentiator; SAM 3.1 and Muse Image are optional.

**Three main flows**

1. Photo to rows: upload, extract with Muse Spark (SAM 3.1 first if it helps), review and confirm, then commit to SQLite.
2. Voice to answer: record, convert with ffmpeg to mono 16 kHz PCM, transcribe, and pass the text to the agent.
3. Agent actions: tools list overdue customers, draft reminders and suggest restocks; the shopkeeper approves each one.

## Data model and API

All balances are computed with SQL, never by the model: credits minus payments per customer. The model chooses which query to run; the database does the arithmetic.

**SQLite tables**

| Table | Key columns |
| --- | --- |
| customers | id, name, phone, created\_at |
| entries | id, customer\_id, date, description, amount, kind (credit or payment), source\_image, confidence, confirmed\_at |
| items | id, name, unit, typical\_qty |
| reminders | id, customer\_id, draft\_text, language, status (draft, approved, sent), created\_at |
| audit\_log | id, ts, actor (user or agent), action, payload\_json |

**Endpoints**

| Endpoint | Purpose |
| --- | --- |
| POST /api/ledger/extract | Photo in, draft rows out (not saved) |
| POST /api/ledger/commit | Confirmed rows saved to SQLite |
| POST /api/voice/ask | Audio in, transcript, agent answer out |
| POST /api/chat | Text question to agent answer |
| GET /api/customers | Customers with balances |
| GET /api/reminders | Drafts waiting for approval |
| POST /api/reminders/{id}/approve | Approve a drafted reminder |
| GET /api/report/weekly | Weekly summary, optional poster |

**Repo layout**

```
dukaan-saathi/
  app/   main.py, meta_client.py, extract.py, voice.py, agent.py, tools.py, db.py
  web/   index.html, app.js
  samples/  synthetic ledger photos + expected JSON
  tests/    extraction accuracy checks
  AGENTS.md, README.md, .env.example
```

All Meta API calls go through `meta_client.py`, so model ids change in one place.

## Agent design

The agent is Muse Spark called through the OpenAI-compatible Responses API at `https://api.meta.ai/v1`, with tools it can call. Anything that changes records needs the shopkeeper's confirmation.

| Tool | What it does | Risk |
| --- | --- | --- |
| get\_balances(customer?) | Balances computed in SQL | Read-only |
| list\_overdue(days) | Customers unpaid past N days | Read-only |
| search\_entries(query, date\_range) | Finds past entries | Read-only |
| restock\_suggestions(period) | Frequent items from history | Read-only |
| draft\_reminder(customer, language) | Saves a reminder draft | Writes a draft only |
| add\_entry(...) | Adds a record | Needs confirmation |

**Loop.** Send the user message and tool definitions, run any tool calls the model returns, send results back with `previous_response_id`, and repeat until the model replies in text. Cap at 6 iterations.

**Safety rules**

- Extracted ledger rows are drafts until the shopkeeper confirms them.
- Reminders are drafts until approved; the app never sends anything by itself.
- Every tool call and user action is written to `audit_log`.
- Output is validated with Pydantic; invalid JSON is retried once, then reported as an error.
- Conversation memory is the last N messages plus a short shop summary in the system prompt; no vector database needed.

## Build plan

&#91;embedded content: build plan · 7 days + deadline\]

Each day has a done-when check; if one fails, cut optional features rather than slipping the schedule. Tuesday 3 Nov is the last full day for submission questions in Discord.

| Day (IST) | Done when |
| --- | --- |
| Thu 29 Oct | One image call, one transcription and the sample set work; first commit is pushed |
| Fri 30 Oct | Extraction accuracy on 10 samples is measured and written in the README |
| Sat 31 Oct | A text question returns an answer that matches a manual SQL check |
| Sun 1 Nov | On a phone: photo, confirm rows, spoken question, answer |
| Mon 2 Nov | One voice command runs a multi-step workflow with an approval screen |
| Tue 3 Nov | A stranger completes the flow on the deployed link without help |
| Wed 4 Nov | Video uploaded, repo public, submitted with buffer before the deadline |

## Building with Muse Code

Muse Code is Meta's terminal coding agent (beta). It reads project instructions from `AGENTS.md`, loads skills from `.agents/skills/<skill-id>/SKILL.md`, and can run several subagents, with write-capable ones in isolated git worktrees. Check dev.meta.ai/docs/muse-code for current syntax, since the tool is in beta.

**Setup.** Install with `curl -fsSL https://dev.meta.ai/install.sh | bash` (macOS or Linux; use WSL on Windows), then sign in with `muse login` or set `META_API_KEY`.

**Project skills to create**

| Skill | Purpose |
| --- | --- |
| extraction-eval | Run all sample ledger photos, print per-field accuracy, suggest prompt fixes |
| add-agent-tool | Create a tool with JSON spec, function, unit test and audit-log entry |
| seed-demo-data | Fill SQLite with consistent demo customers and entries |
| submission-check | Verify public repo, README, no secrets, working video link |

**Workflow.** Use `/plan` per feature and `/grill` to stress-test it before approving. Use `/goal` with a testable target, such as extraction accuracy on `samples/`. Fan out subagents for independent parts (backend API, web UI, tests, docs) and merge each worktree once its tests pass.

**Cautions**

- Review every plan and diff; judges grade our engineering, and the new-work rule needs a clear commit history.
- Never run with `--yolo` on code we did not write.
- Keep API keys out of `AGENTS.md`, skills and commits.
- Mention Muse Code in the README and demo video as part of the Meta tooling used.

## Demo and submission

The demo video must be 3 minutes and show only what we built during the hackathon. It is a main artifact judges use.

**Demo script**

1. 0:00-0:20: the problem, a messy handwritten ledger and a busy shopkeeper.
2. 0:20-1:10: photograph the page, review the extracted rows, confirm.
3. 1:10-2:10: speak a command; the agent runs a multi-step action (for example, remind everyone who owes more than 500 rupees).
4. 2:10-2:40: approval screen for reminders, then the weekly summary.
5. 2:40-3:00: Meta models used, Muse Code, and impact.

**Submission checklist**

- [ ] Repository is public, has no secrets in history, and has a complete README
- [ ] README states what was built during the hackathon and reports extraction accuracy
- [ ] Demo video is uploaded and opens while logged out
- [ ] Deployed link works on a phone over mobile data
- [ ] $150 Meta Model API credits claimed (by Wed 4 Nov, 9:00 PM ET)
- [ ] Everyone who worked on the project is listed on the submission page
- [ ] Submitted on the Cerebral Valley platform with time to spare before Thu 5 Nov, 7:30 AM IST
- [ ] Optional: demo posted on X and the link submitted for the Most Viral Project bonus

## Risks and open questions

The biggest risks are handwriting accuracy and Hindi or Telugu voice quality, and both are tested in the first two days with a fallback ready.

| Risk | Fallback |
| --- | --- |
| Handwriting extraction is weak | Use clearer, higher-resolution photos; restrict to printed bills plus voice; show the confirm step as a feature |
| Hindi or Telugu transcription is poor | Demo in English or Hinglish; put the effort into the agent |
| SAM 3.1 or Muse Image not working quickly | Cut both; they are optional (stop after 2 hours) |
| Meta API failure during recording | Cache extraction results for demo files; keep seeded data and a fallback transcript |
| Running out of time | Cut order: Muse Image, SAM 3.1, Telugu, voice output; protect the end-to-end flow and the demo video |

**Open questions**

- Which Muse Spark model id works on our key (for example muse-spark-1.3)?
- Does Muse Voice Transcribe accept Hindi and Telugu well, and does it take a language hint?
- What are the exact request formats for image input, SAM 3.1 and Muse Image? Check the Model list and Cookbook.
- Are we competing solo or with teammates (maximum 4)? Everyone must be listed on the submission.
