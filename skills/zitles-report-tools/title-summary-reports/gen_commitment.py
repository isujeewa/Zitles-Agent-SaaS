#!/usr/bin/env python3
"""Generate a title commitment PDF from a JSON data file."""

import argparse
import base64
import json
import os
import sys

import pdfkit
from jinja2 import Environment, FileSystemLoader

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
TEMPLATES_DIR = os.path.join(BASE_DIR, "templates")
ASSETS_DIR = os.path.join(BASE_DIR, "assets")


def _load_css():
    with open(os.path.join(TEMPLATES_DIR, "style.css")) as f:
        return f.read()


def _load_logo_base64():
    logo_path = os.path.join(ASSETS_DIR, "logo.png")
    if not os.path.exists(logo_path):
        return ""
    with open(logo_path, "rb") as f:
        return base64.b64encode(f.read()).decode("utf-8")


def generate(data_path: str, output_path: str):
    with open(data_path) as f:
        data = json.load(f)

    # Wrap in simple namespace for template access
    class D(dict):
        __getattr__ = dict.__getitem__

    def wrap(obj):
        if isinstance(obj, dict):
            return D({k: wrap(v) for k, v in obj.items()})
        if isinstance(obj, list):
            return [wrap(i) for i in obj]
        return obj

    data = wrap(data)
    env = Environment(loader=FileSystemLoader(TEMPLATES_DIR))
    template = env.get_template("commitment.html")
    html = template.render(data=data, css=_load_css(), logo_data=_load_logo_base64())

    prop_ref = data.get("property_address", "").upper()
    options = {
        "page-size": "Letter",
        "margin-top": "10mm",
        "margin-right": "12mm",
        "margin-bottom": "14mm",
        "margin-left": "12mm",
        "footer-left": f"REF: {prop_ref}",
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
    print(f"Done! PDF: {output_path}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("data_file")
    parser.add_argument("-o", "--output", required=True)
    args = parser.parse_args()
    generate(args.data_file, args.output)
