# -*- coding: ascii -*-
"""ETEXT_REFS_2026_10_21: a line that begins with the e-text's pada label (1.31a:) keeps the value in brackets at its
end, which is not a reference, and its reference and chapter are the label's (a chapter's first verse begins with its
title in brackets); labels=False reads as before. mend_witness.py reads a witness's lines again from its source file
(when its sha256 is the witness's): the reference only, or the value put back (the scholarly English re-based, with the
verse's reference); the latest English of a verse whose reference alone changes has its reference set, its English
untouched; a reference the e-text gives two verses is named; a source file that changed is not read. The patcher
applies once, from the copies it found. Temp files only; made-up samples."""
import hashlib, json, os, shutil, sqlite3, subprocess, sys, tempfile, unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
SCRIPTS = REPO / "scripts"
sys.path.insert(0, str(SCRIPTS))
MARK = "ETEXT_REFS_2026_10_21"
APPLIED = MARK.encode() in (SCRIPTS / "etext_witness.py").read_bytes() and MARK.encode() in (SCRIPTS / "mend_witness.py").read_bytes()
try:
    import indic_transliteration  # noqa: F401
    HAVE_IT = True
except ImportError:
    HAVE_IT = False

W = "testsurya__w_etext"
SOURCE = ["1.1a: namaH s\u016bry\u0101ya/ 1.1b: dev\u0101ya tejase//", "",
          "1.2a: yug\u0101ni ras\u0101gnayaH/(36) 1.2b: kalpe ca bhaga\u1e47\u0101H//(4320)", "",
          "[gati] 2.1a: atha vak\u1e63ye/ 2.1b: grah\u0101\u1e47\u0101\u1e43 gatim//", "",
          "2.1a: punar anyat/ 2.1b: vad\u0101mi te//", ""]


@unittest.skipUnless(APPLIED and HAVE_IT, "ETEXT_REFS_2026_10_21 or indic_transliteration is not here")
class TheReading(unittest.TestCase):
    def setUp(self):
        import etext_witness as EW
        self.EW = EW

    def test_a_label_keeps_the_value(self):
        ln = SOURCE[2]
        self.assertEqual(self.EW.take_ref(ln), (ln, "1.2", "part"))
        body, ref, where = self.EW.take_ref(ln, labels=False)
        self.assertEqual((ref, where), ("4320", "end"), "as before: the value read as a reference")
        self.assertFalse(body.endswith("(4320)"))
        self.assertEqual(self.EW.take_ref(SOURCE[4])[1], "2.1", "a chapter's title in brackets before the label")
        self.assertEqual(self.EW.take_ref("BhG_1.1 dharmak\u1e63etre")[1], "1.1", "the other references as before")

    def test_parse_gives_the_labels(self):
        vs = self.EW.parse("\n".join(SOURCE), "iast")["verses"]
        self.assertEqual([(v["ref"], v["chapter"]) for v in vs], [("1.1", "1"), ("1.2", "1"), ("2.1", "2"), ("2.1", "2")])
        self.assertTrue(vs[1]["text"].endswith("(\u096a\u0969\u0968\u0966)"), vs[1]["text"])
        self.assertTrue(vs[1]["roman"].endswith("(4320)"))


@unittest.skipUnless(APPLIED and HAVE_IT, "ETEXT_REFS_2026_10_21 or indic_transliteration is not here")
class TheMend(unittest.TestCase):
    def setUp(self):
        import db_utils, etext_witness as EW
        import scholar_translate as ST
        self.EW, self.ST = EW, ST
        self.tmp = Path(tempfile.mkdtemp(prefix="refs_"))
        self.db = str(self.tmp / "t.db")
        con = sqlite3.connect(self.db)
        db_utils.ensure_schema(con); db_utils.migrate_schema(con); ST.ensure_schema(con)
        con.commit(); con.close()
        self.out = self.tmp / "raw_witness"
        d = self.out / W
        d.mkdir(parents=True)
        src = self.tmp / "src.txt"
        src.write_text("\n".join(SOURCE) + "\n", encoding="utf-8")
        self.meta = {"witness": W, "doc": "testsurya", "site": "etext", "mode": "verses", "scheme": "iast",
                     "file": str(src), "sha256": hashlib.sha256(src.read_bytes()).hexdigest()}
        (d / "witness.json").write_text(json.dumps(self.meta), encoding="utf-8")
        recs = []
        for line in (1, 3, 5, 7):   # as read before 21 Oct's evening (the first mend done): the value out, no reference
            body, ref, _w = EW.take_ref(SOURCE[line - 1], labels=False)
            recs.append({"text": EW.to_deva(body, "iast"), "engine": "etext:etext", "page_no": 1, "verse_ref": ref or None,
                         "chapter": "1", "text_type": "mula", "padas": 2, "quality_score": 0.95,
                         "meta": {"witness_of": "testsurya", "src_line": line, "roman_source": body}})
        self.page = d / ("%s_0001.jsonl" % W)
        self.page.write_text("\n".join(json.dumps(r, ensure_ascii=False) for r in recs) + "\n", encoding="utf-8")
        r = subprocess.run([sys.executable, str(SCRIPTS / "ingest_jsonl_fast.py"), "--doc", W, "--glob",
                            str(d / ("%s_*.jsonl" % W)), "--db", self.db, "--source", "given", "--no-segment"],
                           capture_output=True, text=True, cwd=str(REPO))
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        con = sqlite3.connect(self.db)
        self.ids = {i: (pid, t) for pid, i, t in con.execute(
            "SELECT p.id, p.idx, p.text FROM passages p JOIN docs d ON d.id = p.doc_id WHERE d.code = ?", (W,))}
        for i, vr in ((2, "4320"), (3, "1.3")):   # the value's verse, and one whose reference alone changes
            pid, t = self.ids[i]
            rec = {c: None for c in ST.COLS}
            rec.update(passage_id=pid, doc_code=W, page_no=1, idx=i, verse_ref=vr, src_hash=ST.src_hash(t), version=1,
                       translation="English %d" % i, status="passed", fidelity=5, fluency=5, judge_reason="faithful",
                       engine="gemini:gemini-2.5-pro", judge_engine="gemini:gemini-2.5-flash", cost_usd=0.05,
                       created_at="2026-10-21T19:00:00")
            con.execute("INSERT INTO scholar_translations(%s) VALUES (%s)" % (", ".join(ST.COLS), ",".join("?" * len(ST.COLS))),
                        [rec[c] for c in ST.COLS])
        con.commit(); con.close()

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def run_tool(self, *args):
        env = dict(os.environ, PYTHONIOENCODING="utf-8", SA_MEND_NO_DASHBOARD="1", PYTHONDONTWRITEBYTECODE="1")
        r = subprocess.run([sys.executable, str(SCRIPTS / "mend_witness.py"), "--doc", W, "--db", self.db, "--out-dir",
                            str(self.out), "--witnesses", str(self.tmp / "witnesses.jsonl"), "--log-dir", str(self.tmp / "mend"),
                            "--backup-dir", str(self.tmp / "bk"), "--verdicts", str(self.tmp / "v.jsonl")] + list(args),
                           capture_output=True, text=True, encoding="utf-8", env=env)
        return r.returncode, r.stdout + r.stderr

    def test_the_plan_and_the_mend(self):
        rc, out = self.run_tool()
        self.assertEqual(rc, 0, out)
        self.assertIn("passages: 4; respelled 1; header 0; the same 0; the reference only 3;", out)
        self.assertIn("scholarly English: 1 re-based", out)
        self.assertIn("given the verse's reference (the English untouched): 1", out)
        self.assertIn("1 reference(s) to more than one passage (its labels, left as written): 2.1 at 1.3, 1.4", out)
        self.assertIn("the reference: 1.2, chapter 1 (was 4320, chapter 1)", out)
        rc, out = self.run_tool("--yes")
        self.assertEqual(rc, 0, out)
        self.assertIn("1 passages respelled, 0 header line(s) kept in Latin letters as noise, 3 given their reference only; "
                      "1 scholarly English re-based (the same English), 1 given the verse's reference", out)
        con = sqlite3.connect(self.db)
        now = {i: (pid, t, vr, ch) for pid, i, t, vr, ch in con.execute(
            "SELECT p.id, p.idx, p.text, p.verse_ref, p.chapter FROM passages p JOIN docs d ON d.id = p.doc_id WHERE d.code = ?", (W,))}
        self.assertEqual({i: v[0] for i, v in now.items()}, {i: v[0] for i, v in self.ids.items()}, "the ids stay")
        self.assertEqual({i: (v[2], v[3]) for i, v in now.items()}, {1: ("1.1", "1"), 2: ("1.2", "1"), 3: ("2.1", "2"), 4: ("2.1", "2")})
        self.assertTrue(now[2][1].endswith("(\u096a\u0969\u0968\u0966)"), "the value is back")
        self.assertEqual(now[1][1], self.ids[1][1], "the reference only: the text the same")
        rows = con.execute("SELECT id, passage_id, version, verse_ref, src_hash, translation, judge_reason FROM scholar_translations "
                           "ORDER BY passage_id, version").fetchall()
        con.close()
        by = {}
        for r in rows:
            by.setdefault(r[1], []).append(r)
        v = by[self.ids[2][0]]
        self.assertEqual([(x[2], x[3]) for x in v], [(1, "4320"), (2, "1.2")])
        self.assertEqual((v[1][4], v[1][5]), (self.ST.src_hash(now[2][1]), "English 2"))
        self.assertIn("the value in brackets", v[1][6])
        v = by[self.ids[3][0]]
        self.assertEqual([(x[2], x[3], x[5]) for x in v], [(1, "2.1", "English 3")], "its reference set, in place")
        recs = [json.loads(x) for x in self.page.read_text(encoding="utf-8").splitlines() if x.strip()]
        self.assertEqual(recs[1]["meta"]["roman_source"], SOURCE[2])
        self.assertEqual(recs[1]["meta"]["mend_refs"], MARK)
        self.assertEqual([r["verse_ref"] for r in recs], ["1.1", "1.2", "2.1", "2.1"])
        log = [json.loads(x) for x in next((self.tmp / "mend").glob("*.jsonl")).read_text(encoding="utf-8").splitlines()]
        self.assertEqual(sorted((x["idx"], x["kind"], x["ref_old"], x["ref"]) for x in log),
                         [(1, "refs", None, "1.1"), (2, "respelled", "4320", "1.2"), (3, "refs", None, "2.1"), (4, "refs", None, "2.1")])
        w = [json.loads(x) for x in (self.tmp / "witnesses.jsonl").read_text(encoding="utf-8").splitlines()][-1]
        self.assertEqual((w["mended"], w["refs"], w["labelled"], w["rebased"], w["mark_refs"]), (4, 3, 1, 1, MARK))
        rc, out = self.run_tool()
        self.assertIn("VERDICT: nothing to mend in %s" % W, out)

    def test_a_changed_source_is_not_read(self):
        src = Path(self.meta["file"])
        src.write_text(src.read_text(encoding="utf-8") + "\n3.1a: iti//\n", encoding="utf-8")
        rc, out = self.run_tool()
        self.assertEqual(rc, 0, out)
        self.assertIn("passages: 4; respelled 0; header 0; the same 0; the reference only 4;", out,
                      "the labels from the lines kept; the value cannot be put back")


class TheFiles(unittest.TestCase):
    FILES = ("scripts/etext_witness.py", "scripts/mend_witness.py", "tests/test_etext_ortho_2026_10_21.py")

    @unittest.skipUnless(APPLIED, "not applied here")
    def test_it_applies_once_to_what_it_found(self):
        baks = {f: sorted((REPO / f).parent.glob(Path(f).name + ".bak_etextrefs_*")) for f in self.FILES}
        if not all(baks.values()):
            self.skipTest("no .bak_etextrefs_ copies here")
        pat = [sys.executable, str(SCRIPTS / "patch_etext_refs_2026_10_21.py")]
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
                self.assertEqual((t / f).read_bytes(), (REPO / f).read_bytes(), f)
            self.assertIn("Nothing to do", subprocess.run(pat, cwd=td, capture_output=True, text=True).stdout)
            for f in self.FILES:
                shutil.copy2(baks[f][0], t / f)
            p = t / "scripts" / "mend_witness.py"
            p.write_bytes(p.read_bytes().replace(b'MARK = "WITNESS_MEND_2026_10_21"\n', b"MARK = 'WITNESS_MEND_2026_10_21'\n"))
            r = subprocess.run(pat, cwd=td, capture_output=True, text=True)
            self.assertEqual(r.returncode, 1)
            self.assertIn("anchor 2 found 0 times", r.stdout)
            self.assertNotIn(MARK.encode(), (t / "scripts" / "etext_witness.py").read_bytes(), "all or nothing")

    def test_ascii_and_marks(self):
        for f in (SCRIPTS / "patch_etext_refs_2026_10_21.py", Path(__file__)):
            if not f.exists():
                self.skipTest("not here")
            b = f.read_bytes()
            self.assertTrue(all(x < 128 for x in b), f.name)
            self.assertIn(MARK.encode(), b, f.name)


if __name__ == "__main__":
    unittest.main()
