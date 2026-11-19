# -*- coding: ascii -*-
"""VAMSA_FINDINGS_SITE_2026_11_19 (C31): our findings on the vamsa page. index_sync.findings_for (only the approved, only
without problems; each citation resolved from what the site carries; B. C. Law by page only; a citation that cannot be
resolved left out); vamsa_rows carries them, and without them its rows are as before; the findings wait until the site
says it takes them (the hashes as C29 keeps them), then go; vamsa_findings --report's NEXT; C31 as pasted; the Srangam
kit's payload and its patch on made-up checkouts; the automaton patch replays once. Nothing is called."""
import hashlib, importlib.util, io, json, os, re, sys, tempfile, unittest
from contextlib import redirect_stdout
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "scripts"))
MARK = "VAMSA_FINDINGS_SITE_2026_11_19"
C31 = REPO / "docs" / "cloud" / "C31_vamsa_findings_2026-11-19.sql"
C29 = REPO / "docs" / "cloud" / "C29_index_vamsas_2026-11-18.sql"
KIT = REPO / "docs" / "srangam" / "VAMSA_FINDINGS_SITE_2026-11-19"
SPAT = REPO / "scripts" / "patch_srangam_vamsa_findings_site_2026_11_19.py"
APAT = REPO / "scripts" / "patch_vamsa_findings_site_2026_11_19.py"


def load(path, name):
    spec = importlib.util.spec_from_file_location(name, str(path))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def applied():
    return MARK in (REPO / "scripts" / "index_sync.py").read_text(encoding="ascii")


GENS = [
    {"gen": 0, "status": "agree", "name": "Kuru", "cells": {
        "hv": {"name": "Kuru", "ref": "HV 23.107", "words": "kuruh samvaranat", "line": 3},
        "agni": {"name": "Kuru", "ref": "AgP 277.26", "words": "kuruh samvaranat"}},
     "pui": {"person": "pui:19737", "head": "Kuru (II)", "index": "", "page": True}},
    {"gen": 1, "status": "differ", "name": "Jahnu", "cells": {"vip4": {"name": "Jahnu", "ref": "ViP 4,19.78"}},
     "pui": {"person": "pui:21593", "head": "Jahnu", "index": "agrees"}},
]
CLAIM_OF = {"phai1923:22:19": {"key": "phai1923:22:19", "work": "phai1923", "printed": "4", "pdf_page": 22,
                               "claim": "The Visnu Purana gives names of Kuru princes."}}
FINDINGS = {"mark": "VAMSA_FINDINGS_2026_11_19", "dynasty": "kuru", "prompt_version": "vamsa-findings-v2",
            "model": "claude-sonnet-5-5", "at": "2026-11-19T12:53:05",
            "ids": {"l:8044": {"kind": "law", "page": "97"}, "r:phai1923:22:19": {"kind": "raychaudhuri", "page": "4"}},
            "findings": [
                {"n": 1, "kind": "agreement", "text": "Kuru was the son of Samvarana.", "status": "approved",
                 "reviewed_at": "2026-11-19T15:10:00", "problems": [], "warnings": [],
                 "cites": ["g:0", "v:hv:HV 23.107", "v:agni:AgP 277.26", "pi:19737", "l:8044", "r:phai1923:22:19",
                           "g:0", "pi:99999", "r:phai1923:99:9", "v:zz:ZZ 1.1", "a:mbh1:MBh 1,90.45", "x:1", 7]},
                {"n": 2, "kind": "disagreement", "text": "dropped by a person", "status": "dropped", "cites": ["g:1"]},
                {"n": 3, "kind": "open_question", "text": "still proposed", "status": "proposed", "cites": ["g:1"]},
                {"n": 4, "kind": "agreement", "text": "approved but with a problem", "status": "approved",
                 "problems": ["cites g:9, not in what it read"], "cites": ["g:1"]},
                {"n": 5, "kind": "agreement", "text": None, "status": "approved", "cites": []}]}


@unittest.skipUnless(applied(), "VAMSA_FINDINGS_SITE is not applied here")
class TheFindings(unittest.TestCase):
    def setUp(self):
        import index_sync as ix
        self.ix = ix
        self.td = tempfile.TemporaryDirectory()
        (Path(self.td.name) / "kuru.json").write_text(json.dumps(FINDINGS), encoding="utf-8")
        self.said = ix.said_names
        ix.said_names = lambda d, w: [("Paryasravas", "Pratipa", "MBh 1,90.45", "yam ahuh pratipam nama")] if w == "mbh1" else []
        self.out = ix.findings_for(self.td.name, "kuru", GENS, CLAIM_OF, "somewhere")

    def tearDown(self):
        self.ix.said_names = self.said
        self.td.cleanup()

    def test_only_the_approved_without_problems(self):
        self.assertEqual([f["n"] for f in self.out], [1])
        f = self.out[0]
        self.assertEqual((f["model"], f["prompt"], f["read_at"], f["approved_at"]),
                         ("claude-sonnet-5-5", "vamsa-findings-v2", "2026-11-19T12:53:05", "2026-11-19T15:10:00"))

    def test_each_citation_resolved_or_left_out(self):
        c = self.out[0]["cites"]
        self.assertEqual(c[0], {"t": "gen", "gen": 0, "name": "Kuru"})
        self.assertEqual(c[1], {"t": "verse", "work": "hv", "ref": "HV 23.107", "gen": 0, "name": "Kuru",
                                "words": "kuruh samvaranat", "line": 3})
        self.assertEqual(c[2], {"t": "verse", "work": "agni", "ref": "AgP 277.26", "gen": 0, "name": "Kuru",
                                "words": "kuruh samvaranat"})
        self.assertEqual(c[3], {"t": "index", "person": "pui:19737", "head": "Kuru (II)", "page": True})
        self.assertEqual(c[4], {"t": "law", "page": "97"})
        self.assertEqual(c[5], {"t": "ray", "key": "phai1923:22:19", "printed": "4", "pdf_page": 22,
                                "claim": "The Visnu Purana gives names of Kuru princes."})
        self.assertEqual(c[6], {"t": "verse", "work": "zz", "ref": "ZZ 1.1"})
        self.assertEqual(c[7], {"t": "second", "work": "mbh1", "ref": "MBh 1,90.45", "name": "Paryasravas",
                                "other": "Pratipa", "words": "yam ahuh pratipam nama"})
        self.assertEqual(len(c), 8, "the repeated g:0, the unknown pi and r, x:1 and 7 left out")

    def test_law_by_page_only(self):
        law = [c for c in self.out[0]["cites"] if c["t"] == "law"]
        self.assertEqual(law, [{"t": "law", "page": "97"}])
        self.assertNotIn("claim", json.dumps(law))

    def test_none_without_the_folder_or_the_file(self):
        self.assertEqual(self.ix.findings_for("", "kuru", GENS, CLAIM_OF), [])
        self.assertEqual(self.ix.findings_for(self.td.name, "solar", GENS, CLAIM_OF), [])
        (Path(self.td.name) / "bad.json").write_text("{not json", encoding="utf-8")
        self.assertEqual(self.ix.findings_for(self.td.name, "bad", GENS, CLAIM_OF), [])


ALIGNED = {"mark": "VAMSA_ALIGN_2026_11_17", "at": "2026-11-17T23:34:37", "dynasties": [
    {"slug": "kuru", "anchor": "Kuru", "father": "Samvarana", "title": "the Kurus from Kuru", "order": ["hv"],
     "counts": {"agree": 1}, "rows": [
         {"gen": 0, "status": "agree", "name": "Kuru", "n": 1, "cells": {
             "hv": {"name": "Kuru", "ref": "HV 23.107", "words": "kuruh samvaranat"}}}]},
    {"slug": "solar", "anchor": "Iksvaku", "father": "Manu", "title": "the solar line", "order": ["hv"],
     "counts": {"one": 1}, "rows": [
         {"gen": 0, "status": "one", "name": "Iksvaku", "n": 1, "cells": {"hv": {"name": "Iksvaku", "ref": "HV 10.1"}}}]}]}


@unittest.skipUnless(applied(), "VAMSA_FINDINGS_SITE is not applied here")
class TheRows(unittest.TestCase):
    def test_carried_and_without_them_as_before(self):
        import index_sync as ix
        with tempfile.TemporaryDirectory() as rd, tempfile.TemporaryDirectory() as fd:
            (Path(rd) / "aligned.json").write_text(json.dumps(ALIGNED), encoding="utf-8")
            (Path(fd) / "kuru.json").write_text(json.dumps(FINDINGS), encoding="utf-8")
            plain = ix.vamsa_rows(rd, [], {}, {}, [], {}, {})
            withf = ix.vamsa_rows(rd, [], {}, {}, [], {}, {}, findings_dir=fd)
        by_p, by_w = {r["key"]: r for r in plain}, {r["key"]: r for r in withf}
        self.assertNotIn("findings", by_p["kuru"]); self.assertNotIn("findings", by_w["solar"])
        self.assertEqual([f["n"] for f in by_w["kuru"]["findings"]], [1])
        self.assertEqual(by_w["solar"]["row_hash"], by_p["solar"]["row_hash"], "no approved finding: the row as before")
        self.assertNotEqual(by_w["kuru"]["row_hash"], by_p["kuru"]["row_hash"])
        back = ix.without_findings({"vamsas": withf})["vamsas"]
        self.assertEqual([r["row_hash"] for r in back], [r["row_hash"] for r in plain], "C29's hashes, exactly")


@unittest.skipUnless(applied(), "VAMSA_FINDINGS_SITE is not applied here")
class TheSend(unittest.TestCase):
    class Sink:
        def __init__(self, man):
            self.man, self.got = man, {}

        def manifest(self):
            return self.man

        def keys(self, t):
            return {}

        def ingest(self, t, rows):
            self.got.setdefault(t, []).extend(rows)
            return {"changed": len(rows)}

        def delete(self, t, keys):
            return {"deleted": 0}

    def rows(self, ix):
        r = {t: [] for t in ix.TABLES}
        r["vamsas"] = [ix.finish({"key": "kuru", "vamsa": "candra", "findings": [{"n": 1, "text": "x", "cites": []}]}),
                       ix.finish({"key": "solar", "vamsa": "surya"})]
        r["meta"] = [ix.finish({"key": "run", "value": {}})]
        return r

    def man(self, ix, **features):
        m = {t: {"n": 0, "digest": ix.digest([])} for t in ix.TABLES}
        m["features"] = dict({"aliases": True, "vamsas": True}, **features)
        return m

    def test_wait_until_the_site_takes_them(self):
        import index_sync as ix
        s = self.Sink(self.man(ix))
        got = ix.sync(self.rows(ix), s, apply=True, log=lambda *a: None)
        self.assertIn(ix.FINDINGS_FEATURE, got["features_waiting"])
        self.assertFalse(any("findings" in r for r in s.got["vamsas"]))

    def test_go_once_it_does(self):
        import index_sync as ix
        s = self.Sink(self.man(ix, vamsa_findings=True))
        got = ix.sync(self.rows(ix), s, apply=True, log=lambda *a: None)
        self.assertNotIn(ix.FINDINGS_FEATURE, got["features_waiting"])
        self.assertEqual([r["key"] for r in s.got["vamsas"] if "findings" in r], ["kuru"])

    def test_nothing_waits_when_none_is_approved(self):
        import index_sync as ix
        r = self.rows(ix)
        r["vamsas"] = [ix.finish({"key": "solar", "vamsa": "surya"})]
        got = ix.sync(r, self.Sink(self.man(ix)), apply=False, log=lambda *a: None)
        self.assertNotIn(ix.FINDINGS_FEATURE, got["features_waiting"])


@unittest.skipUnless(applied(), "VAMSA_FINDINGS_SITE is not applied here")
class TheReport(unittest.TestCase):
    def test_next_once_all_decided(self):
        import vamsa_findings as vf
        with tempfile.TemporaryDirectory() as out, tempfile.TemporaryDirectory() as ex:
            first = dict(FINDINGS["findings"][0], cites=[c for c in FINDINGS["findings"][0]["cites"] if isinstance(c, str)])
            d = dict(FINDINGS, findings=[first, dict(FINDINGS["findings"][1])])
            (Path(out) / "kuru.json").write_text(json.dumps(d), encoding="utf-8")
            a = type("A", (), {"out": out, "exports": ex})()
            buf = io.StringIO()
            with redirect_stdout(buf):
                vf.do_report(a, ["kuru"])
        self.assertIn("NEXT: python scripts\\index_sync.py --dynasty-works every   (the plan: 1 approved finding(s) for the site)",
                      buf.getvalue())


class TheSql(unittest.TestCase):
    def setUp(self):
        self.s = C31.read_text(encoding="ascii")

    def test_one_change_its_checks_its_rollback(self):
        s = self.s
        self.assertEqual(s.count("\nBEGIN;\n"), 1); self.assertEqual(s.count("\nCOMMIT;\n"), 1)
        ch = s[s.index("\nBEGIN;\n"):s.index("\nCOMMIT;\n")]
        for k in ("ADD COLUMN IF NOT EXISTS findings JSONB NOT NULL DEFAULT '[]'::jsonb",
                  "RENAME TO corpus_index_ingest_c29", "RENAME TO corpus_index_manifest_c29",
                  "RETURN corpus.corpus_index_ingest_c29(p_table, p_rows);", "PERFORM corpus._reader_gate();",
                  "jsonb_build_object('vamsa_findings', true)", "findings = excluded.findings",
                  "GRANT EXECUTE ON FUNCTION %s TO authenticated", "GRANT EXECUTE ON FUNCTION %s TO service_role"):
            self.assertIn(k, ch, k)
        for w in ("DELETE ", "DROP TABLE", "TRUNCATE", "UPDATE corpus"):
            self.assertNotIn(w, ch, w)
        self.assertNotIn("corpus_reader_index_vamsas", ch, "C29's reader is not changed")
        for k in ("-- B1", "-- A1", "-- A2", "-- A3", "DROP FUNCTION IF EXISTS public.corpus_reader_index_vamsa_findings();",
                  "ALTER TABLE corpus.index_vamsas DROP COLUMN IF EXISTS findings;"):
            self.assertIn(k, s, k)
        rb = [l for l in s.splitlines() if re.match(r"^--   (DROP|ALTER)", l)]
        self.assertEqual(len(rb), 8)

    def test_the_columns_the_desk_sends(self):
        cols = re.search(r"AS x\(([^)]*)\)", self.s).group(1)
        names = [c.split()[0] for c in cols.replace("\n", " ").split(",")]
        c29 = re.search(r"AS x\(([^)]*)\)", C29.read_text(encoding="ascii")).group(1)
        old = [c.split()[0] for c in c29.replace("\n", " ").split(",")]
        self.assertEqual(sorted(names), sorted(old + ["findings"]))


class TheKit(unittest.TestCase):
    def test_the_page_and_the_lib(self):
        lib = (KIT / "src/lib/indexSite.ts").read_text(encoding="utf-8")
        page = (KIT / "src/pages/corpus/CorpusVamsas.tsx").read_text(encoding="utf-8")
        for k in (MARK, "corpus_reader_index_vamsa_findings", "export function findingCiteText",
                  "In copyright: read on the desk and never quoted here", "export function findingMade", "term: 'Our findings'"):
            self.assertIn(k, lib, k)
        law = lib[lib.index("default: {", lib.index("export function findingCiteText")):]
        law = law[:law.index("\n    }\n")]
        self.assertNotIn("claim", law.replace("const page = (c as { page?: string }).page;", ""), "Law: the page only")
        for k in (MARK, "loadVamsaFindings", "Our findings (", "genAnchor(k, g.gen)", "staleTime: 10 * 60 * 1000"):
            self.assertIn(k, page, k)
        for bad in ("dangerouslySetInnerHTML", ".insert(", ".update(", ".delete("):
            self.assertNotIn(bad, page + lib, bad)
        a = (KIT / "_append/RELIABILITY_AUDIT.phaseAW.md").read_text(encoding="utf-8")
        self.assertTrue(a.startswith("## Phase AW - ")); self.assertIn("73. A finding reaches the vamsa page", a)
        self.assertTrue((KIT / "src/__tests__/vamsa-findings.test.tsx").exists())


@unittest.skipUnless(SPAT.exists(), "the Srangam patch is not here")
class TheSrangamPatch(unittest.TestCase):
    def setUp(self):
        self.mod = load(SPAT, "pat_findingssite")
        self.td = tempfile.TemporaryDirectory(); self.t = Path(self.td.name)
        (self.t / "package.json").write_text("{}", encoding="ascii")
        (self.t / "src/lib").mkdir(parents=True)
        (self.t / "src/App.tsx").write_text("// ADMIN_STATUS_2026_11_19\n", encoding="ascii")
        self.fake = {}
        for rel in self.mod.REPLACE:
            p = self.t / rel; p.parent.mkdir(parents=True, exist_ok=True)
            b = ("// %s as main had it\n" % rel).encode("ascii"); p.write_bytes(b); self.fake[rel] = b
        (self.t / "docs").mkdir()
        (self.t / "docs/RELIABILITY_AUDIT.md").write_bytes(b"# Audit\r\n\r\n## Phase AV - x (ADMIN_STATUS_2026_11_19)\r\n")
        self.mod.REPLACE = {rel: hashlib.md5(b).hexdigest() for rel, b in self.fake.items()}

    def tearDown(self):
        self.td.cleanup()

    def run_main(self, *a):
        old_cwd, old_argv, buf = os.getcwd(), sys.argv, io.StringIO()
        try:
            os.chdir(str(self.t)); sys.argv = ["x"] + list(a)
            with redirect_stdout(buf):
                rc = self.mod.main()
        finally:
            os.chdir(old_cwd); sys.argv = old_argv
        return rc, buf.getvalue()

    def test_applies_once(self):
        rc, out = self.run_main("--check"); self.assertIn("CHECK OK: 4 file(s)", out)
        rc, out = self.run_main(); self.assertEqual(rc, 0, out)
        for rel in ("src/lib/indexSite.ts", "src/pages/corpus/CorpusVamsas.tsx", "src/__tests__/vamsa-findings.test.tsx"):
            self.assertEqual((self.t / rel).read_bytes(), (KIT / rel).read_bytes(), rel)
        audit = (self.t / "docs/RELIABILITY_AUDIT.md").read_bytes()
        self.assertEqual(audit.count(b"## Phase AW - "), 1); self.assertNotIn(b"\n", audit.replace(b"\r\n", b""), "CRLF kept")
        rc, out = self.run_main(); self.assertIn("Nothing to do", out)

    def test_refuses_a_changed_file(self):
        (self.t / "src/lib/indexSite.ts").write_bytes(self.fake["src/lib/indexSite.ts"] + b"// changed\n")
        rc, out = self.run_main(); self.assertEqual(rc, 1); self.assertIn("REFUSE", out)
        self.assertEqual((self.t / "src/pages/corpus/CorpusVamsas.tsx").read_bytes(),
                         self.fake["src/pages/corpus/CorpusVamsas.tsx"], "all or nothing")


@unittest.skipUnless(APAT.exists(), "the patch is not here")
class TheAutomatonPatch(unittest.TestCase):
    def test_replays_once(self):
        files = load(APAT, "pat_files").FILES
        with tempfile.TemporaryDirectory() as t:
            t = Path(t)
            for rel in files:
                p = REPO / rel
                bak = sorted(p.parent.glob(p.name + ".bak_findingssite_*"))
                if not bak:
                    self.skipTest("only patched copies to replay against")
                (t / rel).parent.mkdir(parents=True, exist_ok=True)
                (t / rel).write_bytes(bak[0].read_bytes())
            old = os.getcwd(); buf = io.StringIO()
            try:
                os.chdir(str(t)); sys.argv = ["x"]
                with redirect_stdout(buf):
                    load(APAT, "pat_a").main()
                    load(APAT, "pat_b").main()
            finally:
                os.chdir(old)
            self.assertIn("Nothing to do", buf.getvalue())
            marks = lambda b: set(re.findall(rb"[A-Z][A-Z0-9_]*_20\d\d_\d\d_\d\d", b))
            for rel in files:
                now, got = (REPO / rel).read_bytes(), (t / rel).read_bytes()
                self.assertIn(MARK.encode(), got, rel)
                if marks(now) == marks(got):   # a later patch adds its own mark: then only the replay itself is checked
                    self.assertEqual(got.replace(b"\r\n", b"\n"), now.replace(b"\r\n", b"\n"), rel)


class TheFiles(unittest.TestCase):
    def test_ascii_and_marks(self):
        for f, m in ((SPAT, MARK), (APAT, MARK), (C31, "C31_VAMSA_FINDINGS_2026_11_19"), (Path(__file__), MARK)):
            if f.exists():
                b = f.read_bytes()
                self.assertTrue(all(x < 128 for x in b), f.name)
                self.assertIn(m.encode(), b, f.name)


if __name__ == "__main__":
    unittest.main()
