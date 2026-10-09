# -*- coding: ascii -*-
"""CORPUS_MEDIA_C8_2026_10_09 against a real PostgreSQL: docs/cloud/C8 (pictures and graphic novels in
the working corpus). Applies the Supabase stand-ins, C4, C4b, C5, C7a and C8 (twice), writes through
the desk's functions as service_role, and reads as anon, as a signed-in reader and as an admin.

Skipped unless CORPUS_TEST_DSN names a THROWAWAY database you own. Never points at the live one.
  python -m unittest tests.test_corpus_media_pg_2026_10_09
"""
import json, os, unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
DSN = os.environ.get("CORPUS_TEST_DSN", "")
CLOUD = REPO / "docs" / "cloud"
FILES = [REPO / "tests" / "supabase_stubs_2026_10_08.sql", CLOUD / "C4_corpus_mirror_2026-10-08.sql",
         CLOUD / "C4b_mirror_digests_2026-10-08.sql", CLOUD / "C5_corpus_reader_2026-10-08.sql",
         CLOUD / "C7a_rbac_roles_2026-10-08.sql", CLOUD / "C8_corpus_media_2026-10-09.sql",
         CLOUD / "C8_corpus_media_2026-10-09.sql"]
READER = "33333333-3333-3333-3333-333333333333"
ADMIN = "44444444-4444-4444-4444-444444444444"
SHA = lambda c: c * 64
READERS = ["SELECT * FROM public.corpus_reader_media()", "SELECT * FROM public.corpus_reader_novels()",
           "SELECT * FROM public.corpus_reader_novel(1)",
           "SELECT * FROM public.corpus_reader_media_file('%s', 'thumb')" % ("a" * 64)]
DESK = ["SELECT public.corpus_media_state()", "SELECT public.corpus_media_upsert('[]')",
        "SELECT public.corpus_novels_upsert('[]')", "SELECT public.corpus_media_retire(NULL, NULL)",
        "SELECT public.corpus_media_file_get('x', 'thumb')", "SELECT public.corpus_media_file_put('{}')",
        "SELECT public.corpus_media_config_get('drive_folder')",
        "SELECT public.corpus_media_config_set('drive_folder', 'x')"]


def media(key, doc, status="approved", sha="a", **kw):
    row = {"media_key": key, "doc_code": doc, "kind": kw.pop("kind", "generated"), "status": status,
           "title": kw.pop("title", key), "caption_en": "An illustration", "caption_hi": None, "context_note": None,
           "anchor_page": kw.pop("anchor_page", 1), "anchor_idx": kw.pop("anchor_idx", 1), "anchor_verse_ref": None,
           "story_id": kw.pop("story_id", None), "novel_id": kw.pop("novel_id", None), "seq": kw.pop("seq", None),
           "version": 1, "width": 1408, "height": 768, "sha256": SHA(sha), "model": "gemini-3.1-flash-image",
           "license": "generated", "provenance": "{}", "created_at_local": "2026-10-07T10:00:00",
           "approved_at_local": None}
    row.update(kw)
    row["row_hash"] = kw.get("row_hash", "h-" + key + "-" + status + "-" + sha)
    return row


def novel(nid, doc, status, **kw):
    row = {"novel_id": nid, "doc_code": doc, "story_id": kw.pop("story_id", 34), "status": status,
           "audience": "general", "title": "Novel %d" % nid, "title_hi": None, "pages": 2,
           "plan": {"title": "Novel %d" % nid, "cast": [{"name": "Hari", "look": "blue"}],
                    "pages": [{"n": 1, "scene": "s1", "caption": "One. [13.9]", "caption_hi": "", "speech": [],
                               "cites": ["13.9"]},
                              {"n": 2, "scene": "s2", "caption": "Two. [13.10]", "caption_hi": "", "speech": [],
                               "cites": ["13.10"]}]},
           "verify": {"ok": True}, "cover_seq": 1, "model": "m", "image_model": "im", "aspect": "3:4",
           "provenance": "{}", "created_at_local": "x", "updated_at_local": "x", "approved_at_local": None}
    row.update(kw)
    row["row_hash"] = kw.get("row_hash", "n-%d-%s" % (nid, status))
    return row


@unittest.skipUnless(DSN, "CORPUS_TEST_DSN is not set")
class Media(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        import psycopg
        if "supabase.co" in DSN or "pooler" in DSN:
            raise unittest.SkipTest("refusing to run against a Supabase host")
        cls.pg = psycopg.connect(DSN, autocommit=True)
        for f in FILES:
            cls.pg.execute(f.read_text(encoding="utf-8"))

    @classmethod
    def tearDownClass(cls):
        cls.pg.close()

    def setUp(self):
        x = self.pg.execute
        x("TRUNCATE corpus.media_files, corpus.media, corpus.novels, corpus.media_config, corpus.stories, "
          "corpus.passages, corpus.docs CASCADE")
        x("UPDATE corpus.reader_access SET mode = 'signed_in'")
        x("INSERT INTO public.user_roles VALUES (%s, 'admin') ON CONFLICT DO NOTHING", (ADMIN,))
        x("INSERT INTO corpus.docs (doc_code, title, row_hash) VALUES ('mark', 'Markandeya', 'x'), ('nil', 'Nilamata', 'x')")
        x("INSERT INTO corpus.docs (doc_code, title, row_hash, retired_at) VALUES ('gone', 'Gone', 'x', now())")
        x("INSERT INTO corpus.stories (doc_code, story_id, status, title, row_hash) VALUES "
          "('nil', 34, 'approved', 'The lake', 'x')")

    def desk(self, sql, args=()):
        with self.pg.transaction():
            self.pg.execute("SET LOCAL ROLE service_role")
            return self.pg.execute(sql, args).fetchall()

    def call(self, sql, args=(), role="authenticated", uid=READER):
        with self.pg.transaction(force_rollback=True):
            self.pg.execute("SET LOCAL ROLE %s" % role)
            if uid:
                self.pg.execute("SELECT set_config('request.jwt.claim.sub', %s, true)", (uid,))
            try:
                with self.pg.transaction():
                    return self.pg.execute(sql, args).fetchall()
            except Exception as e:
                return "ERROR: " + str(e).splitlines()[0]

    def load(self):
        rows = [media("img:1", "mark", "approved", "a", story_id=None, anchor_page=2, anchor_idx=3),
                media("img:2", "mark", "draft", "b"),
                media("img:3", "nil", "approved", "c", story_id=34),
                media("novel:1:page:1", "nil", "approved", "d", kind="novel_page", novel_id=1, seq=1),
                media("novel:1:page:2", "nil", "draft", "e", kind="novel_page", novel_id=1, seq=2),
                media("novel:1:cast:1", "nil", "draft", "f", kind="novel_cast", novel_id=1, seq=1),
                media("novel:2:page:1", "nil", "approved", "9", kind="novel_page", novel_id=2, seq=1)]
        self.assertEqual(self.desk("SELECT public.corpus_media_upsert(%s::jsonb)", (json.dumps(rows),)), [(7,)])
        nov = [novel(1, "nil", "drawing"), novel(2, "nil", "approved", approved_at_local="2026-10-09")]
        self.assertEqual(self.desk("SELECT public.corpus_novels_upsert(%s::jsonb)", (json.dumps(nov),)), [(2,)])
        for sha, r in (("a", "thumb"), ("a", "display"), ("c", "thumb"), ("d", "thumb"), ("9", "display")):
            self.desk("SELECT public.corpus_media_file_put(%s::jsonb)", (json.dumps({
                "sha256": SHA(sha), "rendition": r, "file_id": "drive-" + sha + "-" + r, "mime": "image/jpeg",
                "bytes": 1000, "width": 480, "height": 262, "file_sha256": SHA("0")}),))

    # ---- who may call what

    def test_grants(self):
        for sql in READERS:
            with self.subTest(sql=sql):
                self.assertIn("permission denied", self.call(sql, role="anon", uid=None))
                self.assertIn("signed-in readers only", self.call(sql, uid=None))
        for sql in DESK:
            with self.subTest(sql=sql):
                self.assertIn("permission denied", self.call(sql))
                self.assertIn("permission denied", self.call(sql, role="anon", uid=None))
        self.assertIn("permission denied", self.call("SELECT * FROM corpus.media"))

    # ---- the desk's side

    def test_upsert_is_idempotent_by_row_hash_and_retire_unretire(self):
        self.load()
        rows = [media("img:1", "mark", "approved", "a", anchor_page=2, anchor_idx=3)]
        self.assertEqual(self.desk("SELECT public.corpus_media_upsert(%s::jsonb)", (json.dumps(rows),)), [(0,)])
        rows[0]["row_hash"] = "changed"; rows[0]["title"] = "New title"
        self.assertEqual(self.desk("SELECT public.corpus_media_upsert(%s::jsonb)", (json.dumps(rows),)), [(1,)])
        self.assertEqual(self.desk("SELECT public.corpus_media_retire(ARRAY['img:1','nope'], ARRAY[1])"),
                         [({"media": 1, "novels": 1},)])
        st = self.desk("SELECT public.corpus_media_state()")[0][0]
        self.assertNotIn("img:1", st["media"]); self.assertNotIn("1", st["novels"])
        self.assertEqual(self.desk("SELECT public.corpus_media_upsert(%s::jsonb)", (json.dumps(rows),)), [(1,)])
        st = self.desk("SELECT public.corpus_media_state()")[0][0]
        self.assertEqual(st["media"]["img:1"], "changed")
        self.assertEqual(st["docs"], ["mark", "nil"])
        self.assertIn(SHA("a") + ":thumb", st["files"])
        self.assertIsNone(st["drive_folder"])
        self.desk("SELECT public.corpus_media_config_set('drive_folder', 'FOLDER123')")
        self.assertEqual(self.desk("SELECT public.corpus_media_state()")[0][0]["drive_folder"], "FOLDER123")
        self.assertEqual(self.desk("SELECT public.corpus_media_config_get('drive_folder')"), [("FOLDER123",)])

    def test_file_put_once_and_get(self):
        self.load()
        again = {"sha256": SHA("a"), "rendition": "thumb", "file_id": "other-id-123", "mime": "image/jpeg",
                 "bytes": 5, "file_sha256": SHA("1")}
        self.assertEqual(self.desk("SELECT public.corpus_media_file_put(%s::jsonb)", (json.dumps(again),)), [(False,)])
        got = self.desk("SELECT public.corpus_media_file_get(%s, 'thumb')", (SHA("a"),))[0][0]
        self.assertEqual(got["file_id"], "drive-a-thumb")
        self.assertEqual(self.desk("SELECT public.corpus_media_file_get(%s, 'display')", (SHA("c"),)), [(None,)])

    def test_bad_rows_are_refused(self):
        for bad, msg in [(media("pic:1", "mark"), "media_media_key_check"),
                         (media("img:9", "mark", "brief"), "media_status_check"),
                         (media("img:9", "unknown_doc"), "foreign key"),
                         (media("img:9", "mark", sha="z"), "media_sha256_check")]:
            with self.subTest(msg=msg):
                try:
                    self.desk("SELECT public.corpus_media_upsert(%s::jsonb)", (json.dumps([bad]),))
                    self.fail("accepted")
                except Exception as e:
                    self.assertIn(msg, str(e))
        try:
            self.desk("SELECT public.corpus_media_upsert(%s::jsonb)", (json.dumps([media("img:1", "mark")] * 501),))
            self.fail("accepted")
        except Exception as e:
            self.assertIn("at most 500", str(e))

    # ---- the readers' side

    def test_pictures_approved_for_readers_drafts_for_editors_never_novel_pages(self):
        self.load()
        r = self.call("SELECT media_key, has_thumb, has_display, total FROM public.corpus_reader_media()")
        self.assertEqual(r, [("img:1", True, True, 2), ("img:3", True, False, 2)])
        r = self.call("SELECT media_key, status FROM public.corpus_reader_media()", uid=ADMIN)
        self.assertEqual(r, [("img:2", "draft"), ("img:1", "approved"), ("img:3", "approved")])   # by anchor: 1.1, 2.3
        self.assertEqual(self.call("SELECT media_key FROM public.corpus_reader_media(NULL, 34)"), [("img:3",)])
        self.assertEqual(self.call("SELECT media_key FROM public.corpus_reader_media('mark')"), [("img:1",)])
        self.assertEqual(self.call("SELECT doc_title FROM public.corpus_reader_media('nil')"), [("Nilamata",)])

    def test_novels_list_and_one_novel(self):
        self.load()
        r = self.call("SELECT novel_id, status, story_title, cover_sha, cover_has_thumb FROM public.corpus_reader_novels()")
        self.assertEqual(r, [(2, "approved", "The lake", SHA("9"), False)])
        r = self.call("SELECT novel_id, status, cover_sha, cover_has_thumb FROM public.corpus_reader_novels()", uid=ADMIN)
        self.assertEqual(r, [(1, "drawing", SHA("d"), True), (2, "approved", SHA("9"), False)])
        self.assertEqual(self.call("SELECT * FROM public.corpus_reader_novel(1)"), [])
        r = self.call("SELECT novel_id, plan->'pages'->0->>'caption', media FROM public.corpus_reader_novel(1)", uid=ADMIN)
        self.assertEqual(r[0][1], "One. [13.9]")
        keys = [(m["key"], m["has_thumb"]) for m in r[0][2]]
        self.assertEqual(keys, [("novel:1:page:1", True), ("novel:1:page:2", False), ("novel:1:cast:1", False)])
        r = self.call("SELECT novel_id, jsonb_array_length(media) FROM public.corpus_reader_novel(2)")
        self.assertEqual(r, [(2, 1)])

    def test_media_file_follows_visibility(self):
        self.load()
        f = lambda sha, rnd="thumb", uid=READER: self.call(
            "SELECT file_id FROM public.corpus_reader_media_file(%s, %s)", (SHA(sha), rnd), uid=uid)
        self.assertEqual(f("a"), [("drive-a-thumb",)])
        self.assertEqual(f("c"), [("drive-c-thumb",)])
        self.assertEqual(f("d"), [])                      # a page of a novel still being drawn
        self.assertEqual(f("d", uid=ADMIN), [("drive-d-thumb",)])
        self.assertEqual(f("9", "display"), [("drive-9-display",)])   # a page of an approved novel
        self.assertEqual(f("b", uid=ADMIN), [])           # a draft with no file yet
        self.assertEqual(self.call("SELECT * FROM public.corpus_reader_media_file('nothex', 'thumb')"), [])
        self.assertEqual(self.call("SELECT * FROM public.corpus_reader_media_file(%s, 'huge')", (SHA("a"),)), [])

    def test_retired_and_gone_are_hidden_and_the_gate_applies(self):
        self.load()
        self.desk("SELECT public.corpus_media_retire(ARRAY['img:1'], NULL)")
        self.assertEqual(self.call("SELECT media_key FROM public.corpus_reader_media()"), [("img:3",)])
        self.assertEqual(self.call("SELECT file_id FROM public.corpus_reader_media_file(%s, 'thumb')", (SHA("a"),)), [])
        self.pg.execute("UPDATE corpus.docs SET retired_at = now() WHERE doc_code = 'nil'")
        self.assertEqual(self.call("SELECT media_key FROM public.corpus_reader_media()", uid=ADMIN), [("img:2",)])
        self.assertEqual(self.call("SELECT * FROM public.corpus_reader_novels()", uid=ADMIN), [])
        self.pg.execute("UPDATE corpus.reader_access SET mode = 'admins'")
        self.assertIn("signed-in readers only", self.call("SELECT * FROM public.corpus_reader_media()"))
        self.assertIsInstance(self.call("SELECT * FROM public.corpus_reader_media()", uid=ADMIN), list)


if __name__ == "__main__":
    unittest.main()
