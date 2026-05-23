"""Render ChainData into PDF using Jinja2 + pdfkit."""

import base64
import os

import pdfkit
from jinja2 import Environment, FileSystemLoader

from schema import ChainData

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


def render_pdf(data: ChainData, output_path: str) -> str:
    """Generate a Chain Sheet PDF and return the output file path."""
    env = Environment(loader=FileSystemLoader(TEMPLATES_DIR))
    css = _load_css()
    logo_data = _load_logo_base64()

    template = env.get_template("chain.html")
    html = template.render(data=data, css=css, logo_data=logo_data)

    property_ref = data.property_address.upper() if data.property_address else ""

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

    pdfkit.from_string(html, output_path, options=options)
    return output_path
