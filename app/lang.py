"""Language detection + localized agent replies (Telugu/Hindi/English/Hinglish).

Codes: te = Telugu script, hi = Devanagari Hindi, en = English,
hinglish = Roman-script default (existing behavior, unchanged).
"""
from __future__ import annotations

import re

T = {
    "hinglish": {
        "reminders_made": ("Maine {n} reminder draft banaye hain ({names}). "
                           "Approval screen me check karke approve karein — "
                           "kuch bhi bina approval nahi bheja jayega."),
        "no_dues": "Koi udhaar baki nahi hai. Sab hisaab clear hai!",
        "restock_top": "Is mahine sabse zyada bike: {items}.",
        "restock_none": "Abhi stock suggest karne ke liye kaafi record nahi hai.",
        "balances_top": "Sabse zyada udhaar {name} ka hai: Rs {amt}.\n{lines}",
        "balances_empty": "Abhi koi udhaar record nahi hai.",
        "line": "{name}: Rs {amt}",
        "item_times": "{item} ({n} baar)",
    },
    "hi": {
        "reminders_made": ("मैंने {n} रिमाइंडर ड्राफ्ट बनाए हैं ({names})। "
                           "Approval स्क्रीन में देखकर approve करें — "
                           "बिना approval कुछ नहीं भेजा जाएगा।"),
        "no_dues": "कोई उधार बाकी नहीं है। सब हिसाब क्लियर है!",
        "restock_top": "इस महीने सबसे ज़्यादा बिके: {items}।",
        "restock_none": "स्टॉक सुझाने के लिए अभी काफ़ी रिकॉर्ड नहीं है।",
        "balances_top": "सबसे ज़्यादा उधार {name} का है: ₹{amt}।\n{lines}",
        "balances_empty": "अभी कोई उधार रिकॉर्ड नहीं है।",
        "line": "{name}: ₹{amt}",
        "item_times": "{item} ({n} बार)",
    },
    "te": {
        "reminders_made": ("నేను {n} రిమైండర్ డ్రాఫ్ట్‌లు తయారు చేశాను ({names})। "
                           "Approval స్క్రీన్‌లో చూసి approve చేయండి — "
                           "approval లేకుండా ఏమీ పంపబడదు।"),
        "no_dues": "ఎలాంటి అప్పు మిగిలి లేదు. లెక్క అంతా క్లియర్!",
        "restock_top": "ఈ నెలలో బాగా అమ్ముడైనవి: {items}।",
        "restock_none": "స్టాక్ సూచించడానికి ఇంకా తగిన రికార్డు లేదు.",
        "balances_top": "అందరికంటే ఎక్కువ అప్పు {name} ది: ₹{amt}।\n{lines}",
        "balances_empty": "ప్రస్తుతం అప్పు రికార్డు ఏదీ లేదు.",
        "line": "{name}: ₹{amt}",
        "item_times": "{item} ({n} సార్లు)",
    },
    "en": {
        "reminders_made": ("I made {n} reminder drafts ({names}). "
                           "Please review and approve them on the approval screen — "
                           "nothing is sent without approval."),
        "no_dues": "Nobody owes anything. All accounts are clear!",
        "restock_top": "Top sellers this month: {items}.",
        "restock_none": "Not enough records yet to suggest stock.",
        "balances_top": "{name} owes the most: Rs {amt}.\n{lines}",
        "balances_empty": "No credit records yet.",
        "line": "{name}: Rs {amt}",
        "item_times": "{item} ({n}x)",
    },
}

REMINDER_WORDS = ("remind", "reminder", "yaad", "takaza", "message", "sms",
                  "रिमाइंडर", "याद", "संदेश", "రిమైండర్", "గుర్తు", "సందేశం")
RESTOCK_WORDS = ("stock", "restock", "maal", "samaan", "order",
                 "स्टॉक", "सामान", "స్టాక్", "సరుకు")
TELUGU_HINTS = ("telugu", "garu", "enti", "chepp", "bakayi", "dabbulu")


def has_word(text: str, words: tuple[str, ...]) -> bool:
    """Token match (exact or prefix) — avoids 'याद' matching inside 'ज्यादा'."""
    toks = re.findall(r"[^\s,.!?;:()\"'।॥]+", text.lower())
    return any(t == w or t.startswith(w) for t in toks for w in words)


def detect(text: str, hint: str = "auto") -> str:
    """Return reply language code. Explicit hint wins; else script/keywords."""
    if hint in T:
        return hint
    if any("\u0c00" <= c <= "\u0c7f" for c in text):
        return "te"
    if any("\u0900" <= c <= "\u097f" for c in text):
        return "hi"
    if has_word(text, TELUGU_HINTS):
        return "te"
    return "hinglish"


def reminder_lang(reply_lang: str) -> str:
    """Map a reply language to a reminder-draft language (hi/te/en only)."""
    return {"te": "te", "en": "en"}.get(reply_lang, "hi")


def fmt(lang: str, key: str, **kw) -> str:
    return T[lang][key].format(**kw)


def inr(amount: float) -> str:
    return f"{amount:,.0f}"
