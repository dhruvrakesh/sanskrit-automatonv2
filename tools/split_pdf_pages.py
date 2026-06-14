#!/usr/bin/env python3
"""
Split a PDF into single-page PDFs.

Usage examples:
  python split_pdf_pages.py big.pdf
  python split_pdf_pages.py big.pdf -o ./output_pages -p sheet
  python split_pdf_pages.py big.pdf -s 1 -e 4000 --print-every 100
  python split_pdf_pages.py big.pdf --password "mypassword" --metadata
"""

import argparse
import os
import sys
import traceback
from typing import Optional
from pypdf import PdfReader, PdfWriter


def ensure_dir(path):
    os.makedirs(path, exist_ok=True)


def sanitize_prefix(prefix):
    bad = '<>:"/\\|?*'
    for ch in bad:
        prefix = prefix.replace(ch, "_")
    return prefix.strip() or "page"


def split_pdf(
    input_pdf,
    output_dir=None,
    prefix=None,
    start_page=None,
    end_page=None,
    password=None,
    copy_metadata=False,
    print_every=100,
    zero_pad=None,
):
    if not os.path.isfile(input_pdf):
        print(f"ERROR: Input file not found: {input_pdf}", file=sys.stderr)
        return False

    base = os.path.splitext(os.path.basename(input_pdf))[0]
    output_dir = output_dir or f"{base}_pages"
    ensure_dir(output_dir)
    prefix = sanitize_prefix(prefix or base)

    # Load PDF
    try:
        reader = PdfReader(input_pdf)
    except Exception as e:
        print(f"ERROR: Failed to read PDF '{input_pdf}': {e}", file=sys.stderr)
        traceback.print_exc(file=sys.stderr)
        return False

    # Handle encryption
    if getattr(reader, "is_encrypted", False):
        if password:
            try:
                reader.decrypt(password)
            except Exception as e:
                print(f"ERROR: Failed to decrypt: {e}", file=sys.stderr)
                return False
        else:
            # Try empty password first (some PDFs encrypt with empty pw)
            try:
                reader.decrypt("")
            except Exception:
                pass
            if reader.is_encrypted:
                print("ERROR: PDF is encrypted. Provide --password.", file=sys.stderr)
                return False

    try:
        total_pages = len(reader.pages)
    except Exception as e:
        print(f"ERROR: Could not read pages: {e}", file=sys.stderr)
        traceback.print_exc(file=sys.stderr)
        return False

    if total_pages == 0:
        print("ERROR: PDF has zero pages.", file=sys.stderr)
        return False

    start = start_page or 1
    end   = end_page   or total_pages
    if start < 1 or end < 1 or start > total_pages or end > total_pages or start > end:
        print(
            f"ERROR: Invalid page range. PDF has {total_pages} pages. Got start={start}, end={end}.",
            file=sys.stderr,
        )
        return False

    # Zero-padding for filenames
    digits = int(zero_pad) if zero_pad else max(4, len(str(end)))

    # Prepare metadata (optional)
    meta_dict = None
    if copy_metadata:
        try:
            meta = reader.metadata or {}
            meta_dict = {str(k): ("" if v is None else str(v)) for k, v in meta.items()}
        except Exception:
            meta_dict = None

    page_count = end - start + 1
    print(f"Splitting '{input_pdf}' -> '{output_dir}'")
    print(f"Pages: {start}-{end} of {total_pages} (total outputs: {page_count})")
    print(f"Filename pattern: {prefix}_{{page:0{digits}d}}.pdf")

    written = 0
    for idx in range(start - 1, end):
        try:
            writer = PdfWriter()
            writer.add_page(reader.pages[idx])

            if meta_dict:
                try:
                    writer.add_metadata(meta_dict)
                except Exception:
                    pass

            out_name = f"{prefix}_{(idx + 1):0{digits}d}.pdf"
            out_path = os.path.join(output_dir, out_name)

            with open(out_path, "wb") as f:
                writer.write(f)
            written += 1
        except Exception as e:
            print(f"\nERROR: Failed on page {idx + 1}: {e}", file=sys.stderr)
            traceback.print_exc(file=sys.stderr)
            # Continue splitting remaining pages instead of aborting
            continue

        if print_every and written % print_every == 0:
            print(f"  ... {written}/{page_count} pages done")

    print(f"Done. Wrote {written}/{page_count} single-page PDFs to: {output_dir}")
    return written > 0


def parse_args():
    p = argparse.ArgumentParser(description="Split a PDF into single-page PDFs.")
    p.add_argument("input_pdf",      help="Path to the input PDF")
    p.add_argument("-o", "--output-dir",  help="Directory to write single-page PDFs")
    p.add_argument("-p", "--prefix",      help="Filename prefix for output files")
    p.add_argument("-s", "--start",  type=int, help="Start page (1-based, inclusive)")
    p.add_argument("-e", "--end",    type=int, help="End page (1-based, inclusive)")
    p.add_argument("--password",          help="Password for encrypted PDFs")
    p.add_argument("--metadata",    action="store_true", help="Copy document metadata")
    p.add_argument("--print-every", type=int, default=100, help="Print progress every N pages")
    p.add_argument("--zero-pad",    type=int, help="Force this many digits for page numbers")
    return p.parse_args()


if __name__ == "__main__":
    try:
        args = parse_args()
        ok = split_pdf(
            input_pdf=args.input_pdf,
            output_dir=args.output_dir,
            prefix=args.prefix,
            start_page=args.start,
            end_page=args.end,
            password=args.password,
            copy_metadata=args.metadata,
            print_every=args.print_every,
            zero_pad=args.zero_pad,
        )
        sys.exit(0 if ok else 1)
    except Exception as e:
        print(f"\nFATAL ERROR in split_pdf_pages.py: {e}", file=sys.stderr)
        traceback.print_exc(file=sys.stderr)
        sys.exit(1)
