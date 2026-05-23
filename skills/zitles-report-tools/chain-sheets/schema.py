"""Data models for Chain Sheet reports."""

from dataclasses import dataclass, field


@dataclass
class ChainLink:
    grantee: str = ""
    grantor: str = ""
    book: str = ""
    page: str = ""
    recorded_date: str = ""
    instrument_type: str = ""
    parcel_id: str = ""
    consideration: str = ""
    notes: str = ""

    def to_dict(self) -> dict:
        return {k: getattr(self, k) for k in self.__dataclass_fields__}

    @classmethod
    def from_dict(cls, d: dict) -> "ChainLink":
        return cls(**{k: d.get(k, "") for k in cls.__dataclass_fields__})


@dataclass
class ChainBranch:
    label: str = ""
    chain: list[ChainLink] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {"label": self.label, "chain": [c.to_dict() for c in self.chain]}

    @classmethod
    def from_dict(cls, d: dict) -> "ChainBranch":
        return cls(
            label=d.get("label", ""),
            chain=[ChainLink.from_dict(c) for c in d.get("chain", [])],
        )


@dataclass
class AppendixItem:
    book: str = ""
    page: str = ""
    grantor: str = ""

    def to_dict(self) -> dict:
        return {k: getattr(self, k) for k in self.__dataclass_fields__}

    @classmethod
    def from_dict(cls, d: dict) -> "AppendixItem":
        return cls(**{k: d.get(k, "") for k in cls.__dataclass_fields__})


@dataclass
class Appendix:
    label: str = ""
    items: list[AppendixItem] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {"label": self.label, "items": [i.to_dict() for i in self.items]}

    @classmethod
    def from_dict(cls, d: dict) -> "Appendix":
        return cls(
            label=d.get("label", ""),
            items=[AppendixItem.from_dict(i) for i in d.get("items", [])],
        )


@dataclass
class ChainData:
    property_address: str = ""
    city: str = ""
    state: str = ""
    zip_code: str = ""
    county: str = ""
    parcel_id: str = ""
    legal_description: str = ""
    generated_date: str = ""
    chain: list[ChainLink] = field(default_factory=list)
    branches: list[ChainBranch] = field(default_factory=list)
    footnotes: list[str] = field(default_factory=list)
    appendices: list[Appendix] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "property_address": self.property_address,
            "city": self.city,
            "state": self.state,
            "zip_code": self.zip_code,
            "county": self.county,
            "parcel_id": self.parcel_id,
            "legal_description": self.legal_description,
            "generated_date": self.generated_date,
            "chain": [c.to_dict() for c in self.chain],
            "branches": [b.to_dict() for b in self.branches],
            "footnotes": self.footnotes,
            "appendices": [a.to_dict() for a in self.appendices],
        }

    @classmethod
    def from_dict(cls, d: dict) -> "ChainData":
        return cls(
            property_address=d.get("property_address", ""),
            city=d.get("city", ""),
            state=d.get("state", ""),
            zip_code=d.get("zip_code", ""),
            county=d.get("county", ""),
            parcel_id=d.get("parcel_id", ""),
            legal_description=d.get("legal_description", ""),
            generated_date=d.get("generated_date", ""),
            chain=[ChainLink.from_dict(c) for c in d.get("chain", [])],
            branches=[ChainBranch.from_dict(b) for b in d.get("branches", [])],
            footnotes=d.get("footnotes", []),
            appendices=[Appendix.from_dict(a) for a in d.get("appendices", [])],
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
