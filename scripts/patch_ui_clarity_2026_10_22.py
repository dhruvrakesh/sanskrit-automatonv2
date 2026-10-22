#!/usr/bin/env python3
# -*- coding: ascii -*-
"""
patch_ui_clarity_2026_10_22.py  (2026-10-22)  UI_CLARITY_2026_10_22

Asked on 22 Oct: "tool bar keeps hiding before user can select!" and "how can scholarly english exist for 1400 verses of
hayasirsa yet english shows only 1?".

scripts/dashboard_static.html (needs NAV_MENUS_2026_10_18): the top bar's menus closed the moment the pointer left the
menu's button, and a 6px gap lies between the button and its list: crossing it closed the menu. Now an invisible bridge
covers the gap, and a menu closes 450 ms after the pointer leaves it (coming back keeps it open). No script block added.

scripts/dashboard.py (needs LIBRARY_SCHOLAR_2026_10_16):
  - the Library card's EN says it is the working English (what the reader shows first, and what the names, the search
    by meaning and the Hindi are made from), SC the scholarly English, a separate translation;
  - SC's tooltips no longer say the scholarly English is "not on the site yet": the mirror sends it with the text
    (SCHOLAR_MIRROR_2026_10_18), not while the text is held in repair or withdrawn;
  - a text in repair says why its English was cleared (the repair replaced its Sanskrit; the backup keeps the old
    English and Hindi), what EN and SC count, and how it is published (Finish EN, then Add Hindi; or --release --force);
  - the Source desk says that "% Devanagari" is an OCR text's script, not its fidelity (archive.org's text of our
    Satapatha scan: 100% Devanagari, 25 misread aksharas in 100), and the Fetch button's tooltip says so.
tests/test_nav_menus_2026_10_18.py: the delayed close counted; its replay ends at the copy this patch backed up.
tests/test_tier_r_2026_10_17.py: its replay of dashboard.py ends at the copy this patch backed up.
Anchored, all-or-nothing, marker-idempotent; keeps line endings; backups .bak_uiclarity_<date>. Restart the dashboard
when it is idle for dashboard.py (the static page needs only a refresh).
  python scripts\\patch_ui_clarity_2026_10_22.py --check
  python scripts\\patch_ui_clarity_2026_10_22.py
"""
from __future__ import annotations
import argparse, datetime, os, py_compile, shutil, sys, tempfile
from pathlib import Path

MARK = 'UI_CLARITY_2026_10_22'
TAG = 'uiclarity'
FILES = ['scripts/dashboard_static.html', 'scripts/dashboard.py', 'tests/test_nav_menus_2026_10_18.py', 'tests/test_tier_r_2026_10_17.py']
NEEDS = {'scripts/dashboard_static.html': 'NAV_MENUS_2026_10_18', 'scripts/dashboard.py': 'LIBRARY_SCHOLAR_2026_10_16', 'tests/test_nav_menus_2026_10_18.py': 'NAV_MENUS_2026_10_18', 'tests/test_tier_r_2026_10_17.py': 'TIER_R_2026_10_17'}
REQUIRES = {}   # another file that must carry a marker first
E = []


def edit(f, n, old, new):
    E.append((f, n, old, new))


edit('scripts/dashboard_static.html', 1, '.tn[open]>summary{color:var(--cream);background:#ffffff10}\n.tn-pop{position:absolute;top:calc(100% + 6px);left:0;z-index:1000;min-width:260px;background:var(--bg2);border:1px solid var(--border-v);border-radius:var(--r-sm);padding:6px;box-shadow:0 10px 30px #0009}\n.tn-pop>a,.tn-pop>button{display:block!important;width:100%;box-sizing:border-box;text-align:left;margin:0 0 2px!important;padding:7px 10px!important;border:0!important;border-radius:var(--r-sm);background:transparent;color:var(--cream)!important;font-size:12.5px!important;text-decoration:none!important;cursor:pointer;white-space:normal}\n.tn-pop>a:hover,.tn-pop>button:hover,.tn-pop>a:focus,.tn-pop>button:focus{background:#ffffff14;outline:none}',
     '.tn[open]>summary{color:var(--cream);background:#ffffff10}\n.tn-pop{position:absolute;top:calc(100% + 6px);left:0;z-index:1000;min-width:260px;background:var(--bg2);border:1px solid var(--border-v);border-radius:var(--r-sm);padding:6px;box-shadow:0 10px 30px #0009}\n/* UI_CLARITY_2026_10_22: a bridge over the 6px gap, so that the menu stays open on the way to it */\n.tn-pop::before{content:"";position:absolute;left:-8px;right:-8px;top:-12px;height:12px}\n.tn-pop>a,.tn-pop>button{display:block!important;width:100%;box-sizing:border-box;text-align:left;margin:0 0 2px!important;padding:7px 10px!important;border:0!important;border-radius:var(--r-sm);background:transparent;color:var(--cream)!important;font-size:12.5px!important;text-decoration:none!important;cursor:pointer;white-space:normal}\n.tn-pop>a:hover,.tn-pop>button:hover,.tn-pop>a:focus,.tn-pop>button:focus{background:#ffffff14;outline:none}')

edit('scripts/dashboard_static.html', 2, '    <div class="top-bar-spacer"></div>\n    <nav class="topnav" aria-label="The Automaton\'s pages"><!-- NAV_MENUS_2026_10_18: every page in six menus -->\n    <details class="tn" ontoggle="if(this.open)document.querySelectorAll(\'details.tn[open]\').forEach(function(d){if(d!==this)d.open=false},this)" onmouseleave="this.open=false"><summary>&#128218; Texts</summary><div class="tn-pop">\n      <a href="/shelf" title="Shelf: every text by collection, with covers and editions (SHELF_2026_10_04)" style="color:var(--gold);text-decoration:none;font-size:13px;margin-right:12px">&#x1F4DA; Shelf</a>\n      <a class="btn-refresh" href="/library" target="_blank" style="text-decoration:none;margin-right:6px" title="Browse & read translated texts">&#128218; Library</a>',
     '    <div class="top-bar-spacer"></div>\n    <nav class="topnav" aria-label="The Automaton\'s pages"><!-- NAV_MENUS_2026_10_18: every page in six menus -->\n    <details class="tn" ontoggle="if(this.open)document.querySelectorAll(\'details.tn[open]\').forEach(function(d){if(d!==this)d.open=false},this)" onmouseenter="clearTimeout(this._tnT)" onmouseleave="var d=this;clearTimeout(d._tnT);d._tnT=setTimeout(function(){d.open=false},450)"><summary>&#128218; Texts</summary><div class="tn-pop">\n      <a href="/shelf" title="Shelf: every text by collection, with covers and editions (SHELF_2026_10_04)" style="color:var(--gold);text-decoration:none;font-size:13px;margin-right:12px">&#x1F4DA; Shelf</a>\n      <a class="btn-refresh" href="/library" target="_blank" style="text-decoration:none;margin-right:6px" title="Browse & read translated texts">&#128218; Library</a>')

edit('scripts/dashboard_static.html', 3, '      <a class="btn-refresh" href="/sources" target="_blank" style="text-decoration:none;margin-right:6px" title="JUDGE_DESK_2026_10_11: the texts whose scan stops their translation, the debris judged, the editions found">&#128269; Sources</a>\n    </div></details>\n    <details class="tn" ontoggle="if(this.open)document.querySelectorAll(\'details.tn[open]\').forEach(function(d){if(d!==this)d.open=false},this)" onmouseleave="this.open=false"><summary>&#9889; Translate</summary><div class="tn-pop">\n      <a class="btn-refresh" href="/translate" target="_blank" style="text-decoration:none;margin-right:6px" title="Translate any Sanskrit into English + Hindi on demand">&#9889; Translate</a>\n      <a href="/scholar" target="_blank" title="NAV_MENUS_2026_10_18">&#128220; Scholarly English<span class="tn-d">every text with it, verse by verse and as prose</span></a>\n      <a href="/redeem" target="_blank" title="NAV_MENUS_2026_10_18">&#129529; Redeem<span class="tn-d">the English to mend, by its cause</span></a>\n    </div></details>\n    <details class="tn" ontoggle="if(this.open)document.querySelectorAll(\'details.tn[open]\').forEach(function(d){if(d!==this)d.open=false},this)" onmouseleave="this.open=false"><summary>&#128207; Check</summary><div class="tn-pop">\n      <a class="btn-refresh" href="/benchmarks" target="_blank" style="text-decoration:none;margin-right:6px" title="BENCH_DESK_2026_10_16: BM1 (our English against published translations), and the readings of each text compared">&#128207; Benchmarks</a>\n      <a href="/benchmarks/bm2" target="_blank" title="NAV_MENUS_2026_10_18">&#128065; BM2<span class="tn-d">your blind reading</span></a>\n      <a href="/methodology" target="_blank" title="NAV_MENUS_2026_10_18">&#128209; Methodology<span class="tn-d">how the English is made and judged</span></a>\n    </div></details>\n    <details class="tn" ontoggle="if(this.open)document.querySelectorAll(\'details.tn[open]\').forEach(function(d){if(d!==this)d.open=false},this)" onmouseleave="this.open=false"><summary>&#127912; Make</summary><div class="tn-pop">\n      <a href="/stories" title="Stories: cited retellings beside the images, for the anthology (STORIES_UI_2026_10_05)" style="color:var(--gold);text-decoration:none;font-size:13px;margin-right:12px">&#x1F4DC; Stories</a>\n      <a href="/images" title="Image library: ideas, generation, captions (IMAGES_UI_2026_10_03)" style="color:var(--gold);text-decoration:none;font-size:13px;margin-right:12px">&#x1F5BC; Images</a>\n    </div></details>\n    <details class="tn" ontoggle="if(this.open)document.querySelectorAll(\'details.tn[open]\').forEach(function(d){if(d!==this)d.open=false},this)" onmouseleave="this.open=false"><summary>&#128172; Ask</summary><div class="tn-pop">\n      <a class="btn-refresh" href="/ask" target="_blank" style="text-decoration:none;margin-right:6px" title="Ask questions answered from the corpus, with cited verses">&#128172; Ask the Corpus</a>\n      <button class="btn-refresh" onclick="openDatabase(this)" style="margin-right:6px" title="Open the corpus in Datasette for SQL querying (snapshots first, then launches)">&#128190; Database</button>\n    </div></details>\n    <details class="tn" ontoggle="if(this.open)document.querySelectorAll(\'details.tn[open]\').forEach(function(d){if(d!==this)d.open=false},this)" onmouseleave="this.open=false"><summary>&#127760; Site</summary><div class="tn-pop">\n      <a href="https://srangam.nartiang.org/editions" target="_blank" rel="noopener" title="NAV_MENUS_2026_10_18">&#128214; Srangam: the scholarly editions<span class="tn-d">open to everyone</span></a>\n      <a href="https://srangam.nartiang.org/corpus" target="_blank" rel="noopener" title="NAV_MENUS_2026_10_18">&#128218; Srangam: the working corpus<span class="tn-d">for signed-in readers</span></a>',
     '      <a class="btn-refresh" href="/sources" target="_blank" style="text-decoration:none;margin-right:6px" title="JUDGE_DESK_2026_10_11: the texts whose scan stops their translation, the debris judged, the editions found">&#128269; Sources</a>\n    </div></details>\n    <details class="tn" ontoggle="if(this.open)document.querySelectorAll(\'details.tn[open]\').forEach(function(d){if(d!==this)d.open=false},this)" onmouseenter="clearTimeout(this._tnT)" onmouseleave="var d=this;clearTimeout(d._tnT);d._tnT=setTimeout(function(){d.open=false},450)"><summary>&#9889; Translate</summary><div class="tn-pop">\n      <a class="btn-refresh" href="/translate" target="_blank" style="text-decoration:none;margin-right:6px" title="Translate any Sanskrit into English + Hindi on demand">&#9889; Translate</a>\n      <a href="/scholar" target="_blank" title="NAV_MENUS_2026_10_18">&#128220; Scholarly English<span class="tn-d">every text with it, verse by verse and as prose</span></a>\n      <a href="/redeem" target="_blank" title="NAV_MENUS_2026_10_18">&#129529; Redeem<span class="tn-d">the English to mend, by its cause</span></a>\n    </div></details>\n    <details class="tn" ontoggle="if(this.open)document.querySelectorAll(\'details.tn[open]\').forEach(function(d){if(d!==this)d.open=false},this)" onmouseenter="clearTimeout(this._tnT)" onmouseleave="var d=this;clearTimeout(d._tnT);d._tnT=setTimeout(function(){d.open=false},450)"><summary>&#128207; Check</summary><div class="tn-pop">\n      <a class="btn-refresh" href="/benchmarks" target="_blank" style="text-decoration:none;margin-right:6px" title="BENCH_DESK_2026_10_16: BM1 (our English against published translations), and the readings of each text compared">&#128207; Benchmarks</a>\n      <a href="/benchmarks/bm2" target="_blank" title="NAV_MENUS_2026_10_18">&#128065; BM2<span class="tn-d">your blind reading</span></a>\n      <a href="/methodology" target="_blank" title="NAV_MENUS_2026_10_18">&#128209; Methodology<span class="tn-d">how the English is made and judged</span></a>\n    </div></details>\n    <details class="tn" ontoggle="if(this.open)document.querySelectorAll(\'details.tn[open]\').forEach(function(d){if(d!==this)d.open=false},this)" onmouseenter="clearTimeout(this._tnT)" onmouseleave="var d=this;clearTimeout(d._tnT);d._tnT=setTimeout(function(){d.open=false},450)"><summary>&#127912; Make</summary><div class="tn-pop">\n      <a href="/stories" title="Stories: cited retellings beside the images, for the anthology (STORIES_UI_2026_10_05)" style="color:var(--gold);text-decoration:none;font-size:13px;margin-right:12px">&#x1F4DC; Stories</a>\n      <a href="/images" title="Image library: ideas, generation, captions (IMAGES_UI_2026_10_03)" style="color:var(--gold);text-decoration:none;font-size:13px;margin-right:12px">&#x1F5BC; Images</a>\n    </div></details>\n    <details class="tn" ontoggle="if(this.open)document.querySelectorAll(\'details.tn[open]\').forEach(function(d){if(d!==this)d.open=false},this)" onmouseenter="clearTimeout(this._tnT)" onmouseleave="var d=this;clearTimeout(d._tnT);d._tnT=setTimeout(function(){d.open=false},450)"><summary>&#128172; Ask</summary><div class="tn-pop">\n      <a class="btn-refresh" href="/ask" target="_blank" style="text-decoration:none;margin-right:6px" title="Ask questions answered from the corpus, with cited verses">&#128172; Ask the Corpus</a>\n      <button class="btn-refresh" onclick="openDatabase(this)" style="margin-right:6px" title="Open the corpus in Datasette for SQL querying (snapshots first, then launches)">&#128190; Database</button>\n    </div></details>\n    <details class="tn" ontoggle="if(this.open)document.querySelectorAll(\'details.tn[open]\').forEach(function(d){if(d!==this)d.open=false},this)" onmouseenter="clearTimeout(this._tnT)" onmouseleave="var d=this;clearTimeout(d._tnT);d._tnT=setTimeout(function(){d.open=false},450)"><summary>&#127760; Site</summary><div class="tn-pop">\n      <a href="https://srangam.nartiang.org/editions" target="_blank" rel="noopener" title="NAV_MENUS_2026_10_18">&#128214; Srangam: the scholarly editions<span class="tn-d">open to everyone</span></a>\n      <a href="https://srangam.nartiang.org/corpus" target="_blank" rel="noopener" title="NAV_MENUS_2026_10_18">&#128218; Srangam: the working corpus<span class="tn-d">for signed-in readers</span></a>')

edit('scripts/dashboard.py', 1, '          + \'&#39;,this.dataset.i,&#39;pdf&#39;,this)">Fetch the PDF\' + (c.pdf_mb ? \' (\' + c.pdf_mb + \' MB)\' : \'\') + \'</button>\' : \'\')\n       + (c.txt_url && c.purity != null && c.purity >= 0.85 && !c.current_scan ? \'<button class="tr-rest rp" data-i="\' + i\n          + \'" onclick="_rpFetch(&#39;\' + doc + \'&#39;,this.dataset.i,&#39;text&#39;,this)">Fetch the OCR text (\'\n          + Math.round(100 * c.purity) + \'% Devanagari)</button>\' : \'\')\n       + \'</div></div>\';',
     '          + \'&#39;,this.dataset.i,&#39;pdf&#39;,this)">Fetch the PDF\' + (c.pdf_mb ? \' (\' + c.pdf_mb + \' MB)\' : \'\') + \'</button>\' : \'\')\n       + (c.txt_url && c.purity != null && c.purity >= 0.85 && !c.current_scan ? \'<button class="tr-rest rp" data-i="\' + i\n          + \'" title="The share of its letters that are Devanagari: its script, not its fidelity (UI_CLARITY_2026_10_22)"\'\n          + \' onclick="_rpFetch(&#39;\' + doc + \'&#39;,this.dataset.i,&#39;text&#39;,this)">Fetch the OCR text (\'\n          + Math.round(100 * c.purity) + \'% Devanagari)</button>\' : \'\')\n       + \'</div></div>\';')

edit('scripts/dashboard.py', 2, '    + \'. Try the e-text sites above.</p>\';\n  h += \'<p class="srcnone">Searched \' + _rpEsc(d.at || \'\') + \' as: \' + _rpEsc((d.words || []).join(\' \')) + \'</p>\';\n  h += _rpWitness(doc, d) + _rpBench(doc, d);   // BENCHMARK_2026_10_11\n  list.innerHTML = h; list._data = d;',
     '    + \'. Try the e-text sites above.</p>\';\n  h += \'<p class="srcnone">Searched \' + _rpEsc(d.at || \'\') + \' as: \' + _rpEsc((d.words || []).join(\' \')) + \'</p>\';\n  // UI_CLARITY_2026_10_22: a share of Devanagari is the script of an OCR text, not its fidelity\n  h += \'<p class="srcnone">"% Devanagari" is the script of an OCR text, not its fidelity: archive.org&#39;s text of our \'\n     + \'Satapatha scan is 100% Devanagari and misreads 25 aksharas in 100 (ours 3.3; FIDELITY_2026_10_22). Fetch a text, \'\n     + \'then Benchmark the readings (free) to read it against ours, akshara by akshara.</p>\';\n  h += _rpWitness(doc, d) + _rpBench(doc, d);   // BENCHMARK_2026_10_11\n  list.innerHTML = h; list._data = d;')

edit('scripts/dashboard.py', 3, '    elif st == "in_repair":\n        acts_html += (\'<div class="cardnote state">In repair since %s (%s): the site keeps its last version (%s English, \'\n                      \'%s Hindi) until you publish this one.</div>\'\n                      % (at, why, rec.get("en_before", "?"), rec.get("hi_before", "?")))\n    elif st == "withdrawn":   # PATH_2026_10_12',
     '    elif st == "in_repair":\n        acts_html += (\'<div class="cardnote state">In repair since %s (%s): the site keeps its last version (%s English, \'\n                      \'%s Hindi) until you publish this one. The repair replaced its Sanskrit, so the English and the \'\n                      \'Hindi made from the old reading were cleared (the backup taken before the repair keeps them): \'\n                      \'EN counts the working English made since, SC the scholarly English. Publishing waits for the \'\n                      \'working English and the Hindi (Finish EN, then Add Hindi), or publishes it now with what it \'\n                      \'has (repair_text.py --release --force).</div>\'   # UI_CLARITY_2026_10_22\n                      % (at, why, rec.get("en_before", "?"), rec.get("hi_before", "?")))\n    elif st == "withdrawn":   # PATH_2026_10_12')

edit('scripts/dashboard.py', 4, '        return ""\n    return (\'<span class="badge sc" title="Verses in scholarly English (scholar_translate.py), beside the working \'\n            \'English (EN)">SC {:,}</span>\'.format(c["verses"]))\n\n',
     '        return ""\n    return (\'<span class="badge sc" title="Verses in scholarly English (scholar_translate.py), beside the working \'\n            \'English (EN). The mirror sends them to the site with the text, not while the text is held in repair or \'\n            \'withdrawn (UI_CLARITY_2026_10_22).">SC {:,}</span>\'.format(c["verses"]))\n\n')

edit('scripts/dashboard.py', 5, '    q = quote(code, safe="")\n    tip = ("The scholarly English, verse by verse (scholar_translate.py): drafted with its context and glossary, read by "\n           "a critic, revised, judged. It is kept beside the working English (EN, which the site shows) and is not on "\n           "the site yet. $%.2f spent on all its rows; the last on %s." % (c["spent"], c["last"][:16].replace("T", " ")))\n    return (\'<div class="schl" title="%s">Scholarly English: <b>%s</b> verses by %s; %s. <a href="/scholar/%s">Verse by \'\n            \'verse</a> &middot; <a href="/scholar/%s/prose">as prose</a></div>\'',
     '    q = quote(code, safe="")\n    tip = ("The scholarly English, verse by verse (scholar_translate.py): drafted with its context and glossary, read by "\n           "a critic, revised, judged. It is kept beside the working English (EN) and goes to the site with the text "\n           "(SCHOLAR_MIRROR_2026_10_18), not while the text is held in repair or withdrawn (UI_CLARITY_2026_10_22). "\n           "$%.2f spent on all its rows; the last on %s." % (c["spent"], c["last"][:16].replace("T", " ")))\n    return (\'<div class="schl" title="%s">Scholarly English: <b>%s</b> verses by %s; %s. <a href="/scholar/%s">Verse by \'\n            \'verse</a> &middot; <a href="/scholar/%s/prose">as prose</a></div>\'')

edit('scripts/dashboard.py', 6, '                f\'<div class="code">{_html.escape(code)}</div>\'\n                f\'<div class="bar"><i style="width:{pct}%"></i></div>\'\n                f\'<div class="meta"><span class="badge en">EN {en}/{total}</span>{_scholar_badge(code, sc)}{hi_badge}{qa_badge}\'\n                f\'<span class="pct">{pct}%</span></div></a>\'\n                f\'{_scholar_line(code, sc)}{_redeem_note(code, rdm)}{acts_html}</div>\'   # REDEEM_2026_10_14, LIBRARY_SCHOLAR_2026_10_16',
     '                f\'<div class="code">{_html.escape(code)}</div>\'\n                f\'<div class="bar"><i style="width:{pct}%"></i></div>\'\n                f\'<div class="meta"><span class="badge en" title="The working English (Gemini): what the reader shows first, and \'\n                f\'what the names, the search by meaning and the Hindi are made from. SC beside it is the scholarly \'\n                f\'English, a separate translation (UI_CLARITY_2026_10_22).">EN {en}/{total}</span>\'\n                f\'{_scholar_badge(code, sc)}{hi_badge}{qa_badge}\'\n                f\'<span class="pct">{pct}%</span></div></a>\'\n                f\'{_scholar_line(code, sc)}{_redeem_note(code, rdm)}{acts_html}</div>\'   # REDEEM_2026_10_14, LIBRARY_SCHOLAR_2026_10_16')

edit('tests/test_nav_menus_2026_10_18.py', 1, '    def test_one_menu_at_a_time_without_a_script_block(self):\n        self.assertEqual(self.bar.count("ontoggle="), 6)\n        self.assertEqual(self.bar.count(\'onmouseleave="this.open=false"\'), 6)\n        self.assertNotIn("<script", self.bar)\n        self.assertEqual(self.h.count("<script"), 1, "the page\'s one script block, as before")',
     '    def test_one_menu_at_a_time_without_a_script_block(self):\n        self.assertEqual(self.bar.count("ontoggle="), 6)\n        self.assertEqual(self.bar.count(\'onmouseleave="\'), 6)   # UI_CLARITY_2026_10_22: closed a moment after it is left\n        self.assertNotIn("<script", self.bar)\n        self.assertEqual(self.h.count("<script"), 1, "the page\'s one script block, as before")')

edit('tests/test_nav_menus_2026_10_18.py', 2, '            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)\n            for f in self.FILES:\n                self.assertEqual((t / f).read_bytes(), (REPO / f).read_bytes(), f)\n            self.assertIn("Nothing to do", subprocess.run(pat, cwd=td, capture_output=True, text=True).stdout)\n            for f in self.FILES:',
     '            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)\n            for f in self.FILES:\n                later = sorted((REPO / f).parent.glob(Path(f).name + ".bak_uiclarity_*"))   # UI_CLARITY_2026_10_22 came after\n                self.assertEqual((t / f).read_bytes(), (later[0] if later else REPO / f).read_bytes(), f)\n            self.assertIn("Nothing to do", subprocess.run(pat, cwd=td, capture_output=True, text=True).stdout)\n            for f in self.FILES:')

edit('tests/test_tier_r_2026_10_17.py', 1, '            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)\n            for f in self.FILES:\n                later = sorted((REPO / f).parent.glob(Path(f).name + ".bak_navmenus_*"))   # NAV_MENUS_2026_10_18 came after\n                self.assertEqual((t / f).read_bytes(), (later[0] if later else REPO / f).read_bytes(), f)\n            self.assertIn("Nothing to do", subprocess.run(pat, cwd=td, capture_output=True, text=True).stdout)',
     '            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)\n            for f in self.FILES:\n                later = (sorted((REPO / f).parent.glob(Path(f).name + ".bak_navmenus_*"))   # NAV_MENUS_2026_10_18 came after\n                         or sorted((REPO / f).parent.glob(Path(f).name + ".bak_uiclarity_*")))   # UI_CLARITY_2026_10_22\n                self.assertEqual((t / f).read_bytes(), (later[0] if later else REPO / f).read_bytes(), f)\n            self.assertIn("Nothing to do", subprocess.run(pat, cwd=td, capture_output=True, text=True).stdout)')


def nl_of(raw: bytes) -> str:
    return "\r\n" if raw.count(b"\r\n") > raw.count(b"\n") // 2 else "\n"


def main() -> int:
    ap = argparse.ArgumentParser(); ap.add_argument("--check", action="store_true"); args = ap.parse_args()
    stamp = datetime.date.today().strftime("%Y%m%d")
    for f, m in REQUIRES.items():
        if not Path(f).exists() or m.encode() not in Path(f).read_bytes():
            print("REFUSE: %s does not carry %s (apply it first). Nothing written." % (f, m)); return 1
    plan = {}
    for f in FILES:
        p = Path(f)
        if not p.exists():
            print("FAIL: %s not found. Run from the repo root." % f); return 2
        raw = p.read_bytes()
        if MARK.encode() in raw:
            print("skip %s (already carries %s)" % (f, MARK)); continue
        nl = nl_of(raw)
        src = raw.decode("utf-8").replace("\r\n", "\n")
        if NEEDS.get(f) and NEEDS[f] not in src:
            print("REFUSE: %s has no %s (apply it first). Nothing written." % (f, NEEDS[f])); return 1
        for ff, n, old, new in E:
            if ff != f:
                continue
            if src.count(old) != 1:
                print("REFUSE: %s: anchor %d found %d times (want 1). Nothing written." % (f, n, src.count(old))); return 1
            src = src.replace(old, new, 1)
        if MARK not in src:
            print("FAIL: %s: the edits did not bring %s. Nothing written." % (f, MARK)); return 2
        plan[f] = src.replace("\n", nl).encode("utf-8")
    with tempfile.TemporaryDirectory() as td:
        for f, data in plan.items():
            if f.endswith(".py"):
                t = Path(td) / Path(f).name
                t.write_bytes(data)
                try:
                    py_compile.compile(str(t), doraise=True)
                except py_compile.PyCompileError as ex:
                    print("FAIL: %s would not compile: %s. Nothing written." % (f, str(ex)[:300])); return 2
    if args.check:
        print("CHECK OK: %d file(s) to write. Nothing written." % len(plan)); return 0
    if not plan:
        print("Nothing to do: every file already carries %s." % MARK); return 0
    for f, data in plan.items():
        p = Path(f)
        shutil.copy2(p, p.with_name(p.name + ".bak_" + TAG + "_" + stamp))
        t = p.with_name(p.name + ".tmp_" + TAG); t.write_bytes(data); os.replace(t, p)
        print("wrote %s" % f)
    return 0


if __name__ == "__main__":
    sys.exit(main())
