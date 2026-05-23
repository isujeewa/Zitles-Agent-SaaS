# Counties Reference

Each county section covers: portal URL, interface type, access notes,
index format, known quirks, PDF capture pattern, and developer-period
hit threshold.

## Developer-period thresholds

`period-agent.md` uses a per-county hit count to decide when an
ownership period is "developer-scale" and must be split into 6-month
chunks. The threshold reflects typical index density for the county:
rural counties see less activity per name so the threshold is lower;
high-volume counties need a higher threshold to avoid chunking normal
residential periods.

| County                     | Developer threshold |
|----------------------------|---------------------|
| Berkeley                   | 50                  |
| Dorchester                 | 50                  |
| Charleston (when added)    | 75                  |
| Rural counties (default)   | 25                  |

When adding a new county, set its threshold in this table. If unset, use
the rural default of 25 and tune after the first run.

---

## Berkeley County South Carolina

**Property Cards URL (search form):** https://assessor.berkeleycountysc.gov/prop_card_search.php
**Property Card Direct URL (preferred):** `https://assessor.berkeleycountysc.gov/property_card.php?tms={TMS}`
**Register of Deeds Portal URL:** https://search.berkeleydeeds.com/NameSearch.php?Accept=Accept
**Interface Type:** 3 Verticals (Name Search | Name Picker | Name Display)
**Access:** Public, no login required
**Developer Threshold:** 50 hits

### Property Card Direct URL

Berkeley exposes property cards as deep links keyed by TMS — no search
form required. The pattern is:

```
https://assessor.berkeleycountysc.gov/property_card.php?tms={TMS}
```

Example: `https://assessor.berkeleycountysc.gov/property_card.php?tms=244-10-00-095`

Use this pattern first. Fall back to the search form
(`prop_card_search.php`) only if the direct URL returns an error page
(malformed TMS, retired parcel, etc.).

### Index Format
- Search fields: grantor/grantee, category (select "All"), Book Type, Book, Page, Ins #
- Date range format: MM/DD/YYYY
- Name format: Last or Company Name, First

### Known Quirks
- **Book Type for pre-2015 instruments (CRITICAL — silent failure bug):**
  When searching by book and page for deeds or plats recorded BEFORE
  September 14, 2015, you MUST change the Book Type dropdown from its
  default:
  - Deeds / declarations / agreements → "Old Real Property" (code `D`)
  - Plats → "Old Plats" (code `P`) — book format `CAB{letter}` (e.g., `CABQ`)
  - Post-Sept 14, 2015 instruments → "Record Book" (code `R`) — the default

  The default Book Type silently returns zero results for pre-2015
  instruments — no error, just empty. If an expected instrument cannot
  be found, FIRST check its recording date against the 2015-09-14 cutoff
  before concluding it is missing. Any pull that returns empty for a
  pre-2015 book/page is a bug, not a missing record.

- Online records go back to 07/01/1983
- "Instruments verified through" date shown in top-right corner of portal
  (the "good-thru" date).
- **Date range rule — exclusive upper bound:** ALL searches (party,
  association, any index search) must end on the day PRIOR to the
  good-thru date, not the good-thru date itself. The good-thru date is
  when the index was last verified — instruments recorded ON that date
  may not yet be indexed. Using the good-thru date as an inclusive upper
  bound has caused missed instruments. Always use `good_thru - 1 day` as
  the search end date.

### Property Card — "Search Deed Records" Buttons
The Previous Owner History section on the property card has a blue
"Search Deed Records" button next to each deed entry. Each button
contains a hyperlink that goes directly to that deed in the recorder
portal — no book/page search needed.

**Extract these URLs during Phase 1.** They are the fastest path to
each deed in the chain. The property-card agent should capture the
href from each "Search Deed Records" button and include it in
decisions.json alongside the book/page reference. The doc-processor
can then navigate directly to the deed instead of searching by
book/page.

URL pattern: The link typically goes to the NameDisplay or BookSearch
result page for that specific instrument.

### PDF Capture
- Preview loads in: **new tab** (use Pattern B)
- After clicking an instrument row, the document opens in a new browser tab
- Capture the popup tab, not the original search results page

### HTTP API (Alternative to Browser)
Berkeley's portal supports direct HTTP requests, which are faster than
browser automation for searches:
- Name Search: `POST https://search.berkeleydeeds.com/NameSearch.php`
- Book Search: `POST https://search.berkeleydeeds.com/BookSearch.php`
- Document View: opens in new tab from search results

Use HTTP/curl when possible for speed. Fall back to Playwright for
document capture that requires browser rendering.

---

## Dorchester County South Carolina

**Property Cards URL:** https://www.dorchestercountysc.gov/government/property-tax-services/assessor/real-estate-mobile-home-search/cama-parcel-lookup-old-page-test-page
**Register of Deeds Portal URL:** https://search.dorchesterdeeds.com/NameSearch.php?Accept=Accept
**Interface Type:** 3 Verticals
**Access:** Public
**Developer Threshold:** 50 hits

### Index Format
- Search fields: grantor/grantee, category (select "All"), Book Type, Book, Page, Ins #
- Date range format: MM/DD/YYYY
- Name format: Last or Company Name, First

### Known Quirks
- For property cards: enter parcel number → click Enter → select
  "Sales History" button for list of prior deeds
- Online records go back to 07/01/1983
- "Instruments verified through" date shown in top-right corner

### PDF Capture
- Preview loads in: **new tab** (use Pattern B)
- Same popup behavior as Berkeley

---

## County Entry Template

Use this template when adding support for a new county:

```
## [County Name] County South Carolina

**Property Cards URL:**
**Register of Deeds Portal URL:**
**Interface Type:**
**Access:**
**Developer Threshold:** [number — also add to top table]

### Index Format
- Search fields:
- Date range format:
- Name format:

### Known Quirks
-

### PDF Capture
- Preview loads in: [same tab / new tab / download link]
- Capture pattern: [A / B / C]
```
