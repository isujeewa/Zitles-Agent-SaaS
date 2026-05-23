#!/usr/bin/env python3
"""Extract chain-of-title data from OCR'd deeds using Claude Haiku in parallel."""

import json
import os
import sys
import time
import concurrent.futures
from anthropic import Anthropic

MAX_WORKERS = 20

EXTRACTION_PROMPT = """You are analyzing OCR text from a recorded deed. Extract the following fields as JSON:

{
  "grantee": "Full name(s) of grantee(s), include vesting type (JTWROS, etc.)",
  "grantor": "Full name(s) of grantor(s), include entity type if applicable",
  "book": "Book number (e.g., 0555, C391, Z277)",
  "page": "Page number (e.g., 993, 311, 044)",
  "recorded_date": "MM/DD/YYYY or MM/YYYY if day unknown",
  "instrument_type": "Deed, Limited Warranty Deed, Special Warranty Deed, Merger Agreement, Personal Representative's Deed, etc.",
  "parcel_id": "TMS number if present, otherwise empty string",
  "consideration": "Dollar amount or description (e.g., $460,000, $10.00, Stock exchange)",
  "notes": "Key details: derivation clauses (BEING the same property...), subject-to clauses, acreage, special circumstances (interspousal, exempt, trust, estate, merger), lot references, plat references. Be concise but thorough."
}

IMPORTANT:
- Book/page reference is from the recording stamp or header (e.g., BP0555993 = Book 0555 Page 993, or DB Z277 044 = Deed Book Z277 Page 044)
- For old deed books, the bookmark title IS the book/page reference
- Include derivation info from BEING clauses in notes
- For merger documents, the instrument type should be "Merger Agreement"
- Return ONLY valid JSON, no markdown or explanation.

Bookmark reference for this deed: {bookmark}

OCR TEXT:
{text}"""


def extract_deed(args):
    """Extract data from a single deed using Claude Haiku."""
    deed, client = args
    bookmark = deed["title"]
    text = deed["text"]

    # Truncate very long texts (E102 merger is 188K chars)
    if len(text) > 30000:
        # Keep first 15K and last 15K
        text = text[:15000] + "\n\n[...middle pages omitted...]\n\n" + text[-15000:]

    prompt = EXTRACTION_PROMPT.replace("{bookmark}", bookmark).replace("{text}", text)

    for attempt in range(3):
        try:
            response = client.messages.create(
                model="claude-haiku-4-5-20251001",
                max_tokens=1024,
                messages=[{"role": "user", "content": prompt}],
            )
            raw = response.content[0].text.strip()
            # Strip markdown fences if present
            if raw.startswith("```"):
                raw = raw.split("\n", 1)[1].rsplit("```", 1)[0].strip()
            data = json.loads(raw)
            data["_bookmark"] = bookmark
            data["_pages"] = f"{deed['start_page']}-{deed['end_page']}"
            return data
        except Exception as e:
            if attempt < 2:
                time.sleep(2)
            else:
                return {
                    "_bookmark": bookmark,
                    "_pages": f"{deed['start_page']}-{deed['end_page']}",
                    "_error": str(e),
                    "grantee": "", "grantor": "", "book": "", "page": "",
                    "recorded_date": "", "instrument_type": "", "parcel_id": "",
                    "consideration": "", "notes": f"EXTRACTION FAILED: {e}",
                }


def main():
    if len(sys.argv) < 2:
        print("Usage: python extract_chain.py <ocr_deeds.json> [output.json]", flush=True)
        sys.exit(1)

    input_path = sys.argv[1]
    output_path = sys.argv[2] if len(sys.argv) > 2 else input_path.rsplit(".", 1)[0] + "_extracted.json"

    with open(input_path) as f:
        deeds = json.load(f)

    print(f"Extracting chain data from {len(deeds)} deeds with {MAX_WORKERS} parallel workers...", flush=True)

    client = Anthropic()
    t0 = time.time()

    results = []
    done = 0
    with concurrent.futures.ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        futures = {executor.submit(extract_deed, (d, client)): d["title"] for d in deeds}
        for future in concurrent.futures.as_completed(futures):
            result = future.result()
            results.append(result)
            done += 1
            status = "OK" if "_error" not in result else "FAILED"
            print(f"  [{done}/{len(deeds)}] {futures[future]:20s} → {result.get('grantor', '?')[:30]:30s} → {result.get('grantee', '?')[:30]:30s} [{status}]", flush=True)

    # Sort by original order (start page)
    results.sort(key=lambda x: int(x["_pages"].split("-")[0]))

    with open(output_path, "w") as f:
        json.dump(results, f, indent=2)

    elapsed = time.time() - t0
    failed = sum(1 for r in results if "_error" in r)
    print(f"\nDone! {len(results)} deeds extracted in {elapsed:.1f}s", flush=True)
    if failed:
        print(f"  WARNING: {failed} extractions failed", flush=True)
    print(f"Output: {output_path}", flush=True)


if __name__ == "__main__":
    main()
