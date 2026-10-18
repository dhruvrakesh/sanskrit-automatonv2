# -*- coding: ascii -*-
"""EDITIONS_SITE_2026_10_18: publish_editions.py writes the scholarly editions named in configs/editions.json into the
Srangam repo (public/scholarly/<slug>.html and index.json): the edition as export_html.py --scholar makes it, with a bar
back to /editions, its credits and licence and its canonical address; the plan writes nothing; an unchanged edition is
left as it is; a text held in repair, a witness without its source and licence, a bad slug and an edition turned off
are not published. Temp folders only; nothing is called (no network, no git)."""
import json, subprocess, sys, tempfile, unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
SCRIPTS = REPO / "scripts"
sys.path.insert(0, str(SCRIPTS))
sys.path.insert(0, str(Path(__file__).resolve().parent))

TOOL = SCRIPTS / "publish_editions.py"
MARK = b"EDITIONS_SITE_2026_10_18"
REFS = b"EDITION_REFS_2026_10_18" in (SCRIPTS / "export_html.py").read_bytes()

GRETIL = {"name": "Markandeyapurana 1-93, GRETIL", "url": "https://gretil.sub.uni-goettingen.de/gretil/x.htm",
          "credit": "data entry by members of the Sansknet Project", "licence": "CC BY-NC-SA 4.0",
          "licence_url": "https://creativecommons.org/licenses/by-nc-sa/4.0/"}
ENTRY = {"slug": "devi", "doc": "Mark__w_gretil", "pages": [1, 3], "title": "Devimahatmya", "subtitle": "adhyayas 81 to 82",
         "audit": ", audited", "source": GRETIL, "english_licence": {"name": "CC BY-NC-SA 4.0",
                                                                     "url": "https://creativecommons.org/licenses/by-nc-sa/4.0/"}}


@unittest.skipUnless(REFS and TOOL.exists(), "EDITIONS_SITE_2026_10_18 is not here")
class ThePublisher(unittest.TestCase):
    def setUp(self):
        import test_edition_refs_2026_10_18 as TE
        self.tmp = tempfile.TemporaryDirectory()
        t = self.t = Path(self.tmp.name)
        self.db = TE.fixture(t)
        self.site = t / "srangam"
        (self.site / "src").mkdir(parents=True)
        (self.site / "src" / "App.tsx").write_text("// the site\n", encoding="ascii")
        (self.site / "package.json").write_text("{}\n", encoding="ascii")
        self.reg = t / "source_verdicts.jsonl"
        self.reg.write_text(json.dumps({"doc": "Mark__w_gretil", "status": "witness", "of": "Mark"}) + "\n", encoding="utf-8")
        self.cfg = t / "editions.json"
        self.config([ENTRY])

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

    def test_the_plan_writes_nothing(self):
        rc, out = self.run_tool()
        self.assertEqual(rc, 0, out)
        self.assertIn("devi", out); self.assertIn("new", out)
        self.assertIn("VERDICT: 2 file(s) to write", out)
        self.assertIn("NEXT: python scripts\\publish_editions.py --apply", out)
        self.assertFalse((self.site / "public").exists())

    def test_apply_writes_the_edition_and_its_index(self):
        rc, out = self.run_tool("--apply")
        self.assertEqual(rc, 0, out)
        h = self.out("devi.html").read_text(encoding="utf-8")
        self.assertIn("<a href='/editions'>&larr; Srangam: the scholarly editions</a>", h)
        self.assertIn("<link rel='canonical' href='https://srangam.nartiang.org/scholarly/devi.html'/>", h)
        self.assertIn("<b>The Sanskrit:</b> <a href='https://gretil.sub.uni-goettingen.de/gretil/x.htm' rel='noopener'>"
                      "Markandeyapurana 1-93, GRETIL</a>; data entry by members of the Sansknet Project. "
                      "<a href='https://creativecommons.org/licenses/by-nc-sa/4.0/' rel='noopener'>CC BY-NC-SA 4.0</a>", h)
        self.assertIn("made by Claude Sonnet 5.5, read by a critic and revised, judged verse by verse by Gemini 2.5 Flash, "
                      "audited.", h)
        self.assertIn("<b>Licence of this edition:</b>", h)
        self.assertIn("<h2>Adhy\u0101ya 81</h2>", h, "the edition itself, with its chapters")
        self.assertLess(h.index("class='credits'"), h.index("class='methodology'"))
        idx = json.loads(self.out("index.json").read_text(encoding="utf-8"))
        e = idx["editions"][0]
        self.assertEqual((e["slug"], e["file"], e["doc"], e["pages"]), ("devi", "/scholarly/devi.html", "Mark__w_gretil", [1, 3]))
        self.assertEqual((e["verses"], e["passed"], e["flagged"]), (7, 7, 0))
        self.assertEqual(e["source"]["licence"], "CC BY-NC-SA 4.0")
        self.assertTrue(e["made_at"])
        self.assertIn("wrote", out)
        self.assertIn("git add -- public/scholarly", out)
        # again: nothing changed, nothing written, the date kept
        rc, out = self.run_tool("--apply")
        self.assertEqual(rc, 0, out)
        self.assertIn("unchanged", out); self.assertIn("VERDICT: nothing to write", out)
        self.assertEqual(json.loads(self.out("index.json").read_text(encoding="utf-8"))["editions"][0]["made_at"], e["made_at"])

    def test_refused_and_off(self):
        self.reg.write_text(json.dumps({"doc": "Mark__w_gretil", "status": "in_repair"}) + "\n", encoding="utf-8")
        rc, out = self.run_tool("--apply")
        self.assertIn("REFUSED devi: the register holds Mark__w_gretil (in_repair): not for the site", out)
        self.assertFalse(self.out("devi.html").exists())
        self.reg.write_text("", encoding="utf-8")
        self.config([dict(ENTRY, source={})])
        rc, out = self.run_tool("--apply")
        self.assertIn("REFUSED devi: a witness (an e-text) needs its source and licence in the entry", out)
        self.config([dict(ENTRY, slug="Bad Slug")])
        rc, out = self.run_tool()
        self.assertIn("slug: lower-case letters, digits and hyphens", out)
        self.config([dict(ENTRY, enabled=False, why_off="not yet")])
        rc, out = self.run_tool("--apply")
        self.assertIn("devi                   off (not yet)", out)
        self.assertFalse(self.out("devi.html").exists())

    def test_not_the_site(self):
        self.config([ENTRY])
        r = subprocess.run([sys.executable, str(TOOL), "--config", str(self.cfg), "--db", str(self.db), "--site", str(self.t)],
                           capture_output=True, text=True, cwd=str(REPO))
        self.assertEqual(r.returncode, 1)
        self.assertIn("is not the Srangam repo", r.stdout)


class TheFiles(unittest.TestCase):
    def test_ascii_marks_and_the_config(self):
        for f in (TOOL, Path(__file__)):
            if not f.exists():
                self.skipTest("not here")
            b = f.read_bytes()
            self.assertTrue(all(x < 128 for x in b), f.name)
            self.assertIn(MARK, b, f.name)
        cfg = REPO / "configs" / "editions.json"
        if cfg.exists():
            import publish_editions as P
            c = json.loads(cfg.read_text(encoding="utf-8"))
            slugs = [e["slug"] for e in c["editions"]]
            self.assertEqual(len(slugs), len(set(slugs)))
            for e in c["editions"]:
                self.assertEqual(P.check_entry(e, {}), "", e["slug"])
            self.assertEqual([e["slug"] for e in c["editions"] if e.get("enabled", True)],
                             ["devimahatmya", "markandeya-purana-19-31"])   # DOCS76_2026_10_18


if __name__ == "__main__":
    unittest.main()
