# -*- coding: ascii -*-
"""EXPORT_MODE_VISIBLE_2026_09_30.
Run from the repo root:  python -m unittest tests.test_export_mode_ui -v
Reads scripts/dashboard_static.html only. Never touches data/context.db,
the running dashboard or the network. Fails before the patch, passes after."""
import unittest
from pathlib import Path

HTML = Path(__file__).resolve().parent.parent / "scripts" / "dashboard_static.html"


class ExportModeVisible(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.src = HTML.read_text(encoding="utf-8")

    def test_marker(self):
        self.assertIn("EXPORT_MODE_VISIBLE_2026_09_30", self.src)

    def test_row_button_names_edition(self):
        self.assertIn('<span class="exp-mode">\' + esc(exportModeShort()) + \'</span>', self.src)

    def test_select_relabels_rows(self):
        self.assertIn("localStorage.setItem('exportMode',this.value);syncExportLabels()", self.src)

    def test_labels_cover_all_three_modes(self):
        for label in ("(Sa/En/Hi)", "(Hindi)", "(English)"):
            self.assertIn(label, self.src)

    def test_export_all_confirms(self):
        self.assertIn("'Export ALL ' + nExp + ' docs as ' + exportModeShort()", self.src)

    def test_api_contract_unchanged(self):
        # The request body must still carry mode exactly as /api/export expects.
        self.assertIn("body: JSON.stringify({doc, db: cfg.db, out: cfg.exports, mode})", self.src)


if __name__ == "__main__":
    unittest.main()
