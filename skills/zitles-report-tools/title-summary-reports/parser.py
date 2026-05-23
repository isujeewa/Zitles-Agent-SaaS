"""Parse raw text files into structured ReportData."""

import re
from datetime import datetime

from schema import (
    AnalysisItem, Easement, Judgment, Lien, Mortgage, MortgageAssignment,
    PlatReference, ReportData, Restriction, TaxInfo, TaxYear, UCCFiling,
    VestingDeed,
)

# Section header patterns (order matters — matched top to bottom)
SECTION_HEADERS = [
    "Title Summary Report",
    "Order Information",
    "Property Information",
    "Current Owner Information",
    "General Comments",
    "Vesting Deeds",
    "Estates",
    "Tax Information",
    "Mortgages",
    "Judgments",
    "Liens",
    "UCC Filings",
    "Restrictions",
    "Easements",
]


def _split_sections(text: str) -> dict[str, str]:
    """Split text into named sections based on header markers."""
    sections: dict[str, str] = {}
    lines = text.strip().split("\n")
    current_section = None
    current_lines: list[str] = []

    for line in lines:
        stripped = line.strip()
        matched_header = None
        for header in SECTION_HEADERS:
            if stripped.lower() == header.lower() or stripped.lower().startswith(header.lower()):
                matched_header = header
                break

        if matched_header:
            if current_section is not None:
                sections[current_section] = "\n".join(current_lines).strip()
            current_section = matched_header
            # Keep remainder of line after header (e.g. "Tax Information Pending Tax Sale: ...")
            remainder = stripped[len(matched_header):].strip()
            current_lines = [remainder] if remainder else []
        else:
            current_lines.append(line)

    if current_section is not None:
        sections[current_section] = "\n".join(current_lines).strip()

    return sections


def _extract_kv(text: str, key: str) -> str:
    """Extract a value following 'Key:' pattern."""
    pattern = rf"{re.escape(key)}:\s*(.+?)(?:\s{{2,}}|\n|$)"
    match = re.search(pattern, text, re.IGNORECASE)
    return match.group(1).strip() if match else ""


def _parse_order_info(section: str, report: ReportData) -> None:
    report.order_number = _extract_kv(section, "Order Number")
    report.search_type = _extract_kv(section, "Search Type")
    report.search_start_date = _extract_kv(section, "Search Start Date")
    report.search_end_date = _extract_kv(section, "Search End Date")


def _parse_generated_date(section: str, report: ReportData) -> None:
    match = re.search(r"Generated\s+on\s+(\d{1,2}/\d{1,2}/\d{4})", section, re.IGNORECASE)
    if match:
        try:
            dt = datetime.strptime(match.group(1), "%m/%d/%Y")
            report.generated_date = dt.strftime("%B %d, %Y")
        except ValueError:
            report.generated_date = match.group(1)


def _parse_property_info(section: str, report: ReportData) -> None:
    report.parcel_id = _extract_kv(section, "Parcel Number")

    # Handle inline format: "State: SC County: Charleston Address: ... Parcel Number: ..."
    full = section.replace("\n", " ")

    # Extract state (word(s) before "County:")
    state_match = re.search(r"State:\s*(.+?)\s+County:", full, re.IGNORECASE)
    if state_match:
        report.state = state_match.group(1).strip()

    # Extract county (word(s) before "Address:")
    county_match = re.search(r"County:\s*(.+?)\s+Address:", full, re.IGNORECASE)
    if county_match:
        report.county = county_match.group(1).strip()
    else:
        # Fallback — county before Parcel
        county_match2 = re.search(r"County:\s*(.+?)(?:\s+Parcel|\s*$)", full, re.IGNORECASE)
        if county_match2:
            report.county = county_match2.group(1).strip()

    # Extract address between "Address:" and "Parcel Number:"
    addr_match = re.search(r"Address:\s*(.+?)\s+Parcel Number:", full, re.IGNORECASE)
    if addr_match:
        addr_str = addr_match.group(1).strip()
        parts = [p.strip() for p in addr_str.split(",")]
        if parts:
            report.property_address = parts[0]
        if len(parts) >= 2:
            report.city = parts[1]
        if len(parts) >= 3:
            state_zip = parts[2].strip()
            st_match = re.match(r"([A-Z]{2})\s*(\d{5})?", state_zip)
            if st_match:
                report.state = st_match.group(1)
                if st_match.group(2):
                    report.zip_code = st_match.group(2)


def _parse_owners(section: str, report: ReportData) -> None:
    owners = _extract_kv(section, "Current Owners")
    if owners:
        report.owners = owners


def _parse_general_comments(section: str, report: ReportData) -> None:
    report.general_comments = section.strip()

    # Extract plat references from comments
    # Supports formats: "L16 / 0448", "DF 44", "2023001913-917", "S35q", "M196a", "Q352a-d"
    most_recent_match = re.search(
        r"[Mm]ost recent plat is\s+([^\s.;,]+(?:\s*/\s*[^\s.;,]+)?(?:-[^\s.;,]+)?)",
        section,
    )
    most_recent_ref = most_recent_match.group(1).strip() if most_recent_match else ""

    # Parse "See also plats ..." pattern — split on semicolons, commas, or "and"
    see_also = re.search(r"[Ss]ee also plats?\s+(.+?)$", section, re.MULTILINE)
    if see_also:
        refs_str = see_also.group(1)
        # Split on semicolons, commas, or " and "
        raw_refs = re.split(r"\s*[;,]\s*|\s+and\s+", refs_str)
        refs = [r.strip().rstrip(".") for r in raw_refs if r.strip()]
        if most_recent_ref:
            report.plat_references.append(PlatReference(reference=most_recent_ref, most_recent=True))
        for ref in refs:
            if ref:
                report.plat_references.append(PlatReference(reference=ref, most_recent=False))
    elif most_recent_ref:
        report.plat_references.append(PlatReference(reference=most_recent_ref, most_recent=True))


def _parse_vesting_deeds(section: str, report: ReportData) -> None:
    lines = [l.strip() for l in section.split("\n") if l.strip() and l.strip().lower() != "no data found"]
    if not lines:
        return

    # Pattern: date  book  page  legal_description
    for line in lines:
        match = re.match(r"(\d{1,2}/\d{1,2}/\d{4})\s+(\S+)\s+(\S+)\s+(.+)", line)
        if match:
            deed = VestingDeed(
                date=match.group(1),
                book=match.group(2),
                page=match.group(3),
                legal_description=match.group(4).strip(),
            )
            report.vesting_deed = deed
            break


def _parse_tax_info(section: str, report: ReportData) -> None:
    tax = TaxInfo()

    # Parse flags from the header remainder
    flag_text = section.split("\n")[0] if section else ""
    full_text = section

    # Check for flag values
    pending_match = re.search(r"Pending Tax Sale:\s*(Yes|No)", full_text, re.IGNORECASE)
    delinquent_match = re.search(r"Delinquent Taxes?:\s*(Yes|No)", full_text, re.IGNORECASE)
    rollback_match = re.search(r"Roll\s*Back Taxes?:\s*(Yes|No)", full_text, re.IGNORECASE)
    exempt_match = re.search(r"Tax Exempt:\s*(Yes|No)", full_text, re.IGNORECASE)

    if pending_match:
        tax.pending_tax_sale = pending_match.group(1).lower() == "yes"
    if delinquent_match:
        tax.delinquent = delinquent_match.group(1).lower() == "yes"
    if rollback_match:
        tax.roll_back = rollback_match.group(1).lower() == "yes"
    if exempt_match:
        tax.exempt = exempt_match.group(1).lower() == "yes"

    # Sometimes all flags are on one line: "No No No No"
    if not pending_match:
        flags = re.findall(r"\b(Yes|No)\b", flag_text, re.IGNORECASE)
        if len(flags) >= 4:
            tax.pending_tax_sale = flags[0].lower() == "yes"
            tax.delinquent = flags[1].lower() == "yes"
            tax.roll_back = flags[2].lower() == "yes"
            tax.exempt = flags[3].lower() == "yes"

    # Parse tax years: "2025 0 156,060.45" pattern
    year_pattern = re.findall(r"(20\d{2})\s+(\d+)\s+([\d,]+\.?\d*)", full_text)
    for year, status_code, amount in year_pattern:
        status = "PAID" if status_code == "0" else "UNPAID"
        amount_clean = amount.replace(",", "")
        try:
            amount_formatted = f"${float(amount_clean):,.2f}"
        except ValueError:
            amount_formatted = f"${amount}"
        tax.years.append(TaxYear(year=year, status=status, amount=amount_formatted))

    report.tax_info = tax


def _parse_mortgages(section: str, report: ReportData) -> None:
    if "no data found" in section.lower():
        return

    # Split by "Mortgage N" markers
    mortgage_blocks = re.split(r"Mortgage\s+\d+", section)
    mortgage_blocks = [b.strip() for b in mortgage_blocks if b.strip()]

    for block in mortgage_blocks:
        mortgage = Mortgage(
            lender=_extract_kv(block, "Lender"),
            amount=_extract_kv(block, "Amount"),
            date=_extract_kv(block, "Recorded Date"),
            book=_extract_kv(block, "Book"),
            page=_extract_kv(block, "Page"),
        )

        # Format amount
        if mortgage.amount:
            try:
                amt = float(mortgage.amount.replace(",", ""))
                mortgage.amount = f"${amt:,.0f}"
            except ValueError:
                if not mortgage.amount.startswith("$"):
                    mortgage.amount = f"${mortgage.amount}"

        # Parse assignments after "Assignments" marker
        assignments_match = re.search(r"Assignments\s*\n(.*)", block, re.DOTALL)
        if assignments_match:
            assign_text = assignments_match.group(1).strip()
            assign_lines = [l.strip() for l in assign_text.split("\n") if l.strip()]
            for aline in assign_lines:
                # Pattern: "Description  date  book  page"
                amatch = re.match(r"(.+?)\s{2,}(\d{1,2}/\d{1,2}/\d{4}|\S+)\s+(\S+)\s+(\S+)", aline)
                if amatch:
                    assignment = MortgageAssignment(
                        notes=amatch.group(1).strip(),
                        date=amatch.group(2),
                        book=amatch.group(3),
                        page=amatch.group(4),
                    )
                    mortgage.assignments.append(assignment)
                else:
                    # Try simpler pattern
                    parts = aline.split()
                    if len(parts) >= 4:
                        # Last three are likely date, book, page
                        assignment = MortgageAssignment(
                            notes=" ".join(parts[:-3]),
                            date=parts[-3] if "/" in parts[-3] else "",
                            book=parts[-2] if "/" not in parts[-2] else parts[-3],
                            page=parts[-1],
                        )
                        mortgage.assignments.append(assignment)

        report.mortgages.append(mortgage)


def _parse_judgments(section: str, report: ReportData) -> None:
    if "no data found" in section.lower():
        return

    lines = [l.strip() for l in section.split("\n") if l.strip()]
    for line in lines:
        # Complex format: parties  amount  N/A  case_number  N/A  notes
        # Try to extract case number pattern first
        case_match = re.search(r"(\d{4}CP\d+-\d+)", line)
        if case_match:
            case_number = case_match.group(1)
            # Split around the case number
            before = line[:case_match.start()].strip()
            after = line[case_match.end():].strip()

            # Before contains: parties  amount  N/A
            before_parts = re.split(r"\s{2,}", before)
            parties = before_parts[0] if before_parts else ""
            amount = before_parts[1] if len(before_parts) > 1 else ""

            # After contains: N/A  notes
            after_parts = re.split(r"\s{2,}", after.lstrip())
            notes = after_parts[-1] if after_parts else ""
            # Clean up N/A from notes
            notes = re.sub(r"^N/A\s*", "", notes).strip()

            judgment = Judgment(
                parties=parties.replace(".", ""),
                amount=amount,
                case_number=case_number,
                notes=notes if notes else "",
            )
            report.judgments.append(judgment)


def _parse_ucc_filings(section: str, report: ReportData) -> None:
    if "no data found" in section.lower():
        return

    lines = [l.strip() for l in section.split("\n") if l.strip()]
    # Combine continuation lines
    combined = " ".join(lines)

    # Pattern: address  lender  book/N/A  filing_number  notes
    # Try to find filing number pattern
    filing_match = re.search(r"(\d{4}-\d+)", combined)
    if filing_match:
        filing_number = filing_match.group(1)
        before = combined[:filing_match.start()].strip()
        after = combined[filing_match.end():].strip()

        # Parse before: "1001 Harborview Ameris Bank N/A"
        # Try splitting on double-space first
        parts = re.split(r"\s{2,}", before)
        if len(parts) >= 2:
            address = parts[0]
            lender = parts[1]
        else:
            # Single-space separated — try to identify lender by known patterns
            words = before.split()
            # Heuristic: lender is usually "Something Bank" at end
            bank_idx = None
            for i, w in enumerate(words):
                if w.lower() in ("bank", "credit", "mortgage", "financial", "lending"):
                    bank_idx = i
                    break
            if bank_idx and bank_idx >= 2:
                lender = " ".join(words[bank_idx - 1:])
                address = " ".join(words[:bank_idx - 1])
            else:
                address = before
                lender = ""
        # Strip N/A from lender
        lender = re.sub(r"\s*N/A\s*$", "", lender).strip()

        ucc = UCCFiling(
            filing_number=filing_number,
            lender=lender,
            address=address,
            notes=after.strip(),
        )
        report.ucc_filings.append(ucc)
    elif combined.strip():
        # Fallback: treat entire block as one UCC filing
        report.ucc_filings.append(UCCFiling(notes=combined))


def _parse_restrictions(section: str, report: ReportData) -> None:
    if "no data found" in section.lower():
        return

    lines = [l.strip() for l in section.split("\n") if l.strip()]
    for line in lines:
        # Pattern: book page date description party/notes
        match = re.match(
            r"([A-Z]?\d+)\s+(\d+)\s+(\d{1,2}/\d{1,2}/\d{4})\s+(.+)",
            line,
        )
        if match:
            book = match.group(1)
            page = match.group(2)
            date = match.group(3)
            remainder = match.group(4).strip()

            # Try to split description and party on "N/A" or known patterns
            desc_parts = re.split(r"\s{2,}", remainder)
            description = desc_parts[0] if desc_parts else remainder
            party = desc_parts[1] if len(desc_parts) > 1 else ""
            if party == "N/A":
                party = ""

            restriction = Restriction(
                date=date,
                book=book,
                page=page,
                description=description,
                party=party,
                reference=f"{book} / {page}",
            )
            report.restrictions.append(restriction)


def _parse_easements(section: str, report: ReportData) -> None:
    if "no data found" in section.lower():
        return

    lines = [l.strip() for l in section.split("\n") if l.strip()]
    for line in lines:
        # Pattern: book page date type holder notes
        match = re.match(
            r"([A-Z]?\d+)\s+(\d+)\s+(\d{1,2}/\d{1,2}/\d{4})\s+(.+)",
            line,
        )
        if match:
            book = match.group(1)
            page = match.group(2)
            date = match.group(3)
            remainder = match.group(4).strip()

            # Split on double+ spaces
            parts = re.split(r"\s{2,}", remainder)
            etype = parts[0] if parts else ""
            holder = parts[1] if len(parts) > 1 else ""
            notes = parts[2] if len(parts) > 2 else ""
            if holder == "N/A":
                holder = ""
            if notes == "N/A":
                notes = ""

            easement = Easement(
                date=date,
                book=book,
                page=page,
                type=etype,
                holder=holder,
                notes=notes,
                reference=f"{book} / {page}",
            )
            report.easements.append(easement)


def _generate_analysis(report: ReportData) -> None:
    """Auto-generate analysis items based on report data."""
    items = []

    # Vesting confirmation
    if report.vesting_deed:
        items.append(AnalysisItem(
            icon_type="checkmark",
            text=f"Title confirmed vested via Deed recorded in Book {report.vesting_deed.book} / {report.vesting_deed.page}.",
        ))

    # Tax status
    if report.tax_info and report.tax_info.years:
        all_paid = all(y.status == "PAID" for y in report.tax_info.years)
        if all_paid:
            items.append(AnalysisItem(
                icon_type="checkmark",
                text="All property taxes for current cycles confirmed as paid.",
            ))
        else:
            unpaid = [y.year for y in report.tax_info.years if y.status != "PAID"]
            items.append(AnalysisItem(
                icon_type="warning",
                text=f"Outstanding taxes found for year(s): {', '.join(unpaid)}.",
            ))

    # Plat reference
    if report.plat_references:
        most_recent = next((p for p in report.plat_references if p.most_recent), None)
        if most_recent:
            items.append(AnalysisItem(
                icon_type="info",
                text=f"Subject parcel identified on Plat {most_recent.reference}.",
            ))

    # Mortgages
    if report.mortgages:
        count = len(report.mortgages)
        items.append(AnalysisItem(
            icon_type="info",
            text=f"{count} active mortgage{'s' if count > 1 else ''} identified against the property.",
        ))

    # Judgments
    if report.judgments:
        items.append(AnalysisItem(
            icon_type="warning",
            text=f"{len(report.judgments)} judgment{'s' if len(report.judgments) > 1 else ''} found. Review recommended.",
        ))

    report.analysis_items = items


def parse_text_file(filepath: str) -> ReportData:
    """Parse a raw text file into a ReportData object."""
    with open(filepath, "r") as f:
        text = f.read()

    sections = _split_sections(text)
    report = ReportData()

    # Parse generated date from title section
    if "Title Summary Report" in sections:
        _parse_generated_date(sections["Title Summary Report"], report)

    if "Order Information" in sections:
        _parse_order_info(sections["Order Information"], report)

    if "Property Information" in sections:
        _parse_property_info(sections["Property Information"], report)

    if "Current Owner Information" in sections:
        _parse_owners(sections["Current Owner Information"], report)

    if "General Comments" in sections:
        _parse_general_comments(sections["General Comments"], report)

    if "Vesting Deeds" in sections:
        _parse_vesting_deeds(sections["Vesting Deeds"], report)

    if "Estates" in sections:
        estates = sections["Estates"].strip()
        if estates.lower() != "no data found":
            report.estates_notes = estates

    if "Tax Information" in sections:
        _parse_tax_info(sections["Tax Information"], report)

    if "Mortgages" in sections:
        _parse_mortgages(sections["Mortgages"], report)

    if "Judgments" in sections:
        _parse_judgments(sections["Judgments"], report)

    if "Liens" in sections:
        _parse_ucc_filings(sections["Liens"], report)

    if "UCC Filings" in sections:
        _parse_ucc_filings(sections["UCC Filings"], report)

    if "Restrictions" in sections:
        _parse_restrictions(sections["Restrictions"], report)

    if "Easements" in sections:
        _parse_easements(sections["Easements"], report)

    # Set generated date if not found
    if not report.generated_date:
        report.generated_date = datetime.now().strftime("%B %d, %Y")

    # Auto-generate analysis
    _generate_analysis(report)

    return report


if __name__ == "__main__":
    import json
    import sys

    filepath = sys.argv[1] if len(sys.argv) > 1 else "sample_input.txt"
    data = parse_text_file(filepath)
    print(json.dumps(data.to_dict(), indent=2))
