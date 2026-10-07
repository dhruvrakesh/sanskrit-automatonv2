#!/usr/bin/env python3
# -*- coding: ascii -*-
"""
patch_story_variants_2026_10_07.py  (2026-10-07)  STORY_VARIANTS_2026_10_07

Retellings for age groups. scripts/stories.py:

  retell  --id N --audience young|teen [--yes] [--force]
      A second retelling of an APPROVED story (--force: a draft) for children aged
      8-12 (young) or readers aged 13-16 (teen). One gemini-2.5-flash call (about
      $0.01) from the same passages, the approved retelling and its editorial notes.
      It keeps a citation after every sentence (stored; the young layout hides them),
      keeps every name exactly, may explain an unfamiliar word in a few plain words,
      never adds a fact, and tells hard moments plainly and gently. Checked by the
      same verify as the story (the story's quotation is inherited). Table
      doc_story_variants, one live row per story and audience; draft -> approved.
  variant --id N --audience young|teen --action approve|force|retire|verify

  book --audience young   uses the APPROVED young version where there is one
  book --audience teen    (new) the teen version, general layout without notes
  Where no approved version exists the book uses the approved story, as before.

All-or-nothing, marker-idempotent, backup .bak_variants_<date>, py_compile.
  python scripts\\patch_story_variants_2026_10_07.py --check
  python scripts\\patch_story_variants_2026_10_07.py
Test: python -m unittest tests.test_story_variants_2026_10_07 -v
"""
from __future__ import annotations
import argparse, datetime, os, py_compile, shutil, sys
from pathlib import Path

MARK = "STORY_VARIANTS_2026_10_07"

BLOCK = r'''# ------------------------------------------------------------------ STORY_VARIANTS_2026_10_07
VARIANT_AUDIENCES = ("young", "teen")
VARIANT_SCHEMA = """
CREATE TABLE IF NOT EXISTS doc_story_variants(
  id INTEGER PRIMARY KEY, story_id INTEGER NOT NULL, audience TEXT NOT NULL,
  status TEXT NOT NULL DEFAULT 'draft', title TEXT, title_hi TEXT, story_en TEXT, story_hi TEXT, notes TEXT,
  cites TEXT, verify TEXT, model TEXT, prompt_hash TEXT, provenance TEXT,
  created_at TEXT, updated_at TEXT, approved_at TEXT, UNIQUE(story_id, audience));
"""
AUDIENCE_SPEC = {
    "young": ("children aged 8 to 12",
              "Use short sentences and everyday words, 150-230 words, past tense. Tell hard moments (death, curses, "
              "war) plainly and gently, without gore."),
    "teen": ("readers aged 13 to 16",
             "Use clear, vivid prose, 180-260 words, past tense. Keep the motives the passages give; no gore."),
}
RETELL_SYSTEM = (
    "You retell ONE episode from a Sanskrit text for %s, for an illustrated book. You are given the passages "
    "(tag [page.idx], the Sanskrit as printed and a machine English translation) and the editor-approved retelling "
    "for adults with its editorial notes. Rules: (1) Use ONLY what the passages say. The approved retelling shows "
    "what the editor accepted; the notes say what to leave out. Add no events, motives, speech, places or "
    "descriptions that the passages do not give. (2) After EVERY sentence, cite the passage(s) it rests on, as "
    "[page.idx] or [page.idx, page.idx]. (3) Give every name exactly as the passages give it, in IAST. Where a word "
    "may be unfamiliar, add a few plain words that explain it (for example 'Samika, a forest sage'), never a new "
    "fact. (4) %s (5) story_hi: the same retelling in simple, natural Hindi, with the same citations. "
    "Respond with JSON only: {\"title\": str, \"title_hi\": str, \"story_en\": str, \"story_hi\": str, "
    "\"notes\": str (what you left out or simplified, and why)}")


def ensure_variants(con) -> None:
    con.executescript(VARIANT_SCHEMA)
    con.commit()


def _variant_row(con, sid: int, audience: str) -> dict | None:
    if "doc_story_variants" not in {r[0] for r in con.execute("SELECT name FROM sqlite_master WHERE type='table'")}:
        return None
    cols = [c[1] for c in con.execute("PRAGMA table_info(doc_story_variants)")]
    r = con.execute("SELECT * FROM doc_story_variants WHERE story_id=? AND audience=?", (sid, audience)).fetchone()
    return dict(zip(cols, r)) if r else None


def _variant_for(con, sid: int, audience: str) -> dict | None:
    """The APPROVED version of story sid for this audience, or None."""
    if audience not in VARIANT_AUDIENCES:
        return None
    v = _variant_row(con, sid, audience)
    return v if v and v["status"] == "approved" else None


def variant_verify(con, s: dict, v: dict) -> dict:
    rows = window(passages(con, _code_of(con, s["doc_id"])), (s["from_page"], s["from_idx"]),
                  (s["to_page"], s["to_idx"]), pad=2, cap=60)
    return verify({"story_en": v.get("story_en") or "", "story_hi": v.get("story_hi") or "",
                   "quote_sa": s.get("quote_sa") or "", "quote_ref": s.get("quote_ref") or ""}, rows)


def retell(con, sid: int, audience: str, db: str, http=None, cap: int = 60, force: bool = False) -> dict:
    if audience not in VARIANT_AUDIENCES:
        raise SystemExit("FAIL: audience must be one of %s" % ", ".join(VARIANT_AUDIENCES))
    s = _row(con, sid)
    if s["status"] != "approved" and not (force and s["status"] == "draft"):
        raise SystemExit("FAIL: story #%d is %s; a version for younger readers is made from an approved story "
                         "(--force for a draft)." % (sid, s["status"]))
    ensure_variants(con)
    code = _code_of(con, s["doc_id"])
    rows = window(passages(con, code), (s["from_page"], s["from_idx"]), (s["to_page"], s["to_idx"]), pad=2, cap=cap)
    if not rows:
        raise SystemExit("FAIL: story #%d: no translated passages in its range." % sid)
    who, how = AUDIENCE_SPEC[audience]
    system = RETELL_SYSTEM % (who, how)
    user = ("Episode: %s\n\nAPPROVED RETELLING (for adults):\n%s\n\nEDITORIAL NOTES:\n%s\n\nPASSAGES\n\n%s"
            % (s.get("title") or "", s.get("story_en") or "", s.get("notes") or "(none)", _prompt_block(rows, True)))
    t0 = time.time()
    data, resp = im.call_text_json(MODEL, system, user, http=http)
    im.meter("story", code, "gemini:" + MODEL, resp, db, time.time() - t0, units=1)
    data = data if isinstance(data, dict) else {}
    v = variant_verify(con, s, data)
    ph = hashlib.sha256((MODEL + system + user).encode("utf-8")).hexdigest()[:16]
    con.execute(
        """INSERT INTO doc_story_variants(story_id, audience, status, title, title_hi, story_en, story_hi, notes, cites,
                                          verify, model, prompt_hash, provenance, created_at, updated_at)
           VALUES(?, ?, 'draft', ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
           ON CONFLICT(story_id, audience) DO UPDATE SET status='draft', title=excluded.title,
             title_hi=excluded.title_hi, story_en=excluded.story_en, story_hi=excluded.story_hi, notes=excluded.notes,
             cites=excluded.cites, verify=excluded.verify, model=excluded.model, prompt_hash=excluded.prompt_hash,
             provenance=excluded.provenance, updated_at=excluded.updated_at, approved_at=NULL""",
        (sid, audience, data.get("title") or s.get("title") or "", data.get("title_hi") or s.get("title_hi") or "",
         data.get("story_en") or "", data.get("story_hi") or "", data.get("notes") or "", json.dumps(v["cited"]),
         json.dumps(v), MODEL, ph, json.dumps({"from_story": sid, "story_status": s["status"], "written_at": now()}),
         now(), now()))
    con.commit()
    return v


'''

EDITS = [
    ("schema", "def ensure_schema(con) -> None:\n    con.executescript(SCHEMA)\n    con.commit()\n",
     "def ensure_schema(con) -> None:\n    con.executescript(SCHEMA + VARIANT_SCHEMA)   # STORY_VARIANTS_2026_10_07\n    con.commit()\n", 1),
    ("variants block", "# ------------------------------------------------------------------ CLI\n",
     BLOCK + "# ------------------------------------------------------------------ CLI\n", 1),
    ("book audiences", 'AUDIENCES = ("young", "general", "scholar")\n',
     'AUDIENCES = ("young", "teen", "general", "scholar")   # teen: STORY_VARIANTS_2026_10_07\n', 1),
    ("book uses the approved version",
     '''        en = s.get("story_en") or ""
        hi = s.get("story_hi") or ""
''',
     '''        vv = _variant_for(con, s["id"], audience)   # STORY_VARIANTS_2026_10_07
        if vv:
            s = dict(s, title=vv.get("title") or s.get("title"), title_hi=vv.get("title_hi") or s.get("title_hi"),
                     story_en=vv.get("story_en") or "", story_hi=vv.get("story_hi") or "", cites=vv.get("cites"))
        en = s.get("story_en") or ""
        hi = s.get("story_hi") or ""
''', 1),
    ("teen hides notes",
     '''        if s.get("notes") and audience != "young":
''',
     '''        if s.get("notes") and audience not in ("young", "teen"):
''', 1),
    ("teen css",
     '''           "general": "body{font-size:1.05rem;line-height:1.65}",
''',
     '''           "teen": "body{font-size:1.12rem;line-height:1.7}h2{color:#5a3a12}",
           "general": "body{font-size:1.05rem;line-height:1.65}",
''', 1),
    ("teen intro",
     '''             "general": "Retellings, each cited to the passages it rests on. Illustrations are generated, not historical "
''',
     '''             "teen": "Episodes retold from a Sanskrit text, each resting on the passages cited after its sentences. "
                     "The pictures are new paintings made for this book, not historical sources.",
             "general": "Retellings, each cited to the passages it rests on. Illustrations are generated, not historical "
''', 1),
    ("cli parsers",
     '''    bsx = sub.add_parser("booksmith-source"); bsx.add_argument("--ids", required=True)
''',
     '''    rt = sub.add_parser("retell"); rt.add_argument("--id", type=int, required=True)   # STORY_VARIANTS_2026_10_07
    rt.add_argument("--audience", required=True, choices=VARIANT_AUDIENCES); rt.add_argument("--yes", action="store_true")
    rt.add_argument("--force", action="store_true", help="also from a draft story")
    va = sub.add_parser("variant"); va.add_argument("--id", type=int, required=True)
    va.add_argument("--audience", required=True, choices=VARIANT_AUDIENCES)
    va.add_argument("--action", required=True, choices=["approve", "force", "retire", "verify"])
    bsx = sub.add_parser("booksmith-source"); bsx.add_argument("--ids", required=True)
''', 1),
    ("cli dispatch",
     '''        if args.cmd == "illustrate":   # STORY_BOOKS_2026_10_07
''',
     '''        if args.cmd == "retell":   # STORY_VARIANTS_2026_10_07
            s = _row(con, args.id)
            print("retell #%d %s for %s with %s, about $0.01" % (args.id, s.get("title") or "",
                                                                 AUDIENCE_SPEC[args.audience][0], MODEL))
            if not args.yes:
                print("Dry run. Add --yes."); return 0
            if not budget_ok(args.db):
                print("Refusing: the spend cap is reached."); return 1
            res = retell(con, args.id, args.audience, args.db, force=args.force)
            print("  #%d %s: %s %s" % (args.id, args.audience, "verified" if res["ok"] else "NEEDS REVIEW:",
                                       "; ".join(res["problems"])))
            return 0
        if args.cmd == "variant":
            s = _row(con, args.id)
            v = _variant_row(con, args.id, args.audience)
            if not v:
                print("No %s version of #%d yet (retell --id %d --audience %s)." % (args.audience, args.id, args.id,
                                                                                    args.audience)); return 1
            if args.action == "verify":
                res = variant_verify(con, s, v)
                con.execute("UPDATE doc_story_variants SET verify=?, updated_at=? WHERE id=?", (json.dumps(res), now(), v["id"]))
                con.commit(); print(json.dumps(res, ensure_ascii=False, indent=1)); return 0 if res["ok"] else 1
            if args.action == "retire":
                con.execute("UPDATE doc_story_variants SET status='retired', updated_at=? WHERE id=?", (now(), v["id"]))
                con.commit(); print("#%d %s version retired" % (args.id, args.audience)); return 0
            if v["status"] != "draft":
                print("Refusing: the %s version of #%d is %s." % (args.audience, args.id, v["status"])); return 1
            if not (json.loads(v["verify"] or "{}").get("ok")) and args.action != "force":
                print("Refusing: the check failed. Read it; --action force approves anyway."); return 1
            con.execute("UPDATE doc_story_variants SET status='approved', approved_at=?, updated_at=? WHERE id=?",
                        (now(), now(), v["id"]))
            con.commit(); print("#%d %s version approved" % (args.id, args.audience)); return 0
        if args.cmd == "illustrate":   # STORY_BOOKS_2026_10_07
''', 1),
]

TARGETS = [(Path("scripts/stories.py"), EDITS)]


def load(p: Path):
    raw = p.read_bytes(); crlf = raw.count(b"\r\n")
    return raw.decode("utf-8").replace("\r\n", "\n"), ("\r\n" if crlf > (raw.count(b"\n") - crlf) else "\n")


def main() -> int:
    ap = argparse.ArgumentParser(); ap.add_argument("--check", action="store_true"); args = ap.parse_args()
    for p, _ in TARGETS:
        if not p.exists():
            print("FAIL: %s not found. Run from the repo root." % p); return 2
    loaded = [(p, *load(p), e) for p, e in TARGETS]
    if all(MARK in s for _, s, _, _ in loaded):
        print("Already patched (%s). Nothing to do." % MARK); return 0
    problems, out = [], []
    for p, src, nl, edits in loaded:
        for label, old, new, n in edits:
            c = src.count(old)
            if c != n:
                problems.append("%s %s: matched %d times, expected %d" % (p.name, label, c, n))
            else:
                src = src.replace(old, new)
        out.append((p, src, nl))
    if problems:
        print("REFUSING TO WRITE:"); [print("  " + x) for x in problems]; return 1
    if args.check:
        print("CHECK OK: %d anchored edits in %d files. Nothing written." % (sum(len(e) for _, e in TARGETS), len(TARGETS)))
        return 0
    stamp = datetime.date.today().strftime("%Y%m%d")
    tmps = []
    for p, text, nl in out:
        t = p.with_name(p.name + ".tmp_variants")
        t.write_bytes(text.replace("\n", nl).encode("utf-8"))
        try:
            py_compile.compile(str(t), doraise=True)
        except py_compile.PyCompileError as e:
            for x, _ in tmps + [(t, p)]:
                x.unlink(missing_ok=True)
            print("REFUSING TO WRITE: %s would not compile:\n%s" % (p, e)); return 1
        tmps.append((t, p))
    for t, p in tmps:
        shutil.copy2(p, p.with_name(p.name + ".bak_variants_" + stamp))
    for t, p in tmps:
        os.replace(t, p)
        print("patched %s" % p)
    return 0


if __name__ == "__main__":
    sys.exit(main())
