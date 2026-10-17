#!/usr/bin/env python3
# -*- coding: ascii -*-
"""
patch_scholar_edition_2026_10_17.py  (2026-10-17)  SCHOLAR_EDITION_2026_10_17

Asked on 17 Oct: "can we have some authoritative and scholarly books from our corpus in our good html format like
ganita yuktibhasa". That format is export_html.py's edition (the Export button, Trilingual: the Sanskrit, its IAST,
the English, the notes at each chapter's end); its English is the working English. This gives it the scholarly
English (scripts/scholar_translate.py).

scripts/export_html.py (needs EXPORT_EMPTY_2026_10_07): --scholar. Each verse's latest scholarly row, kept while the
Sanskrit it was made from is the Sanskrit here; a sentence made over several verses once, after its verse range; its
notes and its doubts about the reading as the chapter's numbered notes; a dagger on a verse flagged or doubted and
not yet accepted by a person; a verse a person rejected, or with no current scholarly English, shows the working
English, marked as a draft. The title page names the models, the judge, the prompt and the counts. The file gains
_scholar (exports\\<doc>_<pages>_scholar.html): the working edition is never overwritten. Read only.
scripts/dashboard.py (needs TRANSLATION_DESK_2026_10_17): /api/export mode "scholar"; on a text's desk page (a text
with scholarly English) "Make the edition (free)" and "Open the newest" (/desk/<doc>/edition).
scripts/dashboard_static.html (needs TRANSLATION_DESK_2026_10_17): Export As offers "The scholarly edition".

Anchored, all-or-nothing, marker-idempotent; keeps line endings; py_compile before the atomic replace; backups
.bak_scholaredition_<date>. No database change.
  python scripts\\patch_scholar_edition_2026_10_17.py --check
  python scripts\\patch_scholar_edition_2026_10_17.py
"""
from __future__ import annotations
import argparse, datetime, os, py_compile, shutil, sys, tempfile
from pathlib import Path

MARK = 'SCHOLAR_EDITION_2026_10_17'
NEEDS = {'scripts/export_html.py': 'EXPORT_EMPTY_2026_10_07', 'scripts/dashboard.py': 'TRANSLATION_DESK_2026_10_17', 'scripts/dashboard_static.html': 'TRANSLATION_DESK_2026_10_17'}
FILES = list(NEEDS)
TAG = 'scholaredition'

E = []
def edit(f, n, old, new):
    E.append((f, n, old, new))


edit('scripts/export_html.py', 1, r'''# --- export core -------------------------------------------------------------
''', r'''# --- SCHOLAR_EDITION_2026_10_17: the scholarly English as an edition ----------
# Asked on 17 Oct for "authoritative and scholarly books from our corpus in our good html format like ganita
# yuktibhasa": this exporter's edition (the Sanskrit, its IAST, the English, the notes at each chapter's end), with
# the scholarly English (scripts/scholar_translate.py) in place of the working English. Per verse: its latest row
# (as /scholar/<doc>/prose reads it), kept only while the Sanskrit it was made from is the Sanskrit here (its
# src_hash); a sentence made over several verses stands once, after its verse range, the verses after it saying so;
# its notes become the chapter's numbered notes, its doubts about the reading too. A verse a person rejected, or with
# no current scholarly English, shows the working English, marked as such. A verse flagged by the judge or doubted
# for its reading, and not yet accepted by a person, carries a dagger. Read only: nothing is written but the file.

_SCH_CSS = (".sch-flag { color: #a0522d; font-size: .8em; margin-left: .15em; cursor: help; }"
            ".sch-rng { font-size: .72rem; color: var(--muted); font-family: 'JetBrains Mono',ui-monospace,monospace; "
            "margin-right: .35em; }"
            ".sch-wk { color: #555; }"
            ".sch-wk::before { content: 'working English, a draft: '; font-size: .72rem; color: var(--muted); "
            "font-style: italic; }"
            ".sch-with { color: var(--muted); font-style: italic; font-size: .85rem; }")


def _sch_meth(stats: dict) -> str:
    """The title page's methodology, for the scholarly edition."""
    return ("<div class='methodology'>The scholarly English of the Sanskrit Automaton (scholar_translate.py): each "
            "verse translated afresh from the Sanskrit given here, in the register of an unabridged translation made "
            "from a critical edition, with the verses around it and a glossary kept across the text; at most three "
            "notes a verse, at the end of each chapter, with the translator's doubts about the reading. A critic "
            "reads each draft, which is revised where it finds a fault; a judge reads every verse; the models are "
            "named above. A verse marked &#8224; was flagged by the judge or doubted for its reading and has not yet "
            "been read by a person. Square brackets hold a word the Sanskrit implies; italics, an untranslated term. "
            "A verse with no current scholarly English shows the working English (one pass), marked as a draft. A "
            "machine translation, to be read beside the Sanskrit and checked by a person: not a substitute for the "
            "critical text.</div>")


def _sch_prov(stats: dict) -> str:
    """The title page's line on the scholarly English."""
    if not stats.get("verses"):
        return ("<b>Scholarly English:</b> none current for this text%s; every verse shows the working English."
                % ((" (%d rejected by a person)" % stats["rejected"]) if stats.get("rejected") else " yet"))
    eng = ", ".join("%s (%d)" % (html.escape(str(k)), v) for k, v in sorted(stats["engines"].items(), key=lambda kv: -kv[1]))
    jud = ", ".join(html.escape(str(k)) for k in sorted(stats["judges"]))
    pv = ", ".join(html.escape(str(k)) for k in sorted(stats["prompts"]))
    return ("<b>Scholarly English:</b> %d of %d verses (passed %d, flagged %d, doubted for the reading %d; accepted by a "
            "person %d, rejected %d%s); made by %s; judged by %s; prompt %s.%s"
            % (stats["verses"], stats["shown"], stats["passed"], stats["flagged"], stats["doubt"], stats["accepted"],
               stats["rejected"], ("; %d left out, their Sanskrit changed since" % stats["stale"]) if stats["stale"] else "",
               eng or "-", jud or "-", pv or "-",
               (" The working English stands for %d other verse(s), marked." % stats["working"]) if stats["working"] else ""))


def _scholar_recs(con, doc, recs):
    """(recs, stats): each record's English replaced by its scholarly English where there is a current one."""
    import scholar_translate as ST
    stats = {"verses": 0, "shown": len(recs), "passed": 0, "flagged": 0, "doubt": 0, "accepted": 0, "rejected": 0,
             "stale": 0, "working": 0, "engines": {}, "judges": set(), "prompts": set()}
    if not doc or "scholar_translations" not in _tables(con):
        for r in recs:
            r["sch"] = {"working": True}
        stats["working"] = len(recs)
        return recs, stats
    ptext, pkey = {}, {}
    for pid, pg, ix, tx in con.execute("SELECT p.id, p.page_no, p.idx, p.text FROM passages p JOIN docs d ON d.id = p.doc_id "
                                       "WHERE d.code = ?", (doc,)):
        ptext[pid] = tx
        try:
            pkey[(int(pg), int(ix))] = pid
        except (TypeError, ValueError):
            pkey[(pg, ix)] = pid
    cur = con.execute("SELECT * FROM scholar_translations WHERE doc_code = ? AND id IN (SELECT MAX(id) FROM "
                      "scholar_translations WHERE doc_code = ? GROUP BY passage_id) ORDER BY page_no, idx, id", (doc, doc))
    names = [d_[0] for d_ in cur.description]
    rows = [dict(zip(names, tuple(x))) for x in cur.fetchall()]
    live = []
    for r in rows:
        t = ptext.get(r.get("passage_id"))
        if t is not None and ST.src_hash(t) == r.get("src_hash"):
            live.append(r)
        else:
            stats["stale"] += 1
    by_pid = {}
    for u in ST._units(live):
        r0 = u[0]
        notes = [n for n in ST._loads(r0.get("notes"), []) if isinstance(n, dict)]
        doubt = str(r0.get("doubts") or "").strip()
        flag = r0.get("status") in ("flagged", "source_doubt") and r0.get("review_verdict") != "accept"
        inline = ST._inline(u)
        rng = ST._range(u) if len(u) > 1 else ""
        for k, r in enumerate(u):
            meta = {"status": r0.get("status"), "flag": flag, "rejected": r0.get("review_verdict") == "reject",
                    "accepted": r.get("review_verdict") == "accept", "engine": str(r.get("engine") or "?"),
                    "judge": str(r.get("judge_engine") or ""), "prompt": str(r.get("prompt_version") or "")}
            if inline:
                meta.update(text=r.get("translation") or "", notes=notes if k == 0 else [], doubts=doubt if k == 0 else "")
            elif k == 0:
                meta.update(text=r0.get("group_translation") or r0.get("translation") or "", notes=notes, doubts=doubt,
                            range=rng)
            else:
                meta.update({"with": rng})
            by_pid[r["passage_id"]] = meta
    for rec in recs:
        try:
            pid = pkey.get((int(rec["page"]), int(rec["idx"])))
        except (TypeError, ValueError):
            pid = pkey.get((rec["page"], rec["idx"]))
        s = by_pid.get(pid)
        if s is not None and s.get("rejected"):
            stats["rejected"] += 1
            s = None
        if s is None or (not s.get("with") and not (s.get("text") or "").strip()):
            rec["sch"] = {"working": True}
            if (rec.get("en") or "").strip():
                stats["working"] += 1
            continue
        rec["sch"] = s
        rec["en"] = ("with " + s["with"]) if s.get("with") else re.sub(r"\s*//\s*", " ", s["text"]).strip()
        stats["verses"] += 1
        stats["passed"] += 1 if s["status"] == "passed" else 0
        stats["flagged"] += 1 if s["status"] == "flagged" else 0
        stats["doubt"] += 1 if s["status"] == "source_doubt" else 0
        stats["accepted"] += 1 if s["accepted"] else 0
        stats["engines"][s["engine"]] = stats["engines"].get(s["engine"], 0) + 1
        if s["judge"]:
            stats["judges"].add(s["judge"])
        if s["prompt"]:
            stats["prompts"].add(s["prompt"])
    return recs, stats


def _sch_en_html(en, sch, counter, notes_out, want_footnotes=True):
    """The scholarly English of a verse: italics for *terms*, each note's number after its anchor's first appearance,
    the dagger of a verse not yet read by a person; the working English marked as a draft."""
    if sch.get("working"):
        base = _inline_format(html.escape(en))
        base = _extract_footnotes(base, counter, notes_out) if want_footnotes else base
        return "<span class='sch-wk'>%s</span>" % base
    if sch.get("with"):
        return "<span class='sch-with'>Its English is given with %s, above.</span>" % html.escape(sch["with"])
    s = _inline_format(html.escape(en))
    if want_footnotes:
        for n in sch.get("notes") or []:
            counter[0] += 1
            k = counter[0]
            notes_out.append((k, "%s: %s" % (str(n.get("anchor") or "").strip(), str(n.get("note") or "").strip())))
            mark = "<sup class='fn-ref' id='fnr-%d'><a href='#fn-%d'>%d</a></sup>" % (k, k, k)
            a = html.escape(str(n.get("anchor") or "").strip())
            pos = s.find(a) if a else -1
            s = (s[:pos + len(a)] + mark + s[pos + len(a):]) if pos >= 0 else s + mark
        if sch.get("doubts"):
            counter[0] += 1
            k = counter[0]
            notes_out.append((k, "The reading: " + sch["doubts"]))
            s += "<sup class='fn-ref' id='fnr-%d'><a href='#fn-%d'>%d</a></sup>" % (k, k, k)
    if sch.get("range"):
        s = "<span class='sch-rng'>%s</span>%s" % (html.escape(sch["range"]), s)
    if sch.get("flag"):
        s += ("<span class='sch-flag' title='%s: not yet read by a person'>&#8224;</span>"
              % html.escape(str(sch.get("status") or "flagged").replace("_", " "), quote=True))
    return s


# --- export core -------------------------------------------------------------
''')

edit('scripts/export_html.py', 2, r'''            def _en_html():
                base = _inline_format(html.escape(en))
''', r'''            def _en_html():
                if r.get("sch") is not None:   # SCHOLAR_EDITION_2026_10_17
                    return _sch_en_html(en, r["sch"], fn_counter, fn_notes, want_footnotes)
                base = _inline_format(html.escape(en))
''')

edit('scripts/export_html.py', 3, r'''    subtitle = " / ".join(langs) + (" edition" if langs else "")
''', r'''    subtitle = " / ".join(langs) + (" edition" if langs else "")
    if prov.get("scholar") is not None:   # SCHOLAR_EDITION_2026_10_17
        subtitle = "The scholarly English" + (", with the Sanskrit" if include_san else "") + (
            " and the working " + hi_label if include_hi else "")
''')

edit('scripts/export_html.py', 4, r'''        pv.append(f"<b>English:</b> {en['count']} verses"
''', r'''        pv.append(("<b>Working English:</b> " if prov.get("scholar") is not None else "<b>English:</b> ")   # SCHOLAR_EDITION_2026_10_17
                  + f"{en['count']} verses"
''')

edit('scripts/export_html.py', 5, r'''    if pv:
        out.append("<div class='prov'>" + "<br/>".join(pv) + "</div>")
    out.append("<div class='methodology'>Machine translation produced by the Sanskrit "
''', r'''    if prov.get("scholar") is not None:   # SCHOLAR_EDITION_2026_10_17
        pv.append(_sch_prov(prov["scholar"]))
    if pv:
        out.append("<div class='prov'>" + "<br/>".join(pv) + "</div>")
    _meth_at = len(out)   # SCHOLAR_EDITION_2026_10_17: the methodology's place, for the scholarly edition's own
    out.append("<div class='methodology'>Machine translation produced by the Sanskrit "
''')

edit('scripts/export_html.py', 6, r'''               "substitute for the critical text.</div>")
    out.append("</div>")
''', r'''               "substitute for the critical text.</div>")
    if prov.get("scholar") is not None:   # SCHOLAR_EDITION_2026_10_17
        out[_meth_at] = _sch_meth(prov["scholar"])
    out.append("</div>")
''')

edit('scripts/export_html.py', 7, r'''                keep_frontmatter=False, images="none"):
    title = _display_title(title, doc)   # EXPORT_EMPTY_2026_10_07
''', r'''                keep_frontmatter=False, images="none", scholar=False):   # SCHOLAR_EDITION_2026_10_17: scholar
    title = _display_title(title, doc)   # EXPORT_EMPTY_2026_10_07
''')

edit('scripts/export_html.py', 8, r'''    prov = _provenance(con, doc, hi_lang)
    body, kept = _render(''', r'''    prov = _provenance(con, doc, hi_lang)
    if scholar:   # SCHOLAR_EDITION_2026_10_17: the scholarly English in place of the working English
        recs, prov["scholar"] = _scholar_recs(con, doc, recs)
    body, kept = _render(''')

edit('scripts/export_html.py', 9, r'''    if images == "approved":   # EXPORT_IMAGES_2026_10_04: never overwrite the plain edition
        suffix += "_img"
''', r'''    if scholar:   # SCHOLAR_EDITION_2026_10_17: never overwrite the working edition
        suffix += "_scholar"
    if images == "approved":   # EXPORT_IMAGES_2026_10_04: never overwrite the plain edition
        suffix += "_img"
''')

edit('scripts/export_html.py', 10, r'''        f.write(_with_fig_css(_html(title or (doc or "Export"), body, lang_attr=lang_attr), bool(figs) or bool(cover)))
''', r'''        _doc_html = _with_fig_css(_html(title or (doc or "Export"), body, lang_attr=lang_attr), bool(figs) or bool(cover))
        if scholar:   # SCHOLAR_EDITION_2026_10_17
            _doc_html = _doc_html.replace("</style>", _SCH_CSS + "</style>", 1)
        f.write(_doc_html)
''')

edit('scripts/export_html.py', 11, r'''    ap.add_argument("--debug", action="store_true")
    args = ap.parse_args()
''', r'''    ap.add_argument("--scholar", action="store_true",
                    help="SCHOLAR_EDITION_2026_10_17: the scholarly English (scholar_translate.py) with its notes in "
                         "place of the working English, which stands, marked, where there is none (file name "
                         "gains _scholar)")
    ap.add_argument("--debug", action="store_true")
    args = ap.parse_args()
''')

edit('scripts/export_html.py', 12, r'''                            hi_label=hi_label, want_toc=want_toc, want_footnotes=want_footnotes, debug=args.debug,
                            keep_frontmatter=args.keep_frontmatter, images=args.images)
''', r'''                            hi_label=hi_label, want_toc=want_toc, want_footnotes=want_footnotes, debug=args.debug,
                            keep_frontmatter=args.keep_frontmatter, images=args.images,
                            scholar=args.scholar)   # SCHOLAR_EDITION_2026_10_17
''')

edit('scripts/export_html.py', 13, r'''                        hi_label=hi_label, want_toc=want_toc, want_footnotes=want_footnotes, debug=args.debug,
                        keep_frontmatter=args.keep_frontmatter, images=args.images)
''', r'''                        hi_label=hi_label, want_toc=want_toc, want_footnotes=want_footnotes, debug=args.debug,
                        keep_frontmatter=args.keep_frontmatter, images=args.images,
                        scholar=args.scholar)   # SCHOLAR_EDITION_2026_10_17
''')

edit('scripts/dashboard.py', 1, r'''    elif mode == "tri":
        cmd += ["--sanskrit", "--hindi", "--side-by-side",
''', r'''    elif mode == "scholar":   # SCHOLAR_EDITION_2026_10_17: the scholarly English, its notes, the Sanskrit beside it
        cmd += ["--scholar", "--sanskrit", "--side-by-side",
                "--title", data.get("title") or f"{doc} - the scholarly English"]
    elif mode == "tri":
        cmd += ["--sanskrit", "--hindi", "--side-by-side",
''')

edit('scripts/dashboard.py', 2, r'''    h.append("</main>" + _DESK_JS + "</body></html>")
    return Response("".join(h), mimetype="text/html")


@app.post("/api/desk/scholar")
''', r'''    if sc.get("verses"):   # SCHOLAR_EDITION_2026_10_17: the edition, in the exporter's own format
        h.append('<div class="box"><h3>The edition (HTML)</h3><p class="small">The Sanskrit, its IAST and the '
                 'scholarly English side by side, its notes and doubts at the end of each chapter, a dagger on what '
                 'is flagged and not yet read by a person; where there is no current scholarly English, the working '
                 'English, marked as a draft. Free: nothing is called. The file: exports\\%s_<pages>_scholar.html.</p>'
                 '<div class="row"><button class="btn go dkbtn" onclick="deskEdition(\'%s\', this)">Make the '
                 'edition (free)</button> <a href="/desk/%s/edition" target="_blank">Open the newest</a></div>'
                 '<div class="out" id="dkedout"></div></div>' % (e(r["doc"]), e(r["doc"], quote=True),
                                                                 e(r["doc"], quote=True)))
    h.append("</main>" + _DESK_JS + "</body></html>")
    return Response("".join(h), mimetype="text/html")


@app.get("/desk/<doc>/edition")
def desk_edition(doc):
    """SCHOLAR_EDITION_2026_10_17: the newest scholarly edition of a text (exports/<doc>_<pages>[_tri]_scholar.html, made
    by the desk's "Make the edition" or Export As: the scholarly edition), served as it is. Read only."""
    import export_html as _ex
    d = _validate_doc(doc)
    if not d:
        return Response("invalid doc", status=400, mimetype="text/plain")
    out = ROOT / "exports"
    stem = _ex._safe_filename(d)
    got = sorted((p for p in out.glob(stem + "_*_scholar.html") if p.is_file()), key=lambda p: p.stat().st_mtime) \
        if out.is_dir() else []
    if not got:
        return Response("No scholarly edition of %s yet: make it on its desk page (free)." % d, status=404,
                        mimetype="text/plain")
    return send_from_directory(str(out), got[-1].name)


@app.post("/api/desk/scholar")
''')

edit('scripts/dashboard.py', 3, r'''(function(){ var r = document.getElementById('dkrunning'); if (r && r.getAttribute('data-job')){ _dkWatch(r.getAttribute('data-job'), function(){ location.reload(); }, document.getElementById('dklog')); } })();
''', r'''async function deskEdition(doc, btn){   /* SCHOLAR_EDITION_2026_10_17 */
  var o = document.getElementById('dkedout'); btn.disabled = true; o.textContent = 'making the edition (free)...';
  try{
    var r = await fetch('/api/export', {method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({doc: doc, mode: 'scholar'})});
    var d = await r.json();
    if (!d.job){ o.textContent = 'Could not start: ' + (d.error || 'unknown'); btn.disabled = false; return; }
    _dkWatch(d.job, function(j){ btn.disabled = false; var w = _dkLine(String(j.out || ''), '[export] ');
      o.innerHTML = j.ok ? 'Made: ' + w.replace(/</g, '&lt;') + ' <a href="/desk/' + encodeURIComponent(doc) + '/edition" target="_blank">Open it</a>' : 'It did not finish: the History has why.'; }, null);
  }catch(e){ o.textContent = 'Request failed: ' + e; btn.disabled = false; }
}
(function(){ var r = document.getElementById('dkrunning'); if (r && r.getAttribute('data-job')){ _dkWatch(r.getAttribute('data-job'), function(){ location.reload(); }, document.getElementById('dklog')); } })();
''')

edit('scripts/dashboard_static.html', 1, r'''          <option value="tri">Trilingual (Sa/En/Hi)</option>
''', r'''          <option value="tri">Trilingual (Sa/En/Hi)</option>
          <option value="scholar" title="SCHOLAR_EDITION_2026_10_17: the scholarly English with its notes, the Sanskrit beside it; the working English, marked, where there is none">The scholarly edition (Sa/En, notes)</option>
''')

edit('scripts/dashboard_static.html', 2, r'''  return m === 'tri' ? '(Sa/En/Hi)' : (m === 'hi' ? '(Hindi)' : '(English)');
''', r'''  if (m === 'scholar') return '(scholarly)';   // SCHOLAR_EDITION_2026_10_17
  return m === 'tri' ? '(Sa/En/Hi)' : (m === 'hi' ? '(Hindi)' : '(English)');
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
    print('  python -m unittest tests.test_scholar_edition_2026_10_17')
    print('  .\\scripts\\restart_dashboard.ps1 -Status   (then restart it when idle: the page needs the new server)')
    return 0


if __name__ == "__main__":
    sys.exit(main())
