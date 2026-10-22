#!/usr/bin/env python3
# -*- coding: ascii -*-
"""
patch_bench_letters_2026_10_22.py  (2026-10-22)  BENCH_LETTERS_2026_10_22

The Source desk's "Benchmark the readings (free)" compared the readings by the Latin misread, the noise, the
plausibility and a six-letter consonant-skeleton F1: a share of the script, and n-grams without the vowel signs, where
the misreadings are. scripts/benchmark_sources.py (needs REINGEST_2026_10_12; source_fidelity.py must carry
TRIANGULATE_2026_10_22) now also reads each reading against ours akshara by akshara on a sample of pages
(--letters-pages, 80; 40 with --all; 0: none), and Tesseract beside each other OCR reading: each one's own misreadings,
and where the two agree against ours (ours' likely misreadings). Two columns in the table (aksh%, own), lines in the
opinion, res["letters"] in the JSON; archive.org's reading is judged letter by letter too, and a reading that makes Tesseract's mistakes is said to be no
independent reading; beside the repair, vision and the database
(its sources) vote not, nor a reading 99.9% alike to ours. A failure there never fails
the benchmark. tests/test_reingest_2026_10_12.py: its replay of benchmark_sources.py ends at the copy this patch backed
up. Anchored, all-or-nothing, marker-idempotent; keeps line endings; backups .bak_benchletters_<date>.
  python scripts\\patch_bench_letters_2026_10_22.py --check
  python scripts\\patch_bench_letters_2026_10_22.py
  python scripts\\benchmark_sources.py --doc Daivat-Sanhita
"""
from __future__ import annotations
import argparse, datetime, os, py_compile, shutil, sys, tempfile
from pathlib import Path

MARK = 'BENCH_LETTERS_2026_10_22'
TAG = 'benchletters'
FILES = ['scripts/benchmark_sources.py', 'tests/test_reingest_2026_10_12.py']
NEEDS = {'scripts/benchmark_sources.py': 'REINGEST_2026_10_12', 'tests/test_reingest_2026_10_12.py': 'REINGEST_2026_10_12'}
REQUIRES = {'scripts/source_fidelity.py': 'TRIANGULATE_2026_10_22'}   # another file that must carry a marker first
E = []


def edit(f, n, old, new):
    E.append((f, n, old, new))


edit('scripts/benchmark_sources.py', 1, "fidelity (mt_reviews) where it ran, and the share of the passages translated that carried misread letters:\nthat is the debris's effect on the translation, measured.\n\nWrites data\\\\benchmarks\\\\<doc>.json (and data\\\\benchmarks\\\\_summary.json with --all). Never writes the",
     'fidelity (mt_reviews) where it ran, and the share of the passages translated that carried misread letters:\nthat is the debris\'s effect on the translation, measured.\n\nBENCH_LETTERS_2026_10_22: and letter by letter. On a sample of pages (--letters-pages, 80; 40 with --all; 0: none) each\nreading is read against ours akshara by akshara (source_fidelity.py: folded alike, aligned, upper bounds), and Tesseract\nbeside each other OCR reading: where the two agree with each other against ours, ours is most likely misread there\n("outvoted"); where one lacks what the other and ours have, it is that one\'s own misreading. A share of Devanagari, the\nLatin misread and the noise see the script; this sees the letters (on 22 Oct archive.org\'s text of the Satapatha\'s\nscan was 100% Devanagari and misread 25 aksharas in 100).\n\nWrites data\\\\benchmarks\\\\<doc>.json (and data\\\\benchmarks\\\\_summary.json with --all). Never writes the')

edit('scripts/benchmark_sources.py', 2, '    res["translations"] = {"now": now, "before": before}\n    res["merged_engines"] = page_engines(merged, doc)   # QUALITY_2026_10_11\n    return opine(res, doc, a)\n\n',
     '    res["translations"] = {"now": now, "before": before}\n    res["merged_engines"] = page_engines(merged, doc)   # QUALITY_2026_10_11\n    n_pages = getattr(a, "letters_pages", None)\n    if ours and n_pages:\n        try:\n            letters(res, readings, ours, n_pages)       # BENCH_LETTERS_2026_10_22\n        except Exception as ex:                         # an addition: never the benchmark\'s failure\n            res["letters_error"] = str(ex)[:200]\n    return opine(res, doc, a)\n\n\ndef letters(res: dict, readings: list, ours: tuple, n_pages: int) -> None:\n    """BENCH_LETTERS_2026_10_22: every reading against ours, akshara by akshara, on a sample of ours\' pages; then\n    Tesseract beside each other OCR reading (vision, archive.org\'s text, the repair): own misreadings and where the\n    two agree against ours. Fills each reading\'s aksharas_ours (and own_per100) and res["letters"]."""\n    import source_fidelity as sf\n    pages = sorted(p for p, t in ours[3].items() if len(sf.norm(t)) >= sf.MIN_LETTERS)\n    if not pages:\n        return\n    step = max(1, len(pages) // n_pages)\n    sample = pages[::step][:n_pages]\n    units = [sf.norm(ours[3][p]) for p in sample]\n    refs = ["p%d" % p for p in sample]\n    per = {}\n    for label, kind, site, pg in readings:\n        if label == ours[0]:\n            continue\n        rs = [(sf.measure([u], [(p, pg[p])], False)[0] if pg.get(p) else None) for p, u in zip(sample, units)]\n        per[label] = rs\n        found = [r for r in rs if r]\n        n = sum(r["n"] for r in found)\n        d = _r(res, label)\n        if d is not None:\n            d["aksharas_ours"] = round(100.0 - 100.0 * sum(r["err"] for r in found) / n, 2) if n else None\n            d["aksharas_pages"] = len(found)\n    # the voters: OCR readings of the scan that are not ours\' own text again: the repair is made from vision (and\n    # the database from the repair), so beside the repair they are its sources, not witnesses; a reading 99.9% alike\n    # is a copy of ours too\n    same, voters = [], []\n    for label in per:\n        d = _r(res, label) or {}\n        if d.get("kind") not in ("ocr", "archive-ocr", "ours", "db") or d.get("aksharas_ours") is None:\n            continue\n        derived = ours[0] == "consensus" and label in ("vision", "database")\n        (same if (derived or d["aksharas_ours"] >= 99.9) else voters).append(label)\n    if "tesseract" in voters:\n        combos = [("tesseract", x) for x in voters if x != "tesseract"]\n    else:\n        combos = [(voters[i], voters[j]) for i in range(len(voters)) for j in range(i + 1, len(voters))]\n    pairs = []\n    for la, lb in combos:\n        pr = sf.pair(units, per[la], per[lb], refs, keep=12)\n        if not pr["units"]:\n            continue\n        pr.update(a=la, b=lb)\n        pairs.append(pr)\n        d = _r(res, lb)\n        d["own_per100"] = pr["own_b_per100"]\n        d["outvoted_ours_per100"] = pr["outvoted_per100"]\n        d["independent_of_tesseract"] = pr["independent"] if la == "tesseract" else None\n    for la in {pr["a"] for pr in pairs}:\n        d = _r(res, la)\n        if d is not None:\n            d["own_per100"] = max((x for x in pairs if x["a"] == la), key=lambda x: x["aksharas"])["own_a_per100"]\n    res["letters"] = {"mark": "BENCH_LETTERS_2026_10_22", "pages": len(sample), "ours": ours[0], "pairs": pairs,\n                      "same_as_ours": same}\n\n')

edit('scripts/benchmark_sources.py', 3, '        else:\n            word = "the two are level, each damaged in its own way"\n        L.append("archive.org\'s OCR (%s), on the %d pages it shares with this scan: %s; %s." % (x["label"], x["pages"], how, word))\n    if res["reference"]:',
     '        else:\n            word = "the two are level, each damaged in its own way"\n        if x.get("own_per100") is not None and x.get("independent_of_tesseract") is False:   # BENCH_LETTERS_2026_10_22\n            word += ("; letter by letter it makes Tesseract\'s mistakes (one engine, or the same weak letters): it is no "\n                     "independent reading, and its agreement with Tesseract says nothing against ours")\n        elif x.get("own_per100") is not None:\n            word += ("; letter by letter, its own misreadings %s aksharas in 100, and where it and Tesseract agree "\n                     "against ours, %s in 100 (ours\' likely misreadings)" % (x["own_per100"], x.get("outvoted_ours_per100")))\n        L.append("archive.org\'s OCR (%s), on the %d pages it shares with this scan: %s; %s." % (x["label"], x["pages"], how, word))\n    if res["reference"]:')

edit('scripts/benchmark_sources.py', 4, '            L.append("Vision alone reads the critical text better than the consensus (F1 %.2f against %.2f): the merge "\n                     "keeps some Tesseract readings it should not." % (vi["f1_ref"], co["f1_ref"]))\n    # QUALITY_2026_10_11: without a critical text too. On 11 Oct the Tantric Texts\' repair misread 1.90% of its letters\n    # where vision misread 0.17%: on 7 plates and title pages vision read nothing or a line, and the merge took',
     '            L.append("Vision alone reads the critical text better than the consensus (F1 %.2f against %.2f): the merge "\n                     "keeps some Tesseract readings it should not." % (vi["f1_ref"], co["f1_ref"]))\n    lt = res.get("letters") or {}\n    if lt.get("pages"):   # BENCH_LETTERS_2026_10_22\n        ag = [x for x in res["readings"] if x.get("aksharas_ours") is not None]\n        if ag:\n            L.append("Letter by letter, on %d of ours\' pages: %s agree with ours (%s) in %s of the aksharas." % (\n                lt["pages"], ", ".join(x["label"] for x in ag), lt["ours"],\n                ", ".join("%.1f%%" % x["aksharas_ours"] for x in ag)))\n        if lt.get("same_as_ours"):\n            L.append("%s: ours\' own text again (the repair\'s sources, or 99.9%% alike): no witness of it."\n                     % ", ".join(lt["same_as_ours"]))\n        if not lt.get("pairs"):\n            L.append("No two independent readings of the scan beside ours: its letters cannot be voted on here. A reading "\n                     "by another engine (vision, where ours is Tesseract\'s), or an e-text, measures it.")\n        for pr in lt.get("pairs") or []:\n            if not pr.get("independent", True):\n                L.append("%s and %s, letter by letter: their own misreadings %s and %s aksharas in 100, and they "\n                         "make the same mistakes (alike %.2f and %.2f): one engine, or the same weak letters; their "\n                         "agreement against ours is no evidence." % (pr["a"].capitalize(), pr["b"], pr["own_a_per100"],\n                                                                     pr["own_b_per100"], pr["own_overlap"],\n                                                                     pr["outvoted_overlap"]))\n                continue\n            L.append("%s and %s, letter by letter: their own misreadings %s and %s aksharas in 100; where they "\n                     "agree with each other against ours, %s in 100: there ours is most likely misread (%d places; read "\n                     "them beside the page: python scripts\\\\source_fidelity.py --ref db:%s --cand raw:%s --cand ...)." % (\n                         pr["a"].capitalize(), pr["b"], pr["own_a_per100"], pr["own_b_per100"], pr["outvoted_per100"],\n                         pr["outvoted"], res["doc"], res["doc"]))\n    # QUALITY_2026_10_11: without a critical text too. On 11 Oct the Tantric Texts\' repair misread 1.90% of its letters\n    # where vision misread 0.17%: on 7 plates and title pages vision read nothing or a line, and the merge took')

edit('scripts/benchmark_sources.py', 5, 'def show(res: dict):\n    print("%s  %s" % (res["doc"], MARK))\n    hdr = "  %-22s %-11s %6s %9s %7s %8s %7s %-9s %6s %6s %7s %7s %7s"   # QUALITY_2026_10_11: noise, plausible\n    print(hdr % ("reading", "kind", "pages", "letters", "latin%", "misread%", "pages%", "level", "noise%", "plaus%",\n                 "F1ours", "F1ref", "ref%"))\n    for x in res["readings"]:\n        f = lambda k, fmt="%.2f": (fmt % x[k]) if x.get(k) is not None else "-"\n        print(hdr % (x["label"][:22], x["kind"], x["pages"], x["letters"], f("latin_pct"), f("misread_letters_pct"),\n                     f("pages_misread_pct", "%.0f"), x.get("level") or "-", f("noise_pct", "%.1f"), f("plausible_pct", "%.1f"),\n                     f("f1_ours"), f("f1_ref"), ("%.0f" % (100 * x["recall_ref"])) if x.get("recall_ref") is not None else "-"))\n    for line in res.get("lines") or []:\n        print("  " + line)',
     'def show(res: dict):\n    print("%s  %s" % (res["doc"], MARK))\n    hdr = "  %-22s %-11s %6s %9s %7s %8s %7s %-9s %6s %6s %7s %7s %7s %7s %6s"   # QUALITY_2026_10_11; BENCH_LETTERS_2026_10_22\n    print(hdr % ("reading", "kind", "pages", "letters", "latin%", "misread%", "pages%", "level", "noise%", "plaus%",\n                 "F1ours", "F1ref", "ref%", "aksh%", "own"))\n    for x in res["readings"]:\n        f = lambda k, fmt="%.2f": (fmt % x[k]) if x.get(k) is not None else "-"\n        print(hdr % (x["label"][:22], x["kind"], x["pages"], x["letters"], f("latin_pct"), f("misread_letters_pct"),\n                     f("pages_misread_pct", "%.0f"), x.get("level") or "-", f("noise_pct", "%.1f"), f("plausible_pct", "%.1f"),\n                     f("f1_ours"), f("f1_ref"), ("%.0f" % (100 * x["recall_ref"])) if x.get("recall_ref") is not None else "-",\n                     f("aksharas_ours", "%.1f"), f("own_per100", "%.1f")))\n    for line in res.get("lines") or []:\n        print("  " + line)')

edit('scripts/benchmark_sources.py', 6, '    ap.add_argument("--backup-dir", default=os.environ.get("SA_BACKUP_DIR") or r"D:\\backups")\n    ap.add_argument("--from-dashboard", action="store_true", help=argparse.SUPPRESS)\n    a = ap.parse_args(argv)\n    os.chdir(ROOT)\n    if a.all:',
     '    ap.add_argument("--backup-dir", default=os.environ.get("SA_BACKUP_DIR") or r"D:\\backups")\n    ap.add_argument("--from-dashboard", action="store_true", help=argparse.SUPPRESS)\n    ap.add_argument("--letters-pages", type=int, default=None,   # BENCH_LETTERS_2026_10_22\n                    help="pages read letter by letter against ours (80; 40 with --all; 0: none)")\n    a = ap.parse_args(argv)\n    if a.letters_pages is None:\n        a.letters_pages = 40 if a.all else 80\n    os.chdir(ROOT)\n    if a.all:')

edit('tests/test_reingest_2026_10_12.py', 1, '            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)\n            for f in self.FILES:\n                later = sorted(SCRIPTS.glob(f + ".bak_path_*"))   # PATH_2026_10_12 came after\n                want = later[0] if later else (SCRIPTS / f)\n                self.assertEqual((t / "scripts" / f).read_bytes(), want.read_bytes(), f)',
     '            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)\n            for f in self.FILES:\n                later = (sorted(SCRIPTS.glob(f + ".bak_path_*"))   # PATH_2026_10_12 came after\n                         or sorted(SCRIPTS.glob(f + ".bak_benchletters_*")))   # BENCH_LETTERS_2026_10_22 (benchmark_sources.py)\n                want = later[0] if later else (SCRIPTS / f)\n                self.assertEqual((t / "scripts" / f).read_bytes(), want.read_bytes(), f)')


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
