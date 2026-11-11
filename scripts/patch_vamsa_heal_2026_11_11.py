#!/usr/bin/env python3
# -*- coding: ascii -*-
"""

patch_vamsa_heal_2026_11_11.py  (2026-11-11)  VAMSA_HEAL_2026_11_11

The first run of G5a (11 Nov, 18:52 to 19:10: 56 parts, 1,975 statements, 1,449 verified, $2.00) showed:
  - four parts not read ("Extra data"): Claude corrected itself in the reply ("Correction: ... a corrected reply
    follows", "Final answer:") and the parser read only one object;
  - a part (Visnupurana 4.2, 35 statements) all "bad": its statements came without their verse's reference;
  - 309 "unsupported", of which 281 were Claude's words written as Sanskrit is in a dictionary (putrah, not the verse's
    putra or putras; "..." for words left out);
  - the longest "lines" (42, 40, 36) ran through homonyms of different dynasties (Srnjaya, Candra, Nara, Sudhrti): the
    report joined persons by their names alone.

This patch (scripts/vamsa_read.py, tests/test_vamsa_read_2026_11_11.py): the last object of statements is read; a
statement without its reference takes the verse its words are in; the words are found with sandhi's endings and "..."
allowed; a person is a name with the father the text gives, joined to a father of that name only in the same chapter or
the one before; a mother is not a father; --report writes the lines with their verses
(data\\vamsa_read\\<work>_lines.json, exports\\vamsa_lines_<work>.csv). Nothing is sent again: --reparse reads the stored
replies (free).

Anchored edits, all or nothing; a file that already carries the marker is skipped; .bak_vamsaheal_<date> copies.

  python scripts\\patch_vamsa_heal_2026_11_11.py --check
  python scripts\\patch_vamsa_heal_2026_11_11.py
  python scripts\\vamsa_read.py --reparse
  python scripts\\vamsa_read.py --report
"""
from __future__ import annotations
import argparse, datetime, os, py_compile, shutil, sys, tempfile
from pathlib import Path

MARK = 'VAMSA_HEAL_2026_11_11'
TAG = 'vamsaheal'
FILES = ['scripts/vamsa_read.py', 'tests/test_vamsa_read_2026_11_11.py']
NEEDS = {'scripts/vamsa_read.py': 'VAMSA_READ_2026_11_11', 'tests/test_vamsa_read_2026_11_11.py': 'VAMSA_READ_2026_11_11'}
REQUIRES = {}   # another file that must carry a marker first
E = []


def edit(f, n, old, new):
    E.append((f, n, old, new))


edit('scripts/vamsa_read.py', 1, '  python scripts\\\\vamsa_read.py --reparse                         the stored replies parsed and checked again (free)\n  python scripts\\\\vamsa_read.py --report                          the counts, the CSVs, the longest lines (free)\n"""\nfrom __future__ import annotations',
     '  python scripts\\\\vamsa_read.py --reparse                         the stored replies parsed and checked again (free)\n  python scripts\\\\vamsa_read.py --report                          the counts, the CSVs, the longest lines (free)\n\nVAMSA_HEAL_2026_11_11 (after the first run, 11 Nov: 56 parts, 1,975 statements, 1,449 verified, $2.00):\n  - a reply that corrects itself ("Correction: ... a corrected reply follows", "Final answer:") is read by its last\n    JSON object of statements (four parts were not read: "Extra data");\n  - a statement without its verse\'s reference (a whole part, 35 statements, "bad") takes the verse its words are in;\n  - the words are looked for as Sanskrit is written: the end of each word may change by sandhi (putrah, putras,\n    putro), and "..." stands for words left out (281 of 309 "unsupported" were such);\n  - the lines: a person is a name and the father the text gives; a father\'s name is joined to a person of that name\n    only in the same chapter or the one before (never across the book: the first report drew one "line of 42" through\n    Srnjaya, Candra and Nara of different dynasties, homonyms); a mother is not a father. --report writes each line\n    with its verses (data\\\\vamsa_read\\\\<work>_lines.json, exports\\\\vamsa_lines_<work>.csv). The persons of the\n    indexes (G5b) are what joins a line across chapters and books.\n  python scripts\\\\vamsa_read.py --reparse   then   python scripts\\\\vamsa_read.py --report      (free)\n"""\nfrom __future__ import annotations')

edit('scripts/vamsa_read.py', 2, '\nMARK = "VAMSA_READ_2026_11_11"\nPROMPT_VERSION = "vamsa-read-v1"\nROOT = Path(__file__).resolve().parents[1]',
     '\nMARK = "VAMSA_READ_2026_11_11"\nHEAL = "VAMSA_HEAL_2026_11_11"\nPROMPT_VERSION = "vamsa-read-v1"\nROOT = Path(__file__).resolve().parents[1]')

edit('scripts/vamsa_read.py', 3, '\n# --------------------------------------------------------------------------------------------- the reply\ndef parse_reply(text: str) -> list:\n    """The statements of a reply; raises ValueError when it is not the JSON asked for."""\n    s = (text or "").strip()\n    s = re.sub(r"^```(?:json)?\\s*|\\s*```$", "", s)\n    i, j = s.find("{"), s.rfind("}")\n    if i < 0 or j <= i:\n        raise ValueError("no JSON object in the reply")\n    try:\n        d = json.loads(s[i:j + 1])\n    except ValueError:\n        d = json.loads(s[i:j + 1], strict=False)\n    st = d.get("statements") if isinstance(d, dict) else None\n    if not isinstance(st, list):\n        raise ValueError("the reply has no list of statements")\n    return [x for x in st if isinstance(x, dict)]\n\n',
     '\n# --------------------------------------------------------------------------------------------- the reply\ndef json_objects(s: str) -> list:\n    """Every JSON object at the top level of s, in order (the text between them left out)."""\n    dec, out, i = json.JSONDecoder(strict=False), [], 0\n    while True:\n        i = s.find("{", i)\n        if i < 0:\n            return out\n        try:\n            obj, end = dec.raw_decode(s, i)\n        except ValueError:\n            i += 1\n            continue\n        out.append(obj)\n        i = end\n\n\ndef parse_reply(text: str) -> list:\n    """The statements of a reply; raises ValueError when it is not the JSON asked for. VAMSA_HEAL_2026_11_11: a reply\n    that corrects itself is read by its last object of statements."""\n    s = (text or "").strip()\n    s = re.sub(r"^```(?:json)?\\s*|\\s*```$", "", s)\n    if s.find("{") < 0:\n        raise ValueError("no JSON object in the reply")\n    objs = [o for o in json_objects(s) if isinstance(o, dict) and isinstance(o.get("statements"), list)]\n    if not objs:\n        raise ValueError("the reply has no list of statements")\n    return [x for x in objs[-1]["statements"] if isinstance(x, dict)]\n\n')

edit('scripts/vamsa_read.py', 4, '\n\ndef check(st: dict, refs: dict, order: list) -> str:\n    """verified, words, unsupported or bad (see the docstring). refs: {ref: text}; order: the refs in order."""',
     '\n\ndef words_in(words: str, span: str, fold: bool = False) -> bool:\n    """VAMSA_HEAL_2026_11_11: the words are in span (letters only) as Sanskrit is written: the last letter of each word\n    of four letters or more may differ (sandhi: putrah, putras, putro), at most three letters may come between two\n    words, and "..." stands for words left out (each part found in order)."""\n    f = folded if fold else letters\n    pos = 0\n    for frag in re.split(r"\\.{2,}|\\u2026", str(words or "")):\n        toks = [f(x) for x in frag.split() if f(x)]\n        if not toks:\n            continue\n        cores = [x[:-1] if len(x) > 3 else x for x in toks]\n        if sum(len(c) for c in cores) < 4:\n            return False\n        m = re.compile(".{0,3}".join(re.escape(c) for c in cores)).search(span, pos)\n        if not m:\n            return False\n        pos = m.end()\n    return pos > 0\n\n\ndef ref_of(words: str, refs: dict, order: list):\n    """VAMSA_HEAL_2026_11_11: the verse of the part whose words these are (the first, alone or with the next), or None."""\n    for r in order:\n        if words_in(words, letters(refs[r])):\n            return r\n    for k, r in enumerate(order):\n        if words_in(words, letters(refs[r]) + "".join(letters(refs[x]) for x in order[k + 1:k + 2])):\n            return r\n    return None\n\n\ndef check(st: dict, refs: dict, order: list) -> str:\n    """verified, words, unsupported or bad (see the docstring). refs: {ref: text}; order: the refs in order."""')

edit('scripts/vamsa_read.py', 5, '    here = letters(refs[ref])\n    near = here + "".join(letters(refs[r]) for r in order[k + 1:k + 2])\n    w = letters(words)\n    if not w or w not in near:\n        return "unsupported"\n    span = "".join(letters(refs[r]) for r in order[max(0, k - 1):k]) + near   # a pronoun\'s person: the verse before',
     '    here = letters(refs[ref])\n    near = here + "".join(letters(refs[r]) for r in order[k + 1:k + 2])\n    if not (words_in(words, near) or words_in(words, folded(near), fold=True)):\n        return "unsupported"\n    span = "".join(letters(refs[r]) for r in order[max(0, k - 1):k]) + near   # a pronoun\'s person: the verse before')

edit('scripts/vamsa_read.py', 6, '    for st in statements:\n        x = {k: st.get(k) for k in ("ref", "a", "rel", "b", "words", "doubt")}\n        x["doubt"] = bool(x.get("doubt"))\n        x["check"] = check(st, refs, order)\n        out.append(x)\n    return out',
     '    for st in statements:\n        x = {k: st.get(k) for k in ("ref", "a", "rel", "b", "words", "doubt")}\n        if not x.get("ref"):   # VAMSA_HEAL_2026_11_11: the reference under another name, or none\n            x["ref"] = st.get("reference") or st.get("verse") or st.get("verse_ref")\n        if x.get("ref") not in refs and x.get("words"):\n            got = ref_of(str(x["words"]), refs, order)\n            if got:\n                x["ref"], x["ref_from"] = got, "words"\n        x["doubt"] = bool(x.get("doubt"))\n        x["check"] = check(x, refs, order)\n        out.append(x)\n    return out')

edit('scripts/vamsa_read.py', 7, '\n# --------------------------------------------------------------------------------------------- the lines\ndef longest_lines(statements: list, top: int = 5) -> list:\n    """The longest father-to-son lines of the verified son_of statements: [[ancestor, ..., descendant]]."""\n    kids = {}\n    for s in statements:',
     '\n# --------------------------------------------------------------------------------------------- the lines\ndef persons(statements: list) -> dict:\n    """VAMSA_HEAL_2026_11_11: the persons of the verified son_of statements, homonyms kept apart. A person is a name and\n    the father the text gives; his father is the person of that name who is a son in the same chapter or the one\n    before (the nearest before him, else the nearest after); when there is none, the father is a person of his own\n    (a root). A mother (a wife_of, daughter_of or sister_of in these statements) is not a father.\n    {key: {"name", "father", "up": key or None, "chapter", "ref", "words", "pos"}}"""\n    ver = [s for s in statements if s.get("check") == "verified"]\n    female = {letters(s.get("a")) for s in ver if s.get("rel") in ("wife_of", "daughter_of", "sister_of")}\n    sons = [s for s in ver if s.get("rel") == "son_of" and letters(s.get("b")) not in female\n            and letters(s.get("a")) and letters(s.get("b")) and letters(s.get("a")) != letters(s.get("b"))]\n    out = {}\n    for pos, s in enumerate(sons):\n        key = "%s|%s" % (letters(s["a"]), letters(s["b"]))\n        if key not in out:\n            out[key] = {"name": s["a"], "father": s["b"], "up": None, "chapter": s.get("chapter"), "ref": s.get("ref"),\n                        "words": s.get("words"), "pos": pos}\n    by_name = {}\n    for key, p in out.items():\n        by_name.setdefault(key.split("|")[0], []).append(key)\n    for key, p in out.items():\n        fk = letters(p["father"])\n        near = [k for k in by_name.get(fk, ()) if k != key and p["chapter"] is not None\n                and out[k]["chapter"] is not None and 0 <= p["chapter"] - out[k]["chapter"] <= 1]\n        if not near:\n            continue\n        before = [k for k in near if out[k]["pos"] < p["pos"]]\n        pick = max(before, key=lambda k: out[k]["pos"]) if before else min(near, key=lambda k: out[k]["pos"])\n        if pick != key:\n            p["up"] = pick\n    for key, p in out.items():   # no person his own ancestor\n        seen, k = {key}, p["up"]\n        while k:\n            if k in seen:\n                p["up"] = None\n                break\n            seen.add(k)\n            k = out[k]["up"]\n    return out\n\n\ndef lines_of(statements: list) -> list:\n    """VAMSA_HEAL_2026_11_11: the father-to-son lines of persons(), longest first: [[(name, ref, words), ...]], each\n    from a root (a father who is not a son here: his name and no verse) down to a person with no son here."""\n    ps = persons(statements)\n    kids = {}\n    for key, p in ps.items():\n        kids.setdefault(p["up"] or "root:" + letters(p["father"]), []).append(key)\n    memo = {}\n\n    def down(k):\n        if k not in memo:\n            best = []\n            for c in kids.get(k, ()):\n                got = down(c)\n                if len(got) > len(best):\n                    best = got\n            memo[k] = [k] + best\n        return memo[k]\n    roots = [k for k in kids if k.startswith("root:")]\n    out = []\n    for r in roots:\n        chain = down(r)\n        first = ps[chain[1]]["father"] if len(chain) > 1 else r[5:]\n        out.append([(first, None, None)] + [(ps[k]["name"], ps[k]["ref"], ps[k]["words"]) for k in chain[1:]])\n    return sorted(out, key=lambda x: (-len(x), letters(x[0][0])))\n\n\ndef longest_lines(statements: list, top: int = 5) -> list:\n    """The longest father-to-son lines (lines_of: homonyms kept apart): [[ancestor, ..., descendant]]."""\n    return [[n for n, _r, _w in ln] for ln in lines_of(statements)[:top] if len(ln) > 2]\n\n\ndef longest_lines_by_name(statements: list, top: int = 5) -> list:\n    """The first report\'s lines (before VAMSA_HEAL_2026_11_11): persons joined by their names alone, homonyms merged."""\n    kids = {}\n    for s in statements:')

edit('scripts/vamsa_read.py', 8, '        print("  %-6s %d part(s) read (%d not), %d statements: %s; $%.2f" % (\n            wk, len(recs) - errs, errs, len(st), ", ".join("%s %d" % kv for kv in sorted(by.items())), cost))\n        for ln in longest_lines(st):\n            print("         a line of %d: %s" % (len(ln), " > ".join(ln)))\n        p = ex / ("vamsa_read_%s.csv" % wk)\n        with open(p, "w", encoding="utf-8-sig", newline="") as f:',
     '        print("  %-6s %d part(s) read (%d not), %d statements: %s; $%.2f" % (\n            wk, len(recs) - errs, errs, len(st), ", ".join("%s %d" % kv for kv in sorted(by.items())), cost))\n        lines = lines_of(st)   # VAMSA_HEAL_2026_11_11: homonyms kept apart\n        for ln in lines[:5]:\n            if len(ln) > 2:\n                print("         a line of %d: %s" % (len(ln), " > ".join(n for n, _r, _w in ln)))\n        lp = Path(a.out) / ("%s_lines.json" % wk)\n        lp.parent.mkdir(parents=True, exist_ok=True)\n        lp.write_text(json.dumps({"mark": HEAL, "work": wk, "title": WORKS[wk]["title"], "lines": [\n            [{"name": n, "ref": r, "words": w} for n, r, w in ln] for ln in lines if len(ln) > 1]},\n            ensure_ascii=False, indent=1), encoding="utf-8")\n        lc = ex / ("vamsa_lines_%s.csv" % wk)\n        with open(lc, "w", encoding="utf-8-sig", newline="") as f:\n            wr = csv.writer(f)\n            wr.writerow(["line", "step", "name", "father", "ref", "words"])\n            for i, ln in enumerate(l for l in lines if len(l) > 1):\n                for j, (n, r, w) in enumerate(ln):\n                    wr.writerow([i + 1, j, n, ln[j - 1][0] if j else "", r or "", w or ""])\n        print("         wrote %s, %s (%d lines of 3 or more)" % (lp, lc, sum(1 for l in lines if len(l) > 2)))\n        p = ex / ("vamsa_read_%s.csv" % wk)\n        with open(p, "w", encoding="utf-8-sig", newline="") as f:')

edit('tests/test_vamsa_read_2026_11_11.py', 1, 'import claude_engine as CE   # noqa: E402\n\nMARK = "VAMSA_READ_2026_11_11"\nS, M = "\\u1e63", "\\u0101"    # s with dot below, a with macron\nIK, VI = "ik%sv%sku" % (S, M), "vikuk%si" % S',
     'import claude_engine as CE   # noqa: E402\n\nMARK = "VAMSA_READ_2026_11_11"   # and VAMSA_HEAL_2026_11_11\nS, M = "\\u1e63", "\\u0101"    # s with dot below, a with macron\nIK, VI = "ik%sv%sku" % (S, M), "vikuk%si" % S')

edit('tests/test_vamsa_read_2026_11_11.py', 2, '\n\nclass TheFile(unittest.TestCase):\n    def test_ascii_and_mark(self):',
     '\n\nclass TheHeal(unittest.TestCase):\n    """VAMSA_HEAL_2026_11_11: what the first run of 11 Nov showed."""\n\n    def test_a_reply_that_corrects_itself(self):\n        r = (\'{"statements": [{"ref": "R1", "a": "X", "rel": "son_of", "b": "Y", "words": "x"}]}\\n\\nCorrection: the \'\n             \'last is not valid. A corrected reply follows.\\n\\n{"statements": [{"ref": "R1", "a": "Z"}]}\')\n        self.assertEqual([s["a"] for s in VR.parse_reply(r)], ["Z"])\n        self.assertEqual(VR.parse_reply(r + \'\\n\\nFinal answer:\\n\\n{"statements": []}\'), [])\n        self.assertRaises(ValueError, VR.parse_reply, "no JSON here")\n        self.assertRaises(ValueError, VR.parse_reply, \'{"other": 1}\')\n\n    def test_a_statement_without_its_reference(self):\n        u = {"verses": [("R1", "mano\\u1e25 putra ik%sv%sku\\u1e25" % (S, M)), ("R2", "tasya putro vikuk%si\\u1e25" % S)]}\n        got = VR.checked([{"a": VI, "rel": "son_of", "b": IK, "words": "tasya putro vikuk%si\\u1e25" % S}], u)\n        self.assertEqual((got[0]["ref"], got[0].get("ref_from"), got[0]["check"]), ("R2", "words", "verified"))\n        got = VR.checked([{"verse": "R1", "a": IK, "rel": "son_of", "b": "Manu", "words": "putra ik%sv%sku" % (S, M)}], u)\n        self.assertEqual((got[0]["ref"], got[0]["check"]), ("R1", "verified"))\n\n    def test_sandhi_and_words_left_out(self):\n        L = VR.letters\n        v = "tato da\\u015b\\u0101rho n\\u0101mn\\u0101bh\\u016bt tasya vyoma\\u1e25 sutastata\\u1e25"\n        self.assertTrue(VR.words_in("tasya vyoma\\u1e25 suta\\u1e25", L(v)))\n        v2 = ("paurav\\u012b rohi\\u1e47\\u012b bhadr\\u0101 madir\\u0101 rocan\\u0101 il\\u0101 / devak\\u012bpramukh"\n              "\\u0101\\u015bc\\u0101san patnya \\u0101nakadundubhe\\u1e25")\n        self.assertTrue(VR.words_in("madir\\u0101 rocan\\u0101 ... patnya \\u0101nakadundubhe\\u1e25", L(v2)))\n        self.assertFalse(VR.words_in("patnya \\u0101nakadundubhe\\u1e25 ... madir\\u0101 rocan\\u0101", L(v2)), "in order")\n        self.assertFalse(VR.words_in("r\\u0101masya putra\\u1e25", L(v)))\n        self.assertFalse(VR.words_in("x", L(v)), "too short to tell")\n\n    def test_homonyms_kept_apart_and_a_mother_is_no_father(self):\n        sr = "S\\u1e5b\\u00f1jaya"\n        st = [dict(ref="R1", a="Dh\\u016bmr\\u0101k\\u1e63a", rel="son_of", b="Candra", check="verified", chapter=1),\n              dict(ref="R2", a=sr, rel="son_of", b="Dh\\u016bmr\\u0101k\\u1e63a", check="verified", chapter=1),\n              dict(ref="R3", a="Sahadeva", rel="son_of", b=sr, check="verified", chapter=1),\n              dict(ref="R9", a="Pura\\u00f1jaya", rel="son_of", b=sr, check="verified", chapter=19),\n              dict(ref="R10", a="\\u1e5ak\\u1e63a", rel="son_of", b="Pura\\u00f1jaya", check="verified", chapter=19),\n              dict(ref="R11", a="Pur\\u016bravas", rel="son_of", b="Il\\u0101", check="verified", chapter=1),\n              dict(ref="R12", a="Il\\u0101", rel="wife_of", b="Budha", check="verified", chapter=1),\n              dict(ref="R13", a="X", rel="son_of", b="Y", check="unsupported", chapter=1)]\n        lines = [[n for n, _r, _w in ln] for ln in VR.lines_of(st)]\n        self.assertEqual(lines[0], ["Candra", "Dh\\u016bmr\\u0101k\\u1e63a", sr, "Sahadeva"])\n        self.assertIn([sr, "Pura\\u00f1jaya", "\\u1e5ak\\u1e63a"], lines, "the Srnjaya of chapter 19 is another")\n        self.assertFalse(any("Il\\u0101" in ln for ln in lines), "a mother is not a father")\n        self.assertFalse(any("X" in ln for ln in lines), "only verified statements")\n        by_name = VR.longest_lines_by_name(st)\n        self.assertEqual(len(by_name[0]), 5, "the first report merged them: Candra > ... > Srnjaya > Puranjaya > Rksa")\n\n\nclass TheFile(unittest.TestCase):\n    def test_ascii_and_mark(self):')


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

