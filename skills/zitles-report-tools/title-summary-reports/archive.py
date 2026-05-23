"""Archive storage, recall, and revision for generated reports."""

import json
import os
import shutil

from schema import ReportData
from renderer import render_pdf

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ARCHIVE_DIR = os.path.join(BASE_DIR, "archive")


def _ensure_archive_dir() -> None:
    os.makedirs(ARCHIVE_DIR, exist_ok=True)


def _order_dir(order_number: str) -> str:
    safe_name = order_number.replace("/", "-").replace("\\", "-")
    return os.path.join(ARCHIVE_DIR, safe_name)


def save_report(data: ReportData, pdf_path: str) -> str:
    """Save report data and PDF to the archive. Returns archive directory path."""
    _ensure_archive_dir()
    order_dir = _order_dir(data.order_number)
    os.makedirs(order_dir, exist_ok=True)

    # Save structured data
    data_path = os.path.join(order_dir, "data.json")
    with open(data_path, "w") as f:
        json.dump(data.to_dict(), f, indent=2)

    # Copy PDF
    archive_pdf = os.path.join(order_dir, "report.pdf")
    if os.path.abspath(pdf_path) != os.path.abspath(archive_pdf):
        shutil.copy2(pdf_path, archive_pdf)

    return order_dir


def load_report(order_number: str) -> ReportData:
    """Load report data from the archive."""
    order_dir = _order_dir(order_number)
    data_path = os.path.join(order_dir, "data.json")

    if not os.path.exists(data_path):
        raise FileNotFoundError(f"No archived report found for order: {order_number}")

    with open(data_path, "r") as f:
        return ReportData.from_dict(json.load(f))


def list_reports() -> list[dict]:
    """List all archived reports with summary info."""
    _ensure_archive_dir()
    reports = []

    for name in sorted(os.listdir(ARCHIVE_DIR)):
        order_dir = os.path.join(ARCHIVE_DIR, name)
        if not os.path.isdir(order_dir):
            continue

        data_path = os.path.join(order_dir, "data.json")
        if not os.path.exists(data_path):
            continue

        with open(data_path, "r") as f:
            data = json.load(f)

        reports.append({
            "order_number": data.get("order_number", name),
            "generated_date": data.get("generated_date", ""),
            "property_address": data.get("property_address", ""),
            "city": data.get("city", ""),
            "state": data.get("state", ""),
            "owners": data.get("owners", ""),
            "has_pdf": os.path.exists(os.path.join(order_dir, "report.pdf")),
        })

    return reports


def regenerate_report(order_number: str) -> str:
    """Re-generate PDF from archived data. Returns new PDF path."""
    data = load_report(order_number)
    order_dir = _order_dir(order_number)
    pdf_path = os.path.join(order_dir, "report.pdf")
    render_pdf(data, pdf_path)
    return pdf_path


def export_json(order_number: str) -> str:
    """Export archived report data as formatted JSON string."""
    data = load_report(order_number)
    return json.dumps(data.to_dict(), indent=2)


def update_report(order_number: str, updates: dict) -> ReportData:
    """Update specific fields in archived report data. Returns updated ReportData."""
    data = load_report(order_number)
    current = data.to_dict()
    current.update(updates)
    updated = ReportData.from_dict(current)

    order_dir = _order_dir(order_number)
    data_path = os.path.join(order_dir, "data.json")
    with open(data_path, "w") as f:
        json.dump(updated.to_dict(), f, indent=2)

    return updated
