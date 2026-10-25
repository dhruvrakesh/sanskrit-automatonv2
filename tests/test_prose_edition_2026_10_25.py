# -*- coding: ascii -*-
"""PROSE_EDITION_2026_10_25: export_html.py --scholar --prose reads the scholarly edition as prose (the desk's
/scholar/<doc>/prose): no Sanskrit, the verse numbers small, a sentence over verses whole after its range, a paragraph
where a speaker begins, the chapter's notes at its end, the edition's own chapters and title page; publish_editions.py
writes it beside each edition (public/scholarly/<slug>-prose.html), each page's bar linking the other, the index giving
its file; "prose": false keeps it out; an unchanged prose is left as it is. Temp folders only; nothing is called."""
import json, re, subprocess, sys, tempfile, unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
SCRIPTS = REPO / "scripts"
sys.path.insert(0, str(SCRIPTS))
sys.path.insert(0, str(Path(__file__).resolve().parent))

MARK = b"PROSE_EDITION_2026_10_25"
APPLIED = MARK in (SCRIPTS / "export_html.py").read_bytes() and MARK in (SCRIPTS / "publish_editions.py").read_bytes()
TOOL = SCRIPTS / "publish_editions.py"


def export(db, out, *extra):
    return subprocess.run([sys.executable, str(SCRIPTS / "export_html.py"), "--db", str(db), "--doc", "Mark__w_gretil",
                           "--out", str(out), *extra], capture_output=True, text=True, cwd=str(REPO))


@unittest.skipUnless(APPLIED, "PROSE_EDITION_2026_10_25 is not applied here")
class TheProse(unittest.TestCase):
    def setUp(self):
        import test_edition_refs_2026_10_18 as TE
        self.TE = TE
        self.tmp = tempfile.TemporaryDirectory()
        self.td = Path(self.tmp.name)
        self.db = TE.fixture(self.td)

    def tearDown(self):
        self.tmp.cleanup()

    def test_the_edition_read_as_prose(self):
        r = export(self.db, self.td / "ex", "--scholar", "--prose", "--title", "Devimahatmya")
        self.assertEqual(r.returncode, 0, r.stderr)
        h = (self.td / "ex" / "Mark_w_gretil_1-3_scholar_prose.html").read_text(encoding="utf-8")
        self.assertIn("The scholarly English, read as prose", h)
        self.assertEqual(re.findall(r"<h2>(Adhy\u0101ya [^<]+)</h2>", h), ["Adhy\u0101ya 81", "Adhy\u0101ya 82"],
                         "the edition's own chapters")
        self.assertNotIn(self.TE.VERSE % 1, h, "no Sanskrit")
        self.assertNotIn(self.TE.ITI, h)
        self.assertEqual(h.count("<p class='prose'>"), 3, "81: two paragraphs (a speaker begins the second); 82: one")
        self.assertIn("<span class='vr'>3\u20134</span>Markandeya said: In the age", h, "a sentence whole after its range")
        self.assertNotIn("Its English is given with", h, "the verses after a sentence's first are not repeated")
        self.assertNotIn("<span class='sch-rng'>", h, "the range is the verse number, not a label")
        self.assertIn("<span class='vr'>1</span>Savarni<sup", h)
        self.assertIn("<p class='prose'>Markandeya said: <span class='vr'>1</span>", h, "a line without a reference has no number")
        self.assertIn("<em>Manu</em>", h)
        self.assertIn("<div class='footnotes'><ol>", h, "the notes at the chapter's end")
        self.assertIn("The progenitor of an age.", h)
        self.assertIn("p.prose .vr", h, "its own style")
        self.assertNotIn(" //", h)

    def test_the_verse_edition_is_as_it_was(self):
        r = export(self.db, self.td / "ex", "--scholar", "--sanskrit", "--side-by-side")
        self.assertEqual(r.returncode, 0, r.stderr)
        h = (self.td / "ex" / "Mark_w_gretil_1-3_scholar.html").read_text(encoding="utf-8")
        self.assertNotIn("<p class='prose'>", h)
        self.assertNotIn("p.prose", h)
        self.assertIn(self.TE.VERSE % 1, h)
        self.assertFalse((self.td / "ex" / "Mark_w_gretil_1-3_scholar_prose.html").exists())

    def test_prose_needs_the_scholarly_english(self):
        r = export(self.db, self.td / "ex", "--prose")
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("--prose reads the scholarly English", r.stderr)


@unittest.skipUnless(APPLIED and TOOL.exists(), "PROSE_EDITION_2026_10_25 is not applied here")
class ThePublisher(unittest.TestCase):
    def setUp(self):
        import test_edition_refs_2026_10_18 as TE
        import test_publish_editions_2026_10_18 as TP
        self.tmp = tempfile.TemporaryDirectory()
        t = self.t = Path(self.tmp.name)
        self.db = TE.fixture(t)
        self.site = t / "srangam"
        (self.site / "src").mkdir(parents=True)
        (self.site / "src" / "App.tsx").write_text("// the site\n", encoding="ascii")
        (self.site / "package.json").write_text("{}\n", encoding="ascii")
        self.reg = t / "source_verdicts.jsonl"
        self.reg.write_text(json.dumps({"doc": "Mark__w_gretil", "status": "released"}) + "\n", encoding="utf-8")
        self.cfg = t / "editions.json"
        self.entry = dict(TP.ENTRY)
        self.config([self.entry])

    def tearDown(self):
        self.tmp.cleanup()

    def config(self, entries):
        self.cfg.write_text(json.dumps({"site_repo": str(self.site), "editions": entries}), encoding="utf-8")

    def run_tool(self, *args):
        r = subprocess.run([sys.executable, str(TOOL), "--config", str(self.cfg), "--db", str(self.db),
                            "--verdicts", str(self.reg)] + list(args), capture_output=True, text=True, cwd=str(REPO))
        return r.returncode, r.stdout + r.stderr

    def out(self, name):
        return self.site / "public" / "scholarly" / name

    def test_each_edition_beside_its_prose(self):
        rc, out = self.run_tool()
        self.assertEqual(rc, 0, out)
        self.assertIn("VERDICT: 3 file(s) to write", out, "the edition, its prose and the index")
        self.assertIn("as prose", out)
        rc, out = self.run_tool("--apply")
        self.assertEqual(rc, 0, out)
        v = self.out("devi.html").read_text(encoding="utf-8")
        p = self.out("devi-prose.html").read_text(encoding="utf-8")
        self.assertIn("<a href='/scholarly/devi-prose.html'>Read it as prose</a>", v)
        self.assertIn("<a href='/scholarly/devi.html'>The verses, beside the Sanskrit</a>", p)
        self.assertIn("<link rel='canonical' href='https://srangam.nartiang.org/scholarly/devi-prose.html'/>", p)
        self.assertIn("<b>The Sanskrit:</b>", p, "its credits")
        self.assertIn("<b>Licence of this edition:</b>", p)
        self.assertIn("<p class='prose'>", p)
        e = json.loads(self.out("index.json").read_text(encoding="utf-8"))["editions"][0]
        self.assertEqual(e["prose"], "/scholarly/devi-prose.html")
        self.assertEqual(e["prose_bytes"], len(p.encode("utf-8")))
        self.assertEqual(len(e["prose_sha256"]), 64)
        self.assertEqual((e["verses"], e["passed"]), (7, 7), "the counts are the edition's")
        rc, out = self.run_tool("--apply")
        self.assertEqual(rc, 0, out)
        self.assertIn("VERDICT: nothing to write", out)
        self.assertEqual(out.count("unchanged"), 2, "the edition and its prose")

    def test_prose_false_keeps_it_out(self):
        self.config([dict(self.entry, prose=False)])
        rc, out = self.run_tool("--apply")
        self.assertEqual(rc, 0, out)
        self.assertFalse(self.out("devi-prose.html").exists())
        self.assertNotIn("Read it as prose", self.out("devi.html").read_text(encoding="utf-8"))
        e = json.loads(self.out("index.json").read_text(encoding="utf-8"))["editions"][0]
        self.assertNotIn("prose", e)


class TheFiles(unittest.TestCase):
    def test_ascii_and_marks(self):
        for f in (TOOL, Path(__file__)):
            if not f.exists():
                self.skipTest("not here")
            b = f.read_bytes()
            self.assertTrue(all(x < 128 for x in b), f.name)
        if APPLIED:
            self.assertIn(MARK, TOOL.read_bytes())


if __name__ == "__main__":
    unittest.main()
