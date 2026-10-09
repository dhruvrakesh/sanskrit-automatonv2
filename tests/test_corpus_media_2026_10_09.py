# -*- coding: ascii -*-
"""CORPUS_MEDIA_C8_2026_10_09: scripts/corpus_media.py (the desk's push of pictures and graphic novels).

A temporary repo root with real JPEG/PNG files (Pillow), a small context.db, and a fake site that
behaves as C8 does (upsert only where row_hash differs, retire, files once per sha:rendition).
The PostgreSQL end-to-end test at the bottom runs only with CORPUS_TEST_DSN (a throwaway database).
  python -m unittest tests.test_corpus_media_2026_10_09 -v
"""
import base64, gzip, hashlib, io, json, os, shutil, sqlite3, sys, tempfile, unittest
from pathlib import Path
from unittest import mock

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "scripts"))
import corpus_media as cm  # noqa: E402
import corpus_sync as cs  # noqa: E402

DSN = os.environ.get("CORPUS_TEST_DSN", "")


def jpeg(path: Path, size=(2000, 1200), color=(180, 120, 60), mode="RGB", fmt="JPEG"):
    from PIL import Image
    path.parent.mkdir(parents=True, exist_ok=True)
    im = Image.new(mode, size, color)
    im.save(path, fmt)
    return hashlib.sha256(path.read_bytes()).hexdigest()


class FakeSite:
    """What C8 does, in memory."""
    name = "fake"

    def __init__(self, docs):
        self.docs = sorted(docs)
        self.media, self.novels, self.files = {}, {}, {}
        self.retired_media, self.retired_novels = set(), set()
        self.calls = []

    def state(self):
        self.calls.append("state")
        return {"scheme": cm.SCHEME, "docs": self.docs,
                "media": {k: r["row_hash"] for k, r in self.media.items() if k not in self.retired_media},
                "novels": {str(k): r["row_hash"] for k, r in self.novels.items() if k not in self.retired_novels},
                "files": sorted(self.files), "drive_folder": "folder-1"}

    def _upsert(self, store, retired, key, rows):
        n = 0
        for r in rows:
            k = r[key]
            if k in store and store[k]["row_hash"] == r["row_hash"] and k not in retired:
                continue
            store[k] = dict(r)
            retired.discard(k)
            n += 1
        return n

    def upsert_media(self, rows):
        self.calls.append(("upsert_media", len(rows)))
        assert 0 < len(rows) <= 500
        for r in rows:
            assert r["doc_code"] in self.docs and len(r["sha256"]) == 64 and r["row_hash"]
        return self._upsert(self.media, self.retired_media, "media_key", rows)

    def upsert_novels(self, rows):
        self.calls.append(("upsert_novels", len(rows)))
        return self._upsert(self.novels, self.retired_novels, "novel_id", rows)

    def retire(self, media, novels):
        self.calls.append(("retire", list(media), list(novels)))
        a = [k for k in media if k in self.media and k not in self.retired_media]
        b = [k for k in novels if k in self.novels and k not in self.retired_novels]
        self.retired_media.update(a)
        self.retired_novels.update(b)
        return {"media": len(a), "novels": len(b)}

    def upload(self, meta, data):
        self.calls.append(("upload", meta["sha256"][:8], meta["rendition"]))
        assert hashlib.sha256(data).hexdigest() == meta["file_sha256"]
        k = "%s:%s" % (meta["sha256"], meta["rendition"])
        if k in self.files:
            return {"skipped": True, "file_id": self.files[k]["file_id"]}
        self.files[k] = dict(meta, bytes=len(data), file_id="drive-%d" % len(self.files), data=data)
        return {"uploaded": True, "file_id": self.files[k]["file_id"]}

    def count(self, kind):
        return sum(1 for c in self.calls if isinstance(c, tuple) and c[0] == kind)


SCHEMA = """
CREATE TABLE docs(id INTEGER PRIMARY KEY, code TEXT, category TEXT, src_path TEXT, glossary TEXT, created_at TEXT);
CREATE TABLE doc_images(id INTEGER PRIMARY KEY, doc_id INTEGER, lineage_id INTEGER, version INTEGER, kind TEXT,
  status TEXT, title TEXT, brief TEXT, context_note TEXT, caption_en TEXT, caption_hi TEXT, anchor_page INTEGER,
  anchor_idx INTEGER, anchor_verse_ref TEXT, path TEXT, sha256 TEXT, mime TEXT, width INTEGER, height INTEGER,
  model TEXT, prompt_hash TEXT, provenance TEXT, license TEXT, created_at TEXT, updated_at TEXT, approved_at TEXT,
  retired_at TEXT);
CREATE TABLE doc_stories(id INTEGER PRIMARY KEY, doc_id INTEGER, status TEXT, title TEXT, image_id INTEGER);
CREATE TABLE doc_novels(id INTEGER PRIMARY KEY, story_id INTEGER, doc_id INTEGER, status TEXT, audience TEXT,
  title TEXT, title_hi TEXT, pages INTEGER, plan TEXT, verify TEXT, cast_sheets TEXT, page_images TEXT, model TEXT,
  image_model TEXT, aspect TEXT, provenance TEXT, created_at TEXT, updated_at TEXT, approved_at TEXT);
"""


class Base(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="cmtest_"))
        self.root = self.tmp / "repo"
        imgs = self.root / "data" / "images"
        self.sha = {
            "m3": jpeg(imgs / "Mallapurana" / "3_v1.jpg", (1408, 768), (200, 10, 10)),
            "m4": jpeg(imgs / "Mallapurana" / "4_v1.jpg", (1408, 768), (10, 200, 10)),
            "m5": jpeg(imgs / "Mallapurana" / "5_v1.png", (900, 600), (10, 10, 200, 128), "RGBA", "PNG"),
            "p1": jpeg(imgs / "nilamata_seg" / "novel_1" / "page_01_v1.jpg", (896, 1200), (90, 90, 10)),
            "p2": jpeg(imgs / "nilamata_seg" / "novel_1" / "page_02_v1.jpg", (896, 1200), (10, 90, 90)),
            "p3": jpeg(imgs / "nilamata_seg" / "novel_1" / "page_03_v1.jpg", (896, 1200), (90, 10, 90)),
            "c1": jpeg(imgs / "nilamata_seg" / "novel_1" / "cast_1_v1.jpg", (800, 800), (30, 30, 30)),
        }
        self.db = self.tmp / "context.db"
        con = sqlite3.connect(self.db)
        con.executescript(SCHEMA)
        con.executemany("INSERT INTO docs(id, code) VALUES (?, ?)",
                        [(1, "Mallapurana"), (49, "nilamata_seg"), (7, "not_mirrored")])
        prov = json.dumps({"brief_model": "gemini-2.5-flash", "prompt": "Illustration ... Subject: arenas",
                           "secret_thing": "not for the site", "label": cm.GENERATED_LABEL})
        rows = [
            (3, 1, 1, "generated", "approved", "Arenas", "data\\images\\Mallapurana\\3_v1.jpg", self.sha["m3"], 1408, 768,
             69, 1, prov, "2026-10-03T10:00:00", "2026-10-03T12:00:00", None),
            (4, 1, 1, "generated", "draft", "Stances", "data\\images\\Mallapurana\\4_v1.jpg", self.sha["m4"], 1408, 768,
             73, 10, prov, "2026-10-03T10:00:00", None, None),
            (5, 1, 1, "cover", "approved", "Cover", "data\\images\\Mallapurana\\5_v1.png", "0" * 64, None, None,
             0, 0, "{}", "2026-10-03T10:00:00", "2026-10-04", None),
            (6, 1, 1, "generated", "brief", "Not drawn", None, None, None, None, 1, 1, "{}", None, None, None),
            (8, 1, 1, "generated", "retired", "Old", "data\\images\\Mallapurana\\3_v1.jpg", self.sha["m3"], 1, 1,
             1, 1, "{}", None, None, "2026-10-04"),
            (9, 7, 1, "generated", "approved", "Elsewhere", "data\\images\\Mallapurana\\4_v1.jpg", self.sha["m4"],
             1, 1, 1, 1, "{}", None, None, None),
        ]
        con.executemany("INSERT INTO doc_images(id, doc_id, version, kind, status, title, path, sha256, width, height, "
                        "anchor_page, anchor_idx, provenance, created_at, approved_at, retired_at) "
                        "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)", rows)
        con.execute("UPDATE doc_images SET caption_en='Three arenas', caption_hi='\u0924\u0940\u0928' WHERE id=3")
        con.executemany("INSERT INTO doc_stories(id, doc_id, status, title, image_id) VALUES (?,?,?,?,?)",
                        [(1, 1, "approved", "S1", 3), (2, 1, "approved", "S2", 3), (34, 49, "approved", "Lake", None)])
        win = "D:\\Elsewhere\\sanskrit-automatonv2\\data\\images\\nilamata_seg\\novel_1\\"
        pages = {str(n): {"path": win + "page_%02d_v1.jpg" % n, "sha256": self.sha["p%d" % n], "mime": "image/jpeg",
                          "version": 1, "status": st, "at": "2026-10-07T19:12:09"}
                 for n, st in ((1, "approved"), (2, "draft"), (3, "stale"))}
        cast = {"1": {"path": win + "cast_1_v1.jpg", "sha256": self.sha["c1"], "mime": "image/jpeg", "version": 1,
                      "status": "draft", "at": "2026-10-07T19:10:37", "name": "Hari"},
                "2": {"path": win + "cast_2_v1.jpg", "sha256": "1" * 64, "status": "draft", "name": "Gone"}}
        plan = {"title": "The lake", "title_hi": "\u091d\u0940\u0932", "extra": "dropped",
                "cast": [{"name": "Hari", "look": "blue", "seed": 4}],
                "pages": [{"n": 1, "scene": "s1", "caption": "One. [13.9]", "caption_hi": "\u090f\u0915",
                           "speech": [{"who": "Hari", "line": "Go.", "cite": "13.9", "x": 1}], "cites": ["13.9"],
                           "prompt": "dropped"},
                          {"n": 2, "scene": "s2", "caption": "Two. [13.10]", "speech": [], "cites": ["13.10"]},
                          {"n": 3, "scene": "s3", "caption": "Three.", "speech": [], "cites": []}]}
        verify = {"ok": False, "problems": ["one"], "cited": ["13.9", "13.10"], "pages": 3, "checked_at": "x", "raw": "z"}
        con.execute("INSERT INTO doc_novels VALUES (1, 34, 49, 'drawing', 'general', 'The lake', NULL, 3, ?, ?, ?, ?, "
                    "'gemini-2.5-flash', 'gemini-3.1-flash-image', '3:4', ?, '2026-10-07', '2026-10-08', NULL)",
                    (json.dumps(plan), json.dumps(verify), json.dumps(cast), json.dumps(pages),
                     json.dumps({"story": 34, "variant": False, "prompt_hash": "e26e"})))
        con.execute("INSERT INTO doc_novels(id, story_id, doc_id, status, plan, page_images, cast_sheets) "
                    "VALUES (2, 34, 49, 'retired', '{}', '{}', '{}')")
        con.commit()
        con.close()
        self.site = FakeSite(["Mallapurana", "nilamata_seg"])

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def con(self):
        return cs.open_ro(str(self.db))

    def run_once(self, apply=True, max_mb=None, only=None, **kw):
        con = self.con()
        try:
            docs = cs.live_docs(con)
            if only:
                docs = [d for d in docs if d[1] in only]
            pics, novels, notes, stats = cm.collect(con, docs, only, root=self.root)
        finally:
            con.close()
        run = cm.Run(self.site, apply, None if max_mb is None else int(max_mb * 1e6), **kw)
        return run.execute(pics, novels, notes, stats, only)

    def rw(self, sql, args=()):
        con = sqlite3.connect(self.db)
        con.execute(sql, args)
        con.commit()
        con.close()


class Collect(Base):
    def test_what_is_collected(self):
        con = self.con()
        pics, novels, notes, stats = cm.collect(con, cs.live_docs(con), root=self.root)
        con.close()
        self.assertEqual(sorted(pics), ["img:3", "img:4", "img:5", "img:9", "novel:1:cast:1",
                                        "novel:1:page:1", "novel:1:page:2"])
        self.assertEqual(sorted(novels), [1])                 # #2 is retired
        self.assertEqual(stats["briefs"], 1)
        self.assertEqual(stats["retired"], 1)
        self.assertEqual(stats["stale"], 1)                   # page 3 is drawn again before it travels
        self.assertEqual(stats["keep"], {"novel:1:cast:2"})   # its file is missing: kept, not retired
        r = pics["img:3"].row
        self.assertEqual((r["doc_code"], r["kind"], r["status"], r["story_id"], r["anchor_page"], r["anchor_idx"]),
                         ("Mallapurana", "generated", "approved", 1, 69, 1))   # the first story that uses it
        self.assertEqual(r["caption_hi"], "\u0924\u0940\u0928")
        prov = json.loads(r["provenance"])
        self.assertEqual(prov["label"], cm.GENERATED_LABEL)
        self.assertIn("prompt", prov)
        self.assertNotIn("secret_thing", prov)               # only the known keys travel
        c = pics["img:5"].row                                 # recorded sha256 is wrong: the file's is sent
        self.assertEqual(c["sha256"], self.sha["m5"])
        self.assertEqual((c["width"], c["height"]), (900, 600))   # read from the file when not recorded
        self.assertTrue(any("img:5" in n and "sha256 differs" in n for n in notes))
        p1 = pics["novel:1:page:1"]
        self.assertEqual(p1.path, self.root / "data" / "images" / "nilamata_seg" / "novel_1" / "page_01_v1.jpg")
        self.assertEqual((p1.row["kind"], p1.row["seq"], p1.row["novel_id"], p1.row["title"], p1.row["story_id"]),
                         ("novel_page", 1, 1, "Page 1", 34))
        self.assertEqual(pics["novel:1:cast:1"].row["title"], "Hari")
        n = novels[1]
        self.assertEqual(n["plan"]["pages"][0], {"n": 1, "scene": "s1", "caption": "One. [13.9]",
                                                 "caption_hi": "\u090f\u0915",
                                                 "speech": [{"who": "Hari", "line": "Go.", "cite": "13.9"}],
                                                 "cites": ["13.9"]})
        self.assertNotIn("extra", n["plan"])
        self.assertEqual(n["plan"]["cast"], [{"name": "Hari", "look": "blue"}])
        self.assertEqual(n["verify"], {"ok": False, "problems": ["one"], "cited": ["13.9", "13.10"], "pages": 3,
                                       "checked_at": "x"})
        self.assertEqual(json.loads(n["provenance"]), {"prompt_hash": "e26e", "story": 34, "variant": False})

    def test_paths(self):
        root = self.root
        self.assertEqual(cm.resolve_path("data\\images\\Mallapurana\\3_v1.jpg", root),
                         root / "data/images/Mallapurana/3_v1.jpg")
        self.assertEqual(cm.resolve_path("D:\\x\\y\\data\\images\\Mallapurana\\3_v1.jpg", root),
                         root / "data/images/Mallapurana/3_v1.jpg")
        self.assertEqual(cm.resolve_path(str(root / "data/images/Mallapurana/4_v1.jpg"), root),
                         root / "data/images/Mallapurana/4_v1.jpg")
        self.assertIsNone(cm.resolve_path("D:\\nowhere\\pic.jpg", root))
        self.assertIsNone(cm.resolve_path(None, root))

    def test_renditions(self):
        from PIL import Image
        for key, px in (("m3", 480), ("m3", 1600), ("m5", 480)):
            name = "3_v1.jpg" if key == "m3" else "5_v1.png"
            data, w, h = cm.make_rendition(self.root / "data/images/Mallapurana" / name, px, 80)
            im = Image.open(io.BytesIO(data))
            self.assertEqual(im.format, "JPEG")
            self.assertEqual(im.size, (w, h))
            self.assertLessEqual(max(w, h), px)
            if key == "m3" and px == 1600:
                self.assertEqual((w, h), (1408, 768))         # never enlarged
            if key == "m5":
                self.assertEqual(im.mode, "RGB")
                r, g, b = im.getpixel((10, 10))
                self.assertGreater(r, 100)                    # half-transparent blue on white, not on black


class Push(Base):
    def test_plan_sends_nothing(self):
        s = self.run_once(apply=False)
        self.assertEqual(self.site.calls, ["state"])
        self.assertEqual(s["files"]["to_upload"], 12)         # 6 pictures that may go x 2 renditions
        self.assertEqual(s["media"]["upsert"], 6)
        self.assertEqual(s["novels"]["upsert"], 1)
        self.assertTrue(any("img:9" in h and "not in the mirror" in h for h in s["held"]))

    def test_push_then_nothing(self):
        s = self.run_once()
        self.assertEqual(s["stopped"], "done", s)
        self.assertEqual(s["files"]["uploaded"], 12)
        self.assertEqual(len(self.site.files), 12)
        for k, f in self.site.files.items():
            self.assertLessEqual(max(f["width"], f["height"]), 480 if k.endswith(":thumb") else 1600)
            self.assertEqual(f["mime"], "image/jpeg")
        self.assertEqual(sorted(self.site.media), ["img:3", "img:4", "img:5", "novel:1:cast:1", "novel:1:page:1",
                                                   "novel:1:page:2"])
        self.assertEqual(list(self.site.novels), [1])
        kinds = [c[0] for c in self.site.calls if isinstance(c, tuple)]
        self.assertLess(kinds.index("upload"), kinds.index("upsert_novels"))
        self.assertLess(kinds.index("upsert_novels"), kinds.index("upsert_media"))   # the novel before its pages
        self.assertEqual(s["media"]["changed"], 6)
        self.site.calls.clear()
        s2 = self.run_once()
        self.assertEqual(self.site.calls, ["state"])          # nothing changed: nothing sent
        self.assertEqual((s2["files"]["to_upload"], s2["media"]["upsert"], s2["novels"]["upsert"]), (0, 0, 0))

    def test_changes_travel_and_gone_is_retired(self):
        self.run_once()
        self.site.calls.clear()
        self.rw("UPDATE doc_images SET caption_en='Three arenas, mended' WHERE id=3")
        s = self.run_once()
        self.assertEqual(self.site.count("upload"), 0)
        self.assertEqual((s["media"]["upsert"], s["media"]["changed"]), (1, 1))
        self.assertEqual(self.site.media["img:3"]["caption_en"], "Three arenas, mended")
        # a new version of a picture: its renditions go first, then the row
        jpeg(self.root / "data/images/Mallapurana/4_v2.jpg", (1408, 768), (1, 2, 3))
        self.rw("UPDATE doc_images SET path='data\\images\\Mallapurana\\4_v2.jpg', version=2 WHERE id=4")
        self.site.calls.clear()
        s = self.run_once()
        self.assertEqual(self.site.count("upload"), 2)
        self.assertEqual(s["media"]["changed"], 1)
        # retired here: retired there; the novel retired: it and its pictures
        self.rw("UPDATE doc_images SET status='retired', retired_at='2026-10-09' WHERE id=4")
        self.rw("UPDATE doc_novels SET status='retired' WHERE id=1")
        s = self.run_once()
        self.assertEqual(s["media"]["retired"], 4)
        self.assertEqual(s["novels"]["retired"], 1)
        self.assertEqual(self.site.retired_media, {"img:4", "novel:1:cast:1", "novel:1:page:1", "novel:1:page:2"})
        # and it comes back
        self.rw("UPDATE doc_images SET status='draft', retired_at=NULL WHERE id=4")
        s = self.run_once()
        self.assertEqual(s["media"]["changed"], 1)
        self.assertNotIn("img:4", self.site.retired_media)

    def test_a_missing_file_is_not_retired(self):
        self.run_once()
        (self.root / "data/images/Mallapurana/3_v1.jpg").rename(self.root / "data/images/Mallapurana/moved.jpg")
        s = self.run_once()
        self.assertEqual(s["media"]["retire"], 0)
        self.assertTrue(any("img:3" in n and "missing" in n for n in s["notes"]))

    def test_budget_holds_rows_until_their_files_are_up(self):
        s = self.run_once(max_mb=0.000001)                    # stops after the first upload
        self.assertEqual(s["stopped"], "budget")
        self.assertEqual(self.site.count("upload"), 1)
        self.assertEqual(self.site.media, {})                 # no row without its pictures
        for _ in range(20):
            s = self.run_once(max_mb=0.000001)
            if s["stopped"] == "done":
                break
        self.assertEqual(s["stopped"], "done")
        self.assertEqual(len(self.site.files), 12)
        self.assertEqual(len(self.site.media), 6)

    def test_doc_never_retires_and_mass_retire_is_refused(self):
        self.run_once()
        self.rw("UPDATE doc_images SET status='retired' WHERE id IN (3, 4, 5)")
        s = self.run_once(only={"nilamata_seg"})
        self.assertEqual(s["media"]["retired"], 0)
        self.assertIn("retire skipped (--doc)", s["notes"])
        for k in range(20):                                   # a site with many more pictures than here
            self.site.media["img:%d" % (1000 + k)] = {"row_hash": "x", "media_key": "img:%d" % (1000 + k)}
        with self.assertRaises(cm.SinkError):
            self.run_once()
        s = self.run_once(allow_mass_retire=True)
        self.assertEqual(s["media"]["retired"], 23)

    def test_document_not_in_the_mirror_is_held(self):
        self.site.docs = ["Mallapurana"]
        s = self.run_once()
        self.assertTrue(any("novel #1" in h for h in s["held"]))
        self.assertTrue(any("novel:1:page:1" in h and "not in the mirror" in h for h in s["held"]))
        self.assertEqual(sorted(self.site.media), ["img:3", "img:4", "img:5"])

    def test_wrong_scheme_is_an_error(self):
        self.site.state = lambda: {"scheme": "media.0"}
        with self.assertRaises(cm.SinkError):
            self.run_once()


class Edge(unittest.TestCase):
    def test_requests_are_signed_gzip_with_the_publishable_key(self):
        seen = []

        class R:
            def __init__(self, body): self.body = body
            def read(self): return self.body
            def __enter__(self): return self
            def __exit__(self, *a): return False

        def fake(req, timeout=0):
            seen.append(req)
            return R(json.dumps({"ok": True, "result": {"fn": "corpus-media c8.1"}}).encode())

        sink = cm.EdgeSink("https://x.supabase.co/", "anon-key", "s" * 64)
        with mock.patch("urllib.request.urlopen", fake):
            self.assertEqual(sink.hello(), {"fn": "corpus-media c8.1"})
            r = sink.upload({"sha256": "a" * 64, "rendition": "thumb", "mime": "image/jpeg", "width": 1, "height": 1,
                             "file_sha256": hashlib.sha256(b"xyz").hexdigest()}, b"xyz")
        self.assertGreater(r["_sent"], 0)
        req = seen[1]
        self.assertEqual(req.full_url, "https://x.supabase.co/functions/v1/corpus-media")
        h = {k.lower(): v for k, v in req.header_items()}
        self.assertEqual(h["x-corpus-sig"], cs.sign("s" * 64, h["x-corpus-ts"], req.data))
        self.assertEqual((h["apikey"], h["authorization"], h["x-corpus-encoding"]), ("anon-key", "Bearer anon-key", "gzip"))
        body = json.loads(gzip.decompress(req.data))
        self.assertEqual((body["action"], base64.b64decode(body["data"])), ("upload", b"xyz"))

    def test_not_deployed_and_not_applied_are_recognised(self):
        self.assertTrue(cm.not_ready(cm.SinkError("corpus-media HTTP 404: {\"code\":\"NOT_FOUND\"}", 404)))
        self.assertTrue(cm.not_ready(cm.SinkError(
            "corpus-media HTTP 422: corpus_media_state: Could not find the function public.corpus_media_state", 422)))
        self.assertIsNone(cm.not_ready(cm.SinkError("corpus-media HTTP 401: bad signature", 401)))

    def test_if_configured_without_a_secret_is_quiet(self):
        with mock.patch.object(cs, "load_config", lambda: {"secret": "", "url": "", "anon": "", "dsn": ""}):
            self.assertEqual(cm.main(["--if-configured", "--apply"]), 0)


@unittest.skipUnless(DSN, "CORPUS_TEST_DSN is not set")
class PgEndToEnd(Base):
    """The push through PgSink into a database with C8, then read as a reader and as an admin."""
    FILES = ["tests/supabase_stubs_2026_10_08.sql", "docs/cloud/C4_corpus_mirror_2026-10-08.sql",
             "docs/cloud/C4b_mirror_digests_2026-10-08.sql", "docs/cloud/C5_corpus_reader_2026-10-08.sql",
             "docs/cloud/C7a_rbac_roles_2026-10-08.sql", "docs/cloud/C8_corpus_media_2026-10-09.sql"]

    @classmethod
    def setUpClass(cls):
        import psycopg
        if "supabase.co" in DSN or "pooler" in DSN:
            raise unittest.SkipTest("refusing to run against a Supabase host")
        cls.pg = psycopg.connect(DSN, autocommit=True)
        for f in cls.FILES:
            cls.pg.execute((REPO / f).read_text(encoding="utf-8"))

    @classmethod
    def tearDownClass(cls):
        cls.pg.close()

    def setUp(self):
        super().setUp()
        x = self.pg.execute
        x("TRUNCATE corpus.media_files, corpus.media, corpus.novels, corpus.media_config, corpus.stories, "
          "corpus.passages, corpus.docs CASCADE")
        x("UPDATE corpus.reader_access SET mode = 'signed_in'")
        x("INSERT INTO public.user_roles VALUES ('44444444-4444-4444-4444-444444444444', 'admin') ON CONFLICT DO NOTHING")
        x("INSERT INTO corpus.docs (doc_code, title, row_hash) VALUES ('Mallapurana', 'Mallapurana', 'x'), "
          "('nilamata_seg', 'Nilamata', 'x')")
        self.site = cm.PgSink(DSN)

    def tearDown(self):
        self.site.con.close()
        super().tearDown()

    def read(self, sql, uid):
        with self.pg.transaction(force_rollback=True):
            self.pg.execute("SET LOCAL ROLE authenticated")
            self.pg.execute("SELECT set_config('request.jwt.claim.sub', %s, true)", (uid,))
            return self.pg.execute(sql).fetchall()

    def test_push_read_and_push_again(self):
        s = self.run_once()
        self.assertEqual(s["stopped"], "done", s)
        self.assertEqual((s["files"]["uploaded"], s["media"]["changed"], s["novels"]["changed"]), (12, 6, 1))
        reader, admin = "33333333-3333-3333-3333-333333333333", "44444444-4444-4444-4444-444444444444"
        mine = self.read("SELECT media_key, has_thumb, has_display FROM public.corpus_reader_media()", reader)
        self.assertEqual(mine, [("img:5", True, True), ("img:3", True, True)])     # approved only, in page order
        alls = self.read("SELECT media_key FROM public.corpus_reader_media()", admin)
        self.assertEqual(sorted(r[0] for r in alls), ["img:3", "img:4", "img:5"])  # novel pages are not here
        self.assertEqual(self.read("SELECT novel_id FROM public.corpus_reader_novels()", reader), [])
        nov = self.read("SELECT novel_id, status, jsonb_array_length(media), plan->'pages'->0->>'caption' "
                        "FROM public.corpus_reader_novel(1)", admin)
        self.assertEqual(nov, [(1, "drawing", 3, "One. [13.9]")])
        f = self.read("SELECT file_id FROM public.corpus_reader_media_file('%s', 'thumb')" % self.sha["m3"], reader)
        self.assertEqual(len(f), 1)
        s2 = self.run_once()
        self.assertEqual((s2["files"]["to_upload"], s2["media"]["upsert"], s2["novels"]["upsert"]), (0, 0, 0))


if __name__ == "__main__":
    unittest.main()
