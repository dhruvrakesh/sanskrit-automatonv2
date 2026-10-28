# -*- coding: ascii -*-
"""VEDIC_LLA_2026_10_28: the Vedic l of a romanized e-text (l with a dot below between vowels) is read as the
consonant U+0933, not as the vowel l (U+090C) that indic_transliteration writes; a vowel l after a consonant (its
sign) or at a word's start stays; lla=False reads as before; mend_witness.py finds a witness read the old way
"respelled", naming "the Vedic l"; the patch replays once. Temp files only."""
import json, sqlite3, subprocess, sys, tempfile, types, unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "scripts"))
PAT = REPO / "scripts" / "patch_vedic_lla_2026_10_28.py"
MARK = "VEDIC_LLA_2026_10_28"
FILES = ("scripts/etext_witness.py", "scripts/mend_witness.py", "tests/test_etext_refs_2026_10_21.py",
         "tests/test_etext_prose_2026_10_21.py", "tests/test_etext_prose2_2026_10_22.py", "tests/test_etext_dots_2026_10_22.py",
         "tests/test_witness_fix_2026_10_22.py", "tests/test_etext_analysis_2026_10_22.py")
try:
    import etext_witness as EW
    HAVE = hasattr(EW, "vedic_lla")
except Exception:   # an older etext_witness.py, or one that does not import here
    EW, HAVE = None, False
try:
    import indic_transliteration  # noqa: F401
    TRANS = True
except ImportError:
    TRANS = False

II, LL, EE, L_VOW = "\u012b", "\u1e37", "\u0947", "\u090c"


@unittest.skipUnless(HAVE, "etext_witness.py without VEDIC_LLA_2026_10_28")
class TheRule(unittest.TestCase):
    def test_devanagari_mend(self):
        f = EW.vedic_lla
        self.assertEqual(f("\u0908\u090c\u090f"), "\u0908\u0933\u0947", "iile: the e after it as its sign")
        self.assertEqual(f("\u092a\u0930\u093f\u0935\u0943\u090c\u0939\u092e\u094d"),
                         "\u092a\u0930\u093f\u0935\u0943\u0933\u094d\u0939\u092e\u094d", "parivrlham: a virama before h")
        self.assertEqual(f("\u090f\u090c\u0905\u0915\u094b"), "\u090f\u0933\u0915\u094b", "elako: an a as none")
        self.assertEqual(f("\u090c\u0915\u093e\u0930"), "\u090c\u0915\u093e\u0930", "a word's first letter: the vowel l")
        self.assertEqual(f("\u0915\u0962\u092a\u094d\u0924"), "\u0915\u0962\u092a\u094d\u0924", "klpta: the sign, kept")
        self.assertEqual(f("\u0964 \u090c"), "\u0964 \u090c", "after a danda and a space: a word's start")

    @unittest.skipUnless(TRANS, "indic_transliteration is not installed")
    def test_to_deva(self):
        self.assertEqual(EW.to_deva(II + LL + "e", "iast"), "\u0908\u0933\u0947")
        self.assertEqual(EW.to_deva("m" + II + LL + "hu\u1e63e", "iast"), "\u092e\u0940\u0933\u094d\u0939\u0941\u0937\u0947")
        self.assertEqual(EW.to_deva("k" + LL + "pta", "iast"), "\u0915\u0962\u092a\u094d\u0924")
        old = EW.to_deva(II + LL + "e", "iast", lla=False)
        self.assertIn(L_VOW, old, "lla=False: the reading before")
        self.assertIn(L_VOW, EW.to_deva(II + LL + "e", "iast", ortho=False), "ortho=False: the reading of 21 Oct")
        self.assertEqual(EW.to_deva("\u0908\u0933\u0947", "devanagari"), "\u0908\u0933\u0947", "Devanagari: as it is")

    @unittest.skipUnless(TRANS, "indic_transliteration is not installed")
    def test_mend_witness_finds_it(self):
        import mend_witness as MW
        roman = "parivr\u0325" + LL + "ham " + II + LL + "e |"
        old = MW.convert(roman, "iast", True, lla=False)
        new = MW.convert(roman, "iast", True)
        self.assertNotEqual(old, new)
        with tempfile.TemporaryDirectory() as td:
            t = Path(td)
            w = t / "raw_witness" / "x__w_gretil"
            w.mkdir(parents=True)
            (w / "witness.json").write_text(json.dumps({"scheme": "iast", "mode": "verses", "site": "gretil"}),
                                            encoding="utf-8")
            (w / "x__w_gretil_0001.jsonl").write_text(json.dumps(
                {"text": old, "text_type": "mula", "meta": {"roman_source": roman}}, ensure_ascii=False) + "\n",
                encoding="utf-8")
            db = t / "c.db"
            con = sqlite3.connect(str(db))
            con.executescript("CREATE TABLE docs(id INTEGER PRIMARY KEY, code TEXT);"
                              "CREATE TABLE passages(id INTEGER PRIMARY KEY, doc_id INTEGER, page_no INTEGER, idx INTEGER,"
                              " text TEXT, text_type TEXT, verse_ref TEXT, chapter TEXT);")
            con.execute("INSERT INTO docs VALUES (1, 'x__w_gretil')")
            con.execute("INSERT INTO passages VALUES (1, 1, 1, 1, ?, 'mula', NULL, NULL)",
                        (MW.normalize_sanskrit(old.strip()),))
            con.commit(); con.close()
            a = types.SimpleNamespace(doc="x__w_gretil", out_dir=str(t / "raw_witness"), db=str(db), immutable=False)
            p = MW.plan(a)
            self.assertNotIn("refuse", p, p.get("refuse"))
            it = p["items"][0]
            self.assertEqual(it["kind"], "respelled")
            self.assertIn("the Vedic l", it["what"])
            self.assertEqual(it["new"], new)


def as_left(rel: str) -> bytes:
    """The file as the patch left it: the oldest later backup that carries MARK, else the file now."""
    p = REPO / rel
    later = [b for b in p.parent.glob(p.name + ".bak_*") if ".bak_vedlla_" not in b.name and MARK.encode() in b.read_bytes()]
    return min(later, key=lambda b: b.stat().st_mtime).read_bytes() if later else p.read_bytes()


@unittest.skipUnless(PAT.exists(), "patch_vedic_lla_2026_10_28.py is not here")
class ThePatch(unittest.TestCase):
    def test_ascii(self):
        self.assertTrue(PAT.read_bytes().isascii())
        for rel in FILES:
            if MARK.encode() in (REPO / rel).read_bytes():
                self.assertTrue((REPO / rel).read_bytes().isascii(), rel)

    def test_replays_once(self):
        with tempfile.TemporaryDirectory() as td:
            t = Path(td)
            for rel in FILES:
                p = REPO / rel
                bak = sorted(p.parent.glob(p.name + ".bak_vedlla_*"))
                srcb = (bak[0] if bak else p).read_bytes()
                if MARK.encode() in srcb:
                    self.skipTest("only patched copies to replay against")
                (t / rel).parent.mkdir(parents=True, exist_ok=True)
                (t / rel).write_bytes(srcb)
            run = lambda *a: subprocess.run([sys.executable, str(PAT)] + list(a), cwd=str(t), capture_output=True,
                                            text=True)
            r = run("--check")
            self.assertIn("CHECK OK: 8 file(s)", r.stdout, r.stdout + r.stderr)
            r = run()
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
            for rel in FILES:
                got = (t / rel).read_bytes()
                self.assertIn(MARK.encode(), got, rel)
                if MARK.encode() in (REPO / rel).read_bytes():
                    self.assertEqual(got, as_left(rel), rel)
            self.assertIn("Nothing to do", run().stdout)


if __name__ == "__main__":
    unittest.main()
