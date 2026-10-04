# -*- coding: ascii -*-
"""EXPORT_IMAGES_2026_10_04 - approved images placed in export_html (opt-in).
Fails before patch_export_images.py (no --images switch), passes after."""
import os, re, shutil, sqlite3, subprocess, sys, tempfile, unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))

SA = "\u0927\u0930\u094d\u092e\u0915\u094d\u0937\u0947\u0924\u094d\u0930\u0947 \u0915\u0941\u0930\u0941\u0915\u094d\u0937\u0947\u0924\u094d\u0930\u0947 \u0938\u092e\u0935\u0947\u0924\u093e \u092f\u0941\u092f\u0941\u0924\u094d\u0938\u0935\u0903 \u0965"
HI = "\u0927\u0930\u094d\u092e\u0915\u094d\u0937\u0947\u0924\u094d\u0930 \u092e\u0947\u0902 \u090f\u0915\u0924\u094d\u0930 \u092f\u094b\u0926\u094d\u0927\u093e\u0964"


def _png(path: Path):
    try:
        from PIL import Image
        Image.new("RGB", (60, 40), (200, 180, 140)).save(path, "PNG")
    except Exception:  # a valid 1x1 PNG
        import base64
        path.write_bytes(base64.b64decode(
            "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg=="))


class ExportImages(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="expimg_"))
        self.db = self.tmp / "t.db"
        import db_utils, images
        con = sqlite3.connect(str(self.db))
        db_utils.ensure_schema(con)
        con.execute("INSERT INTO docs(code, category) VALUES('TestDoc','upapurana')")
        did = con.execute("SELECT id FROM docs WHERE code='TestDoc'").fetchone()[0]
        for pg in (1, 2, 3):
            for ix in (1, 2):
                tt = "noise" if (pg, ix) == (3, 1) else "mula"
                cur = con.execute(
                    "INSERT INTO passages(doc_id,page_no,idx,text,text_type,translation,verse_ref) VALUES(?,?,?,?,?,?,?)",
                    (did, pg, ix, SA + " %d.%d" % (pg, ix), tt,
                     "English rendering of verse %d.%d, about the field of dharma." % (pg, ix), "%d.%d" % (pg, ix)))
                con.execute("INSERT INTO translations_l10n(passage_id,lang,translation) VALUES(?,?,?)",
                            (cur.lastrowid, "hi", HI + " %d.%d" % (pg, ix)))
        images.ensure_schema(con)
        imgdir = self.tmp / "img"; imgdir.mkdir()
        rows = [  # (status, kind, page, idx, title)
            ("approved", "generated", 2, 1, "Wrestlers at dawn"),
            ("approved", "edition-plate", 3, 1, "Plate on a noise row"),   # verse filtered -> section end
            ("approved", "generated", 9, 1, "Outside the page range"),
            ("draft", "generated", 1, 1, "A draft"),
            ("retired", "generated", 1, 2, "A retired one"),
        ]
        for i, (st, kind, pg, ix, title) in enumerate(rows, 1):
            p = imgdir / ("%d.png" % i); _png(p)
            con.execute("""INSERT INTO doc_images(doc_id, lineage_id, version, kind, status, title, caption_en,
                           caption_hi, context_note, anchor_page, anchor_idx, path, created_at)
                           VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                        (did, i, 1, kind, st, title, "Caption EN %d" % i, HI + " %d" % i,
                         "Why it belongs %d" % i, pg, ix, str(p), "2026-10-04"))
        con.commit(); con.close()
        self.out = self.tmp / "exports"

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def run_export(self, *extra):
        cmd = [sys.executable, str(SCRIPTS / "export_html.py"), "--db", str(self.db), "--doc", "TestDoc",
               "--from", "1", "--to", "3", "--out", str(self.out), "--sanskrit", "--debug"] + list(extra)
        p = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", cwd=str(ROOT))
        self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
        m = re.search(r"\[export\] wrote (.+?) \|", p.stdout)
        self.assertTrue(m, p.stdout)
        return Path(m.group(1)).read_text(encoding="utf-8"), Path(m.group(1)).name, p.stdout

    def test_default_has_no_figures_and_plain_name(self):
        html, name, _ = self.run_export("--hindi", "--side-by-side")
        self.assertNotIn("<figure", html)
        self.assertNotIn("figure.plate", html)
        self.assertEqual(name, "TestDoc_1-3_tri.html")

    def test_approved_placed_after_its_verse(self):
        html, name, out = self.run_export("--hindi", "--side-by-side", "--images", "approved")
        self.assertEqual(name, "TestDoc_1-3_tri_img.html")
        self.assertIn("figure.plate", html)                       # CSS only in this file
        self.assertEqual(html.count("<figure class='plate'"), 2)  # draft, retired, out-of-range excluded
        a = html.index("verse 2.1,"); f = html.index("Wrestlers at dawn"); b = html.index("verse 2.2,")
        self.assertTrue(a < f < b, "figure must follow its anchored verse")
        self.assertIn("data:image/", html)
        self.assertIn("generated, not a historical source", html)
        self.assertIn("Plate from the source edition", html)
        self.assertNotIn("A draft", html); self.assertNotIn("A retired one", html)
        self.assertIn("images: 3 approved, 2 placed, 1 outside pages 1-3", out)

    def test_filtered_anchor_goes_to_section_end(self):
        html, _, _ = self.run_export("--images", "approved")
        pl = html.index("Plate on a noise row")
        self.assertGreater(pl, html.index("verse 3.2,"))
        self.assertLess(pl, html.rindex("</section>"))

    def test_hindi_only_uses_hindi_caption_and_label(self):
        html, name, _ = self.run_export("--hindi-only", "--images", "approved")
        self.assertTrue(name.endswith("_hi_img.html"), name)
        self.assertIn(HI + " 1", html)
        self.assertIn("\u0910\u0924\u093f\u0939\u093e\u0938\u093f\u0915 \u0938\u094d\u0930\u094b\u0924 \u0928\u0939\u0940\u0902", html)
        self.assertNotIn("Caption EN 1", html)

    def test_no_image_table_is_harmless(self):
        con = sqlite3.connect(str(self.db)); con.execute("DROP TABLE doc_images"); con.commit(); con.close()
        html, _, out = self.run_export("--images", "approved")
        self.assertNotIn("<figure", html)
        self.assertIn("images: 0 approved, 0 placed", out)


if __name__ == "__main__":
    unittest.main()
