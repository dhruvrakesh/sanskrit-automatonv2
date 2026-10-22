# -*- coding: ascii -*-
"""GRETIL_LIBRARY_2026_10_22: scripts/gretil_library.py reads GRETIL's cumulative download as a library of witnesses:
the IAST skeleton is the Devanagari one; --catalog reads each text's header (title, source edition and its year, the
CC licence); --match finds which GRETIL text reads which of our texts, by the lift over each file's baseline, and
resumes from its cache; the legacy files the TEI conversion did not take are read too, from their own headers (a pada
index and a second version of one work left out; the notice "for reference purposes only" kept as the rights);
--extract writes one member into sources\\<doc>\\ with its provenance, once. A made-up zip and made-up pages only;
never data/context.db, never the network."""
import csv, json, random, subprocess, sys, tempfile, unittest, zipfile
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
SCRIPTS = REPO / "scripts"
sys.path.insert(0, str(SCRIPTS))
TOOL = SCRIPTS / "gretil_library.py"
MARK = "GRETIL_LIBRARY_2026_10_22"

SYL = [("ka", "\u0915"), ("k\u0101", "\u0915\u093e"), ("gi", "\u0917\u093f"), ("tu", "\u0924\u0941"),
       ("pe", "\u092a\u0947"), ("ro", "\u0930\u094b"), ("ma", "\u092e"), ("na", "\u0928"), ("sa", "\u0938"),
       ("ha", "\u0939"), ("bh\u0101", "\u092d\u093e"), ("dhi", "\u0927\u093f"), ("\u015bu", "\u0936\u0941"),
       ("\u1e63e", "\u0937\u0947"), ("ya", "\u092f"), ("va", "\u0935"), ("la", "\u0932"), ("ja", "\u091c"),
       ("ca", "\u091a"), ("da", "\u0926"), ("\u1e6da", "\u091f"), ("\u1e47a", "\u0923"), ("tha", "\u0925"),
       ("kha", "\u0916"), ("gha", "\u0918"), ("cha", "\u091b"), ("\u1e0da", "\u0921"), ("ba", "\u092c")]


def verses(seed, n=30):
    r = random.Random(seed)
    out = []
    for _ in range(n):
        words = [[r.choice(SYL) for _ in range(r.randint(2, 4))] for _ in range(10)]
        out.append((" ".join("".join(s[0] for s in w) for w in words), " ".join("".join(s[1] for s in w) for w in words)))
    return out


def plain(title, lines, source="Ed. X, Poona 1998."):
    return ("%s\n\n\n# Header\n\n## Data entry: someone\n## Date of this version: 2020-07-31\n\n## Source: \n   - %s\n\n"
            "## Licence:\n   This e-text was provided to GRETIL in good faith.\n   Distributed under a Creative Commons "
            "Attribution-NonCommercial-ShareAlike 4.0 International License.\n\n## Notes:\n   created by mass conversion "
            "from x_u.htm . \n\n# Text\n\n%s\n" % (title, source, "\n".join(lines)))


def legacy(title, kind, lines, source="Based on the ed. by A. N. Someone: D4smrti,\nMadras : Adyar Library 1953"):
    return ("<html><head><title>%s</title></head><body>\n<h2>%s</h2>\n%s<br>\nInput by Oliver Hellwig<br>\n%s<br>\n"
            "THIS  GRETIL  TEXT FILE IS FOR REFERENCE PURPOSES ONLY!<br>\nCOPYRIGHT AND TERMS OF USAGE AS FOR SOURCE "
            "FILE.<br>\nText converted to Unicode (UTF-8).<br>\nFor further information see:<br>\n"
            "http://gretil.sub.uni-goettingen.de/gretil.htm<hr>\n%s\n</body></html>" % (
                title, title.split(",")[0], source.replace("\n", "<br>\n"), kind,
                "<br>\n".join("%s // D4_%d //" % (l, i) for i, l in enumerate(lines, 1))))


@unittest.skipUnless(MARK.encode() in TOOL.read_bytes(), "GRETIL_LIBRARY_2026_10_22 is not here")
class TheSkeleton(unittest.TestCase):
    def test_iast_reads_as_devanagari(self):
        import gretil_library as g
        for i, d in (("agnim \u012b\u1e37e purohita\u1e43", "\u0905\u0917\u094d\u0928\u093f\u092e\u0940\u0933\u0947 "
                      "\u092a\u0941\u0930\u094b\u0939\u093f\u0924\u0902"),
                     ("sa\u1e43gacchadhvam", "\u0938\u0902\u0917\u091a\u094d\u091b\u0927\u094d\u0935\u092e\u094d"),
                     ("sandhi", "\u0938\u0928\u094d\u0927\u093f"), ("sa\u1e43dhi", "\u0938\u0902\u0927\u093f"),
                     ("k\u1e5bta\u1e25 ka\u1e43sa", "\u0915\u0943\u0924\u0903 \u0915\u0902\u0938"),
                     ("dharmak\u1e63etre", "\u0927\u0930\u094d\u092e\u0915\u094d\u0937\u0947\u0924\u094d\u0930\u0947"),
                     ("agnim \u012b\u1e3be", "\u0905\u0917\u094d\u0928\u093f\u092e\u0940\u0933\u0947"),
                     ("m\u012b\u1e3bhu\u1e63e", "\u092e\u0940\u0933\u094d\u0939\u0941\u0937\u0947"),
                     ("dev\u0101m\u0310 eha", "\u0926\u0947\u0935\u093e\u0901 \u090f\u0939")):
            self.assertEqual(g.iast_skel(i), g.dev_skel(d), i)
        for i, d in verses(1, 5):
            self.assertEqual(g.iast_skel(i), g.dev_skel(d))

    def test_the_same_skeleton_as_etext_witness(self):
        import gretil_library as g
        import etext_witness as ew
        for _, d in verses(2, 5):
            self.assertEqual(g.dev_skel(d), ew.skel(d))


@unittest.skipUnless(MARK.encode() in TOOL.read_bytes(), "GRETIL_LIBRARY_2026_10_22 is not here")
class TheLibrary(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        t = self.t = Path(self.tmp.name)
        self.texts = {d: verses(k) for k, d in enumerate(("D1", "D2", "D3"), 10)}
        d4 = [i for i, _ in verses(13)]   # D4: read by a legacy file alone
        d5 = [i for i, _ in verses(14)]   # D5: read in full by a big file that reads a third of each of the others
        d6 = [i for i, _ in verses(15)]   # D6: a TEI file all but one verse, a legacy file all of it
        big = d5 + sum(([i for i, _ in v[:10]] for v in list(self.texts.values()) + [verses(13)]), [])
        with zipfile.ZipFile(t / "1_sanskr.zip", "w") as z:
            for k, (d, vs) in enumerate(self.texts.items()):
                stem = "sa_text%d" % k
                z.writestr("1_sanskr/tei/transformations/plaintext/%s.txt" % stem,
                           plain("Text %d" % k, [i for i, _ in vs]))
                z.writestr("1_sanskr/tei/transformations/html/%s.htm" % stem, "<html><body>%s</body></html>" % k)
            z.writestr("1_sanskr/tei/transformations/plaintext/sa_other.txt",
                       plain("Other", [i for i, _ in verses(99, 60)], source="Calcutta 1888."))
            z.writestr("1_sanskr/tei/transformations/plaintext/sa_big.txt", plain("Big", big))
            z.writestr("1_sanskr/tei/transformations/plaintext/sa_six.txt", plain("Six", d6[:-1]))
            z.writestr("1_sanskr/3_purana/six_pu.htm", legacy("Six, plain text version", "PLAIN TEXT VERSION", d6))
            z.writestr("1_sanskr/1_veda/1_sam/x_u.htm", legacy("Converted", "PLAIN TEXT VERSION", d4))
            z.writestr("1_sanskr/6_sastra/4_dharma/d4_pu.htm", legacy("D4smrti, plain text version",
                                                                      "PLAIN TEXT VERSION", d4))
            z.writestr("1_sanskr/6_sastra/4_dharma/d4_au.htm", legacy("D4smrti", "TEXT WITH PADA MARKERS",
                                                                      [x.replace(" ", " $ ", 1) for x in d4]))
            z.writestr("1_sanskr/6_sastra/4_dharma/d4_iu.htm", legacy("D4smrti", "PADA INDEX", sorted(d4)))
        (t / "data" / "raw").mkdir(parents=True)
        for d, vs in list(self.texts.items()) + [("D4", verses(13)), ("D5", verses(14)), ("D6", verses(15))]:
            for p in range(3):
                (t / "data" / "raw" / ("%s_%04d.jsonl" % (d, p + 1))).write_text("".join(
                    json.dumps({"text": dv}, ensure_ascii=False) + "\n" for _, dv in vs[p * 10:(p + 1) * 10]),
                    encoding="utf-8")
        (t / "exports").mkdir()
        with open(t / "exports" / "source_ledger.csv", "w", newline="", encoding="utf-8-sig") as f:
            w = csv.writer(f)
            w.writerow(["doc", "category", "register", "source"])
            for d in list(self.texts) + ["D4", "D5", "D6"]:
                w.writerow([d, "", "", "tesseract"])
            w.writerow(["D1__w_gretil", "", "witness", "e-text"])

    def tearDown(self):
        self.tmp.cleanup()

    def run_tool(self, *args):
        r = subprocess.run([sys.executable, str(TOOL), "--root", str(self.t), "--zip", str(self.t / "1_sanskr.zip"),
                            "--out-dir", str(self.t / "out")] + list(args), capture_output=True, text=True,
                           encoding="utf-8", timeout=180)
        return r.returncode, r.stdout + r.stderr

    def test_the_catalog_reads_each_header(self):
        rc, out = self.run_tool("--catalog", "--csv", str(self.t / "cat.csv"))
        self.assertEqual(rc, 0, out)
        rows = [json.loads(x) for x in (self.t / "out" / "catalog.jsonl").read_text(encoding="utf-8").splitlines()]
        self.assertEqual(len([x for x in rows if x["section"] == "tei"]), 6)
        leg = {Path(x["member"]).name: x for x in rows if x["section"] == "legacy"}
        self.assertEqual(sorted(leg), ["d4_au.htm", "d4_iu.htm", "d4_pu.htm", "six_pu.htm"], "x_u.htm has its TEI file")
        p = leg["d4_pu.htm"]
        self.assertEqual((p["kind"], p["variant_of"], p["source_year"], p["data_entry"]),
                         ("plain", "", 1953, "Oliver Hellwig"))
        self.assertIn("Adyar Library 1953", p["source"])
        self.assertEqual(p["rights"], "reference only (rights as the source edition's)")
        self.assertIn("FOR REFERENCE PURPOSES ONLY", p["licence"])
        self.assertEqual(p["cc"], "")
        self.assertEqual(p["url"], "https://gretil.sub.uni-goettingen.de/gretil/1_sanskr/6_sastra/4_dharma/d4_pu.htm")
        self.assertEqual(leg["d4_au.htm"]["variant_of"], p["member"], "the version with pada markers is a variant")
        self.assertEqual(leg["d4_iu.htm"]["kind"], "index")
        self.assertIn("read by --match: 2 (pada indexes 1 and variants 1 left out)", out)
        r = [x for x in rows if x["title"] == "Text 0"][0]
        self.assertEqual(r["cc"], "CC BY-NC-SA 4.0")
        self.assertEqual(r["source_year"], 1998)
        self.assertEqual(r["legacy"], "x_u.htm")
        self.assertTrue(r["tei"].endswith("/corpustei/sa_text0.xml"))
        self.assertIn("CC BY-NC-SA 4.0 6", out)
        self.assertIn("1960 or later (its editor's rights may stand): 5", out)

    def test_each_text_finds_its_own(self):
        rc, out = self.run_tool("--match", "--csv", str(self.t / "m.csv"))
        self.assertEqual(rc, 0, out)
        rows = {json.loads(x)["doc"]: json.loads(x) for x in (self.t / "out" / "match.jsonl").read_text(
            encoding="utf-8").splitlines()}
        self.assertEqual(sorted(rows), ["D1", "D2", "D3", "D4", "D5", "D6"], "the witness in the ledger is not matched")
        five = rows["D5"]
        self.assertEqual((Path(five["top"][0]["member"]).name, five["verdict"]), ("sa_big.txt", "a part or a parallel"),
                         "a big file that reads every text of ours is not its witness")
        self.assertLess(five["top"][0]["ratio"], 5)
        six = rows["D6"]["top"]
        self.assertEqual([Path(c["member"]).name for c in six[:2]], ["sa_six.txt", "six_pu.htm"],
                         "the licensed TEI file first, within 0.05 of the legacy one")
        self.assertIn("its CC licence", six[0]["preferred"])
        self.assertGreater(six[1]["lift"], six[0]["lift"])
        top = rows["D4"]["top"][0]
        self.assertEqual((Path(top["member"]).name, top["section"], rows["D4"]["verdict"]),
                         ("d4_pu.htm", "legacy", "strong"))
        self.assertEqual(top["html"], top["member"], "a legacy file is read as it is")
        self.assertEqual(top["rights"], "reference only (rights as the source edition's)")
        for k, d in enumerate(("D1", "D2", "D3")):
            top = rows[d]["top"][0]
            self.assertEqual(Path(top["member"]).name, "sa_text%d.txt" % k)
            self.assertEqual(rows[d]["verdict"], "strong")
            self.assertGreater(top["lift"], 0.9)
            self.assertTrue(top["html"].endswith("/html/sa_text%d.htm" % k))
        rc, out2 = self.run_tool("--match")
        self.assertEqual(rc, 0, out2)
        cache = (self.t / "out" / "match_cache.jsonl").read_text(encoding="utf-8").splitlines()
        self.assertEqual(len(cache), 1 + 6 + 2, "read once: the second run took the cache")
        self.assertFalse([x for x in cache if "d4_au" in x or "d4_iu" in x or "x_u.htm\"," in x[:80]],
                         "neither the index, nor the variant, nor the converted file is read")
        rc, out3 = self.run_tool("--match", "--tei-only")
        self.assertEqual(rc, 0, out3)
        rows = {json.loads(x)["doc"]: json.loads(x) for x in (self.t / "out" / "match.jsonl").read_text(
            encoding="utf-8").splitlines()}
        self.assertNotEqual(rows["D4"]["verdict"], "strong", "--tei-only: the TEI files alone")

    def test_extract_once_with_its_provenance(self):
        m = "1_sanskr/tei/transformations/html/sa_text1.htm"
        rc, out = self.run_tool("--extract", m, "--doc", "D2")
        self.assertEqual(rc, 0, out)
        dest = self.t / "sources" / "D2" / "sa_text1.htm"
        side = json.loads(dest.with_name(dest.name + ".json").read_text(encoding="utf-8"))
        self.assertEqual(side["member"], m)
        self.assertIn("Creative Commons", side["licence"])
        self.assertEqual(side["url"], "https://gretil.sub.uni-goettingen.de/gretil/corpustei/transformations/html/"
                                      "sa_text1.htm", "where the Nirukta's and the Markandeya's html were fetched")
        self.assertEqual(len(side["zip_sha256"]), 64)
        rc, out = self.run_tool("--extract", m, "--doc", "D2")
        self.assertIn("already there", out)
        dest.write_text("changed", encoding="utf-8")
        rc, out = self.run_tool("--extract", m, "--doc", "D2")
        self.assertEqual(rc, 1)
        self.assertIn("REFUSE", out)
        rc, out = self.run_tool("--extract", "1_sanskr/none.htm", "--doc", "D2")
        self.assertNotEqual(rc, 0)

    def test_a_legacy_file_keeps_its_notice(self):
        m = "1_sanskr/6_sastra/4_dharma/d4_pu.htm"
        rc, out = self.run_tool("--extract", m, "--doc", "D4")
        self.assertEqual(rc, 0, out)
        side = json.loads((self.t / "sources" / "D4" / "d4_pu.htm.json").read_text(encoding="utf-8"))
        self.assertIn("FOR REFERENCE PURPOSES ONLY", side["licence"])
        self.assertIn("Adyar Library 1953", side["source"])
        self.assertEqual(side["url"], "https://gretil.sub.uni-goettingen.de/gretil/" + m)


class TheFiles(unittest.TestCase):
    def test_ascii_and_marks(self):
        for f in (TOOL, Path(__file__)):
            b = f.read_bytes()
            self.assertTrue(all(x < 128 for x in b), f.name)
            self.assertIn(MARK.encode(), b, f.name)


if __name__ == "__main__":
    unittest.main()
