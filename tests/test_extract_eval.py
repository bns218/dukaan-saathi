"""Sample-set integrity (offline): manifest + all ledger JSONs valid.

Vision accuracy itself needs an API key: META_API_KEY=... python tests/eval_extract.py
"""
import json
from pathlib import Path

from app.extract import DraftRow

SAMPLES = Path(__file__).resolve().parent.parent / "samples"


def test_manifest_and_ground_truth_valid():
    manifest = json.loads((SAMPLES / "manifest.json").read_text(encoding="utf-8"))
    assert len(manifest) >= 10, "need at least 10 samples"
    n_rows = 0
    for m in manifest:
        assert (SAMPLES / m["image"]).exists(), f"missing {m['image']}"
        js = SAMPLES / m["image"].replace(".jpg", ".json")
        d = json.loads(js.read_text(encoding="utf-8"))
        assert len(d["rows"]) == m["rows"], f"{js.name} row count vs manifest"
        for r in d["rows"]:
            DraftRow.model_validate({**r, "confidence": 1.0})
        n_rows += len(d["rows"])
    assert n_rows >= 100, "need at least 100 ground-truth rows"
