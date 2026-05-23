# Instrument Types Reference

## Always Pull

**Deeds**
Any conveyance of ownership within the search period. Includes warranty
deeds, quitclaim deeds, deeds of distribution, master deeds, and
corrective/confirmatory deeds. Check grantor/grantee match and extract
legal description, plat reference, and TMS.

**Plats**
Pull if referenced in the legal description of any deed in the chain.
One plat may cover the full search — note it once and reference as
needed. Record subdivision name, lot/block, acreage, and recording info.

**Covenants & Restrictions (CC&Rs)**
Pull once per subdivision/association. Note recording info and whether
there is any expiration language or amendment. Check index for any
amendments filed after the original. Tag with the association name.

**Easements**
Pull all easements affecting the property. Note whether they burden
(run against) or benefit (run with) the property. Note any expiration
or termination language. Tag with the relevant entity.

**Power of Attorney**
Pull only if used to execute another instrument in the chain. Note the
grantor, attorney-in-fact, and whether the POA was limited or general.

---

## Pull If Open (Not Satisfied)

**Mortgages / Deeds of Trust**
Pull if no corresponding satisfaction or release is recorded. If
satisfied, do not pull the original — note it as satisfied (see below).

**Liens**
Includes mechanic's liens, HOA liens, municipal liens, and tax liens.
Pull if no release is recorded.

**UCC Filings / Financing Statements (UCC-1)**
Pull if no termination statement (UCC-3) is recorded. Note secured
party and collateral description.

**Judgments / Lis Pendens**
Pull if not released or dismissed. Note docket number, amount, and
court. Flag for title underwriter attention.

### How to determine if satisfied

Check the index for a corresponding:
- Satisfaction of Mortgage / Release of Mortgage
- Lien Release / Cancellation
- UCC-3 Termination Statement
- Satisfaction of Judgment / Order of Dismissal

If satisfied → do NOT pull the original instrument or the satisfaction.
DO note in decisions.json as CYA:

```json
{
  "instrument": "Mortgage Book 2841 Pg 44",
  "status": "satisfied",
  "satisfied_by": "Satisfaction Book 3102 Pg 88",
  "notes": "CYA — satisfied of record"
}
```

---

## Related / Companion Documents

These modify an existing instrument. Pull if the parent is in scope:

- **Mortgage Amendment / Modification** — changes terms of original
- **Assignment of Mortgage** — transfers lender's interest; note new
  holder and check if corresponding satisfaction was filed by assignee
- **Partial Satisfaction** — releases part of the collateral; note
  which portion was released and confirm subject property is not released
- **UCC-1 Amendment (UCC-3 Amendment)** — modifies original financing
  statement; pull if parent UCC-1 is in scope

Rule: if you grab the parent, search the index for all related
documents and pull those too.

---

## Out of Scope

- Satisfactions / releases where the parent instrument is already noted
- UCC-3 terminations where the parent UCC-1 is confirmed satisfied
- Deeds clearly involving a different property — always confirm via TMS
  or legal description before excluding
- Instruments where the party name is confirmed to be a different person
  (not just a name variant — see `references/name-matching.md`)
