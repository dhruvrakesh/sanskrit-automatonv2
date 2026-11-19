# -*- coding: ascii -*-
"""ADMIN_STATUS_2026_11_19 (A1 of docs/ADMIN_REWIRE_2026-11-19.md): C30 as pasted (one change, read-only, the super
admin only, its checks and rollback); the Srangam kit's payload (the page reads one function, says "as of", warns of a
late desk, a late mirror and a call not through the own keys; the route; the sidebar's entry for the super admin);
its patch on made-up checkouts (writes once, refuses a changed file); the plan's page. Nothing is called."""
import hashlib, importlib.util, io, os, re, sys, tempfile, unittest
from contextlib import redirect_stdout
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
MARK = "ADMIN_STATUS_2026_11_19"
C30 = REPO / "docs" / "cloud" / "C30_admin_status_2026-11-19.sql"
KIT = REPO / "docs" / "srangam" / "ADMIN_STATUS_2026-11-19"
PAT = REPO / "scripts" / "patch_srangam_admin_status_2026_11_19.py"
PLAN = REPO / "docs" / "ADMIN_REWIRE_2026-11-19.md"


class TheSql(unittest.TestCase):
    def setUp(self):
        self.s = C30.read_text(encoding="ascii")

    def test_one_change_read_only(self):
        s = self.s
        self.assertEqual(s.count("\nBEGIN;\n"), 1); self.assertEqual(s.count("\nCOMMIT;\n"), 1)
        change = s[s.index("\nBEGIN;\n"):s.index("\nCOMMIT;\n")]
        for k in ("PERFORM rbac._require_super();", "STABLE SECURITY DEFINER SET search_path = ''",
                  "RETURNS TABLE (result jsonb)", "GRANT EXECUTE ON FUNCTION %s TO authenticated",
                  "REVOKE ALL ON FUNCTION %s FROM anon"):
            self.assertIn(k, change, k)
        for w in ("INSERT ", "UPDATE ", "DELETE ", "CREATE TABLE", "ALTER TABLE", "DROP "):
            self.assertNotIn(w, change, w)
        self.assertNotIn("w.info", change, "the desk's own info is not shown")
        for k in ("-- B1", "-- A1", "-- A2", "Rollback (one paste): DROP FUNCTION IF EXISTS public.corpus_admin_status();"):
            self.assertIn(k, s, k)
        self.assertEqual(s.count("$$") % 2, 0)

    def test_every_index_table(self):
        tabs = re.search(r"FOREACH t IN ARRAY ARRAY\[([^\]]*)\]", self.s).group(1)
        got = re.findall(r"'([a-z]+)'", tabs)
        c29 = (REPO / "docs" / "cloud" / "C29_index_vamsas_2026-11-18.sql").read_text(encoding="ascii")
        rel = re.findall(r"WHEN '([a-z]+)' THEN 'corpus\.index_", c29)
        self.assertEqual(sorted(got), sorted(rel))


class TheKit(unittest.TestCase):
    def test_the_page(self):
        p = (KIT / "src/pages/admin/DeskSite.tsx").read_text(encoding="utf-8")
        for k in (MARK, "callMirror<{ result: AdminStatus }>(FN, {})", "const FN = 'corpus_admin_status';",
                  "staleTime: 10 * 60 * 1000", "As of", "Refresh", "OWN_PROVIDERS = ['gemini', 'openai']",
                  "DESK_LATE_MIN = 30", "MIRROR_LATE_H = 3", "Only the super admin may see the desk and the site.",
                  "This page is not switched on yet"):
            self.assertIn(k, p, k)
        for bad in ("dangerouslySetInnerHTML", "supabase.from(", ".insert(", ".update(", ".delete("):
            self.assertNotIn(bad, p, bad)
        app = (KIT / "src/App.tsx").read_text(encoding="utf-8")
        self.assertIn('<Route path="desk-site" element={<DeskSite />} />', app)
        nav = (KIT / "src/components/admin/AdminLayout.tsx").read_text(encoding="utf-8")
        i = nav.index('title: "Desk and site"')
        self.assertIn("superOnly: true", nav[i:i + 200])
        a = (KIT / "_append/RELIABILITY_AUDIT.phaseAV.md").read_text(encoding="utf-8")
        self.assertTrue(a.startswith("## Phase AV - ")); self.assertIn("72. The admin's status", a)
        self.assertTrue((KIT / "src/__tests__/desk-site.test.tsx").exists())

    def test_the_plan(self):
        t = PLAN.read_text(encoding="utf-8")
        for k in ("ADMIN_REWIRE_2026_11_19", "| A1 |", "| A2 |", "| A3 |", "| A4 |", "| A5 |", "built 19 Nov",
                  "yours to approve", "1 admin, 1 super admin and 3 researchers"):
            self.assertIn(k, t, k)


@unittest.skipUnless(PAT.exists(), "the Srangam patch is not here")
class ThePatch(unittest.TestCase):
    def setUp(self):
        spec = importlib.util.spec_from_file_location("pat_adminstatus", str(PAT))
        self.mod = importlib.util.module_from_spec(spec); spec.loader.exec_module(self.mod)
        self.td = tempfile.TemporaryDirectory(); self.t = Path(self.td.name)
        (self.t / "package.json").write_text("{}", encoding="ascii")
        (self.t / "src/lib").mkdir(parents=True)
        (self.t / "src/lib/indexSite.ts").write_text("// VAMSA_WAYIN_2026_11_18\n", encoding="ascii")
        self.fake = {}
        for rel in self.mod.REPLACE:
            p = self.t / rel; p.parent.mkdir(parents=True, exist_ok=True)
            b = ("// %s as main had it\r\n" % rel).encode("ascii"); p.write_bytes(b); self.fake[rel] = b
        (self.t / "docs").mkdir()
        (self.t / "docs/RELIABILITY_AUDIT.md").write_bytes(b"# Audit\n\n## Phase AU - x (VAMSA_WAYIN_2026_11_18)\n")
        self.mod.REPLACE = {rel: hashlib.md5(b.replace(b"\r\n", b"\n")).hexdigest() for rel, b in self.fake.items()}

    def tearDown(self):
        self.td.cleanup()

    def run_main(self, *a):
        old_cwd, old_argv, buf = os.getcwd(), sys.argv, io.StringIO()
        try:
            os.chdir(str(self.t)); sys.argv = ["x"] + list(a)
            with redirect_stdout(buf):
                rc = self.mod.main()
        finally:
            os.chdir(old_cwd); sys.argv = old_argv
        return rc, buf.getvalue()

    def test_applies_once_keeping_line_endings(self):
        rc, out = self.run_main("--check"); self.assertIn("CHECK OK: 5 file(s)", out)
        rc, out = self.run_main(); self.assertEqual(rc, 0, out)
        app = (self.t / "src/App.tsx").read_bytes()
        self.assertEqual(app.replace(b"\r\n", b"\n"), (KIT / "src/App.tsx").read_bytes().replace(b"\r\n", b"\n"))
        self.assertIn(b"\r\n", app, "a CRLF file stays CRLF")
        self.assertTrue((self.t / "src/pages/admin/DeskSite.tsx").exists())
        self.assertEqual((self.t / "docs/RELIABILITY_AUDIT.md").read_text(encoding="utf-8").count("## Phase AV - "), 1)
        rc, out = self.run_main(); self.assertIn("Nothing to do", out)

    def test_refuses_a_changed_file(self):
        (self.t / "src/App.tsx").write_bytes(self.fake["src/App.tsx"] + b"// changed\r\n")
        rc, out = self.run_main(); self.assertEqual(rc, 1); self.assertIn("REFUSE", out)
        self.assertFalse((self.t / "src/pages/admin/DeskSite.tsx").exists(), "all or nothing")


class TheFiles(unittest.TestCase):
    def test_ascii_and_marks(self):
        for f, m in ((PAT, MARK), (C30, "C30_ADMIN_STATUS_2026_11_19"), (Path(__file__), MARK)):
            if f.exists():
                b = f.read_bytes(); self.assertTrue(all(x < 128 for x in b), f.name); self.assertIn(m.encode(), b, f.name)


if __name__ == "__main__":
    unittest.main()
