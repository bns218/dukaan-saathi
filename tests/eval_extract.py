"""Run vision extraction over samples/ledger_*.jpg, score vs ledger_*.json.

Usage:  META_API_KEY=... python tests/eval_extract.py [te|hi|en|mixed|clean|normal|hard]
Prints per-field accuracy per file + means overall and by language/difficulty.
Exits nonzero if mean customer recall < 50%.
Ground truth: samples/manifest.json + samples/ledger_NNN.json.
"""
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
os.environ.pop("MOCK_META", None)

from dotenv import load_dotenv  # noqa: E402

load_dotenv()

from app import meta_client  # noqa: E402
from app.extract import extract_draft  # noqa: E402

SAMPLES = Path(__file__).resolve().parent.parent / "samples"
FIELDS = ["customer", "description", "amount", "kind", "date"]


def norm(v) -> str:
    return " ".join(str(v).replace("/-", "").strip().lower().split())


def _eq(field: str, a, b) -> bool:
    if field == "amount":
        try:
            return abs(float(a) - float(b)) < 0.01
        except (TypeError, ValueError):
            return False
    return norm(a) == norm(b)


def score(pred_rows: list[dict], exp_rows: list[dict]) -> dict:
    hit = {f: 0 for f in FIELDS}
    for exp in exp_rows:
        for f in FIELDS:
            if any(_eq(f, p.get(f, ""), exp.get(f, "")) for p in pred_rows):
                hit[f] += 1
    n = max(len(exp_rows), 1)
    return {f: round(hit[f] / n, 3) for f in FIELDS}


def main() -> int:
    if meta_client.mock_mode():
        print("ERROR: no META_API_KEY found — refusing to score mock output.")
        return 3
    only = sys.argv[1] if len(sys.argv) > 1 else ""
    manifest = json.loads((SAMPLES / "manifest.json").read_text(encoding="utf-8"))
    totals: dict[str, list[float]] = {}
    n_files = 0
    for m in manifest:
        if only and only not in (m["language"], m["difficulty"]) and only not in m["image"]:
            continue
        png = SAMPLES / m["image"]
        exp = json.loads((SAMPLES / m["image"].replace(".jpg", ".json")).read_text(encoding="utf-8"))
        exp_rows = exp["rows"]
        try:
            pred = [r.model_dump() for r in extract_draft(png.read_bytes()).rows]
        except Exception as e:  # noqa: BLE001
            print(f"{png.name}: EXTRACTION FAILED: {e}")
            continue
        s = score(pred, exp_rows)
        extra = max(0, len(pred) - len(exp_rows))
        print(f"{png.name} [{m['language']}/{m['difficulty']}]: "
              f"pred={len(pred)} exp={len(exp_rows)} extra={extra} {s}")
        n_files += 1
        for k, v in s.items():
            totals.setdefault(k, []).append(v)
    if not totals:
        print("No samples scored (missing files or filter matched nothing).")
        return 1
    avg = {k: round(sum(v) / len(v), 3) for k, v in totals.items()}
    print(f"MEAN over {n_files} files:", avg)
    if avg.get("customer", 0) < 0.5:
        print("HINT: customer recall low — reshoot blurry pages; add column hints to the prompt.")
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
