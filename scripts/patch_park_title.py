#!/usr/bin/env python3
"""patch_park_title.py  (MARKS PARK_ILLEGIBLE_2026_09_27, PUBLISH_TITLE2_2026_09_27)

Two surgical changes, all-or-nothing, marker-idempotent, CRLF preserved,
atomic write (tmp + os.replace), backups *.bak_pk_20260927.

A. PARK_ILLEGIBLE_2026_09_27  (text_filters, translate_passages, plan_empty_retries)
   A verse whose paid answer, under the CURRENT prompt, was nothing but the
   lacuna token ("[ILLEGIBLE]" / "[asphuta]", with punctuation or verse
   numbers) on --park-after (default 2) separate runs, for the SAME source
   text, is "parked": later runs and plans skip it instead of paying for the
   same answer forever. Measured 2026-09-27: 59 such answers in the ledger,
   45 of them Bodhicaryavatara, whose source there is mixed Latin/Devanagari
   OCR noise - it needs re-OCR, not another translation call.
     * Nothing in context.db changes. The evidence is the existing ledger
       data/translate_outcomes.jsonl; new records also carry "prompt".
     * A new prompt version, or a changed (re-OCR'd) source text, un-parks
       the verse automatically. --retry-illegible (translate_passages) and
       --include-parked (planner) switch parking off for one run.
     * Records written before this patch have no "prompt" field; they count
       as the current prompt only if written after the v3 prompts went live
       (infer_mt.py rewritten 2026-09-27 07:16:03 UTC).

B. PUBLISH_TITLE2_2026_09_27  (publish_srangam)
   srangam_texts.title was the raw doc code ('AphorismsOfSandilya').
     * The title now comes from --title, else the Booksmith edition's
       book.yaml (BOOKSMITH_ROOT; the curated 'Sanskrit title' lives there),
       else doc_title(), which now also splits CamelCase.
     * On re-upsert the site title is overwritten ONLY when --title is given,
       so a title corrected in the SQL editor survives every later re-emit.

  python scripts/patch_park_title.py --root .           # check
  python scripts/patch_park_title.py --root . --apply   # write
"""
import argparse, os, py_compile, shutil, sys
from pathlib import Path

BAK = ".bak_pk_20260927"

TF_APPEND = r'''


# -- PARK_ILLEGIBLE_2026_09_27 ------------------------------------------------
# A verse answered with nothing but the lacuna token on --park-after separate
# runs, under the current prompt and for the same source text, is parked:
# asking again buys the same answer. Evidence is the append-only ledger
# data/translate_outcomes.jsonl; nothing in the database is changed, and a new
# prompt version or a re-OCR'd source un-parks the verse by itself.
_PARK_TOKEN_RE = re.compile(
    r"\[\s*(?:illegible|\u0905\u0938\u094d\u092a\u0937\u094d\u091f)\s*\]", re.I)
_PARK_SOFT_RE = re.compile(r"\[\s*\?\s*\]")      # the uncertainty mark [?]
_PARK_PUNCT_RE = re.compile(
    r"[\s\d\u0966-\u096f/|\u0964\u0965.,;:!?'\"()\[\]*_~`\-\u2013\u2014\u2026]+")
# infer_mt.py was rewritten with the v3 prompts at 2026-09-27 07:16:03 UTC.
# Ledger records from before this patch carry no "prompt" field; they count
# as the current prompt only when written after that moment.
PARK_LEGACY_SINCE = "2026-09-27T07:16:04+00:00"


def is_bare_illegible(raw) -> bool:
    """True when raw is only lacuna token(s) plus punctuation / verse numbers."""
    s = raw or ""
    if not _PARK_TOKEN_RE.search(s):
        return False
    s = _PARK_SOFT_RE.sub(" ", _PARK_TOKEN_RE.sub(" ", s))   # tokens first, then punctuation
    return _PARK_PUNCT_RE.sub("", s) == ""


def load_parked(ledger_path, lang, current_prompt, min_attempts=2,
                legacy_since=PARK_LEGACY_SINCE):
    """{(passage_id, source[:2000]): attempts} for verses to skip. Never raises."""
    counts = {}
    try:
        fh = open(str(ledger_path), encoding="utf-8")
    except OSError:
        return {}
    with fh:
        for line in fh:
            try:
                r = json.loads(line)
            except ValueError:
                continue
            if not isinstance(r, dict) or r.get("lang") != lang:
                continue
            if r.get("cause") != "refusal-filter" or not is_bare_illegible(r.get("raw")):
                continue
            p = r.get("prompt")
            if p is None:
                if str(r.get("ts") or "") < legacy_since:
                    continue
            elif p != current_prompt:
                continue
            pid, src = r.get("passage_id"), r.get("source")
            if pid is None or src is None:
                continue
            key = (pid, str(src)[:2000])
            counts[key] = counts.get(key, 0) + 1
    n = max(1, int(min_attempts or 1))
    return {k: v for k, v in counts.items() if v >= n}
'''

EDITS = {
  'scripts/text_filters.py': ('PARK_ILLEGIBLE_2026_09_27', [
    ('json import for the ledger reader', '\nimport re\n', '\nimport json   # PARK_ILLEGIBLE_2026_09_27\nimport re\n'),
  ], TF_APPEND),

  'scripts/translate_passages.py': ('PARK_ILLEGIBLE_2026_09_27', [
    ('import load_parked',
     '                          strip_leading_source_echo)   # FILTERS3_2026_09_27\n',
     '                          strip_leading_source_echo,   # FILTERS3_2026_09_27\n'
     '                          load_parked)                 # PARK_ILLEGIBLE_2026_09_27\n'),
    ('--retry-illegible / --park-after',
     '    ap.add_argument("--config",       default=str(_CONFIG_PATH))\n',
     '    ap.add_argument("--config",       default=str(_CONFIG_PATH))\n'
     '    ap.add_argument("--park-after", type=int, default=2,\n'
     '                    help="PARK_ILLEGIBLE_2026_09_27: skip a verse whose answer under the "\n'
     '                         "current prompt was only the lacuna token on this many runs "\n'
     '                         "(same source text). It needs re-OCR, not another call.")\n'
     '    ap.add_argument("--retry-illegible", action="store_true",\n'
     '                    help="ask parked verses again anyway (this run only)")\n'),
    ('load the parked set before the todo loop',
     '    todo = []\n    for row in rows:\n',
     '    # PARK_ILLEGIBLE_2026_09_27: verses answered only with the lacuna token\n'
     '    # on --park-after runs (current prompt, same source) are not asked again.\n'
     '    parked = {} if (args.retranslate or args.retry_illegible) else load_parked(\n'
     '        _PROGRESS_PATH.parent / "translate_outcomes.jsonl", TGT,\n'
     '        PROMPT_VERSIONS.get(TGT, PROMPT_VERSION), args.park_after)\n'
     '    n_parked = 0\n'
     '    todo = []\n    for row in rows:\n'),
    ('skip parked verses',
     '        cleaned = clean_for_mt(normed)\n        if not cleaned:\n            continue\n'
     '        todo.append((rowid, page_no, idx, cleaned, rest))\n',
     '        cleaned = clean_for_mt(normed)\n        if not cleaned:\n            continue\n'
     '        if parked and (rowid, cleaned[:2000]) in parked:   # PARK_ILLEGIBLE_2026_09_27\n'
     '            n_parked += 1\n'
     '            continue\n'
     '        todo.append((rowid, page_no, idx, cleaned, rest))\n'),
    ('say how many were parked',
     '             if IS_L10N else ""))\n    if not todo:\n',
     '             if IS_L10N else ""))\n'
     '    if n_parked:   # PARK_ILLEGIBLE_2026_09_27\n'
     '        print(f"  [PARKED] {n_parked} verse(s) skipped: only the lacuna token on "\n'
     '              f"{args.park_after}+ runs under this prompt - re-OCR them, or pass "\n'
     '              f"--retry-illegible")\n'
     '    if not todo:\n'),
    ('ledger: prompt version on salvaged records',
     '"cause": "salvaged", "kept": translation,\n',
     '"cause": "salvaged", "kept": translation, "prompt": ver,\n'),
    ('ledger: prompt version on empty records',
     '"cause": why, "raw": raw_out, "source": cleaned[:2000]})\n',
     '"cause": why, "prompt": ver, "raw": raw_out, "source": cleaned[:2000]})\n'),
    ('parked count in the final summary',
     '              + "  (raw outputs: data/translate_outcomes.jsonl)")\n',
     '              + "  (raw outputs: data/translate_outcomes.jsonl)")\n'
     '    if n_parked:   # PARK_ILLEGIBLE_2026_09_27\n'
     '        print(f"  parked (not asked, lacuna-only answers before): {n_parked}")\n'),
  ], None),

  'scripts/plan_empty_retries.py': ('PARK_ILLEGIBLE_2026_09_27', [
    ('prompt versions for the parked set',
     'from normalize_text import normalize_sanskrit  # noqa: E402\n',
     'from normalize_text import normalize_sanskrit  # noqa: E402\n'
     'from infer_mt import PROMPT_VERSIONS           # noqa: E402  PARK_ILLEGIBLE_2026_09_27\n'),
    ('--park-after / --include-parked',
     '    ap.add_argument("--min-rows", type=int, default=1)\n',
     '    ap.add_argument("--min-rows", type=int, default=1)\n'
     '    ap.add_argument("--park-after", type=int, default=2,\n'
     '                    help="same rule as translate_passages --park-after")\n'
     '    ap.add_argument("--include-parked", action="store_true",\n'
     '                    help="count parked verses as retries anyway")\n'),
    ('select p.id',
     '"       AND TRIM(COALESCE(l.translation,\'\'))<>\'\') "\n        "FROM passages p JOIN docs d',
     '"       AND TRIM(COALESCE(l.translation,\'\'))<>\'\'), p.id "\n        "FROM passages p JOIN docs d'),
    ('first loop unpacks p.id',
     '    for code, page, idx, _t, _q, en, hi in rows:\n',
     '    for code, page, idx, _t, _q, en, hi, _pid in rows:\n'),
    ('load the parked set',
     '    count, fresh, below1 = {}, {}, {}\n    for code, page, idx, text, qs, en, hi in rows:\n',
     '    ledger = Path(a.db).resolve().parent / "translate_outcomes.jsonl"\n'
     '    parked = {lg: ({} if a.include_parked else tf.load_parked(\n'
     '        ledger, lg, PROMPT_VERSIONS.get(lg), a.park_after)) for lg in langs}\n'
     '    npark = {}\n'
     '    count, fresh, below1 = {}, {}, {}\n    for code, page, idx, text, qs, en, hi, pid in rows:\n'),
    ('cleaned text for the parked key',
     '        if 0 < qs < a.min_quality:\n            continue\n        for lg, done in (("en", en), ("hi", hi)):\n'
     '            if lg not in langs or done or (code, lg) not in last:\n                continue\n',
     '        if 0 < qs < a.min_quality:\n            continue\n'
     '        src_key = (pid, tf.clean_for_mt(normed)[:2000])\n'
     '        for lg, done in (("en", en), ("hi", hi)):\n'
     '            if lg not in langs or done or (code, lg) not in last:\n                continue\n'
     '            if src_key in parked.get(lg, {}):   # PARK_ILLEGIBLE_2026_09_27\n'
     '                npark[(code, lg)] = npark.get((code, lg), 0) + 1\n'
     '                continue\n'),
    ('print the parked list',
     '    if b:\n        print("  budget:',
     '    if npark:   # PARK_ILLEGIBLE_2026_09_27\n'
     '        print("  parked (lacuna-only answer on %d+ runs, this prompt, same source) - re-OCR these:"\n'
     '              % a.park_after)\n'
     '        for (code, lg), n in sorted(npark.items(), key=lambda kv: -kv[1]):\n'
     '            print("    %-44s %-3s %6d" % (code[:44], lg, n))\n'
     '    if b:\n        print("  budget:'),
    ('parked counts in the JSON plan',
     '"headroom": (b[0] - b[1]) if b else None},\n',
     '"headroom": (b[0] - b[1]) if b else None,\n'
     '                                           "parked": {"%s|%s" % k: v for k, v in npark.items()}},\n'),
  ], None),

  'scripts/publish_srangam.py': ('PUBLISH_TITLE2_2026_09_27', [
    ('doc_title splits CamelCase',
     '    s = _TITLE_SEPS.sub(" ", s)\n',
     '    s = _TITLE_SEPS.sub(" ", s)\n'
     '    s = _title_re.sub(r"(?<=[a-z])(?=[A-Z])", " ", s)   # PUBLISH_TITLE2_2026_09_27: CamelCase\n'),
    ('book_title / resolve_title',
     '# \u2500\u2500 SQL-editor bridge (PUBLISH_BRIDGE_2026_09_27)',
     '# \u2500\u2500 Display title (PUBLISH_TITLE2_2026_09_27) \u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\n'
     '# The curated title lives in the Booksmith edition (projects/<slug>/book.yaml,\n'
     '# set with block_AX -SetTitle). --title wins; else book.yaml; else doc_title().\n'
     '# A book.yaml title that is only the scan id + name (e.g. "2015 405693 ...") is\n'
     '# ignored. Only --title overwrites a title already on the site.\n'
     'DEFAULT_BOOKSMITH_ROOT = r"D:\\Nartiang_Booksmith_v0.1.0_2026-08-29\\nartiang-booksmith"\n'
     '_SCAN_TITLE_RE = _title_re.compile(r"^\\d{4}[\\s_-]\\d{3,}")\n'
     '\n\n'
     'def _book_slug(code):\n'
     '    s = (code or "").strip().lower().replace("_", "-")\n'
     '    s = _title_re.sub(r"[^a-z0-9_-]+", "-", s).strip("-")\n'
     '    return _title_re.sub(r"-{2,}", "-", s)[:64]\n'
     '\n\n'
     'def book_title(code, root=None):\n'
     '    home = pathlib.Path(root or os.getenv("BOOKSMITH_ROOT", DEFAULT_BOOKSMITH_ROOT)) / "projects"\n'
     '    slug = _book_slug(code)\n'
     '    for s in (slug, slug[:61] + "-hi", slug[:61] + "-en"):\n'
     '        try:\n'
     '            text = (home / s / "book.yaml").read_text(encoding="utf-8")\n'
     '        except OSError:\n'
     '            continue\n'
     '        m = _title_re.search(r"(?m)^title:[ \\t]*(.+?)[ \\t]*$", text)\n'
     '        if not m:\n'
     '            continue\n'
     '        t = m.group(1).strip()\n'
     '        if len(t) >= 2 and t[0] == t[-1] and t[0] in "\'\\"":\n'
     '            t = t[1:-1].replace("\'\'", "\'") if t[0] == "\'" else t[1:-1]\n'
     '        if t and t != code and not _SCAN_TITLE_RE.match(t):\n'
     '            return t\n'
     '    return None\n'
     '\n\n'
     'def resolve_title(code, override=None):\n'
     '    """(title, source) - source is \'--title\', \'book.yaml\' or \'derived\'."""\n'
     '    if override and override.strip():\n'
     '        return override.strip(), "--title"\n'
     '    t = book_title(code)\n'
     '    if t:\n'
     '        return t, "book.yaml"\n'
     '    return (doc_title(code) or code), "derived"\n'
     '\n\n'
     '# \u2500\u2500 SQL-editor bridge (PUBLISH_BRIDGE_2026_09_27)'),
    ('emit_sql takes a title override',
     'def emit_sql(out_dir, doc, rows, engine, source_note, batch=200, max_bytes=450000):\n'
     '    import hashlib\n    code = doc["code"]\n',
     'def emit_sql(out_dir, doc, rows, engine, source_note, batch=200, max_bytes=450000,\n'
     '             title_override=None):\n'
     '    import hashlib\n    code = doc["code"]\n'
     '    title, title_src = resolve_title(code, title_override)   # PUBLISH_TITLE2_2026_09_27\n'
     '    title_set = "title = EXCLUDED.title, " if title_src == "--title" else ""\n'),
    ('00_text: title kept on conflict unless --title',
     '"ON CONFLICT (doc_code) DO UPDATE SET title = EXCLUDED.title, "\n',
     '"ON CONFLICT (doc_code) DO UPDATE SET %s"\n'),
    ('00_text: values',
     '          % (lit(code), lit(doc_title(code) or code), lit(doc["category"]), lit(source_note),\n'
     '             lit(engine), len(rows), lit(code)))\n',
     '          % (lit(code), lit(title), lit(doc["category"]), lit(source_note),\n'
     '             lit(engine), len(rows), title_set, lit(code)))\n'),
    ('manifest names the title',
     '"local publishable passages: %d  (after the publication gate)" % len(rows),\n',
     '"local publishable passages: %d  (after the publication gate)" % len(rows),\n'
     '           "title: %s  (from %s; the site title is replaced only with --title)" % (title, title_src),\n'),
    ('--title argument',
     '    ap.add_argument("--sql-batch", type=int, default=200,\n',
     '    ap.add_argument("--title", default=None,\n'
     '                    help="PUBLISH_TITLE2_2026_09_27: display title for srangam_texts "\n'
     '                         "(default: Booksmith book.yaml, else derived). Only this "\n'
     '                         "replaces a title already on the site.")\n'
     '    ap.add_argument("--sql-batch", type=int, default=200,\n'),
    ('emit call passes --title',
     '        emit_sql(args.emit_sql, doc, rows, args.engine, source_note, args.sql_batch)\n',
     '        emit_sql(args.emit_sql, doc, rows, args.engine, source_note, args.sql_batch,\n'
     '                 title_override=args.title)\n'),
    ('dry-run shows the resolved title',
     "title={doc_title(doc['code'])!r} ",
     "title={resolve_title(doc['code'], args.title)[0]!r} "),
    ('REST path uses the resolved title',
     '        "title": doc_title(doc["code"]) or doc["code"],\n',
     '        "title": resolve_title(doc["code"])[0],   # PUBLISH_TITLE2_2026_09_27\n'),
  ], None),
}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=".")
    ap.add_argument("--apply", action="store_true")
    a = ap.parse_args()
    root = Path(a.root)
    plan, bad = [], 0
    for rel, (mark, eds, append) in EDITS.items():
        p = root / rel
        if not p.exists():
            print("  MISSING  %s" % rel); bad += 1; continue
        raw = p.read_bytes()
        crlf = b"\r\n" in raw
        text = raw.decode("utf-8").replace("\r\n", "\n")
        if mark in text:
            print("  already  %s (%s present) - skipped" % (rel, mark)); continue
        new = text
        for name, old, rep in eds:
            n = new.count(old)
            if n != 1:
                print("  ANCHOR   %s :: %s matched %d time(s), need exactly 1" % (rel, name, n))
                bad += 1; continue
            new = new.replace(old, rep, 1)
            print("  ok       %s :: %s" % (rel, name))
        if append:
            new = new.rstrip("\n") + "\n" + append
            print("  ok       %s :: appended helpers" % rel)
        if mark not in new:
            print("  ANCHOR   %s :: marker not present after edits" % rel); bad += 1
        plan.append((p, crlf, new))
    if bad:
        print("REFUSED: %d problem(s); nothing written." % bad); return 2
    if not plan:
        print("nothing to do - every file already patched."); return 0
    # compile every new text BEFORE writing any file (all-or-nothing)
    for p, crlf, new in plan:
        try:
            compile(new, str(p), "exec")
        except SyntaxError as e:
            print("REFUSED: %s would not compile: %s" % (p.name, e)); return 2
    if not a.apply:
        print("CHECK PASSED for %d file(s). Re-run with --apply to write." % len(plan)); return 0
    for p, crlf, new in plan:
        bak = p.with_name(p.name + BAK)
        if not bak.exists():
            shutil.copy2(p, bak)
        tmp = p.with_name(p.name + ".tmp_patch")
        tmp.write_bytes((new.replace("\n", "\r\n") if crlf else new).encode("utf-8"))
        os.replace(str(tmp), str(p))   # atomic: a job starting now reads old or new, never half
        py_compile.compile(str(p), doraise=True)
        print("  WROTE    %s  (backup %s)" % (p.name, bak.name))
    print("APPLIED. To undo: copy each %s back over its file." % BAK)
    return 0


if __name__ == "__main__":
    sys.exit(main())
