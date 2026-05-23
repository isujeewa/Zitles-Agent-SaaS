#!/usr/bin/env python3
"""CLI entry point for Title Summary Report generation."""

import argparse
import json
import os
import sys

from schema import ReportData
from parser import parse_text_file
from renderer import render_pdf
from archive import save_report, load_report, list_reports, regenerate_report, export_json

BASE_DIR = os.path.dirname(os.path.abspath(__file__))


def cmd_from_text(args):
    """Parse a text file and generate PDF."""
    print(f"Parsing text file: {args.input}")
    data = parse_text_file(args.input)

    output = args.output
    if not output:
        output = os.path.join(BASE_DIR, f"report-{data.order_number or 'output'}.pdf")

    print(f"Generating PDF: {output}")
    render_pdf(data, output)

    print(f"Archiving report: {data.order_number}")
    archive_dir = save_report(data, output)

    print(f"\nDone!")
    print(f"  PDF:     {output}")
    print(f"  Archive: {archive_dir}")


def cmd_from_json(args):
    """Generate PDF from a JSON data file."""
    print(f"Loading JSON: {args.input}")
    with open(args.input, "r") as f:
        raw = json.load(f)
    data = ReportData.from_dict(raw)
    # Pass through optional report_title for custom headers
    if "report_title" in raw:
        data.report_title = raw["report_title"]

    output = args.output
    if not output:
        output = os.path.join(BASE_DIR, f"report-{data.order_number or 'output'}.pdf")

    print(f"Generating PDF: {output}")
    render_pdf(data, output)

    print(f"Archiving report: {data.order_number}")
    archive_dir = save_report(data, output)

    print(f"\nDone!")
    print(f"  PDF:     {output}")
    print(f"  Archive: {archive_dir}")


def cmd_list(args):
    """List all archived reports."""
    reports = list_reports()
    if not reports:
        print("No archived reports found.")
        return

    print(f"{'Order':<15} {'Date':<22} {'Address':<35} {'Owners'}")
    print("-" * 95)
    for r in reports:
        addr = f"{r['property_address']}, {r['city']}, {r['state']}" if r['city'] else r['property_address']
        print(f"{r['order_number']:<15} {r['generated_date']:<22} {addr:<35} {r['owners'][:30]}")


def cmd_regenerate(args):
    """Re-generate PDF from archived data."""
    print(f"Loading archived data for: {args.order}")
    pdf_path = regenerate_report(args.order)
    print(f"PDF regenerated: {pdf_path}")


def cmd_export_json(args):
    """Export archived data as JSON."""
    output = export_json(args.order)
    if args.output:
        with open(args.output, "w") as f:
            f.write(output)
        print(f"JSON exported to: {args.output}")
    else:
        print(output)


def main():
    parser = argparse.ArgumentParser(
        description="Title Summary Report Generator — Zitles",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # from-text
    p_text = subparsers.add_parser("from-text", help="Parse text file and generate PDF")
    p_text.add_argument("input", help="Path to input .txt file")
    p_text.add_argument("-o", "--output", help="Output PDF path (default: auto-named)")
    p_text.set_defaults(func=cmd_from_text)

    # from-json
    p_json = subparsers.add_parser("from-json", help="Generate PDF from JSON data file")
    p_json.add_argument("input", help="Path to input .json file")
    p_json.add_argument("-o", "--output", help="Output PDF path (default: auto-named)")
    p_json.set_defaults(func=cmd_from_json)

    # list
    p_list = subparsers.add_parser("list", help="List all archived reports")
    p_list.set_defaults(func=cmd_list)

    # regenerate
    p_regen = subparsers.add_parser("regenerate", help="Re-generate PDF from archived data")
    p_regen.add_argument("order", help="Order number to regenerate")
    p_regen.set_defaults(func=cmd_regenerate)

    # export-json
    p_export = subparsers.add_parser("export-json", help="Export archived data as JSON")
    p_export.add_argument("order", help="Order number to export")
    p_export.add_argument("-o", "--output", help="Output JSON file path (default: stdout)")
    p_export.set_defaults(func=cmd_export_json)

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    args.func(args)


if __name__ == "__main__":
    main()
