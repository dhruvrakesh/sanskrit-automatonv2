#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Import archived WisdomLib pages into the Sanskrit Automaton database.

This reads the local archive produced by D:\\wisdomlib\\scraper.py and upserts
cleaned page content into docs/passages. It is intentionally offline-first:
no network calls, no OpenAI calls, and no key access.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sqlite3
import sys
from pathlib import Path
from typing import Iterable, Sequence

from bs4 import BeautifulSoup

from db_utils import connect, ensure_doc, ensure_schema


DEFAULT_ARCHIVE = Path(r"D:\wisdomlib\wisdomlib_archive")
TAGS = ("h1", "h2", "h3", "h4", "p", "li", "blockquote", "pre")
DROP_SELECTORS = (
    "script",
    "style",
    "noscript",
    "form",
    "header",
    "footer",
    "nav",
    "aside",
    ".navbar",
    ".breadcrumb",
    ".adsbygoogle",
    ".ad",
    ".comments",
)
STOP_HEADINGS = {"comments:", "comment:", "add a comment"}
NAV_TEXT = {
    "home",
    "about",
    "contact",
    "newsletter",
    "shop",
    "links",
    "photos",
    "tools",
    "resources",
    "support me on patreon",
    "buy relevant books",
}
DEV_RE = re.compile(r"[\u0900-\u097F]")
SPACE_RE = re.compile(r"\s+")


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def read_meta(page_dir: Path) -> dict:
    meta_path = page_dir / "meta.json"
    if not meta_path.exists():
        raise FileNotFoundError(f"Missing meta.json: {meta_path}")
    return json.loads(meta_path.read_text(encoding="utf-8"))


def page_dirs_for_slugs(archive: Path, slugs: Sequence[str]) -> list[Path]:
    pages = archive / "pages"
    out = []
    for slug in slugs:
        page_dir = pages / slug
        if not page_dir.exists():
            raise FileNotFoundError(f"WisdomLib slug not found: {slug}")
        out.append(page_dir)
    return out


def page_dirs_for_search(archive: Path, query: str, limit: int) -> list[Path]:
    q = query.casefold()
    matches: list[tuple[str, Path]] = []
    for meta_path in (archive / "pages").glob("*/meta.json"):
        try:
            meta = json.loads(meta_path.read_text(encoding="utf-8"))
        except Exception:
            continue
        haystack = " ".join(
            [
                str(meta.get("title", "")),
                str(meta.get("slug", "")),
                str(meta.get("url", "")),
                str(meta.get("ai_summary", "")),
                " ".join(str(t) for t in meta.get("ai_tags", [])),
            ]
        ).casefold()
        if q in haystack:
            matches.append((str(meta.get("slug") or meta_path.parent.name), meta_path.parent))
    matches.sort(key=lambda item: item[0])
    return [p for _, p in matches[:limit or None]]


def clean_text(text: str) -> str:
    text = text.replace("\u00a0", " ")
    text = SPACE_RE.sub(" ", text)
    return text.strip()


def looks_like_nav(text: str) -> bool:
    t = clean_text(text).casefold()
    return t in NAV_TEXT or (len(t) <= 2 and not DEV_RE.search(t))


def extract_content(page_dir: Path, meta: dict) -> list[str]:
    html_path = page_dir / "page.html"
    if not html_path.exists():
        text_path = page_dir / "page.txt"
        if not text_path.exists():
            return []
        return [clean_text(line) for line in text_path.read_text(encoding="utf-8", errors="replace").splitlines() if clean_text(line)]

    soup = BeautifulSoup(html_path.read_text(encoding="utf-8", errors="replace"), "html.parser")
    for selector in DROP_SELECTORS:
        for node in soup.select(selector):
            node.decompose()

    root = soup.select_one("main") or soup.body or soup
    h1 = root.find("h1") or soup.find("h1")
    lines: list[str] = []
    started = h1 is None

    for tag in root.find_all(TAGS):
        if tag is h1:
            started = True
        if not started:
            continue

        text = clean_text(tag.get_text(" ", strip=True))
        if not text or looks_like_nav(text):
            continue
        if text.casefold() in STOP_HEADINGS:
            break

        if tag.name in {"h1", "h2", "h3", "h4"}:
            text = f"# {text}"
        lines.append(text)

    if not lines and meta.get("title"):
        lines.append(f"# {meta['title']}")
    return lines


def frac_devanagari(text: str) -> float:
    if not text:
        return 0.0
    return len(DEV_RE.findall(text)) / max(1, len(text))


def chunk_lines(lines: Iterable[str], max_chars: int, sanskrit_only: bool) -> list[str]:
    chunks: list[str] = []
    cur: list[str] = []
    cur_len = 0

    def flush() -> None:
        nonlocal cur, cur_len
        if not cur:
            return
        text = "\n".join(cur).strip()
        cur = []
        cur_len = 0
        if not text:
            return
        if sanskrit_only and frac_devanagari(text) < 0.03:
            return
        chunks.append(text)

    for line in lines:
        line = clean_text(line)
        if not line:
            flush()
            continue
        is_heading = line.startswith("# ")
        if is_heading:
            flush()
            chunks.append(line)
            continue
        if cur_len and cur_len + len(line) + 1 > max_chars:
            flush()
        cur.append(line)
        cur_len += len(line) + 1
    flush()
    return chunks


def table_columns(con: sqlite3.Connection, table: str) -> set[str]:
    return {row[1] for row in con.execute(f"PRAGMA table_info({table})")}


def upsert_passage(
    con: sqlite3.Connection,
    passage_cols: set[str],
    doc_id: int,
    page_no: int,
    idx: int,
    text: str,
    source: str,
) -> int:
    values = {
        "doc_id": doc_id,
        "page_no": page_no,
        "idx": idx,
        "text": text,
        "translation": "",
        "source": source,
        "norm": text,
    }
    cols = [c for c in ("doc_id", "page_no", "idx", "text", "translation", "source", "norm") if c in passage_cols]
    placeholders = ",".join("?" for _ in cols)
    updates = ",".join(f"{c}=excluded.{c}" for c in cols if c not in {"doc_id", "page_no", "idx"})
    sql = f"""
        INSERT INTO passages({",".join(cols)})
        VALUES({placeholders})
        ON CONFLICT(doc_id,page_no,idx) DO UPDATE SET {updates}
    """
    con.execute(sql, tuple(values[c] for c in cols))
    row = con.execute(
        "SELECT id FROM passages WHERE doc_id=? AND page_no=? AND idx=?",
        (doc_id, page_no, idx),
    ).fetchone()
    return int(row[0])


def refresh_fts(con: sqlite3.Connection, rowid: int, text: str, translation: str = "") -> None:
    has_fts = con.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='passages_fts'").fetchone()
    if not has_fts:
        return
    con.execute("DELETE FROM passages_fts WHERE rowid=?", (rowid,))
    con.execute("INSERT INTO passages_fts(rowid,text,translation) VALUES(?,?,?)", (rowid, text, translation))


def record_source(con: sqlite3.Connection, doc_id: int, path: str, page_lo: int, page_hi: int, sha256: str) -> None:
    has_sources = con.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='sources'").fetchone()
    if not has_sources:
        return
    con.execute(
        "DELETE FROM sources WHERE doc_id=? AND path=? AND page_lo=? AND page_hi=?",
        (doc_id, path, page_lo, page_hi),
    )
    con.execute(
        "INSERT INTO sources(doc_id,path,page_lo,page_hi,sha256) VALUES(?,?,?,?,?)",
        (doc_id, path, page_lo, page_hi, sha256),
    )


def import_page(
    con: sqlite3.Connection,
    page_dir: Path,
    doc_code: str,
    page_no: int,
    max_chars: int,
    sanskrit_only: bool,
    max_passages: int,
    dry_run: bool,
) -> tuple[int, int]:
    meta = read_meta(page_dir)
    lines = extract_content(page_dir, meta)
    chunks = chunk_lines(lines, max_chars=max_chars, sanskrit_only=sanskrit_only)
    if max_passages:
        chunks = chunks[:max_passages]

    if dry_run:
        print(f"[dry-run] {doc_code} page={page_no} slug={page_dir.name} chunks={len(chunks)}")
        for sample in chunks[:5]:
            print("  -", sample.replace("\n", " ")[:180])
        return len(chunks), 0

    doc_id = ensure_doc(con, doc_code)
    passage_cols = table_columns(con, "passages")
    source = str(meta.get("url") or page_dir)
    con.execute("BEGIN")
    for idx, text in enumerate(chunks, start=1):
        rid = upsert_passage(con, passage_cols, doc_id, page_no, idx, text, source)
        refresh_fts(con, rid, text)
    digest_path = page_dir / "page.html"
    if not digest_path.exists():
        digest_path = page_dir / "page.txt"
    digest = sha256_file(digest_path) if digest_path.exists() else ""
    record_source(con, doc_id, str(page_dir), page_no, page_no, digest)
    con.commit()
    print(f"[import] {doc_code} page={page_no} slug={page_dir.name} chunks={len(chunks)}")
    return len(chunks), len(chunks)


def main() -> None:
    ap = argparse.ArgumentParser(description="Import local WisdomLib archive pages into Sanskrit Automaton SQLite.")
    ap.add_argument("--archive", default=str(DEFAULT_ARCHIVE))
    ap.add_argument("--db", default="data/context.db")
    ap.add_argument("--slug", action="append", default=[], help="WisdomLib archive page slug; can be repeated.")
    ap.add_argument("--search", help="Search title/url/tags/summary in archived meta.json files.")
    ap.add_argument("--search-limit", type=int, default=20)
    ap.add_argument("--doc", help="Destination doc code. Defaults to WL-<slug> for one page, or WL-import for search.")
    ap.add_argument("--page-start", type=int, default=1)
    ap.add_argument("--max-chars", type=int, default=1200)
    ap.add_argument("--max-passages", type=int, default=0)
    ap.add_argument("--sanskrit-only", action="store_true")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    archive = Path(args.archive)
    if not (archive / "pages").exists():
        raise SystemExit(f"WisdomLib archive not found: {archive}")

    page_dirs: list[Path] = []
    if args.slug:
        page_dirs.extend(page_dirs_for_slugs(archive, args.slug))
    if args.search:
        page_dirs.extend(page_dirs_for_search(archive, args.search, args.search_limit))
    if not page_dirs:
        raise SystemExit("Provide --slug or --search.")

    # De-dupe while preserving order.
    page_dirs = list(dict.fromkeys(page_dirs))

    con = connect(args.db)
    ensure_schema(con)

    total_chunks = 0
    total_written = 0
    for offset, page_dir in enumerate(page_dirs):
        doc_code = args.doc
        if not doc_code:
            doc_code = f"WL-{page_dir.name}" if len(page_dirs) == 1 else "WL-import"
        chunks, written = import_page(
            con,
            page_dir=page_dir,
            doc_code=doc_code,
            page_no=args.page_start + offset,
            max_chars=args.max_chars,
            sanskrit_only=args.sanskrit_only,
            max_passages=args.max_passages,
            dry_run=args.dry_run,
        )
        total_chunks += chunks
        total_written += written

    mode = "would write" if args.dry_run else "wrote"
    print(f"[done] pages={len(page_dirs)} chunks={total_chunks} {mode}={total_written}")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        sys.exit(130)
