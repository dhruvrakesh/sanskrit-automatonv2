# -*- coding: ascii -*-
"""EXPORT_PDF_2026_10_03. python -m unittest tests.test_export_pdf -v
No browser is launched; checks the print stylesheet and engine selection only."""
import importlib.util, sys, tempfile, unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent


def load():
    spec = importlib.util.spec_from_file_location("export_pdf_under_test", str(REPO / "scripts" / "export_pdf.py"))
    m = importlib.util.module_from_spec(spec); sys.modules[spec.name] = m; spec.loader.exec_module(m)
    return m


SRC = "<!doctype html><html><head><title>Mallapurana \u2014 Sa/En/Hi</title><style>body{}</style></head><body>x</body></html>"


class ExportPdf(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.m = load()

    def test_print_css_is_appended_once_and_screen_css_kept(self):
        out = self.m.build_print_html(SRC, "A4")
        self.assertIn("EXPORT_PDF_2026_10_03", out)
        self.assertIn("<style>body{}</style>", out, "the screen stylesheet is untouched")
        self.assertIn('content: "Mallapurana \u2014 Sa/En/Hi"', out, "running title from <title>")
        self.assertLess(out.index("EXPORT_PDF"), out.index("</head>"))
        self.assertEqual(self.m.build_print_html(out, "A4"), out, "idempotent")

    def test_sizes(self):
        self.assertIn("size: 176mm 250mm", self.m.build_print_html(SRC, "B5"))
        self.assertIn("size: A4", self.m.build_print_html(SRC, "a4"))

    def test_title_quotes_cannot_break_the_css(self):
        out = self.m.build_print_html(SRC.replace("Mallapurana", 'Mal"la\\pu'), "A4")
        self.assertIn("content: \"Mal'lapu", out)

    def test_find_browser(self):
        with tempfile.TemporaryDirectory() as t:
            exe = Path(t) / "msedge.exe"; exe.write_text("")
            self.assertEqual(self.m.find_browser(None, [str(Path(t) / "nope.exe"), str(exe)]), str(exe))
            self.assertIsNone(self.m.find_browser(str(Path(t) / "missing.exe")))


if __name__ == "__main__":
    unittest.main()
