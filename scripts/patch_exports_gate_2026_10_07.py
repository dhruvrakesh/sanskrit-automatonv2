#!/usr/bin/env python3
# -*- coding: ascii -*-
"""
patch_exports_gate_2026_10_07.py  (2026-10-07)

Four defects found by reading the editions and the graphic novel the dashboard made today, each
measured on backups/context_pre_storyfix_20261007.db (read-only):

  EXPORT_EMPTY_2026_10_07        scripts/export_html.py
    - siddhanta_shiromani has 1,146 passages and none translated. Its English export was 180 empty
      "Page N" headings, 180 lines of contents and "(No content matched your filters.)". A section
      whose rows all have nothing to show is now left out (unless an approved picture is anchored
      there). If nothing is left, the note says what is missing and the run prints a WARNING.
    - The Hindi line of the title page never appeared. translations_l10n is joined to passages,
      which has the same engine / mt_prompt_version / translation_qa columns; unqualified they were
      ambiguous, the query failed and the error was swallowed. They are qualified now. On
      markandeya_purana the line reads 1,244 verses, gemini:gemini-2.5-flash, QA 0.994.
    - A title that starts with the doc code (the dashboard and the pipeline pass
      "<code> - English Translation") shows the curated title from configs/doc_titles.json instead,
      else the code made readable, as the title page already did when no title was given.
  NOVEL_PRINT_2026_10_07         scripts/novel.py
    - The 16-page PDF of novel #1 had 2 blank pages: when a caption was long, the page number under
      it spilled onto a page of its own. Each page is now one page tall, the picture shrinks to leave
      room for the caption, and the number sits inside the caption box.
    - The cover said "passages 13.11-14.10", but the pages cite 13.9 and 13.10 too (the story's
      window). It now gives the span the pages actually cite.
    - The sources table printed the translator's verse marks "//"; they are dropped as on /texts.
    - build --cover N puts page N's picture on the cover (default 1, as before), so the cover need
      not repeat the first page.
  PUBLISH_GATE_LINES_2026_10_07  scripts/publish_srangam.py
    - The gate withheld a whole passage when its FIRST line was page furniture. Corpus-wide that
      withheld 404 translated passages, 402 of them with the verse below the furniture line. On the
      site: Markandeya p11.2, p73.3, p99.2 (a stray folio mark above the verse) and Sandilya p57.6,
      57.7, 69.8, 72.2, 72.3, 72.6, 75.6 (the source of a quotation above the quoted verse). A
      passage is now withheld only when every line is furniture: 6 corpus-wide (Sandilya p43.9 and
      p72.11, a reference with no verse; four bare numbers whose "translation" was invented, e.g.
      Shatapatha p17.3). Nothing published today is withheld by the change.
    - The decoration class lost its digit ranges to re.escape() (only 0 and 9 counted), so most
      Devanagari page numbers were not seen as furniture. The ranges are restored.
    - --emit-sql --only 11.2,73.3 writes only those passages (the text row and the check still use
      the whole publishable set), so a fix can be published without re-pasting a whole text.
  DOC_TITLES_2026_10_07          configs/doc_titles.json
    - markandeya_purana: "M\u0101rka\u1e47\u1e0deya Pur\u0101\u1e47a" (the title on the site since S4 M3).
    - nilamata_seg: "N\u012blamata Pur\u0101\u1e47a" (proposed: the retired upapurana_nilamata_purana is the
      same work, and its story 22 is the draining of the lake and Jalodbhava). Remove it if wrong.

Anchored, all-or-nothing, marker-idempotent per file; keeps each file's line endings; backups
.bak_expgate_<date>; every .py is compiled before it replaces the original.
  python scripts\\patch_exports_gate_2026_10_07.py --check
  python scripts\\patch_exports_gate_2026_10_07.py
"""
from __future__ import annotations
import argparse, datetime, json, os, py_compile, shutil, sys, tempfile
from pathlib import Path

MARKS = {"scripts/export_html.py": "EXPORT_EMPTY_2026_10_07",
         "scripts/novel.py": "NOVEL_PRINT_2026_10_07",
         "scripts/publish_srangam.py": "PUBLISH_GATE_LINES_2026_10_07"}

EDITS = {
"scripts/export_html.py": [
 ("display title helper",
  "def _safe_filename(s: str) -> str:\n",
  "def _display_title(title, doc):\n"
  "    \"\"\"EXPORT_EMPTY_2026_10_07: the dashboard and the pipeline pass '<doc code> - English Translation', so\n"
  "    the title page showed the raw code (siddhanta_shiromani). The code is replaced by the curated title in\n"
  "    configs/doc_titles.json, else by the code made readable. A title without the code is kept as given.\"\"\"\n"
  "    if not title or not doc or not title.startswith(doc):\n"
  "        return title\n"
  "    nice = None\n"
  "    try:\n"
  "        import collections_cfg as _cc\n"
  "        nice = _cc.load_titles().get(doc)\n"
  "    except Exception:\n"
  "        nice = None\n"
  "    return (nice or doc.replace(\"_\", \" \").title()) + title[len(doc):]\n\n"
  "def _safe_filename(s: str) -> str:\n"),
 ("provenance columns",
  "        eng_col = \"engine\" if \"engine\" in _colnames(con, table) else \"NULL\"\n"
  "        pv_col  = \"mt_prompt_version\" if \"mt_prompt_version\" in _colnames(con, table) else \"NULL\"\n"
  "        qa_col  = \"translation_qa\" if \"translation_qa\" in _colnames(con, table) else \"NULL\"\n",
  "        # EXPORT_EMPTY_2026_10_07: qualified. translations_l10n is joined to passages, which has the same\n"
  "        # three columns; unqualified they were ambiguous and the Hindi line of the title page vanished.\n"
  "        eng_col = \"p.engine\" if \"engine\" in _colnames(con, table) else \"NULL\"\n"
  "        pv_col  = \"p.mt_prompt_version\" if \"mt_prompt_version\" in _colnames(con, table) else \"NULL\"\n"
  "        qa_col  = \"p.translation_qa\" if \"translation_qa\" in _colnames(con, table) else \"NULL\"\n"),
 ("drop empty sections",
  "    # \u2500\u2500 TOC \u2500\u2500\n",
  "    # EXPORT_EMPTY_2026_10_07: a section whose rows all have nothing to show in the chosen languages\n"
  "    # used to keep its heading and its line in the contents (an untranslated text exported as 180\n"
  "    # empty \"Page N\" headings). It is left out, unless an approved picture is anchored on its pages.\n"
  "    def _shows(r):\n"
  "        en_ = (r[\"en\"] or \"\").strip()\n"
  "        if include_en and drop_junk_en and _is_junk_en(en_):\n"
  "            en_ = \"\"\n"
  "        return bool((include_san and (r[\"san\"] or \"\").strip()) or (include_en and en_)\n"
  "                    or (include_hi and (r[\"loc\"] or \"\").strip()))\n"
  "    _fig_pages = {k[0] for k in (figures or {})}\n"
  "    sections = OrderedDict((k, v) for k, v in sections.items()\n"
  "                           if any(_shows(r) for r in v) or any(r[\"page\"] in _fig_pages for r in v))\n\n"
  "    # \u2500\u2500 TOC \u2500\u2500\n"),
 ("empty note",
  "    if kept == 0:\n"
  "        out.append(\"<p class='note'>(No content matched your filters.)</p>\")\n",
  "    if kept == 0:   # EXPORT_EMPTY_2026_10_07: say what is missing\n"
  "        want = [x for x, on in ((\"English\", include_en), (hi_label, include_hi), (\"Sanskrit\", include_san)) if on]\n"
  "        out.append(\"<p class='note'>Nothing to show yet: no passage in this range has %s text%s.</p>\"\n"
  "                   % (html.escape(\" or \".join(want) or \"any\"),\n"
  "                      \"\" if include_san else \" (an export with --sanskrit shows the Sanskrit)\"))\n"),
 ("title in export",
  "    san_col, en_col = _detect_cols(con, doc, force_san, force_en, debug=debug)\n",
  "    title = _display_title(title, doc)   # EXPORT_EMPTY_2026_10_07\n"
  "    san_col, en_col = _detect_cols(con, doc, force_san, force_en, debug=debug)\n"),
 ("keep retry count",
  "        body, _ = _render(doc, recs, prov, include_san=include_san, include_en=include_en,\n",
  "        body, kept = _render(doc, recs, prov, include_san=include_san, include_en=include_en,\n"),
 ("summary line",
  "    if debug: print(f\"[export] wrote {out_path} | recs={len(recs)} | san='{san_col}' en='{en_col}' hi='{hi_lang}'\")\n",
  "    if debug: print(f\"[export] wrote {out_path} | recs={len(recs)} | san='{san_col}' en='{en_col}' hi='{hi_lang}'\")\n"
  "    if kept == 0:   # EXPORT_EMPTY_2026_10_07\n"
  "        print(f\"[export] WARNING {doc}: pages {lo}-{hi} have nothing to show in the chosen languages \"\n"
  "              f\"({len(recs)} passages read); {out_path} holds only the title page and a note.\")\n"
  "    else:\n"
  "        print(f\"[export] wrote {out_path}: {kept} passage(s)\")\n"),
],
"scripts/novel.py": [
 ("mt display helper",
  "def build(con, nid: int, out: Path) -> Path:\n",
  "def _mt_display(t: str) -> str:\n"
  "    \"\"\"NOVEL_PRINT_2026_10_07: the translator ends each verse with '//'; a reader sees none (as on /texts).\"\"\"\n"
  "    return re.sub(r\"\\s+//(?:\\s+|$)\", \" \", re.sub(r\"\\s*//\\s*$\", \"\", t or \"\")).strip()\n\n\n"
  "def build(con, nid: int, out: Path, cover_page: int = 1) -> Path:\n"),
 ("number inside caption",
  "        secs.append(\"<section class='pg'>%s<div class='cap'>%s%s<div class='hi'>%s</div></div><div class='no'>%d</div>\"\n"
  "                    \"</section>\" % (pic, cap(p.get(\"caption\") or \"\"), speech, cap(p.get(\"caption_hi\") or \"\"), p[\"n\"]))\n",
  "        # NOVEL_PRINT_2026_10_07: the number sits inside the caption box, so it can never spill onto a page\n"
  "        # of its own (two blank pages in the 16-page PDF of novel #1).\n"
  "        secs.append(\"<section class='pg'>%s<div class='cap'><span class='no'>%d</span>%s%s<div class='hi'>%s</div>\"\n"
  "                    \"</div></section>\" % (pic, p[\"n\"], cap(p.get(\"caption\") or \"\"), speech,\n"
  "                                          cap(p.get(\"caption_hi\") or \"\")))\n"),
 ("sources without verse marks",
  "    src = \"\".join(\"<tr><td>%s</td><td>%s</td></tr>\" % (c, html.escape(rows[c][4]))\n",
  "    src = \"\".join(\"<tr><td>%s</td><td>%s</td></tr>\" % (c, html.escape(_mt_display(rows[c][4])))\n"),
 ("cover page and cited span",
  "    first = (n[\"page_images\"].get(\"1\") or {}).get(\"path\")\n",
  "    # NOVEL_PRINT_2026_10_07: --cover N; and the span the pages cite, not the story's own range (the\n"
  "    # pages may cite the two passages before it, which the story's window includes).\n"
  "    first = (n[\"page_images\"].get(str(cover_page)) or {}).get(\"path\")\n"
  "    _cited = sorted((n[\"verify\"] or {}).get(\"cited\") or [], key=lambda c: st.parse_ref(c) or (0, 0))\n"
  "    span = ((_cited[0], _cited[-1]) if _cited else\n"
  "            (st.ref(s[\"from_page\"], s[\"from_idx\"]), st.ref(s[\"to_page\"], s[\"to_idx\"])))\n"),
 ("page layout css",
  "           \".cover,.pg{page-break-after:always;min-height:95vh;display:flex;flex-direction:column;align-items:center;\"\n"
  "           \"justify-content:center;padding:0 6mm}.cover h1{font-size:2.2rem;text-align:center;margin:.6rem 0}\"\n"
  "           \".cover img,.pg img{max-width:100%;max-height:72vh;border-radius:4px}.cap{max-width:42rem;font-size:\"\n",
  "           \".cover,.pg{break-after:page;page-break-after:always;height:96vh;box-sizing:border-box;display:flex;\"\n"
  "           \"flex-direction:column;align-items:center;justify-content:center;padding:0 6mm}\"\n"
  "           \".cover h1{font-size:2.2rem;text-align:center;margin:.6rem 0}\"\n"
  "           \".cover img,.pg img{flex:0 1 auto;min-height:0;max-width:100%;max-height:100%;object-fit:contain;\"\n"
  "           \"border-radius:4px}.cap{flex:0 0 auto;break-inside:avoid;max-width:42rem;font-size:\"\n"),
 ("number style",
  "solid #e3d4ad;border-radius:6px;padding:.6rem .9rem}.say{margin-top:.4rem;font-style:italic}.no{color:#999;\"\n"
  "           \"font-size:.8rem;margin-top:.4rem}",
  "solid #e3d4ad;border-radius:6px;padding:.6rem .9rem}.say{margin-top:.4rem;font-style:italic}.no{color:#999;\"\n"
  "           \"font-size:.8rem;float:right;margin:0 0 .2rem .6rem}"),
 ("cited span on the cover",
  "               html.escape(s.get(\"title\") or \"\"), html.escape(book_t), st.ref(s[\"from_page\"], s[\"from_idx\"]),\n"
  "               st.ref(s[\"to_page\"], s[\"to_idx\"]), \"\".join(secs),\n",
  "               html.escape(s.get(\"title\") or \"\"), html.escape(book_t), span[0], span[1], \"\".join(secs),\n"),
 ("cli cover",
  "    b = sub.add_parser(\"build\"); b.add_argument(\"--id\", type=int, required=True); b.add_argument(\"--out\", default=None)\n",
  "    b = sub.add_parser(\"build\"); b.add_argument(\"--id\", type=int, required=True); b.add_argument(\"--out\", default=None)\n"
  "    b.add_argument(\"--cover\", type=int, default=1, help=\"page whose picture goes on the cover (NOVEL_PRINT_2026_10_07)\")\n"),
 ("cli cover call",
  "            path = build(con, args.id, out)\n",
  "            path = build(con, args.id, out, args.cover)\n"),
],
"scripts/publish_srangam.py": [
 ("furniture-only",
  "def gate_has_furniture(text: str) -> bool:\n"
  "    \"\"\"True when the passage still LEADS with page furniture. Same detector as\n"
  "    text_filters.strip_page_furniture, which measured 226/226 furniture cases\n"
  "    caught, 0 content loss and 0 false positives over 1,321 real passages.\"\"\"\n"
  "    return bool(text) and _gate_is_furniture_line(text.split(\"\\n\")[0])\n",
  "def gate_has_furniture(text: str) -> bool:\n"
  "    \"\"\"True when the passage is page furniture and nothing else. Same line detector as\n"
  "    text_filters.strip_page_furniture (226/226 furniture lines caught, 0 false positives\n"
  "    over 1,321 real passages).\n\n"
  "    PUBLISH_GATE_LINES_2026_10_07: it used to be enough for the FIRST line to be furniture, and\n"
  "    that withheld 404 translated passages, 402 of them with the verse below the furniture line\n"
  "    (on the site: Markandeya p11.2, p73.3, p99.2; Sandilya p57.6, 57.7, 69.8, 72.2, 72.3, 72.6,\n"
  "    75.6). Such a passage is published as read from the page, its first line included.\"\"\"\n"
  "    lines = [ln for ln in (text or \"\").split(\"\\n\") if ln.strip()]\n"
  "    return bool(lines) and all(_gate_is_furniture_line(ln) for ln in lines)\n"),
 ("only argument",
  "    ap.add_argument(\"--sql-batch\", type=int, default=200,\n"
  "                    help=\"passages per SQL file for --emit-sql (default 200)\")\n",
  "    ap.add_argument(\"--sql-batch\", type=int, default=200,\n"
  "                    help=\"passages per SQL file for --emit-sql (default 200)\")\n"
  "    ap.add_argument(\"--only\", default=None, metavar=\"P.I,P.I\",\n"
  "                    help=\"PUBLISH_GATE_LINES_2026_10_07: with --emit-sql, write only these passages \"\n"
  "                         \"(page.idx, comma separated); the text row and the check use the whole set\")\n"),
 ("only in main",
  "    if args.emit_sql:\n"
  "        emit_sql(args.emit_sql, doc, rows, args.engine, source_note, args.sql_batch,\n"
  "                 title_override=args.title)\n"
  "        return\n",
  "    if args.emit_sql:\n"
  "        only = None\n"
  "        if args.only:   # PUBLISH_GATE_LINES_2026_10_07\n"
  "            only = set()\n"
  "            for part in args.only.split(\",\"):\n"
  "                bits = part.strip().split(\".\")\n"
  "                if len(bits) != 2 or not all(b.isdigit() for b in bits):\n"
  "                    sys.exit(f\"ERROR: --only takes page.idx values like 11.2, not {part.strip()!r}.\")\n"
  "                only.add((int(bits[0]), int(bits[1])))\n"
  "            have = {(int(r[\"page_no\"]), int(r[\"idx\"])) for r in rows}\n"
  "            missing = sorted(only - have)\n"
  "            if missing:\n"
  "                sys.exit(\"ERROR: not in the publishable set (withheld or untranslated): \"\n"
  "                         + \", \".join(\"%d.%d\" % k for k in missing))\n"
  "        emit_sql(args.emit_sql, doc, rows, args.engine, source_note, args.sql_batch,\n"
  "                 title_override=args.title, only=only)\n"
  "        return\n"),
 ("decor ranges",
  "_GF_DECOR = _gate_re.compile(\"[\" + _gate_re.escape(_GF_PUNCT) + r\"\\s]+\")\n",
  "# PUBLISH_GATE_LINES_2026_10_07: escape() turned the two ranges in _GF_PUNCT into the literal characters\n"
  "# 0, - and 9, so a page number such as '23' in Devanagari digits was not decoration. The ranges are\n"
  "# put back after the rest is escaped.\n"
  "_GF_DECOR = _gate_re.compile(\"[\" + _gate_re.escape(_GF_PUNCT.replace(\"\\u0966-\\u096f\", \"\").replace(\"0-9\", \"\"))\n"
  "                             + \"\\u0966-\\u096f0-9\" + r\"\\s]+\")\n"),
 ("emit_sql signature",
  "def emit_sql(out_dir, doc, rows, engine, source_note, batch=200, max_bytes=450000,\n"
  "             title_override=None):\n",
  "def emit_sql(out_dir, doc, rows, engine, source_note, batch=200, max_bytes=450000,\n"
  "             title_override=None, only=None):\n"),
 ("emit only rows",
  "    chunks, cur, size = [], [], 0\n"
  "    for r in rows:\n",
  "    chunks, cur, size = [], [], 0\n"
  "    sel = [r for r in rows if not only or (int(r[\"page_no\"]), int(r[\"idx\"])) in only]   # PUBLISH_GATE_LINES_2026_10_07\n"
  "    for r in sel:\n"),
 ("manifest only",
  "           \"local publishable passages: %d  (after the publication gate)\" % len(rows),\n",
  "           \"local publishable passages: %d  (after the publication gate)\" % len(rows),\n"
  "           \"passages in these files: %d%s\" % (len(sel), \"  (--only)\" if only else \"\"),\n"),
],
}

TITLES = {"markandeya_purana": "M\u0101rka\u1e47\u1e0deya Pur\u0101\u1e47a",
          "nilamata_seg": "N\u012blamata Pur\u0101\u1e47a"}
TITLE_SOURCES = {
    "markandeya_purana": "DOC_TITLES_2026_10_07: the title on the Srangam site since S4 M3 (2026-10-07)",
    "nilamata_seg": "DOC_TITLES_2026_10_07: proposed; the retired upapurana_nilamata_purana is the same work and its "
                    "story 22 is the draining of the lake and Jalodbhava. Remove if wrong."}


def load(p: Path):
    raw = p.read_bytes(); crlf = raw.count(b"\r\n")
    return raw.decode("utf-8").replace("\r\n", "\n"), ("\r\n" if crlf > (raw.count(b"\n") - crlf) else "\n")


def main() -> int:
    ap = argparse.ArgumentParser(); ap.add_argument("--check", action="store_true"); a = ap.parse_args()
    if not Path("scripts/stories.py").exists():
        print("FAIL: run from the automaton repo root."); return 2
    stamp = datetime.date.today().strftime("%Y%m%d")
    todo, problems = [], []
    for rel, edits in EDITS.items():
        p = Path(rel); src, nl = load(p)
        if MARKS[rel] in src:
            print("skip %s (already carries %s)" % (rel, MARKS[rel])); continue
        out = src
        for name, old, new in edits:
            c = out.count(old)
            if c != 1:
                problems.append("%s: anchor '%s' found %d times (want 1)" % (rel, name, c)); continue
            out = out.replace(old, new, 1)
        todo.append((p, out.replace("\n", nl).encode("utf-8"), True))
    tp = Path("configs/doc_titles.json")
    try:
        d = json.loads(tp.read_text(encoding="utf-8"))
        t = d.setdefault("titles", {})
        add = {k: v for k, v in TITLES.items() if k not in t}
        clash = {k: t[k] for k in TITLES if k in t and t[k] != TITLES[k]}
        if clash:
            print("note: doc_titles.json already names %s; left as it is" % ", ".join(sorted(clash)))
        if add:
            t.update(add)
            d.setdefault("_sources", {}).update({k: TITLE_SOURCES[k] for k in add})
            raw = tp.read_bytes(); nl = "\r\n" if b"\r\n" in raw else "\n"
            todo.append((tp, (json.dumps(d, ensure_ascii=False, indent=2) + "\n").replace("\n", nl).encode("utf-8"), False))
        else:
            print("skip configs/doc_titles.json (titles present)")
    except (OSError, ValueError) as e:
        problems.append("configs/doc_titles.json: %s" % e)
    if problems:
        for x in problems:
            print("REFUSE: " + x)
        print("Nothing written."); return 1
    for p, data, is_py in todo:   # compile every new .py before anything is replaced
        if is_py:
            fd, tmp = tempfile.mkstemp(suffix=".py"); os.close(fd)
            Path(tmp).write_bytes(data)
            try:
                py_compile.compile(tmp, doraise=True)
            except py_compile.PyCompileError as e:
                print("REFUSE: %s would not compile: %s" % (p, e)); print("Nothing written."); return 1
            finally:
                os.unlink(tmp)
    if a.check:
        print("CHECK OK: %d file(s) to write: %s. Nothing written." % (len(todo), ", ".join(str(p) for p, _, _ in todo)))
        return 0
    for p, data, _ in todo:
        shutil.copy2(p, p.with_name(p.name + ".bak_expgate_" + stamp))
        t = p.with_name(p.name + ".tmp_expgate"); t.write_bytes(data); os.replace(t, p)
        print("wrote %s" % p)
    return 0


if __name__ == "__main__":
    sys.exit(main())
