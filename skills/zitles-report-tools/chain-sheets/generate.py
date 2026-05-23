#!/usr/bin/env python3
"""CLI entry point for Chain Sheet generation."""

import argparse
import json
import os
import sys

from schema import ChainData
from renderer import render_pdf

BASE_DIR = os.path.dirname(os.path.abspath(__file__))


def cmd_from_json(args):
    """Generate Chain Sheet PDF from a JSON data file."""
    print(f"Loading JSON: {args.input}")
    with open(args.input, "r") as f:
        raw = json.load(f)
    data = ChainData.from_dict(raw)

    output = args.output
    if not output:
        safe_parcel = data.parcel_id.replace("-", "")
        output = os.path.join(BASE_DIR, f"chain-{safe_parcel}.pdf")

    print(f"Generating PDF: {output}")
    render_pdf(data, output)

    print(f"\nDone!")
    print(f"  PDF: {output}")


def main():
    parser = argparse.ArgumentParser(
        description="Chain Sheet Generator — Zitles",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    p_json = subparsers.add_parser("from-json", help="Generate PDF from JSON data file")
    p_json.add_argument("input", help="Path to input .json file")
    p_json.add_argument("-o", "--output", help="Output PDF path (default: auto-named)")
    p_json.set_defaults(func=cmd_from_json)

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    args.func(args)


if __name__ == "__main__":
    main()
