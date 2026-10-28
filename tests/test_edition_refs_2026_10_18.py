# -*- coding: ascii -*-
"""EDITION_REFS_2026_10_18: the scholarly edition of an e-text whose verses carry their own references (GRETIL's 81.1)
takes its chapters from those references, not from the file's headings (the GRETIL Markandeya's speaker lines carried
"77" within adhyaya 81); a heading or a speaker's line goes with the next verse, a colophon with the one before; a
sentence begun by a speaker's line is labelled by its verses' own references, not by that line's page.idx. Three-part
references (MBh01, test_scholar_edition_2026_10_17) are unchanged. Temp files only; nothing is called."""
import json, re, shutil, sqlite3, subprocess, sys, tempfile, unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
SCRIPTS = REPO / "scripts"
sys.path.insert(0, str(SCRIPTS))
sys.path.insert(0, str(Path(__file__).resolve().parent))

MARK = b"EDITION_REFS_2026_10_18"
APPLIED = MARK in (SCRIPTS / "export_html.py").read_bytes()

HEAD81 = "\u090f\u0915\u093e\u0936\u0940\u0924\u093f\u0924\u092e\u094b \u093d\u0927\u094d\u092f\u093e\u092f\u0903"
SPEAK = "\u092e\u093e\u0930\u094d\u0915\u0923\u094d\u0921\u0947\u092f \u0909\u0935\u093e\u091a"
VERSE = "\u0927\u0930\u094d\u092e\u0915\u094d\u0937\u0947\u0924\u094d\u0930\u0947 \u0915\u0941\u0930\u0941\u0915\u094d\u0937\u0947\u0924\u094d\u0930\u0947 %d"
ITI = "\u0907\u0924\u093f \u090f\u0915\u093e\u0936\u0940\u0924\u093f\u0924\u092e\u094b \u093d\u0927\u094d\u092f\u093e\u092f\u0903"
HEAD82 = "\u0926\u094d\u0935\u094d\u092f\u0936\u0940\u0924\u093f\u0924\u092e\u094b \u093d\u0927\u094d\u092f\u093e\u092f\u0903"

# (page, idx, text, verse_ref, chapter as the GRETIL file gave it, text_type)
ROWS = [(1, 1, HEAD81, None, "77", "mula"), (1, 2, SPEAK, None, "77", "prose"), (1, 3, VERSE % 1, "81.1", "81", "mula"),
        (1, 4, VERSE % 2, "81.2", "81", "mula"), (2, 1, SPEAK, None, "77", "prose"), (2, 2, VERSE % 3, "81.3", "81", "mula"),
        (2, 3, VERSE % 4, "81.4", "81", "mula"), (2, 4, ITI, None, "77", "colophon"), (3, 1, HEAD82, None, "78", "mula"),
        (3, 2, VERSE % 5, "82.1", "82", "mula")]


def fixture(td: Path) -> Path:
    import db_utils
    import scholar_translate as ST
    db = td / "context.db"
    con = db_utils.connect(str(db)); db_utils.ensure_schema(con); db_utils.migrate_schema(con)
    con.execute("INSERT INTO docs(code, category) VALUES ('Mark__w_gretil', 'purana')")
    did = con.execute("SELECT id FROM docs WHERE code = 'Mark__w_gretil'").fetchone()[0]
    ids = {}
    for page, idx, text, ref, chap, tt in ROWS:
        con.execute("INSERT INTO passages(doc_id, page_no, idx, text, translation, verse_ref, chapter, text_type, engine) "
                    "VALUES (?, ?, ?, ?, '', ?, ?, ?, 'etext:gretil')", (did, page, idx, text, ref, chap, tt))
        ids[(page, idx)] = (con.execute("SELECT last_insert_rowid()").fetchone()[0], text, ref)
    ST.ensure_schema(con)

    def put(key, tr, ref_as, group=None, gtr=None, notes=()):
        pid, text, _ref = ids[key]
        ST.store(con, {"passage_id": pid, "doc_code": "Mark__w_gretil", "page_no": key[0], "idx": key[1],
                       "verse_ref": ref_as, "src_hash": ST.src_hash(text), "translation": tr, "notes": json.dumps(list(notes)),
                       "doubts": "", "critique": "[]", "status": "passed", "engine": "anthropic:claude-sonnet-5-5",
                       "judge_engine": ST.JUDGE, "prompt_version": "scholar-v2.1", "cost_usd": 0.03,
                       "group_ref": group, "group_translation": gtr, "created_at": "2026-10-18T10:00:00+00:00"})
    put((1, 2), "Markandeya said:", "1.2")
    put((1, 3), "Savarni, the son of the Sun, is called the eighth *Manu*. //", "81.1",
        notes=[{"anchor": "the Sun", "note": "Surya."}, {"anchor": "*Manu*", "note": "The progenitor of an age."},
               {"anchor": "Savarni", "note": "The eighth Manu."}, {"anchor": "nowhere", "note": "Not in the English."}])
    put((1, 4), "Hear how he became the lord of the age. //", "81.2")
    whole = "Markandeya said: In the age of Svarocisa there was a king named Suratha, born of the Caitra line."
    put((2, 1), "p1", "2.1", group="g1", gtr=whole)       # a sentence begun by a speaker's line ...
    put((2, 2), "p2", "81.3", group="g1", gtr=whole)
    put((2, 3), "p3", "81.4", group="g1", gtr=whole)      # ... over two verses
    put((3, 2), "The next chapter begins. //", "82.1")
    con.commit(); con.close()
    return db


def export(db, out, doc, *extra):
    return subprocess.run([sys.executable, str(SCRIPTS / "export_html.py"), "--db", str(db), "--doc", doc, "--out", str(out),
                           "--sanskrit", "--side-by-side", *extra], capture_output=True, text=True, cwd=str(REPO))


@unittest.skipUnless(APPLIED, "EDITION_REFS_2026_10_18 is not applied here")
class TheChapters(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.td = Path(self.tmp.name)
        self.db = fixture(self.td)
        self.out = self.td / "exports"

    def tearDown(self):
        self.tmp.cleanup()

    def edition(self):
        r = export(self.db, self.out, "Mark__w_gretil", "--scholar", "--title", "Devimahatmya")
        self.assertEqual(r.returncode, 0, r.stderr)
        return (self.out / "Mark_w_gretil_1-3_scholar.html").read_text(encoding="utf-8")

    def test_the_chapters_are_the_references(self):
        h = self.edition()
        heads = re.findall(r"<h2>(Adhy\u0101ya [^<]+)</h2>", h)
        self.assertEqual(heads, ["Adhy\u0101ya 81", "Adhy\u0101ya 82"], "not the file's 77 and 78")
        s81 = h[h.index("<h2>Adhy\u0101ya 81</h2>"):h.index("<h2>Adhy\u0101ya 82</h2>")]
        self.assertIn(HEAD81, s81, "the heading goes with the verse after it")
        self.assertIn(ITI, s81, "the colophon with the verse before it")
        s82 = h[h.index("<h2>Adhy\u0101ya 82</h2>"):]
        self.assertIn(HEAD82, s82)

    def test_a_sentence_is_labelled_by_its_own_references(self):
        h = self.edition()
        self.assertIn("<span class='sch-rng'>81.3\u20134</span>Markandeya said: In the age", h)
        self.assertNotIn("2.1\u20134", h)
        self.assertIn("Its English is given with 81.3\u20134, above.", h)

    def test_without_references_the_chapters_are_as_before(self):
        con = sqlite3.connect(str(self.db))
        con.execute("UPDATE passages SET verse_ref = NULL")
        con.commit(); con.close()
        h = self.edition()
        heads = re.findall(r"<h2>(Adhy\u0101ya [^<]+)</h2>", h)
        self.assertIn("Adhy\u0101ya 77", heads, "the file's own chapters, as before")


@unittest.skipUnless(APPLIED, "EDITION_REFS_2026_10_18 is not applied here")
class TheNotes(unittest.TestCase):
    def test_the_notes_are_numbered_as_they_are_read(self):
        with tempfile.TemporaryDirectory() as td:
            db = fixture(Path(td))
            r = export(db, Path(td) / "ex", "Mark__w_gretil", "--scholar")
            self.assertEqual(r.returncode, 0, r.stderr)
            h = (Path(td) / "ex" / "Mark_w_gretil_1-3_scholar.html").read_text(encoding="utf-8")
        sup = lambda k: "<sup class='fn-ref' id='fnr-%d'><a href='#fn-%d'>%d</a></sup>" % (k, k, k)
        self.assertIn("Savarni" + sup(1) + ", the son of the Sun" + sup(2) + ", is called the eighth <em>Manu</em>" + sup(3)
                      + "." + sup(4), h, "in the order they are read; the italic term found; the one not found last")
        notes = re.findall(r"<li id='fn-(\d+)'>(.*?)</li>", h)
        if notes:
            got = [(k, re.sub(r"<[^>]+>", "", t).split(":")[0]) for k, t in notes[:4]]
            self.assertEqual(got, [("1", "Savarni"), ("2", "the Sun"), ("3", "Manu"), ("4", "nowhere")])
        self.assertIn("<li id='fn-3'><em>Manu</em>: The progenitor of an age.", h, "the note's term in italics")


def as_left(rel: str) -> bytes:
    """The file as this patch left it. HEAL_2026_10_28: a later patch of the same file (PROSE_EDITION_2026_10_25 changed
    export_html.py) keeps that state in its own backup, the oldest one that already carries MARK; without one, the file
    as it is now."""
    p = REPO / rel
    later = [b for b in p.parent.glob(p.name + ".bak_*")
             if ".bak_editionrefs_" not in b.name and MARK in b.read_bytes()]
    return min(later, key=lambda b: b.stat().st_mtime).read_bytes() if later else p.read_bytes()


class ThePatcher(unittest.TestCase):
    FILES = ("scripts/export_html.py", "tests/test_scholar_edition_2026_10_17.py")

    @unittest.skipUnless(APPLIED, "not applied here")
    def test_it_applies_once_to_what_it_found(self):
        baks = {f: sorted((REPO / f).parent.glob(Path(f).name + ".bak_editionrefs_*")) for f in self.FILES}
        if not all(baks.values()):
            self.skipTest("no .bak_editionrefs_ copies here")
        pat = [sys.executable, str(SCRIPTS / "patch_edition_refs_2026_10_18.py")]
        with tempfile.TemporaryDirectory() as td:
            t = Path(td)
            (t / "scripts").mkdir(); (t / "tests").mkdir()
            (t / "scripts" / "dashboard.py").write_text("# the repo root\n", encoding="ascii")
            for f in self.FILES:
                shutil.copy2(baks[f][0], t / f)
            r = subprocess.run(pat + ["--check"], cwd=td, capture_output=True, text=True)
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
            r = subprocess.run(pat, cwd=td, capture_output=True, text=True)
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
            for f in self.FILES:
                self.assertEqual((t / f).read_bytes(), as_left(f), f)
            self.assertIn("Nothing to do", subprocess.run(pat, cwd=td, capture_output=True, text=True).stdout)
            for f in self.FILES:
                shutil.copy2(baks[f][0], t / f)
            e = t / "scripts" / "export_html.py"
            e.write_bytes(e.read_bytes().replace(b'        rng = ST._range(u) if len(u) > 1 else ""',
                                                 b'        rng = ST._range(u)'))
            r = subprocess.run(pat, cwd=td, capture_output=True, text=True)
            self.assertEqual(r.returncode, 1)
            self.assertIn("export_html.py: anchor 3 found 0 times (want 1)", r.stdout)
            self.assertNotIn(MARK, (t / "tests" / "test_scholar_edition_2026_10_17.py").read_bytes(), "all or nothing")


class TheFiles(unittest.TestCase):
    def test_ascii_and_marks(self):
        for f in (SCRIPTS / "patch_edition_refs_2026_10_18.py", Path(__file__)):
            if not f.exists():
                self.skipTest("the patcher is not here")
            b = f.read_bytes()
            self.assertTrue(all(x < 128 for x in b), f.name)
            self.assertIn(MARK, b, f.name)


if __name__ == "__main__":
    unittest.main()
