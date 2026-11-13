#!/usr/bin/env python3
# -*- coding: ascii -*-
"""


patch_source_pick_2026_11_13.py  (2026-11-13)  SOURCE_PICK_2026_11_13

Asked on 13 Nov: "are we able to choose the best available from etext and our own ocr+vision text for translation and
then get to the scholarly prose and edition for each? Ganita Yuktibhasa and Surya Siddhanta are on the top of our list."

Within a scan the choice is made already (repair_text.py merges Tesseract and vision page by page: the consensus).
Between the scan and an e-text (etext_witness.py keeps it as its own text, <doc>__w_<site>) benchmark_sources.py measured
both and said nothing of which to use. Now:

  scripts/benchmark_sources.py   pick_reading(): the reading to make the scholarly English and its prose from (the e-text
                                 when it is the same text as ours, F1 page by page at least 0.6, and misreads no more
                                 than ours; else ours, ready when its misreading is cosmetic, else after its repair);
                                 kept in data\\benchmarks\\<doc>.json as "pick" and printed as PICK:
  scripts/translation_desk.py    pick_of(): a text's pick (a witness reads its scan's)
  scripts/dashboard.py           /desk/<doc>: the pick in the box of the scholarly English, with a link to the text
                                 picked; or the free command that measures it
  tests/test_banner_head_2026_11_13.py, tests/test_bench_letters_2026_10_22.py   their replays compare with the
                                 copies from before this patch

A person confirms; nothing is chosen for them. Anchored edits, all or nothing; a file that already carries the marker is
skipped; .bak_sourcepick_<date> copies.

  python scripts\\patch_source_pick_2026_11_13.py --check
  python scripts\\patch_source_pick_2026_11_13.py
"""
from __future__ import annotations
import argparse, datetime, os, py_compile, shutil, sys, tempfile
from pathlib import Path

MARK = 'SOURCE_PICK_2026_11_13'
TAG = 'sourcepick'
FILES = ['scripts/benchmark_sources.py', 'scripts/translation_desk.py', 'scripts/dashboard.py', 'tests/test_banner_head_2026_11_13.py', 'tests/test_bench_letters_2026_10_22.py']
NEEDS = {'scripts/benchmark_sources.py': 'BENCH_LETTERS_2026_10_22', 'scripts/translation_desk.py': 'DESK_SCHOLAR_NEXT_2026_11_13', 'scripts/dashboard.py': 'DESK_SCHOLAR_NEXT_2026_11_13', 'tests/test_banner_head_2026_11_13.py': 'BANNER_HEAD_2026_11_13'}
REQUIRES = {}   # another file that must carry a marker first
E = []


def edit(f, n, old, new):
    E.append((f, n, old, new))


edit('scripts/benchmark_sources.py', 1, '        len(res["readings"]), doc, (" with the critical e-text (%s)" % res["reference"]) if res["reference"] else "",\n        best, (ours or res["readings"][0])["misread_letters_pct"])\n    return res\n\n',
     '        len(res["readings"]), doc, (" with the critical e-text (%s)" % res["reference"]) if res["reference"] else "",\n        best, (ours or res["readings"][0])["misread_letters_pct"])\n    res["pick"] = pick_reading(res, doc)   # SOURCE_PICK_2026_11_13\n    return res\n\n\n# SOURCE_PICK_2026_11_13. Asked on 13 Nov: "are we able to choose the best available from etext and our own ocr+vision\n# text for translation and then get to the scholarly prose and edition for each? Ganita Yuktibhasa and Surya Siddhanta are\n# on the top of our list." Within the scan the choice is made already: the repair (repair_text.py) merges Tesseract and\n# vision page by page into the consensus. Between the scan and an e-text (a witness of etext_witness.py, kept as its own\n# text "<doc>__w_<site>") the benchmark measured both and said nothing of which to use. pick_reading() says it, for the\n# scholarly English and its prose: the e-text when it is the same text as ours (F1 page by page at least PICK_F1) and\n# misreads no more than ours; else ours, ready when its misreading is cosmetic, else after its repair. A person confirms:\n# the desk shows the pick (translation_desk.pick_of) and nothing is chosen for them.\nPICK_F1 = 0.6\n\n\ndef pick_reading(res: dict, doc: str) -> dict:\n    """{doc, reading, why, then}: the reading to make the scholarly English and its prose from (SOURCE_PICK_2026_11_13)."""\n    rd = res.get("readings") or []\n    ours = next((x for x in rd if x.get("kind") == "ours"), None) or next((x for x in rd if x.get("kind") == "db"), None)\n    ets = [x for x in rd if x.get("kind") == "etext" and x.get("site")]\n    om = (ours or {}).get("misread_letters_pct")\n    if ets:\n        w = max(ets, key=lambda x: (x.get("f1_ours") or 0.0, x.get("letters") or 0))\n        f1 = w.get("f1_ours")\n        code = "%s__w_%s" % (doc, w["site"])\n        if f1 is not None and f1 >= PICK_F1 and (om is None or (w.get("misread_letters_pct") or 0.0) <= om):\n            return {"doc": code, "reading": w["label"],\n                    "why": "the e-text (%s) is the same text as ours (F1 %.2f page by page, %s pages) and misreads no letter; "\n                           "ours misreads %s of the letters: make the scholarly English and its prose from the e-text; "\n                           "ours stays the scan\'s witness" % (w["label"], f1, w.get("ours_pages") or "-",\n                                                             ("%.2f%%" % om) if om is not None else "-"),\n                    "then": "python scripts\\\\scholar_translate.py --doc %s --status   (free)" % code}\n        why = ("the e-text (%s) agrees with ours on F1 %.2f only, page by page: another recension, or numbered "\n               "otherwise; ours for the edition, the e-text to compare" % (w["label"], f1) if f1 is not None else\n               "the e-text (%s) could not be aligned with ours: ours for the edition, the e-text to compare" % w["label"])\n        if ours and ours.get("level") not in ("cosmetic", None, "-"):\n            why += "; ours misreads %.2f%% (%s): repair it first" % (om or 0.0, ours.get("level"))\n        return {"doc": doc, "reading": (ours or {}).get("label", ""), "why": why,\n                "then": "python scripts\\\\repair_text.py --doc %s   (free: what the repair would cost)" % doc\n                if ours and ours.get("level") not in ("cosmetic", None, "-") else ""}\n    if not ours:\n        return {"doc": doc, "reading": "", "why": "nothing of this text is read yet", "then": ""}\n    if ours.get("level") in ("cosmetic", None, "-"):\n        return {"doc": doc, "reading": ours["label"],\n                "why": "no e-text of it here; ours (%s) misreads %.2f%% of the letters (cosmetic): ready for its scholarly "\n                       "English and its prose" % (ours["label"], om or 0.0), "then": ""}\n    return {"doc": doc, "reading": ours["label"],\n            "why": "no e-text of it here; ours (%s) misreads %.2f%% of the letters (%s): repair it first (vision reads "\n                   "the pages Tesseract misread), then its scholarly English; an edition made now goes stale where the "\n                   "reading changes" % (ours["label"], om or 0.0, ours.get("level")),\n            "then": "python scripts\\\\repair_text.py --doc %s   (free: what the repair would cost)" % doc}\n\n')

edit('scripts/benchmark_sources.py', 2, '    p = write(res, Path(a.bench_dir))\n    print("  wrote %s" % p)\n    print("VERDICT: " + res.get("verdict", ""))\n    print("NEXT: " + res.get("next", ""))\n    for x in res.get("also") or []:\n        print("ALSO: " + x)\n    return 0\n',
     '    p = write(res, Path(a.bench_dir))\n    print("  wrote %s" % p)\n    pk = res.get("pick") or {}   # SOURCE_PICK_2026_11_13\n    if pk.get("doc"):\n        print("PICK: for the scholarly English and its prose: %s (%s): %s" % (pk["doc"], pk.get("reading") or "-", pk["why"]))\n    print("VERDICT: " + res.get("verdict", ""))\n    print("NEXT: " + res.get("next", ""))\n    for x in res.get("also") or []:\n        print("ALSO: " + x)\n    if pk.get("then"):\n        print("ALSO: " + pk["then"])\n    return 0\n')

edit('scripts/translation_desk.py', 1, '\n\ndef next_step(stage: str, prow=None, cover=None, mula: int = 0) -> str:\n    """The desk\'s one next step for a text, in words."""',
     '\n\ndef pick_of(doc: str, bench_dir) -> dict:\n    """SOURCE_PICK_2026_11_13: the benchmark\'s pick for a text (benchmark_sources.pick_reading): which reading to make the\n    scholarly English and its prose from, with its date and the text it was measured for ("of"). A witness\'s page reads\n    its scan\'s pick. None when no benchmark has a pick."""\n    base = str(doc or "").split("__w_")[0]\n    try:\n        j = json.loads((Path(bench_dir) / ("%s.json" % base)).read_text(encoding="utf-8"))\n    except (OSError, ValueError):\n        return None\n    p = j.get("pick") if isinstance(j, dict) else None\n    if not isinstance(p, dict) or not p.get("doc"):\n        return None\n    return dict(p, at=str(j.get("at") or ""), of=base)\n\n\ndef next_step(stage: str, prow=None, cover=None, mula: int = 0) -> str:\n    """The desk\'s one next step for a text, in words."""')

edit('scripts/dashboard.py', 1, '    held_ok = held == "in_repair"\n    ctl = ""\n    if r.get("guard") and r["stage"] == "edition":\n        ctl += (\'<p class="warn">Its path says the reading comes first (%s): the verses of the pages that change go \'',
     '    held_ok = held == "in_repair"\n    ctl = ""\n    _pk = td.pick_of(r["doc"], BENCH_DIR) if hasattr(td, "pick_of") else None   # SOURCE_PICK_2026_11_13\n    if _pk:\n        ctl += (\'<p class="%s">The reading to make the edition from (the benchmark of %s): %s. %s.%s</p>\' % (\n            "small" if _pk["doc"] == r["doc"] else "warn", e(_pk.get("at", "")[:10]),\n            "<b>this text</b>" if _pk["doc"] == r["doc"] else \'<a href="/desk/%s">%s</a>\' % (e(_pk["doc"], quote=True),\n                                                                                             e(_pk["doc"])),\n            e(_pk.get("why", "")), (" Then: <code>%s</code>" % e(_pk["then"])) if _pk.get("then") else ""))\n    elif "__w_" not in r["doc"]:\n        ctl += (\'<p class="small">Which reading to make the edition from, this scan\\\'s or an e-text\\\'s: not measured yet. \'\n                \'Free: <code>python scripts\\\\benchmark_sources.py --doc %s</code></p>\' % e(r["doc"]))\n    if r.get("guard") and r["stage"] == "edition":\n        ctl += (\'<p class="warn">Its path says the reading comes first (%s): the verses of the pages that change go \'')

edit('tests/test_banner_head_2026_11_13.py', 1, '            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)\n            for rel in FILES:\n                self.assertEqual((t / rel).read_bytes(), (REPO / rel).read_bytes(), rel)\n            self.assertIn("Nothing to do", run().stdout)\n',
     '            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)\n            for rel in FILES:\n                want = (REPO / rel).read_bytes()\n                later = sorted((REPO / rel).parent.glob(Path(rel).name + ".bak_sourcepick_*"))   # SOURCE_PICK_2026_11_13 came after\n                if later and b"SOURCE_PICK_2026_11_13" in want:\n                    want = later[0].read_bytes()\n                self.assertEqual((t / rel).read_bytes(), want, rel)\n            self.assertIn("Nothing to do", run().stdout)\n')

edit('tests/test_bench_letters_2026_10_22.py', 1, '            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)\n            for f in self.FILES:\n                self.assertEqual((t / f).read_bytes(), (REPO / f).read_bytes(), f)\n            self.assertIn("Nothing to do", subprocess.run(pat, cwd=td, capture_output=True, text=True).stdout)\n',
     '            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)\n            for f in self.FILES:\n                want = (REPO / f).read_bytes()\n                later = sorted((REPO / f).parent.glob(Path(f).name + ".bak_sourcepick_*"))   # SOURCE_PICK_2026_11_13 came after\n                if later and b"SOURCE_PICK_2026_11_13" in want:\n                    want = later[0].read_bytes()\n                self.assertEqual((t / f).read_bytes(), want, f)\n            self.assertIn("Nothing to do", subprocess.run(pat, cwd=td, capture_output=True, text=True).stdout)\n')


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

