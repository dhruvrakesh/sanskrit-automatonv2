# -*- coding: ascii -*-
"""SCHOLAR_MIRROR_2026_10_18: corpus_sync.py carries the scholarly English (scholar_translations) to the mirror, as two
rows of the translations table a verse: en-x-scholar (its English, its fidelity and fluency) and en-x-scholar-meta
(JSON: status, flag, a person's acceptance, notes, doubts, a sentence's range). Only a verse's latest version, made
from its Sanskrit as it reads now, not rejected by a person; a sentence over several verses gives its English on its
first verse and "with" on the others. The Hindi rows and every other table are unchanged; a witness stays local until
it is adopted. The FakeServer of test_corpus_sync_2026_10_08 (the C4 rules, in memory); temp files only, no network."""
import json, os, shutil, sqlite3, subprocess, sys, tempfile, unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
SCRIPTS = REPO / "scripts"
sys.path.insert(0, str(SCRIPTS))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import corpus_sync as cs  # noqa: E402
import test_corpus_sync_2026_10_08 as T  # noqa: E402

MARK = b"SCHOLAR_MIRROR_2026_10_18"
APPLIED = MARK in (SCRIPTS / "corpus_sync.py").read_bytes()
DOC = "markandeya_purana"
SLOKA = "\u0936\u094d\u0932\u094b\u0915 %d"   # the fixture's Sanskrit: the same for each page's idx


def add_scholar(db, doc_id=1, code=DOC):
    """Scholarly English for the fixture's first text: a passed verse with a note (and an older version), a flagged one
    with a doubt, one a person accepted, a sentence over two verses, one a person rejected, one made from another
    reading (stale)."""
    import scholar_translate as ST
    con = sqlite3.connect(db)
    ST.ensure_schema(con)
    pid = {(p, i): x for x, p, i in con.execute("SELECT id, page_no, idx FROM passages WHERE doc_id=?", (doc_id,))}

    def put(key, tr, status="passed", fid=5, flu=4, notes=(), doubts="", verdict=None, group=None, gtr=None,
            at="2026-10-18T10:00:00+00:00", text=None):
        con.execute(
            "INSERT INTO scholar_translations(passage_id, doc_code, page_no, idx, verse_ref, src_hash, version, translation, "
            "notes, doubts, fidelity, fluency, status, engine, judge_engine, prompt_version, created_at, review_verdict, "
            "group_ref, group_translation) VALUES (?,?,?,?,?,?,(SELECT coalesce(max(version),0)+1 FROM scholar_translations "
            "WHERE passage_id=?),?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (pid[key], code, key[0], key[1], "%d.%d" % key, ST.src_hash(text or SLOKA % key[1]), pid[key], tr,
             json.dumps(list(notes)), doubts, fid, flu, status, "anthropic:claude-sonnet-5-5", "gemini:gemini-2.5-flash",
             "scholar-v2.1", at, verdict, group, gtr))
    put((1, 1), "Old English. //", at="2026-10-17T10:00:00+00:00")
    put((1, 1), "The first verse names *Manu*. //", notes=[{"anchor": "*Manu*", "note": "The progenitor.", "kind": "name"},
                                                          {"anchor": "x", "note": ""}])
    put((1, 2), "A verse the judge doubted. //", status="flagged", fid=2, doubts="The reading may be corrupt.")
    put((1, 3), "A verse a person read. //", status="flagged", fid=3, verdict="accept")
    put((2, 1), "a", group="g1", gtr="The sentence over two verses.", at="2026-10-18T11:00:00+00:00")
    put((2, 2), "b", group="g1", gtr="The sentence over two verses.", at="2026-10-18T11:00:00+00:00")
    put((3, 1), "Rejected. //", verdict="reject")
    put((3, 2), "Made from another reading. //", text="\u0905\u0928\u094d\u092f")
    con.commit()
    con.close()


@unittest.skipUnless(APPLIED, "SCHOLAR_MIRROR_2026_10_18 is not applied here")
class TheScholarlyRows(T.Base):
    def rows(self):
        return {k: v for k, v in self.server.t["translations"].get(DOC, {}).items() if not v["retired"]}

    def test_they_travel_with_the_hindi(self):
        add_scholar(self.db)
        s = self.sync()
        self.assertEqual(s["stopped"], "done", s)
        self.assertEqual(s["tables"]["translations"]["changed"], 10 + 9, "the fixture's Hindi and 4 + 5 scholarly rows")
        self.assertEqual(s["verified"]["groups_different"], 0)
        r = self.rows()
        en = r["1|1|en-x-scholar"]["row"]
        self.assertEqual((en["translation"], en["translation_score"], en["translation_qa"], en["engine"],
                          en["mt_prompt_version"], en["translated_at"]),
                         ("The first verse names *Manu*. //", 5, 4, "anthropic:claude-sonnet-5-5", "scholar-v2.1",
                          "2026-10-18T10:00:00+00:00"), "the latest version")
        m = json.loads(r["1|1|en-x-scholar-meta"]["row"]["translation"])
        self.assertEqual(m, {"status": "passed", "flag": False, "accepted": False, "judge": "gemini:gemini-2.5-flash",
                             "notes": [{"anchor": "*Manu*", "note": "The progenitor.", "kind": "name"}]},
                         "an empty note left out")
        self.assertEqual(r["1|1|en-x-scholar-meta"]["row"]["mt_prompt_version"], "scholar-meta-1")
        m = json.loads(r["1|2|en-x-scholar-meta"]["row"]["translation"])
        self.assertEqual((m["status"], m["flag"], m["doubts"]), ("flagged", True, "The reading may be corrupt."))
        m = json.loads(r["1|3|en-x-scholar-meta"]["row"]["translation"])
        self.assertEqual((m["flag"], m["accepted"]), (False, True), "a person's reading lifts the flag")
        self.assertEqual(r["2|1|en-x-scholar"]["row"]["translation"], "The sentence over two verses.")
        self.assertEqual(json.loads(r["2|1|en-x-scholar-meta"]["row"]["translation"])["range"], "2.1\u20132")
        self.assertNotIn("2|2|en-x-scholar", r, "the sentence's English is on its first verse")
        self.assertEqual(json.loads(r["2|2|en-x-scholar-meta"]["row"]["translation"])["with"], "2.1\u20132")
        for k in ("3|1|en-x-scholar", "3|1|en-x-scholar-meta", "3|2|en-x-scholar", "3|2|en-x-scholar-meta"):
            self.assertNotIn(k, r, "rejected by a person, or made from another reading")
        s2 = self.sync()
        self.assertEqual(sum(x["upsert"] for x in s2["tables"].values()), 0)

    def test_added_later_only_they_are_sent(self):
        self.sync()
        hi = {k: v["h"] for k, v in self.rows().items()}
        add_scholar(self.db)
        s = self.sync()
        self.assertEqual(s["tables"]["passages"]["upsert"], 0)
        self.assertEqual(s["tables"]["translations"]["upsert"], 9)
        self.assertEqual(s["tables"]["translations"]["retire"], 0)
        self.assertEqual({k: v["h"] for k, v in self.rows().items() if k in hi}, hi, "the Hindi rows as they were")
        self.assertEqual(s["tables"]["translations"]["groups_changed"], 1, "the other text untouched")

    def test_a_new_version_and_a_rejection(self):
        add_scholar(self.db)
        self.sync()
        import scholar_translate as ST
        con = self.rw()
        pid = con.execute("SELECT id FROM passages WHERE doc_id=1 AND page_no=1 AND idx=1").fetchone()[0]
        con.execute("INSERT INTO scholar_translations(passage_id, doc_code, page_no, idx, src_hash, version, translation, "
                    "status, fidelity, fluency, created_at) VALUES (?, ?, 1, 1, ?, 9, 'Revised. //', 'passed', 5, 5, "
                    "'2026-10-18T12:00:00+00:00')", (pid, DOC, ST.src_hash(SLOKA % 1)))
        con.execute("UPDATE scholar_translations SET review_verdict='reject' WHERE id=(SELECT max(id) FROM "
                    "scholar_translations WHERE page_no=1 AND idx=2)")
        con.commit()
        s = self.sync()
        self.assertEqual(s["tables"]["translations"]["upsert"], 2, "the new version: its English and its meta")
        self.assertEqual(s["tables"]["translations"]["retire"], 2, "the rejected verse's two rows")
        self.assertEqual(s["verified"]["groups_different"], 0)
        self.assertEqual(self.rows()["1|1|en-x-scholar"]["row"]["translation"], "Revised. //")
        self.assertNotIn("1|2|en-x-scholar", self.rows())

    def test_status_counts_them(self):
        add_scholar(self.db)
        con = self.ro()
        self.assertEqual(cs.local_counts(con, cs.live_docs(con))["translations"], 10 + 9)

    def test_a_witness_stays_local_until_adopted(self):
        con = self.rw()
        con.execute("INSERT INTO docs(code, category) VALUES ('markandeya_purana__w_gretil', 'purana')")
        wid = con.execute("SELECT id FROM docs WHERE code='markandeya_purana__w_gretil'").fetchone()[0]
        for i in (1, 2, 3):
            con.execute("INSERT INTO passages(doc_id, page_no, idx, text, verse_ref, text_type) VALUES (?, 1, ?, ?, ?, 'mula')",
                        (wid, i, SLOKA % i, "81.%d" % i))
        con.commit()
        add_scholar(self.db)
        import scholar_translate as ST
        con.execute("INSERT INTO scholar_translations(passage_id, doc_code, page_no, idx, src_hash, version, translation, "
                    "status, created_at) SELECT id, 'markandeya_purana__w_gretil', 1, idx, ?, 1, 'Savarni.', 'passed', 'x' "
                    "FROM passages WHERE doc_id=? AND idx=1", (ST.src_hash(SLOKA % 1), wid))
        con.commit()
        reg = Path(self.tmp.name) / "source_verdicts.jsonl"
        reg.write_text(json.dumps({"doc": "markandeya_purana__w_gretil", "status": "witness"}) + "\n", encoding="utf-8")
        old = os.environ.get("SA_SOURCE_VERDICTS")
        os.environ["SA_SOURCE_VERDICTS"] = str(reg)
        try:
            self.sync()
            self.assertNotIn("markandeya_purana__w_gretil", self.server.t["passages"])
            self.assertNotIn("markandeya_purana__w_gretil", self.server.t["translations"])
            with open(reg, "a", encoding="utf-8") as f:
                f.write(json.dumps({"doc": "markandeya_purana__w_gretil", "status": "released"}) + "\n")
            s = self.sync()
            self.assertEqual(s["verified"]["groups_different"], 0)
            w = self.server.t["translations"]["markandeya_purana__w_gretil"]
            self.assertEqual(sorted(w), ["1|1|en-x-scholar", "1|1|en-x-scholar-meta"])
            self.assertEqual(len(self.server.t["passages"]["markandeya_purana__w_gretil"]), 3)
        finally:
            if old is None:
                os.environ.pop("SA_SOURCE_VERDICTS", None)
            else:
                os.environ["SA_SOURCE_VERDICTS"] = old

    def test_without_the_table_nothing_changes(self):
        con = self.ro()
        self.assertEqual(cs.scholar_rows(con, DOC, {1: (1, 1)}, {1: ("x", "1.1")}), [])
        self.assertEqual(cs.scholar_count(con, cs.live_docs(con)), 0)


class ThePatcher(unittest.TestCase):
    FILES = ("scripts/corpus_sync.py", "tests/test_mirror_cap_2026_10_12.py")

    @unittest.skipUnless(APPLIED, "not applied here")
    def test_it_applies_once_to_what_it_found(self):
        baks = {f: sorted((REPO / f).parent.glob(Path(f).name + ".bak_scholarmirror_*")) for f in self.FILES}
        if not all(baks.values()):
            self.skipTest("no .bak_scholarmirror_ copies here")
        pat = [sys.executable, str(SCRIPTS / "patch_scholar_mirror_2026_10_18.py")]
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
            c = t / "scripts" / "corpus_sync.py"
            c.write_bytes(c.read_bytes().replace(b'            out["translations"] = g', b'            out["translations"] = g  # x'))
            r = subprocess.run(pat, cwd=td, capture_output=True, text=True)
            self.assertEqual(r.returncode, 1)
            self.assertIn("corpus_sync.py: anchor 5 found 0 times (want 1)", r.stdout)
            self.assertNotIn(MARK, (t / "tests" / "test_mirror_cap_2026_10_12.py").read_bytes(), "all or nothing")


class TheFiles(unittest.TestCase):
    def test_ascii_and_marks(self):
        for f in (SCRIPTS / "patch_scholar_mirror_2026_10_18.py", Path(__file__)):
            if not f.exists():
                self.skipTest("the patcher is not here")
            b = f.read_bytes()
            self.assertTrue(all(x < 128 for x in b), f.name)
            self.assertIn(MARK, b, f.name)


if __name__ == "__main__":
    unittest.main()
