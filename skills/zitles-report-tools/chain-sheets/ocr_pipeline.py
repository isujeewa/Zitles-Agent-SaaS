#!/usr/bin/env python3
"""OCR a PDF using Google Cloud Vision batch API with parallel workers."""

import io
import os
import sys
import time
import concurrent.futures
from PyPDF2 import PdfReader, PdfWriter
from google.cloud import vision

BATCH_SIZE = 5  # Vision API max pages per request
MAX_WORKERS = 20
MAX_RETRIES = 3


def extract_pages(reader, start, end):
    """Extract a range of pages into bytes."""
    writer = PdfWriter()
    for i in range(start, min(end, len(reader.pages))):
        writer.add_page(reader.pages[i])
    buf = io.BytesIO()
    writer.write(buf)
    return buf.getvalue()


def ocr_batch(args):
    """OCR a batch of pages with retry logic."""
    batch_idx, pdf_bytes, start_page = args
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            client = vision.ImageAnnotatorClient()
            input_config = vision.InputConfig(
                content=pdf_bytes, mime_type="application/pdf"
            )
            feature = vision.Feature(type_=vision.Feature.Type.DOCUMENT_TEXT_DETECTION)
            request = vision.AnnotateFileRequest(
                input_config=input_config, features=[feature]
            )
            response = client.batch_annotate_files(requests=[request])

            results = []
            for file_resp in response.responses:
                for i, page_resp in enumerate(file_resp.responses):
                    page_num = start_page + i + 1
                    text = page_resp.full_text_annotation.text if page_resp.full_text_annotation else ""
                    results.append((page_num, text))
            return results
        except Exception as e:
            if attempt < MAX_RETRIES:
                wait = attempt * 5
                print(f"  [!] Batch {batch_idx} attempt {attempt} failed: {e.__class__.__name__}. Retrying in {wait}s...")
                time.sleep(wait)
            else:
                print(f"  [X] Batch {batch_idx} FAILED after {MAX_RETRIES} attempts: {e}")
                # Return empty text for these pages so pipeline continues
                num_pages = len(PdfReader(io.BytesIO(pdf_bytes)).pages)
                return [(start_page + i + 1, f"[OCR FAILED: {e.__class__.__name__}]") for i in range(num_pages)]


def main():
    if len(sys.argv) < 2:
        print("Usage: python ocr_pipeline.py <input.pdf> [output.txt]")
        sys.exit(1)

    pdf_path = sys.argv[1]
    output_path = sys.argv[2] if len(sys.argv) > 2 else pdf_path.rsplit(".", 1)[0] + "_ocr.txt"

    t0 = time.time()
    reader = PdfReader(pdf_path)
    total_pages = len(reader.pages)
    print(f"PDF: {total_pages} pages, {os.path.getsize(pdf_path) / 1024 / 1024:.1f} MB", flush=True)

    # Build batches
    batches = []
    for start in range(0, total_pages, BATCH_SIZE):
        end = min(start + BATCH_SIZE, total_pages)
        pdf_bytes = extract_pages(reader, start, end)
        batches.append((len(batches), pdf_bytes, start))

    print(f"Created {len(batches)} batches, OCRing with {MAX_WORKERS} workers...", flush=True)

    all_results = []
    done_count = 0
    with concurrent.futures.ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        futures = {executor.submit(ocr_batch, b): b[0] for b in batches}
        for future in concurrent.futures.as_completed(futures):
            batch_results = future.result()
            all_results.extend(batch_results)
            done_count += 1
            pages_done = len(all_results)
            elapsed = time.time() - t0
            rate = pages_done / elapsed if elapsed > 0 else 0
            eta = (total_pages - pages_done) / rate if rate > 0 else 0
            print(f"  Batch {done_count}/{len(batches)} — {pages_done}/{total_pages} pages — {rate:.1f} ppm — ETA {eta:.0f}s", flush=True)

    # Sort by page number and write
    all_results.sort(key=lambda x: x[0])

    with open(output_path, "w") as f:
        for page_num, text in all_results:
            f.write(f"PAGE {page_num}\n")
            f.write("=" * 80 + "\n")
            f.write(text + "\n\n")

    elapsed = time.time() - t0
    failed = sum(1 for _, t in all_results if t.startswith("[OCR FAILED"))
    print(f"\nDone! {total_pages} pages OCR'd in {elapsed:.1f}s ({total_pages/(elapsed/60):.0f} ppm)", flush=True)
    if failed:
        print(f"  WARNING: {failed} pages failed OCR", flush=True)
    print(f"Output: {output_path}", flush=True)


if __name__ == "__main__":
    main()
