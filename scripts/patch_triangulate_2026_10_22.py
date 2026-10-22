#!/usr/bin/env python3
# -*- coding: ascii -*-
"""
patch_triangulate_2026_10_22.py  (2026-10-22)  TRIANGULATE_2026_10_22

Asked on 22 Oct: to "compare our own quality of ingestion and ocr and vision engine" with the sources the search finds,
where no e-text exists. scripts/source_fidelity.py (needs FIDELITY_2026_10_22), --pair A,B now also counts where the two
readings agree with each other against the reference ("outvoted"): with the reference one of our own readings (db:,
vision:, raw:), that is where it is most likely misread, and those places are kept as the mends to read beside the page
(in the report, and the first --examples printed); with an e-text as the reference, where the print reads otherwise.
The verdict, when the reference is ours, judges it by that rate, each other reading by its own; unless the two make
the same mistakes (their own misreadings alike 0.12 or more, or the outvoted places like their mistakes 0.30 or more:
Tesseract and archive.org's text layer of one scan, 0.25 and 0.40 on 22 Oct; independent pairs 0.04 to 0.06): then their vote is no evidence and the
reference is not measured; nor when one of them is the reference's own text again (it lacks fewer than 1 akshara
in 1,000 of it). Nothing else changes.
Anchored, all-or-nothing, marker-idempotent; keeps line endings; backups .bak_triangulate_<date>.
  python scripts\\patch_triangulate_2026_10_22.py --check
  python scripts\\patch_triangulate_2026_10_22.py
  python scripts\\source_fidelity.py --ref db:markandeya_purana --cand raw:markandeya_purana --cand db:markandeya_purana__w_gretil --pair raw:markandeya_purana,db:markandeya_purana__w_gretil
"""
from __future__ import annotations
import argparse, datetime, os, py_compile, shutil, sys, tempfile
from pathlib import Path

MARK = 'TRIANGULATE_2026_10_22'
TAG = 'triangulate'
FILES = ['scripts/source_fidelity.py']
NEEDS = {'scripts/source_fidelity.py': 'FIDELITY_2026_10_22'}
REQUIRES = {}   # another file that must carry a marker first
E = []


def edit(f, n, old, new):
    E.append((f, n, old, new))


edit('scripts/source_fidelity.py', 1, '    ops = SequenceMatcher(None, tu, tw, autojunk=False).get_opcodes()\n    ok, ins, err, diffs = bytearray(L), {}, 0, []\n    first_k = last_k = None\n    shift0 = 0',
     '    ops = SequenceMatcher(None, tu, tw, autojunk=False).get_opcodes()\n    ok, ins, err, diffs = bytearray(L), {}, 0, []\n    got = [""] * L                                     # TRIANGULATE_2026_10_22: what the reading has at each akshara\n    first_k = last_k = None\n    shift0 = 0')

edit('scripts/source_fidelity.py', 2, '            for i in range(i1, i2):\n                ok[i] = 1\n        elif tag == "replace":\n            err += max(i2 - i1, k2 - k1)\n            if k2 - k1 > i2 - i1:',
     '            for i in range(i1, i2):\n                ok[i] = 1\n                got[i] = tu[i]\n        elif tag == "replace":\n            for d, i in enumerate(range(i1, i2)):\n                got[i] = tw[k1 + d] if k1 + d < k2 else ""\n            err += max(i2 - i1, k2 - k1)\n            if k2 - k1 > i2 - i1:')

edit('scripts/source_fidelity.py', 3, '    first_k = first_k or 0\n    last_k = last_k if last_k is not None else 0\n    return {"err": err, "n": L, "ok": ok, "ins": ins, "diffs": diffs,\n            "at": lo + len("".join(tw[:first_k])) + shift0, "end": lo + len("".join(tw[:last_k]))}\n',
     '    first_k = first_k or 0\n    last_k = last_k if last_k is not None else 0\n    return {"err": err, "n": L, "ok": ok, "ins": ins, "diffs": diffs, "got": got,\n            "at": lo + len("".join(tw[:first_k])) + shift0, "end": lo + len("".join(tw[:last_k]))}\n')

edit('scripts/source_fidelity.py', 4, '\n\ndef pair(units: list, ra: list, rb: list) -> dict:\n    """Two readings of one print, over the units both read: each of the e-text\'s aksharas that one reading lacks\n    (misread or missing) and the other has is the first\'s own error; one both lack is shared. Aksharas a reading\n    adds are counted apart: where they go is less sure."""\n    both = [i for i in range(len(units)) if ra[i] and rb[i]]\n    L = own_a = own_b = shared = add_a = add_b = add_shared = 0\n    for i in both:\n        oa, ob = ra[i]["ok"], rb[i]["ok"]\n        L += ra[i]["n"]\n        for j in range(ra[i]["n"]):\n            if not oa[j] and not ob[j]:\n                shared += 1\n            elif not oa[j]:\n                own_a += 1\n            elif not ob[j]:\n                own_b += 1\n        ia, ib = ra[i]["ins"], rb[i]["ins"]\n        for j in set(ia) | set(ib):',
     '\n\ndef pair(units: list, ra: list, rb: list, refs: list = None, keep: int = 200) -> dict:\n    """Two readings of one print, over the units both read: each of the reference\'s aksharas that one reading lacks\n    (misread or missing) and the other has is the first\'s own error; one both lack is shared. Aksharas a reading\n    adds are counted apart: where they go is less sure. TRIANGULATE_2026_10_22: where both lack it and both have the\n    same akshara instead, the two readings agree against the reference ("outvoted"): when the reference is one of our\n    own readings, that is where it is most likely misread (when it is an e-text, where the print reads otherwise);\n    the first `keep` of them are kept as the mends to read beside the page."""\n    both = [i for i in range(len(units)) if ra[i] and rb[i]]\n    L = own_a = own_b = shared = add_a = add_b = add_shared = outvoted = 0\n    mends = []\n    ca, cb, co = {}, {}, {}                            # the substitutions: a\'s own, b\'s own, the outvoted\n    for i in both:\n        oa, ob = ra[i]["ok"], rb[i]["ok"]\n        ga, gb = ra[i].get("got") or [], rb[i].get("got") or []\n        tu = aksharas(units[i])\n        L += ra[i]["n"]\n        for j in range(ra[i]["n"]):\n            if not oa[j] and not ob[j]:\n                shared += 1\n                if j < len(ga) and j < len(gb) and ga[j] and ga[j] == gb[j]:\n                    outvoted += 1\n                    co[(tu_j(units, i, j, tu), ga[j])] = co.get((tu_j(units, i, j, tu), ga[j]), 0) + 1\n                    if len(mends) < keep:\n                        mends.append({"ref": refs[i] if refs else i, "page": ra[i].get("page"),\n                                      "before": "".join(tu[max(0, j - 4):j]), "reference": tu[j], "readings": ga[j],\n                                      "after": "".join(tu[j + 1:j + 5])})\n            elif not oa[j]:\n                own_a += 1\n                if j < len(ga) and ga[j]:\n                    ca[(tu_j(units, i, j, tu), ga[j])] = ca.get((tu_j(units, i, j, tu), ga[j]), 0) + 1\n            elif not ob[j]:\n                own_b += 1\n                if j < len(gb) and gb[j]:\n                    cb[(tu_j(units, i, j, tu), gb[j])] = cb.get((tu_j(units, i, j, tu), gb[j]), 0) + 1\n        ia, ib = ra[i]["ins"], rb[i]["ins"]\n        for j in set(ia) | set(ib):')

edit('scripts/source_fidelity.py', 5, '            add_a += x - min(x, y)\n            add_b += y - min(x, y)\n    return {"units": len(both), "aksharas": L, "own_a_per100": _pct(own_a, L), "own_b_per100": _pct(own_b, L),\n            "shared_per100": _pct(shared, L), "added_a_per100": _pct(add_a, L), "added_b_per100": _pct(add_b, L),\n            "added_shared_per100": _pct(add_shared, L), "own_a": own_a, "own_b": own_b, "shared": shared}\n\n',
     '            add_a += x - min(x, y)\n            add_b += y - min(x, y)\n    own_overlap = _overlap(ca, cb)\n    out_overlap = max(_overlap(co, ca), _overlap(co, cb))\n    # a reading that is the reference\'s own text again (the repair beside the vision it was made from) is no witness\n    same = "a" if L and (own_a + shared) < SAME_TEXT * L else ("b" if L and (own_b + shared) < SAME_TEXT * L else "")\n    return {"units": len(both), "aksharas": L, "own_a_per100": _pct(own_a, L), "own_b_per100": _pct(own_b, L),\n            "shared_per100": _pct(shared, L), "added_a_per100": _pct(add_a, L), "added_b_per100": _pct(add_b, L),\n            "added_shared_per100": _pct(add_shared, L), "outvoted_per100": _pct(outvoted, L), "outvoted": outvoted,\n            "own_a": own_a, "own_b": own_b, "shared": shared, "mends": mends,\n            "own_overlap": own_overlap, "outvoted_overlap": out_overlap, "same_text": same,\n            "independent": not same and own_overlap < SAME_OWN and out_overlap < SAME_OUTVOTED}\n\n\n# TRIANGULATE_2026_10_22: two readings that make the same mistakes are not two witnesses. On 22 Oct, Tesseract and\n# archive.org\'s text layer of the same scan (DLI 2015.405693): their own misreadings overlapped 0.25 and the places\n# they agreed against our vision text looked like their own mistakes, 0.40 (bha read ma, tha read ya); Tesseract and\n# GRETIL\'s Markandeya: 0.04 and 0.11. The vote of a pair over these is no evidence against the reference.\n# On 80 of its pages the same pair\'s own misreadings were alike 0.19; a pair of independent readings 0.04 to 0.06.\nSAME_OWN, SAME_OUTVOTED = 0.12, 0.30\nSAME_TEXT = 0.001          # a reading that lacks fewer than 1 in 1,000 of the reference\'s aksharas is its text again\nTOP = 30\n\n\ndef tu_j(units, i, j, tu):\n    return tu[j] if tu is not None and j < len(tu) else ""\n\n\ndef _overlap(x: dict, y: dict) -> float:\n    """How alike two profiles of substitutions are: the shared share of their 30 commonest, 0 to 1."""\n    def top(c):\n        t = sorted(c.items(), key=lambda kv: -kv[1])[:TOP]\n        s = float(sum(v for _, v in t)) or 1.0\n        return {k: v / s for k, v in t}\n    a, b = top(x), top(y)\n    return round(sum(min(a[k], b[k]) for k in set(a) & set(b)), 3) if a and b else 0.0\n\n')

edit('scripts/source_fidelity.py', 6, '\n\ndef _safe(s: str) -> str:\n    return re.sub(r"[^A-Za-z0-9_.-]+", "_", s).strip("_.")[:120]',
     '\n\nOUR_READINGS = ("db", "vision", "raw")\n\n\ndef verdict_of_ours(ref: str, pairs: list) -> str:\n    """TRIANGULATE_2026_10_22: no e-text, three readings of one print: the reference (ours) is judged by where the other\n    two agree against it, each of them by its own misreadings."""\n    p = pairs[0]\n    o = p["outvoted_per100"]\n    if p.get("same_text"):\n        return ("%s: not measured: %s is its own text again, no witness; a reading by another engine, or an e-text, "\n                "measures it" % (ref, p["a"] if p["same_text"] == "a" else p["b"]))\n    if not p.get("independent", True):\n        return ("%s: not measured: %s and %s make the same mistakes (alike %.2f and %.2f): their vote against it is no "\n                "evidence; a reading by another engine, or an e-text, measures it" % (\n                    ref, p["a"], p["b"], p["own_overlap"], p["outvoted_overlap"]))\n    return ("%s: %s; outvoted by %s and %s in %s aksharas per 100 (its likely misreadings, %d to read beside the page); "\n            "their own misreadings %s and %s per 100" % (\n                ref, STEP_WORDS[step_of(own=o)] if o is not None else "not measured", p["a"], p["b"], o,\n                p["outvoted"], p["own_a_per100"], p["own_b_per100"]))\n\n\ndef _safe(s: str) -> str:\n    return re.sub(r"[^A-Za-z0-9_.-]+", "_", s).strip("_.")[:120]')

edit('scripts/source_fidelity.py', 7, '          "and a final m as the anusvara; a final consonant joined to the vowel after it; a colon as the visarga%s" % (\n              "; ccha and cha as ca" if a.fold_ch else ""))\n    report = {"mark": MARK, "at": _now(), "ref": a.ref, "prefix": a.prefix or "", "fold_ch": bool(a.fold_ch),\n              "units": len(units), "short_left_out": short, "readings": {}, "pairs": []}\n    results = {}',
     '          "and a final m as the anusvara; a final consonant joined to the vowel after it; a colon as the visarga%s" % (\n              "; ccha and cha as ca" if a.fold_ch else ""))\n    ours = a.ref.split(":", 1)[0] in OUR_READINGS       # TRIANGULATE_2026_10_22: the reference is one of our readings\n    report = {"mark": MARK, "at": _now(), "ref": a.ref, "prefix": a.prefix or "", "fold_ch": bool(a.fold_ch),\n              "ours": ours,\n              "units": len(units), "short_left_out": short, "readings": {}, "pairs": []}\n    results = {}')

edit('scripts/source_fidelity.py', 8, '            print("\\npair %s: both must be among the --cand readings" % pr)\n            continue\n        p = pair(units, results[x], results[y])\n        p.update(a=x, b=y)\n        report["pairs"].append(p)\n        print()\n        print("one print, two readings, over the %d units both read (%d aksharas of the e-text), per 100 aksharas:" % (\n            p["units"], p["aksharas"]))\n        print("  misread or missing: %s\'s own %s; %s\'s own %s; shared (the print\'s reading, the e-text\'s slip, or a "\n              "page both fail) %s" % (x, p["own_a_per100"], y, p["own_b_per100"], p["shared_per100"]))\n        print("  added: %s\'s own %s; %s\'s own %s; shared %s" % (\n            x, p["added_a_per100"], y, p["added_b_per100"], p["added_shared_per100"]))\n    first = report["readings"].get(a.cand[0])\n    if not a.no_write:',
     '            print("\\npair %s: both must be among the --cand readings" % pr)\n            continue\n        p = pair(units, results[x], results[y], refs)\n        p.update(a=x, b=y)\n        report["pairs"].append(p)\n        print()\n        print("one print, two readings, over the %d units both read (%d aksharas of the %s), per 100 aksharas:" % (\n            p["units"], p["aksharas"], "reference" if ours else "e-text"))\n        print("  misread or missing: %s\'s own %s; %s\'s own %s; shared (the print\'s reading, the e-text\'s slip, or a "\n              "page both fail) %s" % (x, p["own_a_per100"], y, p["own_b_per100"], p["shared_per100"]))\n        print("  added: %s\'s own %s; %s\'s own %s; shared %s" % (\n            x, p["added_a_per100"], y, p["added_b_per100"], p["added_shared_per100"]))\n        # TRIANGULATE_2026_10_22: both readings agree with each other against the reference\n        if p["same_text"]:\n            print("  NOT INDEPENDENT: %s is the reference\'s own text again (it lacks fewer than 1 akshara in 1,000 of "\n                  "it): no witness. The vote below is no evidence." % (x if p["same_text"] == "a" else y))\n        elif not p["independent"]:\n            print("  NOT INDEPENDENT: the two make the same mistakes (their own misreadings alike %.2f; where they agree "\n                  "against the reference, it looks like their mistakes, %.2f): one engine, or the same weak letters. "\n                  "Their vote below is no evidence against the reference." % (p["own_overlap"], p["outvoted_overlap"]))\n        print("  the two agree against the reference: %s per 100 (%d aksharas)%s" % (\n            p["outvoted_per100"], p["outvoted"],\n            ": the reference\'s likely misreadings, the mends to read beside the page" if ours else\n            ": where the print reads otherwise than the e-text (another edition, or the e-text\'s slip)"))\n        for m in p["mends"][:a.examples]:\n            print("    %s (page %s): %s[%s -> %s]%s" % (m["ref"], m["page"], m["before"], m["reference"],\n                                                       m["readings"], m["after"]))\n    first = report["readings"].get(a.cand[0])\n    if not a.no_write:')

edit('scripts/source_fidelity.py', 9, '        print("\\nwritten: %s" % (out_dir / name))\n    print()\n    print("VERDICT: " + verdict_of(a.cand[0], first, report["pairs"]))\n    print("NEXT: read the worst units beside the print, then decide per text (docs/FIDELITY_2026-10-22.md)")\n    print("ALSO: python scripts\\\\source_fidelity.py --ledger")',
     '        print("\\nwritten: %s" % (out_dir / name))\n    print()\n    if ours and report["pairs"]:\n        print("VERDICT: " + verdict_of_ours(a.ref, report["pairs"]))\n    else:\n        print("VERDICT: " + verdict_of(a.cand[0], first, report["pairs"]))\n    print("NEXT: read the worst units beside the print, then decide per text (docs/FIDELITY_2026-10-22.md)")\n    print("ALSO: python scripts\\\\source_fidelity.py --ledger")')


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
