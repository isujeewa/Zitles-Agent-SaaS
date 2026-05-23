# Zitles Report Tools

Source code for generating Zitles-branded title documents.

## What's here

### `chain-sheets/`
Generates **Chain of Title flowchart PDFs** from JSON data.
- `generate.py` — CLI entry point (`from-json` subcommand)
- `schema.py` — `ChainData` / `ChainLink` dataclasses
- `renderer.py` — Renders `templates/chain.html` via pdfkit
- `extract_chain.py`, `ocr_deeds.py`, `ocr_pipeline.py` — OCR helpers to pull chain data from deed PDFs
- `templates/` — HTML + CSS
- `assets/logo.png` — Zitles logo
- `samples/data-*.json` — Two sample input files

### `title-summary-reports/`
Generates **Title Summary Reports** and **Draft Title Commitments**.

Title summary reports:
- `generate.py` — CLI (`from-text`, `from-json`, `list`, `regenerate`, `export-json`)
- `schema.py` — Data models with `to_dict()` / `from_dict()`
- `renderer.py` — Renders `report.html` + conditional `appendix.html` / `liens-detail.html`
- `parser.py` — Text-file parser (not used in JSON workflow)

Draft commitments (three flavors, depending on underwriter):
- `gen_commitment.py` — Zitles generic
- `gen_alta_commitment.py` — ALTA-format
- `gen_fa_commitment.py` — First American format
- `generate_commitment.py` — Older entry point
- `commit_*.py` — One-off per-property scripts (reference only)
- `templates/commitment.html`, `templates/footer.html`

Other:
- `archive.py` — Moves completed reports out of working set
- `assets/` — Zitles, ALTA, First American logos
- `samples/` — One sample of each input type

## Stack

- Python 3
- Jinja2
- pdfkit (wraps `wkhtmltopdf` — must be installed separately: `brew install wkhtmltopdf` on macOS)
- `python-docx` for `.docx` commitments

Use `python3` (not `python`) to invoke the scripts.

## wkhtmltopdf gotcha

`wkhtmltopdf` ships an old WebKit (~2012). **No flexbox, no grid** — templates use float-based layouts. Don't refactor to modern CSS or PDFs will break.

## Quick test

```bash
cd chain-sheets
python3 generate.py from-json samples/data-535-05-00-061.json --output test-chain.pdf

cd ../title-summary-reports
python3 generate.py from-json samples/data-2026-040.json --output test-summary.pdf
```
