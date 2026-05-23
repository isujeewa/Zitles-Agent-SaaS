#!/usr/bin/env python3
"""Split a merged deed PDF by bookmarks and OCR each deed in parallel."""

import io
import json
import os
import sys
import time
import concurrent.futures
from PyPDF2 import PdfReader, PdfWriter
from google.cloud import vision

MAX_WORKERS = 20
BATCH_SIZE = 5  # Vision API max pages per request
MAX_RETRIES = 3


def get_deed_ranges(reader):
    """Extract deed page ranges from PDF bookmarks."""
    deeds = []
    total = len(reader.pages)

    def walk(outline, level=0):
        for item in outline:
            if isinstance(item, list):
                walk(item, level + 1)
            elif level == 1:  # Child bookmarks = individual deeds
                page = reader.get_destination_page_number(item)
                deeds.append({"title": item.title.strip(), "start": page})

    if reader.outline:
        walk(reader.outline)

    # Set end pages
    for i, d in enumerate(deeds):
        d["end"] = deeds[i + 1]["start"] if i + 1 < len(deeds) else total

    return deeds


def extract_pages_bytes(reader, start, end):
    """Extract page range into PDF bytes."""
    writer = PdfWriter()
    for i in range(start, min(end, len(reader.pages))):
        writer.add_page(reader.pages[i])
    buf = io.BytesIO()
    writer.write(buf)
    return buf.getvalue()


def ocr_pdf_bytes(pdf_bytes):
    """OCR a small PDF via Vision API with retry."""
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            client = vision.ImageAnnotatorClient()
            input_config = vision.InputConfig(content=pdf_bytes, mime_type="application/pdf")
            feature = vision.Feature(type_=vision.Feature.Type.DOCUMENT_TEXT_DETECTION)
            request = vision.AnnotateFileRequest(input_config=input_config, features=[feature])
            response = client.batch_annotate_files(requests=[request])

            texts = []
            for file_resp in response.responses:
                for page_resp in file_resp.responses:
                    text = page_resp.full_text_annotation.text if page_resp.full_text_annotation else ""
                    texts.append(text)
            return "\n".join(texts)
        except Exception as e:
            if attempt < MAX_RETRIES:
                wait = attempt * 5
                time.sleep(wait)
            else:
                return f"[OCR FAILED: {e.__class__.__name__}]"


def ocr_deed(args):
    """OCR a single deed (may need multiple batches if > 5 pages)."""
    deed_info, reader = args
    start, end, title = deed_info["start"], deed_info["end"], deed_info["title"]
    num_pages = end - start

    all_text = []
    for chunk_start in range(start, end, BATCH_SIZE):
        chunk_end = min(chunk_start + BATCH_SIZE, end)
        pdf_bytes = extract_pages_bytes(reader, chunk_start, chunk_end)
        text = ocr_pdf_bytes(pdf_bytes)
        all_text.append(text)

    return {
        "title": title,
        "start_page": start + 1,
        "end_page": end,
        "num_pages": num_pages,
        "text": "\n\n".join(all_text),
    }


def main():
    if len(sys.argv) < 2:
        print("Usage: python ocr_deeds.py <input.pdf> [output.json]", flush=True)
        sys.exit(1)

    pdf_path = sys.argv[1]
    output_path = sys.argv[2] if len(sys.argv) > 2 else pdf_path.rsplit(".", 1)[0] + "_deeds.json"

    t0 = time.time()
    reader = PdfReader(pdf_path)
    total_pages = len(reader.pages)
    print(f"PDF: {total_pages} pages, {os.path.getsize(pdf_path) / 1024 / 1024:.1f} MB", flush=True)

    deeds = get_deed_ranges(reader)
    print(f"Found {len(deeds)} deeds via bookmarks:", flush=True)
    for d in deeds:
        print(f"  [{d['title']}] pages {d['start']+1}-{d['end']} ({d['end']-d['start']} pp)", flush=True)

    # OCR all deeds in parallel
    print(f"\nOCRing with {MAX_WORKERS} parallel workers...", flush=True)

    results = []
    done_count = 0
    with concurrent.futures.ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        future_map = {}
        for deed in deeds:
            f = executor.submit(ocr_deed, (deed, reader))
            future_map[f] = deed["title"]

        for future in concurrent.futures.as_completed(future_map):
            result = future.result()
            results.append(result)
            done_count += 1
            elapsed = time.time() - t0
            print(f"  [{done_count}/{len(deeds)}] {future_map[future]} — {result['num_pages']} pages — {elapsed:.0f}s elapsed", flush=True)

    # Sort by start page (original order)
    results.sort(key=lambda x: x["start_page"])

    # Write JSON output
    with open(output_path, "w") as f:
        json.dump(results, f, indent=2)

    # Also write plain text version
    txt_path = output_path.rsplit(".", 1)[0] + ".txt"
    with open(txt_path, "w") as f:
        for deed in results:
            f.write(f"{'='*80}\n")
            f.write(f"DEED: {deed['title']} (pages {deed['start_page']}-{deed['end_page']})\n")
            f.write(f"{'='*80}\n\n")
            f.write(deed["text"])
            f.write("\n\n")

    elapsed = time.time() - t0
    total_deed_pages = sum(d["num_pages"] for d in results)
    failed = sum(1 for d in results if "[OCR FAILED" in d["text"])
    print(f"\nDone! {len(results)} deeds ({total_deed_pages} pages) OCR'd in {elapsed:.1f}s ({total_deed_pages/(elapsed/60):.0f} ppm)", flush=True)
    if failed:
        print(f"  WARNING: {failed} deeds had OCR failures", flush=True)
    print(f"JSON: {output_path}", flush=True)
    print(f"Text: {txt_path}", flush=True)


if __name__ == "__main__":
    main()
