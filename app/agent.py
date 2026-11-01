"""Agent loop: Muse Spark + tools, max 6 iterations.

Offline (no API key): keyword routing in Hindi/Hinglish/English/Telugu
that calls the same tools, so the demo works without network.
"""
from __future__ import annotations

import json
import sqlite3

from . import db, lang, meta_client, tools

SYSTEM = (
    "You are Dukaan Saathi, a helper for Indian small shopkeepers. "
    "Always reply in the user's language and script "
    "(Telugu script for Telugu, Devanagari for Hindi, Roman for Hinglish/English). "
    "Use tools for all numbers; never invent balances. "
    "draft_reminder only saves drafts; tell the user to approve them. "
    "Never claim a message was sent."
)

MAX_ITERS = 6


def _dispatch(conn: sqlite3.Connection, name: str, args: dict):
    if name == "get_balances":
        return tools.get_balances(conn, args.get("customer"))
    if name == "list_overdue":
        return tools.list_overdue(conn, int(args.get("days", 7)))
    if name == "search_entries":
        return tools.search_entries(conn, args.get("query", ""),
                                    args.get("date_from", ""), args.get("date_to", ""))
    if name == "restock_suggestions":
        return tools.restock_suggestions(conn, int(args.get("period_days", 30)))
    if name == "draft_reminder":
        return tools.draft_reminder(conn, args["customer"], args.get("language", "hi"))
    if name == "add_entry":
        return tools.add_entry(conn, args["customer"], float(args["amount"]),
                               args["kind"], args.get("description", ""),
                               args.get("date", ""))
    raise ValueError(f"unknown tool: {name}")


def _offline_answer(conn: sqlite3.Connection, text: str, reply_lang: str) -> dict:
    t = text.lower()
    calls: list[dict] = []
    if lang.has_word(t, lang.REMINDER_WORDS):
        overdue = tools.list_overdue(conn, 0)
        calls.append({"tool": "list_overdue", "result": overdue})
        drafts = []
        rlang = lang.reminder_lang(reply_lang)
        for c in overdue:
            try:
                drafts.append(tools.draft_reminder(conn, c["customer"], rlang))
            except ValueError:
                pass
        calls.append({"tool": "draft_reminder", "result": drafts})
        if drafts:
            names = ", ".join(d["customer"] for d in drafts)
            reply = lang.fmt(reply_lang, "reminders_made", n=len(drafts), names=names)
        else:
            reply = lang.fmt(reply_lang, "no_dues")
        return {"answer": reply, "tool_calls": calls, "language": reply_lang}
    if lang.has_word(t, lang.RESTOCK_WORDS):
        rows = tools.restock_suggestions(conn)
        calls.append({"tool": "restock_suggestions", "result": rows})
        if rows:
            top = ", ".join(lang.fmt(reply_lang, "item_times", item=r["item"], n=r["times"])
                            for r in rows[:5])
            return {"answer": lang.fmt(reply_lang, "restock_top", items=top),
                    "tool_calls": calls, "language": reply_lang}
        return {"answer": lang.fmt(reply_lang, "restock_none"),
                "tool_calls": calls, "language": reply_lang}
    # default: balances
    bals = tools.get_balances(conn)
    calls.append({"tool": "get_balances", "result": bals})
    if not bals:
        return {"answer": lang.fmt(reply_lang, "balances_empty"),
                "tool_calls": calls, "language": reply_lang}
    top = bals[0]
    lines = [lang.fmt(reply_lang, "line", name=b["customer"], amt=lang.inr(b["balance"]))
             for b in bals[:10]]
    reply = lang.fmt(reply_lang, "balances_top", name=top["customer"],
                     amt=lang.inr(top["balance"]), lines="\n".join(lines))
    return {"answer": reply, "tool_calls": calls, "language": reply_lang}


def run_agent(conn: sqlite3.Connection, user_text: str,
              history: list[dict] | None = None, language: str = "auto") -> dict:
    """Run one user turn. Returns {answer, tool_calls, language}."""
    history = history or []
    reply_lang = lang.detect(user_text, language)
    if meta_client.mock_mode():
        out = _offline_answer(conn, user_text, reply_lang)
        db.audit(conn, "agent", "answer",
                 {"mode": "offline", "lang": reply_lang, "q": user_text[:200]})
        conn.commit()
        return out
    sys = SYSTEM + f" Reply language for this turn: {reply_lang}."
    messages = [{"role": "system", "content": sys}] + history[-10:] + [
        {"role": "user", "content": user_text}]
    tool_defs = [{"type": "function", **s} for s in tools.TOOL_SPECS]
    prev: str | None = None
    calls_log: list[dict] = []
    for _ in range(MAX_ITERS):
        turn = meta_client.agent_turn(messages, tool_defs, prev)
        prev = turn.get("response_id") or prev
        if not turn["tool_calls"]:
            db.audit(conn, "agent", "answer",
                     {"mode": "live", "lang": reply_lang, "q": user_text[:200]})
            conn.commit()
            return {"answer": turn["text"], "tool_calls": calls_log,
                    "language": reply_lang}
        for tc in turn["tool_calls"]:
            args: dict = {}
            try:
                args = json.loads(tc.get("arguments", "{}"))
                result = _dispatch(conn, tc["name"], args)
            except Exception as e:  # noqa: BLE001 - report tool errors to model
                result = {"error": str(e)}
            calls_log.append({"tool": tc["name"], "args": args, "result": result})
            messages.append({"role": "tool", "call_id": tc.get("call_id", ""),
                             "content": json.dumps(result, ensure_ascii=False)})
    return {"answer": "Kaam adhura reh gaya (6 steps se zyada). Kripya chhota sawal poochhein.",
            "tool_calls": calls_log, "language": reply_lang}
