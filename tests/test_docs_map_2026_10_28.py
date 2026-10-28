# -*- coding: ascii -*-
"""DOCS98_2026_10_28: scripts/docs_map.py maps the documentation from the files' own first lines: each dated file's
title (its trailing markers moved to their column), date and markers, grouped by what it is about, newest first; the
cloud SQL in the order it is pasted (C2 before C10a, C21 before C23), with its "Needs" line and its checks marked;
the edge functions; the Srangam kits. --write writes once, --check says when it is stale; a backup or the map
itself is never listed. Made-up repositories in temp folders; the real one is mapped read-only."""
import subprocess, sys, tempfile, unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
TOOL = REPO / "scripts" / "docs_map.py"


def make(t: Path):
    (t / "docs" / "cloud" / "C23_corpus-index").mkdir(parents=True)
    (t / "docs" / "srangam" / "B2_SITE_2026-10-28" / "src").mkdir(parents=True)
    (t / "docs" / "srangam" / "B2_SITE_2026-10-28" / "src" / "a.ts").write_text("x\n")
    (t / "README.md").write_text("# The automaton\n")
    (t / "docs" / "STATE_2026-10-18.md").write_text("# The state (18 Oct 2026)\n\nDOCS97_2026_10_25 and more\n")
    (t / "docs" / "VAMSA_2026-10-25.md").write_text("# Vamsa: the lines (25 Oct 2026) (VAMSA_UI_2026_10_25)\n")
    (t / "docs" / "B2_AND_X1C_2026-10-28.md").write_text("# B2 | and X1c (B2_SITE_2026_10_28, X1C_SITE_2026_10_28)\n")
    (t / "docs" / "SCHOLAR_V2_2026-10-14.md").write_text("no title line\n")
    (t / "docs" / "VAMSA_2026-10-25.md.bak_docs97_20261025").write_text("# old\n")
    c = t / "docs" / "cloud"
    (c / "C2_run_2026-10-07.sql").write_text("-- =====\n-- C2 - the run\n-- Needs C1. Re-running it changes nothing.\n")
    (c / "C10a_corner_2026-10-09.sql").write_text("-- C10a - the Corner\n-- Needs C9. Purely additive.\n")
    (c / "C23_index_claims_2026-10-28.sql").write_text("-- ====\n-- C23 - the claims\n-- Needs C21 (and so C4, C5). Re.\n")
    (c / "C23_checks_2026-10-28.sql").write_text("-- C23 checks: read-only\n")
    (c / "C21_index_site_2026-10-25.sql").write_text("-- C21 - the genealogies\n")
    (c / "C21_index_site_2026-10-25.sql.bak_x_20261025").write_text("-- old\n")
    (c / "CHECKS_debt_2026-10-22.sql").write_text("-- CHECKS_debt (DOCS85_2026_10_22)\n")
    (c / "C20_name_links_2026-10-23.sql").write_text("-- SUPERSEDED 2026-10-24: do not paste this file.\n")
    (c / "S2_followup_2026-10-07.sql").write_text("-- S2 (all read-only; one block at a time)\n")


class TheMap(unittest.TestCase):
    def run_tool(self, t, *a):
        return subprocess.run([sys.executable, str(TOOL)] + list(a), cwd=str(t), capture_output=True, text=True,
                              encoding="utf-8")

    def test_the_map(self):
        with tempfile.TemporaryDirectory() as td:
            t = Path(td); make(t)
            out = self.run_tool(t).stdout
            self.assertIn("# The map of the documentation (DOCS98_2026_10_28)", out)
            self.assertIn("5 documents; the newest is of 2026-10-28.", out)
            self.assertLess(out.index("## Start here"), out.index("## Names, relations and genealogies"))
            self.assertIn("| 2026-10-28 | [B2_AND_X1C_2026-10-28.md](B2_AND_X1C_2026-10-28.md) | B2 \\| and X1c | "
                          "B2_SITE_2026_10_28, X1C_SITE_2026_10_28 |", out)
            self.assertLess(out.index("B2_AND_X1C"), out.index("VAMSA_2026"), "newest first")
            self.assertIn("| - | [README.md](../README.md) | The automaton | - |", out)
            self.assertIn("| [SCHOLAR_V2_2026-10-14.md](SCHOLAR_V2_2026-10-14.md) | SCHOLAR_V2_2026-10-14 |", out)
            self.assertNotIn(".bak_", out)
            sql = out[out.index("## The cloud SQL"):]
            order = [sql.index(n) for n in ("C2_run", "C10a_corner", "C21_index_site", "C23_index_claims", "C23_checks")]
            self.assertEqual(order, sorted(order))
            self.assertIn("| [C23_index_claims_2026-10-28.sql](cloud/C23_index_claims_2026-10-28.sql) | change | "
                          "C23 - the claims | Needs C21 (and so C4, C5) |", sql)
            self.assertIn("| checks | C23 checks: read-only | - |", sql)
            self.assertIn("[C23_corpus-index](cloud/C23_corpus-index)", sql)
            self.assertIn("| [CHECKS_debt_2026-10-22.sql](cloud/CHECKS_debt_2026-10-22.sql) | checks |", sql)
            self.assertIn("| [S2_followup_2026-10-07.sql](cloud/S2_followup_2026-10-07.sql) | checks |", sql)
            self.assertIn("| [C20_name_links_2026-10-23.sql](cloud/C20_name_links_2026-10-23.sql) | superseded |", sql)
            self.assertIn("| 2026-10-28 | [B2_SITE_2026-10-28](srangam/B2_SITE_2026-10-28) | 1 |", out)

    def test_write_once_and_check(self):
        with tempfile.TemporaryDirectory() as td:
            t = Path(td); make(t)
            self.assertEqual(self.run_tool(t, "--check").returncode, 1)
            r = self.run_tool(t, "--write")
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
            self.assertIn("wrote docs\\DOCS_MAP.md", r.stdout)
            self.assertEqual(self.run_tool(t, "--check").returncode, 0)
            self.assertIn("Nothing to do", self.run_tool(t, "--write").stdout)
            self.assertNotIn("DOCS_MAP.md](", (t / "docs" / "DOCS_MAP.md").read_text(encoding="utf-8"))
            (t / "docs" / "NEW_2026-10-29.md").write_text("# New\n")
            self.assertEqual(self.run_tool(t, "--check").returncode, 1, "a new file makes the map stale")

    def test_refuses_outside_a_repository(self):
        with tempfile.TemporaryDirectory() as td:
            self.assertEqual(self.run_tool(Path(td)).returncode, 2)

    def test_ascii_and_the_real_repository(self):
        self.assertTrue(TOOL.read_bytes().isascii())
        if (REPO / "docs").is_dir():
            r = self.run_tool(REPO)
            self.assertEqual(r.returncode, 0, r.stderr)
            if (REPO / "docs" / "cloud").is_dir():
                self.assertIn("## The cloud SQL, in the order it is pasted", r.stdout)


if __name__ == "__main__":
    unittest.main()
