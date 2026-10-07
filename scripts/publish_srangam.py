#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
publish_srangam.py — Publish translated docs from context.db to the Srangam
Supabase corpus tables (srangam_texts / srangam_text_passages).

PURELY ADDITIVE: reads context.db, writes ONLY to Supabase via REST.
Never modifies context.db. Never deletes remote rows. Texts always land
with published=false — you flip them live with --publish AFTER review
(the "no unreviewed live-DB write" agreement applied to content).

Requires in .env (alongside the existing keys):
    SUPABASE_URL=https://<project-ref>.supabase.co
    SUPABASE_SERVICE_ROLE_KEY=eyJ...   (service role — server-side only, never
                                        commit, never ship to the frontend)

Prerequisite: the B1 migration (supabase/migrations/
20260718120000_srangam_texts_corpus.sql) has been reviewed and applied.

Usage (from sanskrit-automatonv2/ root):
    python scripts/publish_srangam.py --list
    python scripts/publish_srangam.py --doc wl_buddha_carita_sanskrit --dry-run
    python scripts/publish_srangam.py --doc wl_buddha_carita_sanskrit
    python scripts/publish_srangam.py --doc wl_buddha_carita_sanskrit --publish
    python scripts/publish_srangam.py --doc wl_buddha_carita_sanskrit --unpublish

Schema contract (verified against ARCHITECTURE.md gotchas):
    passages.translation (NOT .english); join passages.doc_id -> docs.id.
Only passages with a non-empty translation are pushed.
"""

import argparse
import json
import os
import sqlite3
import sys
import time
import pathlib

try:
    from env_loader import load_env  # house pattern (see ingest_jsonl_fast.py)
    load_env()
except Exception:
    try:
        from dotenv import load_dotenv
        load_dotenv()
    except Exception:
        pass

import requests

BATCH = 500
TIMEOUT = 60
RETRIES = 3


# ----------------------------------------------------------------------------
# Supabase REST helpers
# ----------------------------------------------------------------------------

def sb_config():
    url = (os.getenv("SUPABASE_URL") or "").rstrip("/")
    key = os.getenv("SUPABASE_SERVICE_ROLE_KEY") or ""
    if not url or not key:
        sys.exit("ERROR: SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY must be set "
                 "in .env (service role key — keep it out of git and the frontend).")
    headers = {
        "apikey": key,
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json",
    }
    return url, headers


def sb_request(method, path, headers, *, params=None, payload=None, prefer=None):
    url_base, _ = sb_config()
    h = dict(headers)
    if prefer:
        h["Prefer"] = prefer
    last_err = None
    for attempt in range(1, RETRIES + 1):
        try:
            resp = requests.request(
                method, f"{url_base}/rest/v1/{path}",
                headers=h, params=params,
                data=json.dumps(payload) if payload is not None else None,
                timeout=TIMEOUT,
            )
            if resp.status_code >= 500:
                raise requests.RequestException(f"HTTP {resp.status_code}: {resp.text[:200]}")
            return resp
        except requests.RequestException as e:
            last_err = e
            wait = 2 * attempt
            print(f"  [retry {attempt}/{RETRIES}] {e} — waiting {wait}s")
            time.sleep(wait)
    sys.exit(f"ERROR: Supabase request failed after {RETRIES} attempts: {last_err}")


# ----------------------------------------------------------------------------
# Local DB reads (read-only)
# ----------------------------------------------------------------------------

def open_db(path):
    p = pathlib.Path(path)
    if not p.exists():
        sys.exit(f"ERROR: {path} not found — run from the sanskrit-automatonv2 root.")
    con = sqlite3.connect(f"file:{p}?mode=ro", uri=True)  # read-only guarantee
    con.row_factory = sqlite3.Row
    return con


def list_docs(con):
    return con.execute("""
        SELECT d.id, d.code, d.category,
               COUNT(p.id)                                              AS total,
               SUM(CASE WHEN TRIM(COALESCE(p.translation,''))<>'' THEN 1 ELSE 0 END) AS translated
        FROM docs d LEFT JOIN passages p ON p.doc_id = d.id
        GROUP BY d.id ORDER BY d.code
    """).fetchall()


def doc_by_code(con, code):
    row = con.execute("SELECT * FROM docs WHERE code = ?", (code,)).fetchone()
    if row is None:
        sys.exit(f"ERROR: doc code {code!r} not found in context.db "
                 f"(use --list to see available codes).")
    return row


def translated_passages(con, doc_id):
    return con.execute("""
        SELECT page_no, idx, text, iast, translation, verse_ref, quality_score,
               COALESCE(text_type,'mula') AS text_type
        FROM passages
        WHERE doc_id = ? AND TRIM(COALESCE(translation,'')) <> ''
        ORDER BY page_no, idx
    """, (doc_id,)).fetchall()


# ----------------------------------------------------------------------------
# Publish flow
# ----------------------------------------------------------------------------

def upsert_text_row(headers, doc, n_passages, engine, source_note):
    payload = {
        "doc_code": doc["code"],
        "title": resolve_title(doc["code"])[0],   # PUBLISH_TITLE2_2026_09_27
        "category": doc["category"],
        "source_note": source_note,
        "translation_engine": engine,
        "passage_count": n_passages,
        # NOTE: 'published' deliberately omitted — new rows default to false,
        # and re-publishing an updated doc must NOT silently re-flip a text
        # you have unpublished.
    }
    resp = sb_request(
        "POST", "srangam_texts", headers,
        params={"on_conflict": "doc_code"},
        payload=[payload],
        prefer="resolution=merge-duplicates,return=representation",
    )
    if resp.status_code not in (200, 201):
        sys.exit(f"ERROR upserting srangam_texts: HTTP {resp.status_code}: {resp.text[:300]}")
    rows = resp.json()
    if not rows:
        sys.exit("ERROR: upsert returned no representation — check RLS/key.")
    return rows[0]["id"]


def upsert_passages(headers, text_id, rows):
    pushed = 0
    for i in range(0, len(rows), BATCH):
        chunk = rows[i:i + BATCH]
        payload = [{
            "text_id": text_id,
            "page_no": r["page_no"],
            "idx": r["idx"],
            "sanskrit": r["text"],
            "iast": r["iast"],
            "translation": r["translation"],
            "verse_ref": r["verse_ref"],
            "quality_score": r["quality_score"],
        } for r in chunk]
        resp = sb_request(
            "POST", "srangam_text_passages", headers,
            params={"on_conflict": "text_id,page_no,idx"},
            payload=payload,
            prefer="resolution=merge-duplicates,return=minimal",
        )
        if resp.status_code not in (200, 201, 204):
            sys.exit(f"ERROR upserting passages (batch at {i}): "
                     f"HTTP {resp.status_code}: {resp.text[:300]}")
        pushed += len(chunk)
        print(f"  pushed {pushed}/{len(rows)} passages")
    return pushed


def set_published(headers, doc_code, value):
    resp = sb_request(
        "PATCH", "srangam_texts", headers,
        params={"doc_code": f"eq.{doc_code}"},
        payload={"published": value},
        prefer="return=representation",
    )
    rows = resp.json() if resp.status_code == 200 else []
    if not rows:
        sys.exit(f"ERROR: no srangam_texts row with doc_code={doc_code!r} "
                 f"(HTTP {resp.status_code}). Push the doc first.")
    state = "PUBLISHED (live)" if value else "unpublished (hidden)"
    print(f"{doc_code}: {state}")


# ----------------------------------------------------------------------------- PUBLISH_ENGINE_2026_10_07
def single_engine(con, doc_id):
    """The engine to label a text with when --engine is not given: the one engine that every
    translated passage of the doc records (passages.engine). None when they differ, when none is
    recorded, or when the column is absent; then the counts are printed and nothing is guessed."""
    cols = {r[1] for r in con.execute("PRAGMA table_info(passages)")}
    if "engine" not in cols:
        return None
    rows = [tuple(r) for r in con.execute(
        "SELECT engine, COUNT(*) FROM passages WHERE doc_id = ? AND TRIM(COALESCE(translation,'')) <> '' "
        "GROUP BY engine ORDER BY 2 DESC", (doc_id,))]
    if len(rows) == 1 and (rows[0][0] or "").strip():
        return rows[0][0].strip()
    if rows:
        print("note: the translated passages record %d engine label(s): %s - pass --engine to label the text"
              % (len(rows), ", ".join("%s x%d" % (e or "(none)", n) for e, n in rows)))
    return None


def main():
    ap = argparse.ArgumentParser(description="Publish translated docs to Srangam")
    ap.add_argument("--gate-report", action="store_true",
                    help="show what the publication gate would withhold, and why, "
                         "then exit without publishing (PUBLISH_GATE_2026_09_06)")
    ap.add_argument("--no-gate", action="store_true",
                    help="publish WITHOUT the passage-level gate. Only for a corpus "
                         "you have reviewed passage by passage.")
    ap.add_argument("--dup-threshold", type=float, default=0.40)
    ap.add_argument("--dup-window", type=int, default=1)
    ap.add_argument("--db", default="data/context.db")
    ap.add_argument("--doc", help="doc code to push (see --list)")
    ap.add_argument("--list", action="store_true",
                    help="list docs with translation counts and exit")
    ap.add_argument("--dry-run", action="store_true",
                    help="show what would be pushed; no network writes")
    ap.add_argument("--engine", default=None,
                    help="translation engine label stored on the text row")
    ap.add_argument("--source-note", default=None,
                    help="provenance note (default depends on category)")
    ap.add_argument("--publish", action="store_true",
                    help="flip the doc live AFTER you have reviewed it")
    ap.add_argument("--unpublish", action="store_true",
                    help="hide the doc from the public reader")
    ap.add_argument("--emit-sql", default=None, metavar="DIR",
                    help="PUBLISH_BRIDGE_2026_09_27: write the upserts as pasteable UTF-8 "
                         "SQL files under DIR/<doc>/ for the Lovable Cloud SQL editor "
                         "(no service-role key needed). No network use.")
    ap.add_argument("--title", default=None,
                    help="PUBLISH_TITLE2_2026_09_27: display title for srangam_texts "
                         "(default: Booksmith book.yaml, else derived). Only this "
                         "replaces a title already on the site.")
    ap.add_argument("--sql-batch", type=int, default=200,
                    help="passages per SQL file for --emit-sql (default 200)")
    args = ap.parse_args()

    if args.publish and args.unpublish:
        sys.exit("ERROR: --publish and --unpublish are mutually exclusive.")

    con = open_db(args.db)

    if args.list:
        rows = list_docs(con)
        print(f"{'doc code':40s} {'category':14s} {'passages':>8s} {'translated':>10s}")
        for r in rows:
            print(f"{r['code']:40s} {(r['category'] or '-'):14s} "
                  f"{r['total']:8d} {r['translated'] or 0:10d}")
        return

    if not args.doc:
        sys.exit("ERROR: --doc <code> required (or --list).")

    doc = doc_by_code(con, args.doc)

    # publish/unpublish only — no data push
    if (args.publish or args.unpublish) and args.dry_run:
        sys.exit("ERROR: --dry-run cannot be combined with --publish/--unpublish.")
    if args.publish or args.unpublish:
        _, headers = sb_config()
        set_published(headers, args.doc, bool(args.publish))
        return

    rows = translated_passages(con, doc["id"])
    if not rows:
        sys.exit(f"{args.doc}: no translated passages yet — nothing to push.")
    # PUBLISH_BRIDGE_2026_09_27: --gate-report / --no-gate were parsed and the
    # gate never ran. It runs now, before every push, dry-run and SQL emit.
    keep, withheld = gate_rows(rows, dup_threshold=args.dup_threshold,
                               dup_window=args.dup_window)
    if args.gate_report:
        print_gate_report(args.doc, keep, withheld)
        return
    if not args.no_gate:
        if withheld:
            print(f"{args.doc}: the publication gate withholds {len(withheld)} of "
                  f"{len(rows)} passage(s) (--gate-report shows which and why)")
        rows = keep
        if not rows:
            sys.exit(f"{args.doc}: every translated passage is withheld by the gate.")

    source_note = args.source_note or (
        "Sanskrit source text via local wisdomlib.org archive; "
        "AI-assisted translation by the Srangam Sanskrit Automaton."
        if (doc["category"] or "") == "wisdomlib"
        else "Digitised and AI-assisted translation by the Srangam Sanskrit Automaton."
    )

    pages = len({r["page_no"] for r in rows})
    print(f"{args.doc}: {len(rows)} translated passages across {pages} pages")
    if args.engine is None:   # PUBLISH_ENGINE_2026_10_07
        args.engine = single_engine(con, doc["id"])
        if args.engine:
            print(f"{args.doc}: engine label {args.engine} (recorded by every translated passage)")

    if args.emit_sql:
        emit_sql(args.emit_sql, doc, rows, args.engine, source_note, args.sql_batch,
                 title_override=args.title)
        return

    if args.dry_run:
        sample = rows[0]
        print("\n--dry-run: no network writes. First record that would be pushed:")
        print(json.dumps({
            "page_no": sample["page_no"], "idx": sample["idx"],
            "sanskrit": (sample["text"] or "")[:80] + "…",
            "iast": (sample["iast"] or "")[:80],
            "translation": (sample["translation"] or "")[:80] + "…",
            "verse_ref": sample["verse_ref"],
            "quality_score": sample["quality_score"],
        }, ensure_ascii=False, indent=2))
        print(f"\nText row: doc_code={doc['code']!r} title={resolve_title(doc['code'], args.title)[0]!r} "
              f"category={doc['category']!r} passage_count={len(rows)}")
        print("Would land UNPUBLISHED; flip live later with --publish.")
        return

    if os.getenv("SA_SAFE_MODE") != "1":
        print("WARNING: SA_SAFE_MODE is not set to 1 — house rules expect it. "
              "Proceeding (publisher is non-destructive by design).")

    _, headers = sb_config()
    text_id = upsert_text_row(headers, doc, len(rows), args.engine, source_note)
    print(f"srangam_texts row: {text_id}")
    upsert_passages(headers, text_id, rows)
    print(f"\nDone. {args.doc} uploaded. Publish state is unchanged "
          f"(a NEW text starts unpublished; a re-push never re-flips one).")
    print(f"To make it live after review:\n  python scripts/publish_srangam.py "
          f"--doc {args.doc} --publish")


# PUBLISH_BRIDGE_2026_09_27: the __main__ guard used to stand here, so main()
# ran before gate_rows() and doc_title() below were defined. It is at the end.


# ── Publication gate (PUBLISH_GATE_2026_09_06) ───────────────────────────────
# `published` is a per-DOCUMENT flag; it cannot protect a reviewed book from bad
# passages inside it. These are the passage-level rules, each one measured.
import re as _gate_re

_GF_ABBREV = _gate_re.compile(r"(?:का०|प्र०|ब्रा०|बृ०|अध्या०|खण्ड०|पत्र०|पृ०|सं०|अ०)")
_GF_FOLIO = _gate_re.compile(r"[\[\({][^\]\)}\n]{0,60}?"
                             r"(?:का०|प्र०|ब्रा०|बृ०|अ०|पृ०|अध्या०|खण्ड०|सं०)"
                             r"[^\]\)}\n]{0,60}?[\]\)}]")
_GF_TITLE = _gate_re.compile(r"[ऀ-ॿ]{3,}(?:ब्राह्मणम्|ब्राह्मणे|संहिता|संहितायाम्|पुराणम्|"
                             r"उपनिषत्|उपनिषदि|भाष्यसमेतम्|भाष्यसंमेतम्|भाष्यसहितम्|सूत्रम्)")
# Built by concatenation rather than one literal: the class contains both
# quote characters, and escaping those through a generated file is exactly
# the kind of avoidable trap that produces a SyntaxError at import time.
_GF_PUNCT = (" *|-–—_।॥.,;:()[]{}<>०-९0-9"
             + "'" + chr(34) + "“”‘’")
_GF_DECOR = _gate_re.compile("[" + _gate_re.escape(_GF_PUNCT) + r"\s]+")
_GF_DEVRUN = _gate_re.compile(r"[ऀ-ॿ]+")
_GATE_NGRAM = 5


def _gate_is_furniture_line(line: str) -> bool:
    t = (line or "").strip()
    if not t or len(t) > 90:
        return False
    if not _GF_DECOR.sub("", t) and len(t) <= 20:
        return True
    if not (_GF_FOLIO.search(t) or _GF_TITLE.search(t)
            or len(_GF_ABBREV.findall(t)) >= 2):
        return False
    residue = _GF_DECOR.sub("", _GF_ABBREV.sub(
        "", _GF_TITLE.sub("", _GF_FOLIO.sub("", t))))
    return len(residue) <= 3


def gate_has_furniture(text: str) -> bool:
    """True when the passage still LEADS with page furniture. Same detector as
    text_filters.strip_page_furniture, which measured 226/226 furniture cases
    caught, 0 content loss and 0 false positives over 1,321 real passages."""
    return bool(text) and _gate_is_furniture_line(text.split("\n")[0])


def _gate_sig(text: str) -> set:
    s = "".join(_GF_DEVRUN.findall(text or ""))
    return {s[i:i + _GATE_NGRAM] for i in range(len(s) - _GATE_NGRAM + 1)}


def _gate_containment(a: set, b: set) -> float:
    if not a or not b:
        return 0.0
    return len(a & b) / min(len(a), len(b))


def gate_rows(rows, *, dup_threshold=0.40, dup_window=1, min_grams=40):
    """Split publisher rows into (publishable, withheld).

    `withheld` entries are (row, reason). Nothing is deleted anywhere; a
    withheld passage stays in context.db and simply is not mirrored.
    """
    keep, drop = [], []
    staged = []
    for r in rows:
        ttype = (r["text_type"] if "text_type" in r.keys() else None) or "mula"
        if ttype in ("noise", "frontmatter"):
            drop.append((r, f"text_type={ttype}"))
            continue
        if gate_has_furniture(r["text"] or ""):
            drop.append((r, "page furniture (running head / folio mark)"))
            continue
        staged.append(r)

    # duplicate suppression: furniture-bearing member of a 1:1 pair.
    # Anything already dropped for furniture is gone, so this catches the
    # residual case where BOTH copies survived the furniture test.
    sigs = [(_gate_sig(r["text"] or ""), r) for r in staged]
    partners = {}
    for i in range(len(sigs)):
        for j in range(i + 1, len(sigs)):
            if sigs[j][1]["page_no"] - sigs[i][1]["page_no"] > dup_window:
                break
            if len(sigs[i][0]) < min_grams or len(sigs[j][0]) < min_grams:
                continue
            if _gate_containment(sigs[i][0], sigs[j][0]) >= dup_threshold:
                partners.setdefault(i, []).append(j)
                partners.setdefault(j, []).append(i)

    dropped_idx = set()
    for i, js in partners.items():
        if len(js) != 1:
            continue            # one-to-many = commentary or real repetition
        j = js[0]
        if len(partners.get(j, [])) != 1:
            continue
        a, b = sigs[i][1], sigs[j][1]
        # keep the denser reading; ties keep the earlier passage
        da = len(_GF_DEVRUN.findall(a["text"] or ""))
        db = len(_GF_DEVRUN.findall(b["text"] or ""))
        loser = i if (da, -a["page_no"]) < (db, -b["page_no"]) else j
        dropped_idx.add(loser)

    for n, (_s, r) in enumerate(sigs):
        if n in dropped_idx:
            drop.append((r, "duplicate of a cleaner reading on the same page"))
        else:
            keep.append(r)
    return keep, drop


def print_gate_report(code, keep, drop):
    from collections import Counter
    print("=" * 74)
    print(f"PUBLICATION GATE   {code}")
    print("=" * 74)
    total = len(keep) + len(drop)
    print(f"  translated passages : {total}")
    print(f"  would publish       : {len(keep)}")
    print(f"  withheld            : {len(drop)}")
    if not drop:
        print("\n  Nothing withheld. Safe to publish.")
        return
    print()
    for reason, n in Counter(r for _row, r in drop).most_common():
        print(f"  {n:>5}  {reason}")
    print("\n  Examples of what is being withheld:\n")
    seen = set()
    for row, reason in drop:
        if reason in seen:
            continue
        seen.add(reason)
        print(f"   [{reason}]  p{row['page_no']}.{row['idx']}")
        print(f"     src: {(row['text'] or '')[:96]}")
        print(f"     tr : {(row['translation'] or '')[:96]}")
        print()
    print("  Nothing was deleted. These rows remain in context.db; fix the")
    print("  source, re-run, and they will publish.")


# ── Display title (PUBLISH_TITLE_2026_09_06) ─────────────────────────────────
# `docs` has no `title` column (db_utils.py: id, code, category, src_path,
# glossary, created_at). publish_srangam.py asked for d.title and crashed on
# its own --list. srangam_texts.title is NOT NULL, so derive a label from the
# code rather than drop the column.
import re as _title_re

_TITLE_LEAD_ACCESSION = _title_re.compile(r"^(?:\d{4}[_-])?\d{4,}[_-]")
_TITLE_SEPS = _title_re.compile(r"[_\-]+")


def doc_title(code: str) -> str:
    """A human label for a doc code. Display only — doc_code stays the key.

    '2015_405693_Shatpath-Brahmanam'  -> 'Shatpath Brahmanam'
    '476948-Rgveda-samhita'           -> 'Rgveda samhita'
    'wl_buddha_carita_sanskrit'       -> 'Buddha Carita Sanskrit'
    """
    s = (code or "").strip()
    if not s:
        return "(untitled)"
    s = _TITLE_LEAD_ACCESSION.sub("", s)          # drop the accession prefix
    if s.startswith("wl_"):
        s = s[3:]                                 # wisdomlib adapter prefix
    s = _TITLE_SEPS.sub(" ", s)
    s = _title_re.sub(r"(?<=[a-z])(?=[A-Z])", " ", s)   # PUBLISH_TITLE2_2026_09_27: CamelCase
    s = _title_re.sub(r"\s+", " ", s).strip()
    if not s:
        return code
    # Title-case ONLY words that are entirely lowercase, so 'Rgveda', 'IAST'
    # and roman numerals are not mangled.
    return " ".join(w.capitalize() if w.islower() else w for w in s.split(" "))


# ── Display title (PUBLISH_TITLE2_2026_09_27) ───────────────────────────────
# The curated title lives in the Booksmith edition (projects/<slug>/book.yaml,
# set with block_AX -SetTitle). --title wins; else book.yaml; else doc_title().
# A book.yaml title that is only the scan id + name (e.g. "2015 405693 ...") is
# ignored. Only --title overwrites a title already on the site.
DEFAULT_BOOKSMITH_ROOT = r"D:\Nartiang_Booksmith_v0.1.0_2026-08-29\nartiang-booksmith"
_SCAN_TITLE_RE = _title_re.compile(r"^\d{4}[\s_-]\d{3,}")


def _book_slug(code):
    s = (code or "").strip().lower().replace("_", "-")
    s = _title_re.sub(r"[^a-z0-9_-]+", "-", s).strip("-")
    return _title_re.sub(r"-{2,}", "-", s)[:64]


def book_title(code, root=None):
    home = pathlib.Path(root or os.getenv("BOOKSMITH_ROOT", DEFAULT_BOOKSMITH_ROOT)) / "projects"
    slug = _book_slug(code)
    for s in (slug, slug[:61] + "-hi", slug[:61] + "-en"):
        try:
            text = (home / s / "book.yaml").read_text(encoding="utf-8")
        except OSError:
            continue
        m = _title_re.search(r"(?m)^title:[ \t]*(.+?)[ \t]*$", text)
        if not m:
            continue
        t = m.group(1).strip()
        if len(t) >= 2 and t[0] == t[-1] and t[0] in "'\"":
            t = t[1:-1].replace("''", "'") if t[0] == "'" else t[1:-1]
        if t and t != code and not _SCAN_TITLE_RE.match(t):
            return t
    return None


def resolve_title(code, override=None):
    """(title, source) - source is '--title', 'book.yaml' or 'derived'."""
    if override and override.strip():
        return override.strip(), "--title"
    t = book_title(code)
    if t:
        return t, "book.yaml"
    return (doc_title(code) or code), "derived"


# ── SQL-editor bridge (PUBLISH_BRIDGE_2026_09_27) ────────────────────────────
# There is no service-role key on this machine (house rule: privileged Supabase
# access goes through the Lovable Cloud SQL editor only), so the REST path above
# can never run. --emit-sql writes the SAME upserts as UTF-8 SQL files, one
# pasteable file at a time, generated by this program - never through a shell
# redirect or the clipboard (CONSOLIDATION_PLAN section 10). Every file is
# idempotent, never deletes, never touches srangam_texts.published, and ends
# with a SELECT so the editor (which shows only the last result) confirms it.

def _sql_lit(v):
    if v is None:
        return "NULL"
    if isinstance(v, bool):
        return "TRUE" if v else "FALSE"
    if isinstance(v, int):
        return str(v)
    if isinstance(v, float):
        return repr(v)
    s = str(v).replace("\x00", "")
    return "'" + s.replace("'", "''") + "'"


_SQL_HEAD = ("-- PUBLISH_BRIDGE_2026_09_27 - generated by scripts/publish_srangam.py --emit-sql\n"
             "-- Paste this ONE file into the Lovable Cloud SQL editor and run it.\n"
             "-- Idempotent (re-running changes nothing), never deletes, never\n"
             "-- changes srangam_texts.published. Source: context.db, read-only.\n")


def emit_sql(out_dir, doc, rows, engine, source_note, batch=200, max_bytes=450000,
             title_override=None):
    import hashlib
    code = doc["code"]
    title, title_src = resolve_title(code, title_override)   # PUBLISH_TITLE2_2026_09_27
    title_set = "title = EXCLUDED.title, " if title_src == "--title" else ""
    out = pathlib.Path(out_dir) / code
    out.mkdir(parents=True, exist_ok=True)
    for old in out.glob("*.sql"):
        old.unlink()                        # a fresh, complete set every time
    lit = _sql_lit
    files = []

    def write(name, body):
        p = out / name
        data = body.encode("utf-8")
        p.write_bytes(data)
        files.append((name, len(data), hashlib.sha256(data).hexdigest()))

    write("00_text.sql", _SQL_HEAD +
          "INSERT INTO public.srangam_texts (doc_code, title, category, source_note, "
          "translation_engine, passage_count)\nVALUES (%s, %s, %s, %s, %s, %d)\n"
          "ON CONFLICT (doc_code) DO UPDATE SET %s"
          "category = EXCLUDED.category, source_note = EXCLUDED.source_note,\n"
          "  translation_engine = COALESCE(EXCLUDED.translation_engine, "
          "public.srangam_texts.translation_engine),\n"
          "  passage_count = EXCLUDED.passage_count, updated_at = now();\n"
          "SELECT id, doc_code, passage_count, published FROM public.srangam_texts "
          "WHERE doc_code = %s;\n"
          % (lit(code), lit(title), lit(doc["category"]), lit(source_note),
             lit(engine), len(rows), title_set, lit(code)))

    chunks, cur, size = [], [], 0
    for r in rows:
        tup = "(%s, %s, %s, %s, %s, %s, %s)" % (
            lit(int(r["page_no"])), lit(int(r["idx"])), lit(r["text"] or ""),
            lit(r["iast"]), lit(r["translation"]), lit(r["verse_ref"]),
            lit(float(r["quality_score"]) if r["quality_score"] is not None else None))
        if cur and (len(cur) >= batch or size + len(tup) > max_bytes):
            chunks.append(cur); cur, size = [], 0
        cur.append((r, tup)); size += len(tup)
    if cur:
        chunks.append(cur)
    for n, chunk in enumerate(chunks, 1):
        first, last = chunk[0][0], chunk[-1][0]
        write("%02d_passages.sql" % n, _SQL_HEAD +
              "-- passages %d of %d files: p%s.%s .. p%s.%s (%d rows)\n"
              % (n, len(chunks), first["page_no"], first["idx"], last["page_no"], last["idx"], len(chunk)) +
              "INSERT INTO public.srangam_text_passages (text_id, page_no, idx, sanskrit, iast, "
              "translation, verse_ref, quality_score)\n"
              "SELECT t.id, v.page_no::int, v.idx::int, v.sanskrit, v.iast::text, v.translation, "
              "v.verse_ref::text, v.quality_score::real\nFROM (VALUES\n  " +
              ",\n  ".join(t for _r, t in chunk) +
              "\n) AS v(page_no, idx, sanskrit, iast, translation, verse_ref, quality_score)\n"
              "JOIN public.srangam_texts t ON t.doc_code = %s\n" % lit(code) +
              "ON CONFLICT (text_id, page_no, idx) DO UPDATE SET sanskrit = EXCLUDED.sanskrit, "
              "iast = EXCLUDED.iast,\n  translation = EXCLUDED.translation, "
              "verse_ref = EXCLUDED.verse_ref, quality_score = EXCLUDED.quality_score, "
              "updated_at = now();\n"
              "SELECT %d AS rows_in_this_file, count(*) AS now_on_site FROM public.srangam_text_passages p "
              "JOIN public.srangam_texts t ON t.id = p.text_id WHERE t.doc_code = %s;\n"
              % (len(chunk), lit(code)))

    keys = ",".join("(%d,%d)" % (int(r["page_no"]), int(r["idx"])) for r in rows)
    write("99_verify.sql", _SQL_HEAD +
          "-- read-only. Expect local_passages = remote_passages and no stale rows.\n"
          "-- A 'stale' row is on the site but no longer in the local publishable set\n"
          "-- (emptied, re-split or withheld by the gate); this bridge never deletes it.\n"
          "WITH local_keys(page_no, idx) AS (VALUES %s)\n"
          "SELECT t.doc_code, %d AS local_passages, count(p.id) AS remote_passages,\n"
          "  count(p.id) FILTER (WHERE NOT EXISTS (SELECT 1 FROM local_keys k "
          "WHERE k.page_no = p.page_no AND k.idx = p.idx)) AS stale_on_site,\n"
          "  t.published\nFROM public.srangam_texts t LEFT JOIN public.srangam_text_passages p "
          "ON p.text_id = t.id\nWHERE t.doc_code = %s GROUP BY t.doc_code, t.published;\n"
          % (keys, len(rows), lit(code)))

    man = ["PUBLISH_BRIDGE_2026_09_27 manifest for %s" % code,
           "local publishable passages: %d  (after the publication gate)" % len(rows),
           "title: %s  (from %s; the site title is replaced only with --title)" % (title, title_src),
           "paste in order; each file ends with a SELECT that confirms it:", ""]
    man += ["  %-18s %9d bytes  sha256 %s" % f for f in files]
    (out / "MANIFEST.txt").write_text("\n".join(man) + "\n", encoding="utf-8")
    print("%s: %d passage(s) -> %d SQL file(s) in %s" % (code, len(rows), len(files), out))
    for f in files:
        print("  %-18s %9d bytes" % f[:2])
    return out


if __name__ == "__main__":
    main()
