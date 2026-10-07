# -*- coding: ascii -*-
"""STORY_FIX_2026_10_07: story_fix.py applies reviewed corrections to doc_stories the way the
dashboard's Edit does (check stored, back to draft, approval cleared), all or nothing, once.
A throwaway database in a temp folder; no network."""
import hashlib, json, os, sqlite3, subprocess, sys, tempfile, unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

M = "STORY_FIX_2026_10_07"
SA = "\u0930\u093e\u092e\u0903 \u0935\u0928\u0902 \u0917\u091a\u094d\u091b\u0924\u093f"   # ramah vanam gacchati
EN_PASS = [
    "Rama went to the forest with Sita and his brother.",
    "In the forest they built a hut of leaves near the river.",
    "Rama walks to the forest.",
    "Sita gathered flowers every morning by the water.",
    "A golden deer appeared near the hut one day.",
    "Sita asked Rama to catch the golden deer for her.",
]
SENTS = [
    "Rama went into the forest with Sita and his brother, leaving the city behind. [1.1]",
    "Near the river they built a small hut of leaves and lived there quietly for many seasons. [1.2]",
    "Every morning Sita gathered flowers by the water while the brothers kept watch over the hut. [1.4]",
    "One day a golden deer appeared near the hut, shining among the trees like fire. [1.5]",
    "Sita asked Rama to catch the golden deer, and he took his bow and followed it into the woods. [1.6]",
    "The forest grew quiet behind him as the deer ran on and the hut was left alone. [1.5, 1.6]",
]
STORY = " ".join(SENTS)


def make_db(status="approved"):
    d = tempfile.mkdtemp(prefix="storyfix_")
    db = os.path.join(d, "context.db")
    con = sqlite3.connect(db)
    con.executescript("""
        CREATE TABLE docs(id INTEGER PRIMARY KEY, code TEXT);
        CREATE TABLE passages(id INTEGER PRIMARY KEY, doc_id INTEGER, page_no INTEGER, idx INTEGER, text TEXT,
                              iast TEXT, translation TEXT, text_type TEXT);
        INSERT INTO docs VALUES (1, 'demo_text');""")
    for i, en in enumerate(EN_PASS, 1):
        con.execute("INSERT INTO passages(doc_id, page_no, idx, text, iast, translation, text_type) VALUES (1,1,?,?,?,?,'mula')",
                    (i, SA if i == 3 else "x", "", en))
    import stories as st
    st.ensure_schema(con)
    for sid in (1, 2):
        con.execute("""INSERT INTO doc_stories(id, doc_id, status, title, why, from_page, from_idx, to_page, to_idx,
                       story_en, story_hi, quote_sa, quote_ref, notes, verify, updated_at, approved_at)
                       VALUES (?,1,?,?,?,1,1,1,6,?,?,?,?,?,?,?,?)""",
                    (sid, status, "Into the forest %d" % sid, "Rama goes to the forest.", STORY, "", SA, "1.3",
                     "first notes", "{}", "2026-10-07T10:00:00", "2026-10-07T10:00:00" if status == "approved" else None))
    con.commit(); con.close()
    return d, db


def run(d, db, fixes, *extra):
    f = os.path.join(d, "fix.json")
    Path(f).write_text(json.dumps(fixes), encoding="ascii")
    r = subprocess.run([sys.executable, str(ROOT / "scripts" / "story_fix.py"), "--db", db, "--file", f, *extra],
                       capture_output=True, text=True, cwd=d)
    return r.returncode, r.stdout + r.stderr


def row(db, sid):
    con = sqlite3.connect(db); con.row_factory = sqlite3.Row
    r = dict(con.execute("SELECT * FROM doc_stories WHERE id=?", (sid,)).fetchone()); con.close()
    return r


def fix(sid=1, **k):
    f = {"id": sid, "doc": "demo_text", "marker": M, "append_notes": "corrected (%s)" % M}
    f.update(k)
    return f


class StoryFix(unittest.TestCase):
    def test_module_and_marker(self):
        import story_fix
        self.assertEqual(story_fix.MARK, M)

    def test_check_writes_nothing_then_apply_edits_like_the_dashboard(self):
        d, db = make_db()
        f = [fix(replace=[{"field": "story_en", "old": "leaving the city behind", "new": "leaving the town behind"}],
                 set={"why": "Rama and Sita go into exile."})]
        code, out = run(d, db, f, "--check")
        self.assertEqual(code, 0, out); self.assertIn("CHECK OK", out)
        self.assertEqual(row(db, 1)["status"], "approved")
        code, out = run(d, db, f)
        self.assertEqual(code, 0, out)
        r = row(db, 1)
        self.assertIn("leaving the town behind", r["story_en"])
        self.assertEqual(r["why"], "Rama and Sita go into exile.")
        self.assertEqual(r["status"], "draft"); self.assertIsNone(r["approved_at"])
        self.assertTrue(json.loads(r["verify"])["ok"]); self.assertIn("1.6", json.loads(r["cites"]))
        self.assertTrue(r["notes"].startswith("first notes\n")); self.assertIn(M, r["notes"])
        self.assertEqual(row(db, 2)["story_en"], STORY)
        code, out = run(d, db, f)          # a second run changes nothing
        self.assertEqual(code, 0, out); self.assertIn("skip #1", out)

    def test_all_or_nothing(self):
        d, db = make_db()
        f = [fix(1, replace=[{"field": "story_en", "old": "leaving the city behind", "new": "leaving it"}]),
             fix(2, replace=[{"field": "story_en", "old": "this text is not there", "new": "x"}])]
        code, out = run(d, db, f)
        self.assertEqual(code, 1, out); self.assertIn("Nothing written", out)
        self.assertEqual(row(db, 1)["story_en"], STORY); self.assertEqual(row(db, 1)["status"], "approved")

    def test_anchor_must_be_unique(self):
        d, db = make_db()
        code, out = run(d, db, [fix(replace=[{"field": "story_en", "old": "the hut", "new": "a hut"}])])
        self.assertEqual(code, 1, out); self.assertIn("occurs", out)

    def test_whole_field_needs_the_reviewed_md5(self):
        d, db = make_db()
        new = STORY.replace("small hut", "little hut")
        code, out = run(d, db, [fix(set={"story_en": new}, md5={"story_en": "0" * 32})])
        self.assertEqual(code, 1, out); self.assertIn("not the text that was reviewed", out)
        code, out = run(d, db, [fix(set={"story_en": new})])
        self.assertEqual(code, 1, out); self.assertIn("needs its md5", out)
        h = hashlib.md5(STORY.encode("utf-8")).hexdigest()
        code, out = run(d, db, [fix(set={"story_en": new}, md5={"story_en": h})])
        self.assertEqual(code, 0, out); self.assertIn("little hut", row(db, 1)["story_en"])

    def test_span_replace(self):
        d, db = make_db()
        f = [fix(replace=[{"field": "story_en", "from": "One day a golden deer", "to": "[1.5]",
                           "new": "One day a deer of gold came near the hut. [1.5]"}])]
        code, out = run(d, db, f, "--check")
        self.assertEqual(code, 0, out); self.assertIn("replaces", out)
        code, out = run(d, db, f)
        self.assertEqual(code, 0, out)
        s = row(db, 1)["story_en"]
        self.assertIn("a deer of gold came near the hut. [1.5] Sita asked", s); self.assertNotIn("like fire", s)

    def test_a_correction_that_fails_the_check_is_refused(self):
        d, db = make_db()
        bad = [{"field": "story_en", "old": "leaving the city behind", "new": "pursued by Ravana"}]
        code, out = run(d, db, [fix(replace=bad)])
        self.assertEqual(code, 1, out); self.assertIn("Ravana", out); self.assertEqual(row(db, 1)["story_en"], STORY)
        code, out = run(d, db, [fix(replace=bad, allow_fail=True)])
        self.assertEqual(code, 0, out)
        self.assertFalse(json.loads(row(db, 1)["verify"])["ok"])

    def test_retired_wrong_doc_and_missing_marker_are_refused(self):
        d, db = make_db(status="retired")
        code, out = run(d, db, [fix(replace=[{"field": "story_en", "old": "leaving the city behind", "new": "x"}])])
        self.assertEqual(code, 1, out); self.assertIn("retired", out)
        d, db = make_db()
        code, out = run(d, db, [dict(fix(), doc="other_text")])
        self.assertEqual(code, 1, out); self.assertIn("belongs to demo_text", out)
        code, out = run(d, db, [dict(fix(), append_notes="no marker here")])
        self.assertEqual(code, 1, out); self.assertIn("must carry the marker", out)

    def test_the_repo_fix_file_is_well_formed(self):
        p = ROOT / "docs" / "stories" / "fix_markandeya_2026-10-07.json"
        fixes = json.loads(p.read_text(encoding="ascii"))
        self.assertEqual([f["id"] for f in fixes], [3, 5, 10])
        for f in fixes:
            self.assertEqual(f["marker"], M); self.assertIn(M, f["append_notes"])
        self.assertEqual(sorted(fixes[2]["md5"]), ["story_en", "story_hi"])


if __name__ == "__main__":
    unittest.main()
