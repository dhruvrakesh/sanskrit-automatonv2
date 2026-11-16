#!/usr/bin/env python3
# -*- coding: ascii -*-
"""

patch_vamsa_g6a_2026_11_15.py  (2026-11-15)  VAMSA_G6A_2026_11_15   (G6a: the genealogies' texts taught to vamsa_read)

Asked on 15 Nov: "authoritative genealogies of these kings ... the sanskrit texts (primary and critical editions,
wherever possible)", and then: "build G6a: teach scripts\\vamsa_read.py the genealogical chapters of the Harivamsa, the
Ramayana, the Mahabharata's Adiparvan and the Puranas listed in the handover". vamsa_read.py read three works whose
verse mark is "// vip_4,1.2 //". GRETIL's other files mark their verses otherwise. This patch adds:

  scripts/vamsa_read.py   G6_WORKS: hv, ram1, ram2, matsya, bndp1, bndp2, brahma, linga1, kurma1, garuda1, agni,
                          markp, mbh1, vipc4 (each with its mark and its chapters); verses_g6() (two numbers, no
                          closing mark, half-verses joined, prose marks, a star passage left out, a mark with a
                          misprinted chapter mended, a number given twice kept as 20 and 20b); verses_mbh() (the
                          Mahabharata's lines: the padas of one number are one verse); the colophons, headings, page
                          marks and the Agni's footnotes out; --work g6; --show n and --verses (free looks at the cut);
                          the plan's NEXT names chapters the work has.

The three works of G5a (WORKS) are cut as before and --work all is still those three: vamsa_join and the site read
WORKS, so nothing of G6 reaches the site. The prompt, the checks and the store are unchanged.

Anchored edits, all or nothing; a file that already carries the marker is skipped; .bak_vamsag6a_<date> copies.

  python scripts\\patch_vamsa_g6a_2026_11_15.py --check
  python scripts\\patch_vamsa_g6a_2026_11_15.py
"""
from __future__ import annotations
import argparse, datetime, os, py_compile, shutil, sys, tempfile
from pathlib import Path

MARK = 'VAMSA_G6A_2026_11_15'
TAG = 'vamsag6a'
FILES = ['scripts/vamsa_read.py']
NEEDS = {'scripts/vamsa_read.py': 'VAMSA_HEAL_2026_11_11'}
REQUIRES = {}   # another file that must carry a marker first
E = []


def edit(f, n, old, new):
    E.append((f, n, old, new))


edit('scripts/vamsa_read.py', 1, '    indexes (G5b) are what joins a line across chapters and books.\n  python scripts\\\\vamsa_read.py --reparse   then   python scripts\\\\vamsa_read.py --report      (free)\n"""\nfrom __future__ import annotations',
     '    indexes (G5b) are what joins a line across chapters and books.\n  python scripts\\\\vamsa_read.py --reparse   then   python scripts\\\\vamsa_read.py --report      (free)\n\nVAMSA_G6A_2026_11_15 (G6a, free: asked on 15 Nov, "authoritative genealogies of these kings ... the sanskrit texts\n(primary and critical editions, wherever possible)"): the genealogical chapters of the works GRETIL\'s archive holds\nhere, beside the three above. Their verse marks differ (two numbers, no closing //, half-verses, the Mahabharata\'s\nlines), so each work says how its marks are written (G6_WORKS) and verses_g6() cuts it:\n  hv       the Harivamsa (Vaidya\'s constituted text, BORI 1969): 2-3, 9-10, 15, 23-28, 98-99\n  ram1     the Ramayana, book 1: 37-46 (Sagara\'s line), 69-70 (the Iksvakus, Janaka\'s line)     ram2   book 2: 102\n  matsya   the Matsyapurana: 5-6, 12, 24, 34, 43-51            brahma   the Brahmapurana: 3, 7-16\n  bndp1    the Brahmandapurana, book 1: 9-14                   bndp2    book 2: 1-6, 61-74\n  linga1   the Lingapurana, book 1: 63-69                      kurma1   the Kurmapurana, book 1: 8, 12-13, 17-23, 38\n  garuda1  the Garudapurana, book 1: 5-6, 54, 138-145          agni     the Agnipurana: 18-20, 272-277\n  markp    the Markandeyapurana: 52-53, 76\n  mbh1     the Mahabharata, Adiparvan (BORI\'s electronic text): 1.59-61, 70, 80, 89-92, 100, 107, 111\n  vipc4    the Visnupurana, book 4, in Pathak\'s critical edition (vip4 is the 1910 Venkatesvara print)\nA star passage or an appendix (a mark with * or @) is not the constituted text and is left out; half-verses (ab, cd)\nand the Mahabharata\'s padas are joined into their verse; the Agni\'s footnotes, the colophons and the page marks are\ntaken out. --work all is still the three works of G5a (what the site\'s Dynasties page is built from: nothing of G6\ngoes to the site until its pages are decided); --work g6 is these. A work is read with the same prompt and checks.\n  python scripts\\\\vamsa_read.py --work g6                          the plan of these works (free)\n  python scripts\\\\vamsa_read.py --work hv --chapters 9 --show 12   the first 12 verses as they would be sent (free)\n  python scripts\\\\vamsa_read.py --work g6 --verses                 every chapter: its verses, the gaps in their numbers (free)\n"""\nfrom __future__ import annotations')

edit('scripts/vamsa_read.py', 2, 'MARK = "VAMSA_READ_2026_11_11"\nHEAL = "VAMSA_HEAL_2026_11_11"\nPROMPT_VERSION = "vamsa-read-v1"\nROOT = Path(__file__).resolve().parents[1]',
     'MARK = "VAMSA_READ_2026_11_11"\nHEAL = "VAMSA_HEAL_2026_11_11"\nG6A = "VAMSA_G6A_2026_11_15"\nPROMPT_VERSION = "vamsa-read-v1"\nROOT = Path(__file__).resolve().parents[1]')

edit('scripts/vamsa_read.py', 3, '              "chapters": [1], "title": "Bhagavatapurana 12.1", "entry": "Ulrich Stiehl", "ref": "BhP %d.%d.%d"},\n}\nRELS = ("son_of", "daughter_of", "wife_of", "brother_of", "sister_of", "succeeded", "descendant_of", "line_of", "other")\nMODEL = "claude-sonnet-5-5"',
     '              "chapters": [1], "title": "Bhagavatapurana 12.1", "entry": "Ulrich Stiehl", "ref": "BhP %d.%d.%d"},\n}\n# VAMSA_G6A_2026_11_15: the works of G6 (see the docstring). "marker": the verse\'s mark, with the groups b (book, when\n# the work has books), c (chapter), v (verse), h (a half-verse\'s letters), x or cx (a star passage, an appendix: left\n# out). "form": "mbh" for the Mahabharata\'s lines. "notes": True when footnotes stand between the verses (the Agni).\nBORI = "GRETIL\'s copy of the Bhandarkar Oriental Research Institute\'s electronic text (1999), for reference only"\nG6_WORKS = {\n    "hv": {"member": "sa_harivaMza.txt", "marker": r"(?://[ \\t]*)?\\*?HV_(?P<c>\\d+)[.,](?P<v>\\d+)(?P<x>\\*\\S*)?",\n           "book": None, "chapters": [2, 3, 9, 10, 15, 23, 24, 25, 26, 27, 28, 98, 99],\n           "title": "Harivamsa (Vaidya\'s constituted text)", "entry": "Atul Agarwala, J. Wayne Bass and others",\n           "ref": "HV %d.%d"},\n    "ram1": {"member": "sa_rAmAyaNa.txt", "marker": r"R_(?P<b>\\d+),(?P<c>\\d+)\\.(?P<v>\\d+)", "book": 1,\n             "chapters": [37, 38, 39, 40, 41, 42, 43, 44, 45, 46, 69, 70], "title": "Ramayana, book 1 (Balakanda)",\n             "entry": "Muneo Tokunaga, John Smith", "ref": "R %d,%d.%d"},\n    "ram2": {"member": "sa_rAmAyaNa.txt", "marker": r"R_(?P<b>\\d+),(?P<c>\\d+)\\.(?P<v>\\d+)", "book": 2,\n             "chapters": [102], "title": "Ramayana, book 2 (Ayodhyakanda)", "entry": "Muneo Tokunaga, John Smith",\n             "ref": "R %d,%d.%d"},\n    "matsya": {"member": "sa_matsyapurANa1-176.txt",\n               "marker": r"(?://[ \\t]*)?MatsP_(?P<c>\\d+)\\.(?P<v>\\d+)[*:]*", "book": None,\n               "chapters": [5, 6, 12, 24, 34, 43, 44, 45, 46, 47, 48, 49, 50, 51], "title": "Matsyapurana",\n               "entry": "Oliver Hellwig", "ref": "MatsP %d.%d"},\n    "bndp1": {"member": "sa_brahmANDapurANa.txt",\n              "marker": r"//[ \\t]*bndp_(?P<b>\\d+),(?P<c>\\d+)\\.(?P<v>\\d*)[ \\t]*(?://|/)?", "book": 1,\n              "chapters": [9, 10, 11, 12, 13, 14], "title": "Brahmandapurana, book 1",\n              "entry": "members of the Sansknet Project", "ref": "BndP %d,%d.%d"},\n    "bndp2": {"member": "sa_brahmANDapurANa.txt",\n              "marker": r"//[ \\t]*bndp_(?P<b>\\d+),(?P<c>\\d+)\\.(?P<v>\\d*)[ \\t]*(?://|/)?", "book": 2,\n              "chapters": [1, 2, 3, 4, 5, 6, 61, 62, 63, 64, 65, 66, 67, 68, 69, 70, 71, 72, 73, 74],\n              "title": "Brahmandapurana, book 2", "entry": "members of the Sansknet Project", "ref": "BndP %d,%d.%d"},\n    "brahma": {"member": "sa_brahmapurANa-1-246.txt",\n               "marker": r"(?://[ \\t]*|\\|\\|[ \\t]*\\()?BrP_(?P<c>\\d+)(?P<cx>\\*)?\\.(?P<v>\\d+)\\)?", "book": None,\n               "chapters": [3, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16], "title": "Brahmapurana",\n               "entry": "Peter Schreiner and Renate Soehnen-Thieme", "ref": "BrP %d.%d"},\n    "linga1": {"member": "sa_liGgapurANa1-108.txt", "marker": r"(?://[ \\t]*)?LiP_(?P<b>\\d+),(?P<c>\\d+)\\.(?P<v>\\d+)",\n               "book": 1, "chapters": [63, 64, 65, 66, 67, 68, 69], "title": "Lingapurana, book 1",\n               "entry": "members of the Sansknet Project", "ref": "LiP %d,%d.%d"},\n    "kurma1": {"member": "sa_kUrmapurANa.txt",\n               "marker": r"//[ \\t]*k\\u016brmp_(?P<b>\\d+),(?P<c>\\d+)\\.(?P<v>\\d+)[ \\t]*(?://)?", "book": 1,\n               "chapters": [8, 12, 13, 17, 18, 19, 20, 21, 22, 23, 38], "title": "Kurmapurana, book 1",\n               "entry": "members of the Sansknet Project", "ref": "KurmP %d,%d.%d"},\n    "garuda1": {"member": "sa_garuDapurANa.txt",\n                "marker": r"//[ \\t]*garp_(?P<b>\\d+),(?P<c>\\d+)\\.(?P<v>\\d*)(?P<x>\\*\\d+)?[ \\t]*(?://|/)?", "book": 1,\n                "chapters": [5, 6, 54, 138, 139, 140, 141, 142, 143, 144, 145], "title": "Garudapurana, book 1",\n                "entry": "members of the Sansknet Project", "ref": "GarP %d,%d.%d"},\n    "agni": {"member": "sa_agnipurANa.txt",\n             "marker": r"/+ap_(?P<x>\\*)?(?P<c>\\d+)(?P<cx>[^\\d.\\s/]*)\\.(?P<v>\\d+)(?P<h>[^\\d\\s/]*)/", "book": None,\n             "chapters": [18, 19, 20, 272, 273, 274, 275, 276, 277], "title": "Agnipurana", "entry": "Jun Takashima",\n             "ref": "AgP %d.%d", "notes": True},\n    "markp": {"member": "sa_mArkaNDeyapurANa1-93.txt", "marker": r"//[ \\t]*markp_(?P<c>\\d+)\\.(?P<v>\\d*)[ \\t]*(?://)?",\n              "book": None, "chapters": [52, 53, 76], "title": "Markandeyapurana",\n              "entry": "members of the Sansknet Project", "ref": "MarkP %d.%d"},\n    "mbh1": {"member": "mbh_01_u.htm", "form": "mbh", "book": 1,\n             "chapters": [59, 60, 61, 70, 80, 89, 90, 91, 92, 100, 107, 111], "title": "Mahabharata, Adiparvan",\n             "entry": "Muneo Tokunaga, John Smith", "ref": "MBh %d,%d.%d", "source": BORI},\n    "vipc4": {"member": "sa_viSNupurANa-crit.txt",\n              "marker": r"(?://[ \\t]*|\\|\\|[ \\t]*\\()?ViP_(?P<b>\\d+),(?P<c>\\d+)\\.(?P<v>\\d+)(?P<h>ab|cd|ef)?"\n                        r"(?P<x>[*@][^\\s|)]*)?\\|?\\)?",\n              "book": 4, "chapters": None, "title": "Visnupurana, book 4 (Pathak\'s critical edition)",\n              "entry": "Peter Schreiner", "ref": "ViPc %d,%d.%d"},\n}\nGROUPS = {"all": list(WORKS), "g6": list(G6_WORKS)}\n\n\ndef work_of(work: str) -> dict:\n    """The work\'s entry: one of G5a\'s three (WORKS) or one of G6\'s (G6_WORKS)."""\n    return WORKS[work] if work in WORKS else G6_WORKS[work]\n\n\ndef source_of(work: str) -> str:\n    w = work_of(work)\n    return "%s; %s (data entry: %s)" % (w["member"], w.get("source") or GRETIL, w["entry"])\n\n\nRELS = ("son_of", "daughter_of", "wife_of", "brother_of", "sister_of", "succeeded", "descendant_of", "line_of", "other")\nMODEL = "claude-sonnet-5-5"')

edit('scripts/vamsa_read.py', 4, 'def verses_of(work: str, text: str) -> list:\n    """[(chapter, verse, ref, text)] of the work\'s book (and chapters), in order: the text before each marker."""\n    w = WORKS[work]\n    out, last = [], 0',
     'def verses_of(work: str, text: str) -> list:\n    """[(chapter, verse, ref, text)] of the work\'s book (and chapters), in order: the text before each marker."""\n    if work in G6_WORKS:   # VAMSA_G6A_2026_11_15\n        return verses_g6(work, text)\n    w = WORKS[work]\n    out, last = [], 0')

edit('scripts/vamsa_read.py', 5, '        if t:\n            out.append((c, v, w["ref"] % (b, c, v), t))\n    return out\n',
     '        if t:\n            out.append((c, v, w["ref"] % (b, c, v), t))\n    return out\n\n\nG6_DROP = re.compile(r"(?m)^[ \\t]*(?:(?::\\S+[ \\t]+)?\\[*[ \\t]*(?:it[iy]|eti).*dhy\\u0101y.*|.*pur\\u0101\\u1e47e.*dhy\\u0101ya\\u1e25.*"\n                     r"|[%:].*|\\(.*\\)[ \\t]*/?|\\[.*\\]|.*-[ \\t]*\\d+|\\S*-pur\\u0101\\u1e47a[ \\t]+\\d+)[ \\t\\r]*$")\nG6_CALL = re.compile(r"\\((?:\\d+|[?!])\\)|(?<![^\\s(])\\d+(?:[.,]\\d+)*(?=[ \\t]*/)")\nMBH_LINE = re.compile(r"(?m)^(\\d\\d),(\\d\\d\\d)\\.(\\d\\d\\d)([A-Za-z])\\t(.*?)[ \\t\\r]*$")\nPAGE_END = re.compile(r":p[ \\t]*\\d+[ \\t\\r]*$")\n\n\ndef clean_g6(seg: str) -> str:\n    """VAMSA_G6A_2026_11_15: a verse\'s text without the colophon, the chapter\'s heading, the page marks and the\n    footnotes\' calls that stand before it in GRETIL\'s files."""\n    return clean(G6_CALL.sub("", G6_DROP.sub(" ", seg.replace("<BR>", " "))))\n\n\ndef no_notes(text: str, marker: str) -> str:\n    """VAMSA_G6A_2026_11_15: the Agni\'s footnotes out: from a line ":n" to the line that ends with the page\'s mark\n    (":p 8"), or to the next line that carries a verse\'s mark."""\n    out, skip, rx = [], False, re.compile(marker)\n    for ln in text.split("\\n"):\n        if ln.strip() == ":n":\n            skip = True\n            continue\n        if skip:\n            if rx.search(ln):\n                skip = False\n            else:\n                if PAGE_END.search(ln):\n                    skip = False\n                continue\n        out.append(ln)\n    return "\\n".join(out)\n\n\ndef verses_mbh(work: str, text: str) -> list:\n    """VAMSA_G6A_2026_11_15: the Mahabharata\'s file: a line is "01,089.001a", a TAB and a pada (or a prose sentence,\n    A, B, ...); the padas of one number are one verse. A line of a star passage or an appendix (* or @ in its\n    reference) and a speaker\'s line (no letter) are left out."""\n    w = G6_WORKS[work]\n    out = []\n    for m in MBH_LINE.finditer(text):\n        b, c, v = int(m.group(1)), int(m.group(2)), int(m.group(3))\n        if b != w["book"] or (w["chapters"] and c not in w["chapters"]):\n            continue\n        t = clean_g6(re.sub(r"<[^>]*>", " ", m.group(5)))\n        if not t:\n            continue\n        ref = w["ref"] % (b, c, v)\n        if out and out[-1][2] == ref:\n            out[-1] = (c, v, ref, out[-1][3] + " " + t)\n        else:\n            out.append((c, v, ref, t))\n    return out\n\n\ndef verses_g6(work: str, text: str) -> list:\n    """VAMSA_G6A_2026_11_15: [(chapter, verse, ref, text)] of a work of G6_WORKS: the text before each mark; the\n    halves of a verse joined; a star passage or an appendix left out; a mark that lost its verse\'s number gives its\n    text to the verse after it; a number given twice in a chapter keeps both verses (20, 20b)."""\n    w = G6_WORKS[work]\n    if w.get("form") == "mbh":\n        return verses_mbh(work, text)\n    if w.get("notes"):\n        text = no_notes(text, w["marker"])\n    out, last, carry, seen = [], 0, "", set()\n    ms = list(re.finditer(w["marker"], text))\n    at = [(m.groupdict().get("b"), m.group("c")) for m in ms]\n    for i in range(1, len(ms)):   # a chapter\'s number misprinted in one mark (ap_273.001cd in 274): the chapter around it\n        nxt = at[i + 1:i + 4]   # and it is not the chapter that goes on after (the first mark of 274 is right)\n        if at[i] != at[i - 1] and at[i - 1] in nxt and nxt[-1] != at[i]:\n            at[i] = at[i - 1]\n    for i, m in enumerate(ms):\n        seg, last = text[last:m.start()], m.end()\n        d = dict(m.groupdict(), b=at[i][0], c=at[i][1])\n        if d.get("x") or d.get("cx"):\n            carry = ""\n            continue\n        if not d.get("v"):\n            carry += seg + "\\n"\n            continue\n        seg, carry = carry + seg, ""\n        b = int(d["b"]) if d.get("b") else None\n        c, v = int(d["c"]), int(d["v"])\n        if b != w["book"] or (w["chapters"] and c not in w["chapters"]):\n            continue\n        t = clean_g6(seg)\n        if not t:\n            continue\n        ref = w["ref"] % ((b, c, v) if b is not None else (c, v))\n        if out and out[-1][2] == ref:\n            out[-1] = (c, v, ref, out[-1][3] + " " + t)\n            continue\n        k = 0\n        while ref in seen:   # a number given to two verses of a chapter (the print\'s): the second is 20b\n            k += 1\n            ref = w["ref"] % ((b, c, v) if b is not None else (c, v)) + "bcdefgh"[min(k, 7) - 1] * (1 + max(0, k - 7))\n        seen.add(ref)\n        out.append((c, v, ref, t))\n    return out\n\n\ndef gaps(verses: list) -> dict:\n    """VAMSA_G6A_2026_11_15: {chapter: {"verses", "first", "last", "missing": [numbers not there], "again": [numbers\n    there twice]}}: what a look at a work\'s cut shows before any reading is bought."""\n    out = {}\n    for c, v, _r, _t in verses:\n        d = out.setdefault(c, {"verses": 0, "first": v, "last": v, "seen": []})\n        d["verses"] += 1\n        d["first"], d["last"] = min(d["first"], v), max(d["last"], v)\n        d["seen"].append(v)\n    for d in out.values():\n        seen = d.pop("seen")\n        d["missing"] = [n for n in range(1, d["last"] + 1) if n not in set(seen)]\n        d["again"] = sorted({n for n in seen if seen.count(n) > 1})\n    return out\n')

edit('scripts/vamsa_read.py', 6, '\ndef user_message(work: str, u: dict) -> str:\n    w = WORKS[work]\n    lines = ["%s, chapter %d%s (GRETIL\'s text). The verses:" % (w["title"], u["chapter"],\n                                                                 ", part %d" % u["part"] if u["part"] else ""), ""]',
     '\ndef user_message(work: str, u: dict) -> str:\n    w = work_of(work)\n    lines = ["%s, chapter %d%s (GRETIL\'s text). The verses:" % (w["title"], u["chapter"],\n                                                                 ", part %d" % u["part"] if u["part"] else ""), ""]')

edit('scripts/vamsa_read.py', 7, '\ndef plan_units(a) -> dict:\n    works = list(WORKS) if a.work == "all" else [a.work]\n    texts, out = {}, {}\n    want = parse_chapters(a.chapters)\n    for wk in works:\n        m = WORKS[wk]["member"]\n        if m not in texts:\n            texts[m] = read_member(a.zip, m)',
     '\ndef plan_units(a) -> dict:\n    works = GROUPS.get(a.work) or [a.work]\n    texts, out = {}, {}\n    want = parse_chapters(a.chapters)\n    for wk in works:\n        m = work_of(wk)["member"]\n        if m not in texts:\n            texts[m] = read_member(a.zip, m)')

edit('scripts/vamsa_read.py', 8, '\n\ndef do_plan(a, units: dict) -> int:\n    total, todo_n, todo_usd = 0.0, 0, 0.0',
     '\n\ndef trial_of(a, units: dict) -> str:\n    """VAMSA_G6A_2026_11_15: "--work w --chapters a-b": the first two chapters not read yet of the first work that has\n    any (a work of G6 does not begin at chapter 1)."""\n    for wk, us in units.items():\n        left = sorted({u["chapter"] for u in us if not done(a.out, wk, u)})[:2]\n        if left:\n            spec = "%d" % left[0] if len(left) == 1 else ("%d-%d" if left[1] == left[0] + 1 else "%d,%d") % tuple(left)\n            return "--work %s --chapters %s" % (wk, spec)\n    return "--work %s --chapters 1-2" % next(iter(units))\n\n\ndef do_show(a, units: dict) -> int:\n    """VAMSA_G6A_2026_11_15: the verses as they would be sent (--show n: the first n of what was asked), or each\n    chapter\'s count and the gaps in its numbers (--verses). Free: nothing is sent, nothing is written."""\n    n_all, odd = 0, 0\n    for wk, us in units.items():\n        vs = [(u["chapter"], int(re.findall(r"\\d+", r)[-1]), r, t) for u in us for r, t in u["verses"]]\n        n_all += len(vs)\n        if a.show:\n            print("  %s: %s, %s" % (wk, work_of(wk)["title"], source_of(wk)))\n            for _c, _v, r, t in vs[:a.show]:\n                print("    [%s] %s" % (r, t))\n            continue\n        for c, d in sorted(gaps(vs).items()):\n            bad = bool(d["missing"] or d["again"])\n            odd += 1 if bad else 0\n            print("  %-8s chapter %3d: %4d verses, %d to %d%s%s" % (\n                wk, c, d["verses"], d["first"], d["last"],\n                ("; not there: %s" % ", ".join(str(n) for n in d["missing"][:12])) if d["missing"] else "",\n                ("; twice: %s" % ", ".join(str(n) for n in d["again"][:12])) if d["again"] else ""))\n    if a.show:\n        print("VERDICT: the first %d verse(s) of each work asked for, as they would be sent (free; nothing sent)" % a.show)\n    else:\n        print("VERDICT: %d verses in %d work(s); %d chapter(s) with a gap or a number twice (free; nothing sent)"\n              % (n_all, len(units), odd))\n    print("NEXT: python scripts\\\\vamsa_read.py %s --yes   (a trial)" % trial_of(a, units))\n    return 0\n\n\ndef do_plan(a, units: dict) -> int:\n    total, todo_n, todo_usd = 0.0, 0, 0.0')

edit('scripts/vamsa_read.py', 9, '        todo_n += len(left); todo_usd += usd; total += sum(estimate(u["chars"], a.model) for u in us)\n        print("  %-6s %-28s %3d chapter part(s), %5d verses, %7d characters; %d to read, about $%.2f"\n              % (wk, WORKS[wk]["title"], len(us), n_v, chars, len(left), usd))\n    print("  %s" % credit_line(a.db))\n    print("VERDICT: %d part(s) to read, about $%.2f (the whole: about $%.2f; the estimate is a guess until the trial "\n          "measures it), %s with %s" % (todo_n, todo_usd, total, "the Claude credit", a.model))\n    first = next(iter(units))\n    print("NEXT: python scripts\\\\vamsa_read.py --work %s --chapters 1-2 --yes   (a trial)" % first\n          if todo_n else "NEXT: python scripts\\\\vamsa_read.py --report")\n    return 0',
     '        todo_n += len(left); todo_usd += usd; total += sum(estimate(u["chars"], a.model) for u in us)\n        print("  %-6s %-28s %3d chapter part(s), %5d verses, %7d characters; %d to read, about $%.2f"\n              % (wk, work_of(wk)["title"], len(us), n_v, chars, len(left), usd))\n    print("  %s" % credit_line(a.db))\n    print("VERDICT: %d part(s) to read, about $%.2f (the whole: about $%.2f; the estimate is a guess until the trial "\n          "measures it), %s with %s" % (todo_n, todo_usd, total, "the Claude credit", a.model))\n    print("NEXT: python scripts\\\\vamsa_read.py %s --yes   (a trial)" % trial_of(a, units)\n          if todo_n else "NEXT: python scripts\\\\vamsa_read.py --report")\n    return 0')

edit('scripts/vamsa_read.py', 10, '        print("REFUSE: the estimate is $%.2f, above --max-usd %.2f by half again: read fewer chapters (--chapters), or "\n              "raise --max-usd" % (need, a.max_usd))\n        print("VERDICT: nothing sent"); print("NEXT: python scripts\\\\vamsa_read.py --work %s --chapters 1-2 --yes"\n                                               % todo[0][0])\n        return 1\n    own = None',
     '        print("REFUSE: the estimate is $%.2f, above --max-usd %.2f by half again: read fewer chapters (--chapters), or "\n              "raise --max-usd" % (need, a.max_usd))\n        print("VERDICT: nothing sent"); print("NEXT: python scripts\\\\vamsa_read.py %s --yes" % trial_of(a, units))\n        return 1\n    own = None')

edit('scripts/vamsa_read.py', 11, '                break\n            t0 = time.time()\n            rec = {"mark": MARK, "work": wk, "title": WORKS[wk]["title"], "chapter": u["chapter"], "part": u["part"],\n                   "refs": [r for r, _t in u["verses"]], "model": a.model, "effort": a.effort,\n                   "prompt_version": PROMPT_VERSION, "source": "%s; %s (data entry: %s)" % (\n                       WORKS[wk]["member"], GRETIL, WORKS[wk]["entry"]),\n                   "at": datetime.datetime.now().isoformat(timespec="seconds")}\n            try:',
     '                break\n            t0 = time.time()\n            rec = {"mark": MARK, "work": wk, "title": work_of(wk)["title"], "chapter": u["chapter"], "part": u["part"],\n                   "refs": [r for r, _t in u["verses"]], "model": a.model, "effort": a.effort,\n                   "prompt_version": PROMPT_VERSION, "source": source_of(wk),\n                   "at": datetime.datetime.now().isoformat(timespec="seconds")}\n            try:')

edit('scripts/vamsa_read.py', 12, '\ndef do_report(a) -> int:\n    works = list(WORKS) if a.work == "all" else [a.work]\n    ex = Path(a.exports)\n    ex.mkdir(parents=True, exist_ok=True)',
     '\ndef do_report(a) -> int:\n    works = GROUPS.get(a.work) or [a.work]\n    ex = Path(a.exports)\n    ex.mkdir(parents=True, exist_ok=True)')

edit('scripts/vamsa_read.py', 13, '        lp = Path(a.out) / ("%s_lines.json" % wk)\n        lp.parent.mkdir(parents=True, exist_ok=True)\n        lp.write_text(json.dumps({"mark": HEAL, "work": wk, "title": WORKS[wk]["title"], "lines": [\n            [{"name": n, "ref": r, "words": w} for n, r, w in ln] for ln in lines if len(ln) > 1]},\n            ensure_ascii=False, indent=1), encoding="utf-8")',
     '        lp = Path(a.out) / ("%s_lines.json" % wk)\n        lp.parent.mkdir(parents=True, exist_ok=True)\n        lp.write_text(json.dumps({"mark": HEAL, "work": wk, "title": work_of(wk)["title"], "lines": [\n            [{"name": n, "ref": r, "words": w} for n, r, w in ln] for ln in lines if len(ln) > 1]},\n            ensure_ascii=False, indent=1), encoding="utf-8")')

edit('scripts/vamsa_read.py', 14, 'def main(argv=None) -> int:\n    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)\n    ap.add_argument("--work", default="all", choices=["all"] + list(WORKS))\n    ap.add_argument("--chapters", default="", help="numbers and ranges: 1-3,7")\n    ap.add_argument("--yes", action="store_true", help="read (the Claude credit); without it, the plan")',
     'def main(argv=None) -> int:\n    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)\n    ap.add_argument("--work", default="all", choices=list(GROUPS) + list(WORKS) + list(G6_WORKS),\n                    help="all: G5a\'s three works; g6: the works of VAMSA_G6A_2026_11_15; or one work")\n    ap.add_argument("--chapters", default="", help="numbers and ranges: 1-3,7")\n    ap.add_argument("--yes", action="store_true", help="read (the Claude credit); without it, the plan")')

edit('scripts/vamsa_read.py', 15, '    ap.add_argument("--reparse", action="store_true", help="the stored replies parsed and checked again (free)")\n    ap.add_argument("--report", action="store_true", help="the counts, the CSVs, the longest lines (free)")\n    ap.add_argument("--db", default="data/context.db")\n    ap.add_argument("--zip", default=ZIP)',
     '    ap.add_argument("--reparse", action="store_true", help="the stored replies parsed and checked again (free)")\n    ap.add_argument("--report", action="store_true", help="the counts, the CSVs, the longest lines (free)")\n    ap.add_argument("--show", type=int, default=0, help="print the first n verses as they would be sent (free)")\n    ap.add_argument("--verses", action="store_true", help="each chapter\'s verses and the gaps in their numbers (free)")\n    ap.add_argument("--db", default="data/context.db")\n    ap.add_argument("--zip", default=ZIP)')

edit('scripts/vamsa_read.py', 16, '    except (ValueError, FileNotFoundError) as e:\n        print("REFUSE: %s" % e); print("VERDICT: nothing read"); print("NEXT: "); return 1\n    if a.reparse:\n        return do_reparse(a, units)',
     '    except (ValueError, FileNotFoundError) as e:\n        print("REFUSE: %s" % e); print("VERDICT: nothing read"); print("NEXT: "); return 1\n    if getattr(a, "show", 0) or getattr(a, "verses", False):   # VAMSA_G6A_2026_11_15\n        return do_show(a, units)\n    if a.reparse:\n        return do_reparse(a, units)')


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
            print("REFUSE: %s is not here (run this from the repository root). Nothing written." % f); return 1
        raw = p.read_bytes()
        if MARK.encode() in raw:
            print("skip %s (already carries %s)" % (f, MARK)); continue
        need = NEEDS.get(f)
        if need and need.encode() not in raw:
            print("REFUSE: %s does not carry %s (apply that first). Nothing written." % (f, need)); return 1
        nl = nl_of(raw)
        text = raw.decode("utf-8").replace("\r\n", "\n")
        for ff, n, old, new in E:
            if ff != f:
                continue
            k = text.count(old)
            if k != 1:
                print("REFUSE: %s: anchor %d found %d times (want 1). Nothing written." % (f, n, k)); return 1
            text = text.replace(old, new)
        plan[f] = (text.replace("\n", "\r\n") if nl == "\r\n" else text).encode("utf-8")
    if not plan:
        print("Nothing to do: every file already carries %s." % MARK); return 0
    for f, data in plan.items():
        if f.endswith(".py"):
            with tempfile.TemporaryDirectory() as td:
                t = Path(td) / Path(f).name
                t.write_bytes(data)
                try:
                    py_compile.compile(str(t), cfile=str(t) + "c", doraise=True)
                except py_compile.PyCompileError as e:
                    print("FAIL: %s would not compile (%s). Nothing written." % (f, e)); return 1
    if args.check:
        print("CHECK OK: %d file(s) to write. Nothing written." % len(plan)); return 0
    done = []
    try:
        for f, data in plan.items():
            p = Path(f)
            shutil.copy2(p, p.with_name(p.name + ".bak_%s_%s" % (TAG, stamp)))
            tmp = p.with_name(p.name + ".tmp_" + TAG)
            tmp.write_bytes(data)
            os.replace(tmp, p)
            done.append(f)
            print("wrote %s" % f)
    except OSError as e:
        print("FAIL while writing (%s). Restore from the .bak_%s_%s copies: %s" % (e, TAG, stamp, ", ".join(done)))
        return 3
    return 0


if __name__ == "__main__":
    sys.exit(main())

