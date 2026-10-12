# -*- coding: ascii -*-
"""ETEXT_WITNESS_2026_10_11: an e-text as a witness (the Source desk's S2) and the missing page (S3).
etext_witness.py reads GRETIL, sanskritdocuments.org and archive.org texts (IAST, Devanagari, Harvard-Kyoto),
groups their lines into verses by their references, measures the witness against the scan page by page and
offers the pages the scan cannot read; --write and --ingest make it a text of its own, local until adopted;
repair_text.py --release waits for its translation; corpus_sync.py leaves it alone; the dashboard's repair
page shows it. Temp files only, never data/context.db, never the network (a local server stands in)."""
import http.server, importlib.util, json, os, random, re, shutil, socket, sqlite3, subprocess, sys, tempfile
import threading, unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
SCRIPTS = REPO / "scripts"
sys.path.insert(0, str(SCRIPTS))
TOOL = SCRIPTS / "etext_witness.py"


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, str(path))
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


ew = load("etext_witness_t", TOOL)


def node():
    return shutil.which("node")


def translit_ok():
    try:
        import indic_transliteration  # noqa: F401
        return True
    except ImportError:
        return False


GRETIL = """<html><head><title>GRETIL: Bhagavadgita</title></head><body>
<h2>Bhagavadgita</h2>
<p>This GRETIL e-text is based on the edition by ... Input by John Smith. Copyright notice: for scholarly use.<br>
Text converted to Unicode (UTF-8). See http://gretil.sub.uni-goettingen.de/ for the conventions.<br>
</p><hr><p>
dh\u1e5btar\u0101\u1e63\u1e6dra uv\u0101ca |<br>
dharmak\u1e63etre kuruk\u1e63etre samavet\u0101 yuyutsava\u1e25 |<br>
m\u0101mak\u0101\u1e25 p\u0101\u1e47\u1e0dav\u0101\u015b caiva kim akurvata sa\u1e43jaya || BhG_1.1 ||<br>
<br>
sa\u1e43jaya uv\u0101ca |<br>
d\u1e5b\u1e63\u1e6dv\u0101 tu p\u0101\u1e47\u1e0dav\u0101n\u012bka\u1e43 vy\u016b\u1e0dha\u1e43 duryodhanas tad\u0101 |<br>
\u0101c\u0101ryam upasa\u1e43gamya r\u0101j\u0101 vacanam abrav\u012bt || BhG_1.2 ||<br>
<br>
pa\u015byait\u0101\u1e43 p\u0101\u1e47\u1e0duputr\u0101\u1e47\u0101m \u0101c\u0101rya mahat\u012b\u1e43 cam\u016bm |<br>
vy\u016b\u1e0dh\u0101\u1e43 drupadaputre\u1e47a tava \u015bi\u1e63ye\u1e47a dh\u012bmat\u0101 || BhG_1.3 ||<br>
<br>
o\u1e43 tat sad iti \u015br\u012bmadbhagavadg\u012bt\u0101s\u016bpani\u1e63atsu arjunavi\u1e63\u0101dayogo n\u0101ma prathamo 'dhy\u0101ya\u1e25 ||<br>
<br>
\u015br\u012bbhagav\u0101n uv\u0101ca |<br>
kutas tv\u0101 ka\u015bmalam ida\u1e43 vi\u1e63ame samupasthitam |<br>
an\u0101ryaju\u1e63\u1e6dam asvargyam ak\u012brtikaram arjuna || BhG_2.2 ||<br>
</p></body></html>
"""

SDOC = """<html><body><div>Home | Sanskrit Documents | Proofread by volunteers</div>
<pre>
\u0965 \u0936\u094d\u0930\u0940\u0903 \u0965
\u0927\u0930\u094d\u092e\u0915\u094d\u0937\u0947\u0924\u094d\u0930\u0947 \u0915\u0941\u0930\u0941\u0915\u094d\u0937\u0947\u0924\u094d\u0930\u0947 \u0938\u092e\u0935\u0947\u0924\u093e \u092f\u0941\u092f\u0941\u0924\u094d\u0938\u0935\u0903 \u0964
\u092e\u093e\u092e\u0915\u093e\u0903 \u092a\u093e\u0923\u094d\u0921\u0935\u093e\u0936\u094d\u091a\u0948\u0935 \u0915\u093f\u092e\u0915\u0941\u0930\u094d\u0935\u0924 \u0938\u091e\u094d\u091c\u092f \u0965 \u0967\u0965
\u0926\u0943\u0937\u094d\u091f\u094d\u0935\u093e \u0924\u0941 \u092a\u093e\u0923\u094d\u0921\u0935\u093e\u0928\u0940\u0915\u0902 \u0935\u094d\u092f\u0942\u0922\u0902 \u0926\u0941\u0930\u094d\u092f\u094b\u0927\u0928\u0938\u094d\u0924\u0926\u093e \u0964
\u0906\u091a\u093e\u0930\u094d\u092f\u092e\u0941\u092a\u0938\u0919\u094d\u0917\u092e\u094d\u092f \u0930\u093e\u091c\u093e \u0935\u091a\u0928\u092e\u092c\u094d\u0930\u0935\u0940\u0924\u094d \u0964\u0964 \u0968\u0964\u0964
This document was typeset in Unicode and proofread.
</pre></body></html>
"""


class Reading(unittest.TestCase):
    def test_gretil_iast_html(self):
        if not translit_ok():
            self.skipTest("indic_transliteration is not installed")
        p = ew.parse(ew.html_to_text(GRETIL))
        self.assertEqual((p["scheme"], p["mode"]), ("iast", "verses"))
        v = [x for x in p["verses"] if x["type"] != "frontmatter"]
        self.assertEqual([x["ref"] for x in v], ["1.1", "1.2", "1.3", "", "2.2"])
        self.assertTrue(v[0]["text"].startswith("\u0927\u0943\u0924\u0930\u093e\u0937\u094d\u091f\u094d\u0930 \u0909\u0935\u093e\u091a \u0964\n\u0927\u0930\u094d\u092e\u0915\u094d\u0937\u0947\u0924\u094d\u0930\u0947"), "the speaker's line is the verse's")
        self.assertTrue(v[0]["text"].endswith("\u0938\u0902\u091c\u092f \u0965"), "// BhG_1.1 // leaves one double danda")
        self.assertEqual(v[3]["type"], "colophon")
        self.assertEqual([x["chapter"] for x in v], ["1", "1", "1", "1", "2"])
        self.assertGreaterEqual(p["stats"]["dropped_english"], 2, "the header is not the text")
        self.assertFalse(any(re.search("[A-Za-z]", x["text"]) for x in p["verses"]))
        self.assertIn("dharmak\u1e63etre", v[0]["roman"])

    def test_devanagari_with_its_numerals(self):
        p = ew.parse(ew.html_to_text(SDOC))
        self.assertEqual(p["scheme"], "devanagari")
        v = [x for x in p["verses"] if x["type"] == "mula"]
        self.assertEqual([x["ref"] for x in v], ["1", "2"])
        self.assertTrue(v[1]["text"].endswith("\u0935\u091a\u0928\u092e\u092c\u094d\u0930\u0935\u0940\u0924\u094d \u0965"), "\u0964\u0964 is a double danda")
        self.assertFalse(any("Proofread" in x["text"] or "typeset" in x["text"] for x in p["verses"]))

    def test_pada_references_group_one_verse(self):
        if not translit_ok():
            self.skipTest("indic_transliteration is not installed")
        t = ("BhP_01.01.001/1 janm\u0101dy asya yato 'nvay\u0101d itarata\u015b c\u0101rthe\u1e63v abhij\u00f1a\u1e25 svar\u0101\u1e6d\n"
             "BhP_01.01.001/2 tene brahma h\u1e5bd\u0101 ya \u0101dikavaye muhyanti yat s\u016braya\u1e25\n"
             "BhP_01.01.002/1 dharma\u1e25 projjhitakaitavo 'tra paramo nirmatsar\u0101\u1e47\u0101\u1e43 sat\u0101\u1e43\n")
        p = ew.parse(t)
        self.assertEqual([(x["ref"], x["chapter"], x["text"].count("\n")) for x in p["verses"]],
                         [("1.1.1", "1.1", 1), ("1.1.2", "1.1", 0)])
        self.assertIn("\u093d\u0928\u094d\u0935\u092f\u093e\u0926\u094d", p["verses"][0]["text"], "the apostrophe is the avagraha")

    def test_an_archive_ocr_text_keeps_its_pages(self):
        pages = ["\u0927\u0930\u094d\u092e\u0915\u094d\u0937\u0947\u0924\u094d\u0930\u0947 \u0915\u0941\u0930\u0941\u0915\u094d\u0937\u0947\u0924\u094d\u0930\u0947 \u0938\u092e\u0935\u0947\u0924\u093e \u092f\u0941\u092f\u0941\u0924\u094d\u0938\u0935\u0903 \u0964\nPrinted at the Nirnaya Sagar Press\n"] * 6
        p = ew.parse("\f".join(pages))
        self.assertEqual(p["mode"], "pages")
        self.assertEqual(len(p["pages"]), 6)
        self.assertNotIn("Printed", p["pages"][0]["text"])

    def test_harvard_kyoto_and_the_unknown(self):
        if not translit_ok():
            self.skipTest("indic_transliteration is not installed")
        t = "dharmakSetre kurukSetre samavetA yuyutsavaH /\nmAmakAH pANDavAz caiva kim akurvata saMjaya // 1.1 //\n"
        p = ew.parse(t)
        self.assertEqual(p["scheme"], "hk")
        self.assertTrue(p["verses"][0]["text"].startswith("\u0927\u0930\u094d\u092e\u0915\u094d\u0937\u0947\u0924\u094d\u0930\u0947"))
        self.assertEqual(ew.detect_scheme(["kim akurvata samjaya", "tene brahma hrda ya adikavaye"]), "unknown")


def _verses(seed, n):
    R = random.Random(seed)
    C = [chr(c) for c in range(0x0915, 0x093a)]
    V = ["", "\u093e", "\u093f", "\u0940", "\u0941", "\u0947", "\u094b", "\u0948"]
    word = lambda k: "".join(R.choice(C) + R.choice(V) for _ in range(k))
    line = lambda: " ".join(word(R.randint(2, 4)) for _ in range(5))
    return [{"text": line() + " \u0964\n" + line() + " \u0965", "ref": "1.%d" % (i + 1), "chapter": "1", "type": "mula",
             "padas": 4, "src_line": i, "roman": ""} for i in range(n)], R, C


def _scan(verses, R, C, garbled=(7, 15, 16), absent=(22,), commentary=(30, 31)):
    def noisy(t):
        out = []
        for ch in t:
            r = R.random()
            if ch == " " and r < 0.5:
                continue                      # sandhi: the printed text joins what the e-text spaces
            out.append(R.choice(C) if r < 0.05 else ch)
        return "".join(out)
    scan = {}
    for p in range(1, 41):
        t = "\n".join(noisy(v["text"]) for v in verses[(p - 1) * 10:p * 10])
        if p in garbled:
            t = "".join(R.choice("aeOTfnAN ") if R.random() < 0.8 else ch for ch in t)
        if p in absent:
            continue
        if p in commentary:
            t += "\n" + "\n".join(_verses(p, 25)[0][k]["text"] for k in range(25))
        scan[p] = t
    return scan


class Measure(unittest.TestCase):
    def test_the_missing_pages_are_offered_from_their_neighbours(self):
        verses, R, C = _verses(7, 400)
        m = ew.measure(verses, _scan(verses, R, C))
        self.assertEqual((m["readable"], m["matched"], m["coverage"], m["order"]), (36, 36, 1.0, 1.0))
        off = {o["page"]: o for o in m["offers"]}
        self.assertEqual(sorted(off), [7, 15, 16, 22])
        for p in (7, 15, 16, 22):
            self.assertEqual((off[p]["lo"], off[p]["hi"]), ((p - 1) * 10, p * 10 - 1), p)
            self.assertEqual(off[p]["refs"], "1.%d-1.%d" % ((p - 1) * 10 + 1, p * 10))
        self.assertIn("not in the database", off[22]["why"])
        self.assertIn("Latin", off[15]["why"])
        self.assertEqual(m["pages"][30]["status"], "match", "a page with commentary around its verses is still read")
        self.assertTrue(ew.opinion(m, "D").startswith("the same work, in the same order"))

    def test_another_text_is_not_a_witness(self):
        verses, R, C = _verses(7, 400)
        other = _verses(99, 400)[0]
        m = ew.measure(other, _scan(verses, R, C))
        self.assertEqual(m["matched"], 0); self.assertEqual(m["offers"], [])
        self.assertTrue(ew.opinion(m, "D").startswith("not the same text"))

    def test_gretil_against_a_printed_edition(self):
        if not translit_ok():
            self.skipTest("indic_transliteration is not installed")
        w = ew.parse(ew.html_to_text(GRETIL))["verses"]
        printed = "\n".join(x["text"] for x in ew.parse(ew.html_to_text(SDOC))["verses"])
        self.assertEqual(ew.skel("\u0938\u0902\u091c\u092f"), ew.skel("\u0938\u091e\u094d\u091c\u092f"), "samjaya, sanjaya")
        r = ew.measure(w, {1: printed + " " + printed})["pages"][1]
        self.assertEqual(r["status"], "match")
        self.assertGreater(r["in_witness"], 0.8, "spaced IAST and joined Devanagari: the same verses")

    def test_readable(self):
        self.assertFalse(ew.readable("\u0915" * 30)[0])
        self.assertFalse(ew.readable("\u0915" * 100 + "a" * 60)[0])
        self.assertTrue(ew.readable("\u0915" * 100 + "a" * 10)[0])


class Tool(unittest.TestCase):
    """etext_witness.py end to end on a temp tree, with the real ingest_jsonl_fast.py on a temp database."""
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        t = self.t = Path(self.tmp.name)
        (t / "data").mkdir(); (t / "backups").mkdir(); (t / "sources" / "Scan").mkdir(parents=True)
        self.db = t / "data" / "context.db"
        import db_utils
        con = db_utils.connect(str(self.db)); db_utils.ensure_schema(con); db_utils.migrate_schema(con)
        did = db_utils.ensure_doc(con, "Scan", category="agama")
        self.verses, R, C = _verses(7, 400)
        for p, text in _scan(self.verses, R, C).items():
            con.execute("INSERT INTO passages(doc_id,page_no,idx,text,translation) VALUES(?,?,1,?,'')", (did, p, text))
        con.commit(); con.close()
        lines = []
        for v in self.verses:
            a, b = v["text"].split("\n")
            lines += [a, b.replace("\u0965", "\u0965 " + v["ref"].split(".")[1] + " \u0965"), ""]
        self.src = t / "sources" / "Scan" / "witness.txt"
        self.src.write_text("This file was typed in by volunteers, see the notes.\n\n" + "\n".join(lines), encoding="utf-8")

    def tearDown(self):
        self.tmp.cleanup()

    def tool(self, *args, script=TOOL, base=True):
        t = self.t
        b = ["--db", str(self.db), "--sources", str(t / "sources"), "--out-dir", str(t / "data" / "raw_witness"),
             "--witnesses", str(t / "data" / "witnesses.jsonl"), "--verdicts", str(t / "data" / "source_verdicts.jsonl"),
             "--backup-dir", str(t / "backups")] if base else []
        env = dict(os.environ, SA_DASHBOARD_URL="http://127.0.0.1:9", PYTHONIOENCODING="utf-8")
        env.pop("SA_REPAIR_SCRIPTS", None)
        r = subprocess.run([sys.executable, str(script)] + b + list(args), cwd=str(t), capture_output=True, text=True,
                           env=env, timeout=120, encoding="utf-8")
        return r.returncode, r.stdout + r.stderr

    def regs(self):
        p = self.t / "data" / "source_verdicts.jsonl"
        return [json.loads(x) for x in p.read_text(encoding="utf-8").splitlines()] if p.exists() else []

    def test_preview_write_ingest_release(self):
        rc, out = self.tool("--doc", "Scan", "--file", str(self.src))
        self.assertEqual(rc, 0, out)
        self.assertIn("WITNESS: the same work, in the same order", out)
        self.assertIn("pages the scan cannot read: 4; the witness offers a reading for 4: 7, 15, 16, 22", out)
        self.assertRegex(out, r'NEXT: python scripts\\etext_witness.py --doc Scan --file ".*witness.txt" --write')
        self.assertFalse((self.t / "data" / "raw_witness").exists(), "the preview writes nothing")
        rc, out = self.tool("--doc", "Scan", "--file", str(self.src), "--page", "15")
        self.assertEqual(rc, 0, out)
        self.assertIn("page 15: the scan cannot read it", out); self.assertIn("verses 141-150, 141-150", out)
        self.assertIn(self.verses[140]["text"].split("\n")[0], out)
        rc, out = self.tool("--doc", "Scan", "--file", str(self.src), "--write")
        self.assertEqual(rc, 0, out)
        w = self.t / "data" / "raw_witness" / "Scan__w_etext"
        pages = sorted(w.glob("Scan__w_etext_*.jsonl"))
        self.assertEqual(len(pages), 20)
        r0 = json.loads(pages[0].read_text(encoding="utf-8").splitlines()[0])
        self.assertEqual((r0["engine"], r0["verse_ref"], r0["quality_score"], r0["text_type"]), ("etext:etext", "1", 0.95, "mula"))
        al = json.loads((w / "align.json").read_text(encoding="utf-8"))
        self.assertEqual(sorted(o["page"] for o in al["offers"]), [7, 15, 16, 22])
        self.assertEqual(self.regs()[-1]["status"], "witness"); self.assertEqual(self.regs()[-1]["of"], "Scan")
        self.assertIn("NEXT: python scripts\\etext_witness.py --doc Scan --ingest --witness Scan__w_etext", out)
        rc, out = self.tool("--doc", "Scan", "--file", str(self.src), "--write")
        self.assertEqual(rc, 1); self.assertIn("holds a witness already", out)
        # before the ingest, the release refuses: a witness not yet in the database
        rt_args = ["--db", str(self.db), "--verdicts", str(self.t / "data" / "source_verdicts.jsonl"), "--doc", "Scan__w_etext", "--release"]
        rc, out = self.tool(*rt_args, script=SCRIPTS / "repair_text.py", base=False)
        self.assertEqual(rc, 1, out); self.assertIn("a witness not yet in the database", out)
        rc, out = self.tool("--doc", "Scan", "--ingest")
        self.assertEqual(rc, 0, out)
        self.assertIn("Scan__w_etext is in the database as its own text: 400 passages", out)
        self.assertEqual(len(list((self.t / "backups").glob("context_pre_witness_Scan__w_etext_*.db"))), 1)
        con = sqlite3.connect(str(self.db))
        n, eng, cat = con.execute("SELECT COUNT(*), MIN(p.ocr_engine), MIN(d.category) FROM passages p JOIN docs d ON d.id=p.doc_id "
                                  "WHERE d.code='Scan__w_etext'").fetchone()
        scan_n = con.execute("SELECT COUNT(*) FROM passages p JOIN docs d ON d.id=p.doc_id WHERE d.code='Scan'").fetchone()[0]
        con.close()
        self.assertEqual((n, eng, cat, scan_n), (400, "etext:etext", "agama", 39), "the scan is not touched")
        rc, out = self.tool("--doc", "Scan", "--ingest")
        self.assertEqual(rc, 0); self.assertIn("in the database already: 400 passages", out)
        rc, out = self.tool("--doc", "Scan", "--file", str(self.src), "--write", "--force")
        self.assertEqual(rc, 1); self.assertIn("is in the database already", out, "its pages are not rewritten under its translations")
        rc, out = self.tool(*rt_args, script=SCRIPTS / "repair_text.py", base=False)
        self.assertEqual(rc, 1, out); self.assertIn("not yet: English 0 of 400", out)
        rc, out = self.tool(*(rt_args + ["--force"]), script=SCRIPTS / "repair_text.py", base=False)
        self.assertEqual(rc, 0, out); self.assertEqual(self.regs()[-1]["status"], "released")
        rc, out = self.tool("--list")
        self.assertIn("released  Scan__w_etext", out); self.assertIn("ingested 400", out)

    def test_another_text_is_refused_unless_forced(self):
        other = self.t / "sources" / "Scan" / "other.txt"
        other.write_text("\n".join(v["text"] + " " + str(i) + " \u0965\n" for i, v in enumerate(_verses(99, 300)[0])), encoding="utf-8")
        rc, out = self.tool("--doc", "Scan", "--file", str(other))
        self.assertEqual(rc, 0, out); self.assertIn("it should not be made a witness of this text", out)
        rc, out = self.tool("--doc", "Scan", "--file", str(other), "--write")
        self.assertEqual(rc, 1); self.assertIn("refused", out)
        rc, out = self.tool("--doc", "Scan", "--file", str(other), "--write", "--force", "--slug", "other")
        self.assertEqual(rc, 0, out); self.assertTrue((self.t / "data" / "raw_witness" / "Scan__w_other").is_dir())

    def test_fetch_from_a_listed_host_only(self):
        rc, out = self.tool("--doc", "Scan", "--url", "https://example.com/x.htm")
        self.assertEqual(rc, 1); self.assertIn("is not one of the e-text hosts", out)
        rc, out = self.tool("--doc", "Scan", "--url", "https://archive.org/details/in.ernet.dli.2015.1")
        self.assertEqual(rc, 1); self.assertIn("source_desk.py --doc Scan --fetch in.ernet.dli.2015.1 --kind text", out)
        body = self.src.read_bytes()

        class H(http.server.BaseHTTPRequestHandler):
            def do_GET(self):
                self.send_response(200); self.send_header("Content-Length", str(len(body))); self.end_headers()
                self.wfile.write(body)

            def log_message(self, *a):
                pass
        s = socket.socket(); s.bind(("127.0.0.1", 0)); port = s.getsockname()[1]; s.close()
        srv = http.server.HTTPServer(("127.0.0.1", port), H)
        th = threading.Thread(target=srv.serve_forever, daemon=True); th.start()
        try:
            env_hosts = os.environ.get("SA_ETEXT_HOSTS")
            os.environ["SA_ETEXT_HOSTS"] = "127.0.0.1"
            os.environ["NO_PROXY"] = os.environ["no_proxy"] = "127.0.0.1,localhost"
            rc, out = self.tool("--doc", "Scan", "--url", "http://127.0.0.1:%d/gretil/sa_text.txt" % port)
        finally:
            srv.shutdown(); srv.server_close()
            if env_hosts is None:
                os.environ.pop("SA_ETEXT_HOSTS", None)
            else:
                os.environ["SA_ETEXT_HOSTS"] = env_hosts
        self.assertEqual(rc, 0, out)
        saved = self.t / "sources" / "Scan" / "sa_text.txt"
        self.assertEqual(saved.read_bytes(), body)
        side = json.loads((saved.parent / "sa_text.txt.json").read_text(encoding="utf-8"))
        self.assertEqual(side["mark"], "ETEXT_WITNESS_2026_10_11"); self.assertIn("/gretil/sa_text.txt", side["url"])
        self.assertIn("WITNESS: the same work", out)
        self.assertIn("as a witness of Scan", out)


class JudgeV2(unittest.TestCase):
    """repair_text.py's judge, made exact: letters misread count for texts cut into long passages only; two
    vision pages are not a measurement; a page vision failed on is no disagreement."""
    DEVA = "\u0905\u0925 \u092f\u094b\u0917\u093e\u0928\u0941\u0936\u093e\u0938\u0928\u092e\u094d \u0935\u093f\u0930\u093e\u091f\u0903 \u0927\u0930\u094d\u092e\u0903"

    @classmethod
    def setUpClass(cls):
        cls.rt = load("repair_text_v2", SCRIPTS / "repair_text.py")

    def judge(self, rows, vision=Path("/nonexistent"), pages=0):
        return self.rt.judge(rows, vision, "D", max_pages=pages)

    def test_letters_count_in_long_passages_only(self):
        for n_deva, want_long in ((5, "moderate"), (3, "material")):
            seg = (self.DEVA + " ") * n_deva + "aa "
            long_ = self.judge([(i, seg * 12, "tesseract", False, 0.9) for i in range(1, 21)])
            short = self.judge([(i // 6 + 1, seg, "tesseract", False, 0.9) for i in range(120)])
            self.assertEqual(long_["misread_pct"], 0.0, "no passage reaches the 3% a verse")
            self.assertEqual(long_["level"], want_long, long_["misread_letters_pct"])
            self.assertEqual(short["level"], "cosmetic", "verses: the verse rule alone")

    def test_two_vision_pages_are_not_a_measurement_and_failed_pages_do_not_count(self):
        other = "\u0915\u0916\u0917 \u0918\u0919\u091a \u091b\u091c\u091d " * 12
        with tempfile.TemporaryDirectory() as td:
            v = Path(td)
            for pg in range(1, 6):
                (v / ("D_%04d.jsonl" % pg)).write_text(json.dumps({"text": other}) + "\n", encoding="utf-8")
            two = self.judge([(pg, self.DEVA * 4, "tesseract", False, 0.9) for pg in range(1, 3)], v, 40)
            self.assertEqual((two["agree_pages"], two["level"]), (2, "cosmetic"))
            five = self.judge([(pg, self.DEVA * 4, "tesseract", False, 0.9) for pg in range(1, 6)], v, 40)
            self.assertEqual((five["agree_pages"], five["level"]), (5, "material"))
            failed = self.judge([(pg, self.DEVA * 4, "vision-fallback-tesseract", False, 0.9) for pg in range(1, 6)], v, 40)
            self.assertNotIn("agree_pages", failed); self.assertEqual(failed["level"], "cosmetic")
            (v / "D_0001.jsonl").write_text(json.dumps({"text": "\u0915\u0916\u0917 " * 3}) + "\n", encoding="utf-8")
            short = self.judge([(1, self.DEVA * 4, "tesseract", False, 0.9)], v, 40)
            self.assertNotIn("agree_pages", short, "a short vision page is a failed one")


class TheMirror(unittest.TestCase):
    def test_a_witness_is_not_mirrored_until_adopted(self):
        cs = load("corpus_sync_witness", SCRIPTS / "corpus_sync.py")
        with tempfile.TemporaryDirectory() as td:
            v = Path(td) / "v.jsonl"
            con = sqlite3.connect(":memory:")
            con.executescript("CREATE TABLE docs(id INTEGER PRIMARY KEY, code TEXT, category TEXT);"
                              "INSERT INTO docs(code) VALUES('Scan'),('Scan__w_gretil');")
            old = os.environ.get("SA_SOURCE_VERDICTS")
            os.environ["SA_SOURCE_VERDICTS"] = str(v)
            try:
                v.write_text(json.dumps({"doc": "Scan__w_gretil", "status": "witness"}) + "\n")
                self.assertEqual([d[1] for d in cs.live_docs(con)], ["Scan"])
                with open(v, "a") as f:
                    f.write(json.dumps({"doc": "Scan__w_gretil", "status": "released"}) + "\n")
                self.assertEqual([d[1] for d in cs.live_docs(con)], ["Scan", "Scan__w_gretil"])
            finally:
                if old is None:
                    os.environ.pop("SA_SOURCE_VERDICTS", None)
                else:
                    os.environ["SA_SOURCE_VERDICTS"] = old

    def test_source_desk_sends_a_fetched_text_here(self):
        s = (SCRIPTS / "source_desk.py").read_text(encoding="utf-8")
        self.assertIn("etext_witness.py --doc %s --file", s); self.assertNotIn("is the next build (SOURCE_DESK S2)", s)


class Dashboard(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.d = load("dashboard_etext_witness", SCRIPTS / "dashboard.py")
        cls.tmp = tempfile.TemporaryDirectory()
        t = cls.t = Path(cls.tmp.name)
        d = cls.d
        d.JOBS_LOG_PATH = t / "jobs.jsonl"
        d.SOURCE_DESK_DIR = t / "source_desk"
        d.SOURCES_DIR = t / "sources"
        d.WITNESS_DIR = t / "data" / "raw_witness"
        d.WITNESSES_LOG = t / "data" / "witnesses.jsonl"
        cls.c = d.app.test_client()
        (t / "sources" / "Scan").mkdir(parents=True)
        (t / "sources" / "Scan" / "sa_text.htm").write_text("x")
        (t / "sources" / "Scan" / "sa_text.htm.json").write_text(json.dumps({"url": "https://gretil.sub.uni-goettingen.de/x.htm"}))
        (t / "sources" / "Scan" / "scan.pdf").write_bytes(b"%PDF")
        (t / "sources" / "Scan" / "bad;name.txt").write_text("x")   # a name Windows allows that the page will not offer
        (t / "data" / "raw_witness" / "Scan__w_gretil").mkdir(parents=True)
        (t / "data" / "raw_witness" / "Scan__w_gretil" / "align.json").write_text(json.dumps({"offers": [
            {"page": 15, "why": "the scan cannot read it", "refs": "1.141-1.150", "text": "\u0915\u0916 \u0965", "lo": 140, "hi": 149},
            {"page": 30, "why": "x", "text": "", "note": "too many"}]}))
        d.WITNESSES_LOG.write_text(json.dumps({"doc": "Scan", "witness": "Scan__w_gretil", "site": "gretil", "verses": 400,
                                               "pages": 20, "coverage": 0.97, "order": 1.0, "opinion": "the same work",
                                               "at": "2026-10-11T22:00:00"}) + "\n")
        (t / "data" / "source_verdicts.jsonl").write_text(json.dumps({"doc": "Scan__w_gretil", "status": "witness", "of": "Scan",
                                                                      "site": "gretil", "at": "2026-10-11T22:00:00"}) + "\n")
        cls.db = str(t / "data" / "context.db")
        con = sqlite3.connect(cls.db)
        con.executescript("CREATE TABLE docs(id INTEGER PRIMARY KEY, code TEXT, category TEXT);"
                          "CREATE TABLE passages(id INTEGER PRIMARY KEY, doc_id INT, page_no INT, idx INT, text TEXT, translation TEXT);"
                          "INSERT INTO docs VALUES(1,'Scan','agama');")
        con.commit(); con.close()

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def post(self, body):
        got = []
        orig = self.d.launch
        self.d.launch = lambda kind, doc, argv, then=None, mode="": (got.append((kind, doc, argv, mode)) or "j")
        try:
            r = self.c.post("/api/repair", json=body)
        finally:
            self.d.launch = orig
        return r, got

    def test_the_witness_step(self):
        r, got = self.post({"doc": "Scan", "step": "witness", "file": "sa_text.htm"})
        self.assertEqual(r.status_code, 200)
        kind, doc, argv, mode = got[0]
        self.assertEqual((kind, doc, mode), ("repair", "Scan", "witness"))
        i = [k for k, x in enumerate(argv) if str(x).endswith("etext_witness.py")][0]
        self.assertEqual(argv[i + 1:i + 5], ["--doc", "Scan", "--from-dashboard", "--file"])
        self.assertTrue(argv[i + 5].endswith(os.path.join("sources", "Scan", "sa_text.htm")))
        r, got = self.post({"doc": "Scan", "step": "witness", "file": "sa_text.htm", "write": 1})
        self.assertEqual(got[0][2][-1], "--write")
        r, got = self.post({"doc": "Scan", "step": "witness", "url": "https://gretil.sub.uni-goettingen.de/a b"})
        self.assertEqual(r.status_code, 400)
        r, got = self.post({"doc": "Scan", "step": "witness", "url": "https://gretil.sub.uni-goettingen.de/gretil/x.htm"})
        self.assertEqual(got[0][2][-2:], ["--url", "https://gretil.sub.uni-goettingen.de/gretil/x.htm"])
        r, got = self.post({"doc": "Scan", "step": "witness", "ingest": "Scan__w_gretil", "write": 1})
        self.assertEqual(got[0][0], "repair_use", "an ingest writes the database: it waits for the translate lock")
        self.assertEqual(got[0][2][-3:], ["--ingest", "--witness", "Scan__w_gretil"])
        for bad in ({"file": "../x"}, {"file": ".hidden"}, {"ingest": "Other__w_gretil"}, {"ingest": "Scan"}, {}):
            self.assertEqual(self.post(dict(bad, doc="Scan", step="witness"))[0].status_code, 400, bad)

    def test_the_sources_answer_holds_the_witnesses(self):
        j = self.c.get("/api/repair/sources?doc=Scan").get_json()
        self.assertTrue(j["missing"])
        f = {x["name"]: x for x in j["fetched"]}
        self.assertEqual(sorted(f), ["bad;name.txt", "sa_text.htm", "scan.pdf"])
        self.assertTrue(f["sa_text.htm"]["ok"]); self.assertFalse(f["bad;name.txt"]["ok"])
        self.assertEqual(f["scan.pdf"]["kind"], "pdf")
        self.assertEqual(f["sa_text.htm"]["url"], "https://gretil.sub.uni-goettingen.de/x.htm")
        w = j["witnesses"][0]
        self.assertEqual((w["witness"], w["state"], w["coverage"]), ("Scan__w_gretil", "local only", 0.97))
        self.assertEqual(w["offers"][0]["page"], 15)

    def test_the_repair_page(self):
        h = self.c.get("/repair/Scan?db=" + self.db).get_data(as_text=True)
        self.assertIn('id="srcurl-Scan"', h); self.assertIn("Fetch it and read it as a witness", h)
        self.assertIn("function _rpWitness", h)
        self.assertNotIn("__", h.replace("__name__", "").replace("__w_", ""))
        if node():
            js = re.search(r"<script>(.*?)</script>", h, re.S).group(1)
            p = self.t / "page.js"; p.write_text(js, encoding="utf-8")
            r = subprocess.run([node(), "--check", str(p)], capture_output=True, text=True)
            self.assertEqual(r.returncode, 0, r.stderr)

    def test_the_script_reads_a_witness_next_step(self):
        if not node():
            self.skipTest("node is not installed")
        q = 'python scripts\\etext_witness.py --doc Scan --file "D:\\Sanksrit Automatons\\x\\sources\\Scan\\sa_text.htm"'
        cases = [(q, {"step": "witness", "file": "sa_text.htm"}),
                 (q + " --write", {"step": "witness", "write": 1, "file": "sa_text.htm"}),
                 ("python scripts\\etext_witness.py --doc Scan --ingest --witness Scan__w_gretil", {"step": "witness", "ingest": "Scan__w_gretil"}),
                 (q + " --page N   (the witness's reading of a page)", None)]
        js = self.d._REPAIR_JS + "\nvar out = [];\n" + "".join(
            "out.push(_rpNext(%s));\n" % json.dumps(n) for n, _ in cases) + "console.log(JSON.stringify(out));\n"
        p = self.t / "next.js"; p.write_text("var document={getElementById:function(){return null;}};\n" + js, encoding="utf-8")
        r = subprocess.run([node(), str(p)], capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stderr)
        got = json.loads(r.stdout.strip().splitlines()[-1])
        for (n, want), g in zip(cases, got):
            if want is None:
                self.assertIsNone(g, n)
            else:
                self.assertEqual({k: g[k] for k in want}, want, n)

    def test_the_card_of_a_witness(self):
        rec = {"status": "witness", "of": "Scan", "site": "gretil", "at": "2026-10-11T22:00:00"}
        h = self.d._repair_html("Scan__w_gretil", "", [], rec, None)
        self.assertIn("A witness of Scan (gretil), made on 2026-10-11", h)
        self.assertIn("Publish it to the site", h); self.assertIn("Translate it now", h)
        self.assertIn("Scan__w_gretil", self.d._source_verdicts(self.t / "data"))


class ThePatcher(unittest.TestCase):
    FILES = ("repair_text.py", "corpus_sync.py", "source_desk.py", "dashboard.py")

    def test_it_applies_once_to_what_it_found(self):
        baks = {f: sorted(SCRIPTS.glob(f + ".bak_etextwitness_*")) for f in self.FILES}
        if not all(baks.values()):
            self.skipTest("no pre-patch copies beside the scripts (the patcher's backups) to replay it on")
        with tempfile.TemporaryDirectory() as td:
            t = Path(td); (t / "scripts").mkdir()
            for f in self.FILES:
                shutil.copy2(baks[f][0], t / "scripts" / f)
            shutil.copy2(TOOL, t / "scripts" / "etext_witness.py")
            (t / ".gitignore").write_bytes(b"data/raw/\r\nsources/\r\n")
            pat = [sys.executable, str(SCRIPTS / "patch_etext_witness_2026_10_11.py")]
            r = subprocess.run(pat + ["--check"], cwd=td, capture_output=True, text=True)
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
            r = subprocess.run(pat, cwd=td, capture_output=True, text=True)
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
            for f in self.FILES:
                # BENCHMARK_2026_10_11 came after, then QUALITY_2026_10_11: the first later backup is this patch's result
                later = sorted(SCRIPTS.glob(f + ".bak_benchmark_*")) or sorted(SCRIPTS.glob(f + ".bak_quality_*"))
                want = later[0] if later else (SCRIPTS / f)
                self.assertEqual((t / "scripts" / f).read_bytes(), want.read_bytes(), f)
            g = (t / ".gitignore").read_bytes()
            self.assertIn(b"data/raw_witness/\r\ndata/source_judged/\r\n", g, "its line endings kept")
            self.assertIn("Nothing to do", subprocess.run(pat, cwd=td, capture_output=True, text=True).stdout)
            # all or nothing: an anchor that is not there leaves every file as it was
            for f in self.FILES:
                shutil.copy2(baks[f][0], t / "scripts" / f)
            p = t / "scripts" / "source_desk.py"
            p.write_bytes(p.read_bytes().replace(b"ingesting an e-text as a witness is the next build", b"something else"))
            r = subprocess.run(pat, cwd=td, capture_output=True, text=True)
            self.assertEqual(r.returncode, 1); self.assertIn("anchor", r.stdout)
            self.assertNotIn(b"ETEXT_WITNESS", (t / "scripts" / "repair_text.py").read_bytes(), "all or nothing")

    def test_ascii_and_marks(self):
        for p in (TOOL, SCRIPTS / "patch_etext_witness_2026_10_11.py", Path(__file__)):
            b = p.read_bytes()
            self.assertTrue(all(x < 128 for x in b), p); self.assertIn(b"ETEXT_WITNESS_2026_10_11", b)


if __name__ == "__main__":
    unittest.main()
