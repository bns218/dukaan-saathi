"""Audio -> mono 16 kHz PCM -> transcript."""
from __future__ import annotations

import shutil
import subprocess
import tempfile
from pathlib import Path

from . import meta_client


def to_mono_16k(raw: bytes, suffix: str = ".webm") -> bytes:
    """Convert any ffmpeg-readable audio to mono 16 kHz PCM s16le.

    Falls back to the raw bytes when ffmpeg is unavailable.
    """
    if shutil.which("ffmpeg") is None:
        return raw
    with tempfile.TemporaryDirectory() as td:
        src = Path(td) / f"in{suffix}"
        dst = Path(td) / "out.pcm"
        src.write_bytes(raw)
        try:
            subprocess.run(
                ["ffmpeg", "-y", "-i", str(src), "-ac", "1", "-ar", "16000",
                 "-f", "s16le", str(dst)],
                check=True, capture_output=True, timeout=30,
            )
            return dst.read_bytes()
        except Exception:
            return raw


def transcribe_audio(raw: bytes, language: str = "hi", suffix: str = ".webm") -> str:
    pcm = to_mono_16k(raw, suffix)
    return meta_client.transcribe(pcm, language=language)
