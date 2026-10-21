# -*- coding: ascii -*-
"""WITNESS_MEND_2026_10_21: mend_witness.py reads an ingested e-text witness again from its romanized lines: the plan
writes nothing; --yes makes a backup, rewrites the page files (keeping .bak_mend_ copies), ingests them as
etext_witness.py does (the ids stay), keeps GRETIL's English header in Latin letters as noise, and gives a verse's
scholarly English a new version made from the new spelling (the same English); a header line's is not carried
over; a database whose text is not what the page files gave is refused. Temp files only; made-up samples."""
import hashlib, json, os, shutil, sqlite3, subprocess, sys, tempfile, unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
SCRIPTS = REPO / "scripts"
sys.path.insert(0, str(SCRIPTS))
TOOL = SCRIPTS / "mend_witness.py"
MARK = "WITNESS_MEND_2026_10_21"
READY = TOOL.exists() and b"ETEXT_ORTHO_2026_10_21" in (SCRIPTS / "etext_witness.py").read_bytes()
W = "testdoc__w_gretil"
PAGES = {
    1: ["T\u012brthay\u0101tr\u0101", "Header", "Contribution: A. B.", "Source:", "Text",
        "1.01a: namaH \u015biv\u0101ya/ 1.01b: devo +api gataH//"],
    2: ["1.02a: r\u0101maH vana\u1e43 gataH/(B r\u0101mo) 1.02b: s\u012bt\u0101 +api//", "1.03a: sa gacchati/ 1.03b: na ti\u1e63\u1e6dhati//"],
}
SOURCE = ("<html><body><p>T\u012brthay\u0101tr\u0101</p><p>Header</p><p>Publisher: G\u00f6ttingen Register of Electronic Texts "
          "in Indian Languages (GRETIL)</p><p>Text</p></body></html>")


@unittest.skipUnless(READY, "mend_witness.py or ETEXT_ORTHO_2026_10_21 is not here")
class TheMend(unittest.TestCase):
    def setUp(self):
        import db_utils, etext_witness as EW
        import scholar_translate as ST
        self.EW, self.ST = EW, ST
        self.tmp = Path(tempfile.mkdtemp(prefix="mend_"))
        self.db = str(self.tmp / "t.db")
        con = sqlite3.connect(self.db)
        db_utils.ensure_schema(con); db_utils.migrate_schema(con); ST.ensure_schema(con)
        con.commit(); con.close()
        self.out = self.tmp / "raw_witness"
        d = self.out / W
        d.mkdir(parents=True)
        (self.tmp / "src.htm").write_text(SOURCE, encoding="utf-8")
        (d / "witness.json").write_text(json.dumps({"witness": W, "doc": "testdoc", "site": "etext", "mode": "verses",
                                                    "scheme": "iast", "file": str(self.tmp / "src.htm")}), encoding="utf-8")
        for page, lines in PAGES.items():
            recs = []
            for k, rom in enumerate(lines):
                text = EW.to_deva(rom, "iast", ortho=False)
                recs.append({"text": text, "engine": "etext:etext", "page_no": page, "verse_ref": None, "chapter": "1",
                             "text_type": "mula" if "//" in rom else "prose", "padas": 2, "quality_score": 0.95,
                             "meta": {"witness_of": "testdoc", "roman_source": rom}})
            (d / ("%s_%04d.jsonl" % (W, page))).write_text("\n".join(json.dumps(r, ensure_ascii=False) for r in recs) + "\n",
                                                           encoding="utf-8")
        r = subprocess.run([sys.executable, str(SCRIPTS / "ingest_jsonl_fast.py"), "--doc", W, "--glob",
                            str(d / ("%s_*.jsonl" % W)), "--db", self.db, "--source", "given", "--no-segment"],
                           capture_output=True, text=True, cwd=str(REPO))
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        con = sqlite3.connect(self.db)
        self.ids = {(p, i): (pid, t) for pid, p, i, t in con.execute(
            "SELECT p.id, p.page_no, p.idx, p.text FROM passages p JOIN docs d ON d.id = p.doc_id WHERE d.code = ?", (W,))}
        cols = ST.COLS
        for (p, i), (pid, t) in self.ids.items():
            if (p, i) in ((1, 3), (1, 6), (2, 1)):   # a header line, and two verses, have a scholarly English
                rec = {c: None for c in cols}
                rec.update(passage_id=pid, doc_code=W, page_no=p, idx=i, src_hash=ST.src_hash(t), version=1,
                           translation="English %d.%d" % (p, i), status="passed", fidelity=5, fluency=5,
                           judge_reason="faithful", engine="anthropic:claude-sonnet-5-5",
                           judge_engine="gemini:gemini-2.5-flash", cost_usd=0.05, created_at="2026-10-18T20:00:00")
                con.execute("INSERT INTO scholar_translations(%s) VALUES (%s)" % (", ".join(cols), ",".join("?" * len(cols))),
                            [rec[c] for c in cols])
        con.commit(); con.close()

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def run_tool(self, *args):
        env = dict(os.environ, PYTHONIOENCODING="utf-8", SA_MEND_NO_DASHBOARD="1", PYTHONDONTWRITEBYTECODE="1")
        r = subprocess.run([sys.executable, str(TOOL), "--doc", W, "--db", self.db, "--out-dir", str(self.out),
                            "--witnesses", str(self.tmp / "witnesses.jsonl"), "--log-dir", str(self.tmp / "mend"),
                            "--backup-dir", str(self.tmp / "bk")] + list(args),
                           capture_output=True, text=True, encoding="utf-8", env=env)
        return r.returncode, r.stdout + r.stderr

    def test_the_plan_writes_nothing_and_yes_mends(self):
        md5 = lambda: hashlib.md5(Path(self.db).read_bytes()).hexdigest()
        before = md5()
        rc, out = self.run_tool()
        self.assertEqual(rc, 0, out)
        self.assertIn("passages: 8; respelled 3; header 4; the same 1", out)
        self.assertIn("scholarly English: 2 re-based", out)
        self.assertIn("1 dropped (a header line, not a verse)", out)
        self.assertEqual(md5(), before)
        rc, out = self.run_tool("--yes")
        self.assertEqual(rc, 0, out)
        self.assertIn("VERDICT: %s mended: 3 passages respelled, 4 header line(s)" % W, out)
        con = sqlite3.connect(self.db)
        now = {(p, i): (pid, t, tt) for pid, p, i, t, tt in con.execute(
            "SELECT p.id, p.page_no, p.idx, p.text, p.text_type FROM passages p JOIN docs d ON d.id = p.doc_id WHERE d.code = ?", (W,))}
        self.assertEqual({k: v[0] for k, v in now.items()}, {k: v[0] for k, v in self.ids.items()}, "the ids stay")
        self.assertEqual(now[(1, 6)][1], "1.01a: \u0928\u092e\u0903 \u0936\u093f\u0935\u093e\u092f \u0964 1.01b: "
                         "\u0926\u0947\u0935\u094b\u093d\u092a\u093f \u0917\u0924\u0903 \u0965")
        self.assertEqual(now[(1, 3)][1:], ("Contribution: A. B.", "noise"))
        self.assertIn("(B \u0930\u093e\u092e\u094b)", now[(2, 1)][1])
        rows = con.execute("SELECT passage_id, version, src_hash, translation, judge_reason, cost_usd FROM scholar_translations "
                           "ORDER BY passage_id, version").fetchall()
        con.close()
        by = {}
        for r in rows:
            by.setdefault(r[0], []).append(r)
        v = by[self.ids[(1, 6)][0]]
        self.assertEqual(len(v), 2)
        self.assertEqual((v[1][1], v[1][2], v[1][3], v[1][5]), (2, self.ST.src_hash(now[(1, 6)][1]), "English 1.6", 0.0))
        self.assertTrue(v[1][4].startswith("[re-based "), v[1][4])
        self.assertTrue(v[1][4].endswith("] faithful"), v[1][4])
        self.assertEqual(len(by[self.ids[(1, 3)][0]]), 1, "a header line's English is not carried over")
        self.assertNotEqual(by[self.ids[(1, 3)][0]][0][2], self.ST.src_hash(now[(1, 3)][1]), "it is stale now")
        self.assertTrue(list((self.out / W).glob("*.bak_mend_*")))
        self.assertTrue(list((self.tmp / "bk").glob("context_pre_mend_%s_*.db" % W)), "the backup")
        self.assertEqual(len(list((self.tmp / "mend").glob("*.jsonl"))), 1)
        rec = [json.loads(x) for x in (self.tmp / "witnesses.jsonl").read_text(encoding="utf-8").splitlines()][-1]
        self.assertEqual((rec["witness"], rec["mended"], rec["rebased"], rec["mark"]), (W, 7, 2, MARK))
        rc, out = self.run_tool()
        self.assertIn("VERDICT: nothing to mend in %s" % W, out)

    def test_a_changed_database_is_refused(self):
        con = sqlite3.connect(self.db)
        con.execute("UPDATE passages SET text = text || ' x' WHERE id = ?", (self.ids[(2, 2)][0],))
        con.commit(); con.close()
        rc, out = self.run_tool("--yes")
        self.assertEqual(rc, 1)
        self.assertIn("REFUSE: the database's text is not what was ingested from the page files (1 place(s), e.g. 2.2)", out)
        self.assertFalse((self.tmp / "bk").exists(), "no backup, nothing done")


class TheFiles(unittest.TestCase):
    def test_ascii_and_marks(self):
        for f in (TOOL, Path(__file__)):
            if not f.exists():
                self.skipTest("not here")
            b = f.read_bytes()
            self.assertTrue(all(x < 128 for x in b), f.name)
            self.assertIn(MARK.encode(), b, f.name)


if __name__ == "__main__":
    unittest.main()
