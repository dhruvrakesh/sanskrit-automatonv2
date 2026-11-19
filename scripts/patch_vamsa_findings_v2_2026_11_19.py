#!/usr/bin/env python3
# -*- coding: ascii -*-
"""

patch_vamsa_findings_v2_2026_11_19.py  (2026-11-19)  VAMSA_FINDINGS_V2_2026_11_19

R1's prompt v2, from the trial of 19 Nov (kuru, $0.038: five findings, all passing the checks; read by hand, two named
texts they did not cite, one called a Mahabharata king "different" where the text itself says he is Pratipa, one said
Law "only" names a son, one called the critical edition a "translation"):
  scripts/vamsa_findings.py   the pack gives each text's title (vamsa_read.work_of) and the second names the texts
                              themselves state for this dynasty's kings (vamsa_align.aliases_said: MBh 1,90.45,
                              Paryasravas "whom they call Pratipa"); the prompt adds three rules (a text named only by its
                              title and only when one of its verses is cited; no "only" or "never" of a scholar; a second
                              name is one person); each finding carries warnings (a text named, none of its verses cited),
                              shown on the review page, never a refusal; PROMPT_VERSION vamsa-findings-v2 (a dynasty read
                              with v1 is read again by "--dynasty all --yes")
  tests/test_vamsa_findings_2026_11_19.py   the titles, the second names, the warnings, the rules
No model is called by the patch or the tests.

Anchored edits, all or nothing; a file that already carries the marker is skipped; .bak_findingsv2_<date> copies.

  python scripts\\patch_vamsa_findings_v2_2026_11_19.py --check
  python scripts\\patch_vamsa_findings_v2_2026_11_19.py
"""
from __future__ import annotations
import argparse, datetime, os, py_compile, shutil, sys, tempfile
from pathlib import Path

MARK = 'VAMSA_FINDINGS_V2_2026_11_19'
TAG = 'findingsv2'
FILES = ['scripts/vamsa_findings.py', 'tests/test_vamsa_findings_2026_11_19.py']
NEEDS = {'scripts/vamsa_findings.py': 'VAMSA_FINDINGS_2026_11_19', 'tests/test_vamsa_findings_2026_11_19.py': 'VAMSA_FINDINGS_2026_11_19'}
REQUIRES = {}   # another file that must carry a marker first
E = []


def edit(f, n, old, new):
    E.append((f, n, old, new))


edit('scripts/vamsa_findings.py', 1, '\nMARK = "VAMSA_FINDINGS_2026_11_19"\nPROMPT_VERSION = "vamsa-findings-v1"\nROOT = Path(__file__).resolve().parents[1]\nsys.path.insert(0, str(ROOT / "scripts"))',
     '\nMARK = "VAMSA_FINDINGS_2026_11_19"\nPROMPT_VERSION = "vamsa-findings-v2"   # VAMSA_FINDINGS_V2_2026_11_19: the texts\' titles, their second names, three rules\nROOT = Path(__file__).resolve().parents[1]\nsys.path.insert(0, str(ROOT / "scripts"))')

edit('scripts/vamsa_findings.py', 2, 'SOURCE_KIND = {"g": "text", "v": "text", "pi": "index", "r": "raychaudhuri", "l": "law"}\nLAW_WORK, RAY_WORK = "law1926", "phai1923"\nLAW_CREDIT = "B. C. Law, Ancient Indian Tribes (Lahore, 1926)"\nRAY_CREDIT = "H. C. Raychaudhuri, Political History of Ancient India (Calcutta, 1923)"',
     'SOURCE_KIND = {"g": "text", "v": "text", "pi": "index", "r": "raychaudhuri", "l": "law"}\nLAW_WORK, RAY_WORK = "law1926", "phai1923"\n# VAMSA_FINDINGS_V2_2026_11_19: a finding that names a text but cites none of its verses is shown with a warning (the\n# trial of 19 Nov named the Garuda and the Brahma without a verse of either); the names as a finding writes them, folded\nTEXT_NAMES = (\n    ("visnu", r"\\bvisnu", ("vip4", "vipc4")), ("bhagavata", r"\\bbhagavata", ("bhp9", "bhp12")),\n    ("matsya", r"\\bmatsya", ("matsya",)), ("garuda", r"\\bgaruda", ("garuda1",)), ("agni", r"\\bagni\\b", ("agni",)),\n    ("brahma", r"\\bbrahma\\b(?! ?nda)", ("brahma",)), ("brahmanda", r"\\bbrahma ?nda", ("bndp1", "bndp2")),\n    ("harivamsa", r"\\bharivamsa", ("hv",)), ("ramayana", r"\\bramayana", ("ram1", "ram2")),\n    ("mahabharata", r"\\bmahabharata|\\badiparvan", ("mbh1",)), ("linga", r"\\blinga", ("linga1",)),\n    ("kurma", r"\\bkurma", ("kurma1",)), ("markandeya", r"\\bmarkandeya", ("markp",)))\nLAW_CREDIT = "B. C. Law, Ancient Indian Tribes (Lahore, 1926)"\nRAY_CREDIT = "H. C. Raychaudhuri, Political History of Ancient India (Calcutta, 1923)"')

edit('scripts/vamsa_findings.py', 3, "Cite every source a finding rests on by its id, and nothing that is not in the pack. Never copy Law's wording:\nparaphrase him (at most a few words in quotation marks). State no date, place or fact that the pack does not give.\n\nReply with JSON only, no prose before or after:",
     'Cite every source a finding rests on by its id, and nothing that is not in the pack. Never copy Law\'s wording:\nparaphrase him (at most a few words in quotation marks). State no date, place or fact that the pack does not give.\nName a text only by the title the pack gives it, and only when you cite at least one of its verses. The pack holds some\nof each scholar\'s claims, not all: never say that a scholar "only" or "never" says something. Where a text says that a\nking is also called by another name (a:WORK:REF), the two names are one person: that is not a difference between texts.\n\nReply with JSON only, no prose before or after:')

edit('scripts/vamsa_findings.py', 4, '    names = rv._names(db)["ents"]\n    lby, lof = law_claims(claims_db, immutable)\n    return {"vamsas": vam, "entity_of": g.get("entity_of") or {},\n            "canon": {e: v[0] for e, v in names.items()}, "claim_of": {c["key"]: c for c in claims},\n            "ray_by_ent": ent, "law_by_ent": lby, "law_of": lof}',
     '    names = rv._names(db)["ents"]\n    lby, lof = law_claims(claims_db, immutable)\n    import vamsa_align as VA\n    import vamsa_read as VR\n    here = VA.works_here(vamsa_read_dir)   # VAMSA_FINDINGS_V2_2026_11_19: the titles, the second names\n    aliases = {w: VA.aliases_said(VA.statements_of(vamsa_read_dir, w)) for w in here}\n    titles = {w: VR.work_of(w)["title"] for w in here}\n    return {"aliases": aliases, "titles": titles, "vamsas": vam, "entity_of": g.get("entity_of") or {},\n            "canon": {e: v[0] for e, v in names.items()}, "claim_of": {c["key"]: c for c in claims},\n            "ray_by_ent": ent, "law_by_ent": lby, "law_of": lof}')

edit('scripts/vamsa_findings.py', 5, '            ids[vid] = {"kind": "text"}\n            lines.append("  %s %s: %s" % (vid, cell.get("name") or "", (cell.get("words") or "")[:WORDS_MAX]))\n    canon = inp.get("canon") or {}\n',
     '            ids[vid] = {"kind": "text"}\n            lines.append("  %s %s: %s" % (vid, cell.get("name") or "", (cell.get("words") or "")[:WORDS_MAX]))\n    # VAMSA_FINDINGS_V2_2026_11_19: the second names the texts themselves state (vamsa_align.aliases_said), for the\n    # names of this dynasty in that text only (MBh 1,90.45: Paryasravas, "whom they call Pratipa")\n    import vamsa_align as VA\n    said = []\n    for wk, al in sorted((inp.get("aliases") or {}).items()):\n        here = {VA.nkey(c.get("name")) for gen in v.get("rows") or [] for w2, c in (gen.get("cells") or {}).items()\n                if w2 == wk}\n        for _ch, keep, other, ref, wds in al:\n            if ref and (VA.nkey(keep) in here or VA.nkey(other) in here):\n                aid = "a:%s:%s" % (wk, ref)\n                if aid not in ids:\n                    ids[aid] = {"kind": "text"}\n                    said.append("%s %s is also called %s: %s" % (aid, keep, other, (wds or "")[:WORDS_MAX]))\n    if said:\n        lines += ["", "SECOND NAMES THE TEXTS STATE (one person, two names)"] + said\n    titles = inp.get("titles") or {}\n    if titles:\n        lines += ["", "THE TEXTS: " + "; ".join("%s = %s" % (w, titles[w]) for w in (v.get("works") or []) if w in titles)]\n    canon = inp.get("canon") or {}\n')

edit('scripts/vamsa_findings.py', 6, '\n\ndef checked(raw: list, ids: dict, law_grams: set, before=None) -> list:\n    """The findings numbered, each with its problems and status; a person\'s decision on the same text is kept."""',
     '\n\ndef warnings(f: dict) -> list:\n    """VAMSA_FINDINGS_V2_2026_11_19: what a person should look at before approving: a text the finding names whose\n    verses it does not cite. Shown, never a refusal (a god Agni or Brahma is not the Purana of that name)."""\n    if not isinstance(f.get("text"), str):\n        return []\n    t = " ".join(words(f["text"]))\n    cited = {c.split(":")[1] for c in (f.get("cites") or []) if isinstance(c, str) and c.startswith(("v:", "a:"))\n             and c.count(":") >= 2}\n    return ["names the %s but cites none of its verses" % name for name, rx, works_ in TEXT_NAMES\n            if re.search(rx, t) and not cited & set(works_)]\n\n\ndef checked(raw: list, ids: dict, law_grams: set, before=None) -> list:\n    """The findings numbered, each with its problems and status; a person\'s decision on the same text is kept."""')

edit('scripts/vamsa_findings.py', 7, '        p = problems(f, ids, law_grams)\n        x = {"n": n, "kind": f.get("kind"), "text": (f.get("text") or "").strip(), "cites": f.get("cites") or [],\n             "problems": p, "status": "refused" if p else "proposed"}\n        b = kept.get(x["text"])\n        if b and not p:',
     '        p = problems(f, ids, law_grams)\n        x = {"n": n, "kind": f.get("kind"), "text": (f.get("text") or "").strip(), "cites": f.get("cites") or [],\n             "problems": p, "warnings": warnings(f), "status": "refused" if p else "proposed"}\n        b = kept.get(x["text"])\n        if b and not p:')

edit('scripts/vamsa_findings.py', 8, '            n_prop += pr\n            n_ref += len(fs) - pr\n            print("  [%d/%d] %s: %d finding(s), %d proposed, %d refused by the checks, $%.4f%s"\n                  % (i, len(todo), p["key"], len(fs), pr, len(fs) - pr, cost,\n                     ("  (%s)" % rec["error"][:100]) if rec.get("error") else ""), flush=True)\n        say("%d dynasty(ies) read, %d finding(s) proposed, %d refused; $%.3f spent of the Claude credit"',
     '            n_prop += pr\n            n_ref += len(fs) - pr\n            print("  [%d/%d] %s: %d finding(s), %d proposed (%d with a warning), %d refused by the checks, $%.4f%s"\n                  % (i, len(todo), p["key"], len(fs), pr, sum(1 for f in fs if f.get("warnings") and f["status"] != "refused"),\n                     len(fs) - pr, cost,\n                     ("  (%s)" % rec["error"][:100]) if rec.get("error") else ""), flush=True)\n        say("%d dynasty(ies) read, %d finding(s) proposed, %d refused; $%.3f spent of the Claude credit"')

edit('scripts/vamsa_findings.py', 9, '            if f.get("problems"):\n                lines.append("   - checks: %s" % "; ".join(f["problems"]))\n            lines.append("")\n        print("  %-8s %s" % (key, ", ".join("%d %s" % (sum(1 for f in d.get("findings") or [] if f["status"] == s), s)',
     '            if f.get("problems"):\n                lines.append("   - checks: %s" % "; ".join(f["problems"]))\n            if f.get("warnings"):\n                lines.append("   - look before approving: %s" % "; ".join(f["warnings"]))\n            lines.append("")\n        print("  %-8s %s" % (key, ", ".join("%d %s" % (sum(1 for f in d.get("findings") or [] if f["status"] == s), s)')

edit('tests/test_vamsa_findings_2026_11_19.py', 1, '\n\nclass TheGuards(unittest.TestCase):\n    def test_refuses_without_the_alignment(self):',
     '\n\nclass TheV2(unittest.TestCase):\n    """VAMSA_FINDINGS_V2_2026_11_19: the texts\' titles and second names in the pack; the warnings; the three rules."""\n    def test_titles_and_second_names(self):\n        inp = dict(INP, titles={"hv": "Harivamsa", "agni": "Agnipurana"},\n                   aliases={"hv": [(23, "Parikshit", "Pariksita", "HV 23.111", "yam ahuh pariksitam")],\n                            "agni": [(1, "Somebody", "Else", "AgP 1.1", "words")]})\n        p = F.pack_of(VAM, inp)\n        self.assertIn("a:hv:HV 23.111 Parikshit is also called Pariksita: yam ahuh pariksitam", p["text"])\n        self.assertEqual(p["ids"]["a:hv:HV 23.111"], {"kind": "text"})\n        self.assertNotIn("a:agni:AgP 1.1", p["ids"], "a second name of no one in this dynasty")\n        self.assertIn("THE TEXTS: hv = Harivamsa; agni = Agnipurana", p["text"])\n        self.assertNotIn("SECOND NAMES", F.pack_of(VAM, INP)["text"])\n\n    def test_warnings(self):\n        w = F.warnings({"text": "The Garuda and the Harivamsa make Kuru the son of Samvarana.", "cites": ["v:hv:HV 23.107"]})\n        self.assertEqual(w, ["names the garuda but cites none of its verses"])\n        self.assertEqual(F.warnings({"text": "The Brahmanda says so.", "cites": ["v:bndp2:BndP 2.3"]}), [])\n        self.assertEqual(F.warnings({"text": "The Brahmanda says so.", "cites": ["g:0"]}),\n                         ["names the brahmanda but cites none of its verses"])\n        self.assertEqual(F.warnings({"text": "The Visnu Purana, book 4, agrees.", "cites": ["a:vipc4:ViPc 4,20.3"]}), [])\n        fs = F.checked([{"kind": "agreement", "text": "The Garuda and the Harivamsa make Kuru the son of Samvarana.",\n                         "cites": ["v:hv:HV 23.107", "pi:10"]}], F.pack_of(VAM, INP)["ids"], set())\n        self.assertEqual((fs[0]["status"], len(fs[0]["warnings"])), ("proposed", 1), "a warning is not a refusal")\n\n    def test_the_rules(self):\n        self.assertEqual(F.PROMPT_VERSION, "vamsa-findings-v2")\n        for k in ("only when you cite at least one of its verses", \'never say that a scholar "only" or "never"\',\n                  "the two names are one person"):\n            self.assertIn(k, F.SYSTEM, k)\n\n\nclass TheGuards(unittest.TestCase):\n    def test_refuses_without_the_alignment(self):')


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

