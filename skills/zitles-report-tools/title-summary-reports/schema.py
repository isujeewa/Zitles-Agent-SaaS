"""Data models for Title Summary Reports."""

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class TaxYear:
    year: str = ""
    status: str = ""  # "PAID", "UNPAID", "PENDING"
    amount: str = ""

    def to_dict(self) -> dict:
        return {"year": self.year, "status": self.status, "amount": self.amount}

    @classmethod
    def from_dict(cls, d: dict) -> "TaxYear":
        return cls(year=d.get("year", ""), status=d.get("status", ""), amount=d.get("amount", ""))


@dataclass
class TaxInfo:
    pending_tax_sale: bool = False
    delinquent: bool = False
    roll_back: bool = False
    exempt: bool = False
    years: list[TaxYear] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "pending_tax_sale": self.pending_tax_sale,
            "delinquent": self.delinquent,
            "roll_back": self.roll_back,
            "exempt": self.exempt,
            "years": [y.to_dict() for y in self.years],
        }

    @classmethod
    def from_dict(cls, d: dict) -> "TaxInfo":
        return cls(
            pending_tax_sale=d.get("pending_tax_sale", False),
            delinquent=d.get("delinquent", False),
            roll_back=d.get("roll_back", False),
            exempt=d.get("exempt", False),
            years=[TaxYear.from_dict(y) for y in d.get("years", [])],
        )


@dataclass
class VestingDeed:
    date: str = ""
    book: str = ""
    page: str = ""
    legal_description: str = ""
    owners: str = ""
    reference: str = ""

    def to_dict(self) -> dict:
        return {
            "date": self.date, "book": self.book, "page": self.page,
            "legal_description": self.legal_description, "owners": self.owners,
            "reference": self.reference,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "VestingDeed":
        return cls(**{k: d.get(k, "") for k in cls.__dataclass_fields__})


@dataclass
class MortgageAssignment:
    date: str = ""
    book: str = ""
    page: str = ""
    assignee: str = ""
    notes: str = ""

    def to_dict(self) -> dict:
        return {
            "date": self.date, "book": self.book, "page": self.page,
            "assignee": self.assignee, "notes": self.notes,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "MortgageAssignment":
        return cls(**{k: d.get(k, "") for k in cls.__dataclass_fields__})


@dataclass
class Mortgage:
    lender: str = ""
    amount: str = ""
    date: str = ""
    book: str = ""
    page: str = ""
    notes: str = ""
    assignments: list[MortgageAssignment] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "lender": self.lender, "amount": self.amount, "date": self.date,
            "book": self.book, "page": self.page, "notes": self.notes,
            "assignments": [a.to_dict() for a in self.assignments],
        }

    @classmethod
    def from_dict(cls, d: dict) -> "Mortgage":
        return cls(
            lender=d.get("lender", ""), amount=d.get("amount", ""),
            date=d.get("date", ""), book=d.get("book", ""), page=d.get("page", ""),
            notes=d.get("notes", ""),
            assignments=[MortgageAssignment.from_dict(a) for a in d.get("assignments", [])],
        )


@dataclass
class Judgment:
    parties: str = ""
    amount: str = ""
    case_number: str = ""
    book: str = ""
    page: str = ""
    notes: str = ""

    def to_dict(self) -> dict:
        return {k: getattr(self, k) for k in self.__dataclass_fields__}

    @classmethod
    def from_dict(cls, d: dict) -> "Judgment":
        return cls(**{k: d.get(k, "") for k in cls.__dataclass_fields__})


@dataclass
class Lien:
    type: str = ""
    holder: str = ""
    amount: str = ""
    date: str = ""
    book: str = ""
    page: str = ""
    notes: str = ""

    def to_dict(self) -> dict:
        return {k: getattr(self, k) for k in self.__dataclass_fields__}

    @classmethod
    def from_dict(cls, d: dict) -> "Lien":
        return cls(**{k: d.get(k, "") for k in cls.__dataclass_fields__})


@dataclass
class UCCFiling:
    filing_number: str = ""
    lender: str = ""
    address: str = ""
    book: str = ""
    page: str = ""
    notes: str = ""

    def to_dict(self) -> dict:
        return {k: getattr(self, k) for k in self.__dataclass_fields__}

    @classmethod
    def from_dict(cls, d: dict) -> "UCCFiling":
        return cls(**{k: d.get(k, "") for k in cls.__dataclass_fields__})


@dataclass
class Restriction:
    date: str = ""
    book: str = ""
    page: str = ""
    description: str = ""
    party: str = ""
    reference: str = ""

    def to_dict(self) -> dict:
        return {k: getattr(self, k) for k in self.__dataclass_fields__}

    @classmethod
    def from_dict(cls, d: dict) -> "Restriction":
        return cls(**{k: d.get(k, "") for k in cls.__dataclass_fields__})


@dataclass
class Easement:
    date: str = ""
    book: str = ""
    page: str = ""
    type: str = ""
    holder: str = ""
    notes: str = ""
    reference: str = ""

    def to_dict(self) -> dict:
        return {k: getattr(self, k) for k in self.__dataclass_fields__}

    @classmethod
    def from_dict(cls, d: dict) -> "Easement":
        return cls(**{k: d.get(k, "") for k in cls.__dataclass_fields__})


@dataclass
class Lease:
    date: str = ""
    book: str = ""
    page: str = ""
    lessee: str = ""
    lessor: str = ""
    term: str = ""
    rent: str = ""
    notes: str = ""

    def to_dict(self) -> dict:
        return {k: getattr(self, k) for k in self.__dataclass_fields__}

    @classmethod
    def from_dict(cls, d: dict) -> "Lease":
        return cls(**{k: d.get(k, "") for k in cls.__dataclass_fields__})


@dataclass
class PlatReference:
    reference: str = ""
    most_recent: bool = False

    def to_dict(self) -> dict:
        return {"reference": self.reference, "most_recent": self.most_recent}

    @classmethod
    def from_dict(cls, d: dict) -> "PlatReference":
        return cls(reference=d.get("reference", ""), most_recent=d.get("most_recent", False))


@dataclass
class LienDetail:
    lien_id: str = ""
    date_filed: str = ""
    party: str = ""
    ssn_last4: str = ""
    amount: str = ""
    flagged: bool = False

    def to_dict(self) -> dict:
        d = {k: getattr(self, k) for k in self.__dataclass_fields__}
        return d

    @classmethod
    def from_dict(cls, d: dict) -> "LienDetail":
        return cls(
            lien_id=d.get("lien_id", ""),
            date_filed=d.get("date_filed", ""),
            party=d.get("party", ""),
            ssn_last4=d.get("ssn_last4", ""),
            amount=d.get("amount", ""),
            flagged=d.get("flagged", False),
        )


@dataclass
class AnalysisItem:
    icon_type: str = "checkmark"  # "checkmark", "info", "warning"
    text: str = ""

    def to_dict(self) -> dict:
        return {"icon_type": self.icon_type, "text": self.text}

    @classmethod
    def from_dict(cls, d: dict) -> "AnalysisItem":
        return cls(icon_type=d.get("icon_type", "checkmark"), text=d.get("text", ""))


@dataclass
class ReportData:
    # Order info
    order_number: str = ""
    report_title: str = ""
    search_type: str = ""
    search_start_date: str = ""
    search_end_date: str = ""
    generated_date: str = ""

    # Property info
    property_address: str = ""
    city: str = ""
    state: str = ""
    zip_code: str = ""
    county: str = ""
    parcel_id: str = ""

    # Ownership & Vesting
    owners: str = ""
    vesting_deeds: list[VestingDeed] = field(default_factory=list)

    # Estates
    estates_notes: str = ""

    # Tax
    tax_info: Optional[TaxInfo] = None

    # Financial
    mortgages: list[Mortgage] = field(default_factory=list)
    judgments: list[Judgment] = field(default_factory=list)
    liens: list[Lien] = field(default_factory=list)

    # UCC & Legal
    ucc_filings: list[UCCFiling] = field(default_factory=list)

    # Plat references
    plat_references: list[PlatReference] = field(default_factory=list)

    # Restrictions, Easements & Leases (appendix)
    restrictions: list[Restriction] = field(default_factory=list)
    easements: list[Easement] = field(default_factory=list)
    leases: list[Lease] = field(default_factory=list)

    # Lien details (full table for dedicated page)
    lien_details: list[LienDetail] = field(default_factory=list)

    # Analysis
    analysis_items: list[AnalysisItem] = field(default_factory=list)

    # General comments
    general_comments: str = ""

    def to_dict(self) -> dict:
        return {
            "order_number": self.order_number,
            "report_title": self.report_title,
            "search_type": self.search_type,
            "search_start_date": self.search_start_date,
            "search_end_date": self.search_end_date,
            "generated_date": self.generated_date,
            "property_address": self.property_address,
            "city": self.city,
            "state": self.state,
            "zip_code": self.zip_code,
            "county": self.county,
            "parcel_id": self.parcel_id,
            "owners": self.owners,
            "vesting_deeds": [v.to_dict() for v in self.vesting_deeds],
            "estates_notes": self.estates_notes,
            "tax_info": self.tax_info.to_dict() if self.tax_info else None,
            "mortgages": [m.to_dict() for m in self.mortgages],
            "judgments": [j.to_dict() for j in self.judgments],
            "liens": [l.to_dict() for l in self.liens],
            "ucc_filings": [u.to_dict() for u in self.ucc_filings],
            "plat_references": [p.to_dict() for p in self.plat_references],
            "restrictions": [r.to_dict() for r in self.restrictions],
            "easements": [e.to_dict() for e in self.easements],
            "leases": [l.to_dict() for l in self.leases],
            "lien_details": [ld.to_dict() for ld in self.lien_details],
            "analysis_items": [a.to_dict() for a in self.analysis_items],
            "general_comments": self.general_comments,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "ReportData":
        return cls(
            order_number=d.get("order_number", ""),
            report_title=d.get("report_title", ""),
            search_type=d.get("search_type", ""),
            search_start_date=d.get("search_start_date", ""),
            search_end_date=d.get("search_end_date", ""),
            generated_date=d.get("generated_date", ""),
            property_address=d.get("property_address", ""),
            city=d.get("city", ""),
            state=d.get("state", ""),
            zip_code=d.get("zip_code", ""),
            county=d.get("county", ""),
            parcel_id=d.get("parcel_id", ""),
            owners=d.get("owners", ""),
            vesting_deeds=(
                [VestingDeed.from_dict(v) for v in d["vesting_deeds"]]
                if d.get("vesting_deeds")
                else ([VestingDeed.from_dict(d["vesting_deed"])] if d.get("vesting_deed") else [])
            ),
            estates_notes=d.get("estates_notes", ""),
            tax_info=TaxInfo.from_dict(d["tax_info"]) if d.get("tax_info") else None,
            mortgages=[Mortgage.from_dict(m) for m in d.get("mortgages", [])],
            judgments=[Judgment.from_dict(j) for j in d.get("judgments", [])],
            liens=[Lien.from_dict(l) for l in d.get("liens", [])],
            ucc_filings=[UCCFiling.from_dict(u) for u in d.get("ucc_filings", [])],
            plat_references=[PlatReference.from_dict(p) for p in d.get("plat_references", [])],
            restrictions=[Restriction.from_dict(r) for r in d.get("restrictions", [])],
            easements=[Easement.from_dict(e) for e in d.get("easements", [])],
            leases=[Lease.from_dict(l) for l in d.get("leases", [])],
            lien_details=[LienDetail.from_dict(ld) for ld in d.get("lien_details", [])],
            analysis_items=[AnalysisItem.from_dict(a) for a in d.get("analysis_items", [])],
            general_comments=d.get("general_comments", ""),
        )

    @property
    def full_address(self) -> str:
        parts = [self.property_address]
        city_state = ", ".join(filter(None, [self.city, self.state]))
        if city_state:
            parts.append(city_state)
        if self.zip_code:
            parts[-1] = parts[-1] + " " + self.zip_code
        return ", ".join(parts) if len(parts) > 1 else parts[0]

    @property
    def search_window(self) -> str:
        if self.search_start_date and self.search_end_date:
            return f"{self.search_start_date} — {self.search_end_date}"
        return ""

    @property
    def has_appendix_data(self) -> bool:
        return bool(self.easements) or bool(self.restrictions) or bool(self.leases)
