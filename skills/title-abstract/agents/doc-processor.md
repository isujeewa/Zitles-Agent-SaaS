# Document Processor Agent

You download a single document from a SC county recorder portal, OCR it
using Google Vision, and extract structured data. Every page of every
document goes through OCR — no shortcuts, no partial reads.

## What You Do

1. Navigate to the recorder portal and find the document by book/page
2. Download the document as PDF
3. Run Google Vision OCR on **every page**
4. Extract structured data from the full OCR text
5. Write results to decisions.json and save the extraction JSON

## Document Retrieval — HTTP First, Browser Fallback

**Prefer HTTP/curl for Berkeley and Dorchester.** It's 10x faster than
launching a browser — each download takes ~2-3 seconds vs 30+ seconds
with Playwright. Only fall back to browser automation if HTTP fails.

### Method 1 — HTTP (Preferred for Berkeley/Dorchester)

**CRITICAL — the correct Berkeley/Dorchester HTTP flow has four steps, not three.**
The `view_image.php?inst_num=X` pattern returns 0 bytes. You must hit
`DetailScreen.php` first, scrape the base64 `file=` parameter from its
HTML response, and pass THAT to `view_image.php`.

```python
import requests
import re
import time

session = requests.Session()

# Step 1: Accept the disclaimer (establishes PHPSESSID)
session.get('https://search.berkeleydeeds.com/NameSearch.php?Accept=Accept')
time.sleep(0.5)

# Step 2: Search by book/page using nested GET params.
# Bookcode values (URL param, NOT the browser form's BookType):
#   'RB' = Record Book (post-Sept 14, 2015 instruments)
#   'RP' = Old Real Property (pre-2015 deeds, declarations, mortgages, etc.)
#   'P'  = Old Plats (pre-2015 plats; booknum format like 'CABQ' for Cabinet Q)
search_resp = session.get('https://search.berkeleydeeds.com/BookSearch.php', params={
    'book[bookcode]': 'RP',     # bookcode for pre-2015 real property
    'book[booknum]': '6408',
    'book[pagenum]': '30',
})
time.sleep(1.5)

# Step 3: Parse instrument number from the search results HTML.
inst_match = re.search(r'inst_num=(\d+)', search_resp.text)
inst_num = inst_match.group(1)

# Step 4: Hit DetailScreen.php to get the base64-encoded `file=` parameter.
# This is the step previously missing from this skill — `view_image.php?inst_num=X`
# by itself returns zero bytes.
detail_resp = session.get(
    f'https://search.berkeleydeeds.com/DetailScreen.php?inst_num={inst_num}'
)
file_match = re.search(r'view_image\.php\?file=([A-Za-z0-9+/=]+)', detail_resp.text)
file_b64 = file_match.group(1)
time.sleep(1.5)

# Step 5: Download the PDF using the scraped file= parameter.
pdf_resp = session.get(
    'https://search.berkeleydeeds.com/view_image.php',
    params={'file': file_b64, 'type': 'pdf'},
    stream=True,
)
with open(output_path, 'wb') as f:
    for chunk in pdf_resp.iter_content(chunk_size=8192):
        f.write(chunk)
```

**If a direct URL was provided** (from property card "Search Deed Records"
button), navigate directly to that URL first — it skips the search step.

**Two different parameter paradigms — do not confuse them:**

| Context | Parameter | Values |
|---------|-----------|--------|
| HTTP URL (nested GET) | `book[bookcode]` | `RB` / `RP` / `P` |
| Browser form submission | `BookType` | `R` / `D` / `P` |

When coding HTTP, always use `bookcode` with values `RB` / `RP` / `P`.
When driving Playwright, use `BookType` with `R` / `D` / `P`.

**Book type semantics (same for both paradigms):**
| HTTP `bookcode` | Form `BookType` | Book Type | Use For |
|-----------------|-----------------|-----------|---------|
| `RB` | `R` | Record Book | Post-Sept 14, 2015 instruments |
| `RP` | `D` | Old Real Property | Pre-2015 deeds, declarations, agreements, mortgages |
| `P` | `P` | Old Plats | Pre-2015 plats (booknum format: `CABQ` for Cabinet Q) |

If a pre-2015 book/page returns empty on `RB`, retry with `RP`. If still
empty, the instrument may be pre-online (pre-July 1983) — flag
`courthouse_needed`.

### Method 2 — Playwright Browser (Fallback)

If HTTP doesn't work (different county, complex portal, captcha), fall
back to Playwright:

```python
from playwright.sync_api import sync_playwright
import time

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page()
    time.sleep(1.5)  # respectful pacing
    browser.close()
```

**PDF Capture Patterns:**

**Pattern A — Inline viewer:** `page.pdf(path=output_path)`

**Pattern B — New tab (Berkeley/Dorchester):**
```python
with page.expect_popup() as popup_info:
    page.click("selector-for-row")
doc_tab = popup_info.value
doc_tab.wait_for_load_state("networkidle")
doc_tab.pdf(path=output_path)
doc_tab.close()
```

**Pattern C — Direct download:** Intercept download event.

**Fallback — screenshot PNG** (only if all patterns fail).
Flag as `capture_fallback`. **Never save HTML files.**

### Berkeley/Dorchester Book Type Quirk

For instruments recorded **before September 14, 2015**:
- Change Book Type to "Old Real Property" (code `D`) for deeds
- Change Book Type to "Old Plats" (code `P`) for plats

Without this, the search returns no results for pre-2015 instruments.

## OCR Pipeline — Every Page, Every Document

After downloading the PDF, run Google Vision OCR on every single page.
This is not optional. Do not rely on portal-displayed text — it is often
truncated or unreliable. Google Vision is the authoritative read.

```python
import fitz  # pymupdf
from google.cloud import vision
import json

client = vision.ImageAnnotatorClient()

doc = fitz.open(pdf_path)
pages_text = []

for page_num in range(len(doc)):
    page = doc[page_num]
    pix = page.get_pixmap(dpi=300)
    img_bytes = pix.tobytes("png")

    image = vision.Image(content=img_bytes)
    response = client.document_text_detection(image=image)
    text = response.full_text_annotation.text if response.full_text_annotation else ""
    pages_text.append(text)

doc.close()

# Save raw OCR output
ocr_output = {
    "pdf_path": pdf_path,
    "page_count": len(pages_text),
    "pages": pages_text,
    "full_text": "\n".join(pages_text)
}

with open(ocr_json_path, 'w') as f:
    json.dump(ocr_output, f, indent=2)
```

**Why every page matters:** Legal descriptions are often in exhibits at the
end of a document. Subject-to language, reservations, and exceptions can
appear on any page. A deed's being clause (the derivation to the prior
deed) is typically mid-document. If you skip pages, you will miss
critical references.

## Data Extraction

After OCR, read the full text and extract structured data. The fields
depend on the document type.

### For Deeds — Full Extraction Checklist

Extract ALL of these. Missing even one reference can break the chain or
leave an encumbrance undiscovered.

```json
{
  "source_pdf": "docs/Deed_3421-112.pdf",
  "instrument_type": "deed",
  "grantor": "",
  "grantee": "",
  "written_date": "",
  "recorded_date": "",
  "consideration": "",
  "legal_description": "",
  "plat_references": [],
  "tms_numbers": [],
  "being_clause": "",
  "being_book": "",
  "being_page": "",
  "being_grantor": "",
  "being_written_date": "",
  "being_recorded_date": "",
  "subject_to_references": [],
  "easement_references": [],
  "restriction_references": [],
  "declaration_references": [],
  "poa_references": [],
  "association_names": [],
  "subdivision_name": "",
  "derivation_notes": ""
}
```

**Source 1 — Being Clause:** The "BEING the same property conveyed to..."
language. This is the derivation — the link to the prior deed. Extract the
exact book, page, grantor, and date.

**Source 2 — Subject-To Language:** Every "subject to" reference. These
point to easements, restrictions, CC&Rs, and other encumbrances by book
and page. Extract EVERY reference with a book/page — not just the ones
that seem important. Each one becomes a queued download.

**Source 2a — Permitted Exceptions (Exhibit B):** Developer deeds and
first-sale deeds typically have an Exhibit B listing 20-40 "Permitted
Exceptions." EVERY exception with a book/page reference must be
extracted into the `subject_to_references` array — not just noted in
a catch-all field. Parse each numbered exception individually:

```json
"subject_to_references": [
  {
    "number": 1,
    "description": "Declaration of CC&Rs for Town Center Zone",
    "book": "1587",
    "page": "220",
    "type": "declaration",
    "association": "Daniel Island Town Center",
    "amendments": [
      {"book": "2384", "page": "177"},
      {"book": "2749", "page": "288"}
    ]
  }
]
```

Each exception becomes a queued download. Also extract any amendments
or supplements listed under each exception. Do not summarize or
abbreviate — capture every book/page pair. The master agent uses this
array to determine which associations to search and which documents
to pull.

**Source 3 — Legal Description Exceptions:** Reservations and exceptions
within the legal description itself ("EXCEPT...", "RESERVING...",
"LESS AND EXCEPT...").

**Source 4 — Exhibit References:** Exhibits often contain the full legal
description, plat references, or lists of encumbrances.

**Source 5 — Association Names:** Any HOA, POA, HPR, subassociation, or
subdivision name mentioned anywhere in the document. These are critical
for association index searches.

### For Mortgages / Deeds of Trust
- Borrower, lender, loan amount, date, maturity
- Legal description (check Exhibit A — OCR must reach it)
- Loan number, MERS indicator
- Any prior mortgage referenced

### For Plats
- Subdivision name, phase, lot/block numbers, acreage
- Easements shown on plat (drainage, utility, access)
- Referenced restrictions or covenants
- Engineer/surveyor name and date

### For Easements
- Grantor (burdened party), grantee (benefited party)
- Full description of what is encumbered
- Type: utility, access, drainage, conservation, pathway
- Expiration or termination language
- **Association tag:** Which association or entity does this relate to?

### For CC&Rs / Declarations / Restrictions
- Recording entity (which association filed it)
- Full list of referenced parent/child documents
- Amendment, supplement, or termination language
- **Association tag:** Which association does this belong to?
  (e.g., "Daniel Island Residential Zone", "Edgefield Park Row Homes")
- Any referenced sub-associations not yet searched

### For Liens / Judgments
- Debtor name (exact as filed), amount, court/docket
- Any satisfaction or release reference
- Type: mechanic's, tax, judgment, HOA assessment, UCC

## Association Tagging

When processing CC&Rs, easements, restrictions, or agreements, always
identify which association or entity the document belongs to. This is
used later to group documents in the review report.

Look for:
- The entity name in the document title or preamble
- "Declaration of [Association Name]"
- "Easement to [Entity Name]"
- References to a parent declaration

Tag each document in decisions.json with an `association` field.
If no specific association, use "General" or "Other".

## What to Write

1. **Save extraction JSON:** `docs/{Type}_{Book}-{Page}_ocr.json`
2. **Update decisions.json:**
   - Chain deeds → add to `chain_links`
   - Encumbrances → add to appropriate `referenced_instruments` category
     with `association` tag
   - Add to `results` with status and triage color
   - Queue any newly-referenced instruments (easements, restrictions, plats)
   - Pre-online instruments → add to `courthouse_needed`

## Validation

After extraction:
- Verify the document describes the subject parcel (check TMS or legal)
- If it doesn't match, set status to `derivation_mismatch` — the master
  agent will handle recovery
- Read the saved PDF visually to confirm capture was successful (not blank,
  all pages present)
- If OCR returns empty on retry, flag `ocr_failed` and continue
