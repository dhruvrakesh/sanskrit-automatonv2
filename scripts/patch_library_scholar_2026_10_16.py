#!/usr/bin/env python3
# -*- coding: ascii -*-
"""
patch_library_scholar_2026_10_16.py  (2026-10-16)  LIBRARY_SCHOLAR_2026_10_16

Asked on 16 Oct: "the library does not seem to reflect the substantial amount of work done by sonnet api in
translation. fix that too!" The Library's cards count the working English (passages.translation, which the site
shows); the scholarly English (scholar_translate.py, the table scholar_translations) was only on /scholar. On 15 Oct
claude-sonnet-5-5 made 1,418 verses of the Hayasirsa Pancaratra and 1,018 of the Karanagama, and the cards said
"EN 1/1614" and "EN 368/1908".

scripts/dashboard.py:
  - _scholar_cover(con): per text, its scholarly English: the verses (each verse's latest row, as /scholar/<doc> shows
    it, whose Sanskrit is unchanged), passed, flagged, source doubts, accepted and rejected by a person, stale, the
    engines, the $ of all its rows, the last row's time. Counted again when a row or a passage is added, or after two
    minutes; {} on any error (the Library is never stopped by it);
  - the Library: a card carries "SC n" beside "EN n/N", and under it a line "Scholarly English: n verses by <engine>:
    passed, flagged, source doubts", with its links (verse by verse; as prose); a text with scholarly English and no
    working English is listed too; the header counts the verses in scholarly English (a link to /scholar);
  - the reader (/reader/<doc>, /api/passages/<doc>): in English, a verse's scholarly English above its working English,
    with its status (passed, flagged, source doubt; accepted or rejected by a person) and a link to its notes and checks
    on /scholar/<doc>; the header says how many verses are in scholarly English; "Not yet translated" says it is the
    working English that is not.
Read-only: the working English, the site and the scholarly rows are not changed.

Anchored, all-or-nothing, marker-idempotent; keeps line endings; the new text ASCII; py_compile before the atomic
replace; backup .bak_libsch_<date>.
  python scripts\\patch_library_scholar_2026_10_16.py --check
  python scripts\\patch_library_scholar_2026_10_16.py
"""
from __future__ import annotations
import argparse, datetime, os, py_compile, shutil, sys, tempfile
from pathlib import Path

MARK = "LIBRARY_SCHOLAR_2026_10_16"
NEEDS = {"scripts/dashboard.py": "REDEEM_2026_10_14"}
FILES = list(NEEDS)
TAG = "libsch"

E = []
def edit(f, n, old, new):
    E.append((f, n, old, new))


D = "scripts/dashboard.py"

edit(D, 1, r'''@app.get("/scholar")
def scholar_index_page():
''', r'''# LIBRARY_SCHOLAR_2026_10_16 -----------------------------------------------------------------------------------
# The scholarly English (scripts/scholar_translate.py, the table scholar_translations) on the Library's cards and in
# the reader, beside the working English (passages.translation, which the site shows). Read-only: the working English,
# the site and the scholarly rows are not changed.
_SCHOLAR_COVER = {"key": None, "at": 0.0, "res": {}}
_SCHOLAR_TTL = 120.0   # seconds: counted again at most this often, unless a row or a passage is added
_SCHOLAR_CSS = (".badge.sc{background:#2a1f3a;color:#c3a6e8}"
                ".schl{display:block;margin-top:6px;font-family:'Inter',sans-serif;font-size:10.5px;line-height:1.45;"
                "color:#c3a6e8;border-left:2px solid #5a4380;padding:2px 0 2px 7px}.schl a{color:inherit}"
                ".schl b{color:var(--cream)}")


def _scholar_st():
    if str(SCRIPTS) not in sys.path:
        sys.path.insert(0, str(SCRIPTS))
    import scholar_translate as _st
    return _st


def _scholar_cover(con) -> Dict[str, dict]:
    """LIBRARY_SCHOLAR_2026_10_16: {doc: its scholarly English}: "verses" (each verse's latest row, as /scholar/<doc>
    shows it, whose Sanskrit is unchanged), "passed", "flagged", "source_doubt", "accepted" and "rejected" (by a person),
    "stale" (the Sanskrit changed since), "engines" ({engine: verses}), "spent" ($ of all its rows), "last" (the last
    row's time). Counted again when a row or a passage is added, or after _SCHOLAR_TTL; {} when there is no such table
    or on any error (the Library is never stopped by it)."""
    try:
        if not con.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='scholar_translations'").fetchone():
            return {}
        key = tuple(con.execute("SELECT (SELECT MAX(id) FROM scholar_translations), (SELECT COUNT(*) FROM "
                                "scholar_translations), (SELECT MAX(id) FROM passages)").fetchone())
        now_ = time.time()
        if _SCHOLAR_COVER["key"] == key and now_ - _SCHOLAR_COVER["at"] < _SCHOLAR_TTL:
            return _SCHOLAR_COVER["res"]
        _st = _scholar_st()
        res: Dict[str, dict] = {}
        for doc, st, h, rv, eng, ptext in con.execute(
                "SELECT s.doc_code, s.status, s.src_hash, s.review_verdict, s.engine, p.text FROM scholar_translations s "
                "LEFT JOIN passages p ON p.id = s.passage_id WHERE s.id IN (SELECT MAX(id) FROM scholar_translations "
                "GROUP BY passage_id)"):
            c = res.setdefault(doc, {"verses": 0, "passed": 0, "flagged": 0, "source_doubt": 0, "accepted": 0,
                                     "rejected": 0, "stale": 0, "engines": {}, "spent": 0.0, "last": ""})
            if ptext is None or _st.src_hash(ptext) != h:
                c["stale"] += 1
                continue
            c["verses"] += 1
            if st in ("passed", "flagged", "source_doubt"):
                c[st] += 1
            if rv == "accept":
                c["accepted"] += 1
            elif rv == "reject":
                c["rejected"] += 1
            c["engines"][eng or "?"] = c["engines"].get(eng or "?", 0) + 1
        for doc, spent, last in con.execute("SELECT doc_code, COALESCE(SUM(cost_usd), 0), MAX(created_at) FROM "
                                            "scholar_translations GROUP BY doc_code"):
            if doc in res:
                res[doc]["spent"] = float(spent or 0.0)
                res[doc]["last"] = str(last or "")
        _SCHOLAR_COVER.update(key=key, at=now_, res=res)
        return res
    except Exception:
        return {}


def _scholar_badge(code: str, sc: dict) -> str:
    """LIBRARY_SCHOLAR_2026_10_16: the card's "SC n" ('' when none)."""
    c = (sc or {}).get(code)
    if not c or not c.get("verses"):
        return ""
    return ('<span class="badge sc" title="Verses in scholarly English (scholar_translate.py), beside the working '
            'English (EN)">SC {:,}</span>'.format(c["verses"]))


def _scholar_line(code: str, sc: dict) -> str:
    """LIBRARY_SCHOLAR_2026_10_16: the card's line for its scholarly English, with the links to read it ('' when none)."""
    import html as _html
    from urllib.parse import quote
    c = (sc or {}).get(code)
    if not c or not (c.get("verses") or c.get("stale")):
        return ""
    n_ = lambda v: "{:,}".format(int(v or 0))
    top = sorted(c["engines"].items(), key=lambda kv: (-kv[1], kv[0]))
    eng = (top[0][0].split(":", 1)[-1] + ((" and %d other%s" % (len(top) - 1, "s" if len(top) > 2 else ""))
                                          if len(top) > 1 else "")) if top else "?"
    parts = ["%s passed" % n_(c["passed"]), "%s flagged" % n_(c["flagged"])]
    if c["source_doubt"]:
        parts.append("%s source doubts" % n_(c["source_doubt"]))
    if c["accepted"] or c["rejected"]:
        parts.append("%s accepted and %s rejected by a person" % (n_(c["accepted"]), n_(c["rejected"])))
    if c["stale"]:
        parts.append("%s stale (the Sanskrit changed)" % n_(c["stale"]))
    q = quote(code, safe="")
    tip = ("The scholarly English, verse by verse (scholar_translate.py): drafted with its context and glossary, read by "
           "a critic, revised, judged. It is kept beside the working English (EN, which the site shows) and is not on "
           "the site yet. $%.2f spent on all its rows; the last on %s." % (c["spent"], c["last"][:16].replace("T", " ")))
    return ('<div class="schl" title="%s">Scholarly English: <b>%s</b> verses by %s; %s. <a href="/scholar/%s">Verse by '
            'verse</a> &middot; <a href="/scholar/%s/prose">as prose</a></div>'
            % (_html.escape(tip, quote=True), n_(c["verses"]), _html.escape(eng), _html.escape(", ".join(parts)), q, q))


def _scholar_sum(sc: dict) -> str:
    """LIBRARY_SCHOLAR_2026_10_16: the Library header's count of the verses in scholarly English ('' when none)."""
    n = sum(int(c.get("verses") or 0) for c in (sc or {}).values())
    if not n:
        return ""
    return (" &middot; <a href='/scholar' style='color:#c3a6e8;text-decoration:none' title='LIBRARY_SCHOLAR_2026_10_16: "
            "the scholarly English, text by text'>{:,} verses in scholarly English</a>".format(n))


def _scholar_rows(con, doc: str, type_clause: str = "", type_params=(), limit: int = 50, offset: int = 0) -> tuple:
    """LIBRARY_SCHOLAR_2026_10_16: ({(page_no, idx): its scholarly English}, the text's verses in scholarly English) for
    the passages one reader page lists (the filter, order, limit and offset of /api/passages): each passage's latest
    row, as /scholar/<doc> shows it, when its Sanskrit is unchanged, and the link to it there (that page shows 200 rows
    a page). ({}, 0) when there is none, or on any error."""
    try:
        n = int(((_scholar_cover(con).get(doc) or {}).get("verses")) or 0)
        if not n:
            return {}, 0
        listed = con.execute("SELECT p.id, p.page_no, p.idx, p.text FROM passages p JOIN docs d ON d.id=p.doc_id WHERE "
                             "d.code=?%s ORDER BY p.page_no, p.idx LIMIT ? OFFSET ?" % type_clause,
                             (doc, *type_params, limit, offset)).fetchall()
        if not listed:
            return {}, n
        from urllib.parse import quote
        _st = _scholar_st()
        order = [r[0] for r in con.execute(
            "SELECT s.passage_id FROM scholar_translations s LEFT JOIN passages p ON p.id = s.passage_id WHERE "
            "s.doc_code = ? AND s.id IN (SELECT MAX(id) FROM scholar_translations WHERE doc_code = ? GROUP BY "
            "passage_id) ORDER BY COALESCE(p.page_no, s.page_no), COALESCE(p.idx, s.idx), s.id", (doc, doc))]
        rank = {pid: k for k, pid in enumerate(order)}
        ids = [r[0] for r in listed]
        got = {}
        for pid, tr, st, h, eng, gref, ref, rv in con.execute(
                "SELECT passage_id, translation, status, src_hash, engine, group_ref, verse_ref, review_verdict FROM "
                "scholar_translations WHERE id IN (SELECT MAX(id) FROM scholar_translations WHERE passage_id IN (%s) "
                "GROUP BY passage_id)" % ",".join("?" * len(ids)), ids):
            got[pid] = (tr, st, h, eng, gref, ref, rv)
        out, q = {}, quote(doc, safe="")
        for pid, page, idx, text in listed:
            g = got.get(pid)
            if not g or not (g[0] or "").strip() or _st.src_hash(text) != g[2]:
                continue
            tr, st, _h, eng, gref, ref, rv = g
            anchor = str(gref).split("-", 1)[0] if gref else str(ref or "")
            out[(page, idx)] = {"translation": tr, "status": st or "", "engine": eng or "", "review": rv or "",
                                "sentence": gref or "", "ref": ref or "",
                                "href": "/scholar/%s?offset=%d#v-%s" % (q, (rank.get(pid, 0) // 200) * 200,
                                                                       quote(anchor, safe=".-_"))}
        return out, n
    except Exception:
        return {}, 0


def _with_scholar(d: dict, sch: dict) -> dict:
    """LIBRARY_SCHOLAR_2026_10_16: a reader passage with its scholarly English, when it has one."""
    s = (sch or {}).get((d.get("page_no"), d.get("idx")))
    if s:
        d["scholar"] = s
    return d


@app.get("/scholar")
def scholar_index_page():
''')

edit(D, 2, r'''        except Exception:
            qa = {}
        con.close()
''', r'''        except Exception:
            qa = {}
        sc = _scholar_cover(con)   # LIBRARY_SCHOLAR_2026_10_16: the scholarly English, per text
        con.close()
''')

edit(D, 3, r'''        if en == 0:
            continue  # only list readable texts
''', r'''        if en == 0 and not (sc.get(code) or {}).get("verses"):   # LIBRARY_SCHOLAR_2026_10_16: or in scholarly English
            continue  # only list readable texts
''')

edit(D, 4, r'''                f'<div class="meta"><span class="badge en">EN {en}/{total}</span>{hi_badge}{qa_badge}'
''', r'''                f'<div class="meta"><span class="badge en">EN {en}/{total}</span>{_scholar_badge(code, sc)}{hi_badge}{qa_badge}'
''')

edit(D, 5, r'''                f'{_redeem_note(code, rdm)}{acts_html}</div>'   # REDEEM_2026_10_14
''', r'''                f'{_scholar_line(code, sc)}{_redeem_note(code, rdm)}{acts_html}</div>'   # REDEEM_2026_10_14, LIBRARY_SCHOLAR_2026_10_16
''')

edit(D, 6, r'''{total_hi:,} Hindi verses{(''', r'''{total_hi:,} Hindi verses{_scholar_sum(sc)}{(''')

edit(D, 7, r'''{_REDEEM_CSS}
/* BOOKSMITH_WIRING_2026_09_12 */
''', r'''{_REDEEM_CSS}
{_SCHOLAR_CSS}
/* BOOKSMITH_WIRING_2026_09_12 */
''')

edit(D, 8, r'''            (*l10n_param, doc, *type_params, limit, offset)
        ).fetchall()
        con.close()
''', r'''            (*l10n_param, doc, *type_params, limit, offset)
        ).fetchall()
        sch, sch_n = (_scholar_rows(con, doc, type_clause, type_params, limit, offset) if lang == "en"
                      else ({}, 0))   # LIBRARY_SCHOLAR_2026_10_16: the scholarly English of these verses
        con.close()
''')

edit(D, 9, r'''            "passages": [row_to_dict(r) for r in rows]
        })
''', r'''            "scholar_count": sch_n,   # LIBRARY_SCHOLAR_2026_10_16
            "passages": [_with_scholar(row_to_dict(r), sch) for r in rows]
        })
''')

edit(D, 10, r'''    document.getElementById('progText').textContent = d.translated + '/' + d.total + ' translated (' + pct + '%)';
''', r'''    document.getElementById('progText').textContent = d.translated + '/' + d.total + ' translated (' + pct + '%)';
    if (d.scholar_count) document.getElementById('progText').textContent += ' ' + String.fromCharCode(183) + ' '
        + d.scholar_count + ' in scholarly English';   // LIBRARY_SCHOLAR_2026_10_16
''')

edit(D, 11, r'''        '<div class="col-en">' +
          '<div class="col-label col-label-en">' + (LANG_LABELS[activeLang] || activeLang) + '</div>' +
''', r'''        '<div class="col-en">' +
          scholarHtml(p) +
          '<div class="col-label col-label-en">' + (LANG_LABELS[activeLang] || activeLang) + (p.scholar ? ' &middot; the working English' : '') + '</div>' +
''')

edit(D, 12, r'''function looksEnglish(t){{
''', r'''// LIBRARY_SCHOLAR_2026_10_16: a verse's scholarly English (scholar_translate.py) above its working English, with its
// status and a link to its notes and checks on /scholar/<doc>. The working English below it is what the site shows.
function scholarHtml(p){{
  var s = p.scholar;
  if (!s || !s.translation) return '';
  var st = s.review === 'accept' ? 'accepted by a person' : (s.review === 'reject' ? 'rejected by a person'
           : String(s.status || '').replace('_', ' '));
  var cls = (s.review === 'accept' || (s.status === 'passed' && s.review !== 'reject')) ? 'ok'
            : ((s.status === 'source_doubt' || s.review === 'reject') ? 'lo' : 'mid');
  var eng = String(s.engine || '').split(':').pop();
  var txt = esc(s.translation).replace(/\\*([^*\\n]{{1,80}})\\*/g, '<em>$1</em>');
  return '<div class="col-label col-label-sch">&#128220; Scholarly English <span class="sch-st ' + cls + '">' + esc(st)
       + '</span>' + (s.sentence ? '<span class="sch-sent" title="one Sanskrit sentence over these verses">sentence '
       + esc(s.sentence) + '</span>' : '') + '</div><div class="sch-text">' + txt + '</div>'
       + '<div class="sch-by">' + esc(eng) + ' &middot; <a href="' + esc(s.href) + '" target="_blank">its notes and '
       + 'checks</a></div>';
}}

function looksEnglish(t){{
''')

edit(D, 13, r'''.en-pending{{color:var(--muted);font-style:italic;font-size:13px;font-family:'Inter',sans-serif}}
''', r'''.en-pending{{color:var(--muted);font-style:italic;font-size:13px;font-family:'Inter',sans-serif}}
/* LIBRARY_SCHOLAR_2026_10_16: the scholarly English above the working English */
.col-label-sch{{color:#c3a6e8}}
.sch-text{{font-size:15px;line-height:1.75;color:var(--cream);margin-bottom:6px}}
.sch-text em{{font-style:italic;color:#e8dcc8}}
.sch-by{{font-family:'Inter',sans-serif;font-size:10px;color:var(--muted);margin-bottom:12px;padding-bottom:10px;border-bottom:1px dashed var(--border)}}
.sch-by a{{color:#c3a6e8}}
.sch-st{{border-radius:4px;padding:0 6px;font-size:9px;text-transform:none;letter-spacing:0;border:1px solid var(--border)}}
.sch-st.ok{{color:var(--green);border-color:#2f6b45}}
.sch-st.mid{{color:#d9b36a;border-color:#6b5420}}
.sch-st.lo{{color:#e09a9a;border-color:#7a2f2f}}
.sch-sent{{font-size:9px;color:var(--muted);text-transform:none;letter-spacing:0}}
''')

edit(D, 14, r''': '<div class="en-pending">&#x231B; Not yet translated</div>'
''', r''': '<div class="en-pending">&#x231B; Not yet translated' + (p.scholar ? ' (the working English, which the site shows)' : '') + '</div>'
''')

for _f, _n, _o, _new in E:
    assert all(ord(ch) < 128 for ch in _new), "edit %d is not ASCII" % _n


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
    if not Path(D).exists():
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
        data = out.replace("\n", nl).encode("utf-8")
        if all(x < 128 for x in raw) and not all(x < 128 for x in data):
            problems.append("%s would not be ASCII" % rel); continue
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
    print("  python -m unittest tests.test_library_scholar_2026_10_16")
    print("  .\\scripts\\restart_dashboard.ps1 -Status   (then restart it when no job runs)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
