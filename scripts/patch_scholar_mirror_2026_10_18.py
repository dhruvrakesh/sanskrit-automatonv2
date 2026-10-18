#!/usr/bin/env python3
# -*- coding: ascii -*-
"""
patch_scholar_mirror_2026_10_18.py  (2026-10-18)  SCHOLAR_MIRROR_2026_10_18

Asked on 18 Oct: "why is only 1 scholarly text available on srangam.. i thought we had a complete mirror from local
to srangam.. like a react based browser through our local db". The mirror (corpus_sync.py, 8 Oct) carries every live
text's passages, working English, Hindi, names, stories and vectors; the scholarly English (scholar_translations,
14 Oct) came after it and never travelled. The site's reader (/corpus/<doc>) could not show it.

scripts/corpus_sync.py (needs MIRROR_CAP_2026_10_12):
  - scholar_rows(): a text's scholarly English as rows of the translations table, two a verse:
      lang en-x-scholar       its English; translation_score its fidelity and translation_qa its fluency, as the
                              judge gave them (1 to 5); engine, prompt version and date;
      lang en-x-scholar-meta  JSON: status, flag, a person's acceptance, the judge, notes and doubts (on a
                              sentence's first verse), and for a sentence over several verses its range on the first
                              verse and "with" on the others (which have no English row of their own).
    As the edition takes them (export_html.py --scholar): a verse's latest version, made from its Sanskrit as it
    reads now (src_hash), not rejected by a person. A rejected or stale verse's rows are retired on the site.
  - build_doc_groups(): the translations group carries them beside the Hindi. The Hindi rows, their hashes and
    every other table are unchanged (SCHEMA_VERSION stays c4.1: nothing is sent again but the new rows).
  - local_counts() (--status) counts them.
  The site's ingest and edge function take any lang: no change there. Every site function that reads translations
  asks for lang 'hi' (the reader, the library, the counts), so nothing the site shows changes until it asks for the
  scholarly rows: public.corpus_reader_scholar (docs/cloud/C18), and the reader kit
  (docs/srangam/SCHOLAR_READER_2026-10-18). A witness (an e-text, <doc>__w_<site>) stays local until it is adopted
  (repair_text.py --release); a text in repair is held, a withdrawn one retired, as before.
tests/test_mirror_cap_2026_10_12.py (its replay chain): corpus_sync.py's later backup may be .bak_scholarmirror_.
Anchored, all-or-nothing, marker-idempotent; keeps line endings; py_compile before the atomic replace; backups
.bak_scholarmirror_<date>. No database change; nothing is called.
  python scripts\\patch_scholar_mirror_2026_10_18.py --check
  python scripts\\patch_scholar_mirror_2026_10_18.py
"""
from __future__ import annotations
import argparse, datetime, os, py_compile, shutil, sys, tempfile
from pathlib import Path

MARK = 'SCHOLAR_MIRROR_2026_10_18'
NEEDS = {'scripts/corpus_sync.py': 'MIRROR_CAP_2026_10_12', 'tests/test_mirror_cap_2026_10_12.py': 'MIRROR_CAP_2026_10_12'}
FILES = list(NEEDS)
TAG = 'scholarmirror'

E = []
def edit(f, n, old, new):
    E.append((f, n, old, new))


edit('scripts/corpus_sync.py', 1, r'''index, mt_cache, usage and budget tables, retired documents.
''', r'''index, mt_cache, usage and budget tables, retired documents.
SCHOLAR_MIRROR_2026_10_18: the scholarly English (scholar_translations) travels too, as two translation rows a verse:
en-x-scholar (its English; translation_score its fidelity, translation_qa its fluency) and en-x-scholar-meta (JSON:
status, review, notes, doubts, a sentence's range). The site reads them with public.corpus_reader_scholar (C18).
''')

edit('scripts/corpus_sync.py', 2, r'''def build_doc_groups(con, doc, tables, ent_ok: set) -> dict:
''', r'''# --- SCHOLAR_MIRROR_2026_10_18: the scholarly English, as rows of the translations table ----------
SCHOLAR_LANG = "en-x-scholar"            # a verse's scholarly English (scholar_translations, scholar_translate.py)
SCHOLAR_META_LANG = "en-x-scholar-meta"  # its status, review, notes, doubts and range, as JSON in `translation`
SCHOLAR_META_VERSION = "scholar-meta-1"  # in mt_prompt_version of a meta row
_SCHOLAR_COLS = ("id", "passage_id", "verse_ref", "src_hash", "translation", "notes", "doubts", "fidelity", "fluency",
                 "status", "engine", "judge_engine", "prompt_version", "created_at", "review_verdict", "group_ref",
                 "group_translation")
_L10N_OUT = ("doc_code", "page_no", "idx", "lang") + L10N_COLS


def _scholar_range(u, pinfo) -> str:
    """SCHOLAR_MIRROR_2026_10_18: a sentence's range from its verses' own references (81.18-19), as the edition gives it
    (export_html.py, EDITION_REFS_2026_10_18); scholar_translate's _range when none has one."""
    import scholar_translate as ST
    refs = [str((pinfo.get(r.get("passage_id")) or (None, None))[1] or "").strip() for r in u]
    refs = [x for x in refs if x]
    if not refs:
        return ST._range(u)
    a_, b_ = refs[0], refs[-1]
    return a_ if a_ == b_ else "%s\u2013%s" % (a_, b_.split(".")[-1])


def scholar_rows(con, code, passages, pinfo) -> list:
    """SCHOLAR_MIRROR_2026_10_18: [(key, values, row)] of one text's scholarly English, for its translations group.
    A verse with a current scholarly English gets an en-x-scholar row (its English; translation_score its fidelity and
    translation_qa its fluency, as the judge gave them) and an en-x-scholar-meta row (JSON: status, flag, a person's
    acceptance, the judge; notes and doubts on a sentence's first verse; a sentence over several verses has its range
    on the first verse and "with" on the others, which have no English row of their own). As the edition takes them
    (export_html.py --scholar): a verse's latest version, made from its Sanskrit as it reads now, not rejected by a
    person. passages: id -> (page, idx); pinfo: id -> (Sanskrit, verse_ref)."""
    if not passages or not _has_table(con, "scholar_translations"):
        return []
    import scholar_translate as ST
    have = _cols(con, "scholar_translations")
    sel = ", ".join(c if c in have else "NULL" for c in _SCHOLAR_COLS)
    order = "page_no, idx, id" if {"page_no", "idx"} <= have else "id"
    rows = [dict(zip(_SCHOLAR_COLS, r)) for r in con.execute(
        "SELECT %s FROM scholar_translations WHERE doc_code = ? AND id IN (SELECT MAX(id) FROM scholar_translations "
        "WHERE doc_code = ? GROUP BY passage_id) ORDER BY %s" % (sel, order), (code, code))]
    live = []
    for r in rows:
        t = (pinfo.get(r["passage_id"]) or (None, None))[0]
        if r["passage_id"] in passages and t is not None and ST.src_hash(t) == r["src_hash"]:
            live.append(r)
    out = []
    for u in ST._units(live):
        r0 = u[0]
        if r0.get("review_verdict") == "reject":
            continue
        notes = []
        for n in ST._loads(r0.get("notes"), []):
            if isinstance(n, dict) and str(n.get("note") or "").strip():
                notes.append({k: str(n.get(k) or "").strip() for k in ("anchor", "note", "kind")
                              if str(n.get(k) or "").strip()})
        doubt = str(r0.get("doubts") or "").strip()
        status = str(r0.get("status") or "")
        flag = status in ("flagged", "source_doubt") and r0.get("review_verdict") != "accept"
        inline = ST._inline(u)
        rng = _scholar_range(u, pinfo) if len(u) > 1 else ""
        for k, r in enumerate(u):
            page, idx = passages[r["passage_id"]]
            meta = {"status": status, "flag": flag, "accepted": r.get("review_verdict") == "accept"}
            if r.get("judge_engine"):
                meta["judge"] = str(r["judge_engine"])
            if inline or k == 0:
                text = str((r.get("translation") if inline else (r0.get("group_translation") or r0.get("translation")))
                           or "")
                if k == 0:
                    if notes:
                        meta["notes"] = notes
                    if doubt:
                        meta["doubts"] = doubt
                    if rng and not inline:
                        meta["range"] = rng
            else:
                text = ""
                meta["with"] = rng
            if not text.strip() and not meta.get("with"):
                continue
            at = _clean(r.get("created_at"))
            if text.strip():
                vals = [code, page, idx, SCHOLAR_LANG, _clean(text), _clean(r.get("engine")),
                        _clean(r.get("prompt_version")), _clean(r.get("fidelity")), _clean(r.get("fluency")), at]
                out.append(("%d|%d|%s" % (page, idx, SCHOLAR_LANG), vals, dict(zip(_L10N_OUT, vals))))
            mj = json.dumps(meta, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
            vals = [code, page, idx, SCHOLAR_META_LANG, _clean(mj), None, SCHOLAR_META_VERSION, None, None, at]
            out.append(("%d|%d|%s" % (page, idx, SCHOLAR_META_LANG), vals, dict(zip(_L10N_OUT, vals))))
    return out


def scholar_count(con, docs) -> int:
    """SCHOLAR_MIRROR_2026_10_18: the scholarly English's translation rows of these texts (for --status)."""
    if not _has_table(con, "scholar_translations"):
        return 0
    have = {r[0] for r in con.execute("SELECT DISTINCT doc_code FROM scholar_translations")}
    pcols = _cols(con, "passages")
    n = 0
    for d in docs:
        if d[1] not in have:
            continue
        pos_, info_ = {}, {}
        for pid_, page_, idx_, text_, vref_ in con.execute(
                "SELECT p.id, p.page_no, p.idx, %s FROM passages p WHERE p.doc_id=?"
                % _sel(pcols, ("text", "verse_ref"), "p"), (d[0],)):
            pos_[pid_] = (page_, idx_)
            info_[pid_] = (text_, vref_)
        n += len({k for k, _v, _r in scholar_rows(con, d[1], pos_, info_)})
    return n


def build_doc_groups(con, doc, tables, ent_ok: set) -> dict:
''')

edit('scripts/corpus_sync.py', 3, r'''        passages = {}
        rows = con.execute(
''', r'''        passages = {}
        pinfo = {}   # SCHOLAR_MIRROR_2026_10_18: id -> (Sanskrit, verse_ref), for the scholarly English
        rows = con.execute(
''')

edit('scripts/corpus_sync.py', 4, r'''            passages[pid] = (page, idx)
''', r'''            passages[pid] = (page, idx)
            pinfo[pid] = (r[3 + PASSAGE_COLS.index("text")], r[3 + PASSAGE_COLS.index("verse_ref")])
''')

edit('scripts/corpus_sync.py', 5, r'''            out["translations"] = g
''', r'''            for key, vals, row in scholar_rows(con, code, passages, pinfo):   # SCHOLAR_MIRROR_2026_10_18
                if key in g.rows:
                    g.skipped += 1
                    continue
                g.add(key, vals, row)
            out["translations"] = g
''')

edit('scripts/corpus_sync.py', 6, r'''    if _has_table(con, "entity_mentions") and _has_table(con, "entities"):
        out["mentions"] = one(''', r'''    if _has_table(con, "scholar_translations"):   # SCHOLAR_MIRROR_2026_10_18: and the scholarly English's rows
        out["translations"] += scholar_count(con, docs)
    if _has_table(con, "entity_mentions") and _has_table(con, "entities"):
        out["mentions"] = one(''')

edit('tests/test_mirror_cap_2026_10_12.py', 1, r'''                later = sorted(SCRIPTS.glob(f + ".bak_readin_*")) or sorted(SCRIPTS.glob(f + ".bak_redeem_*"))
''', r'''                later = sorted(SCRIPTS.glob(f + ".bak_readin_*")) or sorted(SCRIPTS.glob(f + ".bak_redeem_*")) \
                    or sorted(SCRIPTS.glob(f + ".bak_scholarmirror_*"))   # SCHOLAR_MIRROR_2026_10_18 (corpus_sync.py)
''')


def load(p: Path):
    raw = p.read_bytes()
    nl = "\r\n" if raw.count(b"\r\n") > raw.count(b"\n") // 2 else "\n"
    return raw, raw.decode("utf-8").replace("\r\n", "\n"), nl


def compiles(data: bytes) -> str:
    fd, tmp = tempfile.mkstemp(suffix=".py")
    os.close(fd)
    try:
        Path(tmp).write_bytes(data)
        py_compile.compile(tmp, doraise=True, cfile=tmp + "c")
        return ""
    except py_compile.PyCompileError as e:
        return str(e).splitlines()[-1] if str(e) else "does not compile"
    finally:
        for x in (tmp, tmp + "c"):
            try:
                os.remove(x)
            except OSError:
                pass


def main() -> int:
    ap = argparse.ArgumentParser(); ap.add_argument("--check", action="store_true"); a = ap.parse_args()
    if not Path("scripts/dashboard.py").exists():
        print("FAIL: run from the automaton repo root."); return 2
    stamp = datetime.date.today().strftime("%Y%m%d")
    todo, problems = [], []
    for rel in FILES:
        p = Path(rel)
        if not p.exists():
            problems.append("%s not found" % rel); continue
        raw, src, nl = load(p)
        if MARK in src:
            print("skip %s (already carries %s)" % (rel, MARK)); continue
        if NEEDS[rel] not in src:
            problems.append("%s does not carry %s: this is not the file released" % (rel, NEEDS[rel])); continue
        out, bad = src, False
        for f, n, old, new in E:
            if f != rel:
                continue
            c = out.count(old)
            if c != 1:
                problems.append("%s: anchor %d found %d times (want 1): this is not the file released" % (rel, n, c))
                bad = True; continue
            out = out.replace(old, new, 1)
        if bad:
            continue
        if MARK not in out:
            problems.append("%s: the edits do not carry %s" % (rel, MARK)); continue
        data = out.replace("\n", nl).encode("utf-8")
        if all(x < 128 for x in raw) and not all(x < 128 for x in data):
            problems.append("%s would not be ASCII" % rel); continue
        if rel.endswith(".py"):
            err = compiles(data)
            if err:
                problems.append("%s would not compile: %s" % (rel, err)); continue
        todo.append((p, data))
    if problems:
        for x in problems:
            print("REFUSE: " + x)
        print("Nothing written."); return 1
    if a.check:
        print("CHECK OK: %d file(s) to write: %s. Nothing written." % (len(todo), ", ".join(str(p) for p, _ in todo)))
        return 0
    if not todo:
        print("Nothing to do: %s is in place." % MARK); return 0
    for p, data in todo:
        shutil.copy2(p, p.with_name(p.name + ".bak_%s_%s" % (TAG, stamp)))
        t = p.with_name(p.name + ".tmp_" + TAG); t.write_bytes(data); os.replace(t, p)
        print("wrote %s" % p)
    print("Next:")
    print('  python -m unittest tests.test_scholar_mirror_2026_10_18 tests.test_corpus_sync_2026_10_08 tests.test_mirror_cap_2026_10_12 tests.test_corpus_sync_split_2026_10_09')
    print('  python scripts\\corpus_sync.py   (the plan: the scholarly rows to send)')
    return 0


if __name__ == "__main__":
    sys.exit(main())
