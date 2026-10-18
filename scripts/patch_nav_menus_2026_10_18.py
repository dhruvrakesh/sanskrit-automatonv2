#!/usr/bin/env python3
# -*- coding: ascii -*-
"""
patch_nav_menus_2026_10_18.py  (2026-10-18)  NAV_MENUS_2026_10_18

Asked on 18 Oct: "top nav bar needs to be more extensive and accommodate all features". The main page's top bar held
three links and seven buttons in a row; on a laptop screen the last ones (Ask the Corpus, Database) ran off the edge,
and the Scholarly English, Path, Redeem, BM2 and Methodology pages had no link at all.

scripts/dashboard_static.html (needs TRANSLATION_DESK_2026_10_17):
  - the top bar's links in six menus (Texts, Translate, Check, Make, Ask, Site): every link that was there, as it was,
    and Path, Scholarly English, Redeem, BM2, Methodology, Srangam's editions, its working corpus, the Researchers'
    Corner and the Hub; one menu open at a time, closed when the pointer leaves it; no script block added;
  - the engine selector is narrower (its longest option made the bar overflow); Refresh stays at the right.
tests/test_tier_r_2026_10_17.py (its replay chain: dashboard_static.html's later backup may be .bak_navmenus_)
and tests/test_stories_ui_2026_10_05.py (Stories is in the top bar, now in its Make menu, not before the Shelf).
Anchored, all-or-nothing, marker-idempotent; keeps line endings; backups .bak_navmenus_<date>. Nothing else changes.
  python scripts\\patch_nav_menus_2026_10_18.py --check
  python scripts\\patch_nav_menus_2026_10_18.py
Then refresh the dashboard's page (the dashboard needs no restart: it serves the file as it is).
"""
from __future__ import annotations
import argparse, datetime, os, py_compile, shutil, sys, tempfile
from pathlib import Path

MARK = 'NAV_MENUS_2026_10_18'
NEEDS = {'scripts/dashboard_static.html': 'TRANSLATION_DESK_2026_10_17', 'tests/test_tier_r_2026_10_17.py': 'TIER_R_2026_10_17', 'tests/test_stories_ui_2026_10_05.py': 'STORIES_UI_2026_10_05'}
FILES = list(NEEDS)
TAG = 'navmenus'

E = []
def edit(f, n, old, new):
    E.append((f, n, old, new))


edit('scripts/dashboard_static.html', 1, r'''.btn-refresh{padding:7px 14px;background:transparent;border:1px solid var(--border-v);border-radius:var(--r-sm);color:var(--muted);font-size:12px;cursor:pointer;transition:all .2s}
''', r'''.btn-refresh{padding:7px 14px;background:transparent;border:1px solid var(--border-v);border-radius:var(--r-sm);color:var(--muted);font-size:12px;cursor:pointer;transition:all .2s}
/* NAV_MENUS_2026_10_18: the top bar's menus */
.topnav{display:flex;align-items:center;gap:4px}
.tn{position:relative}
.tn>summary{list-style:none;cursor:pointer;padding:7px 11px;border:1px solid var(--border-v);border-radius:var(--r-sm);color:var(--gold);font-size:12.5px;white-space:nowrap;user-select:none}
.tn>summary::-webkit-details-marker{display:none}
.tn>summary::after{content:" \25BE";color:var(--muted)}
.tn[open]>summary{color:var(--cream);background:#ffffff10}
.tn-pop{position:absolute;top:calc(100% + 6px);left:0;z-index:1000;min-width:260px;background:var(--bg2);border:1px solid var(--border-v);border-radius:var(--r-sm);padding:6px;box-shadow:0 10px 30px #0009}
.tn-pop>a,.tn-pop>button{display:block!important;width:100%;box-sizing:border-box;text-align:left;margin:0 0 2px!important;padding:7px 10px!important;border:0!important;border-radius:var(--r-sm);background:transparent;color:var(--cream)!important;font-size:12.5px!important;text-decoration:none!important;cursor:pointer;white-space:normal}
.tn-pop>a:hover,.tn-pop>button:hover,.tn-pop>a:focus,.tn-pop>button:focus{background:#ffffff14;outline:none}
.tn-d{display:block;font-size:10.5px;color:var(--muted);margin-top:1px}
#engineSelect{max-width:230px}
''')

edit('scripts/dashboard_static.html', 2, r'''    <a href="/stories" title="Stories: cited retellings beside the images, for the anthology (STORIES_UI_2026_10_05)" style="color:var(--gold);text-decoration:none;font-size:13px;margin-right:12px">&#x1F4DC; Stories</a>
    <a href="/shelf" title="Shelf: every text by collection, with covers and editions (SHELF_2026_10_04)" style="color:var(--gold);text-decoration:none;font-size:13px;margin-right:12px">&#x1F4DA; Shelf</a>
    <a href="/images" title="Image library: ideas, generation, captions (IMAGES_UI_2026_10_03)" style="color:var(--gold);text-decoration:none;font-size:13px;margin-right:12px">&#x1F5BC; Images</a>
    <div style="display:flex;align-items:center;gap:8px">
      <span class="engine-label">Engine</span>
      <select id="engineSelect" class="engine-select">
        <option value="gemini:gemini-2.5-flash" selected>&#x26A1; Gemini 2.5 Flash (default)</option>
        <option value="gemini:gemini-2.5-pro">&#x2726; Gemini 2.5 Pro (high quality)</option>
        <option value="gemini:gemini-2.0-flash">&#x26A1; Gemini 2.0 Flash (fast)</option>
        <option value="openai:gpt-4o">&#x1F535; GPT-4o</option>
        <option value="openai:gpt-4o-mini">&#x1F535; GPT-4o-mini (cheap)</option>
        <option value="anthropic:claude-sonnet-5-5" title="TIER_R_2026_10_17: the working English by Claude Sonnet 5.5 in one pass (BM1, BM3, BM2); it bills the Claude credit; one text at a time">&#9670; Claude Sonnet 5.5, one pass (Tier R; the Claude credit)</option>
        <option value="echo">&#x1F501; Echo (test)</option>
      </select>
    </div>
    <div class="status-dot" title="Server running"></div>
    <a class="btn-refresh" href="/translate" target="_blank" style="text-decoration:none;margin-right:6px" title="Translate any Sanskrit into English + Hindi on demand">&#9889; Translate</a>
    <a class="btn-refresh" href="/library" target="_blank" style="text-decoration:none;margin-right:6px" title="Browse & read translated texts">&#128218; Library</a>
    <a class="btn-refresh" href="/sources" target="_blank" style="text-decoration:none;margin-right:6px" title="JUDGE_DESK_2026_10_11: the texts whose scan stops their translation, the debris judged, the editions found">&#128269; Sources</a>
    <a class="btn-refresh" href="/benchmarks" target="_blank" style="text-decoration:none;margin-right:6px" title="BENCH_DESK_2026_10_16: BM1 (our English against published translations), and the readings of each text compared">&#128207; Benchmarks</a>
    <a class="btn-refresh" href="/desk" target="_blank" style="text-decoration:none;margin-right:6px" title="TRANSLATION_DESK_2026_10_17: every text by its stage (the scholarly edition, ready to translate, translated, the reading first), and the scholarly English begun from its page">&#128221; Desk</a>
    <a class="btn-refresh" href="/ask" target="_blank" style="text-decoration:none;margin-right:6px" title="Ask questions answered from the corpus, with cited verses">&#128172; Ask the Corpus</a>
    <button class="btn-refresh" onclick="openDatabase(this)" style="margin-right:6px" title="Open the corpus in Datasette for SQL querying (snapshots first, then launches)">&#128190; Database</button>
''', r'''    <nav class="topnav" aria-label="The Automaton's pages"><!-- NAV_MENUS_2026_10_18: every page in six menus -->
    <details class="tn" ontoggle="if(this.open)document.querySelectorAll('details.tn[open]').forEach(function(d){if(d!==this)d.open=false},this)" onmouseleave="this.open=false"><summary>&#128218; Texts</summary><div class="tn-pop">
      <a href="/shelf" title="Shelf: every text by collection, with covers and editions (SHELF_2026_10_04)" style="color:var(--gold);text-decoration:none;font-size:13px;margin-right:12px">&#x1F4DA; Shelf</a>
      <a class="btn-refresh" href="/library" target="_blank" style="text-decoration:none;margin-right:6px" title="Browse & read translated texts">&#128218; Library</a>
      <a class="btn-refresh" href="/desk" target="_blank" style="text-decoration:none;margin-right:6px" title="TRANSLATION_DESK_2026_10_17: every text by its stage (the scholarly edition, ready to translate, translated, the reading first), and the scholarly English begun from its page">&#128221; Desk</a>
      <a href="/path" target="_blank" title="NAV_MENUS_2026_10_18">&#129517; Path<span class="tn-d">each text's next step, and why</span></a>
      <a class="btn-refresh" href="/sources" target="_blank" style="text-decoration:none;margin-right:6px" title="JUDGE_DESK_2026_10_11: the texts whose scan stops their translation, the debris judged, the editions found">&#128269; Sources</a>
    </div></details>
    <details class="tn" ontoggle="if(this.open)document.querySelectorAll('details.tn[open]').forEach(function(d){if(d!==this)d.open=false},this)" onmouseleave="this.open=false"><summary>&#9889; Translate</summary><div class="tn-pop">
      <a class="btn-refresh" href="/translate" target="_blank" style="text-decoration:none;margin-right:6px" title="Translate any Sanskrit into English + Hindi on demand">&#9889; Translate</a>
      <a href="/scholar" target="_blank" title="NAV_MENUS_2026_10_18">&#128220; Scholarly English<span class="tn-d">every text with it, verse by verse and as prose</span></a>
      <a href="/redeem" target="_blank" title="NAV_MENUS_2026_10_18">&#129529; Redeem<span class="tn-d">the English to mend, by its cause</span></a>
    </div></details>
    <details class="tn" ontoggle="if(this.open)document.querySelectorAll('details.tn[open]').forEach(function(d){if(d!==this)d.open=false},this)" onmouseleave="this.open=false"><summary>&#128207; Check</summary><div class="tn-pop">
      <a class="btn-refresh" href="/benchmarks" target="_blank" style="text-decoration:none;margin-right:6px" title="BENCH_DESK_2026_10_16: BM1 (our English against published translations), and the readings of each text compared">&#128207; Benchmarks</a>
      <a href="/benchmarks/bm2" target="_blank" title="NAV_MENUS_2026_10_18">&#128065; BM2<span class="tn-d">your blind reading</span></a>
      <a href="/methodology" target="_blank" title="NAV_MENUS_2026_10_18">&#128209; Methodology<span class="tn-d">how the English is made and judged</span></a>
    </div></details>
    <details class="tn" ontoggle="if(this.open)document.querySelectorAll('details.tn[open]').forEach(function(d){if(d!==this)d.open=false},this)" onmouseleave="this.open=false"><summary>&#127912; Make</summary><div class="tn-pop">
      <a href="/stories" title="Stories: cited retellings beside the images, for the anthology (STORIES_UI_2026_10_05)" style="color:var(--gold);text-decoration:none;font-size:13px;margin-right:12px">&#x1F4DC; Stories</a>
      <a href="/images" title="Image library: ideas, generation, captions (IMAGES_UI_2026_10_03)" style="color:var(--gold);text-decoration:none;font-size:13px;margin-right:12px">&#x1F5BC; Images</a>
    </div></details>
    <details class="tn" ontoggle="if(this.open)document.querySelectorAll('details.tn[open]').forEach(function(d){if(d!==this)d.open=false},this)" onmouseleave="this.open=false"><summary>&#128172; Ask</summary><div class="tn-pop">
      <a class="btn-refresh" href="/ask" target="_blank" style="text-decoration:none;margin-right:6px" title="Ask questions answered from the corpus, with cited verses">&#128172; Ask the Corpus</a>
      <button class="btn-refresh" onclick="openDatabase(this)" style="margin-right:6px" title="Open the corpus in Datasette for SQL querying (snapshots first, then launches)">&#128190; Database</button>
    </div></details>
    <details class="tn" ontoggle="if(this.open)document.querySelectorAll('details.tn[open]').forEach(function(d){if(d!==this)d.open=false},this)" onmouseleave="this.open=false"><summary>&#127760; Site</summary><div class="tn-pop">
      <a href="https://srangam.nartiang.org/editions" target="_blank" rel="noopener" title="NAV_MENUS_2026_10_18">&#128214; Srangam: the scholarly editions<span class="tn-d">open to everyone</span></a>
      <a href="https://srangam.nartiang.org/corpus" target="_blank" rel="noopener" title="NAV_MENUS_2026_10_18">&#128218; Srangam: the working corpus<span class="tn-d">for signed-in readers</span></a>
      <a href="https://srangam.nartiang.org/corpus/corner" target="_blank" rel="noopener" title="NAV_MENUS_2026_10_18">&#128172; The Researchers' Corner<span class="tn-d">requests from researchers</span></a>
      <a href="http://127.0.0.1:5050/" target="_blank" title="NAV_MENUS_2026_10_18">&#129517; The Hub<span class="tn-d">the runs, the holds and the OCR (127.0.0.1:5050)</span></a>
    </div></details>
    </nav>
    <div style="display:flex;align-items:center;gap:8px">
      <span class="engine-label">Engine</span>
      <select id="engineSelect" class="engine-select">
        <option value="gemini:gemini-2.5-flash" selected>&#x26A1; Gemini 2.5 Flash (default)</option>
        <option value="gemini:gemini-2.5-pro">&#x2726; Gemini 2.5 Pro (high quality)</option>
        <option value="gemini:gemini-2.0-flash">&#x26A1; Gemini 2.0 Flash (fast)</option>
        <option value="openai:gpt-4o">&#x1F535; GPT-4o</option>
        <option value="openai:gpt-4o-mini">&#x1F535; GPT-4o-mini (cheap)</option>
        <option value="anthropic:claude-sonnet-5-5" title="TIER_R_2026_10_17: the working English by Claude Sonnet 5.5 in one pass (BM1, BM3, BM2); it bills the Claude credit; one text at a time">&#9670; Claude Sonnet 5.5, one pass (Tier R; the Claude credit)</option>
        <option value="echo">&#x1F501; Echo (test)</option>
      </select>
    </div>
    <div class="status-dot" title="Server running"></div>
''')

edit('tests/test_tier_r_2026_10_17.py', 1, r'''            for f in self.FILES:
                self.assertEqual((t / f).read_bytes(), (REPO / f).read_bytes(), f)
''', r'''            for f in self.FILES:
                later = sorted((REPO / f).parent.glob(Path(f).name + ".bak_navmenus_*"))   # NAV_MENUS_2026_10_18 came after
                self.assertEqual((t / f).read_bytes(), (later[0] if later else REPO / f).read_bytes(), f)
''')

edit('tests/test_stories_ui_2026_10_05.py', 1, r'''        self.assertLess(h.index('href="/stories"'), h.index('href="/shelf"'))
''', r'''        bar = h[h.index('<header class="top-bar">'):h.index("</header>")]   # NAV_MENUS_2026_10_18: in its Make menu
        self.assertIn('href="/stories"', bar)
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
    print('  python -m unittest tests.test_nav_menus_2026_10_18 tests.test_stories_ui_2026_10_05 tests.test_images_web tests.test_tier_r_2026_10_17 tests.test_judge_desk_2026_10_11 tests.test_translation_desk_2026_10_17 tests.test_buttons_2026_10_17')
    return 0


if __name__ == "__main__":
    sys.exit(main())
