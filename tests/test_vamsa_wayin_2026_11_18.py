# -*- coding: ascii -*-
"""VAMSA_WAYIN_2026_11_18 (P2c): the way in by vamsa. vamsa_align.vamsa_of; index_sync.vamsa_rows (each work's name tied
to its line, Dikshitar's person, Raychaudhuri's claims the site carries, never one it does not); _entity_claims (one
candidate only, the site's claims only); the table waits until the site has it, then goes; C29 as pasted; the Srangam
kit's payload and its patch (made-up checkouts in temp folders); the automaton patch replays once. Nothing is called."""
import hashlib, importlib.util, io, json, os, re, sqlite3, sys, tempfile, unittest
from contextlib import redirect_stdout
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "scripts"))
MARK = "VAMSA_WAYIN_2026_11_18"
C29 = REPO / "docs" / "cloud" / "C29_index_vamsas_2026-11-18.sql"
C28 = REPO / "docs" / "cloud" / "C28_index_dynasties_2026-11-11.sql"
KIT = REPO / "docs" / "srangam" / "VAMSA_WAYIN_2026-11-18"
SPAT = REPO / "scripts" / "patch_srangam_vamsa_wayin_2026_11_18.py"
APAT = REPO / "scripts" / "patch_vamsa_wayin_2026_11_18.py"


def load(path, name):
    spec = importlib.util.spec_from_file_location(name, str(path))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def applied():
    return MARK in (REPO / "scripts" / "index_sync.py").read_text(encoding="ascii")


ALIGNED = {"mark": "VAMSA_ALIGN_2026_11_17", "at": "2026-11-17T23:34:37", "dynasties": [
    {"slug": "kuru", "anchor": "Kuru", "father": "Samvarana", "title": "the Kurus from Kuru", "order": ["hv", "agni", "zz"],
     "counts": {"agree": 1, "most": 0, "differ": 1, "one": 1, "share_agree": 0.5},
     "rows": [
         {"gen": 0, "status": "agree", "name": "Kuru", "n": 2, "cells": {
             "hv": {"name": "Kuru", "ref": "HV 23.107", "words": "kuruh samvaranat"},
             "agni": {"name": "Kuru", "ref": "AgP 277.26", "words": "kuruh samvaranat"}}},
         {"gen": 1, "status": "differ", "name": "Parikshit", "n": 2, "cells": {
             "hv": {"name": "Parikshit", "ref": "HV 23.109"},
             "agni": {"name": "Pariksit", "ref": "AgP 277.30"}}},
         {"gen": 2, "status": "one", "name": "Janamejaya", "n": 1, "cells": {
             "zz": {"name": "Janamejaya", "ref": "ZZ 1.1"}}}]},
    {"slug": "solar", "anchor": "Iksvaku", "father": "Manu", "title": "the solar line", "order": ["hv"],
     "counts": {"agree": 0, "most": 0, "differ": 0, "one": 1}, "rows": [
         {"gen": 0, "status": "one", "name": "Iksvaku", "n": 1, "cells": {"hv": {"name": "Iksvaku", "ref": "HV 10.1"}}}]}]}
DYN = [
    {"key": "hv:3", "work": "hv", "n": 3, "steps": [
        {"name": "Kuru", "ref": "HV 23.107", "person": "pui:10", "index_head": "Kuru (II)", "index": ""},
        {"name": "Parikshit", "ref": "HV 23.109", "person": "pui:11", "index_head": "Pariksit (I)", "index": "agrees"}]},
    {"key": "agni:2", "work": "agni", "n": 2, "steps": [
        {"name": "Kuru", "ref": "AgP 277.26", "person": "pui:10", "index_head": "Kuru (II)", "index": ""},
        {"name": "Pariksit", "ref": "AgP 277.30", "person": "pui:12", "index_head": "Pariksit (II)", "index": "differs"}]},
    {"key": "hv:9", "work": "hv", "n": 9, "steps": [{"name": "Iksvaku", "ref": "HV 10.1"}]},
]
CLAIMS = [{"key": "phai1923:%d:1" % p, "work": "phai1923", "printed": str(p - 3), "pdf_page": p, "claim": "claim %d" % p}
          for p in (20, 21, 22, 23, 24)]
G = {"entity_of": {("pui", 10): 100, ("pui", 11): 101, ("pui", 12): 102}}


@unittest.skipUnless(applied(), "VAMSA_WAYIN is not applied here")
class TheRows(unittest.TestCase):
    def setUp(self):
        import index_sync as ix
        self.ix = ix
        self.td = tempfile.TemporaryDirectory()
        (Path(self.td.name) / "aligned.json").write_text(json.dumps(ALIGNED), encoding="utf-8")
        ent = {100: [c["key"] for c in CLAIMS], 101: ["phai1923:20:1", "phai1923:99:9"]}
        pair = {(100, 101): ["phai1923:21:1", "phai1923:99:9"]}
        self.rows = ix.vamsa_rows(self.td.name, DYN, G, {"pui:10": "Kuru", "pui:11": None}, CLAIMS, pair, ent)
        self.by = {r["key"]: r for r in self.rows}

    def tearDown(self):
        self.td.cleanup()

    def test_vamsa_of(self):
        import vamsa_align as VA
        self.assertEqual([VA.vamsa_of(s) for s in ("solar", "videha", "lunar", "kuru", "magadha", "x")],
                         ["surya", "surya", "candra", "candra", "candra", ""])
        self.assertEqual({a[0] for a in VA.ANCHORS} - set(VA.SURYA), {a[0] for a in VA.ANCHORS if VA.vamsa_of(a[0]) == "candra"})

    def test_a_row_a_dynasty(self):
        k = self.by["kuru"]
        self.assertEqual((k["vamsa"], k["anchor"], k["works"], k["aligned_at"]), ("candra", "Kuru", ["hv", "agni", "zz"],
                                                                                 "2026-11-17T23:34:37"))
        self.assertEqual(self.by["solar"]["vamsa"], "surya")
        self.assertLess(self.by["solar"]["ord"], k["ord"], "the founders' order")
        self.assertEqual(k["names"], ["Janamejaya", "Kuru", "Parikshit", "Pariksit"])
        self.assertIn("row_hash", k)

    def test_names_to_their_lines(self):
        g0, g1, g2 = self.by["kuru"]["rows"]
        self.assertEqual((g0["cells"]["hv"]["line"], g0["cells"]["agni"]["line"]), (3, 2))
        self.assertEqual(g1["cells"]["agni"]["line"], 2)
        self.assertNotIn("line", g2["cells"]["zz"], "a work not sent has no line")
        self.assertEqual(g0["cells"]["hv"]["words"], "kuruh samvaranat")

    def test_dikshitar(self):
        g0, g1, g2 = self.by["kuru"]["rows"]
        self.assertEqual(g0["pui"], {"person": "pui:10", "head": "Kuru (II)", "index": "", "page": True})
        self.assertEqual(g0["canonical"], "Kuru")
        self.assertEqual(g1["pui"]["person"], "pui:11", "a tie: the smaller key, as sorted")
        self.assertTrue(g1["pui"]["page"]) ; self.assertNotIn("canonical", g1, "no name on the site: no link")
        self.assertNotIn("pui", g2)

    def test_raychaudhuri_only_what_the_site_carries(self):
        g0, g1, _g2 = self.by["kuru"]["rows"]
        self.assertEqual(g0["ray_name_n"], 5)
        self.assertNotIn("ray", g0, "the founder: no step before him")
        self.assertEqual(g1["ray_name_n"], 1, "phai1923:99:9 is not on the site")
        self.assertEqual(g1["ray_n"], 1)
        self.assertEqual(g1["ray"], [{"key": "phai1923:21:1", "work": "phai1923", "printed": "18", "pdf_page": 21,
                                      "claim": "claim 21"}])
        txt = json.dumps(self.rows)
        self.assertNotIn("law1926", txt)

    def test_at_most_ray_shown(self):
        pair = {(100, 101): [c["key"] for c in CLAIMS]}
        rows = self.ix.vamsa_rows(self.td.name, DYN, G, {}, CLAIMS, pair, {})
        g1 = rows[0]["rows"][1]
        self.assertEqual((g1["ray_n"], len(g1["ray"])), (5, self.ix.RAY_SHOWN))
        self.assertNotIn("page", g1["pui"])

    def test_none_without_g6c(self):
        with tempfile.TemporaryDirectory() as t:
            self.assertEqual(self.ix.vamsa_rows(t, DYN, G, {}, CLAIMS, {}, {}), [])


@unittest.skipUnless(applied(), "VAMSA_WAYIN is not applied here")
class TheClaimsOfAnEntity(unittest.TestCase):
    def test_one_candidate_and_the_site_only(self):
        import index_sync as ix
        with tempfile.TemporaryDirectory() as t:
            p = Path(t) / "claims.db"
            con = sqlite3.connect(str(p))
            con.executescript("""
                CREATE TABLE claims(id INTEGER PRIMARY KEY, work TEXT, pdf_page INTEGER, n INTEGER);
                CREATE TABLE claim_links(claim_id INTEGER, role TEXT, entity_id INTEGER, cands INTEGER);
                INSERT INTO claims VALUES (1, 'phai1923', 30, 1), (2, 'phai1923', 30, 2), (3, 'law1926', 5, 1),
                                          (4, 'phai1923', 10, 4);
                INSERT INTO claim_links VALUES (1, 'subject', 7, 1), (2, 'object', 7, 2), (3, 'subject', 7, 1),
                                               (4, 'object', 7, 1), (4, 'subject', 8, 1), (1, 'note', 9, 1);""")
            con.commit(); con.close()
            on = {"phai1923:30:1", "phai1923:30:2", "phai1923:10:4"}
            got = ix._entity_claims(str(p), on)
            self.assertEqual(got, {7: ["phai1923:10:4", "phai1923:30:1"], 8: ["phai1923:10:4"]})
            self.assertEqual(ix._entity_claims(str(p), set()), {})
            self.assertEqual(ix._entity_claims(str(Path(t) / "none.db"), on), {})


@unittest.skipUnless(applied(), "VAMSA_WAYIN is not applied here")
class TheSend(unittest.TestCase):
    class Sink:
        def __init__(self, ix, man):
            self.ix, self.man, self.got = ix, man, {}

        def manifest(self):
            return self.man

        def keys(self, t):
            return {}

        def ingest(self, t, rows):
            self.got.setdefault(t, []).extend(r["key"] for r in rows)
            return {"changed": len(rows)}

        def delete(self, t, keys):
            return {"deleted": 0}

    def rows(self, ix):
        r = {t: [] for t in ix.TABLES}
        r["vamsas"] = [ix.finish({"key": "kuru", "vamsa": "candra"}), ix.finish({"key": "solar", "vamsa": "surya"})]
        r["meta"] = [ix.finish({"key": "run", "value": {}})]
        return r

    def test_the_table_and_its_place(self):
        import index_sync as ix
        self.assertIn("vamsas", ix.TABLES); self.assertIn("vamsas", ix.OPTIONAL)
        self.assertEqual(ix.TABLES[-1], "meta"); self.assertEqual(ix.TABLES[-2], "vamsas")

    def test_waits_until_the_site_has_it(self):
        import index_sync as ix
        man = {t: {"n": 0, "digest": ix.digest([])} for t in ix.TABLES if t != "vamsas"}
        man["features"] = {"aliases": True}
        s = self.Sink(ix, man)
        got = ix.sync(self.rows(ix), s, apply=True, log=lambda *a: None)
        self.assertIn("vamsas", got["waiting"]); self.assertNotIn("vamsas", s.got)

    def test_goes_once_it_has(self):
        import index_sync as ix
        man = {t: {"n": 0, "digest": ix.digest([])} for t in ix.TABLES}
        man["features"] = {"aliases": True, "vamsas": True}
        s = self.Sink(ix, man)
        got = ix.sync(self.rows(ix), s, apply=True, log=lambda *a: None)
        self.assertEqual(sorted(s.got["vamsas"]), ["kuru", "solar"])
        self.assertNotIn("vamsas", got["waiting"])


class TheSql(unittest.TestCase):
    def setUp(self):
        self.s = C29.read_text(encoding="ascii")

    def test_one_change_its_checks_its_rollback(self):
        s = self.s
        self.assertEqual(s.count("\nBEGIN;\n"), 1); self.assertEqual(s.count("\nCOMMIT;\n"), 1)
        for k in ("-- B1", "-- A1", "-- A2", "-- A3", "-- Rollback", "DROP TABLE IF EXISTS corpus.index_vamsas;",
                  "corpus.corpus_index_ingest_c28", "corpus.corpus_index_manifest_c28", "PERFORM corpus._reader_gate();",
                  "GRANT EXECUTE ON FUNCTION %s TO authenticated", "ENABLE ROW LEVEL SECURITY",
                  "CASE WHEN p_key IS NULL THEN '[]'::jsonb ELSE v.rows END", "jsonb_build_object('vamsas', true)"):
            self.assertIn(k, s, k)
        self.assertEqual(s.count("$$") % 2, 0)

    def test_index_rel_keeps_every_table(self):
        rel = lambda txt: re.findall(r"WHEN '([a-z]+)' THEN '(corpus\.index_[a-z]+)'::regclass", txt)
        old, new = rel(C28.read_text(encoding="ascii")), rel(self.s)
        self.assertEqual(new[:-1], old); self.assertEqual(new[-1], ("vamsas", "corpus.index_vamsas"))

    def test_the_columns_the_desk_sends(self):
        cols = re.search(r"AS x\(([^)]*)\)", self.s).group(1)
        names = [c.split()[0] for c in cols.replace("\n", " ").split(",")]
        self.assertEqual(names, ["key", "vamsa", "ord", "anchor", "father", "title", "works", "counts", "rows", "names",
                                 "aligned_at", "row_hash"])


class TheKit(unittest.TestCase):
    def test_tables_alike(self):
        lib = (KIT / "supabase/functions/corpus-index/lib.ts").read_text(encoding="utf-8")
        ts = re.findall(r'"([a-z]+)"', re.search(r"export const TABLES = \[([^\]]*)\]", lib).group(1))
        if applied():
            import index_sync as ix
            self.assertEqual(tuple(ts), ix.TABLES)
        self.assertEqual(ts[-2:], ["vamsas", "meta"])

    def test_the_page(self):
        page = (KIT / "src/pages/corpus/CorpusVamsas.tsx").read_text(encoding="utf-8")
        for k in (MARK, "loadVamsas(null)", "loadVamsas(k)", "queryKey: ['index-vamsas']", "queryKey: ['index-vamsa', k]",
                  "CorpusGate", "CorpusRefused", "The va\u1e43\u015bas are not switched on yet", "dynastyLineHref(w, c.line)",
                  "nameHrefOf(g.canonical)", "dynastyPersonHref", "foldPlain", "title={tip}"):
            self.assertIn(k, page, k)
        self.assertNotIn("dangerouslySetInnerHTML", page)
        self.assertNotIn("law1926", page)
        app = (KIT / "src/App.tsx").read_text(encoding="utf-8")
        self.assertIn('<Route path="/corpus/genealogies/vamsas" element={<CorpusVamsas />} />', app)
        dyn = (KIT / "src/pages/corpus/CorpusDynasties.tsx").read_text(encoding="utf-8")
        for k in ("useSearchParams", "params.get('line')", "id={`line-${l.n}`}", "typeof el.scrollIntoView === 'function'"):
            self.assertIn(k, dyn, k)
        lib = (KIT / "src/lib/indexSite.ts").read_text(encoding="utf-8")
        self.assertIn("return list<VamsaRow>('corpus_reader_index_vamsas', { p_key: key });", lib)
        self.assertIn("DYNASTIES_WORKS_2026_11_18", lib, "built on the kit before")
        a = (KIT / "_append/RELIABILITY_AUDIT.phaseAU.md").read_text(encoding="utf-8")
        self.assertTrue(a.startswith("## Phase AU - ")); self.assertIn("71. The vamsa page asks", a)
        self.assertTrue((KIT / "src/__tests__/vamsas.test.tsx").exists())


@unittest.skipUnless(SPAT.exists(), "the Srangam patch is not here")
class TheSrangamPatch(unittest.TestCase):
    def setUp(self):
        self.td = tempfile.TemporaryDirectory()
        self.t = Path(self.td.name)
        self.mod = load(SPAT, "pat_vamsawayin")
        (self.t / "package.json").write_text("{}", encoding="ascii")
        self.fake = {}
        for rel in self.mod.REPLACE:
            p = self.t / rel
            p.parent.mkdir(parents=True, exist_ok=True)
            body = "// %s as main had it, DYNASTIES_WORKS_2026_11_18\n" % rel
            p.write_bytes(body.encode("ascii"))
            self.fake[rel] = body.encode("ascii")
        (self.t / "docs").mkdir()
        (self.t / "docs/RELIABILITY_AUDIT.md").write_bytes(b"# Audit\n\n## Phase AT - x (DYNASTIES_WORKS_2026_11_18)\n")
        self.mod.REPLACE = {rel: hashlib.md5(b).hexdigest() for rel, b in self.fake.items()}

    def tearDown(self):
        self.td.cleanup()

    def run_main(self, *a):
        old_cwd, old_argv = os.getcwd(), sys.argv
        buf = io.StringIO()
        try:
            os.chdir(str(self.t)); sys.argv = ["x"] + list(a)
            with redirect_stdout(buf):
                rc = self.mod.main()
        finally:
            os.chdir(old_cwd); sys.argv = old_argv
        return rc, buf.getvalue()

    def test_applies_once(self):
        rc, out = self.run_main("--check")
        self.assertEqual(rc, 0, out); self.assertIn("CHECK OK: 8 file(s)", out)
        rc, out = self.run_main()
        self.assertEqual(rc, 0, out)
        page = "src/pages/corpus/CorpusVamsas.tsx"
        self.assertEqual((self.t / page).read_bytes(), (KIT / page).read_bytes())
        self.assertTrue(list((self.t / "src/App.tsx").parent.glob("App.tsx.bak_vamsawayin_*")))
        self.assertEqual((self.t / "docs/RELIABILITY_AUDIT.md").read_text(encoding="utf-8").count("## Phase AU - "), 1)
        rc, out = self.run_main()
        self.assertIn("Nothing to do", out)

    def test_refuses_a_changed_file(self):
        (self.t / "src/App.tsx").write_bytes(self.fake["src/App.tsx"] + b"// changed\n")
        rc, out = self.run_main()
        self.assertEqual(rc, 1); self.assertIn("REFUSE", out)
        self.assertEqual((self.t / "src/lib/indexSite.ts").read_bytes(), self.fake["src/lib/indexSite.ts"], "all or nothing")
        self.assertFalse((self.t / "src/pages/corpus/CorpusVamsas.tsx").exists())


@unittest.skipUnless(APAT.exists(), "the patch is not here")
class TheAutomatonPatch(unittest.TestCase):
    def test_replays_once(self):
        files = load(APAT, "pat_files").FILES
        with tempfile.TemporaryDirectory() as t:
            t = Path(t)
            for rel in files:
                p = REPO / rel
                bak = sorted(p.parent.glob(p.name + ".bak_vamsawayin_*"))
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
            for rel in files:
                self.assertEqual((t / rel).read_bytes().replace(b"\r\n", b"\n"),
                                 (REPO / rel).read_bytes().replace(b"\r\n", b"\n"), rel)


class TheFiles(unittest.TestCase):
    def test_ascii_and_marks(self):
        for f in (SPAT, APAT, C29, Path(__file__)):
            if f.exists():
                b = f.read_bytes()
                self.assertTrue(all(x < 128 for x in b), f.name)
                self.assertIn(MARK.encode() if f != C29 else b"C29_INDEX_VAMSAS_2026_11_18", b, f.name)


if __name__ == "__main__":
    unittest.main()
