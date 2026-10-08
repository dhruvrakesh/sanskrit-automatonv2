# -*- coding: ascii -*-
"""EXPORT_EMPTY_2026_10_07, NOVEL_PRINT_2026_10_07, PUBLISH_GATE_LINES_2026_10_07: an export with nothing
to show says so instead of printing empty pages, the Hindi line of the title page appears, a raw doc code in
the title is made readable; a novel page keeps its number in the caption and the cover gives the span the
pages cite; the publication gate withholds only passages that are nothing but page furniture, and
--emit-sql --only writes just the named passages. Temp databases, no network."""
import importlib, io, json, os, re, sqlite3, sys, tempfile, unittest
from contextlib import redirect_stdout
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "tests"))

SA = "\u0930\u093e\u092e\u0903 \u0935\u0928\u0902 \u0917\u091a\u094d\u091b\u0924\u093f \u0965"
FOLIO = "\u0969\u0969"      # a bare page number, Devanagari digits
HI = "\u0930\u093e\u092e \u0935\u0928 \u0917\u090f\u0964"


OPEN = []   # connections the tests opened; closed before the temp folder goes (Windows cannot delete an open file)


def export_db(d, translated_pages=(4,), with_hi=False):
    db = os.path.join(d, "context.db")
    con = sqlite3.connect(db)
    OPEN.append(con)
    con.executescript("""
        CREATE TABLE docs(id INTEGER PRIMARY KEY, code TEXT, category TEXT, src_path TEXT);
        CREATE TABLE passages(id INTEGER PRIMARY KEY, doc_id INTEGER, page_no INTEGER, idx INTEGER, text TEXT,
            iast TEXT, translation TEXT, text_type TEXT, engine TEXT, mt_prompt_version TEXT, translation_qa REAL);
        CREATE TABLE translations_l10n(id INTEGER PRIMARY KEY, passage_id INTEGER, lang TEXT, translation TEXT,
            engine TEXT, mt_prompt_version TEXT, translation_score REAL, translation_qa REAL, translated_at TEXT);
        INSERT INTO docs VALUES (1, 'demo_text', 'purana', NULL);""")
    for page in range(1, 6):
        for idx in (1, 2):
            en = ("Rama went to the forest on page %d." % page) if page in translated_pages else ""
            cur = con.execute("INSERT INTO passages(doc_id,page_no,idx,text,iast,translation,text_type,engine,"
                              "mt_prompt_version,translation_qa) VALUES (1,?,?,?,?,?,'mula','gemini:x','v3',0.9)",
                              (page, idx, SA, "", en))
            if with_hi and en:
                con.execute("INSERT INTO translations_l10n(passage_id,lang,translation,engine,mt_prompt_version,"
                            "translation_qa) VALUES (?,?,?,?,?,?)", (cur.lastrowid, "hi", HI, "gemini:h", "hi-1", 0.95))
    con.commit()
    return db, con


def run_export(con, d, **kw):
    import export_html as ex
    importlib.reload(ex)
    con.row_factory = sqlite3.Row
    args = dict(doc="demo_text", lo=1, hi=5, title=None, dest=d, include_san=False, include_en=True,
                side_by_side=False, number_pages=True, drop_junk_en=True, force_san=None, force_en=None)
    args.update(kw)
    buf = io.StringIO()
    with redirect_stdout(buf):
        path = ex._export_one(con, **args)
    return Path(path).read_text(encoding="utf-8"), buf.getvalue()


class Export(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()

    def tearDown(self):
        while OPEN:
            OPEN.pop().close()
        self.tmp.cleanup()

    def test_empty_pages_are_left_out(self):
        db, con = export_db(self.tmp.name, translated_pages=(2, 4))
        h, out = run_export(con, self.tmp.name)
        self.assertEqual(re.findall(r"<h2>(Page \d+)</h2>", h), ["Page 2", "Page 4"])
        self.assertEqual(h.count("<li><a href="), 2, "contents list only pages with text")
        self.assertIn("wrote", out); self.assertIn("4 passage(s)", out)

    def test_nothing_to_show_says_what_is_missing(self):
        db, con = export_db(self.tmp.name, translated_pages=())
        h, out = run_export(con, self.tmp.name)
        self.assertNotIn("<h2>Page", h)
        self.assertIn("Nothing to show yet: no passage in this range has English text", h)
        self.assertIn("--sanskrit", h)
        self.assertIn("WARNING demo_text", out)
        h2, _ = run_export(con, self.tmp.name, include_san=True)   # the Sanskrit is there
        self.assertEqual(len(re.findall(r"<h2>Page \d+</h2>", h2)), 5)

    def test_hindi_line_on_the_title_page(self):
        db, con = export_db(self.tmp.name, translated_pages=(1, 2), with_hi=True)
        h, _ = run_export(con, self.tmp.name, hi_lang="hi", hi_label="Hindi")
        self.assertIn("<b>English:</b> 4 verses", h)
        self.assertIn("<b>Hindi:</b> 4 verses, engine gemini:h, prompt hi-1, mean QA 0.95", h)

    def test_raw_code_in_the_title_is_made_readable(self):
        import export_html as ex
        importlib.reload(ex)
        self.assertEqual(ex._display_title("demo_text \u2014 English Translation", "demo_text"),
                         "Demo Text \u2014 English Translation")
        self.assertEqual(ex._display_title("My Own Title", "demo_text"), "My Own Title")
        self.assertEqual(ex._display_title(None, "demo_text"), None)
        db, con = export_db(self.tmp.name)
        h, _ = run_export(con, self.tmp.name, title="demo_text \u2014 English Translation")
        self.assertIn("<h1>Demo Text \u2014 English Translation</h1>", h)
        self.assertIn("<title>Demo Text \u2014 English Translation</title>", h)


class NovelBuild(unittest.TestCase):
    def setUp(self):
        import stories, novel
        importlib.reload(stories); importlib.reload(novel)
        from test_novel_2026_10_07 import plan_payload, image_stub
        from test_vignettes_2026_10_05 import stub
        from test_story_books_2026_10_07 import _fixture
        self.nv = novel
        self.tmp = tempfile.TemporaryDirectory()
        self.db = _fixture(self.tmp.name)
        self.con = sqlite3.connect(self.db)
        payload = plan_payload()
        payload["pages"][0]["caption"] += " Both rested there [11.4]."
        self.nid = novel.plan(self.con, 1, self.db, pages=8, http=stub(payload, []))
        novel.draw_pages(self.con, self.nid, self.db, which=[1, 2], http=image_stub([]), root=Path(self.tmp.name) / "i")

    def tearDown(self):
        self.con.close(); self.tmp.cleanup()

    def test_number_inside_caption_and_one_page_per_panel(self):
        out = Path(self.tmp.name) / "n.html"
        self.nv.build(self.con, self.nid, out)
        h = out.read_text(encoding="utf-8")
        self.assertEqual(len(re.findall(r"<div class='cap'><span class='no'>\d+</span>", h)), 8)
        self.assertNotIn("</div><div class='no'>", h, "no number after the caption box")
        self.assertIn("height:96vh", h); self.assertIn("object-fit:contain", h)

    def test_cover_gives_the_cited_span_and_can_use_another_page(self):
        n = self.nv.get(self.con, self.nid)
        import stories
        cited = sorted(n["verify"]["cited"], key=lambda c: stories.parse_ref(c) or (0, 0))
        out = Path(self.tmp.name) / "n.html"
        self.nv.build(self.con, self.nid, out)
        h = out.read_text(encoding="utf-8")
        self.assertIn("passages %s-%s." % (cited[0], cited[-1]), h)
        covers = re.findall(r"<img src='([^']+)' alt='cover'/>", h)
        page1 = re.findall(r"<img src='([^']+)' alt='page 1'/>", h)
        self.assertEqual(covers, page1)
        self.nv.build(self.con, self.nid, out, cover_page=2)
        h2 = out.read_text(encoding="utf-8")
        self.assertEqual(re.findall(r"<img src='([^']+)' alt='cover'/>", h2),
                         re.findall(r"<img src='([^']+)' alt='page 2'/>", h2))

    def test_sources_drop_verse_marks(self):
        import novel
        self.assertEqual(novel._mt_display("Then he went. // And so on. //"), "Then he went. And so on.")
        self.assertEqual(novel._mt_display("see http://x.org //"), "see http://x.org")


class Gate(unittest.TestCase):
    def setUp(self):
        import publish_srangam as ps
        importlib.reload(ps)
        self.ps = ps

    def rows(self, texts):
        return [{"page_no": 1, "idx": k, "text": t, "iast": "", "translation": "x", "verse_ref": None,
                 "quality_score": 0.9, "text_type": "mula"} for k, t in enumerate(texts, 1)]

    def test_only_furniture_is_withheld(self):
        ps = self.ps
        self.assertTrue(ps.gate_has_furniture(FOLIO))
        self.assertFalse(ps.gate_has_furniture(FOLIO + "\n" + SA), "a verse under a folio mark is published")
        self.assertFalse(ps.gate_has_furniture(SA))
        self.assertFalse(ps.gate_has_furniture(""))
        keep, drop = ps.gate_rows(self.rows([FOLIO, FOLIO + "\n" + SA, SA + " \u0915"]))
        self.assertEqual([r["idx"] for r in keep], [2, 3])
        self.assertEqual([(r["idx"], why) for r, why in drop], [(1, "page furniture (running head / folio mark)")])

    def test_emit_only(self):
        ps = self.ps
        d = tempfile.mkdtemp(prefix="emit_")
        rows = [{"page_no": p, "idx": i, "text": SA, "iast": "", "translation": "t %d.%d" % (p, i), "verse_ref": None,
                 "quality_score": 0.9, "text_type": "mula"} for p in (1, 2) for i in (1, 2)]
        doc = {"code": "demo_text", "category": "purana"}
        with redirect_stdout(io.StringIO()):
            out = ps.emit_sql(d, doc, rows, "gemini:x", "note", only={(2, 1)})
        files = sorted(p.name for p in Path(out).glob("*.sql"))
        self.assertEqual(files, ["00_text.sql", "01_passages.sql", "99_verify.sql"])
        body = (Path(out) / "01_passages.sql").read_text(encoding="utf-8")
        self.assertIn("'t 2.1'", body); self.assertNotIn("'t 1.1'", body)
        self.assertIn(", 4)\n", (Path(out) / "00_text.sql").read_text(encoding="utf-8"), "passage_count is the whole set")
        self.assertIn("(1,1),(1,2),(2,1),(2,2)", (Path(out) / "99_verify.sql").read_text(encoding="utf-8"))
        self.assertIn("passages in these files: 1  (--only)", (Path(out) / "MANIFEST.txt").read_text(encoding="utf-8"))


class Titles(unittest.TestCase):
    def test_titles_file(self):
        d = json.loads((ROOT / "configs" / "doc_titles.json").read_text(encoding="utf-8"))
        self.assertEqual(d["titles"]["markandeya_purana"], "M\u0101rka\u1e47\u1e0deya Pur\u0101\u1e47a")
        self.assertIn("nilamata_seg", d["titles"])
        self.assertIn("MBh01", d["titles"], "existing titles kept")


if __name__ == "__main__":
    unittest.main()
