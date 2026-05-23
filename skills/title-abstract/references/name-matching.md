# Name Matching Reference

## Core Rule

When in doubt, open the document. A missed instrument is always worse
than a false positive. These rules help you triage — they are not
permission to exclude without opening.

---

## Always Treat as Same Person

- Initials vs. full name: `J.A. Smith` = `John A. Smith`
- Middle name present vs. absent: `John Allen Smith` = `John Smith`
- Suffix variations: `John Smith Jr` = `John Smith JR` = `John A. Smith Jr.`
- Common abbreviations in index: `JTWROS`, `ET UX`, `ET AL` — these
  are tenancy/party qualifiers, not part of the name
- Punctuation and spacing differences: `Smith,John` = `Smith, John`
- Hyphenated surnames: search both `Smith-Jones` and `Smith` and `Jones`

## Treat as Likely Same — Open and Confirm

- One-letter spelling difference: `Smithe` vs `Smith`
- Transposed letters: `Smtih` vs `Smith` (index data entry errors are common)
- Nickname vs. formal name: `Bill` vs `William`, `Bob` vs `Robert`,
  `Jim` vs `James`, `Liz` vs `Elizabeth`, `Kate` vs `Katherine`,
  `Mike` vs `Michael`, `Tom` vs `Thomas`, `Dick` vs `Richard`,
  `Chuck` vs `Charles`, `Peggy` vs `Margaret`, `Jack` vs `John`,
  `Ted` vs `Theodore`, `Pat` vs `Patricia`
- Trust variations: `John Smith Trust` / `John A. Smith Revocable Trust`
  / `Smith Family Trust` — open and confirm trustee name
- LLC / corporate variations: `Smith Properties LLC` vs `Smith
  Properties, LLC` vs `Smith Properties` — open and confirm

## Treat as Different Person — Skip (with logged reason)

- Clearly different first name with no nickname relationship
- Different surname with no hyphenation or maiden name explanation
- Different generation confirmed by suffix (Sr. vs Jr.) **only if**
  you have already confirmed which generation owned the property

## Maiden Name / Marital Name Changes

If the chain spans a marriage or divorce, the same person may appear
under different surnames. Watch for:
- AKA / FKA / NKA language in a deed (e.g., "Jane Smith FKA Jane Jones")
- A deed from a woman with a different surname that matches the property
  timeline

When you encounter this, note both names in parcel_tracking and search
the index under both for the relevant period.

## Entity Name Variations

**Default stance: truncate to the distinctive stem.** LLCs,
corporations, and trusts get filed under every permutation — `LLC` vs
`L L C`, `CORPORATION` vs `CORP` vs `CO`, `COMPANY` vs `CO`, `LIMITED`
vs `LTD`, `INCORPORATED` vs `INC`. The index joins your search as a
prefix match, so the shorter the stem, the more variants you catch.

Run searches on (in this order):
- Shortest unique stem: `MOSSEY CREEK`, `CHARLESTON LAND`, `FORD DEV`,
  `PALMETTO BEACH`
- Add the suffix only if the stem returns too much unrelated noise:
  `MOSSEY CREEK L` (catches `LLC`/`L L C`/`LTD` without going full)
- Full legal name as a belt-and-suspenders final pass only when the
  stem was insufficient

Examples of correct stems:
| Legal name | Search stem |
|------------|-------------|
| Mossey Creek LLC | `MOSSEY CREEK` (and `MOSSY CREEK` — alt spelling) |
| Charleston Land Partners LLC | `CHARLESTON LAND` |
| Ford Development Corporation | `FORD DEV` |
| RGT/Charleston Partners Ltd | `RGT` and `CHARLESTON PARTNERS` |
| Palmetto Beach Holdings LLC | `PALMETTO BEACH` |

**Alternate-spelling watch**: if the surrounding documents use a
variant spelling for the same thing (e.g., property address "Mossy
Creek" vs entity "Mossey Creek LLC"), search BOTH spellings as
separate variants. The index indexes whatever was typed on the filing.

## Association Name Variations

**Do not search the full "X Master Association" form as your primary
query.** Associations get filed under many forms, and the master
association's own filings often drop the "Master" qualifier. Start
with the **community/development name** alone and let triage filter
noise.

Primary-then-qualifier pattern:
| Community | Primary | Also try |
|-----------|---------|----------|
| Tanner Plantation Master Association | `TANNER PLANTATION` | `TANNER PLANTATION MASTER`, `TANNER PLANTATION HOA`, `TANNER PLANTATION POA`, `TANNER PLANTATION COMMUNITY`, `TANNER PLANTATION OWNERS` |
| Daniel Island Community Association | `DANIEL ISLAND` | `DANIEL ISLAND COMMUNITY`, `DICA`, `DI COMMUNITY` |
| Nexton Residential Association | `NEXTON RESIDENTIAL` | `NEXTON RESIDENTIAL ASSOCIATION`, `NEXTON RESIDENTIAL COMMUNITY` |
| Mossey Creek Property Owners Association | `MOSSEY CREEK` | `MOSSEY CREEK POA`, `MOSSEY CREEK PROPERTY OWNERS`, `MOSSEY CREEK HOMEOWNERS`, `MOSSY CREEK` (alt spelling) |

The community-name primary captures the developer's filings, the
association's filings, sub-associations, and any entity that uses the
community name — all in one pass.

**Caveat — commercial vs residential**: for large master-planned
communities with commercial tracts, the broad community name will
match commercial association filings. Residential subjects still
search the community name but triage commercial-association results
red.

Always try multiple variations. Association searches reveal CC&R
amendments and supplemental declarations that affect every property in
the subdivision.
