# -*- coding: ascii -*-
"""DYNASTIES_WORKS_2026_11_18 (P2b): the Srangam kit by which the Dynasties page asks for one work's lines at a time,
lists the 17 works the desk reads, and finds a name typed in plain letters by the desk's own rule. The patch writes only
over the version main had, keeps line endings, backs up, appends Phase AT once, refuses a changed file and runs once.
Made-up checkouts in temp folders; nothing is called."""
import hashlib, importlib.util, io, os, sys, tempfile, unittest
from contextlib import redirect_stdout
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
PAT = REPO / "scripts" / "patch_srangam_dynasties_works_2026_11_18.py"
KIT = REPO / "docs" / "srangam" / "DYNASTIES_WORKS_2026-11-18"
MARK = "DYNASTIES_WORKS_2026_11_18"
PAGE = "src/pages/corpus/CorpusDynasties.tsx"
LIB = "src/lib/indexSite.ts"
OLD = "src/__tests__/dynasties.test.tsx"
NEW = "src/__tests__/dynasties-works.test.tsx"
sys.path.insert(0, str(REPO / "scripts"))


def patcher():
    spec = importlib.util.spec_from_file_location("pat_dynworks", str(PAT))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


class ThePayload(unittest.TestCase):
    def test_one_work_at_a_time(self):
        page = (KIT / PAGE).read_text(encoding="utf-8")
        self.assertIn(MARK, page)
        self.assertIn("loadDynasties(w)", page)
        self.assertNotIn("loadDynasties(null)", page)
        self.assertIn("queryKey: ['index-dynasties', w]", page)
        self.assertIn("foldPlain(find)", page)
        self.assertIn("No dynasty of this text has been sent from the desk yet.", page)
        for kept in ("CorpusGate", "CorpusRefused", "dynastyCountsText", "The dynasties are not switched on yet"):
            self.assertIn(kept, page, kept)

    def test_the_17_works_and_the_rule(self):
        import vamsa_read as VR
        lib = (KIT / LIB).read_text(encoding="utf-8")
        self.assertIn("export function foldPlain(", lib)
        self.assertIn("export function foldName(", lib, "foldName as before")
        for w in list(VR.WORKS) + [w for w in VR.G6_WORKS if w not in VR.WORKS]:
            self.assertIn("'%s'" % w, lib.split("export const WORK_ORDER")[1].split("];")[0], w)
        for pair in (("sh", "s"), ("ch", "c"), ("aa", "a"), ("ii", "i"), ("uu", "u"), ("ri", "r"), ("w", "v")):
            self.assertIn("['%s', '%s']" % pair, lib, pair)

    def test_the_tests_and_the_audit(self):
        old = (KIT / OLD).read_text(encoding="utf-8")
        self.assertIn("{ p_work: 'vip4' }", old)
        new = (KIT / NEW).read_text(encoding="utf-8")
        self.assertIn("expect(asked()).toEqual(['vip4', 'hv'])", new)
        a = (KIT / "_append/RELIABILITY_AUDIT.phaseAT.md").read_text(encoding="utf-8")
        self.assertTrue(a.startswith("## Phase AT - "))
        self.assertIn("70. The Dynasties page asks the database for one work's lines at a time", a)


@unittest.skipUnless(PAT.exists(), "the patch is not here")
class ThePatch(unittest.TestCase):
    def setUp(self):
        self.td = tempfile.TemporaryDirectory()
        self.t = Path(self.td.name)
        self.mod = patcher()
        (self.t / "package.json").write_text("{}", encoding="ascii")
        self.fake = {}
        for rel in (LIB, PAGE, OLD):
            p = self.t / rel
            p.parent.mkdir(parents=True, exist_ok=True)
            body = "// %s as main had it\nexport function loadDynasties(work) {}\n" % rel
            p.write_bytes(body.encode("ascii"))
            self.fake[rel] = body.encode("ascii")
        (self.t / "docs").mkdir()
        (self.t / "docs/RELIABILITY_AUDIT.md").write_bytes(b"# Audit\n\n## Phase AS - x (AI_GATEWAY_OFF_2026_11_17)\n")
        self.mod.REPLACE = {rel: hashlib.md5(b.replace(b"\r\n", b"\n")).hexdigest() for rel, b in self.fake.items()}

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
        self.assertEqual(rc, 0, out); self.assertIn("CHECK OK: 5 file(s)", out)
        rc, out = self.run_main()
        self.assertEqual(rc, 0, out)
        self.assertEqual((self.t / PAGE).read_bytes(), (KIT / PAGE).read_bytes().replace(b"\r\n", b"\n"))
        self.assertTrue((self.t / NEW).exists())
        self.assertTrue(list((self.t / PAGE).parent.glob("CorpusDynasties.tsx.bak_dynworks_*")))
        audit = (self.t / "docs/RELIABILITY_AUDIT.md").read_text(encoding="utf-8")
        self.assertEqual(audit.count("## Phase AT - "), 1)
        rc, out = self.run_main()
        self.assertIn("Nothing to do", out)

    def test_refuses_a_changed_file(self):
        changed = self.fake[PAGE] + b"// changed\n"
        (self.t / PAGE).write_bytes(changed)
        rc, out = self.run_main()
        self.assertEqual(rc, 1); self.assertIn("REFUSE", out)
        self.assertEqual((self.t / LIB).read_bytes(), self.fake[LIB], "all or nothing")
        self.assertFalse((self.t / NEW).exists())


class TheFiles(unittest.TestCase):
    def test_ascii_and_marks(self):
        for f in (PAT, Path(__file__)):
            b = f.read_bytes()
            self.assertTrue(all(x < 128 for x in b), f.name)
            self.assertIn(MARK.encode(), b, f.name)


if __name__ == "__main__":
    unittest.main()
