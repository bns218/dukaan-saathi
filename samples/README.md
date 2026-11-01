# Samples

20 synthetic ledger pages with ground truth (248 rows):

- `ledger_001.jpg` … `ledger_020.jpg` — ledger photos
- `ledger_001.json` … — expected rows (`{image, page, rows, ignored_rows}`)
- `manifest.json` — per-page language (te/hi/en/mixed) and difficulty
  (clean/normal/hard)

Score extraction with a real key (optional filter by language/difficulty):

```
META_API_KEY=... python tests/eval_extract.py
META_API_KEY=... python tests/eval_extract.py te
META_API_KEY=... python tests/eval_extract.py hard
```

Goal (Fri 30 Oct milestone): per-field accuracy from this set in the README.
`ignored_rows` lists crossed-out rows the model must NOT extract.
