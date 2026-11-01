"""All Meta Model API calls go through this module.

Uses the OpenAI-compatible endpoint at META_BASE_URL (default
https://api.meta.ai/v1). When META_API_KEY is missing or MOCK_META=1,
deterministic offline mocks are returned so the app and tests run
without network access.
"""
from __future__ import annotations

import base64
import json
import os

import httpx

BASE_URL = os.environ.get("META_BASE_URL", "https://api.meta.ai/v1")
VISION_MODEL = os.environ.get("META_VISION_MODEL", "muse-spark-1.3")
AGENT_MODEL = os.environ.get("META_AGENT_MODEL", "muse-spark-1.3")
TRANSCRIBE_MODEL = os.environ.get("META_TRANSCRIBE_MODEL", "muse-voice-transcribe-1")


def mock_mode() -> bool:
    return os.environ.get("MOCK_META", "0") == "1" or not os.environ.get("META_API_KEY")


def _headers() -> dict:
    return {
        "Authorization": f"Bearer {os.environ.get('META_API_KEY', '')}",
        "Content-Type": "application/json",
    }


def vision_extract(image_bytes: bytes, prompt: str, retries: int = 1) -> str:
    """Send a ledger photo to Muse Spark vision, return raw text (JSON)."""
    if mock_mode():
        return json.dumps(
            {
                "rows": [
                    {
                        "customer": "Ramesh",
                        "description": "rice 5kg",
                        "amount": 320,
                        "kind": "credit",
                        "date": "2026-10-28",
                        "confidence": 0.9,
                    }
                ]
            }
        )
    data_url = "data:image/jpeg;base64," + base64.b64encode(image_bytes).decode()
    body = {
        "model": VISION_MODEL,
        "messages": [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {"type": "image_url", "image_url": {"url": data_url}},
                ],
            }
        ],
        "max_tokens": 6000,
        "response_format": {"type": "json_object"},
    }
    last_err = ""
    for _ in range(retries + 1):
        try:
            r = httpx.post(
                f"{BASE_URL}/chat/completions", headers=_headers(),
                json=body, timeout=90,
            )
            r.raise_for_status()
            content = r.json()["choices"][0]["message"].get("content") or ""
            if not content.strip():
                raise RuntimeError("empty model response (truncated?)")
            return content
        except Exception as e:  # noqa: BLE001 - retry then surface
            last_err = str(e)
    raise RuntimeError(f"vision_extract failed: {last_err}")


def transcribe(pcm_bytes: bytes, language: str = "hi") -> str:
    """Transcribe mono 16 kHz PCM audio. Returns transcript text."""
    if mock_mode():
        return "sabse zyada udhaar kiska hai"
    files = {"file": ("audio.pcm", pcm_bytes, "audio/pcm")}
    data = {"model": TRANSCRIBE_MODEL, "language": language}
    headers = {"Authorization": f"Bearer {os.environ.get('META_API_KEY', '')}"}
    r = httpx.post(
        f"{BASE_URL}/audio/transcriptions", headers=headers,
        data=data, files=files, timeout=60,
    )
    r.raise_for_status()
    return r.json().get("text", "")


def agent_turn(
    messages: list[dict], tools: list[dict], previous_response_id: str | None = None
) -> dict:
    """One Responses-API turn. Returns dict with text, tool_calls, response_id.

    In mock mode returns a plain-text reply so the offline agent path in
    agent.py (keyword routing) is used instead; main agent loop checks
    mock_mode() first and never calls this.
    """
    if mock_mode():
        return {"text": "", "tool_calls": [], "response_id": "mock-0"}
    body: dict = {"model": AGENT_MODEL, "input": messages, "tools": tools}
    if previous_response_id:
        body["previous_response_id"] = previous_response_id
    r = httpx.post(
        f"{BASE_URL}/responses", headers=_headers(), json=body, timeout=60
    )
    r.raise_for_status()
    data = r.json()
    text_parts: list[str] = []
    tool_calls: list[dict] = []
    for item in data.get("output", []):
        if item.get("type") == "message":
            for c in item.get("content", []):
                if c.get("type") == "output_text":
                    text_parts.append(c.get("text", ""))
        elif item.get("type") == "function_call":
            tool_calls.append(
                {
                    "call_id": item.get("call_id", ""),
                    "name": item.get("name", ""),
                    "arguments": item.get("arguments", "{}"),
                }
            )
    return {
        "text": "\n".join(text_parts),
        "tool_calls": tool_calls,
        "response_id": data.get("id", ""),
    }
