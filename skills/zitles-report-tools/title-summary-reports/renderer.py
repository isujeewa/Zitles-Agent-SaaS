"""Render ReportData into PDF using Jinja2 + pdfkit."""

import base64
import os
import tempfile

import pdfkit
from jinja2 import Environment, FileSystemLoader  # noqa: F401

from schema import ReportData

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
TEMPLATES_DIR = os.path.join(BASE_DIR, "templates")
ASSETS_DIR = os.path.join(BASE_DIR, "assets")


def _load_css() -> str:
    css_path = os.path.join(TEMPLATES_DIR, "style.css")
    with open(css_path, "r") as f:
        return f.read()


def _load_logo_base64() -> str:
    logo_path = os.path.join(ASSETS_DIR, "logo.png")
    if not os.path.exists(logo_path):
        return ""
    with open(logo_path, "rb") as f:
        return base64.b64encode(f.read()).decode("utf-8")


def render_pdf(data: ReportData, output_path: str) -> str:
    """Generate a PDF report and return the output file path."""
    env = Environment(loader=FileSystemLoader(TEMPLATES_DIR))
    css = _load_css()
    logo_data = _load_logo_base64()

    # Compute lien total for report template
    lien_total = ""
    if data.lien_details:
        total = 0.0
        for ld in data.lien_details:
            try:
                total += float(ld.amount.replace("$", "").replace(",", ""))
            except (ValueError, AttributeError):
                pass
        lien_total = f"${total:,.2f}"

    # Compute sum of the primary `liens` list for the J&L page total row
    liens_sum = ""
    if data.liens:
        s = 0.0
        for l in data.liens:
            try:
                s += float(l.amount.replace("$", "").replace(",", "").split()[0])
            except (ValueError, AttributeError, IndexError):
                pass
        if s:
            liens_sum = f"${s:,.2f}"

    # Render page 1
    report_template = env.get_template("report.html")
    report_title = getattr(data, 'report_title', None)
    page1_html = report_template.render(data=data, css=css, logo_data=logo_data, lien_total=lien_total, liens_sum=liens_sum, report_title=report_title)

    import re

    # If appendix data exists, render it and inject into page 1 HTML before </body>
    # When a JL-page exists AND restrictions/easements are present, those tables
    # have already been merged onto the JL-page (report.html), so skip the appendix
    # render entirely to keep everything on one page.
    has_jl_page = bool(data.judgments or data.liens or data.lien_details)
    merge_re_into_jl = has_jl_page and (bool(data.restrictions) or bool(data.easements))
    if data.has_appendix_data and not merge_re_into_jl:
        appendix_template = env.get_template("appendix.html")
        appendix_html = appendix_template.render(data=data, css=css, logo_data=logo_data)
        body_match = re.search(r'<body[^>]*>(.*?)</body>', appendix_html, re.DOTALL)
        if body_match:
            appendix_body = body_match.group(1)
            page1_html = page1_html.replace('</body>', appendix_body + '\n</body>')

    # Lien details are now rendered inline on the judgments & liens page (report.html)
    # The separate liens-detail.html page is kept for standalone use but skipped here.

    # Footer using wkhtmltopdf built-in text substitution
    property_ref = data.property_address.upper() if data.property_address else ""

    # pdfkit options
    options = {
        "page-size": "Letter",
        "margin-top": "10mm",
        "margin-right": "12mm",
        "margin-bottom": "14mm",
        "margin-left": "12mm",
        "footer-left": f"REF: {property_ref}",
        "footer-right": "PAGE [page] OF [topage]",
        "footer-font-size": "7",
        "footer-font-name": "Helvetica",
        "footer-spacing": "5",
        "enable-local-file-access": "",
        "print-media-type": "",
        "encoding": "UTF-8",
        "no-outline": "",
        "quiet": "",
    }

    # Generate single PDF from combined HTML
    pdfkit.from_string(page1_html, output_path, options=options)

    # Sanitize through Ghostscript to fix wkhtmltopdf's malformed ToUnicode CMap
    # (otherwise text scrambles when the PDF is saved/exported by another viewer).
    _sanitize_pdf(output_path)

    return output_path


def _sanitize_pdf(path: str) -> None:
    import shutil
    import subprocess

    gs = shutil.which("gs")
    if not gs:
        return

    tmp = path + ".gs.tmp"
    try:
        subprocess.run(
            [
                gs, "-q", "-dNOPAUSE", "-dBATCH",
                "-sDEVICE=pdfwrite",
                "-dCompatibilityLevel=1.7",
                "-dPDFSETTINGS=/prepress",
                f"-sOutputFile={tmp}",
                path,
            ],
            check=True,
            capture_output=True,
        )
        os.replace(tmp, path)
    except Exception:
        if os.path.exists(tmp):
            os.remove(tmp)
