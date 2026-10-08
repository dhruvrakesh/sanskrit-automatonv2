# -*- coding: ascii -*-
"""CORPUS_MIRROR_C4_2026_10_08: scripts/corpus_sync.py keeps a private PostgreSQL mirror of the
local brain current, idempotently. These tests need no PostgreSQL and no network:

  - FakeServer emulates the five C4 functions (manifest / keys / ingest / retire / run) in memory,
    with the same rules as docs/cloud/C4_corpus_mirror_2026-10-08.sql;
  - a local HTTP stub checks the HMAC signature and gzip exactly as the corpus-ingest edge
    function does, so EdgeSink is exercised end to end on 127.0.0.1;
  - golden values tie Python to PostgreSQL (the digest, computed by PostgreSQL 16) and to the
    edge function (the signature, also asserted in lib_test.ts).
The real SQL is tested by tests/test_corpus_sync_pg_2026_10_08.py when CORPUS_TEST_DSN is set.
Temp files only, never data/context.db; every connection is closed before cleanup (Windows)."""
import gzip, hashlib, hmac, json, math, sqlite3, struct, sys, tempfile, threading, unittest
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "scripts"))
import corpus_sync as cs  # noqa: E402

GOLDEN_DIGEST = "3c45b2b6931764f9259ed4a12f6add95"   # PostgreSQL 16, see test_digest_matches_postgres
GOLDEN_SIG = "ebbbca6a429aed3e2a14acb6a414b9954119895f96c2640427664324ddc43e16"
OPEN = []


def unit_vec(seed, dim=3072):
    vals = [math.sin(seed * 7.13 + i * 0.37) + 0.01 * ((i * seed) % 5) for i in range(dim)]
    n = math.sqrt(sum(v * v for v in vals))
    return struct.pack("<%df" % dim, *[v / n for v in vals])


def make_fixture(path):
    """The live schema's shape (measured 2026-10-08 on context_20261008.db), small."""
    con = sqlite3.connect(path)
    con.executescript("""
    CREATE TABLE docs(id INTEGER PRIMARY KEY AUTOINCREMENT, code TEXT UNIQUE, category TEXT, src_path TEXT,
                      glossary TEXT, created_at TEXT);
    CREATE TABLE passages(id INTEGER PRIMARY KEY AUTOINCREMENT, doc_id INTEGER NOT NULL, page_no INTEGER NOT NULL,
      idx INTEGER NOT NULL, text TEXT, translation TEXT, iast TEXT, verse_ref TEXT, chapter TEXT, text_type TEXT,
      chandas TEXT, padas INTEGER, quality_score REAL, translation_score REAL, engine TEXT, norm TEXT, sandhi TEXT,
      morph TEXT, ents TEXT, source TEXT, mt_prompt_version TEXT, translated_at TEXT, translation_qa REAL,
      ocr_engine TEXT, ocr_variants TEXT, UNIQUE(doc_id, page_no, idx));
    CREATE TABLE translations_l10n(id INTEGER PRIMARY KEY AUTOINCREMENT, passage_id INTEGER NOT NULL, lang TEXT NOT NULL,
      translation TEXT, engine TEXT, mt_prompt_version TEXT, translation_score REAL, translation_qa REAL,
      translated_at TEXT, UNIQUE(passage_id, lang));
    CREATE TABLE entities(id INTEGER PRIMARY KEY, canonical TEXT UNIQUE, kind TEXT, notes TEXT, created_at TEXT);
    CREATE TABLE entity_variants(entity_id INTEGER, variant TEXT, UNIQUE(entity_id, variant));
    CREATE TABLE entity_mentions(id INTEGER PRIMARY KEY, entity_id INTEGER, passage_id INTEGER, surface TEXT,
      created_at TEXT, UNIQUE(entity_id, passage_id));
    CREATE TABLE doc_stories(id INTEGER PRIMARY KEY, doc_id INTEGER NOT NULL, image_id INTEGER, status TEXT,
      title TEXT, title_hi TEXT, why TEXT, from_page INTEGER, from_idx INTEGER, to_page INTEGER, to_idx INTEGER,
      story_en TEXT, story_hi TEXT, quote_sa TEXT, quote_ref TEXT, notes TEXT, cites TEXT, verify TEXT, model TEXT,
      prompt_hash TEXT, provenance TEXT, created_at TEXT, updated_at TEXT, approved_at TEXT);
    CREATE TABLE doc_stage(id INTEGER PRIMARY KEY AUTOINCREMENT, doc_code TEXT NOT NULL, stage TEXT NOT NULL,
      status TEXT NOT NULL, input_fp TEXT, measured TEXT, reason TEXT, attempts INTEGER NOT NULL DEFAULT 0,
      updated_at TEXT NOT NULL, UNIQUE(doc_code, stage));
    CREATE TABLE passage_embeddings(passage_id INTEGER PRIMARY KEY, model TEXT, dim INTEGER, vec BLOB, updated_at TEXT);
    """)
    con.execute("INSERT INTO docs(code, category, src_path) VALUES ('markandeya_purana','purana','D:\\\\corpus\\\\mp.pdf')")
    con.execute("INSERT INTO docs(code, category) VALUES ('AphorismsOfSandilya','bhakti')")
    con.execute("INSERT INTO docs(code, category) VALUES ('smriti_14manu_smriti-RETIRED','smriti')")
    con.execute("INSERT INTO entities(id, canonical, kind) VALUES (1, 'Indra', 'deity'), (2, 'Meru', 'place'), (3, '', 'x')")
    con.execute("INSERT INTO entity_variants VALUES (1, 'Indrah'), (1, 'Sakra'), (2, 'Sumeru')")
    pid = 0
    for doc_id, pages in ((1, 3), (2, 2), (3, 1)):
        for page in range(1, pages + 1):
            for idx in range(1, 4):
                tr = "the passage %d.%d.%d" % (doc_id, page, idx) if idx != 3 else None
                con.execute(
                    "INSERT INTO passages(doc_id, page_no, idx, text, translation, iast, verse_ref, text_type, "
                    "quality_score, norm, ocr_variants, translated_at) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
                    (doc_id, page, idx, "\u0936\u094d\u0932\u094b\u0915 %d" % idx, tr, "sloka %d" % idx,
                     "%d.%d" % (page, idx), "mula", 0.9, "RAW OCR PAGE " * 50, "[]", "2026-10-07T10:00:00+00:00"))
                pid = con.execute("SELECT last_insert_rowid()").fetchone()[0]
                if tr:
                    con.execute("INSERT INTO translations_l10n(passage_id, lang, translation, engine) VALUES (?,?,?,?)",
                                (pid, "hi", "\u0905\u0928\u0941\u0935\u093e\u0926 %d" % pid, "gemini"))
                    con.execute("INSERT INTO passage_embeddings VALUES (?,?,?,?,?)",
                                (pid, "models/gemini-embedding-001", 3072, unit_vec(pid), "2026-10-07"))
                if idx == 1:
                    con.execute("INSERT INTO entity_mentions(entity_id, passage_id, surface) VALUES (1, ?, 'Indrah')", (pid,))
    con.execute("INSERT INTO doc_stories(id, doc_id, status, title, story_en, from_page, from_idx) "
                "VALUES (7, 1, 'approved', 'The lake', 'Once ...', 1, 1)")
    for code in ("markandeya_purana", "AphorismsOfSandilya"):
        con.execute("INSERT INTO doc_stage(doc_code, stage, status, updated_at) VALUES (?, 'translate_en', 'done', 'x')", (code,))
    con.execute("INSERT INTO doc_stage(doc_code, stage, status, updated_at) VALUES "
                "('smriti_14manu_smriti-RETIRED', 'retired', 'done', 'x')")
    con.commit()
    con.close()


class FakeServer:
    """The C4 functions' rules, in memory: rows keyed per table and group, soft retire."""

    def __init__(self):
        self.t = {t: {} for t in cs.TABLES}   # table -> group -> key -> {"h": hash, "retired": bool, "row": row}
        self.calls = []

    @staticmethod
    def key_of(table, r):
        return {"docs": lambda: ("*", r["doc_code"]),
                "entities": lambda: ("*", r["canonical"]),
                "passages": lambda: (r["doc_code"], "%d|%d" % (r["page_no"], r["idx"])),
                "translations": lambda: (r["doc_code"], "%d|%d|%s" % (r["page_no"], r["idx"], r["lang"])),
                "mentions": lambda: (r["doc_code"], "%d|%d|%s" % (r["page_no"], r["idx"], r["canonical"])),
                "stories": lambda: (r["doc_code"], str(r["story_id"])),
                "stages": lambda: (r["doc_code"], r["stage"]),
                "vectors": lambda: (r["doc_code"], "%d|%d" % (r["page_no"], r["idx"]))}[table]()

    def manifest(self, tables):
        self.calls.append(("manifest",))
        out = {}
        for t in tables:
            out[t] = {}
            for g, rows in self.t[t].items():
                live = {k: v["h"] for k, v in rows.items() if not v["retired"]}
                if live:
                    out[t][g] = [len(live), cs.digest(live)]
        return out

    def keys(self, table, group):
        self.calls.append(("keys", table, group))
        return {k: v["h"] for k, v in self.t[table].get(group, {}).items() if not v["retired"]}

    def ingest(self, table, rows, run_id):
        self.calls.append(("ingest", table, len(rows)))
        assert len(rows) <= 2000 and all(r.get("row_hash") for r in rows)
        if table in ("translations", "mentions", "vectors"):    # the foreign keys
            for r in rows:
                g, k = self.key_of("passages", dict(r, idx=r["idx"]))
                assert k in self.t["passages"].get(g, {}), "FK: %s %s" % (table, k)
        changed = 0
        for r in rows:
            g, k = self.key_of(table, r)
            cur = self.t[table].setdefault(g, {}).get(k)
            if cur is None or cur["h"] != r["row_hash"] or cur["retired"]:
                self.t[table][g][k] = {"h": r["row_hash"], "retired": False, "row": r}
                changed += 1
        return {"received": len(rows), "changed": changed}

    def retire(self, table, group, keys, run_id):
        self.calls.append(("retire", table, group, len(keys)))
        n = 0
        for k in keys:
            v = self.t[table].get(group, {}).get(k)
            if v and not v["retired"]:
                v["retired"] = True
                n += 1
        return {"retired": n}

    def run(self, run_id, info, finish):
        return {"ok": True}


class FakeSink(cs.NoneSink):
    name = "fake"

    def __init__(self, server):
        self.s = server

    def manifest(self, tables):
        return self.s.manifest(tables)

    def keys(self, table, group):
        return self.s.keys(table, group)

    def ingest(self, table, rows, run_id):
        return self.s.ingest(table, json.loads(json.dumps(rows)), run_id)

    def retire(self, table, group, keys, run_id):
        return self.s.retire(table, group, keys, run_id)


class Base(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.db = str(Path(self.tmp.name) / "context.db")
        make_fixture(self.db)
        self.server = FakeServer()

    def tearDown(self):
        while OPEN:
            try:
                OPEN.pop().close()
            except Exception:
                pass
        self.tmp.cleanup()

    def ro(self):
        con = cs.open_ro(self.db)
        OPEN.append(con)
        return con

    def rw(self):
        con = sqlite3.connect(self.db)
        OPEN.append(con)
        return con

    def sync(self, apply=True, sink=None, **kw):
        con = self.ro()
        docs = cs.live_docs(con)
        only = kw.pop("only", None)
        kw.setdefault("progress", lambda m: None)
        run = cs.Run(con, sink or FakeSink(self.server), apply, **kw)
        return run.execute(list(cs.TABLES), docs, only)


class Idempotent(Base):
    def test_first_run_sends_everything_second_sends_nothing(self):
        s1 = self.sync()
        self.assertEqual(s1["stopped"], "done", s1)
        t = s1["tables"]
        self.assertEqual(t["docs"]["changed"], 2)            # the retired document stays at home
        self.assertEqual(t["passages"]["changed"], 15)
        self.assertEqual(t["translations"]["changed"], 10)
        self.assertEqual(t["vectors"]["changed"], 10)
        self.assertEqual(t["entities"]["changed"], 2)        # the empty canonical is skipped
        self.assertEqual(t["mentions"]["changed"], 5)
        self.assertEqual(t["stories"]["changed"], 1)
        self.assertEqual(t["stages"]["changed"], 2)
        self.assertEqual(s1["verified"]["groups_different"], 0)
        n_calls = len(self.server.calls)
        s2 = self.sync()
        self.assertEqual(sum(x["upsert"] for x in s2["tables"].values()), 0)
        self.assertEqual(sum(x["retire"] for x in s2["tables"].values()), 0)
        self.assertEqual(s2["verified"]["groups_different"], 0)
        # the second run asks only for the manifest (twice: before and to verify)
        self.assertEqual([c for c in self.server.calls[n_calls:] if c[0] != "manifest"], [])

    def test_one_new_translation_sends_one_passage_and_its_children(self):
        self.sync()
        con = self.rw()
        pid = con.execute("SELECT id FROM passages WHERE doc_id=1 AND page_no=2 AND idx=3").fetchone()[0]
        con.execute("UPDATE passages SET translation='new English' WHERE id=?", (pid,))
        con.execute("INSERT INTO translations_l10n(passage_id, lang, translation) VALUES (?, 'hi', 'x')", (pid,))
        con.commit()
        s = self.sync()
        self.assertEqual(s["tables"]["passages"]["upsert"], 1)
        self.assertEqual(s["tables"]["passages"]["changed"], 1)
        self.assertEqual(s["tables"]["translations"]["upsert"], 1)
        self.assertEqual(s["tables"]["passages"]["groups_changed"], 1)   # the other document untouched
        self.assertEqual(s["verified"]["groups_different"], 0)
        row = self.server.t["passages"]["markandeya_purana"]["2|3"]["row"]
        self.assertEqual(row["translation"], "new English")

    def test_a_repeated_batch_changes_nothing(self):
        self.sync()
        g = cs.build_doc_groups(self.ro(), cs.live_docs(self.ro())[0], {"passages"}, set())["passages"]
        res = self.server.ingest("passages", list(g.rows.values()), "r")
        self.assertEqual(res["changed"], 0)

    def test_removed_passage_is_retired_and_comes_back(self):
        self.sync()
        con = self.rw()
        pid = con.execute("SELECT id FROM passages WHERE doc_id=2 AND page_no=1 AND idx=3").fetchone()[0]
        row = con.execute("SELECT * FROM passages WHERE id=?", (pid,)).fetchone()
        con.execute("DELETE FROM passages WHERE id=?", (pid,))
        con.commit()
        s = self.sync()
        self.assertEqual(s["tables"]["passages"]["retired"], 1)
        self.assertTrue(self.server.t["passages"]["AphorismsOfSandilya"]["1|3"]["retired"])
        self.assertEqual(s["verified"]["groups_different"], 0)
        con.execute("INSERT INTO passages VALUES (%s)" % ",".join("?" * len(row)), row)
        con.commit()
        s = self.sync()
        self.assertEqual(s["tables"]["passages"]["changed"], 1)
        self.assertFalse(self.server.t["passages"]["AphorismsOfSandilya"]["1|3"]["retired"])

    def test_reingest_with_new_local_ids_keeps_keys(self):
        self.sync()
        con = self.rw()
        con.execute("UPDATE passages SET id = id + 1000 WHERE doc_id = 2")
        con.execute("UPDATE translations_l10n SET passage_id = passage_id + 1000 WHERE passage_id IN "
                    "(SELECT id - 1000 FROM passages WHERE doc_id = 2)")
        con.commit()
        s = self.sync()
        self.assertEqual(s["tables"]["passages"]["retire"], 0)
        self.assertEqual(s["tables"]["passages"]["upsert"], 6)     # local_id changed, keys did not
        self.assertEqual(s["verified"]["groups_different"], 0)


class Guards(Base):
    def test_plan_sends_nothing(self):
        s = self.sync(apply=False)
        self.assertGreater(s["tables"]["passages"]["upsert"], 0)
        self.assertEqual([c for c in self.server.calls if c[0] in ("ingest", "retire")], [])

    def test_retired_documents_are_not_sent(self):
        self.sync()
        self.assertNotIn("smriti_14manu_smriti-RETIRED", self.server.t["passages"])
        self.assertNotIn("smriti_14manu_smriti-RETIRED", self.server.t["docs"]["*"])

    def test_raw_ocr_never_travels(self):
        self.sync()
        for g in self.server.t["passages"].values():
            for v in g.values():
                self.assertNotIn("norm", v["row"])
                self.assertNotIn("ocr_variants", v["row"])

    def test_emptied_document_is_held_not_retired(self):
        self.sync()
        con = self.rw()
        con.execute("DELETE FROM translations_l10n")
        con.commit()
        s = self.sync()
        # 6 rows of markandeya_purana would all go: held. 4 of AphorismsOfSandilya: a group of
        # five or fewer may empty without the flag.
        self.assertEqual(s["tables"]["translations"]["held"], 6)
        self.assertEqual(s["tables"]["translations"]["retired"], 4)
        self.assertTrue(any("translations/markandeya_purana: 6 of 6" in h for h in s["held"]))
        self.assertEqual(len(self.server.keys("translations", "markandeya_purana")), 6)
        s = self.sync(allow_mass_retire=True)
        self.assertEqual(s["tables"]["translations"]["retired"], 6)
        self.assertEqual(s["verified"]["groups_different"], 0)

    def test_document_retired_locally_is_retired_in_the_mirror(self):
        self.sync()
        con = self.rw()
        con.execute("UPDATE docs SET code='AphorismsOfSandilya-RETIRED' WHERE code='AphorismsOfSandilya'")
        con.commit()
        s = self.sync()
        self.assertEqual(s["tables"]["passages"]["retired"], 6)
        self.assertEqual(s["tables"]["docs"]["retired"], 1)
        self.assertEqual(s["verified"]["groups_different"], 0)

    def test_budget_stops_and_the_next_run_finishes(self):
        s = self.sync(max_bytes_total=3000, batch_bytes=1500)
        self.assertEqual(s["stopped"], "budget")
        for _ in range(40):
            s = self.sync(max_bytes_total=3000, batch_bytes=1500)
            if s["stopped"] == "done":
                break
        self.assertEqual(s["stopped"], "done")
        s = self.sync()
        self.assertEqual(sum(x["upsert"] for x in s["tables"].values()), 0)

    def test_partial_run_never_retires_documents(self):
        self.sync()
        s = self.sync(only={"markandeya_purana"})
        self.assertEqual(s["tables"]["docs"]["retire"], 0)
        self.assertEqual(s["tables"]["passages"]["upsert"], 0)

    def test_stray_values_in_typed_columns_are_coerced(self):
        con = self.rw()
        con.execute("UPDATE passages SET padas='four', quality_score='0.7' WHERE doc_id=1 AND page_no=1 AND idx=1")
        con.execute("UPDATE passages SET padas='2', quality_score='n/a' WHERE doc_id=1 AND page_no=1 AND idx=2")
        con.commit()
        s = self.sync()
        # SQLite's column affinity already turns '0.7' and '2' into numbers; 'four' and 'n/a' stay text
        self.assertEqual(s["tables"]["passages"]["coerced"], 2)
        rows = self.server.t["passages"]["markandeya_purana"]
        self.assertEqual((rows["1|1"]["row"]["padas"], rows["1|1"]["row"]["quality_score"]), (None, 0.7))
        self.assertEqual((rows["1|2"]["row"]["padas"], rows["1|2"]["row"]["quality_score"]), (2, None))
        self.assertEqual(sum(x["upsert"] for x in self.sync()["tables"].values()), 0)   # still idempotent

    def test_database_is_opened_read_only(self):
        con = self.ro()
        with self.assertRaises(sqlite3.OperationalError):
            con.execute("UPDATE docs SET category='x'")


class Progress(Base):
    """PROGRESS_2026_10_08: a first push printed nothing for minutes and looked stuck."""

    def test_a_push_says_what_it_is_doing(self):
        lines = []
        s = self.sync(progress=lines.append, batch_bytes=1500)
        self.assertEqual(s["stopped"], "done")
        text = "\n".join(lines)
        self.assertIn("mirror holds 0 rows; 2 live documents here; sending changes", text)
        self.assertIn("passages markandeya_purana: 9 to send, 0 gone here", text)
        self.assertIn("passages markandeya_purana: done in", text)
        self.assertRegex(text, r"batch 1/\d+: \d+ rows")
        self.assertIn("compared 2/2 documents", text)
        self.assertIn("checking every group against the mirror", text)
        self.assertTrue(all(l.startswith("[") for l in lines))

    def test_a_run_with_nothing_to_send_stays_short(self):
        self.sync()
        lines = []
        self.sync(progress=lines.append)
        self.assertFalse([l for l in lines if "to send" in l])
        self.assertLessEqual(len(lines), 4)

    def test_status_compares_mirror_with_here(self):
        out = []
        before = cs.status(self.ro(), FakeSink(self.server), cs.live_docs(self.ro()), out=out.append)
        self.assertEqual(before["passages"], {"mirror": 0, "here": 15})
        self.sync()
        after = cs.status(self.ro(), FakeSink(self.server), cs.live_docs(self.ro()), out=out.append)
        for t, v in after.items():
            self.assertEqual(v["mirror"], v["here"], t)
        self.assertEqual(after["vectors"]["here"], 10)
        self.assertEqual(after["entities"]["here"], 2)


class Formats(Base):
    def test_digest_matches_postgres(self):
        keyed = {"10|2": "aaa", "1|20": "bbb", "9|1": "ccc", "\u015aiva": "ddd", "agni": "eee", "Agni": "fff",
                 "\u1e5b\u1e63i": "ggg"}
        self.assertEqual(cs.digest(keyed), GOLDEN_DIGEST)

    def test_signature_matches_the_edge_function(self):
        self.assertEqual(cs.sign("test-secret-for-golden", "1760000000", b'{"action":"hello"}'), GOLDEN_SIG)

    def test_vector_literal(self):
        lit = cs.vector_literal(unit_vec(5))
        vals = [float(x) for x in lit[1:-1].split(",")]
        self.assertEqual(len(vals), 1536)
        self.assertAlmostEqual(math.sqrt(sum(v * v for v in vals)), 1.0, places=3)
        self.assertTrue(lit.startswith("[") and lit.endswith("]") and " " not in lit)

    def test_batches_respect_limits(self):
        rows = [{"k": i, "pad": "x" * 100} for i in range(50)]
        out = list(cs.batches(rows, 1000, 7))
        self.assertEqual(sum(len(b) for b, _ in out), 50)
        self.assertTrue(all(len(b) <= 7 and size <= 1000 for b, size in out))

    def test_env_file_parsing(self):
        p = Path(self.tmp.name) / ".env"
        p.write_text('# c\nCORPUS_SYNC_SECRET="abc"\nVITE_SUPABASE_URL=https://x.supabase.co\n', encoding="utf-8")
        d = cs._read_env_file(p)
        self.assertEqual(d["CORPUS_SYNC_SECRET"], "abc")
        self.assertEqual(d["VITE_SUPABASE_URL"], "https://x.supabase.co")


class StubHandler(BaseHTTPRequestHandler):
    """What the corpus-ingest edge function checks, in Python: signature over 'ts.' + body as
    sent, the clock within 300 s, gzip, then the call."""
    server_ref = None
    secret = "stub-secret"

    def log_message(self, *a):
        pass

    def do_POST(self):
        import time as _t
        body = self.rfile.read(int(self.headers.get("Content-Length", "0")))
        ts, sig = self.headers.get("x-corpus-ts", ""), self.headers.get("x-corpus-sig", "")
        want = hmac.new(self.secret.encode(), ts.encode() + b"." + body, hashlib.sha256).hexdigest()
        if not hmac.compare_digest(want, sig) or abs(_t.time() - int(ts or 0)) > 300:
            return self._send(401, {"ok": False, "error": "bad signature"})
        if self.headers.get("apikey") != "anon-key":
            return self._send(401, {"ok": False, "error": "no apikey"})
        p = json.loads(gzip.decompress(body).decode("utf-8"))
        s, a = self.server_ref, p["action"]
        if a == "hello":
            r = {"fn": "stub"}
        elif a == "manifest":
            r = s.manifest(p["tables"])
        elif a == "keys":
            r = s.keys(p["table"], p["group"])
        elif a == "ingest":
            r = s.ingest(p["table"], p["rows"], p["run_id"])
        elif a == "retire":
            r = s.retire(p["table"], p["group"], p["keys"], p["run_id"])
        else:
            r = s.run(p["run_id"], p.get("info"), p.get("finish"))
        self._send(200, {"ok": True, "result": r})

    def _send(self, code, obj):
        b = json.dumps(obj).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(b)))
        self.end_headers()
        self.wfile.write(b)


class EdgeTransport(Base):
    def setUp(self):
        super().setUp()
        StubHandler.server_ref = self.server
        self.httpd = HTTPServer(("127.0.0.1", 0), StubHandler)
        self.th = threading.Thread(target=self.httpd.serve_forever, daemon=True)
        self.th.start()
        self.base = "http://127.0.0.1:%d" % self.httpd.server_address[1]

    def tearDown(self):
        self.httpd.shutdown()
        self.httpd.server_close()
        super().tearDown()

    def test_edge_sink_end_to_end(self):
        sink = cs.EdgeSink(self.base, "anon-key", "stub-secret", timeout=10, retries=1)
        self.assertEqual(sink.hello(), {"fn": "stub"})
        s = self.sync(sink=sink)
        self.assertEqual(s["stopped"], "done", s)
        self.assertEqual(s["tables"]["passages"]["changed"], 15)
        self.assertEqual(s["verified"]["groups_different"], 0)
        s = self.sync(sink=sink)
        self.assertEqual(sum(x["upsert"] for x in s["tables"].values()), 0)

    def test_wrong_secret_is_refused(self):
        sink = cs.EdgeSink(self.base, "anon-key", "not-the-secret", timeout=10, retries=1)
        with self.assertRaises(cs.SinkError) as e:
            sink.hello()
        self.assertIn("401", str(e.exception))


if __name__ == "__main__":
    unittest.main()
