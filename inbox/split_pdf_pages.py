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
from pypdf import PdfReader, PdfWriter


def ensure_dir(path: str):
    os.makedirs(path, exist_ok=True)


def sanitize_prefix(prefix: str) -> str:
    # Keep it simple: remove OS-problematic chars
    bad = '<>:"/\\|?*'
    for ch in bad:
        prefix = prefix.replace(ch, "_")
    return prefix.strip() or "page"


def split_pdf(
    input_pdf: str,
    output_dir: str | None = None,
    prefix: str | None = None,
    start_page: int | None = None,  # 1-based inclusive
    end_page: int | None = None,    # 1-based inclusive
    password: str | None = None,
    copy_metadata: bool = False,
    print_every: int = 100,
    zero_pad: int | None = None,
):
    if not os.path.isfile(input_pdf):
        print(f"ERROR: Input file not found: {input_pdf}", file=sys.stderr)
        sys.exit(1)

    base = os.path.splitext(os.path.basename(input_pdf))[0]
    output_dir = output_dir or f"{base}_pages"
    ensure_dir(output_dir)
    prefix = sanitize_prefix(prefix or base)

    # Load PDF
    try:
        reader = PdfReader(input_pdf)
    except Exception as e:
        print(f"ERROR: Failed to read PDF: {e}", file=sys.stderr)
        sys.exit(1)

    # Handle encryption
    if getattr(reader, "is_encrypted", False):
        if password:
            try:
                reader.decrypt(password)
            except Exception as e:
                print(f"ERROR: Failed to decrypt with provided password: {e}", file=sys.stderr)
                sys.exit(2)
        else:
            print("ERROR: PDF is encrypted. Provide --password.", file=sys.stderr)
            sys.exit(2)

    total_pages = len(reader.pages)
    if total_pages == 0:
        print("ERROR: PDF has zero pages.", file=sys.stderr)
        sys.exit(1)

    start = start_page or 1
    end = end_page or total_pages
    if start < 1 or end < 1 or start > total_pages or end > total_pages or start > end:
        print(f"ERROR: Invalid page range. PDF has {total_pages} pages. "
              f"Got start={start}, end={end}.", file=sys.stderr)
        sys.exit(1)

    # Zero-padding for filenames
    if zero_pad is None:
        digits = max(4, len(str(end)))  # at least 4 digits for large PDFs
    else:
        digits = int(zero_pad)

    # Prepare metadata (optional)
    meta_dict = None
    if copy_metadata:
        try:
            meta = reader.metadata or {}
            # Ensure keys/values are strings to avoid pypdf type issues
            meta_dict = {str(k): ("" if v is None else str(v)) for k, v in meta.items()}
        except Exception:
            meta_dict = None  # Safe fallback

    page_count = end - start + 1
    print(f"Splitting '{input_pdf}' → '{output_dir}'")
    print(f"Pages: {start}–{end} of {total_pages} (total outputs: {page_count})")
    print(f"Filename pattern: {prefix}_{{page:0{digits}d}}.pdf")

    for idx in range(start - 1, end):
        writer = PdfWriter()
        writer.add_page(reader.pages[idx])

        if meta_dict:
            try:
                writer.add_metadata(meta_dict)
            except Exception:
                # Ignore metadata issues to keep splitting robust
                pass

        out_name = f"{prefix}_{(idx + 1):0{digits}d}.pdf"
        out_path = os.path.join(output_dir, out_name)
        try:
            with open(out_path, "wb") as f:
                writer.write(f)
        except Exception as e:
            print(f"\nERROR: Failed writing page {idx + 1} to '{out_path}': {e}", file=sys.stderr)
            sys.exit(3)

        if print_every and ((idx + 1 - start + 1) % print_every == 0):
            done = (idx + 1 - start + 1)
            print(f"  ... {done}/{page_count} pages done")

    print(f"Done. Wrote {page_count} single-page PDFs to: {output_dir}")


def parse_args():
    p = argparse.ArgumentParser(description="Split a PDF into single-page PDFs.")
    p.add_argument("input_pdf", help="Path to the input PDF")
    p.add_argument("-o", "--output-dir", help="Directory to write single-page PDFs")
    p.add_argument("-p", "--prefix", help="Filename prefix for output files")
    p.add_argument("-s", "--start", type=int, help="Start page (1-based, inclusive)")
    p.add_argument("-e", "--end", type=int, help="End page (1-based, inclusive)")
    p.add_argument("--password", help="Password for encrypted PDFs")
    p.add_argument("--metadata", action="store_true", help="Copy document metadata to each output page")
    p.add_argument("--print-every", type=int, default=100, help="Print progress every N pages (0 to disable)")
    p.add_argument("--zero-pad", type=int, help="Force this many digits for page numbers (e.g., 5)")
    return p.parse_args()


if __name__ == "__main__":
    args = parse_args()
    split_pdf(
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
