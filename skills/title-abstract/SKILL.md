---
name: title-abstract
description: >
  Performs a complete SC title abstract — searches county recorder portals,
  pulls and analyzes deeds/plats/encumbrances, builds chain of title, and
  produces a comprehensive review report. Use this skill whenever the user
  asks to run a title search, abstract a title, pull a chain of title,
  check indexes, search grantor/grantee records, or any task involving a
  SC county + property address, TMS number, or party name. Also trigger
  when user asks to review, continue, or audit an existing search, or
  mentions "title search", "run a search", "pull the chain", "check the
  index", "run the chain", "abstract", or "title work".
---

# SC Title Abstract

You orchestrate a pipeline of focused sub-agents to search SC county public
records, analyze documents, build a chain of title, and produce a
comprehensive title abstract with review report.

**Your role is coordination.** You decide what comes next, delegate work to
sub-agents, and verify results. You never interact with portals or OCR
documents yourself. Each sub-agent gets a clean context window with only
the instructions relevant to its task — this is what keeps quality
consistent whether it's the first document or the fiftieth.

## Architecture — Layered Production Pipeline

The pipeline is a layered cascade: sequential where it must be (chain
tracing, meta examination), parallel wherever possible (period agents,
index searches, document pulls, specialist examiners). Each layer writes
to `decisions.json` and gates the next.

```
Phase 1:  Property Card                                     (sequential)
    │  seed: current owner, entry deed, associations, online range
    ▼
Phase 2:  Chain Trace                                       (sequential)
    │  walks backward one link at a time, authority = being clauses
    │  output: chain[] skeleton with per-link date ranges
    ▼
Phase 3:  Period Agents (one per chain link)                (parallel)
    │  each runs index searches for its owner + window
    │  flags developer periods (>50 hits) and splits into 6mo chunks
    ▼
Phase 3b: Reconciler                  (only if developer periods present)
    │  matches open instruments to closures across chunk boundaries
    ▼
Phase 4:  Index Searches — consolidated                     (parallel)
    │  any residual association / referenced-party searches
    │  (most index work already happened in Phase 3)
    ▼
Phase 5:  Document Pull                                     (parallel)
    │  OCR + extract every green/yellow triaged instrument
    │  + every book/page referenced in chain deed subject-to clauses
    ▼
Phase 6:  Specialist Examiners × 5                          (parallel)
    │  conveyance, mortgage, lien, easement, restriction
    │  each runs Pass 1 (completeness audit) → Pass 2 (examination)
    ▼
Phase 6b: Retrieval Loop                         (only if examiners ask)
    │  doc-processor fetches missing instruments from retrieval_requests[]
    │  examiner whose request was filled re-fires Pass 1/Pass 2
    ▼
Phase 7:  Meta-Examiner                                     (sequential)
    │  cross-category conflict resolution, consistency checks
    │  assembles final_exceptions[]
    ▼
Phase 8:  Report Generation                                 (sequential)
```

| Phase | What | Agent File | Parallelism |
|-------|------|-----------|-------------|
| 1     | Property card | `agents/property-card.md` | No |
| 2     | Chain trace | `agents/chain-tracer.md` | No (sequential walk) |
| 3     | Period research | `agents/period-agent.md` × N | Yes (one per link) |
| 3b    | Developer reconciliation | `agents/reconciler.md` | One per developer period (parallel across periods) |
| 4     | Residual index searches | `agents/index-searcher.md` | Yes |
| 5     | Document pull | `agents/doc-processor.md` | Yes, ALL at once |
| 6     | Specialist exam | `agents/examiner-conveyance.md`, `examiner-mortgage.md`, `examiner-lien.md`, `examiner-easement.md`, `examiner-restriction.md` | Yes, all 5 fire simultaneously |
| 6b    | Retrieval loop | `agents/doc-processor.md` | Yes |
| 7     | Meta exam | `agents/examiner-meta.md` | No |
| 8     | Report | `agents/report-builder.md` | No |

Data flows through `decisions.json`. Every sub-agent reads from it and
writes back to it. You read it between phases to decide the next step.

### Layer discipline

Each agent has a narrowly defined scope. Do not ask an agent to do work
outside its charter — respawn the correct agent instead:

- `chain-tracer` does not pull encumbrances or triage
- `period-agent` does not match satisfactions across chunks
- `reconciler` does not pull documents
- Specialist examiners do not pull documents — they flag
  `retrieval_requests[]`; `doc-processor` fulfills
- Specialist examiners do not write the final exception list — only
  `examiner-meta` does
- `report-builder` does no examination — it renders what examiners wrote

## Setup

Create the search directory immediately:

```
~/searches/{county}_{owner-lastname}_{YYYY-MM-DD}/
├── index/          ← property cards, search screenshots, annotated results
├── docs/           ← downloaded instruments (deeds, plats, easements, etc.)
├── decisions.json  ← central state file
└── review.html     ← final output
```

Initialize `decisions.json` with the schema at the bottom of this file.
Set `search.county`, `search.tms`, and `search.date_range.to` to today.

## How to Delegate

When spawning a sub-agent, always include:

1. Path to its agent instruction file — tell it to **read that file first**
2. Path to `references/counties.md` for the county
3. The specific task parameters (book/page, party name, date range, etc.)
4. The search directory path and decisions.json path
5. If available, the direct URL to the document (from property card links)

After each sub-agent completes, **read decisions.json** to verify results.

## Phase 1: Property Card

Spawn one sub-agent with `agents/property-card.md`.

**Input:** TMS number + county name.

**Output in decisions.json:**
- `search.current_owner`, `search.entry_deed`, `search.property_address`
- `search.subdivision`, `search.associations`
- `search.online_available_from`, `search.good_thru`
- `search.prior_owners` — every deed in the history with book/page AND
  direct URLs if the portal provides them (Berkeley's "Search Deed Records"
  buttons)

**Gate:** Do not proceed until decisions.json has `current_owner` and
`entry_deed` and `prior_owners`.

## Phase 2: Chain Trace (Sequential)

Spawn one sub-agent with `agents/chain-tracer.md`. It walks the chain
backward **one link at a time** — pull the entry deed, read its being
clause, pull the next deed, repeat. This is sequential by definition:
each link depends on reading the prior deed's being clause.

**Output to `decisions.json` `chain[]`:** a clean skeleton with per-link
`date_range_to_search` (the grantor's ownership window). Chain tracer
does NOT pull encumbrances, run index searches, or analyze — only the
skeleton.

**Gate:** `chain[]` must be populated and terminate with a valid stop
flag (`online_limit_reached`, `root_deed`, `gap`, `out_of_county`)
before Phase 3 begins.

## Phase 3: Period Agents (Parallel)

Spawn one `agents/period-agent.md` per entry in `chain[]` — all in
parallel. Each receives one owner and one date range and runs all index
searches for that period.

**Developer-period flag:** if a period agent's initial count estimate
exceeds 50 hits, it splits into 6-month chunks and runs them in
parallel. It sets `periods.link_{N}.is_developer_period: true` and
`status: awaiting_reconciler`.

## Phase 3b: Reconciler (Conditional)

For any period with `is_developer_period: true`, spawn
`agents/reconciler.md` once all chunks are `complete`. Reconcilers run
in parallel across periods (but fire only when their period's chunks
are done).

The reconciler matches open instruments (mortgages, liens) to closing
instruments (satisfactions, releases) across chunk boundaries and
populates `periods.link_{N}.reconciled`.

## Phase 4: Residual Index Searches (Parallel) — Association-Only

Phase 4 is **association-only**, triggered by developer-deed extractions.
Period agents already covered all chain parties; do not re-run them.

Spawn `agents/index-searcher.md` in parallel for each SPECIFIC
association entity named in developer-deed permitted exceptions:

- Use the **full legal entity name** from the exception language
  (e.g., "Nexton Residential Association Inc"), not the broad community
  name ("Nexton")
- Also search the subdivision name (e.g., "Northeast Village")
- Residential properties skip commercial association searches

### Period date-range drift → human review, not re-run

After deed extractions complete, the actual written/recorded dates of
each chain deed may differ from the date windows period agents used.
- **Immaterial drift (days / a few weeks):** ignore
- **Material drift (months), with a plausible gap that could contain
  instruments:** do NOT re-spawn the period agent. Add an entry to
  top-level `follow_up[]`:

```json
{
  "type": "period_date_range_review",
  "link_number": 3,
  "given_range": ["2005-01-01", "2010-06-30"],
  "actual_range_from_deed": ["2005-08-14", "2010-11-02"],
  "gap_months": 4,
  "reason": "Actual ownership ended ~4 months after period window; potential instruments missed Jul-Oct 2010"
}
```

Human reviews the flag and decides whether to re-spawn the period agent
with a corrected window.

## Phase 5: Document Pull (Parallel)

Spawn parallel `agents/doc-processor.md` for:
1. Every green/yellow triaged instrument from every index search
2. Every referenced instrument with a book/page from chain deeds
   (subject-to clauses, permitted exceptions, Exhibit B)
3. Every amendment/supplement referenced in any CC&R or declaration
4. Plats referenced in the legal description or property card

**Skip list (exhaustive):**
- Satisfied mortgages and their satisfactions (the reconciler and
  index-searcher already noted them as CYA)
- Instruments confirmed via TMS as affecting a different property
- Instruments where the named party is confirmed as a different person
  (not a name variant)

**Developer deeds are reference-heavy.** If a developer deed has 33
permitted exceptions with book/page references, spawn agents for all 33
(minus any already pulled). No cherry-picking.

### Phase 4 note: identifying the right associations

When you do launch targeted association searches in Phase 4, they must
come AFTER developer-deed extractions. Do NOT launch them from the
property card alone. The developer deed's permitted exceptions name the
SPECIFIC associations that encumber the property.

In large master-planned communities (Nexton, Daniel Island, Cane Bay),
the broad development name matches dozens of unrelated entities:
commercial associations, 55+ communities, other neighborhoods. Examples:

- WRONG: Search "NEXTON" → 309 results, 57 entities, massive noise
- RIGHT: Search "NEXTON RESIDENTIAL ASSOCIATION" → 24 results, all relevant
- RIGHT: Search "NORTHEAST VILLAGE" → 53 results (plats for the subdivision)

Residential subjects skip commercial association searches unless the
deed specifically references commercial CC&Rs affecting the property.

## Phase 6: Specialist Examiners (Parallel)

Spawn all five specialist examiners simultaneously:

- `agents/examiner-conveyance.md` — chain integrity, authority to convey
- `agents/examiner-mortgage.md` — open mortgages, assignments, UCCs
- `agents/examiner-lien.md` — mechanics/tax/judgment liens, lis pendens
- `agents/examiner-easement.md` — utility, access, drainage, ingress/egress
- `agents/examiner-restriction.md` — CC&Rs, declarations, HOA governance

Each runs **two passes**:
- **Pass 1 — Completeness audit:** confirm every instrument in its scope
  was actually pulled. If anything is missing or referenced but not
  retrieved, add it to `retrieval_requests[]` at the top level of
  `decisions.json` and stop. Do not render findings.
- **Pass 2 — Examination:** only after Pass 1 is clean (no pending
  `required` retrieval requests). Write findings into
  `examiner_findings.{category}`.

If an examiner sets `status: awaiting_retrieval`, it blocks Phase 7 for
its own findings only. The other four examiners continue in parallel.

## Phase 6b: Retrieval Loop (Conditional, Per-Category Cap)

The retrieval loop runs independently **per examiner category**. Each
category gets up to 3 iterations before the orchestrator escalates that
category to human review — one category hitting the cap does not block
the others.

Track iteration count per category in decisions.json:

```json
"retrieval_loop_state": {
  "conveyance":  {"iterations": 0, "status": "idle"},
  "mortgage":    {"iterations": 0, "status": "idle"},
  "lien":        {"iterations": 0, "status": "idle"},
  "easement":    {"iterations": 0, "status": "idle"},
  "restriction": {"iterations": 0, "status": "idle"}
}
```

`status` values: `idle` (never blocked), `retrieving` (doc-processor
running), `re-examining` (examiner re-running), `capped` (3 iterations
reached), `done` (examiner reached `complete`).

### Pseudocode (orchestrator logic)

```python
CATEGORIES = ["conveyance", "mortgage", "lien", "easement", "restriction"]
MAX_ITER_PER_CATEGORY = 3

# Initial Phase 6 spawn (all 5 in parallel, already done)
# Now enter retrieval loop:

while True:
    state = read_decisions_json()
    pending_categories = []

    for cat in CATEGORIES:
        finding   = state["examiner_findings"][cat]
        loop_meta = state["retrieval_loop_state"][cat]

        if finding["status"] == "complete":
            loop_meta["status"] = "done"
            continue

        if finding["status"] != "awaiting_retrieval":
            continue  # still examining, let it finish

        if loop_meta["iterations"] >= MAX_ITER_PER_CATEGORY:
            loop_meta["status"] = "capped"
            # Add one follow_up entry per unresolved request for this category
            for req in state["retrieval_requests"]:
                is_mine    = (req["requested_by"] == f"examiner-{cat}")
                is_pending = (req["status"] == "pending")
                if is_mine and is_pending:
                    append_follow_up({
                        "type": "retrieval_cap_reached",
                        "category": cat,
                        "instrument": req["instrument"],
                        "reason": req["reason"],
                        "iterations_attempted": loop_meta["iterations"]
                    })
                    req["status"] = "escalated"
            continue

        # This category has pending required retrievals and is below cap
        pending_categories.append(cat)

    write_decisions_json(state)

    if not pending_categories:
        break  # all categories either done or capped → exit loop

    # Fulfill every pending required retrieval request, in parallel,
    # across all pending categories
    pending_reqs = [
        r for r in state["retrieval_requests"]
        if r["status"] == "pending" and r["priority"] == "required"
    ]
    spawn_parallel("doc-processor", pending_reqs)
    wait_for_all()

    # Mark fulfilled requests complete (doc-processor did this if the
    # pull succeeded; otherwise it flagged fetch_failed and we leave
    # the request pending — the examiner will re-flag on next Pass 1)

    # Re-spawn each pending-category examiner in parallel
    for cat in pending_categories:
        state["retrieval_loop_state"][cat]["iterations"] += 1
        state["retrieval_loop_state"][cat]["status"] = "re-examining"
    write_decisions_json(state)

    examiners_to_rerun = [f"examiner-{cat}" for cat in pending_categories]
    spawn_parallel(examiners_to_rerun)
    wait_for_all()
    # Loop around: read state, check statuses again

# Post-loop: any category in `capped` status has escalated follow_up[]
# entries. The meta-examiner still fires for categories in `done` status
# and notes the capped categories in escalations_for_underwriter[].
```

### Gate for Phase 7 after the loop exits

- Every category is either `done` or `capped`
- No `pending` `required` retrieval requests remain (capped ones are
  moved to `escalated` with `follow_up[]` entries)
- Meta-examiner proceeds even if some categories are `capped` — it reads
  only `examiner_findings.{cat}` where `status == "complete"` and rolls
  the capped categories into `escalations_for_underwriter[]` with a
  note: "Category {cat} hit the 3-iteration retrieval cap; unresolved
  gaps listed in follow_up[]."

## Phase 7: Meta-Examiner (Sequential)

Spawn one sub-agent with `agents/examiner-meta.md`.

**Gate:** all five specialist examiners must have `status: complete`
before the meta-examiner fires. No pending `required` retrieval
requests.

The meta-examiner reads every specialist's `for_meta_examiner[]` list,
resolves cross-category conflicts (lien priority vs mortgage priority,
easements created by CC&Rs, purchase-money mortgages and spousal join,
etc.), runs consistency checks, and assembles `final_exceptions[]`.

Output: `examiner_findings.meta.summary` (3-5 sentence exec summary) and
ordered `final_exceptions[]` list with categories, priorities, and
underwriter escalations.

## Phase 8: Report Generation (Sequential)

Spawn one sub-agent with `agents/report-builder.md`.

**Input:** The complete decisions.json (including `final_exceptions[]`
and `examiner_findings.meta.summary`) and all files in the search
directory.

**Output:**
- `review.html` — self-contained HTML, every reference hyperlinked to
  its local PDF. CC&Rs AND easements grouped by association, ordered
  oldest to newest within each group.
- `courthouse_report.html` if `courthouse_needed` has entries.

Use `~/searches/berkeley_mangahas-edzel_2026-03-14/review.html` as the
styling and structural reference.

## decisions.json Schema

```json
{
  "search": {
    "county": "",
    "tms": "",
    "property_address": "",
    "current_owner": "",
    "purchaser": [],
    "entry_deed": "",
    "subdivision": "",
    "legal_description": "",
    "plat_reference": "",
    "associations": [],
    "prior_owners": [],
    "date_range": {"from": "", "to": ""},
    "online_available_from": "",
    "good_thru": ""
  },
  "parcel_tracking": {
    "current": [],
    "history": []
  },
  "chain": [],
  "chain_links": [],
  "periods": {},
  "index_searches": [],
  "results": [],
  "referenced_instruments": {
    "easements": [],
    "restrictions": [],
    "declarations": [],
    "poa": [],
    "hpr": []
  },
  "examiner_findings": {
    "conveyance": {},
    "mortgage": {},
    "lien": {},
    "easement": {},
    "restriction": {},
    "meta": {}
  },
  "retrieval_requests": [],
  "retrieval_loop_state": {
    "conveyance":  {"iterations": 0, "status": "idle"},
    "mortgage":    {"iterations": 0, "status": "idle"},
    "lien":        {"iterations": 0, "status": "idle"},
    "easement":    {"iterations": 0, "status": "idle"},
    "restriction": {"iterations": 0, "status": "idle"}
  },
  "final_exceptions": [],
  "follow_up": [],
  "courthouse_needed": [],
  "tax_collection": {}
}
```

### New fields in this version

- **`chain[]`** — populated by `chain-tracer.md`. Backward-walked
  skeleton from the entry deed. Each entry has
  `{link, grantor, grantee, instrument, book, page, date,
  date_range_to_search[from,to]}` plus a terminal entry with stop flag.
  Distinct from `chain_links[]`, which is the detailed chain used by
  the report builder.
- **`periods{}`** — keyed by `link_{N}`. Written by `period-agent.md`.
  Contains `{owner, date_range, link_number, is_developer_period,
  chunks[], index_searches[], raw_results[], status, reconciled?}`.
- **`examiner_findings{}`** — per-category findings from specialist
  examiners plus the meta-examiner consolidation.
- **`retrieval_requests[]`** — instruments flagged missing by examiners.
  Each `{requested_by, instrument, reason, priority, status}`.
  Fulfilled by Phase 6b.
- **`final_exceptions[]`** — ordered exception list written by
  `examiner-meta.md`. This is what the report builder renders.

**prior_owners entry (from property card):**
```json
{
  "name": "Bedard, Stephen A & Marie T",
  "deed_book_page": "2982-378",
  "sale_date": "03/26/2019",
  "sale_price": 487000,
  "deed_url": "https://search.berkeleydeeds.com/..."
}
```

**chain_links entry:**
```json
{
  "seq": 1,
  "instrument": "Record Book 3995, Page 424",
  "written": "2021-09-22",
  "recorded": "2021-10-04",
  "grantor": "Donald Ralph Compton and Rosalind Castillo Compton",
  "grantee": "Edzel Delacruz Mangahas and Sarah Wilk Mangahas (JTWROS)",
  "consideration": "$1,775,000",
  "legal": "Lot CC-C24, Block C, Parcel CC, Daniel Island",
  "plat_ref": "Plat Cabinet S, Page 64I",
  "tms": "277-08-02-017",
  "status": "confirmed",
  "pdf": "docs/Deed_3995-424.pdf",
  "notes": ""
}
```

**referenced_instruments entry (with association tag):**
```json
{
  "instrument": "Book 2056, Pg 320",
  "description": "Amended & Restated CC&Rs for DI Residential Zone",
  "association": "Daniel Island Residential Zone",
  "first_referenced_in": "Deed Book 3995 Pg 424",
  "pdf": "docs/Declaration_2056-320.pdf",
  "status": "grabbed"
}
```

## File Naming

`DocumentType_Book-Page.pdf` — no exceptions.

| Type | Example |
|------|---------|
| Deed | `Deed_3995-424.pdf` |
| Mortgage | `Mortgage_3995-429.pdf` |
| Satisfaction | `Satisfaction_3500-44.pdf` |
| Easement | `Easement_1204-88.pdf` |
| Plat | `Plat_CabinetS-64I.pdf` |
| Declaration | `Declaration_882-14.pdf` |
| Amendment | `Amendment_950-12.pdf` |
| POA | `POA_1500-200.pdf` |
| Lien | `Lien_2100-5.pdf` |
| Agreement | `Agreement_2782-204.pdf` |
| Property Card | `Property Card_277-08-02-017.pdf` |
| Index Search | `Search_Smith-Jo_p1.pdf` |
| Annotated | `Search_Smith-Jo_p1_annotated.pdf` |
| Tax Bill | `Tax Bill_2025_277-08-02-017.pdf` |
| Tax Receipt | `Tax Receipt_2024_277-08-02-017.pdf` |

## Verification Gates

| After Phase | Verify |
|-------------|--------|
| 1  | `search.current_owner`, `search.entry_deed`, `search.prior_owners`, `search.good_thru`, `search.online_available_from` populated |
| 2  | `chain[]` populated in sequence order; terminal entry has a valid stop flag (`online_limit_reached`, `root_deed`, `gap`, `out_of_county`) |
| 3  | Every entry in `chain[]` has a corresponding `periods.link_{N}` with status `complete`, `awaiting_reconciler`, or `partial` |
| 3b | Every developer period (`is_developer_period: true`) has `status: reconciled` and `reconciled.open[]` / `.closed[]` populated |
| 4  | Targeted association searches fired for every specific association entity named in developer deed permitted exceptions |
| 5  | Every green/yellow triaged instrument and every referenced book/page has a PDF and extraction JSON in `docs/` |
| 6  | Each `examiner_findings.{cat}.status` is either `complete` OR its `retrieval_loop_state.{cat}.status` is `capped` (3 iterations exhausted) |
| 6b | For every category, iteration count ≤ 3; `retrieval_requests[]` has no entries with `priority: required` and `status: pending` (pending entries either got fulfilled or were moved to `escalated`) |
| 7  | `examiner_findings.meta.status == "complete"`; `final_exceptions[]` populated and ordered; capped categories reflected in `escalations_for_underwriter[]` |
| 8  | `review.html` exists with all 15 sections; every reference hyperlinked |

## Resuming an Interrupted Search

If a search directory already exists:
1. Read decisions.json
2. Walk the verification gates to find the first incomplete phase
3. Resume from there — do not redo completed work
4. Check for existing PDFs before re-downloading

## Error Handling

- **Portal timeout:** Save state to decisions.json, retry
- **Capture failure:** Try alternate PDF patterns. Last resort: screenshot PNG + flag
- **OCR empty:** Retry once. If still empty, flag `ocr_failed`, continue
- **Chain break:** Flag to `follow_up`, do not block remaining work
- **0 index results:** Try broader name prefixes, save empty results as proof
- **250+ results:** Spawn sub-agents in 1-month date chunks
- **Never save HTML files.** Always PDF. Screenshot PNG as last resort.
