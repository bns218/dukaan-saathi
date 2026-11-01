"""Photo -> draft rows. Output validated with Pydantic; never saved here."""
from __future__ import annotations

import json

from pydantic import BaseModel, Field

from . import meta_client

PROMPT = """You read a photo of an Indian small-shop handwritten ledger page.
Return ONLY valid JSON: {"rows": [{"customer": str, "description": str,
"amount": number, "kind": "credit"|"payment", "date": "YYYY-MM-DD",
"confidence": 0-1}]}.
Rules: credit = customer took goods on udhaar (amount in the అప్పు/उधार column);
payment = customer paid back (amount in the జమ/जमा column, description "జమ"/"जम"/"payment" as written).
If a date is missing use the most recent date visible on the page.
Keep customer names and descriptions in their original script exactly as written.
Skip crossed-out rows. No markdown, no commentary."""


class DraftRow(BaseModel):
    customer: str
    description: str = ""
    amount: float
    kind: str = Field(pattern="^(credit|payment)$")
    date: str = ""
    confidence: float = 0.0


class DraftResult(BaseModel):
    rows: list[DraftRow]


def _parse(raw: str) -> DraftResult:
    raw = (raw or "").strip()
    if raw.startswith("```"):
        raw = raw.split("\n", 1)[1].rsplit("```", 1)[0]
    return DraftResult.model_validate(json.loads(raw))


def extract_draft(image_bytes: bytes) -> DraftResult:
    """Return validated draft rows. Retries once on invalid JSON."""
    raw = meta_client.vision_extract(image_bytes, PROMPT)
    try:
        return _parse(raw)
    except Exception:
        raw = meta_client.vision_extract(image_bytes, PROMPT + "\nReturn JSON only.")
        try:
            return _parse(raw)
        except Exception as e:
            raise ValueError(f"model returned invalid extraction JSON: {e}") from e
