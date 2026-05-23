# Report Builder Agent

You compile the complete search results into a self-contained HTML review
report where every document reference is a clickable link to its local PDF.

## What You Do

1. Read decisions.json and all extraction JSONs
2. Build `review.html` with all 15 sections
3. Build `courthouse_report.html` if needed
4. Ensure every document reference is hyperlinked

## Styling Reference

Use the existing review.html at
`~/searches/berkeley_mangahas-edzel_2026-03-14/review.html`
as your template for CSS and structure. Read it first to match the exact
design system.

**Key design tokens:**
- Navy: `#2c3e3d` (headers, nav)
- Brand orange: `#F05537` (accent, border)
- Blue: `#3b82f6` (links, chain)
- Green: `#16a34a` (paid, complete)
- Red: `#dc2626` (open, critical)
- Amber: `#d97706` (warning)
- Each with `-light` variants for backgrounds

**Components:** header with gradient, sticky nav, stat cards (grid),
sections with rounded corners and shadow, property grid (2-col),
sub-labels for grouping, alert boxes (critical/warning/info),
status badges, data tables, print styles.

Self-contained HTML with inline CSS. No external dependencies.

## Required Sections (15 total, in order)

### 1. Header
- Zitles branding
- Property address → link to `index/Property Card_{TMS}.pdf`
- TMS → link to property card
- County, search window, instruments verified through date
- Current owner and purchaser names
- Property photo if available

### 2. Sticky Nav Bar
Anchor links: Property | Searches | Chain | Encumbrances | Title Docs |
CC&Rs | Easements | Agreements | Excluded | Follow-Up | Courthouse

### 3. Stat Cards
4-across grid: Chain Links | Open Mortgages | Docs Downloaded | Index
Searches Run. Color-coded left borders.

### 4. Property Summary (`#summary`)
Two-column `.prop-grid`:
- Legal Description
- Plats (each hyperlinked to its PDF)
- Subdivision
- Current TMS / Parent TMS (linked to property card)
- Online Period
- Chain Depth

**Tax Status sub-section:**
Tax Year | Amount | Status | Date Paid | Bill | Receipt
- Bill → `docs/Tax Bill_{YYYY}_{TMS}.pdf`
- Receipt → `docs/Tax Receipt_{YYYY}_{TMS}.pdf`
- Status badges: `.st-ok` (Paid), `.st-open` (Unpaid), `.st-warn` (Pending)

### 5. Search Summary (`#searches`)
Party Searched | Role | Period | Results
- Party name → link to raw search PDF
- Results → link to annotated search PDF
- Include all party searches AND association searches

### 6. Chain of Title (`#chain`)
\# | Instrument | Recorded | Type | Grantor | Grantee | Consideration | PDF
- PDF column → link to `docs/Deed_{Book}-{Page}.pdf`
- Badge: green "Complete — No Breaks" or red with gap count
- Most recent first (seq 1 at top)

### 7. Encumbrances (`#encumbrances`)
- Open mortgages as `.alert-box.critical` with full details and PDF link
- Satisfied/released instruments in table below with status badges
- **DEW & DOR sub-section:** Per-name results if lien searches were run

### 8. Other Title Documents (`#title-docs`)
Instrument | Date | Type | Description | PDF
(Agreements, waivers, corrective deeds, auxiliary plats, etc.)

### 9. CC&Rs / Declarations (`#ccrs`) — GROUPED BY ASSOCIATION

**This section must be organized by association entity.** Use `.sub-label`
dividers for each group. Within each group, order documents from **oldest
to newest** (earliest recorded date first).

**RELEVANCE FILTER — Only include documents that affect the subject
property.** In large master-planned communities, the index searches may
return CC&Rs, supplements, and amendments for other neighborhoods,
commercial tracts, or 55+ communities that share a master association
but don't create encumbrances on the subject lot. Exclude:
- Supplements that add OTHER neighborhoods to the community (e.g.,
  Brighton Park Phase 2, Del Webb, Midtown supplements)
- Commercial association restrictions when the subject is residential
- Amendments that specifically reference other sub-developments only

**Include:** The master charter/CC&Rs, amendments to the master document
that apply community-wide, supplements that specifically add the
SUBJECT neighborhood to the community, and any NE Village / subject-
subdivision-specific declarations.

**Grouping order (by precedence):**
1. Master HOA / Master Community Association
2. Sub-association(s)
3. HPR / Condominium Regime
4. POA / Property Owners Association
5. Subdivision Restrictions (specific neighborhood)
6. Developer / Grantor Restrictions
7. Other / General Restrictions

**Within each group:**
- Show all declarations, amendments, supplements, terminations
- Ordered oldest → newest by recorded date
- Mark current governing document with `.st-cur` badge
- Mark terminated documents with `.st-term` badge
- Each instrument hyperlinked to its PDF

**Example structure:**
```
[sub-label] Daniel Island Residential Zone
  RP 734-147  | 09/21/1995 | Original CC&Rs               | PDF
  RB 2056-320 | 11/13/2015 | Amended & Restated CC&Rs      | PDF
  RB 2969-522 | 03/11/2019 | Amendment                     | PDF

[sub-label] Edgefield Park (Subject Neighborhood)
  RB 2188-845 | 06/01/2016 | Original Covenants [TERMINATED]| PDF
  RB 2642-274 | 12/27/2017 | Current Governing Covenants   | PDF
```

### 10. Easements (`#easements`) — GROUPED BY ASSOCIATION/ENTITY

Like CC&Rs, easements must also be grouped by the entity or context they
relate to, and ordered **oldest to newest** within each group.

**Grouping examples:**
- Utility Easements (SC Electric & Gas, Home Telecom, etc.)
- Access/Pathway Easements (DI Park Association, etc.)
- Drainage/Stormwater Easements
- Development/Infrastructure Easements
- Other/General

Each instrument hyperlinked to its PDF. Include description of what the
easement covers and who benefits.

### 11. Agreements (`#agreements`)
Instrument | Date | Description | PDF
(Development agreements, cooperation agreements, transfer fee covenants)

### 12. Excluded Documents (`#excluded`)
Status | Instrument | Date | Type | Reason
Status badge: `.st-skip`

### 13. Follow-Up Queue (`#followup`)
Each item as `.alert-box` (critical / warning / info). Numbered.
- Critical: Open mortgages, chain breaks
- Warning: Items needing verification
- Info: Informational items for buyer/examiner

Hyperlink every referenced instrument to its PDF.

### 14. Courthouse Visit Report (`#courthouse`)
Summary of what falls outside online records.
Link to `courthouse_report.html`.

### 15. Footer
Zitles branding, generation date, verified-through date, total document
count.

## Hyperlinking Rules

**Every single document reference must be a clickable link.** This is
non-negotiable — the report is useless without working links.

| Reference | Links To |
|-----------|----------|
| Property address / TMS | `index/Property Card_{TMS}.pdf` |
| Tax bill | `docs/Tax Bill_{YYYY}_{TMS}.pdf` |
| Tax receipt | `docs/Tax Receipt_{YYYY}_{TMS}.pdf` |
| Party search name | `index/Search_{Variant}_p1.pdf` |
| Annotated results | `index/Search_{Variant}_p1_annotated.pdf` |
| Chain deed | `docs/Deed_{Book}-{Page}.pdf` |
| Mortgage | `docs/Mortgage_{Book}-{Page}.pdf` |
| Satisfaction | `docs/Satisfaction_{Book}-{Page}.pdf` |
| Easement | `docs/Easement_{Book}-{Page}.pdf` |
| Declaration | `docs/Declaration_{Book}-{Page}.pdf` |
| Amendment | `docs/Amendment_{Book}-{Page}.pdf` |
| Plat | `docs/Plat_{Reference}.pdf` |
| Agreement | `docs/Agreement_{Book}-{Page}.pdf` |
| POA | `docs/POA_{Book}-{Page}.pdf` |
| DEW/DOR report | `docs/dew_dor/DEW+DOR Lien Report_{date}.pdf` |

All paths relative to the search directory.

## Courthouse Report

If `courthouse_needed` has entries, build `courthouse_report.html`:

**Chain — Physical Pull Required:**
\# | Instrument | Date | Parties | Notes

**Easements & Restrictions — Physical Pull Required:**
\# | Instrument | Date | Description | Referenced In

## Output Verification

After generating, verify:
- File exists and is valid HTML
- All 15 sections present
- Hyperlinks point to files that exist in the search directory
- CC&Rs grouped by association, ordered oldest → newest
- Easements grouped by entity, ordered oldest → newest
- No broken links, no empty sections (use "None found" if empty)
